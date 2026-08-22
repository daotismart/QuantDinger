"""Orchestration for realtime + historical market data maintenance."""

from __future__ import annotations

import os
import time
from typing import Any, Dict, List, Optional, Tuple

from app.services.ctp_md.config import CtpMdConfig
from app.services.market_data_maint.config import (
    MarketDataMaintSettings,
    WatchSpec,
    parse_watch_csv,
)
from app.services.market_data_maint import repository
from app.services.market_data_maint.historical import run_historical_maintenance
from app.services.market_data_maint.realtime import get_realtime_maintainer
from app.utils.logger import get_logger

logger = get_logger(__name__)

_INDEX_ROOTS = {"IF", "IH", "IC", "IM", "IO", "HO", "MO"}


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)) or default)
    except Exception:
        return default


def _symbol_root(symbol: str) -> str:
    text = str(symbol or "").strip().upper()
    out: List[str] = []
    for ch in text:
        if ch.isalpha():
            out.append(ch)
        else:
            break
    return "".join(out)


def resolve_cn_market(symbol: str, market: str = "") -> str:
    """Map legacy Futures/CTP labels onto CNFutures / CNIndexFutures."""
    current = str(market or "").strip()
    if current in {"CNFutures", "CNIndexFutures", "CNFuturesOptions", "CNIndexOptions"}:
        return current
    root = _symbol_root(symbol)
    if not root:
        return current or "Futures"
    try:
        from app.markets.cn_futures import resolve_market_category

        return str(
            resolve_market_category(symbol)
            or resolve_market_category(root)
            or current
            or "CNFutures"
        )
    except Exception:
        if root in _INDEX_ROOTS:
            return "CNIndexFutures"
        # Mainland commodity roots are alphabetic and typically 1-3 letters.
        if root.isalpha() and 1 <= len(root) <= 3:
            return "CNFutures"
        return current or "Futures"


def normalize_watch_spec(spec: WatchSpec) -> WatchSpec:
    market = str(spec.market or "").strip()
    symbol = str(spec.symbol or "").strip()
    if market in {"", "Futures", "Future"} or market.lower() == "futures":
        market = resolve_cn_market(symbol, market)
    # CTP exchange_id is not a kline routing key for CN continuous history.
    exchange_id = str(spec.exchange_id or "").strip()
    if market.startswith("CN") and exchange_id.lower() in {"ctp", "openctp"}:
        exchange_id = ""
    return WatchSpec(
        market=market,
        symbol=symbol,
        timeframe=str(spec.timeframe or "1m"),
        exchange_id=exchange_id,
        market_type=str(spec.market_type or "") or ("futures" if market.startswith("CN") else ""),
        lookback_bars=int(spec.lookback_bars or 1500),
    )


def collect_watch_specs(settings: Optional[MarketDataMaintSettings] = None) -> List[WatchSpec]:
    settings = settings or MarketDataMaintSettings.load()
    specs: List[WatchSpec] = []
    seen = set()

    def _add(spec: WatchSpec) -> None:
        normalized = normalize_watch_spec(spec)
        # Drop unmapped generic Futures leftovers.
        if normalized.market in {"Futures", "Future"}:
            return
        key = normalized.key().lower()
        if key in seen:
            return
        seen.add(key)
        specs.append(normalized)

    for spec in parse_watch_csv(settings.watchlist_csv):
        _add(spec)
    for spec in repository.list_watch_specs():
        _add(spec)
    lookback = _env_int("MARKET_DATA_MAINT_LOOKBACK_BARS", 1500)
    for instrument in CtpMdConfig.INSTRUMENTS:
        _add(
            WatchSpec(
                market=resolve_cn_market(str(instrument), "CNFutures"),
                symbol=str(instrument),
                timeframe="1m",
                exchange_id="",
                market_type="futures",
                lookback_bars=lookback,
            )
        )
    return specs


def select_historical_batch(specs: List[WatchSpec]) -> Tuple[List[WatchSpec], Dict[str, Any]]:
    """Prefer stale symbols and cap work per cycle so beat jobs can finish."""
    batch_size = max(1, _env_int("MARKET_DATA_MAINT_HISTORICAL_BATCH_SIZE", 40))
    fresh_sec = max(60, _env_int("MARKET_DATA_MAINT_FRESH_SEC", 6 * 3600))
    now = int(time.time())
    ranked: List[Tuple[int, WatchSpec]] = []
    skipped_fresh = 0
    for spec in specs:
        latest = 0
        try:
            latest = int(repository.latest_bar_ts(spec) or 0)
        except Exception:
            latest = 0
        age = now - latest if latest > 0 else 10**12
        if latest > 0 and age <= fresh_sec:
            skipped_fresh += 1
            continue
        ranked.append((age, spec))
    ranked.sort(key=lambda item: item[0], reverse=True)
    selected = [spec for _, spec in ranked[:batch_size]]
    # If everything looks fresh, still refresh a small rotating slice.
    if not selected and specs:
        selected = specs[: min(batch_size, len(specs))]
        skipped_fresh = max(0, skipped_fresh - len(selected))
    meta = {
        "candidates": len(specs),
        "selected": len(selected),
        "skipped_fresh": skipped_fresh,
        "batch_size": batch_size,
        "fresh_sec": fresh_sec,
    }
    return selected, meta


def sync_watchlist_to_db(settings: Optional[MarketDataMaintSettings] = None) -> int:
    specs = collect_watch_specs(settings)
    if not specs:
        return 0
    try:
        # Disable legacy Futures rows so they stop poisoning historical cycles.
        try:
            repository.disable_markets(["Futures", "Future"])
        except Exception as exc:
            logger.debug("disable_markets skipped: %s", exc)
        return repository.upsert_watch_specs(specs)
    except Exception as exc:
        logger.warning("sync_watchlist_to_db failed: %s", exc)
        return 0


def run_historical_cycle(*, trigger: str = "manual", on_progress=None) -> Dict[str, Any]:
    settings = MarketDataMaintSettings.load()
    if not settings.enabled or not settings.historical_enabled:
        return {"skipped": True, "reason": "disabled"}
    sync_watchlist_to_db(settings)
    specs = collect_watch_specs(settings)
    if not specs:
        return {"skipped": True, "reason": "empty_watchlist"}
    batch, batch_meta = select_historical_batch(specs)
    result = run_historical_maintenance(
        batch,
        settings=settings,
        trigger=trigger,
        on_progress=on_progress,
    )
    if isinstance(result, dict):
        result["batch"] = batch_meta
    return result


def run_retention_cycle(*, trigger: str = "manual") -> Dict[str, Any]:
    settings = MarketDataMaintSettings.load()
    if not settings.enabled:
        return {"skipped": True, "reason": "disabled"}
    run_id = repository.claim_run(run_kind="retention", trigger_type=trigger)
    if run_id is None:
        return {"skipped": True, "reason": "already_running"}
    ticks = repository.purge_old_ticks(retention_days=settings.tick_retention_days)
    bars = repository.purge_old_bars(retention_days=settings.bar_retention_days)
    payload = {
        "ticks_deleted": ticks,
        "bars_deleted": bars,
        "tick_retention_days": settings.tick_retention_days,
        "bar_retention_days": settings.bar_retention_days,
    }
    repository.finish_run(run_id, "success", payload)
    payload["run_id"] = run_id
    payload["status"] = "success"
    return payload


def start_realtime_maintenance() -> None:
    settings = MarketDataMaintSettings.load()
    if not settings.enabled or not settings.realtime_enabled:
        logger.info("Market data realtime maintenance not started (disabled)")
        return
    sync_watchlist_to_db(settings)
    get_realtime_maintainer().start()
    logger.info("Market data realtime maintenance start requested")


def maintenance_status() -> Dict[str, Any]:
    settings = MarketDataMaintSettings.load()
    return {
        "settings": {
            "enabled": settings.enabled,
            "realtimeEnabled": settings.realtime_enabled,
            "historicalEnabled": settings.historical_enabled,
            "realtimeIntervalSec": settings.realtime_interval_sec,
            "historicalIntervalSec": settings.historical_interval_sec,
            "persistTicks": settings.persist_ticks,
        },
        "watchlist": [spec.key() for spec in collect_watch_specs(settings)],
        "realtime": get_realtime_maintainer().status(),
        "recentRuns": repository.latest_runs(limit=10),
    }
