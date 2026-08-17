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
MINUTE_LOOKBACK_BARS = 20000
DAILY_TFS = {"1D", "1W"}
DERIVE_FROM_1M = ("3m", "5m", "15m", "30m", "1H", "4H")
RESUME_MIN_BARS = 200


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


def _apply_stitch_months(months: Optional[int]) -> int:
    value = max(1, int(months if months is not None else os.getenv("CN_FUTURES_MINUTE_STITCH_MONTHS", "12") or 12))
    os.environ["CN_FUTURES_MINUTE_STITCH_MONTHS"] = str(value)
    try:
        import app.data_sources.cn_futures as cn_mod

        cn_mod._MINUTE_STITCH_MONTHS = value
    except Exception:
        pass
    return value


def _watch_spec(target: Dict[str, Any], timeframe: str) -> WatchSpec:
    lookback = DAILY_LOOKBACK_BARS if timeframe.upper() in DAILY_TFS else MINUTE_LOOKBACK_BARS
    return WatchSpec(
        market=str(target["market"]),
        symbol=str(target["symbol"]),
        timeframe=timeframe,
        exchange_id="",
        market_type=str(target.get("market_type") or "futures"),
        lookback_bars=lookback,
    )


def _existing_bar_count(spec: WatchSpec) -> int:
    counter = getattr(repository, "count_bars", None)
    if callable(counter):
        try:
            return int(counter(spec))
        except Exception:
            pass
    return len(repository.load_bars(spec, limit=RESUME_MIN_BARS))


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
    watch_intraday: bool = False,
    derive_weekly: bool = True,
    stitch_months: Optional[int] = None,
    resume: bool = True,
    src: Optional[CnFuturesDataSource] = None,
    sleeper: Callable[[float], None] = time.sleep,
    on_progress: Optional[Callable[[Dict[str, Any]], None]] = None,
) -> Dict[str, Any]:
    """Fetch catalog-wide continuous history and optionally persist it.

    ``provider`` is forced for this process so a failed Sina call cannot fall
    back to compliance synthetic bars and pollute production.

    When ``1m`` is requested, higher intraday frames (5m/15m/30m/1H/4H) are
    resampled locally so the full catalog does not hit Sina once per timeframe.
    Minute watches are opt-in: registering 69 x 1m targets would overload the
    historical maintainer.
    """
    tfs = _normalize_timeframes(timeframes)
    os.environ["CN_FUTURES_MARKET_DATA_PROVIDER"] = (provider or "akshare").strip() or "akshare"
    stitch = _apply_stitch_months(stitch_months)
    if any(tf in {"1m", "3m", "5m", "15m", "30m", "1H", "4H"} for tf in tfs):
        os.environ.setdefault("CN_FUTURES_MINUTE_STITCH_PAUSE_SEC", "0.35")
    source = src or CnFuturesDataSource()
    targets = select_history_targets(symbols=symbols, exchanges=exchanges)
    started = time.time()
    results: List[Dict[str, Any]] = []
    errors: List[Dict[str, Any]] = []
    upserted_total = 0
    watch_specs: List[WatchSpec] = []
    skipped = 0

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
            source="cn_futures_history",
            quality_flags=flags,
        )
        upserted_total += written
        if _should_watch(timeframe):
            watch_specs.append(spec)
        return written

    for index, target in enumerate(targets, start=1):
        symbol = str(target["symbol"])
        item: Dict[str, Any] = {
            "exchange": target["exchange"],
            "root": target["root"],
            "symbol": symbol,
            "market": target["market"],
            "name": target["name"],
            "timeframes": {},
        }
        if resume and persist and want_1m:
            existing = _existing_bar_count(_watch_spec(target, "1m"))
            if existing >= RESUME_MIN_BARS:
                skipped += 1
                item["skipped"] = True
                item["timeframes"]["1m"] = {"ok": True, "bars": existing, "skipped": True}
                for tf in derived_tfs:
                    item["timeframes"][tf] = {"ok": True, "skipped": True, "derived_from": "1m"}
                results.append(item)
                logger.info("skip %s 1m already has %s bars (%s/%s)", symbol, existing, index, len(targets))
                continue

        daily_rows: List[Dict[str, Any]] = []
        minute_rows: List[Dict[str, Any]] = []
        logger.info("CN futures ingest %s/%s symbol=%s tfs=%s", index, len(targets), symbol, fetch_tfs)
        print(f"ingest {index}/{len(targets)} {symbol} fetch={fetch_tfs}", flush=True)
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
            if tf == "1m":
                minute_rows = validated.clean_bars
            if tf in tfs:
                payload["upserted"] = _persist_bars(
                    target, tf, validated.clean_bars, ["validated", "akshare"]
                )
                item["timeframes"][tf] = payload

        if want_1m and minute_rows:
            for tf in derived_tfs:
                seconds = TIMEFRAME_SECONDS.get(tf)
                if not seconds:
                    continue
                resampled = source._resample(minute_rows, seconds)
                validated = sanitize_bars(resampled)
                payload = {
                    "ok": True,
                    "bars": len(validated.clean_bars),
                    "rejected": len(validated.rejected_bars),
                    "derived_from": "1m",
                    "start_time": validated.clean_bars[0]["time"] if validated.clean_bars else None,
                    "end_time": validated.clean_bars[-1]["time"] if validated.clean_bars else None,
                }
                payload["upserted"] = _persist_bars(
                    target,
                    tf,
                    validated.clean_bars,
                    ["validated", "akshare", "resampled"],
                )
                item["timeframes"][tf] = payload
        elif want_1m and derived_tfs and "1m" in item["timeframes"] and not item["timeframes"]["1m"].get("ok"):
            for tf in derived_tfs:
                item["timeframes"][tf] = {
                    "ok": False,
                    "error": "1m source failed",
                }

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
            payload["upserted"] = _persist_bars(
                target,
                "1W",
                validated.clean_bars,
                ["validated", "akshare", "resampled"],
            )
            item["timeframes"]["1W"] = payload
        results.append(item)
        if on_progress:
            on_progress({"index": index, "total": len(targets), "symbol": symbol, "item": item})
        if want_1m and index < len(targets):
            pause = float(os.getenv("CN_FUTURES_INGEST_SYMBOL_PAUSE_SEC", "1.5") or 1.5)
            if pause > 0:
                sleeper(pause)

    watch_written = 0
    if persist and watch_specs:
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
        "stitch_months": stitch,
        "targets": len(targets),
        "ok_symbols": ok_symbols,
        "skipped_symbols": skipped,
        "failed_symbols": len({e["symbol"] for e in errors if e.get("symbol") and e["symbol"] != "*"}),
        "upserted_rows": upserted_total,
        "watch_written": watch_written,
        "elapsed_sec": round(time.time() - started, 2),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "errors": errors,
        "results": results,
    }
    logger.info(
        "CN futures history ingest status=%s targets=%s ok=%s skipped=%s upserted=%s elapsed=%.1fs",
        status,
        len(targets),
        ok_symbols,
        skipped,
        upserted_total,
        summary["elapsed_sec"],
    )
    return summary


def ingest_from_env() -> Dict[str, Any]:
    raw_tf = os.getenv("CN_FUTURES_INGEST_TIMEFRAMES", "1D,1W")
    raw_symbols = os.getenv("CN_FUTURES_INGEST_SYMBOLS", "")
    raw_ex = os.getenv("CN_FUTURES_INGEST_EXCHANGES", "")
    stitch_raw = os.getenv("CN_FUTURES_MINUTE_STITCH_MONTHS") or os.getenv("CN_FUTURES_INGEST_STITCH_MONTHS")
    return ingest_cn_futures_history(
        timeframes=[p.strip() for p in raw_tf.split(",") if p.strip()],
        persist=_bool_env("CN_FUTURES_INGEST_PERSIST", False),
        provider=os.getenv("CN_FUTURES_INGEST_PROVIDER", "akshare") or "akshare",
        retries=max(1, int(os.getenv("CN_FUTURES_INGEST_RETRIES", "3") or 3)),
        symbols=[p.strip() for p in raw_symbols.split(",") if p.strip()] or None,
        exchanges=[p.strip() for p in raw_ex.split(",") if p.strip()] or None,
        register_watch=_bool_env("CN_FUTURES_INGEST_REGISTER_WATCH", True),
        watch_intraday=_bool_env("CN_FUTURES_INGEST_WATCH_INTRADAY", False),
        stitch_months=int(stitch_raw) if stitch_raw else None,
        resume=_bool_env("CN_FUTURES_INGEST_RESUME", True),
    )
