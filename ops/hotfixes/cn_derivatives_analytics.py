"""CN futures & derivatives analytics for the market-composite workbench."""

from __future__ import annotations

import math
import time
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional

from app.markets.cn_futures import get_future_product, list_products
from app.markets.cn_options import INDEX_OPTION_UNDERLYING
from app.utils.logger import get_logger

logger = get_logger(__name__)

# Live Sina commodity option Chinese names (scraped from optionsDP.php).
# Names must match Sina's nav labels exactly; outdated aliases (e.g. 铜期权) 404.
SINA_OPTION_NAME: Dict[str, str] = {
    "A": "黄大豆1号期权",
    "B": "黄大豆2号期权",
    "M": "豆粕期权",
    "Y": "豆油期权",
    "C": "玉米期权",
    "I": "铁矿石期权",
    "EG": "乙二醇期权",
    "EB": "苯乙烯期权",
    "PG": "液化石油气期权",
    "RB": "螺纹钢期权",
    "CU": "沪铜期权",
    "AL": "沪铝期权",
    "AU": "黄金期权",
    "AG": "白银期权",
    "RU": "橡胶期权",
    "BR": "丁二烯橡胶期权",
    "SR": "白糖期权",
    "CF": "棉花期权",
    "TA": "PTA期权",
    "MA": "甲醇期权",
    "OI": "菜籽油期权",
    "RM": "菜籽粕期权",
    "PK": "花生期权",
    "ZC": "动力煤期权",
    "SH": "烧碱期权",
    "PX": "二甲苯期权",
    "SI": "工业硅期权",
    "LC": "碳酸锂期权",
}

# CFFEX index options via dedicated Sina endpoints (not commodity optionsDP).
CFFEX_OPTION_LIST_FN: Dict[str, str] = {
    "IO": "option_cffex_hs300_list_sina",
    "HO": "option_cffex_sz50_list_sina",
    "MO": "option_cffex_zz1000_list_sina",
}
CFFEX_OPTION_LIST_KEY: Dict[str, str] = {
    "IO": "沪深300指数",
    "HO": "上证50指数",
    "MO": "中证1000指数",
}
CFFEX_OPTION_SPOT_FN: Dict[str, str] = {
    "IO": "option_cffex_hs300_spot_sina",
    "HO": "option_cffex_sz50_spot_sina",
    "MO": "option_cffex_zz1000_spot_sina",
}

CN_NAME: Dict[str, str] = {
    # CFFEX
    "IF": "沪深300股指期货",
    "IH": "上证50股指期货",
    "IC": "中证500股指期货",
    "IM": "中证1000股指期货",
    "IO": "沪深300股指期权",
    "HO": "上证50股指期权",
    "MO": "中证1000股指期权",
    "T": "10年期国债期货",
    "TF": "5年期国债期货",
    "TS": "2年期国债期货",
    "TL": "30年期国债期货",
    # SHFE
    "CU": "铜",
    "AL": "铝",
    "ZN": "锌",
    "PB": "铅",
    "NI": "镍",
    "SN": "锡",
    "AU": "黄金",
    "AG": "白银",
    "RB": "螺纹钢",
    "HC": "热轧卷板",
    "SS": "不锈钢",
    "BU": "沥青",
    "RU": "橡胶",
    "FU": "燃油",
    "SP": "纸浆",
    "AO": "氧化铝",
    "BR": "丁二烯橡胶",
    "AD": "铸造铝合金",
    "OP": "胶版印刷纸",
    # DCE
    "A": "黄大豆1号",
    "B": "黄大豆2号",
    "M": "豆粕",
    "Y": "豆油",
    "P": "棕榈油",
    "C": "玉米",
    "CS": "玉米淀粉",
    "JD": "鸡蛋",
    "L": "聚乙烯",
    "V": "PVC",
    "PP": "聚丙烯",
    "J": "焦炭",
    "JM": "焦煤",
    "I": "铁矿石",
    "EG": "乙二醇",
    "EB": "苯乙烯",
    "PG": "液化石油气",
    "LH": "生猪",
    "LG": "原木",
    "BZ": "纯苯",
    # CZCE
    "SR": "白糖",
    "CF": "棉花",
    "TA": "PTA",
    "MA": "甲醇",
    "FG": "玻璃",
    "OI": "菜籽油",
    "RM": "菜粕",
    "SF": "硅铁",
    "SM": "锰硅",
    "AP": "苹果",
    "CJ": "红枣",
    "UR": "尿素",
    "SA": "纯碱",
    "PF": "短纤",
    "PK": "花生",
    "SH": "烧碱",
    "PX": "对二甲苯",
    "PL": "丙烯",
    "PR": "瓶片",
    "ZC": "动力煤",
    # INE
    "SC": "原油",
    "NR": "20号胶",
    "LU": "低硫燃料油",
    "BC": "国际铜",
    "EC": "集运指数（欧线）",
    # GFEX
    "SI": "工业硅",
    "LC": "碳酸锂",
    "PS": "多晶硅",
    "PD": "钯金",
    "PT": "铂金",
}


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        text = str(value).strip().replace(",", "")
        if text in {"", "-", "--", "None", "nan", "NaN"}:
            return default
        return float(text)
    except Exception:
        return default


def _ak():
    import akshare as ak  # type: ignore

    return ak


def _product_payload(root: str) -> Dict[str, Any]:
    root_u = str(root or "").upper()
    product = get_future_product(root_u)
    has_chain = root_u in SINA_OPTION_NAME or root_u in CFFEX_OPTION_LIST_FN
    underlying_root = INDEX_OPTION_UNDERLYING.get(root_u, root_u)
    if not product:
        return {
            "root": root_u,
            "name": root_u,
            "name_cn": CN_NAME.get(root_u, root_u),
            "has_options": has_chain,
            "has_option_chain": has_chain,
            "multiplier": 10.0,
            "option_multiplier": 10.0,
            "exchange": "",
            "product_class": "commodity",
            "option_sina_name": SINA_OPTION_NAME.get(root_u),
            "option_feed": (
                "cffex_sina"
                if root_u in CFFEX_OPTION_LIST_FN
                else ("commodity_sina" if root_u in SINA_OPTION_NAME else None)
            ),
            "continuous_symbol": f"{underlying_root}0",
            "underlying_root": underlying_root,
            "long_margin_rate": 0.10,
            "option_seller_margin_rate": 0.12,
        }
    return {
        "root": product.root,
        "name": product.name,
        "name_cn": CN_NAME.get(product.root, product.name),
        "exchange": product.exchange,
        "multiplier": float(product.multiplier or 1),
        "tick_size": float(product.tick_size or 0),
        "has_options": bool(product.has_options or has_chain),
        "has_option_chain": has_chain,
        "product_class": product.product_class,
        "option_multiplier": float(product.option_multiplier or product.multiplier or 1),
        "option_sina_name": SINA_OPTION_NAME.get(product.root),
        "option_feed": (
            "cffex_sina"
            if product.root in CFFEX_OPTION_LIST_FN
            else ("commodity_sina" if product.root in SINA_OPTION_NAME else None)
        ),
        "continuous_symbol": f"{underlying_root}0",
        "underlying_root": underlying_root,
        "long_margin_rate": float(getattr(product, "long_margin_rate", 0.10) or 0.10),
        "option_seller_margin_rate": float(
            getattr(product, "option_seller_margin_rate", 0.12) or 0.12
        ),
    }


def _month_code(symbol: str) -> str:
    """Extract YYMM / YMM delivery code from futures/option month symbols."""
    digits = "".join(ch for ch in str(symbol or "") if ch.isdigit())
    if len(digits) >= 4:
        return digits[-4:]
    if len(digits) == 3:
        return digits
    return digits


def _option_capital_for_chain(
    chain: List[Dict[str, Any]],
    *,
    underlying: float,
    multiplier: float,
) -> Dict[str, float]:
    """Premium = mid*OI*mult; notional = underlying*OI*mult."""
    call_premium = sum(float(row["call_mid"]) * float(row["call_oi"]) * multiplier for row in chain)
    put_premium = sum(float(row["put_mid"]) * float(row["put_oi"]) * multiplier for row in chain)
    call_oi = sum(float(row["call_oi"]) for row in chain)
    put_oi = sum(float(row["put_oi"]) for row in chain)
    u = float(underlying or 0.0)
    call_notional = call_oi * u * multiplier
    put_notional = put_oi * u * multiplier
    return {
        "call_oi": call_oi,
        "put_oi": put_oi,
        "total_oi": call_oi + put_oi,
        "call_premium": call_premium,
        "put_premium": put_premium,
        "premium": call_premium + put_premium,
        "call_notional": call_notional,
        "put_notional": put_notional,
        "notional": call_notional + put_notional,
        # Backward-compatible aliases (premium / 权利金)
        "call_settled": call_premium,
        "put_settled": put_premium,
        "settled_capital": call_premium + put_premium,
    }


def _time_value_annualized_yield(
    chain: List[Dict[str, Any]],
    *,
    underlying: float,
    multiplier: float,
    margin_rate: float,
    T: float,
    month: str,
) -> Dict[str, Any]:
    """Annualized time-value / seller-margin yield by strike for one expiry."""
    F = float(underlying or 0.0)
    mult = float(multiplier or 1.0)
    rate = float(margin_rate or 0.12)
    t_years = max(float(T or 0.0), 1.0 / 365.0)
    call_points = []
    put_points = []
    if F <= 0 or mult <= 0 or rate <= 0:
        return {"month": month, "T": t_years, "call": [], "put": []}

    for row in chain:
        k = float(row["strike"])
        call_mid = float(row.get("call_mid") or 0.0)
        put_mid = float(row.get("put_mid") or 0.0)
        call_intrinsic = max(F - k, 0.0)
        put_intrinsic = max(k - F, 0.0)
        call_tv = max(call_mid - call_intrinsic, 0.0)
        put_tv = max(put_mid - put_intrinsic, 0.0)
        # Seller margin approx: underlying * multiplier * option seller margin rate
        margin = F * mult * rate
        if margin <= 0:
            continue
        if call_mid > 0:
            call_points.append(
                {
                    "strike": k,
                    "time_value": call_tv,
                    "premium": call_mid,
                    "margin": margin,
                    "yield": (call_tv * mult / margin) / t_years,
                    "side": "call",
                    "month": month,
                }
            )
        if put_mid > 0:
            put_points.append(
                {
                    "strike": k,
                    "time_value": put_tv,
                    "premium": put_mid,
                    "margin": margin,
                    "yield": (put_tv * mult / margin) / t_years,
                    "side": "put",
                    "month": month,
                }
            )
    return {"month": month, "T": t_years, "call": call_points, "put": put_points}


def list_derivative_products() -> List[Dict[str, Any]]:
    rows = [_product_payload(item.root) for item in list_products()]
    rows.sort(key=lambda item: (0 if item.get("has_options") else 1, item["root"]))
    return rows


def _spot_board_row(root: str) -> Optional[Dict[str, Any]]:
    root_u = str(root or "").upper()
    ak = _ak()
    frame = None
    today = date.today()
    for offset in range(0, 6):
        day = (today - timedelta(days=offset)).strftime("%Y%m%d")
        try:
            candidate = ak.futures_spot_price_daily(start_day=day, end_day=day)
            if candidate is not None and not getattr(candidate, "empty", True):
                frame = candidate
                break
        except Exception as exc:
            logger.debug("futures_spot_price_daily %s failed: %s", day, exc)
    if frame is None:
        try:
            frame = ak.futures_spot_price()
        except Exception as exc:
            logger.warning("futures_spot_price failed: %s", exc)
            return None
    if frame is None or getattr(frame, "empty", True):
        return None
    for _, row in frame.iterrows():
        symbol = str(row.get("symbol") or "").strip().upper()
        if symbol != root_u:
            continue
        return {
            "date": str(row.get("date") or ""),
            "root": root_u,
            "spot_price": _safe_float(row.get("spot_price")),
            "near_contract": str(row.get("near_contract") or "").lower(),
            "near_contract_price": _safe_float(row.get("near_contract_price")),
            "dominant_contract": str(row.get("dominant_contract") or "").lower(),
            "dominant_contract_price": _safe_float(row.get("dominant_contract_price")),
            "near_basis": _safe_float(row.get("near_basis")),
            "dom_basis": _safe_float(row.get("dom_basis")),
            "near_basis_rate": _safe_float(row.get("near_basis_rate")),
            "dom_basis_rate": _safe_float(row.get("dom_basis_rate")),
        }
    return None


def _futures_zh_spot(symbol: str) -> Optional[Dict[str, Any]]:
    code = str(symbol or "").strip()
    if not code:
        return None
    ak = _ak()
    queries: List[str] = []
    if code[:-1].isalpha() and code.endswith("0"):
        queries.extend([code.upper(), code.lower()])
    else:
        queries.extend([code.lower(), code.upper()])
    for query in queries:
        try:
            frame = ak.futures_zh_spot(symbol=query, market="CF", adjust="0")
            if frame is None or getattr(frame, "empty", True):
                continue
            row = frame.iloc[-1]
            return {
                "symbol": query,
                "name": str(row.get("symbol") or query),
                "price": _safe_float(row.get("current_price")),
                "open": _safe_float(row.get("open")),
                "high": _safe_float(row.get("high")),
                "low": _safe_float(row.get("low")),
                "bid": _safe_float(row.get("bid_price")),
                "ask": _safe_float(row.get("ask_price")),
                "volume": _safe_float(row.get("volume")),
                "open_interest": _safe_float(row.get("hold")),
                "avg_price": _safe_float(row.get("avg_price")),
                "prev_close": _safe_float(row.get("last_close")),
                "prev_settle": _safe_float(row.get("last_settle_price")),
            }
        except Exception as exc:
            logger.debug("futures_zh_spot %s failed: %s", query, exc)
    return None


def _option_months(root: str) -> List[str]:
    root_u = str(root or "").upper()
    if root_u in CFFEX_OPTION_LIST_FN:
        return _cffex_option_months(root_u)
    name = SINA_OPTION_NAME.get(root_u)
    if not name:
        return []
    try:
        frame = _ak().option_commodity_contract_sina(symbol=name)
        if frame is None or getattr(frame, "empty", True):
            return []
        col = "合约" if "合约" in frame.columns else frame.columns[-1]
        out: List[str] = []
        for value in frame[col].tolist():
            text = str(value or "").strip().lower()
            if text:
                out.append(text)
        return out
    except Exception as exc:
        logger.warning("option months for %s failed: %s", root, exc)
        return []


def _cffex_option_months(root: str) -> List[str]:
    root_u = str(root or "").upper()
    fn_name = CFFEX_OPTION_LIST_FN.get(root_u)
    key = CFFEX_OPTION_LIST_KEY.get(root_u)
    if not fn_name or not key:
        return []
    try:
        ak = _ak()
        fn = getattr(ak, fn_name, None)
        if not callable(fn):
            return []
        payload = fn() or {}
        months = payload.get(key) or []
        out: List[str] = []
        for value in months:
            text = str(value or "").strip().lower()
            if text:
                out.append(text)
        return out
    except Exception as exc:
        logger.warning("cffex option months for %s failed: %s", root_u, exc)
        return []


def _mid(bid: float, ask: float, last: float) -> float:
    if bid > 0 and ask > 0:
        return (bid + ask) / 2.0
    if last > 0:
        return last
    return max(bid, ask, 0.0)


def _parse_option_chain_frame(frame: Any) -> List[Dict[str, Any]]:
    """Normalize commodity / CFFEX Sina option chain tables into a common shape."""
    if frame is None or getattr(frame, "empty", True):
        return []
    rows: List[Dict[str, Any]] = []
    for _, item in frame.iterrows():
        strike = _safe_float(item.get("行权价"))
        if strike <= 0:
            continue
        call_last = _safe_float(item.get("看涨合约-最新价"))
        put_last = _safe_float(item.get("看跌合约-最新价"))
        call_bid = _safe_float(item.get("看涨合约-买价"))
        call_ask = _safe_float(item.get("看涨合约-卖价"))
        put_bid = _safe_float(item.get("看跌合约-买价"))
        put_ask = _safe_float(item.get("看跌合约-卖价"))
        call_symbol = str(
            item.get("看涨合约-看涨期权合约")
            or item.get("看涨合约-标识")
            or item.get("看涨合约代码")
            or ""
        )
        put_symbol = str(
            item.get("看跌合约-看跌期权合约")
            or item.get("看跌合约-标识")
            or item.get("看跌合约代码")
            or ""
        )
        rows.append(
            {
                "strike": strike,
                "call_symbol": call_symbol,
                "put_symbol": put_symbol,
                "call_last": call_last,
                "put_last": put_last,
                "call_bid": call_bid,
                "call_ask": call_ask,
                "put_bid": put_bid,
                "put_ask": put_ask,
                "call_mid": _mid(call_bid, call_ask, call_last),
                "put_mid": _mid(put_bid, put_ask, put_last),
                "call_oi": _safe_float(item.get("看涨合约-持仓量")),
                "put_oi": _safe_float(item.get("看跌合约-持仓量")),
                "call_change": _safe_float(item.get("看涨合约-涨跌")),
                "put_change": _safe_float(item.get("看跌合约-涨跌")),
            }
        )
    rows.sort(key=lambda row: row["strike"])
    return rows


def _option_chain_table(root: str, month_contract: str) -> List[Dict[str, Any]]:
    root_u = str(root or "").upper()
    contract = str(month_contract or "").strip().lower()
    if not contract:
        return []
    if root_u in CFFEX_OPTION_SPOT_FN:
        return _cffex_option_chain_table(root_u, contract)
    name = SINA_OPTION_NAME.get(root_u)
    if not name:
        return []
    try:
        frame = _ak().option_commodity_contract_table_sina(symbol=name, contract=contract)
        return _parse_option_chain_frame(frame)
    except Exception as exc:
        logger.warning("option chain %s/%s failed: %s", root, contract, exc)
        return []


def _cffex_option_chain_table(root: str, month_contract: str) -> List[Dict[str, Any]]:
    root_u = str(root or "").upper()
    contract = str(month_contract or "").strip().lower()
    fn_name = CFFEX_OPTION_SPOT_FN.get(root_u)
    if not fn_name or not contract:
        return []
    try:
        ak = _ak()
        fn = getattr(ak, fn_name, None)
        if not callable(fn):
            return []
        frame = fn(symbol=contract)
        return _parse_option_chain_frame(frame)
    except Exception as exc:
        logger.warning("cffex option chain %s/%s failed: %s", root_u, contract, exc)
        return []


def _underlying_futures_symbol(root: str, month_contract: Optional[str] = None) -> str:
    """Map option root/month onto the futures quote symbol used for underlying."""
    root_u = str(root or "").upper()
    fut_root = INDEX_OPTION_UNDERLYING.get(root_u, root_u)
    month = str(month_contract or "").strip().lower()
    if not month:
        return f"{fut_root}0"
    digits = "".join(ch for ch in month if ch.isdigit())
    if not digits:
        return f"{fut_root}0"
    return f"{fut_root.lower()}{digits}"

def _norm_cdf(x: float) -> float:
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def _norm_pdf(x: float) -> float:
    return math.exp(-0.5 * x * x) / math.sqrt(2.0 * math.pi)


def black76_price(F: float, K: float, T: float, sigma: float, is_call: bool) -> float:
    if F <= 0 or K <= 0 or T <= 0 or sigma <= 0:
        return max(F - K, 0.0) if is_call else max(K - F, 0.0)
    vol = sigma * math.sqrt(T)
    d1 = (math.log(F / K) + 0.5 * sigma * sigma * T) / vol
    d2 = d1 - vol
    if is_call:
        return F * _norm_cdf(d1) - K * _norm_cdf(d2)
    return K * _norm_cdf(-d2) - F * _norm_cdf(-d1)


def black76_greeks(F: float, K: float, T: float, sigma: float, is_call: bool) -> Dict[str, float]:
    if F <= 0 or K <= 0 or T <= 0 or sigma <= 0:
        return {"delta": 0.0, "gamma": 0.0, "vega": 0.0, "theta": 0.0}
    vol = sigma * math.sqrt(T)
    d1 = (math.log(F / K) + 0.5 * sigma * sigma * T) / vol
    pdf = _norm_pdf(d1)
    gamma = pdf / (F * vol) if F * vol > 0 else 0.0
    vega = F * pdf * math.sqrt(T) / 100.0
    theta = (-(F * pdf * sigma) / (2 * math.sqrt(T))) / 365.0
    delta = _norm_cdf(d1) if is_call else _norm_cdf(d1) - 1.0
    return {"delta": delta, "gamma": gamma, "vega": vega, "theta": theta}


def implied_vol_black76(price: float, F: float, K: float, T: float, is_call: bool) -> Optional[float]:
    if price <= 0 or F <= 0 or K <= 0 or T <= 0:
        return None
    lo, hi = 1e-4, 5.0
    for _ in range(50):
        mid = 0.5 * (lo + hi)
        model = black76_price(F, K, T, mid, is_call)
        if model > price:
            hi = mid
        else:
            lo = mid
    iv = 0.5 * (lo + hi)
    if iv <= 1e-3 or iv >= 4.9:
        return None
    return iv


def _year_fraction_to_month(contract: str) -> float:
    digits = "".join(ch for ch in str(contract) if ch.isdigit())
    try:
        if len(digits) == 3:
            year = 2020 + int(digits[0])
            month = int(digits[1:])
        elif len(digits) >= 4:
            year = 2000 + int(digits[:2])
            month = int(digits[2:4])
        else:
            return 30 / 365.0
        expiry = date(year, max(1, min(month, 12)), 15)
    except Exception:
        return 30 / 365.0
    return max((expiry - date.today()).days, 1) / 365.0


def compute_max_pain(chain: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    if not chain:
        return None
    strikes = [row["strike"] for row in chain]
    best_strike = None
    best_pain = None
    curve = []
    for settle in strikes:
        pain = 0.0
        for row in chain:
            k = row["strike"]
            pain += row["call_oi"] * max(settle - k, 0.0)
            pain += row["put_oi"] * max(k - settle, 0.0)
        curve.append({"strike": settle, "pain": pain})
        if best_pain is None or pain < best_pain:
            best_pain = pain
            best_strike = settle
    return {"strike": best_strike, "pain": best_pain, "curve": curve}


def compute_gex(
    chain: List[Dict[str, Any]],
    *,
    underlying: float,
    multiplier: float,
    T: float,
) -> Dict[str, Any]:
    """Delegate to the GEX indicator compute path (legacy dict shape)."""
    from app.services.gex_indicator import compute_gex as _compute_gex_indicator

    return _compute_gex_indicator(
        chain,
        underlying=underlying,
        multiplier=multiplier,
        T=T,
    )


def build_spot_panel(root: str) -> Dict[str, Any]:
    root_u = str(root or "").upper()
    product = _product_payload(root_u)
    board = _spot_board_row(root_u)
    continuous = _futures_zh_spot(str(product.get("continuous_symbol") or f"{root_u}0"))
    analysis: List[str] = []
    if board:
        basis = board.get("dom_basis") or 0.0
        rate = board.get("dom_basis_rate") or 0.0
        if basis > 0:
            analysis.append(f"主力合约升水 {basis:.2f}（{rate * 100:.2f}%），远月相对现货偏强。")
        elif basis < 0:
            analysis.append(f"主力合约贴水 {abs(basis):.2f}（{abs(rate) * 100:.2f}%），远月相对现货偏弱。")
        else:
            analysis.append("主力合约与现货基本平水。")
        analysis.append(
            f"近月 {board.get('near_contract')} @ {board.get('near_contract_price')}，"
            f"主力 {board.get('dominant_contract')} @ {board.get('dominant_contract_price')}。"
        )
    if continuous and continuous.get("price"):
        analysis.append(
            f"连续合约最新价 {continuous['price']:.2f}，持仓 {continuous.get('open_interest', 0):.0f}，"
            f"成交 {continuous.get('volume', 0):.0f}。"
        )
    if not analysis:
        analysis.append("暂无现货升贴水看板，已回退连续合约报价。")
    spot_price = (board or {}).get("spot_price") or (continuous or {}).get("price")
    return {
        "root": root_u,
        "product": product,
        "name_cn": product.get("name_cn") or root_u,
        "spot": board,
        "continuous": continuous,
        "spot_price": spot_price,
        "analysis": analysis,
        "asof": datetime.now().isoformat(timespec="seconds"),
    }


def build_futures_panel(root: str) -> Dict[str, Any]:
    root_u = str(root or "").upper()
    product = _product_payload(root_u)
    board = _spot_board_row(root_u)
    months = _option_months(root_u)

    candidates: List[str] = []
    if board:
        for key in ("near_contract", "dominant_contract"):
            sym = str(board.get(key) or "").strip()
            if sym:
                candidates.append(sym)
    candidates.extend(months)
    if root_u in INDEX_OPTION_UNDERLYING:
        for m in months:
            candidates.append(_underlying_futures_symbol(root_u, m))
    candidates.append(str(product.get("continuous_symbol") or f"{root_u.lower()}0"))

    seen = set()
    symbols: List[str] = []
    for item in candidates:
        key = item.lower()
        if key in seen:
            continue
        seen.add(key)
        symbols.append(item)

    curve = []
    for symbol in symbols[:12]:
        quote = _futures_zh_spot(symbol)
        if not quote or quote.get("price", 0) <= 0:
            continue
        is_continuous = symbol.lower().endswith("0") and symbol[:-1].isalpha()
        curve.append(
            {
                "symbol": symbol.lower(),
                "label": "连续" if is_continuous else symbol.lower(),
                "price": quote["price"],
                "volume": quote.get("volume") or 0.0,
                "open_interest": quote.get("open_interest") or 0.0,
                "prev_settle": quote.get("prev_settle") or 0.0,
                "is_continuous": is_continuous,
            }
        )

    spot_price = (board or {}).get("spot_price") or 0.0
    for point in curve:
        if spot_price > 0 and not point["is_continuous"]:
            point["basis"] = point["price"] - spot_price
            point["basis_rate"] = point["basis"] / spot_price
        else:
            point["basis"] = None
            point["basis_rate"] = None

    options_capital = []
    capital_by_month: Dict[str, Dict[str, float]] = {}
    mult = float(product.get("option_multiplier") or product.get("multiplier") or 1)
    for month in months[:6]:
        chain = _option_chain_table(root_u, month)
        if not chain:
            continue
        month_quote = _futures_zh_spot(month)
        month_underlying = (
            (month_quote or {}).get("price")
            or next((p["price"] for p in curve if _month_code(p["symbol"]) == _month_code(month)), 0.0)
            or spot_price
            or 0.0
        )
        capital = _option_capital_for_chain(chain, underlying=month_underlying, multiplier=mult)
        row = {
            "month": month,
            "month_code": _month_code(month),
            "underlying": month_underlying,
            **capital,
        }
        options_capital.append(row)
        capital_by_month[_month_code(month)] = capital

    monthly_activity = []
    fut_mult = float(product.get("multiplier") or 1)
    for point in curve:
        if point["is_continuous"]:
            continue
        code = _month_code(point["symbol"])
        opt = capital_by_month.get(code) or {}
        futures_capital = float(point["price"] or 0.0) * float(point["open_interest"] or 0.0) * fut_mult
        option_notional = float(opt.get("notional") or 0.0)
        monthly_activity.append(
            {
                "symbol": point["symbol"],
                "month_code": code,
                "volume": point["volume"],
                "open_interest": point["open_interest"],
                "price": point["price"],
                "futures_capital": futures_capital,
                "option_notional": option_notional or None,
                "option_premium": opt.get("premium"),
                "option_call_notional": opt.get("call_notional"),
                "option_put_notional": opt.get("put_notional"),
                "combined_capital": futures_capital + option_notional,
            }
        )

    return {
        "root": root_u,
        "name_cn": product.get("name_cn") or root_u,
        "spot": board,
        "term_structure": curve,
        "basis": {
            "near_basis": (board or {}).get("near_basis"),
            "dom_basis": (board or {}).get("dom_basis"),
            "near_basis_rate": (board or {}).get("near_basis_rate"),
            "dom_basis_rate": (board or {}).get("dom_basis_rate"),
            "spot_price": spot_price,
        },
        "monthly_activity": monthly_activity,
        "options_settled_capital": options_capital,
        "asof": datetime.now().isoformat(timespec="seconds"),
    }


def _aggregate_chains_by_strike(chains: List[List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
    """Merge option chains across months: sum OI, OI-weighted mids."""
    bucket: Dict[float, Dict[str, float]] = {}
    for chain in chains:
        for row in chain:
            k = float(row["strike"])
            item = bucket.setdefault(
                k,
                {
                    "strike": k,
                    "call_oi": 0.0,
                    "put_oi": 0.0,
                    "call_mid_w": 0.0,
                    "put_mid_w": 0.0,
                    "call_mid_n": 0.0,
                    "put_mid_n": 0.0,
                },
            )
            call_oi = float(row.get("call_oi") or 0.0)
            put_oi = float(row.get("put_oi") or 0.0)
            call_mid = float(row.get("call_mid") or 0.0)
            put_mid = float(row.get("put_mid") or 0.0)
            item["call_oi"] += call_oi
            item["put_oi"] += put_oi
            if call_oi > 0 and call_mid > 0:
                item["call_mid_w"] += call_mid * call_oi
                item["call_mid_n"] += call_oi
            if put_oi > 0 and put_mid > 0:
                item["put_mid_w"] += put_mid * put_oi
                item["put_mid_n"] += put_oi
    rows: List[Dict[str, Any]] = []
    for item in bucket.values():
        rows.append(
            {
                "strike": item["strike"],
                "call_oi": item["call_oi"],
                "put_oi": item["put_oi"],
                "call_mid": (item["call_mid_w"] / item["call_mid_n"]) if item["call_mid_n"] > 0 else 0.0,
                "put_mid": (item["put_mid_w"] / item["put_mid_n"]) if item["put_mid_n"] > 0 else 0.0,
                "call_last": 0.0,
                "put_last": 0.0,
                "call_bid": 0.0,
                "call_ask": 0.0,
                "put_bid": 0.0,
                "put_ask": 0.0,
            }
        )
    rows.sort(key=lambda row: row["strike"])
    return rows


def build_options_panel(root: str, month: Optional[str] = None) -> Dict[str, Any]:
    root_u = str(root or "").upper()
    product = _product_payload(root_u)
    months = _option_months(root_u)
    if not months:
        listed = bool(product.get("has_options"))
        if listed and not product.get("has_option_chain"):
            message = (
                "该品种已上市期权，但公开新浪期权链暂未覆盖；"
                "可在合约搜索中查看 CTP 挂牌合约，链截面分析待接入本地快照。"
            )
        elif root_u in {"IO", "HO", "MO"}:
            message = "股指期权链暂时不可用，请稍后重试。"
        else:
            message = "该品种暂无可用的公开期权链数据（未上市或新浪未覆盖）。"
        return {
            "root": root_u,
            "name_cn": product.get("name_cn") or root_u,
            "months": [],
            "month": None,
            "available": False,
            "has_option_chain": False,
            "message": message,
            "asof": datetime.now().isoformat(timespec="seconds"),
        }

    month_raw = (month or "all").strip().lower()
    select_all = month_raw in {"", "all", "*", "全部"}
    selected_months = months[:6] if select_all else [month_raw]
    if not select_all:
        if selected_months[0] not in {m.lower() for m in months}:
            selected_months = [months[0].lower()]
        else:
            # keep original casing from catalog when possible
            selected_months = [next(m for m in months if m.lower() == selected_months[0])]

    board = _spot_board_row(root_u)
    continuous = _futures_zh_spot(str(product.get("continuous_symbol") or f"{root_u}0"))
    fallback_underlying = (
        (continuous or {}).get("price")
        or (board or {}).get("dominant_contract_price")
        or (board or {}).get("spot_price")
        or 0.0
    )
    mult = float(product.get("option_multiplier") or product.get("multiplier") or 1)
    margin_rate = float(product.get("option_seller_margin_rate") or 0.12)

    month_series: List[Dict[str, Any]] = []
    chains_for_agg: List[List[Dict[str, Any]]] = []
    underlyings: List[float] = []
    Ts: List[float] = []

    for m in selected_months:
        chain = _option_chain_table(root_u, m)
        if not chain:
            continue
        fut_symbol = _underlying_futures_symbol(root_u, m)
        fut = _futures_zh_spot(fut_symbol) or continuous
        underlying = (fut or {}).get("price") or fallback_underlying
        T = _year_fraction_to_month(m)
        underlyings.append(float(underlying or 0.0))
        Ts.append(float(T))
        chains_for_agg.append(chain)
        from app.services.gex_indicator import panel_fields_from_gex_indicator, run_gex_indicator

        gex_indicator = run_gex_indicator(
            chain,
            underlying=float(underlying or 0.0),
            multiplier=mult,
            T=T,
            name=f"GEX {m}",
        )
        gex_fields = panel_fields_from_gex_indicator(gex_indicator)
        max_pain = compute_max_pain(chain) if chain else None
        tv_yield = _time_value_annualized_yield(
            chain,
            underlying=float(underlying or 0.0),
            multiplier=mult,
            margin_rate=margin_rate,
            T=T,
            month=m,
        )
        month_series.append(
            {
                "month": m,
                "underlying": underlying,
                "T": T,
                "gex_distribution": gex_fields.get("gex_distribution") or [],
                "gex_summary": gex_fields.get("gex_summary") or {},
                "greeks": gex_fields.get("greeks") or {},
                "iv_smile": gex_fields.get("iv_smile") or [],
                "max_pain": max_pain,
                "time_value_yield": tv_yield,
                "indicators": gex_fields.get("indicators") or {},
            }
        )

    if not month_series:
        return {
            "root": root_u,
            "name_cn": product.get("name_cn") or root_u,
            "available": True,
            "has_option_chain": True,
            "months": months,
            "month": "all" if select_all else (selected_months[0] if selected_months else None),
            "underlying": fallback_underlying,
            "current_price": fallback_underlying,
            "multiplier": mult,
            "margin_rate": margin_rate,
            "chain": [],
            "greeks": {},
            "gex_summary": {},
            "gex_distribution": [],
            "iv_smile": [],
            "max_pain": None,
            "time_value_yield": {"month": None, "T": 0, "call": [], "put": []},
            "month_series": [],
            "indicators": {
                "gex": {
                    "name": "GEX",
                    "meta": {"kind": "strike_profile", "axis": "strike"},
                    "categories": [],
                    "plots": [],
                    "signals": [],
                    "layers": [],
                    "summary": {},
                    "calculatedVars": {"points": [], "portfolio_greeks": {}, "iv_smile": []},
                }
            },
            "asof": datetime.now().isoformat(timespec="seconds"),
        }

    if select_all:
        agg_chain = _aggregate_chains_by_strike(chains_for_agg)
        underlying = next((u for u in underlyings if u > 0), fallback_underlying)
        T = (sum(Ts) / len(Ts)) if Ts else 30 / 365.0
        from app.services.gex_indicator import panel_fields_from_gex_indicator, run_gex_indicator

        gex_indicator = run_gex_indicator(
            agg_chain,
            underlying=float(underlying or 0.0),
            multiplier=mult,
            T=T,
            name="GEX all",
        )
        gex_fields = panel_fields_from_gex_indicator(gex_indicator)
        # Max pain on aggregated OI
        max_pain = compute_max_pain(agg_chain) if agg_chain else None
        selected_label = "all"
        # Overlay series for non-GEX charts come from month_series
        iv_smile = []
        for item in month_series:
            for point in item.get("iv_smile") or []:
                iv_smile.append({**point, "month": item["month"]})
        # Flatten TV for convenience; frontend mainly uses month_series
        tv_yield = {"month": "all", "T": T, "call": [], "put": [], "by_month": [m["time_value_yield"] for m in month_series]}
        chain = agg_chain
        greeks = gex_fields.get("greeks") or {}
        gex_summary = gex_fields.get("gex_summary") or {}
        gex_distribution = gex_fields.get("gex_distribution") or []
    else:
        primary = month_series[0]
        selected_label = primary["month"]
        underlying = primary["underlying"]
        T = primary["T"]
        chain = chains_for_agg[0]
        greeks = primary["greeks"]
        gex_summary = primary["gex_summary"]
        gex_distribution = primary["gex_distribution"]
        iv_smile = primary["iv_smile"]
        max_pain = primary["max_pain"]
        tv_yield = primary["time_value_yield"]
        gex_indicator = (primary.get("indicators") or {}).get("gex")

    from app.services.cn_derivatives_etf_capital import build_capital_curve_by_month

    chains_by_month_cap = {}
    for idx, ms in enumerate(month_series):
        if idx < len(chains_for_agg):
            chains_by_month_cap[ms.get("month")] = chains_for_agg[idx]
    capital_curve = build_capital_curve_by_month(
        chains_by_month_cap,
        underlying=float(underlying or 0.0),
        multiplier=mult,
        margin_rate=margin_rate,
        months=[ms.get("month") for ms in month_series],
    )

    if not gex_indicator:
        from app.services.gex_indicator import run_gex_indicator

        gex_indicator = run_gex_indicator(
            chain or [],
            underlying=float(underlying or 0.0),
            multiplier=mult,
            T=float(T or 30 / 365.0),
            name="GEX",
        )

    return {
        "root": root_u,
        "name_cn": product.get("name_cn") or root_u,
        "available": True,
        "has_option_chain": True,
        "option_feed": product.get("option_feed"),
        "months": months,
        "month": selected_label,
        "underlying": underlying,
        "current_price": underlying,
        "multiplier": mult,
        "margin_rate": margin_rate,
        "T": T,
        "chain": chain,
        "greeks": greeks,
        "gex_summary": gex_summary,
        "gex_distribution": gex_distribution,
        "iv_smile": iv_smile,
        "max_pain": max_pain,
        "time_value_yield": tv_yield,
        "month_series": month_series,
        "capital_curve": capital_curve,
        "indicators": {"gex": gex_indicator},
        "asof": datetime.now().isoformat(timespec="seconds"),
    }


def _normalize_history_date(value: Any) -> Optional[str]:
    text = str(value or "").strip()
    if not text:
        return None
    text = text.replace("/", "-")
    if " " in text:
        text = text.split(" ", 1)[0]
    if len(text) == 8 and text.isdigit():
        return f"{text[0:4]}-{text[4:6]}-{text[6:8]}"
    if len(text) >= 10 and text[4] == "-" and text[7] == "-":
        return text[:10]
    return None


def _parse_history_date(value: str) -> Optional[date]:
    try:
        return datetime.strptime(value[:10], "%Y-%m-%d").date()
    except Exception:
        return None


def _futures_daily_by_date(symbol: str) -> Dict[str, Dict[str, float]]:
    """Map YYYY-MM-DD -> {price, volume, open_interest} for a futures symbol."""
    code = str(symbol or "").strip()
    if not code:
        return {}
    out: Dict[str, Dict[str, float]] = {}
    queries = [code.lower(), code.upper()]
    for query in queries:
        try:
            frame = _ak().futures_zh_daily_sina(symbol=query)
            if frame is None or getattr(frame, "empty", True):
                continue
            for _, row in frame.iterrows():
                date_v = _normalize_history_date(row.get("date") or row.get("datetime"))
                if not date_v:
                    continue
                price = _safe_float(row.get("close") or row.get("settle"))
                oi = _safe_float(row.get("hold") or row.get("open_interest") or row.get("oi"))
                volume = _safe_float(row.get("volume") or row.get("vol"))
                if price <= 0 and oi <= 0 and volume <= 0:
                    continue
                out[date_v] = {"price": price, "volume": volume, "open_interest": oi}
            if out:
                return out
        except Exception as exc:
            logger.debug("futures daily history %s failed: %s", query, exc)
    return out


def _history_month_symbols(root: str) -> List[str]:
    """Prefer listed option months; fall back to spot board contracts."""
    root_u = str(root or "").upper()
    months = [m for m in (_option_months(root_u) or []) if m]
    if months:
        return months[:8]
    board = _spot_board_row(root_u) or {}
    out: List[str] = []
    for key in ("near_contract", "dominant_contract"):
        sym = str(board.get(key) or "").strip().lower()
        if sym and sym not in out:
            out.append(sym)
    return out[:8]


def _resample_slice_dates(dates: List[str], frequency: str) -> List[str]:
    """Keep last trading day in each day/week/month bucket (ascending)."""
    freq = str(frequency or "day").lower()
    if freq in {"d", "1d", "day", "daily"}:
        return list(dates)
    buckets: Dict[str, str] = {}
    for date_v in dates:
        parsed = _parse_history_date(date_v)
        if not parsed:
            continue
        if freq in {"w", "1w", "week", "weekly"}:
            iso = parsed.isocalendar()
            key = f"{iso[0]}-W{iso[1]:02d}"
        else:
            key = f"{parsed.year:04d}-{parsed.month:02d}"
        # dates are ascending; last write wins within bucket
        buckets[key] = date_v
    return list(buckets.values())


def _build_futures_cross_section_slices(
    root: str,
    *,
    days: int,
    frequency: str,
) -> List[Dict[str, Any]]:
    """Rebuild historical term / activity cross-sections from per-month daily bars."""
    root_u = str(root or "").upper()
    product = _product_payload(root_u)
    fut_mult = float(product.get("multiplier") or 1)
    months = _history_month_symbols(root_u)
    if not months:
        return []

    series_by_symbol: Dict[str, Dict[str, Dict[str, float]]] = {}
    all_dates: set = set()
    for symbol in months:
        series = _futures_daily_by_date(symbol)
        if not series:
            continue
        series_by_symbol[symbol.lower()] = series
        all_dates.update(series.keys())

    if not all_dates:
        return []

    ordered = sorted(all_dates)
    cutoff = ordered[-1]
    start_idx = max(0, len(ordered) - max(days, 7))
    window = ordered[start_idx:]
    # Prefer calendar cutoff relative to latest bar when denser history exists
    latest = _parse_history_date(cutoff)
    if latest:
        min_date = (latest - timedelta(days=max(days, 7))).isoformat()
        window = [d for d in ordered if d >= min_date] or window

    sampled = _resample_slice_dates(window, frequency)
    if not sampled:
        return []

    board = _spot_board_row(root_u) or {}
    spot_price = float(board.get("spot_price") or 0.0)
    slices: List[Dict[str, Any]] = []
    for date_v in sampled:
        term_structure = []
        monthly_activity = []
        for symbol, series in series_by_symbol.items():
            bar = series.get(date_v)
            if not bar:
                continue
            price = float(bar.get("price") or 0.0)
            volume = float(bar.get("volume") or 0.0)
            oi = float(bar.get("open_interest") or 0.0)
            basis = (price - spot_price) if spot_price > 0 and price > 0 else None
            point = {
                "symbol": symbol,
                "label": symbol,
                "price": price,
                "volume": volume,
                "open_interest": oi,
                "basis": basis,
                "basis_rate": (basis / spot_price) if basis is not None and spot_price > 0 else None,
                "is_continuous": False,
            }
            term_structure.append(point)
            futures_capital = price * oi * fut_mult
            monthly_activity.append(
                {
                    "symbol": symbol,
                    "month_code": _month_code(symbol),
                    "volume": volume,
                    "open_interest": oi,
                    "price": price,
                    "futures_capital": futures_capital,
                    "option_notional": None,
                    "option_premium": None,
                    "option_call_notional": None,
                    "option_put_notional": None,
                    "combined_capital": futures_capital,
                }
            )
        term_structure.sort(key=lambda row: _month_code(row["symbol"]) or row["symbol"])
        monthly_activity.sort(key=lambda row: row.get("month_code") or row["symbol"])
        if not term_structure:
            continue
        slices.append(
            {
                "date": date_v,
                "label": date_v,
                "term_structure": term_structure,
                "monthly_activity": monthly_activity,
                "options_settled_capital": [],
            }
        )
    return slices


def build_chart_history(
    root: str,
    *,
    chart_key: str,
    days: int = 30,
    month: Optional[str] = None,
    frequency: str = "day",
) -> Dict[str, Any]:
    """History view for chart drill-down.

    2D charts return ``mode=slices``: time-bucketed cross-sections for a slider.
    Frequency controls resampling (day / week / month). Options public history is
    limited, so option charts currently expose a single live slice.
    """
    root_u = str(root or "").upper()
    days = max(7, min(int(days or 30), 365))
    chart = str(chart_key or "").strip()
    freq_raw = str(frequency or "day").strip().lower()
    if freq_raw in {"w", "1w", "week", "weekly"}:
        freq = "week"
    elif freq_raw in {"m", "1m", "month", "monthly"}:
        freq = "month"
    else:
        freq = "day"
    asof = datetime.now().isoformat(timespec="seconds")

    # Futures 2D charts: rebuild month cross-sections from daily bars
    if chart in {"futures.term", "futures.activity", "futures.notional", "futures.premium"}:
        slices = _build_futures_cross_section_slices(root_u, days=days, frequency=freq)
        note = (
            "按选定频率重建各月份合约截面；滑动进度条可查看该时刻二维图。"
            "期权名义/权利金历史链公开数据有限，历史切片中期权字段为空。"
        )
        # Enrich the latest slice with live option capital when available
        if slices and chart in {"futures.notional", "futures.premium", "futures.activity"}:
            try:
                live = build_futures_panel(root_u)
                capital = live.get("options_settled_capital") or []
                activity = live.get("monthly_activity") or []
                if capital:
                    slices[-1]["options_settled_capital"] = capital
                if activity and chart == "futures.activity":
                    # merge option notionals onto matching months of the latest slice
                    by_code = {str(r.get("month_code") or ""): r for r in activity}
                    for row in slices[-1].get("monthly_activity") or []:
                        live_row = by_code.get(str(row.get("month_code") or ""))
                        if not live_row:
                            continue
                        row["option_notional"] = live_row.get("option_notional")
                        row["option_premium"] = live_row.get("option_premium")
                        row["option_call_notional"] = live_row.get("option_call_notional")
                        row["option_put_notional"] = live_row.get("option_put_notional")
                        fut_cap = float(row.get("futures_capital") or 0.0)
                        opt_n = float(live_row.get("option_notional") or 0.0)
                        row["combined_capital"] = fut_cap + opt_n
            except Exception as exc:
                logger.debug("enrich latest futures slice failed: %s", exc)
        return {
            "root": root_u,
            "chart_key": chart,
            "mode": "slices",
            "frequency": freq,
            "days": days,
            "slices": slices,
            "note": note,
            "asof": asof,
        }

    # Options 2D charts: live snapshot only (no public historical option chain)
    if chart.startswith("options"):
        options = build_options_panel(root_u, month=month or "all")
        slice_payload = {
            "date": asof[:10],
            "label": "当前",
            "current_price": options.get("current_price"),
            "gex_distribution": options.get("gex_distribution") or [],
            "gex_summary": options.get("gex_summary") or {},
            "month_series": options.get("month_series") or [],
            "month": options.get("month"),
        }
        return {
            "root": root_u,
            "chart_key": chart,
            "mode": "slices",
            "frequency": freq,
            "days": days,
            "slices": [slice_payload],
            "note": "期权链公开历史有限，暂仅提供当前截面；接入本地快照后可按频率滑动回放。",
            "asof": asof,
        }

    # Fallback: continuous daily series (legacy line mode)
    product = _product_payload(root_u)
    symbol = str(product.get("continuous_symbol") or f"{root_u}0")
    points = []
    try:
        frame = _ak().futures_zh_daily_sina(symbol=symbol)
        if frame is not None and not getattr(frame, "empty", True):
            tail = frame.tail(days)
            mult = float(product.get("multiplier") or 1)
            for _, row in tail.iterrows():
                price = _safe_float(row.get("close") or row.get("settle") or row.get("hold"))
                oi = _safe_float(row.get("hold") or row.get("open_interest") or row.get("oi"))
                volume = _safe_float(row.get("volume") or row.get("vol"))
                date_v = _normalize_history_date(row.get("date") or row.get("datetime")) or ""
                points.append(
                    {
                        "date": date_v,
                        "price": price,
                        "open_interest": oi,
                        "volume": volume,
                        "futures_capital": price * oi * mult,
                    }
                )
    except Exception as exc:
        logger.warning("chart history futures daily failed root=%s: %s", root_u, exc)
    return {
        "root": root_u,
        "chart_key": chart,
        "mode": "daily",
        "frequency": freq,
        "days": days,
        "points": points,
        "note": "连续合约日线沉淀资金 = 收盘价 × 持仓 × 乘数。",
        "asof": asof,
    }


def build_overview(root: str, month: Optional[str] = None) -> Dict[str, Any]:
    started = time.time()
    root_u = str(root or "").upper()
    return {
        "root": root_u,
        "name_cn": CN_NAME.get(root_u, root_u),
        "product": _product_payload(root_u),
        "spot": build_spot_panel(root_u),
        "futures": build_futures_panel(root_u),
        "options": build_options_panel(root_u, month=month),
        "elapsed_ms": int((time.time() - started) * 1000),
        "asof": datetime.now().isoformat(timespec="seconds"),
    }
