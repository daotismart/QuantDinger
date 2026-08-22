"""Tests for CN ETF options ingest helpers."""

from __future__ import annotations

from app.services.cn_options_chain import listed_etf_underlying_catalog
from app.services.market_data_maint.cn_etf_options_ingest import (
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


def test_select_etf_underlying_targets_unique():
    catalog = _etf_catalog()
    option_targets = select_etf_option_targets(catalog=catalog)
    underlyings = select_etf_underlying_targets(option_targets)
    codes = {row["symbol"] for row in underlyings}
    assert codes == {"510050", "159901"}
    assert all(row["market"] == "CNStock" for row in underlyings)


def test_listed_etf_underlying_catalog_from_frame():
    catalog = listed_etf_underlying_catalog(_etf_catalog())
    codes = {item["symbol"] for item in catalog}
    assert codes == {"510050", "159901"}
    assert all(item["asset_class"] == "etf" for item in catalog)
