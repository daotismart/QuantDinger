#!/usr/bin/env python3
"""Run GEX+LSP delta-targeted short-strangle backtest on exported ETF options CSVs.

LSP sets net-delta direction/size; GEX walls set strikes; hedge with option skew + spot.

Example:
  PYTHONPATH=backend_api_python python backend_api_python/scripts/backtest_gex_lsp_short_strangle.py \\
    --data-dir tmp/gex_lsp_strangle --underlying 510050
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from app.services.gex_lsp_strangle import (
    ShortStrangleBacktestConfig,
    run_short_strangle_backtest,
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
    parser.add_argument("--lots", type=int, default=1)
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args()

    data_dir = args.data_dir
    und = _load_csv(data_dir / f"underlying_{args.underlying}.csv")
    chain = _load_csv(data_dir / f"chain_{args.underlying}.csv")
    oi = _load_csv(data_dir / f"oi_{args.underlying}.csv")

    # Keep backtest window where chain+OI overlap.
    und["trade_date"] = pd.to_datetime(und["trade_date"])
    chain["trade_date"] = pd.to_datetime(chain["trade_date"])
    oi["trade_date"] = pd.to_datetime(oi["trade_date"])
    start = max(chain["trade_date"].min(), oi["trade_date"].min())
    und = und[und["trade_date"] >= start]
    chain = chain[chain["trade_date"] >= start]
    oi = oi[oi["trade_date"] >= start]

    cfg = ShortStrangleBacktestConfig(
        underlying_code=str(args.underlying),
        initial_capital=float(args.capital),
        lots=int(args.lots),
    )
    result = run_short_strangle_backtest(und, chain, oi, config=cfg)
    payload = result.to_dict()

    out = args.out or Path("docs/reports") / f"GEX_LSP_SHORT_STRANGLE_{args.underlying}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    summary = payload["summary"]
    md = Path("docs/reports") / f"GEX_LSP_SHORT_STRANGLE_{args.underlying}.md"
    lines = [
        f"# GEX + LSP Short Strangle Backtest ({args.underlying})",
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
        "",
        "## Rules",
        "",
        "1. **LSP**: continuous `lsp_delta_score` sets portfolio net-delta direction and size.",
        "2. **GEX walls**: sell OTM call near call wall and OTM put near put wall.",
        "3. **Option skew**: bullish LSP → more short puts / fewer short calls (and vice versa).",
        "4. **Spot hedge**: residual delta (target − option book) rebalanced when outside band.",
        "5. **Exits**: DTE floor, max hold, wall breach, or flattened option book.",
        "",
        "## Recent trades",
        "",
    ]
    for trade in payload["trades"][-10:]:
        lines.append(
            f"- {trade['entryDate']} → {trade['exitDate']} | "
            f"K={trade['putStrike']}/{trade['callStrike']} | "
            f"lots={trade.get('putLots')}/{trade.get('callLots')} | "
            f"score={trade.get('lspScoreEntry')} | "
            f"PnL={trade['pnl']:,.2f} | {trade['reason']}"
        )
    md.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print(f"wrote {out}")
    print(f"wrote {md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
