"""Market-data loading for Strategy API V2 backtests.

Prefer ``qd_market_bars`` when coverage is sufficient; fall back to live
upstream klines via ``DataSourceFactory``. Listed ETF/index option contracts
often exist for only a few months — any overlapping local bars are used even
when they do not span the full requested window.
"""

from __future__ import annotations

import math
import os
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Sequence

import pandas as pd

from app.data_sources import DataSourceFactory
from app.services.backtest_cache import KlineCache
from app.utils.logger import get_logger

logger = get_logger(__name__)
_cache = KlineCache()

TIMEFRAME_SECONDS = {
    "1m": 60,
    "3m": 180,
    "5m": 300,
    "15m": 900,
    "30m": 1800,
    "1h": 3600,
    "4h": 14400,
    "1d": 86400,
    "1w": 604800,
}

PROVIDER_TIMEFRAMES = {
    "1h": "1H",
    "4h": "4H",
    "1d": "1D",
    "1w": "1W",
}

_CN_MARKETS = {
    "CNFutures",
    "CNFuturesOptions",
    "CNIndexFutures",
    "CNIndexOptions",
}

_OPTION_MARKETS = {"CNFuturesOptions", "CNIndexOptions"}


def _normalize_utc_datetime(value: datetime) -> datetime:
    """Return an aware UTC datetime, interpreting naive inputs as UTC."""
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _prefer_db_bars() -> bool:
    return str(os.getenv("STRATEGY_V2_PREFER_DB_BARS", "1")).strip().lower() not in {
        "0",
        "false",
        "no",
        "off",
    }


def _db_min_coverage() -> float:
    try:
        return max(0.05, min(1.0, float(os.getenv("STRATEGY_V2_DB_BARS_MIN_COVERAGE", "0.6"))))
    except Exception:
        return 0.6


def _uniq(values: Sequence[Any]) -> List[str]:
    out: List[str] = []
    seen: set[str] = set()
    for raw in values:
        text = str(raw or "").strip()
        key = text.lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(text)
    return out


def _db_symbol_candidates(market: str, symbol: str) -> List[str]:
    """Symbols that may appear in ``qd_market_bars`` for this request."""
    raw = str(symbol or "").strip()
    candidates: List[str] = [raw]
    if str(market) == "CNStock" or raw.endswith((".SH", ".SZ", ".BJ")):
        if "." in raw:
            candidates.append(raw.split(".", 1)[0])
        else:
            try:
                from app.markets.cn_options import cn_etf_stock_symbol

                candidates.append(cn_etf_stock_symbol(raw))
            except Exception:
                candidates.extend([f"{raw}.SH", f"{raw}.SZ"])
    if str(market) not in _CN_MARKETS:
        return _uniq(candidates)
    try:
        from app.data_sources.cn_futures import resolve_history_symbol
        from app.markets.cn_futures import parse_cn_option_symbol
        from app.markets.cn_options import option_underlying_continuous, parse_cn_option_instrument

        feed, mode = resolve_history_symbol(symbol)
        candidates.append(feed)
        if mode == "option":
            parsed = parse_cn_option_instrument(symbol)
            if parsed is not None and parsed.root:
                candidates.append(option_underlying_continuous(str(parsed.root)))
            else:
                opt = parse_cn_option_symbol(symbol)
                if opt and opt.get("root"):
                    candidates.append(option_underlying_continuous(str(opt["root"])))
    except Exception as exc:
        logger.debug("db symbol resolve failed market=%s symbol=%s: %s", market, symbol, exc)
    return _uniq(candidates)


def _db_market_candidates(market: str) -> List[str]:
    text = str(market or "").strip()
    if text == "CNFuturesOptions":
        return _uniq([text, "CNFutures", "CNIndexFutures"])
    if text == "CNIndexOptions":
        return _uniq([text, "CNIndexFutures", "CNFutures"])
    return _uniq([text])


def _db_market_type_candidates(market_type: Optional[str], market: str) -> List[str]:
    passed = str(market_type or "").strip()
    extras = ["futures", "options", "spot", ""]
    if str(market) in _OPTION_MARKETS:
        extras = ["futures", "options", ""]
    elif str(market) in {"CNFutures", "CNIndexFutures"}:
        extras = ["futures", ""]
    elif str(market) == "CNStock":
        extras = ["spot", ""]
    return _uniq([passed, *extras])


def _db_exchange_candidates(exchange_id: Optional[str]) -> List[str]:
    return _uniq([str(exchange_id or "").strip(), ""])


def _db_timeframe_candidates(provider_timeframe: str, normalized: str) -> List[str]:
    return _uniq([provider_timeframe, normalized, str(provider_timeframe).upper(), str(normalized).lower()])


def _load_db_bar_rows(
    *,
    market: str,
    symbol: str,
    provider_timeframe: str,
    normalized_timeframe: str,
    market_type: Optional[str],
    exchange_id: Optional[str],
    after_time: int,
    before_time: int,
    limit: int,
) -> List[Dict[str, Any]]:
    from app.services.market_data_maint import repository as market_repo
    from app.services.market_data_maint.config import WatchSpec

    fetch_limit = min(max(int(limit or 500), 5000), 250000)
    best: List[Dict[str, Any]] = []
    for mkt in _db_market_candidates(market):
        for sym in _db_symbol_candidates(market, symbol):
            for tf in _db_timeframe_candidates(provider_timeframe, normalized_timeframe):
                for ex_id in _db_exchange_candidates(exchange_id):
                    for mt in _db_market_type_candidates(market_type, market):
                        spec = WatchSpec(
                            market=mkt,
                            symbol=sym,
                            timeframe=tf,
                            exchange_id=ex_id,
                            market_type=mt,
                        )
                        try:
                            rows = market_repo.load_bars(
                                spec,
                                start_ts=after_time,
                                end_ts=before_time,
                                limit=fetch_limit,
                            )
                        except Exception as exc:
                            logger.debug(
                                "qd_market_bars load failed %s:%s %s @%s/%s: %s",
                                mkt,
                                sym,
                                tf,
                                ex_id or "-",
                                mt or "-",
                                exc,
                            )
                            continue
                        if len(rows) > len(best):
                            best = rows
                        if len(best) >= max(50, int(fetch_limit * 0.2)):
                            return best
    return best


def _rows_to_frame(rows: Sequence[Dict[str, Any]]) -> pd.DataFrame:
    if not rows:
        return pd.DataFrame()
    frame = pd.DataFrame(list(rows))
    time_column = next((name for name in ("time", "timestamp", "datetime", "date") if name in frame.columns), "")
    if not time_column:
        return pd.DataFrame()
    raw_time = frame.pop(time_column)
    numeric = pd.to_numeric(raw_time, errors="coerce")
    if numeric.notna().any():
        unit = "ms" if float(numeric.dropna().abs().median()) > 10_000_000_000 else "s"
        converted = pd.to_datetime(numeric, unit=unit, errors="coerce", utc=True)
        frame.index = pd.DatetimeIndex(converted).tz_convert(None)
    else:
        converted = pd.to_datetime(raw_time, errors="coerce", utc=True)
        frame.index = pd.DatetimeIndex(converted).tz_convert(None)
    frame = frame[~frame.index.isna()].sort_index()
    frame.columns = [str(column).strip().lower() for column in frame.columns]
    if any(column not in frame.columns for column in ("open", "high", "low", "close")):
        return pd.DataFrame()
    for column in ("open", "high", "low", "close", "volume"):
        if column not in frame.columns:
            frame[column] = 0.0
        frame[column] = pd.to_numeric(frame[column], errors="coerce")
    return frame.dropna(subset=["open", "high", "low", "close"])


def _trim_frame(
    frame: pd.DataFrame,
    *,
    start_utc: datetime,
    end_utc: datetime,
    timeframe_seconds: int,
) -> pd.DataFrame:
    if frame is None or frame.empty:
        return pd.DataFrame()
    requested_start = pd.Timestamp(start_utc).tz_localize(None)
    requested_end = pd.Timestamp(end_utc).tz_localize(None)
    out = frame[(frame.index >= requested_start) & (frame.index <= requested_end)].dropna(
        subset=["open", "high", "low", "close"]
    )
    closed_bar_cutoff = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(seconds=timeframe_seconds)
    if requested_end >= closed_bar_cutoff:
        out = out[out.index <= pd.Timestamp(closed_bar_cutoff)]
    return out


def _coverage_ok(
    frame: pd.DataFrame,
    *,
    start_utc: datetime,
    end_utc: datetime,
    limit: int,
    market: str = "",
) -> bool:
    if frame is None or frame.empty:
        return False
    # Listed option contracts typically live a few months. Any overlapping
    # local bars are more useful than an empty/synthetic upstream series.
    if str(market) in _OPTION_MARKETS:
        return len(frame) >= 5
    min_rows = max(20, int(max(1, int(limit or 500)) * _db_min_coverage()))
    if len(frame) < min_rows:
        return False
    span = max(1.0, (end_utc - start_utc).total_seconds())
    first = float(pd.Timestamp(frame.index[0]).timestamp())
    last = float(pd.Timestamp(frame.index[-1]).timestamp())
    covered = max(0.0, last - first)
    if covered < span * 0.5:
        return False
    start_ts = float(start_utc.timestamp())
    end_ts = float(end_utc.timestamp())
    if first > start_ts + span * 0.25:
        return False
    if last < end_ts - span * 0.25:
        return False
    return True


def _load_upstream_rows(
    *,
    market: str,
    symbol: str,
    provider_timeframe: str,
    limit: int,
    after_time: int,
    before_time: int,
    exchange_id: Optional[str],
    market_type: Optional[str],
) -> List[Dict[str, Any]]:
    try:
        rows = DataSourceFactory.get_kline(
            market=market,
            symbol=symbol,
            timeframe=provider_timeframe,
            limit=limit,
            before_time=before_time,
            after_time=after_time,
            exchange_id=exchange_id,
            market_type=market_type,
        )
    except Exception as exc:
        logger.warning(
            "Strategy market-data fetch failed for %s:%s %s via %s/%s: %s",
            market,
            symbol,
            provider_timeframe,
            exchange_id or "default",
            market_type or "default",
            exc,
        )
        return []
    return list(rows or [])


def load_strategy_frame(
    market: str,
    symbol: str,
    timeframe: str,
    start_date: datetime,
    end_date: datetime,
    *,
    market_type: Optional[str] = None,
    exchange_id: Optional[str] = None,
) -> pd.DataFrame:
    start_utc = _normalize_utc_datetime(start_date)
    end_utc = _normalize_utc_datetime(end_date)
    total_seconds = max(1.0, (end_utc - start_utc).total_seconds())
    normalized_timeframe = str(timeframe or "1d").strip().lower()
    timeframe_seconds = TIMEFRAME_SECONDS.get(normalized_timeframe, 86400)
    provider_timeframe = PROVIDER_TIMEFRAMES.get(normalized_timeframe, normalized_timeframe)
    limit = int(math.ceil(total_seconds / timeframe_seconds * 1.15) + 200)
    after_time = int((start_utc - timedelta(seconds=timeframe_seconds)).timestamp())
    before_time = int((end_utc + timedelta(seconds=timeframe_seconds)).timestamp())
    cache_key = ":".join(
        (
            str(market),
            str(symbol),
            str(timeframe),
            str(market_type or ""),
            str(exchange_id or ""),
            start_utc.isoformat(),
            end_utc.isoformat(),
            "db1" if _prefer_db_bars() else "up",
        )
    )
    cached = _cache.get(cache_key)
    if cached is not None and not cached.empty:
        return cached.copy()

    db_frame = pd.DataFrame()
    if _prefer_db_bars():
        try:
            db_rows = _load_db_bar_rows(
                market=market,
                symbol=symbol,
                provider_timeframe=provider_timeframe,
                normalized_timeframe=normalized_timeframe,
                market_type=market_type,
                exchange_id=exchange_id,
                after_time=after_time,
                before_time=before_time,
                limit=limit,
            )
            db_frame = _trim_frame(
                _rows_to_frame(db_rows),
                start_utc=start_utc,
                end_utc=end_utc,
                timeframe_seconds=timeframe_seconds,
            )
            if _coverage_ok(db_frame, start_utc=start_utc, end_utc=end_utc, limit=limit, market=market):
                db_frame.attrs["bar_source"] = "qd_market_bars"
                logger.info(
                    "strategy_v2 bars from qd_market_bars market=%s symbol=%s tf=%s rows=%s",
                    market,
                    symbol,
                    provider_timeframe,
                    len(db_frame),
                )
                _cache.put(cache_key, db_frame, timeframe)
                return db_frame.copy()
            logger.info(
                "strategy_v2 qd_market_bars insufficient market=%s symbol=%s tf=%s rows=%s; fallback upstream",
                market,
                symbol,
                provider_timeframe,
                0 if db_frame is None or db_frame.empty else len(db_frame),
            )
        except Exception as exc:
            logger.warning(
                "strategy_v2 qd_market_bars failed market=%s symbol=%s tf=%s: %s; fallback upstream",
                market,
                symbol,
                provider_timeframe,
                exc,
            )

    rows = _load_upstream_rows(
        market=market,
        symbol=symbol,
        provider_timeframe=provider_timeframe,
        limit=limit,
        after_time=after_time,
        before_time=before_time,
        exchange_id=exchange_id,
        market_type=market_type,
    )
    frame = _trim_frame(
        _rows_to_frame(rows),
        start_utc=start_utc,
        end_utc=end_utc,
        timeframe_seconds=timeframe_seconds,
    )
    if frame.empty and not db_frame.empty:
        db_frame.attrs["bar_source"] = "qd_market_bars_partial"
        _cache.put(cache_key, db_frame, timeframe)
        return db_frame.copy()
    if frame.empty:
        return pd.DataFrame()
    frame.attrs["bar_source"] = "upstream"
    _cache.put(cache_key, frame, timeframe)
    return frame.copy()
