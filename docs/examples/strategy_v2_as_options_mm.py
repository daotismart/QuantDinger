"""AS Options Market Maker
Bar-based Avellaneda-Stoikov quotes on a CN soybean-meal call, with Black-76
greeks, inventory plus net-delta skew, gamma/vega widening, realized-vol or IV,
toxicity, tick/fee floors, inventory caps, cancel-replace, and optional delta hedge.

Universe is source-owned: CNFuturesOptions:M2609-C-2800 quoted against CNFutures:M2609
on 5-minute bars. Selling options requires direction_mode=both. This is not a
tick engine; quotes refresh on completed bars and rest until the next bar open.
"""

import datetime
import math
import statistics

# @param tick_size float 0.5 Option price tick range=0.1:5:0.1
# @param quote_lots int 1 Size of each bid/ask quote in lots range=1:20:1
# @param max_inventory int 5 Max |option lots| before one-sided quoting range=1:50:1
# @param gamma float 0.1 AS risk aversion range=0.01:1:0.01
# @param k_intensity float 1.5 AS order-intensity k range=0.1:10:0.1
# @param inventory_skew float 0.5 Extra reservation shift per option lot range=0:5:0.1
# @param gamma_delta float 0.05 Extra reservation shift per net delta-lot range=0:2:0.01
# @param min_ticks int 2 Minimum full spread in ticks range=1:20:1
# @param fee_floor float 0.5 Half-spread fee floor in price units range=0:10:0.1
# @param vol_lookback int 48 Realized-vol window in bars range=10:200:1
# @param implied_vol float 0.0 Underlying IV override; 0 uses realized vol range=0:2:0.01
# @param gamma_widen float 0.5 Extra half-spread from option gamma range=0:5:0.1
# @param vega_widen float 0.05 Extra half-spread from option vega range=0:2:0.01
# @param tox_lambda float 0.2 EWMA weight on |delta mid| range=0.01:1:0.01
# @param tox_widen float 1.0 Toxicity multiplier on the EWMA range=0:10:0.1
# @param horizon_years float 1.0 AS inventory horizon in years range=0.01:2:0.01
# @param max_half_spread_frac float 0.15 Cap half-spread as a fraction of mid range=0.02:0.5:0.01
# @param enable_delta_hedge bool false Hedge net option delta in the underlying
# @param hedge_every_n_bars int 6 Bars between delta-hedge rebalances range=1:48:1

PERSIST_RUNTIME_STATE = True

OPTION_SYMBOL = "CNFuturesOptions:M2609-C-2800"
UNDERLYING_SYMBOL = "CNFutures:M2609"
BAR_FREQUENCY = "5m"
# 5-minute CN futures: ~72 tradable bars per session-day, 244 session-days.
BARS_PER_YEAR = 244 * 72
MIN_TTE_YEARS = 0.02
SIGMA_FLOOR = 0.05
SIGMA_CAP = 2.0
DEFAULT_SIGMA = 0.20


def initialize(context):
    g.option_symbol = OPTION_SYMBOL
    g.underlying_symbol = UNDERLYING_SYMBOL
    g.bid_oid = ""
    g.ask_oid = ""
    g.hedge_oid = ""
    g.last_mid = 0.0
    g.toxicity = 0.0
    g.bar_index = 0
    context.set_universe([g.option_symbol, g.underlying_symbol])
    context.set_benchmark(g.underlying_symbol)
    context.subscribe(
        frequency=BAR_FREQUENCY,
        fields=["open", "high", "low", "close", "volume"],
    )
    context.set_warmup(60)
    context.set_metadata(
        direction_mode="both",
        strategy_family="options_market_making",
    )


def handle_data(context, data):
    if not is_trade():
        return
    if context.current_dt is None:
        return

    tick_size = max(_param_float(context.params.get("tick_size", 0.5), 0.5), 1e-6)
    quote_lots = max(int(context.params.get("quote_lots", 1) or 1), 1)
    max_inventory = max(int(context.params.get("max_inventory", 5) or 5), 1)
    gamma = max(_param_float(context.params.get("gamma", 0.1), 0.1), 1e-6)
    k_intensity = max(_param_float(context.params.get("k_intensity", 1.5), 1.5), 1e-6)
    inventory_skew = _param_float(context.params.get("inventory_skew", 0.5), 0.5)
    gamma_delta = _param_float(context.params.get("gamma_delta", 0.05), 0.05)
    min_ticks = max(int(context.params.get("min_ticks", 2) or 2), 1)
    fee_floor = max(_param_float(context.params.get("fee_floor", 0.5), 0.5), 0.0)
    vol_lookback = max(int(context.params.get("vol_lookback", 48) or 48), 8)
    implied_vol = max(_param_float(context.params.get("implied_vol", 0.0), 0.0), 0.0)
    gamma_widen = max(_param_float(context.params.get("gamma_widen", 0.5), 0.5), 0.0)
    vega_widen = max(_param_float(context.params.get("vega_widen", 0.05), 0.05), 0.0)
    tox_lambda = min(max(_param_float(context.params.get("tox_lambda", 0.2), 0.2), 0.0), 1.0)
    tox_widen = max(_param_float(context.params.get("tox_widen", 1.0), 1.0), 0.0)
    horizon_years = max(_param_float(context.params.get("horizon_years", 1.0), 1.0), 1e-4)
    max_half_spread_frac = max(
        _param_float(context.params.get("max_half_spread_frac", 0.15), 0.15),
        0.01,
    )
    enable_delta_hedge = _param_bool(context.params.get("enable_delta_hedge", False), False)
    hedge_every_n_bars = max(int(context.params.get("hedge_every_n_bars", 6) or 6), 1)

    _cancel_working(g.bid_oid)
    _cancel_working(g.ask_oid)
    g.bid_oid = ""
    g.ask_oid = ""

    und_bars = get_history(vol_lookback + 2, BAR_FREQUENCY, "close", g.underlying_symbol)
    opt_bars = get_history(3, BAR_FREQUENCY, "close", g.option_symbol)
    if len(und_bars) < 8 or len(opt_bars) < 1:
        return

    mid = float(data.current(g.option_symbol, "close"))
    futures_px = float(data.current(g.underlying_symbol, "close"))
    if mid <= tick_size or futures_px <= 0.0:
        return

    if g.last_mid > 0.0:
        g.toxicity = (1.0 - tox_lambda) * float(g.toxicity) + tox_lambda * abs(mid - g.last_mid)
    g.last_mid = mid
    g.bar_index = int(g.bar_index) + 1

    spec = _parse_cn_option_spec(g.option_symbol)
    strike = spec["strike"] if spec["strike"] > 0.0 else futures_px
    tte = _years_to_expiry(context.current_dt, spec["year"], spec["month"], MIN_TTE_YEARS)
    closes = [float(value) for value in und_bars["close"].tolist() if float(value) > 0.0]
    realized = _realized_sigma(closes, BARS_PER_YEAR)
    sigma_f = implied_vol if implied_vol > 0.0 else realized
    if sigma_f <= 0.0:
        sigma_f = DEFAULT_SIGMA
    sigma_f = min(max(sigma_f, SIGMA_FLOOR), SIGMA_CAP)

    option_pos = get_position(g.option_symbol)
    underlying_pos = get_position(g.underlying_symbol)
    q_opt = float(option_pos.amount or 0.0)
    q_und = float(underlying_pos.amount or 0.0)

    quotes = _as_option_quotes(
        mid=mid,
        futures_px=futures_px,
        strike=strike,
        is_call=spec["is_call"],
        tte=tte,
        horizon=horizon_years,
        sigma_f=sigma_f,
        q_opt=q_opt,
        q_und=q_und,
        tick=tick_size,
        gamma=gamma,
        gamma_delta=gamma_delta,
        k_intensity=k_intensity,
        inventory_skew=inventory_skew,
        gamma_widen=gamma_widen,
        vega_widen=vega_widen,
        toxicity=float(g.toxicity) * tox_widen,
        min_ticks=min_ticks,
        fee_floor=fee_floor,
        max_inventory=float(max_inventory),
        max_half_spread_frac=max_half_spread_frac,
    )
    if quotes is None:
        return

    now_dt = _as_naive_datetime(context.current_dt)
    if now_dt is None:
        return
    tag = now_dt.strftime("%Y%m%d%H%M")
    if quotes["bid"] is not None:
        g.bid_oid = order(
            g.option_symbol,
            float(quote_lots),
            order_type="limit",
            limit_price=float(quotes["bid"]),
            client_order_id=("asmm-bid-" + tag)[:100],
            reason="as_mm_bid",
        ) or ""
    if quotes["ask"] is not None:
        g.ask_oid = order(
            g.option_symbol,
            -float(quote_lots),
            order_type="limit",
            limit_price=float(quotes["ask"]),
            client_order_id=("asmm-ask-" + tag)[:100],
            reason="as_mm_ask",
        ) or ""

    if enable_delta_hedge and int(g.bar_index) % hedge_every_n_bars == 0:
        target_und = -_round_lots(q_opt * float(quotes["delta"]))
        current_und = _round_lots(q_und)
        if target_und != current_und:
            g.hedge_oid = order_target(
                g.underlying_symbol,
                float(target_und),
                order_type="market",
                client_order_id=("asmm-hdg-" + tag)[:100],
                reason="as_mm_delta_hedge",
            ) or ""


def _param_float(value, default):
    try:
        number = float(value)
    except Exception:
        return float(default)
    if not math.isfinite(number):
        return float(default)
    return number


def _param_bool(value, default):
    if isinstance(value, bool):
        return value
    if value is None:
        return bool(default)
    text = str(value).strip().lower()
    if text in ("true", "1", "yes", "on"):
        return True
    if text in ("false", "0", "no", "off"):
        return False
    return bool(default)


def _cancel_working(order_id):
    if not order_id:
        return
    status = str(get_order_status(order_id)["status"] or "").strip().lower()
    if status in ("filled", "cancelled"):
        return
    cancel_order(order_id)


def _round_lots(value):
    if value >= 0.0:
        return float(int(value + 0.5))
    return float(int(value - 0.5))


def _parse_cn_option_spec(symbol):
    body = str(symbol or "").strip()
    if ":" in body:
        body = body.split(":", 1)[1]
    parts = body.split("-")
    result = {
        "root": "",
        "year": 0,
        "month": 0,
        "is_call": True,
        "strike": 0.0,
    }
    if len(parts) < 3:
        return result
    head = parts[0].strip()
    cp = parts[1].strip().upper()
    try:
        result["strike"] = float(parts[2])
    except Exception:
        result["strike"] = 0.0
    result["is_call"] = not cp.startswith("P")
    digits = []
    root_chars = []
    started = False
    for ch in head:
        if ch.isdigit():
            started = True
            digits.append(ch)
        elif not started:
            root_chars.append(ch)
        else:
            break
    digit_str = "".join(digits)
    result["root"] = "".join(root_chars)
    if len(digit_str) >= 4:
        result["year"] = 2000 + int(digit_str[:2])
        result["month"] = int(digit_str[2:4])
    return result


def _as_naive_datetime(value):
    if value is None:
        return None
    if isinstance(value, datetime.datetime):
        return datetime.datetime(
            int(value.year),
            int(value.month),
            int(value.day),
            int(value.hour),
            int(value.minute),
            int(value.second),
        )
    if isinstance(value, datetime.date):
        return datetime.datetime(int(value.year), int(value.month), int(value.day))
    if hasattr(value, "year") and hasattr(value, "month") and hasattr(value, "day"):
        hour = int(value.hour) if hasattr(value, "hour") else 0
        minute = int(value.minute) if hasattr(value, "minute") else 0
        second = int(value.second) if hasattr(value, "second") else 0
        try:
            return datetime.datetime(
                int(value.year),
                int(value.month),
                int(value.day),
                hour,
                minute,
                second,
            )
        except Exception:
            return None
    text = str(value).strip()
    if not text:
        return None
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.datetime.fromisoformat(text)
    except Exception:
        return None
    return datetime.datetime(
        parsed.year,
        parsed.month,
        parsed.day,
        parsed.hour,
        parsed.minute,
        parsed.second,
    )


def _years_to_expiry(now, year, month, min_years):
    floor = max(float(min_years), 1e-4)
    if year < 1990 or month < 1 or month > 12:
        return floor
    now_dt = _as_naive_datetime(now)
    if now_dt is None:
        return floor
    try:
        expiry = datetime.datetime(int(year), int(month), 5)
    except Exception:
        return floor
    seconds = (expiry - now_dt).total_seconds()
    return max(seconds / (365.0 * 24.0 * 3600.0), floor)


def _realized_sigma(closes, bars_per_year):
    returns = []
    previous = None
    for price in closes:
        if previous is not None and previous > 0.0 and price > 0.0:
            returns.append(math.log(price / previous))
        previous = price
    if len(returns) < 2:
        return 0.0
    try:
        sigma_bar = statistics.stdev(returns)
    except Exception:
        return 0.0
    return float(sigma_bar) * math.sqrt(max(float(bars_per_year), 1.0))


def _norm_pdf(value):
    return math.exp(-0.5 * value * value) / math.sqrt(2.0 * math.pi)


def _norm_cdf(value):
    return 0.5 * (1.0 + math.erf(value / math.sqrt(2.0)))


def _black76_d1_d2(futures_px, strike, tte, sigma):
    futures_px = max(float(futures_px), 1e-12)
    strike = max(float(strike), 1e-12)
    tte = max(float(tte), 1e-8)
    sigma = max(float(sigma), 1e-8)
    vol_sqrt = sigma * math.sqrt(tte)
    d1 = (math.log(futures_px / strike) + 0.5 * sigma * sigma * tte) / vol_sqrt
    d2 = d1 - vol_sqrt
    return d1, d2


def _black76_delta(futures_px, strike, tte, sigma, is_call):
    d1, _d2 = _black76_d1_d2(futures_px, strike, tte, sigma)
    call_delta = _norm_cdf(d1)
    if is_call:
        return call_delta
    return call_delta - 1.0


def _black76_gamma(futures_px, strike, tte, sigma):
    d1, _d2 = _black76_d1_d2(futures_px, strike, tte, sigma)
    denom = max(float(futures_px), 1e-12) * max(float(sigma), 1e-8) * math.sqrt(max(float(tte), 1e-8))
    return _norm_pdf(d1) / denom


def _black76_vega(futures_px, strike, tte, sigma):
    d1, _d2 = _black76_d1_d2(futures_px, strike, tte, sigma)
    return max(float(futures_px), 0.0) * _norm_pdf(d1) * math.sqrt(max(float(tte), 1e-8))


def _floor_tick(price, tick):
    if tick <= 0.0:
        return price
    units = math.floor(price / tick + 1e-12)
    return max(tick, units * tick)


def _ceil_tick(price, tick):
    if tick <= 0.0:
        return price
    units = math.ceil(price / tick - 1e-12)
    return max(tick, units * tick)


def _as_option_quotes(
    mid,
    futures_px,
    strike,
    is_call,
    tte,
    horizon,
    sigma_f,
    q_opt,
    q_und,
    tick,
    gamma,
    gamma_delta,
    k_intensity,
    inventory_skew,
    gamma_widen,
    vega_widen,
    toxicity,
    min_ticks,
    fee_floor,
    max_inventory,
    max_half_spread_frac,
):
    if mid <= 0.0 or futures_px <= 0.0 or tick <= 0.0:
        return None

    delta = _black76_delta(futures_px, strike, tte, sigma_f, is_call)
    opt_gamma = _black76_gamma(futures_px, strike, tte, sigma_f)
    opt_vega = _black76_vega(futures_px, strike, tte, sigma_f)
    q_delta = float(q_opt) * float(delta) + float(q_und)

    vol_term = float(gamma) * float(sigma_f) * float(sigma_f) * float(horizon)
    reservation = (
        float(mid)
        - float(q_opt) * (float(inventory_skew) + vol_term)
        - q_delta * float(gamma_delta) * tick
    )

    intensity = max(float(k_intensity), 1e-8)
    aversion = max(float(gamma), 1e-8)
    as_half = 0.5 * (
        vol_term + (2.0 / aversion) * math.log(1.0 + aversion / intensity)
    )
    gamma_add = float(gamma_widen) * abs(opt_gamma) * float(futures_px) * float(tick)
    vega_add = float(vega_widen) * (opt_vega / 100.0) * float(tick)
    half = as_half + gamma_add + vega_add + max(float(toxicity), 0.0) + max(float(fee_floor), 0.0)
    min_half = max(int(min_ticks), 1) * float(tick) * 0.5
    cap = max(float(max_half_spread_frac) * float(mid), min_half)
    half = min(max(half, min_half), cap)

    bid = _floor_tick(reservation - half, tick)
    ask = _ceil_tick(reservation + half, tick)
    guard = 0
    while bid >= ask - 1e-12 and guard < 32:
        bid = _floor_tick(bid - tick, tick)
        ask = _ceil_tick(ask + tick, tick)
        guard += 1
    if bid <= 0.0:
        bid = None
    if ask <= 0.0:
        return None
    if bid is not None and ask <= bid:
        return None

    place_bid = float(q_opt) < float(max_inventory) - 1e-12
    place_ask = float(q_opt) > -float(max_inventory) + 1e-12
    return {
        "reservation": reservation,
        "half_spread": half,
        "bid": bid if place_bid else None,
        "ask": ask if place_ask else None,
        "delta": delta,
        "gamma": opt_gamma,
        "vega": opt_vega,
        "sigma": float(sigma_f),
        "tte": float(tte),
        "q_delta": q_delta,
    }
