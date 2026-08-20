"""Local data service orchestration built on ``qd_market_bars``."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from app.data_sources import DataSourceFactory
from app.data_sources.local_bar import (
    local_read_settings,
    merge_kline_results,
    query_local_kline,
    try_local_kline,
)
from app.services.local_data.config import LocalDataSettings, save_local_read_overrides
from app.services.local_data import repository as ds_repo
from app.services.market_data_maint import repository
from app.services.market_data_maint.config import WatchSpec, parse_watch_csv
from app.services.market_data_maint.service import (
    collect_watch_specs,
    maintenance_status,
    run_historical_cycle,
    run_retention_cycle,
)
from app.services.market_data_maint.validators import detect_gaps
from app.services.market_data_maint.config import MarketDataMaintSettings
from app.utils.logger import get_logger

logger = get_logger(__name__)


def overview() -> Dict[str, Any]:
    inventory = repository.bar_inventory_summary(limit=20)
    maint = maintenance_status()
    settings = local_read_settings()
    return {
        "localService": settings.to_dict(),
        "maintenance": maint,
        "inventory": inventory,
        "configEntries": ds_repo.list_config(),
    }


def collection_watchlist(*, include_disabled: bool = True) -> List[Dict[str, Any]]:
    return repository.list_watch_rows(include_disabled=include_disabled)


def upsert_watchlist(raw: Any) -> Dict[str, Any]:
    if isinstance(raw, str):
        specs = parse_watch_csv(raw)
    elif isinstance(raw, list):
        specs = []
        for item in raw:
            if isinstance(item, str):
                specs.extend(parse_watch_csv(item))
            elif isinstance(item, dict):
                specs.append(
                    WatchSpec(
                        market=str(item.get("market") or "Futures"),
                        symbol=str(item.get("symbol") or ""),
                        timeframe=str(item.get("timeframe") or "1m"),
                        exchange_id=str(item.get("exchange_id") or item.get("exchangeId") or ""),
                        market_type=str(item.get("market_type") or item.get("marketType") or ""),
                        lookback_bars=int(item.get("lookback_bars") or item.get("lookbackBars") or 1500),
                    )
                )
    else:
        raise ValueError("watchlist must be string or list")
    specs = [spec for spec in specs if spec.symbol]
    if not specs:
        raise ValueError("no valid symbols")
    written = repository.upsert_watch_specs(specs)
    return {"upserted": written, "items": [spec.key() for spec in specs]}


def governance_inventory(*, limit: int = 100) -> Dict[str, Any]:
    rows = repository.bar_inventory_summary(limit=limit)
    total = repository.total_bar_count()
    return {"totalBars": total, "topSymbols": rows}


def governance_gaps(*, limit: int = 50) -> List[Dict[str, Any]]:
    settings = MarketDataMaintSettings.load()
    specs = collect_watch_specs(settings)[: max(1, int(limit))]
    issues: List[Dict[str, Any]] = []
    for spec in specs:
        lookback = max(50, int(spec.lookback_bars or 1500))
        bars = repository.load_bars(spec, limit=lookback)
        gaps = detect_gaps(
            bars,
            timeframe=spec.timeframe,
            session_gap_seconds=settings.session_gap_seconds,
        )
        data_gaps = [gap for gap in gaps if gap.kind == "data_gap"]
        if not data_gaps:
            continue
        issues.append(
            {
                "symbol": spec.key(),
                "barCount": len(bars),
                "dataGaps": len(data_gaps),
                "largestGapBars": max(g.missing_bars for g in data_gaps),
                "gaps": [
                    {
                        "startTs": g.start_ts,
                        "endTs": g.end_ts,
                        "missingBars": g.missing_bars,
                    }
                    for g in data_gaps[:5]
                ],
            }
        )
    return issues


def governance_quality(*, limit: int = 100) -> List[Dict[str, Any]]:
    return repository.quality_flag_summary(limit=limit)


def service_config() -> Dict[str, Any]:
    env = LocalDataSettings.from_env().to_dict()
    effective = local_read_settings().to_dict()
    return {"envDefaults": env, "effective": effective, "entries": ds_repo.list_config()}


def update_service_config(payload: Dict[str, Any]) -> Dict[str, Any]:
    allowed = {
        "localReadEnabled",
        "minCoverage",
        "maxStaleSec",
        "preferLocal",
        "warmUpstreamOnMiss",
    }
    patch = {k: payload[k] for k in allowed if k in payload}
    if not patch:
        raise ValueError("no supported config keys")
    merged = save_local_read_overrides(patch)
    return {"effective": merged}


def preview_kline(
    *,
    market: str,
    symbol: str,
    timeframe: str,
    limit: int = 100,
    exchange_id: Optional[str] = None,
    market_type: Optional[str] = None,
) -> Dict[str, Any]:
    local, sufficient = try_local_kline(
        market,
        symbol,
        timeframe,
        limit,
        exchange_id=exchange_id,
        market_type=market_type,
    )
    upstream = DataSourceFactory.get_kline(
        market,
        symbol,
        timeframe,
        limit,
        exchange_id=exchange_id,
        market_type=market_type,
        upstream_only=True,
    )
    effective = local if sufficient else merge_kline_results(local, upstream, limit=limit)
    source = "local" if sufficient else ("merged" if local and upstream else ("upstream" if upstream else "empty"))
    return {
        "source": source,
        "localCount": len(local),
        "upstreamCount": len(upstream),
        "effectiveCount": len(effective),
        "localSufficient": sufficient,
        "sample": effective[-min(5, len(effective)) :],
    }


def service_health() -> Dict[str, Any]:
    settings = local_read_settings()
    total = repository.total_bar_count()
    maint = maintenance_status()
    return {
        "localReadEnabled": settings.local_read_enabled,
        "totalBars": total,
        "watchlistSize": len(maint.get("watchlist") or []),
        "realtimeRunning": bool((maint.get("realtime") or {}).get("running")),
        "recentRuns": maint.get("recentRuns") or [],
    }
