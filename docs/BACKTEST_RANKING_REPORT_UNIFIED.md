# QuantDinger 回测综合排名与分析报告

- 生成时间：2026-08-20 13:30 UTC
- 数据来源：`qd_backtest_runs`（**128** 条）
- 去重后策略样本：**128**（同名+同周期保留最高分）
- 评分：收益 40% + Sharpe 25% + 回撤 20% + 盈亏比 10% + 有成交 5%；极端异常值×0.25，零成交×0.35
- 指标已统一为小数收益率（自动识别历史百分比口径）
- 过滤条件：tag=`UNIFIED-20260820`

---

## 1. 执行摘要

| 项目 | 数值 |
|------|------|
| 回测总数 | 128 |
| 去重策略数 | 128 |
| 有成交（去重） | 6 |
| 零成交（去重） | 122 |
| 策略族 | 13 |
| 综合第 1（去重） | **Dual Moving Average**（#80，得分 82.03，收益 12.11%） |
| 有成交且正收益 | 3 / 6 |

### 核心结论

1. **可交易样本榜首**：`Dual Moving Average`（得分 82.03，收益 12.11%，回撤 -7.46%，Sharpe 1.78）。
2. **策略族均值最高**：`US Portfolio`（平均得分 58.8，有成交 4/4）。
3. **零成交 Pack**：Breakout Pack, Carry Pack, Mean Reversion Pack, Microstructure Pack, Order Flow Pack — 回测链路成功但未触发交易，通常是分钟线深度/合约符号不足（如 `SA701`）。

## 2. 综合排名（去重 Top 15）

| 排名 | 得分 | 策略 | 族 | Run | 周期 | 总收益 | 最大回撤 | Sharpe | 胜率 | 成交 | 标记 |
|------|------|------|----|-----|------|--------|----------|--------|------|------|------|
| 1 | 82.0 | Dual Moving Average | CTA Classic | #80 | 4h | 12.11% | -7.46% | 1.78 | 50.00% | 6 | ok |
| 2 | 80.8 | Small and Large Cap Barbell | US Portfolio | #84 | 1d | 7.33% | -7.44% | 2.44 | 76.47% | 17 | ok |
| 3 | 69.5 | Low Volatility Rotation | US Portfolio | #86 | 1d | 6.45% | -4.76% | 1.86 | 87.50% | 16 | ok |
| 4 | 58.6 | Quality Growth Multi-Factor | US Portfolio | #87 | 1d | -0.74% | -12.32% | 0.10 | 53.85% | 13 | ok |
| 5 | 35.9 | MACD and KDJ Confirmation | CTA Classic | #83 | 4h | -5.97% | -8.37% | -2.13 | 36.36% | 33 | ok |
| 6 | 26.4 | Momentum Top-N Rotation | US Portfolio | #85 | 1d | -11.50% | -14.42% | -2.23 | 54.55% | 22 | ok |
| 7 | 17.5 | Bullish Candle Through Three Averages | CTA Classic | #81 | 1d | 0.00% | 0.00% | 0.00 | 0.00% | 0 | no_trades |
| 8 | 17.5 | Bullish Three Averages With Trend Filter | CTA Classic | #82 | 1d | 0.00% | 0.00% | 0.00 | 0.00% | 0 | no_trades |
| 9 | 17.5 | Trend Following Pack · Variant 1 | Trend Pack | #88 | 1m | 0.00% | 0.00% | 0.00 | 0.00% | 0 | no_trades |
| 10 | 17.5 | Trend Following Pack · Variant 2 | Trend Pack | #89 | 1m | 0.00% | 0.00% | 0.00 | 0.00% | 0 | no_trades |
| 11 | 17.5 | Trend Following Pack · Variant 3 | Trend Pack | #90 | 1m | 0.00% | 0.00% | 0.00 | 0.00% | 0 | no_trades |
| 12 | 17.5 | Trend Following Pack · Variant 4 | Trend Pack | #91 | 1m | 0.00% | 0.00% | 0.00 | 0.00% | 0 | no_trades |
| 13 | 17.5 | Trend Following Pack · Variant 5 | Trend Pack | #92 | 1m | 0.00% | 0.00% | 0.00 | 0.00% | 0 | no_trades |
| 14 | 17.5 | Trend Following Pack · Variant 6 | Trend Pack | #93 | 1m | 0.00% | 0.00% | 0.00 | 0.00% | 0 | no_trades |
| 15 | 17.5 | Trend Following Pack · Variant 7 | Trend Pack | #94 | 1m | 0.00% | 0.00% | 0.00 | 0.00% | 0 | no_trades |

## 3. 有成交策略排名（去重）

| 排名 | 得分 | 策略 | 族 | 总收益 | 回撤 | Sharpe | 盈亏比 | 成交 | Run |
|------|------|------|----|--------|------|--------|--------|------|-----|
| 1 | 82.0 | Dual Moving Average | CTA Classic | 12.11% | -7.46% | 1.78 | 4.88 | 6 | #80 |
| 2 | 80.8 | Small and Large Cap Barbell | US Portfolio | 7.33% | -7.44% | 2.44 | 18.09 | 17 | #84 |
| 3 | 69.5 | Low Volatility Rotation | US Portfolio | 6.45% | -4.76% | 1.86 | 0.54 | 16 | #86 |
| 4 | 58.6 | Quality Growth Multi-Factor | US Portfolio | -0.74% | -12.32% | 0.10 | 6.17 | 13 | #87 |
| 5 | 35.9 | MACD and KDJ Confirmation | CTA Classic | -5.97% | -8.37% | -2.13 | 0.54 | 33 | #83 |
| 6 | 26.4 | Momentum Top-N Rotation | US Portfolio | -11.50% | -14.42% | -2.23 | 0.07 | 22 | #85 |

## 4. 策略族排行榜

| 排名 | 策略族 | 策略数 | 有成交 | 平均得分 | 平均收益* | 总成交 | 族内最佳 |
|------|--------|--------|--------|----------|-----------|--------|----------|
| 1 | US Portfolio | 4 | 4 | 58.8 | 0.39% | 68 | Small and Large Cap Barbell (#84) |
| 2 | CTA Classic | 4 | 2 | 38.2 | 3.07% | 39 | Dual Moving Average (#80) |
| 3 | Breakout Pack | 10 | 0 | 17.5 | 0.00% | 0 | Breakout & Momentum Pack · Variant 1 (#98) |
| 4 | Carry Pack | 10 | 0 | 17.5 | 0.00% | 0 | Carry & Roll Yield Pack · Variant 1 (#118) |
| 5 | Mean Reversion Pack | 10 | 0 | 17.5 | 0.00% | 0 | Mean Reversion Pack · Variant 1 (#108) |
| 6 | Microstructure Pack | 10 | 0 | 17.5 | 0.00% | 0 | Market Microstructure Pack · Variant 1 (#148) |
| 7 | Order Flow Pack | 10 | 0 | 17.5 | 0.00% | 0 | Order Flow Proxy Pack · Variant 1 (#198) |
| 8 | Regime Switch Pack | 10 | 0 | 17.5 | 0.00% | 0 | Regime Switch Pack · Variant 1 (#188) |
| 9 | Relative Value Pack | 10 | 0 | 17.5 | 0.00% | 0 | Relative Value Pack · Variant 1 (#128) |
| 10 | Session Alpha Pack | 10 | 0 | 17.5 | 0.00% | 0 | Session Alpha Pack · Variant 1 (#178) |
| 11 | Stat Arb Pack | 10 | 0 | 17.5 | 0.00% | 0 | Statistical Arbitrage Pack · Variant 1 (#158) |
| 12 | Trend Pack | 10 | 0 | 17.5 | 0.00% | 0 | Trend Following Pack · Variant 1 (#88) |
| 13 | Volatility Pack | 20 | 0 | 17.5 | 0.00% | 0 | Volatility Pack · Variant 1 (#138) |

\*平均收益仅统计有成交样本。

## 5. 方法说明与限制

- 跨族不可直接比绝对收益：标的、周期、资金、费率可能不同。
- 同策略重复回测时，总榜以去重结果为主；附录保留全量。
- Pack 依赖国内期货分钟线与期权合约键；连续合约 `SA0` 与月份码 `SA701` 不是同一符号。

## 附录 A：全量回测清单（按得分）

| Run | 策略 | 族 | 标的 | 周期 | 收益 | Sharpe | 成交 | 得分 | 标记 |
|-----|------|----|------|------|------|--------|------|------|------|
| #80 | Dual Moving Average | CTA Classic | Crypto:BTC/USDT | 4h | 12.11% | 1.78 | 6 | 82.0 | ok |
| #84 | Small and Large Cap Barbell | US Portfolio | AAPL + MSFT + NVDA + AMZN + META + GOOG… | 1d | 7.33% | 2.44 | 17 | 80.8 | ok |
| #86 | Low Volatility Rotation | US Portfolio | AAPL + MSFT + NVDA + AMZN + META + GOOG… | 1d | 6.45% | 1.86 | 16 | 69.5 | ok |
| #87 | Quality Growth Multi-Factor | US Portfolio | AAPL + MSFT + NVDA + AMZN + META + GOOG… | 1d | -0.74% | 0.10 | 13 | 58.6 | ok |
| #83 | MACD and KDJ Confirmation | CTA Classic | Crypto:BTC/USDT | 4h | -5.97% | -2.13 | 33 | 35.9 | ok |
| #85 | Momentum Top-N Rotation | US Portfolio | AAPL + MSFT + NVDA + AMZN + META + GOOG… | 1d | -11.50% | -2.23 | 22 | 26.4 | ok |
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
