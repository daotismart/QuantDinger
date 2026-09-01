"""Periodic maintenance tasks managed by Celery Beat."""

from __future__ import annotations

import os
import socket

from app.celery_app import celery_app


def _enabled(name: str, default: str = "true") -> bool:
    return os.getenv(name, default).strip().lower() in {"1", "true", "yes", "on"}


@celery_app.task(name="quantdinger.tasks.worker_heartbeat")
def record_worker_heartbeat() -> None:
    from app.services.strategy_command_repository import StrategyCommandRepository

    StrategyCommandRepository().record_worker_heartbeat(
        worker_id=f"celery:{socket.gethostname()}",
        role="celery",
        metadata={},
    )


@celery_app.task(name="quantdinger.tasks.cleanup_runtime_metadata")
def cleanup_runtime_metadata() -> dict:
    from app.services.strategy_command_repository import StrategyCommandRepository

    return StrategyCommandRepository().cleanup_runtime_metadata(
        command_retention_days=max(1, int(os.getenv("STRATEGY_COMMAND_RETENTION_DAYS", "30"))),
        heartbeat_retention_days=max(1, int(os.getenv("WORKER_HEARTBEAT_RETENTION_DAYS", "7"))),
    )


@celery_app.task(
    bind=True,
    name="quantdinger.tasks.reflection",
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_jitter=True,
    max_retries=3,
)
def run_reflection(self):
    del self
    if not _enabled("ENABLE_REFLECTION_WORKER"):
        return {"skipped": True}
    from app.services.reflection import ReflectionService

    return ReflectionService().run_verification_cycle()


@celery_app.task(
    bind=True,
    name="quantdinger.tasks.ai_calibration",
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_jitter=True,
    max_retries=3,
)
def run_ai_calibration(self):
    del self
    if not _enabled("ENABLE_OFFLINE_AI_CALIBRATION"):
        return {"skipped": True}
    from app.services.ai_calibration import AICalibrationService

    service = AICalibrationService()
    results = []
    markets = os.getenv("AI_CALIBRATION_MARKETS", "Crypto").split(",")
    for market in markets:
        market = market.strip()
        if not market:
            continue
        result = service.calibrate_market(
            market=market,
            lookback_days=int(os.getenv("AI_CALIBRATION_LOOKBACK_DAYS", "30")),
            min_samples=int(os.getenv("AI_CALIBRATION_MIN_SAMPLES", "80")),
        )
        if result is not None:
            results.append(result.__dict__)
    return {"markets": results}


@celery_app.task(
    bind=True,
    name="quantdinger.tasks.market_catalog_sync",
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_jitter=True,
    max_retries=3,
)
def run_market_catalog_sync(self):
    del self
    if not _enabled("MARKET_CATALOG_AUTO_SYNC"):
        return {"skipped": True}
    from app.services.market_catalog_sync import run_market_catalog_sync_inline

    return run_market_catalog_sync_inline("celery-beat")


@celery_app.task(
    bind=True,
    name="quantdinger.tasks.market_data_historical_maint",
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_jitter=True,
    max_retries=3,
)
def run_market_data_historical_maint(self):
    del self
    if not _enabled("MARKET_DATA_MAINT_ENABLED", "false"):
        return {"skipped": True}
    if not _enabled("MARKET_DATA_MAINT_HISTORICAL_ENABLED", "true"):
        return {"skipped": True, "reason": "historical_disabled"}
    from app.services.market_data_maint import run_historical_cycle

    return run_historical_cycle(trigger="celery-beat")


@celery_app.task(
    bind=True,
    name="quantdinger.tasks.market_data_retention_maint",
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_jitter=True,
    max_retries=2,
)
def run_market_data_retention_maint(self):
    del self
    if not _enabled("MARKET_DATA_MAINT_ENABLED", "false"):
        return {"skipped": True}
    from app.services.market_data_maint import run_retention_cycle

    return run_retention_cycle(trigger="celery-beat")


def _csv_env(name: str) -> list[str] | None:
    raw = os.getenv(name, "")
    parts = [item.strip() for item in str(raw or "").replace(";", ",").split(",") if item.strip()]
    return parts or None


@celery_app.task(
    bind=True,
    name="quantdinger.tasks.cn_etf_options_history_ingest",
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_jitter=True,
    max_retries=1,
)
def run_cn_etf_options_history_ingest(self):
    """Post-close ETF options + underlying daily/weekly ingest.

    Disabled by default so a single Celery worker is not starved. Production
    prefers host crontab (`scripts/ops/cron-cn-etf-options-ingest.sh`); enable
    this Beat entry with CN_ETF_OPTIONS_INGEST_ENABLED=true as a backup.
    """
    del self
    if not _enabled("CN_ETF_OPTIONS_INGEST_ENABLED", "false"):
        return {"skipped": True, "reason": "disabled"}
    from app.services.market_data_maint.cn_etf_options_ingest import ingest_cn_etf_options_history

    timeframes = _csv_env("CN_ETF_OPTIONS_INGEST_TIMEFRAMES") or ["1D", "1W"]
    persist = _enabled("CN_ETF_OPTIONS_INGEST_PERSIST", "true")
    return ingest_cn_etf_options_history(
        timeframes=timeframes,
        persist=persist,
        provider=os.getenv("CN_ETF_OPTIONS_INGEST_PROVIDER", "akshare"),
        retries=max(1, int(os.getenv("CN_ETF_OPTIONS_INGEST_RETRIES", "3") or 3)),
        symbols=_csv_env("CN_ETF_OPTIONS_INGEST_SYMBOLS"),
        exchanges=_csv_env("CN_ETF_OPTIONS_INGEST_EXCHANGES"),
        include_underlyings=_enabled("CN_ETF_OPTIONS_INGEST_UNDERLYINGS", "true"),
        include_indices=_enabled("CN_ETF_OPTIONS_INGEST_INDICES", "true"),
        register_watch=_enabled("CN_ETF_OPTIONS_INGEST_WATCH", "true"),
        watch_intraday=_enabled("CN_ETF_OPTIONS_INGEST_WATCH_INTRADAY", "false"),
    )

