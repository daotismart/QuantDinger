"""Normalized CTP depth-market (tick) payloads."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, Optional


@dataclass(frozen=True)
class CtpTick:
    """One CTP ``OnRtnDepthMarketData`` update.

    CTP market data is push-based depth/last updates (commonly called ticks
    in CN futures). Fields follow the CTP depth-market structure and are
    normalized to plain Python types for caching and REST responses.
    """

    instrument_id: str
    exchange_id: str = ""
    last_price: float = 0.0
    volume: int = 0
    turnover: float = 0.0
    open_interest: float = 0.0
    bid_price1: float = 0.0
    bid_volume1: int = 0
    ask_price1: float = 0.0
    ask_volume1: int = 0
    open_price: float = 0.0
    high_price: float = 0.0
    low_price: float = 0.0
    pre_close_price: float = 0.0
    pre_settlement_price: float = 0.0
    upper_limit_price: float = 0.0
    lower_limit_price: float = 0.0
    trading_day: str = ""
    action_day: str = ""
    update_time: str = ""
    update_millisec: int = 0
    received_at_ms: int = 0
    raw: Dict[str, Any] = field(default_factory=dict)

    @property
    def usable_price(self) -> float:
        for value in (self.last_price, self.bid_price1, self.ask_price1):
            try:
                price = float(value or 0.0)
            except (TypeError, ValueError):
                continue
            if price > 0:
                return price
        return 0.0

    def to_dict(self) -> Dict[str, Any]:
        payload = asdict(self)
        payload["price"] = self.usable_price
        return payload

    def to_ticker(self) -> Dict[str, Any]:
        last = self.usable_price
        prev = float(self.pre_close_price or self.pre_settlement_price or 0.0)
        change = round(last - prev, 6) if last > 0 and prev > 0 else 0.0
        change_pct = round(change / prev * 100.0, 4) if prev > 0 else 0.0
        return {
            "symbol": self.instrument_id,
            "last": last,
            "bid": float(self.bid_price1 or 0.0),
            "ask": float(self.ask_price1 or 0.0),
            "high": float(self.high_price or 0.0),
            "low": float(self.low_price or 0.0),
            "open": float(self.open_price or 0.0),
            "previousClose": prev,
            "change": change,
            "changePercent": change_pct,
            "percentage": change_pct,
            "volume": int(self.volume or 0),
            "openInterest": float(self.open_interest or 0.0),
            "source": "ctp_tick",
            "exchangeId": self.exchange_id,
            "updateTime": self.update_time,
            "updateMillisec": int(self.update_millisec or 0),
            "tradingDay": self.trading_day,
            "actionDay": self.action_day,
        }


def _safe_float(value: Any) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return 0.0
    # CTP uses DBL_MAX sentinels for empty optional doubles.
    if number != number or abs(number) > 1e15:
        return 0.0
    return number


def _safe_int(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def tick_from_depth_market_data(payload: Any, *, received_at_ms: int = 0) -> Optional[CtpTick]:
    """Build a :class:`CtpTick` from a CTP depth-market object or mapping."""
    if payload is None:
        return None
    getter = payload.get if isinstance(payload, dict) else lambda key, default="": getattr(payload, key, default)

    instrument_id = str(getter("InstrumentID", "") or "").strip()
    if not instrument_id:
        return None

    raw = {
        key: getter(key, "")
        for key in (
            "InstrumentID",
            "ExchangeID",
            "LastPrice",
            "Volume",
            "Turnover",
            "OpenInterest",
            "BidPrice1",
            "BidVolume1",
            "AskPrice1",
            "AskVolume1",
            "OpenPrice",
            "HighestPrice",
            "LowestPrice",
            "PreClosePrice",
            "PreSettlementPrice",
            "UpperLimitPrice",
            "LowerLimitPrice",
            "TradingDay",
            "ActionDay",
            "UpdateTime",
            "UpdateMillisec",
        )
    }
    return CtpTick(
        instrument_id=instrument_id,
        exchange_id=str(getter("ExchangeID", "") or "").strip().upper(),
        last_price=_safe_float(getter("LastPrice", 0)),
        volume=_safe_int(getter("Volume", 0)),
        turnover=_safe_float(getter("Turnover", 0)),
        open_interest=_safe_float(getter("OpenInterest", 0)),
        bid_price1=_safe_float(getter("BidPrice1", 0)),
        bid_volume1=_safe_int(getter("BidVolume1", 0)),
        ask_price1=_safe_float(getter("AskPrice1", 0)),
        ask_volume1=_safe_int(getter("AskVolume1", 0)),
        open_price=_safe_float(getter("OpenPrice", 0)),
        high_price=_safe_float(getter("HighestPrice", 0)),
        low_price=_safe_float(getter("LowestPrice", 0)),
        pre_close_price=_safe_float(getter("PreClosePrice", 0)),
        pre_settlement_price=_safe_float(getter("PreSettlementPrice", 0)),
        upper_limit_price=_safe_float(getter("UpperLimitPrice", 0)),
        lower_limit_price=_safe_float(getter("LowerLimitPrice", 0)),
        trading_day=str(getter("TradingDay", "") or "").strip(),
        action_day=str(getter("ActionDay", "") or "").strip(),
        update_time=str(getter("UpdateTime", "") or "").strip(),
        update_millisec=_safe_int(getter("UpdateMillisec", 0)),
        received_at_ms=int(received_at_ms or 0),
        raw=raw,
    )
