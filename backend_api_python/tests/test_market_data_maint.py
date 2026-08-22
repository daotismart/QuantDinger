"""Tests for market data continuity / accuracy maintenance."""

from __future__ import annotations

from app.services.market_data_maint.config import WatchSpec, parse_watch_csv
from app.services.market_data_maint.validators import (
    align_bar_time,
    detect_gaps,
    sanitize_bars,
    tick_anomaly,
    validate_bar,
)
from app.services.ctp_md.models import tick_from_depth_market_data
from app.services.market_data_maint.realtime import RealtimeMaintainer
from app.services.market_data_maint.config import MarketDataMaintSettings
from app.services.market_data_maint.service import normalize_watch_spec, resolve_cn_market


def test_normalize_legacy_futures_to_cn_markets():
    assert resolve_cn_market("rb2505", "Futures") == "CNFutures"
    assert resolve_cn_market("IF2509", "Futures") == "CNIndexFutures"
    normalized = normalize_watch_spec(
        WatchSpec(
            market="Futures",
            symbol="rb2505",
            timeframe="1m",
            exchange_id="ctp",
            market_type="futures",
            lookback_bars=1500,
        )
    )
    assert normalized.market == "CNFutures"
    assert normalized.exchange_id == ""
    assert normalized.market_type == "futures"


def test_parse_watch_csv_variants():
    specs = parse_watch_csv(
        "Futures:rb2505:1m@ctp:futures,BTC/USDT:5m@binance:swap,ag2506"
    )
    assert specs[0].market == "Futures"
    assert specs[0].symbol == "rb2505"
    assert specs[0].exchange_id == "ctp"
    assert specs[1].symbol == "BTC/USDT"
    assert specs[1].timeframe == "5m"
    assert specs[2].symbol == "ag2506"
    assert specs[2].market == "Futures"


def test_validate_and_sanitize_bars_reject_bad_ohlc():
    good = {"time": 100, "open": 10, "high": 12, "low": 9, "close": 11, "volume": 1}
    bad = {"time": 160, "open": 10, "high": 9, "low": 8, "close": 11, "volume": 1}
    assert validate_bar(good) == []
    assert any(issue.code == "high_inconsistent" for issue in validate_bar(bad))
    result = sanitize_bars([good, bad, good])
    assert len(result.clean_bars) == 1
    assert len(result.rejected_bars) >= 1


def test_detect_gaps_distinguishes_session_and_data_gaps():
    bars = [
        {"time": 0, "open": 1, "high": 1, "low": 1, "close": 1, "volume": 1},
        {"time": 60, "open": 1, "high": 1, "low": 1, "close": 1, "volume": 1},
        {"time": 240, "open": 1, "high": 1, "low": 1, "close": 1, "volume": 1},  # missing 120,180
        {"time": 240 + 20 * 3600, "open": 1, "high": 1, "low": 1, "close": 1, "volume": 1},
    ]
    gaps = detect_gaps(bars, timeframe="1m", session_gap_seconds=15 * 3600)
    kinds = {gap.kind for gap in gaps}
    assert "data_gap" in kinds
    assert "session_gap" in kinds
    data = next(gap for gap in gaps if gap.kind == "data_gap")
    assert data.missing_bars == 2


def test_tick_anomaly_and_bar_alignment():
    prev = {"last_price": 100.0, "volume": 10}
    assert tick_anomaly(prev, {"last_price": 101.0, "volume": 11}) is None
    spike = tick_anomaly(prev, {"last_price": 150.0, "volume": 11}, spike_ratio=1.15)
    assert spike is not None and spike.code == "tick_price_spike"
    assert align_bar_time(1710000061, "1m") == 1710000060


def test_realtime_maintainer_aggregates_ticks_without_db(monkeypatch):
    settings = MarketDataMaintSettings(
        enabled=True,
        realtime_enabled=True,
        historical_enabled=True,
        realtime_interval_sec=5,
        historical_interval_sec=300,
        tick_stale_after_sec=15,
        tick_retention_days=7,
        bar_retention_days=365,
        max_gap_bars=50,
        session_gap_seconds=54000,
        price_spike_ratio=1.15,
        watchlist_csv="",
        persist_ticks=False,
    )
    maint = RealtimeMaintainer(settings=settings)
    monkeypatch.setattr(maint, "_ensure_ctp_hook", lambda: None)
    tick = tick_from_depth_market_data(
        {"InstrumentID": "rb2505", "LastPrice": 3500, "Volume": 100, "ExchangeID": "SHFE"},
        received_at_ms=1_710_000_060_500,
    )
    maint.on_ctp_tick(tick)
    tick2 = tick_from_depth_market_data(
        {"InstrumentID": "rb2505", "LastPrice": 3505, "Volume": 120, "ExchangeID": "SHFE"},
        received_at_ms=1_710_000_070_500,
    )
    maint.on_ctp_tick(tick2)
    status = maint.status()
    assert status["ticks_seen"] == 2
    assert status["open_bars"] == 1
