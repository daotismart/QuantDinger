"""Tests for ETF options surface history (IV smile playback)."""

from __future__ import annotations

from datetime import datetime

import app.services.gex_history as surface


def test_is_etf_surface_history_chart():
    assert surface.is_etf_surface_history_chart("options.iv")
    assert surface.is_etf_surface_history_chart("options.oi")
    assert surface.is_etf_surface_history_chart("options.tv")
    assert surface.is_etf_surface_history_chart("options.maxPain")
    assert not surface.is_etf_surface_history_chart("options.gex")
    assert not surface.is_etf_surface_history_chart("options.capital")


def test_compute_surface_slice_builds_iv_smile(monkeypatch):
    chain = [
        {
            "strike": 4.4,
            "call_mid": 0.18,
            "put_mid": 0.05,
            "call_oi": 100,
            "put_oi": 80,
            "call_last": 0.18,
            "put_last": 0.05,
            "expire_date": "2026-09-23",
        },
        {
            "strike": 4.5,
            "call_mid": 0.12,
            "put_mid": 0.09,
            "call_oi": 120,
            "put_oi": 110,
            "call_last": 0.12,
            "put_last": 0.09,
            "expire_date": "2026-09-23",
        },
    ]
    monkeypatch.setattr(
        surface,
        "build_strike_chains_by_month",
        lambda _rows: {"202609": chain},
    )
    out = surface._compute_surface_slice(
        [],
        underlying=4.55,
        asof=datetime(2026, 8, 27),
        multiplier=10000,
        month="all",
    )
    assert out["iv_smile"]
    assert {p["side"] for p in out["iv_smile"]} <= {"call", "put"}
    assert out["month_series"][0]["iv_smile"]
    assert out["gex_distribution"]
    assert out["time_value_yield"].get("call") is not None
    assert out["max_pain"] is not None


def test_surface_history_falls_back_when_ch_unavailable(monkeypatch):
    monkeypatch.setattr(surface, "etf_options_ch_enabled", lambda: False)
    monkeypatch.setattr(surface, "ch_ping", lambda: False)

    smile = [{"strike": 4.5, "iv": 0.2, "side": "call"}]
    month_series = [
        {"month": "202609", "iv_smile": smile, "time_value_yield": {"call": [], "put": []}}
    ]

    def _fake_panel(code, month="all"):
        return {
            "current_price": 4.55,
            "underlying": 4.55,
            "iv_smile": smile,
            "gex_distribution": [],
            "month_series": month_series,
            "max_pain": {"strike": 4.5, "pain": 1.0, "curve": []},
            "time_value_yield": {"call": [], "put": []},
            "month": "202609",
        }

    monkeypatch.setattr(
        "app.services.cn_derivatives_etf.build_etf_options_panel",
        _fake_panel,
    )
    hist = surface.build_etf_options_surface_history(
        "510300",
        chart_key="options.iv",
        interval="day",
        bars=30,
    )
    assert hist["mode"] == "slices"
    assert len(hist["slices"]) == 1
    assert hist["slices"][0]["iv_smile"] == smile
    assert "回退" in (hist.get("note") or "")


def test_near_month_atm_iv_from_smile():
    iv = surface._near_month_atm_iv_from_smile(
        [
            {"strike": 4.4, "iv": 0.18, "side": "call"},
            {"strike": 4.5, "iv": 0.20, "side": "call"},
            {"strike": 4.5, "iv": 0.22, "side": "put"},
            {"strike": 4.6, "iv": 0.25, "side": "call"},
        ],
        4.52,
    )
    assert abs(iv - 0.21) < 1e-9


def test_build_near_month_iv_klines_ohlc():
    bounds = [{"open_ts": "2026-08-26 09:31:00", "close_ts": "2026-08-26 14:56:00", "label": "2026-08-26 14:56:00"}]
    by_ts = {
        "2026-08-26 09:31:00": [
            {"month": "202609", "strike": 4.5, "iv": 0.18, "expire_date": "2026-09-23"},
            {"month": "202609", "strike": 4.5, "iv": 0.20, "expire_date": "2026-09-23"},
        ],
        "2026-08-26 14:56:00": [
            {"month": "202609", "strike": 4.5, "iv": 0.22, "expire_date": "2026-09-23"},
            {"month": "202609", "strike": 4.5, "iv": 0.24, "expire_date": "2026-09-23"},
        ],
    }
    underlyings = {
        "2026-08-26 09:31:00": 4.5,
        "2026-08-26 14:56:00": 4.5,
    }
    candles = surface._build_near_month_iv_klines(bounds, by_ts, underlyings)
    assert len(candles) == 1
    c = candles[0]
    assert c["month"] == "202609"
    assert abs(c["open"] - 0.19) < 1e-9
    assert abs(c["close"] - 0.23) < 1e-9
    assert abs(c["high"] - 0.23) < 1e-9
    assert abs(c["low"] - 0.19) < 1e-9


def test_surface_history_includes_near_month_iv_klines_on_fallback(monkeypatch):
    monkeypatch.setattr(surface, "etf_options_ch_enabled", lambda: False)
    monkeypatch.setattr(surface, "ch_ping", lambda: False)
    smile = [{"strike": 4.5, "iv": 0.2, "side": "call"}]

    def _fake_panel(code, month="all"):
        return {
            "current_price": 4.55,
            "underlying": 4.55,
            "iv_smile": smile,
            "gex_distribution": [],
            "month_series": [{"month": "202609", "iv_smile": smile, "time_value_yield": {"call": [], "put": []}}],
            "max_pain": {"strike": 4.5, "pain": 1.0, "curve": []},
            "time_value_yield": {"call": [], "put": []},
            "month": "202609",
        }

    monkeypatch.setattr(
        "app.services.cn_derivatives_etf.build_etf_options_panel",
        _fake_panel,
    )
    hist = surface.build_etf_options_surface_history(
        "510300",
        chart_key="options.iv",
        interval="day",
        bars=30,
    )
    klines = hist.get("near_month_iv_klines") or []
    assert len(klines) == 1
    assert abs(klines[0]["close"] - 0.2) < 1e-9
