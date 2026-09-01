# GEX + LSP + Kelly Iron Condor Backtest (510050)

## Summary

- Initial capital: 1,000,000
- Final equity: 978,659.54
- Total return: -2.13%
- Annualized return: -5.29% (100 trading days)
- Sharpe: -1.730
- Max drawdown: -2.40%
- Trades: 2 (win rate 0.0%)
- Avg trade PnL: -10,670.23
- Sizing: kelly_defined_risk
- High-IV filter: True
- Short Δ band: 0.14–0.25 | min credit/width=0.2
- Wing steps: 3 | target DTE=45 | risk cap=0.06
- Take-profit=0.75 (credit captured) | stop-loss=0.9
- Trend filter: |20d return| > 8% sits out
- Listed chain: 2026-03-27 → 2026-08-31 (100 sessions, 232 contracts)
- Legs: each entry picks then-listed strikes via GEX-TV (no hardcoded codes)

## Rules

1. **GEX-TV pick**: 14–25Δ shorts **outside** GEX walls; prefer 3-step listed wings (min 2); credit/width ≥ 20%.
2. **Defined risk**: max loss ≈ (max wing − net credit) × multiplier × lots.
3. **Sizing**: min(lots, max_lots, 6% NAV / max_loss, Kelly cap 10%).
4. **IV Rank ≥ 40** (0–1 = 0.40) to sell; skip adjusted *A strikes and missing quotes.
5. **~45 DTE** entry (28–65), roll at 21 DTE; take-profit at 75% of credit captured.
6. **Exits**: short-strike / wall breach, TP, stop-loss, DTE roll, max hold. Missing leg quote → do not flatten.

## Trades

- 2026-04-30 → 2026-06-11 | K=2.85/2.95/3.2/3.3 | 50ETF沽6月2950/50ETF购6月3200 | lots=80/80 | credit=0.0271 | PnL=-11,469.60 | roll_month
- 2026-06-11 → 2026-07-01 | K=2.7/2.8/3.1/3.2 | 50ETF沽7月2800/50ETF购7月3100 | lots=74/74 | credit=0.0206 | PnL=-9,870.86 | roll_month
