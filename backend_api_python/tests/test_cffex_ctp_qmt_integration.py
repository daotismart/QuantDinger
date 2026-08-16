"""CFFEX index futures/options capability — contracts, data, CTP/QMT, policy."""

from __future__ import annotations

import pytest

from app.data_sources.cffex import CffexDataSource
from app.data_sources.factory import DataSourceFactory
from app.data_sources.futures import FuturesDataSource, _TD_FUTURES_SYMBOLS
from app.markets.cn_index_derivatives import (
    CFFEX_MARKET_FUTURES,
    CFFEX_MARKET_OPTIONS,
    UNSUPPORTED_MESSAGE,
    estimate_futures_margin,
    get_future_spec,
    is_cffex_index_derivative,
    is_cffex_index_future,
    is_cffex_index_option,
)
from app.markets.registry import MARKET_MODULES
from app.services.broker_market_policy import (
    LIVE_MARKET_CATEGORIES,
    list_supported_brokers_for_market,
    validate_strategy_config,
)
from app.services.cffex_trading import CffexRuntime, CffexRuntimeError, CtpClient, CtpConfig, QmtClient, QmtConfig
from app.services.live_trading.base import LiveTradingError
from app.services.live_trading.factory import create_client
from app.services.strategy_v2.instruments import InstrumentParseError, infer_market, parse_instrument
from app.services.symbol_master_sync import fetch_cn_index_futures_symbols, fetch_futures_symbols


INDEX_FUTURE_SAMPLES = ["IF", "IH", "IC", "IM", "IF2509", "IH2509", "IC2509", "IM2509"]
INDEX_OPTION_SAMPLES = ["IO", "HO", "MO", "IO2509-C-4000", "HO2509P2800", "MO2509-C-5500"]


class TestCffexDetectorsAndContracts:
    @pytest.mark.parametrize("symbol", INDEX_FUTURE_SAMPLES)
    def test_detects_index_futures(self, symbol):
        assert is_cffex_index_future(symbol) is True
        assert is_cffex_index_derivative(symbol) is True
        spec = get_future_spec(symbol)
        assert spec.exchange == "CFFEX"
        assert spec.multiplier in (200, 300)

    @pytest.mark.parametrize("symbol", INDEX_OPTION_SAMPLES)
    def test_detects_index_options(self, symbol):
        assert is_cffex_index_option(symbol) is True
        assert is_cffex_index_derivative(symbol) is True

    @pytest.mark.parametrize("symbol", ["ES", "GC", "AAPL", "600519.SH", "BTC/USDT"])
    def test_non_cffex_symbols_are_not_flagged(self, symbol):
        assert is_cffex_index_derivative(symbol) is False

    def test_margin_estimate_uses_multiplier(self):
        # IF: 3800 * 300 * 1 * 0.12 = 136800
        margin = estimate_futures_margin("IF2509", price=3800.0, lots=1, direction="long")
        assert margin == pytest.approx(136800.0)


class TestMarketModules:
    def test_cn_index_futures_module_is_live_capable(self):
        module = MARKET_MODULES["CNIndexFutures"]
        assert "live" in module.features
        assert module.asset_class == "futures"

    def test_cn_index_options_module_is_research_paper(self):
        module = MARKET_MODULES["CNIndexOptions"]
        assert "live" not in module.features
        assert module.asset_class == "options"

    def test_generic_futures_remains_research_only(self):
        features = set(MARKET_MODULES["Futures"].features)
        assert "live" not in features

    def test_symbol_master_includes_cffex_roots(self):
        symbols = {row.symbol.upper() for row in fetch_cn_index_futures_symbols()}
        assert {"IF", "IH", "IC", "IM"} <= symbols

    def test_generic_futures_master_still_cme_style(self):
        symbols = {row.symbol.upper() for row in fetch_futures_symbols()}
        assert {"ES", "GC", "CL"} <= symbols
        assert "IF" not in symbols


class TestLivePolicyMatrix:
    def test_live_categories_include_cn_index_futures(self):
        assert "CNIndexFutures" in LIVE_MARKET_CATEGORIES
        assert "CNIndexOptions" not in LIVE_MARKET_CATEGORIES

    def test_ctp_and_qmt_are_live_brokers_for_cn_index_futures(self):
        brokers = list_supported_brokers_for_market("CNIndexFutures")
        assert brokers == {"ctp", "qmt"}

    @pytest.mark.parametrize("exchange_id", ["ctp", "qmt"])
    def test_valid_ctp_qmt_strategy_config(self, exchange_id):
        validate_strategy_config(
            exchange_id=exchange_id,
            market_category="CNIndexFutures",
            market_type="futures",
            trade_direction="both",
            bot_type="trend",
        )

    def test_options_still_analysis_only(self):
        with pytest.raises(ValueError, match="not supported for live trading|analysis-only"):
            validate_strategy_config(
                exchange_id="ctp",
                market_category="CNIndexOptions",
                market_type="options",
                trade_direction="both",
            )

    def test_ibkr_cannot_route_cffex_market(self):
        with pytest.raises(ValueError, match="cannot trade market_category|not supported"):
            validate_strategy_config(
                exchange_id="ibkr",
                market_category="CNIndexFutures",
                market_type="futures",
                trade_direction="long",
            )

    def test_grid_bot_rejected_on_cn_index_futures(self):
        with pytest.raises(ValueError, match="bot_type='grid'"):
            validate_strategy_config(
                exchange_id="ctp",
                market_category="CNIndexFutures",
                market_type="futures",
                trade_direction="both",
                bot_type="grid",
            )


class TestInstrumentParsingSafety:
    @pytest.mark.parametrize("symbol", INDEX_FUTURE_SAMPLES + INDEX_OPTION_SAMPLES)
    def test_bare_cffex_codes_are_not_inferred_as_usstock(self, symbol):
        assert infer_market(symbol) == ""
        with pytest.raises(InstrumentParseError, match="marketUnknown"):
            parse_instrument(symbol)

    def test_explicit_cn_index_futures_prefix_parses(self):
        spec = parse_instrument("CNIndexFutures:IF2509")
        assert spec.market == CFFEX_MARKET_FUTURES
        assert spec.symbol == "IF2509"

    def test_explicit_futures_prefix_still_parses_but_is_not_cffex_data(self):
        spec = parse_instrument("Futures:IF2509")
        assert spec.market == "Futures"
        assert spec.symbol == "IF2509"
        assert "IF2509" not in _TD_FUTURES_SYMBOLS


class TestComplianceMarketData:
    def test_cffex_source_ticker_and_kline(self):
        src = CffexDataSource()
        ticker = src.get_ticker("IF2509")
        assert ticker["last"] > 0
        assert ticker["exchange"] == "CFFEX"
        bars = src.get_kline("IF2509", "1D", 5)
        assert len(bars) == 5
        assert {"time", "open", "high", "low", "close", "volume"} <= set(bars[0])

    def test_factory_routes_cn_index_markets(self):
        src = DataSourceFactory.get_source("CNIndexFutures")
        assert isinstance(src, CffexDataSource)
        opt = DataSourceFactory.get_source("CNIndexOptions")
        assert isinstance(opt, CffexDataSource)

    def test_generic_futures_refuses_cffex(self):
        src = FuturesDataSource()
        with pytest.raises(ValueError, match="CFFEX|CNIndexFutures|CTP/QMT"):
            src.get_ticker("IF")
        with pytest.raises(ValueError, match="CFFEX|CNIndexFutures|CTP/QMT"):
            src.get_kline("IO2509-C-4000", "1D", 10)

    def test_misroute_message_mentions_channels(self):
        assert "CTP" in UNSUPPORTED_MESSAGE
        assert "CNIndexFutures" in UNSUPPORTED_MESSAGE or "CTP/QMT" in UNSUPPORTED_MESSAGE


class TestMarginOpenCloseRuntime:
    def test_open_close_yesterday_and_today(self):
        rt = CffexRuntime(cash=2_000_000)
        open_fill = rt.place_order(symbol="IF2509", side="long", offset="open", lots=2, price=3800)
        assert open_fill.margin_delta > 0
        rt.roll_day()
        # Open one more today lot after rollover.
        rt.place_order(symbol="IF2509", side="long", offset="open", lots=1, price=3810)
        book = rt.books["IF2509"].long
        assert book.yesterday == 2
        assert book.today == 1

        close_yd = rt.place_order(
            symbol="IF2509", side="long", offset="close_yesterday", lots=1, price=3820
        )
        assert close_yd.raw["closed_yesterday"] == 1
        assert rt.books["IF2509"].long.yesterday == 1

        close_td = rt.place_order(
            symbol="IF2509", side="long", offset="close_today", lots=1, price=3825
        )
        assert close_td.raw["closed_today"] == 1
        assert rt.books["IF2509"].long.today == 0

    def test_insufficient_margin_rejected(self):
        rt = CffexRuntime(cash=1000)
        with pytest.raises(CffexRuntimeError, match="Insufficient margin"):
            rt.place_order(symbol="IF2509", side="long", offset="open", lots=1, price=3800)


class TestCtpQmtChannels:
    def test_factory_creates_simulation_clients(self):
        ctp = create_client(
            {"exchange_id": "ctp", "environment": "demo", "market_scope": "futures"},
            market_type="futures",
        )
        qmt = create_client(
            {"exchange_id": "qmt", "environment": "demo", "market_scope": "futures"},
            market_type="futures",
        )
        assert isinstance(ctp, CtpClient)
        assert isinstance(qmt, QmtClient)
        assert ctp.test_connection()["ok"] is True
        assert qmt.test_connection()["ok"] is True

    def test_ctp_simulation_round_trip_order(self):
        client = CtpClient(CtpConfig(mode="simulation", initial_cash=2_000_000))
        result = client.place_order(
            symbol="IH2509", side="short", offset="open", lots=1, price=2600
        )
        assert result.filled == 1
        assert result.exchange_id == "ctp"
        positions = client.get_positions()
        assert positions[0]["side"] == "short"
        assert positions[0]["today"] == 1

    def test_qmt_live_without_flag_is_blocked(self, monkeypatch):
        monkeypatch.delenv("CFFEX_LIVE_TRADING_ENABLED", raising=False)
        with pytest.raises(LiveTradingError, match="disabled|bridge"):
            QmtClient(QmtConfig(mode="live", qmt_path="/opt/qmt"))
