"""Live runtime price feed backed by CTP tick cache."""

from __future__ import annotations

from typing import Any, Callable, Dict, Iterable, Mapping

from app.services.ctp_md.config import CtpMdConfig
from app.services.ctp_md.gateway import get_ctp_md_gateway
from app.services.ctp_md.store import get_ctp_tick_store
from app.services.ctp_md.symbols import normalize_ctp_instrument, unique_instruments
from app.services.market_price_stream import PriceFeedSnapshot
from app.utils.logger import get_logger

logger = get_logger(__name__)


class CtpTickPriceFeed:
    """Public-market-style snapshot feed using CTP MdApi ticks.

    Shares the same ``start`` / ``stop`` / ``snapshot`` surface as
    :class:`~app.services.market_price_stream.PublicMarketPriceFeed` so the
    trading executor can swap feeds without special-casing risk loops.
    """

    SUPPORTED_EXCHANGES = {"ctp"}

    def __init__(
        self,
        *,
        exchange_id: str = "ctp",
        market_type: str = "futures",
        instruments: Iterable[Mapping[str, Any]],
        rest_fallback: Callable[[], Dict[str, float]],
    ) -> None:
        self.exchange_id = str(exchange_id or "ctp").strip().lower()
        self.market_type = str(market_type or "futures").strip().lower()
        self.instruments = [dict(item) for item in instruments]
        self.rest_fallback = rest_fallback
        self._gateway = get_ctp_md_gateway()
        self._store = get_ctp_tick_store()
        self._started = False

    @property
    def supported(self) -> bool:
        return self.exchange_id in self.SUPPORTED_EXCHANGES and bool(self.instruments)

    def start(self) -> None:
        if not self.supported:
            return
        symbols = unique_instruments(
            normalize_ctp_instrument(str(item.get("symbol") or ""))
            for item in self.instruments
        )
        if not symbols:
            return
        try:
            if not self._gateway.settings.enabled:
                # Runtime request still wants CTP ticks: ensure gateway settings
                # allow a best-effort subscribe when the process already started
                # an enabled gateway via env.
                logger.debug("CTP price feed start skipped; CTP_MD_ENABLED is false")
            self._gateway.subscribe(symbols)
            if self._gateway.settings.enabled and not self._gateway.running:
                self._gateway.start()
            self._started = True
        except Exception as exc:
            logger.warning("CTP tick price feed failed to start: %s", exc)

    def stop(self, timeout: float = 3.0) -> None:
        # Keep the process-wide gateway alive for other consumers; only drop
        # this feed's subscription interest when uniquely owned later.
        self._started = False

    def snapshot(self, *, max_age_seconds: float = 10.0) -> PriceFeedSnapshot:
        stale_after = max(
            0.5,
            float(max_age_seconds or CtpMdConfig.TICK_STALE_AFTER_SECONDS or 10.0),
        )
        stream_prices = self._store.prices_for(self.instruments, max_age_seconds=stale_after)
        missing = {
            str(item.get("key") or "")
            for item in self.instruments
            if str(item.get("key") or "") not in stream_prices
        }
        fallback: Dict[str, float] = {}
        if missing:
            try:
                fallback = {
                    str(key): float(value or 0.0)
                    for key, value in (self.rest_fallback() or {}).items()
                    if str(key) in missing and float(value or 0.0) > 0
                }
            except Exception as exc:
                logger.debug("CTP tick REST fallback failed: %s", exc)
        prices = {**fallback, **stream_prices}
        if stream_prices and fallback:
            source = "ctp_tick+rest_fallback"
        elif stream_prices:
            source = "ctp_tick"
        elif fallback:
            source = "rest_fallback"
        else:
            source = "unavailable"
        ages = []
        for item in self.instruments:
            key = str(item.get("key") or "")
            if key not in stream_prices:
                continue
            age = self._store.age_ms(str(item.get("symbol") or key))
            if age >= 0:
                ages.append(age)
        return PriceFeedSnapshot(
            prices=prices,
            source=source,
            age_ms=int(max(ages) if ages else 0),
            connected=bool(self._gateway.connected),
        )
