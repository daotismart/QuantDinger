# GEX + LSP + Kelly Short Strangle Backtest (510050)

## Summary

- Initial capital: 1,000,000.0
- Final equity: 1,006,460.78
- Total return: 0.65%
- Sharpe: 0.7689
- Max drawdown: -0.90%
- Trades: 6 (win rate 66.7%)
- Avg trade PnL: 1076.8
- Sizing: kelly_margin_ratio
- Expiry month: **next** (次月)
- Roll before DTE: **15**
- High-IV filter: True (odds b=1.0)

## Rules

1. **次月合约**: each entry uses the second-nearest monthly expiry (not front month).
2. **移仓换月**: flatten and reopen the new 次月 when held DTE ≤ 15 (same day, IV gate skipped).
3. **GEX walls**: sell OTM call near call wall and OTM put near put wall.
4. **High IV**: enter only when ATM IV rank ≥ threshold (rolls skip this gate).
5. **Kelly margin ratio (premium odds 1:1)**: `f* = 2p-1`; clamp to max fraction/lots.
6. **LSP**: sets net delta exposure from margin budget; skew call/put lots; no spot hedge.
7. **Risk control**: clamp margin ratio/`max_lots`; scale if LSP skew exceeds Kelly budget.
8. **Other exits**: wall breach, max hold, flattened option book.

## Trades

- 2026-04-02 → 2026-04-16 | exp=2026-05-27 | K=2.85/3.0 | lots=11/9 | PnL=593.88 | call_wall_breach
- 2026-04-27 → 2026-05-11 | exp=2026-06-24 | K=2.85/3.1 | lots=11/9 | PnL=-2940.4 | call_wall_breach
- 2026-05-12 → 2026-05-28 | exp=2026-06-24 | K=3.0/3.2 | lots=11/9 | PnL=-1133.09 | put_wall_breach
- 2026-05-28 → 2026-07-07 | exp=2026-07-22 | K=2.8/3.1 | lots=11/9 | PnL=3286.6 | roll_month
- 2026-07-08 → 2026-08-11 | exp=2026-08-26 | K=2.85/3.1 | lots=11/9 | PnL=5469.46 | roll_month
- 2026-08-11 → 2026-08-28 | exp=2026-09-23 | K=2.9/3.6 | lots=9/11 | PnL=1184.33 | eod_force_close
