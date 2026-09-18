"""Orchestration for realtime + historical market data maintenance."""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

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


def collect_watch_specs(settings: Optional[MarketDataMaintSettings] = None) -> List[WatchSpec]:
    settings = settings or MarketDataMaintSettings.load()
    specs: List[WatchSpec] = []
    seen = set()

    def _add(spec: WatchSpec) -> None:
        key = spec.key().lower()
        if key in seen:
            return
        seen.add(key)
        specs.append(spec)

    for spec in parse_watch_csv(settings.watchlist_csv):
        _add(spec)
    for spec in repository.list_watch_specs():
        _add(spec)
    # CTP instruments default to Futures 1m continuity maintenance.
    for instrument in CtpMdConfig.INSTRUMENTS:
        _add(
            WatchSpec(
                market="Futures",
                symbol=str(instrument),
                timeframe="1m",
                exchange_id="ctp",
                market_type="futures",
                lookback_bars=int(os.getenv("MARKET_DATA_MAINT_LOOKBACK_BARS", "1500") or 1500),
            )
        )
    return specs


def sync_watchlist_to_db(settings: Optional[MarketDataMaintSettings] = None) -> int:
    specs = collect_watch_specs(settings)
    if not specs:
        return 0
    try:
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
    return run_historical_maintenance(
        specs,
        settings=settings,
        trigger=trigger,
        on_progress=on_progress,
    )


def run_retention_cycle(*, trigger: str = "manual") -> Dict[str, Any]:
    settings = MarketDataMaintSettings.load()
    if not settings.enabled:
        return {"skipped": True, "reason": "disabled"}
    run_id = repository.claim_run(run_kind="retention", trigger_type=trigger)
    ticks = repository.purge_old_ticks(retention_days=settings.tick_retention_days)
    bars = repository.purge_old_bars(retention_days=settings.bar_retention_days)
    payload = {
        "ticks_deleted": ticks,
        "bars_deleted": bars,
        "tick_retention_days": settings.tick_retention_days,
        "bar_retention_days": settings.bar_retention_days,
    }
    if run_id is not None:
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
