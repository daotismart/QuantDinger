"""IV Rank time series for market-composite options / ETF options pages.

ETF options: rank of near-month ATM implied vol from ClickHouse playback.
Futures options: rank of 20-day realized vol of the continuous contract
(historical implied vol is not stored for CFFEX chains in this deployment).
"""

from __future__ import annotations

import math
from datetime import datetime
from typing import Any, Dict, List, Optional, Sequence

from app.utils.logger import get_logger

logger = get_logger(__name__)

_IV_RANK_CHARTS = {"options.ivRank", "options.iv_rank"}
_DEFAULT_LOOKBACK = 252
_HV_WINDOW = 20


def is_iv_rank_chart(chart_key: str) -> bool:
    return str(chart_key or "").strip() in _IV_RANK_CHARTS


def realized_vol_series(closes: Sequence[float], *, window: int = _HV_WINDOW) -> List[float]:
    values = [float(item) for item in closes if item is not None and float(item) > 0]
    if len(values) < window + 1:
        return []
    logs: List[float] = []
    for index in range(1, len(values)):
        prev = values[index - 1]
        current = values[index]
        if prev <= 0 or current <= 0:
            logs.append(0.0)
        else:
            logs.append(math.log(current / prev))
    out: List[float] = []
    for end in range(window, len(logs) + 1):
        chunk = logs[end - window : end]
        mean = sum(chunk) / window
        var = sum((item - mean) ** 2 for item in chunk) / max(window - 1, 1)
        out.append(math.sqrt(max(var, 0.0)) * math.sqrt(252.0))
    return out


def rolling_iv_rank(values: Sequence[Optional[float]], *, lookback: int = _DEFAULT_LOOKBACK) -> List[Optional[float]]:
    """IV Rank of each point versus the trailing ``lookback`` observations."""
    window = max(2, int(lookback or _DEFAULT_LOOKBACK))
    out: List[Optional[float]] = []
    for index, raw in enumerate(values):
        try:
            current = float(raw) if raw is not None else None
        except (TypeError, ValueError):
            current = None
        if current is None or current <= 0:
            out.append(None)
            continue
        start = max(0, index - window + 1)
        sample = []
        for item in values[start : index + 1]:
            try:
                number = float(item) if item is not None else None
            except (TypeError, ValueError):
                number = None
            if number is not None and number > 0:
                sample.append(number)
        if len(sample) < 2:
            out.append(50.0)
            continue
        lo = min(sample)
        hi = max(sample)
        if hi <= lo:
            out.append(50.0)
        else:
            out.append(100.0 * (current - lo) / (hi - lo))
    return out


def rolling_iv_percentile(values: Sequence[Optional[float]], *, lookback: int = _DEFAULT_LOOKBACK) -> List[Optional[float]]:
    window = max(2, int(lookback or _DEFAULT_LOOKBACK))
    out: List[Optional[float]] = []
    for index, raw in enumerate(values):
        try:
            current = float(raw) if raw is not None else None
        except (TypeError, ValueError):
            current = None
        if current is None or current <= 0:
            out.append(None)
            continue
        start = max(0, index - window + 1)
        sample = []
        for item in values[start : index + 1]:
            try:
                number = float(item) if item is not None else None
            except (TypeError, ValueError):
                number = None
            if number is not None and number > 0:
                sample.append(number)
        if not sample:
            out.append(None)
            continue
        below = sum(1 for item in sample if item < current)
        out.append(100.0 * below / len(sample))
    return out


def _snapshot(points: List[Dict[str, Any]]) -> Dict[str, Any]:
    for row in reversed(points):
        if row.get("iv_rank") is None:
            continue
        return {
            "iv_rank": row.get("iv_rank"),
            "iv_percentile": row.get("iv_percentile"),
            "atm_iv": row.get("atm_iv"),
            "ts": row.get("ts") or row.get("date"),
            "proxy": row.get("proxy"),
        }
    return {"iv_rank": None, "iv_percentile": None, "atm_iv": None}


def points_from_iv_values(
    rows: Sequence[Dict[str, Any]],
    *,
    value_key: str = "close",
    lookback: int = _DEFAULT_LOOKBACK,
    proxy: str = "atm_iv",
) -> List[Dict[str, Any]]:
    values: List[Optional[float]] = []
    for row in rows:
        try:
            number = float(row.get(value_key) or 0.0)
        except (TypeError, ValueError):
            number = 0.0
        values.append(number if number > 0 else None)
    ranks = rolling_iv_rank(values, lookback=lookback)
    percentiles = rolling_iv_percentile(values, lookback=lookback)
    points: List[Dict[str, Any]] = []
    for row, value, rank, percentile in zip(rows, values, ranks, percentiles):
        date_s = str(row.get("date") or row.get("label") or row.get("ts") or "")[:10]
        points.append(
            {
                "ts": row.get("ts") or row.get("label") or date_s,
                "label": row.get("label") or date_s,
                "date": date_s,
                "month": row.get("month"),
                "atm_iv": value,
                "iv_rank": rank,
                "iv_percentile": percentile,
                "proxy": proxy,
            }
        )
    return points


def _payload(
    *,
    root: str,
    points: List[Dict[str, Any]],
    interval: str,
    bars: int,
    note: str,
    proxy: str,
) -> Dict[str, Any]:
    snap = _snapshot(points)
    return {
        "root": root,
        "chart_key": "options.ivRank",
        "mode": "daily",
        "interval": interval,
        "bars": bars,
        "points": points,
        "snapshot": snap,
        "proxy": proxy,
        "note": note,
        "asof": datetime.now().isoformat(timespec="seconds"),
    }


def build_etf_options_iv_rank_history(
    root: str,
    *,
    interval: str = "day",
    bars: int = 60,
    month: str = "all",
    lookback: int = _DEFAULT_LOOKBACK,
) -> Dict[str, Any]:
    from app.services.etf_options_clickhouse import (
        ch_ping,
        etf_options_ch_enabled,
        fetch_option_chain_rows_at_timestamps,
        fetch_underlying_series,
        list_playback_timestamps,
        normalize_playback_bars,
        normalize_playback_interval,
    )
    from app.services.gex_history import (
        _near_month_atm_iv_from_flat,
        _near_month_atm_iv_from_smile,
        _parse_ts,
        _surface_code6,
        _surface_live_fallback_slice,
    )

    code6 = _surface_code6(root)
    interval_n = normalize_playback_interval(interval)
    bars_n = normalize_playback_bars(bars)
    extra = "IV Rank 由近月 ATM 隐含波动率相对回看窗口最高/最低值计算。"
    klines: List[Dict[str, Any]] = []
    note = ""

    def _klines_from_live() -> List[Dict[str, Any]]:
        live = _surface_live_fallback_slice(code6, month)
        atm = _near_month_atm_iv_from_smile(
            list(live.get("iv_smile") or []),
            float(live.get("underlying") or live.get("current_price") or 0.0),
        )
        month_key = None
        ms = live.get("month_series") or []
        if ms:
            month_key = ms[0].get("month")
            if atm is None:
                atm = _near_month_atm_iv_from_smile(
                    list(ms[0].get("iv_smile") or []),
                    float(live.get("underlying") or live.get("current_price") or 0.0),
                )
        if atm is None:
            return []
        return [
            {
                "ts": live.get("ts"),
                "label": live.get("label") or live.get("ts"),
                "date": str(live.get("date") or (live.get("ts") or ""))[:10],
                "month": month_key,
                "close": atm,
                "underlying": live.get("underlying") or live.get("current_price"),
            }
        ]

    if not code6:
        return _payload(
            root=str(root or ""),
            points=[],
            interval=interval_n,
            bars=bars_n,
            note="missing underlying code",
            proxy="atm_iv",
        )

    if etf_options_ch_enabled() and ch_ping():
        timestamps = list_playback_timestamps(code6, interval=interval_n, bars=bars_n)
        if timestamps:
            underlyings = fetch_underlying_series(code6, timestamps)
            by_ts, meta = fetch_option_chain_rows_at_timestamps(code6, timestamps, fields="iv")
            for ts in timestamps:
                asof_dt = _parse_ts(ts) or datetime.now()
                spot = float(underlyings.get(ts) or 0.0)
                flat = by_ts.get(ts) or []
                if spot <= 0:
                    for row in flat:
                        up = float(row.get("underlying_price") or 0.0)
                        if up > 0:
                            spot = up
                            break
                near_month, atm_iv = _near_month_atm_iv_from_flat(
                    flat,
                    underlying=spot,
                    asof=asof_dt,
                    month=month,
                )
                klines.append(
                    {
                        "ts": ts,
                        "label": ts,
                        "date": ts[:10],
                        "month": near_month,
                        "close": atm_iv,
                        "underlying": spot or None,
                    }
                )
            note = (
                f"按 {interval_n} 取最近 {bars_n} 根近月 ATM IV（ClickHouse 轻量切片，不回放完整表面）。"
            )
            if isinstance(meta, dict) and meta.get("error"):
                note += f" meta_error={meta.get('error')}"
        else:
            note = "ClickHouse 无回放时间点，已回退为当前近月 ATM IV。"
    else:
        note = "ClickHouse 不可用，已回退为当前近月 ATM IV。"

    if not any(row.get("close") for row in klines):
        try:
            klines = _klines_from_live()
            if not note:
                note = "已回退为当前近月 ATM IV。"
        except Exception as exc:
            logger.warning("ETF IV Rank live fallback failed root=%s: %s", root, exc)
            if not note:
                note = f"ETF IV Rank unavailable: {exc}"

    points = points_from_iv_values(klines, value_key="close", lookback=lookback, proxy="atm_iv")
    return _payload(
        root=code6 or str(root or ""),
        points=points,
        interval=interval_n,
        bars=bars_n,
        note=f"{note} {extra}".strip(),
        proxy="atm_iv",
    )


def build_futures_options_iv_rank_history(
    root: str,
    *,
    interval: str = "day",
    bars: int = 60,
    lookback: int = _DEFAULT_LOOKBACK,
) -> Dict[str, Any]:
    from app.services.cn_derivatives_futures_options_history import _underlying_daily_bars

    bars_n = max(7, int(bars or 60))
    extra = max(_HV_WINDOW + 5, 30)
    rows = _underlying_daily_bars(str(root or "").upper(), bars=bars_n + extra, interval=interval)
    closes = []
    for row in rows:
        try:
            closes.append(float(row.get("close") or row.get("underlying") or 0.0))
        except (TypeError, ValueError):
            closes.append(0.0)
    hv = realized_vol_series(closes, window=_HV_WINDOW)
    aligned = rows[_HV_WINDOW:]
    hv_rows: List[Dict[str, Any]] = []
    for row, value in zip(aligned, hv):
        item = dict(row)
        item["close"] = value
        hv_rows.append(item)
    hv_rows = hv_rows[-bars_n:]
    points = points_from_iv_values(hv_rows, value_key="close", lookback=lookback, proxy="realized_vol")
    note = (
        "期货期权暂无逐日隐含波动率存档；IV Rank 用连续合约 20 日已实现波动率"
        f"相对最近 {lookback} 个观察的高低值计算（HV Rank 代理）。"
    )
    return _payload(
        root=str(root or "").upper(),
        points=points,
        interval=interval,
        bars=bars_n,
        note=note,
        proxy="realized_vol",
    )


def build_options_iv_rank_history(
    root: str,
    *,
    interval: str = "day",
    bars: int = 60,
    month: str = "all",
    scope: str = "",
) -> Dict[str, Any]:
    if str(scope or "").strip().lower() == "etf":
        return build_etf_options_iv_rank_history(
            root,
            interval=interval,
            bars=bars,
            month=month,
        )
    return build_futures_options_iv_rank_history(
        root,
        interval=interval,
        bars=bars,
    )
