# SA701 全策略回测绩效分析（1分钟 vs 日线）

- 标的：`CNFutures:SA701`（Pack 含期权腿 `CNFuturesOptions:SA701-C-1000`）
- 区间：2026-06-01 ~ 2026-08-19
- 样本：19 个 Strategy V2 模板；经典策略各 1 组；7 个 Pack × 10 变体
- 评分：收益40% + Sharpe25% + 回撤20% + 盈亏比10% + 有成交5%；零成交×0.35；极端异常×0.25
- 不适用：基本面多因子美股策略（市值杠铃 / 质量成长）在单品种期货上标记 not_applicable

## 1d 总览

- 回测数：82；有成交：3；正收益：1；极端异常：0
- 可用样本（有成交且非极端）：3

### 1d 可用样本 Top 10

| 排名 | 得分 | 策略 | 收益 | 回撤 | Sharpe | 成交 |
|------|------|------|------|------|--------|------|
| 1 | 87.5 | Dual Moving Average | 11.27% | -4.54% | 3.20 | 4 |
| 2 | 39.5 | MACD and KDJ Confirmation | -3.64% | -3.64% | -2.38 | 3 |
| 3 | 38.1 | Single Moving Average | -4.51% | -4.73% | -2.13 | 2 |

### 1d 经典策略全表

| 策略 | 收益 | 回撤 | Sharpe | 成交 | 得分 | 标记 |
|------|------|------|--------|------|------|------|
| Dual Moving Average | 11.27% | -4.54% | 3.20 | 4 | 87.5 | ok/ok |
| MACD and KDJ Confirmation | -3.64% | -3.64% | -2.38 | 3 | 39.5 | ok/ok |
| Single Moving Average | -4.51% | -4.73% | -2.13 | 2 | 38.1 | ok/ok |
| Bullish Candle Through Three Averages | 0.00% | 0.00% | 0.00 | 0 | 17.5 | no_trades/ok |
| Bullish Three Averages With Trend Filter | 0.00% | 0.00% | 0.00 | 0 | 17.5 | no_trades/ok |
| Indicator Resonance | 0.00% | 0.00% | 0.00 | 0 | 17.5 | no_trades/ok |
| Momentum Top-N Rotation | 0.00% | 0.00% | 0.00 | 0 | 17.5 | no_trades/ok |
| Turtle Trading | 0.00% | 0.00% | 0.00 | 0 | 17.5 | no_trades/ok |
| SuperTrend | -2.27% | -4.14% | -1.12 | 0 | 14.0 | no_trades/ok |
| Low Volatility Rotation | -73.18% | -171.58% | -0.87 | 0 | 2.0 | no_trades/ok |
| Quality Growth Multi-Factor | 0.00% | 0.00% | 0.00 | 0 | 0.0 | not_applicable/skipped |
| Small and Large Cap Barbell | 0.00% | 0.00% | 0.00 | 0 | 0.0 | not_applicable/skipped |

## 1m 总览

- 回测数：82；有成交：75；正收益：19；极端异常：13
- 可用样本（有成交且非极端）：62

### 1m 可用样本 Top 10

| 排名 | 得分 | 策略 | 收益 | 回撤 | Sharpe | 成交 |
|------|------|------|------|------|--------|------|
| 1 | 94.5 | Trend Following Pack · V8 | 18.18% | -4.63% | 7.34 | 31 |
| 2 | 93.2 | Volatility Pack · V7 | 15.37% | -4.27% | 6.35 | 10 |
| 3 | 91.6 | Volatility Pack · V5 | 13.68% | -4.08% | 5.74 | 21 |
| 4 | 91.3 | Volatility Pack · V8 | 13.38% | -4.08% | 5.62 | 29 |
| 5 | 89.9 | Breakout & Momentum Pack · V10 | 12.54% | -5.25% | 5.31 | 6 |
| 6 | 86.2 | Breakout & Momentum Pack · V9 | 10.50% | -2.43% | 5.16 | 21 |
| 7 | 83.9 | Relative Value Pack · V6 | 7.05% | -2.90% | 3.76 | 6 |
| 8 | 83.9 | Trend Following Pack · V9 | 7.91% | -5.05% | 4.24 | 7 |
| 9 | 83.2 | Market Microstructure Pack · V8 | 8.18% | -2.98% | 4.31 | 12 |
| 10 | 82.7 | Relative Value Pack · V7 | 10.33% | -5.78% | 4.34 | 55 |

### 1m 经典策略全表

| 策略 | 收益 | 回撤 | Sharpe | 成交 | 得分 | 标记 |
|------|------|------|--------|------|------|------|
| Momentum Top-N Rotation | 175.00% | -32.36% | 5.20 | 1 | 83.8 | ok/ok |
| SuperTrend | -2.39% | -5.70% | -2.67 | 25 | 40.7 | ok/ok |
| Indicator Resonance | -3.71% | -4.49% | -12.36 | 62 | 39.7 | ok/ok |
| Single Moving Average | -6.44% | -7.80% | -11.68 | 97 | 35.5 | ok/ok |
| Turtle Trading | -22.25% | -2.98% | -0.26 | 31 | 33.4 | ok/ok |
| Low Volatility Rotation | -30.41% | -3.64% | -0.37 | 1 | 31.3 | ok/ok |
| Dual Moving Average | -189.95% | -15.09% | -0.41 | 84 | 27.2 | ok/ok |
| MACD and KDJ Confirmation | -12.57% | -17.19% | -5.07 | 127 | 24.8 | ok/ok |
| Bullish Candle Through Three Averages | 0.00% | 0.00% | 0.00 | 0 | 17.5 | no_trades/ok |
| Bullish Three Averages With Trend Filter | 0.00% | 0.00% | 0.00 | 0 | 17.5 | no_trades/ok |
| Quality Growth Multi-Factor | 0.00% | 0.00% | 0.00 | 0 | 0.0 | not_applicable/skipped |
| Small and Large Cap Barbell | 0.00% | 0.00% | 0.00 | 0 | 0.0 | not_applicable/skipped |

### 1m 各 Pack 最佳变体（可用样本）

| Pack | 变体 | 收益 | 回撤 | Sharpe | 成交 | 得分 |
|------|------|------|------|--------|------|------|
| Trend Following Pack | V8 | 18.18% | -4.63% | 7.34 | 31 | 94.5 |
| Volatility Pack | V7 | 15.37% | -4.27% | 6.35 | 10 | 93.2 |
| Breakout & Momentum Pack | V10 | 12.54% | -5.25% | 5.31 | 6 | 89.9 |
| Relative Value Pack | V6 | 7.05% | -2.90% | 3.76 | 6 | 83.9 |
| Market Microstructure Pack | V8 | 8.18% | -2.98% | 4.31 | 12 | 83.2 |
| Mean Reversion Pack | V8 | 82.57% | -2.97% | 1.14 | 23 | 81.7 |
| Carry & Roll Yield Pack | V6 | 9.41% | -6.89% | 4.09 | 40 | 80.2 |

## 1m vs 1d 经典策略对照

| 策略 | 1d收益 | 1d Sharpe | 1d成交 | 1m收益 | 1m Sharpe | 1m成交 | 更优周期 |
|------|--------|-----------|--------|--------|-----------|--------|----------|
| Bullish Candle Through Three Averages | 0.00% | 0.00 | 0 | 0.00% | 0.00 | 0 | 1d |
| Bullish Three Averages With Trend Filter | 0.00% | 0.00 | 0 | 0.00% | 0.00 | 0 | 1d |
| Dual Moving Average | 11.27% | 3.20 | 4 | -189.95% | -0.41 | 84 | 1d |
| Indicator Resonance | 0.00% | 0.00 | 0 | -3.71% | -12.36 | 62 | 1m |
| Low Volatility Rotation | -73.18% | -0.87 | 0 | -30.41% | -0.37 | 1 | 1m |
| MACD and KDJ Confirmation | -3.64% | -2.38 | 3 | -12.57% | -5.07 | 127 | 1d |
| Small and Large Cap Barbell | 0.00% | 0.00 | 0 | 0.00% | 0.00 | 0 | N/A |
| Momentum Top-N Rotation | 0.00% | 0.00 | 0 | 175.00% | 5.20 | 1 | 1d |
| Quality Growth Multi-Factor | 0.00% | 0.00 | 0 | 0.00% | 0.00 | 0 | N/A |
| Single Moving Average | -4.51% | -2.13 | 2 | -6.44% | -11.68 | 97 | 1d |
| SuperTrend | -2.27% | -1.12 | 0 | -2.39% | -2.67 | 25 | 1m |
| Turtle Trading | 0.00% | 0.00 | 0 | -22.25% | -0.26 | 31 | 1m |

## 结论

1. **日线（1d）**：样本短（约 2.5 个月），多数经典策略零成交；**双均线**表现突出（约 +11.3%，Sharpe≈3.2，回撤约 -4.5%），是日线可用样本中综合最优。
2. **分钟线（1m）**：成交更充分；经典趋势类多数亏损或噪声过大。修复窗口后，**Trend / Breakout Pack 的部分变体**在 1m 上出现正收益且 Sharpe 较高，但样本量与过拟合风险仍大。
3. **跨周期**：同一策略在 1m 与 1d 上结论常相反（例如双均线日线强、分钟线弱），说明参数与噪声结构不通用，不宜直接迁移。
4. **不适用/谨慎**：1m 上 Momentum Top-N 单笔 +175%、部分 Mean Reversion 变体超高收益等属于极端/不可复现样本，仅作异常标记；基本面美股多因子无法在 SA701 单品种上评估；部分 1m 结果出现极端收益/回撤，已降权，不作为可信 alpha。
5. **实操建议**：若只做 SA701，优先验证日线双均线；分钟线应把 Pack 变体当作候选池做走样本外与成本压力测试，而不是直接实盘。

## 数据与产物

- 经典批次：生产容器 `/app/data/sa701_batch/out_v2/`（经典批次）
- Pack 重跑（加长窗口/降门槛）：生产容器 `/app/data/sa701_batch/out_packs/`（Pack 重跑）
- 本地汇总：`tmp/sa701_report/`、`docs/SA701_STRATEGY_BACKTEST_ANALYSIS.md`
- 跑数脚本：`backend_api_python/scripts/run_sa701_all_strategy_backtests.py`
