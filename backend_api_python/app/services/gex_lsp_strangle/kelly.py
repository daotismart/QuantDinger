"""Kelly sizing for short-premium books with 1:1 premium odds.

For a short strangle, treat collected premium as the unit stake. With odds b=1
(risking ~1× credit to earn 1× credit), Kelly reduces to::

    f* = p - q = 2p - 1

where ``p`` is win probability and ``q = 1 - p``. Negative f* means no trade.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class KellySizingResult:
    win_prob: float
    odds_b: float
    raw_fraction: float
    fraction: float
    base_lots: int
    capped: bool
    blocked: bool
    reason: str
    capital_budget: float
    capital_per_lot: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "winProb": round(self.win_prob, 6),
            "oddsB": round(self.odds_b, 6),
            "rawFraction": round(self.raw_fraction, 6),
            "fraction": round(self.fraction, 6),
            "baseLots": int(self.base_lots),
            "capped": bool(self.capped),
            "blocked": bool(self.blocked),
            "reason": self.reason,
            "capitalBudget": round(self.capital_budget, 2),
            "capitalPerLot": round(self.capital_per_lot, 2),
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
    """Bayesian-smoothed win rate from closed trade PnLs."""
    prior_p = min(max(float(prior_p), 0.01), 0.99)
    strength = max(float(prior_strength), 0.0)
    wins = sum(1 for x in closed_pnls if float(x) > 0)
    n = len(closed_pnls)
    return (prior_p * strength + wins) / (strength + n) if (strength + n) > 0 else prior_p


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
) -> KellySizingResult:
    """Map Kelly fraction to integer short-strangle lots with hard risk caps.

    Capital-at-risk per lot is the credit received (call+put)×multiplier, matching
    the 1:1 premium odds assumption. Exceeding ``max_kelly_fraction`` or
    ``max_lots`` is clamped (risk control) rather than rejected unless f*≤0.
    """
    raw = kelly_fraction(win_prob, odds_b=odds_b)
    credit = max(float(call_premium), 0.0) + max(float(put_premium), 0.0)
    capital_per_lot = credit * float(multiplier)
    equity = max(float(equity), 0.0)
    max_f = max(float(max_kelly_fraction), 0.0)
    max_lots = max(int(max_lots), 0)
    min_lots = max(int(min_lots), 0)

    if raw <= 0 or equity <= 0 or capital_per_lot <= 0 or max_lots <= 0:
        return KellySizingResult(
            win_prob=float(win_prob),
            odds_b=float(odds_b),
            raw_fraction=float(raw),
            fraction=0.0,
            base_lots=0,
            capped=False,
            blocked=True,
            reason="kelly_non_positive" if raw <= 0 else "invalid_budget",
            capital_budget=0.0,
            capital_per_lot=float(capital_per_lot),
        )

    capped = raw > max_f
    fraction = min(raw, max_f) if max_f > 0 else 0.0
    budget = equity * fraction
    raw_lots = int(budget // capital_per_lot)
    lots = min(max(raw_lots, 0), max_lots)
    if lots < min_lots:
        return KellySizingResult(
            win_prob=float(win_prob),
            odds_b=float(odds_b),
            raw_fraction=float(raw),
            fraction=float(fraction),
            base_lots=0,
            capped=capped,
            blocked=True,
            reason="below_min_lot_budget",
            capital_budget=float(budget),
            capital_per_lot=float(capital_per_lot),
        )
    if raw_lots > max_lots:
        capped = True
    return KellySizingResult(
        win_prob=float(win_prob),
        odds_b=float(odds_b),
        raw_fraction=float(raw),
        fraction=float(fraction),
        base_lots=int(lots),
        capped=bool(capped),
        blocked=False,
        reason="capped" if capped else "ok",
        capital_budget=float(budget),
        capital_per_lot=float(capital_per_lot),
    )
