# GEX + LSP + Kelly Short Strangle Backtest (510050)

## Summary

- Initial capital: 1,000,000
- Final equity: 1,004,180.11
- Total return: 0.42%
- Sharpe: 0.262
- Max drawdown: -2.04%
- Trades: 6 (win rate 66.7%)
- Avg trade PnL: 696.69
- Sizing: kelly_1to1_premium
- High-IV filter: True (odds b=1.0)

## Rules

1. **GEX walls**: sell OTM call near call wall and OTM put near put wall (safe width).
2. **High IV**: enter only when ATM IV rank ≥ threshold (short premium when rich).
3. **Kelly (1:1 premium)**: `f* = 2p-1` on collected credit; clamp to max fraction/lots.
4. **LSP**: skew call/put lots for directional delta; no spot hedge.
5. **Risk control**: oversize Kelly/`max_lots` clamped; insufficient budget blocks entry.
6. **Exits**: DTE floor, max hold, wall breach, or flattened option book.

## Recent trades

- 2026-04-02 → 2026-04-16 | K=2.9/3.0 | lots=10/10 | score=-0.3654 | PnL=592.30 | call_wall_breach
- 2026-05-08 → 2026-05-11 | K=3.0/3.1 | lots=11/9 | score=0.6848 | PnL=-1,776.00 | call_wall_breach
- 2026-05-14 → 2026-05-22 | K=3.0/3.1 | lots=9/11 | score=-0.0655 | PnL=384.12 | exit_dte
- 2026-05-26 → 2026-05-28 | K=3.0/3.1 | lots=11/9 | score=1.0 | PnL=-1,902.82 | put_wall_breach
- 2026-06-25 → 2026-07-16 | K=3.0/3.1 | lots=9/11 | score=-0.2178 | PnL=3,117.92 | max_hold
- 2026-07-17 → 2026-08-07 | K=2.85/3.1 | lots=11/9 | score=-0.068 | PnL=3,764.59 | max_hold
