"""Continuity and accuracy checks for OHLCV bars and ticks."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from app.data_sources.base import TIMEFRAME_SECONDS


@dataclass
class GapRange:
    start_ts: int
    end_ts: int
    missing_bars: int
    kind: str = "data_gap"  # data_gap | session_gap


@dataclass
class ValidationIssue:
    code: str
    message: str
    bar_time: Optional[int] = None


@dataclass
class ValidationResult:
    clean_bars: List[Dict[str, Any]] = field(default_factory=list)
    rejected_bars: List[Dict[str, Any]] = field(default_factory=list)
    issues: List[ValidationIssue] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.rejected_bars and not self.issues


def timeframe_seconds(timeframe: str) -> int:
    return int(TIMEFRAME_SECONDS.get(str(timeframe or "").strip(), 60))


def validate_bar(bar: Dict[str, Any]) -> List[ValidationIssue]:
    issues: List[ValidationIssue] = []
    try:
        ts = int(bar.get("time") or 0)
        o = float(bar.get("open") or 0)
        h = float(bar.get("high") or 0)
        l = float(bar.get("low") or 0)
        c = float(bar.get("close") or 0)
        v = float(bar.get("volume") or 0)
    except (TypeError, ValueError):
        return [ValidationIssue("parse_error", "bar fields are not numeric", None)]
    if ts <= 0:
        issues.append(ValidationIssue("bad_time", "bar time must be positive", ts))
    if min(o, h, l, c) <= 0:
        issues.append(ValidationIssue("non_positive_price", "OHLC must be > 0", ts))
    if v < 0:
        issues.append(ValidationIssue("negative_volume", "volume must be >= 0", ts))
    if h + 1e-12 < max(o, c, l):
        issues.append(ValidationIssue("high_inconsistent", "high < max(open,close,low)", ts))
    if l - 1e-12 > min(o, c, h):
        issues.append(ValidationIssue("low_inconsistent", "low > min(open,close,high)", ts))
    return issues


def sanitize_bars(bars: Iterable[Dict[str, Any]]) -> ValidationResult:
    result = ValidationResult()
    seen = set()
    for raw in bars:
        bar = {
            "time": int(raw.get("time") or 0),
            "open": float(raw.get("open") or 0),
            "high": float(raw.get("high") or 0),
            "low": float(raw.get("low") or 0),
            "close": float(raw.get("close") or 0),
            "volume": float(raw.get("volume") or 0),
        }
        problems = validate_bar(bar)
        if problems:
            result.rejected_bars.append(bar)
            result.issues.extend(problems)
            continue
        if bar["time"] in seen:
            result.issues.append(ValidationIssue("duplicate_time", "duplicate bar time", bar["time"]))
            result.rejected_bars.append(bar)
            continue
        seen.add(bar["time"])
        result.clean_bars.append(bar)
    result.clean_bars.sort(key=lambda item: item["time"])
    return result


def detect_gaps(
    bars: Sequence[Dict[str, Any]],
    *,
    timeframe: str,
    session_gap_seconds: int = 15 * 3600,
) -> List[GapRange]:
    """Detect missing bars between consecutive timestamps."""
    step = timeframe_seconds(timeframe)
    if step <= 0 or len(bars) < 2:
        return []
    ordered = sorted(bars, key=lambda item: int(item.get("time") or 0))
    gaps: List[GapRange] = []
    for left, right in zip(ordered, ordered[1:]):
        start = int(left.get("time") or 0)
        end = int(right.get("time") or 0)
        delta = end - start
        if delta <= step:
            continue
        missing = max(0, int(delta // step) - 1)
        if missing <= 0:
            continue
        kind = "session_gap" if delta >= int(session_gap_seconds) else "data_gap"
        gaps.append(
            GapRange(
                start_ts=start + step,
                end_ts=end - step,
                missing_bars=missing,
                kind=kind,
            )
        )
    return gaps


def merge_bars(*series: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    by_time: Dict[int, Dict[str, Any]] = {}
    for rows in series:
        for raw in rows:
            try:
                ts = int(raw.get("time") or 0)
            except (TypeError, ValueError):
                continue
            if ts <= 0:
                continue
            by_time[ts] = {
                "time": ts,
                "open": float(raw.get("open") or 0),
                "high": float(raw.get("high") or 0),
                "low": float(raw.get("low") or 0),
                "close": float(raw.get("close") or 0),
                "volume": float(raw.get("volume") or 0),
            }
    return [by_time[key] for key in sorted(by_time)]


def tick_anomaly(
    previous: Optional[Dict[str, Any]],
    current: Dict[str, Any],
    *,
    spike_ratio: float = 1.15,
) -> Optional[ValidationIssue]:
    try:
        price = float(current.get("last_price") or current.get("price") or 0)
        volume = int(current.get("volume") or 0)
    except (TypeError, ValueError):
        return ValidationIssue("tick_parse_error", "tick fields invalid")
    if price <= 0:
        return ValidationIssue("tick_non_positive", "tick price must be > 0")
    if previous is None:
        return None
    try:
        prev_price = float(previous.get("last_price") or previous.get("price") or 0)
        prev_volume = int(previous.get("volume") or 0)
    except (TypeError, ValueError):
        return None
    if prev_price > 0 and (price / prev_price > spike_ratio or prev_price / price > spike_ratio):
        return ValidationIssue("tick_price_spike", f"price jumped beyond ratio {spike_ratio}")
    if volume + 0 < prev_volume and volume >= 0:
        # CTP cumulative volume resets on trading day; treat large drops as session reset.
        if prev_volume - volume > max(10, int(prev_volume * 0.5)):
            return ValidationIssue("tick_volume_reset", "cumulative volume reset detected", None)
    return None


def align_bar_time(unix_seconds: int, timeframe: str) -> int:
    step = timeframe_seconds(timeframe)
    if step <= 0:
        return int(unix_seconds)
    return int(unix_seconds) - (int(unix_seconds) % step)
