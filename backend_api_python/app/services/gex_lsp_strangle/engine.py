"""Daily short-strangle backtest driven by LSP regime + GEX walls."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

import numpy as np
import pandas as pd

from app.services.gex_lsp_strangle.gex_walls import compute_gex_walls, select_strangle_strikes
from app.services.gex_lsp_strangle.lsp import compute_lsp_features


@dataclass
class ShortStrangleBacktestConfig:
    underlying_code: str = "510050"
    initial_capital: float = 1_000_000.0
    lots: int = 1
    multiplier: float = 10000.0
    commission_per_lot: float = 5.0
    slippage_pct: float = 0.02
    hedge_band_delta: float = 0.15
    min_dte: int = 7
    max_dte: int = 45
    min_width_pct: float = 0.03
    max_hold_days: int = 15
    exit_dte: int = 5
    lsp_days_1: int = 5
    lsp_days_2: int = 10
    lsp_neutral_band: float = 8.0
    require_inside_walls: bool = True
    wall_buffer_pct: float = 0.005


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
    lots: int
    entry_spot: float
    hedge_shares: float = 0.0
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


def run_short_strangle_backtest(
    underlying: pd.DataFrame,
    chain: pd.DataFrame,
    oi: pd.DataFrame,
    *,
    config: ShortStrangleBacktestConfig | None = None,
) -> ShortStrangleBacktestResult:
    """Run a daily short wide-strangle backtest with dynamic delta hedging."""
    cfg = config or ShortStrangleBacktestConfig()
    und, panel = prepare_panel(underlying, chain, oi, config=cfg)

    cash = float(cfg.initial_capital)
    equity_curve: list[dict[str, Any]] = []
    trades: list[dict[str, Any]] = []
    daily: list[dict[str, Any]] = []
    open_trade: _OpenTrade | None = None

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
        lsp_ok = bool(row.get("lsp_ok_for_short_vol"))
        regime = str(row.get("lsp_regime") or "mixed")

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

            target_hedge = open_trade.lots * cfg.multiplier * (call_delta + put_delta)
            band_shares = cfg.hedge_band_delta * open_trade.lots * cfg.multiplier
            if abs(target_hedge - open_trade.hedge_shares) > band_shares:
                delta_shares = target_hedge - open_trade.hedge_shares
                if abs(delta_shares) >= 100:
                    cash -= delta_shares * spot
                    cash -= abs(delta_shares) / 100.0 * cfg.commission_per_lot
                    open_trade.hedge_shares = target_hedge
                    open_trade.call_delta = call_delta
                    open_trade.put_delta = put_delta

            exit_reason = None
            dte = (pd.Timestamp(open_trade.expire_date) - dt).days
            if dte <= cfg.exit_dte:
                exit_reason = "exit_dte"
            elif open_trade.days_held >= cfg.max_hold_days:
                exit_reason = "max_hold"
            elif spot >= open_trade.call_wall * (1.0 + cfg.wall_buffer_pct):
                exit_reason = "call_wall_breach"
            elif spot <= open_trade.put_wall * (1.0 - cfg.wall_buffer_pct):
                exit_reason = "put_wall_breach"
            elif regime in {"bullish", "bearish"} and not lsp_ok:
                exit_reason = "lsp_directional"

            if exit_reason:
                cover_call = _premium_slip(call_px, "buy", cfg.slippage_pct)
                cover_put = _premium_slip(put_px, "buy", cfg.slippage_pct)
                cash -= (cover_call + cover_put) * open_trade.lots * cfg.multiplier
                cash -= 2 * _fee(open_trade.lots, cfg.commission_per_lot)
                cash += open_trade.hedge_shares * spot
                cash -= abs(open_trade.hedge_shares) / 100.0 * cfg.commission_per_lot
                entry_credit = (open_trade.call_entry + open_trade.put_entry) * open_trade.lots * cfg.multiplier
                exit_debit = (cover_call + cover_put) * open_trade.lots * cfg.multiplier
                trade_pnl = (
                    (entry_credit - exit_debit)
                    + open_trade.hedge_shares * (spot - open_trade.entry_spot)
                    - 4 * _fee(open_trade.lots, cfg.commission_per_lot)
                )
                trades.append(
                    {
                        "entryDate": str(open_trade.entry_date.date()),
                        "exitDate": str(dt.date()),
                        "reason": exit_reason,
                        "callStrike": open_trade.call_strike,
                        "putStrike": open_trade.put_strike,
                        "callCode": open_trade.call_code,
                        "putCode": open_trade.put_code,
                        "entryCredit": round(entry_credit, 2),
                        "exitDebit": round(exit_debit, 2),
                        "pnl": round(trade_pnl, 2),
                        "daysHeld": open_trade.days_held,
                        "callWall": open_trade.call_wall,
                        "putWall": open_trade.put_wall,
                        "lspRegimeEntry": open_trade.lsp_regime_entry,
                    }
                )
                open_trade = None

        if open_trade is None and pick is not None and lsp_ok:
            call_wall = float(pick["call_wall"])
            put_wall = float(pick["put_wall"])
            inside = (spot <= call_wall * (1.0 - cfg.wall_buffer_pct)) and (
                spot >= put_wall * (1.0 + cfg.wall_buffer_pct)
            )
            call_px = pick.get("call_close")
            put_px = pick.get("put_close")
            if (
                ((not cfg.require_inside_walls) or inside)
                and call_px
                and put_px
                and float(call_px) > 0
                and float(put_px) > 0
                and pick.get("call_code")
                and pick.get("put_code")
            ):
                call_fill = _premium_slip(float(call_px), "sell", cfg.slippage_pct)
                put_fill = _premium_slip(float(put_px), "sell", cfg.slippage_pct)
                cash += (call_fill + put_fill) * cfg.lots * cfg.multiplier
                cash -= 2 * _fee(cfg.lots, cfg.commission_per_lot)
                call_delta = float(pick.get("call_delta") or 0.25)
                put_delta = float(pick.get("put_delta") or -0.25)
                hedge = cfg.lots * cfg.multiplier * (call_delta + put_delta)
                if abs(hedge) >= 100:
                    cash -= hedge * spot
                    cash -= abs(hedge) / 100.0 * cfg.commission_per_lot
                else:
                    hedge = 0.0
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
                    lots=cfg.lots,
                    entry_spot=spot,
                    hedge_shares=hedge,
                    days_held=0,
                    lsp_regime_entry=regime,
                )

        liability = 0.0
        hedge_mv = 0.0
        if open_trade is not None:
            call_px = _option_px(day_chain, open_trade.call_code, open_trade.call_strike, "C")
            put_px = _option_px(day_chain, open_trade.put_code, open_trade.put_strike, "P")
            liability = -(call_px + put_px) * open_trade.lots * cfg.multiplier
            hedge_mv = open_trade.hedge_shares * spot
        equity = cash + liability + hedge_mv
        equity_curve.append({"date": str(dt.date()), "equity": round(float(equity), 2)})
        daily.append(
            {
                "date": str(dt.date()),
                "spot": spot,
                "lspRegime": regime,
                "lspOk": lsp_ok,
                "callWall": walls.get("call_wall"),
                "putWall": walls.get("put_wall"),
                "pin": walls.get("pin"),
                "flip": walls.get("flip"),
                "inPosition": open_trade is not None,
                "equity": round(float(equity), 2),
            }
        )

    if open_trade is not None and dates:
        dt = dates[-1]
        spot = float(und.loc[dt, "close"])
        day_chain = panel[panel["trade_date"] == dt]
        call_px = _option_px(day_chain, open_trade.call_code, open_trade.call_strike, "C")
        put_px = _option_px(day_chain, open_trade.put_code, open_trade.put_strike, "P")
        cover_call = _premium_slip(call_px, "buy", cfg.slippage_pct)
        cover_put = _premium_slip(put_px, "buy", cfg.slippage_pct)
        cash -= (cover_call + cover_put) * open_trade.lots * cfg.multiplier
        cash -= 2 * _fee(open_trade.lots, cfg.commission_per_lot)
        cash += open_trade.hedge_shares * spot
        entry_credit = (open_trade.call_entry + open_trade.put_entry) * open_trade.lots * cfg.multiplier
        exit_debit = (cover_call + cover_put) * open_trade.lots * cfg.multiplier
        trade_pnl = (
            (entry_credit - exit_debit)
            + open_trade.hedge_shares * (spot - open_trade.entry_spot)
            - 4 * _fee(open_trade.lots, cfg.commission_per_lot)
        )
        trades.append(
            {
                "entryDate": str(open_trade.entry_date.date()),
                "exitDate": str(dt.date()),
                "reason": "eod_force_close",
                "callStrike": open_trade.call_strike,
                "putStrike": open_trade.put_strike,
                "callCode": open_trade.call_code,
                "putCode": open_trade.put_code,
                "entryCredit": round(entry_credit, 2),
                "exitDebit": round(exit_debit, 2),
                "pnl": round(trade_pnl, 2),
                "daysHeld": open_trade.days_held,
                "callWall": open_trade.call_wall,
                "putWall": open_trade.put_wall,
                "lspRegimeEntry": open_trade.lsp_regime_entry,
            }
        )
        if equity_curve and equity_curve[-1]["date"] == str(dt.date()):
            equity_curve[-1]["equity"] = round(float(cash), 2)
        else:
            equity_curve.append({"date": str(dt.date()), "equity": round(float(cash), 2)})

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
        "config": asdict(cfg),
    }
    return ShortStrangleBacktestResult(
        summary=summary,
        equity_curve=equity_curve,
        trades=trades,
        daily=daily,
    )
