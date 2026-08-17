"""Unit tests for CTP TdApi helpers and live CtpClient wiring (mocked)."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.services.cffex_trading import CtpClient, CtpConfig
from app.services.ctp_td.gateway import (
    CtpOrderFill,
    CtpTdGateway,
    map_side_offset_to_ctp,
    signal_to_side_offset,
)
from app.services.live_trading.base import LiveTradingError
from app.services.live_trading.execution import place_order_from_signal


class TestSignalMapping:
    def test_open_close_directions(self):
        assert map_side_offset_to_ctp(side="long", offset="open") == ("0", "0")
        assert map_side_offset_to_ctp(side="long", offset="close") == ("1", "1")
        assert map_side_offset_to_ctp(side="short", offset="open") == ("1", "0")
        assert map_side_offset_to_ctp(side="short", offset="close") == ("0", "1")
        assert map_side_offset_to_ctp(side="long", offset="close_today") == ("1", "3")

    def test_signal_to_side_offset(self):
        assert signal_to_side_offset("open_long") == ("long", "open")
        assert signal_to_side_offset("close_short") == ("short", "close")
        with pytest.raises(Exception, match="Unsupported"):
            signal_to_side_offset("hold")


class TestLiveGating:
    def test_live_blocked_without_kill_switch(self, monkeypatch):
        monkeypatch.delenv("CFFEX_LIVE_TRADING_ENABLED", raising=False)
        with pytest.raises(LiveTradingError, match="disabled"):
            CtpClient(
                CtpConfig(
                    mode="live",
                    broker_id="9999",
                    user_id="u",
                    password="p",
                    td_front="tcp://127.0.0.1:1",
                )
            )

    def test_live_blocked_when_binding_missing(self, monkeypatch):
        monkeypatch.setenv("CFFEX_LIVE_TRADING_ENABLED", "true")

        def _boom(_module=None):
            from app.services.ctp_td.gateway import CtpTdDependencyError

            raise CtpTdDependencyError("no binding")

        monkeypatch.setattr(
            "app.services.ctp_td.gateway.load_ctp_tdapi",
            _boom,
        )
        with pytest.raises(LiveTradingError, match="binding|no binding"):
            CtpClient(
                CtpConfig(
                    mode="live",
                    broker_id="9999",
                    user_id="u",
                    password="p",
                    td_front="tcp://127.0.0.1:1",
                )
            )


class TestCtpClientLivePlaceOrder:
    def test_place_order_routes_to_gateway(self, monkeypatch):
        monkeypatch.setenv("CFFEX_LIVE_TRADING_ENABLED", "true")
        monkeypatch.setattr(
            "app.services.ctp_td.gateway.load_ctp_tdapi",
            lambda _module=None: SimpleNamespace(),
        )

        class FakeGateway:
            def place_order(self, **kwargs):
                assert kwargs["symbol"] == "rb2609"
                assert kwargs["side"] == "long"
                assert kwargs["offset"] == "open"
                assert kwargs["lots"] == 2
                return CtpOrderFill(
                    order_id="SYS1",
                    instrument_id="rb2609",
                    direction="0",
                    offset="0",
                    volume=2.0,
                    price=3500.0,
                    status="all_traded",
                    raw={"order_ref": "000001"},
                )

        client = CtpClient(
            CtpConfig(
                mode="live",
                broker_id="9999",
                user_id="u",
                password="p",
                td_front="tcp://127.0.0.1:1",
            )
        )
        client._gateway = FakeGateway()
        result = client.place_order(
            symbol="rb2609",
            side="long",
            offset="open",
            lots=2,
            price=3500,
            order_type="limit",
        )
        assert result.exchange_order_id == "SYS1"
        assert result.filled == 2.0
        assert result.avg_price == 3500.0

    def test_place_order_from_signal(self, monkeypatch):
        monkeypatch.setenv("CFFEX_LIVE_TRADING_ENABLED", "true")
        monkeypatch.setattr(
            "app.services.ctp_td.gateway.load_ctp_tdapi",
            lambda _module=None: SimpleNamespace(),
        )

        class FakeGateway:
            def place_order(self, **kwargs):
                assert kwargs["side"] == "short"
                assert kwargs["offset"] == "open"
                return CtpOrderFill(
                    order_id="2",
                    instrument_id="ag2609",
                    direction="1",
                    offset="0",
                    volume=1.0,
                    price=7000.0,
                    status="all_traded",
                )

        client = CtpClient(
            CtpConfig(
                mode="live",
                broker_id="9999",
                user_id="u",
                password="p",
                td_front="tcp://127.0.0.1:1",
            )
        )
        client._gateway = FakeGateway()
        result = place_order_from_signal(
            client,
            signal_type="open_short",
            symbol="CNFutures:ag2609",
            amount=1,
            market_type="futures",
            exchange_config={"price": 7000, "order_type": "limit"},
        )
        assert result.filled == 1.0
        assert result.avg_price == 7000.0


class TestGatewayHelpers:
    def test_status_snapshot(self):
        gw = CtpTdGateway(
            settings=__import__("app.services.ctp_td.config", fromlist=["CtpTdSettings"]).CtpTdSettings(
                enabled=True,
                front="tcp://x",
                broker_id="b",
                user_id="u",
                password="p",
                app_id="",
                auth_code="",
                product_info="",
                investor_id="u",
                flow_path="/tmp/ctp_td_test/",
                api_module="openctp_ctp",
                order_timeout_sec=5.0,
                reconnect_seconds=5.0,
            )
        )
        st = gw.status()
        assert st["configured"] is True
        assert st["connected"] is False
