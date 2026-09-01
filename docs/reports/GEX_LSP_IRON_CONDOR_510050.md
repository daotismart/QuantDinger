# GEX + LSP + Kelly Iron Condor Backtest (510050)

## Summary

- Initial capital: 1,000,000
- Final equity: 986,839.60
- Total return: -1.32%
- Annualized return: -3.28% (100 trading days)
- Sharpe: -0.042
- Max drawdown: -5.48%
- Trades: 8 (win rate 25.0%)
- Avg trade PnL: -1,645.05
- Sizing: fixed_lots
- High-IV filter: False
- Short OTM: 0.0 | min credit/width=0.0
- Wing steps: 1 | take-profit=0.5 | stop-loss=0.9
- Trend filter: |20d return| > 8% sits out
- Listed chain: 2026-03-27 → 2026-08-31 (100 sessions, 232 contracts)
- Legs: each entry picks then-listed 次月 strikes via GEX walls (no hardcoded codes)

## Rules

1. **GEX walls**: short call/put near walls; buy 1-step further-OTM wings.
2. **Defined risk**: max loss ≈ (max wing − net credit) × multiplier × lots.
3. **Sizing**: default fixed 120 lots on 1M (margin per lot is small); optional Kelly.
4. **Filters off by default**: high-IV and inside-wall gates skipped so the book stays in the market.
5. **Trend filter**: flatten/skip when |spot return| over 20 sessions exceeds 8%.
6. **Exits**: short-strike / wall breach, take-profit, stop-loss, DTE roll, max hold.

## Trades

- 2026-03-27 → 2026-04-20 | K=2.8/2.85/3.2/3.3 | 50ETF沽5月2850/50ETF购5月3200 | lots=120/120 | credit=0.0178 | PnL=4,693.20 | take_profit
- 2026-04-20 → 2026-04-24 | K=2.95/3.0/3.1/3.2 | 50ETF沽5月3000/50ETF购5月3100 | lots=120/120 | credit=0.03 | PnL=-7,566.00 | call_wall_breach
- 2026-04-24 → 2026-05-06 | K=2.825/2.85/3.1/3.117 | 50ETF沽6月2850/50ETF购6月3100 | lots=120/120 | credit=0.008 | PnL=-12,169.20 | short_call_breach
- 2026-05-06 → 2026-06-11 | K=2.825/2.85/3.2/3.215 | 50ETF沽6月2850/50ETF购6月3200 | lots=120/120 | credit=0.0045 | PnL=-4,944.00 | roll_month
- 2026-06-11 → 2026-07-07 | K=2.75/2.8/3.1/3.2 | 50ETF沽7月2800/50ETF购7月3100 | lots=120/120 | credit=0.0151 | PnL=-3,954.00 | roll_month
- 2026-07-07 → 2026-08-04 | K=2.8/2.85/3.1/3.2 | 50ETF沽8月2850/50ETF购8月3100 | lots=120/120 | credit=0.0321 | PnL=13,736.40 | take_profit
- 2026-08-04 → 2026-08-12 | K=2.65/2.7/3.5/3.6 | 50ETF沽9月2700/50ETF购9月3500 | lots=120/120 | credit=0.0038 | PnL=-2,786.40 | take_profit
- 2026-08-12 → 2026-08-31 | K=2.85/2.9/3.5/3.6 | 50ETF沽9月2900/50ETF购9月3500 | lots=120/120 | credit=0.0089 | PnL=-170.40 | eod_force_close
