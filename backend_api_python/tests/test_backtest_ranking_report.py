"""Unit tests for backtest ranking score helpers."""

from __future__ import annotations

import importlib.util
from pathlib import Path


def _load_builder():
    path = Path(__file__).resolve().parents[1] / "scripts" / "build_backtest_ranking_report.py"
    spec = importlib.util.spec_from_file_location("build_backtest_ranking_report", path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_normalize_return_percent_vs_ratio():
    mod = _load_builder()
    assert abs(mod._normalize_return(7.49) - 0.0749) < 1e-9
    assert abs(mod._normalize_return(0.0749) - 0.0749) < 1e-9
    assert abs(mod._normalize_return(-0.74) + 0.74) < 1e-9


def test_score_uses_final_equity_when_present():
    mod = _load_builder()
    row = mod._score_row(
        {
            "id": 1,
            "strategy_name": "[UNIFIED-20260820] Quality Growth Multi-Factor",
            "total_return": -0.74,  # ambiguous raw metric
            "initial_capital": 100000,
            "final_equity": 99257.32,
            "sharpe": 0.1,
            "max_drawdown": -12.32,
            "profit_factor": 1.0,
            "total_trades": 13,
            "win_rate": 53.85,
        }
    )
    assert row["strategy_name"] == "Quality Growth Multi-Factor"
    assert abs(row["total_return"] - ((99257.32 / 100000) - 1.0)) < 1e-9
    assert abs(row["win_rate"] - 0.5385) < 1e-4


def test_score_penalizes_zero_trades_and_outliers():
    mod = _load_builder()
    traded = mod._score_row(
        {
            "id": 1,
            "strategy_name": "Quality Growth Multi-Factor",
            "total_return": 7.49,
            "sharpe": 2.5,
            "max_drawdown": -7.4,
            "profit_factor": 16.0,
            "total_trades": 19,
        }
    )
    zero = mod._score_row(
        {
            "id": 2,
            "strategy_name": "Trend Following Pack · Variant 1",
            "total_return": 0.0,
            "sharpe": 0.0,
            "max_drawdown": 0.0,
            "profit_factor": 0.0,
            "total_trades": 0,
        }
    )
    outlier = mod._score_row(
        {
            "id": 3,
            "strategy_name": "AS Options Market Maker",
            "total_return": 2159.0,
            "sharpe": 46.0,
            "max_drawdown": -20.0,
            "profit_factor": 2000.0,
            "total_trades": 200,
        }
    )
    assert traded["flag"] == "ok"
    assert traded["family"] == "US Portfolio"
    assert zero["flag"] == "no_trades"
    assert zero["score"] < traded["score"]
    assert outlier["flag"] == "extreme_outlier"
    assert outlier["score"] < traded["score"]
