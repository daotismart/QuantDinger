# GEX-TV Iron Condor（ETF 期权铁鹰）

有限风险卖权结构，选腿对齐 ScriptTrader **GEX 宽跨收时间价值** 铁鹰：

1. **当日已挂牌期权链**选腿：每个交易日读取当时仍在交易的合约，**不写死合约代码**；剔除调整合约（*A）和缺价腿。
2. **GEX-TV**：在 GEX 墙外卖 14–25Δ 短腿，优先 3 档长腿（挂牌不足则对称回退到至少 2 档）；净权利金至少为翼宽的 20%（SA 实盘脚本为 25%，50ETF 翼更窄所以略降）；按净 theta / 最大亏损排序。
3. **到期窗口**：目标约 45 DTE（28–65），21 DTE 移仓；收回 75% 权利金止盈。
4. **定仓**：单笔最大亏损占净值 6%（再被 Kelly 10% 与 80 张上限封顶）。
5. **缺价不平仓**：四腿任一 `option_close<=0` 当日不平，PnL 裁剪在 `[-max_risk, credit]`。

## 合约怎么选

回测与实盘选腿都走研究引擎 `gex-lsp-iron-condor-research`：

1. 取标的当日 `opt_analytics_daily` / CSV 中**已挂牌**合约（ClickHouse `etf_options`，失败则 `GEX_LSP_DATA_DIR`）。
2. 缺 strike/cp/到期日时，用展示名（如 `50ETF沽4月2650`）补全，到期日按该月第四个周三。
3. 选最接近 45 DTE 的月份，算 GEX 墙，在墙外 14–25Δ 扫描铁鹰，长腿 3 档。
4. 月份到期后自然从列表消失，下一期合约自动进入候选。

Strategy V2 示例只订阅标的 `CNStock:510050.SH`，并用

`strategy_family=options_short_vol_iron_condor`

把回测从 V2 K 线沙箱切到上述引擎。**不要**再把 `CNIndexOptions:1000xxxx` 写进 universe。

## 规则摘要

| 模块 | 作用 |
|------|------|
| Listed chain | 每个交易日按当时期权列表选 4 条腿 |
| GEX-TV pick | 墙外 14–25Δ 短腿 + 优先 3 档长腿；credit/width ≥ 20% |
| Defined risk | `max_loss ≈ (max(wing) − credit) × multiplier × lots` |
| Sizing | `min(80, 6% NAV / max_loss, Kelly 10%)` |
| 合约月份 | 目标 45 DTE；到期前 21 日移仓 |
| 退出 | 破短腿/破墙、止盈 75% 已实现权利金、止损 90% 最大风险、移仓；缺价跳过 |

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
- 20 日绝对涨跌幅超过 8% 时停开/平仓。
- 生产后端镜像若没有 `app.services.gex_lsp_strangle`，需要挂载该包 + `strategy_v2/service.py` 的 listed-chain 拦截。
