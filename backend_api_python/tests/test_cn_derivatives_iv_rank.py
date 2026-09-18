"""IV Rank history for market-composite options charts."""

from __future__ import annotations

from app.services import cn_derivatives_iv_rank as ivr


def test_rolling_iv_rank_at_high_and_low():
    series = [10.0, 12.0, 11.0, 20.0, 9.0]
    ranks = ivr.rolling_iv_rank(series, lookback=5)
    assert ranks[0] == 50.0
    assert ranks[3] == 100.0
    assert ranks[4] == 0.0


def test_rolling_iv_percentile_counts_below():
    series = [1.0, 2.0, 3.0, 4.0]
    pct = ivr.rolling_iv_percentile(series, lookback=4)
    assert pct[-1] == 75.0


def test_points_from_iv_klines():
    klines = [
        {"ts": "2026-01-01 15:00:00", "date": "2026-01-01", "label": "2026-01-01", "close": 0.12, "month": "202603"},
        {"ts": "2026-01-02 15:00:00", "date": "2026-01-02", "label": "2026-01-02", "close": 0.20, "month": "202603"},
        {"ts": "2026-01-03 15:00:00", "date": "2026-01-03", "label": "2026-01-03", "close": 0.10, "month": "202603"},
    ]
    points = ivr.points_from_iv_values(klines, lookback=20)
    assert points[-1]["iv_rank"] == 0.0
    assert points[1]["iv_rank"] == 100.0
    assert points[-1]["proxy"] == "atm_iv"


def test_etf_iv_rank_history_uses_near_month_klines(monkeypatch):
    stamps = ["2026-08-01 15:00:00", "2026-08-02 15:00:00", "2026-08-03 15:00:00"]
    ivs = [0.15, 0.25, 0.20]

    def _boom(*_args, **_kwargs):
        raise AssertionError("IV Rank must not build the full ETF surface history")

    monkeypatch.setattr("app.services.gex_history.build_etf_options_surface_history", _boom)
    monkeypatch.setattr("app.services.etf_options_clickhouse.etf_options_ch_enabled", lambda: True)
    monkeypatch.setattr("app.services.etf_options_clickhouse.ch_ping", lambda: True)
    monkeypatch.setattr(
        "app.services.etf_options_clickhouse.list_playback_timestamps",
        lambda *_args, **_kwargs: stamps,
    )
    monkeypatch.setattr(
        "app.services.etf_options_clickhouse.fetch_underlying_series",
        lambda *_args, **_kwargs: {ts: 4.5 for ts in stamps},
    )
    monkeypatch.setattr(
        "app.services.etf_options_clickhouse.fetch_near_month_atm_iv_series",
        lambda *_args, **_kwargs: (
            {
                ts: {"iv": iv, "month": "202609", "underlying": 4.5}
                for ts, iv in zip(stamps, ivs)
            },
            {"source": "mock_atm"},
        ),
    )
    monkeypatch.setattr(
        "app.services.etf_options_clickhouse.fetch_option_chain_rows_at_timestamps",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("ATM IV series should skip full chain fetch")
        ),
    )
    data = ivr.build_etf_options_iv_rank_history("510050.SH", bars=3)
    assert data["chart_key"] == "options.ivRank"
    assert data["mode"] == "daily"
    assert data["proxy"] == "atm_iv"
    assert len(data["points"]) == 3
    assert data["snapshot"]["iv_rank"] is not None
    assert 0.0 <= data["points"][-1]["iv_rank"] <= 100.0
    assert "轻量" in (data.get("note") or "") or "聚合" in (data.get("note") or "")


def test_etf_iv_rank_falls_back_to_chain_rows(monkeypatch):
    stamps = ["2026-08-01 15:00:00", "2026-08-02 15:00:00"]
    by_ts = {
        ts: [
            {
                "month": "202609",
                "strike": 4.5,
                "iv": 0.18,
                "expire_date": "2026-09-23",
                "underlying_price": 4.5,
            }
        ]
        for ts in stamps
    }
    monkeypatch.setattr("app.services.gex_history.build_etf_options_surface_history", lambda *_a, **_k: {})
    monkeypatch.setattr("app.services.etf_options_clickhouse.etf_options_ch_enabled", lambda: True)
    monkeypatch.setattr("app.services.etf_options_clickhouse.ch_ping", lambda: True)
    monkeypatch.setattr(
        "app.services.etf_options_clickhouse.list_playback_timestamps",
        lambda *_args, **_kwargs: stamps,
    )
    monkeypatch.setattr(
        "app.services.etf_options_clickhouse.fetch_underlying_series",
        lambda *_args, **_kwargs: {ts: 4.5 for ts in stamps},
    )
    monkeypatch.setattr(
        "app.services.etf_options_clickhouse.fetch_near_month_atm_iv_series",
        lambda *_args, **_kwargs: ({}, {"source": "empty"}),
    )
    monkeypatch.setattr(
        "app.services.etf_options_clickhouse.fetch_option_chain_rows_at_timestamps",
        lambda *_args, **_kwargs: (by_ts, {"source": "mock"}),
    )
    data = ivr.build_etf_options_iv_rank_history("510050", bars=3)
    assert len(data["points"]) == 2
    assert data["points"][0]["atm_iv"] == 0.18


def test_futures_iv_rank_history_uses_realized_vol(monkeypatch):
    closes = [100.0 + i * 0.2 for i in range(50)]
    rows = [
        {"ts": f"2026-01-{i+1:02d} 15:00:00", "date": f"2026-01-{i+1:02d}", "label": f"2026-01-{i+1:02d}", "close": c, "underlying": c}
        for i, c in enumerate(closes)
    ]
    monkeypatch.setattr(
        "app.services.cn_derivatives_futures_options_history._underlying_daily_bars",
        lambda root, **kwargs: rows,
    )
    data = ivr.build_futures_options_iv_rank_history("IF", bars=20)
    assert data["proxy"] == "realized_vol"
    assert data["mode"] == "daily"
    assert data["points"]
    assert data["snapshot"]["iv_rank"] is not None


def test_is_iv_rank_chart():
    assert ivr.is_iv_rank_chart("options.ivRank")
    assert ivr.is_iv_rank_chart("options.iv_rank")
    assert not ivr.is_iv_rank_chart("options.iv")
