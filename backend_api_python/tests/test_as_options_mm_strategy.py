"""AS options market-maker: Strategy API V2 contract and pricing helpers."""

from __future__ import annotations

import ast
import math
from pathlib import Path

import numpy as np
import pandas as pd

from app.services.indicator_params import IndicatorParamsParser
from app.services.strategy_v2 import StrategyV2BacktestRunner, compile_strategy_v2
from app.utils.safe_exec import SAFE_IMPORT_MODULES, validate_code_safety


AS_MM_PATH = Path(__file__).resolve().parents[2] / "docs" / "examples" / "strategy_v2_as_options_mm.py"
OPTION_KEY = "CNFuturesOptions:M2609-C-2800"
UNDERLYING_KEY = "CNFutures:M2609"


def _load_code() -> str:
    return AS_MM_PATH.read_text(encoding="utf-8")


def _compile():
    return compile_strategy_v2(_load_code())


def _ns():
    return _compile().namespace


def test_as_mm_example_file_exists():
    assert AS_MM_PATH.is_file()
    code = _load_code()
    assert "AS Options Market Maker" in code.splitlines()[0] or "AS Options Market Maker" in code
    assert "Avellaneda-Stoikov" in code
    assert "PERSIST_RUNTIME_STATE = True" in code
    assert 'direction_mode="both"' in code
    assert "order_type=\"limit\"" in code
    assert "cancel_order" in code
    assert "context.params" not in code.split("def handle_data")[0]
    assert "from __future__" not in code
    assert "import pandas" not in code
    ok, err = validate_code_safety(code)
    assert ok is True, err


def test_as_mm_source_imports_are_sandbox_safe():
    tree = ast.parse(_load_code())
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert alias.name.split(".")[0] in SAFE_IMPORT_MODULES
        elif isinstance(node, ast.ImportFrom) and node.module:
            assert node.module.split(".")[0] in SAFE_IMPORT_MODULES


def test_as_mm_compiles_when_editor_injects_future_annotations():
    compiled = compile_strategy_v2("from __future__ import annotations\n\n" + _load_code())
    assert compiled.manifest.strategy_type == "portfolio"
    assert compiled.manifest.direction_mode == "both"


def test_as_mm_compiles_as_portfolio_both_sides():
    compiled = _compile()
    manifest = compiled.manifest
    assert compiled.ok if hasattr(compiled, "ok") else True
    assert manifest.strategy_type == "portfolio"
    assert manifest.direction_mode == "both"
    assert manifest.primary_frequency == "5m"
    assert manifest.warmup_bars == 60
    symbols = {item.key for item in manifest.universe.instruments}
    assert OPTION_KEY in symbols
    assert UNDERLYING_KEY in symbols


def test_as_mm_param_defaults_match_get_fallbacks():
    code = _load_code()
    declared = {item["name"]: item["default"] for item in IndicatorParamsParser.parse_params(code)}
    assert declared
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
    assert set(declared) == set(fallbacks)
    for name, default in declared.items():
        assert fallbacks[name] == default, name


def test_black76_atm_call_delta_near_half():
    ns = _ns()
    delta = ns["_black76_delta"](2800.0, 2800.0, 0.25, 0.2, True)
    assert 0.50 < delta < 0.54
    put_delta = ns["_black76_delta"](2800.0, 2800.0, 0.25, 0.2, False)
    assert -0.50 < put_delta < -0.46
    gamma = ns["_black76_gamma"](2800.0, 2800.0, 0.25, 0.2)
    assert gamma > 0.0


def test_parse_cn_option_spec_from_canonical_key():
    ns = _ns()
    spec = ns["_parse_cn_option_spec"](OPTION_KEY)
    assert spec["root"] == "M"
    assert spec["year"] == 2026
    assert spec["month"] == 9
    assert spec["is_call"] is True
    assert spec["strike"] == 2800.0
    put = ns["_parse_cn_option_spec"]("CNFuturesOptions:m2609-P-2650")
    assert put["is_call"] is False
    assert put["strike"] == 2650.0


def _quotes(ns, **overrides):
    payload = {
        "mid": 80.0,
        "futures_px": 2800.0,
        "strike": 2800.0,
        "is_call": True,
        "tte": 0.25,
        "horizon": 1.0,
        "sigma_f": 0.2,
        "q_opt": 0.0,
        "q_und": 0.0,
        "tick": 0.5,
        "gamma": 0.1,
        "gamma_delta": 0.05,
        "k_intensity": 1.5,
        "inventory_skew": 0.5,
        "gamma_widen": 0.5,
        "vega_widen": 0.05,
        "toxicity": 0.0,
        "min_ticks": 2,
        "fee_floor": 0.5,
        "max_inventory": 5.0,
        "max_half_spread_frac": 0.15,
    }
    payload.update(overrides)
    return ns["_as_option_quotes"](**payload)


def test_long_inventory_lowers_reservation_price():
    ns = _ns()
    flat = _quotes(ns, q_opt=0.0)
    long_opt = _quotes(ns, q_opt=3.0)
    short_opt = _quotes(ns, q_opt=-3.0)
    assert flat is not None and long_opt is not None and short_opt is not None
    assert long_opt["reservation"] < flat["reservation"] < short_opt["reservation"]
    assert long_opt["bid"] < flat["bid"]
    assert short_opt["ask"] > flat["ask"]


def test_net_delta_inventory_also_skews_quotes():
    ns = _ns()
    flat = _quotes(ns, q_opt=0.0, q_und=0.0)
    long_delta = _quotes(ns, q_opt=0.0, q_und=4.0)
    assert long_delta["reservation"] < flat["reservation"]


def test_min_spread_and_tick_rounding():
    ns = _ns()
    quotes = _quotes(ns, gamma=0.01, k_intensity=50.0, fee_floor=0.0, gamma_widen=0.0, vega_widen=0.0)
    assert quotes is not None
    assert quotes["ask"] - quotes["bid"] >= 2 * 0.5 - 1e-9
    assert abs(quotes["bid"] / 0.5 - round(quotes["bid"] / 0.5)) < 1e-9
    assert abs(quotes["ask"] / 0.5 - round(quotes["ask"] / 0.5)) < 1e-9
    assert quotes["bid"] < quotes["ask"]


def test_inventory_cap_quotes_only_reducing_side():
    ns = _ns()
    long_cap = _quotes(ns, q_opt=5.0, max_inventory=5.0)
    short_cap = _quotes(ns, q_opt=-5.0, max_inventory=5.0)
    assert long_cap["bid"] is None
    assert long_cap["ask"] is not None
    assert short_cap["ask"] is None
    assert short_cap["bid"] is not None


def test_gamma_widens_near_expiry_atm():
    ns = _ns()
    far = _quotes(ns, tte=0.5, gamma_widen=0.5)
    near = _quotes(ns, tte=0.04, gamma_widen=0.5)
    assert near["half_spread"] > far["half_spread"]


def _ohlc(close, index, rng, width=0.02):
    close = np.asarray(close, dtype=float)
    noise = np.abs(rng.normal(0.0, width * 0.35, size=len(close)))
    opened = np.roll(close, 1)
    opened[0] = close[0]
    high = np.maximum.reduce([close, opened, close * (1.0 + noise + width)])
    low = np.minimum.reduce([close, opened, close * (1.0 - noise - width)])
    return pd.DataFrame(
        {
            "open": opened,
            "high": high,
            "low": low,
            "close": close,
            "volume": np.full(len(close), 20000.0),
            "lot_size": np.full(len(close), 1.0),
        },
        index=index,
    )


def _aligned_frames(periods=240):
    rng = np.random.default_rng(7)
    index = pd.date_range("2026-03-02 09:00", periods=periods, freq="5min")
    futures = 2800.0 + np.cumsum(rng.normal(0.0, 1.2, size=periods))
    futures = np.maximum(futures, 2400.0)
    tte = np.linspace(0.40, 0.28, periods)
    d1 = (np.log(futures / 2800.0) + 0.5 * 0.2 * 0.2 * tte) / (0.2 * np.sqrt(tte))
    d2 = d1 - 0.2 * np.sqrt(tte)
    call = futures * (0.5 * (1.0 + np.vectorize(math.erf)(d1 / math.sqrt(2.0)))) - 2800.0 * (
        0.5 * (1.0 + np.vectorize(math.erf)(d2 / math.sqrt(2.0)))
    )
    call = np.maximum(call, 5.0)
    return {
        UNDERLYING_KEY: _ohlc(futures, index, rng, width=0.006),
        OPTION_KEY: _ohlc(call, index, rng, width=0.03),
    }


def test_as_mm_backtest_runs_and_quotes():
    result = StrategyV2BacktestRunner(
        code=_load_code(),
        frames=_aligned_frames(),
        initial_capital=200000,
        commission=0.0005,
        slippage=0.0,
        params={"enable_delta_hedge": False, "quote_lots": 1, "max_inventory": 5},
    ).run()

    assert result["engine"]["version"] == "quantdinger-strategy-api-v2"
    assert result["manifest"]["strategyType"] == "portfolio"
    assert result["manifest"]["directionMode"] == "both"
    curve = result["equityCurve"]
    assert len(curve) >= 200
    assert result["finalEquity"] > 0
    reasons = {str(item.get("reason") or "") for item in result.get("executions") or []}
    assert "as_mm_bid" in reasons or "as_mm_ask" in reasons
    client_ids = [str(item.get("clientOrderId") or item.get("client_order_id") or "") for item in result.get("executions") or []]
    assert any(item.startswith("asmm-") for item in client_ids)


def test_as_mm_optional_delta_hedge_emits_underlying_orders():
    frames = _aligned_frames(180)
    option = frames[OPTION_KEY].copy()
    option["high"] = np.maximum(option["open"], option["close"])
    option["low"] = np.minimum(option["open"], option["close"]) * 0.94
    frames[OPTION_KEY] = option
    result = StrategyV2BacktestRunner(
        code=_load_code(),
        frames=frames,
        initial_capital=200000,
        commission=0.0005,
        slippage=0.0,
        params={
            "enable_delta_hedge": True,
            "hedge_every_n_bars": 2,
            "max_inventory": 4,
            "quote_lots": 1,
        },
    ).run()
    executions = result.get("executions") or []
    symbols = {str(item.get("symbol") or "") for item in executions}
    reasons = {str(item.get("reason") or "") for item in executions}
    assert OPTION_KEY in symbols
    assert "as_mm_bid" in reasons
    assert UNDERLYING_KEY in symbols
    assert "as_mm_delta_hedge" in reasons
