"""Daily short-vol backtest for ETF options short strangles.

GEX walls pick safe OTM strikes; sell only when IV rank is high.
Kelly (premium odds 1:1) sets the account **margin utilization ratio**;
LSP sets the **net delta exposure**; call/put lot skew realizes that delta.
Margin above the Kelly budget is scaled down as risk control. No spot hedge.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

import numpy as np
import pandas as pd

from app.services.gex_lsp_strangle.gex_walls import compute_gex_walls, select_strangle_strikes
from app.services.gex_lsp_strangle.kelly import (
    estimate_strangle_margin,
    estimate_win_prob,
    size_by_kelly_margin,
)
from app.services.gex_lsp_strangle.lsp import (
    compute_lsp_features,
    lsp_delta_exposure_shares,
    lsp_option_skew_lots,
    lsp_target_delta_shares,
)


@dataclass
class ShortStrangleBacktestConfig:
    underlying_code: str = "510050"
    initial_capital: float = 1_000_000.0
    lots: int = 1
    multiplier: float = 10000.0
    commission_per_lot: float = 5.0
    slippage_pct: float = 0.02
    min_dte: int = 7
    max_dte: int = 45
    min_width_pct: float = 0.03
    max_hold_days: int = 15
    exit_dte: int = 5
    lsp_days_1: int = 5
    lsp_days_2: int = 10
    lsp_neutral_band: float = 8.0
    # |target delta| cap as a fraction of one short-lot notional delta (reporting + lot picker).
    lsp_max_abs_delta: float = 0.5
    # Extra short lots tilted by LSP (call vs put asymmetry).
    lsp_max_skew_lots: int = 1
    require_inside_walls: bool = True
    wall_buffer_pct: float = 0.005
    # Re-skew option lots when LSP score changes by this much.
    reskew_score_band: float = 0.25
    # Sell only when ATM IV rank is elevated (short premium).
    require_high_iv: bool = True
    iv_lookback: int = 60
    iv_rank_min: float = 0.60
    # Kelly (premium odds 1:1) → margin/equity ratio; LSP sets delta exposure.
    use_kelly_sizing: bool = True
    kelly_odds_b: float = 1.0
    kelly_prior_win_prob: float = 0.55
    kelly_prior_strength: float = 10.0
    kelly_max_fraction: float = 0.25  # hard cap on margin / equity
    kelly_max_lots: int = 10
    kelly_min_lots: int = 1
    # ETF option short-leg margin rates (SSE-style research approx).
    option_margin_rate: float = 0.12
    option_margin_floor_rate: float = 0.07


@dataclass
class _OpenTrade:
    entry_date: pd.Timestamp
    expire_date: str
    call_code: str
    put_code: str
    call_strike: float
    put_strike: float
    call_entry: float
    put_entry: float
    call_delta: float
    put_delta: float
    call_wall: float
    put_wall: float
    call_lots: int
    put_lots: int
    entry_spot: float
    lsp_score_entry: float
    target_delta_entry: float
    # Net cash from option sells(+) / buys(-), excluding commission (tracked separately).
    option_cash: float = 0.0
    option_fees: float = 0.0
    days_held: int = 0
    lsp_regime_entry: str = "neutral"


@dataclass
class ShortStrangleBacktestResult:
    summary: dict[str, Any]
    equity_curve: list[dict[str, Any]] = field(default_factory=list)
    trades: list[dict[str, Any]] = field(default_factory=list)
    daily: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "summary": self.summary,
            "equityCurve": self.equity_curve,
            "trades": self.trades,
            "daily": self.daily,
        }


def _fee(lots: int, commission_per_lot: float) -> float:
    return abs(int(lots)) * float(commission_per_lot)


def _premium_slip(price: float, side: str, slippage_pct: float) -> float:
    px = max(float(price), 0.0)
    slip = max(float(slippage_pct), 0.0)
    if side == "sell":
        return px * (1.0 - slip)
    return px * (1.0 + slip)


def _option_px(day_chain: pd.DataFrame, code: str, strike: float, cp: str) -> float:
    if day_chain is None or day_chain.empty:
        return 0.0
    hit = day_chain[day_chain["contract_code"].astype(str) == str(code)]
    if hit.empty:
        hit = day_chain[(day_chain["strike"] == float(strike)) & (day_chain["cp"] == cp)]
    if hit.empty:
        return 0.0
    px = hit["option_close"].iloc[0]
    return float(px) if pd.notna(px) else 0.0


def _option_delta(day_chain: pd.DataFrame, code: str, strike: float, cp: str, fallback: float) -> float:
    if day_chain is None or day_chain.empty:
        return float(fallback)
    hit = day_chain[day_chain["contract_code"].astype(str) == str(code)]
    if hit.empty:
        hit = day_chain[(day_chain["strike"] == float(strike)) & (day_chain["cp"] == cp)]
    if hit.empty or pd.isna(hit["delta"].iloc[0]):
        return float(fallback)
    return float(hit["delta"].iloc[0])


def _max_drawdown(equity: list[float]) -> float:
    if not equity:
        return 0.0
    peak = equity[0]
    max_dd = 0.0
    for value in equity:
        peak = max(peak, value)
        if peak > 0:
            max_dd = min(max_dd, value / peak - 1.0)
    return float(max_dd)


def _option_book_delta(
    *,
    call_lots: int,
    put_lots: int,
    call_delta: float,
    put_delta: float,
    multiplier: float,
) -> float:
    """Net delta of a short call/put book in underlying shares."""
    return (
        -float(call_lots) * float(call_delta) * float(multiplier)
        - float(put_lots) * float(put_delta) * float(multiplier)
    )


def _lots_for_option_hedge(
    *,
    lsp_score: float,
    target_delta_shares: float,
    call_delta: float,
    put_delta: float,
    base_lots: int,
    max_skew_lots: int,
    multiplier: float,
) -> tuple[int, int]:
    """Pick short call/put lots to approximate LSP target delta with options only.

    Starts from the LSP score skew grid, then chooses the (call, put) lot pair whose
    short-book delta is closest to ``target_delta_shares``.
    """
    base = max(int(base_lots), 1)
    max_skew = max(int(max_skew_lots), 0)
    candidates: set[tuple[int, int]] = {lsp_option_skew_lots(lsp_score, base_lots=base, max_skew_lots=max_skew)}
    for skew in range(0, max_skew + 1):
        candidates.add((base - skew, base + skew))
        candidates.add((base + skew, base - skew))
        candidates.add((base, base))
    best = (base, base)
    best_err = float("inf")
    for call_lots, put_lots in candidates:
        if call_lots < 0 or put_lots < 0:
            continue
        if call_lots + put_lots <= 0:
            continue
        book = _option_book_delta(
            call_lots=call_lots,
            put_lots=put_lots,
            call_delta=call_delta,
            put_delta=put_delta,
            multiplier=multiplier,
        )
        err = abs(book - float(target_delta_shares))
        # Mild preference for keeping both short-vol legs when error is similar.
        if call_lots == 0 or put_lots == 0:
            err += abs(float(target_delta_shares)) * 0.001 + 1.0
        if err < best_err:
            best_err = err
            best = (int(call_lots), int(put_lots))
    return best



def _atm_iv_by_date(panel: pd.DataFrame) -> pd.Series:
    """Daily ATM IV proxy: contracts closest to spot, averaged across calls/puts."""
    if panel is None or panel.empty or "iv" not in panel.columns:
        return pd.Series(dtype=float)
    df = panel.dropna(subset=["iv", "strike"]).copy()
    if df.empty or "underlying_close" not in df.columns:
        return pd.Series(dtype=float)
    df["underlying_close"] = pd.to_numeric(df["underlying_close"], errors="coerce")
    df["iv"] = pd.to_numeric(df["iv"], errors="coerce")
    df = df.dropna(subset=["underlying_close", "iv"])
    if df.empty:
        return pd.Series(dtype=float)
    df["moneyness"] = (df["strike"] - df["underlying_close"]).abs()
    rows: list[tuple[pd.Timestamp, float]] = []
    for dt, group in df.groupby("trade_date"):
        g = group.nsmallest(min(4, len(group)), "moneyness")
        iv = float(g["iv"].mean())
        if iv == iv and iv > 0:
            rows.append((pd.Timestamp(dt), iv))
    if not rows:
        return pd.Series(dtype=float)
    return pd.Series({d: v for d, v in rows}).sort_index()


def _iv_rank(iv_series: pd.Series, asof: pd.Timestamp, lookback: int) -> float | None:
    if iv_series is None or iv_series.empty:
        return None
    hist = iv_series.loc[:asof].dropna().tail(max(int(lookback), 2))
    if len(hist) < 2:
        return None
    cur = float(hist.iloc[-1])
    lo = float(hist.min())
    hi = float(hist.max())
    if hi <= lo:
        return 0.5
    return (cur - lo) / (hi - lo)


def prepare_panel(
    underlying: pd.DataFrame,
    chain: pd.DataFrame,
    oi: pd.DataFrame,
    *,
    config: ShortStrangleBacktestConfig,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Normalize vendor dumps into underlying bars + joined chain panel."""
    und = underlying.copy()
    und["trade_date"] = pd.to_datetime(und["trade_date"])
    und = und.sort_values("trade_date").drop_duplicates("trade_date")
    und["open"] = pd.to_numeric(und["open"], errors="coerce")
    und["high"] = pd.to_numeric(und["high"], errors="coerce")
    und["low"] = pd.to_numeric(und["low"], errors="coerce")
    und["close"] = pd.to_numeric(und["close"], errors="coerce")
    und["volume"] = pd.to_numeric(und.get("volume"), errors="coerce")
    if "amount" in und.columns:
        und["amount"] = pd.to_numeric(und["amount"], errors="coerce")
    und["open"] = und["open"].fillna(und["close"])
    und["high"] = und["high"].fillna(und[["open", "close"]].max(axis=1))
    und["low"] = und["low"].fillna(und[["open", "close"]].min(axis=1))
    und = und.dropna(subset=["close"]).set_index("trade_date")

    lsp = compute_lsp_features(
        und,
        days_1=config.lsp_days_1,
        days_2=config.lsp_days_2,
        neutral_band=config.lsp_neutral_band,
    )
    und = und.join(lsp)

    ch = chain.copy()
    ch["trade_date"] = pd.to_datetime(ch["trade_date"])
    ch["expire_date"] = pd.to_datetime(ch["expire_date"])
    ch["contract_code"] = ch["contract_code"].astype(str).str.strip()
    ch["cp"] = ch["cp"].astype(str).str.upper().str.strip().str[0]
    for col in ("strike", "option_close", "underlying_close", "delta", "gamma", "vega", "theta", "iv"):
        if col in ch.columns:
            ch[col] = pd.to_numeric(ch[col], errors="coerce")

    oi_df = oi.copy()
    oi_df["trade_date"] = pd.to_datetime(oi_df["trade_date"])
    oi_df["contract_code"] = oi_df["contract_code"].astype(str).str.strip()
    oi_df["open_interest"] = pd.to_numeric(oi_df["open_interest"], errors="coerce").fillna(0.0)
    oi_df = oi_df[["trade_date", "contract_code", "open_interest"]]

    panel = ch.merge(oi_df, on=["trade_date", "contract_code"], how="left")
    panel["open_interest"] = panel["open_interest"].fillna(0.0)
    return und, panel


def _adjust_option_lots(
    *,
    cash: float,
    open_trade: _OpenTrade,
    day_chain: pd.DataFrame,
    desired_call_lots: int,
    desired_put_lots: int,
    cfg: ShortStrangleBacktestConfig,
) -> tuple[float, _OpenTrade]:
    """Dynamically re-skew short call/put lots toward LSP-implied asymmetry."""
    call_px = _option_px(day_chain, open_trade.call_code, open_trade.call_strike, "C")
    put_px = _option_px(day_chain, open_trade.put_code, open_trade.put_strike, "P")

    def _apply_leg(cp: str, d_lots: int, px: float) -> None:
        nonlocal cash
        if d_lots == 0:
            return
        if d_lots > 0:
            fill = _premium_slip(px, "sell", cfg.slippage_pct)
            premium = fill * d_lots * cfg.multiplier
            fee = _fee(d_lots, cfg.commission_per_lot)
            cash += premium
            cash -= fee
            open_trade.option_cash += premium
            open_trade.option_fees += fee
            if cp == "C":
                open_trade.call_lots += d_lots
            else:
                open_trade.put_lots += d_lots
        else:
            qty = abs(d_lots)
            fill = _premium_slip(px, "buy", cfg.slippage_pct)
            premium = fill * qty * cfg.multiplier
            fee = _fee(qty, cfg.commission_per_lot)
            cash -= premium
            cash -= fee
            open_trade.option_cash -= premium
            open_trade.option_fees += fee
            if cp == "C":
                open_trade.call_lots -= qty
            else:
                open_trade.put_lots -= qty

    _apply_leg("C", int(desired_call_lots) - int(open_trade.call_lots), call_px)
    _apply_leg("P", int(desired_put_lots) - int(open_trade.put_lots), put_px)
    open_trade.call_lots = max(int(open_trade.call_lots), 0)
    open_trade.put_lots = max(int(open_trade.put_lots), 0)
    return cash, open_trade


def _close_option_book(
    *,
    cash: float,
    open_trade: _OpenTrade,
    call_px: float,
    put_px: float,
    exit_date: pd.Timestamp,
    cfg: ShortStrangleBacktestConfig,
    reason: str,
) -> tuple[float, dict[str, Any]]:
    cover_call = _premium_slip(call_px, "buy", cfg.slippage_pct)
    cover_put = _premium_slip(put_px, "buy", cfg.slippage_pct)
    exit_debit = (cover_call * open_trade.call_lots + cover_put * open_trade.put_lots) * cfg.multiplier
    exit_fee = _fee(open_trade.call_lots + open_trade.put_lots, cfg.commission_per_lot)
    cash -= exit_debit
    cash -= exit_fee
    open_trade.option_cash -= exit_debit
    open_trade.option_fees += exit_fee

    trade_pnl = open_trade.option_cash - open_trade.option_fees
    trade = {
        "entryDate": str(open_trade.entry_date.date()),
        "exitDate": str(pd.Timestamp(exit_date).date()),
        "reason": reason,
        "callStrike": open_trade.call_strike,
        "putStrike": open_trade.put_strike,
        "callCode": open_trade.call_code,
        "putCode": open_trade.put_code,
        "callLots": open_trade.call_lots,
        "putLots": open_trade.put_lots,
        "lspScoreEntry": round(open_trade.lsp_score_entry, 4),
        "targetDeltaEntry": round(open_trade.target_delta_entry, 2),
        "optionCash": round(open_trade.option_cash, 2),
        "fees": round(open_trade.option_fees, 2),
        "exitDebit": round(exit_debit, 2),
        "pnl": round(trade_pnl, 2),
        "daysHeld": open_trade.days_held,
        "callWall": open_trade.call_wall,
        "putWall": open_trade.put_wall,
        "lspRegimeEntry": open_trade.lsp_regime_entry,
    }
    return cash, trade


def run_short_strangle_backtest(
    underlying: pd.DataFrame,
    chain: pd.DataFrame,
    oi: pd.DataFrame,
    *,
    config: ShortStrangleBacktestConfig | None = None,
) -> ShortStrangleBacktestResult:
    """Run short-vol backtest: walls pick strikes, LSP delta hedged with options only."""
    cfg = config or ShortStrangleBacktestConfig()
    und, panel = prepare_panel(underlying, chain, oi, config=cfg)

    cash = float(cfg.initial_capital)
    equity_curve: list[dict[str, Any]] = []
    trades: list[dict[str, Any]] = []
    daily: list[dict[str, Any]] = []
    open_trade: _OpenTrade | None = None
    closed_pnls: list[float] = []
    atm_iv = _atm_iv_by_date(panel)

    dates = [d for d in und.index if d in set(panel["trade_date"].unique())]
    for dt in dates:
        row = und.loc[dt]
        spot = float(row["close"])
        day_chain = panel[panel["trade_date"] == dt].copy()
        walls = compute_gex_walls(
            day_chain,
            underlying=spot,
            multiplier=cfg.multiplier,
            min_dte=cfg.min_dte,
            max_dte=cfg.max_dte,
        )
        pick = select_strangle_strikes(walls, min_width_pct=cfg.min_width_pct)
        regime = str(row.get("lsp_regime") or "mixed")
        lsp_score = float(row.get("lsp_delta_score") or 0.0)
        if not np.isfinite(lsp_score):
            lsp_score = 0.0
        iv_rank = _iv_rank(atm_iv, pd.Timestamp(dt), cfg.iv_lookback)
        high_iv_ok = (not cfg.require_high_iv) or (
            iv_rank is not None and float(iv_rank) >= float(cfg.iv_rank_min)
        )
        win_prob = estimate_win_prob(
            closed_pnls,
            prior_p=cfg.kelly_prior_win_prob,
            prior_strength=cfg.kelly_prior_strength,
        )
        base_lots = max(int(cfg.lots), 1)
        kelly_info: dict[str, Any] = {
            "winProb": round(win_prob, 6),
            "fraction": None,
            "baseLots": base_lots,
            "ivRank": None if iv_rank is None else round(float(iv_rank), 4),
            "highIvOk": bool(high_iv_ok),
            "blocked": False,
            "reason": "fixed_lots",
        }
        target_delta = lsp_target_delta_shares(
            lsp_score,
            lots=base_lots,
            multiplier=cfg.multiplier,
            max_abs_delta=cfg.lsp_max_abs_delta,
        )

        # Default desired lots from score; refined with live deltas when in a trade / opening.
        desired_call_lots, desired_put_lots = lsp_option_skew_lots(
            lsp_score,
            base_lots=base_lots,
            max_skew_lots=cfg.lsp_max_skew_lots,
        )

        if open_trade is not None:
            open_trade.days_held += 1
            call_px = _option_px(day_chain, open_trade.call_code, open_trade.call_strike, "C")
            put_px = _option_px(day_chain, open_trade.put_code, open_trade.put_strike, "P")
            call_delta = _option_delta(
                day_chain, open_trade.call_code, open_trade.call_strike, "C", open_trade.call_delta
            )
            put_delta = _option_delta(
                day_chain, open_trade.put_code, open_trade.put_strike, "P", open_trade.put_delta
            )
            live_base = max(int(round((open_trade.call_lots + open_trade.put_lots) / 2.0)), 1)
            target_delta = lsp_target_delta_shares(
                lsp_score,
                lots=live_base,
                multiplier=cfg.multiplier,
                max_abs_delta=cfg.lsp_max_abs_delta,
            )
            desired_call_lots, desired_put_lots = _lots_for_option_hedge(
                lsp_score=lsp_score,
                target_delta_shares=target_delta,
                call_delta=call_delta,
                put_delta=put_delta,
                base_lots=live_base,
                max_skew_lots=cfg.lsp_max_skew_lots,
                multiplier=cfg.multiplier,
            )

            # Options-only hedge: re-skew call/put lots toward LSP target delta.
            if (
                abs(lsp_score - open_trade.lsp_score_entry) >= cfg.reskew_score_band
                or desired_call_lots != open_trade.call_lots
                or desired_put_lots != open_trade.put_lots
            ) and abs(lsp_score - open_trade.lsp_score_entry) >= cfg.reskew_score_band:
                cash, open_trade = _adjust_option_lots(
                    cash=cash,
                    open_trade=open_trade,
                    day_chain=day_chain,
                    desired_call_lots=desired_call_lots,
                    desired_put_lots=desired_put_lots,
                    cfg=cfg,
                )
                open_trade.lsp_score_entry = lsp_score
                open_trade.target_delta_entry = target_delta
                call_delta = _option_delta(
                    day_chain, open_trade.call_code, open_trade.call_strike, "C", call_delta
                )
                put_delta = _option_delta(
                    day_chain, open_trade.put_code, open_trade.put_strike, "P", put_delta
                )

            open_trade.call_delta = call_delta
            open_trade.put_delta = put_delta

            exit_reason = None
            dte = (pd.Timestamp(open_trade.expire_date) - dt).days
            if open_trade.call_lots <= 0 and open_trade.put_lots <= 0:
                exit_reason = "flat_options"
            elif dte <= cfg.exit_dte:
                exit_reason = "exit_dte"
            elif open_trade.days_held >= cfg.max_hold_days:
                exit_reason = "max_hold"
            elif spot >= open_trade.call_wall * (1.0 + cfg.wall_buffer_pct):
                exit_reason = "call_wall_breach"
            elif spot <= open_trade.put_wall * (1.0 - cfg.wall_buffer_pct):
                exit_reason = "put_wall_breach"

            if exit_reason:
                cash, trade = _close_option_book(
                    cash=cash,
                    open_trade=open_trade,
                    call_px=call_px,
                    put_px=put_px,
                    exit_date=dt,
                    cfg=cfg,
                    reason=exit_reason,
                )
                trades.append(trade)
                closed_pnls.append(float(trade.get("pnl") or 0.0))
                open_trade = None

        if open_trade is None and pick is not None:
            call_wall = float(pick["call_wall"])
            put_wall = float(pick["put_wall"])
            inside = (spot <= call_wall * (1.0 - cfg.wall_buffer_pct)) and (
                spot >= put_wall * (1.0 + cfg.wall_buffer_pct)
            )
            call_px = pick.get("call_close")
            put_px = pick.get("put_close")
            call_delta = float(pick.get("call_delta") or 0.25)
            put_delta = float(pick.get("put_delta") or -0.25)
            entry_allowed = bool(high_iv_ok)
            margin_budget = 0.0
            call_strike = float(pick.get("call_strike") or pick.get("call_wall") or spot)
            put_strike = float(pick.get("put_strike") or pick.get("put_wall") or spot)
            if cfg.use_kelly_sizing and call_px and put_px:
                kelly = size_by_kelly_margin(
                    equity=cash,
                    spot=spot,
                    call_strike=call_strike,
                    put_strike=put_strike,
                    call_premium=float(call_px),
                    put_premium=float(put_px),
                    multiplier=cfg.multiplier,
                    win_prob=win_prob,
                    odds_b=cfg.kelly_odds_b,
                    max_kelly_fraction=cfg.kelly_max_fraction,
                    max_lots=cfg.kelly_max_lots,
                    min_lots=cfg.kelly_min_lots,
                    margin_rate=cfg.option_margin_rate,
                    floor_rate=cfg.option_margin_floor_rate,
                )
                kelly_info = kelly.to_dict()
                kelly_info["ivRank"] = None if iv_rank is None else round(float(iv_rank), 4)
                kelly_info["highIvOk"] = bool(high_iv_ok)
                margin_budget = float(kelly.margin_budget)
                if kelly.blocked or kelly.base_lots <= 0:
                    entry_allowed = False
                    base_lots = 0
                else:
                    base_lots = int(kelly.base_lots)
                    if kelly.capped:
                        kelly_info["riskControl"] = "clamped_to_max_margin"
                if not high_iv_ok:
                    entry_allowed = False
                    kelly_info["blocked"] = True
                    kelly_info["reason"] = "iv_rank_too_low"
            elif not high_iv_ok:
                entry_allowed = False
                kelly_info["blocked"] = True
                kelly_info["reason"] = "iv_rank_too_low"
            else:
                margin_budget = float(
                    estimate_strangle_margin(
                        spot=spot,
                        call_strike=call_strike,
                        put_strike=put_strike,
                        call_premium=float(call_px or 0.0),
                        put_premium=float(put_px or 0.0),
                        multiplier=cfg.multiplier,
                        call_lots=base_lots,
                        put_lots=base_lots,
                        margin_rate=cfg.option_margin_rate,
                        floor_rate=cfg.option_margin_floor_rate,
                    )
                )
                kelly_info["marginBudget"] = round(margin_budget, 2)
                kelly_info["marginRatio"] = round(margin_budget / cash, 6) if cash > 0 else 0.0
                kelly_info["fraction"] = kelly_info["marginRatio"]

            # LSP owns directional delta exposure; Kelly only set the margin budget.
            if margin_budget > 0 and spot > 0:
                target_delta = lsp_delta_exposure_shares(
                    lsp_score,
                    margin_budget=margin_budget,
                    spot=spot,
                    max_abs_delta=cfg.lsp_max_abs_delta,
                )
            else:
                target_delta = lsp_target_delta_shares(
                    lsp_score,
                    lots=max(base_lots, 1),
                    multiplier=cfg.multiplier,
                    max_abs_delta=cfg.lsp_max_abs_delta,
                )
            desired_call_lots, desired_put_lots = _lots_for_option_hedge(
                lsp_score=lsp_score,
                target_delta_shares=target_delta,
                call_delta=call_delta,
                put_delta=put_delta,
                base_lots=max(base_lots, 1),
                max_skew_lots=cfg.lsp_max_skew_lots,
                multiplier=cfg.multiplier,
            )
            if base_lots <= 0:
                desired_call_lots, desired_put_lots = 0, 0
            # Risk control: scale lots down if LSP skew exceeds Kelly margin budget.
            if (
                entry_allowed
                and margin_budget > 0
                and desired_call_lots + desired_put_lots > 0
                and call_px
                and put_px
            ):
                used = estimate_strangle_margin(
                    spot=spot,
                    call_strike=call_strike,
                    put_strike=put_strike,
                    call_premium=float(call_px),
                    put_premium=float(put_px),
                    multiplier=cfg.multiplier,
                    call_lots=desired_call_lots,
                    put_lots=desired_put_lots,
                    margin_rate=cfg.option_margin_rate,
                    floor_rate=cfg.option_margin_floor_rate,
                )
                if used > margin_budget * 1.001 and used > 0:
                    scale = margin_budget / used
                    desired_call_lots = int(desired_call_lots * scale)
                    desired_put_lots = int(desired_put_lots * scale)
                    used = estimate_strangle_margin(
                        spot=spot,
                        call_strike=call_strike,
                        put_strike=put_strike,
                        call_premium=float(call_px),
                        put_premium=float(put_px),
                        multiplier=cfg.multiplier,
                        call_lots=desired_call_lots,
                        put_lots=desired_put_lots,
                        margin_rate=cfg.option_margin_rate,
                        floor_rate=cfg.option_margin_floor_rate,
                    )
                    kelly_info["riskControl"] = "scaled_to_kelly_margin"
                kelly_info["marginUsed"] = round(float(used), 2)
                if desired_call_lots + desired_put_lots <= 0:
                    entry_allowed = False
                    kelly_info["blocked"] = True
                    kelly_info["reason"] = "margin_scale_flat"

            if (
                entry_allowed
                and ((not cfg.require_inside_walls) or inside)
                and call_px
                and put_px
                and float(call_px) > 0
                and float(put_px) > 0
                and pick.get("call_code")
                and pick.get("put_code")
                and desired_call_lots + desired_put_lots > 0
            ):
                call_fill = _premium_slip(float(call_px), "sell", cfg.slippage_pct)
                put_fill = _premium_slip(float(put_px), "sell", cfg.slippage_pct)
                call_premium = call_fill * desired_call_lots * cfg.multiplier
                put_premium = put_fill * desired_put_lots * cfg.multiplier
                open_fee = _fee(desired_call_lots + desired_put_lots, cfg.commission_per_lot)
                cash += call_premium + put_premium
                cash -= open_fee
                open_trade = _OpenTrade(
                    entry_date=dt,
                    expire_date=str(pick["expire_date"]),
                    call_code=str(pick["call_code"]),
                    put_code=str(pick["put_code"]),
                    call_strike=float(pick["call_strike"]),
                    put_strike=float(pick["put_strike"]),
                    call_entry=call_fill,
                    put_entry=put_fill,
                    call_delta=call_delta,
                    put_delta=put_delta,
                    call_wall=call_wall,
                    put_wall=put_wall,
                    call_lots=desired_call_lots,
                    put_lots=desired_put_lots,
                    entry_spot=spot,
                    lsp_score_entry=lsp_score,
                    target_delta_entry=target_delta,
                    option_cash=call_premium + put_premium,
                    option_fees=open_fee,
                    days_held=0,
                    lsp_regime_entry=regime,
                )

        liability = 0.0
        net_delta = 0.0
        if open_trade is not None:
            call_px = _option_px(day_chain, open_trade.call_code, open_trade.call_strike, "C")
            put_px = _option_px(day_chain, open_trade.put_code, open_trade.put_strike, "P")
            liability = -(
                call_px * open_trade.call_lots + put_px * open_trade.put_lots
            ) * cfg.multiplier
            net_delta = _option_book_delta(
                call_lots=open_trade.call_lots,
                put_lots=open_trade.put_lots,
                call_delta=open_trade.call_delta,
                put_delta=open_trade.put_delta,
                multiplier=cfg.multiplier,
            )
        equity = cash + liability
        equity_curve.append({"date": str(dt.date()), "equity": round(float(equity), 2)})
        daily.append(
            {
                "date": str(dt.date()),
                "spot": spot,
                "lspRegime": regime,
                "lspDeltaScore": round(lsp_score, 4),
                "targetDeltaShares": round(target_delta, 2),
                "netDeltaShares": round(net_delta, 2),
                "desiredCallLots": desired_call_lots,
                "desiredPutLots": desired_put_lots,
                "callWall": walls.get("call_wall"),
                "putWall": walls.get("put_wall"),
                "pin": walls.get("pin"),
                "flip": walls.get("flip"),
                "inPosition": open_trade is not None,
                "equity": round(float(equity), 2),
                "ivRank": kelly_info.get("ivRank"),
                "highIvOk": kelly_info.get("highIvOk"),
                "kellyFraction": kelly_info.get("fraction"),
                "kellyMarginRatio": kelly_info.get("marginRatio", kelly_info.get("fraction")),
                "kellyBaseLots": kelly_info.get("baseLots"),
                "kellyBlocked": kelly_info.get("blocked"),
                "kellyReason": kelly_info.get("reason"),
                "marginBudget": kelly_info.get("marginBudget"),
                "marginUsed": kelly_info.get("marginUsed"),
                "marginPerLot": kelly_info.get("marginPerLot"),
            }
        )

    if open_trade is not None and dates:
        dt = dates[-1]
        day_chain = panel[panel["trade_date"] == dt]
        call_px = _option_px(day_chain, open_trade.call_code, open_trade.call_strike, "C")
        put_px = _option_px(day_chain, open_trade.put_code, open_trade.put_strike, "P")
        cash, trade = _close_option_book(
            cash=cash,
            open_trade=open_trade,
            call_px=call_px,
            put_px=put_px,
            exit_date=dt,
            cfg=cfg,
            reason="eod_force_close",
        )
        trades.append(trade)
        if equity_curve and equity_curve[-1]["date"] == str(pd.Timestamp(dt).date()):
            equity_curve[-1]["equity"] = round(float(cash), 2)
        else:
            equity_curve.append({"date": str(pd.Timestamp(dt).date()), "equity": round(float(cash), 2)})

    final_equity = equity_curve[-1]["equity"] if equity_curve else cfg.initial_capital
    rets = pd.Series([p["equity"] for p in equity_curve], dtype=float).pct_change().dropna()
    vol = float(rets.std() * np.sqrt(252)) if len(rets) else 0.0
    ret = final_equity / cfg.initial_capital - 1.0
    sharpe = float((rets.mean() * 252) / (rets.std() * np.sqrt(252))) if len(rets) and rets.std() > 0 else 0.0
    max_dd = _max_drawdown([p["equity"] for p in equity_curve])
    wins = [t for t in trades if t.get("pnl", 0) > 0]
    summary = {
        "underlying": cfg.underlying_code,
        "initialCapital": cfg.initial_capital,
        "finalEquity": final_equity,
        "totalReturn": round(ret, 6),
        "annualizedVol": round(vol, 6),
        "sharpe": round(sharpe, 4),
        "maxDrawdown": round(max_dd, 6),
        "trades": len(trades),
        "winRate": round(len(wins) / len(trades), 4) if trades else 0.0,
        "avgTradePnl": round(float(np.mean([t["pnl"] for t in trades])), 2) if trades else 0.0,
        "hedgeMode": "options_only",
        "sizingMode": "kelly_margin_ratio" if cfg.use_kelly_sizing else "fixed_lots",
        "requireHighIv": bool(cfg.require_high_iv),
        "kellyOddsB": float(cfg.kelly_odds_b),
        "config": asdict(cfg),
    }
    return ShortStrangleBacktestResult(
        summary=summary,
        equity_curve=equity_curve,
        trades=trades,
        daily=daily,
    )
