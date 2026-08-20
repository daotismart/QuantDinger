"""Tests for local data service and DataSourceFactory local-first integration."""

from __future__ import annotations

from app.data_sources.local_bar import (
    local_kline_sufficient,
    merge_kline_results,
    query_local_kline,
)
from app.services.local_data.config import LocalDataSettings


def test_merge_kline_results_prefers_newer_duplicate_timestamps():
    local = [{"time": 100, "open": 1, "high": 1, "low": 1, "close": 1, "volume": 1}]
    upstream = [{"time": 100, "open": 2, "high": 2, "low": 2, "close": 2, "volume": 2}]
    merged = merge_kline_results(local, upstream, limit=10)
    assert len(merged) == 1
    assert merged[0]["close"] == 2


def test_local_kline_sufficient_respects_coverage_and_stale():
    settings = LocalDataSettings(
        local_read_enabled=True,
        min_coverage=0.8,
        max_stale_sec=900.0,
        prefer_local=True,
        warm_upstream_on_miss=False,
    )
    bars = [
        {"time": int(__import__("time").time()) - 120, "open": 1, "high": 1, "low": 1, "close": 1, "volume": 1}
        for _ in range(80)
    ]
    assert local_kline_sufficient(
        bars,
        limit=100,
        after_time=None,
        before_time=None,
        timeframe="1m",
        settings=settings,
    )
    assert not local_kline_sufficient(
        bars[:10],
        limit=100,
        after_time=None,
        before_time=None,
        timeframe="1m",
        settings=settings,
    )


def test_query_local_kline_empty_without_db(monkeypatch):
    monkeypatch.setattr(
        "app.data_sources.local_bar.repository.query_kline_bars",
        lambda *args, **kwargs: [],
    )
    rows = query_local_kline("Futures", "rb2505", "1m", 10)
    assert rows == []


def test_factory_upstream_only_skips_local(monkeypatch):
    from app.data_sources.factory import DataSourceFactory

    called = {"local": False}

    def _try_local(*args, **kwargs):
        called["local"] = True
        return [], False

    monkeypatch.setattr("app.data_sources.local_bar.try_local_kline", _try_local)

    class _StubSource:
        def get_kline(self, symbol, timeframe, limit, before_time=None, after_time=None):
            return [{"time": 1, "open": 1, "high": 1, "low": 1, "close": 1, "volume": 1}]

    monkeypatch.setattr(DataSourceFactory, "_resolve_source", lambda *a, **k: _StubSource())
    monkeypatch.setattr("app.data_sources.factory.assert_fd_available", lambda *a, **k: None)

    rows = DataSourceFactory.get_kline("Futures", "rb2505", "1m", 5, upstream_only=True)
    assert len(rows) == 1
    assert called["local"] is False
