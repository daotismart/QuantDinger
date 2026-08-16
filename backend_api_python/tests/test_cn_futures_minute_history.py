"""Tests for China futures minute-bar history stitching."""

from __future__ import annotations

import pytest

from app.data_sources.cn_futures import CnFuturesDataSource


def _bars(start_ts: int, count: int, step: int = 300, volume: float = 1.0):
    rows = []
    for i in range(count):
        ts = start_ts + i * step
        rows.append(
            {
                "time": ts,
                "open": 100.0 + i,
                "high": 101.0 + i,
                "low": 99.0 + i,
                "close": 100.5 + i,
                "volume": volume,
            }
        )
    return rows


def test_candidate_minute_symbols_include_continuous_and_months():
    src = CnFuturesDataSource()
    cands = src._candidate_minute_symbols("RB0", months=6)
    assert "RB0" in cands
    assert any(c.startswith("RB") and c[-4:].isdigit() for c in cands if c != "RB0")


def test_minute_history_stitches_contract_chunks(monkeypatch):
    monkeypatch.setenv("CN_FUTURES_MARKET_DATA_PROVIDER", "akshare")
    monkeypatch.setenv("CN_FUTURES_MINUTE_STITCH_MONTHS", "4")
    src = CnFuturesDataSource()

    # Two non-overlapping 5m windows.
    chunks = {
        "RB0": _bars(1_700_000_000, 3, step=300, volume=10),
        "RB2505": _bars(1_700_000_000 - 3000, 4, step=300, volume=5),
        "RB2504": _bars(1_700_000_000 - 6000, 4, step=300, volume=5),
    }

    def fake_load(_ak, symbol, period):
        assert period == "5"
        return list(chunks.get(symbol.upper(), []))

    monkeypatch.setattr(src, "_import_akshare", lambda: object())
    monkeypatch.setattr(src, "_load_minute_rows", fake_load)
    monkeypatch.setattr(
        src,
        "_candidate_minute_symbols",
        lambda symbol, months=12: ["RB0", "RB2505", "RB2504"],
    )

    rows = src.get_history("RB0", "5m")
    assert len(rows) == 11
    assert rows[0]["time"] < rows[-1]["time"]
    # Overlap prefers higher volume (RB0 chunk).
    assert rows[-1]["volume"] == 10


def test_short_kline_does_not_require_stitch(monkeypatch):
    monkeypatch.setenv("CN_FUTURES_MARKET_DATA_PROVIDER", "akshare")
    src = CnFuturesDataSource()
    calls = []

    def fake_load(_ak, symbol, period):
        calls.append(symbol)
        return _bars(1_700_000_000, 5)

    monkeypatch.setattr(src, "_import_akshare", lambda: object())
    monkeypatch.setattr(src, "_load_minute_rows", fake_load)
    rows = src.get_kline("RB2509", "5m", limit=5)
    assert len(rows) == 5
    # Only primary dated contract should be hit when prefer_full is false.
    assert calls == ["RB2509"]


def test_3m_resamples_from_1m(monkeypatch):
    monkeypatch.setenv("CN_FUTURES_MARKET_DATA_PROVIDER", "akshare")
    src = CnFuturesDataSource()
    monkeypatch.setattr(src, "_import_akshare", lambda: object())
    # Align to a 3-minute boundary so 6x1m bars collapse to exactly 2 buckets.
    start = 1_700_000_000 - (1_700_000_000 % 180)
    monkeypatch.setattr(
        src,
        "_load_minute_history",
        lambda *_args, **_kwargs: _bars(start, 6, step=60),
    )
    rows = src.get_history("IF2509", "3m")
    assert len(rows) == 2
    assert rows[1]["time"] - rows[0]["time"] == 180
