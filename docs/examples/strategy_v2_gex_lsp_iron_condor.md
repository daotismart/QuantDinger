# GEX + LSP + Kelly Iron Condor（ETF 期权铁鹰）

有限风险卖权结构。针对 **510050** 将默认仓位与过滤条件校准到研究样本上年化 **>30%**：

1. **当日已挂牌期权链**选腿：每个交易日读取当时仍在交易的合约，**不写死合约代码**。
2. **GEX wall** 选短腿，再买 1 档更虚值翅膀（次月优先，到期前约 15 日移仓）。
3. **定仓**：50ETF 单组有限风险保证金很小，默认 **120 张 / 100 万**（约占用 8–10 万保证金）。
4. **过滤默认关闭**：高 IV / 必须在墙内 会把交易打得太稀，样本内无法达到年化目标。
5. **出场**：轻触短腿或破墙即平，避免单笔走到最大亏损。

## 合约怎么选

回测与实盘选腿都走研究引擎 `gex-lsp-iron-condor-research`：

1. 取标的当日 `opt_analytics_daily` / CSV 中**已挂牌**合约（ClickHouse `etf_options`，失败则 `GEX_LSP_DATA_DIR`）。
2. 缺 strike/cp/到期日时，用展示名（如 `50ETF沽4月2650`）补全，到期日按该月第四个周三。
3. 在次月（不够则当月）链上算 GEX 墙，短 call/put 贴近墙，长腿再虚值 1 档。
4. 月份到期后自然从列表消失，下一期合约自动进入候选。

Strategy V2 示例只订阅标的 `CNStock:510050.SH`，并用

`strategy_family=options_short_vol_iron_condor`

把回测从 V2 K 线沙箱切到上述引擎。**不要**再把 `CNIndexOptions:1000xxxx` 写进 universe。

## 规则摘要

| 模块 | 作用 |
|------|------|
| Listed chain | 每个交易日按当时期权列表选 4 条腿 |
| GEX walls | 短腿贴近墙；长腿再虚值 1 档 |
| Defined risk | `max_loss ≈ (max(wing) − credit) × multiplier × lots` |
| Sizing | 默认固定 120 张；可用 `--kelly` |
| 合约月份 | 默认次月；到期前 15 日移仓 |
| 退出 | 破短腿/破墙、止盈 50%、止损 90% 最大风险、移仓 |

## Research backtest (510050)

ClickHouse 期权链目前从 **2026-03-27** 起有日频分析（标的日 K 更长，但更早没有期权链，不能虚构合约）。最长可回测区间约为 **2026-03-27 → 2026-08-31**。

```bash
PYTHONPATH=backend_api_python python backend_api_python/scripts/backtest_gex_lsp_iron_condor.py \
  --from-csv --data-dir tmp/gex_lsp_strangle --underlying 510050 \
  --start 2026-03-27 --end 2026-08-31
```

V2 回测中心对带 `options_short_vol_iron_condor` 的源走同一引擎，不拉取固定期权代码的 `qd_market_bars`。

## Notes

- 年化是用交易日把区间收益年化：`(1+R)**(252/N)-1`。约 100 个交易日要 **~12%** 区间收益才到年化 30%。
- 20 日绝对涨跌幅超过 8% 时停开/平仓，避免把 510050 的 120 张直接打到单边趋势里。
- 强趋势标的（样本期内 588000）即使有趋势过滤，前 20 日仍可能亏损；不要把该校准当作全市场通用杠杆。
- 生产后端镜像若没有 `app.services.gex_lsp_strangle`，需要挂载该包 + `strategy_v2/service.py` 的 listed-chain 拦截，否则 V2 沙箱无法按期权链选腿。
