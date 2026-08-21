"""CN futures & derivatives analytics for the market-composite workbench."""

from __future__ import annotations

import math
import time
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional

from app.markets.cn_futures import get_future_product, list_products
from app.utils.logger import get_logger

logger = get_logger(__name__)

SINA_OPTION_NAME: Dict[str, str] = {
    "A": "黄大豆1号期权",
    "B": "黄大豆2号期权",
    "M": "豆粕期权",
    "Y": "豆油期权",
    "P": "棕榈油期权",
    "C": "玉米期权",
    "CS": "玉米淀粉期权",
    "L": "聚乙烯期权",
    "V": "PVC期权",
    "PP": "聚丙烯期权",
    "I": "铁矿石期权",
    "JM": "焦煤期权",
    "EG": "乙二醇期权",
    "EB": "苯乙烯期权",
    "PG": "液化石油气期权",
    "LH": "生猪期权",
    "RB": "螺纹钢期权",
    "HC": "热轧卷板期权",
    "CU": "铜期权",
    "AL": "铝期权",
    "ZN": "锌期权",
    "NI": "镍期权",
    "SN": "锡期权",
    "AU": "黄金期权",
    "AG": "白银期权",
    "RU": "橡胶期权",
    "BU": "沥青期权",
    "FU": "燃油期权",
    "SP": "纸浆期权",
    "SC": "原油期权",
    "NR": "20号胶期权",
    "LU": "低硫燃料油期权",
    "BC": "国际铜期权",
    "SR": "白糖期权",
    "CF": "棉花期权",
    "TA": "PTA期权",
    "MA": "甲醇期权",
    "FG": "玻璃期权",
    "OI": "菜籽油期权",
    "RM": "菜粕期权",
    "SF": "硅铁期权",
    "SM": "锰硅期权",
    "AP": "苹果期权",
    "CJ": "红枣期权",
    "UR": "尿素期权",
    "SA": "纯碱期权",
    "PF": "短纤期权",
    "PK": "花生期权",
    "SI": "工业硅期权",
    "LC": "碳酸锂期权",
}

CN_NAME: Dict[str, str] = {
    "IF": "沪深300股指期货",
    "IH": "上证50股指期货",
    "IC": "中证500股指期货",
    "IM": "中证1000股指期货",
    "RB": "螺纹钢",
    "HC": "热轧卷板",
    "I": "铁矿石",
    "M": "豆粕",
    "Y": "豆油",
    "P": "棕榈油",
    "C": "玉米",
    "A": "黄大豆1号",
    "AU": "黄金",
    "AG": "白银",
    "CU": "铜",
    "AL": "铝",
    "ZN": "锌",
    "NI": "镍",
    "RU": "橡胶",
    "BU": "沥青",
    "FU": "燃油",
    "SC": "原油",
    "SR": "白糖",
    "CF": "棉花",
    "TA": "PTA",
    "MA": "甲醇",
    "FG": "玻璃",
    "OI": "菜籽油",
    "RM": "菜粕",
    "SA": "纯碱",
    "JM": "焦煤",
    "J": "焦炭",
    "L": "聚乙烯",
    "PP": "聚丙烯",
    "V": "PVC",
    "EG": "乙二醇",
    "EB": "苯乙烯",
    "PG": "LPG",
    "LH": "生猪",
    "SI": "工业硅",
    "LC": "碳酸锂",
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
    if not product:
        return {
            "root": root_u,
            "name": root_u,
            "name_cn": CN_NAME.get(root_u, root_u),
            "has_options": root_u in SINA_OPTION_NAME,
            "multiplier": 10.0,
            "option_multiplier": 10.0,
            "exchange": "",
            "product_class": "commodity",
            "option_sina_name": SINA_OPTION_NAME.get(root_u),
            "continuous_symbol": f"{root_u}0",
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
        "has_options": bool(product.has_options or product.root in SINA_OPTION_NAME),
        "product_class": product.product_class,
        "option_multiplier": float(product.option_multiplier or product.multiplier or 1),
        "option_sina_name": SINA_OPTION_NAME.get(product.root),
        "continuous_symbol": f"{product.root}0",
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
    name = SINA_OPTION_NAME.get(str(root or "").upper())
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


def _mid(bid: float, ask: float, last: float) -> float:
    if bid > 0 and ask > 0:
        return (bid + ask) / 2.0
    if last > 0:
        return last
    return max(bid, ask, 0.0)


def _option_chain_table(root: str, month_contract: str) -> List[Dict[str, Any]]:
    name = SINA_OPTION_NAME.get(str(root or "").upper())
    contract = str(month_contract or "").strip().lower()
    if not name or not contract:
        return []
    try:
        frame = _ak().option_commodity_contract_table_sina(symbol=name, contract=contract)
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
            rows.append(
                {
                    "strike": strike,
                    "call_symbol": str(item.get("看涨合约-看涨期权合约") or ""),
                    "put_symbol": str(item.get("看跌合约-看跌期权合约") or ""),
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
    except Exception as exc:
        logger.warning("option chain %s/%s failed: %s", root, contract, exc)
        return []


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
    points = []
    total_call_gex = 0.0
    total_put_gex = 0.0
    total_call_oi = 0.0
    total_put_oi = 0.0
    portfolio = {"delta": 0.0, "gamma": 0.0, "vega": 0.0, "theta": 0.0}
    smile = []

    for row in chain:
        k = float(row["strike"])
        call_iv = (
            implied_vol_black76(row["call_mid"], underlying, k, T, True)
            if row.get("call_mid", 0) > 0
            else None
        )
        put_iv = (
            implied_vol_black76(row["put_mid"], underlying, k, T, False)
            if row.get("put_mid", 0) > 0
            else None
        )
        iv = call_iv or put_iv or 0.25
        call_greeks = black76_greeks(underlying, k, T, call_iv or iv, True)
        put_greeks = black76_greeks(underlying, k, T, put_iv or iv, False)
        call_oi = float(row.get("call_oi") or 0)
        put_oi = float(row.get("put_oi") or 0)
        call_gex = call_greeks["gamma"] * call_oi * multiplier * underlying
        put_gex = -put_greeks["gamma"] * put_oi * multiplier * underlying
        total_call_gex += call_gex
        total_put_gex += put_gex
        total_call_oi += call_oi
        total_put_oi += put_oi
        portfolio["delta"] += (call_greeks["delta"] * call_oi + put_greeks["delta"] * put_oi) * multiplier
        portfolio["gamma"] += (call_greeks["gamma"] * call_oi + put_greeks["gamma"] * put_oi) * multiplier
        portfolio["vega"] += (call_greeks["vega"] * call_oi + put_greeks["vega"] * put_oi) * multiplier
        portfolio["theta"] += (call_greeks["theta"] * call_oi + put_greeks["theta"] * put_oi) * multiplier
        points.append(
            {
                "strike": k,
                "call_oi": call_oi,
                "put_oi": put_oi,
                "total_oi": call_oi + put_oi,
                "net_oi": call_oi - put_oi,
                "call_gex": call_gex,
                "put_gex": put_gex,
                "net_gex": call_gex + put_gex,
                "call_iv": call_iv,
                "put_iv": put_iv,
            }
        )
        if call_iv:
            smile.append({"strike": k, "iv": call_iv, "side": "call"})
        if put_iv:
            smile.append({"strike": k, "iv": put_iv, "side": "put"})

    call_wall = max(points, key=lambda p: p["call_oi"])["strike"] if points else None
    put_wall = max(points, key=lambda p: p["put_oi"])["strike"] if points else None
    pin = max(points, key=lambda p: p["call_oi"] + p["put_oi"])["strike"] if points else None

    flip = None
    cum = 0.0
    prev_cum = None
    for point in sorted(points, key=lambda p: p["strike"]):
        cum += point["net_gex"]
        if prev_cum is not None and prev_cum * cum <= 0 and point["strike"] >= underlying * 0.8:
            flip = point["strike"]
            break
        prev_cum = cum

    return {
        "points": points,
        "summary": {
            "net_gex": total_call_gex + total_put_gex,
            "call_gex": total_call_gex,
            "put_gex": total_put_gex,
            "call_oi": total_call_oi,
            "put_oi": total_put_oi,
            "call_wall": call_wall,
            "put_wall": put_wall,
            "pin": pin,
            "flip": flip,
            "underlying": underlying,
        },
        "portfolio_greeks": portfolio,
        "iv_smile": smile,
    }


def build_spot_panel(root: str) -> Dict[str, Any]:
    root_u = str(root or "").upper()
    product = _product_payload(root_u)
    board = _spot_board_row(root_u)
    continuous = _futures_zh_spot(f"{root_u}0")
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
    candidates.append(f"{root_u.lower()}0")

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
    for point in curve:
        if point["is_continuous"]:
            continue
        code = _month_code(point["symbol"])
        opt = capital_by_month.get(code) or {}
        monthly_activity.append(
            {
                "symbol": point["symbol"],
                "month_code": code,
                "volume": point["volume"],
                "open_interest": point["open_interest"],
                "price": point["price"],
                "option_notional": opt.get("notional"),
                "option_premium": opt.get("premium"),
                "option_call_notional": opt.get("call_notional"),
                "option_put_notional": opt.get("put_notional"),
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


def build_options_panel(root: str, month: Optional[str] = None) -> Dict[str, Any]:
    root_u = str(root or "").upper()
    product = _product_payload(root_u)
    months = _option_months(root_u)
    if not months:
        return {
            "root": root_u,
            "name_cn": product.get("name_cn") or root_u,
            "months": [],
            "month": None,
            "available": False,
            "message": "该品种暂无新浪商品期权链数据（股指期权或未上市品种）。",
            "asof": datetime.now().isoformat(timespec="seconds"),
        }
    selected = (month or months[0]).lower()
    if selected not in {m.lower() for m in months}:
        selected = months[0].lower()
    chain = _option_chain_table(root_u, selected)
    board = _spot_board_row(root_u)
    fut = _futures_zh_spot(selected) or _futures_zh_spot(f"{root_u}0")
    underlying = (
        (fut or {}).get("price")
        or (board or {}).get("dominant_contract_price")
        or (board or {}).get("spot_price")
        or 0.0
    )
    T = _year_fraction_to_month(selected)
    mult = float(product.get("option_multiplier") or product.get("multiplier") or 1)
    margin_rate = float(product.get("option_seller_margin_rate") or 0.12)
    if chain and underlying > 0:
        gex = compute_gex(chain, underlying=underlying, multiplier=mult, T=T)
        max_pain = compute_max_pain(chain)
        tv_yield = _time_value_annualized_yield(
            chain,
            underlying=underlying,
            multiplier=mult,
            margin_rate=margin_rate,
            T=T,
            month=selected,
        )
    else:
        gex = {"points": [], "summary": {}, "portfolio_greeks": {}, "iv_smile": []}
        max_pain = None
        tv_yield = {"month": selected, "T": T, "call": [], "put": []}
    return {
        "root": root_u,
        "name_cn": product.get("name_cn") or root_u,
        "available": True,
        "months": months,
        "month": selected,
        "underlying": underlying,
        "current_price": underlying,
        "multiplier": mult,
        "margin_rate": margin_rate,
        "T": T,
        "chain": chain,
        "greeks": gex.get("portfolio_greeks") or {},
        "gex_summary": gex.get("summary") or {},
        "gex_distribution": gex.get("points") or [],
        "iv_smile": gex.get("iv_smile") or [],
        "max_pain": max_pain,
        "time_value_yield": tv_yield,
        "asof": datetime.now().isoformat(timespec="seconds"),
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
