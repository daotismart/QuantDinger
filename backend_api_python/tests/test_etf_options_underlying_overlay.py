"""ETF options current price should follow cash last when CH 1m is stale."""

from datetime import datetime

from app.services.cn_derivatives_etf import (
    ch_underlying_is_stale,
    resolve_etf_options_underlying,
)


def test_missing_ch_ts_is_stale():
    assert ch_underlying_is_stale(None) is True
    assert ch_underlying_is_stale("") is True


def test_ch_print_older_than_ten_minutes_is_stale():
    now = datetime(2026, 10, 9, 21, 0, 0)
    assert ch_underlying_is_stale("2026-10-09 14:01:00", now=now) is True
    assert ch_underlying_is_stale("2026-10-09 20:55:00", now=now) is False


def test_stale_ch_underlying_yields_to_etf_spot():
    px, src = resolve_etf_options_underlying(
        ch_price=1.52,
        ch_ts="2026-10-09 14:01:00",
        spot_price=1.54,
        now=datetime(2026, 10, 9, 21, 0, 0),
    )
    assert px == 1.54
    assert src == "etf_spot"


def test_fresh_ch_underlying_kept_during_session():
    px, src = resolve_etf_options_underlying(
        ch_price=1.526,
        ch_ts="2026-10-09 14:50:00",
        spot_price=1.54,
        now=datetime(2026, 10, 9, 14, 52, 0),
    )
    assert px == 1.526
    assert src == "clickhouse"


def test_spot_used_when_ch_price_missing():
    px, src = resolve_etf_options_underlying(
        ch_price=0.0,
        ch_ts="2026-10-09 14:50:00",
        spot_price=1.541,
        now=datetime(2026, 10, 9, 14, 52, 0),
    )
    assert px == 1.541
    assert src == "etf_spot"


def test_build_etf_options_panel_overlays_stale_ch(monkeypatch):
    from app.services import cn_derivatives_etf as etf_mod

    monkeypatch.setattr(etf_mod, "_etf_options_cache_get", lambda _key: None)
    monkeypatch.setattr(etf_mod, "_etf_options_cache_set", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(etf_mod, "_etf_spot_last_price", lambda _code: 1.54)
    monkeypatch.setattr(
        "app.services.etf_options_clickhouse.try_load_etf_option_chains",
        lambda _code: {
            "months": ["202610"],
            "chains_by_month": {
                "202610": [
                    {
                        "strike": 1.5,
                        "call_mid": 0.04,
                        "put_mid": 0.03,
                        "call_oi": 100,
                        "put_oi": 80,
                    }
                ]
            },
            "month_meta": {"202610": {"multiplier": 10000.0, "T": 20 / 365.0}},
            "underlying": 1.52,
            "underlying_ts": "2026-10-09 14:01:00",
        },
    )
    monkeypatch.setattr(
        etf_mod,
        "ch_underlying_is_stale",
        lambda *_args, **_kwargs: True,
    )

    captured = {}

    def _assemble(**kwargs):
        captured.update(kwargs)
        return {
            "root": kwargs["code6"],
            "underlying": kwargs["underlying"],
            "current_price": kwargs["underlying"],
            "month_series": [{"month": "202610"}],
            "data_source": kwargs["data_source"],
        }

    monkeypatch.setattr(etf_mod, "_assemble_etf_options_panel", _assemble)
    monkeypatch.setattr(
        "app.services.etf_options_clickhouse.etf_options_panel_cache_ttl",
        lambda: 0,
    )

    panel = etf_mod.build_etf_options_panel("588000", month="all")
    assert captured["underlying"] == 1.54
    assert panel["current_price"] == 1.54
    assert panel["underlying_source"] == "etf_spot"
    assert panel["ch_underlying"] == 1.52
