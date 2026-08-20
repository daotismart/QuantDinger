"""Tests for local data service and DataSourceFactory local-first integration."""

from __future__ import annotations

from app.data_sources.local_bar import (
    local_kline_sufficient,
    merge_kline_results,
    query_local_kline,
)
from app.services.local_data.config import LocalDataSettings
from app.services.local_data.coverage import build_governance_charts


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


def test_governance_charts_symbol_and_timeframe_coverage():
    watch = [
        {
            "market": "Futures",
            "symbol": "rb2609",
            "timeframe": "1m",
            "exchange_id": "SHFE",
            "lookback_bars": 100,
            "enabled": True,
            "bar_count": 80,
        },
        {
            "market": "Futures",
            "symbol": "rb2609",
            "timeframe": "5m",
            "exchange_id": "SHFE",
            "lookback_bars": 100,
            "enabled": True,
            "bar_count": 0,
        },
        {
            "market": "Futures",
            "symbol": "ag2608",
            "timeframe": "1m",
            "exchange_id": "SHFE",
            "lookback_bars": 100,
            "enabled": True,
            "bar_count": 0,
        },
        {
            "market": "Futures",
            "symbol": "cu2609",
            "timeframe": "1m",
            "exchange_id": "SHFE",
            "lookback_bars": 100,
            "enabled": False,
            "bar_count": 0,
        },
    ]
    inventory = [
        {
            "market": "Futures",
            "symbol": "rb2609",
            "timeframe": "1m",
            "exchange_id": "SHFE",
            "bar_count": 80,
            "min_time": 1_700_000_000,
            "max_time": 1_700_086_400,
        },
        {
            "market": "Futures",
            "symbol": "IF2609",
            "timeframe": "1m",
            "exchange_id": "CFFEX",
            "bar_count": 20,
            "min_time": 1_700_010_000,
            "max_time": 1_700_050_000,
        },
    ]
    out = build_governance_charts(
        watch_rows=watch,
        inventory_rows=inventory,
        symbol_limit=10,
        timeline_limit=10,
    )
    assert out["coverage"]["watchSymbols"] == 2
    assert out["coverage"]["symbolCoveragePct"] == 50.0
    assert out["coverage"]["watchSeries"] == 3
    assert out["coverage"]["timeframeCoveragePct"] == 33.3
    assert out["coverage"]["avgDepthPct"] == 26.7
    assert out["byMarket"][0]["name"] == "Futures"
    assert out["byMarket"][0]["barCount"] == 100
    assert {item["name"] for item in out["byExchange"]} == {"SHFE", "CFFEX"}
    assert out["timeline"][0]["symbol"] == "rb2609"
    assert out["timelineTotal"] == 2
    missing = {item["symbol"] for item in out["coverage"]["missingSymbols"]}
    assert missing == {"AG2608"}


def test_governance_charts_drops_epoch_timeline_rows():
    inventory = [
        {
            "market": "Futures",
            "symbol": "BAD",
            "timeframe": "1w",
            "exchange_id": "SHFE",
            "bar_count": 3,
            "min_time": 604800,
            "max_time": 1_700_000_000,
        },
        {
            "market": "Futures",
            "symbol": "OK",
            "timeframe": "1m",
            "exchange_id": "SHFE",
            "bar_count": 10,
            "min_time": 1_700_000_000,
            "max_time": 1_700_086_400,
        },
    ]
    out = build_governance_charts(watch_rows=[], inventory_rows=inventory)
    assert [row["symbol"] for row in out["timeline"]] == ["OK"]
    assert out["timelineTotal"] == 1


def test_governance_charts_without_watchlist_leaves_coverage_null():
    inventory = [
        {
            "market": "Crypto",
            "symbol": "BTCUSDT",
            "timeframe": "1h",
            "exchange_id": "BINANCE",
            "bar_count": 12,
            "min_time": 1_700_000_000,
            "max_time": 1_700_003_600,
        }
    ]
    out = build_governance_charts(watch_rows=[], inventory_rows=inventory)
    assert out["coverage"]["symbolCoveragePct"] is None
    assert out["coverage"]["timeframeCoveragePct"] is None
    assert out["coverage"]["symbolsWithData"] == 1
    assert out["bySymbol"][0]["symbol"] == "BTCUSDT"
