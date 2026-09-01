# GEX + LSP + Kelly Iron Condor Backtest (510050)

## Summary

- Initial capital: 1,000,000
- Final equity: 1,026,041.44
- Total return: 2.60%
- Annualized return: 6.69% (100 trading days)
- Sharpe: 2.152
- Max drawdown: -0.75%
- Trades: 4 (win rate 100.0%)
- Avg trade PnL: 6,510.36
- Sizing: kelly_defined_risk
- High-IV filter: False
- Short Δ band: 0.14–0.25 | min credit/width=0.15
- Wing steps: 3 | target DTE=45 | risk cap=0.06
- Take-profit=0.75 (credit captured) | stop-loss=0.9
- Trend filter: |20d return| > 8% sits out
- Listed chain: 2026-03-27 → 2026-08-31 (100 sessions, 232 contracts)
- Legs: each entry picks then-listed strikes via GEX-TV (no hardcoded codes)

## Rules

1. **GEX-TV pick**: 14–25Δ shorts **outside** GEX walls; prefer 3-step listed wings (min 2); credit/width ≥ 15%.
2. **Defined risk**: max loss ≈ (max wing − net credit) × multiplier × lots.
3. **Sizing**: min(lots, max_lots, 6% NAV / max_loss, Kelly cap 10%).
4. Skip adjusted *A strikes and missing quotes. IV-rank gate is off (short ETF samples).
5. **~45 DTE** entry (28–65), roll at 10 DTE; take-profit at 75% of credit captured.
6. **Exits**: short-strike flatten, TP, stop-loss, DTE roll. Walls are entry-only. Missing mid-hold quote → skip flatten.

## Trades

- 2026-04-01 → 2026-05-18 | K=2.7/2.8/3.1/3.2 | 50ETF沽5月2800/50ETF购5月3100 | lots=77/77 | credit=0.0231 | PnL=9,260.79 | roll_month
- 2026-05-19 → 2026-06-15 | K=2.8/2.9/3.2/3.3 | 50ETF沽6月2900/50ETF购6月3200 | lots=71/71 | credit=0.0157 | PnL=5,728.99 | roll_month
- 2026-06-15 → 2026-07-13 | K=2.8/2.9/3.2/3.3 | 50ETF沽7月2900/50ETF购7月3200 | lots=74/74 | credit=0.018 | PnL=3,051.02 | roll_month
- 2026-07-23 → 2026-08-17 | K=2.75/2.95/3.2/3.4 | 50ETF沽8月2950/50ETF购8月3200 | lots=36/36 | credit=0.0322 | PnL=8,000.64 | roll_month
