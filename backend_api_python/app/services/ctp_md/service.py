"""Process-local CTP market-data supervisor."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from app.services.ctp_md.config import CtpMdConfig
from app.services.ctp_md.gateway import CtpMdGateway, get_ctp_md_gateway
from app.services.ctp_md.models import CtpTick
from app.services.ctp_md.store import get_ctp_tick_store
from app.services.ctp_md.symbols import looks_like_cn_futures_instrument, normalize_ctp_instrument
from app.utils.logger import get_logger

logger = get_logger(__name__)


def start_ctp_md_service() -> Optional[CtpMdGateway]:
    """Boot the shared CTP MdApi gateway when enabled."""
    settings = CtpMdConfig.settings()
    if not settings.enabled:
        logger.info("CTP market-data service disabled (CTP_MD_ENABLED!=true)")
        return None
    gateway = get_ctp_md_gateway()
    if settings.instruments:
        gateway.subscribe(settings.instruments)
    gateway.start()
    logger.info(
        "CTP market-data service start requested front=%s instruments=%s",
        settings.front,
        ",".join(settings.instruments) or "(runtime subscribe)",
    )
    return gateway


def ctp_ticker_for_symbol(symbol: str, *, max_age_seconds: Optional[float] = None) -> Optional[Dict[str, Any]]:
    """Return a CCXT-like ticker dict from the latest CTP tick, if fresh."""
    instrument = normalize_ctp_instrument(symbol)
    if not looks_like_cn_futures_instrument(instrument):
        return None
    settings = CtpMdConfig.settings()
    stale_after = (
        float(max_age_seconds)
        if max_age_seconds is not None
        else float(settings.tick_stale_after_seconds or 10.0)
    )
    tick = get_ctp_tick_store().get(instrument, max_age_seconds=stale_after)
    if tick is None or tick.usable_price <= 0:
        return None
    return tick.to_ticker()


def latest_ctp_ticks(*, max_age_seconds: Optional[float] = None) -> List[Dict[str, Any]]:
    settings = CtpMdConfig.settings()
    stale_after = (
        float(max_age_seconds)
        if max_age_seconds is not None
        else float(settings.tick_stale_after_seconds or 10.0)
    )
    return [tick.to_dict() for tick in get_ctp_tick_store().list_latest(max_age_seconds=stale_after)]


def ctp_md_status() -> Dict[str, Any]:
    gateway = get_ctp_md_gateway()
    status = gateway.status()
    status["tickCount"] = len(get_ctp_tick_store().list_latest(max_age_seconds=None))
    status["enabled"] = bool(CtpMdConfig.ENABLED)
    return status
