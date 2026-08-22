"""Mainland China futures & futures-options product catalog.

Covers the six futures exchanges:
  CFFEX / SHFE / DCE / CZCE / INE / GFEX

Market categories:
  - ``CNFutures``         — all commodity & financial futures (live-capable)
  - ``CNFuturesOptions``  — futures options on those underlyings (live-capable)
  - ``CNIndexFutures`` / ``CNIndexOptions`` remain as CFFEX index aliases

Generic QuantDinger ``Futures`` stays CME/crypto research-only.
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any, Dict, Iterable, List, Optional, Tuple

CN_FUTURES_MARKET = "CNFutures"
CN_FUTURES_OPTIONS_MARKET = "CNFuturesOptions"
CN_INDEX_FUTURES_MARKET = "CNIndexFutures"
CN_INDEX_OPTIONS_MARKET = "CNIndexOptions"

CN_FUTURES_LIVE_CHANNELS = frozenset({"ctp", "qmt"})
CN_FUTURES_EXCHANGES = frozenset({"CFFEX", "SHFE", "DCE", "CZCE", "INE", "GFEX"})
CZCE_EXCHANGES = frozenset({"CZCE", "ZCE"})
# Main-continuous / weighted / next-main sentinels used by Sina and CTP.
CONTINUOUS_MONTH_CODES = frozenset({"", "0", "888", "999"})

MISROUTE_MESSAGE = (
    "Mainland China futures/options must use market CNFutures/CNFuturesOptions "
    "(or CNIndexFutures/CNIndexOptions) with CTP/QMT channels — "
    "not generic Futures/Crypto routing."
)


@dataclass(frozen=True)
class CnFutureProduct:
    """Static specification for one futures product root."""

    root: str
    name: str
    exchange: str
    multiplier: float
    tick_size: float
    currency: str = "CNY"
    product_class: str = "commodity"  # commodity | financial | index
    long_margin_rate: float = 0.10
    short_margin_rate: float = 0.10
    open_commission: float = 5.0
    close_commission: float = 5.0
    close_today_commission: float = 5.0
    has_options: bool = False
    option_multiplier: Optional[float] = None
    option_tick_size: Optional[float] = None
    option_seller_margin_rate: float = 0.12
    night_session: bool = False
    base_price: float = 0.0  # compliance simulator seed

    @property
    def market_category(self) -> str:
        if self.product_class == "index":
            return CN_INDEX_FUTURES_MARKET
        return CN_FUTURES_MARKET

    def to_dict(self) -> Dict[str, Any]:
        payload = asdict(self)
        payload["market_category"] = self.market_category
        payload["product_type"] = "future"
        return payload


def _p(
    root: str,
    name: str,
    exchange: str,
    multiplier: float,
    tick_size: float,
    *,
    product_class: str = "commodity",
    margin: float = 0.10,
    open_fee: float = 5.0,
    close_fee: float = 5.0,
    close_today_fee: float = 5.0,
    has_options: bool = False,
    option_mult: Optional[float] = None,
    option_tick: Optional[float] = None,
    option_margin: float = 0.12,
    night: bool = False,
    base_price: float = 0.0,
) -> CnFutureProduct:
    return CnFutureProduct(
        root=root.upper(),
        name=name,
        exchange=exchange,
        multiplier=float(multiplier),
        tick_size=float(tick_size),
        product_class=product_class,
        long_margin_rate=margin,
        short_margin_rate=margin,
        open_commission=open_fee,
        close_commission=close_fee,
        close_today_commission=close_today_fee,
        has_options=has_options,
        option_multiplier=option_mult if option_mult is not None else (float(multiplier) if has_options else None),
        option_tick_size=option_tick if option_tick is not None else (float(tick_size) if has_options else None),
        option_seller_margin_rate=option_margin,
        night_session=night,
        base_price=float(base_price),
    )


# Synthetic product for SSE/SZSE ETF listed options (not in the futures catalog).
_ETF_OPTIONS_PRODUCT = _p(
    "ETFO",
    "China ETF Options",
    "SSE",
    10000,
    0.0001,
    product_class="index",
    has_options=True,
    base_price=0.35,
)

# Approximate published-style specs for mainstream products. Brokers may raise
# margins; operators can override via exchange_config at order time.
_PRODUCTS: Tuple[CnFutureProduct, ...] = (
    # ----- CFFEX equity-index / treasury -----
    _p("IF", "CSI 300 Index Futures", "CFFEX", 300, 0.2, product_class="index", margin=0.12, open_fee=23, close_fee=23, close_today_fee=23, has_options=False, base_price=3800),
    _p("IH", "SSE 50 Index Futures", "CFFEX", 300, 0.2, product_class="index", margin=0.12, open_fee=23, close_fee=23, close_today_fee=23, base_price=2600),
    _p("IC", "CSI 500 Index Futures", "CFFEX", 200, 0.2, product_class="index", margin=0.14, open_fee=23, close_fee=23, close_today_fee=23, base_price=5600),
    _p("IM", "CSI 1000 Index Futures", "CFFEX", 200, 0.2, product_class="index", margin=0.14, open_fee=23, close_fee=23, close_today_fee=23, base_price=5800),
    _p("IO", "CSI 300 Index Options", "CFFEX", 100, 0.2, product_class="index", margin=0.12, has_options=True, option_mult=100, option_tick=0.2, base_price=3800),
    _p("HO", "SSE 50 Index Options", "CFFEX", 100, 0.2, product_class="index", margin=0.12, has_options=True, option_mult=100, option_tick=0.2, base_price=2600),
    _p("MO", "CSI 1000 Index Options", "CFFEX", 100, 0.2, product_class="index", margin=0.14, has_options=True, option_mult=100, option_tick=0.2, base_price=5800),
    _p("T", "10Y Treasury Futures", "CFFEX", 10000, 0.005, product_class="financial", margin=0.02, open_fee=3, close_fee=3, close_today_fee=3, base_price=102),
    _p("TF", "5Y Treasury Futures", "CFFEX", 10000, 0.005, product_class="financial", margin=0.012, open_fee=3, close_fee=3, close_today_fee=3, base_price=102),
    _p("TS", "2Y Treasury Futures", "CFFEX", 20000, 0.005, product_class="financial", margin=0.005, open_fee=3, close_fee=3, close_today_fee=3, base_price=101),
    _p("TL", "30Y Treasury Futures", "CFFEX", 10000, 0.01, product_class="financial", margin=0.035, open_fee=3, close_fee=3, close_today_fee=3, base_price=100),
    # ----- SHFE -----
    _p("CU", "Copper", "SHFE", 5, 10, margin=0.10, has_options=True, night=True, base_price=75000),
    _p("AL", "Aluminum", "SHFE", 5, 5, margin=0.10, has_options=True, night=True, base_price=20000),
    _p("ZN", "Zinc", "SHFE", 5, 5, margin=0.10, has_options=True, night=True, base_price=24000),
    _p("PB", "Lead", "SHFE", 5, 5, margin=0.10, has_options=True, night=True, base_price=17000),
    _p("NI", "Nickel", "SHFE", 1, 10, margin=0.12, has_options=True, night=True, base_price=130000),
    _p("SN", "Tin", "SHFE", 1, 10, margin=0.12, has_options=True, night=True, base_price=260000),
    _p("AU", "Gold", "SHFE", 1000, 0.02, margin=0.08, has_options=True, night=True, base_price=560),
    _p("AG", "Silver", "SHFE", 15, 1, margin=0.10, has_options=True, night=True, base_price=7500),
    _p("RB", "Rebar", "SHFE", 10, 1, margin=0.09, has_options=True, night=True, base_price=3400),
    _p("HC", "Hot-rolled Coil", "SHFE", 10, 1, margin=0.09, night=True, base_price=3400),
    _p("SS", "Stainless Steel", "SHFE", 5, 5, margin=0.10, night=True, base_price=14000),
    _p("BU", "Bitumen", "SHFE", 10, 1, margin=0.10, has_options=True, night=True, base_price=3600),
    _p("RU", "Natural Rubber", "SHFE", 10, 5, margin=0.10, has_options=True, night=True, base_price=15000),
    _p("FU", "Fuel Oil", "SHFE", 10, 1, margin=0.10, has_options=True, night=True, base_price=3200),
    _p("SP", "Pulp", "SHFE", 10, 2, margin=0.09, has_options=True, night=True, base_price=5500),
    _p("AO", "Alumina", "SHFE", 20, 1, margin=0.10, has_options=True, night=True, base_price=3500),
    _p("BR", "BR Rubber", "SHFE", 5, 5, margin=0.10, has_options=True, night=True, base_price=14000),
    _p("AD", "Cast Aluminum", "SHFE", 10, 1, margin=0.10, has_options=True, night=True, base_price=20000),
    _p("OP", "Offset Paper", "SHFE", 40, 1, margin=0.10, has_options=True, night=True, base_price=5000),
    # ----- DCE -----
    _p("A", "Soybean No.1", "DCE", 10, 1, margin=0.08, has_options=True, night=True, base_price=4500),
    _p("B", "Soybean No.2", "DCE", 10, 1, margin=0.08, has_options=True, night=True, base_price=3800),
    _p("M", "Soybean Meal", "DCE", 10, 1, margin=0.08, has_options=True, night=True, base_price=3000),
    _p("Y", "Soybean Oil", "DCE", 10, 2, margin=0.08, has_options=True, night=True, base_price=7800),
    _p("P", "Palm Oil", "DCE", 10, 2, margin=0.08, has_options=True, night=True, base_price=7500),
    _p("C", "Corn", "DCE", 10, 1, margin=0.08, has_options=True, night=True, base_price=2400),
    _p("CS", "Corn Starch", "DCE", 10, 1, margin=0.07, has_options=True, night=True, base_price=2800),
    _p("JD", "Eggs", "DCE", 10, 1, margin=0.08, has_options=True, base_price=4000),
    _p("L", "Plastic (LLDPE)", "DCE", 5, 1, margin=0.08, has_options=True, night=True, base_price=8200),
    _p("V", "PVC", "DCE", 5, 1, margin=0.08, has_options=True, night=True, base_price=5800),
    _p("PP", "Polypropylene", "DCE", 5, 1, margin=0.08, has_options=True, night=True, base_price=7500),
    _p("J", "Coke", "DCE", 100, 0.5, margin=0.12, night=True, base_price=2000),
    _p("JM", "Coking Coal", "DCE", 60, 0.5, margin=0.12, has_options=True, night=True, base_price=1500),
    _p("I", "Iron Ore", "DCE", 100, 0.5, margin=0.11, has_options=True, night=True, base_price=800),
    _p("EG", "Ethylene Glycol", "DCE", 10, 1, margin=0.08, has_options=True, night=True, base_price=4500),
    _p("EB", "Styrene", "DCE", 5, 1, margin=0.08, has_options=True, night=True, base_price=8500),
    _p("PG", "LPG", "DCE", 20, 1, margin=0.09, has_options=True, night=True, base_price=4500),
    _p("LH", "Live Hog", "DCE", 16, 5, margin=0.08, has_options=True, base_price=16000),
    _p("LG", "Log", "DCE", 90, 0.5, margin=0.08, has_options=True, base_price=800),
    _p("BZ", "Benzene", "DCE", 30, 0.5, margin=0.08, has_options=True, night=True, base_price=7000),
    # ----- CZCE -----
    _p("SR", "White Sugar", "CZCE", 10, 1, margin=0.07, has_options=True, night=True, base_price=6200),
    _p("CF", "Cotton", "CZCE", 5, 5, margin=0.07, has_options=True, night=True, base_price=15000),
    _p("TA", "PTA", "CZCE", 5, 2, margin=0.07, has_options=True, night=True, base_price=5500),
    _p("MA", "Methanol", "CZCE", 10, 1, margin=0.08, has_options=True, night=True, base_price=2400),
    _p("FG", "Glass", "CZCE", 20, 1, margin=0.09, has_options=True, night=True, base_price=1400),
    _p("OI", "Rapeseed Oil", "CZCE", 10, 1, margin=0.08, has_options=True, night=True, base_price=9000),
    _p("RM", "Rapeseed Meal", "CZCE", 10, 1, margin=0.08, has_options=True, night=True, base_price=2400),
    _p("SF", "Silico-manganese", "CZCE", 5, 2, margin=0.09, has_options=True, night=True, base_price=6500),
    _p("SM", "Ferrosilicon", "CZCE", 5, 2, margin=0.09, has_options=True, night=True, base_price=6500),
    _p("AP", "Apple", "CZCE", 10, 1, margin=0.10, has_options=True, base_price=8000),
    _p("CJ", "Red Dates", "CZCE", 5, 5, margin=0.10, has_options=True, base_price=12000),
    _p("UR", "Urea", "CZCE", 20, 1, margin=0.08, has_options=True, night=True, base_price=2000),
    _p("SA", "Soda Ash", "CZCE", 20, 1, margin=0.09, has_options=True, night=True, base_price=1800),
    _p("PF", "Short-staple Fiber", "CZCE", 5, 2, margin=0.08, has_options=True, night=True, base_price=7000),
    _p("PK", "Peanut", "CZCE", 5, 2, margin=0.08, has_options=True, base_price=9000),
    _p("SH", "Caustic Soda", "CZCE", 20, 1, margin=0.08, has_options=True, night=True, base_price=2500),
    _p("PX", "Paraxylene", "CZCE", 5, 2, margin=0.08, has_options=True, night=True, base_price=7500),
    _p("PL", "Propylene", "CZCE", 20, 0.5, margin=0.08, has_options=True, night=True, base_price=7000),
    _p("PR", "Bottle-grade PET", "CZCE", 15, 0.5, margin=0.08, has_options=True, night=True, base_price=7000),
    _p("ZC", "Thermal Coal", "CZCE", 100, 0.1, margin=0.10, has_options=True, night=True, base_price=800),
    # ----- INE -----
    _p("SC", "Crude Oil", "INE", 1000, 0.1, margin=0.10, has_options=True, night=True, base_price=580),
    _p("NR", "TSR20 Rubber", "INE", 10, 5, margin=0.09, has_options=True, night=True, base_price=13000),
    _p("LU", "Low-sulfur Fuel Oil", "INE", 10, 1, margin=0.10, night=True, base_price=3800),
    _p("BC", "Bonded Copper", "INE", 5, 10, margin=0.10, has_options=True, night=True, base_price=75000),
    _p("EC", "Container Shipping", "INE", 50, 0.1, margin=0.14, base_price=1500),
    # ----- GFEX -----
    _p("SI", "Industrial Silicon", "GFEX", 5, 5, margin=0.09, has_options=True, night=True, base_price=12000),
    _p("LC", "Lithium Carbonate", "GFEX", 1, 50, margin=0.10, has_options=True, night=True, base_price=90000),
    _p("PS", "Polysilicon", "GFEX", 3, 5, margin=0.11, night=True, base_price=40000),
    _p("PD", "Palladium", "GFEX", 1000, 0.05, margin=0.12, has_options=True, night=True, base_price=800),
    _p("PT", "Platinum", "GFEX", 1000, 0.05, margin=0.12, has_options=True, night=True, base_price=800),
)

CN_FUTURE_PRODUCTS: Dict[str, CnFutureProduct] = {p.root: p for p in _PRODUCTS}

# Index option roots that are options-only product codes (not futures).
_INDEX_OPTION_ONLY = frozenset({"IO", "HO", "MO"})

# Build longest-root-first matcher so JM matches before J, CS before C, etc.
_ROOTS_BY_LEN: Tuple[str, ...] = tuple(
    sorted(CN_FUTURE_PRODUCTS.keys(), key=len, reverse=True)
)
_ROOT_ALT = "|".join(_ROOTS_BY_LEN)

_FUTURE_RE = re.compile(
    rf"^(?P<root>{_ROOT_ALT})(?P<month>\d{{3,4}}|0|888|999)?$",
    re.IGNORECASE,
)
_OPTION_RE = re.compile(
    rf"^(?P<root>{_ROOT_ALT})(?P<month>\d{{3,4}})"
    rf"(?:[-_]?([CP])[-_]?(\d+(?:\.\d+)?))?$",
    re.IGNORECASE,
)


def normalize_cn_symbol(symbol: str) -> str:
    raw = str(symbol or "").strip().upper()
    if ":" in raw:
        raw = raw.split(":", 1)[-1]
    return raw.replace("=F", "").strip()


def is_continuous_month(month: Optional[str]) -> bool:
    return str(month or "").strip().upper() in CONTINUOUS_MONTH_CODES


def expand_cn_delivery_month(
    month: str,
    *,
    exchange: Optional[str] = None,
    now: Optional[datetime] = None,
) -> str:
    """Expand CZCE-style 3-digit ``YMM`` months to Sina/YYMM ``YYMM``.

    CTP on Zhengzhou often publishes ``SA701`` / ``TA509`` (last year digit +
    month). Public Sina / akshare minute feeds expect ``SA2701`` / ``TA2509``.
    Four-digit months and continuous sentinels are returned unchanged.
    """
    raw = str(month or "").strip().upper()
    if is_continuous_month(raw) or (len(raw) == 4 and raw.isdigit()):
        return raw
    if len(raw) != 3 or not raw.isdigit():
        return raw
    exch = str(exchange or "").strip().upper()
    if exch and exch not in CZCE_EXCHANGES:
        return raw

    year_digit = int(raw[0])
    mon = int(raw[1:3])
    if mon < 1 or mon > 12:
        return raw

    ref = now or datetime.now().astimezone()
    year = (int(ref.year) // 10) * 10 + year_digit
    try:
        from datetime import date as _date

        pivot = _date(int(ref.year), int(ref.month), 1)
        contract = _date(year, mon, 1)
        if contract > _date(pivot.year + 2, pivot.month, 1):
            year -= 10
        elif contract < _date(pivot.year - 8, pivot.month, 1):
            year += 10
    except Exception:
        pass
    return f"{year % 100:02d}{mon:02d}"


def to_sina_contract_symbol(symbol: str, *, now: Optional[datetime] = None) -> str:
    """Map a CN futures instrument id onto the Sina/akshare contract code."""
    code = normalize_cn_symbol(symbol)
    parsed = parse_cn_future_symbol(code)
    if not parsed:
        return code
    root = parsed["root"]
    month = parsed.get("month") or ""
    if is_continuous_month(month):
        return f"{root}0"
    expanded = expand_cn_delivery_month(month, exchange=parsed.get("exchange"), now=now)
    return f"{root}{expanded}"


def _match_future(symbol: str) -> Optional[re.Match[str]]:
    value = normalize_cn_symbol(symbol)
    return _FUTURE_RE.fullmatch(value)


def _match_option(symbol: str) -> Optional[re.Match[str]]:
    value = normalize_cn_symbol(symbol)
    if value in _INDEX_OPTION_ONLY:
        # Synthetic match-like dict handled by callers via dedicated path.
        return None
    return _OPTION_RE.fullmatch(value)


def parse_cn_future_symbol(symbol: str) -> Optional[Dict[str, str]]:
    value = normalize_cn_symbol(symbol)
    if value in _INDEX_OPTION_ONLY:
        return None
    match = _match_future(value)
    if not match:
        return None
    root = match.group("root").upper()
    # IO/HO/MO roots without strike are options products, not futures.
    if root in _INDEX_OPTION_ONLY:
        return None
    month = match.group("month") or ""
    return {
        "root": root,
        "month": month,
        "symbol": f"{root}{month}" if month else root,
        "instrument_id": f"{root}{month}" if month else root,
        "exchange": CN_FUTURE_PRODUCTS[root].exchange,
    }


def parse_cn_option_symbol(symbol: str) -> Optional[Dict[str, Any]]:
    value = normalize_cn_symbol(symbol)
    from app.markets.cn_options import is_etf_option_code

    if is_etf_option_code(value):
        return {
            "root": "ETFO",
            "month": "",
            "option_type": "",
            "strike": None,
            "symbol": value,
            "instrument_id": value,
            "exchange": "SSE",
            "kind": "etf",
        }
    if value in _INDEX_OPTION_ONLY:
        product = CN_FUTURE_PRODUCTS[value]
        return {
            "root": value,
            "month": "",
            "option_type": "",
            "strike": None,
            "symbol": value,
            "instrument_id": value,
            "exchange": product.exchange,
        }
    from app.markets.cn_options import canonical_option_symbol, parse_cn_option_instrument

    parsed = parse_cn_option_instrument(value)
    if parsed is not None:
        product = CN_FUTURE_PRODUCTS.get(parsed.root)
        exchange = parsed.exchange or (product.exchange if product else "")
        return {
            "root": parsed.root,
            "month": parsed.month,
            "option_type": parsed.call_put,
            "strike": float(parsed.strike) if parsed.strike else None,
            "symbol": canonical_option_symbol(parsed),
            "instrument_id": value,
            "exchange": exchange,
        }
    # Index option roots may appear as IO2509 without a strike.
    match = _match_option(value)
    if not match:
        return None
    root = match.group("root").upper()
    if root not in _INDEX_OPTION_ONLY:
        return None
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
        "exchange": CN_FUTURE_PRODUCTS[root].exchange,
    }


def exchange_for_root(root: str) -> Optional[str]:
    product = CN_FUTURE_PRODUCTS.get(str(root or "").strip().upper())
    return product.exchange if product else None


def is_cn_future(symbol: str) -> bool:
    return parse_cn_future_symbol(symbol) is not None


def is_cn_futures_option(symbol: str) -> bool:
    from app.markets.cn_options import is_etf_option_code

    return parse_cn_option_symbol(symbol) is not None or is_etf_option_code(normalize_cn_symbol(symbol))


def is_cn_derivative(symbol: str) -> bool:
    return is_cn_future(symbol) or is_cn_futures_option(symbol)


def get_future_product(symbol: str) -> CnFutureProduct:
    from app.markets.cn_options import is_etf_option_code

    if is_etf_option_code(normalize_cn_symbol(symbol)):
        return _ETF_OPTIONS_PRODUCT
    parsed = parse_cn_future_symbol(symbol)
    if parsed:
        return CN_FUTURE_PRODUCTS[parsed["root"]]
    # Index option-only roots are stored in the same catalog.
    opt = parse_cn_option_symbol(symbol)
    if opt and opt["root"] in CN_FUTURE_PRODUCTS:
        return CN_FUTURE_PRODUCTS[opt["root"]]
    raise ValueError(f"Unknown China futures/options symbol: {symbol!r}")


def estimate_futures_margin(
    symbol: str,
    *,
    price: float,
    lots: float,
    direction: str = "long",
    margin_rate: Optional[float] = None,
) -> float:
    product = get_future_product(symbol)
    if product.root in _INDEX_OPTION_ONLY:
        raise ValueError(f"{symbol!r} is an options product; use estimate_option_seller_margin")
    side = (direction or "long").strip().lower()
    rate = margin_rate
    if rate is None:
        rate = product.short_margin_rate if side in ("short", "sell") else product.long_margin_rate
    notional = abs(float(price)) * float(product.multiplier) * abs(float(lots))
    return round(notional * float(rate), 2)


def estimate_option_seller_margin(
    symbol: str,
    *,
    underlying_price: float,
    lots: float,
    margin_rate: Optional[float] = None,
) -> float:
    product = get_future_product(symbol)
    mult = float(product.option_multiplier or product.multiplier)
    rate = float(margin_rate if margin_rate is not None else product.option_seller_margin_rate)
    notional = abs(float(underlying_price)) * mult * abs(float(lots))
    return round(notional * rate, 2)


def resolve_market_category(symbol: str) -> str:
    if is_cn_futures_option(symbol):
        root = parse_cn_option_symbol(symbol)["root"]  # type: ignore[index]
        product = CN_FUTURE_PRODUCTS.get(root)
        if root in _INDEX_OPTION_ONLY or (product and product.product_class == "index"):
            return CN_INDEX_OPTIONS_MARKET
        return CN_FUTURES_OPTIONS_MARKET
    if is_cn_future(symbol):
        product = get_future_product(symbol)
        if product.product_class == "index":
            return CN_INDEX_FUTURES_MARKET
        return CN_FUTURES_MARKET
    return ""


def list_products(*, exchange: Optional[str] = None, options_only: bool = False) -> List[CnFutureProduct]:
    rows = list(CN_FUTURE_PRODUCTS.values())
    if exchange:
        ex = exchange.strip().upper()
        rows = [p for p in rows if p.exchange == ex]
    if options_only:
        rows = [p for p in rows if p.has_options or p.root in _INDEX_OPTION_ONLY]
    return rows


def list_continuous_history_targets(
    *,
    exchange: Optional[str] = None,
    include_options_only: bool = False,
) -> List[Dict[str, Any]]:
    """Main-continuous symbols covering the listed futures catalog.

    Index-option-only roots (IO/HO/MO) are skipped by default because they have
    no independent futures continuous series; use the underlying IF/IH/IM feed.
    """
    out: List[Dict[str, Any]] = []
    for product in list_products(exchange=exchange):
        if product.root in _INDEX_OPTION_ONLY and not include_options_only:
            continue
        if product.root in _INDEX_OPTION_ONLY:
            market = CN_INDEX_OPTIONS_MARKET
            market_type = "options"
        else:
            market = product.market_category
            market_type = "futures"
        out.append(
            {
                "root": product.root,
                "symbol": f"{product.root}0",
                "name": product.name,
                "exchange": product.exchange,
                "market": market,
                "market_type": market_type,
                "product_class": product.product_class,
            }
        )
    return out


def list_symbol_master_rows() -> List[Dict[str, Any]]:
    """Rows suitable for seeding qd_market_symbols."""
    out: List[Dict[str, Any]] = []
    for product in CN_FUTURE_PRODUCTS.values():
        if product.root in _INDEX_OPTION_ONLY:
            out.append(
                {
                    "market": CN_FUTURES_OPTIONS_MARKET,
                    "symbol": product.root,
                    "name": product.name,
                    "exchange": product.exchange,
                    "currency": product.currency,
                    "market_type": "options",
                    "asset_class": "options",
                }
            )
            # Keep CFFEX index option alias market too.
            out.append(
                {
                    "market": CN_INDEX_OPTIONS_MARKET,
                    "symbol": product.root,
                    "name": product.name,
                    "exchange": product.exchange,
                    "currency": product.currency,
                    "market_type": "options",
                    "asset_class": "options",
                }
            )
            continue
        market = CN_INDEX_FUTURES_MARKET if product.product_class == "index" else CN_FUTURES_MARKET
        out.append(
            {
                "market": CN_FUTURES_MARKET,
                "symbol": product.root,
                "name": product.name,
                "exchange": product.exchange,
                "currency": product.currency,
                "market_type": "futures",
                "asset_class": "futures",
            }
        )
        if product.product_class == "index":
            out.append(
                {
                    "market": CN_INDEX_FUTURES_MARKET,
                    "symbol": product.root,
                    "name": product.name,
                    "exchange": product.exchange,
                    "currency": product.currency,
                    "market_type": "futures",
                    "asset_class": "futures",
                }
            )
        if product.has_options:
            out.append(
                {
                    "market": CN_FUTURES_OPTIONS_MARKET,
                    "symbol": product.root,
                    "name": f"{product.name} Options",
                    "exchange": product.exchange,
                    "currency": product.currency,
                    "market_type": "options",
                    "asset_class": "options",
                }
            )
    return out


def cn_misroute_error(symbol: str) -> ValueError:
    sym = normalize_cn_symbol(symbol) or "?"
    return ValueError(f"{MISROUTE_MESSAGE} Got symbol={sym!r}.")


def exchanges() -> Iterable[str]:
    return sorted(CN_FUTURES_EXCHANGES)
