"""Kelly margin-ratio sizing for short-premium ETF option books.

Odds are set to b=1 on option premium (risk ~1× credit to earn 1× credit), so::

    f* = 2p - 1

Win probability ``p`` comes from **Black–Scholes risk-neutral leg win rates**
(short call / short put expire OTM), not from a flat prior:

- short call win = P(S_T < K_c) = N(-d2_c)
- short put win  = P(S_T > K_p) = N(d2_p)
- default Kelly p = premium-weighted average of the two leg win rates

``f*`` is the **account margin utilization ratio**. Lots are sized as
``floor(equity * f* / margin_per_strangle_lot)``, with hard caps as risk control.

Delta exposure is an LSP concern, not Kelly's.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class KellySizingResult:
    win_prob: float
    odds_b: float
    raw_fraction: float
    margin_ratio: float
    base_lots: int
    capped: bool
    blocked: bool
    reason: str
    margin_budget: float
    margin_per_lot: float
    margin_used: float

    @property
    def fraction(self) -> float:
        return self.margin_ratio

    def to_dict(self) -> dict[str, Any]:
        return {
            "winProb": round(self.win_prob, 6),
            "oddsB": round(self.odds_b, 6),
            "rawFraction": round(self.raw_fraction, 6),
            "marginRatio": round(self.margin_ratio, 6),
            "fraction": round(self.margin_ratio, 6),
            "baseLots": int(self.base_lots),
            "capped": bool(self.capped),
            "blocked": bool(self.blocked),
            "reason": self.reason,
            "marginBudget": round(self.margin_budget, 2),
            "marginPerLot": round(self.margin_per_lot, 2),
            "marginUsed": round(self.margin_used, 2),
            "capitalBudget": round(self.margin_budget, 2),
            "capitalPerLot": round(self.margin_per_lot, 2),
        }


def kelly_fraction(win_prob: float, *, odds_b: float = 1.0) -> float:
    """Classic Kelly fraction f* = (b*p - q) / b."""
    p = float(win_prob)
    b = float(odds_b)
    if b <= 0 or p <= 0 or p >= 1:
        return 0.0
    q = 1.0 - p
    return (b * p - q) / b


def estimate_win_prob(
    closed_pnls: list[float],
    *,
    prior_p: float = 0.55,
    prior_strength: float = 10.0,
) -> float:
    """Bayesian-smoothed win rate from closed trade PnLs (fallback only)."""
    prior_p = min(max(float(prior_p), 0.01), 0.99)
    strength = max(float(prior_strength), 0.0)
    wins = sum(1 for x in closed_pnls if float(x) > 0)
    n = len(closed_pnls)
    return (prior_p * strength + wins) / (strength + n) if (strength + n) > 0 else prior_p


def _norm_cdf(x: float) -> float:
    return 0.5 * (1.0 + math.erf(float(x) / math.sqrt(2.0)))


def bs_d2(
    spot: float,
    strike: float,
    t_years: float,
    vol: float,
    *,
    rate: float = 0.0,
    dividend: float = 0.0,
) -> float | None:
    """Black–Scholes d2; None when inputs are not usable."""
    s = float(spot)
    k = float(strike)
    t = float(t_years)
    sig = float(vol)
    if s <= 0.0 or k <= 0.0 or t <= 0.0 or sig <= 0.0:
        return None
    return (math.log(s / k) + (float(rate) - float(dividend) - 0.5 * sig * sig) * t) / (
        sig * math.sqrt(t)
    )


def bs_short_call_win_prob(
    spot: float,
    strike: float,
    t_years: float,
    vol: float,
    *,
    rate: float = 0.0,
    dividend: float = 0.0,
) -> float | None:
    """Short-call win rate = Prob(expire OTM) = N(-d2)."""
    d2 = bs_d2(spot, strike, t_years, vol, rate=rate, dividend=dividend)
    if d2 is None:
        return None
    return float(_norm_cdf(-d2))


def bs_short_put_win_prob(
    spot: float,
    strike: float,
    t_years: float,
    vol: float,
    *,
    rate: float = 0.0,
    dividend: float = 0.0,
) -> float | None:
    """Short-put win rate = Prob(expire OTM) = N(d2)."""
    d2 = bs_d2(spot, strike, t_years, vol, rate=rate, dividend=dividend)
    if d2 is None:
        return None
    return float(_norm_cdf(d2))


def estimate_win_prob_from_bs_legs(
    *,
    spot: float,
    call_strike: float,
    put_strike: float,
    t_years: float,
    vol: float,
    call_premium: float = 0.0,
    put_premium: float = 0.0,
    rate: float = 0.0,
    dividend: float = 0.0,
    mode: str = "credit_weighted",
) -> dict[str, Any] | None:
    """Kelly ``p`` from BS short-leg win probabilities.

    Modes:
    - ``credit_weighted`` (default): premium-weighted average of leg win rates
    - ``average``: simple mean of leg win rates
    - ``both_otm``: Prob(put_wall < S_T < call_wall) = p_call + p_put - 1
    """
    p_call = bs_short_call_win_prob(
        spot, call_strike, t_years, vol, rate=rate, dividend=dividend
    )
    p_put = bs_short_put_win_prob(
        spot, put_strike, t_years, vol, rate=rate, dividend=dividend
    )
    if p_call is None or p_put is None:
        return None
    both_otm = max(0.0, min(1.0, float(p_call) + float(p_put) - 1.0))
    mode_u = str(mode or "credit_weighted").strip().lower()
    if mode_u == "both_otm":
        win_prob = both_otm
    elif mode_u == "average":
        win_prob = 0.5 * (float(p_call) + float(p_put))
    else:
        w_c = max(float(call_premium), 0.0)
        w_p = max(float(put_premium), 0.0)
        if w_c + w_p <= 0.0:
            win_prob = 0.5 * (float(p_call) + float(p_put))
            mode_u = "average"
        else:
            win_prob = (w_c * float(p_call) + w_p * float(p_put)) / (w_c + w_p)
            mode_u = "credit_weighted"
    win_prob = min(max(float(win_prob), 1e-6), 1.0 - 1e-6)
    return {
        "win_prob": win_prob,
        "call_win_prob": float(p_call),
        "put_win_prob": float(p_put),
        "both_otm_prob": float(both_otm),
        "mode": mode_u,
        "vol": float(vol),
        "t_years": float(t_years),
        "spot": float(spot),
        "call_strike": float(call_strike),
        "put_strike": float(put_strike),
    }


def estimate_short_leg_margin(
    *,
    spot: float,
    strike: float,
    premium: float,
    cp: str,
    multiplier: float,
    margin_rate: float = 0.12,
    floor_rate: float = 0.07,
) -> float:
    """SSE-style ETF option short-leg margin (research approximation)."""
    spot = max(float(spot), 0.0)
    strike = max(float(strike), 0.0)
    premium = max(float(premium), 0.0)
    mult = max(float(multiplier), 0.0)
    rate = max(float(margin_rate), 0.0)
    floor = max(float(floor_rate), 0.0)
    cp_u = str(cp).upper()[:1]
    if cp_u == "C":
        otm = max(0.0, strike - spot)
        inner = max(rate * spot - otm, floor * spot)
    else:
        otm = max(0.0, spot - strike)
        inner = max(rate * spot - otm, floor * strike)
    return (premium + inner) * mult


def estimate_strangle_margin(
    *,
    spot: float,
    call_strike: float,
    put_strike: float,
    call_premium: float,
    put_premium: float,
    multiplier: float,
    call_lots: int = 1,
    put_lots: int = 1,
    margin_rate: float = 0.12,
    floor_rate: float = 0.07,
) -> float:
    """Total short-strangle margin for given call/put lot counts."""
    call_m = estimate_short_leg_margin(
        spot=spot,
        strike=call_strike,
        premium=call_premium,
        cp="C",
        multiplier=multiplier,
        margin_rate=margin_rate,
        floor_rate=floor_rate,
    )
    put_m = estimate_short_leg_margin(
        spot=spot,
        strike=put_strike,
        premium=put_premium,
        cp="P",
        multiplier=multiplier,
        margin_rate=margin_rate,
        floor_rate=floor_rate,
    )
    return call_m * max(int(call_lots), 0) + put_m * max(int(put_lots), 0)


def size_by_kelly_margin(
    *,
    equity: float,
    spot: float,
    call_strike: float,
    put_strike: float,
    call_premium: float,
    put_premium: float,
    multiplier: float,
    win_prob: float,
    odds_b: float = 1.0,
    max_kelly_fraction: float = 0.25,
    max_lots: int = 20,
    min_lots: int = 1,
    margin_rate: float = 0.12,
    floor_rate: float = 0.07,
) -> KellySizingResult:
    """Map Kelly f* to integer base lots via margin budget (margin / equity)."""
    raw = kelly_fraction(win_prob, odds_b=odds_b)
    margin_per_lot = estimate_strangle_margin(
        spot=spot,
        call_strike=call_strike,
        put_strike=put_strike,
        call_premium=call_premium,
        put_premium=put_premium,
        multiplier=multiplier,
        call_lots=1,
        put_lots=1,
        margin_rate=margin_rate,
        floor_rate=floor_rate,
    )
    equity = max(float(equity), 0.0)
    max_f = max(float(max_kelly_fraction), 0.0)
    max_lots = max(int(max_lots), 0)
    min_lots = max(int(min_lots), 0)

    if raw <= 0 or equity <= 0 or margin_per_lot <= 0 or max_lots <= 0:
        return KellySizingResult(
            win_prob=float(win_prob),
            odds_b=float(odds_b),
            raw_fraction=float(raw),
            margin_ratio=0.0,
            base_lots=0,
            capped=False,
            blocked=True,
            reason="kelly_non_positive" if raw <= 0 else "invalid_budget",
            margin_budget=0.0,
            margin_per_lot=float(margin_per_lot),
            margin_used=0.0,
        )

    capped = raw > max_f
    margin_ratio = min(raw, max_f) if max_f > 0 else 0.0
    budget = equity * margin_ratio
    raw_lots = int(budget // margin_per_lot)
    lots = min(max(raw_lots, 0), max_lots)
    if lots < min_lots:
        return KellySizingResult(
            win_prob=float(win_prob),
            odds_b=float(odds_b),
            raw_fraction=float(raw),
            margin_ratio=float(margin_ratio),
            base_lots=0,
            capped=capped,
            blocked=True,
            reason="below_min_lot_margin",
            margin_budget=float(budget),
            margin_per_lot=float(margin_per_lot),
            margin_used=0.0,
        )
    if raw_lots > max_lots:
        capped = True
    used = float(lots) * float(margin_per_lot)
    return KellySizingResult(
        win_prob=float(win_prob),
        odds_b=float(odds_b),
        raw_fraction=float(raw),
        margin_ratio=float(margin_ratio),
        base_lots=int(lots),
        capped=bool(capped),
        blocked=False,
        reason="capped" if capped else "ok",
        margin_budget=float(budget),
        margin_per_lot=float(margin_per_lot),
        margin_used=float(used),
    )


def size_short_premium_lots(
    *,
    equity: float,
    call_premium: float,
    put_premium: float,
    multiplier: float,
    win_prob: float,
    odds_b: float = 1.0,
    max_kelly_fraction: float = 0.25,
    max_lots: int = 20,
    min_lots: int = 1,
    spot: float | None = None,
    call_strike: float | None = None,
    put_strike: float | None = None,
    margin_rate: float = 0.12,
    floor_rate: float = 0.07,
) -> KellySizingResult:
    """Back-compat wrapper; prefers margin-ratio Kelly when spot/strikes given."""
    spot_v = float(spot) if spot is not None else max(float(call_premium) + float(put_premium), 1e-6)
    call_k = float(call_strike) if call_strike is not None else spot_v
    put_k = float(put_strike) if put_strike is not None else spot_v
    return size_by_kelly_margin(
        equity=equity,
        spot=spot_v,
        call_strike=call_k,
        put_strike=put_k,
        call_premium=call_premium,
        put_premium=put_premium,
        multiplier=multiplier,
        win_prob=win_prob,
        odds_b=odds_b,
        max_kelly_fraction=max_kelly_fraction,
        max_lots=max_lots,
        min_lots=min_lots,
        margin_rate=margin_rate,
        floor_rate=floor_rate,
    )
