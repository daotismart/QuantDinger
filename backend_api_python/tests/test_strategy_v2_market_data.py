from datetime import datetime, timedelta, timezone

from app.services.strategy_v2 import market_data


def _disable_db_bars(monkeypatch):
    monkeypatch.setenv("STRATEGY_V2_PREFER_DB_BARS", "0")
    monkeypatch.setattr(market_data._cache, "get", lambda _key: None)
    monkeypatch.setattr(market_data._cache, "put", lambda *_args: None)


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

    _disable_db_bars(monkeypatch)
    monkeypatch.setattr(market_data.DataSourceFactory, "get_kline", get_kline)

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
    assert captured["timeframe"] == "4H"
    assert captured["limit"] < 250
    assert captured["after_time"] == int(datetime(2025, 12, 31, 20, tzinfo=timezone.utc).timestamp())
    assert captured["before_time"] == int(datetime(2026, 1, 2, 4, tzinfo=timezone.utc).timestamp())


def test_four_hour_year_requests_enough_bars(monkeypatch):
    captured = {}

    def get_kline(**kwargs):
        captured.update(kwargs)
        return []

    _disable_db_bars(monkeypatch)
    monkeypatch.setattr(market_data.DataSourceFactory, "get_kline", get_kline)

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


def test_cnstock_symbol_candidates_include_board_suffix():
    candidates = market_data._db_symbol_candidates("CNStock", "510050")
    assert "510050" in candidates
    assert "510050.SH" in candidates


def test_etf_option_local_bars_used_even_when_range_is_longer(monkeypatch):
    rows = []
    base = int(datetime(2026, 8, 3, tzinfo=timezone.utc).timestamp())
    for index in range(30):
        ts = base + index * 86400
        rows.append(
            {
                "time": ts,
                "open": 0.04,
                "high": 0.05,
                "low": 0.03,
                "close": 0.041,
                "volume": 10,
            }
        )

    monkeypatch.setenv("STRATEGY_V2_PREFER_DB_BARS", "1")
    monkeypatch.setattr(market_data, "_load_db_bar_rows", lambda **_kwargs: rows)
    monkeypatch.setattr(market_data.DataSourceFactory, "get_kline", lambda **_kwargs: [])
    monkeypatch.setattr(market_data._cache, "get", lambda _key: None)
    monkeypatch.setattr(market_data._cache, "put", lambda *_args: None)

    frame = market_data.load_strategy_frame(
        "CNIndexOptions",
        "10010975",
        "1d",
        datetime(2025, 1, 1),
        datetime(2026, 8, 31),
    )

    assert len(frame) >= 5
    assert frame.attrs.get("bar_source") == "qd_market_bars"


def test_partial_local_bars_used_when_upstream_empty(monkeypatch):
    rows = [
        {
            "time": int(datetime(2026, 6, 1, tzinfo=timezone.utc).timestamp()),
            "open": 2.7,
            "high": 2.8,
            "low": 2.6,
            "close": 2.75,
            "volume": 100,
        }
    ]
    monkeypatch.setenv("STRATEGY_V2_PREFER_DB_BARS", "1")
    monkeypatch.setattr(market_data, "_load_db_bar_rows", lambda **_kwargs: rows)
    monkeypatch.setattr(market_data.DataSourceFactory, "get_kline", lambda **_kwargs: [])
    monkeypatch.setattr(market_data._cache, "get", lambda _key: None)
    monkeypatch.setattr(market_data._cache, "put", lambda *_args: None)

    frame = market_data.load_strategy_frame(
        "CNStock",
        "510050",
        "1d",
        datetime(2026, 1, 1),
        datetime(2026, 6, 30),
    )

    assert len(frame) == 1
    assert frame.attrs.get("bar_source") == "qd_market_bars_partial"

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
    assert captured["timeframe"] == "4H"
    assert captured["limit"] < 250
    assert captured["after_time"] == int(datetime(2025, 12, 31, 20, tzinfo=timezone.utc).timestamp())
    assert captured["before_time"] == int(datetime(2026, 1, 2, 4, tzinfo=timezone.utc).timestamp())


def test_four_hour_year_requests_enough_bars(monkeypatch):
    captured = {}

    def get_kline(**kwargs):
        captured.update(kwargs)
        return []

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
