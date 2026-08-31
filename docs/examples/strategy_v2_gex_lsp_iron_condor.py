"""GEX+LSP+Kelly Iron Condor (options-only, defined risk)
Short call/put near GEX walls + long further-OTM wings.
Kelly sizes on defined-risk margin; LSP skews short lots (wings match).
No underlying hedge. Prefer next-month contracts; roll ~15 DTE.

Universe is source-owned for Strategy API V2 sandboxes. For research with full
historical walls, use scripts/backtest_gex_lsp_iron_condor.py.
"""

import math

# @param lots int 120 Base short lots per side before LSP skew range=1:200:1
# @param max_skew_lots int 1 Extra short lots tilted by LSP range=0:5:1
# @param wing_steps int 1 Listed strikes beyond short for long wings range=1:5:1
# @param lsp_days_1 int 5 Short LSP window range=3:20:1
# @param lsp_days_2 int 10 Long LSP window range=5:40:1
# @param put_wall float 2.9 GEX put-wall strike range=1:10:0.05
# @param call_wall float 3.1 GEX call-wall strike range=1:10:0.05
# @param long_put_strike float 2.8 Long put wing strike range=1:10:0.05
# @param long_call_strike float 3.2 Long call wing strike range=1:10:0.05
# @param wall_buffer_pct float 0.005 Buffer around walls for entry/exit range=0:0.05:0.001
# @param max_hold_bars int 60 Exit after N daily bars range=1:90:1
# @param take_profit_pct float 0.5 Close when remaining debit <= (1-tp)*entry credit range=0.1:0.9:0.05
# @param stop_loss_pct float 0.9 Close when MTM loss >= stop * max risk range=0.3:1.5:0.05
# @param iv_rank_min float 0.6 Min ATM IV-rank proxy to sell premium range=0:1:0.05
# @param kelly_max_fraction float 0.25 Hard Kelly fraction cap range=0.05:0.5:0.05
# @param kelly_max_lots int 5 Max base lots after Kelly range=1:20:1
# @param kelly_prior_p float 0.55 Prior win probability for Kelly range=0.4:0.7:0.01

PERSIST_RUNTIME_STATE = True

SHORT_CALL_SYMBOL = "CNIndexOptions:10004448"  # placeholder near call wall
SHORT_PUT_SYMBOL = "CNIndexOptions:10004449"  # placeholder near put wall
LONG_CALL_SYMBOL = "CNIndexOptions:10004450"  # placeholder further OTM call
LONG_PUT_SYMBOL = "CNIndexOptions:10004451"  # placeholder further OTM put
UNDERLYING_SYMBOL = "CNStock:510050"
BAR_FREQUENCY = "1d"
MULTIPLIER = 10000.0


def initialize(context):
    g.short_call = SHORT_CALL_SYMBOL
    g.short_put = SHORT_PUT_SYMBOL
    g.long_call = LONG_CALL_SYMBOL
    g.long_put = LONG_PUT_SYMBOL
    g.underlying_symbol = UNDERLYING_SYMBOL
    g.bar_index = 0
    g.entry_bar = -1
    g.in_trade = False
    g.entry_credit_cash = 0.0
    g.max_risk = 0.0
    g.lsp_score = 0.0
    context.set_universe(
        [g.short_call, g.short_put, g.long_call, g.long_put, g.underlying_symbol]
    )
    context.set_benchmark(g.underlying_symbol)
    context.subscribe(frequency=BAR_FREQUENCY, fields=["open", "high", "low", "close", "volume"])
    context.set_warmup(30)
    context.set_metadata(direction_mode="both", strategy_family="options_short_vol_iron_condor")


def handle_data(context, data):
    if not is_trade() or context.current_dt is None:
        return

    lots = max(int(context.params.get("lots", 1) or 1), 1)
    max_skew = max(int(context.params.get("max_skew_lots", 1) or 1), 0)
    days_1 = max(int(context.params.get("lsp_days_1", 5) or 5), 1)
    days_2 = max(int(context.params.get("lsp_days_2", 10) or 10), 1)
    put_wall = _f(context.params.get("put_wall", 2.9), 2.9)
    call_wall = _f(context.params.get("call_wall", 3.1), 3.1)
    long_put_k = _f(context.params.get("long_put_strike", 2.8), 2.8)
    long_call_k = _f(context.params.get("long_call_strike", 3.2), 3.2)
    wall_buf = max(_f(context.params.get("wall_buffer_pct", 0.005), 0.005), 0.0)
    max_hold = max(int(context.params.get("max_hold_bars", 60) or 60), 1)
    take_profit = max(_f(context.params.get("take_profit_pct", 0.5), 0.5), 0.0)
    stop_loss = max(_f(context.params.get("stop_loss_pct", 0.9), 0.9), 0.0)
    iv_rank_min = max(_f(context.params.get("iv_rank_min", 0.6), 0.6), 0.0)
    kelly_max_f = max(_f(context.params.get("kelly_max_fraction", 0.25), 0.25), 0.0)
    kelly_max_lots = max(int(context.params.get("kelly_max_lots", 5) or 5), 0)
    prior_p = min(max(_f(context.params.get("kelly_prior_p", 0.55), 0.55), 0.01), 0.99)

    hist = get_history(max(days_2 * 3, 40), BAR_FREQUENCY, ["open", "high", "low", "close", "volume"], g.underlying_symbol)
    if hist is None or len(hist) < days_2 + 2:
        return

    spot = float(data.current(g.underlying_symbol, "close"))
    sc = float(data.current(g.short_call, "close"))
    sp = float(data.current(g.short_put, "close"))
    lc = float(data.current(g.long_call, "close"))
    lp = float(data.current(g.long_put, "close"))
    if spot <= 0 or min(sc, sp, lc, lp) <= 0:
        return

    lsp_score = _lsp_delta_score(hist, days_1=days_1, days_2=days_2)
    g.lsp_score = lsp_score
    iv_rank = _iv_rank_proxy(hist)
    high_iv_ok = iv_rank is None or iv_rank >= iv_rank_min
    equity = float(getattr(context.portfolio, "total_value", 0.0) or 0.0)
    net_credit = max(sc - lc, 0.0) + max(sp - lp, 0.0)
    call_wing = max(long_call_k - call_wall, 0.0)
    put_wing = max(put_wall - long_put_k, 0.0)
    wing = max(call_wing, put_wing)
    margin_per = max(wing - net_credit, 0.0) * MULTIPLIER
    base_lots = _kelly_base_lots(equity, margin_per, prior_p, kelly_max_f, kelly_max_lots)
    call_lots, put_lots = _skew_lots(lsp_score, max(base_lots, 1) if base_lots > 0 else 0, max_skew)
    if base_lots <= 0:
        call_lots, put_lots = 0, 0
    inside = (spot <= call_wall * (1.0 - wall_buf)) and (spot >= put_wall * (1.0 + wall_buf))
    g.bar_index = int(g.bar_index) + 1

    sc_qty = float(get_position(g.short_call).amount or 0.0)
    sp_qty = float(get_position(g.short_put).amount or 0.0)
    lc_qty = float(get_position(g.long_call).amount or 0.0)
    lp_qty = float(get_position(g.long_put).amount or 0.0)
    g.in_trade = sc_qty < 0 or sp_qty < 0

    if g.in_trade:
        order_target(g.short_call, -float(call_lots), reason="lsp_skew_short_call")
        order_target(g.short_put, -float(put_lots), reason="lsp_skew_short_put")
        order_target(g.long_call, float(call_lots), reason="match_long_call_wing")
        order_target(g.long_put, float(put_lots), reason="match_long_put_wing")
        und_qty = float(get_position(g.underlying_symbol).amount or 0.0)
        if abs(und_qty) > 1e-9:
            order_target(g.underlying_symbol, 0, reason="flatten_unwanted_spot")

        held = int(g.bar_index) - int(g.entry_bar)
        close_debit = (sc + sp - lc - lp) * MULTIPLIER * max(call_lots, put_lots, 1)
        mtm = float(g.entry_credit_cash) - close_debit
        take_ok = g.entry_credit_cash > 0 and close_debit <= g.entry_credit_cash * (1.0 - take_profit)
        stop_ok = g.max_risk > 0 and mtm <= -stop_loss * g.max_risk
        breach = spot >= call_wall * (1.0 + wall_buf) or spot <= put_wall * (1.0 - wall_buf)
        if held >= max_hold or breach or take_ok or stop_ok:
            for sym, reason in (
                (g.short_call, "exit_flat_short_call"),
                (g.short_put, "exit_flat_short_put"),
                (g.long_call, "exit_flat_long_call"),
                (g.long_put, "exit_flat_long_put"),
                (g.underlying_symbol, "exit_flat_spot"),
            ):
                order_target(sym, 0, reason=reason)
            g.in_trade = False
            g.entry_bar = -1
        return

    flat = abs(sc_qty) < 1e-9 and abs(sp_qty) < 1e-9 and abs(lc_qty) < 1e-9 and abs(lp_qty) < 1e-9
    if inside and high_iv_ok and flat and (call_lots + put_lots) > 0 and net_credit > 0:
        order_target(g.short_call, -float(call_lots), reason="short_call_iron_condor")
        order_target(g.short_put, -float(put_lots), reason="short_put_iron_condor")
        order_target(g.long_call, float(call_lots), reason="long_call_wing")
        order_target(g.long_put, float(put_lots), reason="long_put_wing")
        order_target(g.underlying_symbol, 0, reason="no_spot_hedge")
        g.entry_credit_cash = net_credit * MULTIPLIER * max(call_lots, put_lots)
        g.max_risk = margin_per * max(call_lots, put_lots)
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


def _iv_rank_proxy(hist):
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


def _kelly_base_lots(equity, margin_per_lot, win_prob, max_fraction, max_lots):
    p = float(win_prob)
    raw = 2.0 * p - 1.0
    if raw <= 0 or equity <= 0 or max_lots <= 0 or margin_per_lot <= 0:
        return 0
    fraction = min(raw, float(max_fraction))
    lots = int((equity * fraction) // float(margin_per_lot))
    return int(min(max(lots, 0), int(max_lots)))
