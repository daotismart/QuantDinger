#!/usr/bin/env python3
"""Research backtest for docs/examples/strategy_v2_lsp_inventory_periodic.py."""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.services.strategy_v2 import StrategyV2BacktestRunner

EXAMPLE = REPO / "docs" / "examples" / "strategy_v2_lsp_inventory_periodic.py"
DEFAULT_SYMBOL = "USStock:SPY"


def _synthetic_ohlcv(periods: int, seed: int, freq: str) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    index = pd.date_range("2024-01-02 09:30", periods=periods, freq=freq)
    wave = np.sin(np.linspace(0, 10 * math.pi, periods)) * 0.0018
    rets = rng.normal(0.00015, 0.0038, size=periods) + wave
    close = 100.0 * np.cumprod(1.0 + rets)
    open_ = np.concatenate([[close[0]], close[:-1]])
    high = np.maximum(open_, close) * (1.0 + rng.uniform(0.0, 0.0025, periods))
    low = np.minimum(open_, close) * (1.0 - rng.uniform(0.0, 0.0025, periods))
    volume = rng.integers(700_000, 4_000_000, size=periods).astype(float)
    return pd.DataFrame(
        {
            "open": open_,
            "high": high,
            "low": low,
            "close": close,
            "volume": volume,
        },
        index=index,
    )


def _load_csv(path: Path) -> pd.DataFrame:
    frame = pd.read_csv(path)
    lower = {str(col).strip().lower(): col for col in frame.columns}

    def col(*names: str) -> str:
        for name in names:
            if name in lower:
                return lower[name]
        raise KeyError(f"missing columns {names} in {path}")

    ts_col = col("datetime", "timestamp", "date", "time", "ts")
    index = pd.to_datetime(frame[ts_col], errors="coerce")
    out = pd.DataFrame(
        {
            "open": pd.to_numeric(frame[col("open", "o")], errors="coerce"),
            "high": pd.to_numeric(frame[col("high", "h")], errors="coerce"),
            "low": pd.to_numeric(frame[col("low", "l")], errors="coerce"),
            "close": pd.to_numeric(frame[col("close", "c", "last")], errors="coerce"),
            "volume": pd.to_numeric(frame[col("volume", "vol", "v")], errors="coerce"),
        },
        index=index,
    )
    out = out.dropna().sort_index()
    if out.empty:
        raise ValueError(f"no usable OHLCV rows in {path}")
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--csv", type=Path, default=None, help="OHLCV CSV (optional)")
    parser.add_argument("--symbol", default=DEFAULT_SYMBOL)
    parser.add_argument("--periods", type=int, default=800)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--freq", default="h")
    parser.add_argument("--capital", type=float, default=100000.0)
    parser.add_argument("--fill-mode", choices=("take", "make"), default="take")
    parser.add_argument("--rebalance-every", type=int, default=4)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    code = EXAMPLE.read_text(encoding="utf-8")
    if args.symbol != DEFAULT_SYMBOL:
        code = code.replace(f'SYMBOL = "{DEFAULT_SYMBOL}"', f'SYMBOL = "{args.symbol}"')

    frame = _load_csv(args.csv) if args.csv else _synthetic_ohlcv(args.periods, args.seed, args.freq)

    result = StrategyV2BacktestRunner(
        code=code,
        frames={args.symbol: frame},
        initial_capital=args.capital,
        commission=0.0005,
        slippage=0.0005,
        params={
            "fill_mode": args.fill_mode,
            "rebalance_every": args.rebalance_every,
            "days_1": 5,
            "days_2": 10,
            "long_only": True,
            "max_position_pct": 0.9,
            "deadband_pct": 0.03,
            "book_spread_bps": 4.0,
        },
    ).run()

    summary = {
        "symbol": args.symbol,
        "bars": int(len(frame)),
        "fillMode": args.fill_mode,
        "rebalanceEvery": args.rebalance_every,
        "initialCapital": float(args.capital),
        "finalEquity": float(result.get("finalEquity") or 0.0),
        "totalReturnPct": float(result.get("totalReturn") or 0.0),
        "maxDrawdownPct": float(result.get("maxDrawdown") or 0.0),
        "annualizedReturnPct": float(result.get("annualizedReturn") or 0.0),
        "executions": int(len(result.get("executions") or [])),
        "closedTrades": int(
            len(result["closedTrades"])
            if isinstance(result.get("closedTrades"), list)
            else (result.get("closedTrades") or 0)
        ),
        "engine": (result.get("engine") or {}).get("version"),
    }

    if args.json:
        print(json.dumps(summary, ensure_ascii=False, indent=2))
    else:
        print("LSP inventory periodic book backtest")
        for key, value in summary.items():
            print(f"  {key}: {value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
