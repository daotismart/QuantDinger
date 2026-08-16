"""Historical bar continuity maintenance: gap detect, backfill, validate."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from app.data_sources import DataSourceFactory
from app.data_sources.base import TIMEFRAME_SECONDS
from app.services.market_data_maint.config import MarketDataMaintSettings, WatchSpec
from app.services.market_data_maint import repository
from app.services.market_data_maint.validators import detect_gaps, sanitize_bars
from app.utils.logger import get_logger

logger = get_logger(__name__)


def _fetch_upstream(spec: WatchSpec, *, limit: int) -> List[Dict[str, Any]]:
    return list(
        DataSourceFactory.get_kline(
            spec.market,
            spec.symbol,
            spec.timeframe,
            max(10, int(limit)),
            exchange_id=spec.exchange_id or None,
            market_type=spec.market_type or None,
        )
        or []
    )


def maintain_symbol(
    spec: WatchSpec,
    *,
    settings: Optional[MarketDataMaintSettings] = None,
) -> Dict[str, Any]:
    settings = settings or MarketDataMaintSettings.load()
    lookback = max(50, int(spec.lookback_bars or 1500))
    stored = repository.load_bars(spec, limit=lookback)
    upstream = _fetch_upstream(spec, limit=lookback)
    validated = sanitize_bars(upstream)
    upserted = repository.upsert_bars(
        spec,
        validated.clean_bars,
        source="historical_maint",
        quality_flags=["validated"] if validated.clean_bars else [],
    )

    merged_for_gap = sanitize_bars(stored + validated.clean_bars).clean_bars
    gaps = detect_gaps(
        merged_for_gap,
        timeframe=spec.timeframe,
        session_gap_seconds=settings.session_gap_seconds,
    )
    data_gaps = [gap for gap in gaps if gap.kind == "data_gap"]
    backfilled = 0
    backfill_attempts = 0
    step = int(TIMEFRAME_SECONDS.get(spec.timeframe, 60))

    for gap in data_gaps[: settings.max_gap_bars]:
        # Upstream APIs are usually "latest N bars"; request a wider window and
        # rely on upsert + validation to fill the hole when the provider can.
        need = min(lookback, max(gap.missing_bars + 5, 50))
        backfill_attempts += 1
        try:
            patch = _fetch_upstream(spec, limit=need)
            patch_clean = sanitize_bars(patch).clean_bars
            in_range = [
                bar
                for bar in patch_clean
                if gap.start_ts - step <= int(bar["time"]) <= gap.end_ts + step
            ]
            if in_range:
                backfilled += repository.upsert_bars(
                    spec,
                    in_range,
                    source="historical_backfill",
                    quality_flags=["backfill"],
                )
        except Exception as exc:
            logger.warning("backfill failed %s: %s", spec.key(), exc)

    refreshed = repository.load_bars(spec, limit=lookback)
    remaining = [
        gap
        for gap in detect_gaps(
            refreshed,
            timeframe=spec.timeframe,
            session_gap_seconds=settings.session_gap_seconds,
        )
        if gap.kind == "data_gap"
    ]
    return {
        "symbol": spec.key(),
        "stored_before": len(stored),
        "upstream_clean": len(validated.clean_bars),
        "upstream_rejected": len(validated.rejected_bars),
        "upserted": upserted,
        "data_gaps_before": len(data_gaps),
        "backfill_attempts": backfill_attempts,
        "backfilled_rows": backfilled,
        "data_gaps_after": len(remaining),
        "session_gaps": len([gap for gap in gaps if gap.kind == "session_gap"]),
        "issues": [
            {"code": issue.code, "message": issue.message, "bar_time": issue.bar_time}
            for issue in validated.issues[:50]
        ],
        "continuity_ok": len(remaining) == 0,
        "accuracy_ok": len(validated.rejected_bars) == 0,
    }


def run_historical_maintenance(
    specs: List[WatchSpec],
    *,
    settings: Optional[MarketDataMaintSettings] = None,
    trigger: str = "manual",
) -> Dict[str, Any]:
    settings = settings or MarketDataMaintSettings.load()
    if not settings.enabled or not settings.historical_enabled:
        return {"skipped": True, "reason": "disabled"}
    run_id = repository.claim_run(run_kind="historical", trigger_type=trigger)
    results = []
    errors = []
    for spec in specs:
        try:
            results.append(maintain_symbol(spec, settings=settings))
        except Exception as exc:
            logger.exception("historical maintain failed %s", spec.key())
            errors.append({"symbol": spec.key(), "error": str(exc)})
    continuity_ok = sum(1 for item in results if item.get("continuity_ok"))
    accuracy_ok = sum(1 for item in results if item.get("accuracy_ok"))
    status = "success"
    if errors and results:
        status = "partial"
    elif errors and not results:
        status = "failed"
    elif results and continuity_ok < len(results):
        status = "partial"
    payload = {
        "symbols": len(specs),
        "processed": len(results),
        "continuity_ok": continuity_ok,
        "accuracy_ok": accuracy_ok,
        "errors": errors,
        "results": results,
    }
    if run_id is not None:
        repository.finish_run(run_id, status, payload)
    payload["status"] = status
    payload["run_id"] = run_id
    return payload
