# GEX + LSP Short Strangle Backtest (510050)

## Summary

- Initial capital: 1,000,000
- Final equity: 999,653.96
- Total return: -0.03%
- Sharpe: -0.303
- Max drawdown: -0.10%
- Trades: 11 (win rate 54.5%)
- Avg trade PnL: -31.46

## Rules

1. **LSP**: continuous `lsp_delta_score` sets portfolio net-delta direction and size.
2. **GEX walls**: sell OTM call near call wall and OTM put near put wall.
3. **Option-only hedge**: skew short call/put lots to approximate LSP target delta.
4. **No spot**: underlying is signal-only; never traded for delta hedge.
5. **Exits**: DTE floor, max hold, wall breach, or flattened option book.

## Recent trades

- 2026-04-16 → 2026-04-17 | K=3.0/3.1 | lots=1/1 | score=-0.2171 | PnL=-85.77 | put_wall_breach
- 2026-04-24 → 2026-05-11 | K=3.0/3.1 | lots=2/0 | score=0.6425 | PnL=87.58 | call_wall_breach
- 2026-05-14 → 2026-05-22 | K=3.0/3.1 | lots=1/1 | score=-0.0655 | PnL=-256.11 | exit_dte
- 2026-05-25 → 2026-05-28 | K=3.0/3.1 | lots=2/0 | score=1.0 | PnL=-615.86 | put_wall_breach
- 2026-06-11 → 2026-06-22 | K=2.85/3.1 | lots=2/0 | score=1.0 | PnL=138.68 | exit_dte
- 2026-06-24 → 2026-07-15 | K=3.0/3.1 | lots=1/1 | score=-0.2162 | PnL=542.79 | max_hold
- 2026-07-15 → 2026-07-17 | K=3.0/3.1 | lots=1/1 | score=-0.0748 | PnL=-552.69 | exit_dte
- 2026-07-17 → 2026-08-07 | K=2.85/3.1 | lots=1/1 | score=-0.068 | PnL=184.18 | max_hold
- 2026-08-07 → 2026-08-21 | K=3.0/3.1 | lots=1/1 | score=0.3514 | PnL=172.68 | exit_dte
- 2026-08-21 → 2026-08-24 | K=2.9/3.6 | lots=0/2 | score=0.1178 | PnL=-19.20 | eod_force_close
