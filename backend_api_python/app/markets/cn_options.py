"""Chinese listed option contract parsing and CTP instrument formatting.

Futures-style options (CFFEX/SHFE/INE/DCE/CZCE/GFEX) use alphabetic roots plus
expiry and strike. SSE/SZSE ETF options use 8-digit numeric codes and are
catalogued under CNIndexOptions for search; they are not sent through CTP
commodity option order formatting.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

# CTP option_contract_info_ctp() column names (akshare 1.18.x).
CTP_COL_INSTRUMENT = "合约ID"
CTP_COL_NAME = "合约名称"
CTP_COL_EXCHANGE = "交易所代码"
CTP_COL_EXCHANGE_ALT = "交易所ID"
CTP_COL_PRODUCT = "品种ID"
CTP_COL_ASSET_CLASS = "商品类别"
CTP_COL_STATUS = "合约状态"
CTP_COL_UNDERLYING = "标的合约"
CTP_COL_UNDERLYING_ALT = "标的合约ID"
CTP_COL_STRIKE = "执行价"
CTP_COL_STRIKE_ALT = "行权价"
CTP_COL_CALL_PUT = "看涨看跌"
CTP_COL_CALL_PUT_ALT = "期权类型"
CTP_COL_MULTIPLE = "合约乘数"
CTP_COL_TICK = "最小变动价位"
CTP_COL_EXPIRE = "到期日"

CTP_STATUS_LISTED = 1

# Index-option-only roots map onto the corresponding index futures continuous.
INDEX_OPTION_UNDERLYING = {"IO": "IF", "HO": "IH", "MO": "IM"}

_OPTION_RE = re.compile(
    r"^([A-Za-z]{1,3})(\d{3,4})(?:-([CPcp])-|([CPcp]))(\d+(?:\.\d+)?)$"
)
_ETF_OPTION_RE = re.compile(r"^\d{8}$")


@dataclass(frozen=True, slots=True)
class ParsedCnOption:
    root: str
    month: str
    call_put: str
    strike: str
    exchange: str | None
    hyphenated: bool


def exchange_for_root(root: str) -> str | None:
    from app.markets.cn_futures import CN_FUTURE_PRODUCTS

    product = CN_FUTURE_PRODUCTS.get(str(root or "").strip().upper())
    return product.exchange if product else None


def is_etf_option_code(symbol: str) -> bool:
    return bool(_ETF_OPTION_RE.fullmatch((symbol or "").strip()))


def parse_cn_option_instrument(symbol: str) -> ParsedCnOption | None:
    """Parse a listed futures-style option instrument (any China futures exchange)."""
    raw = (symbol or "").strip().upper().replace(" ", "")
    if not raw or is_etf_option_code(raw):
        return None
    match = _OPTION_RE.fullmatch(raw)
    if not match:
        return None
    root, month, hyphen_cp, compact_cp, strike = match.groups()
    call_put = (hyphen_cp or compact_cp or "").upper()
    if call_put not in {"C", "P"}:
        return None
    return ParsedCnOption(
        root=root,
        month=month,
        call_put=call_put,
        strike=_format_strike(strike),
        exchange=exchange_for_root(root),
        hyphenated=hyphen_cp is not None,
    )


def is_cn_listed_option(symbol: str) -> bool:
    return parse_cn_option_instrument(symbol) is not None or is_etf_option_code(symbol)


def canonical_option_symbol(parsed: ParsedCnOption) -> str:
    return f"{parsed.root}{parsed.month}-{parsed.call_put}-{parsed.strike}"


def sina_option_symbol(parsed: ParsedCnOption) -> str:
    """AkShare option_commodity_hist_sina expects e.g. m2609C2800."""
    from app.markets.cn_futures import expand_cn_delivery_month

    month = expand_cn_delivery_month(parsed.month, exchange=parsed.exchange)
    return f"{parsed.root.lower()}{month}{parsed.call_put}{parsed.strike}"


def option_underlying_continuous(root: str) -> str:
    mapped = INDEX_OPTION_UNDERLYING.get(str(root or "").strip().upper(), str(root or "").strip().upper())
    return f"{mapped}0"


def format_ctp_option_instrument(
    *,
    root: str,
    month: str,
    call_put: str,
    strike: str | float | int,
    exchange: str | None = None,
) -> str:
    """Assemble the CTP instrument id for the given exchange."""
    cp = str(call_put).strip().upper()
    if cp not in {"C", "P"}:
        raise ValueError(f"call_put must be C or P, got {call_put!r}")
    month_s = str(month).strip()
    strike_s = _format_strike(strike)
    root_s = str(root).strip()
    exch = (exchange or exchange_for_root(root_s) or "").upper()
    if exch in {"DCE", "GFEX"}:
        return f"{root_s.lower()}{month_s}-{cp}-{strike_s}"
    if exch in {"CFFEX"}:
        return f"{root_s.upper()}{month_s}-{cp}-{strike_s}"
    if exch in {"CZCE"}:
        return f"{root_s.upper()}{month_s}{cp}{strike_s}"
    # SHFE / INE default to compact lowercase (also used when exchange unknown).
    return f"{root_s.lower()}{month_s}{cp}{strike_s}"


def format_ctp_option_instrument_from_symbol(symbol: str, exchange: str | None = None) -> str | None:
    parsed = parse_cn_option_instrument(symbol)
    if parsed is None:
        return None
    return format_ctp_option_instrument(
        root=parsed.root,
        month=parsed.month,
        call_put=parsed.call_put,
        strike=parsed.strike,
        exchange=exchange or parsed.exchange,
    )


def _format_strike(strike: str | float | int) -> str:
    if isinstance(strike, float):
        if strike == int(strike):
            return str(int(strike))
        return f"{strike:.10f}".rstrip("0").rstrip(".")
    text = str(strike).strip()
    if "." in text:
        return text.rstrip("0").rstrip(".")
    return text


def _row_get(row: Any, key: str) -> Any:
    if hasattr(row, "get"):
        return row.get(key)
    return getattr(row, key, None)


def _row_get_first(row: Any, *keys: str) -> Any:
    for key in keys:
        value = _row_get(row, key)
        if value is not None and str(value).strip() != "":
            return value
    return None


def _row_exchange(row: Any) -> str:
    return str(_row_get_first(row, CTP_COL_EXCHANGE, CTP_COL_EXCHANGE_ALT) or "").strip().upper()


def _row_underlying(row: Any) -> str:
    return str(_row_get_first(row, CTP_COL_UNDERLYING, CTP_COL_UNDERLYING_ALT) or "").strip()


# Mainland ETF option underlyings (SSE/SZSE six-digit codes).
KNOWN_ETF_UNDERLYINGS: dict[str, str] = {
    "510050": "SSE 50 ETF",
    "510300": "CSI 300 ETF",
    "510500": "CSI 500 ETF",
    "588000": "STAR 50 ETF",
    "588080": "STAR 50 ETF",
    "159901": "SZSE 100 ETF",
    "159915": "ChiNext ETF",
    "159919": "CSI 300 ETF",
    "159922": "CSI 500 ETF",
}

# ETF underlyings -> spot benchmark index (code, board, display name).
ETF_BENCHMARK_INDEX: dict[str, tuple[str, str, str]] = {
    "510050": ("000016", "SH", "SSE 50 Index"),
    "510300": ("000300", "SH", "CSI 300 Index"),
    "510500": ("000905", "SH", "CSI 500 Index"),
    "588000": ("000688", "SH", "STAR 50 Index"),
    "588080": ("000688", "SH", "STAR 50 Index"),
    "159901": ("399330", "SZ", "SZSE 100 Index"),
    "159915": ("399006", "SZ", "ChiNext Index"),
    "159919": ("399300", "SZ", "CSI 300 Index (SZ)"),
    "159922": ("399905", "SZ", "CSI 500 Index (SZ)"),
}


def etf_underlying_display_name(code: str) -> str:
    key = str(code or "").strip()
    return KNOWN_ETF_UNDERLYINGS.get(key, f"ETF {key}")


def cn_symbol_with_board(code: str, board: str) -> str:
    """Return canonical CN symbol with board suffix, e.g. ``000300.SH``."""
    raw = str(code or "").strip().upper()
    if not raw:
        return raw
    if "." in raw:
        return raw
    return f"{raw}.{str(board or '').strip().upper()}"


def infer_cn_etf_board(code: str) -> str:
    """Infer SSE/SZSE board for a six-digit ETF code."""
    key = str(code or "").strip()
    if key.startswith(("15", "16")):
        return "SZ"
    if key.startswith(("51", "56", "58")):
        return "SH"
    return "SH" if key.startswith("6") else "SZ"


def cn_etf_stock_symbol(etf_code: str) -> str:
    """Canonical CNStock symbol for an ETF underlying (``510050.SH``)."""
    code = str(etf_code or "").strip()
    if not code:
        return code
    if "." in code:
        return code.upper()
    return cn_symbol_with_board(code, infer_cn_etf_board(code))


def etf_benchmark_index(etf_code: str) -> tuple[str, str, str] | None:
    return ETF_BENCHMARK_INDEX.get(str(etf_code or "").strip())


def etf_benchmark_symbol(etf_code: str) -> str | None:
    item = etf_benchmark_index(etf_code)
    if not item:
        return None
    code, board, _name = item
    return cn_symbol_with_board(code, board)


def etf_benchmark_display_name(etf_code: str) -> str:
    item = etf_benchmark_index(etf_code)
    if item:
        return item[2]
    sym = etf_benchmark_symbol(etf_code)
    return f"Index {sym}" if sym else f"Index {etf_code}"


def _safe_int(value: Any) -> int:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return 0


def _safe_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def normalize_ctp_option_row(row: Any) -> dict[str, Any] | None:
    """Map one option_contract_info_ctp() row to a catalog dict, or None to skip."""
    instrument = str(_row_get(row, CTP_COL_INSTRUMENT) or "").strip()
    if not instrument:
        return None
    if _safe_int(_row_get(row, CTP_COL_STATUS)) != CTP_STATUS_LISTED:
        return None

    exchange = _row_exchange(row)
    name = str(_row_get(row, CTP_COL_NAME) or "").strip()
    product_id = str(_row_get(row, CTP_COL_PRODUCT) or "").strip()
    underlying = _row_underlying(row)

    if is_etf_option_code(instrument) or exchange in {"SSE", "SZSE"}:
        display = name or instrument
        if instrument and instrument not in display:
            display = f"{display} [{instrument}]"
        return {
            "market": "CNIndexOptions",
            "symbol": instrument,
            "name": display[:255],
            "instrument_id": instrument,
            "exchange": exchange or None,
            "currency": "CNY",
            "market_type": "options",
            "asset_class": "options",
            "tick_size": _safe_float(_row_get(row, CTP_COL_TICK)),
            "lot_size": _safe_float(_row_get(row, CTP_COL_MULTIPLE)) or 10000.0,
            "is_active": True,
            "kind": "etf",
            "product_id": product_id or "ETF_O",
            "underlying": underlying or None,
        }

    parsed = parse_cn_option_instrument(instrument)
    if parsed is None:
        return None

    from app.markets.cn_futures import CN_FUTURE_PRODUCTS

    market = "CNIndexOptions" if exchange == "CFFEX" or parsed.root in INDEX_OPTION_UNDERLYING else "CNFuturesOptions"
    symbol = canonical_option_symbol(parsed)
    cp_zh = "看涨" if parsed.call_put == "C" else "看跌"
    product = CN_FUTURE_PRODUCTS.get(parsed.root)
    display = name or f"{parsed.root} {parsed.month} {cp_zh} {parsed.strike}"
    extra_bits = [instrument, symbol]
    if product:
        extra_bits.append(product.name)
    for bit in extra_bits:
        if bit and bit not in display:
            display = f"{display} [{bit}]" if display else bit
    tick = _safe_float(_row_get(row, CTP_COL_TICK))
    lot = _safe_float(_row_get(row, CTP_COL_MULTIPLE))
    if tick is None and product is not None:
        tick = product.option_tick_size or product.tick_size
    if lot is None and product is not None:
        lot = float(product.option_multiplier or product.multiplier)
    return {
        "market": market,
        "symbol": symbol[:50],
        "name": display[:255],
        "instrument_id": instrument,
        "exchange": exchange or parsed.exchange,
        "currency": "CNY",
        "market_type": "options",
        "asset_class": "options",
        "tick_size": tick,
        "lot_size": lot,
        "is_active": True,
        "kind": "index" if market == "CNIndexOptions" else "commodity",
        "product_id": product_id,
        "underlying": underlying,
    }
