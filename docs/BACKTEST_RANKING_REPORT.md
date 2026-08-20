# QuantDinger 回测综合排名与分析报告

- 生成时间：2026-08-20 13:30 UTC
- 数据来源：`qd_backtest_runs`（**207** 条）
- 去重后策略样本：**135**（同名+同周期保留最高分）
- 评分：收益 40% + Sharpe 25% + 回撤 20% + 盈亏比 10% + 有成交 5%；极端异常值×0.25，零成交×0.35
- 指标已统一为小数收益率（自动识别历史百分比口径）
- 过滤条件：全部成功回测

---

## 1. 执行摘要

| 项目 | 数值 |
|------|------|
| 回测总数 | 207 |
| 去重策略数 | 135 |
| 有成交（去重） | 11 |
| 零成交（去重） | 124 |
| 策略族 | 14 |
| 综合第 1（去重） | **Dual Moving Average**（#5，得分 82.77，收益 12.38%） |
| 有成交且正收益 | 5 / 11 |

### 核心结论

1. **可交易样本榜首**：`Dual Moving Average`（得分 82.77，收益 12.38%，回撤 -7.35%，Sharpe 1.81）。
2. **策略族均值最高**：`US Portfolio`（平均得分 64.6，有成交 4/4）。
3. **零成交 Pack**：Breakout Pack, Carry Pack, Mean Reversion Pack, Microstructure Pack, Order Flow Pack — 回测链路成功但未触发交易，通常是分钟线深度/合约符号不足（如 `SA701`）。
4. **极端异常值 1 个**已降权，不作为可信 alpha 依据。

## 2. 综合排名（去重 Top 15）

| 排名 | 得分 | 策略 | 族 | Run | 周期 | 总收益 | 最大回撤 | Sharpe | 胜率 | 成交 | 标记 |
|------|------|------|----|-----|------|--------|----------|--------|------|------|------|
| 1 | 82.8 | Dual Moving Average | CTA Classic | #5 | 4h | 12.38% | -7.35% | 1.81 | 50.00% | 6 | ok |
| 2 | 81.3 | Quality Growth Multi-Factor | US Portfolio | #28 | 1d | 7.49% | -7.44% | 2.51 | 73.68% | 19 | ok |
| 3 | 80.8 | Small and Large Cap Barbell | US Portfolio | #84 | 1d | 7.33% | -7.44% | 2.44 | 76.47% | 17 | ok |
| 4 | 69.9 | Low Volatility Rotation | US Portfolio | #11 | 1d | 6.61% | -4.75% | 1.92 | 82.35% | 17 | ok |
| 5 | 51.1 | Indicator Resonance | CTA Classic | #26 | 1d | -0.44% | -1.54% | -0.55 | 0.00% | 1 | ok |
| 6 | 50.7 | Single Moving Average | CTA Classic | #24 | 1d | -0.99% | -4.12% | -0.33 | 33.33% | 3 | ok |
| 7 | 43.0 | AS Options Market Maker | AS Options MM | #3 | 1m | -0.04% | -4.02% | -17.09 | 2.00% | 50 | ok |
| 8 | 39.4 | MACD and KDJ Confirmation | CTA Classic | #9 | 4h | -4.77% | -7.32% | -1.68 | 39.39% | 33 | ok |
| 9 | 38.3 | AS Options Market Maker | AS Options MM | #1 | 5m | -0.15% | -14.79% | -3.02 | 39.60% | 399 | ok |
| 10 | 26.4 | Momentum Top-N Rotation | US Portfolio | #85 | 1d | -11.50% | -14.42% | -2.23 | 54.55% | 22 | ok |
| 11 | 22.4 | AS Options Market Maker(SA2701) | AS Options MM | #4 | 1m | 21.59% | -20.81% | 46.40 | 100.00% | 247 | extreme_outlier |
| 12 | 19.3 | Turtle Trading | CTA Classic | #25 | 1d | 0.82% | -1.27% | 1.00 | 0.00% | 0 | no_trades |
| 13 | 17.5 | Bullish Candle Through Three Averages | CTA Classic | #7 | 1d | 0.00% | 0.00% | 0.00 | 0.00% | 0 | no_trades |
| 14 | 17.5 | Bullish Three Averages With Trend Filter | CTA Classic | #8 | 1d | 0.00% | 0.00% | 0.00 | 0.00% | 0 | no_trades |
| 15 | 17.5 | Statistical Arbitrage Pack · Variant 1 | Stat Arb Pack | #30 | 1m | 0.00% | 0.00% | 0.00 | 0.00% | 0 | no_trades |

## 3. 有成交策略排名（去重）

| 排名 | 得分 | 策略 | 族 | 总收益 | 回撤 | Sharpe | 盈亏比 | 成交 | Run |
|------|------|------|----|--------|------|--------|--------|------|-----|
| 1 | 82.8 | Dual Moving Average | CTA Classic | 12.38% | -7.35% | 1.81 | 5.08 | 6 | #5 |
| 2 | 81.3 | Quality Growth Multi-Factor | US Portfolio | 7.49% | -7.44% | 2.51 | 16.03 | 19 | #28 |
| 3 | 80.8 | Small and Large Cap Barbell | US Portfolio | 7.33% | -7.44% | 2.44 | 18.09 | 17 | #84 |
| 4 | 69.9 | Low Volatility Rotation | US Portfolio | 6.61% | -4.75% | 1.92 | 0.55 | 17 | #11 |
| 5 | 51.1 | Indicator Resonance | CTA Classic | -0.44% | -1.54% | -0.55 | 0.00 | 1 | #26 |
| 6 | 50.7 | Single Moving Average | CTA Classic | -0.99% | -4.12% | -0.33 | 0.17 | 3 | #24 |
| 7 | 43.0 | AS Options Market Maker | AS Options MM | -0.04% | -4.02% | -17.09 | 0.02 | 50 | #3 |
| 8 | 39.4 | MACD and KDJ Confirmation | CTA Classic | -4.77% | -7.32% | -1.68 | 0.62 | 33 | #9 |
| 9 | 38.3 | AS Options Market Maker | AS Options MM | -0.15% | -14.79% | -3.02 | 0.42 | 399 | #1 |
| 10 | 26.4 | Momentum Top-N Rotation | US Portfolio | -11.50% | -14.42% | -2.23 | 0.07 | 22 | #85 |
| 11 | 22.4 | AS Options Market Maker(SA2701) | AS Options MM | 21.59% | -20.81% | 46.40 | 2159.10 | 247 | #4 |

## 4. 策略族排行榜

| 排名 | 策略族 | 策略数 | 有成交 | 平均得分 | 平均收益* | 总成交 | 族内最佳 |
|------|--------|--------|--------|----------|-----------|--------|----------|
| 1 | US Portfolio | 4 | 4 | 64.6 | 2.48% | 75 | Quality Growth Multi-Factor (#28) |
| 2 | CTA Classic | 8 | 4 | 36.5 | 1.55% | 43 | Dual Moving Average (#5) |
| 3 | AS Options MM | 3 | 3 | 34.6 | 7.14% | 696 | AS Options Market Maker (#3) |
| 4 | Breakout Pack | 10 | 0 | 17.5 | 0.00% | 0 | Breakout & Momentum Pack · Variant 1 (#98) |
| 5 | Carry Pack | 10 | 0 | 17.5 | 0.00% | 0 | Carry & Roll Yield Pack · Variant 1 (#118) |
| 6 | Mean Reversion Pack | 10 | 0 | 17.5 | 0.00% | 0 | Mean Reversion Pack · Variant 1 (#108) |
| 7 | Microstructure Pack | 10 | 0 | 17.5 | 0.00% | 0 | Market Microstructure Pack · Variant 1 (#148) |
| 8 | Order Flow Pack | 10 | 0 | 17.5 | 0.00% | 0 | Order Flow Proxy Pack · Variant 1 (#70) |
| 9 | Regime Switch Pack | 10 | 0 | 17.5 | 0.00% | 0 | Regime Switch Pack · Variant 1 (#60) |
| 10 | Relative Value Pack | 10 | 0 | 17.5 | 0.00% | 0 | Relative Value Pack · Variant 1 (#128) |
| 11 | Session Alpha Pack | 10 | 0 | 17.5 | 0.00% | 0 | Session Alpha Pack · Variant 1 (#50) |
| 12 | Stat Arb Pack | 10 | 0 | 17.5 | 0.00% | 0 | Statistical Arbitrage Pack · Variant 1 (#30) |
| 13 | Trend Pack | 10 | 0 | 17.5 | 0.00% | 0 | Trend Following Pack · Variant 1 (#88) |
| 14 | Volatility Pack | 20 | 0 | 17.5 | 0.00% | 0 | Options Volatility Pack · Variant 1 (#40) |

\*平均收益仅统计有成交样本。

## 5. 方法说明与限制

- 跨族不可直接比绝对收益：标的、周期、资金、费率可能不同。
- 同策略重复回测时，总榜以去重结果为主；附录保留全量。
- Pack 依赖国内期货分钟线与期权合约键；连续合约 `SA0` 与月份码 `SA701` 不是同一符号。

## 附录 A：全量回测清单（按得分）

| Run | 策略 | 族 | 标的 | 周期 | 收益 | Sharpe | 成交 | 得分 | 标记 |
|-----|------|----|------|------|------|--------|------|------|------|
| #5 | Dual Moving Average | CTA Classic | Crypto:BTC/USDT | 4h | 12.38% | 1.81 | 6 | 82.8 | ok |
| #6 | Dual Moving Average | CTA Classic | Crypto:BTC/USDT | 4h | 12.38% | 1.81 | 6 | 82.8 | ok |
| #12 | Dual Moving Average | CTA Classic | Crypto:BTC/USDT | 4h | 12.38% | 1.81 | 6 | 82.8 | ok |
| #18 | Dual Moving Average | CTA Classic | Crypto:BTC/USDT | 4h | 12.38% | 1.81 | 6 | 82.8 | ok |
| #80 | Dual Moving Average | CTA Classic | Crypto:BTC/USDT | 4h | 12.11% | 1.78 | 6 | 82.0 | ok |
| #28 | Quality Growth Multi-Factor | US Portfolio | AAPL + MSFT + NVDA + AMZN + META + GOOG… | 1d | 7.49% | 2.51 | 19 | 81.3 | ok |
| #84 | Small and Large Cap Barbell | US Portfolio | AAPL + MSFT + NVDA + AMZN + META + GOOG… | 1d | 7.33% | 2.44 | 17 | 80.8 | ok |
| #11 | Low Volatility Rotation | US Portfolio | AAPL + MSFT + NVDA + AMZN + META + GOOG… | 1d | 6.61% | 1.92 | 17 | 69.9 | ok |
| #17 | Low Volatility Rotation | US Portfolio | AAPL + MSFT + NVDA + AMZN + META + GOOG… | 1d | 6.61% | 1.92 | 17 | 69.9 | ok |
| #23 | Low Volatility Rotation | US Portfolio | AAPL + MSFT + NVDA + AMZN + META + GOOG… | 1d | 6.61% | 1.92 | 17 | 69.9 | ok |
| #86 | Low Volatility Rotation | US Portfolio | AAPL + MSFT + NVDA + AMZN + META + GOOG… | 1d | 6.45% | 1.86 | 16 | 69.5 | ok |
| #87 | Quality Growth Multi-Factor | US Portfolio | AAPL + MSFT + NVDA + AMZN + META + GOOG… | 1d | -0.74% | 0.10 | 13 | 58.6 | ok |
| #29 | Small and Large Cap Barbell | US Portfolio | AAPL + MSFT + NVDA + AMZN + META + GOOG… | 1d | -1.20% | 0.00 | 13 | 57.6 | ok |
| #26 | Indicator Resonance | CTA Classic | USStock:QQQ | 1d | -0.44% | -0.55 | 1 | 51.1 | ok |
| #24 | Single Moving Average | CTA Classic | USStock:SPY | 1d | -0.99% | -0.33 | 3 | 50.7 | ok |
| #3 | AS Options Market Maker | AS Options MM | M2610-C-1000 + SA2610 | 1m | -0.04% | -17.09 | 50 | 43.0 | ok |
| #9 | MACD and KDJ Confirmation | CTA Classic | Crypto:BTC/USDT | 4h | -4.77% | -1.68 | 33 | 39.4 | ok |
| #15 | MACD and KDJ Confirmation | CTA Classic | Crypto:BTC/USDT | 4h | -4.77% | -1.68 | 33 | 39.4 | ok |
| #21 | MACD and KDJ Confirmation | CTA Classic | Crypto:BTC/USDT | 4h | -4.77% | -1.68 | 33 | 39.4 | ok |
| #1 | AS Options Market Maker | AS Options MM | M2609-C-2800 + M2609 | 5m | -0.15% | -3.02 | 399 | 38.3 | ok |
| #83 | MACD and KDJ Confirmation | CTA Classic | Crypto:BTC/USDT | 4h | -5.97% | -2.13 | 33 | 35.9 | ok |
| #85 | Momentum Top-N Rotation | US Portfolio | AAPL + MSFT + NVDA + AMZN + META + GOOG… | 1d | -11.50% | -2.23 | 22 | 26.4 | ok |
| #10 | Momentum Top-N Rotation | US Portfolio | AAPL + MSFT + NVDA + AMZN + META + GOOG… | 1d | -11.52% | -2.25 | 19 | 26.4 | ok |
| #16 | Momentum Top-N Rotation | US Portfolio | AAPL + MSFT + NVDA + AMZN + META + GOOG… | 1d | -11.52% | -2.25 | 19 | 26.4 | ok |
| #22 | Momentum Top-N Rotation | US Portfolio | AAPL + MSFT + NVDA + AMZN + META + GOOG… | 1d | -11.52% | -2.25 | 19 | 26.4 | ok |
| #4 | AS Options Market Maker(SA2701) | AS Options MM | SA2701-C-1000 + SA2701 | 1m | 21.59% | 46.40 | 247 | 22.4 | extreme_outlier |
| #2 | AS Options Market Maker | AS Options MM | M2610-C-1000 + SA2610 | 1m | 33.79% | 35.04 | 246 | 21.0 | extreme_outlier |
| #25 | Turtle Trading | CTA Classic | USStock:SPY | 1d | 0.82% | 1.00 | 0 | 19.3 | no_trades |
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
| #27 | SuperTrend | CTA Classic | USStock:SPY | 1d | -1.05% | -1.56 | 0 | 14.2 | no_trades |
