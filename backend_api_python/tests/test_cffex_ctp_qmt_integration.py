"""Mainland China futures & futures-options — catalog, data, CTP/QMT, policy."""

from __future__ import annotations

import pytest

from app.data_sources.cn_futures import CnFuturesDataSource
from app.data_sources.factory import DataSourceFactory
from app.data_sources.futures import FuturesDataSource
from app.markets.cn_futures import (
    CN_FUTURE_PRODUCTS,
    CN_FUTURES_EXCHANGES,
    CN_FUTURES_MARKET,
    CN_FUTURES_OPTIONS_MARKET,
    estimate_futures_margin,
    get_future_product,
    is_cn_derivative,
    is_cn_future,
    is_cn_futures_option,
    list_products,
)
from app.markets.cn_index_derivatives import (
    UNSUPPORTED_MESSAGE,
    is_cffex_index_derivative,
    is_cffex_index_future,
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
from app.services.symbol_master_sync import (
    fetch_cn_futures_options_symbols,
    fetch_cn_futures_symbols,
    fetch_cn_index_futures_symbols,
)


INDEX_FUTURE_SAMPLES = ["IF", "IH", "IC", "IM", "IF2509", "IH2509"]
COMMODITY_FUTURE_SAMPLES = ["rb2509", "m2509", "sc2509", "cu2509", "si2509", "TA509", "SR2509"]
OPTION_SAMPLES = ["IO2509-C-4000", "m2509-C-2800", "rb2509P3400", "sc2509-C-580"]


class TestCatalog:
    def test_six_exchanges_present(self):
        assert CN_FUTURES_EXCHANGES == {"CFFEX", "SHFE", "DCE", "CZCE", "INE", "GFEX"}
        exchanges = {p.exchange for p in CN_FUTURE_PRODUCTS.values()}
        assert CN_FUTURES_EXCHANGES <= exchanges

    def test_product_count_covers_mainstream(self):
        assert len(CN_FUTURE_PRODUCTS) >= 60

    @pytest.mark.parametrize("symbol", INDEX_FUTURE_SAMPLES + COMMODITY_FUTURE_SAMPLES)
    def test_detects_futures(self, symbol):
        assert is_cn_future(symbol) is True
        assert is_cn_derivative(symbol) is True
        product = get_future_product(symbol)
        assert product.exchange in CN_FUTURES_EXCHANGES

    @pytest.mark.parametrize("symbol", OPTION_SAMPLES)
    def test_detects_options(self, symbol):
        assert is_cn_futures_option(symbol) is True

    def test_cffex_helpers_still_work(self):
        assert is_cffex_index_future("IF2509") is True
        assert is_cffex_index_derivative("IO2509-C-4000") is True
        assert is_cffex_index_future("rb2509") is False

    def test_margin_for_commodity(self):
        # rb: 3400 * 10 * 1 * 0.09 = 3060
        margin = estimate_futures_margin("rb2509", price=3400, lots=1, direction="long")
        assert margin == pytest.approx(3060.0)

    def test_options_only_products_listed(self):
        opts = list_products(options_only=True)
        roots = {p.root for p in opts}
        assert {"IO", "HO", "MO", "M", "CU", "SC", "SI"} <= roots


class TestMarketModules:
    def test_cn_futures_live(self):
        assert "live" in MARKET_MODULES["CNFutures"].features
        assert "live" in MARKET_MODULES["CNFuturesOptions"].features

    def test_symbol_master_seeded(self):
        fut = {r.symbol.upper() for r in fetch_cn_futures_symbols()}
        assert {"RB", "M", "SC", "CU", "IF", "SI"} <= fut
        opt = {r.symbol.upper() for r in fetch_cn_futures_options_symbols()}
        assert {"M", "IO", "CU"} <= opt
        assert {"IF", "IH", "IC", "IM"} <= {r.symbol.upper() for r in fetch_cn_index_futures_symbols()}


class TestLivePolicyMatrix:
    def test_live_categories(self):
        assert {
            "CNFutures",
            "CNFuturesOptions",
            "CNIndexFutures",
            "CNIndexOptions",
        } <= LIVE_MARKET_CATEGORIES

    def test_ctp_qmt_cover_all_cn_markets(self):
        for market in ("CNFutures", "CNFuturesOptions", "CNIndexFutures", "CNIndexOptions"):
            assert list_supported_brokers_for_market(market) == {"ctp", "qmt"}

    @pytest.mark.parametrize(
        "exchange_id,market,market_type",
        [
            ("ctp", "CNFutures", "futures"),
            ("qmt", "CNFutures", "futures"),
            ("ctp", "CNFuturesOptions", "options"),
            ("qmt", "CNIndexFutures", "futures"),
            ("ctp", "CNIndexOptions", "options"),
        ],
    )
    def test_valid_combos(self, exchange_id, market, market_type):
        validate_strategy_config(
            exchange_id=exchange_id,
            market_category=market,
            market_type=market_type,
            trade_direction="both",
            bot_type="trend",
        )

    def test_grid_rejected(self):
        with pytest.raises(ValueError, match="bot_type='grid'"):
            validate_strategy_config(
                exchange_id="ctp",
                market_category="CNFutures",
                market_type="futures",
                trade_direction="both",
                bot_type="grid",
            )


class TestInstrumentParsing:
    @pytest.mark.parametrize("symbol", INDEX_FUTURE_SAMPLES + COMMODITY_FUTURE_SAMPLES + OPTION_SAMPLES)
    def test_bare_codes_not_usstock(self, symbol):
        assert infer_market(symbol) == ""
        with pytest.raises(InstrumentParseError, match="marketUnknown"):
            parse_instrument(symbol)

    def test_cn_futures_prefix(self):
        spec = parse_instrument("CNFutures:rb2509")
        assert spec.market == CN_FUTURES_MARKET
        assert spec.symbol == "RB2509"

    def test_cn_futures_options_prefix(self):
        spec = parse_instrument("CNFuturesOptions:m2509-C-2800")
        assert spec.market == CN_FUTURES_OPTIONS_MARKET


class TestMarketDataAndMisroute:
    def test_compliance_ticker_across_exchanges(self):
        src = CnFuturesDataSource()
        for symbol, exchange in (("IF2509", "CFFEX"), ("rb2509", "SHFE"), ("sc2509", "INE"), ("si2509", "GFEX")):
            ticker = src.get_ticker(symbol)
            assert ticker["last"] > 0
            assert ticker["exchange"] == exchange

    def test_factory_routes(self):
        assert isinstance(DataSourceFactory.get_source("CNFutures"), CnFuturesDataSource)
        assert isinstance(DataSourceFactory.get_source("CNFuturesOptions"), CnFuturesDataSource)

    def test_generic_futures_refuses_cn(self):
        src = FuturesDataSource()
        with pytest.raises(ValueError, match="CNFutures|CTP/QMT|China futures"):
            src.get_ticker("rb2509")
        with pytest.raises(ValueError, match="CNFutures|CTP/QMT|China futures"):
            src.get_kline("IF2509", "1D", 5)

    def test_message(self):
        assert "CTP" in UNSUPPORTED_MESSAGE


class TestRuntimeAndChannels:
    def test_commodity_open_close(self):
        rt = CffexRuntime(cash=2_000_000)
        rt.place_order(symbol="rb2509", side="long", offset="open", lots=2, price=3400)
        rt.roll_day()
        fill = rt.place_order(symbol="rb2509", side="long", offset="close_yesterday", lots=1, price=3450)
        assert fill.realized_pnl != 0
        assert rt.books["RB2509"].long.yesterday == 1

    def test_option_seller_open(self):
        rt = CffexRuntime(cash=2_000_000)
        fill = rt.place_order(symbol="m2509-C-2800", side="short", offset="open", lots=1, price=3000)
        assert fill.margin_delta > 0
        assert rt.books["M2509-C-2800"].short.today == 1

    def test_insufficient_margin(self):
        rt = CffexRuntime(cash=100)
        with pytest.raises(CffexRuntimeError, match="Insufficient margin"):
            rt.place_order(symbol="sc2509", side="long", offset="open", lots=1, price=580)

    def test_factory_clients(self):
        ctp = create_client(
            {"exchange_id": "ctp", "environment": "demo", "market_scope": "futures"},
            market_type="futures",
        )
        assert isinstance(ctp, CtpClient)
        result = ctp.place_order(symbol="cu2509", side="short", offset="open", lots=1, price=75000)
        assert result.filled == 1

        qmt = create_client(
            {"exchange_id": "qmt", "environment": "demo", "market_scope": "options"},
            market_type="options",
        )
        assert isinstance(qmt, QmtClient)

    def test_live_blocked(self, monkeypatch):
        monkeypatch.delenv("CFFEX_LIVE_TRADING_ENABLED", raising=False)
        with pytest.raises(LiveTradingError, match="disabled"):
            CtpClient(CtpConfig(mode="live", broker_id="9999", user_id="u", password="p", td_front="tcp://x"))
