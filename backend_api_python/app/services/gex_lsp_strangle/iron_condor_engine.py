"""ETF options iron-condor backtest (GEX walls + high-IV + Kelly defined-risk + LSP skew).

Iron condor = short strangle at/near GEX walls + long further-OTM wings.
Kelly sizes on defined-risk margin; LSP skews short call/put lots (wings match).
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

import numpy as np
import pandas as pd

from app.services.gex_lsp_strangle.engine import (
    ShortStrangleBacktestConfig,
    _atm_iv_by_date,
    _fee,
    _iv_rank,
    _max_drawdown,
    _option_px,
    _premium_slip,
    prepare_panel,
)
from app.services.gex_lsp_strangle.gex_walls import compute_gex_walls, select_iron_condor_strikes
from app.services.gex_lsp_strangle.kelly import estimate_win_prob, kelly_fraction
from app.services.gex_lsp_strangle.lsp import lsp_option_skew_lots


@dataclass
class IronCondorBacktestConfig(ShortStrangleBacktestConfig):
    wing_steps: int = 1
    wing_pct: float = 0.0
    take_profit_pct: float = 0.50  # close when remaining debit <= (1-tp)*entry credit cash
    stop_loss_pct: float = 0.90  # close when MTM loss >= stop * max_risk
    # 0 = short at GEX walls (default). >0 = short that percent OTM from spot.
    short_otm_pct: float = 0.0
    min_credit_to_width: float = 0.0
    exit_on_short_breach: bool = True
    exit_on_wall_breach: bool = True
    # Defined-risk margin per lot is small; default to fixed 120 lots on 1M capital.
    lots: int = 120
    use_kelly_sizing: bool = False
    require_high_iv: bool = False
    require_inside_walls: bool = False
    kelly_max_lots: int = 150
    kelly_prior_win_prob: float = 0.60
    lsp_max_skew_lots: int = 0
    max_hold_days: int = 60
    roll_before_dte: int = 15
    exit_dte: int = 15
    # Skip / flatten when |spot return over trend_lookback bars| exceeds this.
    max_abs_trend_pct: float = 0.08
    trend_lookback: int = 20


@dataclass
class _OpenIronCondor:
    entry_date: pd.Timestamp
    expire_date: str
    short_call_code: str
    short_put_code: str
    long_call_code: str
    long_put_code: str
    short_call_strike: float
    short_put_strike: float
    long_call_strike: float
    long_put_strike: float
    call_wall: float
    put_wall: float
    call_lots: int
    put_lots: int
    entry_spot: float
    entry_credit: float  # per-share net credit (mid, pre-slip)
    entry_credit_cash: float  # cash credit after slip at open
    max_risk: float  # cash max loss for current lots
    lsp_score_entry: float
    option_cash: float = 0.0
    option_fees: float = 0.0
    days_held: int = 0
    lsp_regime_entry: str = "neutral"


@dataclass
class IronCondorBacktestResult:
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


def estimate_iron_condor_margin(
    *,
    short_call_strike: float,
    long_call_strike: float,
    short_put_strike: float,
    long_put_strike: float,
    net_credit: float,
    multiplier: float,
    lots: int = 1,
) -> float:
    call_wing = max(float(long_call_strike) - float(short_call_strike), 0.0)
    put_wing = max(float(short_put_strike) - float(long_put_strike), 0.0)
    wing = max(call_wing, put_wing)
    per_lot = max(wing - max(float(net_credit), 0.0), 0.0) * float(multiplier)
    return per_lot * max(int(lots), 0)


def size_iron_condor_lots(
    *,
    equity: float,
    short_call_strike: float,
    long_call_strike: float,
    short_put_strike: float,
    long_put_strike: float,
    net_credit: float,
    multiplier: float,
    win_prob: float,
    odds_b: float = 1.0,
    max_kelly_fraction: float = 0.25,
    max_lots: int = 20,
    min_lots: int = 1,
) -> dict[str, Any]:
    raw = kelly_fraction(win_prob, odds_b=odds_b)
    margin_per = estimate_iron_condor_margin(
        short_call_strike=short_call_strike,
        long_call_strike=long_call_strike,
        short_put_strike=short_put_strike,
        long_put_strike=long_put_strike,
        net_credit=net_credit,
        multiplier=multiplier,
        lots=1,
    )
    equity = max(float(equity), 0.0)
    max_f = max(float(max_kelly_fraction), 0.0)
    if raw <= 0 or equity <= 0 or margin_per <= 0:
        return {
            "winProb": float(win_prob),
            "fraction": 0.0,
            "marginRatio": 0.0,
            "baseLots": 0,
            "blocked": True,
            "reason": "kelly_non_positive" if raw <= 0 else "invalid_budget",
            "marginBudget": 0.0,
            "marginPerLot": float(margin_per),
            "marginUsed": 0.0,
            "capped": False,
        }
    capped = raw > max_f
    ratio = min(raw, max_f) if max_f > 0 else 0.0
    budget = equity * ratio
    raw_lots = int(budget // margin_per)
    lots = min(max(raw_lots, 0), int(max_lots))
    if lots < int(min_lots):
        return {
            "winProb": float(win_prob),
            "fraction": float(ratio),
            "marginRatio": float(ratio),
            "baseLots": 0,
            "blocked": True,
            "reason": "below_min_lot_margin",
            "marginBudget": float(budget),
            "marginPerLot": float(margin_per),
            "marginUsed": 0.0,
            "capped": capped,
        }
    if raw_lots > int(max_lots):
        capped = True
    return {
        "winProb": float(win_prob),
        "fraction": float(ratio),
        "marginRatio": float(ratio),
        "baseLots": int(lots),
        "blocked": False,
        "reason": "capped" if capped else "ok",
        "marginBudget": float(budget),
        "marginPerLot": float(margin_per),
        "marginUsed": float(lots) * float(margin_per),
        "capped": capped,
    }


def _close_cost(
    open_trade: _OpenIronCondor,
    day_chain: pd.DataFrame,
    cfg: IronCondorBacktestConfig,
) -> dict[str, float]:
    sc = _option_px(day_chain, open_trade.short_call_code, open_trade.short_call_strike, "C")
    sp = _option_px(day_chain, open_trade.short_put_code, open_trade.short_put_strike, "P")
    lc = _option_px(day_chain, open_trade.long_call_code, open_trade.long_call_strike, "C")
    lp = _option_px(day_chain, open_trade.long_put_code, open_trade.long_put_strike, "P")
    debit = (
        _premium_slip(sc, "buy", cfg.slippage_pct) * open_trade.call_lots
        + _premium_slip(sp, "buy", cfg.slippage_pct) * open_trade.put_lots
        - _premium_slip(lc, "sell", cfg.slippage_pct) * open_trade.call_lots
        - _premium_slip(lp, "sell", cfg.slippage_pct) * open_trade.put_lots
    ) * cfg.multiplier
    fee = _fee(2 * (open_trade.call_lots + open_trade.put_lots), cfg.commission_per_lot)
    return {"close_debit": float(debit), "close_fee": float(fee)}


def _close_iron_condor(
    *,
    cash: float,
    open_trade: _OpenIronCondor,
    day_chain: pd.DataFrame,
    exit_date: pd.Timestamp,
    cfg: IronCondorBacktestConfig,
    reason: str,
) -> tuple[float, dict[str, Any]]:
    mark = _close_cost(open_trade, day_chain, cfg)
    cash -= mark["close_debit"]
    cash -= mark["close_fee"]
    open_trade.option_cash -= mark["close_debit"]
    open_trade.option_fees += mark["close_fee"]
    pnl = open_trade.option_cash - open_trade.option_fees
    trade = {
        "entryDate": str(open_trade.entry_date.date()),
        "exitDate": str(pd.Timestamp(exit_date).date()),
        "expireDate": str(pd.Timestamp(open_trade.expire_date).date()),
        "reason": reason,
        "structure": "iron_condor",
        "shortCallStrike": open_trade.short_call_strike,
        "shortPutStrike": open_trade.short_put_strike,
        "longCallStrike": open_trade.long_call_strike,
        "longPutStrike": open_trade.long_put_strike,
        "shortCallCode": open_trade.short_call_code,
        "shortPutCode": open_trade.short_put_code,
        "longCallCode": open_trade.long_call_code,
        "longPutCode": open_trade.long_put_code,
        "callLots": open_trade.call_lots,
        "putLots": open_trade.put_lots,
        "entryCredit": round(open_trade.entry_credit, 4),
        "maxRisk": round(open_trade.max_risk, 2),
        "lspScoreEntry": round(open_trade.lsp_score_entry, 4),
        "optionCash": round(open_trade.option_cash, 2),
        "fees": round(open_trade.option_fees, 2),
        "exitDebit": round(mark["close_debit"], 2),
        "pnl": round(pnl, 2),
        "daysHeld": open_trade.days_held,
        "callWall": open_trade.call_wall,
        "putWall": open_trade.put_wall,
        "lspRegimeEntry": open_trade.lsp_regime_entry,
        "entrySpot": open_trade.entry_spot,
    }
    return cash, trade


def run_iron_condor_backtest(
    underlying: pd.DataFrame,
    chain: pd.DataFrame,
    oi: pd.DataFrame,
    *,
    config: IronCondorBacktestConfig | None = None,
) -> IronCondorBacktestResult:
    cfg = config or IronCondorBacktestConfig()
    und, panel = prepare_panel(underlying, chain, oi, config=cfg)

    cash = float(cfg.initial_capital)
    equity_curve: list[dict[str, Any]] = []
    trades: list[dict[str, Any]] = []
    daily: list[dict[str, Any]] = []
    open_trade: _OpenIronCondor | None = None
    closed_pnls: list[float] = []
    pending_roll = False
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
            expiry_month=cfg.expiry_month,
        )
        pick = select_iron_condor_strikes(
            walls,
            min_width_pct=cfg.min_width_pct,
            wing_steps=cfg.wing_steps,
            wing_pct=cfg.wing_pct,
            short_otm_pct=cfg.short_otm_pct,
            min_credit_to_width=cfg.min_credit_to_width,
        )
        regime = str(row.get("lsp_regime") or "mixed")
        lsp_score = float(row.get("lsp_delta_score") or 0.0)
        if not np.isfinite(lsp_score):
            lsp_score = 0.0
        trend = 0.0
        if int(cfg.trend_lookback) > 0:
            hist = und["close"].loc[:dt]
            lb = int(cfg.trend_lookback)
            if len(hist) > lb:
                base = float(hist.iloc[-(lb + 1)])
                if base > 0:
                    trend = spot / base - 1.0
        trend_block = float(cfg.max_abs_trend_pct) > 0 and abs(trend) > float(cfg.max_abs_trend_pct)
        iv_rank = _iv_rank(atm_iv, pd.Timestamp(dt), cfg.iv_lookback)
        high_iv_ok = (not cfg.require_high_iv) or (
            iv_rank is not None and float(iv_rank) >= float(cfg.iv_rank_min)
        )
        win_prob = estimate_win_prob(
            closed_pnls,
            prior_p=cfg.kelly_prior_win_prob,
            prior_strength=cfg.kelly_prior_strength,
        )
        kelly_info: dict[str, Any] = {
            "winProb": round(win_prob, 6),
            "ivRank": None if iv_rank is None else round(float(iv_rank), 4),
            "highIvOk": bool(high_iv_ok),
            "fraction": None,
            "baseLots": max(int(cfg.lots), 1),
            "blocked": False,
            "reason": "fixed_lots",
        }

        if open_trade is not None:
            open_trade.days_held += 1
            mark = _close_cost(open_trade, day_chain, cfg)
            exit_reason = None
            dte = (pd.Timestamp(open_trade.expire_date) - pd.Timestamp(dt)).days
            roll_dte = int(cfg.roll_before_dte or cfg.exit_dte)
            if dte <= roll_dte:
                exit_reason = "roll_month"
            elif open_trade.days_held >= cfg.max_hold_days:
                exit_reason = "max_hold"
            elif cfg.exit_on_short_breach and spot >= open_trade.short_call_strike:
                exit_reason = "short_call_breach"
            elif cfg.exit_on_short_breach and spot <= open_trade.short_put_strike:
                exit_reason = "short_put_breach"
            elif cfg.exit_on_wall_breach and spot >= open_trade.call_wall * (1.0 + cfg.wall_buffer_pct):
                exit_reason = "call_wall_breach"
            elif cfg.exit_on_wall_breach and spot <= open_trade.put_wall * (1.0 - cfg.wall_buffer_pct):
                exit_reason = "put_wall_breach"
            elif trend_block:
                exit_reason = "trend_filter"
            elif spot >= open_trade.long_call_strike or spot <= open_trade.long_put_strike:
                exit_reason = "wing_breach"
            else:
                entry_credit_cash = float(open_trade.entry_credit_cash)
                if entry_credit_cash > 0 and mark["close_debit"] <= entry_credit_cash * (
                    1.0 - float(cfg.take_profit_pct)
                ):
                    exit_reason = "take_profit"
                else:
                    mtm = open_trade.option_cash - open_trade.option_fees - mark["close_debit"] - mark["close_fee"]
                    if open_trade.max_risk > 0 and mtm <= -float(cfg.stop_loss_pct) * open_trade.max_risk:
                        exit_reason = "stop_loss"

            if exit_reason:
                cash, trade = _close_iron_condor(
                    cash=cash,
                    open_trade=open_trade,
                    day_chain=day_chain,
                    exit_date=dt,
                    cfg=cfg,
                    reason=exit_reason,
                )
                trades.append(trade)
                closed_pnls.append(float(trade.get("pnl") or 0.0))
                pending_roll = exit_reason == "roll_month"
                open_trade = None

        if open_trade is None and pick is not None:
            call_wall = float(pick["call_wall"])
            put_wall = float(pick["put_wall"])
            inside = (spot <= call_wall * (1.0 - cfg.wall_buffer_pct)) and (
                spot >= put_wall * (1.0 + cfg.wall_buffer_pct)
            )
            sc_px = float(pick.get("call_close") or 0.0)
            sp_px = float(pick.get("put_close") or 0.0)
            lc_px = float(pick.get("long_call_close") or 0.0)
            lp_px = float(pick.get("long_put_close") or 0.0)
            call_credit = max(sc_px - lc_px, 0.0)
            put_credit = max(sp_px - lp_px, 0.0)
            net_credit = call_credit + put_credit
            high_iv = high_iv_ok or (pending_roll and cfg.roll_skip_iv_filter)
            entry_allowed = bool(high_iv) and net_credit > 0 and (
                (not cfg.require_inside_walls) or inside
            ) and not trend_block
            base_lots = max(int(cfg.lots), 1)
            if cfg.use_kelly_sizing:
                kelly = size_iron_condor_lots(
                    equity=cash,
                    short_call_strike=float(pick["call_strike"]),
                    long_call_strike=float(pick["long_call_strike"]),
                    short_put_strike=float(pick["put_strike"]),
                    long_put_strike=float(pick["long_put_strike"]),
                    net_credit=net_credit,
                    multiplier=cfg.multiplier,
                    win_prob=win_prob,
                    odds_b=cfg.kelly_odds_b,
                    max_kelly_fraction=cfg.kelly_max_fraction,
                    max_lots=cfg.kelly_max_lots,
                    min_lots=cfg.kelly_min_lots,
                )
                kelly_info.update(kelly)
                if kelly["blocked"] or kelly["baseLots"] <= 0:
                    entry_allowed = False
                    base_lots = 0
                else:
                    base_lots = int(kelly["baseLots"])
            if not high_iv:
                entry_allowed = False
                kelly_info["blocked"] = True
                kelly_info["reason"] = "iv_rank_too_low"
            if trend_block:
                entry_allowed = False
                kelly_info["blocked"] = True
                kelly_info["reason"] = "trend_filter"

            call_lots, put_lots = lsp_option_skew_lots(
                lsp_score,
                base_lots=max(base_lots, 1),
                max_skew_lots=cfg.lsp_max_skew_lots,
            )
            if base_lots <= 0:
                call_lots, put_lots = 0, 0

            if entry_allowed and call_lots > 0 and put_lots > 0:
                sc_fill = _premium_slip(sc_px, "sell", cfg.slippage_pct)
                sp_fill = _premium_slip(sp_px, "sell", cfg.slippage_pct)
                lc_fill = _premium_slip(lc_px, "buy", cfg.slippage_pct)
                lp_fill = _premium_slip(lp_px, "buy", cfg.slippage_pct)
                credit_cash = (
                    sc_fill * call_lots + sp_fill * put_lots - lc_fill * call_lots - lp_fill * put_lots
                ) * cfg.multiplier
                if credit_cash <= 0:
                    kelly_info["blocked"] = True
                    kelly_info["reason"] = "debit_after_slippage"
                else:
                    open_fee = _fee(2 * (call_lots + put_lots), cfg.commission_per_lot)
                    cash += credit_cash
                    cash -= open_fee
                    max_risk = estimate_iron_condor_margin(
                        short_call_strike=float(pick["call_strike"]),
                        long_call_strike=float(pick["long_call_strike"]),
                        short_put_strike=float(pick["put_strike"]),
                        long_put_strike=float(pick["long_put_strike"]),
                        net_credit=net_credit,
                        multiplier=cfg.multiplier,
                        lots=max(call_lots, put_lots),
                    )
                    open_trade = _OpenIronCondor(
                        entry_date=pd.Timestamp(dt),
                        expire_date=str(pick.get("expire_date") or walls.get("expire_date")),
                        short_call_code=str(pick.get("call_code") or ""),
                        short_put_code=str(pick.get("put_code") or ""),
                        long_call_code=str(pick.get("long_call_code") or ""),
                        long_put_code=str(pick.get("long_put_code") or ""),
                        short_call_strike=float(pick["call_strike"]),
                        short_put_strike=float(pick["put_strike"]),
                        long_call_strike=float(pick["long_call_strike"]),
                        long_put_strike=float(pick["long_put_strike"]),
                        call_wall=call_wall,
                        put_wall=put_wall,
                        call_lots=int(call_lots),
                        put_lots=int(put_lots),
                        entry_spot=spot,
                        entry_credit=float(net_credit),
                        entry_credit_cash=float(credit_cash),
                        max_risk=float(max_risk),
                        lsp_score_entry=lsp_score,
                        option_cash=float(credit_cash),
                        option_fees=float(open_fee),
                        days_held=0,
                        lsp_regime_entry=regime,
                    )
                    pending_roll = False

        if open_trade is not None:
            mark = _close_cost(open_trade, day_chain, cfg)
            equity = float(cash) - mark["close_debit"] - mark["close_fee"]
        else:
            equity = float(cash)

        equity_curve.append({"date": str(pd.Timestamp(dt).date()), "equity": round(float(equity), 2)})
        daily.append(
            {
                "date": str(pd.Timestamp(dt).date()),
                "spot": spot,
                "lspRegime": regime,
                "lspDeltaScore": round(lsp_score, 4),
                "callWall": walls.get("call_wall"),
                "putWall": walls.get("put_wall"),
                "inPosition": open_trade is not None,
                "equity": round(float(equity), 2),
                "ivRank": kelly_info.get("ivRank"),
                "highIvOk": kelly_info.get("highIvOk"),
                "kellyFraction": kelly_info.get("fraction"),
                "kellyBaseLots": kelly_info.get("baseLots"),
                "kellyBlocked": kelly_info.get("blocked"),
                "kellyReason": kelly_info.get("reason"),
                "trend": round(float(trend), 4),
                "trendBlock": bool(trend_block),
            }
        )

    if open_trade is not None and dates:
        dt = dates[-1]
        day_chain = panel[panel["trade_date"] == dt]
        cash, trade = _close_iron_condor(
            cash=cash,
            open_trade=open_trade,
            day_chain=day_chain,
            exit_date=dt,
            cfg=cfg,
            reason="eod_force_close",
        )
        trades.append(trade)
        if equity_curve and equity_curve[-1]["date"] == str(pd.Timestamp(dt).date()):
            equity_curve[-1]["equity"] = round(float(cash), 2)

    final_equity = equity_curve[-1]["equity"] if equity_curve else cfg.initial_capital
    rets = pd.Series([p["equity"] for p in equity_curve], dtype=float).pct_change().dropna()
    vol = float(rets.std() * np.sqrt(252)) if len(rets) else 0.0
    ret = final_equity / cfg.initial_capital - 1.0
    n_days = max(len(equity_curve), 1)
    ann = (1.0 + ret) ** (252.0 / n_days) - 1.0 if n_days > 1 else 0.0
    sharpe = (
        float((rets.mean() * 252) / (rets.std() * np.sqrt(252)))
        if len(rets) and rets.std() > 0
        else 0.0
    )
    max_dd = _max_drawdown([p["equity"] for p in equity_curve])
    wins = [t for t in trades if t.get("pnl", 0) > 0]
    summary = {
        "underlying": cfg.underlying_code,
        "structure": "iron_condor",
        "initialCapital": cfg.initial_capital,
        "finalEquity": final_equity,
        "totalReturn": round(ret, 6),
        "annualizedReturn": round(ann, 6),
        "tradingDays": int(n_days),
        "annualizedVol": round(vol, 6),
        "sharpe": round(sharpe, 4),
        "maxDrawdown": round(max_dd, 6),
        "trades": len(trades),
        "winRate": round(len(wins) / len(trades), 4) if trades else 0.0,
        "avgTradePnl": round(float(np.mean([t["pnl"] for t in trades])), 2) if trades else 0.0,
        "sizingMode": "kelly_defined_risk" if cfg.use_kelly_sizing else "fixed_lots",
        "requireHighIv": bool(cfg.require_high_iv),
        "expiryMonth": cfg.expiry_month,
        "wingSteps": int(cfg.wing_steps),
        "wingPct": float(cfg.wing_pct),
        "shortOtmPct": float(cfg.short_otm_pct),
        "minCreditToWidth": float(cfg.min_credit_to_width),
        "takeProfitPct": float(cfg.take_profit_pct),
        "stopLossPct": float(cfg.stop_loss_pct),
        "exitOnShortBreach": bool(cfg.exit_on_short_breach),
        "maxAbsTrendPct": float(cfg.max_abs_trend_pct),
        "config": asdict(cfg),
    }
    return IronCondorBacktestResult(
        summary=summary,
        equity_curve=equity_curve,
        trades=trades,
        daily=daily,
    )
