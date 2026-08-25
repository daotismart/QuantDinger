"""Compile + backtest the LSP inventory periodic book strategy."""

from __future__ import annotations

import math
from pathlib import Path

import numpy as np
import pandas as pd

from app.services.strategy_v2 import StrategyV2BacktestRunner, compile_strategy_v2
from app.utils.safe_exec import validate_code_safety


EXAMPLE = (
    Path(__file__).resolve().parents[2]
    / "docs"
    / "examples"
    / "strategy_v2_lsp_inventory_periodic.py"
)
SYMBOL = "USStock:SPY"


def _load_code() -> str:
    return EXAMPLE.read_text(encoding="utf-8")


def _synthetic_frame(periods: int = 500, seed: int = 7) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    index = pd.date_range("2024-01-02 09:30", periods=periods, freq="h")
    noise = rng.normal(0.0, 0.0035, size=periods)
    shock = np.sin(np.linspace(0, 12 * math.pi, periods)) * 0.0015
    rets = noise + shock
    close = 100.0 * np.cumprod(1.0 + rets)
    open_ = np.concatenate([[close[0]], close[:-1]])
    high = np.maximum(open_, close) * (1.0 + rng.uniform(0.0005, 0.0025, periods))
    low = np.minimum(open_, close) * (1.0 - rng.uniform(0.0005, 0.0025, periods))
    volume = rng.integers(800_000, 3_000_000, size=periods).astype(float)
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


def test_example_file_is_sandbox_safe_and_compiles():
    assert EXAMPLE.is_file()
    code = _load_code()
    ok, err = validate_code_safety(code)
    assert ok is True, err
    compiled = compile_strategy_v2(code)
    meta = compiled.manifest.metadata()
    assert "initialize" in meta["handlers"]
    assert "handle_data" in meta["handlers"]
    assert meta["primaryFrequency"] == "1h"
    instruments = meta["universe"]["instruments"]
    ids = {
        str(item.get("instrument_id") or item.get("symbol") or "")
        for item in instruments
    }
    assert SYMBOL in ids


def test_lsp_inventory_score_is_bounded():
    ns = compile_strategy_v2(_load_code()).namespace
    frame = _synthetic_frame(240, seed=3)
    features = ns["compute_lsp_inventory_features"](
        opens=frame["open"],
        highs=frame["high"],
        lows=frame["low"],
        closes=frame["close"],
        volumes=frame["volume"],
        days_1=5,
        days_2=10,
    )
    assert features is not None
    assert -1.0 <= float(features["inventory_score"]) <= 1.0
    assert math.isfinite(float(features["lsp_bb"]))
    assert math.isfinite(float(features["lsp_bb2"]))


def test_take_mode_backtest_runs_and_trades():
    result = StrategyV2BacktestRunner(
        code=_load_code(),
        frames={SYMBOL: _synthetic_frame()},
        initial_capital=100_000,
        commission=0.0005,
        slippage=0.0005,
        params={
            "rebalance_every": 4,
            "days_1": 5,
            "days_2": 10,
            "fill_mode": "take",
            "long_only": True,
            "max_position_pct": 0.9,
            "deadband_pct": 0.02,
        },
    ).run()

    assert result["engine"]["version"] == "quantdinger-strategy-api-v2"
    assert result["finalEquity"] > 0
    assert len(result["equityCurve"]) >= 100
    assert len(result.get("executions") or []) >= 1


def test_make_mode_backtest_completes():
    result = StrategyV2BacktestRunner(
        code=_load_code(),
        frames={SYMBOL: _synthetic_frame(360, seed=11)},
        initial_capital=100_000,
        commission=0.0005,
        slippage=0.0,
        params={
            "rebalance_every": 3,
            "fill_mode": "make",
            "book_spread_bps": 5.0,
            "deadband_pct": 0.01,
            "long_only": True,
        },
    ).run()
    assert result["finalEquity"] > 0
    assert len(result["equityCurve"]) >= 100
