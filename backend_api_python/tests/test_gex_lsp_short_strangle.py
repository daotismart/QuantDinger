"""Unit tests for GEX+LSP short-strangle helpers and backtest engine."""

from __future__ import annotations

import numpy as np
import pandas as pd

from app.services.gex_lsp_strangle.engine import ShortStrangleBacktestConfig, run_short_strangle_backtest
from app.services.gex_lsp_strangle.gex_walls import compute_gex_walls, select_strangle_strikes
from app.services.gex_lsp_strangle.lsp import compute_lsp_features


def test_lsp_features_have_regime_columns():
    idx = pd.date_range("2026-01-01", periods=40, freq="B")
    close = pd.Series(np.linspace(2.8, 3.0, len(idx)) + np.sin(np.arange(len(idx)) / 3) * 0.02, index=idx)
    bars = pd.DataFrame(
        {
            "open": close.shift(1).fillna(close.iloc[0]),
            "high": close * 1.01,
            "low": close * 0.99,
            "close": close,
            "volume": np.full(len(idx), 5_000_000.0),
        },
        index=idx,
    )
    out = compute_lsp_features(bars, days_1=5, days_2=10, neutral_band=8.0)
    assert {"lsp_bb", "lsp_bb2", "lsp_regime", "lsp_ok_for_short_vol"} <= set(out.columns)
    assert out["lsp_regime"].notna().any()


def test_gex_walls_pick_max_oi_strikes():
    rows = []
    for strike, call_oi, put_oi in [
        (2.8, 1000, 50000),
        (2.9, 2000, 20000),
        (3.0, 80000, 8000),
        (3.1, 10000, 3000),
    ]:
        rows.append(
            {
                "trade_date": "2026-08-01",
                "strike": strike,
                "cp": "C",
                "expire_date": "2026-09-23",
                "open_interest": call_oi,
                "gamma": 1.0,
                "delta": 0.4,
                "option_close": 0.05,
                "contract_code": f"C{strike}",
            }
        )
        rows.append(
            {
                "trade_date": "2026-08-01",
                "strike": strike,
                "cp": "P",
                "expire_date": "2026-09-23",
                "open_interest": put_oi,
                "gamma": 1.0,
                "delta": -0.4,
                "option_close": 0.05,
                "contract_code": f"P{strike}",
            }
        )
    walls = compute_gex_walls(pd.DataFrame(rows), underlying=2.95, min_dte=5, max_dte=60)
    assert walls["call_wall"] == 3.0
    assert walls["put_wall"] == 2.8
    pick = select_strangle_strikes(walls, min_width_pct=0.02)
    assert pick is not None
    assert pick["call_strike"] >= pick["spot"]
    assert pick["put_strike"] <= pick["spot"]


def test_short_strangle_backtest_runs_on_synthetic_panel():
    dates = pd.date_range("2026-04-01", periods=30, freq="B")
    und = pd.DataFrame(
        {
            "trade_date": dates,
            "underlying_code": "510050",
            "open": 2.95,
            "high": 2.97,
            "low": 2.93,
            "close": np.linspace(2.94, 2.96, len(dates)),
            "volume": 8_000_000,
            "amount": 24_000_000,
        }
    )
    chain_rows = []
    oi_rows = []
    for dt in dates:
        for strike, call_oi, put_oi in [(2.85, 20000, 50000), (2.95, 30000, 30000), (3.05, 60000, 15000)]:
            for cp, oi in (("C", call_oi), ("P", put_oi)):
                code = f"50ETF-{cp}-{strike}"
                chain_rows.append(
                    {
                        "trade_date": dt,
                        "underlying_code": "510050",
                        "contract_code": code,
                        "strike": strike,
                        "cp": cp,
                        "expire_date": "2026-06-24",
                        "option_close": 0.04 if strike != 2.95 else 0.06,
                        "underlying_close": float(und.loc[und.trade_date == dt, "close"].iloc[0]),
                        "delta": 0.3 if cp == "C" else -0.3,
                        "gamma": 1.2,
                        "vega": 0.01,
                        "theta": -0.001,
                        "iv": 0.2,
                    }
                )
                oi_rows.append({"trade_date": dt, "underlying_code": "510050", "contract_code": code, "open_interest": oi})
    chain = pd.DataFrame(chain_rows)
    oi = pd.DataFrame(oi_rows)
    result = run_short_strangle_backtest(
        und,
        chain,
        oi,
        config=ShortStrangleBacktestConfig(require_inside_walls=False, lots=1),
    )
    assert result.summary["trades"] >= 0
    assert result.summary["finalEquity"] > 0
    assert len(result.equity_curve) > 0
