# GEX + LSP + Kelly Iron Condor（ETF 期权铁鹰）

有限风险卖权结构。针对 **510050** 将默认仓位与过滤条件校准到研究样本上年化 **>30%**：

1. **GEX wall** 选短腿，再买 1 档更虚值翅膀。
2. **定仓**：50ETF 单组有限风险保证金很小，默认 **120 张 / 100 万**（约占用 8–10 万保证金）。
3. **过滤默认关闭**：高 IV / 必须在墙内 会把交易打得太稀，样本内无法达到年化目标。
4. **出场**：轻触短腿或破墙即平，避免单笔走到最大亏损。

## 规则摘要

| 模块 | 作用 |
|------|------|
| GEX walls | 短腿贴近墙；长腿再虚值 1 档 |
| Defined risk | `max_loss ≈ (max(wing) − credit) × multiplier × lots` |
| Sizing | 默认固定 120 张；可用 `--kelly` |
| 合约月份 | 默认次月；到期前 15 日移仓 |
| 退出 | 破短腿/破墙、止盈 50%、止损 90% 最大风险、移仓 |

## Research backtest (510050)

```bash
PYTHONPATH=backend_api_python python backend_api_python/scripts/backtest_gex_lsp_iron_condor.py \
  --data-dir tmp/gex_lsp_strangle --underlying 510050
```

## Notes

- 年化是用交易日把区间收益年化：`(1+R)**(252/N)-1`。约 90 个交易日要 **~12%** 区间收益才到年化 30%。
- 20 日绝对涨跌幅超过 8% 时停开/平仓，避免把 510050 的 120 张直接打到单边趋势里。
- 强趋势标的（样本期内 588000）即使有趋势过滤，前 20 日仍可能亏损；不要把该校准当作全市场通用杠杆。
- Strategy V2 sandbox 需要显式合约代码。
