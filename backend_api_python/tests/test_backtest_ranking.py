"""Unit tests for backtest ranking scores."""

from app.services.backtest_ranking import dedupe_best, score_metrics, score_run_row


def test_score_metrics_prefers_strong_risk_adjusted_returns():
    strong = score_metrics(
        total_return=0.25,
        sharpe=1.8,
        max_drawdown=-0.08,
        profit_factor=2.2,
        total_trades=40,
        strategy_name="Trend Following Pack Alpha",
    )
    weak = score_metrics(
        total_return=-0.10,
        sharpe=-0.5,
        max_drawdown=-0.35,
        profit_factor=0.6,
        total_trades=12,
        strategy_name="Other Strategy",
    )
    assert strong["score"] > weak["score"]
    assert strong["family"] == "Trend Pack"
    assert strong["flag"] == "ok"


def test_score_metrics_penalizes_no_trades_and_outliers():
    empty = score_metrics(
        total_return=0.0,
        sharpe=0.0,
        max_drawdown=0.0,
        profit_factor=0.0,
        total_trades=0,
        strategy_name="Idle",
    )
    outlier = score_metrics(
        total_return=12.0,
        sharpe=40.0,
        max_drawdown=-0.01,
        profit_factor=9.0,
        total_trades=3,
        strategy_name="Exploded",
    )
    normal = score_metrics(
        total_return=0.30,
        sharpe=1.5,
        max_drawdown=-0.10,
        profit_factor=1.8,
        total_trades=20,
        strategy_name="Normal",
    )
    assert empty["flag"] == "no_trades"
    assert outlier["flag"] == "extreme_outlier"
    assert empty["score"] < 40
    assert outlier["score"] < normal["score"]


def test_score_run_row_reads_result_json_and_percent_forms():
    row = score_run_row(
        {
            "id": 9,
            "strategy_name": "[UNIFIED-20260820] Turtle Trend",
            "market": "Crypto",
            "symbol": "BTC/USDT",
            "timeframe": "1h",
            "initial_capital": 10000,
            "result_json": {
                "totalReturn": 12.5,
                "sharpeRatio": 1.2,
                "maxDrawdown": -8.5,
                "profitFactor": 1.7,
                "totalTrades": 18,
                "winRate": 55,
            },
        }
    )
    assert row["strategy_name"] == "Turtle Trend"
    assert abs(row["total_return"] - 0.125) < 1e-9
    assert abs(row["max_drawdown"] + 0.085) < 1e-9
    assert abs(row["win_rate"] - 0.55) < 1e-9
    assert row["family"] == "CTA Classic"
    assert row["run_id"] == 9


def test_dedupe_best_keeps_highest_score_per_strategy_timeframe():
    rows = [
        score_metrics(
            total_return=0.10,
            sharpe=1.0,
            max_drawdown=-0.1,
            profit_factor=1.2,
            total_trades=10,
            strategy_name="A",
            timeframe="1h",
            run_id=1,
        ),
        score_metrics(
            total_return=0.30,
            sharpe=1.5,
            max_drawdown=-0.1,
            profit_factor=1.8,
            total_trades=10,
            strategy_name="A",
            timeframe="1h",
            run_id=2,
        ),
        score_metrics(
            total_return=0.20,
            sharpe=1.2,
            max_drawdown=-0.1,
            profit_factor=1.4,
            total_trades=10,
            strategy_name="A",
            timeframe="4h",
            run_id=3,
        ),
    ]
    ranked = dedupe_best(rows)
    assert len(ranked) == 2
    assert ranked[0]["run_id"] == 2
    assert {item["timeframe"] for item in ranked} == {"1h", "4h"}
