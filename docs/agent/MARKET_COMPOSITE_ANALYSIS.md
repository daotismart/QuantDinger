# Market composite analysis (frontend)

## Summary

Adds a **市场综合分析** (Market Analysis) menu with two pages:

1. **期货及衍生品分析** — tabs: 现货 / 期货 / 期权  
2. **ETF及衍生品分析** — tabs: 指数 / ETF / ETF期权  

Implementation lives in the private Vue repo (`QuantDinger-Vue`):

- Routes: `/market-composite/futures-derivatives`, `/market-composite/etf-derivatives`
- Views: `src/views/market-composite-analysis/`

## Futures & derivatives workflow

1. Select a futures product (`root`, e.g. `M` / `RB`).
2. **现货** tab: spot price, near/dominant contracts, basis, short analysis text.
3. **期货** tab: term structure, basis, monthly volume/OI, monthly options settled capital.
4. **期权** tab: portfolio Greeks, GEX summary (flip / call wall / put wall / pin), GEX distribution, IV smile, Max Pain.

Backend APIs (login required):

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/api/cn-derivatives/products` | Product catalog |
| GET | `/api/cn-derivatives/spot?root=` | Spot panel |
| GET | `/api/cn-derivatives/futures?root=` | Futures panel |
| GET | `/api/cn-derivatives/options?root=&month=` | Options panel |
| GET | `/api/cn-derivatives/overview?root=` | Combined (slow; prefer per-tab) |

Service: `backend_api_python/app/services/cn_derivatives_analytics.py`  
Data: AkShare spot board + Sina commodity futures/options. Index futures/options may degrade when Sina commodity feeds are unavailable.

ETF page still scopes AI analysis via `allowedMarkets` / `presetMarket` on the shared shell.

## Deploy note

After rebuilding the frontend image, realign `ops/hotfixes/fe-compat/index.html` entry hashes with the image `index.html` (no-store metas), or login can break on stale JS.
