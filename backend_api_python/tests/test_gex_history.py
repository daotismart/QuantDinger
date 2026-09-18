"""GEX playback history: interval/bars + slice/levels alignment."""

from __future__ import annotations

from unittest.mock import patch

from app.services.etf_options_clickhouse import (
    normalize_playback_bars,
    normalize_playback_interval,
)
from app.services.gex_history import build_gex_playback_history, _compute_slice_gex
from datetime import datetime


def test_normalize_playback_interval_aliases():
    assert normalize_playback_interval("1min") == "1m"
    assert normalize_playback_interval("30") == "30m"
    assert normalize_playback_interval("daily") == "day"
    assert normalize_playback_interval("1w") == "week"
    assert normalize_playback_interval("weird") == "day"


def test_normalize_playback_bars_allowed_and_nearest():
    assert normalize_playback_bars(60) == 60
    assert normalize_playback_bars(240) == 240
    assert normalize_playback_bars(50) == 60
    assert normalize_playback_bars(200) == 240
    assert normalize_playback_bars("x") == 60


def test_compute_slice_gex_from_analytics_gamma():
    flat = [
        {
            "month": "202603",
            "strike": 1.4,
            "cp": "C",
            "open_interest": 100,
            "close": 0.05,
            "gamma": 0.2,
            "expire_date": "2026-03-25",
        },
        {
            "month": "202603",
            "strike": 1.4,
            "cp": "P",
            "open_interest": 80,
            "close": 0.04,
            "gamma": 0.15,
            "expire_date": "2026-03-25",
        },
        {
            "month": "202603",
            "strike": 1.5,
            "cp": "C",
            "open_interest": 200,
            "close": 0.02,
            "gamma": 0.25,
            "expire_date": "2026-03-25",
        },
        {
            "month": "202603",
            "strike": 1.5,
            "cp": "P",
            "open_interest": 50,
            "close": 0.08,
            "gamma": 0.18,
            "expire_date": "2026-03-25",
        },
        {
            "month": "202603",
            "strike": 1.6,
            "cp": "C",
            "open_interest": 40,
            "close": 0.01,
            "gamma": 0.1,
            "expire_date": "2026-03-25",
        },
        {
            "month": "202603",
            "strike": 1.6,
            "cp": "P",
            "open_interest": 120,
            "close": 0.12,
            "gamma": 0.12,
            "expire_date": "2026-03-25",
        },
    ]
    out = _compute_slice_gex(flat, underlying=1.45, asof=datetime(2026, 3, 1))
    assert out["gex_distribution"]
    assert out["levels"]
    assert "call_wall" in out["levels"]
    assert out["gex_summary"].get("call_wall") == out["levels"].get("call_wall")


def test_build_gex_playback_history_aligns_slices_and_levels():
    stamps = ["2026-03-10 14:30:00", "2026-03-11 14:30:00", "2026-03-12 14:30:00"]

    def _flat(ts: str):
        return [
            {
                "month": "202603",
                "strike": 1.4,
                "cp": "C",
                "open_interest": 100,
                "close": 0.05,
                "gamma": 0.2,
                "expire_date": "2026-03-25",
                "underlying_price": 1.45,
            },
            {
                "month": "202603",
                "strike": 1.4,
                "cp": "P",
                "open_interest": 80,
                "close": 0.04,
                "gamma": 0.15,
                "expire_date": "2026-03-25",
            },
            {
                "month": "202603",
                "strike": 1.5,
                "cp": "C",
                "open_interest": 200,
                "close": 0.02,
                "gamma": 0.25,
                "expire_date": "2026-03-25",
            },
            {
                "month": "202603",
                "strike": 1.5,
                "cp": "P",
                "open_interest": 50,
                "close": 0.08,
                "gamma": 0.18,
                "expire_date": "2026-03-25",
            },
            {
                "month": "202603",
                "strike": 1.6,
                "cp": "C",
                "open_interest": 40,
                "close": 0.01,
                "gamma": 0.1,
                "expire_date": "2026-03-25",
            },
            {
                "month": "202603",
                "strike": 1.6,
                "cp": "P",
                "open_interest": 120,
                "close": 0.12,
                "gamma": 0.12,
                "expire_date": "2026-03-25",
            },
        ]

    by_ts = {stamps[0]: _flat(stamps[0]), stamps[1]: [], stamps[2]: _flat(stamps[2])}
    underlyings = {stamps[0]: 1.45, stamps[1]: 1.46, stamps[2]: 1.47}

    with patch("app.services.gex_history.etf_options_ch_enabled", return_value=True), patch(
        "app.services.gex_history.ch_ping", return_value=True
    ), patch(
        "app.services.gex_history.list_playback_timestamps", return_value=stamps
    ), patch(
        "app.services.gex_history.fetch_underlying_series", return_value=underlyings
    ), patch(
        "app.services.gex_history.fetch_option_chain_rows_at_timestamps",
        return_value=(by_ts, {"source": "mock"}),
    ):
        data = build_gex_playback_history("588000", interval="day", bars=60)

    assert data["mode"] == "gex_playback"
    assert data["interval"] == "day"
    assert data["bars"] == 60
    assert len(data["slices"]) == 3
    assert len(data["levels_series"]) == 3
    assert [s["ts"] for s in data["slices"]] == stamps
    assert [r["ts"] for r in data["levels_series"]] == stamps
    assert data["slices"][0]["gex_distribution"]
    assert data["slices"][1]["gex_distribution"] == []
    assert data["levels_series"][0]["underlying"] == 1.45
    assert data["levels_series"][1]["call_wall"] is None
    assert data["levels_series"][2]["underlying"] == 1.47
    assert "call_wall" in data["levels_series"][0]
    assert "flip" in data["levels_series"][0]
    assert "pin" in data["levels_series"][0]


def test_build_gex_playback_history_normalizes_exchange_suffix():
    """510300.SH from the UI must query ClickHouse as 510300."""
    stamps = ["2026-03-10 14:30:00"]

    with patch("app.services.gex_history.etf_options_ch_enabled", return_value=True), patch(
        "app.services.gex_history.ch_ping", return_value=True
    ), patch(
        "app.services.gex_history.list_playback_timestamps", return_value=stamps
    ) as list_ts, patch(
        "app.services.gex_history.fetch_underlying_series", return_value={stamps[0]: 4.2}
    ), patch(
        "app.services.gex_history.fetch_option_chain_rows_at_timestamps",
        return_value=({stamps[0]: []}, {"source": "mock"}),
    ):
        data = build_gex_playback_history("510300.SH", interval="day", bars=30)

    list_ts.assert_called_once_with("510300", interval="day", bars=30)
    assert data["root"] == "510300"
    assert data.get("note") != "no playback timestamps in ClickHouse for this underlying/interval"
