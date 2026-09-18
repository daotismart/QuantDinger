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


def test_weighted_avg():
    rows = [
        {"weight_pct": 50, "pe_ratio": 10, "profit_margin": 20},
        {"weight_pct": 30, "pe_ratio": 20, "profit_margin": 10},
        {"weight_pct": 20, "pe_ratio": None, "profit_margin": 30},
    ]
    assert metrics._weighted_avg(rows, "pe_ratio") == 13.75
    assert metrics._weighted_avg(rows, "profit_margin") == 19.0


def test_holdings_profit_metrics_aggregates(monkeypatch):
    class _FakeFrame:
        empty = False

        def iterrows(self):
            return iter(
                [
                    (
                        0,
                        {
                            "股票代码": "600519",
                            "股票名称": "贵州茅台",
                            "占净值比例": 10.0,
                            "持股数": 100,
                            "持仓市值": 1_000_000,
                            "季度": "2024-12-31",
                        },
                    ),
                    (
                        1,
                        {
                            "股票代码": "000858",
                            "股票名称": "五粮液",
                            "占净值比例": 5.0,
                            "持股数": 200,
                            "持仓市值": 500_000,
                            "季度": "2024-12-31",
                        },
                    ),
                ]
            )

        def __len__(self):
            return 2

    class FakeAk:
        def fund_portfolio_hold_em(self, symbol, date):
            return _FakeFrame()

    monkeypatch.setattr(metrics, "_cache_get", lambda key: None)
    monkeypatch.setattr(metrics, "_cache_set", lambda *a, **k: None)
    monkeypatch.setattr(metrics, "_ak", lambda: FakeAk())
    monkeypatch.setattr(
        metrics,
        "_load_constituent_base_rows",
        lambda code6: (
            [
                {
                    "code": "600519",
                    "name": "贵州茅台",
                    "weight_pct": 10.0,
                    "shares": 100,
                    "market_value": 1_000_000,
                    "quarter": "2024-12-31",
                },
                {
                    "code": "000858",
                    "name": "五粮液",
                    "weight_pct": 5.0,
                    "shares": 200,
                    "market_value": 500_000,
                    "quarter": "2024-12-31",
                },
            ],
            "fund_portfolio_hold_em",
            "2024-12-31",
        ),
    )

    def _snap(code):
        if metrics._code6(code) == "600519":
            return {
                "net_profit": 100.0,
                "profit_margin": 20.0,
                "pe_ratio": 10.0,
                "market_cap": 2_000_000.0,
            }
        return {
            "net_profit": 50.0,
            "profit_margin": 10.0,
            "pe_ratio": 20.0,
            "market_cap": 800_000.0,
        }

    monkeypatch.setattr(metrics, "_stock_constituent_snapshot", _snap)

    out = metrics._holdings_profit_metrics("510300", top_n=2)
    assert out["holdings_count"] == 2
    assert len(out["holdings"]) == 2
    assert out["constituent_market_value_sum"] == 1_500_000.0
    assert out["constituent_market_cap_sum"] == 2_800_000.0
    assert out["constituent_profit_sum"] == 150.0
    assert out["avg_pe"] == 13.33
    assert out["avg_profit_margin"] == 16.67


def test_load_constituent_base_rows_prefers_index(monkeypatch):
    monkeypatch.setattr(metrics, "_benchmark_index_code", lambda code6: "000300")
    monkeypatch.setattr(
        metrics,
        "_load_index_constituent_rows",
        lambda index_code: [
            {"code": "600519", "name": "贵州茅台", "weight_pct": 5.0, "quarter": "000300 index 2026-07-31"}
        ],
    )
    monkeypatch.setattr(metrics, "_load_fund_portfolio_rows", lambda code6: [])
    rows, source, _ = metrics._load_constituent_base_rows("510300")
    assert source == "index_stock_cons_weight_csindex"
    assert len(rows) == 1
    assert rows[0]["code"] == "600519"


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
            "constituent_market_value_sum": 9e8,
            "constituent_market_cap_sum": 1.2e11,
            "avg_pe": 15.5,
            "avg_profit_margin": 12.3,
            "pe_coverage": 3,
            "margin_coverage": 3,
            "market_cap_coverage": 3,
            "holdings_count": 3,
            "holdings_quarter": "2024-12-31",
            "holdings": [
                {
                    "code": "600519",
                    "name": "贵州茅台",
                    "weight_pct": 10.0,
                    "market_value": 1e8,
                    "net_profit": 1e10,
                    "pe_ratio": 20.0,
                    "profit_margin": 15.0,
                    "market_cap": 2e11,
                }
            ],
            "holdings_sample": [],
            "source": "mock",
        },
    )

    out = metrics.enrich_etf_metrics("510300", {"code": "510300", "price": 4.2, "volume": 0})
    assert out["scale"] == 2e9 * 4.2
    assert out["amount"] == 888
    assert out["total_fee_pct"] == 0.6
    assert out["constituent_profit_sum"] == 12345
    assert out["constituent_market_value_sum"] == 9e8
    assert out["avg_pe"] == 15.5
    assert len(out["holdings"]) == 1
