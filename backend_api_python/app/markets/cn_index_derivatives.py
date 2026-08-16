"""China Financial Futures Exchange (CFFEX) index futures / options helpers.

QuantDinger currently treats generic ``Futures`` as CME/crypto-style research
symbols. CFFEX equity-index products (IF/IH/IC/IM futures and IO/HO/MO options)
are **not** a supported market module or live-trading venue. These helpers exist
so callers can detect the codes, refuse unsafe fallbacks (e.g. routing ``IF`` to
Binance), and keep capability reports / regression tests consistent.
"""

from __future__ import annotations

import re

# Equity-index futures on CFFEX (沪深300 / 上证50 / 中证500 / 中证1000).
CFFEX_INDEX_FUTURE_ROOTS = frozenset({"IF", "IH", "IC", "IM"})

# Equity-index options on CFFEX (沪深300 / 上证50 / 中证1000).
CFFEX_INDEX_OPTION_ROOTS = frozenset({"IO", "HO", "MO"})

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

UNSUPPORTED_MESSAGE = (
    "CFFEX China equity-index futures/options "
    "(IF/IH/IC/IM, IO/HO/MO) are not supported in QuantDinger yet. "
    "No Options market module, no CTP/QMT broker, and Futures data covers "
    "CME/crypto symbols only."
)


def normalize_derivative_symbol(symbol: str) -> str:
    raw = str(symbol or "").strip().upper()
    if ":" in raw:
        raw = raw.split(":", 1)[-1]
    return raw.replace("=F", "").strip()


def is_cffex_index_future(symbol: str) -> bool:
    value = normalize_derivative_symbol(symbol)
    return _FUTURE_RE.fullmatch(value) is not None


def is_cffex_index_option(symbol: str) -> bool:
    value = normalize_derivative_symbol(symbol)
    if value in CFFEX_INDEX_OPTION_ROOTS:
        return True
    return _OPTION_RE.fullmatch(value) is not None


def is_cffex_index_derivative(symbol: str) -> bool:
    return is_cffex_index_future(symbol) or is_cffex_index_option(symbol)


def cffex_unsupported_error(symbol: str) -> ValueError:
    sym = normalize_derivative_symbol(symbol) or "?"
    return ValueError(f"{UNSUPPORTED_MESSAGE} Got symbol={sym!r}.")
