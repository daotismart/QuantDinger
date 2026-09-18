"""Tests for catalog-wide CN futures history ingest."""

from __future__ import annotations

from app.markets.cn_futures import (
    CN_FUTURES_MARKET,
    CN_INDEX_FUTURES_MARKET,
    list_continuous_history_targets,
)
from app.services.market_data_maint.cn_futures_ingest import (
    ingest_cn_futures_history,
    select_history_targets,
)
from app.services.market_data_maint.config import parse_watch_csv
from app.services.market_data_maint.repository import INTRADAY_PURGE_TIMEFRAMES


def test_continuous_universe_covers_six_exchanges_and_skips_index_options():
    rows = list_continuous_history_targets()
    exchanges = {row["exchange"] for row in rows}
    assert exchanges == {"CFFEX", "SHFE", "DCE", "CZCE", "INE", "GFEX"}
    roots = {row["root"] for row in rows}
    assert "RB" in roots and "IF" in roots and "SC" in roots and "SI" in roots
    assert "IO" not in roots and "HO" not in roots and "MO" not in roots
    assert all(row["symbol"].endswith("0") for row in rows)
    assert any(row["market"] == CN_INDEX_FUTURES_MARKET for row in rows)
    assert any(row["market"] == CN_FUTURES_MARKET for row in rows)
    assert len(rows) >= 60


def test_select_history_targets_filters_exchange_and_symbol():
    shfe = select_history_targets(exchanges=["SHFE"])
    assert shfe and all(row["exchange"] == "SHFE" for row in shfe)
    rb = select_history_targets(symbols=["rb", "IF0"])
    assert {row["symbol"] for row in rb} == {"RB0", "IF0"}


def test_parse_watch_csv_accepts_cn_futures_market():
    specs = parse_watch_csv("CNFutures:RB0,CNIndexFutures:IF0:1D")
    assert specs[0].market == "CNFutures"
    assert specs[0].symbol == "RB0"
    assert specs[1].market == "CNIndexFutures"
    assert specs[1].timeframe == "1D"


def test_intraday_purge_does_not_include_daily_or_weekly():
    lowered = {tf.lower() for tf in INTRADAY_PURGE_TIMEFRAMES}
    assert "1d" not in lowered
    assert "1w" not in lowered
    assert "1m" in lowered


def test_ingest_persists_validated_daily_and_derived_weekly(monkeypatch):
    daily = [
        {"time": 1_704_067_200 + i * 86400, "open": 10 + i, "high": 11 + i, "low": 9 + i, "close": 10.5 + i, "volume": 1}
        for i in range(10)
    ]

    class FakeSrc:
        def get_history(self, symbol, timeframe):
            assert timeframe == "1D"
            return list(daily)

        def _resample(self, rows, seconds):
            assert seconds > 86400
            return [
                {
                    "time": rows[0]["time"],
                    "open": rows[0]["open"],
                    "high": max(r["high"] for r in rows),
                    "low": min(r["low"] for r in rows),
                    "close": rows[-1]["close"],
                    "volume": sum(r["volume"] for r in rows),
                }
            ]

    written = []
    watches = []

    def fake_upsert(spec, bars, *, source, quality_flags):
        written.append((spec.market, spec.symbol, spec.timeframe, len(bars), source))
        return len(bars)

    monkeypatch.setattr(
        "app.services.market_data_maint.cn_futures_ingest.repository.upsert_bars",
        fake_upsert,
    )
    monkeypatch.setattr(
        "app.services.market_data_maint.cn_futures_ingest.repository.upsert_watch_specs",
        lambda specs: watches.extend(specs) or len(specs),
    )

    summary = ingest_cn_futures_history(
        timeframes=["1D", "1W"],
        persist=True,
        symbols=["RB0"],
        retries=1,
        src=FakeSrc(),
        sleeper=lambda _s: None,
    )
    assert summary["status"] == "success"
    assert summary["ok_symbols"] == 1
    assert summary["upserted_rows"] == 11
    assert ("CNFutures", "RB0", "1D", 10, "cn_futures_history") in written
    assert ("CNFutures", "RB0", "1W", 1, "cn_futures_history") in written
    assert {w.timeframe for w in watches} == {"1D", "1W"}


def test_ingest_records_failures_without_compliance_fallback(monkeypatch):
    class BoomSrc:
        def get_history(self, symbol, timeframe):
            raise RuntimeError("sina down")

    summary = ingest_cn_futures_history(
        timeframes=["1D"],
        persist=False,
        symbols=["RB0"],
        retries=2,
        src=BoomSrc(),
        sleeper=lambda _s: None,
    )
    assert summary["status"] == "failed"
    assert summary["errors"]
    assert "sina down" in summary["errors"][0]["error"]


def test_ingest_derives_intraday_from_one_minute(monkeypatch):
    minute = [
        {
            "time": 1_710_000_000 + i * 60,
            "open": 10 + i,
            "high": 11 + i,
            "low": 9 + i,
            "close": 10.5 + i,
            "volume": 2,
        }
        for i in range(15)
    ]

    class FakeSrc:
        def get_history(self, symbol, timeframe):
            assert timeframe == "1m"
            return list(minute)

        def _resample(self, rows, seconds):
            return [
                {
                    "time": rows[0]["time"],
                    "open": rows[0]["open"],
                    "high": max(r["high"] for r in rows),
                    "low": min(r["low"] for r in rows),
                    "close": rows[-1]["close"],
                    "volume": sum(r["volume"] for r in rows),
                }
            ]

    written = []
    monkeypatch.setattr(
        "app.services.market_data_maint.cn_futures_ingest.repository.upsert_bars",
        lambda spec, bars, *, source, quality_flags: written.append(spec.timeframe) or len(bars),
    )
    monkeypatch.setattr(
        "app.services.market_data_maint.cn_futures_ingest.repository.upsert_watch_specs",
        lambda specs: len(specs),
    )
    monkeypatch.setattr(
        "app.services.market_data_maint.cn_futures_ingest.repository.count_bars",
        lambda spec: 0,
    )

    summary = ingest_cn_futures_history(
        timeframes=["1m", "5m", "1H"],
        persist=True,
        symbols=["RB0"],
        retries=1,
        src=FakeSrc(),
        sleeper=lambda _s: None,
        watch_intraday=False,
    )
    assert summary["status"] == "success"
    assert summary["watch_written"] == 0
    assert written == ["1m", "5m", "1H"]
    assert summary["results"][0]["timeframes"]["5m"]["derived_from"] == "1m"


def test_ingest_derive_only_from_stored_1m(monkeypatch):
    minute = [
        {
            "time": 1_710_000_000 + i * 60,
            "open": 10 + i,
            "high": 11 + i,
            "low": 9 + i,
            "close": 10.5 + i,
            "volume": 2,
        }
        for i in range(20)
    ]

    class FakeSrc:
        def get_history(self, symbol, timeframe):
            raise AssertionError("derive_only must not fetch")

        def _resample(self, rows, seconds):
            return [
                {
                    "time": rows[0]["time"],
                    "open": rows[0]["open"],
                    "high": max(r["high"] for r in rows),
                    "low": min(r["low"] for r in rows),
                    "close": rows[-1]["close"],
                    "volume": sum(r["volume"] for r in rows),
                }
            ]

    written = []
    monkeypatch.setattr(
        "app.services.market_data_maint.cn_futures_ingest.repository.load_bars",
        lambda spec, limit=5000: list(minute) if spec.timeframe == "1m" else [],
    )
    monkeypatch.setattr(
        "app.services.market_data_maint.cn_futures_ingest.repository.upsert_bars",
        lambda spec, bars, *, source, quality_flags: written.append(spec.timeframe) or len(bars),
    )
    monkeypatch.setattr(
        "app.services.market_data_maint.cn_futures_ingest.repository.upsert_watch_specs",
        lambda specs: 0,
    )

    summary = ingest_cn_futures_history(
        timeframes=["3m", "4H"],
        persist=True,
        symbols=["RB0"],
        derive_only=True,
        src=FakeSrc(),
        sleeper=lambda _s: None,
        register_watch=False,
    )
    assert summary["status"] == "success"
    assert summary["derive_only"] is True
    assert set(written) == {"3m", "4H"}
