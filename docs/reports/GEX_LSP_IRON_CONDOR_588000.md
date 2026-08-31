# GEX + LSP + Kelly Iron Condor Backtest (588000)

## Summary

- Initial capital: 1,000,000
- Final equity: 995,966.70
- Total return: -0.40%
- Sharpe: -2.317
- Max drawdown: -0.47%
- Trades: 2 (win rate 0.0%)
- Avg trade PnL: -2,016.65
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

- 2026-04-02 → 2026-04-27 | K=1.1/1.15/1.55/1.6 | lots=10/10 | credit=0.0069 | PnL=-2,684.20 | short_call_breach
- 2026-04-27 → 2026-05-11 | K=1.4/1.45/1.8/1.85 | lots=10/10 | credit=0.0157 | PnL=-1,349.10 | short_call_breach
