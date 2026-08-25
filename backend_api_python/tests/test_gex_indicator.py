"""GEX indicator: compute → indicator contract → panel display fields."""

from __future__ import annotations

from app.services.gex_indicator import (
    compute_gex,
    derive_gex_levels,
    panel_fields_from_gex_indicator,
    run_gex_indicator,
)
from app.services.cn_derivatives_etf import _assemble_etf_options_panel


def _sample_chain():
    return [
        {"strike": 2.9, "call_oi": 5, "put_oi": 20, "call_mid": 0.15, "put_mid": 0.02},
        {"strike": 3.0, "call_oi": 25, "put_oi": 12, "call_mid": 0.07, "put_mid": 0.05},
        {"strike": 3.1, "call_oi": 10, "put_oi": 8, "call_mid": 0.03, "put_mid": 0.10},
        {"strike": 3.2, "call_oi": 4, "put_oi": 6, "call_mid": 0.015, "put_mid": 0.16},
    ]


def test_derive_gex_levels_flip_only_on_neg_to_pos_cross():
    """Old bug: prev_cum * cum <= 0 treated +→− (and zero) as Flip."""
    points = [
        {"strike": 2.7, "call_oi": 1, "put_oi": 10, "net_gex": -50.0},
        {"strike": 2.8, "call_oi": 2, "put_oi": 40, "net_gex": -30.0},
        {"strike": 2.9, "call_oi": 5, "put_oi": 20, "net_gex": -10.0},
        {"strike": 3.0, "call_oi": 15, "put_oi": 12, "net_gex": 100.0},  # cum -90 → +10
        {"strike": 3.1, "call_oi": 10, "put_oi": 8, "net_gex": 25.0},
        {"strike": 3.2, "call_oi": 80, "put_oi": 6, "net_gex": -5.0},  # +→− must NOT win
    ]
    levels = derive_gex_levels(points, underlying=2.95)
    assert levels["flip"] == 3.0
    assert levels["call_wall"] == 3.2  # max call OI at/above spot
    assert levels["put_wall"] == 2.8  # max put OI at/below spot
    assert levels["pin"] == 3.2  # 80+6


def test_derive_gex_levels_ignores_pos_to_neg_cross():
    points = [
        {"strike": 2.8, "call_oi": 10, "put_oi": 1, "net_gex": 40.0},
        {"strike": 2.9, "call_oi": 10, "put_oi": 1, "net_gex": 20.0},
        {"strike": 3.0, "call_oi": 10, "put_oi": 1, "net_gex": -80.0},  # +→− only
        {"strike": 3.1, "call_oi": 10, "put_oi": 1, "net_gex": -10.0},
    ]
    levels = derive_gex_levels(points, underlying=2.95)
    assert levels["flip"] is None


def test_derive_gex_levels_ignores_zero_product_false_flip():
    points = [
        {"strike": 2.8, "call_oi": 1, "put_oi": 5, "net_gex": 10.0},
        {"strike": 2.9, "call_oi": 2, "put_oi": 5, "net_gex": -10.0},  # cum → 0
        {"strike": 3.0, "call_oi": 3, "put_oi": 5, "net_gex": -20.0},
        {"strike": 3.1, "call_oi": 4, "put_oi": 5, "net_gex": 30.0},  # true -→+
    ]
    levels = derive_gex_levels(points, underlying=3.0)
    assert levels["flip"] == 3.1


def test_derive_gex_levels_walls_prefer_spot_side_with_fallback():
    points = [
        # Huge call OI below spot should NOT be call wall
        {"strike": 2.5, "call_oi": 1000, "put_oi": 1, "net_gex": -1.0},
        {"strike": 2.8, "call_oi": 10, "put_oi": 50, "net_gex": -2.0},
        {"strike": 3.0, "call_oi": 40, "put_oi": 5, "net_gex": 1.0},
        # Huge put OI above spot should NOT be put wall
        {"strike": 3.3, "call_oi": 5, "put_oi": 900, "net_gex": 2.0},
    ]
    levels = derive_gex_levels(points, underlying=2.95)
    assert levels["call_wall"] == 3.0
    assert levels["put_wall"] == 2.8
    assert levels["pin"] == 2.5


def test_run_gex_indicator_emits_plots_layers_summary():
    ind = run_gex_indicator(
        _sample_chain(),
        underlying=3.02,
        multiplier=10000.0,
        T=30 / 365.0,
        name="GEX",
    )
    assert ind["name"] == "GEX"
    assert ind["meta"]["axis"] == "strike"
    assert len(ind["categories"]) == 4
    assert [p["name"] for p in ind["plots"]] == ["Call GEX", "Put GEX", "Net GEX"]
    assert all(len(p["data"]) == 4 for p in ind["plots"])
    assert ind["summary"]["underlying"] == 3.02
    assert "net_gex" in ind["summary"]
    layer_texts = {layer["text"] for layer in ind["layers"]}
    assert "Price" in layer_texts
    assert ind["calculatedVars"]["points"]


def test_panel_fields_preserve_legacy_keys_and_indicator():
    ind = run_gex_indicator(_sample_chain(), underlying=3.02, multiplier=10000.0, T=0.08)
    fields = panel_fields_from_gex_indicator(ind)
    assert len(fields["gex_distribution"]) == 4
    assert "net_gex" in fields["gex_summary"]
    assert fields["indicators"]["gex"]["name"] == "GEX"
    assert fields["greeks"]


def test_compute_gex_legacy_shape_matches_indicator_points():
    raw = compute_gex(_sample_chain(), underlying=3.02, multiplier=10000.0, T=0.08)
    ind = run_gex_indicator(_sample_chain(), underlying=3.02, multiplier=10000.0, T=0.08)
    assert [p["strike"] for p in raw["points"]] == ind["categories"]
    assert raw["summary"]["net_gex"] == ind["summary"]["net_gex"]


def test_etf_panel_assembly_exposes_indicators_gex():
    chain = _sample_chain()

    def _max_pain(_chain):
        return {"strike": 3.0, "pain": 1.0, "curve": []}

    def _tv(*_a, **_k):
        return {"month": _k.get("month"), "call": [], "put": []}

    panel = _assemble_etf_options_panel(
        code6="510050",
        name_cn="50ETF",
        months=["202508", "202509"],
        selected_months=["202508", "202509"],
        select_all=True,
        underlying=3.02,
        chains_by_month={"202508": chain, "202509": chain},
        month_meta={
            "202508": {"multiplier": 10000.0, "T": 0.08},
            "202509": {"multiplier": 10000.0, "T": 0.16},
        },
        compute_gex=compute_gex,
        compute_max_pain=_max_pain,
        time_value_fn=_tv,
        data_source="test",
    )
    assert "gex" in panel["indicators"]
    assert panel["indicators"]["gex"]["plots"]
    assert panel["gex_distribution"]
    assert panel["gex_summary"]
    assert all("gex" in (row.get("indicators") or {}) for row in panel["month_series"])
