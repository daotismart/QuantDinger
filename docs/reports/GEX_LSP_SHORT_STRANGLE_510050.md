# GEX + LSP Short Strangle Backtest (510050)

## Summary

- Initial capital: 1,000,000
- Final equity: 996,388.81
- Total return: -0.36%
- Sharpe: -3.507
- Max drawdown: -0.36%
- Trades: 11 (win rate 81.8%)
- Avg trade PnL: 215.78

## Rules

1. **LSP gate**: only sell when LSP regime is neutral/mixed (no strong directional pressure).
2. **GEX walls**: sell OTM call near call wall and OTM put near put wall (wide strangle).
3. **Entry filter**: prefer spot inside put/call walls.
4. **Dynamic hedge**: rebalance underlying shares when residual delta exceeds band.
5. **Exits**: DTE floor, max hold, wall breach, or LSP turning directional.

## Recent trades

- 2026-04-16 → 2026-04-17 | K=3.0/3.1 | PnL=7.28 | put_wall_breach
- 2026-04-24 → 2026-04-28 | K=3.0/3.1 | PnL=26.77 | lsp_directional
- 2026-05-19 → 2026-05-22 | K=3.0/3.1 | PnL=71.77 | exit_dte
- 2026-05-25 → 2026-05-26 | K=3.0/3.1 | PnL=-40.90 | lsp_directional
- 2026-07-03 → 2026-07-09 | K=3.0/3.1 | PnL=314.53 | lsp_directional
- 2026-07-14 → 2026-07-17 | K=3.0/3.1 | PnL=441.85 | exit_dte
- 2026-07-17 → 2026-07-23 | K=2.85/3.1 | PnL=690.69 | lsp_directional
- 2026-07-30 → 2026-08-04 | K=3.0/3.1 | PnL=222.15 | put_wall_breach
- 2026-08-05 → 2026-08-13 | K=3.0/3.1 | PnL=218.62 | lsp_directional
- 2026-08-20 → 2026-08-24 | K=2.9/3.6 | PnL=-3.87 | eod_force_close
