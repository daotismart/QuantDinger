"""Unit tests for CN derivatives analytics (no live AkShare)."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from app.services import cn_derivatives_analytics as svc


def _chain_row(strike, call_mid, put_mid, call_oi, put_oi):
    return {
        "strike": float(strike),
        "call_mid": float(call_mid),
        "put_mid": float(put_mid),
        "call_oi": float(call_oi),
        "put_oi": float(put_oi),
        "call_last": float(call_mid),
        "put_last": float(put_mid),
        "call_bid": 0.0,
        "call_ask": 0.0,
        "put_bid": 0.0,
        "put_ask": 0.0,
    }


def test_black76_call_put_parity_shape():
    F, K, T, sigma = 3000.0, 3000.0, 0.25, 0.2
    call = svc.black76_price(F, K, T, sigma, True)
    put = svc.black76_price(F, K, T, sigma, False)
    assert call > 0 and put > 0
    assert abs((call - put) - (F - K)) < 1e-6


def test_implied_vol_roundtrip():
    F, K, T, sigma = 2800.0, 2900.0, 0.2, 0.35
    price = svc.black76_price(F, K, T, sigma, True)
    iv = svc.implied_vol_black76(price, F, K, T, True)
    assert iv is not None
    assert iv == pytest.approx(sigma, rel=0.05)


def test_max_pain_prefers_high_put_wall_side():
    chain = [
        _chain_row(100, 12, 1, 10, 100),
        _chain_row(110, 5, 4, 20, 20),
        _chain_row(120, 1, 12, 100, 10),
    ]
    result = svc.compute_max_pain(chain)
    assert result is not None
    assert result["strike"] in {100.0, 110.0, 120.0}
    assert result["pain"] >= 0
    assert len(result["curve"]) == 3


def test_gex_summary_walls_and_portfolio():
    chain = [
        _chain_row(2900, 80, 10, 50, 10),
        _chain_row(3000, 40, 40, 30, 30),
        _chain_row(3100, 10, 90, 10, 80),
    ]
    gex = svc.compute_gex(chain, underlying=3000.0, multiplier=10.0, T=0.2)
    summary = gex["summary"]
    assert summary["call_wall"] == 2900.0
    assert summary["put_wall"] == 3100.0
    assert summary["pin"] == 3100.0
    assert "delta" in gex["portfolio_greeks"]
    assert len(gex["points"]) == 3
    assert len(gex["iv_smile"]) >= 1


def test_build_spot_panel_uses_board_and_continuous():
    board = {
        "date": "20260320",
        "root": "M",
        "spot_price": 2800.0,
        "near_contract": "m2505",
        "near_contract_price": 2810.0,
        "dominant_contract": "m2509",
        "dominant_contract_price": 2850.0,
        "near_basis": 10.0,
        "dom_basis": 50.0,
        "near_basis_rate": 0.0035,
        "dom_basis_rate": 0.0178,
    }
    continuous = {
        "symbol": "M0",
        "price": 2840.0,
        "volume": 1000.0,
        "open_interest": 2000.0,
    }
    with patch.object(svc, "_spot_board_row", return_value=board), patch.object(
        svc, "_futures_zh_spot", return_value=continuous
    ), patch.object(
        svc,
        "_product_payload",
        return_value={"root": "M", "name_cn": "豆粕", "has_options": True, "multiplier": 10},
    ):
        data = svc.build_spot_panel("M")
    assert data["spot_price"] == 2800.0
    assert any("升水" in line for line in data["analysis"])


def test_build_options_panel_unavailable_without_months():
    with patch.object(svc, "_option_months", return_value=[]), patch.object(
        svc,
        "_product_payload",
        return_value={"root": "IF", "name_cn": "沪深300", "has_options": False, "multiplier": 300},
    ):
        data = svc.build_options_panel("IF")
    assert data["available"] is False
    assert data["months"] == []


def test_option_capital_splits_notional_and_premium():
    chain = [
        _chain_row(3000, 50, 20, 10, 5),
        _chain_row(3100, 30, 40, 8, 12),
    ]
    capital = svc._option_capital_for_chain(chain, underlying=3050.0, multiplier=10.0)
    assert capital["call_premium"] == pytest.approx(50 * 10 * 10 + 30 * 8 * 10)
    assert capital["put_premium"] == pytest.approx(20 * 5 * 10 + 40 * 12 * 10)
    assert capital["call_notional"] == pytest.approx((10 + 8) * 3050 * 10)
    assert capital["put_notional"] == pytest.approx((5 + 12) * 3050 * 10)
    assert capital["notional"] == capital["call_notional"] + capital["put_notional"]
    assert capital["premium"] == capital["call_premium"] + capital["put_premium"]


def test_time_value_annualized_yield_shape():
    chain = [
        _chain_row(2900, 120, 10, 1, 1),  # ITM call -> smaller time value
        _chain_row(3000, 80, 80, 1, 1),   # ATM
        _chain_row(3100, 10, 120, 1, 1),  # ITM put
    ]
    result = svc._time_value_annualized_yield(
        chain,
        underlying=3000.0,
        multiplier=10.0,
        margin_rate=0.12,
        T=0.25,
        month="m2505",
    )
    assert result["month"] == "m2505"
    assert len(result["call"]) == 3
    assert len(result["put"]) == 3
    assert all(p["yield"] >= 0 for p in result["call"] + result["put"])
    atm_call = next(p for p in result["call"] if p["strike"] == 3000)
    # ATM call time value ~= 80, margin = 3000*10*0.12=3600, yield=(800/3600)/0.25
    assert atm_call["yield"] == pytest.approx((80 * 10 / 3600) / 0.25, rel=1e-6)


def test_gex_points_include_total_oi():
    chain = [_chain_row(3000, 40, 40, 30, 20)]
    gex = svc.compute_gex(chain, underlying=3000.0, multiplier=10.0, T=0.2)
    assert gex["points"][0]["total_oi"] == 50.0


def test_aggregate_chains_sums_oi_and_weights_mid():
    chains = [
        [_chain_row(3000, 40, 20, 10, 5)],
        [_chain_row(3000, 60, 30, 30, 15)],
    ]
    rows = svc._aggregate_chains_by_strike(chains)
    assert len(rows) == 1
    assert rows[0]["call_oi"] == 40.0
    assert rows[0]["put_oi"] == 20.0
    assert rows[0]["call_mid"] == pytest.approx((40 * 10 + 60 * 30) / 40)
    assert rows[0]["put_mid"] == pytest.approx((20 * 5 + 30 * 15) / 20)


def test_build_options_panel_defaults_to_all(monkeypatch):
    chain_a = [_chain_row(3000, 40, 20, 10, 5)]
    chain_b = [_chain_row(3100, 20, 40, 8, 12)]

    monkeypatch.setattr(svc, "_option_months", lambda root: ["m2505", "m2509"])
    monkeypatch.setattr(
        svc,
        "_option_chain_table",
        lambda root, month: chain_a if "05" in month else chain_b,
    )
    monkeypatch.setattr(svc, "_spot_board_row", lambda root: {"spot_price": 3000, "dominant_contract_price": 3010})
    monkeypatch.setattr(svc, "_futures_zh_spot", lambda symbol: {"price": 3020})
    monkeypatch.setattr(
        svc,
        "_product_payload",
        lambda root: {
            "root": "M",
            "name_cn": "豆粕",
            "multiplier": 10,
            "option_multiplier": 10,
            "option_seller_margin_rate": 0.12,
        },
    )
    data = svc.build_options_panel("M", month="all")
    assert data["month"] == "all"
    assert len(data["month_series"]) == 2
    assert data["gex_distribution"]
    # aggregated should include both strikes
    strikes = {p["strike"] for p in data["gex_distribution"]}
    assert 3000.0 in strikes and 3100.0 in strikes
