"""Backward-compatible CFFEX index helpers.

New code should prefer ``app.markets.cn_futures``. This module keeps the
previous public names used by tests and call sites.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from app.markets.cn_futures import (
    CN_FUTURE_PRODUCTS,
    CN_INDEX_FUTURES_MARKET as CFFEX_MARKET_FUTURES,
    CN_INDEX_OPTIONS_MARKET as CFFEX_MARKET_OPTIONS,
    CN_FUTURES_LIVE_CHANNELS as CFFEX_LIVE_CHANNELS,
    MISROUTE_MESSAGE as LEGACY_UNSUPPORTED_MESSAGE,
    CnFutureProduct,
    cn_misroute_error,
    estimate_futures_margin,
    get_future_product,
    is_cn_derivative,
    is_cn_future,
    is_cn_futures_option,
    normalize_cn_symbol,
    parse_cn_future_symbol,
    parse_cn_option_symbol,
    resolve_market_category,
)

CFFEX_INDEX_FUTURE_ROOTS = frozenset({"IF", "IH", "IC", "IM"})
CFFEX_INDEX_OPTION_ROOTS = frozenset({"IO", "HO", "MO"})
UNSUPPORTED_MESSAGE = LEGACY_UNSUPPORTED_MESSAGE


# Legacy dataclass aliases -------------------------------------------------


class CffexFutureContract(CnFutureProduct):
    """Compatibility alias — fields match CnFutureProduct."""


class CffexOptionContract:
    def __init__(self, product: CnFutureProduct):
        self._product = product

    @property
    def root(self) -> str:
        return self._product.root

    @property
    def name(self) -> str:
        return self._product.name

    @property
    def underlying(self) -> str:
        return {
            "IO": "000300.SH",
            "HO": "000016.SH",
            "MO": "000852.SH",
            "IF": "000300.SH",
            "IH": "000016.SH",
            "IC": "000905.SH",
            "IM": "000852.SH",
        }.get(self._product.root, "")

    @property
    def multiplier(self) -> float:
        return float(self._product.option_multiplier or self._product.multiplier)

    @property
    def tick_size(self) -> float:
        return float(self._product.option_tick_size or self._product.tick_size)

    @property
    def currency(self) -> str:
        return self._product.currency

    @property
    def exchange(self) -> str:
        return self._product.exchange

    @property
    def seller_margin_rate(self) -> float:
        return self._product.option_seller_margin_rate

    @property
    def market_category(self) -> str:
        return CFFEX_MARKET_OPTIONS

    def to_dict(self) -> Dict[str, Any]:
        return {
            "root": self.root,
            "name": self.name,
            "underlying": self.underlying,
            "multiplier": self.multiplier,
            "tick_size": self.tick_size,
            "currency": self.currency,
            "exchange": self.exchange,
            "seller_margin_rate": self.seller_margin_rate,
            "market_category": self.market_category,
            "product_type": "index_option",
        }


CFFEX_FUTURE_SPECS = {
    root: CN_FUTURE_PRODUCTS[root]
    for root in CFFEX_INDEX_FUTURE_ROOTS
}
CFFEX_OPTION_SPECS = {
    root: CffexOptionContract(CN_FUTURE_PRODUCTS[root])
    for root in CFFEX_INDEX_OPTION_ROOTS
}


def normalize_derivative_symbol(symbol: str) -> str:
    return normalize_cn_symbol(symbol)


def parse_future_symbol(symbol: str) -> Optional[Dict[str, str]]:
    parsed = parse_cn_future_symbol(symbol)
    if not parsed or parsed["root"] not in CFFEX_INDEX_FUTURE_ROOTS:
        return None
    return parsed


def parse_option_symbol(symbol: str) -> Optional[Dict[str, Any]]:
    parsed = parse_cn_option_symbol(symbol)
    if not parsed or parsed["root"] not in CFFEX_INDEX_OPTION_ROOTS:
        return None
    return parsed


def is_cffex_index_future(symbol: str) -> bool:
    parsed = parse_cn_future_symbol(symbol)
    return bool(parsed and parsed["root"] in CFFEX_INDEX_FUTURE_ROOTS)


def is_cffex_index_option(symbol: str) -> bool:
    parsed = parse_cn_option_symbol(symbol)
    return bool(parsed and parsed["root"] in CFFEX_INDEX_OPTION_ROOTS)


def is_cffex_index_derivative(symbol: str) -> bool:
    return is_cffex_index_future(symbol) or is_cffex_index_option(symbol)


def get_future_spec(symbol: str) -> CnFutureProduct:
    product = get_future_product(symbol)
    if product.root not in CFFEX_INDEX_FUTURE_ROOTS:
        raise ValueError(f"Not a CFFEX index futures symbol: {symbol!r}")
    return product


def get_option_spec(symbol: str) -> CffexOptionContract:
    parsed = parse_option_symbol(symbol)
    if not parsed:
        raise ValueError(f"Not a CFFEX index options symbol: {symbol!r}")
    return CFFEX_OPTION_SPECS[parsed["root"]]


def cffex_misroute_error(symbol: str) -> ValueError:
    return cn_misroute_error(symbol)


cffex_unsupported_error = cffex_misroute_error

__all__ = [
    "CFFEX_INDEX_FUTURE_ROOTS",
    "CFFEX_INDEX_OPTION_ROOTS",
    "CFFEX_MARKET_FUTURES",
    "CFFEX_MARKET_OPTIONS",
    "CFFEX_LIVE_CHANNELS",
    "CFFEX_FUTURE_SPECS",
    "CFFEX_OPTION_SPECS",
    "UNSUPPORTED_MESSAGE",
    "CffexFutureContract",
    "CffexOptionContract",
    "normalize_derivative_symbol",
    "parse_future_symbol",
    "parse_option_symbol",
    "is_cffex_index_future",
    "is_cffex_index_option",
    "is_cffex_index_derivative",
    "get_future_spec",
    "get_option_spec",
    "estimate_futures_margin",
    "resolve_market_category",
    "cffex_misroute_error",
    "cffex_unsupported_error",
    "is_cn_derivative",
    "is_cn_future",
    "is_cn_futures_option",
]
