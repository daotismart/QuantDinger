"""Iron condor strategy: compile, synthetic backtest, and parameter sanity checks."""

from __future__ import annotations

import ast
from pathlib import Path

import numpy as np
import pandas as pd

from app.services.indicator_params import IndicatorParamsParser
from app.services.strategy_v2 import StrategyV2BacktestRunner, compile_strategy_v2
from app.utils.safe_exec import SAFE_IMPORT_MODULES, validate_code_safety

IC_PATH = Path(__file__).resolve().parents[2] / "docs" / "examples" / "strategy_v2_iron_condor.py"
UNDERLYING_KEY = "CNStock:510050.SH"
LEG_KEYS = (
    "CNIndexOptions:90000001",
    "CNIndexOptions:90000002",
    "CNIndexOptions:90000003",
    "CNIndexOptions:90000004",
)


def _load_code() -> str:
    return IC_PATH.read_text(encoding="utf-8")


def _compile():
    return compile_strategy_v2(_load_code())


def test_iron_condor_example_exists_and_is_safe():
    assert IC_PATH.is_file()
    code = _load_code()
    assert "Iron Condor" in code.splitlines()[0]
    assert 'direction_mode="both"' in code
    assert "PERSIST_RUNTIME_STATE = True" in code
    assert "context.params" not in code.split("def handle_data")[0]
    ok, err = validate_code_safety(code)
    assert ok is True, err


def test_iron_condor_imports_are_sandbox_safe():
    tree = ast.parse(_load_code())
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert alias.name.split(".")[0] in SAFE_IMPORT_MODULES
        elif isinstance(node, ast.ImportFrom) and node.module:
            assert node.module.split(".")[0] in SAFE_IMPORT_MODULES


def test_iron_condor_compiles_as_portfolio_both():
    manifest = _compile().manifest
    assert manifest.strategy_type == "portfolio"
    assert manifest.direction_mode == "both"
    assert manifest.primary_frequency == "1d"
    symbols = {item.key for item in manifest.universe.instruments}
    assert UNDERLYING_KEY in symbols
    for key in LEG_KEYS:
        assert key in symbols


def test_iron_condor_param_defaults_match_get_fallbacks():
    code = _load_code()
    declared = {item["name"]: item["default"] for item in IndicatorParamsParser.parse_params(code)}
    fallbacks = {}
    tree = ast.parse(code)
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if not (
            isinstance(func, ast.Attribute)
            and func.attr == "get"
            and isinstance(func.value, ast.Attribute)
            and func.value.attr == "params"
        ):
            continue
        if len(node.args) < 2 or not isinstance(node.args[0], ast.Constant):
            continue
        name = node.args[0].value
        fallbacks[name] = ast.literal_eval(node.args[1])
    for name, default in declared.items():
        assert name in fallbacks, name
        assert fallbacks[name] == default, name


def _ohlc(close, index, rng, width=0.012):
    close = np.asarray(close, dtype=float)
    opened = np.roll(close, 1)
    opened[0] = close[0]
    noise = np.abs(rng.normal(0.0, width * 0.35, size=len(close)))
    high = np.maximum.reduce([close, opened, close * (1.0 + noise + width)])
    low = np.minimum.reduce([close, opened, close * (1.0 - noise - width)])
    return pd.DataFrame(
        {
            "open": opened,
            "high": high,
            "low": low,
            "close": close,
            "volume": np.full(len(close), 1_000_000.0),
            "lot_size": np.full(len(close), 1.0),
        },
        index=index,
    )


def _synthetic_frames(periods=260):
    rng = np.random.default_rng(11)
    index = pd.bdate_range("2025-06-02", periods=periods)
    spot = 2.80 + np.cumsum(rng.normal(0.0, 0.015, size=periods))
    spot = np.maximum(spot, 2.2)
    frames = {UNDERLYING_KEY: _ohlc(spot, index, rng, width=0.008)}
    t = np.linspace(1.0, 0.2, periods)
    frames[LEG_KEYS[0]] = _ohlc(0.04 + 0.02 * t, index, rng, width=0.03)
    frames[LEG_KEYS[1]] = _ohlc(0.08 + 0.04 * t, index, rng, width=0.03)
    frames[LEG_KEYS[2]] = _ohlc(0.08 + 0.04 * t, index, rng, width=0.03)
    frames[LEG_KEYS[3]] = _ohlc(0.04 + 0.02 * t, index, rng, width=0.03)
    return frames


def test_iron_condor_backtest_opens_and_closes():
    result = StrategyV2BacktestRunner(
        code=_load_code(),
        frames=_synthetic_frames(),
        initial_capital=200_000,
        commission=0.0003,
        slippage=0.0002,
        params={
            "put_otm_pct": 0.03,
            "call_otm_pct": 0.03,
            "wing_width": 0.10,
            "profit_target_pct": 0.50,
            "stop_loss_mult": 2.0,
            "min_credit": 0.02,
            "min_entry_dte": 7,
            "max_entry_dte": 45,
            "exit_dte": 7,
            "max_realized_vol": 0.50,
            "expiry_year": 2026,
            "expiry_month": 3,
            "expiry_day": 25,
        },
    ).run()

    assert result["engine"]["version"] == "quantdinger-strategy-api-v2"
    assert len(result["equityCurve"]) >= 200
    reasons = {str(item.get("reason") or "") for item in result.get("executions") or []}
    assert "ic_open_put_short" in reasons or "ic_open_call_short" in reasons
