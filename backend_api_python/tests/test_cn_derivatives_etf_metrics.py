"""Unit tests for ETF fund metrics enrichment and history series."""

from __future__ import annotations

import app.services.cn_derivatives_etf_metrics as metrics


def test_code6_and_safe_float():
    assert metrics._code6("510300.SH") == "510300"
    assert metrics._code6("sh510300") == "510300"
    assert metrics._safe_float("1,234.56") == 1234.56
    assert metrics._safe_float("--") is None
    assert metrics._parse_fee_pct("0.50%") == 0.5


def test_build_etf_metrics_history_shape(monkeypatch):
    monkeypatch.setattr(
        metrics,
        "enrich_etf_metrics",
        lambda code, etf_row=None: {
            "code": "510300",
            "price": 4.2,
            "volume": 1000,
            "amount": 50000,
            "shares": 1e10,
            "scale": 4.2e10,
            "total_fee_pct": 0.6,
            "management_fee_pct": 0.5,
            "custodian_fee_pct": 0.1,
            "constituent_profit_sum": 1.2e11,
            "constituent_profit_weighted": 9e10,
            "holdings_count": 12,
            "holdings_quarter": "2024-12-31",
        },
    )
    monkeypatch.setattr(
        metrics,
        "_load_etf_ohlcv_history",
        lambda code6, *, days: [
            {"date": "2024-01-02", "price": 4.0, "volume": 10, "amount": 100},
            {"date": "2024-01-03", "price": 4.1, "volume": 12, "amount": 120},
        ],
    )

    data = metrics.build_etf_metrics_history("510300.SH", chart_key="etf.metrics", days=30, frequency="day")
    assert data["root"] == "510300"
    assert data["mode"] == "daily"
    assert data["chart_key"] == "etf.metrics"
    assert len(data["points"]) == 2
    assert data["points"][0]["scale"] == 4.0 * 1e10
    assert data["points"][0]["fee_pct"] == 0.6
    assert data["points"][0]["constituent_profit_sum"] == 1.2e11
    assert data["metrics"]["scale"] == 4.2e10
    assert "新浪" in data["note"]


def test_metrics_history_estimates_amount_from_lot_volume(monkeypatch):
    monkeypatch.setattr(
        metrics,
        "enrich_etf_metrics",
        lambda code, etf_row=None: {"shares": 1e9, "total_fee_pct": 0.2, "constituent_profit_sum": None},
    )
    monkeypatch.setattr(
        metrics,
        "_load_etf_ohlcv_history",
        lambda code6, *, days: [{"date": "2026-09-17", "price": 3.0, "volume": 1000, "amount": None}],
    )
    data = metrics.build_etf_metrics_history("510050", chart_key="etf.volume", days=30)
    assert data["points"][0]["amount"] == 3.0 * 1000 * 100
    assert data["points"][0]["scale"] == 3.0 * 1e9


def test_fill_holding_market_values_from_scale_and_weight():
    out = metrics._fill_holding_market_values(
        {
            "scale": 1000.0,
            "holdings": [
                {"code": "600000", "weight_pct": 10.0, "market_value": None},
                {"code": "600519", "weight_pct": 5.0},
            ],
            "holdings_sample": [],
        }
    )
    assert out["holdings"][0]["market_value"] == 100.0
    assert out["holdings"][1]["market_value"] == 50.0
    assert out["constituent_market_value_sum"] == 150.0


def test_enrich_index_metrics_uses_index_constituents(monkeypatch):
    monkeypatch.setattr(metrics, "_cache_get", lambda key: None)
    monkeypatch.setattr(metrics, "_cache_set", lambda *a, **k: None)
    monkeypatch.setattr(
        metrics,
        "_load_index_constituent_rows",
        lambda code: [
            {"code": "600519", "name": "贵州茅台", "weight_pct": 10.0, "market_value": None},
            {"code": "601318", "name": "中国平安", "weight_pct": 5.0, "market_value": None},
        ],
    )
    captured = {}

    def _snap(codes, **kwargs):
        captured.update(kwargs)
        return {
            "600519": {"net_profit": 100.0, "pe_ratio": 20.0, "profit_margin": 25.0, "market_cap": 1e12},
            "601318": {"net_profit": 50.0, "pe_ratio": 10.0, "profit_margin": 15.0, "market_cap": 5e11},
        }

    monkeypatch.setattr(metrics, "_enrich_constituent_snapshots", _snap)
    out = metrics.enrich_index_metrics("000016.SH")
    assert captured.get("live") is False
    assert out["holdings_count"] == 2
    assert out["holdings"][0]["market_value"] == 1e12
    assert out["constituent_market_cap_sum"] == 1.5e12
    assert out["avg_pe"] == 16.67
    assert "total_fee_pct" not in out
    assert "scale" not in out


def test_enrich_constituent_snapshots_live_false_skips_remote(monkeypatch):
    called = {"live": 0}
    complete = {
        "net_profit": 100.0,
        "pe_ratio": 20.0,
        "profit_margin": 25.0,
        "market_cap": 1e12,
        "price": 1800.0,
    }

    def _cache_get(key):
        if str(key).endswith(":600519"):
            return complete
        if str(key).endswith(":601318"):
            return {"net_profit": 50.0}
        return None

    monkeypatch.setattr(metrics, "_cache_get", _cache_get)
    monkeypatch.setattr(metrics, "_cache_set", lambda *a, **k: None)

    def _live(code):
        called["live"] += 1
        raise AssertionError(f"live snapshot should not run for {code}")

    monkeypatch.setattr(metrics, "_stock_constituent_snapshot", _live)
    out = metrics._enrich_constituent_snapshots(["600519", "601318"], live=False)
    assert called["live"] == 0
    assert out["600519"]["market_cap"] == 1e12
    assert out["601318"]["net_profit"] == 50.0


def test_enrich_index_metrics_prefers_stale_bundle(monkeypatch):
    stale = {"code": "000016", "holdings_count": 50, "avg_pe": 11.0, "holdings": [{"code": "600519"}]}
    monkeypatch.setattr(metrics, "_cache_get", lambda key: stale if "metrics_bundle" in key else None)

    def _boom(*a, **k):
        raise AssertionError("should not rebuild when stale bundle exists")

    monkeypatch.setattr(metrics, "_load_index_constituent_rows", _boom)
    monkeypatch.setattr(metrics, "_enrich_constituent_snapshots", _boom)
    out = metrics.enrich_index_metrics("000016.SH")
    assert out["avg_pe"] == 11.0
    assert out["holdings_count"] == 50


def test_build_index_metrics_history_shape(monkeypatch):
    monkeypatch.setattr(
        metrics,
        "enrich_index_metrics",
        lambda symbol: {"avg_pe": 11.0, "holdings_count": 50, "constituent_profit_sum": 9.0, "constituent_profit_coverage": 50},
    )
    monkeypatch.setattr(
        metrics,
        "_query_index_ohlcv",
        lambda symbol, *, days: [
            {"date": "2026-09-16", "price": 2800.0, "volume": 10},
            {"date": "2026-09-17", "price": 2860.0, "volume": 12},
        ],
    )
    monkeypatch.setattr(
        metrics,
        "_fetch_index_tencent_daily",
        lambda symbol, *, days: [
            {"date": "2026-09-16", "price": 2800.0, "volume": 10, "amount": 1.1e11},
            {"date": "2026-09-17", "price": 2860.0, "volume": 12, "amount": 1.2e11},
        ],
    )
    data = metrics.build_index_metrics_history("000016.SH", chart_key="index.price", days=30)
    assert data["root"] == "000016.SH"
    assert len(data["points"]) == 2
    assert data["points"][-1]["price"] == 2860.0
    assert data["points"][-1]["avg_pe"] == 11.0
    assert data["points"][-1]["amount"] == 1.2e11
    assert "手" in data["note"]
    assert "成交额" in data["note"]


def test_bar_date_cn_uses_shanghai_session():
    assert metrics._bar_date_cn(1789660800) == "2026-09-18"
    assert metrics._bar_date_cn(1789574400) == "2026-09-17"


def test_index_tx_code_uses_board():
    assert metrics._index_tx_code("000016.SH") == "sh000016"
    assert metrics._index_tx_code("399006.SZ") == "sz399006"
    assert metrics._index_tx_code("000300.SH") == "sh000300"


def test_parse_tencent_index_quote_volume_and_amount():
    parts = [""] * 60
    parts[3] = "2860.77"
    parts[6] = "39360945"
    parts[35] = "2860.77/39360945/138366086012"
    parts[36] = "39360945"
    parts[37] = "13836609"
    out = metrics._parse_tencent_index_quote(parts)
    assert out["volume"] == 39360945
    assert out["amount"] == 138366086012


def test_parse_tencent_index_kline_amount_from_wan():
    row = ["2026-09-18", "2857.05", "2860.77", "2870.71", "2854.05", "39360945.00", {}, "0.24", "13836608.60"]
    out = metrics._parse_tencent_index_kline_row(row)
    assert out["date"] == "2026-09-18"
    assert out["volume"] == 39360945
    assert abs(out["amount"] - 138366086000) < 1


def test_reconcile_index_activity_matches_local_and_tencent():
    out = metrics.reconcile_index_activity(
        local_volume=39360945,
        live_volume=39360945,
        live_amount=138366086012,
        hist_amount=138366086000,
        hist_volume_shares=3936094500,
        live_source="tencent_quote",
    )
    assert out["volume"] == 39360945
    assert out["volume_shares"] == 3936094500
    assert out["amount"] == 138366086012
    assert out["checked"] is True
    statuses = {c["field"]: c["status"] for c in out["checks"]}
    assert statuses["volume"] == "match"
    assert statuses["amount"] == "match"
    assert statuses["volume_shares"] == "match"


def test_compute_etf_index_share_pct():
    assert metrics.compute_etf_index_share_pct(2.32e10, 9e12) == 0.2578
    assert metrics.compute_etf_index_share_pct(None, 9e12) is None
    assert metrics.compute_etf_index_share_pct(100, 0) is None


def test_build_index_etf_shares_marks_primary(monkeypatch):
    monkeypatch.setattr(metrics, "load_etf_scale", lambda code: 1e10 if code == "510050" else 5e9)
    out = metrics.build_index_etf_shares(["510050", "510300"], index_market_cap=1e12, primary="510050")
    assert out["primary"] == "510050"
    assert out["etfs"][0]["primary"] is True
    assert out["etfs"][0]["share_pct"] == 1.0
    assert out["etfs"][1]["etf_group_share_pct"] == 33.33
    assert out["combined_share_pct"] == 1.5


def test_compute_option_greek_notionals():
    out = metrics.compute_option_greek_notionals(
        {"delta": 1000.0, "gamma": 20.0, "vega": 50.0, "theta": -8.0},
        spot=3.0,
        net_gex=75.0,
    )
    assert out["delta_notional"] == 3000.0
    assert out["gamma_notional"] == 75.0
    assert out["vega_notional"] == 50.0
    assert out["theta_notional"] == -8.0


def test_option_notionals_from_options_panel_includes_capital():
    panel = {
        "greeks": {"delta": 10.0, "gamma": 2.0, "vega": 4.0, "theta": -1.0},
        "underlying": 2.5,
        "gex_summary": {"net_gex": 8.0},
        "multiplier": 10000,
        "capital_curve": {
            "total": {
                "premium_total": 100.0,
                "margin_total": 300.0,
                "margin_short_total": 300.0,
                "margin_long_total": 100.0,
                "time_value_total": 40.0,
            }
        },
    }
    out = metrics.option_notionals_from_options_panel(panel)
    assert out["delta_notional"] == 25.0
    assert out["premium_total"] == 100.0
    assert out["margin_total"] == 300.0
    assert out["time_value_total"] == 40.0


def test_merge_option_notionals_sums_etfs():
    rows = [
        {
            "etf_code": "510300",
            "etf_name": "沪深300ETF",
            "primary": True,
            "spot": 4.1,
            "delta_notional": 10.0,
            "premium_total": 100.0,
            "margin_total": 200.0,
            "time_value_total": 30.0,
        },
        {
            "etf_code": "159919",
            "etf_name": "沪深300ETF",
            "primary": False,
            "delta_notional": 5.0,
            "premium_total": 50.0,
            "margin_total": 80.0,
            "time_value_total": 20.0,
        },
    ]
    out = metrics.merge_option_notionals(rows)
    assert out["delta_notional"] == 15.0
    assert out["premium_total"] == 150.0
    assert out["margin_total"] == 280.0
    assert out["time_value_total"] == 50.0
    assert out["etf_code"] == "510300"
    assert out["etf_count"] == 2


def test_estimate_etf_amount_uses_lot_volume():
    # Local/EM 成交量单位是手（100 股）。
    assert metrics.estimate_etf_amount(2.975, 4851416) == 2.975 * 4851416 * 100
    assert metrics.estimate_etf_amount(0, 100) is None
    assert metrics.estimate_etf_amount(3.0, None) is None


def test_enrich_etf_metrics_merges_spot_and_fees(monkeypatch):
    spot = {
        "price": 4.5,
        "volume": 99,
        "amount": 888,
        "shares": 2e9,
        "scale": None,
        "source": "fund_etf_spot_em",
    }
    monkeypatch.setattr(metrics, "_cache_get", lambda key: None)
    monkeypatch.setattr(metrics, "_cache_set", lambda *a, **k: None)
    monkeypatch.setattr(metrics, "_spot_em_row_from_cache", lambda code6: dict(spot))
    monkeypatch.setattr(metrics, "_kick_spot_em_refresh", lambda: None)
    monkeypatch.setattr(
        metrics,
        "_fee_metrics",
        lambda code6: {
            "management_fee_pct": 0.5,
            "custodian_fee_pct": 0.1,
            "total_fee_pct": 0.6,
            "source": "fund_fee_em",
        },
    )
    monkeypatch.setattr(
        metrics,
        "_holdings_profit_metrics",
        lambda code6, **kwargs: {
            "constituent_profit_sum": 12345,
            "constituent_profit_weighted": 1000,
            "constituent_profit_coverage": 3,
            "holdings_count": 3,
            "holdings_quarter": "2024-12-31",
            "holdings_sample": [],
            "source": "mock",
        },
    )

    out = metrics.enrich_etf_metrics("510300", {"code": "510300", "price": 4.2, "volume": 0})
    assert out["scale"] == 2e9 * 4.2
    assert out["amount"] == 888
    assert out["total_fee_pct"] == 0.6
    assert out["constituent_profit_sum"] == 12345
