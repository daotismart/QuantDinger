# QuantDinger 回测综合排名与分析报告

- 生成时间：2026-08-20 15:03 UTC
- 数据来源：`qd_backtest_runs`（**343** 条）
- 去重后策略样本：**136**（同名+同周期保留最高分）
- 评分：收益 40% + Sharpe 25% + 回撤 20% + 盈亏比 10% + 有成交 5%；极端异常值×0.25，零成交×0.35
- 指标已统一为小数收益率（自动识别历史百分比口径）
- 过滤条件：全部成功回测

---

## 1. 执行摘要

| 项目 | 数值 |
|------|------|
| 回测总数 | 343 |
| 去重策略数 | 136 |
| 有成交（去重） | 85 |
| 零成交（去重） | 51 |
| 策略族 | 15 |
| 综合第 1（去重） | **[DEBUG] SA701 force long**（#214，得分 83.07，收益 3.65%） |
| 有成交且正收益 | 26 / 85 |

### 核心结论

1. **可交易样本榜首**：`[DEBUG] SA701 force long`（得分 83.07，收益 3.65%，回撤 -1.15%，Sharpe 9.93）。
2. **策略族均值最高**：`Other`（平均得分 83.1，有成交 1/1）。
4. **极端异常值 1 个**已降权，不作为可信 alpha 依据。

## 2. 综合排名（去重 Top 15）

| 排名 | 得分 | 策略 | 族 | Run | 周期 | 总收益 | 最大回撤 | Sharpe | 胜率 | 成交 | 标记 |
|------|------|------|----|-----|------|--------|----------|--------|------|------|------|
| 1 | 83.1 | [DEBUG] SA701 force long | Other | #214 | 1m | 3.65% | -1.15% | 9.93 | 100.00% | 2 | ok |
| 2 | 82.8 | Dual Moving Average | CTA Classic | #5 | 4h | 12.38% | -7.35% | 1.81 | 50.00% | 6 | ok |
| 3 | 82.0 | Mean Reversion Pack · Variant 8 | Mean Reversion Pack | #251 | 1m | 2.84% | -1.64% | 7.41 | 37.50% | 16 | ok |
| 4 | 81.3 | Quality Growth Multi-Factor | US Portfolio | #28 | 1d | 7.49% | -7.44% | 2.51 | 73.68% | 19 | ok |
| 5 | 81.1 | Mean Reversion Pack · Variant 6 | Mean Reversion Pack | #249 | 1m | 1.84% | -1.54% | 6.02 | 42.86% | 21 | ok |
| 6 | 80.8 | Small and Large Cap Barbell | US Portfolio | #84 | 1d | 7.33% | -7.44% | 2.44 | 76.47% | 17 | ok |
| 7 | 77.7 | Options Volatility Pack · Variant 3 | Volatility Pack | #306 | 1m | 0.09% | -4.71% | 5.40 | 100.00% | 1 | ok |
| 8 | 76.8 | Mean Reversion Pack · Variant 2 | Mean Reversion Pack | #245 | 1m | 2.18% | -2.11% | 5.67 | 24.14% | 29 | ok |
| 9 | 72.5 | Order Flow Proxy Pack · Variant 5 | Order Flow Pack | #338 | 1m | 0.99% | -2.56% | 3.48 | 17.39% | 23 | ok |
| 10 | 69.9 | Low Volatility Rotation | US Portfolio | #11 | 1d | 6.61% | -4.75% | 1.92 | 82.35% | 17 | ok |
| 11 | 69.4 | Mean Reversion Pack · Variant 10 | Mean Reversion Pack | #253 | 1m | 0.87% | -1.77% | 2.14 | 30.00% | 20 | ok |
| 12 | 65.9 | Statistical Arbitrage Pack · Variant 3 | Stat Arb Pack | #296 | 1m | 0.45% | -1.55% | 1.65 | 57.14% | 7 | ok |
| 13 | 65.7 | Volatility Pack · Variant 5 | Volatility Pack | #278 | 1m | 1.44% | -5.00% | 1.58 | 22.73% | 22 | ok |
| 14 | 63.8 | Volatility Pack · Variant 8 | Volatility Pack | #281 | 1m | 1.28% | -4.92% | 1.44 | 20.51% | 39 | ok |
| 15 | 63.4 | Regime Switch Pack · Variant 5 | Regime Switch Pack | #328 | 1m | 1.09% | -4.89% | 1.29 | 66.67% | 3 | ok |

## 3. 有成交策略排名（去重）

| 排名 | 得分 | 策略 | 族 | 总收益 | 回撤 | Sharpe | 盈亏比 | 成交 | Run |
|------|------|------|----|--------|------|--------|--------|------|-----|
| 1 | 83.1 | [DEBUG] SA701 force long | Other | 3.65% | -1.15% | 9.93 | 170.00 | 2 | #214 |
| 2 | 82.8 | Dual Moving Average | CTA Classic | 12.38% | -7.35% | 1.81 | 5.08 | 6 | #5 |
| 3 | 82.0 | Mean Reversion Pack · Variant 8 | Mean Reversion Pack | 2.84% | -1.64% | 7.41 | 7.08 | 16 | #251 |
| 4 | 81.3 | Quality Growth Multi-Factor | US Portfolio | 7.49% | -7.44% | 2.51 | 16.03 | 19 | #28 |
| 5 | 81.1 | Mean Reversion Pack · Variant 6 | Mean Reversion Pack | 1.84% | -1.54% | 6.02 | 10.52 | 21 | #249 |
| 6 | 80.8 | Small and Large Cap Barbell | US Portfolio | 7.33% | -7.44% | 2.44 | 18.09 | 17 | #84 |
| 7 | 77.7 | Options Volatility Pack · Variant 3 | Volatility Pack | 0.09% | -4.71% | 5.40 | 87.63 | 1 | #306 |
| 8 | 76.8 | Mean Reversion Pack · Variant 2 | Mean Reversion Pack | 2.18% | -2.11% | 5.67 | 2.81 | 29 | #245 |
| 9 | 72.5 | Order Flow Proxy Pack · Variant 5 | Order Flow Pack | 0.99% | -2.56% | 3.48 | 1.42 | 23 | #338 |
| 10 | 69.9 | Low Volatility Rotation | US Portfolio | 6.61% | -4.75% | 1.92 | 0.55 | 17 | #11 |
| 11 | 69.4 | Mean Reversion Pack · Variant 10 | Mean Reversion Pack | 0.87% | -1.77% | 2.14 | 1.85 | 20 | #253 |
| 12 | 65.9 | Statistical Arbitrage Pack · Variant 3 | Stat Arb Pack | 0.45% | -1.55% | 1.65 | 1.48 | 7 | #296 |
| 13 | 65.7 | Volatility Pack · Variant 5 | Volatility Pack | 1.44% | -5.00% | 1.58 | 1.94 | 22 | #278 |
| 14 | 63.8 | Volatility Pack · Variant 8 | Volatility Pack | 1.28% | -4.92% | 1.44 | 1.39 | 39 | #281 |
| 15 | 63.4 | Regime Switch Pack · Variant 5 | Regime Switch Pack | 1.09% | -4.89% | 1.29 | 1.65 | 3 | #328 |
| 16 | 62.0 | Trend Following Pack · Variant 8 | Trend Pack | 1.06% | -5.56% | 1.23 | 1.26 | 30 | #231 |
| 17 | 61.8 | Session Alpha Pack · Variant 9 | Session Alpha Pack | 1.06% | -5.65% | 1.22 | 1.23 | 35 | #322 |
| 18 | 61.1 | Order Flow Proxy Pack · Variant 4 | Order Flow Pack | 0.83% | -4.40% | 1.02 | 1.17 | 46 | #337 |
| 19 | 58.3 | Regime Switch Pack · Variant 7 | Regime Switch Pack | 0.45% | -5.41% | 0.67 | 1.09 | 21 | #330 |
| 20 | 56.8 | Breakout & Momentum Pack · Variant 10 | Breakout Pack | 0.26% | -5.93% | 0.49 | 1.01 | 7 | #243 |
| 21 | 54.9 | Order Flow Proxy Pack · Variant 7 | Order Flow Pack | 1.35% | -99.82% | 3.98 | 1.79 | 15 | #340 |
| 22 | 54.6 | Volatility Pack · Variant 2 | Volatility Pack | 0.83% | -69.43% | 4.89 | 1.89 | 4 | #275 |
| 23 | 52.1 | Trend Following Pack · Variant 1 | Trend Pack | -0.48% | -6.37% | -0.21 | 0.89 | 19 | #215 |
| 24 | 51.1 | Indicator Resonance | CTA Classic | -0.44% | -1.54% | -0.55 | 0.00 | 1 | #26 |
| 25 | 50.9 | Volatility Pack · Variant 7 | Volatility Pack | -0.66% | -6.55% | -0.37 | 0.87 | 22 | #280 |
| 26 | 50.7 | Single Moving Average | CTA Classic | -0.99% | -4.12% | -0.33 | 0.17 | 3 | #24 |
| 27 | 49.8 | Regime Switch Pack · Variant 6 | Regime Switch Pack | -0.82% | -6.73% | -0.52 | 0.82 | 29 | #329 |
| 28 | 48.3 | Mean Reversion Pack · Variant 9 | Mean Reversion Pack | -0.33% | -1.58% | -1.43 | 0.78 | 21 | #252 |
| 29 | 46.0 | Mean Reversion Pack · Variant 1 | Mean Reversion Pack | 0.02% | -41.11% | 0.20 | 10.30 | 2 | #244 |
| 30 | 46.0 | Statistical Arbitrage Pack · Variant 10 | Stat Arb Pack | 0.02% | -41.11% | 0.20 | 10.30 | 2 | #303 |
| 31 | 45.4 | Options Volatility Pack · Variant 6 | Volatility Pack | 0.39% | -86.58% | 1.54 | 1.18 | 25 | #309 |
| 32 | 45.2 | Carry & Roll Yield Pack · Variant 8 | Carry Pack | -0.56% | -1.74% | -2.14 | 0.83 | 38 | #261 |
| 33 | 44.5 | Mean Reversion Pack · Variant 5 | Mean Reversion Pack | -0.62% | -1.82% | -2.50 | 0.52 | 11 | #248 |
| 34 | 44.5 | Relative Value Pack · Variant 2 | Relative Value Pack | -0.62% | -1.82% | -2.50 | 0.52 | 11 | #265 |
| 35 | 44.5 | Statistical Arbitrage Pack · Variant 1 | Stat Arb Pack | -0.62% | -1.82% | -2.49 | 0.52 | 11 | #294 |
| 36 | 43.4 | Breakout & Momentum Pack · Variant 9 | Breakout Pack | -1.49% | -2.28% | -3.22 | 0.53 | 28 | #242 |
| 37 | 43.2 | Regime Switch Pack · Variant 3 | Regime Switch Pack | -1.31% | -1.44% | -6.07 | 0.12 | 11 | #326 |
| 38 | 43.2 | Volatility Pack · Variant 4 | Volatility Pack | -1.38% | -3.35% | -6.32 | 0.62 | 38 | #277 |
| 39 | 43.0 | AS Options Market Maker | AS Options MM | -0.04% | -4.02% | -17.09 | 0.02 | 50 | #3 |
| 40 | 42.9 | Session Alpha Pack · Variant 10 | Session Alpha Pack | -1.80% | -2.02% | -7.24 | 0.37 | 23 | #323 |
| 41 | 42.2 | Session Alpha Pack · Variant 2 | Session Alpha Pack | -2.37% | -3.54% | -4.77 | 0.69 | 69 | #315 |
| 42 | 41.5 | Market Microstructure Pack · Variant 8 | Microstructure Pack | -2.34% | -3.45% | -6.04 | 0.31 | 23 | #291 |
| 43 | 40.5 | Market Microstructure Pack · Variant 6 | Microstructure Pack | -3.09% | -3.09% | -19.57 | 0.06 | 20 | #289 |
| 44 | 39.8 | Carry & Roll Yield Pack · Variant 7 | Carry Pack | -3.80% | -4.90% | -10.49 | 0.51 | 79 | #260 |
| 45 | 39.6 | Mean Reversion Pack · Variant 7 | Mean Reversion Pack | -3.84% | -4.48% | -11.20 | 0.35 | 95 | #250 |
| 46 | 39.4 | MACD and KDJ Confirmation | CTA Classic | -4.77% | -7.32% | -1.68 | 0.62 | 33 | #9 |
| 47 | 39.2 | Session Alpha Pack · Variant 3 | Session Alpha Pack | -4.16% | -5.20% | -11.93 | 0.50 | 100 | #316 |
| 48 | 39.2 | Order Flow Proxy Pack · Variant 6 | Order Flow Pack | -4.22% | -4.44% | -13.49 | 0.31 | 45 | #339 |
| 49 | 39.2 | Relative Value Pack · Variant 7 | Relative Value Pack | -2.84% | -8.79% | -2.50 | 0.71 | 108 | #270 |
| 50 | 39.0 | Session Alpha Pack · Variant 8 | Session Alpha Pack | -3.41% | -7.32% | -3.01 | 0.55 | 16 | #321 |
| 51 | 39.0 | Carry & Roll Yield Pack · Variant 4 | Carry Pack | -4.72% | -4.72% | -11.82 | 0.52 | 114 | #257 |
| 52 | 38.9 | Breakout & Momentum Pack · Variant 6 | Breakout Pack | -4.17% | -5.79% | -11.70 | 0.48 | 67 | #239 |
| 53 | 38.9 | Market Microstructure Pack · Variant 1 | Microstructure Pack | -4.17% | -5.79% | -11.69 | 0.48 | 67 | #284 |
| 54 | 38.6 | Statistical Arbitrage Pack · Variant 2 | Stat Arb Pack | -4.22% | -4.30% | -13.46 | 0.00 | 18 | #295 |
| 55 | 38.3 | AS Options Market Maker | AS Options MM | -0.15% | -14.79% | -3.02 | 0.42 | 399 | #1 |
| 56 | 37.8 | Statistical Arbitrage Pack · Variant 9 | Stat Arb Pack | -3.96% | -9.19% | -3.53 | 0.68 | 124 | #302 |
| 57 | 37.7 | Statistical Arbitrage Pack · Variant 5 | Stat Arb Pack | -5.12% | -5.12% | -13.19 | 0.21 | 48 | #298 |
| 58 | 37.5 | Volatility Pack · Variant 10 | Volatility Pack | -4.91% | -6.77% | -14.68 | 0.40 | 83 | #283 |
| 59 | 37.5 | Trend Following Pack · Variant 2 | Trend Pack | -3.67% | -9.62% | -3.23 | 0.48 | 34 | #225 |
| 60 | 37.2 | Options Volatility Pack · Variant 8 | Volatility Pack | -5.17% | -5.17% | -12.59 | 0.00 | 14 | #311 |
| 61 | 36.4 | Breakout & Momentum Pack · Variant 2 | Breakout Pack | -5.74% | -5.83% | -14.03 | 0.03 | 38 | #235 |
| 62 | 36.2 | Options Volatility Pack · Variant 4 | Volatility Pack | -0.02% | -70.01% | -0.14 | 0.97 | 7 | #307 |
| 63 | 36.1 | Carry & Roll Yield Pack · Variant 10 | Carry Pack | -6.38% | -6.38% | -19.39 | 0.36 | 119 | #263 |
| 64 | 35.8 | Order Flow Proxy Pack · Variant 10 | Order Flow Pack | -6.12% | -6.48% | -13.36 | 0.09 | 51 | #343 |
| 65 | 35.3 | Volatility Pack · Variant 3 | Volatility Pack | -7.00% | -7.00% | -18.93 | 0.38 | 115 | #276 |
| 66 | 34.7 | Session Alpha Pack · Variant 4 | Session Alpha Pack | -6.99% | -7.85% | -6.53 | 0.31 | 45 | #317 |
| 67 | 34.4 | Regime Switch Pack · Variant 2 | Regime Switch Pack | -6.81% | -8.00% | -6.87 | 0.11 | 10 | #325 |
| 68 | 34.0 | Session Alpha Pack · Variant 7 | Session Alpha Pack | -7.07% | -8.33% | -6.57 | 0.10 | 7 | #320 |
| 69 | 33.8 | Regime Switch Pack · Variant 10 | Regime Switch Pack | -7.34% | -8.26% | -7.43 | 0.14 | 24 | #333 |
| 70 | 33.1 | Relative Value Pack · Variant 9 | Relative Value Pack | -8.21% | -8.70% | -7.99 | 0.33 | 49 | #272 |
| 71 | 32.1 | Regime Switch Pack · Variant 8 | Regime Switch Pack | -8.51% | -9.77% | -8.00 | 0.22 | 57 | #331 |
| 72 | 31.8 | Market Microstructure Pack · Variant 2 | Microstructure Pack | -8.65% | -9.69% | -9.14 | 0.13 | 50 | #285 |
| 73 | 31.4 | Order Flow Proxy Pack · Variant 9 | Order Flow Pack | -9.08% | -9.97% | -8.55 | 0.21 | 87 | #342 |
| 74 | 28.1 | Carry & Roll Yield Pack · Variant 2 | Carry Pack | -11.52% | -12.07% | -11.15 | 0.35 | 129 | #255 |
| 75 | 26.8 | Volatility Pack · Variant 6 | Volatility Pack | -12.36% | -12.36% | -12.92 | 0.16 | 107 | #279 |
| 76 | 26.7 | Breakout & Momentum Pack · Variant 4 | Breakout Pack | -0.21% | -63.50% | -1.62 | 0.00 | 2 | #237 |
| 77 | 26.4 | Momentum Top-N Rotation | US Portfolio | -11.50% | -14.42% | -2.23 | 0.07 | 22 | #85 |
| 78 | 25.7 | Breakout & Momentum Pack · Variant 5 | Breakout Pack | -0.39% | -74.04% | -2.87 | 0.53 | 7 | #238 |
| 79 | 24.9 | Carry & Roll Yield Pack · Variant 1 | Carry Pack | -13.65% | -14.18% | -13.36 | 0.32 | 149 | #254 |
| 80 | 24.8 | Breakout & Momentum Pack · Variant 8 | Breakout Pack | -0.24% | -55.71% | -2.46 | 0.00 | 2 | #241 |
| 81 | 24.6 | Mean Reversion Pack · Variant 4 | Mean Reversion Pack | -0.66% | -78.06% | -4.20 | 0.12 | 6 | #247 |
| 82 | 22.4 | AS Options Market Maker(SA2701) | AS Options MM | 21.59% | -20.81% | 46.40 | 2159.10 | 247 | #4 |
| 83 | 21.0 | Order Flow Proxy Pack · Variant 3 | Order Flow Pack | -15.93% | -16.19% | -15.67 | 0.03 | 71 | #336 |
| 84 | 18.3 | Market Microstructure Pack · Variant 7 | Microstructure Pack | -17.97% | -17.97% | -18.93 | 0.14 | 157 | #290 |
| 85 | 18.0 | Order Flow Proxy Pack · Variant 8 | Order Flow Pack | -18.22% | -18.28% | -18.10 | 0.16 | 133 | #341 |

## 4. 策略族排行榜

| 排名 | 策略族 | 策略数 | 有成交 | 平均得分 | 平均收益* | 总成交 | 族内最佳 |
|------|--------|--------|--------|----------|-----------|--------|----------|
| 1 | Other | 1 | 1 | 83.1 | 3.65% | 2 | [DEBUG] SA701 force long (#214) |
| 2 | US Portfolio | 4 | 4 | 64.6 | 2.48% | 75 | Quality Growth Multi-Factor (#28) |
| 3 | Mean Reversion Pack | 10 | 9 | 53.0 | 0.26% | 221 | Mean Reversion Pack · Variant 8 (#251) |
| 4 | Order Flow Pack | 10 | 8 | 36.9 | -6.30% | 471 | Order Flow Proxy Pack · Variant 5 (#338) |
| 5 | Regime Switch Pack | 10 | 7 | 36.7 | -3.32% | 155 | Regime Switch Pack · Variant 5 (#328) |
| 6 | CTA Classic | 8 | 4 | 36.5 | 1.55% | 43 | Dual Moving Average (#5) |
| 7 | Volatility Pack | 20 | 12 | 35.7 | -2.29% | 477 | Options Volatility Pack · Variant 3 (#306) |
| 8 | Session Alpha Pack | 10 | 7 | 34.6 | -3.54% | 295 | Session Alpha Pack · Variant 9 (#322) |
| 9 | AS Options MM | 3 | 3 | 34.6 | 7.14% | 696 | AS Options Market Maker (#3) |
| 10 | Stat Arb Pack | 10 | 6 | 34.1 | -2.24% | 210 | Statistical Arbitrage Pack · Variant 3 (#296) |
| 11 | Breakout Pack | 10 | 7 | 30.5 | -1.71% | 151 | Breakout & Momentum Pack · Variant 10 (#243) |
| 12 | Carry Pack | 10 | 6 | 28.3 | -6.77% | 628 | Carry & Roll Yield Pack · Variant 8 (#261) |
| 13 | Trend Pack | 10 | 3 | 27.4 | -1.03% | 83 | Trend Following Pack · Variant 8 (#231) |
| 14 | Microstructure Pack | 10 | 5 | 25.9 | -7.24% | 317 | Market Microstructure Pack · Variant 8 (#291) |
| 15 | Relative Value Pack | 10 | 3 | 23.9 | -3.89% | 168 | Relative Value Pack · Variant 2 (#265) |

\*平均收益仅统计有成交样本。

## 5. 方法说明与限制

- 跨族不可直接比绝对收益：标的、周期、资金、费率可能不同。
- 同策略重复回测时，总榜以去重结果为主；附录保留全量。
- Pack 依赖国内期货分钟线与期权合约键；连续合约 `SA0` 与月份码 `SA701` 不是同一符号。

## 附录 A：全量回测清单（按得分）

| Run | 策略 | 族 | 标的 | 周期 | 收益 | Sharpe | 成交 | 得分 | 标记 |
|-----|------|----|------|------|------|--------|------|------|------|
| #214 | [DEBUG] SA701 force long | Other | CNFutures:SA701 | 1m | 3.65% | 9.93 | 2 | 83.1 | ok |
| #5 | Dual Moving Average | CTA Classic | Crypto:BTC/USDT | 4h | 12.38% | 1.81 | 6 | 82.8 | ok |
| #6 | Dual Moving Average | CTA Classic | Crypto:BTC/USDT | 4h | 12.38% | 1.81 | 6 | 82.8 | ok |
| #12 | Dual Moving Average | CTA Classic | Crypto:BTC/USDT | 4h | 12.38% | 1.81 | 6 | 82.8 | ok |
| #18 | Dual Moving Average | CTA Classic | Crypto:BTC/USDT | 4h | 12.38% | 1.81 | 6 | 82.8 | ok |
| #80 | Dual Moving Average | CTA Classic | Crypto:BTC/USDT | 4h | 12.11% | 1.78 | 6 | 82.0 | ok |
| #216 | Dual Moving Average | CTA Classic | Crypto:BTC/USDT | 4h | 12.11% | 1.78 | 6 | 82.0 | ok |
| #251 | Mean Reversion Pack · Variant 8 | Mean Reversion Pack | SA701 + SA701-C-1000 | 1m | 2.84% | 7.41 | 16 | 82.0 | ok |
| #28 | Quality Growth Multi-Factor | US Portfolio | AAPL + MSFT + NVDA + AMZN + META + GOOG… | 1d | 7.49% | 2.51 | 19 | 81.3 | ok |
| #249 | Mean Reversion Pack · Variant 6 | Mean Reversion Pack | SA701 + SA701-C-1000 | 1m | 1.84% | 6.02 | 21 | 81.1 | ok |
| #84 | Small and Large Cap Barbell | US Portfolio | AAPL + MSFT + NVDA + AMZN + META + GOOG… | 1d | 7.33% | 2.44 | 17 | 80.8 | ok |
| #220 | Small and Large Cap Barbell | US Portfolio | AAPL + MSFT + NVDA + AMZN + META + GOOG… | 1d | 7.33% | 2.44 | 17 | 80.8 | ok |
| #306 | Options Volatility Pack · Variant 3 | Volatility Pack | SA701 + SA701-C-1000 | 1m | 0.09% | 5.40 | 1 | 77.7 | ok |
| #245 | Mean Reversion Pack · Variant 2 | Mean Reversion Pack | SA701 + SA701-C-1000 | 1m | 2.18% | 5.67 | 29 | 76.8 | ok |
| #338 | Order Flow Proxy Pack · Variant 5 | Order Flow Pack | SA701 + SA701-C-1000 | 1m | 0.99% | 3.48 | 23 | 72.5 | ok |
| #11 | Low Volatility Rotation | US Portfolio | AAPL + MSFT + NVDA + AMZN + META + GOOG… | 1d | 6.61% | 1.92 | 17 | 69.9 | ok |
| #17 | Low Volatility Rotation | US Portfolio | AAPL + MSFT + NVDA + AMZN + META + GOOG… | 1d | 6.61% | 1.92 | 17 | 69.9 | ok |
| #23 | Low Volatility Rotation | US Portfolio | AAPL + MSFT + NVDA + AMZN + META + GOOG… | 1d | 6.61% | 1.92 | 17 | 69.9 | ok |
| #86 | Low Volatility Rotation | US Portfolio | AAPL + MSFT + NVDA + AMZN + META + GOOG… | 1d | 6.45% | 1.86 | 16 | 69.5 | ok |
| #222 | Low Volatility Rotation | US Portfolio | AAPL + MSFT + NVDA + AMZN + META + GOOG… | 1d | 6.45% | 1.86 | 16 | 69.5 | ok |
| #253 | Mean Reversion Pack · Variant 10 | Mean Reversion Pack | SA701 + SA701-C-1000 | 1m | 0.87% | 2.14 | 20 | 69.4 | ok |
| #296 | Statistical Arbitrage Pack · Variant 3 | Stat Arb Pack | SA701 + SA701-C-1000 | 1m | 0.45% | 1.65 | 7 | 65.9 | ok |
| #278 | Volatility Pack · Variant 5 | Volatility Pack | SA701 + SA701-C-1000 | 1m | 1.44% | 1.58 | 22 | 65.7 | ok |
| #281 | Volatility Pack · Variant 8 | Volatility Pack | SA701 + SA701-C-1000 | 1m | 1.28% | 1.44 | 39 | 63.8 | ok |
| #328 | Regime Switch Pack · Variant 5 | Regime Switch Pack | SA701 + SA701-C-1000 | 1m | 1.09% | 1.29 | 3 | 63.4 | ok |
| #231 | Trend Following Pack · Variant 8 | Trend Pack | SA701 + SA701-C-1000 | 1m | 1.06% | 1.23 | 30 | 62.0 | ok |
| #322 | Session Alpha Pack · Variant 9 | Session Alpha Pack | SA701 + SA701-C-1000 | 1m | 1.06% | 1.22 | 35 | 61.8 | ok |
| #337 | Order Flow Proxy Pack · Variant 4 | Order Flow Pack | SA701 + SA701-C-1000 | 1m | 0.83% | 1.02 | 46 | 61.1 | ok |
| #87 | Quality Growth Multi-Factor | US Portfolio | AAPL + MSFT + NVDA + AMZN + META + GOOG… | 1d | -0.74% | 0.10 | 13 | 58.6 | ok |
| #223 | Quality Growth Multi-Factor | US Portfolio | AAPL + MSFT + NVDA + AMZN + META + GOOG… | 1d | -0.74% | 0.10 | 13 | 58.6 | ok |
| #330 | Regime Switch Pack · Variant 7 | Regime Switch Pack | SA701 + SA701-C-1000 | 1m | 0.45% | 0.67 | 21 | 58.3 | ok |
| #29 | Small and Large Cap Barbell | US Portfolio | AAPL + MSFT + NVDA + AMZN + META + GOOG… | 1d | -1.20% | 0.00 | 13 | 57.6 | ok |
| #243 | Breakout & Momentum Pack · Variant 10 | Breakout Pack | SA701 + SA701-C-1000 | 1m | 0.26% | 0.49 | 7 | 56.8 | ok |
| #340 | Order Flow Proxy Pack · Variant 7 | Order Flow Pack | SA701 + SA701-C-1000 | 1m | 1.35% | 3.98 | 15 | 54.9 | ok |
| #275 | Volatility Pack · Variant 2 | Volatility Pack | SA701 + SA701-C-1000 | 1m | 0.83% | 4.89 | 4 | 54.6 | ok |
| #215 | Trend Following Pack · Variant 1 | Trend Pack | SA701 + SA701-C-1000 | 1m | -0.48% | -0.21 | 19 | 52.1 | ok |
| #224 | Trend Following Pack · Variant 1 | Trend Pack | SA701 + SA701-C-1000 | 1m | -0.58% | -0.29 | 19 | 51.5 | ok |
| #26 | Indicator Resonance | CTA Classic | USStock:QQQ | 1d | -0.44% | -0.55 | 1 | 51.1 | ok |
| #280 | Volatility Pack · Variant 7 | Volatility Pack | SA701 + SA701-C-1000 | 1m | -0.66% | -0.37 | 22 | 50.9 | ok |
| #24 | Single Moving Average | CTA Classic | USStock:SPY | 1d | -0.99% | -0.33 | 3 | 50.7 | ok |
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
| #3 | AS Options Market Maker | AS Options MM | M2610-C-1000 + SA2610 | 1m | -0.04% | -17.09 | 50 | 43.0 | ok |
| #323 | Session Alpha Pack · Variant 10 | Session Alpha Pack | SA701 + SA701-C-1000 | 1m | -1.80% | -7.24 | 23 | 42.9 | ok |
| #315 | Session Alpha Pack · Variant 2 | Session Alpha Pack | SA701 + SA701-C-1000 | 1m | -2.37% | -4.77 | 69 | 42.2 | ok |
| #291 | Market Microstructure Pack · Variant 8 | Microstructure Pack | SA701 + SA701-C-1000 | 1m | -2.34% | -6.04 | 23 | 41.5 | ok |
| #289 | Market Microstructure Pack · Variant 6 | Microstructure Pack | SA701 + SA701-C-1000 | 1m | -3.09% | -19.57 | 20 | 40.5 | ok |
| #260 | Carry & Roll Yield Pack · Variant 7 | Carry Pack | SA701 + SA701-C-1000 | 1m | -3.80% | -10.49 | 79 | 39.8 | ok |
| #250 | Mean Reversion Pack · Variant 7 | Mean Reversion Pack | SA701 + SA701-C-1000 | 1m | -3.84% | -11.20 | 95 | 39.6 | ok |
| #9 | MACD and KDJ Confirmation | CTA Classic | Crypto:BTC/USDT | 4h | -4.77% | -1.68 | 33 | 39.4 | ok |
| #15 | MACD and KDJ Confirmation | CTA Classic | Crypto:BTC/USDT | 4h | -4.77% | -1.68 | 33 | 39.4 | ok |
| #21 | MACD and KDJ Confirmation | CTA Classic | Crypto:BTC/USDT | 4h | -4.77% | -1.68 | 33 | 39.4 | ok |
| #316 | Session Alpha Pack · Variant 3 | Session Alpha Pack | SA701 + SA701-C-1000 | 1m | -4.16% | -11.93 | 100 | 39.2 | ok |
| #339 | Order Flow Proxy Pack · Variant 6 | Order Flow Pack | SA701 + SA701-C-1000 | 1m | -4.22% | -13.49 | 45 | 39.2 | ok |
| #270 | Relative Value Pack · Variant 7 | Relative Value Pack | SA701 + SA701-C-1000 | 1m | -2.84% | -2.50 | 108 | 39.2 | ok |
| #321 | Session Alpha Pack · Variant 8 | Session Alpha Pack | SA701 + SA701-C-1000 | 1m | -3.41% | -3.01 | 16 | 39.0 | ok |
| #257 | Carry & Roll Yield Pack · Variant 4 | Carry Pack | SA701 + SA701-C-1000 | 1m | -4.72% | -11.82 | 114 | 39.0 | ok |
| #239 | Breakout & Momentum Pack · Variant 6 | Breakout Pack | SA701 + SA701-C-1000 | 1m | -4.17% | -11.70 | 67 | 38.9 | ok |
| #284 | Market Microstructure Pack · Variant 1 | Microstructure Pack | SA701 + SA701-C-1000 | 1m | -4.17% | -11.69 | 67 | 38.9 | ok |
| #295 | Statistical Arbitrage Pack · Variant 2 | Stat Arb Pack | SA701 + SA701-C-1000 | 1m | -4.22% | -13.46 | 18 | 38.6 | ok |
| #1 | AS Options Market Maker | AS Options MM | M2609-C-2800 + M2609 | 5m | -0.15% | -3.02 | 399 | 38.3 | ok |
| #302 | Statistical Arbitrage Pack · Variant 9 | Stat Arb Pack | SA701 + SA701-C-1000 | 1m | -3.96% | -3.53 | 124 | 37.8 | ok |
| #298 | Statistical Arbitrage Pack · Variant 5 | Stat Arb Pack | SA701 + SA701-C-1000 | 1m | -5.12% | -13.19 | 48 | 37.7 | ok |
| #283 | Volatility Pack · Variant 10 | Volatility Pack | SA701 + SA701-C-1000 | 1m | -4.91% | -14.68 | 83 | 37.5 | ok |
| #225 | Trend Following Pack · Variant 2 | Trend Pack | SA701 + SA701-C-1000 | 1m | -3.67% | -3.23 | 34 | 37.5 | ok |
| #311 | Options Volatility Pack · Variant 8 | Volatility Pack | SA701 + SA701-C-1000 | 1m | -5.17% | -12.59 | 14 | 37.2 | ok |
| #235 | Breakout & Momentum Pack · Variant 2 | Breakout Pack | SA701 + SA701-C-1000 | 1m | -5.74% | -14.03 | 38 | 36.4 | ok |
| #307 | Options Volatility Pack · Variant 4 | Volatility Pack | SA701 + SA701-C-1000 | 1m | -0.02% | -0.14 | 7 | 36.2 | ok |
| #263 | Carry & Roll Yield Pack · Variant 10 | Carry Pack | SA701 + SA701-C-1000 | 1m | -6.38% | -19.39 | 119 | 36.1 | ok |
| #83 | MACD and KDJ Confirmation | CTA Classic | Crypto:BTC/USDT | 4h | -5.97% | -2.13 | 33 | 35.9 | ok |
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
| #85 | Momentum Top-N Rotation | US Portfolio | AAPL + MSFT + NVDA + AMZN + META + GOOG… | 1d | -11.50% | -2.23 | 22 | 26.4 | ok |
| #221 | Momentum Top-N Rotation | US Portfolio | AAPL + MSFT + NVDA + AMZN + META + GOOG… | 1d | -11.50% | -2.23 | 22 | 26.4 | ok |
| #10 | Momentum Top-N Rotation | US Portfolio | AAPL + MSFT + NVDA + AMZN + META + GOOG… | 1d | -11.52% | -2.25 | 19 | 26.4 | ok |
| #16 | Momentum Top-N Rotation | US Portfolio | AAPL + MSFT + NVDA + AMZN + META + GOOG… | 1d | -11.52% | -2.25 | 19 | 26.4 | ok |
| #22 | Momentum Top-N Rotation | US Portfolio | AAPL + MSFT + NVDA + AMZN + META + GOOG… | 1d | -11.52% | -2.25 | 19 | 26.4 | ok |
| #238 | Breakout & Momentum Pack · Variant 5 | Breakout Pack | SA701 + SA701-C-1000 | 1m | -0.39% | -2.87 | 7 | 25.7 | ok |
| #254 | Carry & Roll Yield Pack · Variant 1 | Carry Pack | SA701 + SA701-C-1000 | 1m | -13.65% | -13.36 | 149 | 24.9 | ok |
| #241 | Breakout & Momentum Pack · Variant 8 | Breakout Pack | SA701 + SA701-C-1000 | 1m | -0.24% | -2.46 | 2 | 24.8 | ok |
| #247 | Mean Reversion Pack · Variant 4 | Mean Reversion Pack | SA701 + SA701-C-1000 | 1m | -0.66% | -4.20 | 6 | 24.6 | ok |
| #4 | AS Options Market Maker(SA2701) | AS Options MM | SA2701-C-1000 + SA2701 | 1m | 21.59% | 46.40 | 247 | 22.4 | extreme_outlier |
| #336 | Order Flow Proxy Pack · Variant 3 | Order Flow Pack | SA701 + SA701-C-1000 | 1m | -15.93% | -15.67 | 71 | 21.0 | ok |
| #2 | AS Options Market Maker | AS Options MM | M2610-C-1000 + SA2610 | 1m | 33.79% | 35.04 | 246 | 21.0 | extreme_outlier |
| #25 | Turtle Trading | CTA Classic | USStock:SPY | 1d | 0.82% | 1.00 | 0 | 19.3 | no_trades |
| #290 | Market Microstructure Pack · Variant 7 | Microstructure Pack | SA701 + SA701-C-1000 | 1m | -17.97% | -18.93 | 157 | 18.3 | ok |
| #341 | Order Flow Proxy Pack · Variant 8 | Order Flow Pack | SA701 + SA701-C-1000 | 1m | -18.22% | -18.10 | 133 | 18.0 | ok |
| #7 | Bullish Candle Through Three Averages | CTA Classic | CNStock:600519.SH | 1d | 0.00% | 0.00 | 0 | 17.5 | no_trades |
| #8 | Bullish Three Averages With Trend Filter | CTA Classic | CNStock:600519.SH | 1d | 0.00% | 0.00 | 0 | 17.5 | no_trades |
| #13 | Bullish Candle Through Three Averages | CTA Classic | CNStock:600519.SH | 1d | 0.00% | 0.00 | 0 | 17.5 | no_trades |
| #14 | Bullish Candle Through Three Averages | CTA Classic | CNStock:600519.SH | 1d | 0.00% | 0.00 | 0 | 17.5 | no_trades |
| #19 | Bullish Candle Through Three Averages | CTA Classic | CNStock:600519.SH | 1d | 0.00% | 0.00 | 0 | 17.5 | no_trades |
| #20 | Bullish Candle Through Three Averages | CTA Classic | CNStock:600519.SH | 1d | 0.00% | 0.00 | 0 | 17.5 | no_trades |
| #30 | Statistical Arbitrage Pack · Variant 1 | Stat Arb Pack | SA701 + SA701-C-1000 | 1m | 0.00% | 0.00 | 0 | 17.5 | no_trades |
| #31 | Statistical Arbitrage Pack · Variant 2 | Stat Arb Pack | SA701 + SA701-C-1000 | 1m | 0.00% | 0.00 | 0 | 17.5 | no_trades |
| #32 | Statistical Arbitrage Pack · Variant 3 | Stat Arb Pack | SA701 + SA701-C-1000 | 1m | 0.00% | 0.00 | 0 | 17.5 | no_trades |
| #33 | Statistical Arbitrage Pack · Variant 4 | Stat Arb Pack | SA701 + SA701-C-1000 | 1m | 0.00% | 0.00 | 0 | 17.5 | no_trades |
| #34 | Statistical Arbitrage Pack · Variant 5 | Stat Arb Pack | SA701 + SA701-C-1000 | 1m | 0.00% | 0.00 | 0 | 17.5 | no_trades |
| #35 | Statistical Arbitrage Pack · Variant 6 | Stat Arb Pack | SA701 + SA701-C-1000 | 1m | 0.00% | 0.00 | 0 | 17.5 | no_trades |
| #36 | Statistical Arbitrage Pack · Variant 7 | Stat Arb Pack | SA701 + SA701-C-1000 | 1m | 0.00% | 0.00 | 0 | 17.5 | no_trades |
| #37 | Statistical Arbitrage Pack · Variant 8 | Stat Arb Pack | SA701 + SA701-C-1000 | 1m | 0.00% | 0.00 | 0 | 17.5 | no_trades |
| #38 | Statistical Arbitrage Pack · Variant 9 | Stat Arb Pack | SA701 + SA701-C-1000 | 1m | 0.00% | 0.00 | 0 | 17.5 | no_trades |
| #39 | Statistical Arbitrage Pack · Variant 10 | Stat Arb Pack | SA701 + SA701-C-1000 | 1m | 0.00% | 0.00 | 0 | 17.5 | no_trades |
| #40 | Options Volatility Pack · Variant 1 | Volatility Pack | SA701 + SA701-C-1000 | 1m | 0.00% | 0.00 | 0 | 17.5 | no_trades |
| #41 | Options Volatility Pack · Variant 2 | Volatility Pack | SA701 + SA701-C-1000 | 1m | 0.00% | 0.00 | 0 | 17.5 | no_trades |
| #42 | Options Volatility Pack · Variant 3 | Volatility Pack | SA701 + SA701-C-1000 | 1m | 0.00% | 0.00 | 0 | 17.5 | no_trades |
| #43 | Options Volatility Pack · Variant 4 | Volatility Pack | SA701 + SA701-C-1000 | 1m | 0.00% | 0.00 | 0 | 17.5 | no_trades |
| #44 | Options Volatility Pack · Variant 5 | Volatility Pack | SA701 + SA701-C-1000 | 1m | 0.00% | 0.00 | 0 | 17.5 | no_trades |
| #45 | Options Volatility Pack · Variant 6 | Volatility Pack | SA701 + SA701-C-1000 | 1m | 0.00% | 0.00 | 0 | 17.5 | no_trades |
| #46 | Options Volatility Pack · Variant 7 | Volatility Pack | SA701 + SA701-C-1000 | 1m | 0.00% | 0.00 | 0 | 17.5 | no_trades |
| #47 | Options Volatility Pack · Variant 8 | Volatility Pack | SA701 + SA701-C-1000 | 1m | 0.00% | 0.00 | 0 | 17.5 | no_trades |
| #48 | Options Volatility Pack · Variant 9 | Volatility Pack | SA701 + SA701-C-1000 | 1m | 0.00% | 0.00 | 0 | 17.5 | no_trades |
| #49 | Options Volatility Pack · Variant 10 | Volatility Pack | SA701 + SA701-C-1000 | 1m | 0.00% | 0.00 | 0 | 17.5 | no_trades |
| #50 | Session Alpha Pack · Variant 1 | Session Alpha Pack | SA701 + SA701-C-1000 | 1m | 0.00% | 0.00 | 0 | 17.5 | no_trades |
| #51 | Session Alpha Pack · Variant 2 | Session Alpha Pack | SA701 + SA701-C-1000 | 1m | 0.00% | 0.00 | 0 | 17.5 | no_trades |
| #52 | Session Alpha Pack · Variant 3 | Session Alpha Pack | SA701 + SA701-C-1000 | 1m | 0.00% | 0.00 | 0 | 17.5 | no_trades |
| #53 | Session Alpha Pack · Variant 4 | Session Alpha Pack | SA701 + SA701-C-1000 | 1m | 0.00% | 0.00 | 0 | 17.5 | no_trades |
| #54 | Session Alpha Pack · Variant 5 | Session Alpha Pack | SA701 + SA701-C-1000 | 1m | 0.00% | 0.00 | 0 | 17.5 | no_trades |
| #55 | Session Alpha Pack · Variant 6 | Session Alpha Pack | SA701 + SA701-C-1000 | 1m | 0.00% | 0.00 | 0 | 17.5 | no_trades |
| #56 | Session Alpha Pack · Variant 7 | Session Alpha Pack | SA701 + SA701-C-1000 | 1m | 0.00% | 0.00 | 0 | 17.5 | no_trades |
| #57 | Session Alpha Pack · Variant 8 | Session Alpha Pack | SA701 + SA701-C-1000 | 1m | 0.00% | 0.00 | 0 | 17.5 | no_trades |
| #58 | Session Alpha Pack · Variant 9 | Session Alpha Pack | SA701 + SA701-C-1000 | 1m | 0.00% | 0.00 | 0 | 17.5 | no_trades |
| #59 | Session Alpha Pack · Variant 10 | Session Alpha Pack | SA701 + SA701-C-1000 | 1m | 0.00% | 0.00 | 0 | 17.5 | no_trades |
| #60 | Regime Switch Pack · Variant 1 | Regime Switch Pack | SA701 + SA701-C-1000 | 1m | 0.00% | 0.00 | 0 | 17.5 | no_trades |
| #61 | Regime Switch Pack · Variant 2 | Regime Switch Pack | SA701 + SA701-C-1000 | 1m | 0.00% | 0.00 | 0 | 17.5 | no_trades |
| #62 | Regime Switch Pack · Variant 3 | Regime Switch Pack | SA701 + SA701-C-1000 | 1m | 0.00% | 0.00 | 0 | 17.5 | no_trades |
| #63 | Regime Switch Pack · Variant 4 | Regime Switch Pack | SA701 + SA701-C-1000 | 1m | 0.00% | 0.00 | 0 | 17.5 | no_trades |
| #64 | Regime Switch Pack · Variant 5 | Regime Switch Pack | SA701 + SA701-C-1000 | 1m | 0.00% | 0.00 | 0 | 17.5 | no_trades |
| #65 | Regime Switch Pack · Variant 6 | Regime Switch Pack | SA701 + SA701-C-1000 | 1m | 0.00% | 0.00 | 0 | 17.5 | no_trades |
| #66 | Regime Switch Pack · Variant 7 | Regime Switch Pack | SA701 + SA701-C-1000 | 1m | 0.00% | 0.00 | 0 | 17.5 | no_trades |
| #67 | Regime Switch Pack · Variant 8 | Regime Switch Pack | SA701 + SA701-C-1000 | 1m | 0.00% | 0.00 | 0 | 17.5 | no_trades |
| #68 | Regime Switch Pack · Variant 9 | Regime Switch Pack | SA701 + SA701-C-1000 | 1m | 0.00% | 0.00 | 0 | 17.5 | no_trades |
| #69 | Regime Switch Pack · Variant 10 | Regime Switch Pack | SA701 + SA701-C-1000 | 1m | 0.00% | 0.00 | 0 | 17.5 | no_trades |
| #70 | Order Flow Proxy Pack · Variant 1 | Order Flow Pack | SA701 + SA701-C-1000 | 1m | 0.00% | 0.00 | 0 | 17.5 | no_trades |
| #71 | Order Flow Proxy Pack · Variant 2 | Order Flow Pack | SA701 + SA701-C-1000 | 1m | 0.00% | 0.00 | 0 | 17.5 | no_trades |
| #72 | Order Flow Proxy Pack · Variant 3 | Order Flow Pack | SA701 + SA701-C-1000 | 1m | 0.00% | 0.00 | 0 | 17.5 | no_trades |
| #73 | Order Flow Proxy Pack · Variant 4 | Order Flow Pack | SA701 + SA701-C-1000 | 1m | 0.00% | 0.00 | 0 | 17.5 | no_trades |
| #74 | Order Flow Proxy Pack · Variant 5 | Order Flow Pack | SA701 + SA701-C-1000 | 1m | 0.00% | 0.00 | 0 | 17.5 | no_trades |
| #75 | Order Flow Proxy Pack · Variant 6 | Order Flow Pack | SA701 + SA701-C-1000 | 1m | 0.00% | 0.00 | 0 | 17.5 | no_trades |
| #76 | Order Flow Proxy Pack · Variant 7 | Order Flow Pack | SA701 + SA701-C-1000 | 1m | 0.00% | 0.00 | 0 | 17.5 | no_trades |
| #77 | Order Flow Proxy Pack · Variant 8 | Order Flow Pack | SA701 + SA701-C-1000 | 1m | 0.00% | 0.00 | 0 | 17.5 | no_trades |
| #78 | Order Flow Proxy Pack · Variant 9 | Order Flow Pack | SA701 + SA701-C-1000 | 1m | 0.00% | 0.00 | 0 | 17.5 | no_trades |
| #79 | Order Flow Proxy Pack · Variant 10 | Order Flow Pack | SA701 + SA701-C-1000 | 1m | 0.00% | 0.00 | 0 | 17.5 | no_trades |
| #81 | Bullish Candle Through Three Averages | CTA Classic | CNStock:600519.SH | 1d | 0.00% | 0.00 | 0 | 17.5 | no_trades |
| #82 | Bullish Three Averages With Trend Filter | CTA Classic | CNStock:600519.SH | 1d | 0.00% | 0.00 | 0 | 17.5 | no_trades |
| #88 | Trend Following Pack · Variant 1 | Trend Pack | SA701 + SA701-C-1000 | 1m | 0.00% | 0.00 | 0 | 17.5 | no_trades |
| #89 | Trend Following Pack · Variant 2 | Trend Pack | SA701 + SA701-C-1000 | 1m | 0.00% | 0.00 | 0 | 17.5 | no_trades |
| #90 | Trend Following Pack · Variant 3 | Trend Pack | SA701 + SA701-C-1000 | 1m | 0.00% | 0.00 | 0 | 17.5 | no_trades |
| #91 | Trend Following Pack · Variant 4 | Trend Pack | SA701 + SA701-C-1000 | 1m | 0.00% | 0.00 | 0 | 17.5 | no_trades |
| #92 | Trend Following Pack · Variant 5 | Trend Pack | SA701 + SA701-C-1000 | 1m | 0.00% | 0.00 | 0 | 17.5 | no_trades |
| #93 | Trend Following Pack · Variant 6 | Trend Pack | SA701 + SA701-C-1000 | 1m | 0.00% | 0.00 | 0 | 17.5 | no_trades |
| #94 | Trend Following Pack · Variant 7 | Trend Pack | SA701 + SA701-C-1000 | 1m | 0.00% | 0.00 | 0 | 17.5 | no_trades |
| #95 | Trend Following Pack · Variant 8 | Trend Pack | SA701 + SA701-C-1000 | 1m | 0.00% | 0.00 | 0 | 17.5 | no_trades |
| #96 | Trend Following Pack · Variant 9 | Trend Pack | SA701 + SA701-C-1000 | 1m | 0.00% | 0.00 | 0 | 17.5 | no_trades |
| #97 | Trend Following Pack · Variant 10 | Trend Pack | SA701 + SA701-C-1000 | 1m | 0.00% | 0.00 | 0 | 17.5 | no_trades |
| #98 | Breakout & Momentum Pack · Variant 1 | Breakout Pack | SA701 + SA701-C-1000 | 1m | 0.00% | 0.00 | 0 | 17.5 | no_trades |
| #99 | Breakout & Momentum Pack · Variant 2 | Breakout Pack | SA701 + SA701-C-1000 | 1m | 0.00% | 0.00 | 0 | 17.5 | no_trades |
| #100 | Breakout & Momentum Pack · Variant 3 | Breakout Pack | SA701 + SA701-C-1000 | 1m | 0.00% | 0.00 | 0 | 17.5 | no_trades |
| #101 | Breakout & Momentum Pack · Variant 4 | Breakout Pack | SA701 + SA701-C-1000 | 1m | 0.00% | 0.00 | 0 | 17.5 | no_trades |
| #102 | Breakout & Momentum Pack · Variant 5 | Breakout Pack | SA701 + SA701-C-1000 | 1m | 0.00% | 0.00 | 0 | 17.5 | no_trades |
| #103 | Breakout & Momentum Pack · Variant 6 | Breakout Pack | SA701 + SA701-C-1000 | 1m | 0.00% | 0.00 | 0 | 17.5 | no_trades |
| #104 | Breakout & Momentum Pack · Variant 7 | Breakout Pack | SA701 + SA701-C-1000 | 1m | 0.00% | 0.00 | 0 | 17.5 | no_trades |
| #105 | Breakout & Momentum Pack · Variant 8 | Breakout Pack | SA701 + SA701-C-1000 | 1m | 0.00% | 0.00 | 0 | 17.5 | no_trades |
| #106 | Breakout & Momentum Pack · Variant 9 | Breakout Pack | SA701 + SA701-C-1000 | 1m | 0.00% | 0.00 | 0 | 17.5 | no_trades |
| #107 | Breakout & Momentum Pack · Variant 10 | Breakout Pack | SA701 + SA701-C-1000 | 1m | 0.00% | 0.00 | 0 | 17.5 | no_trades |
| #108 | Mean Reversion Pack · Variant 1 | Mean Reversion Pack | SA701 + SA701-C-1000 | 1m | 0.00% | 0.00 | 0 | 17.5 | no_trades |
| #109 | Mean Reversion Pack · Variant 2 | Mean Reversion Pack | SA701 + SA701-C-1000 | 1m | 0.00% | 0.00 | 0 | 17.5 | no_trades |
| #110 | Mean Reversion Pack · Variant 3 | Mean Reversion Pack | SA701 + SA701-C-1000 | 1m | 0.00% | 0.00 | 0 | 17.5 | no_trades |
| #111 | Mean Reversion Pack · Variant 4 | Mean Reversion Pack | SA701 + SA701-C-1000 | 1m | 0.00% | 0.00 | 0 | 17.5 | no_trades |
| #112 | Mean Reversion Pack · Variant 5 | Mean Reversion Pack | SA701 + SA701-C-1000 | 1m | 0.00% | 0.00 | 0 | 17.5 | no_trades |
| #113 | Mean Reversion Pack · Variant 6 | Mean Reversion Pack | SA701 + SA701-C-1000 | 1m | 0.00% | 0.00 | 0 | 17.5 | no_trades |
| #114 | Mean Reversion Pack · Variant 7 | Mean Reversion Pack | SA701 + SA701-C-1000 | 1m | 0.00% | 0.00 | 0 | 17.5 | no_trades |
| #115 | Mean Reversion Pack · Variant 8 | Mean Reversion Pack | SA701 + SA701-C-1000 | 1m | 0.00% | 0.00 | 0 | 17.5 | no_trades |
| #116 | Mean Reversion Pack · Variant 9 | Mean Reversion Pack | SA701 + SA701-C-1000 | 1m | 0.00% | 0.00 | 0 | 17.5 | no_trades |
| #117 | Mean Reversion Pack · Variant 10 | Mean Reversion Pack | SA701 + SA701-C-1000 | 1m | 0.00% | 0.00 | 0 | 17.5 | no_trades |
| #118 | Carry & Roll Yield Pack · Variant 1 | Carry Pack | SA701 + SA701-C-1000 | 1m | 0.00% | 0.00 | 0 | 17.5 | no_trades |
| #119 | Carry & Roll Yield Pack · Variant 2 | Carry Pack | SA701 + SA701-C-1000 | 1m | 0.00% | 0.00 | 0 | 17.5 | no_trades |
| #120 | Carry & Roll Yield Pack · Variant 3 | Carry Pack | SA701 + SA701-C-1000 | 1m | 0.00% | 0.00 | 0 | 17.5 | no_trades |
| #121 | Carry & Roll Yield Pack · Variant 4 | Carry Pack | SA701 + SA701-C-1000 | 1m | 0.00% | 0.00 | 0 | 17.5 | no_trades |
| #122 | Carry & Roll Yield Pack · Variant 5 | Carry Pack | SA701 + SA701-C-1000 | 1m | 0.00% | 0.00 | 0 | 17.5 | no_trades |
| #123 | Carry & Roll Yield Pack · Variant 6 | Carry Pack | SA701 + SA701-C-1000 | 1m | 0.00% | 0.00 | 0 | 17.5 | no_trades |
| #124 | Carry & Roll Yield Pack · Variant 7 | Carry Pack | SA701 + SA701-C-1000 | 1m | 0.00% | 0.00 | 0 | 17.5 | no_trades |
| #125 | Carry & Roll Yield Pack · Variant 8 | Carry Pack | SA701 + SA701-C-1000 | 1m | 0.00% | 0.00 | 0 | 17.5 | no_trades |
| #126 | Carry & Roll Yield Pack · Variant 9 | Carry Pack | SA701 + SA701-C-1000 | 1m | 0.00% | 0.00 | 0 | 17.5 | no_trades |
| #127 | Carry & Roll Yield Pack · Variant 10 | Carry Pack | SA701 + SA701-C-1000 | 1m | 0.00% | 0.00 | 0 | 17.5 | no_trades |
| #128 | Relative Value Pack · Variant 1 | Relative Value Pack | SA701 + SA701-C-1000 | 1m | 0.00% | 0.00 | 0 | 17.5 | no_trades |
| #129 | Relative Value Pack · Variant 2 | Relative Value Pack | SA701 + SA701-C-1000 | 1m | 0.00% | 0.00 | 0 | 17.5 | no_trades |
| #130 | Relative Value Pack · Variant 3 | Relative Value Pack | SA701 + SA701-C-1000 | 1m | 0.00% | 0.00 | 0 | 17.5 | no_trades |
| #131 | Relative Value Pack · Variant 4 | Relative Value Pack | SA701 + SA701-C-1000 | 1m | 0.00% | 0.00 | 0 | 17.5 | no_trades |
| #132 | Relative Value Pack · Variant 5 | Relative Value Pack | SA701 + SA701-C-1000 | 1m | 0.00% | 0.00 | 0 | 17.5 | no_trades |
| #133 | Relative Value Pack · Variant 6 | Relative Value Pack | SA701 + SA701-C-1000 | 1m | 0.00% | 0.00 | 0 | 17.5 | no_trades |
| #134 | Relative Value Pack · Variant 7 | Relative Value Pack | SA701 + SA701-C-1000 | 1m | 0.00% | 0.00 | 0 | 17.5 | no_trades |
| #135 | Relative Value Pack · Variant 8 | Relative Value Pack | SA701 + SA701-C-1000 | 1m | 0.00% | 0.00 | 0 | 17.5 | no_trades |
| #136 | Relative Value Pack · Variant 9 | Relative Value Pack | SA701 + SA701-C-1000 | 1m | 0.00% | 0.00 | 0 | 17.5 | no_trades |
| #137 | Relative Value Pack · Variant 10 | Relative Value Pack | SA701 + SA701-C-1000 | 1m | 0.00% | 0.00 | 0 | 17.5 | no_trades |
| #138 | Volatility Pack · Variant 1 | Volatility Pack | SA701 + SA701-C-1000 | 1m | 0.00% | 0.00 | 0 | 17.5 | no_trades |
| #139 | Volatility Pack · Variant 2 | Volatility Pack | SA701 + SA701-C-1000 | 1m | 0.00% | 0.00 | 0 | 17.5 | no_trades |
| #140 | Volatility Pack · Variant 3 | Volatility Pack | SA701 + SA701-C-1000 | 1m | 0.00% | 0.00 | 0 | 17.5 | no_trades |
| #141 | Volatility Pack · Variant 4 | Volatility Pack | SA701 + SA701-C-1000 | 1m | 0.00% | 0.00 | 0 | 17.5 | no_trades |
| #142 | Volatility Pack · Variant 5 | Volatility Pack | SA701 + SA701-C-1000 | 1m | 0.00% | 0.00 | 0 | 17.5 | no_trades |
| #143 | Volatility Pack · Variant 6 | Volatility Pack | SA701 + SA701-C-1000 | 1m | 0.00% | 0.00 | 0 | 17.5 | no_trades |
| #144 | Volatility Pack · Variant 7 | Volatility Pack | SA701 + SA701-C-1000 | 1m | 0.00% | 0.00 | 0 | 17.5 | no_trades |
| #145 | Volatility Pack · Variant 8 | Volatility Pack | SA701 + SA701-C-1000 | 1m | 0.00% | 0.00 | 0 | 17.5 | no_trades |
| #146 | Volatility Pack · Variant 9 | Volatility Pack | SA701 + SA701-C-1000 | 1m | 0.00% | 0.00 | 0 | 17.5 | no_trades |
| #147 | Volatility Pack · Variant 10 | Volatility Pack | SA701 + SA701-C-1000 | 1m | 0.00% | 0.00 | 0 | 17.5 | no_trades |
| #148 | Market Microstructure Pack · Variant 1 | Microstructure Pack | SA701 + SA701-C-1000 | 1m | 0.00% | 0.00 | 0 | 17.5 | no_trades |
| #149 | Market Microstructure Pack · Variant 2 | Microstructure Pack | SA701 + SA701-C-1000 | 1m | 0.00% | 0.00 | 0 | 17.5 | no_trades |
| #150 | Market Microstructure Pack · Variant 3 | Microstructure Pack | SA701 + SA701-C-1000 | 1m | 0.00% | 0.00 | 0 | 17.5 | no_trades |
| #151 | Market Microstructure Pack · Variant 4 | Microstructure Pack | SA701 + SA701-C-1000 | 1m | 0.00% | 0.00 | 0 | 17.5 | no_trades |
| #152 | Market Microstructure Pack · Variant 5 | Microstructure Pack | SA701 + SA701-C-1000 | 1m | 0.00% | 0.00 | 0 | 17.5 | no_trades |
| #153 | Market Microstructure Pack · Variant 6 | Microstructure Pack | SA701 + SA701-C-1000 | 1m | 0.00% | 0.00 | 0 | 17.5 | no_trades |
| #154 | Market Microstructure Pack · Variant 7 | Microstructure Pack | SA701 + SA701-C-1000 | 1m | 0.00% | 0.00 | 0 | 17.5 | no_trades |
| #155 | Market Microstructure Pack · Variant 8 | Microstructure Pack | SA701 + SA701-C-1000 | 1m | 0.00% | 0.00 | 0 | 17.5 | no_trades |
| #156 | Market Microstructure Pack · Variant 9 | Microstructure Pack | SA701 + SA701-C-1000 | 1m | 0.00% | 0.00 | 0 | 17.5 | no_trades |
| #157 | Market Microstructure Pack · Variant 10 | Microstructure Pack | SA701 + SA701-C-1000 | 1m | 0.00% | 0.00 | 0 | 17.5 | no_trades |
| #158 | Statistical Arbitrage Pack · Variant 1 | Stat Arb Pack | SA701 + SA701-C-1000 | 1m | 0.00% | 0.00 | 0 | 17.5 | no_trades |
| #159 | Statistical Arbitrage Pack · Variant 2 | Stat Arb Pack | SA701 + SA701-C-1000 | 1m | 0.00% | 0.00 | 0 | 17.5 | no_trades |
| #160 | Statistical Arbitrage Pack · Variant 3 | Stat Arb Pack | SA701 + SA701-C-1000 | 1m | 0.00% | 0.00 | 0 | 17.5 | no_trades |
| #161 | Statistical Arbitrage Pack · Variant 4 | Stat Arb Pack | SA701 + SA701-C-1000 | 1m | 0.00% | 0.00 | 0 | 17.5 | no_trades |
| #162 | Statistical Arbitrage Pack · Variant 5 | Stat Arb Pack | SA701 + SA701-C-1000 | 1m | 0.00% | 0.00 | 0 | 17.5 | no_trades |
| #163 | Statistical Arbitrage Pack · Variant 6 | Stat Arb Pack | SA701 + SA701-C-1000 | 1m | 0.00% | 0.00 | 0 | 17.5 | no_trades |
| #164 | Statistical Arbitrage Pack · Variant 7 | Stat Arb Pack | SA701 + SA701-C-1000 | 1m | 0.00% | 0.00 | 0 | 17.5 | no_trades |
| #165 | Statistical Arbitrage Pack · Variant 8 | Stat Arb Pack | SA701 + SA701-C-1000 | 1m | 0.00% | 0.00 | 0 | 17.5 | no_trades |
| #166 | Statistical Arbitrage Pack · Variant 9 | Stat Arb Pack | SA701 + SA701-C-1000 | 1m | 0.00% | 0.00 | 0 | 17.5 | no_trades |
| #167 | Statistical Arbitrage Pack · Variant 10 | Stat Arb Pack | SA701 + SA701-C-1000 | 1m | 0.00% | 0.00 | 0 | 17.5 | no_trades |
| #168 | Options Volatility Pack · Variant 1 | Volatility Pack | SA701 + SA701-C-1000 | 1m | 0.00% | 0.00 | 0 | 17.5 | no_trades |
| #169 | Options Volatility Pack · Variant 2 | Volatility Pack | SA701 + SA701-C-1000 | 1m | 0.00% | 0.00 | 0 | 17.5 | no_trades |
| #170 | Options Volatility Pack · Variant 3 | Volatility Pack | SA701 + SA701-C-1000 | 1m | 0.00% | 0.00 | 0 | 17.5 | no_trades |
| #171 | Options Volatility Pack · Variant 4 | Volatility Pack | SA701 + SA701-C-1000 | 1m | 0.00% | 0.00 | 0 | 17.5 | no_trades |
| #172 | Options Volatility Pack · Variant 5 | Volatility Pack | SA701 + SA701-C-1000 | 1m | 0.00% | 0.00 | 0 | 17.5 | no_trades |
| #173 | Options Volatility Pack · Variant 6 | Volatility Pack | SA701 + SA701-C-1000 | 1m | 0.00% | 0.00 | 0 | 17.5 | no_trades |
| #174 | Options Volatility Pack · Variant 7 | Volatility Pack | SA701 + SA701-C-1000 | 1m | 0.00% | 0.00 | 0 | 17.5 | no_trades |
| #175 | Options Volatility Pack · Variant 8 | Volatility Pack | SA701 + SA701-C-1000 | 1m | 0.00% | 0.00 | 0 | 17.5 | no_trades |
| #176 | Options Volatility Pack · Variant 9 | Volatility Pack | SA701 + SA701-C-1000 | 1m | 0.00% | 0.00 | 0 | 17.5 | no_trades |
| #177 | Options Volatility Pack · Variant 10 | Volatility Pack | SA701 + SA701-C-1000 | 1m | 0.00% | 0.00 | 0 | 17.5 | no_trades |
| #178 | Session Alpha Pack · Variant 1 | Session Alpha Pack | SA701 + SA701-C-1000 | 1m | 0.00% | 0.00 | 0 | 17.5 | no_trades |
| #179 | Session Alpha Pack · Variant 2 | Session Alpha Pack | SA701 + SA701-C-1000 | 1m | 0.00% | 0.00 | 0 | 17.5 | no_trades |
| #180 | Session Alpha Pack · Variant 3 | Session Alpha Pack | SA701 + SA701-C-1000 | 1m | 0.00% | 0.00 | 0 | 17.5 | no_trades |
| #181 | Session Alpha Pack · Variant 4 | Session Alpha Pack | SA701 + SA701-C-1000 | 1m | 0.00% | 0.00 | 0 | 17.5 | no_trades |
| #182 | Session Alpha Pack · Variant 5 | Session Alpha Pack | SA701 + SA701-C-1000 | 1m | 0.00% | 0.00 | 0 | 17.5 | no_trades |
| #183 | Session Alpha Pack · Variant 6 | Session Alpha Pack | SA701 + SA701-C-1000 | 1m | 0.00% | 0.00 | 0 | 17.5 | no_trades |
| #184 | Session Alpha Pack · Variant 7 | Session Alpha Pack | SA701 + SA701-C-1000 | 1m | 0.00% | 0.00 | 0 | 17.5 | no_trades |
| #185 | Session Alpha Pack · Variant 8 | Session Alpha Pack | SA701 + SA701-C-1000 | 1m | 0.00% | 0.00 | 0 | 17.5 | no_trades |
| #186 | Session Alpha Pack · Variant 9 | Session Alpha Pack | SA701 + SA701-C-1000 | 1m | 0.00% | 0.00 | 0 | 17.5 | no_trades |
| #187 | Session Alpha Pack · Variant 10 | Session Alpha Pack | SA701 + SA701-C-1000 | 1m | 0.00% | 0.00 | 0 | 17.5 | no_trades |
| #188 | Regime Switch Pack · Variant 1 | Regime Switch Pack | SA701 + SA701-C-1000 | 1m | 0.00% | 0.00 | 0 | 17.5 | no_trades |
| #189 | Regime Switch Pack · Variant 2 | Regime Switch Pack | SA701 + SA701-C-1000 | 1m | 0.00% | 0.00 | 0 | 17.5 | no_trades |
| #190 | Regime Switch Pack · Variant 3 | Regime Switch Pack | SA701 + SA701-C-1000 | 1m | 0.00% | 0.00 | 0 | 17.5 | no_trades |
| #191 | Regime Switch Pack · Variant 4 | Regime Switch Pack | SA701 + SA701-C-1000 | 1m | 0.00% | 0.00 | 0 | 17.5 | no_trades |
| #192 | Regime Switch Pack · Variant 5 | Regime Switch Pack | SA701 + SA701-C-1000 | 1m | 0.00% | 0.00 | 0 | 17.5 | no_trades |
| #193 | Regime Switch Pack · Variant 6 | Regime Switch Pack | SA701 + SA701-C-1000 | 1m | 0.00% | 0.00 | 0 | 17.5 | no_trades |
| #194 | Regime Switch Pack · Variant 7 | Regime Switch Pack | SA701 + SA701-C-1000 | 1m | 0.00% | 0.00 | 0 | 17.5 | no_trades |
| #195 | Regime Switch Pack · Variant 8 | Regime Switch Pack | SA701 + SA701-C-1000 | 1m | 0.00% | 0.00 | 0 | 17.5 | no_trades |
| #196 | Regime Switch Pack · Variant 9 | Regime Switch Pack | SA701 + SA701-C-1000 | 1m | 0.00% | 0.00 | 0 | 17.5 | no_trades |
| #197 | Regime Switch Pack · Variant 10 | Regime Switch Pack | SA701 + SA701-C-1000 | 1m | 0.00% | 0.00 | 0 | 17.5 | no_trades |
| #198 | Order Flow Proxy Pack · Variant 1 | Order Flow Pack | SA701 + SA701-C-1000 | 1m | 0.00% | 0.00 | 0 | 17.5 | no_trades |
| #199 | Order Flow Proxy Pack · Variant 2 | Order Flow Pack | SA701 + SA701-C-1000 | 1m | 0.00% | 0.00 | 0 | 17.5 | no_trades |
| #200 | Order Flow Proxy Pack · Variant 3 | Order Flow Pack | SA701 + SA701-C-1000 | 1m | 0.00% | 0.00 | 0 | 17.5 | no_trades |
| #201 | Order Flow Proxy Pack · Variant 4 | Order Flow Pack | SA701 + SA701-C-1000 | 1m | 0.00% | 0.00 | 0 | 17.5 | no_trades |
| #202 | Order Flow Proxy Pack · Variant 5 | Order Flow Pack | SA701 + SA701-C-1000 | 1m | 0.00% | 0.00 | 0 | 17.5 | no_trades |
| #203 | Order Flow Proxy Pack · Variant 6 | Order Flow Pack | SA701 + SA701-C-1000 | 1m | 0.00% | 0.00 | 0 | 17.5 | no_trades |
| #204 | Order Flow Proxy Pack · Variant 7 | Order Flow Pack | SA701 + SA701-C-1000 | 1m | 0.00% | 0.00 | 0 | 17.5 | no_trades |
| #205 | Order Flow Proxy Pack · Variant 8 | Order Flow Pack | SA701 + SA701-C-1000 | 1m | 0.00% | 0.00 | 0 | 17.5 | no_trades |
| #206 | Order Flow Proxy Pack · Variant 9 | Order Flow Pack | SA701 + SA701-C-1000 | 1m | 0.00% | 0.00 | 0 | 17.5 | no_trades |
| #207 | Order Flow Proxy Pack · Variant 10 | Order Flow Pack | SA701 + SA701-C-1000 | 1m | 0.00% | 0.00 | 0 | 17.5 | no_trades |
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
| #27 | SuperTrend | CTA Classic | USStock:SPY | 1d | -1.05% | -1.56 | 0 | 14.2 | no_trades |
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
