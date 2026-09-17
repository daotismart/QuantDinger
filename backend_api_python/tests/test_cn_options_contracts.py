"""Listed China option contracts — parsing, CTP catalog, order ids."""

from __future__ import annotations

from datetime import date

import pandas as pd
import pytest

from app.data_sources.cn_futures import CnFuturesDataSource, resolve_history_symbol
from app.markets.cn_futures import (
    CN_FUTURE_PRODUCTS,
    get_future_product,
    is_cn_futures_option,
    parse_cn_option_symbol,
)
from app.markets.cn_options import (
    canonical_option_symbol,
    format_ctp_option_instrument,
    format_ctp_option_instrument_from_symbol,
    normalize_ctp_option_row,
    parse_cn_option_instrument,
    sina_option_symbol,
)
from app.services.cn_options_chain import catalog_stats, listed_option_catalog
from app.services.ctp_td.gateway import format_instrument_id
from app.services.symbol_master_sync import (
    SymbolMasterRow,
    fetch_cn_futures_options_symbols,
    fetch_cn_index_options_symbols,
    upsert_symbol_master,
)


EXCHANGE_SAMPLES = [
    ("HO2608-C-2500", "CFFEX", "HO2608-C-2500"),
    ("IO2509-C-4000", "CFFEX", "IO2509-C-4000"),
    ("m2609-C-2800", "DCE", "m2609-C-2800"),
    ("a2609-C-3400", "DCE", "a2609-C-3400"),
    ("lc2610-C-100000", "GFEX", "lc2610-C-100000"),
    ("cu2609C100000", "SHFE", "cu2609C100000"),
    ("sc2610C350", "INE", "sc2610C350"),
    ("AP610C10000", "CZCE", "AP610C10000"),
    ("SR509C6200", "CZCE", "SR509C6200"),
]


class TestParseListedOptions:
    @pytest.mark.parametrize("raw,exchange,native", EXCHANGE_SAMPLES)
    def test_parse_and_format_roundtrip(self, raw, exchange, native):
        parsed = parse_cn_option_instrument(raw)
        assert parsed is not None
        assert parsed.exchange == exchange
        assert format_ctp_option_instrument(
            root=parsed.root,
            month=parsed.month,
            call_put=parsed.call_put,
            strike=parsed.strike,
            exchange=exchange,
        ) == native
        assert is_cn_futures_option(raw) is True
        assert get_future_product(raw).exchange == exchange

    def test_hyphenated_search_form_formats_to_native(self):
        assert format_ctp_option_instrument_from_symbol("CU2609-C-100000") == "cu2609C100000"
        assert format_ctp_option_instrument_from_symbol("M2609-C-2800") == "m2609-C-2800"
        assert format_ctp_option_instrument_from_symbol("AP610-C-10000") == "AP610C10000"
        assert format_ctp_option_instrument_from_symbol("SC2610-C-350") == "sc2610C350"

    def test_soybean_one_is_no_longer_rejected(self):
        parsed = parse_cn_option_symbol("a2609-C-3400")
        assert parsed is not None
        assert parsed["root"] == "A"
        assert parsed["option_type"] == "C"
        assert parsed["strike"] == 3400.0

    def test_skips_czce_combo_codes(self):
        assert parse_cn_option_instrument("SR611MSP4700") is None
        assert is_cn_futures_option("SR611MSP4700") is False

    def test_etf_numeric_codes(self):
        from app.markets.cn_futures import resolve_market_category
        from app.markets.cn_options import extract_etf_option_code, is_etf_option_code

        assert is_etf_option_code("10010971") is True
        assert is_etf_option_code("90007051") is True
        assert is_etf_option_code("20260918") is False
        assert parse_cn_option_instrument("10010971") is None
        assert extract_etf_option_code("CNIndexOptions:10010971") == "10010971"
        assert extract_etf_option_code("50ETF购9月2750 [10010971]") == "10010971"
        assert extract_etf_option_code("到期20260918") is None
        assert resolve_market_category("10010971") == "CNIndexOptions"
        assert parse_cn_option_symbol("50ETF购9月2750 [10010971]")["symbol"] == "10010971"

    def test_new_product_roots(self):
        assert {"AD", "OP", "BZ", "PD", "PT", "PL", "PR", "ZC"} <= set(CN_FUTURE_PRODUCTS)
        assert CN_FUTURE_PRODUCTS["SH"].name == "Caustic Soda"
        assert CN_FUTURE_PRODUCTS["A"].has_options is True
        assert CN_FUTURE_PRODUCTS["PB"].has_options is True

    def test_canonical_and_sina_symbols(self):
        parsed = parse_cn_option_instrument("m2609-C-2800")
        assert canonical_option_symbol(parsed) == "M2609-C-2800"
        assert sina_option_symbol(parsed) == "m2609C2800"


class TestCtpInstrumentIds:
    @pytest.mark.parametrize(
        "symbol,exchange,expected",
        [
            ("rb2509", "SHFE", "rb2509"),
            ("TA509", "CZCE", "TA509"),
            ("IF2509", "CFFEX", "IF2509"),
            ("m2609-C-2800", "DCE", "m2609-C-2800"),
            ("M2609-C-2800", "DCE", "m2609-C-2800"),
            ("cu2609C100000", "SHFE", "cu2609C100000"),
            ("CU2609-C-100000", "SHFE", "cu2609C100000"),
            ("HO2608-C-2500", "CFFEX", "HO2608-C-2500"),
            ("AP610C10000", "CZCE", "AP610C10000"),
            ("AP610-C-10000", "CZCE", "AP610C10000"),
            ("sc2610C350", "INE", "sc2610C350"),
            ("lc2610-C-100000", "GFEX", "lc2610-C-100000"),
        ],
    )
    def test_format_instrument_id(self, symbol, exchange, expected):
        assert format_instrument_id(symbol, exchange) == expected


class TestCtpCatalogNormalize:
    def _row(self, **overrides):
        base = {
            "合约ID": "m2609-C-2800",
            "合约名称": "豆粕2609看涨2800",
            "交易所代码": "DCE",
            "品种ID": "m_o",
            "商品类别": 2,
            "合约状态": 1,
            "标的合约": "m2609",
            "执行价": 2800,
            "看涨看跌": "C",
            "合约乘数": 10,
            "最小变动价位": 0.5,
            "到期日": "20260914",
        }
        base.update(overrides)
        return base

    def test_listed_commodity_option(self):
        item = normalize_ctp_option_row(self._row())
        assert item is not None
        assert item["market"] == "CNFuturesOptions"
        assert item["symbol"] == "M2609-C-2800"
        assert item["instrument_id"] == "m2609-C-2800"
        assert item["exchange"] == "DCE"
        assert item["strike"] == 2800.0
        assert item["call_put"] == "C"
        assert item["expire_date"] == "2026-09-14"

    def test_skips_delisted(self):
        assert normalize_ctp_option_row(self._row(**{"合约状态": 0})) is None

    def test_cffex_goes_to_index_options(self):
        item = normalize_ctp_option_row(
            self._row(
                **{
                    "合约ID": "HO2608-C-2500",
                    "合约名称": "上证50股指2608看涨2500",
                    "交易所代码": "CFFEX",
                    "品种ID": "HO",
                    "商品类别": 1,
                    "标的合约": "HO2608",
                }
            )
        )
        assert item["market"] == "CNIndexOptions"
        assert item["symbol"] == "HO2608-C-2500"

    def test_etf_numeric(self):
        item = normalize_ctp_option_row(
            self._row(
                **{
                    "合约ID": "10010971",
                    "合约名称": "50ETF购9月2750",
                    "交易所代码": "SSE",
                    "品种ID": "ETF_O",
                    "商品类别": 1,
                    "标的合约": "510050",
                    "执行价": 2.75,
                    "看涨看跌": "C",
                    "到期日": "20260923",
                    "合约乘数": 10000,
                }
            )
        )
        assert item["market"] == "CNIndexOptions"
        assert item["symbol"] == "10010971"
        assert item["kind"] == "etf"
        assert item["underlying"] == "510050"
        assert item["exchange"] == "SSE"
        assert item["strike"] == 2.75
        assert item["call_put"] == "C"
        assert item["expire_date"] == "2026-09-23"
        assert item["expire_source"] == "ctp"

    def test_etf_numeric_new_ctp_columns(self):
        item = normalize_ctp_option_row(
            {
                "合约ID": "90007051",
                "合约名称": "深证100ETF购9月3100",
                "交易所ID": "SZSE",
                "品种ID": "ETF_O",
                "商品类别": "1",
                "合约状态": "1",
                "标的合约ID": "159901",
                "最小变动价位": 0.0001,
                "合约乘数": 10000,
            }
        )
        assert item is not None
        assert item["exchange"] == "SZSE"
        assert item["underlying"] == "159901"
        assert item["kind"] == "etf"
        assert item["call_put"] == "C"
        assert item["strike"] == 3100.0
        assert item["expire_date"] is not None
        assert item["expire_source"] == "inferred_name"

    def test_infer_etf_expire_fourth_wednesday(self):
        from app.markets.cn_options import fourth_wednesday, infer_etf_option_expire_date

        assert fourth_wednesday(2026, 9).isoformat() == "2026-09-23"
        assert infer_etf_option_expire_date("50ETF购9月2650", as_of=date(2026, 9, 1)) == "2026-09-23"
        assert infer_etf_option_expire_date("50ETF沽12月2700", as_of=date(2026, 9, 1)) == "2026-12-23"

    def test_listed_option_catalog_from_frame(self):
        frame = pd.DataFrame(
            [
                self._row(),
                self._row(**{"合约ID": "cu2609C100000", "交易所代码": "SHFE", "品种ID": "cu_o"}),
                self._row(**{"合约ID": "SR611MSP4700", "交易所代码": "CZCE"}),
                self._row(**{"合约ID": "10010971", "交易所代码": "SSE", "品种ID": "ETF_O"}),
            ]
        )
        rows = listed_option_catalog(frame)
        symbols = {row["symbol"] for row in rows}
        assert "M2609-C-2800" in symbols
        assert "CU2609-C-100000" in symbols
        assert "SR611MSP4700" not in symbols
        assert "10010971" in symbols
        stats = catalog_stats(rows)
        assert stats["total"] == 3
        assert stats["by_exchange"]["DCE"] == 1


class TestSymbolMasterFetch:
    def test_static_roots_still_present(self, monkeypatch):
        monkeypatch.setenv("CN_OPTIONS_CTP_SYNC", "false")
        opt = {row.symbol.upper() for row in fetch_cn_futures_options_symbols()}
        assert {"M", "IO", "CU", "A", "AD"} <= opt
        idx = {row.symbol.upper() for row in fetch_cn_index_options_symbols()}
        assert {"IO", "HO", "MO"} <= idx

    def test_listed_contracts_merge(self, monkeypatch):
        monkeypatch.setenv("CN_OPTIONS_CTP_SYNC", "true")
        listed = [
            SymbolMasterRow(
                "CNFuturesOptions",
                "M2609-C-2800",
                "豆粕2609看涨2800",
                "DCE",
                "CNY",
                "options",
                "m2609-C-2800",
                asset_class="options",
            )
        ]
        monkeypatch.setattr(
            "app.services.symbol_master_sync._listed_option_rows_from_ctp",
            lambda **kwargs: listed,
        )
        symbols = {row.symbol.upper() for row in fetch_cn_futures_options_symbols()}
        assert "M" in symbols
        assert "M2609-C-2800" in symbols

    def test_upsert_deactivates_stale_listed_contracts(self, monkeypatch):
        executed = []

        class FakeCursor:
            def execute(self, sql, params=None):
                executed.append((sql, params))

            def close(self):
                return None

        class FakeDb:
            def cursor(self):
                return FakeCursor()

            def commit(self):
                return None

            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

        monkeypatch.setattr("app.services.symbol_master_sync.get_db_connection", lambda: FakeDb())
        upsert_symbol_master(
            [
                SymbolMasterRow(
                    "CNFuturesOptions",
                    "M2609-C-2800",
                    "豆粕2609看涨2800",
                    "DCE",
                    "CNY",
                    "options",
                    "m2609-C-2800",
                    asset_class="options",
                )
            ]
        )
        deactivate = [
            sql for sql, params in executed if "is_active = 0" in sql and "CNFuturesOptions" in str(params)
        ]
        assert deactivate, executed


class TestOptionHistory:
    def test_resolve_option_uses_sina_compact(self):
        assert resolve_history_symbol("m2509-C-2800") == ("m2509C2800", "option")
        assert resolve_history_symbol("IO2509-C-4000") == ("io2509C4000", "option")
        assert resolve_history_symbol("cu2609C100000") == ("cu2609C100000", "option")

    def test_resolve_etf_option_uses_numeric_code(self):
        assert resolve_history_symbol("10010971") == ("10010971", "etf_option")
        assert resolve_history_symbol("90007051") == ("90007051", "etf_option")

    def test_is_cn_derivative_includes_etf_options(self):
        from app.markets.cn_futures import is_cn_derivative, is_cn_futures_option

        assert is_cn_futures_option("10010971") is True
        assert is_cn_derivative("10010971") is True

    def test_option_daily_prefers_sina_then_underlying(self, monkeypatch):
        monkeypatch.setenv("CN_FUTURES_MARKET_DATA_PROVIDER", "akshare")
        src = CnFuturesDataSource()
        option_frame = pd.DataFrame(
            [
                {"日期": "2026-01-05", "开盘": 10, "最高": 12, "最低": 9, "收盘": 11, "成交量": 100},
                {"日期": "2026-01-06", "开盘": 11, "最高": 13, "最低": 10, "收盘": 12, "成交量": 110},
            ]
        )

        class FakeAk:
            @staticmethod
            def option_commodity_hist_sina(symbol="m2509C2800"):
                assert symbol == "m2509C2800"
                return option_frame

            @staticmethod
            def futures_zh_daily_sina(symbol="M0"):
                raise AssertionError("should not fall back when option history exists")

        monkeypatch.setattr(src, "_import_akshare", lambda: FakeAk)
        rows = src.get_history("m2509-C-2800", "1D")
        assert len(rows) == 2
        assert rows[-1]["close"] == 12.0

    def test_etf_option_daily_uses_sse_sina(self, monkeypatch):
        monkeypatch.setenv("CN_FUTURES_MARKET_DATA_PROVIDER", "akshare")
        src = CnFuturesDataSource()
        option_frame = pd.DataFrame(
            [
                {"日期": "2026-01-05", "开盘": 0.39, "最高": 0.45, "最低": 0.38, "收盘": 0.44, "成交量": 100},
                {"日期": "2026-01-06", "开盘": 0.41, "最高": 0.42, "最低": 0.40, "收盘": 0.41, "成交量": 110},
            ]
        )

        class FakeAk:
            @staticmethod
            def option_sse_daily_sina(symbol="10010971"):
                assert symbol == "10010971"
                return option_frame

            @staticmethod
            def option_commodity_hist_sina(symbol="m2509C2800"):
                raise AssertionError("commodity option API should not be used for ETF codes")

        monkeypatch.setattr(src, "_import_akshare", lambda: FakeAk)
        rows = src.get_history("10010971", "1D")
        assert len(rows) == 2
        assert rows[-1]["close"] == 0.41
