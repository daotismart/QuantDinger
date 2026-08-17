"""Bulk ingest of mainland China futures history into qd_market_bars.

Pulls the public Sina/akshare main-continuous series (``RB0`` / ``IF0`` / …)
for every catalogued futures root and upserts validated OHLCV bars.

Minute history is opt-in: Sina returns ~1023 bars per contract and stitching
nearby months is expensive across the full catalog.
"""

from __future__ import annotations

import os
import time
from datetime import datetime, timezone
from typing import Any, Callable, Dict, Iterable, List, Optional, Sequence

from app.data_sources.base import TIMEFRAME_SECONDS
from app.data_sources.cn_futures import CnFuturesDataSource, resolve_history_symbol
from app.services.market_data_maint import repository
from app.services.market_data_maint.config import WatchSpec
from app.services.market_data_maint.validators import sanitize_bars
from app.utils.logger import get_logger

try:
    from app.markets.cn_futures import list_continuous_history_targets
except ImportError:  # pragma: no cover - older production images
    from app.markets.cn_futures import list_products

    def list_continuous_history_targets(  # type: ignore[misc]
        *,
        exchange: Optional[str] = None,
        include_options_only: bool = False,
    ) -> List[Dict[str, Any]]:
        option_only = {"IO", "HO", "MO"}
        out: List[Dict[str, Any]] = []
        for product in list_products(exchange=exchange):
            if product.root in option_only and not include_options_only:
                continue
            market = getattr(product, "market_category", "CNFutures")
            out.append(
                {
                    "root": product.root,
                    "symbol": f"{product.root}0",
                    "name": product.name,
                    "exchange": product.exchange,
                    "market": market,
                    "market_type": "futures",
                    "product_class": product.product_class,
                }
            )
        return out

logger = get_logger(__name__)

DEFAULT_TIMEFRAMES = ("1D",)
DAILY_LOOKBACK_BARS = 10000
MINUTE_LOOKBACK_BARS = 3000


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
    }
    for item in raw:
        tf = aliases.get(str(item or "").strip().lower(), str(item or "").strip())
        if not tf or tf in seen:
            continue
        seen.add(tf)
        out.append(tf)
    return out or list(DEFAULT_TIMEFRAMES)


def select_history_targets(
    *,
    symbols: Optional[Sequence[str]] = None,
    exchanges: Optional[Sequence[str]] = None,
) -> List[Dict[str, Any]]:
    wanted_syms = {str(s).strip().upper() for s in (symbols or []) if str(s).strip()}
    wanted_ex = {str(e).strip().upper() for e in (exchanges or []) if str(e).strip()}
    rows = list_continuous_history_targets()
    if wanted_ex:
        rows = [row for row in rows if str(row["exchange"]).upper() in wanted_ex]
    if wanted_syms:
        expanded = set()
        for raw in wanted_syms:
            feed, _mode = resolve_history_symbol(raw)
            expanded.add(feed.upper())
            expanded.add(raw.upper())
        rows = [row for row in rows if row["symbol"].upper() in expanded or row["root"].upper() in wanted_syms]
    return rows


def _watch_spec(target: Dict[str, Any], timeframe: str) -> WatchSpec:
    lookback = DAILY_LOOKBACK_BARS if timeframe.upper() in {"1D", "1W"} else MINUTE_LOOKBACK_BARS
    return WatchSpec(
        market=str(target["market"]),
        symbol=str(target["symbol"]),
        timeframe=timeframe,
        exchange_id="",
        market_type=str(target.get("market_type") or "futures"),
        lookback_bars=lookback,
    )


def _fetch_with_retry(
    src: CnFuturesDataSource,
    symbol: str,
    timeframe: str,
    *,
    retries: int,
    sleeper: Callable[[float], None],
) -> List[Dict[str, Any]]:
    last_exc: Optional[BaseException] = None
    attempts = max(1, int(retries))
    for attempt in range(1, attempts + 1):
        try:
            rows = src.get_history(symbol, timeframe)
            if rows:
                return list(rows)
            last_exc = ValueError(f"empty history for {symbol} {timeframe}")
        except Exception as exc:  # noqa: BLE001 — persist failure, keep ingesting peers
            last_exc = exc
            logger.warning(
                "CN futures history fetch failed symbol=%s tf=%s attempt=%s/%s: %s",
                symbol,
                timeframe,
                attempt,
                attempts,
                exc,
            )
        if attempt < attempts:
            sleeper(min(30.0, 2.0 ** attempt))
    if last_exc:
        raise last_exc
    return []


def ingest_cn_futures_history(
    *,
    timeframes: Sequence[str] = DEFAULT_TIMEFRAMES,
    persist: bool = False,
    provider: str = "akshare",
    retries: int = 3,
    symbols: Optional[Sequence[str]] = None,
    exchanges: Optional[Sequence[str]] = None,
    register_watch: bool = True,
    derive_weekly: bool = True,
    src: Optional[CnFuturesDataSource] = None,
    sleeper: Callable[[float], None] = time.sleep,
) -> Dict[str, Any]:
    """Fetch catalog-wide continuous history and optionally persist it.

    ``provider`` is forced for this process so a failed Sina call cannot fall
    back to compliance synthetic bars and pollute production.
    """
    tfs = _normalize_timeframes(timeframes)
    os.environ["CN_FUTURES_MARKET_DATA_PROVIDER"] = (provider or "akshare").strip() or "akshare"
    source = src or CnFuturesDataSource()
    targets = select_history_targets(symbols=symbols, exchanges=exchanges)
    started = time.time()
    results: List[Dict[str, Any]] = []
    errors: List[Dict[str, Any]] = []
    upserted_total = 0
    watch_specs: List[WatchSpec] = []

    want_weekly = "1W" in tfs
    fetch_tfs = [tf for tf in tfs if tf != "1W"]
    if want_weekly and "1D" not in fetch_tfs:
        fetch_tfs.append("1D")

    for target in targets:
        symbol = str(target["symbol"])
        item: Dict[str, Any] = {
            "exchange": target["exchange"],
            "root": target["root"],
            "symbol": symbol,
            "market": target["market"],
            "name": target["name"],
            "timeframes": {},
        }
        daily_rows: List[Dict[str, Any]] = []
        for tf in fetch_tfs:
            try:
                rows = _fetch_with_retry(
                    source, symbol, tf, retries=retries, sleeper=sleeper
                )
            except Exception as exc:  # noqa: BLE001
                errors.append({"symbol": symbol, "timeframe": tf, "error": str(exc)})
                if tf in tfs:
                    item["timeframes"][tf] = {"ok": False, "error": str(exc)}
                elif tf == "1D" and want_weekly:
                    item["timeframes"]["1W"] = {
                        "ok": False,
                        "error": f"daily source failed: {exc}",
                    }
                continue
            validated = sanitize_bars(rows)
            payload = {
                "ok": True,
                "bars": len(validated.clean_bars),
                "rejected": len(validated.rejected_bars),
                "start_time": validated.clean_bars[0]["time"] if validated.clean_bars else None,
                "end_time": validated.clean_bars[-1]["time"] if validated.clean_bars else None,
                "last_close": validated.clean_bars[-1]["close"] if validated.clean_bars else None,
            }
            if tf == "1D":
                daily_rows = validated.clean_bars
            if persist and tf in tfs and validated.clean_bars:
                spec = _watch_spec(target, tf)
                written = repository.upsert_bars(
                    spec,
                    validated.clean_bars,
                    source="cn_futures_history",
                    quality_flags=["validated", "akshare"],
                )
                payload["upserted"] = written
                upserted_total += written
                if register_watch:
                    watch_specs.append(spec)
            if tf in tfs:
                item["timeframes"][tf] = payload

        if want_weekly and daily_rows:
            weekly = source._resample(daily_rows, TIMEFRAME_SECONDS["1W"])
            validated = sanitize_bars(weekly)
            payload = {
                "ok": True,
                "bars": len(validated.clean_bars),
                "rejected": len(validated.rejected_bars),
                "derived_from": "1D",
                "start_time": validated.clean_bars[0]["time"] if validated.clean_bars else None,
                "end_time": validated.clean_bars[-1]["time"] if validated.clean_bars else None,
            }
            if persist and validated.clean_bars:
                spec = _watch_spec(target, "1W")
                written = repository.upsert_bars(
                    spec,
                    validated.clean_bars,
                    source="cn_futures_history",
                    quality_flags=["validated", "akshare", "resampled"],
                )
                payload["upserted"] = written
                upserted_total += written
                if register_watch:
                    watch_specs.append(spec)
            item["timeframes"]["1W"] = payload
        results.append(item)

    watch_written = 0
    if persist and register_watch and watch_specs:
        try:
            watch_written = repository.upsert_watch_specs(watch_specs)
        except Exception as exc:  # noqa: BLE001
            logger.warning("register CN futures history watchlist failed: %s", exc)
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
        "targets": len(targets),
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
        "CN futures history ingest status=%s targets=%s ok=%s upserted=%s elapsed=%.1fs",
        status,
        len(targets),
        ok_symbols,
        upserted_total,
        summary["elapsed_sec"],
    )
    return summary


def ingest_from_env() -> Dict[str, Any]:
    raw_tf = os.getenv("CN_FUTURES_INGEST_TIMEFRAMES", "1D,1W")
    raw_symbols = os.getenv("CN_FUTURES_INGEST_SYMBOLS", "")
    raw_ex = os.getenv("CN_FUTURES_INGEST_EXCHANGES", "")
    return ingest_cn_futures_history(
        timeframes=[p.strip() for p in raw_tf.split(",") if p.strip()],
        persist=_bool_env("CN_FUTURES_INGEST_PERSIST", False),
        provider=os.getenv("CN_FUTURES_INGEST_PROVIDER", "akshare") or "akshare",
        retries=max(1, int(os.getenv("CN_FUTURES_INGEST_RETRIES", "3") or 3)),
        symbols=[p.strip() for p in raw_symbols.split(",") if p.strip()] or None,
        exchanges=[p.strip() for p in raw_ex.split(",") if p.strip()] or None,
        register_watch=_bool_env("CN_FUTURES_INGEST_REGISTER_WATCH", True),
    )
