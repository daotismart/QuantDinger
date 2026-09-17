-- Strategy API V2 advanced pack seed (5 packs x 10 variants = 50 strategies)

INSERT INTO qd_script_templates
(template_key, asset_type, title, description, code, param_schema, tags, icon, accent, sort_order, is_active, metadata, updated_at)
VALUES
('strategy_v2_stat_arb_pack', 'portfolio_strategy', 'Statistical Arbitrage Pack', 'Z-score, spread, and ratio mean-reversion on SA701 futures vs options.', $statpack$"""
Statistical Arbitrage Pack
Z-score, spread, and ratio mean-reversion on SA701 futures vs options.
"""

# @param variant int 0 range=0:9:1
# @param target_pct float 0.95 range=0.05:1:0.05
# @param allow_short bool true

def initialize(context):
    g.futures = "CNFutures:SA701"
    g.option = "CNFuturesOptions:SA701-C-1000"
    context.set_universe([g.futures, g.option])
    context.set_benchmark(g.futures)
    context.subscribe(frequency="1m")
    context.set_metadata(direction_mode="both")
    context.set_warmup(8000)


def handle_data(context, data):
    del data
    variant = int(context.params.get("variant", 0))
    target_pct = float(context.params.get("target_pct", 0.95))
    allow_short = bool(context.params.get("allow_short", True))

    def _agg30(bars_1m):
        o = bars_1m["open"].values
        h = bars_1m["high"].values
        l = bars_1m["low"].values
        c = bars_1m["close"].values
        v = bars_1m["volume"].values
        n = len(o)
        count = n // 30
        if count < 1:
            return None, None, None, None, None
        start = n - count * 30
        o30 = [o[start + i * 30] for i in range(count)]
        h30 = [max(h[start + i * 30: start + (i + 1) * 30]) for i in range(count)]
        l30 = [min(l[start + i * 30: start + (i + 1) * 30]) for i in range(count)]
        c30 = [c[start + (i + 1) * 30 - 1] for i in range(count)]
        v30 = [sum(v[start + i * 30: start + (i + 1) * 30]) for i in range(count)]
        return o30, h30, l30, c30, v30

    def _rolling_mean(arr, period):
        if len(arr) < period:
            return []
        return [sum(arr[i - period:i]) / period for i in range(period, len(arr) + 1)]

    def _rolling_max(arr, period):
        if len(arr) < period:
            return []
        return [max(arr[i - period:i]) for i in range(period, len(arr) + 1)]

    def _rolling_min(arr, period):
        if len(arr) < period:
            return []
        return [min(arr[i - period:i]) for i in range(period, len(arr) + 1)]

    def _rolling_std(arr, period):
        if len(arr) < period:
            return []
        out = []
        for i in range(period, len(arr) + 1):
            window = arr[i - period:i]
            m = sum(window) / period
            out.append((sum((x - m) ** 2 for x in window) / period) ** 0.5)
        return out

    bars = get_history(8000, "1m", ["open", "high", "low", "close", "volume"], g.futures)
    o30, h30, l30, c30, v30 = _agg30(bars)
    if o30 is None or len(c30) < 100:
        return

    position = get_position(g.futures)
    position_amt = float(position.amount or 0.0)
    is_long = position_amt > 1e-12
    is_short = position_amt < -1e-12
    desired = 0.0
    reason = ""
    if variant == 0:
        std20 = _rolling_std(c30, 20)
        if std20:
            z = (c30[-1] - _rolling_mean(c30, 20)[-1]) / std20[-1] if std20[-1] else 0
            if z < -1.5:
                desired = target_pct
            elif z > 1.5 and allow_short:
                desired = -target_pct
        reason = "stat_zscore_mr"
    elif variant == 1:
        std20 = _rolling_std(c30, 20)
        if std20:
            z = (c30[-1] - _rolling_mean(c30, 20)[-1]) / std20[-1] if std20[-1] else 0
            if z > 1.0:
                desired = target_pct
            elif z < -1.0 and allow_short:
                desired = -target_pct
        reason = "stat_zscore_momo"
    elif variant == 2:
        opt = get_history(8000, '1m', 'close', g.option)
        if len(opt) >= 30 and len(c30) >= 20:
            spread = [c30[i] - float(opt['close'].values[-len(c30) + i]) for i in range(len(c30))]
            mz = _rolling_mean(spread, 20)
            sz = _rolling_std(spread, 20)
            if mz and sz and sz[-1]:
                z = (spread[-1] - mz[-1]) / sz[-1]
                desired = target_pct if z < -1.2 else (-target_pct if z > 1.2 and allow_short else 0.0)
        reason = "stat_spread_z"
    elif variant == 3:
        opt = get_history(8000, '1m', 'close', g.option)
        if len(opt) >= 30:
            ratio = [c30[i] / max(1e-6, float(opt['close'].values[-len(c30) + i])) for i in range(len(c30))]
            mr = _rolling_mean(ratio, 30)
            if mr and ratio[-1] < mr[-1] * 0.995:
                desired = target_pct
            elif mr and ratio[-1] > mr[-1] * 1.005 and allow_short:
                desired = -target_pct
        reason = "stat_ratio_mr"
    elif variant == 4:
        z5 = _rolling_std(c30, 5)
        z20 = _rolling_std(c30, 20)
        if z5 and z20:
            fast = (c30[-1] - _rolling_mean(c30, 5)[-1]) / (z5[-1] or 1)
            slow = (c30[-1] - _rolling_mean(c30, 20)[-1]) / (z20[-1] or 1)
            if fast > 0 and slow > 0:
                desired = target_pct
            elif fast < 0 and slow < 0 and allow_short:
                desired = -target_pct
        reason = "stat_dual_z"
    elif variant == 5:
        if len(c30) >= 60:
            window = c30[-60:]
            rank = sum(1 for x in window if x <= c30[-1]) / len(window)
            if rank < 0.2:
                desired = target_pct
            elif rank > 0.8 and allow_short:
                desired = -target_pct
        reason = "stat_percentile_mr"
    elif variant == 6:
        ma5 = _rolling_mean(c30, 5)
        ma40 = _rolling_mean(c30, 40)
        if ma5 and ma40:
            diff = ma5[-1] - ma40[-1]
            pdiff = ma5[-2] - ma40[-2] if len(ma5) > 1 else diff
            if diff < 0 and diff > pdiff:
                desired = target_pct
            elif diff > 0 and diff < pdiff and allow_short:
                desired = -target_pct
        reason = "stat_diff_ma"
    elif variant == 7:
        if len(c30) > 40:
            r1 = c30[-1] / c30[-2] - 1
            r5 = c30[-1] / c30[-6] - 1
            if abs(r5) > abs(r1) * 2 and r5 > 0:
                desired = target_pct
            elif abs(r5) > abs(r1) * 2 and r5 < 0 and allow_short:
                desired = -target_pct
        reason = "stat_variance_ratio"
    elif variant == 8:
        rets = [c30[i] / c30[i - 1] - 1 for i in range(1, len(c30))]
        if len(rets) >= 20:
            m = sum(rets[-20:]) / 20
            if rets[-1] < m - 0.001:
                desired = target_pct
            elif rets[-1] > m + 0.001 and allow_short:
                desired = -target_pct
        reason = "stat_autocorr_mr"
    elif variant == 9:
        ma = _rolling_mean(c30, 20)
        sd = _rolling_std(c30, 20)
        if ma and sd:
            upper = ma[-1] + 2 * sd[-1]
            lower = ma[-1] - 2 * sd[-1]
            if c30[-1] <= lower:
                desired = target_pct
            elif c30[-1] >= upper and allow_short:
                desired = -target_pct
        reason = "stat_band_walk"

    if desired > 0 and not is_long:
        order_target_percent(g.futures, target_pct, reason=reason)
    elif desired < 0 and allow_short and not is_short:
        order_target_percent(g.futures, -target_pct, reason=reason)
    elif abs(desired) <= 1e-12 and (is_long or is_short):
        order_target_percent(g.futures, 0.0, reason=reason + "_exit")

$statpack$, '{"params":[{"name":"variant","type":"integer","default":0,"min":0,"max":9,"step":1,"labelKey":"strategyV2.params.variant"},{"name":"target_pct","type":"percent","default":0.95,"min":0.05,"max":1,"step":0.05,"labelKey":"strategyV2.params.targetPosition"},{"name":"allow_short","type":"boolean","default":true,"labelKey":"strategyV2.params.allowShort"}]}'::jsonb, '["strategy-v2","cta","pack","cn-futures","options","stat-arb"]'::jsonb, 'experiment', 'geekblue', 270, TRUE, '{"source":"system_seed","version":11,"apiVersion":2}'::jsonb, NOW()),
('strategy_v2_options_vol_pack', 'portfolio_strategy', 'Options Volatility Pack', 'Volatility regime and option-lead signals on SA701 futures/options.', $optvolpack$"""
Options Volatility Pack
Volatility regime and option-lead signals on SA701 futures/options.
"""

# @param variant int 0 range=0:9:1
# @param target_pct float 0.95 range=0.05:1:0.05
# @param allow_short bool true

def initialize(context):
    g.futures = "CNFutures:SA701"
    g.option = "CNFuturesOptions:SA701-C-1000"
    context.set_universe([g.futures, g.option])
    context.set_benchmark(g.futures)
    context.subscribe(frequency="1m")
    context.set_metadata(direction_mode="both")
    context.set_warmup(8000)


def handle_data(context, data):
    del data
    variant = int(context.params.get("variant", 0))
    target_pct = float(context.params.get("target_pct", 0.95))
    allow_short = bool(context.params.get("allow_short", True))

    def _agg30(bars_1m):
        o = bars_1m["open"].values
        h = bars_1m["high"].values
        l = bars_1m["low"].values
        c = bars_1m["close"].values
        v = bars_1m["volume"].values
        n = len(o)
        count = n // 30
        if count < 1:
            return None, None, None, None, None
        start = n - count * 30
        o30 = [o[start + i * 30] for i in range(count)]
        h30 = [max(h[start + i * 30: start + (i + 1) * 30]) for i in range(count)]
        l30 = [min(l[start + i * 30: start + (i + 1) * 30]) for i in range(count)]
        c30 = [c[start + (i + 1) * 30 - 1] for i in range(count)]
        v30 = [sum(v[start + i * 30: start + (i + 1) * 30]) for i in range(count)]
        return o30, h30, l30, c30, v30

    def _rolling_mean(arr, period):
        if len(arr) < period:
            return []
        return [sum(arr[i - period:i]) / period for i in range(period, len(arr) + 1)]

    def _rolling_max(arr, period):
        if len(arr) < period:
            return []
        return [max(arr[i - period:i]) for i in range(period, len(arr) + 1)]

    def _rolling_min(arr, period):
        if len(arr) < period:
            return []
        return [min(arr[i - period:i]) for i in range(period, len(arr) + 1)]

    def _rolling_std(arr, period):
        if len(arr) < period:
            return []
        out = []
        for i in range(period, len(arr) + 1):
            window = arr[i - period:i]
            m = sum(window) / period
            out.append((sum((x - m) ** 2 for x in window) / period) ** 0.5)
        return out

    bars = get_history(8000, "1m", ["open", "high", "low", "close", "volume"], g.futures)
    o30, h30, l30, c30, v30 = _agg30(bars)
    if o30 is None or len(c30) < 100:
        return

    position = get_position(g.futures)
    position_amt = float(position.amount or 0.0)
    is_long = position_amt > 1e-12
    is_short = position_amt < -1e-12
    desired = 0.0
    reason = ""
    if variant == 0:
        opt = get_history(8000, '1m', ['close', 'volume'], g.option)
        if len(opt) >= 30:
            fv = float(opt['volume'].values[-1] or 0)
            ratio = fv / max(1.0, float(v30[-1]))
            avg = sum(float(x) for x in opt['volume'].values[-30:]) / 30
            if ratio > 1.5 and c30[-1] > c30[-2]:
                desired = target_pct
            elif ratio > 1.5 and c30[-1] < c30[-2] and allow_short:
                desired = -target_pct
        reason = "opt_vol_ratio"
    elif variant == 1:
        opt = get_history(8000, '1m', 'close', g.option)
        if len(opt) >= 5:
            oc = opt['close'].values
            if float(oc[-1]) > float(oc[-2]) and c30[-1] <= c30[-2]:
                desired = target_pct
            elif float(oc[-1]) < float(oc[-2]) and c30[-1] >= c30[-2] and allow_short:
                desired = -target_pct
        reason = "opt_lead"
    elif variant == 2:
        opt = get_history(8000, '1m', 'close', g.option)
        if len(opt) >= 20:
            ov = [abs(float(opt['close'].values[-len(c30) + i]) - c30[i]) for i in range(max(0, len(c30)-20), len(c30))]
            if ov and ov[-1] > sum(ov) / len(ov) * 1.2:
                desired = target_pct if c30[-1] > c30[-2] else (-target_pct if allow_short else 0.0)
        reason = "opt_straddle_proxy"
    elif variant == 3:
        opt = get_history(8000, '1m', 'close', g.option)
        if len(opt) >= 10:
            oc = [float(x) for x in opt['close'].values[-10:]]
            if oc[-1] > oc[0] * 1.01:
                desired = target_pct
            elif oc[-1] < oc[0] * 0.99 and allow_short:
                desired = -target_pct
        reason = "opt_iv_momo"
    elif variant == 4:
        opt = get_history(8000, '1m', 'close', g.option)
        if len(opt) >= 2:
            skew = float(opt['close'].values[-1]) / max(1e-6, c30[-1])
            skew_prev = float(opt['close'].values[-2]) / max(1e-6, c30[-2])
            if skew < skew_prev:
                desired = target_pct
            elif skew > skew_prev and allow_short:
                desired = -target_pct
        reason = "opt_skew_proxy"
    elif variant == 5:
        rng = [h30[i] - l30[i] for i in range(len(h30))]
        if len(rng) >= 20:
            if rng[-1] > sum(rng[-20:]) / 20 * 1.3:
                desired = target_pct if c30[-1] > o30[-1] else (-target_pct if allow_short else 0.0)
        reason = "opt_vol_break"
    elif variant == 6:
        opt = get_history(8000, '1m', 'close', g.option)
        if len(opt) >= 3:
            accel = float(opt['close'].values[-1]) - 2 * float(opt['close'].values[-2]) + float(opt['close'].values[-3])
            desired = target_pct if accel > 0 else (-target_pct if accel < 0 and allow_short else 0.0)
        reason = "opt_gamma_proxy"
    elif variant == 7:
        std20 = _rolling_std(c30, 20)
        if std20 and std20[-1] < sum(std20[-20:]) / min(20, len(std20)) * 0.8:
            desired = 0.0
        elif std20 and c30[-1] > _rolling_mean(c30, 20)[-1]:
            desired = target_pct
        reason = "opt_vega_flat"
    elif variant == 8:
        opt = get_history(8000, '1m', 'close', g.option)
        if len(opt) >= 2:
            beta = (float(opt['close'].values[-1]) - float(opt['close'].values[-2])) / max(1e-6, c30[-1] - c30[-2])
            if beta > 1.2:
                desired = target_pct
            elif beta < 0.8 and allow_short:
                desired = -target_pct
        reason = "opt_delta_hedge"
    elif variant == 9:
        rng = [h30[i] - l30[i] for i in range(len(h30))]
        mr = _rolling_mean(rng, 20)
        if mr and rng[-1] < mr[-1] * 0.85:
            desired = target_pct if c30[-1] > c30[-5] else 0.0
        elif mr and rng[-1] > mr[-1] * 1.15 and allow_short:
            desired = -target_pct
        reason = "opt_vol_mean_rev"

    if desired > 0 and not is_long:
        order_target_percent(g.futures, target_pct, reason=reason)
    elif desired < 0 and allow_short and not is_short:
        order_target_percent(g.futures, -target_pct, reason=reason)
    elif abs(desired) <= 1e-12 and (is_long or is_short):
        order_target_percent(g.futures, 0.0, reason=reason + "_exit")

$optvolpack$, '{"params":[{"name":"variant","type":"integer","default":0,"min":0,"max":9,"step":1,"labelKey":"strategyV2.params.variant"},{"name":"target_pct","type":"percent","default":0.95,"min":0.05,"max":1,"step":0.05,"labelKey":"strategyV2.params.targetPosition"},{"name":"allow_short","type":"boolean","default":true,"labelKey":"strategyV2.params.allowShort"}]}'::jsonb, '["strategy-v2","cta","pack","cn-futures","options","options-vol"]'::jsonb, 'experiment', 'volcano', 280, TRUE, '{"source":"system_seed","version":11,"apiVersion":2}'::jsonb, NOW()),
('strategy_v2_session_alpha_pack', 'portfolio_strategy', 'Session Alpha Pack', 'Day/night session momentum and open-drive patterns on 30m bars.', $sesspack$"""
Session Alpha Pack
Day/night session momentum and open-drive patterns on 30m bars.
"""

# @param variant int 0 range=0:9:1
# @param target_pct float 0.95 range=0.05:1:0.05
# @param allow_short bool true

def initialize(context):
    g.futures = "CNFutures:SA701"
    g.option = "CNFuturesOptions:SA701-C-1000"
    context.set_universe([g.futures, g.option])
    context.set_benchmark(g.futures)
    context.subscribe(frequency="1m")
    context.set_metadata(direction_mode="both")
    context.set_warmup(8000)


def handle_data(context, data):
    del data
    variant = int(context.params.get("variant", 0))
    target_pct = float(context.params.get("target_pct", 0.95))
    allow_short = bool(context.params.get("allow_short", True))

    def _agg30(bars_1m):
        o = bars_1m["open"].values
        h = bars_1m["high"].values
        l = bars_1m["low"].values
        c = bars_1m["close"].values
        v = bars_1m["volume"].values
        n = len(o)
        count = n // 30
        if count < 1:
            return None, None, None, None, None
        start = n - count * 30
        o30 = [o[start + i * 30] for i in range(count)]
        h30 = [max(h[start + i * 30: start + (i + 1) * 30]) for i in range(count)]
        l30 = [min(l[start + i * 30: start + (i + 1) * 30]) for i in range(count)]
        c30 = [c[start + (i + 1) * 30 - 1] for i in range(count)]
        v30 = [sum(v[start + i * 30: start + (i + 1) * 30]) for i in range(count)]
        return o30, h30, l30, c30, v30

    def _rolling_mean(arr, period):
        if len(arr) < period:
            return []
        return [sum(arr[i - period:i]) / period for i in range(period, len(arr) + 1)]

    def _rolling_max(arr, period):
        if len(arr) < period:
            return []
        return [max(arr[i - period:i]) for i in range(period, len(arr) + 1)]

    def _rolling_min(arr, period):
        if len(arr) < period:
            return []
        return [min(arr[i - period:i]) for i in range(period, len(arr) + 1)]

    def _rolling_std(arr, period):
        if len(arr) < period:
            return []
        out = []
        for i in range(period, len(arr) + 1):
            window = arr[i - period:i]
            m = sum(window) / period
            out.append((sum((x - m) ** 2 for x in window) / period) ** 0.5)
        return out

    bars = get_history(8000, "1m", ["open", "high", "low", "close", "volume"], g.futures)
    o30, h30, l30, c30, v30 = _agg30(bars)
    if o30 is None or len(c30) < 100:
        return

    position = get_position(g.futures)
    position_amt = float(position.amount or 0.0)
    is_long = position_amt > 1e-12
    is_short = position_amt < -1e-12
    desired = 0.0
    reason = ""
    if variant == 0:
        if len(c30) >= 3:
            drive = c30[-1] - o30[-1]
            desired = target_pct if drive > 0 else (-target_pct if drive < 0 and allow_short else 0.0)
        reason = "sess_open_drive"
    elif variant == 1:
        if len(c30) >= 4:
            fh = c30[-1] - c30[-4]
            desired = target_pct if fh > 0 else (-target_pct if fh < 0 and allow_short else 0.0)
        reason = "sess_first_hour"
    elif variant == 2:
        if len(c30) >= 6:
            if c30[-3] > c30[-6] and c30[-1] < c30[-3]:
                desired = -target_pct if allow_short else 0.0
            elif c30[-3] < c30[-6] and c30[-1] > c30[-3]:
                desired = target_pct
        reason = "sess_midday_fade"
    elif variant == 3:
        if len(c30) >= 5:
            desired = target_pct if c30[-1] > c30[-5] else (-target_pct if allow_short else 0.0)
        reason = "sess_close_momo"
    elif variant == 4:
        if len(c30) >= 2:
            gap = o30[-1] - c30[-2]
            desired = -target_pct if gap > 0 and allow_short else (target_pct if gap < 0 else 0.0)
        reason = "sess_gap_fade"
    elif variant == 5:
        if len(c30) >= 2:
            gap = o30[-1] - c30[-2]
            desired = target_pct if gap > 0 else (-target_pct if gap < 0 and allow_short else 0.0)
        reason = "sess_gap_go"
    elif variant == 6:
        if len(c30) >= 8:
            desired = target_pct if c30[-1] > c30[-8] else (-target_pct if allow_short else 0.0)
        reason = "sess_night_momo"
    elif variant == 7:
        if len(c30) >= 16:
            day_ret = c30[-8] / c30[-16] - 1
            night_ret = c30[-1] / c30[-8] - 1
            desired = target_pct if night_ret > day_ret else (-target_pct if allow_short else 0.0)
        reason = "sess_day_night_spread"
    elif variant == 8:
        if len(c30) >= 20:
            num = sum(c30[i] * v30[i] for i in range(-20, 0))
            den = sum(v30[-20:])
            vwap = num / den if den else c30[-1]
            desired = target_pct if c30[-1] > vwap else (-target_pct if allow_short else 0.0)
        reason = "sess_vwap_bias"
    elif variant == 9:
        if len(h30) >= 10:
            hi = max(h30[-10:-1])
            lo = min(l30[-10:-1])
            if c30[-1] > hi:
                desired = target_pct
            elif c30[-1] < lo and allow_short:
                desired = -target_pct
        reason = "sess_range_break"

    if desired > 0 and not is_long:
        order_target_percent(g.futures, target_pct, reason=reason)
    elif desired < 0 and allow_short and not is_short:
        order_target_percent(g.futures, -target_pct, reason=reason)
    elif abs(desired) <= 1e-12 and (is_long or is_short):
        order_target_percent(g.futures, 0.0, reason=reason + "_exit")

$sesspack$, '{"params":[{"name":"variant","type":"integer","default":0,"min":0,"max":9,"step":1,"labelKey":"strategyV2.params.variant"},{"name":"target_pct","type":"percent","default":0.95,"min":0.05,"max":1,"step":0.05,"labelKey":"strategyV2.params.targetPosition"},{"name":"allow_short","type":"boolean","default":true,"labelKey":"strategyV2.params.allowShort"}]}'::jsonb, '["strategy-v2","cta","pack","cn-futures","options","session-alpha"]'::jsonb, 'experiment', 'gold', 290, TRUE, '{"source":"system_seed","version":11,"apiVersion":2}'::jsonb, NOW()),
('strategy_v2_regime_switch_pack', 'portfolio_strategy', 'Regime Switch Pack', 'Trend/volatility regime switching with adaptive exposure.', $regpack$"""
Regime Switch Pack
Trend/volatility regime switching with adaptive exposure.
"""

# @param variant int 0 range=0:9:1
# @param target_pct float 0.95 range=0.05:1:0.05
# @param allow_short bool true

def initialize(context):
    g.futures = "CNFutures:SA701"
    g.option = "CNFuturesOptions:SA701-C-1000"
    context.set_universe([g.futures, g.option])
    context.set_benchmark(g.futures)
    context.subscribe(frequency="1m")
    context.set_metadata(direction_mode="both")
    context.set_warmup(8000)


def handle_data(context, data):
    del data
    variant = int(context.params.get("variant", 0))
    target_pct = float(context.params.get("target_pct", 0.95))
    allow_short = bool(context.params.get("allow_short", True))

    def _agg30(bars_1m):
        o = bars_1m["open"].values
        h = bars_1m["high"].values
        l = bars_1m["low"].values
        c = bars_1m["close"].values
        v = bars_1m["volume"].values
        n = len(o)
        count = n // 30
        if count < 1:
            return None, None, None, None, None
        start = n - count * 30
        o30 = [o[start + i * 30] for i in range(count)]
        h30 = [max(h[start + i * 30: start + (i + 1) * 30]) for i in range(count)]
        l30 = [min(l[start + i * 30: start + (i + 1) * 30]) for i in range(count)]
        c30 = [c[start + (i + 1) * 30 - 1] for i in range(count)]
        v30 = [sum(v[start + i * 30: start + (i + 1) * 30]) for i in range(count)]
        return o30, h30, l30, c30, v30

    def _rolling_mean(arr, period):
        if len(arr) < period:
            return []
        return [sum(arr[i - period:i]) / period for i in range(period, len(arr) + 1)]

    def _rolling_max(arr, period):
        if len(arr) < period:
            return []
        return [max(arr[i - period:i]) for i in range(period, len(arr) + 1)]

    def _rolling_min(arr, period):
        if len(arr) < period:
            return []
        return [min(arr[i - period:i]) for i in range(period, len(arr) + 1)]

    def _rolling_std(arr, period):
        if len(arr) < period:
            return []
        out = []
        for i in range(period, len(arr) + 1):
            window = arr[i - period:i]
            m = sum(window) / period
            out.append((sum((x - m) ** 2 for x in window) / period) ** 0.5)
        return out

    bars = get_history(8000, "1m", ["open", "high", "low", "close", "volume"], g.futures)
    o30, h30, l30, c30, v30 = _agg30(bars)
    if o30 is None or len(c30) < 100:
        return

    position = get_position(g.futures)
    position_amt = float(position.amount or 0.0)
    is_long = position_amt > 1e-12
    is_short = position_amt < -1e-12
    desired = 0.0
    reason = ""
    if variant == 0:
        ma50 = _rolling_mean(c30, 50)
        sd20 = _rolling_std(c30, 20)
        if ma50 and sd20:
            if sd20[-1] > sum(sd20[-10:]) / min(10, len(sd20)) and c30[-1] > ma50[-1]:
                desired = target_pct
            elif sd20[-1] > sum(sd20[-10:]) / min(10, len(sd20)) and c30[-1] < ma50[-1] and allow_short:
                desired = -target_pct
        reason = "reg_trend_vol"
    elif variant == 1:
        sd = _rolling_std(c30, 20)
        if sd and sd[-1] < sum(sd[-20:]) / min(20, len(sd)) * 0.85:
            desired = target_pct if c30[-1] < _rolling_mean(c30, 20)[-1] else (-target_pct if allow_short else 0.0)
        reason = "reg_low_vol_mr"
    elif variant == 2:
        sd = _rolling_std(c30, 20)
        if sd and sd[-1] > sum(sd[-20:]) / min(20, len(sd)) * 1.2:
            desired = target_pct if c30[-1] > h30[-2] else (-target_pct if allow_short else 0.0)
        reason = "reg_high_vol_break"
    elif variant == 3:
        ma10 = _rolling_mean(c30, 10)
        ma30 = _rolling_mean(c30, 30)
        ma60 = _rolling_mean(c30, 60)
        if ma10 and ma30 and ma60:
            if ma10[-1] > ma30[-1] > ma60[-1]:
                desired = target_pct
            elif ma10[-1] < ma30[-1] < ma60[-1] and allow_short:
                desired = -target_pct
        reason = "reg_ma_fan"
    elif variant == 4:
        if len(c30) >= 20:
            up = sum(max(c30[i]-c30[i-1],0) for i in range(-19,0))
            dn = sum(max(c30[i-1]-c30[i],0) for i in range(-19,0))
            if up > dn * 1.5:
                desired = target_pct
            elif dn > up * 1.5 and allow_short:
                desired = -target_pct
        reason = "reg_adx_proxy"
    elif variant == 5:
        sd = _rolling_std(c30, 20)
        if sd and sd[-1]:
            scale = min(1.0, 0.01 / sd[-1])
            desired = target_pct * scale if c30[-1] > _rolling_mean(c30, 20)[-1] else (-target_pct * scale if allow_short else 0.0)
        reason = "reg_vol_target"
    elif variant == 6:
        if len(c30) >= 20:
            chop = sum(abs(c30[i]-c30[i-1]) for i in range(-19,0))
            net = abs(c30[-1]-c30[-20])
            if net > chop * 0.35:
                desired = target_pct if c30[-1] > c30[-20] else (-target_pct if allow_short else 0.0)
        reason = "reg_chop_filter"
    elif variant == 7:
        ma20 = _rolling_mean(c30, 20)
        sd = _rolling_std(c30, 20)
        if ma20 and sd:
            trending = sd[-1] > sum(sd[-10:])/min(10,len(sd))
            if trending:
                desired = target_pct if c30[-1] > ma20[-1] else (-target_pct if allow_short else 0.0)
            else:
                desired = target_pct if c30[-1] < ma20[-1] else (-target_pct if allow_short else 0.0)
        reason = "reg_dual_regime"
    elif variant == 8:
        hi = _rolling_max(h30, 55)
        lo = _rolling_min(l30, 20)
        sd = _rolling_std(c30, 20)
        if hi and lo and sd and sd[-1] > sum(sd[-20:])/min(20,len(sd)):
            if c30[-1] > hi[-2]:
                desired = target_pct
            elif c30[-1] < lo[-2] and allow_short:
                desired = -target_pct
        reason = "reg_breakout_regime"
    elif variant == 9:
        sd = _rolling_std(c30, 20)
        ma = _rolling_mean(c30, 20)
        if sd and ma and sd[-1] < sum(sd[-20:])/min(20,len(sd))*0.9:
            desired = target_pct if c30[-1] < ma[-1] else (-target_pct if c30[-1] > ma[-1] and allow_short else 0.0)
        reason = "reg_mean_regime"

    if desired > 0 and not is_long:
        order_target_percent(g.futures, target_pct, reason=reason)
    elif desired < 0 and allow_short and not is_short:
        order_target_percent(g.futures, -target_pct, reason=reason)
    elif abs(desired) <= 1e-12 and (is_long or is_short):
        order_target_percent(g.futures, 0.0, reason=reason + "_exit")

$regpack$, '{"params":[{"name":"variant","type":"integer","default":0,"min":0,"max":9,"step":1,"labelKey":"strategyV2.params.variant"},{"name":"target_pct","type":"percent","default":0.95,"min":0.05,"max":1,"step":0.05,"labelKey":"strategyV2.params.targetPosition"},{"name":"allow_short","type":"boolean","default":true,"labelKey":"strategyV2.params.allowShort"}]}'::jsonb, '["strategy-v2","cta","pack","cn-futures","options","regime-switch"]'::jsonb, 'experiment', 'cyan', 300, TRUE, '{"source":"system_seed","version":11,"apiVersion":2}'::jsonb, NOW()),
('strategy_v2_orderflow_proxy_pack', 'portfolio_strategy', 'Order Flow Proxy Pack', 'Volume delta, OBV, and microstructure flow proxies.', $flowpack$"""
Order Flow Proxy Pack
Volume delta, OBV, and microstructure flow proxies.
"""

# @param variant int 0 range=0:9:1
# @param target_pct float 0.95 range=0.05:1:0.05
# @param allow_short bool true

def initialize(context):
    g.futures = "CNFutures:SA701"
    g.option = "CNFuturesOptions:SA701-C-1000"
    context.set_universe([g.futures, g.option])
    context.set_benchmark(g.futures)
    context.subscribe(frequency="1m")
    context.set_metadata(direction_mode="both")
    context.set_warmup(8000)


def handle_data(context, data):
    del data
    variant = int(context.params.get("variant", 0))
    target_pct = float(context.params.get("target_pct", 0.95))
    allow_short = bool(context.params.get("allow_short", True))

    def _agg30(bars_1m):
        o = bars_1m["open"].values
        h = bars_1m["high"].values
        l = bars_1m["low"].values
        c = bars_1m["close"].values
        v = bars_1m["volume"].values
        n = len(o)
        count = n // 30
        if count < 1:
            return None, None, None, None, None
        start = n - count * 30
        o30 = [o[start + i * 30] for i in range(count)]
        h30 = [max(h[start + i * 30: start + (i + 1) * 30]) for i in range(count)]
        l30 = [min(l[start + i * 30: start + (i + 1) * 30]) for i in range(count)]
        c30 = [c[start + (i + 1) * 30 - 1] for i in range(count)]
        v30 = [sum(v[start + i * 30: start + (i + 1) * 30]) for i in range(count)]
        return o30, h30, l30, c30, v30

    def _rolling_mean(arr, period):
        if len(arr) < period:
            return []
        return [sum(arr[i - period:i]) / period for i in range(period, len(arr) + 1)]

    def _rolling_max(arr, period):
        if len(arr) < period:
            return []
        return [max(arr[i - period:i]) for i in range(period, len(arr) + 1)]

    def _rolling_min(arr, period):
        if len(arr) < period:
            return []
        return [min(arr[i - period:i]) for i in range(period, len(arr) + 1)]

    def _rolling_std(arr, period):
        if len(arr) < period:
            return []
        out = []
        for i in range(period, len(arr) + 1):
            window = arr[i - period:i]
            m = sum(window) / period
            out.append((sum((x - m) ** 2 for x in window) / period) ** 0.5)
        return out

    bars = get_history(8000, "1m", ["open", "high", "low", "close", "volume"], g.futures)
    o30, h30, l30, c30, v30 = _agg30(bars)
    if o30 is None or len(c30) < 100:
        return

    position = get_position(g.futures)
    position_amt = float(position.amount or 0.0)
    is_long = position_amt > 1e-12
    is_short = position_amt < -1e-12
    desired = 0.0
    reason = ""
    if variant == 0:
        obv = 0.0
        for i in range(1, len(c30)):
            if c30[i] > c30[i-1]:
                obv += v30[i]
            elif c30[i] < c30[i-1]:
                obv -= v30[i]
        desired = target_pct if obv > 0 else (-target_pct if allow_short else 0.0)
        reason = "flow_obv"
    elif variant == 1:
        if len(c30) >= 2:
            upv = v30[-1] if c30[-1] >= c30[-2] else 0
            dnv = v30[-1] if c30[-1] < c30[-2] else 0
            desired = target_pct if upv > dnv else (-target_pct if allow_short else 0.0)
        reason = "flow_vol_delta"
    elif variant == 2:
        if len(c30) >= 15:
            tp = [(h30[i]+l30[i]+c30[i])/3 for i in range(-14,0)]
            rmf_pos = sum(tp[i]*v30[-14+i] for i in range(14) if i>0 and tp[i]>tp[i-1])
            rmf_neg = sum(tp[i]*v30[-14+i] for i in range(14) if i>0 and tp[i]<tp[i-1])
            if rmf_pos > rmf_neg:
                desired = target_pct
            elif rmf_neg > rmf_pos and allow_short:
                desired = -target_pct
        reason = "flow_mfi_proxy"
    elif variant == 3:
        if len(c30) >= 20:
            num = sum(c30[i]*v30[i] for i in range(-20,0))
            den = sum(v30[-20:])
            vwap = num/den if den else c30[-1]
            dev = (c30[-1]-vwap)/vwap if vwap else 0
            desired = target_pct if dev > 0.001 else (-target_pct if dev < -0.001 and allow_short else 0.0)
        reason = "flow_vwap_dev"
    elif variant == 4:
        if len(c30) >= 5 and v30[-1] > sum(v30[-5:])/5*1.5:
            desired = target_pct if c30[-1] > c30[-2] else (-target_pct if allow_short else 0.0)
        reason = "flow_absorption"
    elif variant == 5:
        if v30[-1] > sum(v30[-20:])/min(20,len(v30))*2:
            desired = -target_pct if c30[-1] > c30[-2] and allow_short else (target_pct if c30[-1] < c30[-2] else 0.0)
        reason = "flow_climax"
    elif variant == 6:
        if len(c30) >= 10:
            price_up = c30[-1] > c30[-10]
            vol_up = v30[-1] > sum(v30[-10:])/10
            if price_up and not vol_up and allow_short:
                desired = -target_pct
            elif not price_up and vol_up:
                desired = target_pct
        reason = "flow_divergence"
    elif variant == 7:
        imb = [v30[i] if c30[i] >= c30[i-1] else -v30[i] for i in range(1,len(c30))]
        if len(imb) >= 10:
            desired = target_pct if sum(imb[-10:]) > 0 else (-target_pct if allow_short else 0.0)
        reason = "flow_imbalance_ma"
    elif variant == 8:
        ups = sum(1 for i in range(-20,0) if c30[i] > c30[i-1])
        desired = target_pct if ups >= 12 else (-target_pct if ups <= 8 and allow_short else 0.0)
        reason = "flow_tick_rule"
    elif variant == 9:
        if len(c30) >= 5:
            effort = sum(v30[-5:])
            result = abs(c30[-1]-c30[-5])
            if effort > 0 and result/effort < 0.0001:
                desired = -target_pct if c30[-1] > c30[-5] and allow_short else (target_pct if c30[-1] < c30[-5] else 0.0)
        reason = "flow_effort_result"

    if desired > 0 and not is_long:
        order_target_percent(g.futures, target_pct, reason=reason)
    elif desired < 0 and allow_short and not is_short:
        order_target_percent(g.futures, -target_pct, reason=reason)
    elif abs(desired) <= 1e-12 and (is_long or is_short):
        order_target_percent(g.futures, 0.0, reason=reason + "_exit")

$flowpack$, '{"params":[{"name":"variant","type":"integer","default":0,"min":0,"max":9,"step":1,"labelKey":"strategyV2.params.variant"},{"name":"target_pct","type":"percent","default":0.95,"min":0.05,"max":1,"step":0.05,"labelKey":"strategyV2.params.targetPosition"},{"name":"allow_short","type":"boolean","default":true,"labelKey":"strategyV2.params.allowShort"}]}'::jsonb, '["strategy-v2","cta","pack","cn-futures","options","orderflow"]'::jsonb, 'experiment', 'green', 310, TRUE, '{"source":"system_seed","version":11,"apiVersion":2}'::jsonb, NOW())
ON CONFLICT (template_key) DO UPDATE SET
    asset_type = EXCLUDED.asset_type,
    title = EXCLUDED.title,
    description = EXCLUDED.description,
    code = EXCLUDED.code,
    param_schema = EXCLUDED.param_schema,
    tags = EXCLUDED.tags,
    icon = EXCLUDED.icon,
    accent = EXCLUDED.accent,
    sort_order = EXCLUDED.sort_order,
    is_active = TRUE,
    metadata = EXCLUDED.metadata,
    updated_at = NOW();

-- pack_keys: strategy_v2_stat_arb_pack, strategy_v2_options_vol_pack, strategy_v2_session_alpha_pack, strategy_v2_regime_switch_pack, strategy_v2_orderflow_proxy_pack
