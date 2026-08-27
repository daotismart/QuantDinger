"""Unit tests for ETF options premium / long-short margin capital aggregates."""

from __future__ import annotations

import app.services.cn_derivatives_etf_capital as capital


def test_short_margin_formula_matches_peer_put_sample():
    # Peer CH sample: put K=4.2 S=4.653 px=0.0643 → long=643, short=3583
    ml = capital.initial_margin_long_per_contract(0.0643)
    ms = capital.initial_margin_short_per_contract(
        0.0643, 4.653, 4.2, is_call=False
    )
    assert abs(ml - 643.0) < 1e-6
    assert abs(ms - 3583.0) < 1e-6


def test_compute_option_capital_metrics_long_short_ratio():
    chain = [
        {"strike": 4.5, "call_mid": 0.2, "put_mid": 0.1, "call_oi": 100, "put_oi": 80},
        {"strike": 4.6, "call_mid": 0.12, "put_mid": 0.18, "call_oi": 50, "put_oi": 60},
    ]
    out = capital.compute_option_capital_metrics(
        chain, underlying=4.55, multiplier=10000, margin_rate=0.15
    )
    assert out["premium_total"] > 0
    assert out["margin_long_total"] > 0
    assert out["margin_short_total"] > 0
    # Long margin equals premium for ETF options.
    assert abs(out["margin_long_total"] - out["premium_total"]) < 1e-6
    # Backward-compatible alias points at short margin.
    assert abs(out["margin_total"] - out["margin_short_total"]) < 1e-6
    assert abs(out["premium_total"] - (out["intrinsic_total"] + out["time_value_total"])) < 1e-6
    assert out["long_short_ratio"] is not None
    assert 0 < out["long_short_ratio"] < 2
    assert 0 < out["premium_margin_ratio"] < 2
    assert 0 <= out["time_value_premium_ratio"] <= 1.0001
    assert 0 <= out["intrinsic_premium_ratio"] <= 1.0001
    # Exchange short margin must exceed flat 12% notional in this sample.
    flat12 = out["total_oi"] * 4.55 * 10000 * 0.12
    assert out["margin_short_total"] != flat12


def test_build_capital_curve_by_month():
    chain = [
        {"strike": 1.0, "call_mid": 0.05, "put_mid": 0.04, "call_oi": 10, "put_oi": 12},
    ]
    curve = capital.build_capital_curve_by_month(
        {"202609": chain, "202610": chain},
        underlying=1.0,
        multiplier=10000,
        margin_rate=0.15,
        months=["202609", "202610"],
    )
    assert len(curve["points"]) == 2
    assert curve["total"]["premium_total"] == curve["points"][0]["premium_total"] * 2
    assert curve["total"]["margin_short_total"] == curve["points"][0]["margin_short_total"] * 2
    assert "多头/空头" in (curve.get("note") or "") or "多头保证金" in (curve.get("note") or "")


def test_build_etf_options_capital_history_empty_without_ch(monkeypatch):
    monkeypatch.setattr(
        "app.services.etf_options_clickhouse.etf_options_ch_enabled",
        lambda: False,
    )
    data = capital.build_etf_options_capital_history("510300", bars=30, interval="day")
    assert data["points"] == []
    assert "unavailable" in (data.get("note") or "").lower() or "ClickHouse" in (data.get("note") or "")


def test_etf_time_value_annualized_yield_matches_peer_formula():
    # Peer: AY = (TV × unit / short_margin) × (365.25 / days)
    # put K=4.2 S=4.653 px=0.0643 → short≈3583, TV=0.0643 (OTM)
    chain = [
        {
            "strike": 4.2,
            "put_last": 0.0643,
            "put_oi": 100,
            "call_last": 0.0,
            "call_oi": 0,
        }
    ]
    out = capital.compute_etf_time_value_annualized_yield(
        chain,
        underlying=4.653,
        multiplier=10000,
        margin_rate=0.15,
        T=30 / 365.0,
        month="202609",
    )
    assert out["days_to_expiry"] == 30
    assert len(out["put"]) == 1
    expected = (0.0643 * 10000 / 3583.0) * (365.25 / 30.0)
    assert abs(out["put"][0]["yield"] - expected) < 1e-9
    assert abs(out["market_yield"] - expected) < 1e-9
    assert "OI" in (out.get("market_yield_weight") or "")


def test_combine_market_tv_yields_oi_margin_weights():
    a = capital.compute_etf_time_value_annualized_yield(
        [{"strike": 4.2, "put_last": 0.0643, "put_oi": 10, "call_last": 0, "call_oi": 0}],
        underlying=4.653,
        multiplier=10000,
        margin_rate=0.15,
        T=30 / 365.0,
        month="m1",
    )
    b = capital.compute_etf_time_value_annualized_yield(
        [{"strike": 4.2, "put_last": 0.0643, "put_oi": 90, "call_last": 0, "call_oi": 0}],
        underlying=4.653,
        multiplier=10000,
        margin_rate=0.15,
        T=30 / 365.0,
        month="m2",
    )
    # Same AY per contract → combined equals either
    combo = capital.combine_market_tv_yields([a, b])
    assert combo["market_yield"] is not None
    assert abs(combo["market_yield"] - a["market_yield"]) < 1e-9
    assert "OI" in (combo.get("market_yield_weight") or "")
