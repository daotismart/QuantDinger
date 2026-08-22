# QuantDinger 回测综合排名与分析报告

- 生成时间：2026-08-20 15:55 UTC
- 数据来源：`qd_backtest_runs`（**132** 条）
- 去重后策略样本：**132**（同名+同周期保留最高分）
- 评分：收益 40% + Sharpe 25% + 回撤 20% + 盈亏比 10% + 有成交 5%；极端异常值×0.25，零成交×0.35
- 指标已统一为小数收益率（自动识别历史百分比口径）
- 过滤条件：tag=`UNIFIED-20260820C2`

---

## 1. 执行摘要

| 项目 | 数值 |
|------|------|
| 回测总数 | 132 |
| 去重策略数 | 132 |
| 有成交（去重） | 98 |
| 零成交（去重） | 34 |
| 策略族 | 13 |
| 综合第 1（去重） | **Single Moving Average**（#356，得分 92.82，收益 50.76%） |
| 有成交且正收益 | 25 / 98 |

### 核心结论

1. **可交易样本榜首**：`Single Moving Average`（得分 92.82，收益 50.76%，回撤 -2.84%，Sharpe 1.85）。
2. **策略族均值最高**：`US Portfolio`（平均得分 73.9，有成交 4/4）。
4. **极端异常值 13 个**已降权，不作为可信 alpha 依据。

## 2. 综合排名（去重 Top 15）

| 排名 | 得分 | 策略 | 族 | Run | 周期 | 总收益 | 最大回撤 | Sharpe | 胜率 | 成交 | 标记 |
|------|------|------|----|-----|------|--------|----------|--------|------|------|------|
| 1 | 92.8 | Single Moving Average | CTA Classic | #356 | 1d | 50.76% | -2.84% | 1.85 | 65.00% | 20 | ok |
| 2 | 89.6 | SuperTrend | CTA Classic | #362 | 1d | 29.49% | -4.38% | 1.35 | 66.67% | 6 | ok |
| 3 | 88.8 | Turtle Trading | CTA Classic | #359 | 1d | 23.77% | -3.73% | 1.13 | 56.25% | 16 | ok |
| 4 | 87.3 | Trend Following Pack · Variant 8 | Trend Pack | #374 | 1m | 8.05% | -1.55% | 9.33 | 35.71% | 14 | ok |
| 5 | 87.3 | Session Alpha Pack · Variant 9 | Session Alpha Pack | #465 | 1m | 8.05% | -1.55% | 9.33 | 35.71% | 14 | ok |
| 6 | 85.2 | Regime Switch Pack · Variant 7 | Regime Switch Pack | #473 | 1m | 6.39% | -2.46% | 7.51 | 60.00% | 5 | ok |
| 7 | 81.2 | Breakout & Momentum Pack · Variant 9 | Breakout Pack | #385 | 1m | 2.00% | -1.51% | 5.97 | 40.00% | 5 | ok |
| 8 | 81.2 | Order Flow Proxy Pack · Variant 4 | Order Flow Pack | #480 | 1m | 6.43% | -2.63% | 7.62 | 10.00% | 20 | ok |
| 9 | 79.9 | Small and Large Cap Barbell | US Portfolio | #363 | 1d | 42.64% | -19.87% | 0.96 | 87.88% | 132 | ok |
| 10 | 77.7 | Options Volatility Pack · Variant 3 | Volatility Pack | #449 | 1m | 0.09% | -4.71% | 6.58 | 100.00% | 1 | ok |
| 11 | 77.7 | Statistical Arbitrage Pack · Variant 2 | Stat Arb Pack | #438 | 1m | 1.22% | -1.54% | 3.77 | 50.00% | 2 | ok |
| 12 | 76.2 | Statistical Arbitrage Pack · Variant 5 | Stat Arb Pack | #441 | 1m | 1.33% | -1.42% | 4.23 | 50.00% | 6 | ok |
| 13 | 76.1 | Quality Growth Multi-Factor | US Portfolio | #366 | 1d | 40.97% | -24.81% | 0.70 | 78.76% | 113 | ok |
| 14 | 75.7 | Regime Switch Pack · Variant 5 | Regime Switch Pack | #471 | 1m | 6.79% | -2.18% | 7.95 | 0.00% | 1 | ok |
| 15 | 75.3 | Statistical Arbitrage Pack · Variant 9 | Stat Arb Pack | #445 | 1m | 3.43% | -3.18% | 4.26 | 30.00% | 30 | ok |

## 3. 有成交策略排名（去重）

| 排名 | 得分 | 策略 | 族 | 总收益 | 回撤 | Sharpe | 盈亏比 | 成交 | Run |
|------|------|------|----|--------|------|--------|--------|------|-----|
| 1 | 92.8 | Single Moving Average | CTA Classic | 50.76% | -2.84% | 1.85 | 9.92 | 20 | #356 |
| 2 | 89.6 | SuperTrend | CTA Classic | 29.49% | -4.38% | 1.35 | 10.53 | 6 | #362 |
| 3 | 88.8 | Turtle Trading | CTA Classic | 23.77% | -3.73% | 1.13 | 5.13 | 16 | #359 |
| 4 | 87.3 | Trend Following Pack · Variant 8 | Trend Pack | 8.05% | -1.55% | 9.33 | 6.82 | 14 | #374 |
| 5 | 87.3 | Session Alpha Pack · Variant 9 | Session Alpha Pack | 8.05% | -1.55% | 9.33 | 6.82 | 14 | #465 |
| 6 | 85.2 | Regime Switch Pack · Variant 7 | Regime Switch Pack | 6.39% | -2.46% | 7.51 | 17.97 | 5 | #473 |
| 7 | 81.2 | Breakout & Momentum Pack · Variant 9 | Breakout Pack | 2.00% | -1.51% | 5.97 | 6.46 | 5 | #385 |
| 8 | 81.2 | Order Flow Proxy Pack · Variant 4 | Order Flow Pack | 6.43% | -2.63% | 7.62 | 3.05 | 20 | #480 |
| 9 | 79.9 | Small and Large Cap Barbell | US Portfolio | 42.64% | -19.87% | 0.96 | 47.35 | 132 | #363 |
| 10 | 77.7 | Options Volatility Pack · Variant 3 | Volatility Pack | 0.09% | -4.71% | 6.58 | 87.63 | 1 | #449 |
| 11 | 77.7 | Statistical Arbitrage Pack · Variant 2 | Stat Arb Pack | 1.22% | -1.54% | 3.77 | 3.60 | 2 | #438 |
| 12 | 76.2 | Statistical Arbitrage Pack · Variant 5 | Stat Arb Pack | 1.33% | -1.42% | 4.23 | 2.78 | 6 | #441 |
| 13 | 76.1 | Quality Growth Multi-Factor | US Portfolio | 40.97% | -24.81% | 0.70 | 21.80 | 113 | #366 |
| 14 | 75.7 | Regime Switch Pack · Variant 5 | Regime Switch Pack | 6.79% | -2.18% | 7.95 | 0.00 | 1 | #471 |
| 15 | 75.3 | Statistical Arbitrage Pack · Variant 9 | Stat Arb Pack | 3.43% | -3.18% | 4.26 | 1.73 | 30 | #445 |
| 16 | 74.4 | Momentum Top-N Rotation | US Portfolio | 45.00% | -17.44% | 0.95 | 1.68 | 164 | #364 |
| 17 | 74.3 | Volatility Pack · Variant 8 | Volatility Pack | 3.90% | -2.17% | 4.77 | 0.75 | 11 | #424 |
| 18 | 73.8 | Trend Following Pack · Variant 2 | Trend Pack | 4.88% | -2.17% | 5.86 | 0.00 | 1 | #368 |
| 19 | 73.8 | Breakout & Momentum Pack · Variant 10 | Breakout Pack | 4.88% | -2.17% | 5.86 | 0.00 | 1 | #386 |
| 20 | 73.8 | Volatility Pack · Variant 5 | Volatility Pack | 4.88% | -2.17% | 5.86 | 0.00 | 1 | #421 |
| 21 | 73.0 | Indicator Resonance | CTA Classic | 14.33% | -7.27% | 0.60 | 2.17 | 33 | #360 |
| 22 | 70.8 | Relative Value Pack · Variant 7 | Relative Value Pack | 2.33% | -3.23% | 3.06 | 0.06 | 17 | #413 |
| 23 | 65.4 | Dual Moving Average | CTA Classic | 23.08% | -29.71% | 0.52 | 1.30 | 66 | #357 |
| 24 | 65.3 | Low Volatility Rotation | US Portfolio | 16.12% | -21.27% | 0.47 | 1.22 | 119 | #365 |
| 25 | 62.4 | Breakout & Momentum Pack · Variant 2 | Breakout Pack | -0.06% | -2.70% | -0.04 | 4.49 | 4 | #378 |
| 26 | 61.5 | Market Microstructure Pack · Variant 6 | Microstructure Pack | 1.48% | -76.54% | 6.34 | 16.41 | 4 | #432 |
| 27 | 61.1 | Market Microstructure Pack · Variant 8 | Microstructure Pack | -0.16% | -2.17% | -0.53 | 10.47 | 3 | #434 |
| 28 | 53.7 | Options Volatility Pack · Variant 8 | Volatility Pack | -0.66% | -2.43% | -1.89 | 395.28 | 1 | #454 |
| 29 | 51.8 | Session Alpha Pack · Variant 2 | Session Alpha Pack | -0.24% | -1.86% | -0.77 | 0.91 | 21 | #458 |
| 30 | 50.3 | Mean Reversion Pack · Variant 6 | Mean Reversion Pack | -0.32% | -1.82% | -0.91 | 0.52 | 3 | #392 |
| 31 | 48.2 | Bullish Candle Through Three Averages | CTA Classic | -2.30% | -7.14% | -0.23 | 0.09 | 2 | #358 |
| 32 | 46.0 | Mean Reversion Pack · Variant 2 | Mean Reversion Pack | -0.54% | -2.96% | -1.40 | 0.00 | 1 | #388 |
| 33 | 46.0 | Mean Reversion Pack · Variant 8 | Mean Reversion Pack | -0.54% | -2.96% | -1.40 | 0.00 | 1 | #394 |
| 34 | 45.3 | Session Alpha Pack · Variant 3 | Session Alpha Pack | -0.57% | -1.31% | -2.79 | 0.74 | 25 | #459 |
| 35 | 45.1 | Carry & Roll Yield Pack · Variant 4 | Carry Pack | -0.51% | -2.00% | -2.51 | 0.82 | 35 | #400 |
| 36 | 44.7 | Options Volatility Pack · Variant 6 | Volatility Pack | -0.75% | -1.24% | -5.23 | 0.53 | 16 | #452 |
| 37 | 44.5 | Mean Reversion Pack · Variant 9 | Mean Reversion Pack | -0.84% | -1.37% | -4.19 | 0.53 | 12 | #395 |
| 38 | 43.9 | Order Flow Proxy Pack · Variant 5 | Order Flow Pack | -0.92% | -2.65% | -5.30 | 0.59 | 17 | #481 |
| 39 | 43.6 | Carry & Roll Yield Pack · Variant 8 | Carry Pack | -1.15% | -1.19% | -14.33 | 0.19 | 14 | #404 |
| 40 | 43.2 | Regime Switch Pack · Variant 3 | Regime Switch Pack | -1.31% | -1.44% | -7.41 | 0.12 | 11 | #469 |
| 41 | 43.1 | Mean Reversion Pack · Variant 7 | Mean Reversion Pack | -1.67% | -1.72% | -9.56 | 0.33 | 27 | #393 |
| 42 | 43.0 | Mean Reversion Pack · Variant 5 | Mean Reversion Pack | -1.59% | -1.89% | -7.29 | 0.26 | 10 | #391 |
| 43 | 43.0 | Relative Value Pack · Variant 2 | Relative Value Pack | -1.59% | -1.89% | -7.29 | 0.26 | 10 | #408 |
| 44 | 43.0 | Statistical Arbitrage Pack · Variant 1 | Stat Arb Pack | -1.59% | -1.89% | -7.29 | 0.26 | 10 | #437 |
| 45 | 42.7 | Order Flow Proxy Pack · Variant 10 | Order Flow Pack | -1.86% | -2.17% | -9.25 | 0.32 | 3 | #486 |
| 46 | 42.5 | Mean Reversion Pack · Variant 10 | Mean Reversion Pack | -1.31% | -2.96% | -3.79 | 0.17 | 2 | #396 |
| 47 | 41.9 | Order Flow Proxy Pack · Variant 7 | Order Flow Pack | -2.03% | -3.02% | -7.23 | 0.22 | 8 | #483 |
| 48 | 41.7 | Volatility Pack · Variant 4 | Volatility Pack | -2.23% | -2.23% | -10.56 | 0.00 | 5 | #420 |
| 49 | 41.7 | Options Volatility Pack · Variant 10 | Volatility Pack | -2.10% | -4.90% | -6.42 | 0.60 | 30 | #456 |
| 50 | 41.0 | Carry & Roll Yield Pack · Variant 9 | Carry Pack | -2.93% | -2.93% | -16.79 | 0.21 | 27 | #405 |
| 51 | 41.0 | Statistical Arbitrage Pack · Variant 3 | Stat Arb Pack | -2.54% | -3.33% | -7.80 | 0.09 | 6 | #439 |
| 52 | 40.7 | Carry & Roll Yield Pack · Variant 7 | Carry Pack | -3.08% | -4.15% | -14.48 | 0.42 | 55 | #403 |
| 53 | 40.3 | Order Flow Proxy Pack · Variant 6 | Order Flow Pack | -3.42% | -3.46% | -16.23 | 0.22 | 37 | #482 |
| 54 | 40.3 | Carry & Roll Yield Pack · Variant 10 | Carry Pack | -3.24% | -4.30% | -17.86 | 0.32 | 48 | #406 |
| 55 | 38.9 | Breakout & Momentum Pack · Variant 6 | Breakout Pack | -4.09% | -5.41% | -18.54 | 0.35 | 56 | #382 |
| 56 | 38.9 | Market Microstructure Pack · Variant 1 | Microstructure Pack | -4.09% | -5.41% | -18.54 | 0.35 | 56 | #427 |
| 57 | 38.6 | Session Alpha Pack · Variant 1 | Session Alpha Pack | -4.58% | -5.08% | -18.79 | 0.37 | 71 | #457 |
| 58 | 38.0 | Session Alpha Pack · Variant 4 | Session Alpha Pack | -3.70% | -7.75% | -4.12 | 0.26 | 7 | #460 |
| 59 | 37.6 | Relative Value Pack · Variant 9 | Relative Value Pack | -4.15% | -7.64% | -4.78 | 0.28 | 9 | #415 |
| 60 | 37.0 | Session Alpha Pack · Variant 7 | Session Alpha Pack | -4.29% | -8.32% | -4.80 | 0.20 | 3 | #463 |
| 61 | 35.4 | Volatility Pack · Variant 10 | Volatility Pack | -0.19% | -18.89% | -16.76 | 0.00 | 2 | #426 |
| 62 | 35.2 | Session Alpha Pack · Variant 8 | Session Alpha Pack | -5.55% | -9.09% | -6.50 | 0.17 | 7 | #464 |
| 63 | 33.7 | Session Alpha Pack · Variant 10 | Session Alpha Pack | -0.08% | -73.86% | -0.60 | 0.91 | 10 | #466 |
| 64 | 33.5 | Regime Switch Pack · Variant 2 | Regime Switch Pack | -7.58% | -7.81% | -9.67 | 0.00 | 2 | #468 |
| 65 | 33.2 | Order Flow Proxy Pack · Variant 9 | Order Flow Pack | -7.44% | -9.85% | -8.66 | 0.28 | 7 | #485 |
| 66 | 31.8 | Carry & Roll Yield Pack · Variant 2 | Carry Pack | -8.77% | -10.04% | -10.51 | 0.28 | 48 | #398 |
| 67 | 30.9 | Regime Switch Pack · Variant 10 | Regime Switch Pack | -9.32% | -9.55% | -11.65 | 0.00 | 3 | #476 |
| 68 | 30.3 | Market Microstructure Pack · Variant 2 | Microstructure Pack | -9.76% | -10.07% | -12.19 | 0.07 | 26 | #428 |
| 69 | 30.1 | Volatility Pack · Variant 6 | Volatility Pack | -9.93% | -10.01% | -12.92 | 0.04 | 37 | #422 |
| 70 | 29.9 | Carry & Roll Yield Pack · Variant 1 | Carry Pack | -10.06% | -10.88% | -12.14 | 0.22 | 50 | #397 |
| 71 | 28.8 | Order Flow Proxy Pack · Variant 1 | Order Flow Pack | -9.95% | -13.04% | -11.91 | 0.15 | 61 | #477 |
| 72 | 28.2 | Regime Switch Pack · Variant 8 | Regime Switch Pack | -10.99% | -11.53% | -13.25 | 0.00 | 4 | #474 |
| 73 | 27.8 | Order Flow Proxy Pack · Variant 3 | Order Flow Pack | -10.75% | -13.44% | -12.94 | 0.13 | 43 | #479 |
| 74 | 27.5 | Market Microstructure Pack · Variant 7 | Microstructure Pack | -11.64% | -12.27% | -14.85 | 0.12 | 56 | #433 |
| 75 | 25.6 | Market Microstructure Pack · Variant 10 | Microstructure Pack | -0.55% | -79.91% | -5.78 | 0.59 | 16 | #436 |
| 76 | 25.5 | Breakout & Momentum Pack · Variant 5 | Breakout Pack | -0.48% | -73.90% | -4.32 | 0.48 | 8 | #381 |
| 77 | 24.8 | Mean Reversion Pack · Variant 4 | Mean Reversion Pack | -0.19% | -41.11% | -2.12 | 0.00 | 2 | #390 |
| 78 | 24.8 | Mean Reversion Pack · Variant 1 | Mean Reversion Pack | -0.36% | -78.88% | -3.30 | 0.06 | 6 | #387 |
| 79 | 24.8 | Statistical Arbitrage Pack · Variant 10 | Stat Arb Pack | -0.36% | -78.88% | -3.30 | 0.06 | 6 | #446 |
| 80 | 24.5 | Volatility Pack · Variant 2 | Volatility Pack | -0.46% | -46.19% | -8.64 | 0.00 | 2 | #418 |
| 81 | 24.5 | Order Flow Proxy Pack · Variant 8 | Order Flow Pack | -13.05% | -15.66% | -15.96 | 0.16 | 70 | #484 |
| 82 | 24.4 | Options Volatility Pack · Variant 4 | Volatility Pack | -0.56% | -55.88% | -11.24 | 0.00 | 6 | #450 |
| 83 | 24.4 | Breakout & Momentum Pack · Variant 4 | Breakout Pack | -0.59% | -69.78% | -5.49 | 0.00 | 6 | #380 |
| 84 | 23.3 | Order Flow Proxy Pack · Variant 2 | Order Flow Pack | -14.42% | -15.11% | -17.93 | 0.14 | 89 | #478 |
| 85 | 10.3 | Market Microstructure Pack · Variant 4 | Microstructure Pack | -2.83% | -2.88% | -26.66 | 0.16 | 62 | #430 |
| 86 | 9.8 | MACD and KDJ Confirmation | CTA Classic | -32.93% | -40.96% | -1.34 | 0.77 | 265 | #361 |
| 87 | 9.6 | Volatility Pack · Variant 3 | Volatility Pack | -4.51% | -5.05% | -24.61 | 0.22 | 44 | #419 |
| 88 | 9.3 | Options Volatility Pack · Variant 5 | Volatility Pack | -5.42% | -5.68% | -22.18 | 0.29 | 80 | #451 |
| 89 | 9.3 | Relative Value Pack · Variant 5 | Relative Value Pack | -5.57% | -5.77% | -24.81 | 0.28 | 78 | #411 |
| 90 | 9.1 | Market Microstructure Pack · Variant 3 | Microstructure Pack | -6.00% | -6.21% | -26.00 | 0.27 | 78 | #429 |
| 91 | 8.7 | Market Microstructure Pack · Variant 5 | Microstructure Pack | -6.41% | -8.89% | -20.13 | 0.25 | 90 | #431 |
| 92 | 8.5 | Relative Value Pack · Variant 3 | Relative Value Pack | -7.65% | -7.65% | -40.54 | 0.14 | 82 | #409 |
| 93 | 8.2 | Options Volatility Pack · Variant 2 | Volatility Pack | -8.21% | -8.21% | -61.62 | 0.06 | 113 | #448 |
| 94 | 7.4 | Session Alpha Pack · Variant 6 | Session Alpha Pack | -10.35% | -10.35% | -60.85 | 0.10 | 159 | #462 |
| 95 | 7.4 | Session Alpha Pack · Variant 5 | Session Alpha Pack | -10.43% | -10.46% | -60.37 | 0.07 | 159 | #461 |
| 96 | 5.2 | Market Microstructure Pack · Variant 9 | Microstructure Pack | -16.28% | -16.35% | -76.30 | 0.13 | 233 | #435 |
| 97 | 4.8 | Options Volatility Pack · Variant 9 | Volatility Pack | -17.26% | -17.47% | -22.09 | 0.11 | 139 | #455 |
| 98 | 3.7 | Options Volatility Pack · Variant 7 | Volatility Pack | -20.35% | -20.35% | -88.53 | 0.05 | 275 | #453 |

## 4. 策略族排行榜

| 排名 | 策略族 | 策略数 | 有成交 | 平均得分 | 平均收益* | 总成交 | 族内最佳 |
|------|--------|--------|--------|----------|-----------|--------|----------|
| 1 | US Portfolio | 4 | 4 | 73.9 | 36.18% | 528 | Small and Large Cap Barbell (#363) |
| 2 | CTA Classic | 8 | 7 | 60.6 | 15.17% | 408 | Single Moving Average (#356) |
| 3 | Stat Arb Pack | 10 | 6 | 40.8 | 0.25% | 60 | Statistical Arbitrage Pack · Variant 2 (#438) |
| 4 | Order Flow Pack | 10 | 10 | 38.8 | -5.74% | 355 | Order Flow Proxy Pack · Variant 4 (#480) |
| 5 | Mean Reversion Pack | 10 | 9 | 38.3 | -0.82% | 64 | Mean Reversion Pack · Variant 6 (#392) |
| 6 | Session Alpha Pack | 10 | 10 | 38.2 | -3.17% | 476 | Session Alpha Pack · Variant 9 (#465) |
| 7 | Breakout Pack | 10 | 6 | 37.6 | 0.28% | 80 | Breakout & Momentum Pack · Variant 9 (#385) |
| 8 | Regime Switch Pack | 10 | 6 | 37.4 | -2.67% | 26 | Regime Switch Pack · Variant 7 (#473) |
| 9 | Carry Pack | 10 | 7 | 32.5 | -4.25% | 277 | Carry & Roll Yield Pack · Variant 4 (#400) |
| 10 | Volatility Pack | 20 | 16 | 31.7 | -3.99% | 763 | Options Volatility Pack · Variant 3 (#449) |
| 11 | Trend Pack | 10 | 2 | 30.8 | 6.47% | 15 | Trend Following Pack · Variant 8 (#374) |
| 12 | Microstructure Pack | 10 | 10 | 27.8 | -5.62% | 624 | Market Microstructure Pack · Variant 6 (#432) |
| 13 | Relative Value Pack | 10 | 5 | 25.7 | -3.33% | 196 | Relative Value Pack · Variant 7 (#413) |

\*平均收益仅统计有成交样本。

## 5. 方法说明与限制

- 跨族不可直接比绝对收益：标的、周期、资金、费率可能不同。
- 同策略重复回测时，总榜以去重结果为主；附录保留全量。
- Pack 依赖国内期货分钟线与期权合约键；连续合约 `SA0` 与月份码 `SA701` 不是同一符号。

## 附录 A：全量回测清单（按得分）

| Run | 策略 | 族 | 标的 | 周期 | 收益 | Sharpe | 成交 | 得分 | 标记 |
|-----|------|----|------|------|------|--------|------|------|------|
| #356 | Single Moving Average | CTA Classic | USStock:SPY | 1d | 50.76% | 1.85 | 20 | 92.8 | ok |
| #362 | SuperTrend | CTA Classic | USStock:SPY | 1d | 29.49% | 1.35 | 6 | 89.6 | ok |
| #359 | Turtle Trading | CTA Classic | USStock:SPY | 1d | 23.77% | 1.13 | 16 | 88.8 | ok |
| #374 | Trend Following Pack · Variant 8 | Trend Pack | SA701 + SA701-C-1000 | 1m | 8.05% | 9.33 | 14 | 87.3 | ok |
| #465 | Session Alpha Pack · Variant 9 | Session Alpha Pack | SA701 + SA701-C-1000 | 1m | 8.05% | 9.33 | 14 | 87.3 | ok |
| #473 | Regime Switch Pack · Variant 7 | Regime Switch Pack | SA701 + SA701-C-1000 | 1m | 6.39% | 7.51 | 5 | 85.2 | ok |
| #385 | Breakout & Momentum Pack · Variant 9 | Breakout Pack | SA701 + SA701-C-1000 | 1m | 2.00% | 5.97 | 5 | 81.2 | ok |
| #480 | Order Flow Proxy Pack · Variant 4 | Order Flow Pack | SA701 + SA701-C-1000 | 1m | 6.43% | 7.62 | 20 | 81.2 | ok |
| #363 | Small and Large Cap Barbell | US Portfolio | AAPL + MSFT + NVDA + AMZN + META + GOOG… | 1d | 42.64% | 0.96 | 132 | 79.9 | ok |
| #449 | Options Volatility Pack · Variant 3 | Volatility Pack | SA701 + SA701-C-1000 | 1m | 0.09% | 6.58 | 1 | 77.7 | ok |
| #438 | Statistical Arbitrage Pack · Variant 2 | Stat Arb Pack | SA701 + SA701-C-1000 | 1m | 1.22% | 3.77 | 2 | 77.7 | ok |
| #441 | Statistical Arbitrage Pack · Variant 5 | Stat Arb Pack | SA701 + SA701-C-1000 | 1m | 1.33% | 4.23 | 6 | 76.2 | ok |
| #366 | Quality Growth Multi-Factor | US Portfolio | AAPL + MSFT + NVDA + AMZN + META + GOOG… | 1d | 40.97% | 0.70 | 113 | 76.1 | ok |
| #471 | Regime Switch Pack · Variant 5 | Regime Switch Pack | SA701 + SA701-C-1000 | 1m | 6.79% | 7.95 | 1 | 75.7 | ok |
| #445 | Statistical Arbitrage Pack · Variant 9 | Stat Arb Pack | SA701 + SA701-C-1000 | 1m | 3.43% | 4.26 | 30 | 75.3 | ok |
| #364 | Momentum Top-N Rotation | US Portfolio | AAPL + MSFT + NVDA + AMZN + META + GOOG… | 1d | 45.00% | 0.95 | 164 | 74.4 | ok |
| #424 | Volatility Pack · Variant 8 | Volatility Pack | SA701 + SA701-C-1000 | 1m | 3.90% | 4.77 | 11 | 74.3 | ok |
| #368 | Trend Following Pack · Variant 2 | Trend Pack | SA701 + SA701-C-1000 | 1m | 4.88% | 5.86 | 1 | 73.8 | ok |
| #386 | Breakout & Momentum Pack · Variant 10 | Breakout Pack | SA701 + SA701-C-1000 | 1m | 4.88% | 5.86 | 1 | 73.8 | ok |
| #421 | Volatility Pack · Variant 5 | Volatility Pack | SA701 + SA701-C-1000 | 1m | 4.88% | 5.86 | 1 | 73.8 | ok |
| #360 | Indicator Resonance | CTA Classic | USStock:QQQ | 1d | 14.33% | 0.60 | 33 | 73.0 | ok |
| #413 | Relative Value Pack · Variant 7 | Relative Value Pack | SA701 + SA701-C-1000 | 1m | 2.33% | 3.06 | 17 | 70.8 | ok |
| #357 | Dual Moving Average | CTA Classic | Crypto:BTC/USDT | 4h | 23.08% | 0.52 | 66 | 65.4 | ok |
| #365 | Low Volatility Rotation | US Portfolio | AAPL + MSFT + NVDA + AMZN + META + GOOG… | 1d | 16.12% | 0.47 | 119 | 65.3 | ok |
| #378 | Breakout & Momentum Pack · Variant 2 | Breakout Pack | SA701 + SA701-C-1000 | 1m | -0.06% | -0.04 | 4 | 62.4 | ok |
| #432 | Market Microstructure Pack · Variant 6 | Microstructure Pack | SA701 + SA701-C-1000 | 1m | 1.48% | 6.34 | 4 | 61.5 | ok |
| #434 | Market Microstructure Pack · Variant 8 | Microstructure Pack | SA701 + SA701-C-1000 | 1m | -0.16% | -0.53 | 3 | 61.1 | ok |
| #454 | Options Volatility Pack · Variant 8 | Volatility Pack | SA701 + SA701-C-1000 | 1m | -0.66% | -1.89 | 1 | 53.7 | ok |
| #458 | Session Alpha Pack · Variant 2 | Session Alpha Pack | SA701 + SA701-C-1000 | 1m | -0.24% | -0.77 | 21 | 51.8 | ok |
| #392 | Mean Reversion Pack · Variant 6 | Mean Reversion Pack | SA701 + SA701-C-1000 | 1m | -0.32% | -0.91 | 3 | 50.3 | ok |
| #358 | Bullish Candle Through Three Averages | CTA Classic | CNStock:600519.SH | 1d | -2.30% | -0.23 | 2 | 48.2 | ok |
| #388 | Mean Reversion Pack · Variant 2 | Mean Reversion Pack | SA701 + SA701-C-1000 | 1m | -0.54% | -1.40 | 1 | 46.0 | ok |
| #394 | Mean Reversion Pack · Variant 8 | Mean Reversion Pack | SA701 + SA701-C-1000 | 1m | -0.54% | -1.40 | 1 | 46.0 | ok |
| #459 | Session Alpha Pack · Variant 3 | Session Alpha Pack | SA701 + SA701-C-1000 | 1m | -0.57% | -2.79 | 25 | 45.3 | ok |
| #400 | Carry & Roll Yield Pack · Variant 4 | Carry Pack | SA701 + SA701-C-1000 | 1m | -0.51% | -2.51 | 35 | 45.1 | ok |
| #452 | Options Volatility Pack · Variant 6 | Volatility Pack | SA701 + SA701-C-1000 | 1m | -0.75% | -5.23 | 16 | 44.7 | ok |
| #395 | Mean Reversion Pack · Variant 9 | Mean Reversion Pack | SA701 + SA701-C-1000 | 1m | -0.84% | -4.19 | 12 | 44.5 | ok |
| #481 | Order Flow Proxy Pack · Variant 5 | Order Flow Pack | SA701 + SA701-C-1000 | 1m | -0.92% | -5.30 | 17 | 43.9 | ok |
| #404 | Carry & Roll Yield Pack · Variant 8 | Carry Pack | SA701 + SA701-C-1000 | 1m | -1.15% | -14.33 | 14 | 43.6 | ok |
| #469 | Regime Switch Pack · Variant 3 | Regime Switch Pack | SA701 + SA701-C-1000 | 1m | -1.31% | -7.41 | 11 | 43.2 | ok |
| #393 | Mean Reversion Pack · Variant 7 | Mean Reversion Pack | SA701 + SA701-C-1000 | 1m | -1.67% | -9.56 | 27 | 43.1 | ok |
| #391 | Mean Reversion Pack · Variant 5 | Mean Reversion Pack | SA701 + SA701-C-1000 | 1m | -1.59% | -7.29 | 10 | 43.0 | ok |
| #408 | Relative Value Pack · Variant 2 | Relative Value Pack | SA701 + SA701-C-1000 | 1m | -1.59% | -7.29 | 10 | 43.0 | ok |
| #437 | Statistical Arbitrage Pack · Variant 1 | Stat Arb Pack | SA701 + SA701-C-1000 | 1m | -1.59% | -7.29 | 10 | 43.0 | ok |
| #486 | Order Flow Proxy Pack · Variant 10 | Order Flow Pack | SA701 + SA701-C-1000 | 1m | -1.86% | -9.25 | 3 | 42.7 | ok |
| #396 | Mean Reversion Pack · Variant 10 | Mean Reversion Pack | SA701 + SA701-C-1000 | 1m | -1.31% | -3.79 | 2 | 42.5 | ok |
| #483 | Order Flow Proxy Pack · Variant 7 | Order Flow Pack | SA701 + SA701-C-1000 | 1m | -2.03% | -7.23 | 8 | 41.9 | ok |
| #420 | Volatility Pack · Variant 4 | Volatility Pack | SA701 + SA701-C-1000 | 1m | -2.23% | -10.56 | 5 | 41.7 | ok |
| #456 | Options Volatility Pack · Variant 10 | Volatility Pack | SA701 + SA701-C-1000 | 1m | -2.10% | -6.42 | 30 | 41.7 | ok |
| #405 | Carry & Roll Yield Pack · Variant 9 | Carry Pack | SA701 + SA701-C-1000 | 1m | -2.93% | -16.79 | 27 | 41.0 | ok |
| #439 | Statistical Arbitrage Pack · Variant 3 | Stat Arb Pack | SA701 + SA701-C-1000 | 1m | -2.54% | -7.80 | 6 | 41.0 | ok |
| #403 | Carry & Roll Yield Pack · Variant 7 | Carry Pack | SA701 + SA701-C-1000 | 1m | -3.08% | -14.48 | 55 | 40.7 | ok |
| #482 | Order Flow Proxy Pack · Variant 6 | Order Flow Pack | SA701 + SA701-C-1000 | 1m | -3.42% | -16.23 | 37 | 40.3 | ok |
| #406 | Carry & Roll Yield Pack · Variant 10 | Carry Pack | SA701 + SA701-C-1000 | 1m | -3.24% | -17.86 | 48 | 40.3 | ok |
| #382 | Breakout & Momentum Pack · Variant 6 | Breakout Pack | SA701 + SA701-C-1000 | 1m | -4.09% | -18.54 | 56 | 38.9 | ok |
| #427 | Market Microstructure Pack · Variant 1 | Microstructure Pack | SA701 + SA701-C-1000 | 1m | -4.09% | -18.54 | 56 | 38.9 | ok |
| #457 | Session Alpha Pack · Variant 1 | Session Alpha Pack | SA701 + SA701-C-1000 | 1m | -4.58% | -18.79 | 71 | 38.6 | ok |
| #460 | Session Alpha Pack · Variant 4 | Session Alpha Pack | SA701 + SA701-C-1000 | 1m | -3.70% | -4.12 | 7 | 38.0 | ok |
| #415 | Relative Value Pack · Variant 9 | Relative Value Pack | SA701 + SA701-C-1000 | 1m | -4.15% | -4.78 | 9 | 37.6 | ok |
| #463 | Session Alpha Pack · Variant 7 | Session Alpha Pack | SA701 + SA701-C-1000 | 1m | -4.29% | -4.80 | 3 | 37.0 | ok |
| #426 | Volatility Pack · Variant 10 | Volatility Pack | SA701 + SA701-C-1000 | 1m | -0.19% | -16.76 | 2 | 35.4 | ok |
| #464 | Session Alpha Pack · Variant 8 | Session Alpha Pack | SA701 + SA701-C-1000 | 1m | -5.55% | -6.50 | 7 | 35.2 | ok |
| #466 | Session Alpha Pack · Variant 10 | Session Alpha Pack | SA701 + SA701-C-1000 | 1m | -0.08% | -0.60 | 10 | 33.7 | ok |
| #468 | Regime Switch Pack · Variant 2 | Regime Switch Pack | SA701 + SA701-C-1000 | 1m | -7.58% | -9.67 | 2 | 33.5 | ok |
| #485 | Order Flow Proxy Pack · Variant 9 | Order Flow Pack | SA701 + SA701-C-1000 | 1m | -7.44% | -8.66 | 7 | 33.2 | ok |
| #398 | Carry & Roll Yield Pack · Variant 2 | Carry Pack | SA701 + SA701-C-1000 | 1m | -8.77% | -10.51 | 48 | 31.8 | ok |
| #476 | Regime Switch Pack · Variant 10 | Regime Switch Pack | SA701 + SA701-C-1000 | 1m | -9.32% | -11.65 | 3 | 30.9 | ok |
| #428 | Market Microstructure Pack · Variant 2 | Microstructure Pack | SA701 + SA701-C-1000 | 1m | -9.76% | -12.19 | 26 | 30.3 | ok |
| #422 | Volatility Pack · Variant 6 | Volatility Pack | SA701 + SA701-C-1000 | 1m | -9.93% | -12.92 | 37 | 30.1 | ok |
| #397 | Carry & Roll Yield Pack · Variant 1 | Carry Pack | SA701 + SA701-C-1000 | 1m | -10.06% | -12.14 | 50 | 29.9 | ok |
| #477 | Order Flow Proxy Pack · Variant 1 | Order Flow Pack | SA701 + SA701-C-1000 | 1m | -9.95% | -11.91 | 61 | 28.8 | ok |
| #474 | Regime Switch Pack · Variant 8 | Regime Switch Pack | SA701 + SA701-C-1000 | 1m | -10.99% | -13.25 | 4 | 28.2 | ok |
| #479 | Order Flow Proxy Pack · Variant 3 | Order Flow Pack | SA701 + SA701-C-1000 | 1m | -10.75% | -12.94 | 43 | 27.8 | ok |
| #433 | Market Microstructure Pack · Variant 7 | Microstructure Pack | SA701 + SA701-C-1000 | 1m | -11.64% | -14.85 | 56 | 27.5 | ok |
| #436 | Market Microstructure Pack · Variant 10 | Microstructure Pack | SA701 + SA701-C-1000 | 1m | -0.55% | -5.78 | 16 | 25.6 | ok |
| #381 | Breakout & Momentum Pack · Variant 5 | Breakout Pack | SA701 + SA701-C-1000 | 1m | -0.48% | -4.32 | 8 | 25.5 | ok |
| #390 | Mean Reversion Pack · Variant 4 | Mean Reversion Pack | SA701 + SA701-C-1000 | 1m | -0.19% | -2.12 | 2 | 24.8 | ok |
| #367 | Trend Following Pack · Variant 1 | Trend Pack | SA701 + SA701-C-1000 | 1m | 6.88% | 8.06 | 0 | 24.8 | no_trades |
| #423 | Volatility Pack · Variant 7 | Volatility Pack | SA701 + SA701-C-1000 | 1m | 6.88% | 8.06 | 0 | 24.8 | no_trades |
| #472 | Regime Switch Pack · Variant 6 | Regime Switch Pack | SA701 + SA701-C-1000 | 1m | 6.88% | 8.06 | 0 | 24.8 | no_trades |
| #387 | Mean Reversion Pack · Variant 1 | Mean Reversion Pack | SA701 + SA701-C-1000 | 1m | -0.36% | -3.30 | 6 | 24.8 | ok |
| #446 | Statistical Arbitrage Pack · Variant 10 | Stat Arb Pack | SA701 + SA701-C-1000 | 1m | -0.36% | -3.30 | 6 | 24.8 | ok |
| #418 | Volatility Pack · Variant 2 | Volatility Pack | SA701 + SA701-C-1000 | 1m | -0.46% | -8.64 | 2 | 24.5 | ok |
| #484 | Order Flow Proxy Pack · Variant 8 | Order Flow Pack | SA701 + SA701-C-1000 | 1m | -13.05% | -15.96 | 70 | 24.5 | ok |
| #450 | Options Volatility Pack · Variant 4 | Volatility Pack | SA701 + SA701-C-1000 | 1m | -0.56% | -11.24 | 6 | 24.4 | ok |
| #380 | Breakout & Momentum Pack · Variant 4 | Breakout Pack | SA701 + SA701-C-1000 | 1m | -0.59% | -5.49 | 6 | 24.4 | ok |
| #478 | Order Flow Proxy Pack · Variant 2 | Order Flow Pack | SA701 + SA701-C-1000 | 1m | -14.42% | -17.93 | 89 | 23.3 | ok |
| #369 | Trend Following Pack · Variant 3 | Trend Pack | SA701 + SA701-C-1000 | 1m | 0.00% | 0.00 | 0 | 17.5 | no_trades |
| #370 | Trend Following Pack · Variant 4 | Trend Pack | SA701 + SA701-C-1000 | 1m | 0.00% | 0.00 | 0 | 17.5 | no_trades |
| #371 | Trend Following Pack · Variant 5 | Trend Pack | SA701 + SA701-C-1000 | 1m | 0.00% | 0.00 | 0 | 17.5 | no_trades |
| #372 | Trend Following Pack · Variant 6 | Trend Pack | SA701 + SA701-C-1000 | 1m | 0.00% | 0.00 | 0 | 17.5 | no_trades |
| #373 | Trend Following Pack · Variant 7 | Trend Pack | SA701 + SA701-C-1000 | 1m | 0.00% | 0.00 | 0 | 17.5 | no_trades |
| #375 | Trend Following Pack · Variant 9 | Trend Pack | SA701 + SA701-C-1000 | 1m | 0.00% | 0.00 | 0 | 17.5 | no_trades |
| #376 | Trend Following Pack · Variant 10 | Trend Pack | SA701 + SA701-C-1000 | 1m | 0.00% | 0.00 | 0 | 17.5 | no_trades |
| #377 | Breakout & Momentum Pack · Variant 1 | Breakout Pack | SA701 + SA701-C-1000 | 1m | 0.00% | 0.00 | 0 | 17.5 | no_trades |
| #379 | Breakout & Momentum Pack · Variant 3 | Breakout Pack | SA701 + SA701-C-1000 | 1m | 0.00% | 0.00 | 0 | 17.5 | no_trades |
| #383 | Breakout & Momentum Pack · Variant 7 | Breakout Pack | SA701 + SA701-C-1000 | 1m | 0.00% | 0.00 | 0 | 17.5 | no_trades |
| #384 | Breakout & Momentum Pack · Variant 8 | Breakout Pack | SA701 + SA701-C-1000 | 1m | 0.00% | 0.00 | 0 | 17.5 | no_trades |
| #389 | Mean Reversion Pack · Variant 3 | Mean Reversion Pack | SA701 + SA701-C-1000 | 1m | 0.00% | 0.00 | 0 | 17.5 | no_trades |
| #399 | Carry & Roll Yield Pack · Variant 3 | Carry Pack | SA701 + SA701-C-1000 | 1m | 0.00% | 0.00 | 0 | 17.5 | no_trades |
| #401 | Carry & Roll Yield Pack · Variant 5 | Carry Pack | SA701 + SA701-C-1000 | 1m | 0.00% | 0.00 | 0 | 17.5 | no_trades |
| #402 | Carry & Roll Yield Pack · Variant 6 | Carry Pack | SA701 + SA701-C-1000 | 1m | 0.00% | 0.00 | 0 | 17.5 | no_trades |
| #407 | Relative Value Pack · Variant 1 | Relative Value Pack | SA701 + SA701-C-1000 | 1m | 0.00% | 0.00 | 0 | 17.5 | no_trades |
| #410 | Relative Value Pack · Variant 4 | Relative Value Pack | SA701 + SA701-C-1000 | 1m | 0.00% | 0.00 | 0 | 17.5 | no_trades |
| #412 | Relative Value Pack · Variant 6 | Relative Value Pack | SA701 + SA701-C-1000 | 1m | 0.00% | 0.00 | 0 | 17.5 | no_trades |
| #414 | Relative Value Pack · Variant 8 | Relative Value Pack | SA701 + SA701-C-1000 | 1m | 0.00% | 0.00 | 0 | 17.5 | no_trades |
| #416 | Relative Value Pack · Variant 10 | Relative Value Pack | SA701 + SA701-C-1000 | 1m | 0.00% | 0.00 | 0 | 17.5 | no_trades |
| #417 | Volatility Pack · Variant 1 | Volatility Pack | SA701 + SA701-C-1000 | 1m | 0.00% | 0.00 | 0 | 17.5 | no_trades |
| #425 | Volatility Pack · Variant 9 | Volatility Pack | SA701 + SA701-C-1000 | 1m | 0.00% | 0.00 | 0 | 17.5 | no_trades |
| #440 | Statistical Arbitrage Pack · Variant 4 | Stat Arb Pack | SA701 + SA701-C-1000 | 1m | 0.00% | 0.00 | 0 | 17.5 | no_trades |
| #442 | Statistical Arbitrage Pack · Variant 6 | Stat Arb Pack | SA701 + SA701-C-1000 | 1m | 0.00% | 0.00 | 0 | 17.5 | no_trades |
| #443 | Statistical Arbitrage Pack · Variant 7 | Stat Arb Pack | SA701 + SA701-C-1000 | 1m | 0.00% | 0.00 | 0 | 17.5 | no_trades |
| #444 | Statistical Arbitrage Pack · Variant 8 | Stat Arb Pack | SA701 + SA701-C-1000 | 1m | 0.00% | 0.00 | 0 | 17.5 | no_trades |
| #447 | Options Volatility Pack · Variant 1 | Volatility Pack | SA701 + SA701-C-1000 | 1m | 0.00% | 0.00 | 0 | 17.5 | no_trades |
| #467 | Regime Switch Pack · Variant 1 | Regime Switch Pack | SA701 + SA701-C-1000 | 1m | 0.00% | 0.00 | 0 | 17.5 | no_trades |
| #470 | Regime Switch Pack · Variant 4 | Regime Switch Pack | SA701 + SA701-C-1000 | 1m | 0.00% | 0.00 | 0 | 17.5 | no_trades |
| #475 | Regime Switch Pack · Variant 9 | Regime Switch Pack | SA701 + SA701-C-1000 | 1m | 0.00% | 0.00 | 0 | 17.5 | no_trades |
| #487 | Bullish Three Averages With Trend Filter | CTA Classic | CNStock:600519.SH | 1d | 0.00% | 0.00 | 0 | 17.5 | no_trades |
| #430 | Market Microstructure Pack · Variant 4 | Microstructure Pack | SA701 + SA701-C-1000 | 1m | -2.83% | -26.66 | 62 | 10.3 | extreme_outlier |
| #361 | MACD and KDJ Confirmation | CTA Classic | Crypto:BTC/USDT | 4h | -32.93% | -1.34 | 265 | 9.8 | ok |
| #419 | Volatility Pack · Variant 3 | Volatility Pack | SA701 + SA701-C-1000 | 1m | -4.51% | -24.61 | 44 | 9.6 | extreme_outlier |
| #451 | Options Volatility Pack · Variant 5 | Volatility Pack | SA701 + SA701-C-1000 | 1m | -5.42% | -22.18 | 80 | 9.3 | extreme_outlier |
| #411 | Relative Value Pack · Variant 5 | Relative Value Pack | SA701 + SA701-C-1000 | 1m | -5.57% | -24.81 | 78 | 9.3 | extreme_outlier |
| #429 | Market Microstructure Pack · Variant 3 | Microstructure Pack | SA701 + SA701-C-1000 | 1m | -6.00% | -26.00 | 78 | 9.1 | extreme_outlier |
| #431 | Market Microstructure Pack · Variant 5 | Microstructure Pack | SA701 + SA701-C-1000 | 1m | -6.41% | -20.13 | 90 | 8.7 | extreme_outlier |
| #409 | Relative Value Pack · Variant 3 | Relative Value Pack | SA701 + SA701-C-1000 | 1m | -7.65% | -40.54 | 82 | 8.5 | extreme_outlier |
| #448 | Options Volatility Pack · Variant 2 | Volatility Pack | SA701 + SA701-C-1000 | 1m | -8.21% | -61.62 | 113 | 8.2 | extreme_outlier |
| #462 | Session Alpha Pack · Variant 6 | Session Alpha Pack | SA701 + SA701-C-1000 | 1m | -10.35% | -60.85 | 159 | 7.4 | extreme_outlier |
| #461 | Session Alpha Pack · Variant 5 | Session Alpha Pack | SA701 + SA701-C-1000 | 1m | -10.43% | -60.37 | 159 | 7.4 | extreme_outlier |
| #435 | Market Microstructure Pack · Variant 9 | Microstructure Pack | SA701 + SA701-C-1000 | 1m | -16.28% | -76.30 | 233 | 5.2 | extreme_outlier |
| #455 | Options Volatility Pack · Variant 9 | Volatility Pack | SA701 + SA701-C-1000 | 1m | -17.26% | -22.09 | 139 | 4.8 | extreme_outlier |
| #453 | Options Volatility Pack · Variant 7 | Volatility Pack | SA701 + SA701-C-1000 | 1m | -20.35% | -88.53 | 275 | 3.7 | extreme_outlier |
