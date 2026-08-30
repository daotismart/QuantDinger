"""GEX+LSP+Kelly Dynamic Short Strangle (options-only)
GEX walls set short call/put strikes; enter only when IV is rich; Kelly (premium odds 1:1) sets margin/equity ratio with hard caps;
LSP sets net delta exposure; call/put skew realizes that delta.
No underlying hedge.
Opens on next-month (次月) contracts and rolls 15 DTE before expiry.

Universe is source-owned for Strategy API V2 sandboxes. For research with full
historical walls, use scripts/backtest_gex_lsp_short_strangle.py.
"""

import math

# @param lots int 1 Base short lots per leg before LSP skew range=1:20:1
# @param max_skew_lots int 1 Extra short lots tilted by LSP range=0:5:1
# @param max_abs_delta float 0.5 Max |target delta| as fraction of one lot range=0.1:1:0.05
# @param lsp_days_1 int 5 Short LSP window range=3:20:1
# @param lsp_days_2 int 10 Long LSP window range=5:40:1
# @param put_wall float 2.9 GEX put-wall strike range=1:10:0.05
# @param call_wall float 3.1 GEX call-wall strike range=1:10:0.05
# @param wall_buffer_pct float 0.005 Buffer around walls for entry/exit range=0:0.05:0.001
# @param max_hold_bars int 60 Exit after N daily bars (prefer roll_before_dte) range=1:90:1
# @param roll_before_dte int 15 Roll to next-month when DTE <= N range=5:30:1
# @param expiry_month str next Open on next-month (次月) not front month
# @param iv_rank_min float 0.6 Min ATM IV-rank proxy to sell premium range=0:1:0.05
# @param kelly_max_fraction float 0.25 Hard Kelly fraction cap (risk control) range=0.05:0.5:0.05
# @param kelly_max_lots int 5 Max base lots after Kelly range=1:20:1
# @param kelly_prior_p float 0.55 Prior win probability for Kelly range=0.4:0.7:0.01

PERSIST_RUNTIME_STATE = True

CALL_SYMBOL = "CNIndexOptions:10010975"  # sandbox leg near call wall (replace per roll)
PUT_SYMBOL = "CNIndexOptions:10010981"  # sandbox leg near put wall (replace per roll)
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
    g.hold_dte = 0
    g.lsp_score = 0.0
    # Underlying is used only for LSP / wall / spot price signals — never traded.
    context.set_universe([g.call_symbol, g.put_symbol, g.underlying_symbol])
    context.set_benchmark(g.underlying_symbol)
    context.subscribe(frequency=BAR_FREQUENCY, fields=["open", "high", "low", "close", "volume"])
    context.set_warmup(30)
    context.set_metadata(direction_mode="both", strategy_family="options_short_vol_options_hedge")


def handle_data(context, data):
    if not is_trade() or context.current_dt is None:
        return

    lots = max(int(context.params.get("lots", 1) or 1), 1)
    max_skew = max(int(context.params.get("max_skew_lots", 1) or 1), 0)
    max_abs_delta = max(_f(context.params.get("max_abs_delta", 0.5), 0.5), 0.0)
    days_1 = max(int(context.params.get("lsp_days_1", 5) or 5), 1)
    days_2 = max(int(context.params.get("lsp_days_2", 10) or 10), 1)
    put_wall = _f(context.params.get("put_wall", 2.9), 2.9)
    call_wall = _f(context.params.get("call_wall", 3.1), 3.1)
    wall_buf = max(_f(context.params.get("wall_buffer_pct", 0.005), 0.005), 0.0)
    max_hold = max(int(context.params.get("max_hold_bars", 60) or 60), 1)
    roll_before_dte = max(int(context.params.get("roll_before_dte", 15) or 15), 1)
    iv_rank_min = max(_f(context.params.get("iv_rank_min", 0.6), 0.6), 0.0)
    kelly_max_f = max(_f(context.params.get("kelly_max_fraction", 0.25), 0.25), 0.0)
    kelly_max_lots = max(int(context.params.get("kelly_max_lots", 5) or 5), 0)
    prior_p = min(max(_f(context.params.get("kelly_prior_p", 0.55), 0.55), 0.01), 0.99)

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
    # Target delta is informational; hedge is realized only via option lot skew.
    _ = lsp_score * max_abs_delta * lots * MULTIPLIER
    iv_rank = _iv_rank_proxy(hist)
    high_iv_ok = iv_rank is None or iv_rank >= iv_rank_min
    equity = float(context.portfolio.total_value or 0.0)
    # Prior-only win prob in sandbox (research engine tracks closed PnLs).
    base_lots = _kelly_base_lots(equity, call_px, put_px, prior_p, kelly_max_f, kelly_max_lots)
    if base_lots <= 0:
        base_lots = 0
    call_lots, put_lots = _skew_lots(lsp_score, max(base_lots, 1) if base_lots > 0 else 0, max_skew)
    if base_lots <= 0:
        call_lots, put_lots = 0, 0
    inside = (spot <= call_wall * (1.0 - wall_buf)) and (spot >= put_wall * (1.0 + wall_buf))
    g.bar_index = int(g.bar_index) + 1

    call_qty = float(get_position(g.call_symbol).amount or 0.0)
    put_qty = float(get_position(g.put_symbol).amount or 0.0)
    g.in_trade = call_qty < 0 or put_qty < 0

    if g.in_trade:
        g.hold_dte = max(int(g.hold_dte) - 1, 0)
        # Options-only hedge: keep short call/put skew aligned with LSP.
        order_target(g.call_symbol, -float(call_lots), reason="lsp_skew_short_call")
        order_target(g.put_symbol, -float(put_lots), reason="lsp_skew_short_put")
        # Ensure no residual underlying position.
        und_qty = float(get_position(g.underlying_symbol).amount or 0.0)
        if abs(und_qty) > 1e-9:
            order_target(g.underlying_symbol, 0, reason="flatten_unwanted_spot")

        held = int(g.bar_index) - int(g.entry_bar)
        need_roll = int(g.hold_dte) <= int(roll_before_dte)
        breach = spot >= call_wall * (1.0 + wall_buf) or spot <= put_wall * (1.0 - wall_buf)
        if need_roll or held >= max_hold or breach:
            reason = "roll_month" if need_roll else ("exit_max_hold" if held >= max_hold else "exit_wall_breach")
            order_target(g.call_symbol, 0, reason=reason + "_call")
            order_target(g.put_symbol, 0, reason=reason + "_put")
            order_target(g.underlying_symbol, 0, reason=reason + "_spot")
            g.in_trade = False
            g.entry_bar = -1
            # Same-day roll: reopen next-month placeholder legs when still inside walls.
            if need_roll and inside and (call_lots + put_lots) > 0:
                order_target(g.call_symbol, -float(call_lots), reason="roll_open_next_month_call")
                order_target(g.put_symbol, -float(put_lots), reason="roll_open_next_month_put")
                order_target(g.underlying_symbol, 0, reason="roll_no_spot_hedge")
                g.in_trade = True
                g.entry_bar = int(g.bar_index)
                g.hold_dte = 45
        return

    if inside and high_iv_ok and abs(call_qty) < 1e-9 and abs(put_qty) < 1e-9 and (call_lots + put_lots) > 0:
        order_target(g.call_symbol, -float(call_lots), reason="short_call_at_gex_wall")
        order_target(g.put_symbol, -float(put_lots), reason="short_put_at_gex_wall")
        order_target(g.underlying_symbol, 0, reason="no_spot_hedge")
        g.in_trade = True
        g.entry_bar = int(g.bar_index)
        g.hold_dte = 45  # next-month approx DTE at entry


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


def _iv_rank_proxy(hist):
    """Proxy IV rank from realized vol of underlying closes (sandbox has no chain IV)."""
    closes = [float(x) for x in hist["close"].tolist()]
    if len(closes) < 10:
        return None
    rets = []
    for i in range(1, len(closes)):
        if closes[i - 1] > 0:
            rets.append(math.log(closes[i] / closes[i - 1]))
    if len(rets) < 5:
        return None
    window = rets[-60:] if len(rets) >= 60 else rets
    vols = []
    for i in range(4, len(window)):
        chunk = window[i - 4 : i + 1]
        mu = sum(chunk) / len(chunk)
        var = sum((x - mu) ** 2 for x in chunk) / max(len(chunk) - 1, 1)
        vols.append(math.sqrt(max(var, 0.0)))
    if len(vols) < 2:
        return None
    cur, lo, hi = vols[-1], min(vols), max(vols)
    if hi <= lo:
        return 0.5
    return (cur - lo) / (hi - lo)


def _kelly_base_lots(equity, call_px, put_px, win_prob, max_fraction, max_lots):
    """f* = 2p-1 for 1:1 premium odds; clamp fraction and lots (risk control)."""
    p = float(win_prob)
    raw = 2.0 * p - 1.0
    if raw <= 0 or equity <= 0 or max_lots <= 0:
        return 0
    fraction = min(raw, float(max_fraction))
    capital_per_lot = (max(call_px, 0.0) + max(put_px, 0.0)) * MULTIPLIER
    if capital_per_lot <= 0:
        return 0
    lots = int((equity * fraction) // capital_per_lot)
    return int(min(max(lots, 0), int(max_lots)))
