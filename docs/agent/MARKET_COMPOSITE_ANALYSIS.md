# Market composite analysis (frontend)

## Summary

Adds a **市场综合分析** (Market Analysis) menu with two pages:

1. **期货及衍生品分析** — tabs: 现货 / 期货 / 期权  
   Markets: `CNStock` / `CNFutures` / `CNFuturesOptions`
2. **ETF及衍生品分析** — tabs: 指数 / ETF / ETF期权  
   Markets: `CNIndexFutures` / `CNStock+USStock+HKStock` / `CNIndexOptions`

Implementation lives in the private Vue repo (`QuantDinger-Vue`):

- Routes: `/market-composite/futures-derivatives`, `/market-composite/etf-derivatives`
- Views: `src/views/market-composite-analysis/`
- AI analysis scoped via `allowedMarkets` / `marketLabelOverrides` / `presetMarket` props on `ai-analysis` + `CopilotWorkbench`

No new backend routes are required; analysis reuses `/api/fast-analysis` and existing market modules.

## Deploy note

After rebuilding the frontend image, realign `ops/hotfixes/fe-compat/index.html` entry hashes with the image `index.html` (no-store metas), or login can break on stale JS.
