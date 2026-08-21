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
