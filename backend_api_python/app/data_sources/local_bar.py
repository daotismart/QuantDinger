"""Local OHLCV reads from ``qd_market_bars`` with upstream fallback support."""

from __future__ import annotations

import os
import time
from typing import Any, Dict, List, Optional, Sequence, Tuple

from app.data_sources.base import TIMEFRAME_SECONDS
from app.services.market_data_maint import repository
from app.utils.logger import get_logger

logger = get_logger(__name__)

_KLINE_FIELDS = ("time", "open", "high", "low", "close", "volume")


def _bool_env(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return str(raw).strip().lower() in ("1", "true", "yes", "on")


def local_read_settings():
    from app.services.local_data.config import LocalDataSettings

    return LocalDataSettings.load()


def is_local_read_enabled() -> bool:
    settings = local_read_settings()
    return bool(settings.local_read_enabled)


def _normalize_scope(exchange_id: Optional[str], market_type: Optional[str]) -> Tuple[str, str]:
    return str(exchange_id or "").strip(), str(market_type or "").strip()


def _strip_bar(row: Dict[str, Any]) -> Dict[str, Any]:
    return {key: row[key] for key in _KLINE_FIELDS if key in row}


def _dedupe_sort(bars: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    by_time: Dict[int, Dict[str, Any]] = {}
    for bar in bars:
        try:
            ts = int(bar["time"])
        except Exception:
            continue
        by_time[ts] = _strip_bar(bar)
    return [by_time[ts] for ts in sorted(by_time)]


def query_local_kline(
    market: str,
    symbol: str,
    timeframe: str,
    limit: int,
    *,
    before_time: Optional[int] = None,
    after_time: Optional[int] = None,
    exchange_id: Optional[str] = None,
    market_type: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Return ascending OHLCV rows from ``qd_market_bars`` (may be partial)."""
    ex, mt = _normalize_scope(exchange_id, market_type)
    rows = repository.query_kline_bars(
        market=str(market or ""),
        symbol=str(symbol or ""),
        timeframe=str(timeframe or "1m"),
        limit=max(1, int(limit or 1)),
        before_time=before_time,
        after_time=after_time,
        exchange_id=ex,
        market_type=mt,
    )
    if rows:
        return [_strip_bar(row) for row in rows]
    if ex or mt:
        fallback = repository.query_kline_bars(
            market=str(market or ""),
            symbol=str(symbol or ""),
            timeframe=str(timeframe or "1m"),
            limit=max(1, int(limit or 1)),
            before_time=before_time,
            after_time=after_time,
            exchange_id="",
            market_type="",
        )
        if fallback:
            return [_strip_bar(row) for row in fallback]
    resolved_ex, resolved_mt = repository.resolve_bar_scope(
        str(market or ""),
        str(symbol or ""),
        str(timeframe or "1m"),
    )
    if (resolved_ex or resolved_mt) and (resolved_ex, resolved_mt) != (ex, mt):
        scoped = repository.query_kline_bars(
            market=str(market or ""),
            symbol=str(symbol or ""),
            timeframe=str(timeframe or "1m"),
            limit=max(1, int(limit or 1)),
            before_time=before_time,
            after_time=after_time,
            exchange_id=resolved_ex,
            market_type=resolved_mt,
        )
        return [_strip_bar(row) for row in scoped]
    return []


def _latest_bar_age_seconds(bars: Sequence[Dict[str, Any]]) -> Optional[float]:
    if not bars:
        return None
    try:
        latest = max(int(bar["time"]) for bar in bars)
    except Exception:
        return None
    return max(0.0, time.time() - float(latest))


def _coverage_ratio(
    bars: Sequence[Dict[str, Any]],
    *,
    limit: int,
    after_time: Optional[int],
    before_time: Optional[int],
    timeframe: str,
) -> float:
    if limit <= 0:
        return 0.0
    if not bars:
        return 0.0
    if after_time is None and before_time is None:
        return min(1.0, len(bars) / float(limit))
    step = max(1, int(TIMEFRAME_SECONDS.get(str(timeframe or "1m").lower(), 60)))
    if after_time is not None and before_time is not None and before_time > after_time:
        expected = max(1, int((before_time - after_time) / step))
        return min(1.0, len(bars) / float(min(limit, expected)))
    return min(1.0, len(bars) / float(limit))


def local_kline_sufficient(
    bars: Sequence[Dict[str, Any]],
    *,
    limit: int,
    after_time: Optional[int],
    before_time: Optional[int],
    timeframe: str,
    settings: Optional[Any] = None,
) -> bool:
    from app.services.local_data.config import LocalDataSettings

    settings = settings or local_read_settings()
    if not bars:
        return False
    coverage = _coverage_ratio(
        bars,
        limit=limit,
        after_time=after_time,
        before_time=before_time,
        timeframe=timeframe,
    )
    if coverage < settings.min_coverage:
        return False
    age = _latest_bar_age_seconds(bars)
    if age is None:
        return False
    tf = str(timeframe or "1m").lower()
    if tf in {"1m", "3m", "5m", "15m", "30m", "1h", "4h"} and age > settings.max_stale_sec:
        return False
    return True


def merge_kline_results(
    local: Sequence[Dict[str, Any]],
    upstream: Sequence[Dict[str, Any]],
    *,
    limit: int,
) -> List[Dict[str, Any]]:
    merged = _dedupe_sort(list(local) + list(upstream))
    if limit > 0 and len(merged) > limit:
        merged = merged[-limit:]
    return merged


def try_local_kline(
    market: str,
    symbol: str,
    timeframe: str,
    limit: int,
    *,
    before_time: Optional[int] = None,
    after_time: Optional[int] = None,
    exchange_id: Optional[str] = None,
    market_type: Optional[str] = None,
) -> Tuple[List[Dict[str, Any]], bool]:
    """Return (bars, sufficient). Empty list + False when local read disabled."""
    settings = local_read_settings()
    if not settings.local_read_enabled:
        return [], False
    local = query_local_kline(
        market,
        symbol,
        timeframe,
        limit,
        before_time=before_time,
        after_time=after_time,
        exchange_id=exchange_id,
        market_type=market_type,
    )
    sufficient = local_kline_sufficient(
        local,
        limit=limit,
        after_time=after_time,
        before_time=before_time,
        timeframe=timeframe,
        settings=settings,
    )
    if local:
        logger.debug(
            "Local bar read %s:%s %s rows=%d sufficient=%s",
            market,
            symbol,
            timeframe,
            len(local),
            sufficient,
        )
    return local, sufficient
