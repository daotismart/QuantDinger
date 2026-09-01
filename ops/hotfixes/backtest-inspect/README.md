# Backtest process visualization

Adds graphical panels for **decision process**, **fills**, and **positions**
under the Backtest Center result view.

```bash
python3 ops/hotfixes/backtest-inspect/patch_backtest_inspect.py
docker compose -f docker-compose.yml -f docker-compose.production.yml \
  -f docker-compose.hotfix.yml up -d --no-deps frontend
```

The page is also available at `/backtest-inspect.html?runId=<id>`.
It reads `GET /api/backtest/get` and can rebuild series from research runs
that only stored trades + equity.
