"""Futures options history playback using underlying bar series + live OI structure.

Unlike ETF options (ClickHouse minute chains), CFFEX commodity/index option chains
have no public historical OI snapshots in this deployment. We replay surfaces by
holding the **current** chain OI fixed and repricing/recalculating greeks at each
historical underlying close from the continuous futures daily series.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from app.services.cn_derivatives_analytics import (
    _ak,
    _normalize_history_date,
    _product_payload,
    _safe_float,
    _time_value_annualized_yield,
    _year_fraction_to_month,
    build_options_panel,
    compute_max_pain,
)
from app.services.cn_derivatives_etf_capital import (
    build_capital_curve_by_month,
    compute_option_capital_metrics,
)
from app.services.etf_options_clickhouse import (
    normalize_playback_bars,
    normalize_playback_interval,
)
from app.services.gex_indicator import (
    compute_gex_raw,
    derive_gex_levels,
    panel_fields_from_gex_indicator,
    run_gex_indicator,
    summary_from_gex_points,
)
from app.utils.logger import get_logger

logger = get_logger(__name__)

_SURFACE_CHARTS = {
    "options.iv",
    "options.oi",
    "options.tv",
    "options.maxPain",
    "options.max_pain",
}

_APPROX_NOTE = (
    "期货期权公开链历史有限：回放使用连续合约日线收盘价作为标的，"
    "OI/链结构取当前截面并重算 GEX/IV/时间价值/Max Pain（近似趋势，非真实历史 OI）。"
)


def is_futures_surface_history_chart(chart_key: str) -> bool:
    return str(chart_key or "").strip() in _SURFACE_CHARTS


def _parse_ts(value: str) -> Optional[datetime]:
    text = str(value or "").strip()[:19]
    if not text:
        return None
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue
    return None


def _resample_bars(rows: List[Dict[str, Any]], interval: str) -> List[Dict[str, Any]]:
    if interval == "week" and len(rows) > 1:
        out: List[Dict[str, Any]] = []
        bucket: List[Dict[str, Any]] = []
        for row in rows:
            bucket.append(row)
            if len(bucket) >= 5:
                out.append(bucket[-1])
                bucket = []
        if bucket:
            out.append(bucket[-1])
        return out
    return rows


def _underlying_daily_bars(root: str, *, bars: int, interval: str) -> List[Dict[str, Any]]:
    root_u = str(root or "").upper()
    product = _product_payload(root_u)
    symbol = str(product.get("continuous_symbol") or f"{root_u}0")
    frame = None
    try:
        frame = _ak().futures_zh_daily_sina(symbol=symbol)
    except Exception as exc:
        logger.warning("futures underlying daily failed root=%s: %s", root_u, exc)
    if frame is None or getattr(frame, "empty", True):
        return []
    tail = frame.tail(max(bars * 2, bars))
    rows: List[Dict[str, Any]] = []
    for _, row in tail.iterrows():
        date_v = _normalize_history_date(row.get("date") or row.get("datetime")) or ""
        price = _safe_float(row.get("close") or row.get("settle"))
        if not date_v or price <= 0:
            continue
        rows.append(
            {
                "ts": f"{date_v} 15:00:00",
                "label": date_v,
                "date": date_v,
                "underlying": price,
                "close": price,
            }
        )
    rows = _resample_bars(rows, interval)
    return rows[-bars:]


def _chains_by_month_from_panel(panel: Dict[str, Any], month: str) -> Dict[str, List[Dict[str, Any]]]:
    month_raw = str(month or "all").strip().lower()
    out: Dict[str, List[Dict[str, Any]]] = {}
    for ms in panel.get("month_series") or []:
        mkey = str(ms.get("month") or "")
        dist = ms.get("gex_distribution") or []
        if not mkey or not dist:
            continue
        chain: List[Dict[str, Any]] = []
        for p in dist:
            chain.append(
                {
                    "strike": p.get("strike"),
                    "call_oi": p.get("call_oi"),
                    "put_oi": p.get("put_oi"),
                    "call_price": p.get("call_price"),
                    "put_price": p.get("put_price"),
                    "call_iv": p.get("call_iv"),
                    "put_iv": p.get("put_iv"),
                }
            )
        if chain:
            out[mkey] = chain
    if out:
        if month_raw not in {"", "all", "*", "全部"}:
            wanted = str(month or "").strip()
            filtered = {
                k: v
                for k, v in out.items()
                if k == wanted or k.lower() == wanted.lower() or k.endswith(wanted[-4:])
            }
            if filtered:
                return filtered
        return out
    agg = panel.get("chain") or []
    sel = str(panel.get("month") or "all")
    if agg:
        return {sel: agg}
    return {}


def _recompute_month_slice(
    chains_by_month: Dict[str, List[Dict[str, Any]]],
    *,
    underlying: float,
    asof: datetime,
    multiplier: float,
    margin_rate: float,
) -> Dict[str, Any]:
    month_series: List[Dict[str, Any]] = []
    all_points: List[Dict[str, Any]] = []
    for month, chain in sorted(chains_by_month.items()):
        if not chain:
            continue
        T = _year_fraction_to_month(month)
        raw = compute_gex_raw(
            chain,
            underlying=float(underlying or 0.0),
            multiplier=multiplier,
            T=T,
        )
        points = list(raw.get("points") or [])
        indicator = run_gex_indicator(
            chain,
            underlying=float(underlying or 0.0),
            multiplier=multiplier,
            T=T,
            name=f"GEX {month}",
        )
        gex_fields = panel_fields_from_gex_indicator(indicator)
        max_pain = compute_max_pain(chain)
        tv_yield = _time_value_annualized_yield(
            chain,
            underlying=float(underlying or 0.0),
            multiplier=multiplier,
            margin_rate=margin_rate,
            T=T,
            month=month,
        )
        month_series.append(
            {
                "month": month,
                "underlying": underlying,
                "gex_distribution": gex_fields.get("gex_distribution") or points,
                "gex_summary": gex_fields.get("gex_summary") or summary_from_gex_points(points, underlying=underlying),
                "iv_smile": gex_fields.get("iv_smile") or list(raw.get("iv_smile") or []),
                "max_pain": max_pain,
                "time_value_yield": tv_yield,
            }
        )
        all_points.extend(points)

    if len(month_series) == 1:
        primary = month_series[0]
        gex_distribution = primary.get("gex_distribution") or []
        gex_summary = primary.get("gex_summary") or {}
    else:
        from app.services.cn_derivatives_analytics import _aggregate_chains_by_strike

        flat_chains = []
        for chain in chains_by_month.values():
            flat_chains.append(chain)
        agg_chain = _aggregate_chains_by_strike(flat_chains)
        T = 30 / 365.0
        raw = compute_gex_raw(
            agg_chain,
            underlying=float(underlying or 0.0),
            multiplier=multiplier,
            T=T,
        )
        gex_distribution = list(raw.get("points") or [])
        gex_summary = summary_from_gex_points(gex_distribution, underlying=underlying)

    levels = derive_gex_levels(gex_distribution, underlying=underlying)
    for key in ("call_wall", "put_wall", "pin", "flip"):
        gex_summary[key] = levels.get(key)

    return {
        "gex_distribution": gex_distribution,
        "gex_summary": gex_summary,
        "month_series": month_series,
        "levels": levels,
        "underlying": underlying,
        "current_price": underlying,
    }


def _near_month_atm_iv(smile: List[Dict[str, Any]], underlying: float) -> Optional[float]:
    spot = float(underlying or 0.0)
    if spot <= 0 or not smile:
        return None
    by_strike: Dict[float, List[float]] = {}
    for point in smile:
        try:
            strike = float(point.get("strike") or 0.0)
            iv = float(point.get("iv") or 0.0)
        except (TypeError, ValueError):
            continue
        if strike <= 0 or iv <= 0:
            continue
        by_strike.setdefault(strike, []).append(iv)
    if not by_strike:
        return None
    nearest = min(by_strike.keys(), key=lambda k: abs(k - spot))
    vals = by_strike[nearest]
    return float(sum(vals) / len(vals)) if vals else None


def build_futures_options_gex_playback(
    root: str,
    *,
    interval: str = "day",
    bars: int = 60,
    month: str = "all",
) -> Dict[str, Any]:
    root_u = str(root or "").upper()
    interval_n = normalize_playback_interval(interval)
    bars_n = normalize_playback_bars(bars)
    asof = datetime.now().isoformat(timespec="seconds")
    empty: Dict[str, Any] = {
        "root": root_u,
        "chart_key": "options.gex",
        "mode": "gex_playback",
        "interval": interval_n,
        "bars": bars_n,
        "slices": [],
        "levels_series": [],
        "note": "",
        "asof": asof,
    }
    panel = build_options_panel(root_u, month=month or "all")
    if not panel.get("available"):
        empty["note"] = panel.get("message") or "options unavailable"
        return empty
    chains_by_month = _chains_by_month_from_panel(panel, month)
    if not chains_by_month:
        empty["note"] = "empty option chain"
        return empty

    mult = float(panel.get("multiplier") or 1)
    margin_rate = float(panel.get("margin_rate") or 0.12)
    bar_rows = _underlying_daily_bars(root_u, bars=bars_n, interval=interval_n)
    if not bar_rows:
        live = _recompute_month_slice(
            chains_by_month,
            underlying=float(panel.get("current_price") or panel.get("underlying") or 0.0),
            asof=datetime.now(),
            multiplier=mult,
            margin_rate=margin_rate,
        )
        ts = asof[:19]
        empty["slices"] = [
            {
                "ts": ts,
                "date": ts[:10],
                "label": "当前",
                **live,
            }
        ]
        empty["levels_series"] = [
            {
                "ts": ts,
                "label": "当前",
                "underlying": live.get("underlying"),
                **(live.get("levels") or {}),
            }
        ]
        empty["note"] = _APPROX_NOTE + " 标的日线不可用，仅返回当前截面。"
        return empty

    slices: List[Dict[str, Any]] = []
    levels_series: List[Dict[str, Any]] = []
    for bar in bar_rows:
        ts = str(bar.get("ts") or bar.get("label") or "")
        spot = float(bar.get("underlying") or bar.get("close") or 0.0)
        asof_dt = _parse_ts(ts) or datetime.now()
        payload = _recompute_month_slice(
            chains_by_month,
            underlying=spot,
            asof=asof_dt,
            multiplier=mult,
            margin_rate=margin_rate,
        )
        levels = payload.get("levels") or {}
        slices.append(
            {
                "ts": ts,
                "date": str(bar.get("date") or ts[:10]),
                "label": bar.get("label") or ts[:10],
                **payload,
            }
        )
        levels_series.append(
            {
                "ts": ts,
                "label": bar.get("label") or ts[:10],
                "underlying": spot,
                "call_wall": levels.get("call_wall"),
                "put_wall": levels.get("put_wall"),
                "flip": levels.get("flip"),
                "pin": levels.get("pin"),
            }
        )

    empty["slices"] = slices
    empty["levels_series"] = levels_series
    empty["note"] = (
        f"按 {interval_n} 连续合约日线回放最近 {bars_n} 根；{_APPROX_NOTE}"
    )
    return empty


def build_futures_options_surface_history(
    root: str,
    *,
    chart_key: str = "options.iv",
    interval: str = "day",
    bars: int = 60,
    month: str = "all",
) -> Dict[str, Any]:
    gex = build_futures_options_gex_playback(
        root,
        interval=interval,
        bars=bars,
        month=month,
    )
    chart = str(chart_key or "options.iv").strip() or "options.iv"
    want_iv = chart == "options.iv"
    want_max_pain = chart in {"options.maxPain", "options.max_pain"}
    out: Dict[str, Any] = {
        "root": gex.get("root"),
        "chart_key": chart,
        "mode": "slices",
        "interval": gex.get("interval"),
        "bars": gex.get("bars"),
        "slices": [],
        "near_month_iv_klines": [],
        "near_month_max_pain_series": [],
        "note": gex.get("note") or _APPROX_NOTE,
        "asof": gex.get("asof"),
    }
    slices_out: List[Dict[str, Any]] = []
    iv_klines: List[Dict[str, Any]] = []
    mp_series: List[Dict[str, Any]] = []

    for sl in gex.get("slices") or []:
        ms = sl.get("month_series") or []
        primary = ms[0] if ms else {}
        surface_slice = {
            "ts": sl.get("ts"),
            "date": sl.get("date"),
            "label": sl.get("label"),
            "underlying": sl.get("underlying"),
            "current_price": sl.get("current_price"),
            "gex_distribution": sl.get("gex_distribution") or [],
            "gex_summary": sl.get("gex_summary") or {},
            "month_series": ms,
            "iv_smile": primary.get("iv_smile") or [],
            "max_pain": primary.get("max_pain"),
            "time_value_yield": primary.get("time_value_yield") or {},
        }
        slices_out.append(surface_slice)

        if want_iv:
            atm = _near_month_atm_iv(surface_slice.get("iv_smile") or [], float(sl.get("underlying") or 0.0))
            if atm is not None:
                iv_klines.append(
                    {
                        "ts": sl.get("ts"),
                        "label": sl.get("label"),
                        "date": sl.get("date"),
                        "month": primary.get("month"),
                        "open": atm,
                        "high": atm,
                        "low": atm,
                        "close": atm,
                        "underlying": sl.get("underlying"),
                    }
                )
        if want_max_pain:
            mp = primary.get("max_pain") or {}
            mp_series.append(
                {
                    "ts": sl.get("ts"),
                    "label": sl.get("label"),
                    "date": sl.get("date"),
                    "month": primary.get("month"),
                    "underlying": sl.get("underlying"),
                    "max_pain": mp.get("strike"),
                }
            )

    out["slices"] = slices_out
    out["near_month_iv_klines"] = iv_klines
    out["near_month_max_pain_series"] = mp_series
    if not slices_out:
        out["note"] = (gex.get("note") or "") + " 无可用回放切片。"
    return out


def build_futures_options_capital_history(
    root: str,
    *,
    chart_key: str = "options.capital",
    interval: str = "day",
    bars: int = 60,
    month: str = "all",
) -> Dict[str, Any]:
    root_u = str(root or "").upper()
    interval_n = normalize_playback_interval(interval)
    bars_n = normalize_playback_bars(bars)
    asof = datetime.now().isoformat(timespec="seconds")
    empty: Dict[str, Any] = {
        "root": root_u,
        "chart_key": chart_key or "options.capital",
        "mode": "daily",
        "interval": interval_n,
        "bars": bars_n,
        "points": [],
        "note": "",
        "asof": asof,
    }
    panel = build_options_panel(root_u, month=month or "all")
    if not panel.get("available"):
        empty["note"] = panel.get("message") or "options unavailable"
        return empty
    chains_by_month = _chains_by_month_from_panel(panel, month)
    if not chains_by_month:
        empty["note"] = "empty option chain"
        return empty

    mult = float(panel.get("multiplier") or 1)
    margin_rate = float(panel.get("margin_rate") or 0.12)
    bar_rows = _underlying_daily_bars(root_u, bars=bars_n, interval=interval_n)
    points: List[Dict[str, Any]] = []

    if not bar_rows:
        spot = float(panel.get("current_price") or panel.get("underlying") or 0.0)
        curve = build_capital_curve_by_month(
            chains_by_month,
            underlying=spot,
            multiplier=mult,
            margin_rate=margin_rate,
        )
        total = curve.get("total") or {}
        points.append(
            {
                "date": asof[:10],
                "ts": asof[:19],
                "underlying": spot,
                **{k: total.get(k) for k in (
                    "premium_total", "margin_long_total", "margin_short_total",
                    "intrinsic_total", "time_value_total", "long_short_ratio",
                    "premium_margin_ratio", "total_oi",
                )},
                "margin_total": total.get("margin_short_total"),
            }
        )
        empty["points"] = points
        empty["note"] = _APPROX_NOTE + " 标的日线不可用，仅返回当前截面。"
        return empty

    for bar in bar_rows:
        spot = float(bar.get("underlying") or bar.get("close") or 0.0)
        if spot <= 0:
            continue
        curve = build_capital_curve_by_month(
            chains_by_month,
            underlying=spot,
            multiplier=mult,
            margin_rate=margin_rate,
        )
        total = curve.get("total") or {}
        points.append(
            {
                "date": bar.get("date") or str(bar.get("label") or "")[:10],
                "ts": bar.get("ts"),
                "underlying": spot,
                "premium_total": total.get("premium_total"),
                "margin_long_total": total.get("margin_long_total"),
                "margin_short_total": total.get("margin_short_total"),
                "margin_total": total.get("margin_short_total"),
                "intrinsic_total": total.get("intrinsic_total"),
                "time_value_total": total.get("time_value_total"),
                "long_short_ratio": total.get("long_short_ratio"),
                "premium_margin_ratio": total.get("premium_margin_ratio"),
                "total_oi": total.get("total_oi"),
            }
        )

    empty["points"] = points
    empty["note"] = f"按 {interval_n} 连续合约日线回放最近 {bars_n} 根；{_APPROX_NOTE}"
    return empty
