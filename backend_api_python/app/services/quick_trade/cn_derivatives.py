"""Quick Trade helpers for mainland China futures and futures-options."""

from __future__ import annotations

from typing import Any, Dict, Optional, Tuple

from app.markets.cn_futures import is_cn_derivative, is_cn_futures_option
from app.utils.logger import get_logger

logger = get_logger(__name__)

CN_QUICK_TRADE_EXCHANGES = {"ctp", "qmt"}
CN_QUICK_TRADE_MARKETS = {
    "CNFutures",
    "CNFuturesOptions",
    "CNIndexFutures",
    "CNIndexOptions",
}
CN_MARKET_TYPES = {"futures", "options"}


def is_cn_quick_trade_exchange(exchange_id: str) -> bool:
    return str(exchange_id or "").strip().lower() in CN_QUICK_TRADE_EXCHANGES


def is_cn_quick_trade_market(market: str) -> bool:
    return str(market or "").strip() in CN_QUICK_TRADE_MARKETS


def lots_from_amount(amount: float) -> int:
    """Quick Trade ``amount`` is contract lots for CTP/QMT (not USDT)."""
    lots = int(round(float(amount or 0.0)))
    if lots <= 0:
        raise ValueError("amount must be an integer lot size >= 1 for China futures/options")
    return lots


def resolve_cn_market_type(
    *,
    market_type: str = "",
    symbol: str = "",
    market: str = "",
) -> str:
    raw = str(market_type or "").strip().lower()
    if raw in ("option", "options"):
        return "options"
    if raw in ("futures", "future"):
        return "futures"
    # Crypto aliases must not stick when the instrument is a CN listed contract.
    if raw in ("spot", "swap", "perp", "perpetual"):
        raw = ""
    mc = str(market or "").strip()
    if mc in ("CNFuturesOptions", "CNIndexOptions"):
        return "options"
    if mc in ("CNFutures", "CNIndexFutures"):
        return "futures"
    try:
        from app.markets.cn_futures import parse_cn_option_symbol

        parsed = parse_cn_option_symbol(symbol) or {}
        if parsed.get("option_type"):
            return "options"
    except Exception:
        pass
    if is_cn_derivative(symbol):
        return "futures"
    return raw or "futures"


def side_offset_to_signal(*, side: str, offset: str = "open") -> str:
    side_l = str(side or "").strip().lower()
    offset_l = str(offset or "open").strip().lower().replace("-", "_")
    is_close = offset_l in {"close", "close_today", "closetoday", "close_yesterday", "closeyesterday"}
    if side_l in {"buy", "long"}:
        return "close_short" if is_close else "open_long"
    if side_l in {"sell", "short"}:
        return "close_long" if is_close else "open_short"
    raise ValueError("side must be buy/sell (or long/short)")


def resolve_cn_order_price(*, symbol: str, price: float = 0.0, market: str = "") -> float:
    if float(price or 0.0) > 0:
        return float(price)
    try:
        from app.services.ctp_md.service import ctp_ticker_for_symbol

        ticker = ctp_ticker_for_symbol(symbol) or {}
        last = float(ticker.get("last") or ticker.get("price") or 0.0)
        if last > 0:
            return last
    except Exception as exc:
        logger.debug("CTP tick price unavailable for %s: %s", symbol, exc)
    try:
        from app.data_sources.factory import DataSourceFactory

        market_key = market or ("CNFuturesOptions" if is_cn_futures_option(symbol) else "CNFutures")
        source = DataSourceFactory.get_source(market_key)
        ticker = source.get_ticker(symbol) if source is not None else None
        if isinstance(ticker, dict):
            last = float(ticker.get("last") or ticker.get("price") or ticker.get("close") or 0.0)
            if last > 0:
                return last
    except Exception as exc:
        logger.debug("CN futures ticker unavailable for %s: %s", symbol, exc)
    return 0.0


def parse_cn_balance(raw: Any) -> Dict[str, Any]:
    result = {"available": 0.0, "total": 0.0, "currency": "CNY"}
    if not isinstance(raw, dict):
        return result
    available = raw.get("available")
    total = raw.get("cash") or raw.get("balance") or raw.get("total") or available
    try:
        result["available"] = float(available or 0.0)
    except (TypeError, ValueError):
        result["available"] = 0.0
    try:
        result["total"] = float(total or result["available"] or 0.0)
    except (TypeError, ValueError):
        result["total"] = result["available"]
    result["currency"] = str(raw.get("currency") or "CNY")
    return result


def place_cn_quick_order(
    client: Any,
    *,
    symbol: str,
    side: str,
    amount: float,
    price: float = 0.0,
    order_type: str = "market",
    offset: str = "open",
    market: str = "",
    exchange_config: Optional[Dict[str, Any]] = None,
):
    from app.services.live_trading.execution import place_order_from_signal

    lots = lots_from_amount(amount)
    order_price = resolve_cn_order_price(symbol=symbol, price=price, market=market)
    if str(order_type or "market").strip().lower() == "limit" and order_price <= 0:
        raise ValueError("price required for limit orders")
    if str(order_type or "market").strip().lower() != "limit" and order_price <= 0:
        # Simulation ledger requires a positive price; live CTP market orders may be 0.
        mode = str((exchange_config or {}).get("mode") or (exchange_config or {}).get("environment") or "").lower()
        if mode in ("", "demo", "paper", "simulate", "simulation", "testnet"):
            raise ValueError("unable to resolve a reference price for this China futures/options contract")
    cfg = dict(exchange_config or {})
    cfg["price"] = order_price
    cfg["order_type"] = order_type
    signal_type = side_offset_to_signal(side=side, offset=offset)
    return place_order_from_signal(
        client=client,
        signal_type=signal_type,
        symbol=symbol,
        amount=float(lots),
        market_type=resolve_cn_market_type(symbol=symbol, market=market),
        exchange_config=cfg,
    )


def split_cn_display_symbol(symbol: str) -> str:
    """Keep listed option codes (m2609-C-2800) intact instead of fake crypto pairs."""
    raw = str(symbol or "").strip()
    if not raw:
        return raw
    if is_cn_derivative(raw):
        if ":" in raw:
            return raw.split(":", 1)[-1].strip()
        return raw
    return raw
