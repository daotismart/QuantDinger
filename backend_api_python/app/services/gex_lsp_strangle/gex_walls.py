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


def list_monthly_expiries(
    chain: pd.DataFrame | Sequence[Mapping[str, Any]],
    *,
    asof: Any | None = None,
    min_dte: int = 1,
    max_dte: int = 120,
    min_contracts: int = 8,
) -> list[pd.Timestamp]:
    """Sorted monthly expiries available on ``asof`` (DTE within [min_dte, max_dte])."""
    if isinstance(chain, pd.DataFrame):
        df = chain.copy()
    else:
        df = pd.DataFrame(list(chain))
    if df.empty:
        return []
    lower = {str(c).lower(): c for c in df.columns}
    if "expire_date" not in df.columns:
        for name in ("expire_date", "expiry", "expiration"):
            if name in lower:
                df = df.rename(columns={lower[name]: "expire_date"})
                break
    if "expire_date" not in df.columns:
        return []
    df["expire_date"] = pd.to_datetime(df["expire_date"], errors="coerce")
    if asof is not None:
        trade_date = pd.to_datetime(asof)
    elif "trade_date" in df.columns:
        trade_date = pd.to_datetime(df["trade_date"].iloc[0], errors="coerce")
    else:
        trade_date = pd.Timestamp.utcnow().normalize()
    df["dte"] = (df["expire_date"] - trade_date).dt.days
    df = df[(df["dte"] >= int(min_dte)) & (df["dte"] <= int(max_dte))]
    df = df[df["expire_date"].notna()]
    if df.empty:
        return []
    counts = df.groupby("expire_date").size().sort_index()
    liquid = [pd.Timestamp(exp) for exp, count in counts.items() if int(count) >= int(min_contracts)]
    if len(liquid) >= 2:
        return liquid
    # If books are thin (common in unit tests / sparse dumps), keep every month
    # with any quotes so 次月 selection still works.
    if liquid:
        extras = [pd.Timestamp(exp) for exp in counts.index if pd.Timestamp(exp) not in liquid]
        return liquid + extras
    return [pd.Timestamp(e) for e in counts.index]


def select_target_expire(
    chain: pd.DataFrame | Sequence[Mapping[str, Any]],
    *,
    asof: Any | None = None,
    expiry_month: str = "next",
    min_dte: int = 1,
    max_dte: int = 120,
    min_contracts: int = 8,
    prefer_expire: str | None = None,
) -> pd.Timestamp | None:
    """Pick 当月 (front) or 次月 (next) expiry.

    ``expiry_month``:
      - ``front`` / ``near`` / ``当月``: nearest eligible monthly
      - ``next`` / ``next_month`` / ``次月``: second nearest (fallback to front)
    """
    if prefer_expire:
        pref = pd.to_datetime(prefer_expire, errors="coerce")
        if pd.notna(pref):
            return pd.Timestamp(pref)
    expiries = list_monthly_expiries(
        chain,
        asof=asof,
        min_dte=min_dte,
        max_dte=max_dte,
        min_contracts=min_contracts,
    )
    if not expiries:
        return None
    mode = str(expiry_month or "next").strip().lower()
    if mode in ("next", "next_month", "次月", "second"):
        if len(expiries) >= 2:
            return expiries[1]
        return expiries[0]
    return expiries[0]


def compute_gex_walls(
    chain: pd.DataFrame | Sequence[Mapping[str, Any]],
    *,
    underlying: float,
    multiplier: float = 10000.0,
    min_dte: int = 1,
    max_dte: int = 90,
    prefer_expire: str | None = None,
    expiry_month: str = "next",
    min_contracts: int = 8,
) -> dict[str, Any]:
    """Compute call/put walls, pin, and flip from a single-day option chain.

    Expected columns:
      strike, cp (C/P), expire_date, open_interest, gamma, delta, option_close

    Dealer GEX convention: call gamma*OI positive, put gamma*OI negative.
    Call wall = strike with max call OI; put wall = max put OI; pin = max total OI.
    Flip = first strike (ascending, near/above 0.8× spot) where cumulative net GEX
    changes sign from negative to positive.

    By default selects **次月** (``expiry_month="next"``) rather than front month.
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
            "expiry_month": expiry_month,
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
    for want in ("strike", "cp", "gamma", "delta", "trade_date", "contract_code"):
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
    # Broad DTE window for listing months; target expiry is chosen below.
    list_min = min(int(min_dte), 1)
    list_max = max(int(max_dte), 90)
    df = df[(df["dte"] >= list_min) & (df["dte"] <= list_max)]
    df = df[df["strike"].notna() & df["cp"].isin(["C", "P"])]
    if df.empty:
        return {
            "call_wall": None,
            "put_wall": None,
            "pin": None,
            "flip": None,
            "expire_date": None,
            "spot": float(underlying),
            "points": [],
            "expiry_month": expiry_month,
        }

    target = select_target_expire(
        df,
        asof=trade_date,
        expiry_month=expiry_month,
        min_dte=list_min,
        max_dte=list_max,
        min_contracts=min_contracts,
        prefer_expire=prefer_expire,
    )
    if target is None:
        return {
            "call_wall": None,
            "put_wall": None,
            "pin": None,
            "flip": None,
            "expire_date": None,
            "spot": float(underlying),
            "points": [],
            "expiry_month": expiry_month,
        }
    df = df[df["expire_date"] == pd.Timestamp(target)].copy()
    if df.empty:
        return {
            "call_wall": None,
            "put_wall": None,
            "pin": None,
            "flip": None,
            "expire_date": None,
            "spot": float(underlying),
            "points": [],
            "expiry_month": expiry_month,
        }
    expire = pd.Timestamp(target)
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
        "expiry_month": expiry_month,
        "dte": int((expire - trade_date).days),
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


def select_iron_condor_strikes(
    walls: Mapping[str, Any],
    *,
    min_width_pct: float = 0.02,
    wing_steps: int = 2,
    wing_pct: float = 0.0,
) -> dict[str, Any] | None:
    """Build a short iron condor from GEX walls + further OTM long wings.

    Structure (credit):
      - short call near call wall, long call ``wing_steps`` strikes further OTM
      - short put near put wall, long put ``wing_steps`` strikes further OTM

    When the wall sits on the edge of the listed strike grid (no room for a wing),
    the short strike is walked one step closer to spot so a long wing still fits.
    If ``wing_pct`` > 0, wing distance is at least ``wing_pct * spot``.
    """
    body = select_strangle_strikes(walls, min_width_pct=min_width_pct)
    if body is None:
        return None
    points = list(walls.get("points") or [])
    by_strike = {float(p["strike"]): p for p in points}
    strikes = sorted(by_strike)
    if len(strikes) < 4:
        return None

    short_call = float(body["call_strike"])
    short_put = float(body["put_strike"])
    spot = float(body["spot"])
    steps = max(int(wing_steps), 1)
    min_wing = max(float(wing_pct), 0.0) * spot

    # Ensure enough listed strikes beyond each short for long wings.
    otm_calls = [k for k in strikes if k >= spot]
    otm_puts = [k for k in strikes if k <= spot]
    if len(otm_calls) < steps + 1 or len(otm_puts) < steps + 1:
        return None

    # If short call is too close to the top of the grid, pull it inward.
    while True:
        higher = [k for k in strikes if k > short_call]
        if len(higher) >= steps:
            break
        prev = [k for k in otm_calls if k < short_call]
        if not prev:
            return None
        short_call = prev[-1]

    # If short put is too close to the bottom of the grid, push it inward.
    while True:
        lower = [k for k in strikes if k < short_put]
        if len(lower) >= steps:
            break
        nxt = [k for k in otm_puts if k > short_put]
        if not nxt:
            return None
        short_put = nxt[0]

    if short_call <= short_put or short_call < spot or short_put > spot:
        return None
    if (short_call - short_put) / spot < float(min_width_pct):
        return None

    higher = [k for k in strikes if k > short_call]
    lower = [k for k in strikes if k < short_put]
    long_call = higher[min(steps, len(higher)) - 1]
    long_put = lower[max(len(lower) - steps, 0)]
    if min_wing > 0:
        for k in higher:
            if k - short_call >= min_wing:
                long_call = k
                break
        for k in reversed(lower):
            if short_put - k >= min_wing:
                long_put = k
                break

    if not (long_put < short_put <= spot <= short_call < long_call):
        return None

    call_short_row = by_strike.get(short_call) or {}
    put_short_row = by_strike.get(short_put) or {}
    call_long_row = by_strike.get(long_call) or {}
    put_long_row = by_strike.get(long_put) or {}
    call_wing = float(long_call - short_call)
    put_wing = float(short_put - long_put)
    return {
        "call_strike": short_call,
        "put_strike": short_put,
        "call_code": call_short_row.get("call_code"),
        "put_code": put_short_row.get("put_code"),
        "call_close": call_short_row.get("call_close"),
        "put_close": put_short_row.get("put_close"),
        "call_delta": call_short_row.get("call_delta"),
        "put_delta": put_short_row.get("put_delta"),
        "call_wall": body.get("call_wall"),
        "put_wall": body.get("put_wall"),
        "pin": body.get("pin"),
        "flip": body.get("flip"),
        "expire_date": body.get("expire_date"),
        "spot": spot,
        "long_call_strike": long_call,
        "long_put_strike": long_put,
        "long_call_code": call_long_row.get("call_code"),
        "long_put_code": put_long_row.get("put_code"),
        "long_call_close": call_long_row.get("call_close"),
        "long_put_close": put_long_row.get("put_close"),
        "long_call_delta": call_long_row.get("call_delta"),
        "long_put_delta": put_long_row.get("put_delta"),
        "call_wing": call_wing,
        "put_wing": put_wing,
        "wing_width": max(call_wing, put_wing),
        "structure": "iron_condor",
    }
