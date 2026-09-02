"""GEX wall selection from option chain rows (OI × gamma / dealer convention)."""

from __future__ import annotations

import re
from typing import Any, Mapping, Sequence

import numpy as np
import pandas as pd

# SSE/SZSE adjusted contracts: "50ETF购4月3.117A" / "50ETF沽4月3215A"
_ADJUSTED_CONTRACT_RE = re.compile(r"(?:A(?:购|沽)|(?:购|沽)[^购沽]*\dA$|\dA$)")


def is_adjusted_contract(code: Any) -> bool:
    """True for dividend-adjusted ETF option display names (*A)."""
    text = str(code or "").strip()
    if not text:
        return False
    if "A购" in text or "A沽" in text:
        return True
    return bool(_ADJUSTED_CONTRACT_RE.search(text))


def on_strike_grid(strike: float, step: float, *, tol: float = 1e-6) -> bool:
    """True when ``strike`` sits on ``step`` (skip 3.117-style adjusted strikes)."""
    grid = float(step)
    if grid <= 0:
        return True
    snapped = round(float(strike) / grid) * grid
    return abs(snapped - float(strike)) <= tol


def _median_strike_step(strikes: Sequence[float], fallback: float = 0.05) -> float:
    vals = sorted({round(float(k), 6) for k in strikes if float(k) > 0})
    diffs = [b - a for a, b in zip(vals, vals[1:]) if b > a + 1e-9]
    if not diffs:
        return float(fallback)
    mid = diffs[len(diffs) // 2]
    return float(mid if mid > 0 else fallback)


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
    target_dte: int | None = None,
) -> pd.Timestamp | None:
    """Pick 当月 (front), 次月 (next), or closest-to-target DTE expiry.

    ``expiry_month``:
      - ``front`` / ``near`` / ``当月``: nearest eligible monthly
      - ``next`` / ``next_month`` / ``次月``: second nearest (fallback to front)
      - ``target`` / ``dte``: expiry closest to ``target_dte`` (default 45)
    When ``target_dte`` is set, DTE-distance wins over front/next.
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
    trade_date = pd.to_datetime(asof) if asof is not None else None
    if trade_date is None and isinstance(chain, pd.DataFrame) and "trade_date" in chain.columns:
        trade_date = pd.to_datetime(chain["trade_date"].iloc[0], errors="coerce")
    want_target = target_dte is not None or mode in ("target", "dte", "target_dte", "45dte")
    if want_target and trade_date is not None and pd.notna(trade_date):
        goal = int(target_dte if target_dte is not None else 45)
        return min(expiries, key=lambda exp: abs(int((pd.Timestamp(exp) - pd.Timestamp(trade_date)).days) - goal))
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
    target_dte: int | None = None,
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
    for want in ("strike", "cp", "gamma", "delta", "theta", "trade_date", "contract_code"):
        if want not in df.columns and want in lower:
            rename[lower[want]] = want
    if rename:
        df = df.rename(columns=rename)

    df["strike"] = pd.to_numeric(df["strike"], errors="coerce")
    df["open_interest"] = pd.to_numeric(df.get("open_interest"), errors="coerce").fillna(0.0)
    df["gamma"] = pd.to_numeric(df.get("gamma"), errors="coerce").fillna(0.0)
    df["delta"] = pd.to_numeric(df.get("delta"), errors="coerce")
    df["theta"] = pd.to_numeric(df.get("theta"), errors="coerce") if "theta" in df.columns else np.nan
    df["option_close"] = pd.to_numeric(df.get("option_close"), errors="coerce")
    df["cp"] = df["cp"].astype(str).str.upper().str.strip().str[0]
    if "contract_code" in df.columns:
        df = df[~df["contract_code"].map(is_adjusted_contract)]
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
        target_dte=target_dte,
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
                "call_theta": (
                    float(call["theta"].iloc[0])
                    if not call.empty and "theta" in call.columns and pd.notna(call["theta"].iloc[0])
                    else 0.0
                ),
                "put_theta": (
                    float(put["theta"].iloc[0])
                    if not put.empty and "theta" in put.columns and pd.notna(put["theta"].iloc[0])
                    else 0.0
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
        "target_dte": target_dte,
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


def _pack_iron_condor(
    *,
    by_strike: Mapping[float, Mapping[str, Any]],
    short_call: float,
    short_put: float,
    long_call: float,
    long_put: float,
    spot: float,
    walls: Mapping[str, Any],
    min_credit_to_width: float = 0.0,
    min_credit: float = 0.0,
) -> dict[str, Any] | None:
    if not (long_put < short_put <= spot <= short_call < long_call):
        return None
    call_short_row = by_strike.get(short_call) or {}
    put_short_row = by_strike.get(short_put) or {}
    call_long_row = by_strike.get(long_call) or {}
    put_long_row = by_strike.get(long_put) or {}
    sc_px = _f(call_short_row.get("call_close"))
    sp_px = _f(put_short_row.get("put_close"))
    lc_px = _f(call_long_row.get("call_close"))
    lp_px = _f(put_long_row.get("put_close"))
    if min(sc_px, sp_px, lc_px, lp_px) <= 0:
        return None
    call_wing = float(long_call - short_call)
    put_wing = float(short_put - long_put)
    wing_width = max(call_wing, put_wing)
    if wing_width <= 0:
        return None
    call_credit = max(sc_px - lc_px, 0.0)
    put_credit = max(sp_px - lp_px, 0.0)
    net_credit = call_credit + put_credit
    if net_credit <= 0:
        return None
    cr_w = net_credit / wing_width
    if float(min_credit_to_width) > 0 and cr_w < float(min_credit_to_width):
        return None
    if float(min_credit) > 0 and net_credit < float(min_credit):
        return None
    max_loss_share = wing_width - net_credit
    if max_loss_share <= 0:
        return None
    # BS theta is for a long option (typically negative). Seller net theta:
    # shorts contribute -theta, longs contribute +theta.
    net_theta = (
        -(_f(call_short_row.get("call_theta")) + _f(put_short_row.get("put_theta")))
        + (_f(call_long_row.get("call_theta")) + _f(put_long_row.get("put_theta")))
    )
    efficiency = (net_theta / max_loss_share) if abs(net_theta) > 1e-12 else (net_credit / max_loss_share)
    d_call = abs(_f(call_short_row.get("call_delta")))
    d_put = abs(_f(put_short_row.get("put_delta")))
    range_prob = max(0.0, min(1.0, (1.0 - d_call) * (1.0 - d_put)))
    return {
        "call_strike": short_call,
        "put_strike": short_put,
        "call_code": call_short_row.get("call_code"),
        "put_code": put_short_row.get("put_code"),
        "call_close": sc_px,
        "put_close": sp_px,
        "call_delta": call_short_row.get("call_delta"),
        "put_delta": put_short_row.get("put_delta"),
        "call_wall": walls.get("call_wall"),
        "put_wall": walls.get("put_wall"),
        "pin": walls.get("pin"),
        "flip": walls.get("flip"),
        "expire_date": walls.get("expire_date"),
        "spot": spot,
        "long_call_strike": long_call,
        "long_put_strike": long_put,
        "long_call_code": call_long_row.get("call_code"),
        "long_put_code": put_long_row.get("put_code"),
        "long_call_close": lc_px,
        "long_put_close": lp_px,
        "long_call_delta": call_long_row.get("call_delta"),
        "long_put_delta": put_long_row.get("put_delta"),
        "call_wing": call_wing,
        "put_wing": put_wing,
        "wing_width": wing_width,
        "net_credit": net_credit,
        "credit_to_width": cr_w,
        "max_loss_share": max_loss_share,
        "net_theta": net_theta,
        "efficiency": efficiency,
        "payoff_ratio": net_credit / max_loss_share,
        "range_prob": range_prob,
        "structure": "iron_condor",
    }


def _usable_points(
    points: Sequence[Mapping[str, Any]],
    *,
    exclude_adjusted: bool,
    strike_grid: float,
) -> dict[float, Mapping[str, Any]]:
    by_strike: dict[float, Mapping[str, Any]] = {}
    for raw in points:
        k = _f(raw.get("strike"))
        if k <= 0:
            continue
        if strike_grid > 0 and not on_strike_grid(k, strike_grid):
            continue
        if exclude_adjusted and (
            is_adjusted_contract(raw.get("call_code")) or is_adjusted_contract(raw.get("put_code"))
        ):
            continue
        by_strike[float(k)] = raw
    return by_strike


def _listed_wing(
    strikes: Sequence[float],
    short: float,
    wing: float,
    *,
    higher: bool,
    min_wing: float = 0.0,
) -> float | None:
    """Prefer ``wing`` further OTM; if the book is truncated, take the last listed
    strike that still clears ``min_wing`` (ETF 50ETF often has only 2 OTM steps).
    """
    need = max(float(wing), 0.0)
    floor = max(float(min_wing), 0.0)
    if higher:
        cands = [k for k in strikes if k > short + 1e-12]
        hit = next((k for k in cands if k - short >= need - 1e-9), None)
        if hit is not None:
            return float(hit)
        if cands and cands[-1] - short >= floor - 1e-9:
            return float(cands[-1])
        return None
    cands = [k for k in reversed(list(strikes)) if k < short - 1e-12]
    hit = next((k for k in cands if short - k >= need - 1e-9), None)
    if hit is not None:
        return float(hit)
    if cands and short - cands[-1] >= floor - 1e-9:
        return float(cands[-1])
    return None


def _delta_in_band(delta: Any, min_delta: float, max_delta: float) -> bool:
    ad = abs(_f(delta))
    if ad <= 0:
        return False
    return float(min_delta) <= ad <= float(max_delta)


def select_iron_condor_strikes(
    walls: Mapping[str, Any],
    *,
    min_width_pct: float = 0.02,
    wing_steps: int = 2,
    wing_pct: float = 0.0,
    short_otm_pct: float = 0.0,
    min_credit_to_width: float = 0.0,
    min_credit: float = 0.0,
    min_short_delta: float = 0.0,
    max_short_delta: float = 1.0,
    exclude_adjusted: bool = True,
    strike_grid: float = 0.05,
    min_wing_steps: int = 2,
) -> dict[str, Any] | None:
    """Build a short iron condor from the listed chain.

    GEX-TV mode (``min_short_delta``/``max_short_delta`` inside (0, 1)):
    short 14–25Δ calls/puts **outside** GEX walls, long legs ``wing_steps``
    exchange steps further OTM, keep only structures with net credit / wing
    width ≥ ``min_credit_to_width``, rank by net theta / max loss.

    Legacy mode (delta band disabled): short at/near GEX walls, or
    ``short_otm_pct`` OTM from spot, then buy ``wing_steps`` further-OTM wings.
    """
    points = list(walls.get("points") or [])
    by_strike = _usable_points(points, exclude_adjusted=exclude_adjusted, strike_grid=strike_grid)
    strikes = sorted(by_strike)
    spot = _f(walls.get("spot"))
    if spot <= 0 or len(strikes) < 4:
        return None
    step = _median_strike_step(strikes, fallback=strike_grid if strike_grid > 0 else 0.05)
    steps = max(int(wing_steps), 1)
    min_steps = min(max(int(min_wing_steps), 1), steps)
    wing = max(steps * step, max(float(wing_pct), 0.0) * spot)
    min_wing = max(min_steps * step, 0.0)
    delta_scan = float(min_short_delta) > 0.0 or float(max_short_delta) < 1.0 - 1e-12

    pack_kw = dict(
        by_strike=by_strike,
        spot=spot,
        walls=walls,
        min_credit_to_width=min_credit_to_width,
        min_credit=min_credit,
    )

    if delta_scan:
        return _pick_iron_condor_gex_tv(
            by_strike=by_strike,
            strikes=strikes,
            spot=spot,
            walls=walls,
            step=step,
            wing=wing,
            min_wing=min_wing,
            min_width_pct=min_width_pct,
            min_short_delta=min_short_delta,
            max_short_delta=max_short_delta,
            min_credit_to_width=min_credit_to_width,
            min_credit=min_credit,
        )

    otm_calls = [k for k in strikes if k >= spot]
    otm_puts = [k for k in strikes if k <= spot]
    if len(otm_calls) < steps + 1 or len(otm_puts) < steps + 1:
        return None

    if float(short_otm_pct) > 0:
        tgt_call = spot * (1.0 + float(short_otm_pct))
        tgt_put = spot * (1.0 - float(short_otm_pct))
        short_call = next((k for k in otm_calls if k >= tgt_call), None)
        short_put = next((k for k in reversed(otm_puts) if k <= tgt_put), None)
        if short_call is None or short_put is None:
            return None
        if len([k for k in strikes if k > short_call]) < steps:
            short_call = otm_calls[-(steps + 1)]
        if len([k for k in strikes if k < short_put]) < steps:
            short_put = otm_puts[steps]
        if short_call <= short_put or (short_call - short_put) / spot < float(min_width_pct):
            return None
        long_call = _listed_wing(strikes, float(short_call), wing, higher=True, min_wing=min_wing)
        long_put = _listed_wing(strikes, float(short_put), wing, higher=False, min_wing=min_wing)
        if long_call is None or long_put is None:
            return None
        return _pack_iron_condor(
            short_call=float(short_call),
            short_put=float(short_put),
            long_call=float(long_call),
            long_put=float(long_put),
            **pack_kw,
        )

    body = select_strangle_strikes(walls, min_width_pct=min_width_pct)
    if body is None:
        return None

    short_call = float(body["call_strike"])
    short_put = float(body["put_strike"])
    if short_call not in by_strike or short_put not in by_strike:
        # Walls landed on an adjusted/off-grid strike; snap to nearest usable.
        short_call = min(otm_calls, key=lambda k: abs(k - short_call)) if otm_calls else short_call
        short_put = min(otm_puts, key=lambda k: abs(k - short_put)) if otm_puts else short_put

    while True:
        if _listed_wing(strikes, short_call, wing, higher=True, min_wing=min_wing) is not None:
            break
        prev = [k for k in otm_calls if k < short_call]
        if not prev:
            return None
        short_call = prev[-1]

    while True:
        if _listed_wing(strikes, short_put, wing, higher=False, min_wing=min_wing) is not None:
            break
        nxt = [k for k in otm_puts if k > short_put]
        if not nxt:
            return None
        short_put = nxt[0]

    if short_call <= short_put or short_call < spot or short_put > spot:
        return None
    if (short_call - short_put) / spot < float(min_width_pct):
        return None
    long_call = _listed_wing(strikes, short_call, wing, higher=True, min_wing=min_wing)
    long_put = _listed_wing(strikes, short_put, wing, higher=False, min_wing=min_wing)
    if long_call is None or long_put is None:
        return None
    return _pack_iron_condor(
        short_call=float(short_call),
        short_put=float(short_put),
        long_call=float(long_call),
        long_put=float(long_put),
        **pack_kw,
    )


def _pick_iron_condor_gex_tv(
    *,
    by_strike: Mapping[float, Mapping[str, Any]],
    strikes: Sequence[float],
    spot: float,
    walls: Mapping[str, Any],
    step: float,
    wing: float,
    min_wing: float,
    min_width_pct: float,
    min_short_delta: float,
    max_short_delta: float,
    min_credit_to_width: float,
    min_credit: float,
) -> dict[str, Any] | None:
    """GEX-TV: 14–25Δ shorts outside walls, 3-step wings, max theta / max-loss."""
    atm = round(spot / step) * step if step > 0 else spot
    call_wall = _f(walls.get("call_wall"), atm + step)
    put_wall = _f(walls.get("put_wall"), atm - step)
    call_floor = max(call_wall, atm + step)
    put_ceil = min(put_wall, atm - step)
    calls: list[float] = []
    puts: list[float] = []
    for k in strikes:
        row = by_strike[k]
        if k >= call_floor - 1e-9 and _delta_in_band(row.get("call_delta"), min_short_delta, max_short_delta):
            if _f(row.get("call_close")) > 0:
                calls.append(k)
        if k <= put_ceil + 1e-9 and _delta_in_band(row.get("put_delta"), min_short_delta, max_short_delta):
            if _f(row.get("put_close")) > 0:
                puts.append(k)
    best: dict[str, Any] | None = None
    best_eff = -1e18
    for k_c in calls:
        max_call_wing = _max_listed_distance(strikes, k_c, higher=True)
        if max_call_wing + 1e-12 < min_wing:
            continue
        for k_p in puts:
            if k_c - k_p < 2 * step - 1e-9:
                continue
            if (k_c - k_p) / spot < float(min_width_pct):
                continue
            max_put_wing = _max_listed_distance(strikes, k_p, higher=False)
            width = min(float(wing), max_call_wing, max_put_wing)
            if width + 1e-12 < min_wing:
                continue
            k_lc = _listed_wing(strikes, k_c, width, higher=True, min_wing=width)
            k_lp = _listed_wing(strikes, k_p, width, higher=False, min_wing=width)
            if k_lc is None or k_lp is None or k_lp <= 0:
                continue
            cand = _pack_iron_condor(
                by_strike=by_strike,
                short_call=float(k_c),
                short_put=float(k_p),
                long_call=float(k_lc),
                long_put=float(k_lp),
                spot=spot,
                walls=walls,
                min_credit_to_width=min_credit_to_width,
                min_credit=min_credit,
            )
            if cand is None:
                continue
            eff = float(cand.get("efficiency") or -1e18)
            if best is None or eff > best_eff:
                best = cand
                best_eff = eff
    return best


def _max_listed_distance(strikes: Sequence[float], short: float, *, higher: bool) -> float:
    if higher:
        cands = [k for k in strikes if k > short + 1e-12]
        return float(cands[-1] - short) if cands else 0.0
    cands = [k for k in strikes if k < short - 1e-12]
    return float(short - cands[0]) if cands else 0.0

