"""China Financial Futures Exchange (CFFEX) equity-index product helpers.

Covers:
  - Index futures: IF / IH / IC / IM
  - Index options: IO / HO / MO

Generic ``Futures`` in QuantDinger remains CME/crypto-style research symbols.
CFFEX products use dedicated market categories ``CNIndexFutures`` /
``CNIndexOptions`` plus CTP / QMT live channels.
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from typing import Any, Dict, Optional

# Equity-index futures on CFFEX (沪深300 / 上证50 / 中证500 / 中证1000).
CFFEX_INDEX_FUTURE_ROOTS = frozenset({"IF", "IH", "IC", "IM"})

# Equity-index options on CFFEX (沪深300 / 上证50 / 中证1000).
CFFEX_INDEX_OPTION_ROOTS = frozenset({"IO", "HO", "MO"})

CFFEX_MARKET_FUTURES = "CNIndexFutures"
CFFEX_MARKET_OPTIONS = "CNIndexOptions"
CFFEX_LIVE_CHANNELS = frozenset({"ctp", "qmt"})

# Continuity / front-month root, or root + YYMM contract month.
_FUTURE_RE = re.compile(
    r"^(?P<root>IF|IH|IC|IM)(?P<month>\d{4})?$",
    re.IGNORECASE,
)

# Common vendor notations: IO2509-C-4000, IO2509C4000, IO2509-P-4000.0
_OPTION_RE = re.compile(
    r"^(?P<root>IO|HO|MO)(?P<month>\d{4})"
    r"(?:[-_]?([CP])[-_]?(\d+(?:\.\d+)?))?$",
    re.IGNORECASE,
)

LEGACY_UNSUPPORTED_MESSAGE = (
    "CFFEX China equity-index futures/options "
    "(IF/IH/IC/IM, IO/HO/MO) must use market CNIndexFutures/CNIndexOptions "
    "with CTP/QMT channels — not generic Futures/Crypto routing."
)


@dataclass(frozen=True)
class CffexFutureContract:
    """Static contract specification for one CFFEX index-futures root."""

    root: str
    name: str
    underlying: str
    multiplier: int
    tick_size: float
    currency: str = "CNY"
    exchange: str = "CFFEX"
    # Approximate exchange margin rates (ratio of notional). Brokers may raise.
    long_margin_rate: float = 0.12
    short_margin_rate: float = 0.12
    # Commission model used by the in-process runtime (per lot).
    open_commission: float = 23.0
    close_commission: float = 23.0
    close_today_commission: float = 23.0

    @property
    def market_category(self) -> str:
        return CFFEX_MARKET_FUTURES

    def to_dict(self) -> Dict[str, Any]:
        payload = asdict(self)
        payload["market_category"] = self.market_category
        payload["product_type"] = "index_future"
        return payload


@dataclass(frozen=True)
class CffexOptionContract:
    """Static contract specification for one CFFEX index-options root."""

    root: str
    name: str
    underlying: str
    multiplier: int
    tick_size: float
    currency: str = "CNY"
    exchange: str = "CFFEX"
    # Seller (writer) margin is notional * rate; buyers pay premium only.
    seller_margin_rate: float = 0.12

    @property
    def market_category(self) -> str:
        return CFFEX_MARKET_OPTIONS

    def to_dict(self) -> Dict[str, Any]:
        payload = asdict(self)
        payload["market_category"] = self.market_category
        payload["product_type"] = "index_option"
        return payload


# Published CFFEX-style specs (multipliers / ticks). Margin rates are
# conservative defaults for runtime sizing — operators should override via
# exchange_config when broker rates differ.
CFFEX_FUTURE_SPECS: Dict[str, CffexFutureContract] = {
    "IF": CffexFutureContract(
        root="IF",
        name="CSI 300 Index Futures",
        underlying="000300.SH",
        multiplier=300,
        tick_size=0.2,
        long_margin_rate=0.12,
        short_margin_rate=0.12,
    ),
    "IH": CffexFutureContract(
        root="IH",
        name="SSE 50 Index Futures",
        underlying="000016.SH",
        multiplier=300,
        tick_size=0.2,
        long_margin_rate=0.12,
        short_margin_rate=0.12,
    ),
    "IC": CffexFutureContract(
        root="IC",
        name="CSI 500 Index Futures",
        underlying="000905.SH",
        multiplier=200,
        tick_size=0.2,
        long_margin_rate=0.14,
        short_margin_rate=0.14,
    ),
    "IM": CffexFutureContract(
        root="IM",
        name="CSI 1000 Index Futures",
        underlying="000852.SH",
        multiplier=200,
        tick_size=0.2,
        long_margin_rate=0.14,
        short_margin_rate=0.14,
    ),
}

CFFEX_OPTION_SPECS: Dict[str, CffexOptionContract] = {
    "IO": CffexOptionContract(
        root="IO",
        name="CSI 300 Index Options",
        underlying="000300.SH",
        multiplier=100,
        tick_size=0.2,
        seller_margin_rate=0.12,
    ),
    "HO": CffexOptionContract(
        root="HO",
        name="SSE 50 Index Options",
        underlying="000016.SH",
        multiplier=100,
        tick_size=0.2,
        seller_margin_rate=0.12,
    ),
    "MO": CffexOptionContract(
        root="MO",
        name="CSI 1000 Index Options",
        underlying="000852.SH",
        multiplier=100,
        tick_size=0.2,
        seller_margin_rate=0.14,
    ),
}


def normalize_derivative_symbol(symbol: str) -> str:
    raw = str(symbol or "").strip().upper()
    if ":" in raw:
        raw = raw.split(":", 1)[-1]
    return raw.replace("=F", "").strip()


def parse_future_symbol(symbol: str) -> Optional[Dict[str, str]]:
    value = normalize_derivative_symbol(symbol)
    match = _FUTURE_RE.fullmatch(value)
    if not match:
        return None
    root = match.group("root").upper()
    month = match.group("month") or ""
    return {
        "root": root,
        "month": month,
        "symbol": f"{root}{month}" if month else root,
        "instrument_id": f"{root}{month}" if month else root,
    }


def parse_option_symbol(symbol: str) -> Optional[Dict[str, Any]]:
    value = normalize_derivative_symbol(symbol)
    if value in CFFEX_INDEX_OPTION_ROOTS:
        return {
            "root": value,
            "month": "",
            "option_type": "",
            "strike": None,
            "symbol": value,
            "instrument_id": value,
        }
    match = _OPTION_RE.fullmatch(value)
    if not match:
        return None
    root = match.group("root").upper()
    month = match.group("month") or ""
    option_type = (match.group(3) or "").upper()
    strike_raw = match.group(4)
    strike = float(strike_raw) if strike_raw else None
    return {
        "root": root,
        "month": month,
        "option_type": option_type,
        "strike": strike,
        "symbol": value,
        "instrument_id": value,
    }


def is_cffex_index_future(symbol: str) -> bool:
    return parse_future_symbol(symbol) is not None


def is_cffex_index_option(symbol: str) -> bool:
    return parse_option_symbol(symbol) is not None


def is_cffex_index_derivative(symbol: str) -> bool:
    return is_cffex_index_future(symbol) or is_cffex_index_option(symbol)


def get_future_spec(symbol: str) -> CffexFutureContract:
    parsed = parse_future_symbol(symbol)
    if not parsed:
        raise ValueError(f"Not a CFFEX index futures symbol: {symbol!r}")
    return CFFEX_FUTURE_SPECS[parsed["root"]]


def get_option_spec(symbol: str) -> CffexOptionContract:
    parsed = parse_option_symbol(symbol)
    if not parsed:
        raise ValueError(f"Not a CFFEX index options symbol: {symbol!r}")
    return CFFEX_OPTION_SPECS[parsed["root"]]


def resolve_market_category(symbol: str) -> str:
    if is_cffex_index_future(symbol):
        return CFFEX_MARKET_FUTURES
    if is_cffex_index_option(symbol):
        return CFFEX_MARKET_OPTIONS
    return ""


def estimate_futures_margin(
    symbol: str,
    *,
    price: float,
    lots: float,
    direction: str = "long",
    margin_rate: Optional[float] = None,
) -> float:
    """Estimate initial margin for an index-futures open."""
    spec = get_future_spec(symbol)
    side = (direction or "long").strip().lower()
    rate = margin_rate
    if rate is None:
        rate = spec.short_margin_rate if side in ("short", "sell") else spec.long_margin_rate
    notional = abs(float(price)) * float(spec.multiplier) * abs(float(lots))
    return round(notional * float(rate), 2)


def cffex_misroute_error(symbol: str) -> ValueError:
    """Refuse unsafe fallback into CME/crypto Futures data paths."""
    sym = normalize_derivative_symbol(symbol) or "?"
    return ValueError(f"{LEGACY_UNSUPPORTED_MESSAGE} Got symbol={sym!r}.")


# Back-compat alias used by the capability-boundary tests / Futures guard.
cffex_unsupported_error = cffex_misroute_error
UNSUPPORTED_MESSAGE = LEGACY_UNSUPPORTED_MESSAGE
