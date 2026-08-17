"""China futures-options Quick Trade: lots, codes, CTP/QMT execution."""

from __future__ import annotations

import pytest

from app.markets.cn_futures import format_ctp_option_instrument_id, is_cn_derivative
from app.openapi.schemas.high_risk import QuickTradeOrderRequestSchema
from app.routes.quick_trade import _parse_positions, _reject_quick_trade_if_desktop_broker
from app.services.cffex_trading import CtpClient, CtpConfig
from app.services.ctp_td.gateway import format_instrument_id
from app.services.live_trading.contracts import normalize_order_market_type
from app.services.live_trading.execution import _normalize_symbol_for_order, place_order_from_signal
from app.services.live_trading.factory import create_client
from app.services.quick_trade.cn_derivatives import (
    is_cn_quick_trade_exchange,
    is_cn_quick_trade_market,
    lots_from_amount,
    parse_cn_balance,
    place_cn_quick_order,
    resolve_cn_market_type,
    side_offset_to_signal,
    split_cn_display_symbol,
)
from app.services.quick_trade.symbols import is_supported_crypto_exchange


class TestOptionInstrumentIds:
    def test_dce_meal_call(self):
        assert format_ctp_option_instrument_id("m2609-C-2800") == "m2609-C-2800"
        assert format_instrument_id("m2609-C-2800", "DCE") == "m2609-C-2800"

    def test_cffex_ho_call(self):
        assert format_ctp_option_instrument_id("HO2608-C-2500") == "HO2608-C-2500"
        assert format_instrument_id("HO2608-C-2500", "CFFEX") == "HO2608-C-2500"

    def test_shfe_compact_call(self):
        assert format_ctp_option_instrument_id("cu2609C100000", "SHFE") == "cu2609C100000"
        assert format_instrument_id("cu2609C100000", "SHFE") == "cu2609C100000"

    def test_czce_compact(self):
        formatted = format_ctp_option_instrument_id("SR509P5200", "CZCE")
        assert formatted is not None
        assert formatted.startswith("SR")
        assert "P" in formatted


class TestCnQuickTradeHelpers:
    def test_lots_require_positive_integer(self):
        assert lots_from_amount(1) == 1
        assert lots_from_amount(2.0) == 2
        with pytest.raises(ValueError, match="lot"):
            lots_from_amount(0)
        with pytest.raises(ValueError, match="lot"):
            lots_from_amount(0.4)

    def test_market_type_from_page_and_symbol(self):
        assert resolve_cn_market_type(market="CNFuturesOptions", symbol="m2609-C-2800") == "options"
        assert resolve_cn_market_type(market="CNIndexOptions") == "options"
        assert resolve_cn_market_type(market="CNFutures", symbol="rb2609") == "futures"
        assert resolve_cn_market_type(market_type="swap", symbol="m2609-C-2800") == "options"
        assert resolve_cn_market_type(market_type="option") == "options"

    def test_side_offset_mapping(self):
        assert side_offset_to_signal(side="buy", offset="open") == "open_long"
        assert side_offset_to_signal(side="sell", offset="open") == "open_short"
        assert side_offset_to_signal(side="sell", offset="close") == "close_long"
        assert side_offset_to_signal(side="buy", offset="close") == "close_short"

    def test_option_codes_are_not_fake_crypto_pairs(self):
        assert split_cn_display_symbol("m2609-C-2800") == "m2609-C-2800"
        assert split_cn_display_symbol("M2609-C-2800") == "M2609-C-2800"
        assert split_cn_display_symbol("CNFuturesOptions:m2609-C-2800") == "m2609-C-2800"
        assert is_cn_derivative("M2609-C-2800") is True

    def test_parse_cn_balance_uses_cny(self):
        parsed = parse_cn_balance({"available": 120000.5, "cash": 150000, "currency": "CNY"})
        assert parsed["available"] == 120000.5
        assert parsed["total"] == 150000
        assert parsed["currency"] == "CNY"

    def test_exchange_allowlist(self):
        assert is_cn_quick_trade_exchange("ctp") is True
        assert is_cn_quick_trade_exchange("QMT") is True
        assert is_cn_quick_trade_market("CNFuturesOptions") is True
        assert is_cn_quick_trade_market("CNIndexOptions") is True
        assert is_supported_crypto_exchange("ctp") is False


class TestQuickTradeContracts:
    def test_schema_accepts_options_and_offset(self):
        loaded = QuickTradeOrderRequestSchema().load(
            {
                "credential_id": 3,
                "symbol": "m2609-C-2800",
                "side": "BUY",
                "amount": 1,
                "market_type": "OPTIONS",
                "market": "CNFuturesOptions",
                "offset": "OPEN",
            }
        )
        assert loaded["market_type"] == "options"
        assert loaded["offset"] == "open"
        assert loaded["amount"] == 1.0

    def test_parse_positions_keeps_listed_option_code(self):
        out = _parse_positions(
            [
                {
                    "symbol": "M2609-C-2800",
                    "side": "long",
                    "volume": 2,
                    "avg_price": 86.5,
                }
            ]
        )
        assert len(out) == 1
        assert out[0]["symbol"] == "M2609-C-2800"
        assert out[0]["size"] == 2.0
        assert out[0]["side"] == "long"

    def test_normalize_market_type_keeps_options(self):
        assert normalize_order_market_type("options") == "options"
        assert normalize_order_market_type("option") == "options"
        assert normalize_order_market_type("futures") == "swap"

    def test_order_symbol_does_not_gain_usdt(self):
        assert _normalize_symbol_for_order("m2609-C-2800", "options") == "m2609-C-2800"
        assert _normalize_symbol_for_order("m2609-C-2800", "swap") == "m2609-C-2800"
        assert _normalize_symbol_for_order("CNFuturesOptions:m2609-C-2800", "options") == "m2609-C-2800"


class TestCtpSimulationQuickTrade:
    def test_futures_scoped_seat_can_trade_options(self):
        client = create_client(
            {"exchange_id": "ctp", "environment": "demo", "market_scope": "futures"},
            market_type="options",
        )
        assert isinstance(client, CtpClient)
        result = place_cn_quick_order(
            client,
            symbol="m2509-C-2800",
            side="buy",
            amount=1,
            price=80,
            order_type="limit",
            offset="open",
            market="CNFuturesOptions",
            exchange_config={"environment": "demo", "price": 80, "order_type": "limit"},
        )
        assert result.filled == 1
        assert result.avg_price == 80

    def test_place_order_from_signal_option_short(self):
        client = CtpClient(CtpConfig(mode="demo"))
        result = place_order_from_signal(
            client,
            signal_type="open_short",
            symbol="m2509-C-2800",
            amount=1,
            market_type="options",
            exchange_config={"price": 90, "order_type": "limit"},
        )
        assert result.filled == 1.0
        positions = client.get_positions()
        assert any(row.get("symbol") == "M2509-C-2800" for row in positions)


def test_reject_helper_allows_ctp(app):
    with app.app_context():
        assert _reject_quick_trade_if_desktop_broker("ctp") is None
        assert _reject_quick_trade_if_desktop_broker("qmt") is None
        rejected = _reject_quick_trade_if_desktop_broker("ibkr")
        assert rejected is not None
        response, status = rejected
        assert status == 400
        assert "CTP" in response.get_json()["msg"]
