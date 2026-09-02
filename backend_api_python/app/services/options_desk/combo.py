"""Combo leg parsing, conservative margin, and paper-atomic order support."""

from __future__ import annotations

import math
from typing import Any, Mapping, Sequence

from app.services.options_desk.greeks import (
    align_strike_to_spot,
    black_scholes_greeks,
    combo_greeks,
)


class ComboError(ValueError):
    def __init__(self, code: str, message: str | None = None):
        super().__init__(message or code)
        self.code = code


def parse_combo_legs(
    legs: object,
    *,
    min_legs: int = 2,
    max_legs: int = 4,
) -> list[dict[str, Any]]:
    if not isinstance(legs, (list, tuple)):
        raise ComboError("combo.legsRequired", "legs must be a list of 2-4 option legs")
    if not (min_legs <= len(legs) <= max_legs):
        raise ComboError("combo.legCount", f"combo requires {min_legs}-{max_legs} legs, got {len(legs)}")
    parsed: list[dict[str, Any]] = []
    for index, raw in enumerate(legs, start=1):
        if not isinstance(raw, Mapping):
            raise ComboError("combo.legInvalid", f"leg {index} must be an object")
        symbol = str(raw.get("symbol") or "").strip()
        if not symbol:
            raise ComboError("combo.symbolRequired", f"leg {index} is missing symbol")
        market = str(raw.get("market") or "CNIndexOptions").strip() or "CNIndexOptions"
        qty_raw = raw.get("qty", raw.get("quantity", raw.get("amount")))
        side = str(raw.get("side") or "").strip().lower()
        if side in {"buy", "long", "bid"}:
            side = "buy"
        elif side in {"sell", "short", "ask"}:
            side = "sell"
        elif qty_raw is not None:
            try:
                signed = float(qty_raw)
            except (TypeError, ValueError) as exc:
                raise ComboError("combo.qtyInvalid", f"leg {index} qty is invalid") from exc
            side = "buy" if signed >= 0 else "sell"
            qty_raw = abs(signed)
        else:
            raise ComboError("combo.sideRequired", f"leg {index} needs side or signed qty")
        try:
            qty = abs(float(qty_raw))
        except (TypeError, ValueError) as exc:
            raise ComboError("combo.qtyInvalid", f"leg {index} qty is invalid") from exc
        if not math.isfinite(qty) or qty <= 0:
            raise ComboError("combo.qtyInvalid", f"leg {index} qty must be a positive finite number")
        call_put = str(raw.get("call_put") or raw.get("cp") or raw.get("right") or "").strip().upper()
        if call_put in {"CALL", "C"}:
            call_put = "C"
        elif call_put in {"PUT", "P"}:
            call_put = "P"
        elif not call_put:
            call_put = ""
        else:
            raise ComboError("combo.callPutInvalid", f"leg {index} call_put must be C or P")
        strike = raw.get("strike")
        try:
            strike_f = float(strike) if strike not in (None, "") else None
        except (TypeError, ValueError) as exc:
            raise ComboError("combo.strikeInvalid", f"leg {index} strike is invalid") from exc
        multiplier = raw.get("multiplier") or raw.get("lot_size") or raw.get("lotSize")
        try:
            multiplier_f = float(multiplier) if multiplier not in (None, "") else 10000.0
        except (TypeError, ValueError):
            multiplier_f = 10000.0
        premium = raw.get("premium") or raw.get("price") or raw.get("limit_price")
        try:
            premium_f = float(premium) if premium not in (None, "") else None
        except (TypeError, ValueError):
            premium_f = None
        parsed.append(
            {
                "index": index,
                "market": market,
                "symbol": symbol,
                "side": side,
                "qty": qty,
                "qty_signed": qty if side == "buy" else -qty,
                "call_put": call_put or None,
                "strike": strike_f,
                "expire": raw.get("expire") or raw.get("expire_date"),
                "underlying": str(raw.get("underlying") or "").strip() or None,
                "kind": str(raw.get("kind") or "etf").strip() or "etf",
                "multiplier": multiplier_f,
                "premium": premium_f,
                "order_type": str(raw.get("order_type") or raw.get("orderType") or "market").strip().lower(),
                "limit_price": raw.get("limit_price") or raw.get("limitPrice"),
            }
        )
    return parsed


def _short_call_margin(*, spot: float, strike: float, premium: float, multiplier: float) -> float:
    otm = max(strike - spot, 0.0)
    per_share = premium + max(0.12 * spot - otm, 0.07 * spot)
    return max(per_share, 0.0) * multiplier


def _short_put_margin(*, spot: float, strike: float, premium: float, multiplier: float) -> float:
    otm = max(spot - strike, 0.0)
    per_share = premium + max(0.12 * spot - otm, 0.07 * strike)
    return max(per_share, 0.0) * multiplier


def _defined_risk_width(legs: Sequence[Mapping[str, Any]], call_put: str) -> float | None:
    same = [leg for leg in legs if str(leg.get("call_put") or "").upper() == call_put]
    shorts = [leg for leg in same if float(leg.get("qty_signed") or 0) < 0]
    longs = [leg for leg in same if float(leg.get("qty_signed") or 0) > 0]
    if not shorts or not longs:
        return None
    widths: list[float] = []
    for short in shorts:
        short_k = float(short.get("strike") or 0)
        short_qty = abs(float(short.get("qty_signed") or 0))
        short_mult = float(short.get("multiplier") or 10000)
        for long in longs:
            long_k = float(long.get("strike") or 0)
            covered = min(short_qty, abs(float(long.get("qty_signed") or 0)))
            widths.append(abs(short_k - long_k) * covered * short_mult)
    return max(widths) if widths else None


def estimate_combo(
    legs: Sequence[Mapping[str, Any]],
    *,
    spot: float | None,
    sigma: float = 0.20,
    rate: float = 0.02,
    dte: int | None = None,
) -> dict[str, Any]:
    """Combo greeks plus a conservative SSE/SZSE-style margin estimate."""
    enriched: list[dict[str, Any]] = []
    obligation = 0.0
    premium_debit = 0.0
    for leg in legs:
        item = dict(leg)
        strike = align_strike_to_spot(spot, item.get("strike"))
        item["strike"] = strike
        is_call = str(item.get("call_put") or "C").upper() == "C"
        greeks = None
        if spot is not None and strike is not None:
            tte = max(int(dte if dte is not None else 30), 0) / 365.0
            model = "bs" if str(item.get("kind") or "etf").lower() == "etf" else "black76"
            greeks = black_scholes_greeks(
                spot=float(spot),
                strike=float(strike),
                tte=tte,
                sigma=float(sigma or 0.2),
                is_call=is_call,
                rate=rate,
                model=model,
            )
        item["greeks"] = greeks or {"price": item.get("premium") or 0.0, "delta": 0.0, "gamma": 0.0, "vega": 0.0, "theta": 0.0}
        premium = float(item.get("premium") if item.get("premium") is not None else item["greeks"]["price"])
        item["premium"] = premium
        qty = abs(float(item.get("qty_signed") or item.get("qty") or 0.0))
        multiplier = float(item.get("multiplier") or 10000.0)
        signed = float(item.get("qty_signed") or 0.0)
        premium_debit += signed * premium * multiplier
        if signed < 0 and spot is not None and strike is not None:
            per = (
                _short_call_margin(spot=float(spot), strike=float(strike), premium=premium, multiplier=multiplier)
                if is_call
                else _short_put_margin(spot=float(spot), strike=float(strike), premium=premium, multiplier=multiplier)
            )
            obligation += per * qty
        enriched.append(item)

    call_width = _defined_risk_width(enriched, "C")
    put_width = _defined_risk_width(enriched, "P")
    defined = [width for width in (call_width, put_width) if width is not None]
    if defined:
        margin = max(defined)
        method = "defined_risk_width"
        note = (
            "Iron-condor / vertical: exchange-style occupied margin approximated as "
            "max(call-spread width, put-spread width) × lots × multiplier."
        )
    else:
        margin = obligation
        method = "sse_obligation_short"
        note = (
            "Conservative SSE/SZSE short-option obligation: "
            "call max(premium+12%*S-OTM, premium+7%*S); "
            "put max(premium+12%*S-OTM, premium+7%*K), times multiplier."
        )

    greeks = combo_greeks(enriched)
    return {
        "legs": [
            {
                "index": item.get("index"),
                "symbol": item.get("symbol"),
                "side": item.get("side"),
                "qty": item.get("qty"),
                "call_put": item.get("call_put"),
                "strike": item.get("strike"),
                "premium": item.get("premium"),
                "greeks": item.get("greeks"),
            }
            for item in enriched
        ],
        "greeks": greeks,
        "net_premium": premium_debit,
        "margin_estimate": margin,
        "margin_currency": "CNY",
        "margin_method": method,
        "conservative": True,
        "note": note,
        "spot": spot,
        "sigma": sigma,
    }
