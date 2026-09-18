"""Tests for SSE/SZSE ETF option chain quote parsing."""

import pandas as pd

from app.services.cn_derivatives_etf import (
    _apply_sse_option_quote,
    _empty_etf_option_chain_bucket,
    _etf_option_chain_from_current_day,
    _etf_option_exchange,
    _normalize_option_listing_row,
    _normalize_sse_option_month_key,
    _sse_option_spot_values,
)


def _mid(bid, ask, last):
    if bid > 0 and ask > 0:
        return (bid + ask) / 2.0
    if last > 0:
        return last
    return max(bid, ask, 0.0)


def _safe_float(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def test_normalize_sse_option_month_key():
    assert _normalize_sse_option_month_key("202608") == "2608"
    assert _normalize_sse_option_month_key("2608") == "2608"


def test_etf_option_exchange_routes_szse_codes():
    assert _etf_option_exchange("159915") == "SZSE"
    assert _etf_option_exchange("510050") == "SSE"
    assert _etf_option_exchange("588000") == "SSE"


def test_normalize_option_listing_row_szse_columns():
    row = {
        "标的证券简称(代码)": "创业板ETF(159915)",
        "合约代码": "159915C2609M002950",
        "合约编码": 90007069,
        "行权价": 2.95,
        "合约类型": "认购",
        "合约单位": 10000,
        "合约总持仓": 1784.0,
        "前结算价": 0.55,
        "行权日": pd.Timestamp("2026-09-24"),
    }
    norm = _normalize_option_listing_row(row, "SZSE")
    assert norm["underlying_col"] == "创业板ETF(159915)"
    assert norm["contract_id"] == "159915C2609M002950"
    assert norm["code"] == "90007069"
    assert norm["opt_type"] == "认购"


def test_sse_option_spot_values_reads_oi_and_level_one_quotes():
    frame = pd.DataFrame(
        [
            {"字段": "买价", "值": ""},
            {"字段": "申买价一", "值": "0.2415"},
            {"字段": "卖价", "值": ""},
            {"字段": "申卖价一", "值": "0.2464"},
            {"字段": "最新价", "值": "0.2453"},
            {"字段": "持仓量", "值": "386"},
        ]
    )
    quote = _sse_option_spot_values(frame, _safe_float, _mid)
    assert quote["oi"] == 386.0
    assert quote["bid"] == 0.2415
    assert quote["ask"] == 0.2464
    assert quote["last"] == 0.2453
    assert quote["mid"] == (0.2415 + 0.2464) / 2.0


def test_apply_sse_option_quote_uses_listing_oi_fallback():
    bucket = _empty_etf_option_chain_bucket(2.95)
    _apply_sse_option_quote(
        bucket,
        "认购",
        {"bid": 0.6, "ask": 0.62, "last": 0.61, "mid": 0.61, "oi": 0.0},
        listing_oi=1784.0,
    )
    assert bucket["call_oi"] == 1784.0


def test_etf_row_from_spot_parses_sina_symbol_codes():
    from app.services.cn_derivatives_etf import _etf_row_from_spot

    frame = pd.DataFrame(
        [
            {
                "代码": "sh510050",
                "名称": "上证50ETF华夏",
                "最新价": 2.993,
                "成交量": 1000,
                "成交额": 2000,
                "买入": 2.992,
                "卖出": 2.993,
            },
            {
                "代码": "sz159915",
                "名称": "创业板ETF易方达",
                "最新价": 3.56,
                "成交量": 500,
                "成交额": 800,
            },
        ]
    )
    sh = _etf_row_from_spot(frame, "510050", _safe_float)
    sz = _etf_row_from_spot(frame, "159915", _safe_float)
    assert sh["price"] == 2.993
    assert sh["bid"] == 2.992
    assert sz["price"] == 3.56


def test_etf_option_chain_from_current_day_merges_sse_quotes_per_strike():
    current_day = pd.DataFrame(
        [
            {
                "标的券名称及代码": "50ETF(510050)",
                "合约交易代码": "510050C2608M02750",
                "行权价": 2.75,
                "类型": "认购",
                "合约编码": "10012127",
            },
            {
                "标的券名称及代码": "50ETF(510050)",
                "合约交易代码": "510050P2608M02750",
                "行权价": 2.75,
                "类型": "认沽",
                "合约编码": "10012128",
            },
        ]
    )

    def make_spot(code):
        if code == "10012127":
            rows = [
                {"字段": "买价", "值": "0.24"},
                {"字段": "卖价", "值": "0.25"},
                {"字段": "最新价", "值": "0.245"},
                {"字段": "持仓量", "值": "120"},
            ]
        else:
            rows = [
                {"字段": "买价", "值": "0.01"},
                {"字段": "卖价", "值": "0.02"},
                {"字段": "最新价", "值": "0.015"},
                {"字段": "持仓量", "值": "340"},
            ]
        return pd.DataFrame(rows)

    class FakeAk:
        def option_current_day_sse(self):
            return current_day

        def option_sse_spot_price_sina(self, symbol=""):
            return make_spot(symbol)

    chain, meta = _etf_option_chain_from_current_day(
        "510050",
        "202608",
        lambda: FakeAk(),
        _mid,
        _safe_float,
    )
    assert meta["exchange"] == "SSE"
    assert len(chain) == 1
    row = chain[0]
    assert row["strike"] == 2.75
    assert row["call_oi"] == 120.0
    assert row["put_oi"] == 340.0


def test_etf_option_chain_from_current_day_uses_szse_listing():
    current_day = pd.DataFrame(
        [
            {
                "标的证券简称(代码)": "创业板ETF(159915)",
                "合约代码": "159915C2609M002950",
                "行权价": 2.95,
                "合约类型": "认购",
                "合约编码": 90007069,
                "合约单位": 10000,
                "合约总持仓": 1784.0,
                "前结算价": 0.55,
                "行权日": pd.Timestamp("2026-09-24"),
            },
        ]
    )

    class FakeAk:
        def option_current_day_szse(self):
            return current_day

        def option_sse_spot_price_sina(self, symbol=""):
            return pd.DataFrame(
                [
                    {"字段": "买价", "值": "0.60"},
                    {"字段": "卖价", "值": "0.62"},
                    {"字段": "最新价", "值": "0.615"},
                    {"字段": "持仓量", "值": "1790"},
                    {"字段": "标的股票", "值": "159915"},
                ]
            )

    chain, meta = _etf_option_chain_from_current_day(
        "159915",
        "202609",
        lambda: FakeAk(),
        _mid,
        _safe_float,
    )
    assert meta["exchange"] == "SZSE"
    assert len(chain) == 1
    assert chain[0]["call_oi"] == 1790.0
    assert chain[0]["call_mid"] == 0.61


def test_etf_option_chain_szse_listing_fallback_without_spot():
    current_day = pd.DataFrame(
        [
            {
                "标的证券简称(代码)": "创业板ETF(159915)",
                "合约代码": "159915C2609M002950",
                "行权价": 2.95,
                "合约类型": "认购",
                "合约编码": 90007069,
                "合约单位": 10000,
                "合约总持仓": 1784.0,
                "前结算价": 0.55,
                "行权日": pd.Timestamp("2026-09-24"),
            },
        ]
    )

    class FakeAk:
        def option_current_day_szse(self):
            return current_day

        def option_sse_spot_price_sina(self, symbol=""):
            raise RuntimeError("spot unavailable")

    chain, _meta = _etf_option_chain_from_current_day(
        "159915",
        "202609",
        lambda: FakeAk(),
        _mid,
        _safe_float,
    )
    assert chain[0]["call_oi"] == 1784.0
    assert chain[0]["call_mid"] == 0.55
