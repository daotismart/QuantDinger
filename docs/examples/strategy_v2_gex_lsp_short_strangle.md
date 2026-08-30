# GEX + LSP + Kelly Short Strangle（纯期权）

## 配置标的

**策略标的 = ETF 期权对应的现货 ETF**（不是期权合约代码）。

| 项 | 默认值 |
|----|--------|
| 配置/基准标的 | `CNStock:510050`（上证50ETF） |
| 交易品种 | 该 ETF 的次月认购/认沽期权 |
| 现货 ETF | 只做 LSP / wall / IV 信号，**不下单买卖 ETF** |

配置或分叉策略时：先选定 ETF（如 510050 / 510300 / 159915），再把 call/put 腿换成同一 ETF 次月链上的合约，并同步 wall 行权价。

期权卖方策略分工：

1. **GEX wall** 决定 **安全行权价**（call wall / put wall 附近卖出宽跨式）。
2. **高 IV** 过滤：ATM IV rank 达阈值才卖权（权利金偏贵时做空波动）。
3. **Kelly（权利金盈亏比 1:1）** 决定账户 **保证金占用比例** `f*=2p−1`，再换算可开张数；超出比例/`max_lots` 风控封顶。
4. **LSP** 单独决定 **净 delta 敞口**（按保证金预算缩放），再用 call/put 张数 skew 实现；**不交易现货**。

## 规则摘要

| 模块 | 作用 |
|------|------|
| 配置标的 | **ETF**（期权标的）；默认 510050 |
| GEX walls | 选 OTM call≈call wall、OTM put≈put wall；优先现货在墙内开仓 |
| High IV | `iv_rank ≥ iv_rank_min` 才开仓 |
| Kelly | `f* = 2p − 1`；**p 来自 BS 期权腿胜率**（短 call/put 到期虚值概率，权利金加权）；再换算保证金/权益与张数 |
| Risk control | 保证金占用与张数硬顶；LSP skew 后若超 Kelly 预算则缩仓 |
| LSP score | 决定净 delta 敞口；`score > 0` 偏多 → 多卖 put / 少卖 call |
| Spot | **不下单**；标的仅用于 LSP / wall / IV 代理信号 |
| 合约月份 | **每次开仓次月合约**（第二近月） |
| 移仓换月 | **到期前 15 个自然日**平仓并换入新的次月 |
| 退出 | 破墙、到期前移仓、最长持有、期权腿被 skew 平光 |


## Kelly 胜率（BS 期权腿）

卖权“胜利”= 到期仍为虚值（权利金全部赚到）：

- 短 call 胜率 \(p_c = N(-d2_c) = P(S_T < K_c)\)
- 短 put 胜率 \(p_p = N(d2_p) = P(S_T > K_p)\)
- 默认 Kelly \(p\) = 权利金加权：\((C\cdot p_c + P\cdot p_p)/(C+P)\)
- 可选：`average` 两腿均值；`both_otm` = 两腿同时虚值 \(p_c+p_p-1\)

\(\sigma\) 优先用 ATM IV，缺失时用现货实现波动；\(T\) 用剩余到期年化；行权价用 GEX 墙/腿行权价。

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

## Production publish (daotismart)

Published as admin Strategy V2 script source + marketplace template:

| Item | Value |
|------|-------|
| Script source id | `38` |
| Inventory name | `GEX+LSP+Kelly 次月宽跨式卖方` |
| Successful backtest | run `941` (2026-03-01 → 2026-08-20) |
| Marketplace indicator id | `2` (`script_template`, free, approved) |

Sandbox legs: `CNIndexOptions:10010975` / `10010981` with `CNStock:510050`. Replace contracts when rolling in live use. Research engine with live GEX walls is separate (`gex_lsp_strangle` service).
