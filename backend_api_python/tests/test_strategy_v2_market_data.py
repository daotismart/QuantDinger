from datetime import datetime, timedelta, timezone

from app.services.strategy_v2 import market_data


def test_market_data_normalizes_numeric_time_series_and_lowercase_timeframe(monkeypatch):
    captured = {}

    def get_kline(**kwargs):
        captured.update(kwargs)
        return [
            {
                "time": 1767225600000,
                "open": 100,
                "high": 102,
                "low": 99,
                "close": 101,
                "volume": 10,
            },
            {
                "time": 1767240000000,
                "open": 101,
                "high": 103,
                "low": 100,
                "close": 102,
                "volume": 11,
            },
        ]

    monkeypatch.setattr(market_data, "_prefer_db_bars", lambda: False)
    monkeypatch.setattr(market_data.DataSourceFactory, "get_kline", get_kline)
    monkeypatch.setattr(market_data._cache, "get", lambda _key: None)
    monkeypatch.setattr(market_data._cache, "put", lambda *_args: None)

    frame = market_data.load_strategy_frame(
        "Crypto",
        "BTC/USDT",
        "4h",
        datetime(2026, 1, 1),
        datetime(2026, 1, 2),
        market_type="spot",
    )

    assert len(frame) == 2
    assert frame.index.tz is None
    assert frame.attrs.get("bar_source") == "upstream"
    assert captured["timeframe"] == "4H"
    assert captured["limit"] < 250
    assert captured["after_time"] == int(datetime(2025, 12, 31, 20, tzinfo=timezone.utc).timestamp())
    assert captured["before_time"] == int(datetime(2026, 1, 2, 4, tzinfo=timezone.utc).timestamp())


def test_four_hour_year_requests_enough_bars(monkeypatch):
    captured = {}

    def get_kline(**kwargs):
        captured.update(kwargs)
        return []

    monkeypatch.setattr(market_data, "_prefer_db_bars", lambda: False)
    monkeypatch.setattr(market_data.DataSourceFactory, "get_kline", get_kline)
    monkeypatch.setattr(market_data._cache, "get", lambda _key: None)

    market_data.load_strategy_frame(
        "Crypto",
        "BTC/USDT",
        "4h",
        datetime(2025, 1, 1),
        datetime(2026, 1, 1),
        market_type="spot",
    )

    assert captured["limit"] > 2400


def test_market_data_normalizes_naive_and_aware_datetimes_to_utc():
    naive = datetime(2026, 7, 19, 4, 14, 13)
    shanghai = timezone(timedelta(hours=8))
    aware = datetime(2026, 7, 19, 12, 14, 13, tzinfo=shanghai)

    normalized_naive = market_data._normalize_utc_datetime(naive)
    normalized_aware = market_data._normalize_utc_datetime(aware)

    assert normalized_naive == datetime(2026, 7, 19, 4, 14, 13, tzinfo=timezone.utc)
    assert normalized_aware == normalized_naive
    assert normalized_naive.timestamp() == normalized_aware.timestamp()


def test_prefers_qd_market_bars_when_coverage_ok(monkeypatch):
    upstream_calls = {"n": 0}
    start = datetime(2025, 1, 1, tzinfo=timezone.utc)
    end = datetime(2025, 4, 1, tzinfo=timezone.utc)
    rows = []
    cursor = start
    while cursor <= end:
        rows.append(
            {
                "time": int(cursor.timestamp()),
                "open": 100.0,
                "high": 101.0,
                "low": 99.0,
                "close": 100.5,
                "volume": 1.0,
            }
        )
        cursor += timedelta(hours=4)

    monkeypatch.setattr(market_data, "_prefer_db_bars", lambda: True)
    monkeypatch.setattr(market_data, "_db_min_coverage", lambda: 0.5)
    monkeypatch.setattr(market_data, "_load_db_bar_rows", lambda **_kwargs: rows)
    monkeypatch.setattr(market_data._cache, "get", lambda _key: None)
    monkeypatch.setattr(market_data._cache, "put", lambda *_args: None)

    def get_kline(**_kwargs):
        upstream_calls["n"] += 1
        return []

    monkeypatch.setattr(market_data.DataSourceFactory, "get_kline", get_kline)

    frame = market_data.load_strategy_frame(
        "CNFutures",
        "RB0",
        "4h",
        start.replace(tzinfo=None),
        end.replace(tzinfo=None),
        market_type="futures",
    )

    assert len(frame) >= 100
    assert frame.attrs.get("bar_source") == "qd_market_bars"
    assert upstream_calls["n"] == 0


def test_falls_back_to_upstream_when_db_empty(monkeypatch):
    captured = {}

    def get_kline(**kwargs):
        captured.update(kwargs)
        return [
            {
                "time": int(datetime(2026, 1, 1, tzinfo=timezone.utc).timestamp()),
                "open": 1,
                "high": 2,
                "low": 0.5,
                "close": 1.5,
                "volume": 9,
            },
            {
                "time": int(datetime(2026, 1, 2, tzinfo=timezone.utc).timestamp()),
                "open": 1.5,
                "high": 2.5,
                "low": 1,
                "close": 2,
                "volume": 10,
            },
        ]

    monkeypatch.setattr(market_data, "_prefer_db_bars", lambda: True)
    monkeypatch.setattr(market_data, "_load_db_bar_rows", lambda **_kwargs: [])
    monkeypatch.setattr(market_data.DataSourceFactory, "get_kline", get_kline)
    monkeypatch.setattr(market_data._cache, "get", lambda _key: None)
    monkeypatch.setattr(market_data._cache, "put", lambda *_args: None)

    frame = market_data.load_strategy_frame(
        "Crypto",
        "BTC/USDT",
        "1d",
        datetime(2026, 1, 1),
        datetime(2026, 1, 2),
        market_type="spot",
    )

    assert len(frame) == 2
    assert frame.attrs.get("bar_source") == "upstream"
    assert captured["timeframe"] == "1D"


def test_falls_back_to_upstream_when_db_raises(monkeypatch):
    def boom(**_kwargs):
        raise RuntimeError("db down")

    def get_kline(**_kwargs):
        return [
            {
                "time": int(datetime(2026, 1, 1, tzinfo=timezone.utc).timestamp()),
                "open": 1,
                "high": 2,
                "low": 0.5,
                "close": 1.5,
                "volume": 9,
            }
        ]

    monkeypatch.setattr(market_data, "_prefer_db_bars", lambda: True)
    monkeypatch.setattr(market_data, "_load_db_bar_rows", boom)
    monkeypatch.setattr(market_data.DataSourceFactory, "get_kline", get_kline)
    monkeypatch.setattr(market_data._cache, "get", lambda _key: None)
    monkeypatch.setattr(market_data._cache, "put", lambda *_args: None)

    frame = market_data.load_strategy_frame(
        "CNFutures",
        "RB0",
        "1d",
        datetime(2026, 1, 1),
        datetime(2026, 1, 1, 12),
        market_type="futures",
    )

    assert len(frame) == 1
    assert frame.attrs.get("bar_source") == "upstream"


def test_db_symbol_candidates_map_options_to_underlying():
    symbols = market_data._db_symbol_candidates("CNFuturesOptions", "m2509-C-2800")
    assert "M0" in {s.upper() for s in symbols}
