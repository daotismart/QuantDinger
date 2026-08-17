"""CTP credential vault helpers."""

from __future__ import annotations

import pytest
from marshmallow import ValidationError

from app.openapi.schemas.high_risk import CredentialCreateRequestSchema
from app.routes.credentials import _ctp_credential_config
from app.services.live_trading.factory import exchange_trading_environment


def test_ctp_schema_accepts_eastmoney_style_fields():
    loaded = CredentialCreateRequestSchema().load(
        {
            "name": "东方财富期货",
            "exchange_id": "ctp",
            "CTP_USERNAME": "6605239",
            "CTP_PASSWORD": "secret",
            "CTP_BROKER_ID": "9099",
            "CTP_TRADE_SERVER": "103.192.214.78:51205",
            "CTP_MD_SERVER": "103.192.214.78:51213",
            "CTP_APP_ID": "client_DTSCTP_1.1.0",
            "CTP_AUTH_CODE": "AUTH",
            "CTP_PRODUCT_INFO": "DTSCTP",
            "CTP_ENVIRONMENT": "实盘",
        }
    )
    assert loaded["exchange_id"] == "ctp"
    assert loaded["CTP_USERNAME"] == "6605239"


def test_ctp_schema_skips_api_key_requirement():
    with pytest.raises(ValidationError):
        CredentialCreateRequestSchema().load({"exchange_id": "binance"})
    CredentialCreateRequestSchema().load(
        {
            "exchange_id": "ctp",
            "user_id": "u",
            "password": "p",
            "broker_id": "9099",
            "td_front": "tcp://127.0.0.1:1",
        }
    )


def test_ctp_credential_config_maps_aliases():
    cfg = _ctp_credential_config(
        {
            "CTP_USERNAME": "6605239",
            "CTP_PASSWORD": "98521.01",
            "CTP_BROKER_ID": "9099",
            "CTP_TRADE_SERVER": "103.192.214.78:51205",
            "CTP_MD_SERVER": "103.192.214.78:51213",
            "CTP_APP_ID": "client_DTSCTP_1.1.0",
            "CTP_AUTH_CODE": "I7BDKBE312F9KUJ6",
            "CTP_PRODUCT_INFO": "DTSCTP",
            "CTP_ENVIRONMENT": "实盘",
        },
        exchange_id="ctp",
    )
    assert cfg["exchange_id"] == "ctp"
    assert cfg["user_id"] == "6605239"
    assert cfg["password"] == "98521.01"
    assert cfg["broker_id"] == "9099"
    assert cfg["td_front"] == "tcp://103.192.214.78:51205"
    assert cfg["md_front"] == "tcp://103.192.214.78:51213"
    assert cfg["app_id"] == "client_DTSCTP_1.1.0"
    assert cfg["auth_code"] == "I7BDKBE312F9KUJ6"
    assert cfg["product_info"] == "DTSCTP"
    assert cfg["environment"] == "live"
    assert cfg["mode"] == "live"
    assert cfg["market_scope"] == "futures"


def test_environment_accepts_chinese_live_label():
    assert exchange_trading_environment({"CTP_ENVIRONMENT": "实盘"}, "ctp") == "live"
    assert exchange_trading_environment({"environment": "模拟"}, "ctp") == "demo"
