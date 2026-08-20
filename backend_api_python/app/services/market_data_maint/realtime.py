"""Realtime tick continuity monitor, persistence, and 1m bar aggregation."""

from __future__ import annotations

import threading
import time
from collections import defaultdict, deque
from typing import Any, Deque, Dict, List, Optional, Tuple

from app.services.ctp_md.gateway import get_ctp_md_gateway
from app.services.ctp_md.models import CtpTick
from app.services.ctp_md.service import ctp_md_status
from app.services.ctp_md.symbols import normalize_ctp_instrument, unique_instruments
from app.markets.cn_futures_sessions import is_instrument_in_session, md_connection_open
from app.services.market_data_maint.config import MarketDataMaintSettings, WatchSpec
from app.services.market_data_maint import repository
from app.services.market_data_maint.validators import align_bar_time, tick_anomaly
from app.utils.logger import get_logger

logger = get_logger(__name__)


class RealtimeMaintainer:
    """Process-local realtime continuity worker for CTP ticks / 1m bars."""

    def __init__(self, settings: Optional[MarketDataMaintSettings] = None) -> None:
        self.settings = settings or MarketDataMaintSettings.load()
        self._lock = threading.RLock()
        self._stop = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._tick_buffer: Deque[Dict[str, Any]] = deque(maxlen=20000)
        self._last_tick: Dict[str, Dict[str, Any]] = {}
        self._open_bars: Dict[Tuple[str, int], Dict[str, Any]] = {}
        self._stats: Dict[str, Any] = {
            "ticks_seen": 0,
            "ticks_persisted": 0,
            "bars_flushed": 0,
            "anomalies": 0,
            "resubscribes": 0,
            "last_error": "",
            "last_cycle_at": 0,
        }
        self._hooked = False

    @property
    def running(self) -> bool:
        return bool(self._thread and self._thread.is_alive())

    def status(self) -> Dict[str, Any]:
        with self._lock:
            stats = dict(self._stats)
            buffered = len(self._tick_buffer)
            open_bars = len(self._open_bars)
        status = {
            "running": self.running,
            "buffered_ticks": buffered,
            "open_bars": open_bars,
            "ctp": ctp_md_status(),
            **stats,
        }
        return status

    def start(self) -> None:
        if not self.settings.enabled or not self.settings.realtime_enabled:
            logger.info("Realtime market-data maintainer disabled")
            return
        self._ensure_ctp_hook()
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(
            target=self._run,
            name="MarketDataRealtimeMaint",
            daemon=True,
        )
        self._thread.start()

    def stop(self, timeout: float = 3.0) -> None:
        self._stop.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=max(0.0, float(timeout or 0.0)))

    def on_ctp_tick(self, tick: CtpTick) -> None:
        if tick is None or tick.usable_price <= 0:
            return
        payload = {
            "market": "Futures",
            "symbol": tick.instrument_id,
            "exchange_id": tick.exchange_id or "ctp",
            "tick_time_ms": int(tick.received_at_ms or int(time.time() * 1000)),
            "last_price": float(tick.usable_price),
            "volume": int(tick.volume or 0),
            "bid": float(tick.bid_price1 or 0),
            "ask": float(tick.ask_price1 or 0),
            "open_interest": float(tick.open_interest or 0),
            "payload": tick.to_dict(),
        }
        with self._lock:
            prev = self._last_tick.get(tick.instrument_id)
            issue = tick_anomaly(prev, payload, spike_ratio=self.settings.price_spike_ratio)
            if issue and issue.code == "tick_price_spike":
                self._stats["anomalies"] = int(self._stats.get("anomalies") or 0) + 1
                logger.warning(
                    "CTP tick anomaly %s %s price=%s",
                    tick.instrument_id,
                    issue.code,
                    payload["last_price"],
                )
            self._last_tick[tick.instrument_id] = payload
            self._tick_buffer.append(payload)
            self._stats["ticks_seen"] = int(self._stats.get("ticks_seen") or 0) + 1
            self._update_open_bar(payload)

    def _ensure_ctp_hook(self) -> None:
        if self._hooked:
            return
        gateway = get_ctp_md_gateway()
        previous = gateway._on_tick

        def _combined(tick: CtpTick) -> None:
            if previous is not None:
                try:
                    previous(tick)
                except Exception:
                    logger.exception("previous CTP on_tick failed")
            self.on_ctp_tick(tick)

        gateway._on_tick = _combined
        self._hooked = True

    def _update_open_bar(self, tick: Dict[str, Any]) -> None:
        symbol = str(tick.get("symbol") or "")
        price = float(tick.get("last_price") or 0)
        if not symbol or price <= 0:
            return
        ts = int(tick.get("tick_time_ms") or 0) // 1000
        bar_time = align_bar_time(ts, "1m")
        key = (symbol, bar_time)
        bar = self._open_bars.get(key)
        if bar is None:
            self._open_bars[key] = {
                "time": bar_time,
                "open": price,
                "high": price,
                "low": price,
                "close": price,
                "volume": float(tick.get("volume") or 0),
                "symbol": symbol,
                "exchange_id": str(tick.get("exchange_id") or "ctp"),
            }
            return
        bar["high"] = max(float(bar["high"]), price)
        bar["low"] = min(float(bar["low"]), price)
        bar["close"] = price
        bar["volume"] = max(float(bar.get("volume") or 0), float(tick.get("volume") or 0))

    def _run(self) -> None:
        logger.info("Realtime market-data maintainer started")
        while not self._stop.is_set():
            try:
                self.run_once()
            except Exception as exc:
                with self._lock:
                    self._stats["last_error"] = str(exc)
                logger.exception("realtime maint cycle failed")
            if self._stop.wait(self.settings.realtime_interval_sec):
                break
        try:
            self.run_once(final_flush=True)
        except Exception:
            logger.exception("realtime maint final flush failed")

    def run_once(self, *, final_flush: bool = False) -> Dict[str, Any]:
        flushed_ticks = self._flush_ticks()
        flushed_bars = self._flush_completed_bars(force=final_flush)
        resubscribed = self._resubscribe_stale()
        with self._lock:
            self._stats["ticks_persisted"] = int(self._stats.get("ticks_persisted") or 0) + flushed_ticks
            self._stats["bars_flushed"] = int(self._stats.get("bars_flushed") or 0) + flushed_bars
            self._stats["resubscribes"] = int(self._stats.get("resubscribes") or 0) + resubscribed
            self._stats["last_cycle_at"] = int(time.time())
            self._stats["last_error"] = ""
        return {
            "flushed_ticks": flushed_ticks,
            "flushed_bars": flushed_bars,
            "resubscribed": resubscribed,
        }

    def _flush_ticks(self) -> int:
        if not self.settings.persist_ticks:
            with self._lock:
                self._tick_buffer.clear()
            return 0
        batch: List[Dict[str, Any]] = []
        with self._lock:
            while self._tick_buffer and len(batch) < 1000:
                batch.append(self._tick_buffer.popleft())
        if not batch:
            return 0
        try:
            return repository.insert_ticks(batch)
        except Exception:
            # Put back on failure to avoid silent loss.
            with self._lock:
                for item in reversed(batch):
                    self._tick_buffer.appendleft(item)
            raise

    def _flush_completed_bars(self, *, force: bool = False) -> int:
        now = int(time.time())
        current_minute = align_bar_time(now, "1m")
        ready: List[Dict[str, Any]] = []
        with self._lock:
            for key, bar in list(self._open_bars.items()):
                if force or int(bar["time"]) < current_minute:
                    ready.append(bar)
                    self._open_bars.pop(key, None)
        written = 0
        by_symbol: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        for bar in ready:
            by_symbol[str(bar["symbol"])].append(bar)
        for symbol, bars in by_symbol.items():
            spec = WatchSpec(
                market="Futures",
                symbol=symbol,
                timeframe="1m",
                exchange_id="ctp",
                market_type="futures",
            )
            written += repository.upsert_bars(
                spec,
                bars,
                source="realtime_tick_agg",
                quality_flags=["tick_aggregate"],
            )
        return written

    def _resubscribe_stale(self) -> int:
        gateway = get_ctp_md_gateway()
        if not gateway.settings.enabled:
            return 0
        if not md_connection_open(
            list(gateway.status().get("pendingSubscribe") or [])
            + list(gateway.status().get("subscribed") or [])
        ):
            return 0
        stale_after = self.settings.tick_stale_after_sec
        now = time.time()
        stale: List[str] = []
        with self._lock:
            subscribed = list(gateway.status().get("subscribed") or [])
            pending = list(gateway.status().get("pendingSubscribe") or [])
            watched = unique_instruments(subscribed + pending)
            for symbol in watched:
                if not is_instrument_in_session(symbol):
                    continue
                last = self._last_tick.get(symbol)
                if not last:
                    stale.append(symbol)
                    continue
                age = now - (float(last.get("tick_time_ms") or 0) / 1000.0)
                if age > stale_after:
                    stale.append(symbol)
        if not stale:
            return 0
        gateway.subscribe(unique_instruments(stale))
        if gateway.settings.enabled and not gateway.running:
            gateway.start()
        logger.warning("Realtime maint resubscribed stale CTP symbols: %s", ",".join(stale))
        return len(stale)


_REALTIME: Optional[RealtimeMaintainer] = None
_REALTIME_LOCK = threading.Lock()


def get_realtime_maintainer() -> RealtimeMaintainer:
    global _REALTIME
    if _REALTIME is None:
        with _REALTIME_LOCK:
            if _REALTIME is None:
                _REALTIME = RealtimeMaintainer()
    return _REALTIME
