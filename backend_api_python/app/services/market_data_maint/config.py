"""Market data maintenance configuration."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import List


def _bool(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return str(raw).strip().lower() in ("1", "true", "yes", "on")


def _int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except Exception:
        return default


def _float(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, str(default)))
    except Exception:
        return default


@dataclass(frozen=True)
class WatchSpec:
    market: str
    symbol: str
    timeframe: str = "1m"
    exchange_id: str = ""
    market_type: str = ""
    lookback_bars: int = 1500

    def key(self) -> str:
        base = f"{self.market}:{self.symbol}:{self.timeframe}"
        if self.exchange_id or self.market_type:
            return f"{base}@{self.exchange_id}:{self.market_type}"
        return base


def parse_watch_csv(raw: str, *, default_market: str = "Futures", default_tf: str = "1m") -> List[WatchSpec]:
    """Parse ``Market:symbol:tf[@exchange:type]`` CSV entries."""
    out: List[WatchSpec] = []
    for part in str(raw or "").replace(";", ",").split(","):
        item = part.strip()
        if not item:
            continue
        exchange_id = ""
        market_type = ""
        if "@" in item:
            item, suffix = item.split("@", 1)
            bits = suffix.split(":", 1)
            exchange_id = bits[0].strip()
            market_type = bits[1].strip() if len(bits) > 1 else ""
        pieces = [p.strip() for p in item.split(":") if p.strip()]
        if len(pieces) == 1:
            market, symbol, timeframe = default_market, pieces[0], default_tf
        elif len(pieces) == 2:
            # Futures:rb2505 OR rb2505:1m
            if pieces[0] in {"Crypto", "Futures", "USStock", "CNStock", "HKStock", "Forex", "MOEX"}:
                market, symbol, timeframe = pieces[0], pieces[1], default_tf
            else:
                market, symbol, timeframe = default_market, pieces[0], pieces[1]
        else:
            market, symbol, timeframe = pieces[0], pieces[1], pieces[2]
        out.append(
            WatchSpec(
                market=market,
                symbol=symbol,
                timeframe=timeframe or default_tf,
                exchange_id=exchange_id,
                market_type=market_type,
                lookback_bars=_int("MARKET_DATA_MAINT_LOOKBACK_BARS", 1500),
            )
        )
    return out


@dataclass(frozen=True)
class MarketDataMaintSettings:
    enabled: bool
    realtime_enabled: bool
    historical_enabled: bool
    realtime_interval_sec: float
    historical_interval_sec: int
    tick_stale_after_sec: float
    tick_retention_days: int
    bar_retention_days: int
    max_gap_bars: int
    session_gap_seconds: int
    price_spike_ratio: float
    watchlist_csv: str
    persist_ticks: bool

    @classmethod
    def load(cls) -> "MarketDataMaintSettings":
        return cls(
            enabled=_bool("MARKET_DATA_MAINT_ENABLED", False),
            realtime_enabled=_bool("MARKET_DATA_MAINT_REALTIME_ENABLED", True),
            historical_enabled=_bool("MARKET_DATA_MAINT_HISTORICAL_ENABLED", True),
            realtime_interval_sec=max(1.0, _float("MARKET_DATA_MAINT_REALTIME_INTERVAL_SEC", 5.0)),
            historical_interval_sec=max(60, _int("MARKET_DATA_MAINT_HISTORICAL_INTERVAL_SEC", 300)),
            tick_stale_after_sec=max(1.0, _float("MARKET_DATA_MAINT_TICK_STALE_AFTER_SEC", 15.0)),
            tick_retention_days=max(1, _int("MARKET_DATA_MAINT_TICK_RETENTION_DAYS", 7)),
            bar_retention_days=max(7, _int("MARKET_DATA_MAINT_BAR_RETENTION_DAYS", 365)),
            max_gap_bars=max(1, _int("MARKET_DATA_MAINT_MAX_GAP_BARS", 500)),
            session_gap_seconds=max(3600, _int("MARKET_DATA_MAINT_SESSION_GAP_SECONDS", 15 * 3600)),
            price_spike_ratio=max(1.01, _float("MARKET_DATA_MAINT_PRICE_SPIKE_RATIO", 1.15)),
            watchlist_csv=str(os.getenv("MARKET_DATA_MAINT_WATCHLIST", "") or "").strip(),
            persist_ticks=_bool("MARKET_DATA_MAINT_PERSIST_TICKS", True),
        )
