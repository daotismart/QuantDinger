# GEX-TV Iron Condor（ETF 期权铁鹰）

有限风险卖权结构，选腿对齐 ScriptTrader **GEX 宽跨收时间价值**，退出按 50ETF 挂牌链校准：

1. **当日已挂牌期权链**选腿：每个交易日读取当时仍在交易的合约，**不写死合约代码**；剔除调整合约（*A）和缺价腿。
2. **GEX-TV 选腿**：在 GEX 墙外卖 14–25Δ 短腿，长腿优先 3 档（挂牌不足则对称回退到至少 2 档）；净权利金至少为翼宽的 15%；按净 theta / 最大亏损排序。
3. **到期窗口**：目标约 45 DTE（28–65），**10 DTE 移仓**（21 DTE 会过早锁住浮亏）；收回 75% 权利金止盈。
4. **定仓**：单笔最大亏损占净值 6%（再被 Kelly 10% 与 80 张上限封顶）。
5. **墙只用于开仓**：轻触 GEX 墙不平仓（会切掉赢家）；短腿被触及仍平仓。
6. **缺价不平仓**：四腿任一 `option_close<=0` 当日不平（移仓/到期可用内在价值）。

## 合约怎么选

回测与实盘选腿都走研究引擎 `gex-lsp-iron-condor-research`：

1. 取标的当日 `opt_analytics_daily` / CSV 中**已挂牌**合约。
2. 缺 strike/cp/到期日时，用展示名（如 `50ETF沽4月2650`）补全。
3. 选最接近 45 DTE 的月份，算 GEX 墙，在墙外 14–25Δ 扫描铁鹰。
4. 月份到期后自然从列表消失，下一期合约自动进入候选。

Strategy V2 示例只订阅标的 `CNStock:510050.SH`，并用

`strategy_family=options_short_vol_iron_condor`

把回测从 V2 K 线沙箱切到上述引擎。

## 规则摘要

| 模块 | 作用 |
|------|------|
| Listed chain | 每个交易日按当时期权列表选 4 条腿 |
| GEX-TV pick | 墙外 14–25Δ 短腿 + 优先 3 档长腿；credit/width ≥ 15% |
| Defined risk | `max_loss ≈ (max(wing) − credit) × multiplier × lots` |
| Sizing | `min(80, 6% NAV / max_loss, Kelly 10%)` |
| 合约月份 | 目标 45 DTE；到期前 **10 日**移仓 |
| 退出 | 破短腿、止盈 75%、止损 90% 最大风险、移仓；**不**破墙即平 |

## Research backtest (510050)

ClickHouse 期权链目前从 **2026-03-27** 起有日频分析。最长可回测区间约为 **2026-03-27 → 2026-08-31**。

```bash
PYTHONPATH=backend_api_python python backend_api_python/scripts/backtest_gex_lsp_iron_condor.py \
  --from-csv --data-dir tmp/gex_lsp_strangle --underlying 510050 \
  --start 2026-03-27 --end 2026-08-31
```

## Notes

- 约 100 个交易日、单一标的，正收益是样本内校准，不是实盘保证。
- 21 DTE 移仓在这段 50ETF 样本上会把浮亏锁死；10 DTE 才收到大部分权利金。
- 生产后端镜像若没有 `app.services.gex_lsp_strangle`，需要挂载该包 + listed-chain 拦截。
