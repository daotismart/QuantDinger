#!/usr/bin/env python3
"""Run GEX-TV listed-chain iron-condor backtest on exported ETF options CSVs.

Rules (ScriptTrader GEX-TV): ~45 DTE, 14–25Δ shorts outside GEX walls,
3-step wings, net credit ≥ 25% of wing, size by 6% NAV max-loss, TP at 75%
of credit captured, roll at 21 DTE. Legs always come from the then-listed book.

Example:
  PYTHONPATH=backend_api_python python backend_api_python/scripts/backtest_gex_lsp_iron_condor.py \\
    --from-csv --data-dir tmp/gex_lsp_strangle --underlying 510050 \\
    --start 2026-03-27 --end 2026-08-31
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from app.services.gex_lsp_strangle import (
    IronCondorBacktestConfig,
    run_iron_condor_backtest,
)
from app.services.gex_lsp_strangle.chain_store import load_listed_option_panel


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=Path("tmp/gex_lsp_strangle"))
    parser.add_argument("--underlying", default="510050")
    parser.add_argument("--start", default=None, help="Inclusive YYYY-MM-DD; default = first listed chain day")
    parser.add_argument("--end", default=None, help="Inclusive YYYY-MM-DD; default = last listed chain day")
    parser.add_argument("--from-csv", action="store_true", help="Skip ClickHouse and load GEX_LSP_DATA_DIR CSVs")
    parser.add_argument("--capital", type=float, default=1_000_000.0)
    parser.add_argument("--lots", type=int, default=80, help="Lots cap before risk_cap / Kelly")
    parser.add_argument("--wing-steps", type=int, default=3, help="Exchange steps beyond short for long wings")
    parser.add_argument("--wing-pct", type=float, default=0.0, help="Min wing width as fraction of spot")
    parser.add_argument("--short-otm-pct", type=float, default=0.0, help="Legacy: short that percent OTM; 0=GEX-TV")
    parser.add_argument("--min-credit-to-width", type=float, default=0.20, help="Skip entries with thin credit/wing")
    parser.add_argument("--min-short-delta", type=float, default=0.14)
    parser.add_argument("--max-short-delta", type=float, default=0.25)
    parser.add_argument("--target-dte", type=int, default=45)
    parser.add_argument("--risk-cap", type=float, default=0.06, help="Max loss / NAV per condor")
    parser.add_argument("--take-profit", type=float, default=0.75, help="Fraction of credit to capture")
    parser.add_argument("--stop-loss", type=float, default=0.90)
    parser.add_argument("--hold-through-short", action="store_true", help="Do not flatten when spot hits short strikes")
    parser.add_argument("--kelly", action="store_true", help="Enable Kelly cap (default on)")
    parser.add_argument("--no-kelly", action="store_true", help="Disable Kelly; still apply risk_cap")
    parser.add_argument("--require-high-iv", action="store_true", help="Only enter when IV rank is high (default on)")
    parser.add_argument("--no-iv-filter", action="store_true", help="Disable the IV-rank gate")
    parser.add_argument("--iv-rank-min", type=float, default=0.40)
    parser.add_argument("--kelly-max-fraction", type=float, default=0.10)
    parser.add_argument("--kelly-max-lots", type=int, default=80)
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args()

    data_dir = args.data_dir
    if args.from_csv:
        os.environ["ETF_OPTIONS_CH_ENABLED"] = "0"
        os.environ["GEX_LSP_DATA_DIR"] = str(data_dir.resolve())
    und, chain, oi = load_listed_option_panel(
        args.underlying,
        start=args.start,
        end=args.end,
        data_dir=data_dir,
    )

    cfg = IronCondorBacktestConfig(
        underlying_code=str(args.underlying),
        initial_capital=float(args.capital),
        lots=int(args.lots),
        wing_steps=int(args.wing_steps),
        wing_pct=float(args.wing_pct),
        short_otm_pct=float(args.short_otm_pct),
        min_credit_to_width=float(args.min_credit_to_width),
        min_short_delta=float(args.min_short_delta),
        max_short_delta=float(args.max_short_delta),
        target_dte=int(args.target_dte),
        risk_cap=float(args.risk_cap),
        take_profit_pct=float(args.take_profit),
        stop_loss_pct=float(args.stop_loss),
        exit_on_short_breach=not bool(args.hold_through_short),
        use_kelly_sizing=not bool(args.no_kelly),
        require_high_iv=not bool(args.no_iv_filter),
        iv_rank_min=float(args.iv_rank_min),
        kelly_max_fraction=float(args.kelly_max_fraction),
        kelly_max_lots=int(args.kelly_max_lots),
    )
    result = run_iron_condor_backtest(und, chain, oi, config=cfg)
    payload = result.to_dict()

    out = args.out or Path("docs/reports") / f"GEX_LSP_IRON_CONDOR_{args.underlying}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    summary = payload["summary"]
    md = Path("docs/reports") / f"GEX_LSP_IRON_CONDOR_{args.underlying}.md"
    lines = [
        f"# GEX + LSP + Kelly Iron Condor Backtest ({args.underlying})",
        "",
        "## Summary",
        "",
        f"- Initial capital: {summary['initialCapital']:,.0f}",
        f"- Final equity: {summary['finalEquity']:,.2f}",
        f"- Total return: {summary['totalReturn']*100:.2f}%",
        f"- Annualized return: {summary.get('annualizedReturn', 0)*100:.2f}% ({summary.get('tradingDays', 0)} trading days)",
        f"- Sharpe: {summary['sharpe']:.3f}",
        f"- Max drawdown: {summary['maxDrawdown']*100:.2f}%",
        f"- Trades: {summary['trades']} (win rate {summary['winRate']*100:.1f}%)",
        f"- Avg trade PnL: {summary['avgTradePnl']:,.2f}",
        f"- Sizing: {summary.get('sizingMode')}",
        f"- High-IV filter: {summary.get('requireHighIv')}",
        f"- Short Δ band: {summary.get('minShortDelta')}–{summary.get('maxShortDelta')} | min credit/width={summary.get('minCreditToWidth')}",
        f"- Wing steps: {summary.get('wingSteps')} | target DTE={summary.get('targetDte')} | risk cap={summary.get('riskCap')}",
        f"- Take-profit={summary.get('takeProfitPct')} (credit captured) | stop-loss={summary.get('stopLossPct')}",
        f"- Trend filter: |20d return| > {summary.get('maxAbsTrendPct', 0)*100:.0f}% sits out",
        f"- Listed chain: {str(chain['trade_date'].min())[:10]} → {str(chain['trade_date'].max())[:10]} "
        f"({int(chain['trade_date'].nunique())} sessions, {chain['contract_code'].nunique()} contracts)",
        "- Legs: each entry picks then-listed strikes via GEX-TV (no hardcoded codes)",
        "",
        "## Rules",
        "",
        "1. **GEX-TV pick**: 14–25Δ shorts **outside** GEX walls; prefer 3-step listed wings (min 2); credit/width ≥ 20%.",
        "2. **Defined risk**: max loss ≈ (max wing − net credit) × multiplier × lots.",
        "3. **Sizing**: min(lots, max_lots, 6% NAV / max_loss, Kelly cap 10%).",
        "4. **IV Rank ≥ 40** (0–1 = 0.40) to sell; skip adjusted *A strikes and missing quotes.",
        "5. **~45 DTE** entry (28–65), roll at 21 DTE; take-profit at 75% of credit captured.",
        "6. **Exits**: short-strike / wall breach, TP, stop-loss, DTE roll, max hold. Missing leg quote → do not flatten.",
        "",
        "## Trades",
        "",
    ]
    for trade in payload["trades"]:
        lines.append(
            f"- {trade['entryDate']} → {trade['exitDate']} | "
            f"K={trade['longPutStrike']}/{trade['shortPutStrike']}/"
            f"{trade['shortCallStrike']}/{trade['longCallStrike']} | "
            f"{trade.get('shortPutCode')}/{trade.get('shortCallCode')} | "
            f"lots={trade.get('putLots')}/{trade.get('callLots')} | "
            f"credit={trade.get('entryCredit')} | "
            f"PnL={trade['pnl']:,.2f} | {trade['reason']}"
        )
    md.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print(f"wrote {out}")
    print(f"wrote {md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
