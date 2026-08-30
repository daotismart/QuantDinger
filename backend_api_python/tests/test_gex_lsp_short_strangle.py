"""Unit tests for GEX walls + LSP delta-targeted short-vol engine."""

from __future__ import annotations

import numpy as np
import pandas as pd

from app.services.gex_lsp_strangle.engine import ShortStrangleBacktestConfig, run_short_strangle_backtest
from app.services.gex_lsp_strangle.gex_walls import (
    compute_gex_walls,
    list_monthly_expiries,
    select_strangle_strikes,
    select_target_expire,
)
from app.services.gex_lsp_strangle.kelly import (
    bs_short_call_win_prob,
    bs_short_put_win_prob,
    estimate_strangle_margin,
    estimate_win_prob,
    estimate_win_prob_from_bs_legs,
    kelly_fraction,
    size_by_kelly_margin,
    size_short_premium_lots,
)
from app.services.gex_lsp_strangle.lsp import (
    compute_lsp_features,
    lsp_option_skew_lots,
    lsp_target_delta_shares,
)


def test_lsp_features_include_delta_score():
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
    assert {"lsp_bb", "lsp_bb2", "lsp_regime", "lsp_delta_score"} <= set(out.columns)
    assert out["lsp_delta_score"].between(-1.0, 1.0).all()


def test_lsp_maps_to_delta_and_option_skew():
    assert lsp_target_delta_shares(1.0, lots=1, multiplier=10000, max_abs_delta=0.5) == 5000.0
    assert lsp_target_delta_shares(-1.0, lots=1, multiplier=10000, max_abs_delta=0.5) == -5000.0
    assert lsp_option_skew_lots(0.0, base_lots=1, max_skew_lots=1) == (1, 1)
    assert lsp_option_skew_lots(1.0, base_lots=1, max_skew_lots=1) == (0, 2)
    assert lsp_option_skew_lots(-1.0, base_lots=1, max_skew_lots=1) == (2, 0)


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


def test_delta_targeted_backtest_runs_on_synthetic_panel():
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
    result = run_short_strangle_backtest(
        und,
        pd.DataFrame(chain_rows),
        pd.DataFrame(oi_rows),
        config=ShortStrangleBacktestConfig(require_inside_walls=False, require_high_iv=False, use_kelly_sizing=False, lots=1, lsp_max_skew_lots=1),
    )
    assert result.summary["trades"] >= 0
    assert result.summary["finalEquity"] > 0
    assert len(result.equity_curve) > 0
    if result.daily:
        assert "lspDeltaScore" in result.daily[0]
        assert "targetDeltaShares" in result.daily[0]
    assert result.summary.get("hedgeMode") == "options_only"
    for trade in result.trades:
        assert "hedgeCash" not in trade
        assert trade.get("callLots", 0) + trade.get("putLots", 0) >= 0


def test_kelly_fraction_and_win_prob():
    assert abs(kelly_fraction(0.55, odds_b=1.0) - 0.1) < 1e-9
    assert kelly_fraction(0.5, odds_b=1.0) == 0.0
    assert kelly_fraction(0.4, odds_b=1.0) < 0
    assert abs(estimate_win_prob([], prior_p=0.55, prior_strength=10.0) - 0.55) < 1e-9
    pnls = [1.0] * 8 + [-1.0] * 2
    assert abs(estimate_win_prob(pnls, prior_p=0.5, prior_strength=0.0) - 0.8) < 1e-9


def test_kelly_sizing_caps_and_blocks():
    # Margin-ratio Kelly: f*=0.4 → capped to 0.25 of equity as margin budget.
    ok = size_by_kelly_margin(
        equity=1_000_000,
        spot=3.0,
        call_strike=3.1,
        put_strike=2.9,
        call_premium=0.02,
        put_premium=0.02,
        multiplier=10000,
        win_prob=0.7,
        odds_b=1.0,
        max_kelly_fraction=0.25,
        max_lots=5,
    )
    assert not ok.blocked
    assert ok.capped
    assert ok.margin_ratio == 0.25
    assert ok.base_lots == 5
    assert ok.reason == "capped"
    assert ok.margin_budget == 250_000.0

    # Equity 100k * f*=0.1 = 10k margin budget; one strangle lot margin ~ a few k → >=1 lot.
    exact = size_by_kelly_margin(
        equity=100_000,
        spot=3.0,
        call_strike=3.1,
        put_strike=2.9,
        call_premium=0.05,
        put_premium=0.05,
        multiplier=10000,
        win_prob=0.55,
        odds_b=1.0,
        max_kelly_fraction=0.25,
        max_lots=10,
        min_lots=1,
    )
    assert not exact.blocked
    assert exact.base_lots >= 1
    assert exact.margin_used <= exact.margin_budget + 1e-6

    no_edge = size_by_kelly_margin(
        equity=1_000_000,
        spot=3.0,
        call_strike=3.1,
        put_strike=2.9,
        call_premium=0.02,
        put_premium=0.02,
        multiplier=10000,
        win_prob=0.45,
        odds_b=1.0,
    )
    assert no_edge.blocked
    assert no_edge.base_lots == 0


def test_lsp_delta_exposure_scales_with_margin_budget():
    from app.services.gex_lsp_strangle.lsp import lsp_delta_exposure_shares

    d1 = lsp_delta_exposure_shares(1.0, margin_budget=100_000, spot=2.5, max_abs_delta=0.5)
    d2 = lsp_delta_exposure_shares(-0.5, margin_budget=100_000, spot=2.5, max_abs_delta=0.5)
    assert abs(d1 - (100_000 / 2.5) * 0.5) < 1e-6
    assert abs(d2 - (-0.5 * 0.5 * (100_000 / 2.5))) < 1e-6


def _synthetic_panel(n_days: int = 40, iv_fn=None):
    dates = pd.date_range("2026-04-01", periods=n_days, freq="B")
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
    for i, dt in enumerate(dates):
        iv = float(iv_fn(i, n_days)) if iv_fn else 0.2
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
                        "iv": iv,
                    }
                )
                oi_rows.append(
                    {"trade_date": dt, "underlying_code": "510050", "contract_code": code, "open_interest": oi}
                )
    return und, pd.DataFrame(chain_rows), pd.DataFrame(oi_rows)


def test_high_iv_filter_blocks_flat_iv_rank():
    und, chain, oi = _synthetic_panel(n_days=30, iv_fn=lambda i, n: 0.20)
    result = run_short_strangle_backtest(
        und,
        chain,
        oi,
        config=ShortStrangleBacktestConfig(
            require_inside_walls=False,
            require_high_iv=True,
            iv_rank_min=0.6,
            use_kelly_sizing=True,
        ),
    )
    assert result.summary["trades"] == 0
    assert any(d.get("kellyReason") == "iv_rank_too_low" for d in result.daily)


def test_rising_iv_allows_kelly_entry():
    und, chain, oi = _synthetic_panel(n_days=40, iv_fn=lambda i, n: 0.15 + 0.25 * (i / max(n - 1, 1)))
    result = run_short_strangle_backtest(
        und,
        chain,
        oi,
        config=ShortStrangleBacktestConfig(
            require_inside_walls=False,
            require_high_iv=True,
            iv_rank_min=0.6,
            use_kelly_sizing=True,
            kelly_max_lots=2,
            kelly_prior_win_prob=0.6,
        ),
    )
    assert result.summary["trades"] >= 1
    assert result.summary.get("sizingMode") == "kelly_margin_ratio"
    kelly_days = [d for d in result.daily if d.get("kellyBaseLots")]
    assert kelly_days
    assert all(int(d["kellyBaseLots"]) <= 2 for d in kelly_days if d.get("kellyBaseLots") is not None)


def test_select_target_expire_prefers_next_month():
    rows = []
    for expire in ("2026-04-22", "2026-05-27", "2026-06-24"):
        for strike, call_oi, put_oi in [(2.8, 1000, 40000), (3.0, 50000, 5000)]:
            for cp, oi in (("C", call_oi), ("P", put_oi)):
                rows.append(
                    {
                        "trade_date": "2026-04-01",
                        "strike": strike,
                        "cp": cp,
                        "expire_date": expire,
                        "open_interest": oi,
                        "gamma": 1.0,
                        "delta": 0.3 if cp == "C" else -0.3,
                        "option_close": 0.05,
                        "contract_code": f"{cp}-{expire}-{strike}",
                    }
                )
    df = pd.DataFrame(rows)
    months = list_monthly_expiries(df, asof="2026-04-01", min_dte=1, max_dte=120, min_contracts=4)
    assert [str(m.date()) for m in months] == ["2026-04-22", "2026-05-27", "2026-06-24"]
    assert str(select_target_expire(df, asof="2026-04-01", expiry_month="next", min_contracts=4).date()) == "2026-05-27"
    assert str(select_target_expire(df, asof="2026-04-01", expiry_month="front", min_contracts=4).date()) == "2026-04-22"
    walls = compute_gex_walls(df, underlying=2.95, min_dte=1, max_dte=120, expiry_month="next", min_contracts=4)
    assert walls["expire_date"] == "2026-05-27"


def test_roll_month_exits_fifteen_dte_and_reopens_next():
    """Open on 次月; when DTE<=15, roll and reopen a later month same day."""
    dates = pd.date_range("2026-04-01", periods=55, freq="B")
    und = pd.DataFrame(
        {
            "trade_date": dates,
            "underlying_code": "510050",
            "open": 2.95,
            "high": 2.97,
            "low": 2.93,
            "close": np.full(len(dates), 2.95),
            "volume": 8_000_000,
            "amount": 24_000_000,
        }
    )
    chain_rows = []
    oi_rows = []
    # Three months so 次月 can roll into the following 次月.
    for dt in dates:
        for expire in ("2026-05-27", "2026-06-24", "2026-07-22"):
            for strike, call_oi, put_oi in [(2.85, 20000, 50000), (2.95, 30000, 30000), (3.05, 60000, 15000)]:
                for cp, oi in (("C", call_oi), ("P", put_oi)):
                    code = f"50ETF-{expire}-{cp}-{strike}"
                    chain_rows.append(
                        {
                            "trade_date": dt,
                            "underlying_code": "510050",
                            "contract_code": code,
                            "strike": strike,
                            "cp": cp,
                            "expire_date": expire,
                            "option_close": 0.05,
                            "underlying_close": 2.95,
                            "delta": 0.3 if cp == "C" else -0.3,
                            "gamma": 1.2,
                            "vega": 0.01,
                            "theta": -0.001,
                            "iv": 0.15 + 0.25 * (list(dates).index(dt) / max(len(dates) - 1, 1)),
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
    result = run_short_strangle_backtest(
        und,
        pd.DataFrame(chain_rows),
        pd.DataFrame(oi_rows),
        config=ShortStrangleBacktestConfig(
            require_inside_walls=False,
            require_high_iv=True,
            iv_rank_min=0.6,
            use_kelly_sizing=False,
            lots=1,
            expiry_month="next",
            exit_dte=15,
            roll_before_dte=15,
            max_hold_days=60,
            min_dte=1,
            max_dte=120,
            roll_skip_iv_filter=True,
        ),
    )
    assert result.summary.get("expiryMonth") == "next"
    assert result.summary.get("rollBeforeDte") == 15
    assert result.trades, "expected trades"
    # With May/Jun/Jul listed, early 次月 is June.
    first = result.trades[0]
    assert str(first.get("expireDate", ""))[:10] == "2026-06-24"
    roll_trades = [t for t in result.trades if t.get("reason") == "roll_month"]
    assert roll_trades, "expected at least one roll_month exit before expiry"
    roll_idx = next(i for i, t in enumerate(result.trades) if t.get("reason") == "roll_month")
    later = result.trades[roll_idx + 1 :]
    assert later, "expected reopen after roll"
    assert str(later[0].get("expireDate", ""))[:10] == "2026-07-22"



def test_bs_short_leg_win_probs_otm_strangle():
    spot, call_k, put_k = 3.0, 3.1, 2.9
    t_years, vol = 30 / 365.0, 0.20
    p_call = bs_short_call_win_prob(spot, call_k, t_years, vol)
    p_put = bs_short_put_win_prob(spot, put_k, t_years, vol)
    assert p_call is not None and p_put is not None
    # OTM short legs should have win prob > 0.5 for a mild strangle.
    assert p_call > 0.5
    assert p_put > 0.5
    out = estimate_win_prob_from_bs_legs(
        spot=spot,
        call_strike=call_k,
        put_strike=put_k,
        t_years=t_years,
        vol=vol,
        call_premium=0.04,
        put_premium=0.03,
        mode="credit_weighted",
    )
    assert out is not None
    assert 0.5 < out["win_prob"] < 1.0
    assert abs(out["win_prob"] - (0.04 * out["call_win_prob"] + 0.03 * out["put_win_prob"]) / 0.07) < 1e-9
    both = estimate_win_prob_from_bs_legs(
        spot=spot,
        call_strike=call_k,
        put_strike=put_k,
        t_years=t_years,
        vol=vol,
        mode="both_otm",
    )
    assert both is not None
    assert abs(both["win_prob"] - both["both_otm_prob"]) < 1e-12
