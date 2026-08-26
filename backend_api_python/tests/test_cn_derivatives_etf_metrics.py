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


def test_enrich_etf_metrics_merges_spot_and_fees(monkeypatch):
    monkeypatch.setattr(metrics, "_cache_get", lambda key: None)
    monkeypatch.setattr(metrics, "_cache_set", lambda *a, **k: None)
    monkeypatch.setattr(
        metrics,
        "_spot_em_row",
        lambda code6: {
            "price": 4.5,
            "volume": 99,
            "amount": 888,
            "shares": 2e9,
            "scale": None,
            "source": "fund_etf_spot_em",
        },
    )
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
