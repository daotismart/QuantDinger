"""Bulk ingest of SSE/SZSE ETF options and underlying ETF history."""

from __future__ import annotations

import os
import time
from datetime import datetime, timezone
from typing import Any, Callable, Dict, Iterable, List, Optional, Sequence

from app.data_sources.base import TIMEFRAME_SECONDS
from app.data_sources.cn_futures import CnFuturesDataSource
from app.data_sources.cn_stock import CNStockDataSource
from app.markets.cn_options import cn_etf_stock_symbol, infer_cn_etf_board
from app.services.cn_options_chain import listed_etf_index_catalog, listed_option_catalog
from app.services.market_data_maint import repository
from app.services.market_data_maint.config import WatchSpec
from app.services.market_data_maint.validators import sanitize_bars
from app.utils.logger import get_logger

logger = get_logger(__name__)

DEFAULT_TIMEFRAMES = ("1D",)
DAILY_LOOKBACK_BARS = 10000
# Tencent fqkline returns empty above ~640 bars for many symbols; large limits
# fall through to rate-limited yfinance and ingest fails on production hosts.
CN_STOCK_DAILY_FETCH_LIMIT = 2000
MINUTE_LOOKBACK_BARS = 20000
DAILY_TFS = {"1D", "1W"}
DERIVE_FROM_1M = ("3m", "5m", "15m", "30m", "1H", "4H")


def _bool_env(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return str(raw).strip().lower() in ("1", "true", "yes", "on")


def _normalize_timeframes(raw: Iterable[str]) -> List[str]:
    out: List[str] = []
    seen = set()
    aliases = {
        "d": "1D",
        "day": "1D",
        "daily": "1D",
        "w": "1W",
        "week": "1W",
        "weekly": "1W",
        "1min": "1m",
        "min": "1m",
        "minute": "1m",
        "5min": "5m",
        "15min": "15m",
        "30min": "30m",
        "1h": "1H",
        "4h": "4H",
    }
    for item in raw:
        tf = aliases.get(str(item or "").strip().lower(), str(item or "").strip())
        if not tf or tf in seen:
            continue
        seen.add(tf)
        out.append(tf)
    return out or list(DEFAULT_TIMEFRAMES)


def select_etf_option_targets(
    *,
    symbols: Optional[Sequence[str]] = None,
    exchanges: Optional[Sequence[str]] = None,
    catalog: Optional[List[Dict[str, Any]]] = None,
) -> List[Dict[str, Any]]:
    wanted = {str(s).strip() for s in (symbols or []) if str(s).strip()}
    wanted_ex = {str(e).strip().upper() for e in (exchanges or []) if str(e).strip()}
    rows = catalog if catalog is not None else listed_option_catalog()
    targets: List[Dict[str, Any]] = []
    for item in rows:
        if item.get("kind") != "etf":
            continue
        symbol = str(item.get("symbol") or "").strip()
        if not symbol:
            continue
        exchange = str(item.get("exchange") or "").upper()
        if wanted_ex and exchange not in wanted_ex:
            continue
        if wanted and symbol not in wanted:
            continue
        targets.append(
            {
                "market": "CNIndexOptions",
                "symbol": symbol,
                "name": str(item.get("name") or symbol),
                "exchange": exchange,
                "market_type": "options",
                "underlying": str(item.get("underlying") or "").strip(),
                "kind": "etf",
            }
        )
    return targets


def select_etf_underlying_targets(
    targets: Sequence[Dict[str, Any]],
    *,
    symbols: Optional[Sequence[str]] = None,
) -> List[Dict[str, Any]]:
    wanted = {str(s).strip() for s in (symbols or []) if str(s).strip()}
    out: List[Dict[str, Any]] = []
    seen = set()
    for item in targets:
        code = str(item.get("underlying") or "").strip()
        if not code:
            continue
        stock_symbol = cn_etf_stock_symbol(code)
        if stock_symbol in seen:
            continue
        plain = code
        dotted = stock_symbol.split(".", 1)[0]
        if wanted and plain not in wanted and dotted not in wanted and stock_symbol not in wanted:
            continue
        seen.add(stock_symbol)
        out.append(
            {
                "market": "CNStock",
                "symbol": stock_symbol,
                "name": str(item.get("name") or f"ETF {code}"),
                "exchange": infer_cn_etf_board(code),
                "market_type": "spot",
                "kind": "etf_underlying",
            }
        )
    return out


def select_etf_index_targets(
    option_targets: Sequence[Dict[str, Any]],
    *,
    symbols: Optional[Sequence[str]] = None,
    catalog: Optional[List[Dict[str, Any]]] = None,
) -> List[Dict[str, Any]]:
    wanted = {str(s).strip().upper() for s in (symbols or []) if str(s).strip()}
    rows = catalog if catalog is not None else listed_etf_index_catalog()
    etf_codes = {
        str(item.get("underlying") or "").strip()
        for item in option_targets
        if str(item.get("underlying") or "").strip()
    }
    out: List[Dict[str, Any]] = []
    seen = set()
    for item in rows:
        symbol = str(item.get("symbol") or "").strip().upper()
        if not symbol or symbol in seen:
            continue
        underlying_etf = str(item.get("underlying_etf") or "").strip()
        if etf_codes and underlying_etf and underlying_etf not in etf_codes:
            continue
        plain = symbol.split(".", 1)[0]
        if wanted and symbol not in wanted and plain not in wanted and underlying_etf not in wanted:
            continue
        seen.add(symbol)
        out.append(
            {
                "market": "CNStock",
                "symbol": symbol,
                "name": str(item.get("name") or symbol),
                "exchange": str(item.get("exchange") or "CN"),
                "market_type": "index",
                "kind": "etf_index",
                "underlying_etf": underlying_etf,
            }
        )
    return out


def _watch_spec(target: Dict[str, Any], timeframe: str) -> WatchSpec:
    lookback = DAILY_LOOKBACK_BARS if timeframe.upper() in DAILY_TFS else MINUTE_LOOKBACK_BARS
    return WatchSpec(
        market=str(target["market"]),
        symbol=str(target["symbol"]),
        timeframe=timeframe,
        exchange_id="",
        market_type=str(target.get("market_type") or "options"),
        lookback_bars=lookback,
    )


def _fetch_with_retry(
    fetcher: Callable[[], List[Dict[str, Any]]],
    *,
    label: str,
    retries: int,
    sleeper: Callable[[float], None],
) -> List[Dict[str, Any]]:
    last_exc: Optional[BaseException] = None
    attempts = max(1, int(retries))
    for attempt in range(1, attempts + 1):
        try:
            rows = fetcher()
            if rows:
                return list(rows)
            last_exc = ValueError(f"empty history for {label}")
        except Exception as exc:  # noqa: BLE001
            last_exc = exc
            logger.warning(
                "ETF options history fetch failed %s attempt=%s/%s: %s",
                label,
                attempt,
                attempts,
                exc,
            )
        if attempt < attempts:
            sleeper(min(30.0, 2.0 ** attempt))
    if last_exc:
        raise last_exc
    return []


def ingest_cn_etf_options_history(
    *,
    timeframes: Sequence[str] = DEFAULT_TIMEFRAMES,
    persist: bool = False,
    provider: str = "akshare",
    retries: int = 3,
    symbols: Optional[Sequence[str]] = None,
    exchanges: Optional[Sequence[str]] = None,
    include_underlyings: bool = True,
    include_indices: bool = True,
    register_watch: bool = True,
    watch_intraday: bool = False,
    src: Optional[CnFuturesDataSource] = None,
    stock_src: Optional[CNStockDataSource] = None,
    sleeper: Callable[[float], None] = time.sleep,
    on_progress: Optional[Callable[[Dict[str, Any]], None]] = None,
) -> Dict[str, Any]:
    """Fetch listed ETF option + underlying ETF history and optionally persist."""
    tfs = _normalize_timeframes(timeframes)
    os.environ["CN_FUTURES_MARKET_DATA_PROVIDER"] = (provider or "akshare").strip() or "akshare"
    option_source = src or CnFuturesDataSource()
    stock_source = stock_src or CNStockDataSource()
    catalog = listed_option_catalog()
    option_targets = select_etf_option_targets(
        symbols=symbols,
        exchanges=exchanges,
        catalog=catalog,
    )
    underlying_targets = (
        select_etf_underlying_targets(option_targets, symbols=symbols) if include_underlyings else []
    )
    index_targets = (
        select_etf_index_targets(option_targets, symbols=symbols, catalog=listed_etf_index_catalog(catalog))
        if include_indices
        else []
    )
    all_targets = list(option_targets) + list(underlying_targets) + list(index_targets)
    started = time.time()
    results: List[Dict[str, Any]] = []
    errors: List[Dict[str, Any]] = []
    upserted_total = 0
    watch_specs: List[WatchSpec] = []
    symbol_pause = float(os.getenv("CN_ETF_OPTIONS_INGEST_SYMBOL_PAUSE_SEC", "0.35") or 0.35)

    want_weekly = "1W" in tfs
    want_1m = "1m" in tfs
    derived_tfs = [tf for tf in tfs if want_1m and tf in DERIVE_FROM_1M]
    fetch_tfs = [tf for tf in tfs if tf != "1W" and tf not in derived_tfs]
    if want_weekly and "1D" not in fetch_tfs:
        fetch_tfs.append("1D")

    def _should_watch(timeframe: str) -> bool:
        if not register_watch:
            return False
        if timeframe.upper() in DAILY_TFS:
            return True
        return bool(watch_intraday)

    def _persist_bars(target: Dict[str, Any], timeframe: str, bars: List[Dict[str, Any]], flags: List[str]) -> int:
        nonlocal upserted_total
        if not persist or not bars:
            return 0
        spec = _watch_spec(target, timeframe)
        written = repository.upsert_bars(
            spec,
            bars,
            source="cn_etf_options_history",
            quality_flags=flags,
        )
        upserted_total += written
        if _should_watch(timeframe):
            watch_specs.append(spec)
        return written

    for index, target in enumerate(all_targets, start=1):
        market = str(target["market"])
        symbol = str(target["symbol"])
        item: Dict[str, Any] = {
            "market": market,
            "symbol": symbol,
            "name": target.get("name"),
            "exchange": target.get("exchange"),
            "kind": target.get("kind"),
            "timeframes": {},
        }
        logger.info(
            "ETF options ingest %s/%s market=%s symbol=%s tfs=%s",
            index,
            len(all_targets),
            market,
            symbol,
            fetch_tfs,
        )
        daily_rows: List[Dict[str, Any]] = []
        minute_rows: List[Dict[str, Any]] = []

        for tf in fetch_tfs:
            try:
                if market == "CNStock":
                    lim = min(DAILY_LOOKBACK_BARS, CN_STOCK_DAILY_FETCH_LIMIT) if tf.upper() in DAILY_TFS else MINUTE_LOOKBACK_BARS
                    rows = _fetch_with_retry(
                        lambda: stock_source.get_kline(symbol, tf, limit=lim),
                        label=f"{market}:{symbol}:{tf}",
                        retries=retries,
                        sleeper=sleeper,
                    )
                else:
                    rows = _fetch_with_retry(
                        lambda: option_source.get_history(symbol, tf),
                        label=f"{market}:{symbol}:{tf}",
                        retries=retries,
                        sleeper=sleeper,
                    )
            except Exception as exc:  # noqa: BLE001
                errors.append({"symbol": symbol, "market": market, "timeframe": tf, "error": str(exc)})
                if tf in tfs:
                    item["timeframes"][tf] = {"ok": False, "error": str(exc)}
                continue
            validated = sanitize_bars(rows)
            payload = {
                "ok": True,
                "bars": len(validated.clean_bars),
                "rejected": len(validated.rejected_bars),
                "start_time": validated.clean_bars[0]["time"] if validated.clean_bars else None,
                "end_time": validated.clean_bars[-1]["time"] if validated.clean_bars else None,
            }
            if tf == "1D":
                daily_rows = validated.clean_bars
            if tf == "1m":
                minute_rows = validated.clean_bars
            if tf in tfs:
                payload["upserted"] = _persist_bars(
                    target,
                    tf,
                    validated.clean_bars,
                    ["validated", "akshare"],
                )
                item["timeframes"][tf] = payload

        if want_1m and minute_rows and market != "CNStock":
            for tf in derived_tfs:
                seconds = TIMEFRAME_SECONDS.get(tf)
                if not seconds:
                    continue
                resampled = option_source._resample(minute_rows, seconds)
                validated = sanitize_bars(resampled)
                payload = {
                    "ok": True,
                    "bars": len(validated.clean_bars),
                    "derived_from": "1m",
                }
                payload["upserted"] = _persist_bars(
                    target,
                    tf,
                    validated.clean_bars,
                    ["validated", "akshare", "resampled"],
                )
                item["timeframes"][tf] = payload

        if want_weekly and daily_rows:
            weekly = option_source._resample(daily_rows, TIMEFRAME_SECONDS["1W"])
            validated = sanitize_bars(weekly)
            payload = {
                "ok": True,
                "bars": len(validated.clean_bars),
                "derived_from": "1D",
            }
            payload["upserted"] = _persist_bars(
                target,
                "1W",
                validated.clean_bars,
                ["validated", "akshare", "resampled"],
            )
            item["timeframes"]["1W"] = payload

        results.append(item)
        if on_progress:
            on_progress({"index": index, "total": len(all_targets), "symbol": symbol, "item": item})
        if index < len(all_targets) and symbol_pause > 0:
            sleeper(symbol_pause)

    watch_written = 0
    if persist and watch_specs:
        try:
            watch_written = repository.upsert_watch_specs(watch_specs)
        except Exception as exc:  # noqa: BLE001
            logger.warning("register ETF options watchlist failed: %s", exc)
            errors.append({"symbol": "*", "timeframe": "*", "error": f"watchlist: {exc}"})

    ok_symbols = sum(
        1
        for row in results
        if tfs and all((row["timeframes"].get(tf) or {}).get("ok") for tf in tfs)
    )
    status = "success"
    if errors and ok_symbols:
        status = "partial"
    elif errors and not ok_symbols:
        status = "failed"
    elif not results:
        status = "failed"

    summary = {
        "status": status,
        "provider": os.environ.get("CN_FUTURES_MARKET_DATA_PROVIDER", provider),
        "persist": bool(persist),
        "timeframes": tfs,
        "option_targets": len(option_targets),
        "underlying_targets": len(underlying_targets),
        "index_targets": len(index_targets),
        "targets": len(all_targets),
        "ok_symbols": ok_symbols,
        "failed_symbols": len({e["symbol"] for e in errors if e.get("symbol") and e["symbol"] != "*"}),
        "upserted_rows": upserted_total,
        "watch_written": watch_written,
        "elapsed_sec": round(time.time() - started, 2),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "errors": errors,
        "results": results,
    }
    logger.info(
        "ETF options history ingest status=%s options=%s underlyings=%s indices=%s ok=%s upserted=%s",
        status,
        len(option_targets),
        len(underlying_targets),
        len(index_targets),
        ok_symbols,
        upserted_total,
    )
    return summary
