"""In-process CTP tick cache shared by REST and live price feeds."""

from __future__ import annotations

import threading
import time
from typing import Dict, Iterable, List, Optional

from app.services.ctp_md.models import CtpTick
from app.services.ctp_md.symbols import instrument_aliases, resolve_store_key


class CtpTickStore:
    """Thread-safe latest-tick map keyed by CTP InstrumentID."""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._ticks: Dict[str, CtpTick] = {}
        self._seen_at: Dict[str, float] = {}

    def put(self, tick: CtpTick) -> None:
        if tick is None or not tick.instrument_id:
            return
        with self._lock:
            self._ticks[tick.instrument_id] = tick
            self._seen_at[tick.instrument_id] = time.monotonic()

    def get(self, symbol: str, *, max_age_seconds: Optional[float] = None) -> Optional[CtpTick]:
        with self._lock:
            key = resolve_store_key(symbol, self._ticks.keys())
            if not key:
                return None
            if max_age_seconds is not None:
                age = time.monotonic() - float(self._seen_at.get(key) or 0.0)
                if age > max(0.0, float(max_age_seconds)):
                    return None
            return self._ticks.get(key)

    def prices_for(
        self,
        instruments: Iterable[dict],
        *,
        max_age_seconds: float = 10.0,
    ) -> Dict[str, float]:
        """Map runtime instrument keys -> last usable price."""
        max_age = max(0.5, float(max_age_seconds or 0.0))
        now = time.monotonic()
        out: Dict[str, float] = {}
        with self._lock:
            for item in instruments:
                runtime_key = str(item.get("key") or "")
                symbol = str(item.get("symbol") or "")
                if not runtime_key:
                    continue
                candidates = instrument_aliases(symbol) or instrument_aliases(runtime_key)
                matched = None
                for candidate in candidates:
                    store_key = resolve_store_key(candidate, self._ticks.keys())
                    if store_key:
                        matched = store_key
                        break
                if not matched:
                    continue
                age = now - float(self._seen_at.get(matched) or 0.0)
                if age > max_age:
                    continue
                tick = self._ticks.get(matched)
                price = float(tick.usable_price) if tick else 0.0
                if price > 0:
                    out[runtime_key] = price
        return out

    def list_latest(self, *, max_age_seconds: Optional[float] = None) -> List[CtpTick]:
        now = time.monotonic()
        with self._lock:
            rows: List[CtpTick] = []
            for key, tick in self._ticks.items():
                if max_age_seconds is not None:
                    age = now - float(self._seen_at.get(key) or 0.0)
                    if age > max(0.0, float(max_age_seconds)):
                        continue
                rows.append(tick)
            return rows

    def age_ms(self, symbol: str) -> int:
        with self._lock:
            key = resolve_store_key(symbol, self._ticks.keys())
            if not key:
                return -1
            return int(max(0.0, time.monotonic() - float(self._seen_at.get(key) or 0.0)) * 1000)


_STORE: Optional[CtpTickStore] = None
_STORE_LOCK = threading.Lock()


def get_ctp_tick_store() -> CtpTickStore:
    global _STORE
    if _STORE is None:
        with _STORE_LOCK:
            if _STORE is None:
                _STORE = CtpTickStore()
    return _STORE
