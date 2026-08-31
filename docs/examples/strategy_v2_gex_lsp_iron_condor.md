# GEX + LSP + Kelly Iron Condor（ETF 期权铁鹰）

在宽跨式卖权框架上增加更虚值保护腿，把无限风险改为**有限风险**：

1. **GEX wall**：在 call / put 墙附近卖出虚值短腿。
2. **Wings**：再买更虚值 call / put（`wing_steps` 档），构成铁鹰。
3. **高 IV**：ATM IV rank 达标才卖权。
4. **Kelly**：用「翼宽 − 净权利金」定义风险保证金，按 `f*=2p−1` 定仓。
5. **LSP**：只 skew 短腿 call/put 张数；同侧翅膀张数与短腿一致；不交易现货。

## 规则摘要

| 模块 | 作用 |
|------|------|
| GEX walls | 短腿贴近墙；长腿更虚值 |
| Defined risk | `max_loss ≈ (max(wing) − credit) × multiplier × lots` |
| High IV | `iv_rank ≥ iv_rank_min` 才开仓 |
| Kelly | 有限风险保证金换算张数；硬顶 fraction / lots |
| LSP | 净 delta 通过短腿张数倾斜实现 |
| 合约月份 | 默认次月；到期前 `roll_before_dte` 移仓 |
| 退出 | 破短腿、破墙、移仓、最长持有、止盈、止损 |

## Files

| Path | Role |
|------|------|
| `docs/examples/strategy_v2_gex_lsp_iron_condor.py` | Strategy API V2 template |
| `backend_api_python/app/services/gex_lsp_strangle/iron_condor_engine.py` | Research engine |
| `backend_api_python/scripts/backtest_gex_lsp_iron_condor.py` | CLI backtest |
| `docs/reports/GEX_LSP_IRON_CONDOR_510050.md` | Latest 510050 result |

## Research backtest (510050)

```bash
PYTHONPATH=backend_api_python python backend_api_python/scripts/backtest_gex_lsp_iron_condor.py \
  --data-dir tmp/gex_lsp_strangle --underlying 510050
```

## Notes

- ETF 行权价网格较密时，默认 `wing_steps=1`；墙落在网格边缘时引擎会把短腿内移一档以保证翅膀空间。
- Strategy V2 sandbox 需要显式合约代码；完整历史选墙 / IV rank 请用 research CLI。
