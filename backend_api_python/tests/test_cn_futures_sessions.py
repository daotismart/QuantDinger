"""CN futures matching-session calendar for CTP tick gating."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app.markets.cn_futures_sessions import (
    filter_collectible_instruments,
    instrument_session_status,
    is_instrument_in_session,
    md_connection_open,
)
from app.services.ctp_md.config import CtpMdSettings
from app.services.ctp_md.gateway import CtpMdGateway
from app.services.ctp_md.store import CtpTickStore
from app.services.market_data_maint.config import MarketDataMaintSettings
from app.services.market_data_maint.realtime import RealtimeMaintainer

_CST = timezone(timedelta(hours=8))


def _cst(y, m, d, hh, mm) -> datetime:
    return datetime(y, m, d, hh, mm, tzinfo=_CST)


def test_commodity_day_and_tea_break():
    now = _cst(2026, 8, 18, 10, 0)  # Tuesday
    assert is_instrument_in_session("rb2609", now=now) is True
    tea = _cst(2026, 8, 18, 10, 20)
    assert is_instrument_in_session("rb2609", now=tea) is False
    assert instrument_session_status("rb2609", now=tea).in_collect_window is True


def test_cffex_index_hours_differ_from_commodity():
    morning = _cst(2026, 8, 18, 9, 10)
    assert is_instrument_in_session("rb2609", now=morning) is True
    assert is_instrument_in_session("IF2609", now=morning) is False
    lunch = _cst(2026, 8, 18, 13, 10)
    assert is_instrument_in_session("IF2609", now=lunch) is True
    assert is_instrument_in_session("rb2609", now=lunch) is False


def test_night_groups_and_weekend_bridge():
    tue_night = _cst(2026, 8, 18, 21, 30)
    assert is_instrument_in_session("rb2609", now=tue_night) is True
    assert is_instrument_in_session("au2609", now=tue_night) is True
    assert is_instrument_in_session("IF2609", now=tue_night) is False

    after_midnight = _cst(2026, 8, 19, 0, 30)  # Wednesday 00:30
    assert is_instrument_in_session("au2609", now=after_midnight) is True
    assert is_instrument_in_session("rb2609", now=after_midnight) is False

    sat_morning = _cst(2026, 8, 22, 1, 0)  # Saturday after Friday night
    assert is_instrument_in_session("au2609", now=sat_morning) is True
    sat_noon = _cst(2026, 8, 22, 12, 0)
    assert is_instrument_in_session("au2609", now=sat_noon) is False
    assert md_connection_open(["rb2609", "IF2609"], now=sat_noon) is False

    sunday_night = _cst(2026, 8, 23, 21, 30)
    assert is_instrument_in_session("rb2609", now=sunday_night) is True
    assert is_instrument_in_session("IF2609", now=sunday_night) is False
    assert md_connection_open(["rb2609", "IF2609"], now=sunday_night) is True
    assert filter_collectible_instruments(["rb2609", "IF2609"], now=sunday_night) == ["rb2609"]


def test_gateway_status_exposes_session_flag(monkeypatch):
    monkeypatch.delenv("CTP_MD_IGNORE_SESSION", raising=False)
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
        instruments=["rb2609"],
        reconnect_seconds=5,
        tick_stale_after_seconds=10,
    )
    gateway = CtpMdGateway(settings=settings, store=CtpTickStore(), mdapi=object())
    status = gateway.status()
    assert "sessionOpen" in status
    assert "sessionCollectible" in status


def test_realtime_skips_stale_resubscribe_when_closed(monkeypatch):
    settings = MarketDataMaintSettings(
        enabled=True,
        realtime_enabled=True,
        historical_enabled=True,
        realtime_interval_sec=5,
        historical_interval_sec=300,
        tick_stale_after_sec=1,
        tick_retention_days=7,
        bar_retention_days=365,
        max_gap_bars=50,
        session_gap_seconds=54000,
        price_spike_ratio=1.15,
        watchlist_csv="",
        persist_ticks=False,
    )
    maint = RealtimeMaintainer(settings=settings)

    class FakeGateway:
        settings = type("S", (), {"enabled": True})()
        running = True

        def status(self):
            return {"subscribed": ["rb2609"], "pendingSubscribe": []}

        def subscribe(self, _ids):
            raise AssertionError("should not resubscribe while session closed")

        def start(self):
            raise AssertionError("should not start while session closed")

    monkeypatch.setattr(
        "app.services.market_data_maint.realtime.get_ctp_md_gateway",
        lambda: FakeGateway(),
    )
    monkeypatch.setattr(
        "app.services.market_data_maint.realtime.md_connection_open",
        lambda symbols, now=None: False,
    )
    assert maint._resubscribe_stale() == 0
