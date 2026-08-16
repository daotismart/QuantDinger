"""Margin + open/close (今仓/昨仓) runtime for CFFEX index futures.

Chinese futures distinguish:
  - open vs close
  - close yesterday vs close today
  - long vs short position legs

This runtime is the shared ledger used by CTP / QMT simulation clients and
can also size live orders before they hit a gateway bridge.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

from app.markets.cn_index_derivatives import (
    estimate_futures_margin,
    get_future_spec,
    is_cffex_index_future,
    normalize_derivative_symbol,
)


class CffexRuntimeError(Exception):
    pass


class CffexOffsetFlag(str, Enum):
    OPEN = "open"
    CLOSE = "close"
    CLOSE_TODAY = "close_today"
    CLOSE_YESTERDAY = "close_yesterday"


class CffexPositionSide(str, Enum):
    LONG = "long"
    SHORT = "short"


def _norm_side(value: str) -> CffexPositionSide:
    raw = (value or "").strip().lower()
    if raw in ("long", "buy", "多"):
        return CffexPositionSide.LONG
    if raw in ("short", "sell", "空"):
        return CffexPositionSide.SHORT
    raise CffexRuntimeError(f"Unsupported position side: {value!r}")


def _norm_offset(value: str) -> CffexOffsetFlag:
    raw = (value or "").strip().lower().replace("-", "_")
    aliases = {
        "open": CffexOffsetFlag.OPEN,
        "kai": CffexOffsetFlag.OPEN,
        "close": CffexOffsetFlag.CLOSE,
        "ping": CffexOffsetFlag.CLOSE,
        "close_today": CffexOffsetFlag.CLOSE_TODAY,
        "closetoday": CffexOffsetFlag.CLOSE_TODAY,
        "close_yesterday": CffexOffsetFlag.CLOSE_YESTERDAY,
        "closeyesterday": CffexOffsetFlag.CLOSE_YESTERDAY,
        "close_yday": CffexOffsetFlag.CLOSE_YESTERDAY,
    }
    if raw not in aliases:
        raise CffexRuntimeError(f"Unsupported offset flag: {value!r}")
    return aliases[raw]


@dataclass
class PositionLeg:
    yesterday: float = 0.0
    today: float = 0.0
    avg_price: float = 0.0
    margin: float = 0.0

    @property
    def total(self) -> float:
        return float(self.yesterday) + float(self.today)


@dataclass
class SymbolBook:
    long: PositionLeg = field(default_factory=PositionLeg)
    short: PositionLeg = field(default_factory=PositionLeg)


@dataclass
class OrderFill:
    order_id: str
    symbol: str
    side: str
    offset: str
    lots: float
    price: float
    margin_delta: float
    commission: float
    realized_pnl: float
    raw: Dict[str, Any] = field(default_factory=dict)


class CffexRuntime:
    """In-process CFFEX futures ledger with 今/昨仓 semantics."""

    def __init__(
        self,
        *,
        cash: float = 1_000_000.0,
        currency: str = "CNY",
        account_id: str = "SIM-CFFEX",
    ):
        self.cash = float(cash)
        self.currency = currency
        self.account_id = account_id
        self.books: Dict[str, SymbolBook] = {}
        self.fills: List[OrderFill] = []
        self._order_seq = 0

    def _book(self, symbol: str) -> SymbolBook:
        key = normalize_derivative_symbol(symbol)
        if key not in self.books:
            self.books[key] = SymbolBook()
        return self.books[key]

    def _next_order_id(self) -> str:
        self._order_seq += 1
        return f"CFFEX-{self._order_seq}-{uuid.uuid4().hex[:8]}"

    def snapshot(self) -> Dict[str, Any]:
        positions: List[Dict[str, Any]] = []
        used_margin = 0.0
        for symbol, book in self.books.items():
            for side_name, leg in (("long", book.long), ("short", book.short)):
                if leg.total <= 0:
                    continue
                used_margin += float(leg.margin)
                positions.append(
                    {
                        "symbol": symbol,
                        "side": side_name,
                        "yesterday": leg.yesterday,
                        "today": leg.today,
                        "volume": leg.total,
                        "avg_price": leg.avg_price,
                        "margin": leg.margin,
                    }
                )
        return {
            "account_id": self.account_id,
            "currency": self.currency,
            "cash": round(self.cash, 2),
            "used_margin": round(used_margin, 2),
            "available": round(self.cash - used_margin, 2),
            "positions": positions,
            "fills": [fill.__dict__ for fill in self.fills[-50:]],
        }

    def roll_day(self) -> None:
        """Move today lots into yesterday (session rollover)."""
        for book in self.books.values():
            for leg in (book.long, book.short):
                leg.yesterday += leg.today
                leg.today = 0.0

    def estimate_open_margin(self, symbol: str, price: float, lots: float, side: str) -> float:
        return estimate_futures_margin(symbol, price=price, lots=lots, direction=side)

    def place_order(
        self,
        *,
        symbol: str,
        side: str,
        offset: str,
        lots: float,
        price: float,
    ) -> OrderFill:
        if not is_cffex_index_future(symbol):
            raise CffexRuntimeError(
                f"CffexRuntime currently supports index futures only, got {symbol!r}"
            )
        qty = abs(float(lots))
        px = float(price)
        if qty <= 0 or px <= 0:
            raise CffexRuntimeError("lots and price must be positive")

        pos_side = _norm_side(side)
        offset_flag = _norm_offset(offset)
        sym = normalize_derivative_symbol(symbol)
        spec = get_future_spec(sym)
        book = self._book(sym)

        if offset_flag == CffexOffsetFlag.OPEN:
            return self._open(sym, book, pos_side, qty, px, spec)
        return self._close(sym, book, pos_side, qty, px, spec, offset_flag)

    def _commission(self, spec: Any, offset_flag: CffexOffsetFlag, lots: float) -> float:
        if offset_flag == CffexOffsetFlag.CLOSE_TODAY:
            unit = float(spec.close_today_commission)
        elif offset_flag in (CffexOffsetFlag.CLOSE, CffexOffsetFlag.CLOSE_YESTERDAY):
            unit = float(spec.close_commission)
        else:
            unit = float(spec.open_commission)
        return round(unit * abs(lots), 2)

    def _open(
        self,
        symbol: str,
        book: SymbolBook,
        side: CffexPositionSide,
        lots: float,
        price: float,
        spec: Any,
    ) -> OrderFill:
        margin = estimate_futures_margin(symbol, price=price, lots=lots, direction=side.value)
        used = sum(leg.margin for b in self.books.values() for leg in (b.long, b.short))
        available = self.cash - used
        commission = self._commission(spec, CffexOffsetFlag.OPEN, lots)
        if margin + commission > available + 1e-9:
            raise CffexRuntimeError(
                f"Insufficient margin: need {margin + commission:.2f}, available {available:.2f}"
            )

        leg = book.long if side == CffexPositionSide.LONG else book.short
        new_total = leg.total + lots
        leg.avg_price = (
            price if leg.total <= 0 else ((leg.avg_price * leg.total) + (price * lots)) / new_total
        )
        leg.today += lots
        leg.margin += margin
        self.cash -= commission

        fill = OrderFill(
            order_id=self._next_order_id(),
            symbol=symbol,
            side=side.value,
            offset=CffexOffsetFlag.OPEN.value,
            lots=lots,
            price=price,
            margin_delta=margin,
            commission=commission,
            realized_pnl=0.0,
            raw={"ts": int(time.time()), "multiplier": spec.multiplier},
        )
        self.fills.append(fill)
        return fill

    def _close(
        self,
        symbol: str,
        book: SymbolBook,
        side: CffexPositionSide,
        lots: float,
        price: float,
        spec: Any,
        offset_flag: CffexOffsetFlag,
    ) -> OrderFill:
        # Closing a long position uses sell; closing short uses buy.
        # ``side`` here is the position side being reduced.
        leg = book.long if side == CffexPositionSide.LONG else book.short
        if leg.total + 1e-12 < lots:
            raise CffexRuntimeError(
                f"Cannot close {lots} lots on {symbol} {side.value}; open={leg.total}"
            )

        yesterday_use = 0.0
        today_use = 0.0
        if offset_flag == CffexOffsetFlag.CLOSE_TODAY:
            if leg.today + 1e-12 < lots:
                raise CffexRuntimeError(
                    f"Cannot close_today {lots} lots; today={leg.today}"
                )
            today_use = lots
        elif offset_flag == CffexOffsetFlag.CLOSE_YESTERDAY:
            if leg.yesterday + 1e-12 < lots:
                raise CffexRuntimeError(
                    f"Cannot close_yesterday {lots} lots; yesterday={leg.yesterday}"
                )
            yesterday_use = lots
        else:
            # Default CLOSE: prefer yesterday lots first (common CTP behaviour).
            yesterday_use = min(leg.yesterday, lots)
            today_use = lots - yesterday_use
            if today_use > leg.today + 1e-12:
                raise CffexRuntimeError("Not enough position to close")
            offset_flag = (
                CffexOffsetFlag.CLOSE_YESTERDAY
                if today_use <= 0
                else (
                    CffexOffsetFlag.CLOSE_TODAY
                    if yesterday_use <= 0
                    else CffexOffsetFlag.CLOSE
                )
            )

        prev_total = leg.total
        margin_release = 0.0 if prev_total <= 0 else leg.margin * (lots / prev_total)
        if side == CffexPositionSide.LONG:
            realized = (price - leg.avg_price) * spec.multiplier * lots
        else:
            realized = (leg.avg_price - price) * spec.multiplier * lots
        commission = self._commission(spec, offset_flag, lots)

        leg.yesterday -= yesterday_use
        leg.today -= today_use
        leg.margin = max(0.0, leg.margin - margin_release)
        if leg.total <= 1e-12:
            leg.yesterday = 0.0
            leg.today = 0.0
            leg.avg_price = 0.0
            leg.margin = 0.0

        self.cash += realized - commission

        fill = OrderFill(
            order_id=self._next_order_id(),
            symbol=symbol,
            side=side.value,
            offset=offset_flag.value,
            lots=lots,
            price=price,
            margin_delta=-margin_release,
            commission=commission,
            realized_pnl=round(realized, 2),
            raw={
                "ts": int(time.time()),
                "closed_yesterday": yesterday_use,
                "closed_today": today_use,
                "multiplier": spec.multiplier,
            },
        )
        self.fills.append(fill)
        return fill
