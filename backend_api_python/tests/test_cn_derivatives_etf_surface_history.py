"""Tests for ETF options surface history (IV smile playback)."""

from __future__ import annotations

from datetime import datetime

import app.services.gex_history as surface


def test_is_etf_surface_history_chart():
    assert surface.is_etf_surface_history_chart("options.iv")
    assert surface.is_etf_surface_history_chart("options.oi")
    assert surface.is_etf_surface_history_chart("options.tv")
    assert surface.is_etf_surface_history_chart("options.buyerLeverage")
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
    assert out["buyer_leverage"].get("call") is not None
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


def test_build_near_month_iv_klines_close_only_uses_prev_close():
    bounds = [
        {"open_ts": "2026-08-25 14:56:00", "close_ts": "2026-08-25 14:56:00"},
        {"open_ts": "2026-08-26 14:56:00", "close_ts": "2026-08-26 14:56:00"},
    ]
    by_ts = {
        "2026-08-25 14:56:00": [
            {"month": "202609", "strike": 4.5, "iv": 0.20, "expire_date": "2026-09-23"},
        ],
        "2026-08-26 14:56:00": [
            {"month": "202609", "strike": 4.5, "iv": 0.24, "expire_date": "2026-09-23"},
        ],
    }
    underlyings = {
        "2026-08-25 14:56:00": 4.5,
        "2026-08-26 14:56:00": 4.5,
    }
    candles = surface._build_near_month_iv_klines(bounds, by_ts, underlyings)
    assert abs(candles[0]["open"] - 0.20) < 1e-9
    assert abs(candles[0]["close"] - 0.20) < 1e-9
    assert abs(candles[1]["open"] - 0.20) < 1e-9
    assert abs(candles[1]["close"] - 0.24) < 1e-9


def test_compute_surface_slice_uses_stored_iv(monkeypatch):
    chain = [
        {
            "strike": 4.4,
            "call_iv": 0.18,
            "put_iv": 0.19,
            "call_oi": 10,
            "put_oi": 8,
            "expire_date": "2026-09-23",
        },
        {
            "strike": 4.5,
            "call_iv": 0.20,
            "put_iv": 0.21,
            "call_oi": 12,
            "put_oi": 9,
            "expire_date": "2026-09-23",
        },
    ]
    monkeypatch.setattr(surface, "build_strike_chains_by_month", lambda _rows: {"202609": chain})

    def _boom(*_args, **_kwargs):
        raise AssertionError("stored analytics IV should skip Black76")

    monkeypatch.setattr(surface, "compute_gex_raw", _boom)
    out = surface._compute_surface_slice(
        [],
        underlying=4.45,
        asof=datetime(2026, 8, 27),
        multiplier=10000,
        month="all",
        need_iv=True,
        need_oi=False,
        need_tv=False,
        need_max_pain=False,
    )
    assert {p["side"] for p in out["iv_smile"]} == {"call", "put"}
    assert len(out["iv_smile"]) == 4


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


def test_surface_history_flags_are_chart_specific():
    iv = surface.surface_history_flags("options.iv")
    assert iv["need_iv"] and iv["need_iv_klines"]
    assert not iv["need_oi"] and not iv["need_tv"] and not iv["need_max_pain"]
    oi = surface.surface_history_flags("options.oi")
    assert oi["need_oi"] and not oi["need_iv"] and not oi["need_max_pain"]
    mp = surface.surface_history_flags("options.max_pain")
    assert mp["need_max_pain"] and not mp["need_iv"] and not mp["need_tv"]


def test_compute_surface_slice_oi_skips_iv_and_max_pain(monkeypatch):
    chain = [
        {
            "strike": 4.4,
            "call_mid": 0.18,
            "put_mid": 0.05,
            "call_oi": 100,
            "put_oi": 80,
            "expire_date": "2026-09-23",
        }
    ]
    monkeypatch.setattr(surface, "build_strike_chains_by_month", lambda _rows: {"202609": chain})

    def _boom(*_args, **_kwargs):
        raise AssertionError("OI slice should not compute IV / GEX raw")

    monkeypatch.setattr(surface, "compute_gex_raw", _boom)
    out = surface._compute_surface_slice(
        [],
        underlying=4.55,
        asof=datetime(2026, 8, 27),
        multiplier=10000,
        month="all",
        need_iv=False,
        need_oi=True,
        need_tv=False,
        need_max_pain=False,
    )
    assert out["gex_distribution"]
    assert out["iv_smile"] == []
    assert out["max_pain"] is None
    assert out["month_series"][0]["month"] == "202609"
    assert "iv_smile" not in out["month_series"][0]
    assert "max_pain" not in out["month_series"][0]


def _fat_panel():
    smile = [{"strike": 4.5, "iv": 0.2, "side": "call"}]
    curve = [{"strike": 4.5, "pain": 12.0}, {"strike": 4.6, "pain": 9.0}]
    return {
        "current_price": 4.55,
        "underlying": 4.55,
        "iv_smile": smile,
        "gex_distribution": [{"strike": 4.5, "call_oi": 10, "put_oi": 8, "total_oi": 18, "net_oi": 2}],
        "month_series": [
            {
                "month": "202609",
                "T": 0.08,
                "iv_smile": smile,
                "gex_distribution": [{"strike": 4.5, "net_gex": 1}],
                "time_value_yield": {"call": [{"strike": 4.5, "yield": 0.1}], "put": []},
                "buyer_leverage": {"call": [{"strike": 4.5, "leverage": 12.0}], "put": []},
                "max_pain": {"strike": 4.5, "pain": 9.0, "curve": curve},
            }
        ],
        "max_pain": {"strike": 4.5, "pain": 9.0, "curve": curve},
        "time_value_yield": {"call": [{"strike": 4.5, "yield": 0.1}], "put": []},
        "buyer_leverage": {"call": [{"strike": 4.5, "leverage": 12.0}], "put": []},
        "month": "202609",
    }


def test_oi_history_trims_iv_and_max_pain(monkeypatch):
    monkeypatch.setattr(surface, "etf_options_ch_enabled", lambda: False)
    monkeypatch.setattr(surface, "ch_ping", lambda: False)
    monkeypatch.setattr(
        "app.services.cn_derivatives_etf.build_etf_options_panel",
        lambda code, month="all": _fat_panel(),
    )
    hist = surface.build_etf_options_surface_history(
        "510300",
        chart_key="options.oi",
        interval="day",
        bars=30,
    )
    sl = hist["slices"][0]
    assert sl["gex_distribution"]
    assert "iv_smile" not in sl
    assert "max_pain" not in sl
    assert "time_value_yield" not in sl
    assert "buyer_leverage" not in sl
    assert "month_series" not in sl or not sl.get("month_series")
    assert not hist.get("near_month_max_pain_series")


def test_maxpain_history_keeps_curve_and_series(monkeypatch):
    monkeypatch.setattr(surface, "etf_options_ch_enabled", lambda: False)
    monkeypatch.setattr(surface, "ch_ping", lambda: False)
    monkeypatch.setattr(
        "app.services.cn_derivatives_etf.build_etf_options_panel",
        lambda code, month="all": _fat_panel(),
    )
    hist = surface.build_etf_options_surface_history(
        "510300",
        chart_key="options.maxPain",
        interval="day",
        bars=30,
    )
    sl = hist["slices"][0]
    assert sl["max_pain"]["curve"]
    assert sl["month_series"][0]["max_pain"]["curve"]
    assert "iv_smile" not in sl
    assert "time_value_yield" not in sl
    assert "buyer_leverage" not in sl
    series = hist.get("near_month_max_pain_series") or []
    assert len(series) == 1
    assert series[0]["max_pain"] == 4.5
    assert series[0]["month"] == "202609"


def test_buyer_leverage_history_keeps_month_curves(monkeypatch):
    monkeypatch.setattr(surface, "etf_options_ch_enabled", lambda: False)
    monkeypatch.setattr(surface, "ch_ping", lambda: False)
    monkeypatch.setattr(
        "app.services.cn_derivatives_etf.build_etf_options_panel",
        lambda code, month="all": _fat_panel(),
    )
    hist = surface.build_etf_options_surface_history(
        "510300",
        chart_key="options.buyerLeverage",
        interval="day",
        bars=30,
    )
    sl = hist["slices"][0]
    assert sl["buyer_leverage"]["call"][0]["leverage"] == 12.0
    assert sl["month_series"][0]["buyer_leverage"]["call"][0]["strike"] == 4.5
    assert "iv_smile" not in sl
    assert "time_value_yield" not in sl
    assert "max_pain" not in sl
