# GEX + LSP + Kelly Iron Condor Backtest (588000)

## Summary

- Initial capital: 1,000,000
- Final equity: 795,092.80
- Total return: -20.49%
- Annualized return: -47.38% (90 trading days)
- Sharpe: -5.356
- Max drawdown: -20.69%
- Trades: 11 (win rate 0.0%)
- Avg trade PnL: -18,627.93
- Sizing: fixed_lots
- High-IV filter: False
- Short OTM: 0.0 | min credit/width=0.0
- Wing steps: 1 | take-profit=0.5 | stop-loss=0.9
- Trend filter: |20d return| > 8% sits out

## Rules

1. **GEX walls**: short call/put near walls; buy 1-step further-OTM wings.
2. **Defined risk**: max loss ≈ (max wing − net credit) × multiplier × lots.
3. **Sizing**: default fixed 120 lots on 1M (margin per lot is small); optional Kelly.
4. **Filters off by default**: high-IV and inside-wall gates skipped so the book stays in the market.
5. **Trend filter**: flatten/skip when |spot return| over 20 sessions exceeds 8%.
6. **Exits**: short-strike / wall breach, take-profit, stop-loss, DTE roll, max hold.

## Trades

- 2026-04-01 → 2026-04-27 | K=1.15/1.2/1.55/1.6 | lots=120/120 | credit=0.0102 | PnL=-28,372.80 | short_call_breach
- 2026-04-27 → 2026-04-28 | K=1.4/1.45/1.8/1.85 | lots=120/120 | credit=0.0157 | PnL=-8,901.60 | trend_filter
- 2026-06-11 → 2026-06-12 | K=1.65/1.7/1.8/1.85 | lots=120/120 | credit=0.0384 | PnL=-16,689.60 | stop_loss
- 2026-06-12 → 2026-06-18 | K=1.65/1.7/1.95/2.0 | lots=120/120 | credit=0.0289 | PnL=-38,677.20 | short_call_breach
- 2026-06-23 → 2026-06-24 | K=1.95/2.0/2.15/2.2 | lots=120/120 | credit=0.0379 | PnL=-18,434.40 | stop_loss
- 2026-06-24 → 2026-06-25 | K=1.95/2.0/2.1/2.15 | lots=120/120 | credit=0.0394 | PnL=-22,365.60 | short_call_breach
- 2026-07-16 → 2026-07-17 | K=1.85/1.9/2.5/2.55 | lots=120/120 | credit=0.0276 | PnL=-28,414.80 | short_put_breach
- 2026-07-21 → 2026-07-23 | K=1.85/1.9/2.5/2.55 | lots=120/120 | credit=0.0237 | PnL=-21,830.40 | short_put_breach
- 2026-08-13 → 2026-08-19 | K=1.1/1.15/2.5/2.55 | lots=120/120 | credit=0.0012 | PnL=-6,136.80 | trend_filter
- 2026-08-20 → 2026-08-24 | K=1.1/1.15/1.8/1.85 | lots=120/120 | credit=0.0175 | PnL=-170.40 | trend_filter
- 2026-08-25 → 2026-08-28 | K=1.1/1.15/1.8/1.85 | lots=120/120 | credit=0.0103 | PnL=-14,913.60 | eod_force_close
