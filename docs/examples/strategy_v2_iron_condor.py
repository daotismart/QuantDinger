"""Iron Condor on CN 510050 ETF Options
Weekly short iron condor: sell OTM put spread plus OTM call spread on 510050 ETF
options. Entries on Monday when flat; exits on profit target, stop loss, or DTE.
Synthetic backtests use the four CNIndexOptions leg keys below with matching OHLCV.
"""

import datetime
import math

# @param contracts int 1 Number of spreads per side (lots) range=1:10:1
# @param put_otm_pct float 0.03 Short put distance below spot range=0.01:0.10:0.005
# @param call_otm_pct float 0.03 Short call distance above spot range=0.01:0.10:0.005
# @param wing_width float 0.10 Wing width in underlying price units range=0.05:0.30:0.05
# @param profit_target_pct float 0.50 Close at this fraction of max credit range=0.25:0.80:0.05
# @param stop_loss_mult float 2.0 Stop when loss exceeds this multiple of credit range=1.0:4.0:0.5
# @param min_credit float 0.04 Minimum net credit to open range=0.01:0.20:0.01
# @param min_entry_dte int 21 Earliest DTE to open a new condor range=7:45:1
# @param max_entry_dte int 45 Latest DTE to open a new condor range=14:90:1
# @param exit_dte int 7 Force exit when DTE falls below this range=1:21:1
# @param vol_lookback int 20 Realized-vol window in bars range=5:60:1
# @param max_realized_vol float 0.35 Skip entry when annualized vol exceeds this range=0.15:0.60:0.05
# @param strike_step float 0.05 Strike rounding grid range=0.01:0.10:0.01
# @param expiry_year int 2026 Option expiry year range=2024:2030:1
# @param expiry_month int 3 Option expiry month range=1:12:1
# @param expiry_day int 25 Option expiry day range=1:31:1

PERSIST_RUNTIME_STATE = True

UNDERLYING_SYMBOL = "CNStock:510050.SH"
PUT_LONG_SYMBOL = "CNIndexOptions:90000001"
PUT_SHORT_SYMBOL = "CNIndexOptions:90000002"
CALL_SHORT_SYMBOL = "CNIndexOptions:90000003"
CALL_LONG_SYMBOL = "CNIndexOptions:90000004"
BAR_FREQUENCY = "1d"
TRADING_DAYS_PER_YEAR = 244


def initialize(context):
    g.underlying = UNDERLYING_SYMBOL
    g.put_long = PUT_LONG_SYMBOL
    g.put_short = PUT_SHORT_SYMBOL
    g.call_short = CALL_SHORT_SYMBOL
    g.call_long = CALL_LONG_SYMBOL
    g.legs = [g.put_long, g.put_short, g.call_short, g.call_long]
    g.entry_credit = 0.0
    g.max_credit = 0.0
    g.entry_tag = ""
    context.set_universe([g.underlying] + g.legs)
    context.set_benchmark(g.underlying)
    context.subscribe(
        frequency=BAR_FREQUENCY,
        fields=["open", "high", "low", "close", "volume"],
    )
    context.set_warmup(30)
    context.set_metadata(
        direction_mode="both",
        strategy_family="iron_condor",
    )
    run_weekly(_try_open_condor, weekday=1, time="09:35")


def handle_data(context, data):
    if not is_trade():
        return
    if context.current_dt is None:
        return
    if not _has_open_legs(context):
        return

    profit_target_pct = _param_float(context.params.get("profit_target_pct", 0.50), 0.50)
    stop_loss_mult = _param_float(context.params.get("stop_loss_mult", 2.0), 2.0)
    exit_dte = max(int(context.params.get("exit_dte", 7) or 7), 0)

    credit = max(float(g.max_credit or 0.0), 1e-6)
    pnl = _mark_pnl(context, data)
    dte = _days_to_expiry(context)

    reason = ""
    if pnl >= profit_target_pct * credit:
        reason = "ic_profit_target"
    elif pnl <= -stop_loss_mult * credit:
        reason = "ic_stop_loss"
    elif dte <= exit_dte:
        reason = "ic_dte_exit"

    if reason:
        _close_all(context, data, reason)


def _try_open_condor(context, data):
    if not is_trade():
        return
    if context.current_dt is None:
        return
    if _has_open_legs(context):
        return

    contracts = max(int(context.params.get("contracts", 1) or 1), 1)
    put_otm_pct = max(_param_float(context.params.get("put_otm_pct", 0.03), 0.03), 0.0)
    call_otm_pct = max(_param_float(context.params.get("call_otm_pct", 0.03), 0.03), 0.0)
    wing_width = max(_param_float(context.params.get("wing_width", 0.10), 0.10), 0.01)
    min_credit = max(_param_float(context.params.get("min_credit", 0.04), 0.04), 0.0)
    min_entry_dte = max(int(context.params.get("min_entry_dte", 21) or 21), 1)
    max_entry_dte = max(int(context.params.get("max_entry_dte", 45) or 45), min_entry_dte)
    vol_lookback = max(int(context.params.get("vol_lookback", 20) or 20), 5)
    max_realized_vol = max(_param_float(context.params.get("max_realized_vol", 0.35), 0.35), 0.0)
    strike_step = max(_param_float(context.params.get("strike_step", 0.05), 0.05), 0.01)

    dte = _days_to_expiry(context)
    if dte < min_entry_dte or dte > max_entry_dte:
        return

    spot = float(data.current(g.underlying, "close") or 0.0)
    if spot <= strike_step:
        return

    und_bars = get_history(vol_lookback + 1, BAR_FREQUENCY, "close", g.underlying)
    if len(und_bars) < vol_lookback:
        return
    realized_vol = _realized_vol(und_bars["close"].tolist(), vol_lookback)
    if realized_vol > max_realized_vol:
        return

    put_short_k = _round_strike(spot * (1.0 - put_otm_pct), strike_step)
    put_long_k = _round_strike(put_short_k - wing_width, strike_step)
    call_short_k = _round_strike(spot * (1.0 + call_otm_pct), strike_step)
    call_long_k = _round_strike(call_short_k + wing_width, strike_step)
    if put_long_k <= 0.0 or put_short_k <= put_long_k or call_long_k <= call_short_k:
        return

    put_long_px = float(data.current(g.put_long, "close") or 0.0)
    put_short_px = float(data.current(g.put_short, "close") or 0.0)
    call_short_px = float(data.current(g.call_short, "close") or 0.0)
    call_long_px = float(data.current(g.call_long, "close") or 0.0)
    if min(put_long_px, put_short_px, call_short_px, call_long_px) <= 0.0:
        return

    est_credit = (put_short_px - put_long_px) + (call_short_px - call_long_px)
    if est_credit < min_credit:
        return

    tag = _as_naive_datetime(context.current_dt).strftime("%Y%m%d")
    g.entry_tag = tag
    g.max_credit = est_credit * float(contracts)
    g.entry_credit = 0.0

    order_target(
        g.put_long,
        float(contracts),
        client_order_id=("ic-pl-" + tag)[:100],
        reason="ic_open_put_long",
    )
    order_target(
        g.put_short,
        -float(contracts),
        client_order_id=("ic-ps-" + tag)[:100],
        reason="ic_open_put_short",
    )
    order_target(
        g.call_short,
        -float(contracts),
        client_order_id=("ic-cs-" + tag)[:100],
        reason="ic_open_call_short",
    )
    order_target(
        g.call_long,
        float(contracts),
        client_order_id=("ic-cl-" + tag)[:100],
        reason="ic_open_call_long",
    )


def _close_all(context, data, reason):
    tag = str(g.entry_tag or "x")
    close_tag = _as_naive_datetime(context.current_dt).strftime("%Y%m%d")
    for leg, prefix in (
        (g.put_long, "ic-xpl"),
        (g.put_short, "ic-xps"),
        (g.call_short, "ic-xcs"),
        (g.call_long, "ic-xcl"),
    ):
        pos = get_position(leg)
        if abs(float(pos.amount or 0.0)) <= 1e-9:
            continue
        order_target(
            leg,
            0.0,
            client_order_id=(prefix + "-" + close_tag)[:100],
            reason=reason,
        )
    g.entry_credit = 0.0
    g.max_credit = 0.0
    g.entry_tag = ""


def _has_open_legs(context):
    for leg in g.legs:
        if abs(float(get_position(leg).amount or 0.0)) > 1e-9:
            return True
    return False


def _mark_pnl(context, data):
    total = 0.0
    for leg in g.legs:
        pos = get_position(leg)
        amount = float(pos.amount or 0.0)
        if abs(amount) <= 1e-9:
            continue
        mark = float(data.current(leg, "close") or pos.last_price or pos.avg_cost or 0.0)
        avg = float(pos.avg_cost or 0.0)
        total += amount * (mark - avg)
    return total


def _days_to_expiry(context):
    now = _as_naive_datetime(context.current_dt)
    if now is None:
        return 0
    year = max(int(context.params.get("expiry_year", 2026) or 2026), 2000)
    month = min(max(int(context.params.get("expiry_month", 3) or 3), 1), 12)
    day = min(max(int(context.params.get("expiry_day", 25) or 25), 1), 31)
    try:
        expiry = datetime.datetime(year, month, day)
    except ValueError:
        expiry = datetime.datetime(year, month, 28)
    delta = (expiry.date() - now.date()).days
    return max(int(delta), 0)


def _realized_vol(closes, lookback):
    samples = []
    for value in closes[-(lookback + 1) :]:
        try:
            px = float(value)
        except Exception:
            continue
        if px > 0.0:
            samples.append(px)
    if len(samples) < 3:
        return 0.0
    returns = []
    for idx in range(1, len(samples)):
        prev = samples[idx - 1]
        curr = samples[idx]
        if prev > 0.0 and curr > 0.0:
            returns.append(math.log(curr / prev))
    if len(returns) < 2:
        return 0.0
    mean = sum(returns) / float(len(returns))
    var = sum((item - mean) ** 2 for item in returns) / float(max(len(returns) - 1, 1))
    return math.sqrt(max(var, 0.0)) * math.sqrt(float(TRADING_DAYS_PER_YEAR))


def _round_strike(value, step):
    if step <= 0.0:
        return float(value)
    units = round(float(value) / step)
    return units * step


def _param_float(value, default):
    try:
        number = float(value)
    except Exception:
        return float(default)
    if not math.isfinite(number):
        return float(default)
    return number


def _as_naive_datetime(value):
    if value is None:
        return None
    if isinstance(value, datetime.datetime):
        if value.tzinfo is not None:
            return value.replace(tzinfo=None)
        return value
    return None
