"""Agent Gateway options desk: chain selection, combo estimate/order, IV rank."""

from __future__ import annotations

import os
import uuid
from datetime import date
from typing import Any

from flask import request

from app.markets.cn_options import cn_etf_stock_symbol
from app.services.kline import KlineService
from app.services.options_desk.chain import catalog_by_symbol, query_option_chain
from app.services.options_desk.combo import ComboError, estimate_combo, parse_combo_legs
from app.services.options_desk.iv_rank import iv_rank_from_closes
from app.utils.agent_auth import (
    SCOPE_R,
    SCOPE_T,
    agent_required,
    current_token,
    current_user_id,
    instrument_allowed,
    market_allowed,
    paper_only,
    with_idempotency,
)
from app.utils.agent_jobs import record_completed_job
from app.utils.db import get_db_connection
from app.utils.logger import get_logger

from . import agent_v1_bp
from ._helpers import clip_int, envelope, error, get_json_or_400, optional_float, optional_int

logger = get_logger(__name__)
_kline = KlineService()


def _live_trading_kill_switch() -> bool:
    return os.getenv("AGENT_LIVE_TRADING_ENABLED", "false").lower() in ("1", "true", "yes")


def _kline_loader(market: str, symbol: str, timeframe: str = "1D", limit: int = 300):
    return _kline.get_kline(market=market, symbol=symbol, timeframe=timeframe, limit=limit) or []


def _closes(market: str, symbol: str, *, limit: int = 400) -> list[float]:
    rows = _kline_loader(market, symbol, "1D", limit)
    closes: list[float] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        value = row.get("close", row.get("c", row.get("Close")))
        try:
            number = float(value)
        except (TypeError, ValueError):
            continue
        if number > 0:
            closes.append(number)
    return closes


def _last_price(market: str, symbol: str) -> float | None:
    for timeframe in ("1m", "1D"):
        try:
            rows = _kline_loader(market, symbol, timeframe, 1)
        except Exception:
            rows = []
        if not rows:
            continue
        last = rows[-1]
        if isinstance(last, dict):
            for key in ("close", "c", "Close"):
                value = last.get(key)
                if value is not None:
                    try:
                        return float(value)
                    except (TypeError, ValueError):
                        continue
    return None


def _enrich_legs_from_catalog(legs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    found = catalog_by_symbol(item["symbol"] for item in legs)
    out = []
    for item in legs:
        catalog = found.get(item["symbol"]) or {}
        merged = dict(item)
        merged["market"] = merged.get("market") or catalog.get("market") or "CNIndexOptions"
        merged["call_put"] = merged.get("call_put") or catalog.get("call_put")
        if merged.get("strike") is None:
            merged["strike"] = catalog.get("strike")
        merged["expire"] = merged.get("expire") or catalog.get("expire_date") or catalog.get("expire")
        merged["underlying"] = merged.get("underlying") or catalog.get("underlying")
        merged["kind"] = catalog.get("kind") or merged.get("kind") or "etf"
        if catalog.get("lot_size"):
            merged["multiplier"] = float(catalog.get("lot_size") or merged.get("multiplier") or 10000)
        out.append(merged)
    return out


@agent_v1_bp.route("/options/chain", methods=["GET"])
@agent_required(SCOPE_R)
def options_chain():
    """Select listed option legs by underlying, DTE, and delta."""
    underlying = (request.args.get("underlying") or request.args.get("symbol") or "").strip()
    if not underlying:
        return error(400, "underlying is required")
    if not instrument_allowed(underlying) and not instrument_allowed(cn_etf_stock_symbol(underlying)):
        return error(403, f"Instrument not allowed: {underlying}", http=403)

    try:
        payload = query_option_chain(
            underlying=underlying,
            dte_min=optional_int(request.args.get("dte_min"), lo=0, hi=800),
            dte_max=optional_int(request.args.get("dte_max"), lo=0, hi=800),
            delta_min=optional_float(request.args.get("delta_min"), lo=-1.5, hi=1.5),
            delta_max=optional_float(request.args.get("delta_max"), lo=-1.5, hi=1.5),
            side=request.args.get("side") or request.args.get("call_put"),
            target_dte=optional_int(request.args.get("target_dte"), lo=0, hi=800),
            target_delta=optional_float(request.args.get("target_delta"), lo=-1.5, hi=1.5),
            kind=(request.args.get("kind") or "etf").strip() or "etf",
            limit=clip_int(request.args.get("limit"), default=40, lo=1, hi=200),
            kline_loader=_kline_loader,
        )
    except ValueError as exc:
        return error(400, str(exc))
    except Exception as exc:
        logger.error("options chain failed: %s", exc, exc_info=True)
        return error(502, "option chain lookup failed", details=str(exc), retriable=True, http=502)
    return envelope(payload)


@agent_v1_bp.route("/options/combo/estimate", methods=["POST"])
@agent_required(SCOPE_R)
def options_combo_estimate():
    """Combo-level greeks and a conservative margin estimate."""
    body, err = get_json_or_400()
    if err:
        return err
    try:
        legs = _enrich_legs_from_catalog(parse_combo_legs(body.get("legs")))
    except ComboError as exc:
        return error(400, str(exc), details={"code": exc.code})

    underlying = str(body.get("underlying") or legs[0].get("underlying") or "").strip()
    spot = optional_float(body.get("spot"))
    sigma = optional_float(body.get("sigma"), lo=0.01, hi=5.0) or 0.20
    if spot is None and underlying:
        spot = _last_price("CNStock", cn_etf_stock_symbol(underlying))
        if spot is None:
            closes = _closes("CNStock", cn_etf_stock_symbol(underlying), limit=30)
            spot = closes[-1] if closes else None
    dte = optional_int(body.get("dte"), lo=0, hi=800)
    estimate = estimate_combo(legs, spot=spot, sigma=sigma, dte=dte)
    estimate["underlying"] = underlying or None
    return envelope(estimate)


def _record_paper_combo(legs: list[dict[str, Any]], *, combo_uid: str, fills: list[dict[str, Any]]) -> list[dict[str, Any]]:
    user_id = current_user_id()
    token_id = int(current_token().get("id") or 0)
    recorded = []
    with get_db_connection() as db:
        cur = db.cursor()
        try:
            for leg, fill in zip(legs, fills):
                order_uid = uuid.uuid4().hex
                qty = float(leg["qty"])
                fill_price = fill.get("fill_price")
                fill_value = (fill_price * qty) if fill_price is not None else None
                note = (
                    f"combo={combo_uid} leg={leg['index']}/{len(legs)} "
                    f"source={fill.get('fill_source') or 'paper'}"
                )
                cur.execute(
                    """
                    INSERT INTO qd_agent_paper_orders
                      (order_uid, user_id, agent_token_id, market, symbol, side, order_type,
                       qty, limit_price, fill_price, fill_value, status, note)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        order_uid, user_id, token_id,
                        leg.get("market") or "CNIndexOptions",
                        leg["symbol"],
                        leg["side"],
                        leg.get("order_type") or "market",
                        qty,
                        fill.get("limit_price"),
                        fill_price,
                        fill_value,
                        fill.get("status") or "filled",
                        note,
                    ),
                )
                recorded.append(
                    {
                        "order_uid": order_uid,
                        "leg_index": leg["index"],
                        "market": leg.get("market") or "CNIndexOptions",
                        "symbol": leg["symbol"],
                        "side": leg["side"],
                        "qty": qty,
                        "fill_price": fill_price,
                        "status": fill.get("status") or "filled",
                        "fill_source": fill.get("fill_source"),
                        "paper": True,
                    }
                )
            db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            cur.close()
    return recorded


@agent_v1_bp.route("/options/combo/order", methods=["POST"])
@agent_required(SCOPE_T)
def options_combo_order():
    """Atomically record a 2-4 leg combo. Paper is all-or-nothing; live is not enabled."""
    body, err = get_json_or_400()
    if err:
        return err
    try:
        legs = _enrich_legs_from_catalog(parse_combo_legs(body.get("legs")))
    except ComboError as exc:
        return error(400, str(exc), details={"code": exc.code})

    for leg in legs:
        if not market_allowed(leg.get("market") or "CNIndexOptions"):
            return error(403, f"Market not allowed: {leg.get('market')}", http=403)
        if not instrument_allowed(leg["symbol"]):
            return error(403, f"Instrument not allowed: {leg['symbol']}", http=403)

    want_live = (not paper_only()) and _live_trading_kill_switch() and bool(body.get("live"))
    if want_live:
        return error(
            501,
            "Four-leg combo live execution is not wired to CTP combo instructions. "
            "Paper combo orders are atomic; live legs must be reviewed sequentially.",
            http=501,
        )

    with with_idempotency("options_combo_order") as existing:
        if existing is not None:
            return existing

        estimate = estimate_combo(
            legs,
            spot=optional_float(body.get("spot")),
            sigma=optional_float(body.get("sigma"), lo=0.01, hi=5.0) or 0.20,
            dte=optional_int(body.get("dte"), lo=0, hi=800),
        )
        fills = []
        for index, leg in enumerate(legs):
            last = _last_price(leg.get("market") or "CNIndexOptions", leg["symbol"])
            source = "last_price"
            if last is None:
                theo = (estimate.get("legs") or [{}])[index].get("greeks") or {}
                last = theo.get("price")
                source = "theoretical"
            if last is None:
                return error(
                    422,
                    f"No fill price for {leg['symbol']}; combo was not recorded",
                    details={"leg": leg["symbol"]},
                    http=422,
                )
            fills.append(
                {
                    "fill_price": float(last),
                    "status": "filled",
                    "fill_source": source,
                    "limit_price": leg.get("limit_price"),
                }
            )

        combo_uid = uuid.uuid4().hex
        try:
            orders = _record_paper_combo(legs, combo_uid=combo_uid, fills=fills)
        except Exception as exc:
            logger.error("paper combo insert failed: %s", exc, exc_info=True)
            return error(500, "failed to record atomic paper combo", details=str(exc), http=500)

        result = {
            "combo_uid": combo_uid,
            "atomic": True,
            "paper": True,
            "status": "filled",
            "legs": orders,
            "estimate": {
                "greeks": estimate.get("greeks"),
                "margin_estimate": estimate.get("margin_estimate"),
                "margin_method": estimate.get("margin_method"),
                "conservative": True,
            },
        }
        try:
            record_completed_job(
                user_id=current_user_id(),
                agent_token_id=int(current_token().get("id") or 0),
                kind="options_combo_order",
                request_payload={
                    "combo_uid": combo_uid,
                    "legs": [
                        {"symbol": item["symbol"], "side": item["side"], "qty": item["qty"]}
                        for item in orders
                    ],
                },
                result=result,
                idempotency_key=request.headers.get("Idempotency-Key"),
            )
        except Exception as exc:
            logger.warning("combo job record failed: %s", exc)
        return envelope(result)


@agent_v1_bp.route("/options/iv-rank", methods=["GET"])
@agent_required(SCOPE_R)
def options_iv_rank():
    """IV Rank / Percentile proxied by realized vol of the underlying."""
    symbol = (request.args.get("symbol") or request.args.get("underlying") or "").strip()
    if not symbol:
        return error(400, "symbol is required")
    if not instrument_allowed(symbol) and not instrument_allowed(cn_etf_stock_symbol(symbol)):
        return error(403, f"Instrument not allowed: {symbol}", http=403)
    lookback = clip_int(request.args.get("lookback"), default=252, lo=20, hi=1000)
    window = clip_int(request.args.get("window"), default=20, lo=5, hi=60)
    stock = cn_etf_stock_symbol(symbol) if len(symbol.split(".")[0]) == 6 else symbol
    closes = _closes("CNStock", stock, limit=max(lookback + window + 5, 80))
    payload = iv_rank_from_closes(closes, window=window, lookback=lookback)
    payload.update(
        {
            "symbol": stock,
            "as_of": date.today().isoformat(),
            "bars": len(closes),
        }
    )
    return envelope(payload)
