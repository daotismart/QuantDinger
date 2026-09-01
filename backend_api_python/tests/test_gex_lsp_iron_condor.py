"""Unit tests for GEX + LSP + Kelly iron-condor engine."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from app.services.gex_lsp_strangle.gex_walls import compute_gex_walls, select_iron_condor_strikes
from app.services.gex_lsp_strangle.iron_condor_engine import (
    IronCondorBacktestConfig,
    estimate_iron_condor_margin,
    run_iron_condor_backtest,
    size_iron_condor_lots,
)
from app.services.strategy_v2 import compile_strategy_v2

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_select_iron_condor_strikes_builds_wings():
    rows = []
    for strike, call_oi, put_oi in [
        (2.70, 1000, 40000),
        (2.80, 2000, 50000),
        (2.90, 5000, 20000),
        (3.00, 80000, 8000),
        (3.10, 20000, 3000),
        (3.20, 5000, 1000),
    ]:
        rows.append(
            {
                "trade_date": "2026-08-01",
                "strike": strike,
                "cp": "C",
                "expire_date": "2026-09-23",
                "open_interest": call_oi,
                "gamma": 1.0,
                "delta": 0.35,
                "option_close": max(0.01, 0.12 - abs(strike - 2.95) * 0.4),
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
                "delta": -0.35,
                "option_close": max(0.01, 0.12 - abs(strike - 2.95) * 0.4),
                "contract_code": f"P{strike}",
            }
        )
    walls = compute_gex_walls(pd.DataFrame(rows), underlying=2.95, min_dte=5, max_dte=60)
    pick = select_iron_condor_strikes(walls, min_width_pct=0.02, wing_steps=1)
    assert pick is not None
    assert pick["structure"] == "iron_condor"
    assert pick["long_put_strike"] < pick["put_strike"] <= pick["spot"] <= pick["call_strike"] < pick["long_call_strike"]


def test_select_iron_condor_tight_otm_and_credit_filter():
    rows = []
    for strike, call_oi, put_oi in [
        (2.70, 1000, 40000),
        (2.80, 2000, 50000),
        (2.90, 5000, 20000),
        (3.00, 80000, 8000),
        (3.10, 20000, 3000),
        (3.20, 5000, 1000),
    ]:
        rows.append(
            {
                "trade_date": "2026-08-01",
                "strike": strike,
                "cp": "C",
                "expire_date": "2026-09-23",
                "open_interest": call_oi,
                "gamma": 1.0,
                "delta": 0.35,
                "option_close": max(0.01, 0.12 - abs(strike - 2.95) * 0.4),
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
                "delta": -0.35,
                "option_close": max(0.01, 0.12 - abs(strike - 2.95) * 0.4),
                "contract_code": f"P{strike}",
            }
        )
    walls = compute_gex_walls(pd.DataFrame(rows), underlying=2.95, min_dte=5, max_dte=60)
    wall_pick = select_iron_condor_strikes(walls, min_width_pct=0.02, wing_steps=1)
    tight = select_iron_condor_strikes(
        walls, min_width_pct=0.02, wing_steps=1, short_otm_pct=0.025, min_credit_to_width=0.15
    )
    assert tight is not None
    assert tight["long_put_strike"] < tight["put_strike"] < tight["spot"] < tight["call_strike"] < tight["long_call_strike"]
    assert tight["call_strike"] >= tight["spot"] * (1.0 + 0.025) - 1e-9 or tight["call_strike"] in (3.0, 3.1)
    assert tight.get("credit_to_width", 0) >= 0.15
    skinny = select_iron_condor_strikes(
        walls, min_width_pct=0.02, wing_steps=1, short_otm_pct=0.025, min_credit_to_width=0.99
    )
    assert skinny is None


def test_estimate_iron_condor_margin_defined_risk():
    margin = estimate_iron_condor_margin(
        short_call_strike=3.0,
        long_call_strike=3.1,
        short_put_strike=2.85,
        long_put_strike=2.75,
        net_credit=0.03,
        multiplier=10000,
        lots=2,
    )
    # max wing 0.10 - credit 0.03 = 0.07 * 10000 * 2
    assert abs(margin - 1400.0) < 1e-6


def test_kelly_iron_condor_sizing():
    out = size_iron_condor_lots(
        equity=1_000_000,
        short_call_strike=3.0,
        long_call_strike=3.1,
        short_put_strike=2.85,
        long_put_strike=2.75,
        net_credit=0.03,
        multiplier=10000,
        win_prob=0.7,
        odds_b=1.0,
        max_kelly_fraction=0.25,
        max_lots=20,
    )
    assert not out["blocked"]
    assert out["baseLots"] >= 1
    assert abs(out["marginPerLot"] - 700.0) < 1e-6


def test_iron_condor_backtest_runs_on_synthetic_panel():
    dates = pd.date_range("2026-04-01", periods=35, freq="B")
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
    strikes = [2.75, 2.85, 2.95, 3.05, 3.15]
    oi_map = {2.75: (5_000, 60_000), 2.85: (8_000, 40_000), 2.95: (20_000, 20_000), 3.05: (50_000, 8_000), 3.15: (15_000, 3_000)}
    chain_rows = []
    oi_rows = []
    for dt in dates:
        spot = float(und.loc[und.trade_date == dt, "close"].iloc[0])
        for strike in strikes:
            call_oi, put_oi = oi_map[strike]
            for cp, oi in (("C", call_oi), ("P", put_oi)):
                code = f"50ETF-{cp}-{strike}"
                dist = abs(strike - spot)
                px = max(0.005, 0.08 - dist * 0.5)
                chain_rows.append(
                    {
                        "trade_date": dt,
                        "underlying_code": "510050",
                        "contract_code": code,
                        "strike": strike,
                        "cp": cp,
                        "expire_date": "2026-06-24",
                        "option_close": px,
                        "underlying_close": spot,
                        "delta": 0.3 if cp == "C" else -0.3,
                        "gamma": 1.2,
                        "vega": 0.01,
                        "theta": -0.001,
                        "iv": 0.22,
                    }
                )
                oi_rows.append(
                    {
                        "trade_date": dt,
                        "underlying_code": "510050",
                        "contract_code": code,
                        "open_interest": oi,
                    }
                )
    result = run_iron_condor_backtest(
        und,
        pd.DataFrame(chain_rows),
        pd.DataFrame(oi_rows),
        config=IronCondorBacktestConfig(
            require_inside_walls=False,
            require_high_iv=False,
            use_kelly_sizing=False,
            lots=1,
            wing_steps=1,
            lsp_max_skew_lots=0,
        ),
    )
    assert result.summary["structure"] == "iron_condor"
    assert result.summary["finalEquity"] > 0
    assert "annualizedReturn" in result.summary
    assert len(result.equity_curve) > 0
    for trade in result.trades:
        assert trade["longPutStrike"] < trade["shortPutStrike"]
        assert trade["shortCallStrike"] < trade["longCallStrike"]
        assert trade.get("callLots", 0) >= 1
        assert trade.get("putLots", 0) >= 1


def test_iron_condor_v2_example_uses_listed_50etf_contracts():
    path = REPO_ROOT / "docs/examples/strategy_v2_gex_lsp_iron_condor.py"
    code = path.read_text(encoding="utf-8")
    assert "CNIndexOptions:10010975" in code
    assert "CNIndexOptions:10004448" not in code
    program = compile_strategy_v2(code)
    keys = {item.key for item in program.manifest.universe.instruments}
    assert "CNIndexOptions:10010975" in keys
    assert "CNIndexOptions:10010981" in keys
    assert "CNIndexOptions:10010976" in keys
    assert "CNIndexOptions:10010980" in keys
    assert "CNStock:510050.SH" in keys
