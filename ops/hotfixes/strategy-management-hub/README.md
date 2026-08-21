# Strategy management hub (Vue)

Adds:
- Menu group **Strategy Management** with hub / develop / backtest / ranking
- `/strategy-manage` lifecycle hub
- `/backtest-ranking` personal backtest leaderboard UI
- IDE deep links `?action=publish|versions`

Apply this patch in the private QuantDinger-Vue repo, rebuild the frontend
image, then deploy. Backend companion change lives in the main QuantDinger
repo (`GET /api/backtest/ranking`).

If locale files fail to parse after applying the patch, run
`python3 fix_locale_commas.py` in this directory against the Vue
`src/locales/lang/{zh-CN,en-US}.js` paths (adds the missing trailing
comma before the new `strategyManage.*` keys).


## Strategy inventory (2026-08-21)

Backend:
- `GET /api/strategies/inventory` — list current-user script strategies with
  status/visibility/asset type/versions/backtest/live summaries for the
  Strategy Management page table (sortable/filterable in UI).

Mount on production (read-only rootfs):
- `ops/hotfixes/strategy_inventory.py` -> `/app/app/services/strategy_inventory.py`
- `ops/hotfixes/script_source_routes.py` -> `/app/app/routes/script_source_routes.py`
