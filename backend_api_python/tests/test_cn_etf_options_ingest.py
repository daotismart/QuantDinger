"""Tests for CN ETF options ingest helpers."""

from __future__ import annotations

from app.markets.cn_options import cn_etf_stock_symbol, etf_benchmark_symbol
from app.services.cn_options_chain import listed_etf_index_catalog, listed_etf_underlying_catalog
from app.services.market_data_maint.cn_etf_options_ingest import (
    select_etf_index_targets,
    select_etf_option_targets,
    select_etf_underlying_targets,
)


def _etf_catalog():
    return [
        {
            "market": "CNIndexOptions",
            "symbol": "10010971",
            "name": "50ETF购9月2750",
            "exchange": "SSE",
            "kind": "etf",
            "underlying": "510050",
        },
        {
            "market": "CNIndexOptions",
            "symbol": "90007051",
            "name": "深证100ETF购9月3100",
            "exchange": "SZSE",
            "kind": "etf",
            "underlying": "159901",
        },
        {
            "market": "CNFuturesOptions",
            "symbol": "M2609-C-2800",
            "kind": "commodity",
        },
    ]


def test_select_etf_option_targets_filters_kind():
    catalog = _etf_catalog()
    targets = select_etf_option_targets(catalog=catalog)
    symbols = {row["symbol"] for row in targets}
    assert symbols == {"10010971", "90007051"}


def test_select_etf_option_targets_exchange_filter():
    catalog = _etf_catalog()
    targets = select_etf_option_targets(catalog=catalog, exchanges=["SSE"])
    assert [row["symbol"] for row in targets] == ["10010971"]


def test_select_etf_underlying_targets_unique_and_board():
    catalog = _etf_catalog()
    option_targets = select_etf_option_targets(catalog=catalog)
    underlyings = select_etf_underlying_targets(option_targets)
    symbols = {row["symbol"] for row in underlyings}
    assert symbols == {"510050.SH", "159901.SZ"}
    assert all(row["market"] == "CNStock" for row in underlyings)


def test_select_etf_index_targets_unique():
    catalog = _etf_catalog()
    option_targets = select_etf_option_targets(catalog=catalog)
    indices = select_etf_index_targets(option_targets, catalog=listed_etf_index_catalog(catalog))
    symbols = {row["symbol"] for row in indices}
    assert "000016.SH" in symbols
    assert "399330.SZ" in symbols
    assert all(row["market"] == "CNStock" for row in indices)


def test_listed_etf_underlying_catalog_from_frame():
    catalog = listed_etf_underlying_catalog(_etf_catalog())
    symbols = {item["symbol"] for item in catalog}
    assert symbols == {"510050.SH", "159901.SZ"}
    assert all(item["asset_class"] == "etf" for item in catalog)


def test_listed_etf_index_catalog_from_frame():
    catalog = listed_etf_index_catalog(_etf_catalog())
    symbols = {item["symbol"] for item in catalog}
    assert "000016.SH" in symbols
    assert "399330.SZ" in symbols
    assert all(item["asset_class"] == "index" for item in catalog)


def test_cn_etf_stock_symbol_board():
    assert cn_etf_stock_symbol("510050") == "510050.SH"
    assert cn_etf_stock_symbol("159901") == "159901.SZ"


def test_etf_benchmark_symbol():
    assert etf_benchmark_symbol("510050") == "000016.SH"
    assert etf_benchmark_symbol("159915") == "399006.SZ"
