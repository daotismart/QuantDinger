"""GEX wall selection from option chain rows (OI × gamma / dealer convention)."""

from __future__ import annotations

from typing import Any, Mapping, Sequence

import numpy as np
import pandas as pd


def _f(value: Any, default: float = 0.0) -> float:
    try:
        if value is None or (isinstance(value, float) and np.isnan(value)):
            return default
        out = float(value)
        if np.isnan(out) or np.isinf(out):
            return default
        return out
    except Exception:
        return default


def compute_gex_walls(
    chain: pd.DataFrame | Sequence[Mapping[str, Any]],
    *,
    underlying: float,
    multiplier: float = 10000.0,
    min_dte: int = 5,
    max_dte: int = 60,
    prefer_expire: str | None = None,
) -> dict[str, Any]:
    """Compute call/put walls, pin, and flip from a single-day option chain.

    Expected columns:
      strike, cp (C/P), expire_date, open_interest, gamma, delta, option_close

    Dealer GEX convention: call gamma*OI positive, put gamma*OI negative.
    Call wall = strike with max call OI; put wall = max put OI; pin = max total OI.
    Flip = first strike (ascending, near/above 0.8× spot) where cumulative net GEX
    changes sign from negative to positive.
    """
    if isinstance(chain, pd.DataFrame):
        df = chain.copy()
    else:
        df = pd.DataFrame(list(chain))
    if df.empty:
        return {
            "call_wall": None,
            "put_wall": None,
            "pin": None,
            "flip": None,
            "expire_date": None,
            "spot": float(underlying),
            "points": [],
        }

    rename = {}
    lower = {str(c).lower(): c for c in df.columns}
    aliases = {
        "open_interest": ("open_interest", "oi"),
        "expire_date": ("expire_date", "expiry", "expiration"),
        "option_close": ("option_close", "close", "premium"),
        "contract_code": ("contract_code", "code", "symbol"),
    }
    for want, names in aliases.items():
        if want in df.columns:
            continue
        for name in names:
            if name in lower:
                rename[lower[name]] = want
                break
    for want in ("strike", "cp", "gamma", "delta", "trade_date"):
        if want not in df.columns and want in lower:
            rename[lower[want]] = want
    if rename:
        df = df.rename(columns=rename)

    df["strike"] = pd.to_numeric(df["strike"], errors="coerce")
    df["open_interest"] = pd.to_numeric(df.get("open_interest"), errors="coerce").fillna(0.0)
    df["gamma"] = pd.to_numeric(df.get("gamma"), errors="coerce").fillna(0.0)
    df["delta"] = pd.to_numeric(df.get("delta"), errors="coerce")
    df["option_close"] = pd.to_numeric(df.get("option_close"), errors="coerce")
    df["cp"] = df["cp"].astype(str).str.upper().str.strip().str[0]
    df["expire_date"] = pd.to_datetime(df["expire_date"], errors="coerce")
    if "trade_date" in df.columns:
        trade_date = pd.to_datetime(df["trade_date"].iloc[0], errors="coerce")
    else:
        trade_date = pd.Timestamp.utcnow().normalize()
    df["dte"] = (df["expire_date"] - trade_date).dt.days
    df = df[(df["dte"] >= int(min_dte)) & (df["dte"] <= int(max_dte))]
    df = df[df["strike"].notna() & df["cp"].isin(["C", "P"])]
    if prefer_expire:
        pref = pd.to_datetime(prefer_expire)
        subset = df[df["expire_date"] == pref]
        if not subset.empty:
            df = subset
    if df.empty:
        return {
            "call_wall": None,
            "put_wall": None,
            "pin": None,
            "flip": None,
            "expire_date": None,
            "spot": float(underlying),
            "points": [],
        }

    expiry_counts = df.groupby("expire_date").size().sort_index()
    expire = expiry_counts.index[0]
    for exp, count in expiry_counts.items():
        if count >= 8:
            expire = exp
            break
    df = df[df["expire_date"] == expire].copy()
    spot = float(underlying)

    rows: list[dict[str, Any]] = []
    for strike, group in df.groupby("strike"):
        call = group[group["cp"] == "C"]
        put = group[group["cp"] == "P"]
        call_oi = float(call["open_interest"].sum()) if not call.empty else 0.0
        put_oi = float(put["open_interest"].sum()) if not put.empty else 0.0
        call_gamma = float(call["gamma"].mean()) if not call.empty else 0.0
        put_gamma = float(put["gamma"].mean()) if not put.empty else 0.0
        call_gex = call_gamma * call_oi * multiplier * spot
        put_gex = -put_gamma * put_oi * multiplier * spot
        rows.append(
            {
                "strike": float(strike),
                "call_oi": call_oi,
                "put_oi": put_oi,
                "call_gex": call_gex,
                "put_gex": put_gex,
                "net_gex": call_gex + put_gex,
                "call_close": (
                    float(call["option_close"].iloc[0])
                    if not call.empty and pd.notna(call["option_close"].iloc[0])
                    else None
                ),
                "put_close": (
                    float(put["option_close"].iloc[0])
                    if not put.empty and pd.notna(put["option_close"].iloc[0])
                    else None
                ),
                "call_delta": (
                    float(call["delta"].iloc[0])
                    if not call.empty and pd.notna(call["delta"].iloc[0])
                    else None
                ),
                "put_delta": (
                    float(put["delta"].iloc[0])
                    if not put.empty and pd.notna(put["delta"].iloc[0])
                    else None
                ),
                "call_code": (
                    str(call["contract_code"].iloc[0])
                    if not call.empty and "contract_code" in call.columns
                    else None
                ),
                "put_code": (
                    str(put["contract_code"].iloc[0])
                    if not put.empty and "contract_code" in put.columns
                    else None
                ),
            }
        )
    points = sorted(rows, key=lambda p: p["strike"])
    call_wall = max(points, key=lambda p: p["call_oi"])["strike"] if points else None
    put_wall = max(points, key=lambda p: p["put_oi"])["strike"] if points else None
    pin = max(points, key=lambda p: p["call_oi"] + p["put_oi"])["strike"] if points else None

    flip = None
    cum = 0.0
    floor = 0.8 * spot
    prev_cum = None
    for point in points:
        if point["strike"] < floor:
            cum += point["net_gex"]
            prev_cum = cum
            continue
        cum += point["net_gex"]
        if prev_cum is not None and prev_cum < 0.0 <= cum:
            flip = point["strike"]
            break
        prev_cum = cum

    return {
        "call_wall": call_wall,
        "put_wall": put_wall,
        "pin": pin,
        "flip": flip,
        "expire_date": str(pd.Timestamp(expire).date()),
        "spot": spot,
        "points": points,
    }


def select_strangle_strikes(
    walls: Mapping[str, Any],
    *,
    min_width_pct: float = 0.02,
) -> dict[str, Any] | None:
    """Pick OTM call/put strikes from walls for a wide short strangle."""
    spot = _f(walls.get("spot"))
    call_wall = walls.get("call_wall")
    put_wall = walls.get("put_wall")
    points = list(walls.get("points") or [])
    if spot <= 0 or call_wall is None or put_wall is None or not points:
        return None
    call_wall = float(call_wall)
    put_wall = float(put_wall)
    by_strike = {float(p["strike"]): p for p in points}
    strikes = sorted(by_strike)
    call_k = call_wall if call_wall >= spot else next((k for k in strikes if k >= spot), strikes[-1])
    put_k = put_wall if put_wall <= spot else next((k for k in reversed(strikes) if k <= spot), strikes[0])
    if (call_k - put_k) / spot < float(min_width_pct):
        higher = [k for k in strikes if k > call_k]
        lower = [k for k in strikes if k < put_k]
        if higher:
            call_k = higher[0]
        if lower:
            put_k = lower[-1]
    if call_k <= put_k:
        return None
    call_row = by_strike.get(call_k) or {}
    put_row = by_strike.get(put_k) or {}
    return {
        "call_strike": call_k,
        "put_strike": put_k,
        "call_code": call_row.get("call_code"),
        "put_code": put_row.get("put_code"),
        "call_close": call_row.get("call_close"),
        "put_close": put_row.get("put_close"),
        "call_delta": call_row.get("call_delta"),
        "put_delta": put_row.get("put_delta"),
        "call_wall": call_wall,
        "put_wall": put_wall,
        "pin": walls.get("pin"),
        "flip": walls.get("flip"),
        "expire_date": walls.get("expire_date"),
        "spot": spot,
    }
