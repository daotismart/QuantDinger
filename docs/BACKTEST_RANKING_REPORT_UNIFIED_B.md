# QuantDinger 回测综合排名与分析报告

- 生成时间：2026-08-20 15:03 UTC
- 数据来源：`qd_backtest_runs`（**135** 条）
- 去重后策略样本：**128**（同名+同周期保留最高分）
- 评分：收益 40% + Sharpe 25% + 回撤 20% + 盈亏比 10% + 有成交 5%；极端异常值×0.25，零成交×0.35
- 指标已统一为小数收益率（自动识别历史百分比口径）
- 过滤条件：tag=`UNIFIED-20260820B`

---

## 1. 执行摘要

| 项目 | 数值 |
|------|------|
| 回测总数 | 135 |
| 去重策略数 | 128 |
| 有成交（去重） | 97 |
| 零成交（去重） | 31 |
| 策略族 | 13 |
| 综合第 1（去重） | **Dual Moving Average**（#216，得分 82.03，收益 12.11%） |
| 有成交且正收益 | 23 / 97 |

### 核心结论

1. **可交易样本榜首**：`Dual Moving Average`（得分 82.03，收益 12.11%，回撤 -7.46%，Sharpe 1.78）。
2. **策略族均值最高**：`US Portfolio`（平均得分 58.8，有成交 4/4）。
4. **极端异常值 17 个**已降权，不作为可信 alpha 依据。

## 2. 综合排名（去重 Top 15）

| 排名 | 得分 | 策略 | 族 | Run | 周期 | 总收益 | 最大回撤 | Sharpe | 胜率 | 成交 | 标记 |
|------|------|------|----|-----|------|--------|----------|--------|------|------|------|
| 1 | 82.0 | Dual Moving Average | CTA Classic | #216 | 4h | 12.11% | -7.46% | 1.78 | 50.00% | 6 | ok |
| 2 | 82.0 | Mean Reversion Pack · Variant 8 | Mean Reversion Pack | #251 | 1m | 2.84% | -1.64% | 7.41 | 37.50% | 16 | ok |
| 3 | 81.1 | Mean Reversion Pack · Variant 6 | Mean Reversion Pack | #249 | 1m | 1.84% | -1.54% | 6.02 | 42.86% | 21 | ok |
| 4 | 80.8 | Small and Large Cap Barbell | US Portfolio | #220 | 1d | 7.33% | -7.44% | 2.44 | 76.47% | 17 | ok |
| 5 | 77.7 | Options Volatility Pack · Variant 3 | Volatility Pack | #306 | 1m | 0.09% | -4.71% | 5.40 | 100.00% | 1 | ok |
| 6 | 76.8 | Mean Reversion Pack · Variant 2 | Mean Reversion Pack | #245 | 1m | 2.18% | -2.11% | 5.67 | 24.14% | 29 | ok |
| 7 | 72.5 | Order Flow Proxy Pack · Variant 5 | Order Flow Pack | #338 | 1m | 0.99% | -2.56% | 3.48 | 17.39% | 23 | ok |
| 8 | 69.5 | Low Volatility Rotation | US Portfolio | #222 | 1d | 6.45% | -4.76% | 1.86 | 87.50% | 16 | ok |
| 9 | 69.4 | Mean Reversion Pack · Variant 10 | Mean Reversion Pack | #253 | 1m | 0.87% | -1.77% | 2.14 | 30.00% | 20 | ok |
| 10 | 65.9 | Statistical Arbitrage Pack · Variant 3 | Stat Arb Pack | #296 | 1m | 0.45% | -1.55% | 1.65 | 57.14% | 7 | ok |
| 11 | 65.7 | Volatility Pack · Variant 5 | Volatility Pack | #278 | 1m | 1.44% | -5.00% | 1.58 | 22.73% | 22 | ok |
| 12 | 63.8 | Volatility Pack · Variant 8 | Volatility Pack | #281 | 1m | 1.28% | -4.92% | 1.44 | 20.51% | 39 | ok |
| 13 | 63.4 | Regime Switch Pack · Variant 5 | Regime Switch Pack | #328 | 1m | 1.09% | -4.89% | 1.29 | 66.67% | 3 | ok |
| 14 | 62.0 | Trend Following Pack · Variant 8 | Trend Pack | #231 | 1m | 1.06% | -5.56% | 1.23 | 20.00% | 30 | ok |
| 15 | 61.8 | Session Alpha Pack · Variant 9 | Session Alpha Pack | #322 | 1m | 1.06% | -5.65% | 1.22 | 17.14% | 35 | ok |

## 3. 有成交策略排名（去重）

| 排名 | 得分 | 策略 | 族 | 总收益 | 回撤 | Sharpe | 盈亏比 | 成交 | Run |
|------|------|------|----|--------|------|--------|--------|------|-----|
| 1 | 82.0 | Dual Moving Average | CTA Classic | 12.11% | -7.46% | 1.78 | 4.88 | 6 | #216 |
| 2 | 82.0 | Mean Reversion Pack · Variant 8 | Mean Reversion Pack | 2.84% | -1.64% | 7.41 | 7.08 | 16 | #251 |
| 3 | 81.1 | Mean Reversion Pack · Variant 6 | Mean Reversion Pack | 1.84% | -1.54% | 6.02 | 10.52 | 21 | #249 |
| 4 | 80.8 | Small and Large Cap Barbell | US Portfolio | 7.33% | -7.44% | 2.44 | 18.09 | 17 | #220 |
| 5 | 77.7 | Options Volatility Pack · Variant 3 | Volatility Pack | 0.09% | -4.71% | 5.40 | 87.63 | 1 | #306 |
| 6 | 76.8 | Mean Reversion Pack · Variant 2 | Mean Reversion Pack | 2.18% | -2.11% | 5.67 | 2.81 | 29 | #245 |
| 7 | 72.5 | Order Flow Proxy Pack · Variant 5 | Order Flow Pack | 0.99% | -2.56% | 3.48 | 1.42 | 23 | #338 |
| 8 | 69.5 | Low Volatility Rotation | US Portfolio | 6.45% | -4.76% | 1.86 | 0.54 | 16 | #222 |
| 9 | 69.4 | Mean Reversion Pack · Variant 10 | Mean Reversion Pack | 0.87% | -1.77% | 2.14 | 1.85 | 20 | #253 |
| 10 | 65.9 | Statistical Arbitrage Pack · Variant 3 | Stat Arb Pack | 0.45% | -1.55% | 1.65 | 1.48 | 7 | #296 |
| 11 | 65.7 | Volatility Pack · Variant 5 | Volatility Pack | 1.44% | -5.00% | 1.58 | 1.94 | 22 | #278 |
| 12 | 63.8 | Volatility Pack · Variant 8 | Volatility Pack | 1.28% | -4.92% | 1.44 | 1.39 | 39 | #281 |
| 13 | 63.4 | Regime Switch Pack · Variant 5 | Regime Switch Pack | 1.09% | -4.89% | 1.29 | 1.65 | 3 | #328 |
| 14 | 62.0 | Trend Following Pack · Variant 8 | Trend Pack | 1.06% | -5.56% | 1.23 | 1.26 | 30 | #231 |
| 15 | 61.8 | Session Alpha Pack · Variant 9 | Session Alpha Pack | 1.06% | -5.65% | 1.22 | 1.23 | 35 | #322 |
| 16 | 61.1 | Order Flow Proxy Pack · Variant 4 | Order Flow Pack | 0.83% | -4.40% | 1.02 | 1.17 | 46 | #337 |
| 17 | 58.6 | Quality Growth Multi-Factor | US Portfolio | -0.74% | -12.32% | 0.10 | 6.17 | 13 | #223 |
| 18 | 58.3 | Regime Switch Pack · Variant 7 | Regime Switch Pack | 0.45% | -5.41% | 0.67 | 1.09 | 21 | #330 |
| 19 | 56.8 | Breakout & Momentum Pack · Variant 10 | Breakout Pack | 0.26% | -5.93% | 0.49 | 1.01 | 7 | #243 |
| 20 | 54.9 | Order Flow Proxy Pack · Variant 7 | Order Flow Pack | 1.35% | -99.82% | 3.98 | 1.79 | 15 | #340 |
| 21 | 54.6 | Volatility Pack · Variant 2 | Volatility Pack | 0.83% | -69.43% | 4.89 | 1.89 | 4 | #275 |
| 22 | 52.1 | Trend Following Pack · Variant 1 | Trend Pack | -0.48% | -6.37% | -0.21 | 0.89 | 19 | #215 |
| 23 | 50.9 | Volatility Pack · Variant 7 | Volatility Pack | -0.66% | -6.55% | -0.37 | 0.87 | 22 | #280 |
| 24 | 49.8 | Regime Switch Pack · Variant 6 | Regime Switch Pack | -0.82% | -6.73% | -0.52 | 0.82 | 29 | #329 |
| 25 | 48.3 | Mean Reversion Pack · Variant 9 | Mean Reversion Pack | -0.33% | -1.58% | -1.43 | 0.78 | 21 | #252 |
| 26 | 46.0 | Mean Reversion Pack · Variant 1 | Mean Reversion Pack | 0.02% | -41.11% | 0.20 | 10.30 | 2 | #244 |
| 27 | 46.0 | Statistical Arbitrage Pack · Variant 10 | Stat Arb Pack | 0.02% | -41.11% | 0.20 | 10.30 | 2 | #303 |
| 28 | 45.4 | Options Volatility Pack · Variant 6 | Volatility Pack | 0.39% | -86.58% | 1.54 | 1.18 | 25 | #309 |
| 29 | 45.2 | Carry & Roll Yield Pack · Variant 8 | Carry Pack | -0.56% | -1.74% | -2.14 | 0.83 | 38 | #261 |
| 30 | 44.5 | Mean Reversion Pack · Variant 5 | Mean Reversion Pack | -0.62% | -1.82% | -2.50 | 0.52 | 11 | #248 |
| 31 | 44.5 | Relative Value Pack · Variant 2 | Relative Value Pack | -0.62% | -1.82% | -2.50 | 0.52 | 11 | #265 |
| 32 | 44.5 | Statistical Arbitrage Pack · Variant 1 | Stat Arb Pack | -0.62% | -1.82% | -2.49 | 0.52 | 11 | #294 |
| 33 | 43.4 | Breakout & Momentum Pack · Variant 9 | Breakout Pack | -1.49% | -2.28% | -3.22 | 0.53 | 28 | #242 |
| 34 | 43.2 | Regime Switch Pack · Variant 3 | Regime Switch Pack | -1.31% | -1.44% | -6.07 | 0.12 | 11 | #326 |
| 35 | 43.2 | Volatility Pack · Variant 4 | Volatility Pack | -1.38% | -3.35% | -6.32 | 0.62 | 38 | #277 |
| 36 | 42.9 | Session Alpha Pack · Variant 10 | Session Alpha Pack | -1.80% | -2.02% | -7.24 | 0.37 | 23 | #323 |
| 37 | 42.2 | Session Alpha Pack · Variant 2 | Session Alpha Pack | -2.37% | -3.54% | -4.77 | 0.69 | 69 | #315 |
| 38 | 41.5 | Market Microstructure Pack · Variant 8 | Microstructure Pack | -2.34% | -3.45% | -6.04 | 0.31 | 23 | #291 |
| 39 | 40.5 | Market Microstructure Pack · Variant 6 | Microstructure Pack | -3.09% | -3.09% | -19.57 | 0.06 | 20 | #289 |
| 40 | 39.8 | Carry & Roll Yield Pack · Variant 7 | Carry Pack | -3.80% | -4.90% | -10.49 | 0.51 | 79 | #260 |
| 41 | 39.6 | Mean Reversion Pack · Variant 7 | Mean Reversion Pack | -3.84% | -4.48% | -11.20 | 0.35 | 95 | #250 |
| 42 | 39.2 | Session Alpha Pack · Variant 3 | Session Alpha Pack | -4.16% | -5.20% | -11.93 | 0.50 | 100 | #316 |
| 43 | 39.2 | Order Flow Proxy Pack · Variant 6 | Order Flow Pack | -4.22% | -4.44% | -13.49 | 0.31 | 45 | #339 |
| 44 | 39.2 | Relative Value Pack · Variant 7 | Relative Value Pack | -2.84% | -8.79% | -2.50 | 0.71 | 108 | #270 |
| 45 | 39.0 | Session Alpha Pack · Variant 8 | Session Alpha Pack | -3.41% | -7.32% | -3.01 | 0.55 | 16 | #321 |
| 46 | 39.0 | Carry & Roll Yield Pack · Variant 4 | Carry Pack | -4.72% | -4.72% | -11.82 | 0.52 | 114 | #257 |
| 47 | 38.9 | Breakout & Momentum Pack · Variant 6 | Breakout Pack | -4.17% | -5.79% | -11.70 | 0.48 | 67 | #239 |
| 48 | 38.9 | Market Microstructure Pack · Variant 1 | Microstructure Pack | -4.17% | -5.79% | -11.69 | 0.48 | 67 | #284 |
| 49 | 38.6 | Statistical Arbitrage Pack · Variant 2 | Stat Arb Pack | -4.22% | -4.30% | -13.46 | 0.00 | 18 | #295 |
| 50 | 37.8 | Statistical Arbitrage Pack · Variant 9 | Stat Arb Pack | -3.96% | -9.19% | -3.53 | 0.68 | 124 | #302 |
| 51 | 37.7 | Statistical Arbitrage Pack · Variant 5 | Stat Arb Pack | -5.12% | -5.12% | -13.19 | 0.21 | 48 | #298 |
| 52 | 37.5 | Volatility Pack · Variant 10 | Volatility Pack | -4.91% | -6.77% | -14.68 | 0.40 | 83 | #283 |
| 53 | 37.5 | Trend Following Pack · Variant 2 | Trend Pack | -3.67% | -9.62% | -3.23 | 0.48 | 34 | #225 |
| 54 | 37.2 | Options Volatility Pack · Variant 8 | Volatility Pack | -5.17% | -5.17% | -12.59 | 0.00 | 14 | #311 |
| 55 | 36.4 | Breakout & Momentum Pack · Variant 2 | Breakout Pack | -5.74% | -5.83% | -14.03 | 0.03 | 38 | #235 |
| 56 | 36.2 | Options Volatility Pack · Variant 4 | Volatility Pack | -0.02% | -70.01% | -0.14 | 0.97 | 7 | #307 |
| 57 | 36.1 | Carry & Roll Yield Pack · Variant 10 | Carry Pack | -6.38% | -6.38% | -19.39 | 0.36 | 119 | #263 |
| 58 | 35.9 | MACD and KDJ Confirmation | CTA Classic | -5.97% | -8.37% | -2.13 | 0.54 | 33 | #219 |
| 59 | 35.8 | Order Flow Proxy Pack · Variant 10 | Order Flow Pack | -6.12% | -6.48% | -13.36 | 0.09 | 51 | #343 |
| 60 | 35.3 | Volatility Pack · Variant 3 | Volatility Pack | -7.00% | -7.00% | -18.93 | 0.38 | 115 | #276 |
| 61 | 34.7 | Session Alpha Pack · Variant 4 | Session Alpha Pack | -6.99% | -7.85% | -6.53 | 0.31 | 45 | #317 |
| 62 | 34.4 | Regime Switch Pack · Variant 2 | Regime Switch Pack | -6.81% | -8.00% | -6.87 | 0.11 | 10 | #325 |
| 63 | 34.0 | Session Alpha Pack · Variant 7 | Session Alpha Pack | -7.07% | -8.33% | -6.57 | 0.10 | 7 | #320 |
| 64 | 33.8 | Regime Switch Pack · Variant 10 | Regime Switch Pack | -7.34% | -8.26% | -7.43 | 0.14 | 24 | #333 |
| 65 | 33.1 | Relative Value Pack · Variant 9 | Relative Value Pack | -8.21% | -8.70% | -7.99 | 0.33 | 49 | #272 |
| 66 | 32.1 | Regime Switch Pack · Variant 8 | Regime Switch Pack | -8.51% | -9.77% | -8.00 | 0.22 | 57 | #331 |
| 67 | 31.8 | Market Microstructure Pack · Variant 2 | Microstructure Pack | -8.65% | -9.69% | -9.14 | 0.13 | 50 | #285 |
| 68 | 31.4 | Order Flow Proxy Pack · Variant 9 | Order Flow Pack | -9.08% | -9.97% | -8.55 | 0.21 | 87 | #342 |
| 69 | 28.1 | Carry & Roll Yield Pack · Variant 2 | Carry Pack | -11.52% | -12.07% | -11.15 | 0.35 | 129 | #255 |
| 70 | 26.8 | Volatility Pack · Variant 6 | Volatility Pack | -12.36% | -12.36% | -12.92 | 0.16 | 107 | #279 |
| 71 | 26.7 | Breakout & Momentum Pack · Variant 4 | Breakout Pack | -0.21% | -63.50% | -1.62 | 0.00 | 2 | #237 |
| 72 | 26.4 | Momentum Top-N Rotation | US Portfolio | -11.50% | -14.42% | -2.23 | 0.07 | 22 | #221 |
| 73 | 25.7 | Breakout & Momentum Pack · Variant 5 | Breakout Pack | -0.39% | -74.04% | -2.87 | 0.53 | 7 | #238 |
| 74 | 24.9 | Carry & Roll Yield Pack · Variant 1 | Carry Pack | -13.65% | -14.18% | -13.36 | 0.32 | 149 | #254 |
| 75 | 24.8 | Breakout & Momentum Pack · Variant 8 | Breakout Pack | -0.24% | -55.71% | -2.46 | 0.00 | 2 | #241 |
| 76 | 24.6 | Mean Reversion Pack · Variant 4 | Mean Reversion Pack | -0.66% | -78.06% | -4.20 | 0.12 | 6 | #247 |
| 77 | 21.0 | Order Flow Proxy Pack · Variant 3 | Order Flow Pack | -15.93% | -16.19% | -15.67 | 0.03 | 71 | #336 |
| 78 | 18.3 | Market Microstructure Pack · Variant 7 | Microstructure Pack | -17.97% | -17.97% | -18.93 | 0.14 | 157 | #290 |
| 79 | 18.0 | Order Flow Proxy Pack · Variant 8 | Order Flow Pack | -18.22% | -18.28% | -18.10 | 0.16 | 133 | #341 |
| 80 | 17.1 | Order Flow Proxy Pack · Variant 2 | Order Flow Pack | -18.76% | -19.28% | -18.94 | 0.23 | 203 | #335 |
| 81 | 9.9 | Market Microstructure Pack · Variant 10 | Microstructure Pack | -3.74% | -4.43% | -20.45 | 0.26 | 73 | #293 |
| 82 | 8.7 | Carry & Roll Yield Pack · Variant 9 | Carry Pack | -6.93% | -6.93% | -24.77 | 0.15 | 87 | #262 |
| 83 | 8.4 | Options Volatility Pack · Variant 10 | Volatility Pack | -7.53% | -7.91% | -20.92 | 0.12 | 51 | #313 |
| 84 | 8.1 | Relative Value Pack · Variant 5 | Relative Value Pack | -9.01% | -9.05% | -20.96 | 0.38 | 139 | #268 |
| 85 | 7.9 | Market Microstructure Pack · Variant 3 | Microstructure Pack | -9.42% | -9.44% | -25.05 | 0.29 | 130 | #286 |
| 86 | 7.5 | Session Alpha Pack · Variant 1 | Session Alpha Pack | -10.51% | -10.53% | -23.07 | 0.36 | 188 | #314 |
| 87 | 7.4 | Options Volatility Pack · Variant 5 | Volatility Pack | -10.58% | -10.58% | -22.92 | 0.33 | 191 | #308 |
| 88 | 6.9 | Market Microstructure Pack · Variant 4 | Microstructure Pack | -11.57% | -11.63% | -52.55 | 0.08 | 201 | #287 |
| 89 | 6.4 | Market Microstructure Pack · Variant 5 | Microstructure Pack | -13.00% | -13.04% | -36.12 | 0.10 | 145 | #288 |
| 90 | 6.0 | Relative Value Pack · Variant 3 | Relative Value Pack | -14.17% | -14.17% | -41.33 | 0.17 | 192 | #266 |
| 91 | 3.8 | Options Volatility Pack · Variant 2 | Volatility Pack | -19.87% | -19.87% | -73.96 | 0.09 | 310 | #305 |
| 92 | 3.6 | Order Flow Proxy Pack · Variant 1 | Order Flow Pack | -21.54% | -21.54% | -22.02 | 0.08 | 230 | #334 |
| 93 | 3.3 | Market Microstructure Pack · Variant 9 | Microstructure Pack | -23.74% | -24.22% | -65.80 | 0.16 | 397 | #292 |
| 94 | 3.1 | Session Alpha Pack · Variant 6 | Session Alpha Pack | -25.55% | -25.55% | -76.27 | 0.11 | 428 | #319 |
| 95 | 3.1 | Session Alpha Pack · Variant 5 | Session Alpha Pack | -25.79% | -25.82% | -77.08 | 0.09 | 429 | #318 |
| 96 | 2.6 | Options Volatility Pack · Variant 9 | Volatility Pack | -29.34% | -30.06% | -32.03 | 0.14 | 379 | #312 |
| 97 | 1.3 | Options Volatility Pack · Variant 7 | Volatility Pack | -43.18% | -43.18% | -110.27 | 0.07 | 722 | #310 |

## 4. 策略族排行榜

| 排名 | 策略族 | 策略数 | 有成交 | 平均得分 | 平均收益* | 总成交 | 族内最佳 |
|------|--------|--------|--------|----------|-----------|--------|----------|
| 1 | US Portfolio | 4 | 4 | 58.8 | 0.39% | 68 | Small and Large Cap Barbell (#220) |
| 2 | Mean Reversion Pack | 10 | 9 | 53.0 | 0.26% | 221 | Mean Reversion Pack · Variant 8 (#251) |
| 3 | CTA Classic | 4 | 2 | 38.2 | 3.07% | 39 | Dual Moving Average (#216) |
| 4 | Regime Switch Pack | 10 | 7 | 36.7 | -3.32% | 155 | Regime Switch Pack · Variant 5 (#328) |
| 5 | Order Flow Pack | 10 | 10 | 35.5 | -9.07% | 904 | Order Flow Proxy Pack · Variant 5 (#338) |
| 6 | Stat Arb Pack | 10 | 6 | 34.1 | -2.24% | 210 | Statistical Arbitrage Pack · Variant 3 (#296) |
| 7 | Volatility Pack | 20 | 17 | 32.5 | -8.12% | 2130 | Options Volatility Pack · Variant 3 (#306) |
| 8 | Session Alpha Pack | 10 | 10 | 30.8 | -8.66% | 1340 | Session Alpha Pack · Variant 9 (#322) |
| 9 | Breakout Pack | 10 | 7 | 30.5 | -1.71% | 151 | Breakout & Momentum Pack · Variant 10 (#243) |
| 10 | Carry Pack | 10 | 7 | 27.4 | -6.80% | 715 | Carry & Roll Yield Pack · Variant 8 (#261) |
| 11 | Trend Pack | 10 | 3 | 27.4 | -1.03% | 83 | Trend Following Pack · Variant 8 (#231) |
| 12 | Relative Value Pack | 10 | 5 | 21.8 | -6.97% | 499 | Relative Value Pack · Variant 2 (#265) |
| 13 | Microstructure Pack | 10 | 10 | 20.5 | -9.77% | 1263 | Market Microstructure Pack · Variant 8 (#291) |

\*平均收益仅统计有成交样本。

## 5. 方法说明与限制

- 跨族不可直接比绝对收益：标的、周期、资金、费率可能不同。
- 同策略重复回测时，总榜以去重结果为主；附录保留全量。
- Pack 依赖国内期货分钟线与期权合约键；连续合约 `SA0` 与月份码 `SA701` 不是同一符号。

## 附录 A：全量回测清单（按得分）

| Run | 策略 | 族 | 标的 | 周期 | 收益 | Sharpe | 成交 | 得分 | 标记 |
|-----|------|----|------|------|------|--------|------|------|------|
| #216 | Dual Moving Average | CTA Classic | Crypto:BTC/USDT | 4h | 12.11% | 1.78 | 6 | 82.0 | ok |
| #251 | Mean Reversion Pack · Variant 8 | Mean Reversion Pack | SA701 + SA701-C-1000 | 1m | 2.84% | 7.41 | 16 | 82.0 | ok |
| #249 | Mean Reversion Pack · Variant 6 | Mean Reversion Pack | SA701 + SA701-C-1000 | 1m | 1.84% | 6.02 | 21 | 81.1 | ok |
| #220 | Small and Large Cap Barbell | US Portfolio | AAPL + MSFT + NVDA + AMZN + META + GOOG… | 1d | 7.33% | 2.44 | 17 | 80.8 | ok |
| #306 | Options Volatility Pack · Variant 3 | Volatility Pack | SA701 + SA701-C-1000 | 1m | 0.09% | 5.40 | 1 | 77.7 | ok |
| #245 | Mean Reversion Pack · Variant 2 | Mean Reversion Pack | SA701 + SA701-C-1000 | 1m | 2.18% | 5.67 | 29 | 76.8 | ok |
| #338 | Order Flow Proxy Pack · Variant 5 | Order Flow Pack | SA701 + SA701-C-1000 | 1m | 0.99% | 3.48 | 23 | 72.5 | ok |
| #222 | Low Volatility Rotation | US Portfolio | AAPL + MSFT + NVDA + AMZN + META + GOOG… | 1d | 6.45% | 1.86 | 16 | 69.5 | ok |
| #253 | Mean Reversion Pack · Variant 10 | Mean Reversion Pack | SA701 + SA701-C-1000 | 1m | 0.87% | 2.14 | 20 | 69.4 | ok |
| #296 | Statistical Arbitrage Pack · Variant 3 | Stat Arb Pack | SA701 + SA701-C-1000 | 1m | 0.45% | 1.65 | 7 | 65.9 | ok |
| #278 | Volatility Pack · Variant 5 | Volatility Pack | SA701 + SA701-C-1000 | 1m | 1.44% | 1.58 | 22 | 65.7 | ok |
| #281 | Volatility Pack · Variant 8 | Volatility Pack | SA701 + SA701-C-1000 | 1m | 1.28% | 1.44 | 39 | 63.8 | ok |
| #328 | Regime Switch Pack · Variant 5 | Regime Switch Pack | SA701 + SA701-C-1000 | 1m | 1.09% | 1.29 | 3 | 63.4 | ok |
| #231 | Trend Following Pack · Variant 8 | Trend Pack | SA701 + SA701-C-1000 | 1m | 1.06% | 1.23 | 30 | 62.0 | ok |
| #322 | Session Alpha Pack · Variant 9 | Session Alpha Pack | SA701 + SA701-C-1000 | 1m | 1.06% | 1.22 | 35 | 61.8 | ok |
| #337 | Order Flow Proxy Pack · Variant 4 | Order Flow Pack | SA701 + SA701-C-1000 | 1m | 0.83% | 1.02 | 46 | 61.1 | ok |
| #223 | Quality Growth Multi-Factor | US Portfolio | AAPL + MSFT + NVDA + AMZN + META + GOOG… | 1d | -0.74% | 0.10 | 13 | 58.6 | ok |
| #330 | Regime Switch Pack · Variant 7 | Regime Switch Pack | SA701 + SA701-C-1000 | 1m | 0.45% | 0.67 | 21 | 58.3 | ok |
| #243 | Breakout & Momentum Pack · Variant 10 | Breakout Pack | SA701 + SA701-C-1000 | 1m | 0.26% | 0.49 | 7 | 56.8 | ok |
| #340 | Order Flow Proxy Pack · Variant 7 | Order Flow Pack | SA701 + SA701-C-1000 | 1m | 1.35% | 3.98 | 15 | 54.9 | ok |
| #275 | Volatility Pack · Variant 2 | Volatility Pack | SA701 + SA701-C-1000 | 1m | 0.83% | 4.89 | 4 | 54.6 | ok |
| #215 | Trend Following Pack · Variant 1 | Trend Pack | SA701 + SA701-C-1000 | 1m | -0.48% | -0.21 | 19 | 52.1 | ok |
| #224 | Trend Following Pack · Variant 1 | Trend Pack | SA701 + SA701-C-1000 | 1m | -0.58% | -0.29 | 19 | 51.5 | ok |
| #280 | Volatility Pack · Variant 7 | Volatility Pack | SA701 + SA701-C-1000 | 1m | -0.66% | -0.37 | 22 | 50.9 | ok |
| #329 | Regime Switch Pack · Variant 6 | Regime Switch Pack | SA701 + SA701-C-1000 | 1m | -0.82% | -0.52 | 29 | 49.8 | ok |
| #252 | Mean Reversion Pack · Variant 9 | Mean Reversion Pack | SA701 + SA701-C-1000 | 1m | -0.33% | -1.43 | 21 | 48.3 | ok |
| #244 | Mean Reversion Pack · Variant 1 | Mean Reversion Pack | SA701 + SA701-C-1000 | 1m | 0.02% | 0.20 | 2 | 46.0 | ok |
| #303 | Statistical Arbitrage Pack · Variant 10 | Stat Arb Pack | SA701 + SA701-C-1000 | 1m | 0.02% | 0.20 | 2 | 46.0 | ok |
| #309 | Options Volatility Pack · Variant 6 | Volatility Pack | SA701 + SA701-C-1000 | 1m | 0.39% | 1.54 | 25 | 45.4 | ok |
| #261 | Carry & Roll Yield Pack · Variant 8 | Carry Pack | SA701 + SA701-C-1000 | 1m | -0.56% | -2.14 | 38 | 45.2 | ok |
| #248 | Mean Reversion Pack · Variant 5 | Mean Reversion Pack | SA701 + SA701-C-1000 | 1m | -0.62% | -2.50 | 11 | 44.5 | ok |
| #265 | Relative Value Pack · Variant 2 | Relative Value Pack | SA701 + SA701-C-1000 | 1m | -0.62% | -2.50 | 11 | 44.5 | ok |
| #294 | Statistical Arbitrage Pack · Variant 1 | Stat Arb Pack | SA701 + SA701-C-1000 | 1m | -0.62% | -2.49 | 11 | 44.5 | ok |
| #242 | Breakout & Momentum Pack · Variant 9 | Breakout Pack | SA701 + SA701-C-1000 | 1m | -1.49% | -3.22 | 28 | 43.4 | ok |
| #326 | Regime Switch Pack · Variant 3 | Regime Switch Pack | SA701 + SA701-C-1000 | 1m | -1.31% | -6.07 | 11 | 43.2 | ok |
| #277 | Volatility Pack · Variant 4 | Volatility Pack | SA701 + SA701-C-1000 | 1m | -1.38% | -6.32 | 38 | 43.2 | ok |
| #323 | Session Alpha Pack · Variant 10 | Session Alpha Pack | SA701 + SA701-C-1000 | 1m | -1.80% | -7.24 | 23 | 42.9 | ok |
| #315 | Session Alpha Pack · Variant 2 | Session Alpha Pack | SA701 + SA701-C-1000 | 1m | -2.37% | -4.77 | 69 | 42.2 | ok |
| #291 | Market Microstructure Pack · Variant 8 | Microstructure Pack | SA701 + SA701-C-1000 | 1m | -2.34% | -6.04 | 23 | 41.5 | ok |
| #289 | Market Microstructure Pack · Variant 6 | Microstructure Pack | SA701 + SA701-C-1000 | 1m | -3.09% | -19.57 | 20 | 40.5 | ok |
| #260 | Carry & Roll Yield Pack · Variant 7 | Carry Pack | SA701 + SA701-C-1000 | 1m | -3.80% | -10.49 | 79 | 39.8 | ok |
| #250 | Mean Reversion Pack · Variant 7 | Mean Reversion Pack | SA701 + SA701-C-1000 | 1m | -3.84% | -11.20 | 95 | 39.6 | ok |
| #316 | Session Alpha Pack · Variant 3 | Session Alpha Pack | SA701 + SA701-C-1000 | 1m | -4.16% | -11.93 | 100 | 39.2 | ok |
| #339 | Order Flow Proxy Pack · Variant 6 | Order Flow Pack | SA701 + SA701-C-1000 | 1m | -4.22% | -13.49 | 45 | 39.2 | ok |
| #270 | Relative Value Pack · Variant 7 | Relative Value Pack | SA701 + SA701-C-1000 | 1m | -2.84% | -2.50 | 108 | 39.2 | ok |
| #321 | Session Alpha Pack · Variant 8 | Session Alpha Pack | SA701 + SA701-C-1000 | 1m | -3.41% | -3.01 | 16 | 39.0 | ok |
| #257 | Carry & Roll Yield Pack · Variant 4 | Carry Pack | SA701 + SA701-C-1000 | 1m | -4.72% | -11.82 | 114 | 39.0 | ok |
| #239 | Breakout & Momentum Pack · Variant 6 | Breakout Pack | SA701 + SA701-C-1000 | 1m | -4.17% | -11.70 | 67 | 38.9 | ok |
| #284 | Market Microstructure Pack · Variant 1 | Microstructure Pack | SA701 + SA701-C-1000 | 1m | -4.17% | -11.69 | 67 | 38.9 | ok |
| #295 | Statistical Arbitrage Pack · Variant 2 | Stat Arb Pack | SA701 + SA701-C-1000 | 1m | -4.22% | -13.46 | 18 | 38.6 | ok |
| #302 | Statistical Arbitrage Pack · Variant 9 | Stat Arb Pack | SA701 + SA701-C-1000 | 1m | -3.96% | -3.53 | 124 | 37.8 | ok |
| #298 | Statistical Arbitrage Pack · Variant 5 | Stat Arb Pack | SA701 + SA701-C-1000 | 1m | -5.12% | -13.19 | 48 | 37.7 | ok |
| #283 | Volatility Pack · Variant 10 | Volatility Pack | SA701 + SA701-C-1000 | 1m | -4.91% | -14.68 | 83 | 37.5 | ok |
| #225 | Trend Following Pack · Variant 2 | Trend Pack | SA701 + SA701-C-1000 | 1m | -3.67% | -3.23 | 34 | 37.5 | ok |
| #311 | Options Volatility Pack · Variant 8 | Volatility Pack | SA701 + SA701-C-1000 | 1m | -5.17% | -12.59 | 14 | 37.2 | ok |
| #235 | Breakout & Momentum Pack · Variant 2 | Breakout Pack | SA701 + SA701-C-1000 | 1m | -5.74% | -14.03 | 38 | 36.4 | ok |
| #307 | Options Volatility Pack · Variant 4 | Volatility Pack | SA701 + SA701-C-1000 | 1m | -0.02% | -0.14 | 7 | 36.2 | ok |
| #263 | Carry & Roll Yield Pack · Variant 10 | Carry Pack | SA701 + SA701-C-1000 | 1m | -6.38% | -19.39 | 119 | 36.1 | ok |
| #219 | MACD and KDJ Confirmation | CTA Classic | Crypto:BTC/USDT | 4h | -5.97% | -2.13 | 33 | 35.9 | ok |
| #343 | Order Flow Proxy Pack · Variant 10 | Order Flow Pack | SA701 + SA701-C-1000 | 1m | -6.12% | -13.36 | 51 | 35.8 | ok |
| #276 | Volatility Pack · Variant 3 | Volatility Pack | SA701 + SA701-C-1000 | 1m | -7.00% | -18.93 | 115 | 35.3 | ok |
| #317 | Session Alpha Pack · Variant 4 | Session Alpha Pack | SA701 + SA701-C-1000 | 1m | -6.99% | -6.53 | 45 | 34.7 | ok |
| #325 | Regime Switch Pack · Variant 2 | Regime Switch Pack | SA701 + SA701-C-1000 | 1m | -6.81% | -6.87 | 10 | 34.4 | ok |
| #320 | Session Alpha Pack · Variant 7 | Session Alpha Pack | SA701 + SA701-C-1000 | 1m | -7.07% | -6.57 | 7 | 34.0 | ok |
| #333 | Regime Switch Pack · Variant 10 | Regime Switch Pack | SA701 + SA701-C-1000 | 1m | -7.34% | -7.43 | 24 | 33.8 | ok |
| #272 | Relative Value Pack · Variant 9 | Relative Value Pack | SA701 + SA701-C-1000 | 1m | -8.21% | -7.99 | 49 | 33.1 | ok |
| #331 | Regime Switch Pack · Variant 8 | Regime Switch Pack | SA701 + SA701-C-1000 | 1m | -8.51% | -8.00 | 57 | 32.1 | ok |
| #285 | Market Microstructure Pack · Variant 2 | Microstructure Pack | SA701 + SA701-C-1000 | 1m | -8.65% | -9.14 | 50 | 31.8 | ok |
| #342 | Order Flow Proxy Pack · Variant 9 | Order Flow Pack | SA701 + SA701-C-1000 | 1m | -9.08% | -8.55 | 87 | 31.4 | ok |
| #255 | Carry & Roll Yield Pack · Variant 2 | Carry Pack | SA701 + SA701-C-1000 | 1m | -11.52% | -11.15 | 129 | 28.1 | ok |
| #279 | Volatility Pack · Variant 6 | Volatility Pack | SA701 + SA701-C-1000 | 1m | -12.36% | -12.92 | 107 | 26.8 | ok |
| #237 | Breakout & Momentum Pack · Variant 4 | Breakout Pack | SA701 + SA701-C-1000 | 1m | -0.21% | -1.62 | 2 | 26.7 | ok |
| #221 | Momentum Top-N Rotation | US Portfolio | AAPL + MSFT + NVDA + AMZN + META + GOOG… | 1d | -11.50% | -2.23 | 22 | 26.4 | ok |
| #238 | Breakout & Momentum Pack · Variant 5 | Breakout Pack | SA701 + SA701-C-1000 | 1m | -0.39% | -2.87 | 7 | 25.7 | ok |
| #254 | Carry & Roll Yield Pack · Variant 1 | Carry Pack | SA701 + SA701-C-1000 | 1m | -13.65% | -13.36 | 149 | 24.9 | ok |
| #241 | Breakout & Momentum Pack · Variant 8 | Breakout Pack | SA701 + SA701-C-1000 | 1m | -0.24% | -2.46 | 2 | 24.8 | ok |
| #247 | Mean Reversion Pack · Variant 4 | Mean Reversion Pack | SA701 + SA701-C-1000 | 1m | -0.66% | -4.20 | 6 | 24.6 | ok |
| #336 | Order Flow Proxy Pack · Variant 3 | Order Flow Pack | SA701 + SA701-C-1000 | 1m | -15.93% | -15.67 | 71 | 21.0 | ok |
| #290 | Market Microstructure Pack · Variant 7 | Microstructure Pack | SA701 + SA701-C-1000 | 1m | -17.97% | -18.93 | 157 | 18.3 | ok |
| #341 | Order Flow Proxy Pack · Variant 8 | Order Flow Pack | SA701 + SA701-C-1000 | 1m | -18.22% | -18.10 | 133 | 18.0 | ok |
| #208 | Trend Following Pack · Variant 1 | Trend Pack | SA701 + SA701-C-1000 | 1m | 0.00% | 0.00 | 0 | 17.5 | no_trades |
| #209 | Trend Following Pack · Variant 1 | Trend Pack | SA701 + SA701-C-1000 | 1m | 0.00% | 0.00 | 0 | 17.5 | no_trades |
| #210 | Trend Following Pack · Variant 1 | Trend Pack | SA701 + SA701-C-1000 | 1m | 0.00% | 0.00 | 0 | 17.5 | no_trades |
| #211 | Trend Following Pack · Variant 1 | Trend Pack | SA701 + SA701-C-1000 | 1m | 0.00% | 0.00 | 0 | 17.5 | no_trades |
| #212 | Trend Following Pack · Variant 2 | Trend Pack | SA701 + SA701-C-1000 | 1m | 0.00% | 0.00 | 0 | 17.5 | no_trades |
| #213 | Trend Following Pack · Variant 3 | Trend Pack | SA701 + SA701-C-1000 | 1m | 0.00% | 0.00 | 0 | 17.5 | no_trades |
| #217 | Bullish Candle Through Three Averages | CTA Classic | CNStock:600519.SH | 1d | 0.00% | 0.00 | 0 | 17.5 | no_trades |
| #218 | Bullish Three Averages With Trend Filter | CTA Classic | CNStock:600519.SH | 1d | 0.00% | 0.00 | 0 | 17.5 | no_trades |
| #226 | Trend Following Pack · Variant 3 | Trend Pack | SA701 + SA701-C-1000 | 1m | 0.00% | 0.00 | 0 | 17.5 | no_trades |
| #227 | Trend Following Pack · Variant 4 | Trend Pack | SA701 + SA701-C-1000 | 1m | 0.00% | 0.00 | 0 | 17.5 | no_trades |
| #228 | Trend Following Pack · Variant 5 | Trend Pack | SA701 + SA701-C-1000 | 1m | 0.00% | 0.00 | 0 | 17.5 | no_trades |
| #229 | Trend Following Pack · Variant 6 | Trend Pack | SA701 + SA701-C-1000 | 1m | 0.00% | 0.00 | 0 | 17.5 | no_trades |
| #230 | Trend Following Pack · Variant 7 | Trend Pack | SA701 + SA701-C-1000 | 1m | 0.00% | 0.00 | 0 | 17.5 | no_trades |
| #232 | Trend Following Pack · Variant 9 | Trend Pack | SA701 + SA701-C-1000 | 1m | 0.00% | 0.00 | 0 | 17.5 | no_trades |
| #233 | Trend Following Pack · Variant 10 | Trend Pack | SA701 + SA701-C-1000 | 1m | 0.00% | 0.00 | 0 | 17.5 | no_trades |
| #234 | Breakout & Momentum Pack · Variant 1 | Breakout Pack | SA701 + SA701-C-1000 | 1m | 0.00% | 0.00 | 0 | 17.5 | no_trades |
| #236 | Breakout & Momentum Pack · Variant 3 | Breakout Pack | SA701 + SA701-C-1000 | 1m | 0.00% | 0.00 | 0 | 17.5 | no_trades |
| #240 | Breakout & Momentum Pack · Variant 7 | Breakout Pack | SA701 + SA701-C-1000 | 1m | 0.00% | 0.00 | 0 | 17.5 | no_trades |
| #246 | Mean Reversion Pack · Variant 3 | Mean Reversion Pack | SA701 + SA701-C-1000 | 1m | 0.00% | 0.00 | 0 | 17.5 | no_trades |
| #256 | Carry & Roll Yield Pack · Variant 3 | Carry Pack | SA701 + SA701-C-1000 | 1m | 0.00% | 0.00 | 0 | 17.5 | no_trades |
| #258 | Carry & Roll Yield Pack · Variant 5 | Carry Pack | SA701 + SA701-C-1000 | 1m | 0.00% | 0.00 | 0 | 17.5 | no_trades |
| #259 | Carry & Roll Yield Pack · Variant 6 | Carry Pack | SA701 + SA701-C-1000 | 1m | 0.00% | 0.00 | 0 | 17.5 | no_trades |
| #264 | Relative Value Pack · Variant 1 | Relative Value Pack | SA701 + SA701-C-1000 | 1m | 0.00% | 0.00 | 0 | 17.5 | no_trades |
| #267 | Relative Value Pack · Variant 4 | Relative Value Pack | SA701 + SA701-C-1000 | 1m | 0.00% | 0.00 | 0 | 17.5 | no_trades |
| #269 | Relative Value Pack · Variant 6 | Relative Value Pack | SA701 + SA701-C-1000 | 1m | 0.00% | 0.00 | 0 | 17.5 | no_trades |
| #271 | Relative Value Pack · Variant 8 | Relative Value Pack | SA701 + SA701-C-1000 | 1m | 0.00% | 0.00 | 0 | 17.5 | no_trades |
| #273 | Relative Value Pack · Variant 10 | Relative Value Pack | SA701 + SA701-C-1000 | 1m | 0.00% | 0.00 | 0 | 17.5 | no_trades |
| #274 | Volatility Pack · Variant 1 | Volatility Pack | SA701 + SA701-C-1000 | 1m | 0.00% | 0.00 | 0 | 17.5 | no_trades |
| #282 | Volatility Pack · Variant 9 | Volatility Pack | SA701 + SA701-C-1000 | 1m | 0.00% | 0.00 | 0 | 17.5 | no_trades |
| #297 | Statistical Arbitrage Pack · Variant 4 | Stat Arb Pack | SA701 + SA701-C-1000 | 1m | 0.00% | 0.00 | 0 | 17.5 | no_trades |
| #299 | Statistical Arbitrage Pack · Variant 6 | Stat Arb Pack | SA701 + SA701-C-1000 | 1m | 0.00% | 0.00 | 0 | 17.5 | no_trades |
| #300 | Statistical Arbitrage Pack · Variant 7 | Stat Arb Pack | SA701 + SA701-C-1000 | 1m | 0.00% | 0.00 | 0 | 17.5 | no_trades |
| #301 | Statistical Arbitrage Pack · Variant 8 | Stat Arb Pack | SA701 + SA701-C-1000 | 1m | 0.00% | 0.00 | 0 | 17.5 | no_trades |
| #304 | Options Volatility Pack · Variant 1 | Volatility Pack | SA701 + SA701-C-1000 | 1m | 0.00% | 0.00 | 0 | 17.5 | no_trades |
| #324 | Regime Switch Pack · Variant 1 | Regime Switch Pack | SA701 + SA701-C-1000 | 1m | 0.00% | 0.00 | 0 | 17.5 | no_trades |
| #327 | Regime Switch Pack · Variant 4 | Regime Switch Pack | SA701 + SA701-C-1000 | 1m | 0.00% | 0.00 | 0 | 17.5 | no_trades |
| #332 | Regime Switch Pack · Variant 9 | Regime Switch Pack | SA701 + SA701-C-1000 | 1m | 0.00% | 0.00 | 0 | 17.5 | no_trades |
| #335 | Order Flow Proxy Pack · Variant 2 | Order Flow Pack | SA701 + SA701-C-1000 | 1m | -18.76% | -18.94 | 203 | 17.1 | ok |
| #293 | Market Microstructure Pack · Variant 10 | Microstructure Pack | SA701 + SA701-C-1000 | 1m | -3.74% | -20.45 | 73 | 9.9 | extreme_outlier |
| #262 | Carry & Roll Yield Pack · Variant 9 | Carry Pack | SA701 + SA701-C-1000 | 1m | -6.93% | -24.77 | 87 | 8.7 | extreme_outlier |
| #313 | Options Volatility Pack · Variant 10 | Volatility Pack | SA701 + SA701-C-1000 | 1m | -7.53% | -20.92 | 51 | 8.4 | extreme_outlier |
| #268 | Relative Value Pack · Variant 5 | Relative Value Pack | SA701 + SA701-C-1000 | 1m | -9.01% | -20.96 | 139 | 8.1 | extreme_outlier |
| #286 | Market Microstructure Pack · Variant 3 | Microstructure Pack | SA701 + SA701-C-1000 | 1m | -9.42% | -25.05 | 130 | 7.9 | extreme_outlier |
| #314 | Session Alpha Pack · Variant 1 | Session Alpha Pack | SA701 + SA701-C-1000 | 1m | -10.51% | -23.07 | 188 | 7.5 | extreme_outlier |
| #308 | Options Volatility Pack · Variant 5 | Volatility Pack | SA701 + SA701-C-1000 | 1m | -10.58% | -22.92 | 191 | 7.4 | extreme_outlier |
| #287 | Market Microstructure Pack · Variant 4 | Microstructure Pack | SA701 + SA701-C-1000 | 1m | -11.57% | -52.55 | 201 | 6.9 | extreme_outlier |
| #288 | Market Microstructure Pack · Variant 5 | Microstructure Pack | SA701 + SA701-C-1000 | 1m | -13.00% | -36.12 | 145 | 6.4 | extreme_outlier |
| #266 | Relative Value Pack · Variant 3 | Relative Value Pack | SA701 + SA701-C-1000 | 1m | -14.17% | -41.33 | 192 | 6.0 | extreme_outlier |
| #305 | Options Volatility Pack · Variant 2 | Volatility Pack | SA701 + SA701-C-1000 | 1m | -19.87% | -73.96 | 310 | 3.8 | extreme_outlier |
| #334 | Order Flow Proxy Pack · Variant 1 | Order Flow Pack | SA701 + SA701-C-1000 | 1m | -21.54% | -22.02 | 230 | 3.6 | extreme_outlier |
| #292 | Market Microstructure Pack · Variant 9 | Microstructure Pack | SA701 + SA701-C-1000 | 1m | -23.74% | -65.80 | 397 | 3.3 | extreme_outlier |
| #319 | Session Alpha Pack · Variant 6 | Session Alpha Pack | SA701 + SA701-C-1000 | 1m | -25.55% | -76.27 | 428 | 3.1 | extreme_outlier |
| #318 | Session Alpha Pack · Variant 5 | Session Alpha Pack | SA701 + SA701-C-1000 | 1m | -25.79% | -77.08 | 429 | 3.1 | extreme_outlier |
| #312 | Options Volatility Pack · Variant 9 | Volatility Pack | SA701 + SA701-C-1000 | 1m | -29.34% | -32.03 | 379 | 2.6 | extreme_outlier |
| #310 | Options Volatility Pack · Variant 7 | Volatility Pack | SA701 + SA701-C-1000 | 1m | -43.18% | -110.27 | 722 | 1.3 | extreme_outlier |
