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
