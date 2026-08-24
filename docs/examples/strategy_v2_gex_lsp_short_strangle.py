"""GEX+LSP Dynamic Short Strangle
Sell a wide call/put strangle when LSP is non-directional and spot sits between
GEX put/call walls; delta-hedge residual exposure in the underlying ETF.

Universe is source-owned for Strategy API V2 sandboxes. For research with full
historical walls, use scripts/backtest_gex_lsp_short_strangle.py against the
ETF options ClickHouse dump.
"""

import math

# @param lots int 1 Option lots per leg range=1:20:1
# @param hedge_band_delta float 0.15 Rehedge when |net delta| exceeds this * lots range=0.05:0.5:0.01
# @param lsp_days_1 int 5 Short LSP window range=3:20:1
# @param lsp_days_2 int 10 Long LSP window range=5:40:1
# @param lsp_neutral_band float 8.0 |LSP-50| band treated as neutral range=2:20:0.5
# @param put_wall float 2.9 Put-wall strike used for entry gate range=1:10:0.05
# @param call_wall float 3.1 Call-wall strike used for entry gate range=1:10:0.05
# @param wall_buffer_pct float 0.005 Buffer around walls for entry/exit range=0:0.05:0.001
# @param max_hold_bars int 15 Exit after N daily bars range=1:60:1
# @param enable_delta_hedge bool true Hedge residual delta with underlying

PERSIST_RUNTIME_STATE = True

CALL_SYMBOL = "CNIndexOptions:10004448"  # placeholder; replace with listed call near call wall
PUT_SYMBOL = "CNIndexOptions:10004449"  # placeholder; replace with listed put near put wall
UNDERLYING_SYMBOL = "CNStock:510050"
BAR_FREQUENCY = "1d"
MULTIPLIER = 10000.0


def initialize(context):
    g.call_symbol = CALL_SYMBOL
    g.put_symbol = PUT_SYMBOL
    g.underlying_symbol = UNDERLYING_SYMBOL
    g.bar_index = 0
    g.entry_bar = -1
    g.in_trade = False
    context.set_universe([g.call_symbol, g.put_symbol, g.underlying_symbol])
    context.set_benchmark(g.underlying_symbol)
    context.subscribe(frequency=BAR_FREQUENCY, fields=["open", "high", "low", "close", "volume"])
    context.set_warmup(30)
    context.set_metadata(direction_mode="both", strategy_family="options_short_vol")


def handle_data(context, data):
    if not is_trade():
        return
    if context.current_dt is None:
        return

    lots = max(int(context.params.get("lots", 1) or 1), 1)
    hedge_band = max(_f(context.params.get("hedge_band_delta", 0.15), 0.15), 0.01)
    days_1 = max(int(context.params.get("lsp_days_1", 5) or 5), 1)
    days_2 = max(int(context.params.get("lsp_days_2", 10) or 10), 1)
    band = max(_f(context.params.get("lsp_neutral_band", 8.0), 8.0), 0.0)
    put_wall = _f(context.params.get("put_wall", 2.9), 2.9)
    call_wall = _f(context.params.get("call_wall", 3.1), 3.1)
    wall_buf = max(_f(context.params.get("wall_buffer_pct", 0.005), 0.005), 0.0)
    max_hold = max(int(context.params.get("max_hold_bars", 15) or 15), 1)
    enable_hedge = _b(context.params.get("enable_delta_hedge", True), True)

    hist = get_history(max(days_2 * 3, 40), BAR_FREQUENCY, ["open", "high", "low", "close", "volume"], g.underlying_symbol)
    if hist is None or len(hist) < days_2 + 2:
        return
    spot = float(data.current(g.underlying_symbol, "close"))
    call_px = float(data.current(g.call_symbol, "close"))
    put_px = float(data.current(g.put_symbol, "close"))
    if spot <= 0 or call_px <= 0 or put_px <= 0:
        return

    lsp_ok, regime = _lsp_gate(hist, days_1=days_1, days_2=days_2, band=band)
    inside = (spot <= call_wall * (1.0 - wall_buf)) and (spot >= put_wall * (1.0 + wall_buf))
    g.bar_index = int(g.bar_index) + 1

    call_pos = get_position(g.call_symbol)
    put_pos = get_position(g.put_symbol)
    und_pos = get_position(g.underlying_symbol)
    call_qty = float(call_pos.amount or 0.0)
    put_qty = float(put_pos.amount or 0.0)
    und_qty = float(und_pos.amount or 0.0)
    short_call = call_qty < 0
    short_put = put_qty < 0
    g.in_trade = short_call and short_put

    if g.in_trade:
        # Approximate ATM deltas for hedge if contract greeks unavailable.
        call_delta = 0.25
        put_delta = -0.25
        target_hedge = abs(call_qty) * MULTIPLIER * (call_delta + put_delta)
        if enable_hedge and abs(target_hedge - und_qty) > hedge_band * lots * MULTIPLIER:
            order_target(g.underlying_symbol, target_hedge, reason="gex_lsp_delta_hedge")

        held = int(g.bar_index) - int(g.entry_bar)
        exit_now = False
        reason = ""
        if held >= max_hold:
            exit_now, reason = True, "max_hold"
        elif spot >= call_wall * (1.0 + wall_buf):
            exit_now, reason = True, "call_wall_breach"
        elif spot <= put_wall * (1.0 - wall_buf):
            exit_now, reason = True, "put_wall_breach"
        elif regime in ("bullish", "bearish") and not lsp_ok:
            exit_now, reason = True, "lsp_directional"
        if exit_now:
            order_target(g.call_symbol, 0, reason=reason)
            order_target(g.put_symbol, 0, reason=reason)
            order_target(g.underlying_symbol, 0, reason=reason + "_flat_hedge")
            g.in_trade = False
            g.entry_bar = -1
        return

    # Entry: LSP non-directional + inside walls + flat.
    if lsp_ok and inside and abs(call_qty) < 1e-9 and abs(put_qty) < 1e-9:
        order_target(g.call_symbol, -float(lots), reason="short_call_wall")
        order_target(g.put_symbol, -float(lots), reason="short_put_wall")
        if enable_hedge:
            # Initial hedge using placeholder deltas; live/research path should inject greeks.
            order_target(g.underlying_symbol, lots * MULTIPLIER * (0.25 - 0.25), reason="gex_lsp_delta_hedge")
        g.in_trade = True
        g.entry_bar = int(g.bar_index)
        record(regime=regime, spot=spot, call_wall=call_wall, put_wall=put_wall)


def _lsp_gate(hist, days_1, days_2, band):
    closes = [float(x) for x in hist["close"].tolist()]
    opens = [float(x) for x in hist["open"].tolist()]
    highs = [float(x) for x in hist["high"].tolist()]
    lows = [float(x) for x in hist["low"].tolist()]
    volumes = [float(x) for x in hist["volume"].tolist()]
    n = len(closes)
    if n < days_2 + 2:
        return False, "mixed"
    signed = []
    for i in range(n):
        body = closes[i] - opens[i]
        path = 2.0 * (highs[i] - lows[i]) - abs(body)
        if path == 0:
            direction = 1.0 if i > 0 and closes[i] >= closes[i - 1] else -1.0
            signed.append(direction * volumes[i])
        else:
            signed.append((body / path) * volumes[i])
    def lsp(window):
        if n < window:
            return 50.0
        chunk = signed[-window:]
        buy = sum(v for v in chunk if v > 0)
        sell = abs(sum(v for v in chunk if v < 0))
        total = buy + sell
        if total <= 0:
            return 50.0
        return 100.0 * buy / total
    a = lsp(days_1)
    b = lsp(days_2)
    if a >= 50 + band and b >= 50 + band:
        return False, "bullish"
    if a <= 50 - band and b <= 50 - band:
        return False, "bearish"
    if abs(a - 50) <= band and abs(b - 50) <= band:
        return True, "neutral"
    return True, "mixed"


def _f(value, default):
    try:
        out = float(value)
        if math.isnan(out) or math.isinf(out):
            return float(default)
        return out
    except Exception:
        return float(default)


def _b(value, default):
    if isinstance(value, bool):
        return value
    if value is None:
        return bool(default)
    text = str(value).strip().lower()
    if text in ("1", "true", "yes", "y", "on"):
        return True
    if text in ("0", "false", "no", "n", "off"):
        return False
    return bool(default)
