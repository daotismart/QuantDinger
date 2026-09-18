"""Redis/memory cache for ETF options /history payloads."""

from __future__ import annotations

import app.services.etf_options_clickhouse as ch


def test_history_cache_key_normalizes_interval_and_bars():
    key = ch.etf_options_history_cache_key(
        code6="510050.SH",
        chart="options.ivRank",
        interval="daily",
        bars=50,
        month="ALL",
    )
    assert key == "etf_options_hist:v1:510050:options.ivRank:day:60:all"


def test_cached_etf_options_history_roundtrip(monkeypatch):
    store = {}
    monkeypatch.setattr(ch, "etf_options_history_cache_ttl", lambda: 120)
    monkeypatch.setattr(ch, "_history_cache_get", lambda key: store.get(key))
    monkeypatch.setattr(
        ch,
        "_history_cache_set",
        lambda key, value, ttl: store.__setitem__(key, dict(value)),
    )
    calls = {"n": 0}

    def builder():
        calls["n"] += 1
        return {"root": "510050", "points": [{"iv_rank": 40.0}]}

    first = ch.cached_etf_options_history("etf_options_hist:v1:demo", builder)
    second = ch.cached_etf_options_history("etf_options_hist:v1:demo", builder)
    assert first["cache_hit"] is False
    assert second["cache_hit"] is True
    assert second["points"][0]["iv_rank"] == 40.0
    assert calls["n"] == 1


def test_cached_etf_options_history_skips_empty(monkeypatch):
    store = {}
    monkeypatch.setattr(ch, "etf_options_history_cache_ttl", lambda: 120)
    monkeypatch.setattr(ch, "_history_cache_get", lambda key: store.get(key))
    monkeypatch.setattr(
        ch,
        "_history_cache_set",
        lambda key, value, ttl: store.__setitem__(key, dict(value)),
    )
    calls = {"n": 0}

    def builder():
        calls["n"] += 1
        return {"root": "510050", "points": [], "slices": [], "note": "empty"}

    ch.cached_etf_options_history("etf_options_hist:v1:empty", builder)
    ch.cached_etf_options_history("etf_options_hist:v1:empty", builder)
    assert calls["n"] == 2
    assert store == {}
