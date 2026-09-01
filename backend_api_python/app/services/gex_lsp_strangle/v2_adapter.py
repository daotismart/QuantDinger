"""Adapt listed-chain iron-condor research results to Strategy API V2 payloads."""

from __future__ import annotations

import hashlib
from datetime import datetime
from typing import Any, Mapping

from app.services.gex_lsp_strangle.chain_store import load_listed_option_panel
from app.services.gex_lsp_strangle.iron_condor_engine import (
    IronCondorBacktestConfig,
    IronCondorBacktestResult,
    run_iron_condor_backtest,
)

ENGINE_VERSION = "gex-lsp-iron-condor-research"


def iron_condor_family_name(value: object) -> bool:
    raw = str(value or "").strip().lower().replace("-", "_")
    return "iron_condor" in raw or raw.endswith("ironcondor")


def config_from_params(
    params: Mapping[str, Any] | None,
    *,
    underlying: str,
    initial_capital: float,
) -> IronCondorBacktestConfig:
    raw = dict(params or {})

    def _f(name: str, default: float) -> float:
        try:
            return float(raw.get(name, default) if raw.get(name, default) is not None else default)
        except Exception:
            return float(default)

    def _i(name: str, default: int) -> int:
        try:
            return int(raw.get(name, default) if raw.get(name, default) is not None else default)
        except Exception:
            return int(default)

    def _b(name: str, default: bool) -> bool:
        value = raw.get(name, default)
        if isinstance(value, bool):
            return value
        return str(value or "").strip().lower() in {"1", "true", "yes", "on"}

    use_kelly = _b("kelly", True) if "kelly" in raw or "use_kelly_sizing" in raw else _b("use_kelly_sizing", True)
    return IronCondorBacktestConfig(
        underlying_code=str(underlying or "510050"),
        initial_capital=float(initial_capital),
        lots=max(_i("lots", 80), 1),
        wing_steps=max(_i("wing_steps", 3), 1),
        wing_pct=max(_f("wing_pct", 0.0), 0.0),
        take_profit_pct=max(_f("take_profit_pct", 0.75), 0.0),
        stop_loss_pct=max(_f("stop_loss_pct", 0.90), 0.0),
        min_credit_to_width=max(_f("min_credit_to_width", 0.15), 0.0),
        min_short_delta=max(_f("min_short_delta", 0.14), 0.0),
        max_short_delta=max(_f("max_short_delta", 0.25), 0.0),
        target_dte=max(_i("target_dte", 45), 0),
        min_dte=max(_i("min_dte", 28), 1),
        max_dte=max(_i("max_dte", 65), 1),
        roll_before_dte=max(_i("roll_before_dte", 10), 1),
        exit_dte=max(_i("exit_dte", 10), 1),
        risk_cap=max(_f("risk_cap", 0.06), 0.0),
        use_kelly_sizing=use_kelly,
        require_high_iv=_b("require_high_iv", False),
        require_inside_walls=_b("require_inside_walls", False),
        exit_on_wall_breach=_b("exit_on_wall_breach", False),
        exit_on_short_breach=_b("exit_on_short_breach", True),
        iv_rank_min=_f("iv_rank_min", 0.40),
        kelly_max_fraction=_f("kelly_max_fraction", 0.10),
        kelly_max_lots=max(_i("kelly_max_lots", 80), 1),
        lsp_max_skew_lots=max(_i("max_skew_lots", 0), 0),
        max_hold_days=max(_i("max_hold_bars", 60), 1),
        expiry_month=str(raw.get("expiry_month") or "target"),
        exclude_adjusted=_b("exclude_adjusted", True),
    )


def research_to_v2_result(payload: Mapping[str, Any], *, code: str) -> dict[str, Any]:
    summary = dict(payload.get("summary") or {})
    initial = float(summary.get("initialCapital") or 1_000_000)
    final = float(summary.get("finalEquity") or initial)
    trades = list(payload.get("trades") or [])
    curve_in = list(payload.get("equityCurve") or [])
    equity_curve = []
    peak = initial
    for point in curve_in:
        value = float(point.get("equity") or point.get("value") or initial)
        peak = max(peak, value)
        dd = value / peak - 1.0 if peak > 0 else 0.0
        day = point.get("date") or point.get("time") or ""
        stamp = str(day)
        if "T" not in stamp:
            stamp = f"{stamp}T16:00:00Z"
        equity_curve.append(
            {
                "time": stamp,
                "value": value,
                "cash": value,
                "grossExposure": 0.0,
                "netExposure": 0.0,
                "drawdown": dd,
            }
        )
    closed = []
    balance = initial
    for trade in trades:
        pnl = float(trade.get("pnl") or 0.0)
        balance += pnl
        closed.append(
            {
                "symbol": (
                    f"CNIndexOptions:{trade.get('shortCallCode') or trade.get('shortCallStrike')}"
                ),
                "side": "short",
                "entry_time": f"{trade.get('entryDate')}T16:00:00Z",
                "exit_time": f"{trade.get('exitDate')}T16:00:00Z",
                "entry_price": float(trade.get("entryCredit") or 0.0),
                "exit_price": float(trade.get("exitDebit") or 0.0),
                "quantity": float(max(trade.get("callLots") or 0, trade.get("putLots") or 0, 1)),
                "amount": float(max(trade.get("callLots") or 0, trade.get("putLots") or 0, 1)),
                "profit": pnl,
                "gross_profit": pnl,
                "commission": float(trade.get("fees") or 0.0),
                "balance": balance,
                "close_reason": str(trade.get("reason") or ""),
                "structure": "iron_condor",
                "shortCallStrike": trade.get("shortCallStrike"),
                "shortPutStrike": trade.get("shortPutStrike"),
                "longCallStrike": trade.get("longCallStrike"),
                "longPutStrike": trade.get("longPutStrike"),
                "shortCallCode": trade.get("shortCallCode"),
                "shortPutCode": trade.get("shortPutCode"),
                "longCallCode": trade.get("longCallCode"),
                "longPutCode": trade.get("longPutCode"),
                "expireDate": trade.get("expireDate"),
            }
        )
    wins = [item for item in closed if float(item.get("profit") or 0) > 0]
    losses = [item for item in closed if float(item.get("profit") or 0) < 0]
    total_return_pct = float(summary.get("totalReturn") or 0.0) * 100.0
    annualized_pct = float(summary.get("annualizedReturn") or 0.0) * 100.0
    max_dd_pct = float(summary.get("maxDrawdown") or 0.0) * 100.0
    win_rate_pct = float(summary.get("winRate") or 0.0) * 100.0
    return {
        "engine": {"version": ENGINE_VERSION, "kind": "gex_lsp_iron_condor_research"},
        "initialCapital": initial,
        "finalEquity": final,
        "totalReturn": total_return_pct,
        "annualizedReturn": annualized_pct,
        "annualizedReturnAvailable": True,
        "annualizedVolatility": float(summary.get("annualizedVol") or 0.0) * 100.0,
        "sharpeRatio": float(summary.get("sharpe") or 0.0),
        "maxDrawdown": max_dd_pct,
        "winRate": win_rate_pct,
        "totalTrades": int(summary.get("trades") or len(closed)),
        "totalExecutions": int(summary.get("trades") or len(closed)),
        "winningTrades": len(wins),
        "losingTrades": len(losses),
        "avgTrade": float(summary.get("avgTradePnl") or 0.0),
        "totalProfit": float(sum(float(item.get("profit") or 0) for item in closed)),
        "resultStatus": "completed_trades" if closed else "no_trades",
        "dataProvenance": {"kind": "market", "source": "etf_options_listed_chain"},
        "equityCurve": equity_curve,
        "closedTrades": closed,
        "trades": closed,
        "rawTrades": closed,
        "executions": closed,
        "benchmark": {"symbol": f"CNStock:{summary.get('underlying') or '510050'}"},
        "executionAssumptions": {
            "engineVersion": ENGINE_VERSION,
            "fillRule": "listed_chain_daily_close",
            "initialCapital": initial,
            "startDate": str((curve_in[0] or {}).get("date") or "") if curve_in else "",
            "endDate": str((curve_in[-1] or {}).get("date") or "") if curve_in else "",
            "leverageEnabled": False,
            "leverage": 1.0,
            "commission": 5.0,
            "slippage": 0.02,
            "lots": int((summary.get("config") or {}).get("lots") or 80),
            "contractSelection": "listed_chain_gex_walls",
            "pickModel": "gex_tv_iron_condor",
        },
        "manifest": {
            "strategyType": "portfolio",
            "primaryFrequency": "1d",
            "markets": ["CNIndexOptions", "CNStock"],
        },
        "codeHash": hashlib.sha256(str(code or "").encode("utf-8")).hexdigest(),
        "researchSummary": summary,
        "diagnostics": {
            "sourceControlled": True,
            "contractSelection": "listed_chain_gex_walls",
            "pickModel": "gex_tv_iron_condor",
            "chainDays": int(summary.get("tradingDays") or len(equity_curve)),
        },
    }


def run_listed_chain_iron_condor(
    *,
    code: str,
    underlying: str,
    start_date: datetime,
    end_date: datetime,
    initial_capital: float,
    params: Mapping[str, Any] | None = None,
    loader=None,
) -> dict[str, Any]:
    load = loader or load_listed_option_panel
    und, chain, oi = load(underlying, start=start_date, end=end_date)
    if und is None or und.empty or chain is None or chain.empty:
        raise ValueError("strategyV2.noMarketData")
    cfg = config_from_params(params, underlying=underlying, initial_capital=initial_capital)
    result: IronCondorBacktestResult = run_iron_condor_backtest(und, chain, oi, config=cfg)
    payload = result.to_dict()
    return research_to_v2_result(payload, code=code)
