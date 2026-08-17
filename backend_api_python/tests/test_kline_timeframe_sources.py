"""Contract tests: non-tick K-line timeframe sources, cache TTL, latency bounds."""

from __future__ import annotations

from app.config import CacheConfig
from app.config.data_sources import CCXTConfig
from app.data_sources import asia_stock_kline
from app.data_sources.base import TIMEFRAME_SECONDS
from app.data_sources.crypto import CryptoDataSource
from app.data_sources.forex import _TD_INTERVAL_MAP as FOREX_TD_MAP
from app.data_sources.forex import _YF_TIMEFRAME_MAP as FOREX_YF_MAP
from app.data_sources.futures import FuturesDataSource
from app.data_sources.futures import _TD_INTERVAL_MAP as FUTURES_TD_MAP
from app.data_sources.moex import INTERVAL_MAP as MOEX_INTERVAL_MAP
from app.data_sources.moex import _NATIVE_ISS as MOEX_NATIVE
from app.data_sources.us_stock import USStockDataSource
from app.services.market_data_maint.realtime import RealtimeMaintainer
from app.services.market_data_maint.config import MarketDataMaintSettings


# Expected app-layer cache TTLs (seconds). These bound repeat-read freshness
# after an upstream fetch, not provider latency itself.
EXPECTED_KLINE_CACHE_TTL = {
    "1m": 3,
    "3m": 4,
    "5m": 5,
    "15m": 8,
    "30m": 10,
    "1H": 10,
    "4H": 15,
    "1D": 30,
    "1W": 60,
}

# Closed-bar inherent wait upper bound = one full period.
EXPECTED_CLOSED_BAR_WAIT = {
    "1m": 60,
    "3m": 180,
    "5m": 300,
    "15m": 900,
    "30m": 1800,
    "1H": 3600,
    "4H": 14400,
    "1D": 86400,
    "1W": 604800,
}

STANDARD_TFS = list(EXPECTED_KLINE_CACHE_TTL)


def test_kline_cache_ttl_matrix_matches_latency_doc():
    ttl = CacheConfig.KLINE_CACHE_TTL
    for tf, seconds in EXPECTED_KLINE_CACHE_TTL.items():
        assert ttl[tf] == seconds, f"cache TTL mismatch for {tf}"


def test_closed_bar_wait_matches_timeframe_seconds():
    for tf, seconds in EXPECTED_CLOSED_BAR_WAIT.items():
        assert TIMEFRAME_SECONDS[tf] == seconds


def test_crypto_upstream_timeframes_and_resample_candidates():
    mapping = CCXTConfig.TIMEFRAME_MAP
    for tf in STANDARD_TFS:
        assert tf in mapping
    # Unsupported targets may be rebuilt from finer CCXT candles.
    assert CryptoDataSource._RESAMPLE_CANDIDATES["3m"] == [("1m", 3)]
    assert ("1h", 4) in CryptoDataSource._RESAMPLE_CANDIDATES["4h"]
    assert CryptoDataSource._RESAMPLE_CANDIDATES["1w"] == [("1d", 7)]


def test_traditional_futures_and_forex_upstream_maps():
    for tf in ("1m", "5m", "15m", "30m", "1H", "4H", "1D", "1W"):
        assert tf in FUTURES_TD_MAP
        assert tf in FuturesDataSource.YF_TIMEFRAME_MAP
        assert tf in FOREX_TD_MAP
        assert tf in FOREX_YF_MAP
    # Traditional futures path does not natively list 3m in Twelve Data map.
    assert "3m" not in FUTURES_TD_MAP


def test_us_and_asia_stock_merge_factors_for_synthetic_tfs():
    assert USStockDataSource.INTERVAL_MAP["3m"] == "1m"
    assert USStockDataSource.MERGE_FACTOR_MAP["3m"] == 3
    assert asia_stock_kline._TD_INTERVAL_MAP["3m"] == "1min"
    assert asia_stock_kline._YF_INTERVAL_MAP["3m"] == "1m"
    assert asia_stock_kline._MERGE_FACTOR_MAP["3m"] == 3
    assert asia_stock_kline._YF_INTERVAL_MAP["4H"] == "1h"
    assert asia_stock_kline._MERGE_FACTOR_MAP["4H"] == 4


def test_moex_native_vs_resampled_timeframes():
    assert MOEX_NATIVE == {"1m": 1, "1H": 60, "1D": 24, "1W": 7}
    # Non-native intervals still resolve via finer ISS candles.
    assert MOEX_INTERVAL_MAP["5m"] == 1
    assert MOEX_INTERVAL_MAP["15m"] == 1
    assert MOEX_INTERVAL_MAP["30m"] == 1
    assert MOEX_INTERVAL_MAP["4H"] == 60


def test_tick_aggregation_only_emits_1m_not_higher_tfs():
    settings = MarketDataMaintSettings(
        enabled=True,
        realtime_enabled=True,
        historical_enabled=False,
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
    source = open("/workspace/backend_api_python/app/services/market_data_maint/realtime.py", encoding="utf-8").read()
    assert 'align_bar_time(ts, "1m")' in source
    assert 'timeframe="1m"' in source
    # Higher TFs are not referenced as aggregation targets.
    for tf in ("3m", "5m", "15m", "30m", "1H", "4H", "1D", "1W"):
        assert f'align_bar_time(ts, "{tf}")' not in source
        assert f'timeframe="{tf}"' not in source
    assert maint.settings.realtime_enabled is True


def test_latency_budget_formula_for_completed_bars():
    """Documented practical latency upper bound used by operators.

    completed_bar_freshness <= closed_bar_wait + app_cache_ttl
    (plus unknown provider RTT / rate-limit delay)
    """
    for tf in STANDARD_TFS:
        closed = EXPECTED_CLOSED_BAR_WAIT[tf]
        cache = EXPECTED_KLINE_CACHE_TTL[tf]
        budget = closed + cache
        # Sanity: cache is a small add-on relative to closed-bar wait except 1m.
        if tf == "1m":
            assert budget == 63
        else:
            assert cache < closed
            assert budget == closed + cache


def test_source_chain_docstrings_remain_explicit():
    from app.data_sources import cn_stock, futures, forex

    assert "Twelve Data" in (cn_stock.__doc__ or "")
    assert "Twelve Data" in (futures.__doc__ or "") or "三级降级" in (futures.__doc__ or "")
    assert "Twelve Data" in (forex.__doc__ or "") or "Tiingo" in (forex.__doc__ or "")
