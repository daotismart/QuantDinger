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
    from app.services.gex_history import build_etf_options_surface_history

    bars_n = max(7, int(bars or 60))
    surface = build_etf_options_surface_history(
        root,
        chart_key="options.iv",
        interval=interval,
        bars=bars_n,
        month=month,
    )
    klines = list(surface.get("near_month_iv_klines") or [])
    points = points_from_iv_values(klines, value_key="close", lookback=lookback, proxy="atm_iv")
    note = str(surface.get("note") or "").strip()
    extra = "IV Rank 由近月 ATM 隐含波动率相对回看窗口最高/最低值计算。"
    return _payload(
        root=str(surface.get("root") or root),
        points=points,
        interval=str(surface.get("interval") or interval),
        bars=int(surface.get("bars") or bars_n),
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
