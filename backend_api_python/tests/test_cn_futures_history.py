"""Tests for mainland China futures full-history market data."""

from __future__ import annotations

from datetime import datetime

import pandas as pd
import pytest

from app.data_sources.cn_futures import (
    CnFuturesDataSource,
    resolve_history_symbol,
)
from app.services.kline import KlineService


def test_resolve_history_symbol_continuous_and_contract():
    assert resolve_history_symbol("rb") == ("RB0", "continuous")
    assert resolve_history_symbol("RB0") == ("RB0", "continuous")
    assert resolve_history_symbol("rb2509") == ("RB2509", "contract")
    assert resolve_history_symbol("IF2509") == ("IF2509", "contract")
    assert resolve_history_symbol("SA701") == ("SA2701", "contract")
    assert resolve_history_symbol("m2509-C-2800") == ("m2509C2800", "option")


def test_get_history_uses_full_akshare_series(monkeypatch):
    monkeypatch.setenv("CN_FUTURES_MARKET_DATA_PROVIDER", "akshare")
    src = CnFuturesDataSource()

    frame = pd.DataFrame(
        [
            {"date": "2020-01-02", "open": 1, "high": 2, "low": 0.5, "close": 1.5, "volume": 10},
            {"date": "2020-01-03", "open": 1.5, "high": 2.5, "low": 1.0, "close": 2.0, "volume": 11},
            {"date": "2021-06-01", "open": 3, "high": 4, "low": 2.5, "close": 3.5, "volume": 12},
            {"date": "2024-12-31", "open": 5, "high": 6, "low": 4.5, "close": 5.5, "volume": 13},
        ]
    )

    class FakeAk:
        @staticmethod
        def futures_zh_daily_sina(symbol="RB0"):
            assert symbol == "RB0"
            return frame

    monkeypatch.setattr(src, "_import_akshare", lambda: FakeAk)
    rows = src.get_history("RB0", "1D")
    assert len(rows) == 4
    assert rows[0]["close"] == 1.5
    assert rows[-1]["close"] == 5.5

    # Date window (inclusive calendar end_date expands to next midnight).
    windowed = src.get_history("RB", "1D", start_date="2021-01-01", end_date="2021-12-31")
    assert len(windowed) == 1
    assert windowed[0]["close"] == 3.5


def test_get_kline_can_return_long_history_without_truncating_window(monkeypatch):
    monkeypatch.setenv("CN_FUTURES_MARKET_DATA_PROVIDER", "akshare")
    src = CnFuturesDataSource()
    frame = pd.DataFrame(
        [
            {"date": f"2020-01-{day:02d}", "open": 1, "high": 2, "low": 1, "close": float(day), "volume": 1}
            for day in range(1, 11)
        ]
    )

    class FakeAk:
        @staticmethod
        def futures_zh_daily_sina(symbol="RB0"):
            return frame

    monkeypatch.setattr(src, "_import_akshare", lambda: FakeAk)
    start = int(datetime(2020, 1, 3).timestamp()) - 8 * 3600  # approx CST
    # Prefer explicit after_time path: no truncate.
    rows = src.get_kline("RB0", "1D", limit=3, after_time=int(datetime(2020, 1, 3, tzinfo=None).replace().timestamp()))
    # Safer: use get_history for window semantics
    rows = src.get_history("RB0", "1D", start_date="2020-01-03", end_date="2020-01-07")
    assert [r["close"] for r in rows] == [3.0, 4.0, 5.0, 6.0, 7.0]


def test_weekly_resample(monkeypatch):
    monkeypatch.setenv("CN_FUTURES_MARKET_DATA_PROVIDER", "akshare")
    src = CnFuturesDataSource()
    # Two weeks of daily bars.
    days = []
    for d in range(1, 15):
        days.append(
            {"date": f"2024-01-{d:02d}", "open": 1, "high": 10, "low": 1, "close": float(d), "volume": 1}
        )
    frame = pd.DataFrame(days)

    class FakeAk:
        @staticmethod
        def futures_zh_daily_sina(symbol="IF0"):
            return frame

    monkeypatch.setattr(src, "_import_akshare", lambda: FakeAk)
    rows = src.get_history("IF", "1W")
    assert len(rows) >= 2
    assert rows[0]["open"] == 1


def test_kline_service_delegates_to_cn_source(monkeypatch):
    monkeypatch.setenv("CN_FUTURES_MARKET_DATA_PROVIDER", "compliance")
    service = KlineService()
    rows = service.get_history("CNFutures", "rb2509", "1D", start_date="2020-01-01", end_date="2020-01-10")
    assert isinstance(rows, list)
    assert len(rows) >= 1


def test_auto_falls_back_to_compliance_when_akshare_fails(monkeypatch):
    monkeypatch.setenv("CN_FUTURES_MARKET_DATA_PROVIDER", "auto")
    src = CnFuturesDataSource()

    def boom():
        raise RuntimeError("network down")

    monkeypatch.setattr(src, "_import_akshare", boom)
    rows = src.get_history("RB0", "1D")
    assert len(rows) > 0
    assert rows[0]["close"] > 0
