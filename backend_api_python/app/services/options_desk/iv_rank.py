"""IV Rank / IV Percentile proxies from realized volatility of the underlying."""

from __future__ import annotations

import math
from typing import Sequence


def realized_vol_series(closes: Sequence[float], *, window: int = 20) -> list[float]:
    values = [float(item) for item in closes if item is not None and float(item) > 0]
    if len(values) < window + 1:
        return []
    logs: list[float] = []
    for index in range(1, len(values)):
        prev = values[index - 1]
        current = values[index]
        if prev <= 0 or current <= 0:
            logs.append(0.0)
        else:
            logs.append(math.log(current / prev))
    out: list[float] = []
    for end in range(window, len(logs) + 1):
        chunk = logs[end - window : end]
        mean = sum(chunk) / window
        var = sum((item - mean) ** 2 for item in chunk) / max(window - 1, 1)
        out.append(math.sqrt(max(var, 0.0)) * math.sqrt(252.0))
    return out


def realized_vol_from_closes(closes: Sequence[float], *, window: int = 20) -> float | None:
    series = realized_vol_series(closes, window=window)
    if not series:
        return None
    return float(series[-1])


def _percentile(series: Sequence[float], current: float) -> float:
    if not series:
        return float("nan")
    below = sum(1 for item in series if item < current)
    return 100.0 * below / len(series)


def iv_rank_from_closes(
    closes: Sequence[float],
    *,
    window: int = 20,
    lookback: int = 120,
) -> dict[str, float | str | int | None]:
    series = realized_vol_series(closes, window=window)
    if not series:
        return {
            "proxy": "realized_vol",
            "window": window,
            "lookback": lookback,
            "current_rv": None,
            "iv_rank": None,
            "iv_percentile": None,
        }
    windowed = series[-max(1, int(lookback)) :]
    current = float(windowed[-1])
    lo = min(windowed)
    hi = max(windowed)
    if hi <= lo:
        rank = 50.0
    else:
        rank = 100.0 * (current - lo) / (hi - lo)
    percentile = _percentile(windowed, current)
    return {
        "proxy": "realized_vol",
        "window": int(window),
        "lookback": int(lookback),
        "observations": len(windowed),
        "current_rv": current,
        "rv_low": float(lo),
        "rv_high": float(hi),
        "iv_rank": float(rank),
        "iv_percentile": float(percentile),
        "note": "IV Rank/Percentile proxied by 20-day realized vol of the underlying close series.",
    }
