"""ETF options premium / long-short margin aggregates and history.

Aligned with the etf_options market-trend口径:
  - Premium = option price × OI × multiplier
  - Long margin (权利仓) = premium (full premium paid)
  - Short margin (义务仓) = SSE/SZSE ETF option opening-margin formula
  - Primary ratio = long_margin / short_margin (多头/空头)
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from app.utils.logger import get_logger

logger = get_logger(__name__)

_DEFAULT_MULT = 10000.0
# Match etf_options `etf_option_margin.py` (docstring says 12%, runtime uses 15%).
_SHORT_MARGIN_PCT = 0.15
_SHORT_MARGIN_FLOOR_PCT = 0.07


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        return float(value)
    except Exception:
        return default


def _ratio(num: float, den: float) -> Optional[float]:
    if den is None or abs(float(den)) < 1e-12:
        return None
    try:
        return float(num) / float(den)
    except Exception:
        return None


def initial_margin_long_per_contract(option_price: float, multiplier: float = _DEFAULT_MULT) -> float:
    """权利仓开仓应付（元/张）= 期权价 × 合约单位。"""
    px = max(_safe_float(option_price), 0.0)
    mult = _safe_float(multiplier, _DEFAULT_MULT) or _DEFAULT_MULT
    return px * mult


def initial_margin_short_per_contract(
    option_price: float,
    underlying: float,
    strike: float,
    *,
    is_call: bool,
    multiplier: float = _DEFAULT_MULT,
    pct: float = _SHORT_MARGIN_PCT,
    floor_pct: float = _SHORT_MARGIN_FLOOR_PCT,
) -> float:
    """义务仓开仓保证金（元/张），与 etf_options / 上交所 ETF 期权公式一致。

    Call: [C + max(pct×S − OTM, floor×S)] × unit, OTM = max(K−S, 0)
    Put:  min(C + max(pct×S − OTM, floor×K), K) × unit, OTM = max(S−K, 0)
    """
    S = _safe_float(underlying)
    K = _safe_float(strike)
    C = max(_safe_float(option_price), 0.0)
    mult = _safe_float(multiplier, _DEFAULT_MULT) or _DEFAULT_MULT
    if S <= 0 or K <= 0 or mult <= 0:
        return 0.0
    if is_call:
        otm = max(K - S, 0.0)
        bracket = C + max(pct * S - otm, floor_pct * S)
        return bracket * mult
    otm = max(S - K, 0.0)
    inner = C + max(pct * S - otm, floor_pct * K)
    return min(inner, K) * mult


def _option_price(row: Dict[str, Any], side: str) -> float:
    """Prefer last, then mid — same preference as peer last_px / mid fallback."""
    if side == "call":
        return max(
            _safe_float(row.get("call_last") or row.get("call_mid") or row.get("call_close")),
            0.0,
        )
    return max(
        _safe_float(row.get("put_last") or row.get("put_mid") or row.get("put_close")),
        0.0,
    )


def compute_option_capital_metrics(
    chain: List[Dict[str, Any]],
    *,
    underlying: float,
    multiplier: float = _DEFAULT_MULT,
    margin_rate: float = _SHORT_MARGIN_PCT,
) -> Dict[str, Any]:
    """Aggregate premium / long-short margin / intrinsic / time-value for one chain.

    Parameters
    ----------
    margin_rate:
        Short-margin percentage coefficient (default 0.15). Kept for call-site
        compatibility; floor coefficient stays at 7%.
    """
    spot = _safe_float(underlying)
    mult = _safe_float(multiplier, _DEFAULT_MULT) or _DEFAULT_MULT
    pct = _safe_float(margin_rate, _SHORT_MARGIN_PCT) or _SHORT_MARGIN_PCT

    call_premium = 0.0
    put_premium = 0.0
    call_intrinsic = 0.0
    put_intrinsic = 0.0
    call_tv = 0.0
    put_tv = 0.0
    call_oi = 0.0
    put_oi = 0.0
    margin_long = 0.0
    margin_short = 0.0

    for row in chain or []:
        k = _safe_float(row.get("strike"))
        if k <= 0:
            continue
        c_px = _option_price(row, "call")
        p_px = _option_price(row, "put")
        c_oi = max(_safe_float(row.get("call_oi")), 0.0)
        p_oi = max(_safe_float(row.get("put_oi")), 0.0)
        c_intr = max(spot - k, 0.0) if spot > 0 else 0.0
        p_intr = max(k - spot, 0.0) if spot > 0 else 0.0
        c_tv_unit = max(c_px - c_intr, 0.0)
        p_tv_unit = max(p_px - p_intr, 0.0)

        call_oi += c_oi
        put_oi += p_oi
        call_premium += c_px * c_oi * mult
        put_premium += p_px * p_oi * mult
        call_intrinsic += c_intr * c_oi * mult
        put_intrinsic += p_intr * p_oi * mult
        call_tv += c_tv_unit * c_oi * mult
        put_tv += p_tv_unit * p_oi * mult

        if c_oi > 0:
            margin_long += initial_margin_long_per_contract(c_px, mult) * c_oi
            margin_short += (
                initial_margin_short_per_contract(
                    c_px, spot, k, is_call=True, multiplier=mult, pct=pct
                )
                * c_oi
            )
        if p_oi > 0:
            margin_long += initial_margin_long_per_contract(p_px, mult) * p_oi
            margin_short += (
                initial_margin_short_per_contract(
                    p_px, spot, k, is_call=False, multiplier=mult, pct=pct
                )
                * p_oi
            )

    premium_total = call_premium + put_premium
    intrinsic_total = call_intrinsic + put_intrinsic
    time_value_total = call_tv + put_tv
    total_oi = call_oi + put_oi
    notional = total_oi * spot * mult if spot > 0 else 0.0
    # Backward-compatible alias: "margin_total" = short (义务仓) sediment.
    margin_total = margin_short

    return {
        "call_oi": call_oi,
        "put_oi": put_oi,
        "total_oi": total_oi,
        "call_premium": call_premium,
        "put_premium": put_premium,
        "premium_total": premium_total,
        "call_intrinsic": call_intrinsic,
        "put_intrinsic": put_intrinsic,
        "intrinsic_total": intrinsic_total,
        "call_time_value": call_tv,
        "put_time_value": put_tv,
        "time_value_total": time_value_total,
        "notional": notional,
        "margin_long_total": margin_long,
        "margin_short_total": margin_short,
        "margin_total": margin_total,
        "margin_rate": pct,
        "margin_floor_rate": _SHORT_MARGIN_FLOOR_PCT,
        "multiplier": mult,
        "underlying": spot,
        "long_short_ratio": _ratio(margin_long, margin_short),
        # Kept for older clients; now premium / short-margin.
        "premium_margin_ratio": _ratio(premium_total, margin_short),
        "time_value_premium_ratio": _ratio(time_value_total, premium_total),
        "intrinsic_premium_ratio": _ratio(intrinsic_total, premium_total),
    }


def _days_to_expiry_from_T(T: float) -> int:
    """Convert year-fraction T (≈ days/365) to calendar days for peer annualization."""
    try:
        days = int(round(float(T) * 365.0))
    except Exception:
        days = 1
    return max(days, 1)


def _tv_annual_yield(time_value: float, short_margin: float, days: int) -> Optional[float]:
    """Peer formula: (TV×unit / 义务仓保证金) × (365.25 / max(days,1)).

    ``short_margin`` is already in 元/张 (includes contract unit).
    ``time_value`` is the unit option price's time value (premium − intrinsic).
    """
    if short_margin is None or short_margin <= 0:
        return None
    d = max(int(days or 1), 1)
    # time_value is per underlying unit; margin already includes multiplier,
    # so convert TV to yuan with the same unit embedded in short_margin / price space:
    # caller passes tv_yuan = time_value * multiplier.
    return (float(time_value) / float(short_margin)) * (365.25 / float(d))


def compute_etf_time_value_annualized_yield(
    chain: List[Dict[str, Any]],
    *,
    underlying: float,
    multiplier: float = _DEFAULT_MULT,
    margin_rate: float = _SHORT_MARGIN_PCT,
    T: float,
    month: str,
) -> Dict[str, Any]:
    """ETF option time-value annualized yield — same口径 as etf_options.

    Per contract:
      TV = price − intrinsic (can be negative, matching peer mid−intrinsic)
      AY = (TV × multiplier / short_margin) × (365.25 / days)

    Market composite:
      weighted average of AY by OI × short_margin (义务仓保证金),
      falling back to short_margin-only then notional (price×multiplier).
    """
    spot = _safe_float(underlying)
    mult = _safe_float(multiplier, _DEFAULT_MULT) or _DEFAULT_MULT
    pct = _safe_float(margin_rate, _SHORT_MARGIN_PCT) or _SHORT_MARGIN_PCT
    t_years = max(_safe_float(T), 1.0 / 365.0)
    days = _days_to_expiry_from_T(t_years)
    call_points: List[Dict[str, Any]] = []
    put_points: List[Dict[str, Any]] = []
    if spot <= 0 or mult <= 0:
        return {
            "month": month,
            "T": t_years,
            "days_to_expiry": days,
            "call": [],
            "put": [],
            "market_yield": None,
            "market_yield_weight": "",
            "note": "invalid underlying/multiplier",
        }

    weight_rows: List[Dict[str, float]] = []

    for row in chain or []:
        k = _safe_float(row.get("strike"))
        if k <= 0:
            continue
        for side, is_call in (("call", True), ("put", False)):
            px = _option_price(row, side)
            if px <= 0:
                continue
            oi = max(_safe_float(row.get(f"{side}_oi")), 0.0)
            intrinsic = max(spot - k, 0.0) if is_call else max(k - spot, 0.0)
            # Peer keeps signed time value (mid − intrinsic); do not floor at 0.
            tv = px - intrinsic
            short_m = initial_margin_short_per_contract(
                px, spot, k, is_call=is_call, multiplier=mult, pct=pct
            )
            tv_yuan = tv * mult
            ay = _tv_annual_yield(tv_yuan, short_m, days)
            point = {
                "strike": k,
                "time_value": tv,
                "premium": px,
                "margin": short_m,
                "oi": oi,
                "weight": oi * short_m if short_m > 0 else 0.0,
                "yield": ay,
                "side": side,
                "month": month,
            }
            if side == "call":
                call_points.append(point)
            else:
                put_points.append(point)
            if ay is not None:
                weight_rows.append(
                    {
                        "yield": float(ay),
                        "oi_margin": float(oi * short_m) if short_m > 0 else 0.0,
                        "margin": float(short_m) if short_m > 0 else 0.0,
                        "notional": float(px * mult),
                    }
                )

    market_yield = None
    weight_label = ""
    if weight_rows:
        candidates = [
            ("oi_margin", "OI×义务仓保证金加权"),
            ("margin", "义务仓保证金加权"),
            ("notional", "名义(价格×乘数)加权"),
        ]
        for key, label in candidates:
            num = 0.0
            den = 0.0
            for r in weight_rows:
                w = float(r.get(key) or 0.0)
                if w <= 0:
                    continue
                num += float(r["yield"]) * w
                den += w
            if den > 0:
                market_yield = num / den
                weight_label = label
                break

    return {
        "month": month,
        "T": t_years,
        "days_to_expiry": days,
        "call": call_points,
        "put": put_points,
        "market_yield": market_yield,
        "market_yield_weight": weight_label,
        "note": (
            "时间价值年化=(时间价值×合约乘数/义务仓保证金)×(365.25/剩余自然日)；"
            "全市场综合按 OI×义务仓保证金加权（回退：义务仓保证金 / 名义）。"
        ),
    }


def combine_market_tv_yields(tv_payloads: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Combine per-month TV/AY payloads into one market composite (OI×margin weights)."""
    weight_rows: List[Dict[str, float]] = []
    for payload in tv_payloads or []:
        for side in ("call", "put"):
            for p in payload.get(side) or []:
                ay = p.get("yield")
                if ay is None:
                    continue
                short_m = _safe_float(p.get("margin"))
                oi = max(_safe_float(p.get("oi")), 0.0)
                px = max(_safe_float(p.get("premium")), 0.0)
                # Reconstruct notional weight from premium when multiplier unknown:
                # point.weight was oi*margin; notional≈premium is unit price — use
                # margin as yuan and premium*implied via weight when possible.
                weight_rows.append(
                    {
                        "yield": float(ay),
                        "oi_margin": float(oi * short_m) if short_m > 0 else float(p.get("weight") or 0.0),
                        "margin": float(short_m) if short_m > 0 else 0.0,
                        # premium here is unit price; without mult use oi*margin fallback only
                        "notional": float(p.get("weight") or 0.0) if short_m <= 0 else float(px) * max(oi, 1.0),
                    }
                )
    market_yield = None
    weight_label = ""
    if weight_rows:
        for key, label in (
            ("oi_margin", "OI×义务仓保证金加权"),
            ("margin", "义务仓保证金加权"),
            ("notional", "名义加权"),
        ):
            num = den = 0.0
            for r in weight_rows:
                w = float(r.get(key) or 0.0)
                if w <= 0:
                    continue
                num += float(r["yield"]) * w
                den += w
            if den > 0:
                market_yield = num / den
                weight_label = label
                break
    return {"market_yield": market_yield, "market_yield_weight": weight_label}


def build_capital_curve_by_month(
    month_chains: Dict[str, List[Dict[str, Any]]],
    *,
    underlying: float,
    multiplier: float = _DEFAULT_MULT,
    margin_rate: float = _SHORT_MARGIN_PCT,
    months: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Build per-month capital metrics + all-month total for live charts."""
    order = list(months or sorted(month_chains.keys()))
    points: List[Dict[str, Any]] = []
    for month in order:
        chain = month_chains.get(month) or []
        if not chain:
            continue
        metrics = compute_option_capital_metrics(
            chain,
            underlying=underlying,
            multiplier=multiplier,
            margin_rate=margin_rate,
        )
        points.append({"month": month, **metrics})

    total = {
        "premium_total": sum(float(p.get("premium_total") or 0.0) for p in points),
        "margin_long_total": sum(float(p.get("margin_long_total") or 0.0) for p in points),
        "margin_short_total": sum(float(p.get("margin_short_total") or 0.0) for p in points),
        "margin_total": sum(float(p.get("margin_short_total") or 0.0) for p in points),
        "intrinsic_total": sum(float(p.get("intrinsic_total") or 0.0) for p in points),
        "time_value_total": sum(float(p.get("time_value_total") or 0.0) for p in points),
        "notional": sum(float(p.get("notional") or 0.0) for p in points),
        "total_oi": sum(float(p.get("total_oi") or 0.0) for p in points),
        "margin_rate": margin_rate,
        "margin_floor_rate": _SHORT_MARGIN_FLOOR_PCT,
        "multiplier": multiplier,
        "underlying": underlying,
    }
    total["long_short_ratio"] = _ratio(total["margin_long_total"], total["margin_short_total"])
    total["premium_margin_ratio"] = _ratio(total["premium_total"], total["margin_short_total"])
    total["time_value_premium_ratio"] = _ratio(total["time_value_total"], total["premium_total"])
    total["intrinsic_premium_ratio"] = _ratio(total["intrinsic_total"], total["premium_total"])
    return {
        "points": points,
        "total": total,
        "note": (
            "权利金=期权价格×持仓×合约乘数；"
            "多头保证金=权利仓应付权利金；"
            "空头保证金=交易所ETF期权义务仓开仓保证金（15%/7%公式）；"
            "多头/空头=多头保证金÷空头保证金；"
            "内在价值/时间价值按持仓加权。"
        ),
    }


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


def build_etf_options_capital_history(
    code: str,
    *,
    chart_key: str = "options.capital",
    interval: str = "day",
    bars: int = 60,
    month: str = "all",
) -> Dict[str, Any]:
    """Historical premium / long-short margin curves from ClickHouse slices."""
    from app.services.etf_options_clickhouse import (
        build_strike_chains_by_month,
        ch_ping,
        etf_options_ch_enabled,
        fetch_option_chain_rows_at_timestamps,
        list_playback_timestamps,
        normalize_playback_bars,
        normalize_playback_interval,
    )

    code6 = "".join(ch for ch in str(code or "") if ch.isdigit())[:6]
    interval_n = normalize_playback_interval(interval)
    bars_n = normalize_playback_bars(bars)
    month_raw = str(month or "all").strip().lower()
    empty = {
        "root": code6,
        "chart_key": chart_key or "options.capital",
        "mode": "daily",
        "interval": interval_n,
        "bars": bars_n,
        "points": [],
        "note": "",
        "asof": datetime.now().isoformat(timespec="seconds"),
    }
    if not code6:
        empty["note"] = "ETF code is required"
        return empty
    if not etf_options_ch_enabled() or not ch_ping():
        empty["note"] = "ClickHouse ETF options history unavailable"
        return empty

    timestamps = list_playback_timestamps(code6, interval=interval_n, bars=bars_n)
    if not timestamps:
        empty["note"] = "no playback timestamps in ClickHouse for this underlying/interval"
        return empty

    by_ts, meta = fetch_option_chain_rows_at_timestamps(code6, timestamps)
    underlying_by_ts: Dict[str, float] = {}
    try:
        from app.services.etf_options_clickhouse import fetch_underlying_series

        underlying_by_ts = fetch_underlying_series(code6, timestamps) or {}
    except Exception as exc:
        logger.debug("underlying series lookup skipped: %s", exc)

    points: List[Dict[str, Any]] = []
    for ts in timestamps:
        flat = by_ts.get(ts) or by_ts.get(ts[:19]) or []
        if not flat:
            continue
        chains = build_strike_chains_by_month(flat)
        if month_raw not in {"", "all", "none"} and month_raw in chains:
            chains = {month_raw: chains.get(month_raw) or []}
        spot = float(underlying_by_ts.get(ts[:19]) or 0.0)
        if spot <= 0:
            for row in flat:
                spot = _safe_float(row.get("underlying_price"))
                if spot > 0:
                    break
        if spot <= 0:
            continue
        curve = build_capital_curve_by_month(
            chains,
            underlying=spot,
            multiplier=_DEFAULT_MULT,
            margin_rate=_SHORT_MARGIN_PCT,
        )
        total = curve.get("total") or {}
        asof = _parse_ts(ts)
        points.append(
            {
                "date": (asof.date().isoformat() if asof else str(ts)[:10]),
                "ts": ts,
                "underlying": spot,
                "premium_total": total.get("premium_total"),
                "margin_long_total": total.get("margin_long_total"),
                "margin_short_total": total.get("margin_short_total"),
                "margin_total": total.get("margin_short_total"),
                "intrinsic_total": total.get("intrinsic_total"),
                "time_value_total": total.get("time_value_total"),
                "long_short_ratio": total.get("long_short_ratio"),
                "premium_margin_ratio": total.get("premium_margin_ratio"),
                "time_value_premium_ratio": total.get("time_value_premium_ratio"),
                "intrinsic_premium_ratio": total.get("intrinsic_premium_ratio"),
                "total_oi": total.get("total_oi"),
            }
        )

    note = (
        f"按 {interval_n} 取最近 {bars_n} 根，用 ClickHouse 期权切片回放权利金/多空保证金。"
        " 日级时间戳取各交易日最后一根期权报价分钟（通常≈14:55–14:56）。"
        " 多头保证金=权利金；空头保证金=交易所义务仓开仓保证金（15%/7%）；"
        " 多头/空头=多头保证金÷空头保证金。"
        " 到期月切换日总量可能因整月合约摘牌而台阶式变化。"
    )
    if meta.get("error"):
        note += f" meta_error={meta.get('error')}"

    return {
        "root": code6,
        "chart_key": chart_key or "options.capital",
        "mode": "daily",
        "interval": interval_n,
        "bars": bars_n,
        "month": month_raw or "all",
        "points": points,
        "note": note,
        "asof": datetime.now().isoformat(timespec="seconds"),
        "meta": meta,
    }
