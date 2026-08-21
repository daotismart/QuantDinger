# Strategy management hub (Vue)

Adds:
- Menu group **Strategy Management** with hub / develop / backtest / ranking
- `/strategy-manage` lifecycle hub
- `/backtest-ranking` personal backtest leaderboard UI
- IDE deep links `?action=publish|versions`

Apply this patch in the private QuantDinger-Vue repo, rebuild the frontend
image, then deploy. Backend companion change lives in the main QuantDinger
repo (`GET /api/backtest/ranking`).
