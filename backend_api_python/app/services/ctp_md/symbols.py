"""CN futures instrument id helpers for CTP MdApi."""

from __future__ import annotations

import re
from typing import Iterable, List, Optional

# SHFE/DCE/INE/GFEX usually: rb2505 / ag2506 / i2509 / sc2505
# CFFEX: IF2503 / IH2503 / IC2503 / IM2503 / T2506 / TF2506 / TS2506
# CZCE often arrives as TA505 / CF509 (3-digit YY+M or similar)
_CN_FUTURES_INSTRUMENT_RE = re.compile(r"^[A-Za-z]{1,2}\d{3,4}$")


def strip_market_prefix(symbol: str) -> str:
    text = str(symbol or "").strip()
    if ":" in text:
        # Futures:rb2505 or Futures:SHFE.rb2505
        text = text.split(":", 1)[1].strip()
    if "@" in text:
        text = text.split("@", 1)[0].strip()
    return text


def normalize_ctp_instrument(symbol: str) -> str:
    """Normalize a user/runtime symbol to a CTP InstrumentID candidate."""
    text = strip_market_prefix(symbol)
    if "." in text:
        # SHFE.rb2505 / DCE.i2509
        text = text.rsplit(".", 1)[-1].strip()
    # CTP InstrumentID is case-sensitive by exchange convention; keep product
    # letters as provided when mixed, but trim whitespace.
    return text.strip()


def instrument_aliases(symbol: str) -> List[str]:
    instrument = normalize_ctp_instrument(symbol)
    if not instrument:
        return []
    aliases = {
        instrument,
        instrument.lower(),
        instrument.upper(),
    }
    # CZCE contracts are frequently uppercase in CTP.
    if len(instrument) >= 2 and instrument[0].isalpha() and instrument[1].isalpha():
        aliases.add(instrument[:2].upper() + instrument[2:])
        aliases.add(instrument[:2].lower() + instrument[2:])
    elif instrument and instrument[0].isalpha():
        aliases.add(instrument[0].upper() + instrument[1:])
        aliases.add(instrument[0].lower() + instrument[1:])
    return [item for item in aliases if item]


def looks_like_cn_futures_instrument(symbol: str) -> bool:
    instrument = normalize_ctp_instrument(symbol)
    if not instrument or "/" in instrument or instrument.endswith("=F"):
        return False
    return bool(_CN_FUTURES_INSTRUMENT_RE.match(instrument))


def unique_instruments(symbols: Iterable[str]) -> List[str]:
    seen = set()
    out: List[str] = []
    for symbol in symbols:
        instrument = normalize_ctp_instrument(symbol)
        if not instrument:
            continue
        key = instrument.lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(instrument)
    return out


def resolve_store_key(symbol: str, available: Iterable[str]) -> Optional[str]:
    """Match a request symbol against cached InstrumentIDs."""
    wanted = {alias.lower() for alias in instrument_aliases(symbol)}
    if not wanted:
        return None
    for candidate in available:
        if str(candidate).lower() in wanted:
            return str(candidate)
    return None
