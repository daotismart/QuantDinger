"""ETF options premium / margin / value-ratio aggregates and history."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any, Dict, List, Optional, Tuple

from app.utils.logger import get_logger

logger = get_logger(__name__)

_DEFAULT_MULT = 10000.0
_DEFAULT_MARGIN_RATE = 0.12


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


def compute_option_capital_metrics(
    chain: List[Dict[str, Any]],
    *,
    underlying: float,
    multiplier: float = _DEFAULT_MULT,
    margin_rate: float = _DEFAULT_MARGIN_RATE,
) -> Dict[str, Any]:
    """Aggregate premium / seller-margin / intrinsic / time-value for one chain.

    Premium = mid * OI * multiplier
    Margin  ≈ OI * underlying * multiplier * margin_rate  (seller margin proxy)
    Intrinsic / time-value are OI-weighted contract values.
    """
    spot = _safe_float(underlying)
    mult = _safe_float(multiplier, _DEFAULT_MULT) or _DEFAULT_MULT
    rate = _safe_float(margin_rate, _DEFAULT_MARGIN_RATE) or _DEFAULT_MARGIN_RATE

    call_premium = 0.0
    put_premium = 0.0
    call_intrinsic = 0.0
    put_intrinsic = 0.0
    call_tv = 0.0
    put_tv = 0.0
    call_oi = 0.0
    put_oi = 0.0

    for row in chain or []:
        k = _safe_float(row.get("strike"))
        if k <= 0:
            continue
        c_mid = max(_safe_float(row.get("call_mid") or row.get("call_last")), 0.0)
        p_mid = max(_safe_float(row.get("put_mid") or row.get("put_last")), 0.0)
        c_oi = max(_safe_float(row.get("call_oi")), 0.0)
        p_oi = max(_safe_float(row.get("put_oi")), 0.0)
        c_intr = max(spot - k, 0.0) if spot > 0 else 0.0
        p_intr = max(k - spot, 0.0) if spot > 0 else 0.0
        c_tv_unit = max(c_mid - c_intr, 0.0)
        p_tv_unit = max(p_mid - p_intr, 0.0)

        call_oi += c_oi
        put_oi += p_oi
        call_premium += c_mid * c_oi * mult
        put_premium += p_mid * p_oi * mult
        call_intrinsic += c_intr * c_oi * mult
        put_intrinsic += p_intr * p_oi * mult
        call_tv += c_tv_unit * c_oi * mult
        put_tv += p_tv_unit * p_oi * mult

    premium_total = call_premium + put_premium
    intrinsic_total = call_intrinsic + put_intrinsic
    time_value_total = call_tv + put_tv
    total_oi = call_oi + put_oi
    notional = total_oi * spot * mult if spot > 0 else 0.0
    margin_total = notional * rate

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
        "margin_total": margin_total,
        "margin_rate": rate,
        "multiplier": mult,
        "underlying": spot,
        "premium_margin_ratio": _ratio(premium_total, margin_total),
        "time_value_premium_ratio": _ratio(time_value_total, premium_total),
        "intrinsic_premium_ratio": _ratio(intrinsic_total, premium_total),
    }


def build_capital_curve_by_month(
    month_chains: Dict[str, List[Dict[str, Any]]],
    *,
    underlying: float,
    multiplier: float = _DEFAULT_MULT,
    margin_rate: float = _DEFAULT_MARGIN_RATE,
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
        item = {"month": month, **metrics}
        points.append(item)

    # Aggregate totals across months (OI-weighted already inside each month).
    total = {
        "premium_total": sum(float(p.get("premium_total") or 0.0) for p in points),
        "margin_total": sum(float(p.get("margin_total") or 0.0) for p in points),
        "intrinsic_total": sum(float(p.get("intrinsic_total") or 0.0) for p in points),
        "time_value_total": sum(float(p.get("time_value_total") or 0.0) for p in points),
        "notional": sum(float(p.get("notional") or 0.0) for p in points),
        "total_oi": sum(float(p.get("total_oi") or 0.0) for p in points),
        "margin_rate": margin_rate,
        "multiplier": multiplier,
        "underlying": underlying,
    }
    total["premium_margin_ratio"] = _ratio(total["premium_total"], total["margin_total"])
    total["time_value_premium_ratio"] = _ratio(total["time_value_total"], total["premium_total"])
    total["intrinsic_premium_ratio"] = _ratio(total["intrinsic_total"], total["premium_total"])
    return {
        "points": points,
        "total": total,
        "note": (
            "权利金=期权中间价×持仓×合约乘数；"
            "保证金≈持仓×标的价×合约乘数×卖方保证金率；"
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
    """Historical premium/margin/ratio curves from ClickHouse option slices."""
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
            margin_rate=_DEFAULT_MARGIN_RATE,
        )
        total = curve.get("total") or {}
        asof = _parse_ts(ts)
        points.append(
            {
                "date": (asof.date().isoformat() if asof else str(ts)[:10]),
                "ts": ts,
                "underlying": spot,
                "premium_total": total.get("premium_total"),
                "margin_total": total.get("margin_total"),
                "intrinsic_total": total.get("intrinsic_total"),
                "time_value_total": total.get("time_value_total"),
                "premium_margin_ratio": total.get("premium_margin_ratio"),
                "time_value_premium_ratio": total.get("time_value_premium_ratio"),
                "intrinsic_premium_ratio": total.get("intrinsic_premium_ratio"),
                "total_oi": total.get("total_oi"),
            }
        )

    note = (
        f"按 {interval_n} 取最近 {bars_n} 根，用 ClickHouse 期权切片回放权利金/保证金及比率。"
        " 保证金为卖方保证金近似（持仓×标的×乘数×保证金率）。"
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
