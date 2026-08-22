"""Fetch listed China option contracts from CTP (via AkShare)."""

from __future__ import annotations

import os
import re
from typing import Any, Dict, List, Optional

from app.markets.cn_options import (
    is_etf_option_code,
    normalize_ctp_option_row,
)
from app.utils.logger import get_logger

logger = get_logger(__name__)


def _include_etf() -> bool:
    return os.getenv("CN_OPTIONS_INCLUDE_ETF", "true").strip().lower() in {"1", "true", "yes", "on"}


def fetch_ctp_option_contract_frame():
    """Return the raw AkShare DataFrame of listed CTP option contracts."""
    try:
        import akshare as ak  # type: ignore
    except Exception as exc:  # pragma: no cover - environment without akshare
        raise RuntimeError(
            "akshare is required to list CTP option contracts "
            "(pip install akshare)."
        ) from exc
    return ak.option_contract_info_ctp()


def listed_option_catalog(frame: Any = None) -> List[Dict[str, Any]]:
    """Normalize CTP option rows into catalog dicts.

    Pass a DataFrame to keep unit tests offline. When ``frame`` is omitted the
    live AkShare CTP dump is fetched.
    """
    if frame is None:
        frame = fetch_ctp_option_contract_frame()
    if frame is None:
        return []
    include_etf = _include_etf()
    records: List[Dict[str, Any]] = []
    try:
        rows = frame.to_dict("records")
    except Exception:
        rows = list(frame)
    for row in rows:
        item = normalize_ctp_option_row(row)
        if not item:
            continue
        if item.get("kind") == "etf" and not include_etf:
            continue
        records.append(item)
    logger.info(
        "CTP option catalog listed=%s etf=%s",
        len(records),
        sum(1 for item in records if item.get("kind") == "etf"),
    )
    return records


def listed_etf_underlying_codes(records: Optional[List[Dict[str, Any]]] = None) -> List[str]:
    """Unique six-digit ETF codes referenced by listed SSE/SZSE ETF options."""
    rows = records if records is not None else listed_option_catalog()
    codes: List[str] = []
    seen = set()
    for item in rows:
        if item.get("kind") != "etf":
            continue
        code = str(item.get("underlying") or "").strip()
        if not re.fullmatch(r"\d{6}", code):
            continue
        if code in seen:
            continue
        seen.add(code)
        codes.append(code)
    return codes


def listed_etf_underlying_catalog(records: Optional[List[Dict[str, Any]]] = None) -> List[Dict[str, Any]]:
    """Catalog dicts for underlying ETFs (CNStock rows)."""
    from app.markets.cn_options import etf_underlying_display_name

    rows = records if records is not None else listed_option_catalog()
    out: List[Dict[str, Any]] = []
    seen = set()
    for item in rows:
        if item.get("kind") != "etf":
            continue
        code = str(item.get("underlying") or "").strip()
        if not re.fullmatch(r"\d{6}", code) or code in seen:
            continue
        seen.add(code)
        exchange = str(item.get("exchange") or "").upper()
        stock_exchange = "SZ" if exchange == "SZSE" or code.startswith(("15", "16")) else "CN"
        out.append(
            {
                "market": "CNStock",
                "symbol": code,
                "name": etf_underlying_display_name(code),
                "exchange": stock_exchange,
                "currency": "CNY",
                "market_type": "spot",
                "asset_class": "etf",
            }
        )
    return out


def catalog_stats(records: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
    rows = records if records is not None else listed_option_catalog()
    by_exchange: Dict[str, int] = {}
    by_market: Dict[str, int] = {}
    for item in rows:
        exchange = str(item.get("exchange") or "?").upper()
        market = str(item.get("market") or "?")
        by_exchange[exchange] = by_exchange.get(exchange, 0) + 1
        by_market[market] = by_market.get(market, 0) + 1
    return {
        "total": len(rows),
        "by_exchange": dict(sorted(by_exchange.items())),
        "by_market": dict(sorted(by_market.items())),
    }
