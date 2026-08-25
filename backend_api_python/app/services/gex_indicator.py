"""GEX as a chart-style indicator (compute → output → display).

Mirrors the Indicator IDE contract (``plots`` / ``signals`` / ``layers`` /
``summary``), but the X-axis is **strike** rather than time. The derivatives
options panel treats this module as the single source of truth for GEX:

1. **Compute** — ``run_gex_indicator(chain, ...)``
2. **Display payload** — ``output`` dict consumed by the frontend
3. **Legacy fields** — ``panel_fields_from_gex_indicator`` keeps
   ``gex_distribution`` / ``gex_summary`` for older clients

This module does not place orders and does not own option-chain fetching.
"""

from __future__ import annotations

import math
from typing import Any, Dict, List, Optional


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        out = float(value)
        if math.isnan(out) or math.isinf(out):
            return default
        return out
    except Exception:
        return default


def _norm_cdf(x: float) -> float:
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def _norm_pdf(x: float) -> float:
    return math.exp(-0.5 * x * x) / math.sqrt(2.0 * math.pi)


def black76_greeks(
    F: float,
    K: float,
    T: float,
    sigma: float,
    is_call: bool,
) -> Dict[str, float]:
    """Black-76 Greeks for a futures-style underlying (ETF spot used as F)."""
    F = max(float(F), 1e-12)
    K = max(float(K), 1e-12)
    T = max(float(T), 1e-8)
    sigma = max(float(sigma), 1e-8)
    sqrt_t = math.sqrt(T)
    d1 = (math.log(F / K) + 0.5 * sigma * sigma * T) / (sigma * sqrt_t)
    d2 = d1 - sigma * sqrt_t
    pdf = _norm_pdf(d1)
    gamma = pdf / (F * sigma * sqrt_t)
    vega = F * pdf * sqrt_t / 100.0
    theta = (-F * pdf * sigma / (2.0 * sqrt_t)) / 365.0
    if is_call:
        delta = _norm_cdf(d1)
    else:
        delta = _norm_cdf(d1) - 1.0
    return {
        "delta": float(delta),
        "gamma": float(gamma),
        "vega": float(vega),
        "theta": float(theta),
    }


def implied_vol_black76(
    price: float,
    F: float,
    K: float,
    T: float,
    is_call: bool,
) -> Optional[float]:
    """Binary-search Black-76 IV; returns None when unusable."""
    price = _safe_float(price)
    F = _safe_float(F)
    K = _safe_float(K)
    T = max(_safe_float(T, 30 / 365.0), 1e-8)
    if price <= 0 or F <= 0 or K <= 0:
        return None

    def _price(sig: float) -> float:
        sqrt_t = math.sqrt(T)
        d1 = (math.log(F / K) + 0.5 * sig * sig * T) / (sig * sqrt_t)
        d2 = d1 - sig * sqrt_t
        if is_call:
            return F * _norm_cdf(d1) - K * _norm_cdf(d2)
        return K * _norm_cdf(-d2) - F * _norm_cdf(-d1)

    lo, hi = 1e-4, 5.0
    for _ in range(50):
        mid = 0.5 * (lo + hi)
        model = _price(mid)
        if model > price:
            hi = mid
        else:
            lo = mid
    iv = 0.5 * (lo + hi)
    if iv <= 1e-3 or iv >= 4.9:
        return None
    return float(iv)


def compute_gex_raw(
    chain: List[Dict[str, Any]],
    *,
    underlying: float,
    multiplier: float,
    T: float,
) -> Dict[str, Any]:
    """Strike-level GEX math. Return shape matches legacy ``compute_gex``."""
    # Alias kept stable for callers / tests.
    points: List[Dict[str, Any]] = []
    total_call_gex = 0.0
    total_put_gex = 0.0
    total_call_oi = 0.0
    total_put_oi = 0.0
    portfolio = {"delta": 0.0, "gamma": 0.0, "vega": 0.0, "theta": 0.0}
    smile: List[Dict[str, Any]] = []

    underlying = _safe_float(underlying)
    multiplier = _safe_float(multiplier, 10000.0)
    T = max(_safe_float(T, 30 / 365.0), 1e-8)

    for row in chain or []:
        k = _safe_float(row.get("strike"))
        if k <= 0:
            continue
        call_mid = _safe_float(row.get("call_mid"))
        put_mid = _safe_float(row.get("put_mid"))
        call_iv = (
            implied_vol_black76(call_mid, underlying, k, T, True)
            if call_mid > 0
            else None
        )
        put_iv = (
            implied_vol_black76(put_mid, underlying, k, T, False)
            if put_mid > 0
            else None
        )
        iv = call_iv or put_iv or 0.25
        call_greeks = black76_greeks(underlying, k, T, call_iv or iv, True)
        put_greeks = black76_greeks(underlying, k, T, put_iv or iv, False)
        call_oi = _safe_float(row.get("call_oi"))
        put_oi = _safe_float(row.get("put_oi"))
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

    points.sort(key=lambda p: p["strike"])
    levels = derive_gex_levels(points, underlying=underlying)

    return {
        "points": points,
        "summary": {
            "net_gex": total_call_gex + total_put_gex,
            "call_gex": total_call_gex,
            "put_gex": total_put_gex,
            "call_oi": total_call_oi,
            "put_oi": total_put_oi,
            "call_wall": levels["call_wall"],
            "put_wall": levels["put_wall"],
            "pin": levels["pin"],
            "flip": levels["flip"],
            "underlying": underlying,
        },
        "portfolio_greeks": portfolio,
        "iv_smile": smile,
    }


def derive_gex_levels(
    points: List[Dict[str, Any]],
    *,
    underlying: float,
) -> Dict[str, Optional[float]]:
    """Derive Flip / Call Wall / Put Wall / Pin from strike-level GEX rows.

    Chart-aligned conventions (match the Net GEX profile the UI plots):

    - **Call wall** — max ``net_gex`` at strikes ``>=`` spot (peak positive stack)
    - **Put wall** — min ``net_gex`` at strikes ``<=`` spot (deepest trough)
    - **Pin** — strike with max total OI (call + put)
    - **Flip** — first strike (ascending, at/above ``0.8×`` spot) where **per-strike**
      ``net_gex`` crosses from negative to non-negative (same place the Net GEX
      line crosses zero). Falls back to cumulative cross when no per-strike cross.
    """
    if not points:
        return {"call_wall": None, "put_wall": None, "pin": None, "flip": None}

    ordered = sorted(points, key=lambda p: float(p["strike"]))
    spot = _safe_float(underlying)

    def _pick_strike(
        rows: List[Dict[str, Any]],
        key: str,
        *,
        mode: str,
    ) -> Optional[float]:
        if not rows:
            return None
        if mode == "max":
            best = max(rows, key=lambda p: _safe_float(p.get(key)))
        else:
            best = min(rows, key=lambda p: _safe_float(p.get(key)))
        return float(best["strike"])

    above = [p for p in ordered if spot <= 0 or float(p["strike"]) >= spot]
    below = [p for p in ordered if spot <= 0 or float(p["strike"]) <= spot]

    call_wall = _pick_strike(above, "net_gex", mode="max") or _pick_strike(
        ordered, "net_gex", mode="max"
    )
    if call_wall is None or all(_safe_float(p.get("net_gex")) == 0 for p in ordered):
        call_wall = (
            _pick_strike(above, "call_gex", mode="max")
            or _pick_strike(ordered, "call_gex", mode="max")
            or _pick_strike(above, "call_oi", mode="max")
            or _pick_strike(ordered, "call_oi", mode="max")
        )

    put_wall = _pick_strike(below, "net_gex", mode="min") or _pick_strike(
        ordered, "net_gex", mode="min"
    )
    if put_wall is None or all(_safe_float(p.get("net_gex")) == 0 for p in ordered):
        put_wall = (
            _pick_strike(below, "put_gex", mode="min")
            or _pick_strike(ordered, "put_gex", mode="min")
            or _pick_strike(below, "put_oi", mode="max")
            or _pick_strike(ordered, "put_oi", mode="max")
        )

    pin = float(
        max(
            ordered,
            key=lambda p: _safe_float(p.get("call_oi")) + _safe_float(p.get("put_oi")),
        )["strike"]
    )

    # Primary Flip: per-strike Net GEX sign change (matches the plotted orange line).
    flip = None
    floor = 0.8 * spot if spot > 0 else float("-inf")
    prev_net: Optional[float] = None
    for point in ordered:
        strike = float(point["strike"])
        net = _safe_float(point.get("net_gex"))
        if strike < floor:
            prev_net = net
            continue
        if prev_net is not None and prev_net < 0.0 <= net:
            flip = strike
            break
        prev_net = net

    # Fallback: cumulative cross when the profile never flips strike-by-strike.
    if flip is None:
        cum = 0.0
        prev_cum: Optional[float] = None
        for point in ordered:
            strike = float(point["strike"])
            cum += _safe_float(point.get("net_gex"))
            if strike < floor:
                prev_cum = cum
                continue
            if prev_cum is not None and prev_cum < 0.0 <= cum:
                flip = strike
                break
            prev_cum = cum

    return {
        "call_wall": call_wall,
        "put_wall": put_wall,
        "pin": pin,
        "flip": flip,
    }


def aggregate_gex_points(
    point_groups: List[List[Dict[str, Any]]],
) -> List[Dict[str, Any]]:
    """Sum per-month GEX rows by strike (OI + GEX). Do not recompute gamma."""
    bucket: Dict[float, Dict[str, float]] = {}
    for points in point_groups or []:
        for row in points or []:
            k = _safe_float(row.get("strike"))
            if k <= 0:
                continue
            item = bucket.setdefault(
                k,
                {
                    "strike": k,
                    "call_oi": 0.0,
                    "put_oi": 0.0,
                    "call_gex": 0.0,
                    "put_gex": 0.0,
                    "net_gex": 0.0,
                },
            )
            item["call_oi"] += _safe_float(row.get("call_oi"))
            item["put_oi"] += _safe_float(row.get("put_oi"))
            item["call_gex"] += _safe_float(row.get("call_gex"))
            item["put_gex"] += _safe_float(row.get("put_gex"))
            net = row.get("net_gex")
            if net is None:
                item["net_gex"] += _safe_float(row.get("call_gex")) + _safe_float(
                    row.get("put_gex")
                )
            else:
                item["net_gex"] += _safe_float(net)

    out: List[Dict[str, Any]] = []
    for item in sorted(bucket.values(), key=lambda x: x["strike"]):
        call_oi = float(item["call_oi"])
        put_oi = float(item["put_oi"])
        out.append(
            {
                "strike": float(item["strike"]),
                "call_oi": call_oi,
                "put_oi": put_oi,
                "total_oi": call_oi + put_oi,
                "net_oi": call_oi - put_oi,
                "call_gex": float(item["call_gex"]),
                "put_gex": float(item["put_gex"]),
                "net_gex": float(item["net_gex"]),
                "call_iv": None,
                "put_iv": None,
            }
        )
    return out


def summary_from_gex_points(
    points: List[Dict[str, Any]],
    *,
    underlying: float,
) -> Dict[str, Any]:
    """Build gex_summary totals + Flip/Walls/Pin from aggregated points."""
    levels = derive_gex_levels(points, underlying=underlying)
    call_gex = sum(_safe_float(p.get("call_gex")) for p in points)
    put_gex = sum(_safe_float(p.get("put_gex")) for p in points)
    return {
        "net_gex": call_gex + put_gex,
        "call_gex": call_gex,
        "put_gex": put_gex,
        "call_oi": sum(_safe_float(p.get("call_oi")) for p in points),
        "put_oi": sum(_safe_float(p.get("put_oi")) for p in points),
        "call_wall": levels["call_wall"],
        "put_wall": levels["put_wall"],
        "pin": levels["pin"],
        "flip": levels["flip"],
        "underlying": float(underlying),
    }


def indicator_from_gex_points(
    points: List[Dict[str, Any]],
    *,
    underlying: float,
    multiplier: float = 10000.0,
    T: float = 30 / 365.0,
    name: str = "GEX",
) -> Dict[str, Any]:
    """Build indicator display payload from precomputed strike points."""
    summary = summary_from_gex_points(points, underlying=underlying)
    raw = {
        "points": list(points or []),
        "summary": summary,
        "portfolio_greeks": {},
        "iv_smile": [],
    }
    return _build_indicator_output(
        raw,
        name=name,
        underlying=underlying,
        multiplier=multiplier,
        T=T,
    )


def _build_indicator_output(
    raw: Dict[str, Any],
    *,
    name: str = "GEX",
    underlying: float,
    multiplier: float,
    T: float,
) -> Dict[str, Any]:
    """Map raw GEX math into the chart-indicator display contract."""
    points = list(raw.get("points") or [])
    summary = dict(raw.get("summary") or {})
    categories = [p["strike"] for p in points]
    n = len(points)

    def _series(key: str) -> List[Optional[float]]:
        return [p.get(key) for p in points]

    plots = [
        {
            "name": "Call GEX",
            "data": _series("call_gex"),
            "color": "#52c41a",
            "type": "bar",
            "overlay": False,
        },
        {
            "name": "Put GEX",
            "data": _series("put_gex"),
            "color": "#ff4d4f",
            "type": "bar",
            "overlay": False,
        },
        {
            "name": "Net GEX",
            "data": _series("net_gex"),
            "color": "#fa8c16",
            "type": "line",
            "overlay": False,
        },
    ]

    layers: List[Dict[str, Any]] = []
    mark_specs = [
        ("Price", summary.get("underlying", underlying), "#1890ff", False),
        ("Flip", summary.get("flip"), "#faad14", True),
        ("Call Wall", summary.get("call_wall"), "#52c41a", True),
        ("Put Wall", summary.get("put_wall"), "#ff4d4f", True),
        ("Pin", summary.get("pin"), "#722ed1", True),
    ]
    for text, strike, color, dashed in mark_specs:
        if strike is None:
            continue
        layers.append(
            {
                "type": "line",
                "strike": float(strike),
                "text": text,
                "color": color,
                "dashed": dashed,
            }
        )

    # Sparse event markers on the nearest strike category (display-only).
    signals: List[Dict[str, Any]] = []
    for text, strike, color, _dashed in mark_specs:
        if strike is None or n == 0:
            continue
        idx = min(range(n), key=lambda i: abs(categories[i] - float(strike)))
        data: List[Optional[float]] = [None] * n
        data[idx] = float(strike)
        signals.append(
            {
                "type": "mark",
                "text": text,
                "color": color,
                "data": data,
            }
        )

    return {
        "name": name,
        "meta": {
            "kind": "strike_profile",
            "axis": "strike",
            "underlying": float(underlying),
            "multiplier": float(multiplier),
            "T": float(T),
        },
        "categories": categories,
        "plots": plots,
        "signals": signals,
        "layers": layers,
        "summary": summary,
        "calculatedVars": {
            "points": points,
            "portfolio_greeks": raw.get("portfolio_greeks") or {},
            "iv_smile": raw.get("iv_smile") or [],
            "call_oi": _series("call_oi"),
            "put_oi": _series("put_oi"),
            "net_oi": _series("net_oi"),
        },
    }


def run_gex_indicator(
    chain: List[Dict[str, Any]],
    *,
    underlying: float,
    multiplier: float = 10000.0,
    T: float = 30 / 365.0,
    name: str = "GEX",
) -> Dict[str, Any]:
    """Compute GEX and return the indicator display contract."""
    raw = compute_gex_raw(
        chain,
        underlying=underlying,
        multiplier=multiplier,
        T=T,
    )
    return _build_indicator_output(
        raw,
        name=name,
        underlying=underlying,
        multiplier=multiplier,
        T=T,
    )


def panel_fields_from_gex_indicator(indicator: Dict[str, Any]) -> Dict[str, Any]:
    """Derive legacy panel keys from an indicator output (display adapters)."""
    calc = indicator.get("calculatedVars") if isinstance(indicator, dict) else {}
    calc = calc if isinstance(calc, dict) else {}
    summary = indicator.get("summary") if isinstance(indicator, dict) else {}
    return {
        "gex_distribution": list(calc.get("points") or []),
        "gex_summary": dict(summary or {}),
        "greeks": dict(calc.get("portfolio_greeks") or {}),
        "iv_smile": list(calc.get("iv_smile") or []),
        "indicators": {"gex": indicator},
    }


def compute_gex(
    chain: List[Dict[str, Any]],
    *,
    underlying: float,
    multiplier: float,
    T: float,
) -> Dict[str, Any]:
    """Legacy-compatible GEX dict (points/summary/greeks/smile)."""
    return compute_gex_raw(
        chain,
        underlying=underlying,
        multiplier=multiplier,
        T=T,
    )
