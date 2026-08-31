# GEX + LSP + Kelly Iron Condor Backtest (510050)

## Summary

- Initial capital: 1,000,000
- Final equity: 998,387.10
- Total return: -0.16%
- Sharpe: -1.234
- Max drawdown: -0.26%
- Trades: 1 (win rate 0.0%)
- Avg trade PnL: -1,612.90
- Sizing: kelly_defined_risk
- High-IV filter: True
- Wing steps: 1 | take-profit=0.5 | stop-loss=0.9

## Rules

1. **GEX walls**: short call/put near walls; buy further-OTM wings (`wing_steps`).
2. **Defined risk**: max loss ≈ (max wing − net credit) × multiplier × lots.
3. **High IV**: enter only when ATM IV rank ≥ threshold (rolls may skip).
4. **Kelly**: `f*=2p−1` on defined-risk margin; clamp fraction/lots.
5. **LSP**: skew short call/put lots; long wings match short lots per side; no spot hedge.
6. **Exits**: short-strike breach, wall breach, roll DTE, max hold, take-profit, stop-loss.

## Trades

- 2026-04-02 → 2026-04-15 | K=2.8/2.85/3.0/3.1 | lots=10/10 | credit=0.0351 | PnL=-1,612.90 | short_call_breach

## Sensitivity (no IV filter)

Same rules without the high-IV gate on 510050:

- Final equity: 1,010,283.90
- Total return: 1.03%
- Sharpe: 1.432
- Max drawdown: -0.17%
- Trades: 3 (win rate 33.3%)
- Avg trade PnL: 3,427.97

Note: sample window ~Mar–Aug 2026; high-IV gate yields few entries on this panel.

