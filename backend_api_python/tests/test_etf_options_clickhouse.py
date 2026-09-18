"""Unit tests for ETF options ClickHouse chain shaping helpers."""

from unittest.mock import patch

from app.services.etf_options_clickhouse import (
    _month_key_from_expire,
    build_strike_chains_by_month,
    list_playback_timestamps,
)


def test_month_key_from_expire_date_string():
    assert _month_key_from_expire("2026-09-23") == "202609"
    assert _month_key_from_expire("2026-12-23 00:00:00") == "202612"


def test_build_strike_chains_by_month_pairs_calls_and_puts():
    rows = [
        {
            "month": "202609",
            "strike": 3.0,
            "cp": "C",
            "close": 0.12,
            "open_interest": 10,
            "iv": 0.2,
            "expire_date": "2026-09-23",
        },
        {
            "month": "202609",
            "strike": 3.0,
            "cp": "P",
            "close": 0.08,
            "open_interest": 7,
            "iv": 0.22,
            "expire_date": "2026-09-23",
        },
        {
            "month": "202612",
            "strike": 3.1,
            "cp": "C",
            "close": 0.2,
            "open_interest": 3,
            "iv": 0.25,
            "expire_date": "2026-12-23",
        },
    ]
    chains = build_strike_chains_by_month(rows)
    assert set(chains) == {"202609", "202612"}
    row = chains["202609"][0]
    assert row["strike"] == 3.0
    assert row["call_mid"] == 0.12
    assert row["put_mid"] == 0.08
    assert row["call_oi"] == 10
    assert row["put_oi"] == 7


def test_list_playback_timestamps_day_uses_quotes_table():
    captured = {}

    def fake_query(sql, timeout=30.0):
        captured["sql"] = sql
        return ["bucket_ts"], [["2026-08-26 14:56:00"], ["2026-08-25 14:55:00"]]

    with patch("app.services.etf_options_clickhouse._ch_query", side_effect=fake_query):
        out = list_playback_timestamps("510300", interval="day", bars=60)

    assert "opt_quotes_bar_1m" in captured["sql"]
    assert "opt_underlying_1m" not in captured["sql"]
    assert out == ["2026-08-25 14:55:00", "2026-08-26 14:56:00"]
