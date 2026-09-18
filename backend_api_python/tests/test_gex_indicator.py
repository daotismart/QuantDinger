"""GEX indicator: compute → indicator contract → panel display fields."""

from __future__ import annotations

from app.services.gex_indicator import (
    compute_gex,
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
