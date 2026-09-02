# GEX + LSP Short Strangle（纯期权对冲）

期权卖方策略分工：

1. **LSP** 决定组合 **净 delta 方向与大小**（连续分 `lsp_delta_score` ∈ [-1,1]）。
2. **GEX wall** 决定 **call / put 行权价**（call wall / put wall 附近卖出）。
3. **动态对冲（仅期权）**：用 call/put 张数 skew 逼近 LSP 目标 delta，**不交易现货/ETF**。

## 规则摘要

| 模块 | 作用 |
|------|------|
| LSP score | `score > 0` 偏多 → 多卖 put / 少卖 call；`score < 0` 相反 |
| GEX walls | 选 OTM call≈call wall、OTM put≈put wall；优先现货在墙内开仓 |
| Option hedge | `lsp_option_skew_lots` + 按目标 delta 选最优 call/put 张数组合 |
| Spot | **不下单**；标的仅用于 LSP / wall / 价格信号 |
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

## Notes

- Strategy V2 sandbox needs explicit listed option codes; replace placeholders before live use.
- Full historical wall selection is done in the research engine (multi-contract panel), not in the single-symbol V2 template.
