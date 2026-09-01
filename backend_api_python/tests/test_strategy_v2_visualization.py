import unittest

from app.services.strategy_v2.visualization import build_backtest_visualization


class StrategyV2VisualizationTests(unittest.TestCase):
    def test_v2_result_builds_decision_fill_and_position_series(self):
        viz = build_backtest_visualization({
            "protectionEvents": [{
                "time": "2026-01-03T00:00:00Z",
                "symbol": "USStock:SPY",
                "side": "long",
                "reason": "stop_loss",
                "triggerPrice": 99,
            }],
            "rebalanceRecords": [{"time": "2026-01-02T00:00:00Z", "filled": 2, "turnover": 0.1}],
            "orderLedger": [{
                "eventTime": "2026-01-02T00:00:00Z",
                "symbol": "USStock:SPY",
                "status": "rejected",
                "statusReason": "insufficient_cash",
                "requestedQuantity": 10,
            }],
            "closedTrades": [{
                "symbol": "USStock:SPY",
                "side": "long",
                "entry_time": "2026-01-01T00:00:00Z",
                "exit_time": "2026-01-03T00:00:00Z",
                "entry_price": 100,
                "exit_price": 99,
                "quantity": 2,
                "profit": -3,
                "close_reason": "stop_loss",
            }],
            "executions": [{
                "time": "2026-01-01T00:00:00Z",
                "symbol": "USStock:SPY",
                "side": "buy",
                "quantity": 2,
                "price": 100,
                "commission": 1,
                "status": "filled",
                "reason": "entry",
            }],
            "holdingSnapshots": [{
                "time": "2026-01-01T00:00:00Z",
                "cash": 8000,
                "grossExposure": 0.2,
                "netExposure": 0.2,
                "positions": {
                    "USStock:SPY": {
                        "quantity": 2,
                        "marketValue": 200,
                        "weight": 0.02,
                        "averageCost": 100,
                    }
                },
            }],
        })

        kinds = {row["kind"] for row in viz["decisionProcess"]}
        self.assertTrue({"enter", "exit", "protect", "rebalance", "rejected"} <= kinds)
        self.assertEqual(viz["summaries"]["fillCount"], 1)
        self.assertEqual(viz["positions"][0]["symbol"], "USStock:SPY")
        self.assertEqual(viz["positions"][0]["quantity"], 2)

    def test_research_result_reconstructs_fills_and_open_lots(self):
        viz = build_backtest_visualization({
            "equityCurve": [
                {"date": "2026-04-01", "equity": 1000000, "value": 1000000},
                {"date": "2026-04-15", "equity": 1100000, "value": 1100000},
                {"date": "2026-04-20", "equity": 1090000, "value": 1090000},
            ],
            "trades": [{
                "symbol": "CNStock:510050",
                "side": "short",
                "entryDate": "2026-04-01",
                "exitDate": "2026-04-15",
                "entryCredit": 0.12,
                "exitDebit": 0.04,
                "callLots": 120,
                "quantity": 120,
                "pnl": 100000,
                "reason": "take_profit",
            }],
        })

        self.assertGreaterEqual(viz["summaries"]["decisionCount"], 2)
        self.assertEqual(viz["summaries"]["fillCount"], 2)
        self.assertEqual(viz["fills"][0]["side"], "sell")
        open_on_first = next(row for row in viz["positions"] if row["time"].startswith("2026-04-01"))
        open_after_exit = next(row for row in viz["positions"] if row["time"].startswith("2026-04-20"))
        self.assertEqual(open_on_first["quantity"], 120)
        self.assertEqual(open_after_exit["quantity"], 0)

    def test_empty_result_is_safe(self):
        viz = build_backtest_visualization({})
        self.assertEqual(viz["summaries"]["decisionCount"], 0)
        self.assertEqual(viz["summaries"]["fillCount"], 0)
        self.assertEqual(viz["positions"], [])


if __name__ == "__main__":
    unittest.main()
