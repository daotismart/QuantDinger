# GEX + LSP + Kelly Short Strangle（纯期权）

期权卖方策略分工：

1. **GEX wall** 决定 **安全行权价**（call wall / put wall 附近卖出宽跨式）。
2. **高 IV** 过滤：ATM IV rank 达阈值才卖权（权利金偏贵时做空波动）。
3. **Kelly（权利金 1:1）** 决定 **基础张数 / 投入比例**；超出 `max_fraction` / `max_lots` 做风控封顶。
4. **LSP** 决定 **方向 delta 敞口**，用 call/put 张数 skew 表达，**不交易现货**。

## 规则摘要

| 模块 | 作用 |
|------|------|
| GEX walls | 选 OTM call≈call wall、OTM put≈put wall；优先现货在墙内开仓 |
| High IV | `iv_rank ≥ iv_rank_min` 才开仓 |
| Kelly | `f* = 2p − 1`（盈亏比按权利金 1:1）；预算不足一手则跳过 |
| Risk control | `f*` 与张数硬顶；超限 clamp，不追加杠杆 |
| LSP score | `score > 0` 偏多 → 多卖 put / 少卖 call；`score < 0` 相反 |
| Spot | **不下单**；标的仅用于 LSP / wall / IV 代理信号 |
| 退出 | 破墙、DTE 下限、最长持有、期权腿被 skew 平光 |

## Files

| Path | Role |
|------|------|
| `docs/examples/strategy_v2_gex_lsp_short_strangle.py` | Strategy API V2 template (IDE / sandbox) |
| `backend_api_python/app/services/gex_lsp_strangle/` | Research engine (GEX, LSP, Kelly, daily backtest) |
| `backend_api_python/scripts/backtest_gex_lsp_short_strangle.py` | CLI backtest on exported CH CSVs |
| `docs/reports/GEX_LSP_KELLY_STRANGLE_510050.md` | Latest 510050 research result |

## Research backtest (510050)

```bash
PYTHONPATH=backend_api_python python backend_api_python/scripts/backtest_gex_lsp_short_strangle.py \
  --data-dir tmp/gex_lsp_strangle --underlying 510050
```

## Notes

- Strategy V2 sandbox needs explicit listed option codes; replace placeholders before live use.
- Full historical wall selection + chain IV rank is done in the research engine (multi-contract panel).
- V2 template uses realized-vol rank as an IV proxy when chain IV is unavailable.
