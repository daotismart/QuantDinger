"""Unit tests for ETF options ClickHouse chain shaping helpers."""

from unittest.mock import patch

from app.services.etf_options_clickhouse import (
    _atm_iv_series_sql,
    _month_key_from_expire,
    _playback_chain_sql,
    build_strike_chains_by_month,
    list_playback_timestamps,
    playback_fields_for_chart,
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


def test_playback_fields_for_chart():
    assert playback_fields_for_chart("options.ivRank") == "iv"
    assert playback_fields_for_chart("options.oi") == "quotes"
    assert playback_fields_for_chart("options.gex") == "gex"
    assert playback_fields_for_chart("options.capital") == "quotes"


def test_playback_chain_sql_skips_unused_tables():
    ts_sql = "'2026-08-26 14:56:00'"
    iv_sql = _playback_chain_sql("510050", ts_sql, "iv")
    assert "opt_analytics_1m" in iv_sql
    assert "opt_quotes_bar_1m" not in iv_sql
    assert "CROSS JOIN opt_contracts_daily" in iv_sql
    assert "INNER JOIN" in iv_sql

    quotes_sql = _playback_chain_sql("510050", ts_sql, "quotes")
    assert "opt_quotes_bar_1m" in quotes_sql
    assert "opt_analytics_1m" not in quotes_sql

    gex_sql = _playback_chain_sql("510050", ts_sql, "gex")
    assert "opt_quotes_bar_1m" in gex_sql
    assert "opt_analytics_1m" in gex_sql
    assert "gamma" in gex_sql


def test_atm_iv_series_sql_skips_quotes_and_aggregates():
    sql = _atm_iv_series_sql("510050", "'2026-08-26 14:56:00'", month="all")
    assert "opt_analytics_1m" in sql
    assert "opt_quotes_bar_1m" not in sql
    assert "argMin" in sql
    assert "atm_iv" in sql


def test_fetch_option_chain_rows_uses_lookback_argmax(monkeypatch):
    captured = {}

    def fake_query(sql, timeout=35.0):
        captured["sql"] = sql
        return (
            ["contract_code", "contract_id", "strike", "cp", "expire_date", "close", "open_interest", "iv", "delta", "gamma", "vega", "theta", "underlying_price", "quote_ts"],
            [],
        )

    monkeypatch.setattr("app.services.etf_options_clickhouse._ch_query", fake_query)
    from app.services.etf_options_clickhouse import fetch_option_chain_rows

    fetch_option_chain_rows("510300")
    assert "argMax" in captured["sql"]
    assert "INTERVAL" in captured["sql"]
    assert "WITH latest AS" not in captured["sql"]
