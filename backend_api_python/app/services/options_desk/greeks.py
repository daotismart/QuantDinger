"""Black-Scholes / Black-76 greeks used for chain filters and combo estimates."""

from __future__ import annotations

import math
from typing import Any, Mapping, Sequence


def _norm_cdf(value: float) -> float:
    return 0.5 * (1.0 + math.erf(value / math.sqrt(2.0)))


def _norm_pdf(value: float) -> float:
    return math.exp(-0.5 * value * value) / math.sqrt(2.0 * math.pi)


def align_strike_to_spot(spot: float | None, strike: float | None) -> float | None:
    """Scale index-point ETF strikes (e.g. 2750 vs spot 2.75) down to price units."""
    if spot is None or strike is None:
        return strike
    if strike > 50 and 0 < spot < 20:
        return strike / 1000.0
    return strike


def black_scholes_greeks(
    *,
    spot: float,
    strike: float,
    tte: float,
    sigma: float,
    is_call: bool,
    rate: float = 0.02,
    dividend: float = 0.0,
    model: str = "bs",
) -> dict[str, float]:
    """Return theoretical price and first-order greeks.

    ``model="bs"`` is Black-Scholes on the spot (ETF options).
    ``model="black76"`` treats ``spot`` as the futures/forward price.
    """
    forward = max(float(spot), 1e-12)
    strike = max(float(strike), 1e-12)
    tte = max(float(tte), 1.0 / 365.0)
    sigma = max(float(sigma), 1e-6)
    vol_sqrt = sigma * math.sqrt(tte)
    if model == "black76":
        d1 = (math.log(forward / strike) + 0.5 * sigma * sigma * tte) / vol_sqrt
        d2 = d1 - vol_sqrt
        df = math.exp(-max(rate, 0.0) * tte)
        discount = df
        call_price = df * (forward * _norm_cdf(d1) - strike * _norm_cdf(d2))
        put_price = df * (strike * _norm_cdf(-d2) - forward * _norm_cdf(-d1))
        call_delta = df * _norm_cdf(d1)
        gamma = df * _norm_pdf(d1) / (forward * vol_sqrt)
        vega = df * forward * _norm_pdf(d1) * math.sqrt(tte) / 100.0
        call_theta = (
            -forward * df * _norm_pdf(d1) * sigma / (2.0 * math.sqrt(tte))
            + rate * strike * df * _norm_cdf(d2)
            - rate * forward * df * _norm_cdf(d1)
        ) / 365.0
        put_theta = (
            -forward * df * _norm_pdf(d1) * sigma / (2.0 * math.sqrt(tte))
            - rate * strike * df * _norm_cdf(-d2)
            + rate * forward * df * _norm_cdf(-d1)
        ) / 365.0
    else:
        drift = (rate - dividend + 0.5 * sigma * sigma) * tte
        d1 = (math.log(forward / strike) + drift) / vol_sqrt
        d2 = d1 - vol_sqrt
        df = math.exp(-rate * tte)
        dq = math.exp(-dividend * tte)
        call_price = forward * dq * _norm_cdf(d1) - strike * df * _norm_cdf(d2)
        put_price = strike * df * _norm_cdf(-d2) - forward * dq * _norm_cdf(-d1)
        call_delta = dq * _norm_cdf(d1)
        gamma = dq * _norm_pdf(d1) / (forward * vol_sqrt)
        vega = forward * dq * _norm_pdf(d1) * math.sqrt(tte) / 100.0
        call_theta = (
            -forward * dq * _norm_pdf(d1) * sigma / (2.0 * math.sqrt(tte))
            - rate * strike * df * _norm_cdf(d2)
            + dividend * forward * dq * _norm_cdf(d1)
        ) / 365.0
        put_theta = (
            -forward * dq * _norm_pdf(d1) * sigma / (2.0 * math.sqrt(tte))
            + rate * strike * df * _norm_cdf(-d2)
            - dividend * forward * dq * _norm_cdf(-d1)
        ) / 365.0
        discount = df
    del discount
    if is_call:
        return {
            "price": float(call_price),
            "delta": float(call_delta),
            "gamma": float(gamma),
            "vega": float(vega),
            "theta": float(call_theta),
        }
    return {
        "price": float(put_price),
        "delta": float(call_delta - (math.exp(-dividend * tte) if model != "black76" else math.exp(-rate * tte))),
        "gamma": float(gamma),
        "vega": float(vega),
        "theta": float(put_theta),
    }


def combo_greeks(legs: Sequence[Mapping[str, Any]]) -> dict[str, float]:
    """Sum signed greeks. Each leg needs qty_signed and per-unit greeks."""
    totals = {"delta": 0.0, "gamma": 0.0, "vega": 0.0, "theta": 0.0, "theoretical": 0.0}
    for leg in legs:
        signed = float(leg.get("qty_signed") or 0.0)
        multiplier = float(leg.get("multiplier") or 1.0)
        scale = signed * multiplier
        greeks = leg.get("greeks") or {}
        for key in ("delta", "gamma", "vega", "theta"):
            totals[key] += scale * float(greeks.get(key) or 0.0)
        totals["theoretical"] += signed * multiplier * float(
            greeks.get("price") or leg.get("premium") or 0.0
        )
    return {key: float(value) for key, value in totals.items()}
