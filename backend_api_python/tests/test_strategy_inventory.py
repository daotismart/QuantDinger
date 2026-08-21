"""Unit tests for strategy inventory builders."""

from app.services.strategy_inventory import build_strategy_inventory


class _Cur:
    def __init__(self, batches):
        self._batches = list(batches)
        self._idx = 0

    def execute(self, *_args, **_kwargs):
        return None

    def fetchall(self):
        if self._idx >= len(self._batches):
            return []
        rows = self._batches[self._idx]
        self._idx += 1
        return rows

    def close(self):
        return None


class _Db:
    def __init__(self, batches):
        self._batches = batches

    def cursor(self):
        return _Cur(self._batches)

    def __enter__(self):
        return self

    def __exit__(self, *_exc):
        return False


def _batches():
    sources = [
        {
            "id": 1,
            "user_id": 7,
            "name": "Alpha Trend",
            "description": "trend follower",
            "asset_type": "script",
            "template_key": "cta",
            "visibility": "private",
            "status": "draft",
            "metadata": {"tags": ["cta", "trend"]},
            "created_at": "2026-01-01T00:00:00",
            "updated_at": "2026-01-02T00:00:00",
            "version_count": 3,
            "latest_version": 3,
        },
        {
            "id": 2,
            "user_id": 7,
            "name": "Mean Revert",
            "description": "",
            "asset_type": "portfolio_strategy",
            "template_key": "mr",
            "visibility": "public",
            "status": "published",
            "metadata": {},
            "created_at": "2026-01-01T00:00:00",
            "updated_at": "2026-01-03T00:00:00",
            "version_count": 1,
            "latest_version": 1,
        },
    ]
    backtests = [
        {
            "id": 11,
            "source_id": 1,
            "strategy_name": "Alpha Trend",
            "market": "Crypto",
            "symbol": "BTC/USDT",
            "timeframe": "1h",
            "start_date": "2024-01-01",
            "end_date": "2024-06-01",
            "initial_capital": 10000,
            "result_json": {
                "totalReturn": 0.25,
                "sharpeRatio": 1.5,
                "maxDrawdown": -0.1,
                "profitFactor": 1.8,
                "totalTrades": 40,
                "winRate": 0.55,
            },
            "created_at": "2026-01-02T00:00:00",
            "status": "success",
        }
    ]
    live = [
        {
            "id": 99,
            "strategy_name": "Alpha Live",
            "status": "running",
            "market_category": "Crypto",
            "symbol": "BTC/USDT",
            "timeframe": "1h",
            "trading_config": {"script_source_id": 1},
            "updated_at": "2026-01-04T00:00:00",
        }
    ]
    return [sources, backtests, live]


def test_build_strategy_inventory_filters_and_summaries(monkeypatch):
    monkeypatch.setattr(
        "app.services.strategy_inventory.get_db_connection",
        lambda: _Db(_batches()),
    )
    data = build_strategy_inventory(user_id=7, keyword="alpha")
    assert data["count"] == 1
    item = data["items"][0]
    assert item["id"] == 1
    assert item["version_count"] == 3
    assert item["backtest_count"] == 1
    assert item["live_count"] == 1
    assert item["live_running_count"] == 1
    assert item["best_score"] is not None
    assert item["best_return"] is not None

    monkeypatch.setattr(
        "app.services.strategy_inventory.get_db_connection",
        lambda: _Db(_batches()),
    )
    published = build_strategy_inventory(user_id=7, status="published")
    assert published["count"] == 1
    assert published["items"][0]["name"] == "Mean Revert"
