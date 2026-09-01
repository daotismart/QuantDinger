# GEX + LSP + Kelly Short Strangle（纯期权）

期权卖方策略分工：

1. **GEX wall** 决定 **安全行权价**（call wall / put wall 附近卖出宽跨式）。
2. **高 IV** 过滤：ATM IV rank 达阈值才卖权（权利金偏贵时做空波动）。
3. **Kelly（权利金盈亏比 1:1）** 决定账户 **保证金占用比例** `f*=2p−1`，再换算可开张数；超出比例/`max_lots` 风控封顶。
4. **LSP** 单独决定 **净 delta 敞口**（按保证金预算缩放），再用 call/put 张数 skew 实现；**不交易现货**。

## 规则摘要

| 模块 | 作用 |
|------|------|
| GEX walls | 选 OTM call≈call wall、OTM put≈put wall；优先现货在墙内开仓 |
| High IV | `iv_rank ≥ iv_rank_min` 才开仓 |
| Kelly | `f* = 2p − 1` 作为 **保证金/权益** 比例；按单组宽跨保证金换算张数 |
| Risk control | 保证金占用与张数硬顶；LSP skew 后若超 Kelly 预算则缩仓 |
| LSP score | 决定净 delta 敞口；`score > 0` 偏多 → 多卖 put / 少卖 call |
| Spot | **不下单**；标的仅用于 LSP / wall / IV 代理信号 |
| 合约月份 | **每次开仓次月合约**（第二近月） |
| 移仓换月 | **到期前 15 个自然日**平仓并换入新的次月 |
| 退出 | 破墙、到期前移仓、最长持有、期权腿被 skew 平光 |

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

- Strategy V2 sandbox needs listed 50ETF option codes that already have daily bars (example: `10010975` call / `10010981` put). Replace them when the chain rolls.
- Full historical wall selection + chain IV rank is done in the research engine (multi-contract panel).
- V2 template uses realized-vol rank as an IV proxy when chain IV is unavailable.
