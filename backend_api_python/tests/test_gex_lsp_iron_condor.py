"""Unit tests for GEX + LSP + Kelly iron-condor engine."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from app.services.gex_lsp_strangle.gex_walls import (
    compute_gex_walls,
    is_adjusted_contract,
    select_iron_condor_strikes,
)
from app.services.gex_lsp_strangle.iron_condor_engine import (
    IronCondorBacktestConfig,
    _OpenIronCondor,
    _close_cost,
    clip_iron_condor_close_debit,
    estimate_iron_condor_margin,
    normalize_iv_rank_min,
    run_iron_condor_backtest,
    size_iron_condor_by_risk,
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
    pick = select_iron_condor_strikes(
        walls, min_width_pct=0.02, wing_steps=1, min_short_delta=0.0, max_short_delta=1.0
    )
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
    wall_pick = select_iron_condor_strikes(
        walls, min_width_pct=0.02, wing_steps=1, min_short_delta=0.0, max_short_delta=1.0
    )
    tight = select_iron_condor_strikes(
        walls,
        min_width_pct=0.02,
        wing_steps=1,
        short_otm_pct=0.025,
        min_credit_to_width=0.15,
        min_short_delta=0.0,
        max_short_delta=1.0,
    )
    assert tight is not None
    assert tight["long_put_strike"] < tight["put_strike"] < tight["spot"] < tight["call_strike"] < tight["long_call_strike"]
    assert tight["call_strike"] >= tight["spot"] * (1.0 + 0.025) - 1e-9 or tight["call_strike"] in (3.0, 3.1)
    assert tight.get("credit_to_width", 0) >= 0.15
    skinny = select_iron_condor_strikes(
        walls,
        min_width_pct=0.02,
        wing_steps=1,
        short_otm_pct=0.025,
        min_credit_to_width=0.99,
        min_short_delta=0.0,
        max_short_delta=1.0,
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
            min_short_delta=0.0,
            max_short_delta=1.0,
            min_credit_to_width=0.0,
            min_dte=1,
            max_dte=120,
            target_dte=0,
            expiry_month="next",
            risk_cap=0.0,
            exclude_adjusted=False,
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
        assert trade.get("shortCallCode")
        assert trade.get("shortPutCode")
        assert trade.get("longCallCode")
        assert trade.get("longPutCode")


def test_iron_condor_v2_example_uses_listed_chain_not_fixed_codes() -> None:
    path = REPO_ROOT / "docs/examples/strategy_v2_gex_lsp_iron_condor.py"
    code = path.read_text(encoding="utf-8")
    assert 'strategy_family="options_short_vol_iron_condor"' in code
    assert "listed_chain_gex_walls" in code
    assert "CNStock:510050.SH" in code
    assert "10010975" not in code
    assert "10004448" not in code
    assert "10004449" not in code
    program = compile_strategy_v2(code)
    keys = {item.key for item in program.manifest.universe.instruments}
    assert keys == {"CNStock:510050.SH"}
    assert program.manifest.metadata_fields.get("strategy_family") == "options_short_vol_iron_condor"
    assert program.manifest.metadata_fields.get("contract_selection") == "listed_chain_gex_walls"
    assert program.manifest.metadata_fields.get("pick_model") == "gex_tv_iron_condor"


def test_is_adjusted_contract_and_iv_rank_scale():
    assert is_adjusted_contract("50ETF购4月3.117A")
    assert is_adjusted_contract("50ETF沽4月3215A")
    assert not is_adjusted_contract("50ETF购4月3100")
    assert not is_adjusted_contract("50ETF沽5月2900")
    assert abs(normalize_iv_rank_min(40) - 0.40) < 1e-9
    assert abs(normalize_iv_rank_min(0.40) - 0.40) < 1e-9


def test_gex_tv_pick_uses_delta_band_outside_walls():
    rows = []
    # Spot 3.00; call wall 3.10; put wall 2.90. 14–25Δ at 3.15/2.85.
    specs = [
        (2.70, 200, 8000, 0.06, -0.08),
        (2.75, 400, 12000, 0.08, -0.10),
        (2.80, 800, 20000, 0.10, -0.12),
        (2.85, 2000, 35000, 0.12, -0.18),
        (2.90, 5000, 80000, 0.16, -0.24),
        (2.95, 12000, 20000, 0.30, -0.30),
        (3.00, 18000, 8000, 0.50, -0.50),
        (3.05, 25000, 4000, 0.30, -0.16),
        (3.10, 90000, 2500, 0.24, -0.12),
        (3.15, 40000, 1200, 0.18, -0.10),
        (3.20, 8000, 800, 0.12, -0.08),
        (3.25, 3000, 400, 0.08, -0.06),
        (3.30, 1000, 200, 0.05, -0.04),
    ]
    for strike, call_oi, put_oi, d_c, d_p in specs:
        dist = abs(strike - 3.00)
        px = max(0.008, 0.10 - dist * 0.35)
        rows.append(
            {
                "trade_date": "2026-04-01",
                "strike": strike,
                "cp": "C",
                "expire_date": "2026-05-27",
                "open_interest": call_oi,
                "gamma": 1.0,
                "delta": d_c,
                "theta": -0.002 * max(0.2, 1.0 - dist),
                "option_close": px,
                "contract_code": f"50ETF购5月{int(strike * 1000)}",
            }
        )
        rows.append(
            {
                "trade_date": "2026-04-01",
                "strike": strike,
                "cp": "P",
                "expire_date": "2026-05-27",
                "open_interest": put_oi,
                "gamma": 1.0,
                "delta": d_p,
                "theta": -0.002 * max(0.2, 1.0 - dist),
                "option_close": px,
                "contract_code": f"50ETF沽5月{int(strike * 1000)}",
            }
        )
    # Adjusted junk that must not be chosen.
    rows.append(
        {
            "trade_date": "2026-04-01",
            "strike": 3.117,
            "cp": "C",
            "expire_date": "2026-05-27",
            "open_interest": 999999,
            "gamma": 1.0,
            "delta": 0.20,
            "theta": -0.01,
            "option_close": 0.20,
            "contract_code": "50ETF购5月3.117A",
        }
    )
    walls = compute_gex_walls(pd.DataFrame(rows), underlying=3.00, min_dte=20, max_dte=80, target_dte=45)
    pick = select_iron_condor_strikes(
        walls,
        wing_steps=3,
        min_credit_to_width=0.25,
        min_short_delta=0.14,
        max_short_delta=0.25,
        exclude_adjusted=True,
        strike_grid=0.05,
    )
    assert pick is not None
    assert pick["call_strike"] >= float(walls["call_wall"]) - 1e-9
    assert pick["put_strike"] <= float(walls["put_wall"]) + 1e-9
    assert 0.14 - 1e-9 <= abs(float(pick["call_delta"])) <= 0.25 + 1e-9
    assert 0.14 - 1e-9 <= abs(float(pick["put_delta"])) <= 0.25 + 1e-9
    assert pick["call_wing"] >= 0.15 - 1e-9
    assert pick["put_wing"] >= 0.15 - 1e-9
    assert pick["credit_to_width"] >= 0.25 - 1e-9
    assert "A" not in str(pick["call_code"])
    assert pick["long_call_close"] > 0 and pick["long_put_close"] > 0


def test_risk_cap_and_close_debit_clip():
    lots = size_iron_condor_by_risk(
        equity=1_000_000,
        max_loss_per_lot=2000.0,
        risk_cap=0.06,
        max_lots=80,
        base_lots=80,
        kelly_lots=200,
    )
    assert lots == 30  # 60000 / 2000
    assert clip_iron_condor_close_debit(-1.0, 4000.0, 20000.0) == 0.0
    assert clip_iron_condor_close_debit(999999.0, 4000.0, 20000.0) == 24000.0


def test_missing_leg_quote_does_not_flatten():
    open_trade = _OpenIronCondor(
        entry_date=pd.Timestamp("2026-04-01"),
        expire_date="2026-05-27",
        short_call_code="SC",
        short_put_code="SP",
        long_call_code="LC",
        long_put_code="LP",
        short_call_strike=3.10,
        short_put_strike=2.90,
        long_call_strike=3.25,
        long_put_strike=2.75,
        call_wall=3.10,
        put_wall=2.90,
        call_lots=1,
        put_lots=1,
        entry_spot=3.00,
        entry_credit=0.04,
        entry_credit_cash=400.0,
        max_risk=1100.0,
        lsp_score_entry=0.0,
        option_cash=400.0,
        option_fees=20.0,
    )
    day = pd.DataFrame(
        [
            {"contract_code": "SC", "strike": 3.10, "cp": "C", "expire_date": "2026-05-27", "option_close": 0.02, "delta": 0.18},
            {"contract_code": "SP", "strike": 2.90, "cp": "P", "expire_date": "2026-05-27", "option_close": 0.02, "delta": -0.18},
            {"contract_code": "LC", "strike": 3.25, "cp": "C", "expire_date": "2026-05-27", "option_close": 0.0, "delta": 0.08},
            {"contract_code": "LP", "strike": 2.75, "cp": "P", "expire_date": "2026-05-27", "option_close": 0.005, "delta": -0.08},
        ]
    )
    mark = _close_cost(open_trade, day, IronCondorBacktestConfig())
    assert float(mark["quotes_ok"]) == 0.0
    # Scratch mark, not a 0-price buyback of the shorts.
    assert mark["close_debit"] == 400.0

