# GEX + LSP Delta-Targeted Short Strangle

期权卖方策略分工：

1. **LSP** 决定组合 **净 delta 方向与大小**（连续分 `lsp_delta_score` ∈ [-1,1]）。
2. **GEX wall** 决定 **call / put 行权价**（call wall / put wall 附近卖出）。
3. **动态对冲**：先用 call/put 张数 skew 实现部分方向敞口，再用 **现货** 把残差对冲到 LSP 目标 delta。

## 规则摘要

| 模块 | 作用 |
|------|------|
| LSP score | `score > 0` 偏多 → 多卖 put / 少卖 call，目标净 delta 为正；`score < 0` 相反 |
| GEX walls | 选 OTM call≈call wall、OTM put≈put wall；优先现货在墙内开仓 |
| Option skew | `lsp_option_skew_lots` 按 score 倾斜短腿张数 |
| Spot hedge | 残差 delta = 目标 − 期权账面 delta，超出 band 时买卖 ETF |
| 退出 | 破墙、DTE 下限、最长持有、期权腿被 skew 平光 |

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
