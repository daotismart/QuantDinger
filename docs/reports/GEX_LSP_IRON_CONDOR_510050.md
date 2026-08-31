# GEX + LSP + Kelly Iron Condor Backtest (510050)

## Summary

- Initial capital: 1,000,000
- Final equity: 1,142,389.60
- Total return: 14.24%
- Annualized return: 45.17% (90 trading days)
- Sharpe: 1.683
- Max drawdown: -2.94%
- Trades: 7 (win rate 28.6%)
- Avg trade PnL: 20,341.37
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

- 2026-04-01 → 2026-04-15 | K=2.8/2.85/3.0/3.1 | lots=120/120 | credit=0.0375 | PnL=-16,278.00 | short_call_breach
- 2026-04-15 → 2026-04-29 | K=2.8/2.85/3.1/3.2 | lots=120/120 | credit=0.0199 | PnL=156,679.20 | take_profit
- 2026-04-29 → 2026-06-11 | K=2.825/2.85/3.2/3.215 | lots=120/120 | credit=0.0052 | PnL=-3,746.40 | roll_month
- 2026-06-11 → 2026-07-07 | K=2.75/2.8/3.1/3.2 | lots=120/120 | credit=0.0151 | PnL=-3,954.00 | roll_month
- 2026-07-07 → 2026-08-04 | K=2.8/2.85/3.1/3.2 | lots=120/120 | credit=0.0321 | PnL=13,736.40 | take_profit
- 2026-08-04 → 2026-08-12 | K=2.65/2.7/3.5/3.6 | lots=120/120 | credit=0.0038 | PnL=-2,786.40 | take_profit
- 2026-08-12 → 2026-08-28 | K=2.85/2.9/3.5/3.6 | lots=120/120 | credit=0.0089 | PnL=-1,261.20 | eod_force_close
