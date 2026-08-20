"""Unit tests for CTP MdApi tick market-data integration."""

from __future__ import annotations

from app.services.ctp_md.config import CtpMdSettings
from app.services.ctp_md.gateway import CtpMdGateway
from app.services.ctp_md.models import tick_from_depth_market_data
from app.services.ctp_md.price_feed import CtpTickPriceFeed
from app.services.ctp_md.store import CtpTickStore
from app.services.ctp_md.symbols import (
    looks_like_cn_futures_instrument,
    normalize_ctp_instrument,
    unique_instruments,
)
from app.services.market_price_stream import create_market_price_feed


def test_normalize_and_detect_cn_futures_instruments():
    assert normalize_ctp_instrument("Futures:SHFE.rb2505") == "rb2505"
    assert normalize_ctp_instrument("IF2503") == "IF2503"
    assert looks_like_cn_futures_instrument("rb2505")
    assert looks_like_cn_futures_instrument("TA505")
    assert not looks_like_cn_futures_instrument("GC=F")
    assert not looks_like_cn_futures_instrument("BTC/USDT")
    assert unique_instruments(["rb2505", "RB2505", "SHFE.rb2505"]) == ["rb2505"]


def test_tick_from_depth_market_data_and_ticker_shape():
    tick = tick_from_depth_market_data(
        {
            "InstrumentID": "rb2505",
            "ExchangeID": "SHFE",
            "LastPrice": "3412",
            "Volume": "123",
            "BidPrice1": "3411",
            "AskPrice1": "3413",
            "PreClosePrice": "3400",
            "UpdateTime": "10:30:01",
            "UpdateMillisec": 500,
        },
        received_at_ms=1_700_000_000_000,
    )
    assert tick is not None
    assert tick.usable_price == 3412.0
    ticker = tick.to_ticker()
    assert ticker["last"] == 3412.0
    assert ticker["source"] == "ctp_tick"
    assert ticker["change"] == 12.0


def test_tick_store_prices_for_runtime_keys():
    store = CtpTickStore()
    tick = tick_from_depth_market_data(
        {"InstrumentID": "rb2505", "LastPrice": 100.5, "ExchangeID": "SHFE"},
        received_at_ms=1,
    )
    store.put(tick)
    prices = store.prices_for(
        [{"key": "Futures:rb2505@ctp:futures", "symbol": "rb2505"}],
        max_age_seconds=5,
    )
    assert prices["Futures:rb2505@ctp:futures"] == 100.5
    assert store.get("RB2505").last_price == 100.5


def test_ctp_price_feed_snapshot_and_factory(monkeypatch):
    settings = CtpMdSettings(
        enabled=True,
        front="tcp://127.0.0.1:1",
        broker_id="9999",
        user_id="demo",
        password="demo",
        app_id="",
        auth_code="",
        product_info="",
        flow_path="./ctp_md_flow_test/",
        instruments=[],
        reconnect_seconds=5,
        tick_stale_after_seconds=10,
    )
    store = CtpTickStore()
    gateway = CtpMdGateway(settings=settings, store=store, mdapi=object())
    tick = tick_from_depth_market_data({"InstrumentID": "ag2506", "LastPrice": 7788})
    gateway.inject_tick(tick)

    monkeypatch.setattr(
        "app.services.ctp_md.price_feed.get_ctp_md_gateway",
        lambda: gateway,
    )
    monkeypatch.setattr(
        "app.services.ctp_md.price_feed.get_ctp_tick_store",
        lambda: store,
    )

    feed = CtpTickPriceFeed(
        exchange_id="ctp",
        market_type="futures",
        instruments=[{"key": "Futures:ag2506@ctp:futures", "symbol": "ag2506"}],
        rest_fallback=lambda: {},
    )
    snapshot = feed.snapshot(max_age_seconds=5)
    assert snapshot.source == "ctp_tick"
    assert snapshot.prices["Futures:ag2506@ctp:futures"] == 7788.0

    created = create_market_price_feed(
        exchange_id="ctp",
        market_type="futures",
        instruments=[{"key": "Futures:ag2506@ctp:futures", "symbol": "ag2506"}],
        rest_fallback=lambda: {"Futures:ag2506@ctp:futures": 1.0},
    )
    assert isinstance(created, CtpTickPriceFeed)


def test_futures_datasource_prefers_ctp_tick(monkeypatch):
    from app.data_sources.futures import FuturesDataSource

    monkeypatch.setattr(
        "app.services.ctp_md.service.ctp_ticker_for_symbol",
        lambda symbol, max_age_seconds=None: {
            "symbol": "rb2505",
            "last": 3210.0,
            "source": "ctp_tick",
        },
    )
    source = FuturesDataSource()
    ticker = source.get_ticker("rb2505")
    assert ticker["last"] == 3210.0
    assert ticker["source"] == "ctp_tick"


def test_ctp_price_feed_rest_fallback_when_stale(monkeypatch):
    settings = CtpMdSettings(
        enabled=True,
        front="tcp://127.0.0.1:1",
        broker_id="9999",
        user_id="demo",
        password="demo",
        app_id="",
        auth_code="",
        product_info="",
        flow_path="./ctp_md_flow_test/",
        instruments=[],
        reconnect_seconds=5,
        tick_stale_after_seconds=10,
    )
    store = CtpTickStore()
    gateway = CtpMdGateway(settings=settings, store=store, mdapi=object())
    monkeypatch.setattr("app.services.ctp_md.price_feed.get_ctp_md_gateway", lambda: gateway)
    monkeypatch.setattr("app.services.ctp_md.price_feed.get_ctp_tick_store", lambda: store)

    feed = CtpTickPriceFeed(
        exchange_id="ctp",
        market_type="futures",
        instruments=[{"key": "Futures:rb2505@ctp:futures", "symbol": "rb2505"}],
        rest_fallback=lambda: {"Futures:rb2505@ctp:futures": 99.0},
    )
    snapshot = feed.snapshot(max_age_seconds=1)
    assert snapshot.source == "rest_fallback"
    assert snapshot.prices["Futures:rb2505@ctp:futures"] == 99.0


class _Field:
    pass


class _SpiBase:
    pass


class _MdApiModule:
    CThostFtdcMdSpi = _SpiBase
    CThostFtdcReqAuthenticateField = _Field
    CThostFtdcReqUserLoginField = _Field


class _MdApiWithoutAuthenticate:
    def __init__(self):
        self.logins = []
        self.auths = []

    def ReqUserLogin(self, req, request_id):
        self.logins.append((req.BrokerID, req.UserID, request_id))


class _MdApiWithAuthenticate(_MdApiWithoutAuthenticate):
    def ReqAuthenticate(self, req, request_id):
        self.auths.append((req.AppID, req.AuthCode, request_id))


def _auth_settings(**overrides) -> CtpMdSettings:
    values = dict(
        enabled=True,
        front="tcp://127.0.0.1:1",
        broker_id="9099",
        user_id="demo",
        password="demo",
        app_id="client_DTSCTP_1.1.0",
        auth_code="AUTH",
        product_info="DTSCTP",
        flow_path="./ctp_md_flow_test/",
        instruments=["rb2609"],
        reconnect_seconds=5,
        tick_stale_after_seconds=10,
    )
    values.update(overrides)
    return CtpMdSettings(**values)


def test_mdapi_skips_authenticate_when_binding_has_no_method():
    api = _MdApiWithoutAuthenticate()
    gateway = CtpMdGateway(settings=_auth_settings(), store=CtpTickStore(), mdapi=_MdApiModule())
    spi = gateway._build_spi(_MdApiModule(), api)
    spi.OnFrontConnected()
    assert api.auths == []
    assert api.logins == [("9099", "demo", 1)]


def test_mdapi_calls_authenticate_when_binding_supports_it():
    api = _MdApiWithAuthenticate()
    gateway = CtpMdGateway(settings=_auth_settings(), store=CtpTickStore(), mdapi=_MdApiModule())
    spi = gateway._build_spi(_MdApiModule(), api)
    spi.OnFrontConnected()
    assert api.auths == [("client_DTSCTP_1.1.0", "AUTH", 1)]
    assert api.logins == []
