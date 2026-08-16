"""Capability lock for China A-share equity-index futures / options.

These products trade on CFFEX:
  - Index futures: IF / IH / IC / IM
  - Index options: IO / HO / MO

QuantDinger does not support them for research data routing or live trading.
Tests below pin that boundary and guard against unsafe fallbacks (e.g. treating
``IF`` as a Binance crypto future or ``IF2509`` as a US stock ticker).
"""

from __future__ import annotations

import pytest

from app.data_sources.futures import FuturesDataSource, _TD_FUTURES_SYMBOLS
from app.markets.cn_index_derivatives import (
    UNSUPPORTED_MESSAGE,
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
from app.services.strategy_v2.instruments import InstrumentParseError, infer_market, parse_instrument
from app.services.symbol_master_sync import fetch_futures_symbols


INDEX_FUTURE_SAMPLES = ["IF", "IH", "IC", "IM", "IF2509", "IH2509", "IC2509", "IM2509"]
INDEX_OPTION_SAMPLES = ["IO", "HO", "MO", "IO2509-C-4000", "HO2509P2800", "MO2509-C-5500"]


class TestCffexDetectors:
    @pytest.mark.parametrize("symbol", INDEX_FUTURE_SAMPLES)
    def test_detects_index_futures(self, symbol):
        assert is_cffex_index_future(symbol) is True
        assert is_cffex_index_derivative(symbol) is True

    @pytest.mark.parametrize("symbol", INDEX_OPTION_SAMPLES)
    def test_detects_index_options(self, symbol):
        assert is_cffex_index_option(symbol) is True
        assert is_cffex_index_derivative(symbol) is True

    @pytest.mark.parametrize("symbol", ["ES", "GC", "AAPL", "600519.SH", "BTC/USDT"])
    def test_non_cffex_symbols_are_not_flagged(self, symbol):
        assert is_cffex_index_derivative(symbol) is False


class TestMarketModuleGaps:
    def test_no_options_market_module(self):
        assert "Options" not in MARKET_MODULES

    def test_futures_module_is_research_only(self):
        features = set(MARKET_MODULES["Futures"].features)
        assert "live" not in features
        assert features <= {"research", "backtest", "paper"}

    def test_cnstock_is_equity_only_not_derivatives(self):
        module = MARKET_MODULES["CNStock"]
        assert module.asset_class == "equity"
        assert "live" not in module.features

    def test_symbol_master_has_no_cffex_roots(self):
        symbols = {row.symbol.upper() for row in fetch_futures_symbols()}
        assert symbols.isdisjoint(INDEX_FUTURE_SAMPLES)
        assert "IF" not in symbols
        assert "IO" not in symbols
        # Existing traditional futures remain CME-style roots.
        assert {"ES", "GC", "CL"} <= symbols


class TestLiveTradingBlocked:
    @pytest.mark.parametrize("market", ["Futures", "CNStock", "Options"])
    def test_live_policy_rejects_analysis_only_and_unknown_markets(self, market):
        with pytest.raises(ValueError, match="not supported for live trading|analysis-only"):
            validate_strategy_config(
                exchange_id="",
                market_category=market,
                require_exchange=False,
            )

    def test_no_live_broker_for_futures_or_options(self):
        assert list_supported_brokers_for_market("Futures") == set()
        assert list_supported_brokers_for_market("Options") == set()
        assert LIVE_MARKET_CATEGORIES == {"Crypto", "USStock"}

    def test_ctp_broker_is_unknown(self):
        with pytest.raises(ValueError, match="Unknown exchange_id"):
            validate_strategy_config(
                exchange_id="ctp",
                market_category="Futures",
                market_type="swap",
                trade_direction="both",
            )

    def test_ibkr_cannot_route_cffex_futures_market(self):
        with pytest.raises(ValueError, match="not supported for live trading"):
            validate_strategy_config(
                exchange_id="ibkr",
                market_category="Futures",
                market_type="spot",
                trade_direction="long",
            )


class TestInstrumentParsingSafety:
    @pytest.mark.parametrize("symbol", INDEX_FUTURE_SAMPLES + INDEX_OPTION_SAMPLES)
    def test_bare_cffex_codes_are_not_inferred_as_usstock(self, symbol):
        assert infer_market(symbol) == ""
        with pytest.raises(InstrumentParseError, match="marketUnknown"):
            parse_instrument(symbol)

    def test_explicit_futures_prefix_still_parses_but_is_not_cffex_data(self):
        spec = parse_instrument("Futures:IF2509")
        assert spec.market == "Futures"
        assert spec.symbol == "IF2509"
        assert "IF2509" not in _TD_FUTURES_SYMBOLS


class TestFuturesDataSourceGuard:
    def test_get_ticker_refuses_cffex_instead_of_binance_fallback(self):
        src = FuturesDataSource()
        with pytest.raises(ValueError, match="CFFEX|not supported"):
            src.get_ticker("IF")

    def test_get_kline_refuses_cffex(self):
        src = FuturesDataSource()
        with pytest.raises(ValueError, match="CFFEX|not supported"):
            src.get_kline("IO2509-C-4000", "1D", 10)

    def test_unsupported_message_is_explicit(self):
        assert "CTP/QMT" in UNSUPPORTED_MESSAGE or "CTP" in UNSUPPORTED_MESSAGE
        assert "Options" in UNSUPPORTED_MESSAGE
