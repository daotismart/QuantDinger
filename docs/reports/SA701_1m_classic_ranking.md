# SA701 1m 全策略回测排名

- 批次 tag：`SA701-1M-20260601`
- 标的：`CNFutures:SA701`（期权腿 `CNFuturesOptions:SA701-C-1000`，仅 Pack）
- 样本数：82；有成交：8；正收益：1
- 评分：收益40% + Sharpe25% + 回撤20% + 盈亏比10% + 有成交5%；零成交×0.35；极端异常×0.25
- 基本面多因子美股策略在单品种期货上标记为 not_applicable

## Top 15

| 排名 | 得分 | 策略 | 收益 | 回撤 | Sharpe | 成交 | 标记 |
|------|------|------|------|------|--------|------|------|
| 1 | 83.8 | Momentum Top-N Rotation | 175.00% | -32.36% | 5.20 | 1 | ok/ok |
| 2 | 40.7 | SuperTrend | -2.39% | -5.70% | -2.67 | 25 | ok/ok |
| 3 | 39.7 | Indicator Resonance | -3.71% | -4.49% | -12.36 | 62 | ok/ok |
| 4 | 35.5 | Single Moving Average | -6.44% | -7.80% | -11.68 | 97 | ok/ok |
| 5 | 33.4 | Turtle Trading | -22.25% | -2.98% | -0.26 | 31 | ok/ok |
| 6 | 31.3 | Low Volatility Rotation | -30.41% | -3.64% | -0.37 | 1 | ok/ok |
| 7 | 27.2 | Dual Moving Average | -189.95% | -15.09% | -0.41 | 84 | ok/ok |
| 8 | 24.8 | MACD and KDJ Confirmation | -12.57% | -17.19% | -5.07 | 127 | ok/ok |
| 9 | 17.5 | Breakout & Momentum Pack · V1 | 0.00% | 0.00% | 0.00 | 0 | no_trades/ok |
| 10 | 17.5 | Breakout & Momentum Pack · V2 | 0.00% | 0.00% | 0.00 | 0 | no_trades/ok |
| 11 | 17.5 | Breakout & Momentum Pack · V3 | 0.00% | 0.00% | 0.00 | 0 | no_trades/ok |
| 12 | 17.5 | Breakout & Momentum Pack · V4 | 0.00% | 0.00% | 0.00 | 0 | no_trades/ok |
| 13 | 17.5 | Breakout & Momentum Pack · V5 | 0.00% | 0.00% | 0.00 | 0 | no_trades/ok |
| 14 | 17.5 | Breakout & Momentum Pack · V6 | 0.00% | 0.00% | 0.00 | 0 | no_trades/ok |
| 15 | 17.5 | Breakout & Momentum Pack · V7 | 0.00% | 0.00% | 0.00 | 0 | no_trades/ok |

## 有成交排名

| 排名 | 得分 | 策略 | 收益 | 回撤 | Sharpe | 盈亏比 | 成交 |
|------|------|------|------|------|--------|--------|------|
| 1 | 83.8 | Momentum Top-N Rotation | 175.00% | -32.36% | 5.20 | 1750.01 | 1 |
| 2 | 40.7 | SuperTrend | -2.39% | -5.70% | -2.67 | 0.45 | 25 |
| 3 | 39.7 | Indicator Resonance | -3.71% | -4.49% | -12.36 | 0.35 | 62 |
| 4 | 35.5 | Single Moving Average | -6.44% | -7.80% | -11.68 | 0.43 | 97 |
| 5 | 33.4 | Turtle Trading | -22.25% | -2.98% | -0.26 | 0.62 | 31 |
| 6 | 31.3 | Low Volatility Rotation | -30.41% | -3.64% | -0.37 | 0.00 | 1 |
| 7 | 27.2 | Dual Moving Average | -189.95% | -15.09% | -0.41 | 0.92 | 84 |
| 8 | 24.8 | MACD and KDJ Confirmation | -12.57% | -17.19% | -5.07 | 0.50 | 127 |
