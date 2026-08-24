# GEX + LSP Dynamic Short Strangle

Sell a **wide strangle** when:

1. **LSP** confirms non-directional exposure (neutral / mixed regime).
2. Spot sits between **GEX put wall** and **call wall**.
3. Strike selection uses the walls themselves (OTM call near call wall, OTM put near put wall).

Then **delta-hedge** residual exposure in the underlying ETF and exit on wall breach, LSP direction flip, DTE floor, or max hold.

## Files

| Path | Role |
|------|------|
| `docs/examples/strategy_v2_gex_lsp_short_strangle.py` | Strategy API V2 template (IDE / sandbox) |
| `backend_api_python/app/services/gex_lsp_strangle/` | Research engine (LSP, GEX walls, daily backtest) |
| `backend_api_python/scripts/backtest_gex_lsp_short_strangle.py` | CLI backtest on exported CH CSVs |
| `docs/reports/GEX_LSP_SHORT_STRANGLE_510050.md` | Latest 510050 research result |

## Research backtest (510050)

```bash
PYTHONPATH=backend_api_python python backend_api_python/scripts/backtest_gex_lsp_short_strangle.py \
  --data-dir tmp/gex_lsp_strangle --underlying 510050
```

Data export (production ClickHouse `etf_options`):

- `opt_underlying_daily`
- `opt_contracts_daily` ⨝ `opt_analytics_daily`
- EOD OI from `opt_quotes_bar_1m`

## Notes

- Strategy V2 sandbox needs explicit listed option codes; replace placeholders before live use.
- Full historical wall selection is done in the research engine (multi-contract panel), not in the single-symbol V2 template.
