# ETF / Futures derivatives chart layout patch

QuantDinger-Vue push is blocked from this agent environment. Apply on the Vue repo:

```bash
cd QuantDinger-Vue
git apply ../tmp-frontend-patches/etf-derivatives-single-col-fullscreen-gex-labels.patch
# or replace files:
# cp ../tmp-frontend-patches/etf-derivatives.vue src/views/market-composite-analysis/
# cp ../tmp-frontend-patches/futures-derivatives.vue src/views/market-composite-analysis/
```

Changes:
1. Charts render as a single column (one chart per row).
2. Each chart has a fullscreen toggle.
3. GEX distribution markLines label Price / Flip / Walls / Pin with numeric values.
