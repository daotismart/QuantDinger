"""LSP chart indicator: TDX port contract and numeric helpers."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from app.services.indicator_code_quality import analyze_indicator_code_quality
from app.services.indicator_params import IndicatorParamsParser
from app.services.indicator_validation import generate_mock_df, validate_indicator_code
from app.utils.safe_exec import build_safe_builtins, safe_exec_with_validation

LSP_PATH = Path(__file__).resolve().parents[2] / "docs" / "examples" / "chart_indicator_lsp.py"


def _load_lsp_code() -> str:
    return LSP_PATH.read_text(encoding="utf-8")


def test_lsp_example_file_exists():
    assert LSP_PATH.is_file()
    code = _load_lsp_code()
    assert 'my_indicator_name = "LSP"' in code
    assert "days_1" in code and "days_2" in code


def test_lsp_code_quality_has_no_errors():
    hints = analyze_indicator_code_quality(_load_lsp_code())
    errors = [h for h in hints if h.get("severity") == "error"]
    assert errors == []


def test_lsp_indicator_validates_in_sandbox():
    result = validate_indicator_code(_load_lsp_code())
    assert result["success"] is True, result.get("msg")
    assert result["plots_count"] >= 8
    assert result["signals_count"] == 3


def _exec_lsp(df: pd.DataFrame, extra_params=None):
    code = _load_lsp_code()
    declared = IndicatorParamsParser.parse_params(code)
    merged = IndicatorParamsParser.merge_params(declared, extra_params or {})
    env = {
        "df": df.copy(),
        "pd": pd,
        "np": np,
        "params": merged,
        "output": None,
    }
    for col in ("open", "high", "low", "close", "volume"):
        env[col] = env["df"][col]
    env["__builtins__"] = build_safe_builtins()
    result = safe_exec_with_validation(
        code=code,
        exec_globals=env,
        exec_locals=env,
        timeout=20,
    )
    assert result.get("success"), result.get("error")
    return env["output"]


def test_lsp_plot_lengths_and_finite_core_lines():
    df = generate_mock_df(180)
    output = _exec_lsp(df)
    n = len(df)
    by_name = {p["name"]: p["data"] for p in output["plots"]}
    for name in ("LSP_BB", "LSP_BB2", "K1", "D1", "MPF", "P", "F"):
        assert name in by_name
        assert len(by_name[name]) == n
    for sig in output["signals"]:
        assert len(sig["data"]) == n

    finite = [v for v in by_name["LSP_BB"] if isinstance(v, (int, float))]
    assert finite, "LSP_BB should emit values after warmup"
    assert all(0.0 <= v <= 100.0 + 1e-6 for v in finite)


def test_lsp_doji_bars_still_render():
    df = pd.DataFrame(
        {
            "time": list(range(10)),
            "open": [10.0] * 10,
            "high": [10.0, 11.0] * 5,
            "low": [10.0, 9.0] * 5,
            "close": [10.0, 10.5, 10.0, 10.8, 10.0, 11.0, 10.0, 11.2, 10.0, 11.4],
            "volume": [100.0] * 10,
        }
    )
    output = _exec_lsp(df, extra_params={"days_1": 3, "days_2": 4, "n_rsv": 3, "trds": 3})
    assert output["name"] == "LSP"
    assert any(p["name"] == "LSP_BB" for p in output["plots"])


def test_lsp_optional_force_and_path_plots():
    df = generate_mock_df(80)
    base = _exec_lsp(df)
    extra = _exec_lsp(df, extra_params={"show_force": True, "show_path": True})
    assert len(extra["plots"]) > len(base["plots"])
    names = {p["name"] for p in extra["plots"]}
    assert "Force" in names and "LSP_B" in names
    x = np.array([1.0, 2.0, 3.0, 4.0], dtype=float)
    period = 3
    weights = np.arange(1, period + 1, dtype=float)
    weights = weights / weights.sum()
    conv = np.convolve(x, weights[::-1], mode="valid")
    np.testing.assert_allclose(conv[0], 14.0 / 6.0)
    np.testing.assert_allclose(conv[1], 20.0 / 6.0)


def test_tdx_wma_weights_oldest_one_newest_n():
    x = np.array([1.0, 2.0, 3.0, 4.0], dtype=float)
    period = 3
    weights = np.arange(1, period + 1, dtype=float)
    weights = weights / weights.sum()
    conv = np.convolve(x, weights[::-1], mode="valid")
    np.testing.assert_allclose(conv[0], 14.0 / 6.0)
    np.testing.assert_allclose(conv[1], 20.0 / 6.0)


def test_tdx_sma_alpha_is_m_over_n():
    s = pd.Series([1.0, 2.0, 3.0, 4.0, 5.0])
    n, m = 3, 1
    alpha = m / n
    got = s.ewm(alpha=alpha, adjust=False, min_periods=1).mean()
    y = [1.0]
    for x in s.iloc[1:]:
        y.append((m * float(x) + (n - m) * y[-1]) / n)
    np.testing.assert_allclose(got.to_numpy(), np.array(y), rtol=1e-12)
