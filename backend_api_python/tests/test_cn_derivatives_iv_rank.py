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
    monkeypatch.setattr(
        "app.services.gex_history.build_etf_options_surface_history",
        lambda root, **kwargs: {
            "root": "510050",
            "interval": "day",
            "bars": 3,
            "note": "ch",
            "near_month_iv_klines": [
                {"ts": "t1", "date": "2026-08-01", "label": "2026-08-01", "close": 0.15},
                {"ts": "t2", "date": "2026-08-02", "label": "2026-08-02", "close": 0.25},
                {"ts": "t3", "date": "2026-08-03", "label": "2026-08-03", "close": 0.20},
            ],
        },
    )
    data = ivr.build_etf_options_iv_rank_history("510050.SH", bars=3)
    assert data["chart_key"] == "options.ivRank"
    assert data["mode"] == "daily"
    assert data["proxy"] == "atm_iv"
    assert len(data["points"]) == 3
    assert data["snapshot"]["iv_rank"] is not None
    assert 0.0 <= data["points"][-1]["iv_rank"] <= 100.0


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
