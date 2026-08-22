"""Tests for SSE ETF option chain quote parsing."""

import pandas as pd

from app.services.cn_derivatives_etf import (
    _apply_sse_option_quote,
    _empty_etf_option_chain_bucket,
    _etf_option_chain_from_current_day,
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


def test_apply_sse_option_quote_populates_call_and_put_fields():
    bucket = _empty_etf_option_chain_bucket(2.75)
    _apply_sse_option_quote(
        bucket,
        "认购",
        {"bid": 0.24, "ask": 0.25, "last": 0.245, "mid": 0.245, "oi": 100.0},
    )
    assert bucket["call_oi"] == 100.0
    assert bucket["call_bid"] == 0.24
    assert bucket["call_ask"] == 0.25
    assert bucket["call_last"] == 0.245

    _apply_sse_option_quote(
        bucket,
        "认沽",
        {"bid": 0.01, "ask": 0.02, "last": 0.015, "mid": 0.015, "oi": 200.0},
    )
    assert bucket["put_oi"] == 200.0
    assert bucket["put_mid"] == 0.015


def test_etf_sse_list_symbol_for_star50():
    from app.services.cn_derivatives_etf import _etf_sse_list_symbol

    assert _etf_sse_list_symbol("588000") == "科创50ETF"
    assert _etf_sse_list_symbol("588080") == "科创50ETF"


def test_etf_underlying_col_matches_star50():
    from app.services.cn_derivatives_etf import _etf_underlying_col_matches

    assert _etf_underlying_col_matches("科创50(588000)", "588000")
    assert _etf_underlying_col_matches("科创板50(588080)", "588080")
    assert not _etf_underlying_col_matches("50ETF(510050)", "588000")
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

    chain, _meta = _etf_option_chain_from_current_day(
        "510050",
        "202608",
        lambda: FakeAk(),
        _mid,
        _safe_float,
    )
    assert len(chain) == 1
    row = chain[0]
    assert row["strike"] == 2.75
    assert row["call_oi"] == 120.0
    assert row["put_oi"] == 340.0
    assert row["call_mid"] == 0.245
    assert row["put_mid"] == 0.015
