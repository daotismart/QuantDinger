# QuantDinger 回测综合排名与分析报告

- 生成时间：2026-08-20 01:56 UTC
- 数据来源：生产环境 `qd_backtest_runs`（**79** 条）
- 去重后策略样本：**65**（同名+同周期保留最高分）
- 评分：收益 40% + Sharpe 25% + 回撤 20% + 盈亏比 10% + 有成交 5%；极端异常值×0.25，零成交×0.35
- 指标已统一为小数收益率（自动识别历史百分比口径）

---

## 1. 执行摘要

| 项目 | 数值 |
|------|------|
| 回测总数 | 79 |
| 去重策略数 | 65 |
| 有成交（去重） | 11 |
| 零成交（去重） | 54 |
| 策略族 | 8 |
| 综合第 1（有成交·去重） | **Quality Growth Multi-Factor**（#28，得分 75.93，收益 7.49%） |
| 有成交且正收益 | 4 / 11 |

### 核心结论

1. **可交易样本中，美股组合与双均线 CTA 质量最高**：`Quality Growth Multi-Factor`、`Dual Moving Average`、`Low Volatility Rotation` 在可控回撤下取得正收益。
2. **AS 期权做市** 有真实成交，但样本间差异极大：稳健参数下小幅亏损；部分 run 出现千倍级收益/Sharpe，已标为极端异常，**不纳入可信 alpha**。
3. **先进 50 Pack（run 30–79）全部零成交**：回测链路成功，但短窗口 1m 数据未触发交易；低分反映数据约束，而非策略逻辑失败。
4. 报告生成前已修复生产库中被误写成标的代码的策略名称。

---

## 2. 综合排名（去重 Top 15）

| 排名 | 得分 | 策略 | 族 | Run | 周期 | 总收益 | 年化 | 最大回撤 | Sharpe | 胜率 | 成交 | 标记 |
|------|------|------|----|-----|------|--------|------|----------|--------|------|------|------|
| 1 | 75.9 | Quality Growth Multi-Factor | US Portfolio | #28 | 1d | 7.49% | 40.86% | -7.44% | 2.51 | 73.68% | 19 | ok |
| 2 | 74.1 | Dual Moving Average | CTA Classic | #5 | 4h | 12.38% | 71.74% | -7.35% | 1.81 | 50.00% | 6 | ok |
| 3 | 65.6 | Low Volatility Rotation | US Portfolio | #11 | 1d | 6.61% | 35.47% | -4.75% | 1.92 | 82.35% | 17 | ok |
| 4 | 62.5 | Small and Large Cap Barbell | US Portfolio | #29 | 1d | -1.20% | -5.58% | -12.32% | 0.00 | 53.85% | 13 | ok |
| 5 | 53.5 | Single Moving Average | CTA Classic | #24 | 1d | -0.99% | -4.61% | -4.12% | -0.33 | 33.33% | 3 | ok |
| 6 | 52.6 | Indicator Resonance | CTA Classic | #26 | 1d | -0.44% | -2.08% | -1.54% | -0.55 | 0.00% | 1 | ok |
| 7 | 47.8 | MACD and KDJ Confirmation | CTA Classic | #9 | 4h | -4.77% | -20.26% | -7.32% | -1.68 | 39.39% | 33 | ok |
| 8 | 41.2 | AS Options Market Maker | AS Options MM | #3 | 1m | -3.56% | -84.89% | -4.02% | -17.09 | 2.00% | 50 | ok |
| 9 | 40.7 | Momentum Top-N Rotation | US Portfolio | #10 | 1d | -11.52% | -44.03% | -14.40% | -2.25 | 47.37% | 19 | ok |
| 10 | 38.0 | AS Options Market Maker | AS Options MM | #1 | 5m | -14.61% | -30.26% | -14.79% | -3.02 | 39.60% | 399 | ok |
| 11 | 24.0 | AS Options Market Maker(SA2701) | AS Options MM | #4 | 1m | 2159.10% | 100000000.00% | -20.81% | 46.40 | 100.00% | 247 | extreme_outlier |
| 12 | 18.4 | Turtle Trading | CTA Classic | #25 | 1d | 81.74% | 393.70% | -126.66% | 1.00 | 0.00% | 0 | no_trades |
| 13 | 17.6 | Bullish Candle Through Three Averages | CTA Classic | #7 | 1d | 0.00% | 0.00% | 0.00% | 0.00 | 0.00% | 0 | no_trades |
| 14 | 17.6 | Bullish Three Averages With Trend Filter | CTA Classic | #8 | 1d | 0.00% | 0.00% | 0.00% | 0.00 | 0.00% | 0 | no_trades |
| 15 | 17.6 | Statistical Arbitrage Pack · Variant 1 | Stat Arb Pack | #30 | 1m | 0.00% | 0.00% | 0.00% | 0.00 | 0.00% | 0 | no_trades |

## 3. 有成交策略排名（去重）

| 排名 | 得分 | 策略 | 族 | 总收益 | 回撤 | Sharpe | 盈亏比 | 成交 | Run |
|------|------|------|----|--------|------|--------|--------|------|-----|
| 1 | 75.9 | Quality Growth Multi-Factor | US Portfolio | 7.49% | -7.44% | 2.51 | 16.03 | 19 | #28 |
| 2 | 74.1 | Dual Moving Average | CTA Classic | 12.38% | -7.35% | 1.81 | 5.08 | 6 | #5 |
| 3 | 65.6 | Low Volatility Rotation | US Portfolio | 6.61% | -4.75% | 1.92 | 0.55 | 17 | #11 |
| 4 | 62.5 | Small and Large Cap Barbell | US Portfolio | -1.20% | -12.32% | 0.00 | 6.22 | 13 | #29 |
| 5 | 53.5 | Single Moving Average | CTA Classic | -0.99% | -4.12% | -0.33 | 0.17 | 3 | #24 |
| 6 | 52.6 | Indicator Resonance | CTA Classic | -0.44% | -1.54% | -0.55 | 0.00 | 1 | #26 |
| 7 | 47.8 | MACD and KDJ Confirmation | CTA Classic | -4.77% | -7.32% | -1.68 | 0.62 | 33 | #9 |
| 8 | 41.2 | AS Options Market Maker | AS Options MM | -3.56% | -4.02% | -17.09 | 0.02 | 50 | #3 |
| 9 | 40.7 | Momentum Top-N Rotation | US Portfolio | -11.52% | -14.40% | -2.25 | 0.07 | 19 | #10 |
| 10 | 38.0 | AS Options Market Maker | AS Options MM | -14.61% | -14.79% | -3.02 | 0.42 | 399 | #1 |
| 11 | 24.0 | AS Options Market Maker(SA2701) | AS Options MM | 2159.10% | -20.81% | 46.40 | 2159.10 | 247 | #4 |

## 4. 策略族排行榜

| 排名 | 策略族 | 策略数 | 有成交 | 平均得分 | 平均收益* | 总成交 | 族内最佳 |
|------|--------|--------|--------|----------|-----------|--------|----------|

| 1 | US Portfolio | 4 | 4 | 61.2 | 0.34% | 68 | Quality Growth Multi-Factor (#28) |
| 2 | CTA Classic | 8 | 4 | 35.5 | 1.55% | 43 | Dual Moving Average (#5) |
| 3 | AS Options MM | 3 | 3 | 34.4 | -9.08% | 696 | AS Options Market Maker (#3) |
| 4 | Stat Arb Pack | 10 | 0 | 17.6 | 0.00% | 0 | Statistical Arbitrage Pack · Variant 1 (#30) |
| 5 | Options Vol Pack | 10 | 0 | 17.6 | 0.00% | 0 | Options Volatility Pack · Variant 1 (#40) |
| 6 | Session Alpha Pack | 10 | 0 | 17.6 | 0.00% | 0 | Session Alpha Pack · Variant 1 (#50) |
| 7 | Regime Switch Pack | 10 | 0 | 17.6 | 0.00% | 0 | Regime Switch Pack · Variant 1 (#60) |
| 8 | Order Flow Pack | 10 | 0 | 17.6 | 0.00% | 0 | Order Flow Proxy Pack · Variant 1 (#70) |

\*平均收益已排除极端异常值样本。

---

## 5. 分族分析

### US Portfolio

样本 4，有成交 4，平均得分 **61.2**，平均收益 **0.34%**

| 策略 | Run | 区间 | 收益 | Sharpe | 回撤 | 成交 | 得分 |
|------|-----|------|------|--------|------|------|------|
| Quality Growth Multi-Factor | #28 | 2026-06-01→2026-08-18 | 7.49% | 2.51 | -7.44% | 19 | 75.9 |
| Low Volatility Rotation | #11 | 2026-06-01→2026-08-18 | 6.61% | 1.92 | -4.75% | 17 | 65.6 |
| Small and Large Cap Barbell | #29 | 2026-06-01→2026-08-18 | -1.20% | 0.00 | -12.32% | 13 | 62.5 |
| Momentum Top-N Rotation | #10 | 2026-06-01→2026-08-18 | -11.52% | -2.25 | -14.40% | 19 | 40.7 |

### CTA Classic

样本 8，有成交 4，平均得分 **35.5**，平均收益 **1.55%**

| 策略 | Run | 区间 | 收益 | Sharpe | 回撤 | 成交 | 得分 |
|------|-----|------|------|--------|------|------|------|
| Dual Moving Average | #5 | 2026-06-01→2026-08-18 | 12.38% | 1.81 | -7.35% | 6 | 74.1 |
| Single Moving Average | #24 | 2026-06-01→2026-08-18 | -0.99% | -0.33 | -4.12% | 3 | 53.5 |
| Indicator Resonance | #26 | 2026-06-01→2026-08-18 | -0.44% | -0.55 | -1.54% | 1 | 52.6 |
| MACD and KDJ Confirmation | #9 | 2026-06-01→2026-08-18 | -4.77% | -1.68 | -7.32% | 33 | 47.8 |
| Turtle Trading | #25 | 2026-06-01→2026-08-18 | 81.74% | 1.00 | -126.66% | 0 | 18.4 |
| Bullish Candle Through Three Averages | #7 | 2026-06-01→2026-08-18 | 0.00% | 0.00 | 0.00% | 0 | 17.6 |
| Bullish Three Averages With Trend Filter | #8 | 2026-06-01→2026-08-18 | 0.00% | 0.00 | 0.00% | 0 | 17.6 |
| SuperTrend | #27 | 2026-06-01→2026-08-18 | -105.32% | -1.56 | -126.97% | 0 | 2.1 |

### AS Options MM

样本 3，有成交 3，平均得分 **34.4**，平均收益 **-9.08%**

| 策略 | Run | 区间 | 收益 | Sharpe | 回撤 | 成交 | 得分 |
|------|-----|------|------|--------|------|------|------|
| AS Options Market Maker | #3 | 2026-07-21→2026-08-19 | -3.56% | -17.09 | -4.02% | 50 | 41.2 |
| AS Options Market Maker | #1 | 2026-02-21→2026-08-19 | -14.61% | -3.02 | -14.79% | 399 | 38.0 |
| AS Options Market Maker(SA2701) | #4 | 2026-07-21→2026-08-19 | 2159.10% | 46.40 | -20.81% | 247 | 24.0 |

### Stat Arb Pack

样本 10，有成交 0，平均得分 **17.6**，平均收益 **0.00%**

| 策略 | Run | 区间 | 收益 | Sharpe | 回撤 | 成交 | 得分 |
|------|-----|------|------|--------|------|------|------|
| Statistical Arbitrage Pack · Variant 1 | #30 | 2026-08-05→2026-08-18 | 0.00% | 0.00 | 0.00% | 0 | 17.6 |
| Statistical Arbitrage Pack · Variant 2 | #31 | 2026-08-05→2026-08-18 | 0.00% | 0.00 | 0.00% | 0 | 17.6 |
| Statistical Arbitrage Pack · Variant 3 | #32 | 2026-08-05→2026-08-18 | 0.00% | 0.00 | 0.00% | 0 | 17.6 |
| Statistical Arbitrage Pack · Variant 4 | #33 | 2026-08-05→2026-08-18 | 0.00% | 0.00 | 0.00% | 0 | 17.6 |
| Statistical Arbitrage Pack · Variant 5 | #34 | 2026-08-05→2026-08-18 | 0.00% | 0.00 | 0.00% | 0 | 17.6 |
| Statistical Arbitrage Pack · Variant 6 | #35 | 2026-08-05→2026-08-18 | 0.00% | 0.00 | 0.00% | 0 | 17.6 |
| Statistical Arbitrage Pack · Variant 7 | #36 | 2026-08-05→2026-08-18 | 0.00% | 0.00 | 0.00% | 0 | 17.6 |
| Statistical Arbitrage Pack · Variant 8 | #37 | 2026-08-05→2026-08-18 | 0.00% | 0.00 | 0.00% | 0 | 17.6 |
| Statistical Arbitrage Pack · Variant 9 | #38 | 2026-08-05→2026-08-18 | 0.00% | 0.00 | 0.00% | 0 | 17.6 |
| Statistical Arbitrage Pack · Variant 10 | #39 | 2026-08-05→2026-08-18 | 0.00% | 0.00 | 0.00% | 0 | 17.6 |

### Options Vol Pack

样本 10，有成交 0，平均得分 **17.6**，平均收益 **0.00%**

| 策略 | Run | 区间 | 收益 | Sharpe | 回撤 | 成交 | 得分 |
|------|-----|------|------|--------|------|------|------|
| Options Volatility Pack · Variant 1 | #40 | 2026-08-05→2026-08-18 | 0.00% | 0.00 | 0.00% | 0 | 17.6 |
| Options Volatility Pack · Variant 2 | #41 | 2026-08-05→2026-08-18 | 0.00% | 0.00 | 0.00% | 0 | 17.6 |
| Options Volatility Pack · Variant 3 | #42 | 2026-08-05→2026-08-18 | 0.00% | 0.00 | 0.00% | 0 | 17.6 |
| Options Volatility Pack · Variant 4 | #43 | 2026-08-05→2026-08-18 | 0.00% | 0.00 | 0.00% | 0 | 17.6 |
| Options Volatility Pack · Variant 5 | #44 | 2026-08-05→2026-08-18 | 0.00% | 0.00 | 0.00% | 0 | 17.6 |
| Options Volatility Pack · Variant 6 | #45 | 2026-08-05→2026-08-18 | 0.00% | 0.00 | 0.00% | 0 | 17.6 |
| Options Volatility Pack · Variant 7 | #46 | 2026-08-05→2026-08-18 | 0.00% | 0.00 | 0.00% | 0 | 17.6 |
| Options Volatility Pack · Variant 8 | #47 | 2026-08-05→2026-08-18 | 0.00% | 0.00 | 0.00% | 0 | 17.6 |
| Options Volatility Pack · Variant 9 | #48 | 2026-08-05→2026-08-18 | 0.00% | 0.00 | 0.00% | 0 | 17.6 |
| Options Volatility Pack · Variant 10 | #49 | 2026-08-05→2026-08-18 | 0.00% | 0.00 | 0.00% | 0 | 17.6 |

### Session Alpha Pack

样本 10，有成交 0，平均得分 **17.6**，平均收益 **0.00%**

| 策略 | Run | 区间 | 收益 | Sharpe | 回撤 | 成交 | 得分 |
|------|-----|------|------|--------|------|------|------|
| Session Alpha Pack · Variant 1 | #50 | 2026-08-05→2026-08-18 | 0.00% | 0.00 | 0.00% | 0 | 17.6 |
| Session Alpha Pack · Variant 2 | #51 | 2026-08-05→2026-08-18 | 0.00% | 0.00 | 0.00% | 0 | 17.6 |
| Session Alpha Pack · Variant 3 | #52 | 2026-08-05→2026-08-18 | 0.00% | 0.00 | 0.00% | 0 | 17.6 |
| Session Alpha Pack · Variant 4 | #53 | 2026-08-05→2026-08-18 | 0.00% | 0.00 | 0.00% | 0 | 17.6 |
| Session Alpha Pack · Variant 5 | #54 | 2026-08-05→2026-08-18 | 0.00% | 0.00 | 0.00% | 0 | 17.6 |
| Session Alpha Pack · Variant 6 | #55 | 2026-08-05→2026-08-18 | 0.00% | 0.00 | 0.00% | 0 | 17.6 |
| Session Alpha Pack · Variant 7 | #56 | 2026-08-05→2026-08-18 | 0.00% | 0.00 | 0.00% | 0 | 17.6 |
| Session Alpha Pack · Variant 8 | #57 | 2026-08-05→2026-08-18 | 0.00% | 0.00 | 0.00% | 0 | 17.6 |
| Session Alpha Pack · Variant 9 | #58 | 2026-08-05→2026-08-18 | 0.00% | 0.00 | 0.00% | 0 | 17.6 |
| Session Alpha Pack · Variant 10 | #59 | 2026-08-05→2026-08-18 | 0.00% | 0.00 | 0.00% | 0 | 17.6 |

### Regime Switch Pack

样本 10，有成交 0，平均得分 **17.6**，平均收益 **0.00%**

| 策略 | Run | 区间 | 收益 | Sharpe | 回撤 | 成交 | 得分 |
|------|-----|------|------|--------|------|------|------|
| Regime Switch Pack · Variant 1 | #60 | 2026-08-05→2026-08-18 | 0.00% | 0.00 | 0.00% | 0 | 17.6 |
| Regime Switch Pack · Variant 2 | #61 | 2026-08-05→2026-08-18 | 0.00% | 0.00 | 0.00% | 0 | 17.6 |
| Regime Switch Pack · Variant 3 | #62 | 2026-08-05→2026-08-18 | 0.00% | 0.00 | 0.00% | 0 | 17.6 |
| Regime Switch Pack · Variant 4 | #63 | 2026-08-05→2026-08-18 | 0.00% | 0.00 | 0.00% | 0 | 17.6 |
| Regime Switch Pack · Variant 5 | #64 | 2026-08-05→2026-08-18 | 0.00% | 0.00 | 0.00% | 0 | 17.6 |
| Regime Switch Pack · Variant 6 | #65 | 2026-08-05→2026-08-18 | 0.00% | 0.00 | 0.00% | 0 | 17.6 |
| Regime Switch Pack · Variant 7 | #66 | 2026-08-05→2026-08-18 | 0.00% | 0.00 | 0.00% | 0 | 17.6 |
| Regime Switch Pack · Variant 8 | #67 | 2026-08-05→2026-08-18 | 0.00% | 0.00 | 0.00% | 0 | 17.6 |
| Regime Switch Pack · Variant 9 | #68 | 2026-08-05→2026-08-18 | 0.00% | 0.00 | 0.00% | 0 | 17.6 |
| Regime Switch Pack · Variant 10 | #69 | 2026-08-05→2026-08-18 | 0.00% | 0.00 | 0.00% | 0 | 17.6 |

### Order Flow Pack

样本 10，有成交 0，平均得分 **17.6**，平均收益 **0.00%**

| 策略 | Run | 区间 | 收益 | Sharpe | 回撤 | 成交 | 得分 |
|------|-----|------|------|--------|------|------|------|
| Order Flow Proxy Pack · Variant 1 | #70 | 2026-08-05→2026-08-18 | 0.00% | 0.00 | 0.00% | 0 | 17.6 |
| Order Flow Proxy Pack · Variant 2 | #71 | 2026-08-05→2026-08-18 | 0.00% | 0.00 | 0.00% | 0 | 17.6 |
| Order Flow Proxy Pack · Variant 3 | #72 | 2026-08-05→2026-08-18 | 0.00% | 0.00 | 0.00% | 0 | 17.6 |
| Order Flow Proxy Pack · Variant 4 | #73 | 2026-08-05→2026-08-18 | 0.00% | 0.00 | 0.00% | 0 | 17.6 |
| Order Flow Proxy Pack · Variant 5 | #74 | 2026-08-05→2026-08-18 | 0.00% | 0.00 | 0.00% | 0 | 17.6 |
| Order Flow Proxy Pack · Variant 6 | #75 | 2026-08-05→2026-08-18 | 0.00% | 0.00 | 0.00% | 0 | 17.6 |
| Order Flow Proxy Pack · Variant 7 | #76 | 2026-08-05→2026-08-18 | 0.00% | 0.00 | 0.00% | 0 | 17.6 |
| Order Flow Proxy Pack · Variant 8 | #77 | 2026-08-05→2026-08-18 | 0.00% | 0.00 | 0.00% | 0 | 17.6 |
| Order Flow Proxy Pack · Variant 9 | #78 | 2026-08-05→2026-08-18 | 0.00% | 0.00 | 0.00% | 0 | 17.6 |
| Order Flow Proxy Pack · Variant 10 | #79 | 2026-08-05→2026-08-18 | 0.00% | 0.00 | 0.00% | 0 | 17.6 |

---

## 6. 先进 50 Pack 专项

- runId **30–79**，共 50 条，有成交 **0**
- 窗口多为 `2026-08-05 → 2026-08-18`，频率 `1m`（策略内聚合成 30m）
- **结论**：回测全部成功落库，但未产生交易；需在 SA701 1m 历史修复后重跑再评估 alpha

| Pack | 变体 | 有成交 | 平均得分 |
|------|------|--------|----------|
| Stat Arb Pack | 10 | 0 | 17.6 |
| Options Vol Pack | 10 | 0 | 17.6 |
| Session Alpha Pack | 10 | 0 | 17.6 |
| Regime Switch Pack | 10 | 0 | 17.6 |
| Order Flow Pack | 10 | 0 | 17.6 |

---

## 7. 风险与数据质量

- 极端异常值：**2** 条（已降权）

| Run | 策略 | 收益 | Sharpe | 说明 |
|-----|------|------|--------|------|
| #4 | AS Options Market Maker(SA2701) | 2159.10% | 46.40 | 初始资金/合约乘数/脏数据可能导致失真 |
| #2 | AS Options Market Maker | 3378.95% | 35.04 | 初始资金/合约乘数/脏数据可能导致失真 |

- 跨族不可直接比绝对收益：标的、周期、资金、费率不同。
- 同策略存在重复回测，总榜以去重结果为主，附录保留全量。

---

## 8. 建议

1. **重点跟进**：Quality Growth / Dual MA / Low Volatility — 扩大样本期与参数稳健性测试。
2. **AS Options MM**：固定资金与费率后复现，剔除极端 run，评估真实做市期望。
3. **50 Pack**：优先修复 SA701 行情，再批量重跑并刷新本报告。
4. **CTA 经典**：Bullish/Turtle/SuperTrend 等零成交或弱表现样本，检查标的与信号阈值。

---

## 附录 A：全量回测清单（按得分）

| Run | 策略 | 族 | 标的 | 周期 | 收益 | Sharpe | 成交 | 得分 | 标记 |
|-----|------|----|------|------|------|--------|------|------|------|
| #28 | Quality Growth Multi-Factor | US Portfolio | AAPL + MSFT + NVDA + AMZN + META + GOOGL + AVGO +… | 1d | 7.49% | 2.51 | 19 | 75.9 | ok |
| #5 | Dual Moving Average | CTA Classic | Crypto:BTC/USDT | 4h | 12.38% | 1.81 | 6 | 74.1 | ok |
| #6 | Dual Moving Average | CTA Classic | Crypto:BTC/USDT | 4h | 12.38% | 1.81 | 6 | 74.1 | ok |
| #12 | Dual Moving Average | CTA Classic | Crypto:BTC/USDT | 4h | 12.38% | 1.81 | 6 | 74.1 | ok |
| #18 | Dual Moving Average | CTA Classic | Crypto:BTC/USDT | 4h | 12.38% | 1.81 | 6 | 74.1 | ok |
| #11 | Low Volatility Rotation | US Portfolio | AAPL + MSFT + NVDA + AMZN + META + GOOGL + AVGO +… | 1d | 6.61% | 1.92 | 17 | 65.6 | ok |
| #17 | Low Volatility Rotation | US Portfolio | AAPL + MSFT + NVDA + AMZN + META + GOOGL + AVGO +… | 1d | 6.61% | 1.92 | 17 | 65.6 | ok |
| #23 | Low Volatility Rotation | US Portfolio | AAPL + MSFT + NVDA + AMZN + META + GOOGL + AVGO +… | 1d | 6.61% | 1.92 | 17 | 65.6 | ok |
| #29 | Small and Large Cap Barbell | US Portfolio | AAPL + MSFT + NVDA + AMZN + META + GOOGL + AVGO +… | 1d | -1.20% | 0.00 | 13 | 62.5 | ok |
| #24 | Single Moving Average | CTA Classic | USStock:SPY | 1d | -0.99% | -0.33 | 3 | 53.5 | ok |
| #26 | Indicator Resonance | CTA Classic | USStock:QQQ | 1d | -0.44% | -0.55 | 1 | 52.6 | ok |
| #9 | MACD and KDJ Confirmation | CTA Classic | Crypto:BTC/USDT | 4h | -4.77% | -1.68 | 33 | 47.8 | ok |
| #15 | MACD and KDJ Confirmation | CTA Classic | Crypto:BTC/USDT | 4h | -4.77% | -1.68 | 33 | 47.8 | ok |
| #21 | MACD and KDJ Confirmation | CTA Classic | Crypto:BTC/USDT | 4h | -4.77% | -1.68 | 33 | 47.8 | ok |
| #3 | AS Options Market Maker | AS Options MM | M2610-C-1000 + SA2610 | 1m | -3.56% | -17.09 | 50 | 41.2 | ok |
| #10 | Momentum Top-N Rotation | US Portfolio | AAPL + MSFT + NVDA + AMZN + META + GOOGL + AVGO +… | 1d | -11.52% | -2.25 | 19 | 40.7 | ok |
| #16 | Momentum Top-N Rotation | US Portfolio | AAPL + MSFT + NVDA + AMZN + META + GOOGL + AVGO +… | 1d | -11.52% | -2.25 | 19 | 40.7 | ok |
| #22 | Momentum Top-N Rotation | US Portfolio | AAPL + MSFT + NVDA + AMZN + META + GOOGL + AVGO +… | 1d | -11.52% | -2.25 | 19 | 40.7 | ok |
| #1 | AS Options Market Maker | AS Options MM | M2609-C-2800 + M2609 | 5m | -14.61% | -3.02 | 399 | 38.0 | ok |
| #4 | AS Options Market Maker(SA2701) | AS Options MM | SA2701-C-1000 + SA2701 | 1m | 2159.10% | 46.40 | 247 | 24.0 | extreme_outlier |
| #2 | AS Options Market Maker | AS Options MM | M2610-C-1000 + SA2610 | 1m | 3378.95% | 35.04 | 246 | 23.4 | extreme_outlier |
| #25 | Turtle Trading | CTA Classic | USStock:SPY | 1d | 81.74% | 1.00 | 0 | 18.4 | no_trades |
| #7 | Bullish Candle Through Three Averages | CTA Classic | CNStock:600519.SH | 1d | 0.00% | 0.00 | 0 | 17.6 | no_trades |
| #8 | Bullish Three Averages With Trend Filter | CTA Classic | CNStock:600519.SH | 1d | 0.00% | 0.00 | 0 | 17.6 | no_trades |
| #13 | Bullish Candle Through Three Averages | CTA Classic | CNStock:600519.SH | 1d | 0.00% | 0.00 | 0 | 17.6 | no_trades |
| #14 | Bullish Candle Through Three Averages | CTA Classic | CNStock:600519.SH | 1d | 0.00% | 0.00 | 0 | 17.6 | no_trades |
| #19 | Bullish Candle Through Three Averages | CTA Classic | CNStock:600519.SH | 1d | 0.00% | 0.00 | 0 | 17.6 | no_trades |
| #20 | Bullish Candle Through Three Averages | CTA Classic | CNStock:600519.SH | 1d | 0.00% | 0.00 | 0 | 17.6 | no_trades |
| #30 | Statistical Arbitrage Pack · Variant 1 | Stat Arb Pack | SA701 + SA701-C-1000 | 1m | 0.00% | 0.00 | 0 | 17.6 | no_trades |
| #31 | Statistical Arbitrage Pack · Variant 2 | Stat Arb Pack | SA701 + SA701-C-1000 | 1m | 0.00% | 0.00 | 0 | 17.6 | no_trades |
| #32 | Statistical Arbitrage Pack · Variant 3 | Stat Arb Pack | SA701 + SA701-C-1000 | 1m | 0.00% | 0.00 | 0 | 17.6 | no_trades |
| #33 | Statistical Arbitrage Pack · Variant 4 | Stat Arb Pack | SA701 + SA701-C-1000 | 1m | 0.00% | 0.00 | 0 | 17.6 | no_trades |
| #34 | Statistical Arbitrage Pack · Variant 5 | Stat Arb Pack | SA701 + SA701-C-1000 | 1m | 0.00% | 0.00 | 0 | 17.6 | no_trades |
| #35 | Statistical Arbitrage Pack · Variant 6 | Stat Arb Pack | SA701 + SA701-C-1000 | 1m | 0.00% | 0.00 | 0 | 17.6 | no_trades |
| #36 | Statistical Arbitrage Pack · Variant 7 | Stat Arb Pack | SA701 + SA701-C-1000 | 1m | 0.00% | 0.00 | 0 | 17.6 | no_trades |
| #37 | Statistical Arbitrage Pack · Variant 8 | Stat Arb Pack | SA701 + SA701-C-1000 | 1m | 0.00% | 0.00 | 0 | 17.6 | no_trades |
| #38 | Statistical Arbitrage Pack · Variant 9 | Stat Arb Pack | SA701 + SA701-C-1000 | 1m | 0.00% | 0.00 | 0 | 17.6 | no_trades |
| #39 | Statistical Arbitrage Pack · Variant 10 | Stat Arb Pack | SA701 + SA701-C-1000 | 1m | 0.00% | 0.00 | 0 | 17.6 | no_trades |
| #40 | Options Volatility Pack · Variant 1 | Options Vol Pack | SA701 + SA701-C-1000 | 1m | 0.00% | 0.00 | 0 | 17.6 | no_trades |
| #41 | Options Volatility Pack · Variant 2 | Options Vol Pack | SA701 + SA701-C-1000 | 1m | 0.00% | 0.00 | 0 | 17.6 | no_trades |
| #42 | Options Volatility Pack · Variant 3 | Options Vol Pack | SA701 + SA701-C-1000 | 1m | 0.00% | 0.00 | 0 | 17.6 | no_trades |
| #43 | Options Volatility Pack · Variant 4 | Options Vol Pack | SA701 + SA701-C-1000 | 1m | 0.00% | 0.00 | 0 | 17.6 | no_trades |
| #44 | Options Volatility Pack · Variant 5 | Options Vol Pack | SA701 + SA701-C-1000 | 1m | 0.00% | 0.00 | 0 | 17.6 | no_trades |
| #45 | Options Volatility Pack · Variant 6 | Options Vol Pack | SA701 + SA701-C-1000 | 1m | 0.00% | 0.00 | 0 | 17.6 | no_trades |
| #46 | Options Volatility Pack · Variant 7 | Options Vol Pack | SA701 + SA701-C-1000 | 1m | 0.00% | 0.00 | 0 | 17.6 | no_trades |
| #47 | Options Volatility Pack · Variant 8 | Options Vol Pack | SA701 + SA701-C-1000 | 1m | 0.00% | 0.00 | 0 | 17.6 | no_trades |
| #48 | Options Volatility Pack · Variant 9 | Options Vol Pack | SA701 + SA701-C-1000 | 1m | 0.00% | 0.00 | 0 | 17.6 | no_trades |
| #49 | Options Volatility Pack · Variant 10 | Options Vol Pack | SA701 + SA701-C-1000 | 1m | 0.00% | 0.00 | 0 | 17.6 | no_trades |
| #50 | Session Alpha Pack · Variant 1 | Session Alpha Pack | SA701 + SA701-C-1000 | 1m | 0.00% | 0.00 | 0 | 17.6 | no_trades |
| #51 | Session Alpha Pack · Variant 2 | Session Alpha Pack | SA701 + SA701-C-1000 | 1m | 0.00% | 0.00 | 0 | 17.6 | no_trades |
| #52 | Session Alpha Pack · Variant 3 | Session Alpha Pack | SA701 + SA701-C-1000 | 1m | 0.00% | 0.00 | 0 | 17.6 | no_trades |
| #53 | Session Alpha Pack · Variant 4 | Session Alpha Pack | SA701 + SA701-C-1000 | 1m | 0.00% | 0.00 | 0 | 17.6 | no_trades |
| #54 | Session Alpha Pack · Variant 5 | Session Alpha Pack | SA701 + SA701-C-1000 | 1m | 0.00% | 0.00 | 0 | 17.6 | no_trades |
| #55 | Session Alpha Pack · Variant 6 | Session Alpha Pack | SA701 + SA701-C-1000 | 1m | 0.00% | 0.00 | 0 | 17.6 | no_trades |
| #56 | Session Alpha Pack · Variant 7 | Session Alpha Pack | SA701 + SA701-C-1000 | 1m | 0.00% | 0.00 | 0 | 17.6 | no_trades |
| #57 | Session Alpha Pack · Variant 8 | Session Alpha Pack | SA701 + SA701-C-1000 | 1m | 0.00% | 0.00 | 0 | 17.6 | no_trades |
| #58 | Session Alpha Pack · Variant 9 | Session Alpha Pack | SA701 + SA701-C-1000 | 1m | 0.00% | 0.00 | 0 | 17.6 | no_trades |
| #59 | Session Alpha Pack · Variant 10 | Session Alpha Pack | SA701 + SA701-C-1000 | 1m | 0.00% | 0.00 | 0 | 17.6 | no_trades |
| #60 | Regime Switch Pack · Variant 1 | Regime Switch Pack | SA701 + SA701-C-1000 | 1m | 0.00% | 0.00 | 0 | 17.6 | no_trades |
| #61 | Regime Switch Pack · Variant 2 | Regime Switch Pack | SA701 + SA701-C-1000 | 1m | 0.00% | 0.00 | 0 | 17.6 | no_trades |
| #62 | Regime Switch Pack · Variant 3 | Regime Switch Pack | SA701 + SA701-C-1000 | 1m | 0.00% | 0.00 | 0 | 17.6 | no_trades |
| #63 | Regime Switch Pack · Variant 4 | Regime Switch Pack | SA701 + SA701-C-1000 | 1m | 0.00% | 0.00 | 0 | 17.6 | no_trades |
| #64 | Regime Switch Pack · Variant 5 | Regime Switch Pack | SA701 + SA701-C-1000 | 1m | 0.00% | 0.00 | 0 | 17.6 | no_trades |
| #65 | Regime Switch Pack · Variant 6 | Regime Switch Pack | SA701 + SA701-C-1000 | 1m | 0.00% | 0.00 | 0 | 17.6 | no_trades |
| #66 | Regime Switch Pack · Variant 7 | Regime Switch Pack | SA701 + SA701-C-1000 | 1m | 0.00% | 0.00 | 0 | 17.6 | no_trades |
| #67 | Regime Switch Pack · Variant 8 | Regime Switch Pack | SA701 + SA701-C-1000 | 1m | 0.00% | 0.00 | 0 | 17.6 | no_trades |
| #68 | Regime Switch Pack · Variant 9 | Regime Switch Pack | SA701 + SA701-C-1000 | 1m | 0.00% | 0.00 | 0 | 17.6 | no_trades |
| #69 | Regime Switch Pack · Variant 10 | Regime Switch Pack | SA701 + SA701-C-1000 | 1m | 0.00% | 0.00 | 0 | 17.6 | no_trades |
| #70 | Order Flow Proxy Pack · Variant 1 | Order Flow Pack | SA701 + SA701-C-1000 | 1m | 0.00% | 0.00 | 0 | 17.6 | no_trades |
| #71 | Order Flow Proxy Pack · Variant 2 | Order Flow Pack | SA701 + SA701-C-1000 | 1m | 0.00% | 0.00 | 0 | 17.6 | no_trades |
| #72 | Order Flow Proxy Pack · Variant 3 | Order Flow Pack | SA701 + SA701-C-1000 | 1m | 0.00% | 0.00 | 0 | 17.6 | no_trades |
| #73 | Order Flow Proxy Pack · Variant 4 | Order Flow Pack | SA701 + SA701-C-1000 | 1m | 0.00% | 0.00 | 0 | 17.6 | no_trades |
| #74 | Order Flow Proxy Pack · Variant 5 | Order Flow Pack | SA701 + SA701-C-1000 | 1m | 0.00% | 0.00 | 0 | 17.6 | no_trades |
| #75 | Order Flow Proxy Pack · Variant 6 | Order Flow Pack | SA701 + SA701-C-1000 | 1m | 0.00% | 0.00 | 0 | 17.6 | no_trades |
| #76 | Order Flow Proxy Pack · Variant 7 | Order Flow Pack | SA701 + SA701-C-1000 | 1m | 0.00% | 0.00 | 0 | 17.6 | no_trades |
| #77 | Order Flow Proxy Pack · Variant 8 | Order Flow Pack | SA701 + SA701-C-1000 | 1m | 0.00% | 0.00 | 0 | 17.6 | no_trades |
| #78 | Order Flow Proxy Pack · Variant 9 | Order Flow Pack | SA701 + SA701-C-1000 | 1m | 0.00% | 0.00 | 0 | 17.6 | no_trades |
| #79 | Order Flow Proxy Pack · Variant 10 | Order Flow Pack | SA701 + SA701-C-1000 | 1m | 0.00% | 0.00 | 0 | 17.6 | no_trades |
| #27 | SuperTrend | CTA Classic | USStock:SPY | 1d | -105.32% | -1.56 | 0 | 2.1 | no_trades |
