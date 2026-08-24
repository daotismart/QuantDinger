"""GEX+LSP Dynamic Short Strangle (delta-targeted)
LSP sets portfolio net-delta direction and magnitude; GEX walls set short call /
put strikes; residual delta is hedged with option-lot skew plus spot.

Universe is source-owned for Strategy API V2 sandboxes. For research with full
historical walls, use scripts/backtest_gex_lsp_short_strangle.py.
"""

import math

# @param lots int 1 Base short lots per leg before LSP skew range=1:20:1
# @param max_skew_lots int 1 Extra short lots tilted by LSP range=0:5:1
# @param max_abs_delta float 0.5 Max |target delta| as fraction of one lot range=0.1:1:0.05
# @param hedge_band_delta float 0.10 Spot rehedge band (delta fraction of lots) range=0.05:0.5:0.01
# @param lsp_days_1 int 5 Short LSP window range=3:20:1
# @param lsp_days_2 int 10 Long LSP window range=5:40:1
# @param put_wall float 2.9 GEX put-wall strike range=1:10:0.05
# @param call_wall float 3.1 GEX call-wall strike range=1:10:0.05
# @param wall_buffer_pct float 0.005 Buffer around walls for entry/exit range=0:0.05:0.001
# @param max_hold_bars int 15 Exit after N daily bars range=1:60:1
# @param enable_spot_hedge bool true Hedge residual delta with underlying
# @param enable_option_skew bool true Skew short call/put lots by LSP

PERSIST_RUNTIME_STATE = True

CALL_SYMBOL = "CNIndexOptions:10004448"  # placeholder near call wall
PUT_SYMBOL = "CNIndexOptions:10004449"  # placeholder near put wall
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
    g.lsp_score = 0.0
    context.set_universe([g.call_symbol, g.put_symbol, g.underlying_symbol])
    context.set_benchmark(g.underlying_symbol)
    context.subscribe(frequency=BAR_FREQUENCY, fields=["open", "high", "low", "close", "volume"])
    context.set_warmup(30)
    context.set_metadata(direction_mode="both", strategy_family="options_short_vol_delta_target")


def handle_data(context, data):
    if not is_trade() or context.current_dt is None:
        return

    lots = max(int(context.params.get("lots", 1) or 1), 1)
    max_skew = max(int(context.params.get("max_skew_lots", 1) or 1), 0)
    max_abs_delta = max(_f(context.params.get("max_abs_delta", 0.5), 0.5), 0.0)
    hedge_band = max(_f(context.params.get("hedge_band_delta", 0.10), 0.10), 0.01)
    days_1 = max(int(context.params.get("lsp_days_1", 5) or 5), 1)
    days_2 = max(int(context.params.get("lsp_days_2", 10) or 10), 1)
    put_wall = _f(context.params.get("put_wall", 2.9), 2.9)
    call_wall = _f(context.params.get("call_wall", 3.1), 3.1)
    wall_buf = max(_f(context.params.get("wall_buffer_pct", 0.005), 0.005), 0.0)
    max_hold = max(int(context.params.get("max_hold_bars", 15) or 15), 1)
    enable_spot = _b(context.params.get("enable_spot_hedge", True), True)
    enable_skew = _b(context.params.get("enable_option_skew", True), True)

    hist = get_history(max(days_2 * 3, 40), BAR_FREQUENCY, ["open", "high", "low", "close", "volume"], g.underlying_symbol)
    if hist is None or len(hist) < days_2 + 2:
        return

    spot = float(data.current(g.underlying_symbol, "close"))
    call_px = float(data.current(g.call_symbol, "close"))
    put_px = float(data.current(g.put_symbol, "close"))
    if spot <= 0 or call_px <= 0 or put_px <= 0:
        return

    lsp_score = _lsp_delta_score(hist, days_1=days_1, days_2=days_2)
    g.lsp_score = lsp_score
    target_delta = lsp_score * max_abs_delta * lots * MULTIPLIER
    call_lots, put_lots = _skew_lots(lsp_score, lots, max_skew) if enable_skew else (lots, lots)
    inside = (spot <= call_wall * (1.0 - wall_buf)) and (spot >= put_wall * (1.0 + wall_buf))
    g.bar_index = int(g.bar_index) + 1

    call_qty = float(get_position(g.call_symbol).amount or 0.0)
    put_qty = float(get_position(g.put_symbol).amount or 0.0)
    und_qty = float(get_position(g.underlying_symbol).amount or 0.0)
    g.in_trade = call_qty < 0 or put_qty < 0

    # Approximate contract deltas when live greeks are unavailable.
    call_delta = 0.25
    put_delta = -0.25
    option_delta = (-abs(call_qty) * call_delta - abs(put_qty) * put_delta) * MULTIPLIER
    # If flat options, option_delta=0.
    if abs(call_qty) < 1e-9 and abs(put_qty) < 1e-9:
        option_delta = 0.0

    if g.in_trade:
        # Keep option skew aligned with latest LSP.
        if enable_skew:
            order_target(g.call_symbol, -float(call_lots), reason="lsp_skew_short_call")
            order_target(g.put_symbol, -float(put_lots), reason="lsp_skew_short_put")
            call_qty = -float(call_lots)
            put_qty = -float(put_lots)
            option_delta = (-abs(call_qty) * call_delta - abs(put_qty) * put_delta) * MULTIPLIER

        if enable_spot:
            target_hedge = target_delta - option_delta
            if abs(target_hedge - und_qty) > hedge_band * lots * MULTIPLIER:
                order_target(g.underlying_symbol, target_hedge, reason="lsp_spot_delta_hedge")

        held = int(g.bar_index) - int(g.entry_bar)
        if held >= max_hold or spot >= call_wall * (1.0 + wall_buf) or spot <= put_wall * (1.0 - wall_buf):
            order_target(g.call_symbol, 0, reason="exit_flat_call")
            order_target(g.put_symbol, 0, reason="exit_flat_put")
            order_target(g.underlying_symbol, 0, reason="exit_flat_hedge")
            g.in_trade = False
            g.entry_bar = -1
        return

    if inside and abs(call_qty) < 1e-9 and abs(put_qty) < 1e-9 and (call_lots + put_lots) > 0:
        order_target(g.call_symbol, -float(call_lots), reason="short_call_at_gex_wall")
        order_target(g.put_symbol, -float(put_lots), reason="short_put_at_gex_wall")
        if enable_spot:
            option_delta = (call_lots * call_delta + put_lots * put_delta) * (-MULTIPLIER)
            order_target(g.underlying_symbol, target_delta - option_delta, reason="lsp_spot_delta_hedge")
        g.in_trade = True
        g.entry_bar = int(g.bar_index)


def _lsp_delta_score(hist, days_1, days_2):
    closes = [float(x) for x in hist["close"].tolist()]
    opens = [float(x) for x in hist["open"].tolist()]
    highs = [float(x) for x in hist["high"].tolist()]
    lows = [float(x) for x in hist["low"].tolist()]
    volumes = [float(x) for x in hist["volume"].tolist()]
    n = len(closes)
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
    score = ((a + b) / 2.0 - 50.0) / 50.0
    if score > 1.0:
        return 1.0
    if score < -1.0:
        return -1.0
    return float(score)


def _skew_lots(score, base_lots, max_skew_lots):
    base = max(int(base_lots), 1)
    skew = int(round(abs(float(score)) * max(int(max_skew_lots), 0)))
    skew = min(skew, base)
    if score > 0:
        return base - skew, base + skew
    if score < 0:
        return base + skew, base - skew
    return base, base


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
