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

Auth: Vue stores `Access-Token` with the `store` library (`JSON.stringify(jwt)`).
The inspect page must unwrap that quoted JWT; sending the raw quoted value
as `Authorization: Bearer "eyJ..."` yields HTTP 401.
