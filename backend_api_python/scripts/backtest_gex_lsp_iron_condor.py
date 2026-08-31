#!/usr/bin/env python3
"""Run GEX+LSP+Kelly iron-condor backtest on exported ETF options CSVs.

Iron condor = short strangle near GEX walls + long further-OTM wings (defined risk).
Kelly sizes on wing-minus-credit margin; LSP skews short call/put lots (wings match).

Example:
  PYTHONPATH=backend_api_python python backend_api_python/scripts/backtest_gex_lsp_iron_condor.py \\
    --data-dir tmp/gex_lsp_strangle --underlying 510050
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from app.services.gex_lsp_strangle import (
    IronCondorBacktestConfig,
    run_iron_condor_backtest,
)


def _load_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(path)
    return pd.read_csv(path)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=Path("tmp/gex_lsp_strangle"))
    parser.add_argument("--underlying", default="510050")
    parser.add_argument("--capital", type=float, default=1_000_000.0)
    parser.add_argument("--lots", type=int, default=1, help="Fixed lots when --no-kelly")
    parser.add_argument("--wing-steps", type=int, default=1, help="Listed strikes beyond short for long wings")
    parser.add_argument("--wing-pct", type=float, default=0.0, help="Min wing width as fraction of spot")
    parser.add_argument("--take-profit", type=float, default=0.50)
    parser.add_argument("--stop-loss", type=float, default=0.90)
    parser.add_argument("--no-kelly", action="store_true", help="Disable Kelly sizing")
    parser.add_argument("--no-iv-filter", action="store_true", help="Allow entries regardless of IV rank")
    parser.add_argument("--iv-rank-min", type=float, default=0.60)
    parser.add_argument("--kelly-max-fraction", type=float, default=0.25)
    parser.add_argument("--kelly-max-lots", type=int, default=10)
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args()

    data_dir = args.data_dir
    und = _load_csv(data_dir / f"underlying_{args.underlying}.csv")
    chain = _load_csv(data_dir / f"chain_{args.underlying}.csv")
    oi = _load_csv(data_dir / f"oi_{args.underlying}.csv")

    und["trade_date"] = pd.to_datetime(und["trade_date"])
    chain["trade_date"] = pd.to_datetime(chain["trade_date"])
    oi["trade_date"] = pd.to_datetime(oi["trade_date"])
    start = max(chain["trade_date"].min(), oi["trade_date"].min())
    und = und[und["trade_date"] >= start]
    chain = chain[chain["trade_date"] >= start]
    oi = oi[oi["trade_date"] >= start]

    cfg = IronCondorBacktestConfig(
        underlying_code=str(args.underlying),
        initial_capital=float(args.capital),
        lots=int(args.lots),
        wing_steps=int(args.wing_steps),
        wing_pct=float(args.wing_pct),
        take_profit_pct=float(args.take_profit),
        stop_loss_pct=float(args.stop_loss),
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
        f"- Sharpe: {summary['sharpe']:.3f}",
        f"- Max drawdown: {summary['maxDrawdown']*100:.2f}%",
        f"- Trades: {summary['trades']} (win rate {summary['winRate']*100:.1f}%)",
        f"- Avg trade PnL: {summary['avgTradePnl']:,.2f}",
        f"- Sizing: {summary.get('sizingMode')}",
        f"- High-IV filter: {summary.get('requireHighIv')}",
        f"- Wing steps: {summary.get('wingSteps')} | take-profit={summary.get('takeProfitPct')} | stop-loss={summary.get('stopLossPct')}",
        "",
        "## Rules",
        "",
        "1. **GEX walls**: short call/put near walls; buy further-OTM wings (`wing_steps`).",
        "2. **Defined risk**: max loss ≈ (max wing − net credit) × multiplier × lots.",
        "3. **High IV**: enter only when ATM IV rank ≥ threshold (rolls may skip).",
        "4. **Kelly**: `f*=2p−1` on defined-risk margin; clamp fraction/lots.",
        "5. **LSP**: skew short call/put lots; long wings match short lots per side; no spot hedge.",
        "6. **Exits**: short-strike breach, wall breach, roll DTE, max hold, take-profit, stop-loss.",
        "",
        "## Trades",
        "",
    ]
    for trade in payload["trades"]:
        lines.append(
            f"- {trade['entryDate']} → {trade['exitDate']} | "
            f"K={trade['longPutStrike']}/{trade['shortPutStrike']}/"
            f"{trade['shortCallStrike']}/{trade['longCallStrike']} | "
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
