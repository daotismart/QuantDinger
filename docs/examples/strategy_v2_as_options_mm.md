# AS Options Market Maker (Strategy API V2)

This is a **bar-based** Avellaneda–Stoikov (AS) style options market maker using **Strategy API V2**.

> Quotes refresh once per completed bar (e.g. `5m`). It is **not** a tick-driven engine.

## Universe / instruments

The strategy is **source-owned** (declared in code):

- Option: `CNFuturesOptions:M2609-C-2800`
- Underlying futures: `CNFutures:M2609`

To sell options, the strategy declares `direction_mode="both"` so the runtime can reserve both sides / hedge legs for exchange hedge mode.

## What it does

For each bar, it:

1. Computes **Black-76** option greeks (delta / gamma / vega, with `r≈0`).
2. Builds an AS-style **reservation price** that penalizes:
   - option inventory (`q_opt`)
   - net delta inventory (`q_opt * delta + q_und`)
3. Widens the half-spread with **gamma/vega widening**, realized-vol or IV override, and an EWMA **toxicity** term.
4. Places **cancel-replace** limit orders for bid/ask on the option.
5. (Optional) performs **delta hedging** with the underlying via `order_target(...)`.

## Key risk / control knobs

Tune these via `# @param` in the source file:

- `max_inventory`: one-sided inventory cap (only quote the reducing side when capped)
- `min_ticks`: minimum full spread in ticks
- `fee_floor`: extra half-spread added to cover fee floors / adverse selection
- `tox_lambda`, `tox_widen`: EWMA toxicity and its widening factor
- `gamma_widen`, `vega_widen`: additional spread terms from option greeks
- `enable_delta_hedge`, `hedge_every_n_bars`: optional futures delta hedge

## Where to find the source

Code: [`strategy_v2_as_options_mm.py`](strategy_v2_as_options_mm.py)

