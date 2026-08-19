-- ===== Strategy API V2 canonical template seed =====

DELETE FROM qd_script_templates
WHERE template_key NOT IN (
    'strategy_v2_single_ma',
    'strategy_v2_double_ma',
    'strategy_v2_bullish_three_lines',
    'strategy_v2_bullish_three_lines_trend',
    'strategy_v2_turtle',
    'strategy_v2_indicator_resonance',
    'strategy_v2_macd_kdj',
    'strategy_v2_supertrend',
    'strategy_v2_market_cap_barbell',
    'strategy_v2_momentum_top_n',
    'strategy_v2_low_volatility',
    'strategy_v2_quality_growth',
    'strategy_v2_trend_pack',
    'strategy_v2_breakout_momentum_pack',
    'strategy_v2_mean_reversion_pack',
    'strategy_v2_carry_pack',
    'strategy_v2_relative_value_pack',
    'strategy_v2_volatility_pack',
    'strategy_v2_market_microstructure_pack'
);

INSERT INTO qd_script_templates
(template_key, asset_type, title, description, code, param_schema, tags, icon, accent, sort_order, is_active, metadata, updated_at)
VALUES
('strategy_v2_single_ma', 'script', 'Single Moving Average', 'A parameterized SPY trend strategy using one moving average.', $single$"""
Single Moving Average
SPY trend regime driven by a configurable moving average.
"""

# @param ma_period int 50 range=2:250:1
# @param target_pct float 0.95 range=0.05:1:0.05

def initialize(context):
    g.symbol = "USStock:SPY"
    context.set_universe([g.symbol])
    context.set_benchmark(g.symbol)
    context.subscribe(frequency="1d")
    context.set_metadata(direction_mode="long_only")
    context.set_warmup(260)


def handle_data(context, data):
    ma_period = int(context.params.get("ma_period", 50))
    target_pct = float(context.params.get("target_pct", 0.95))
    bars = get_history(ma_period + 2, "1d", "close", g.symbol)
    if len(bars) < ma_period + 1:
        return
    close = bars["close"]
    average = float(close.iloc[:-1].tail(ma_period).mean())
    price = float(close.iloc[-1])
    position = get_position(g.symbol)
    is_long = float(position.amount or 0.0) > 0
    if price > average and not is_long:
        order_target_percent(g.symbol, target_pct, reason="single_ma_entry")
    elif price <= average and is_long:
        order_target_percent(g.symbol, 0.0, reason="single_ma_exit")
$single$, '{"params":[{"name":"ma_period","type":"integer","default":50,"min":2,"max":250,"step":1,"labelKey":"strategyV2.params.maPeriod","descriptionKey":"strategyV2.params.maPeriodDesc"},{"name":"target_pct","type":"percent","default":0.95,"min":0.05,"max":1,"step":0.05,"labelKey":"strategyV2.params.targetPosition","descriptionKey":"strategyV2.params.targetPositionDesc"}]}'::jsonb, '["strategy-v2","cta","moving-average","us-stock"]'::jsonb, 'line-chart', 'green', 10, TRUE, '{"source":"system_seed","version":11,"apiVersion":2}'::jsonb, NOW()),

('strategy_v2_double_ma', 'script', 'Dual Moving Average', 'A parameterized BTC perpetual dual moving-average strategy with optional leverage.', $double$"""
Dual Moving Average
BTC perpetual trend strategy with configurable long and short regimes.
"""

# @param fast_period int 20 range=2:100:1
# @param slow_period int 60 range=5:300:1
# @param target_pct float 0.95 range=0.05:1:0.05
# @param allow_short bool true

def initialize(context):
    g.symbol = "Crypto:BTC/USDT@swap"
    context.set_universe([g.symbol])
    context.set_benchmark("Crypto:BTC/USDT@spot")
    context.subscribe(frequency="4h")
    context.set_metadata(direction_mode="both")
    context.set_warmup(310)
    context.allow_leverage(max_leverage=20)


def handle_data(context, data):
    fast_period = int(context.params.get("fast_period", 20))
    slow_period = int(context.params.get("slow_period", 60))
    target_pct = float(context.params.get("target_pct", 0.95))
    allow_short = bool(context.params.get("allow_short", True))
    if fast_period >= slow_period:
        return
    bars = get_history(slow_period + 2, "4h", "close", g.symbol)
    if len(bars) < slow_period + 1:
        return
    close = bars["close"]
    fast = float(close.tail(fast_period).mean())
    slow = float(close.tail(slow_period).mean())
    long_position = get_position(g.symbol, position_side="long")
    short_position = get_position(g.symbol, position_side="short")
    long_open = abs(float(long_position.amount or 0.0)) > 1e-12
    short_open = abs(float(short_position.amount or 0.0)) > 1e-12
    bullish = fast > slow
    if bullish:
        if short_open:
            order_target_percent(g.symbol, 0.0, position_side="short", reason="dual_ma_close_short")
        elif not long_open:
            order_target_percent(g.symbol, target_pct, position_side="long", reason="dual_ma_open_long")
    else:
        if long_open:
            order_target_percent(g.symbol, 0.0, position_side="long", reason="dual_ma_close_long")
        elif allow_short and not short_open:
            order_target_percent(g.symbol, -target_pct, position_side="short", reason="dual_ma_open_short")
        elif not allow_short and short_open:
            order_target_percent(g.symbol, 0.0, position_side="short", reason="dual_ma_close_short_disabled")
$double$, '{"params":[{"name":"fast_period","type":"integer","default":20,"min":2,"max":100,"step":1,"labelKey":"trading-assistant.templateParam.fast_period.label","descriptionKey":"trading-assistant.templateParam.fast_period.desc"},{"name":"slow_period","type":"integer","default":60,"min":5,"max":300,"step":1,"labelKey":"trading-assistant.templateParam.slow_period.label","descriptionKey":"trading-assistant.templateParam.slow_period.desc"},{"name":"target_pct","type":"percent","default":0.95,"min":0.05,"max":1,"step":0.05,"labelKey":"strategyV2.params.targetPosition","descriptionKey":"strategyV2.params.targetPositionDesc"},{"name":"allow_short","type":"boolean","default":true,"labelKey":"strategyV2.params.allowShort","descriptionKey":"strategyV2.params.allowShortDesc"}]}'::jsonb, '["strategy-v2","cta","moving-average","crypto","swap"]'::jsonb, 'swap', 'blue', 20, TRUE, '{"source":"system_seed","version":11,"apiVersion":2}'::jsonb, NOW()),

('strategy_v2_bullish_three_lines', 'script', 'Bullish Candle Through Three Averages', 'An A-share bullish candle breakout through three configurable averages.', $three$"""
Bullish Candle Through Three Averages
Daily A-share breakout through three configurable moving averages.
"""

# @param short_period int 5 range=2:60:1
# @param mid_period int 10 range=3:120:1
# @param long_period int 20 range=5:250:1
# @param min_body_pct float 0.02 range=0:0.2:0.005
# @param target_pct float 0.95 range=0.05:1:0.05

def initialize(context):
    g.symbol = "CNStock:600519.SH"
    context.set_universe([g.symbol])
    context.set_benchmark(g.symbol)
    context.subscribe(frequency="1d")
    context.set_metadata(direction_mode="long_only")
    context.set_warmup(260)


def handle_data(context, data):
    periods = [
        int(context.params.get("short_period", 5)),
        int(context.params.get("mid_period", 10)),
        int(context.params.get("long_period", 20)),
    ]
    min_body_pct = float(context.params.get("min_body_pct", 0.02))
    target_pct = float(context.params.get("target_pct", 0.95))
    if not periods[0] < periods[1] < periods[2]:
        return
    bars = get_history(periods[-1] + 3, "1d", ["open", "close"], g.symbol)
    if len(bars) < periods[-1] + 1:
        return
    close = bars["close"]
    current = bars.iloc[-1]
    averages = [float(close.iloc[:-1].tail(period).mean()) for period in periods]
    open_price = float(current["open"])
    close_price = float(current["close"])
    body_pct = (close_price - open_price) / open_price if open_price > 0 else 0.0
    crossed = body_pct >= min_body_pct and open_price <= min(averages) and close_price >= max(averages)
    position = get_position(g.symbol)
    is_long = float(position.amount or 0.0) > 0
    if crossed and not is_long:
        order_target_percent(g.symbol, target_pct, reason="bullish_three_lines_entry")
    elif is_long and close_price < averages[-1]:
        order_target_percent(g.symbol, 0.0, reason="bullish_three_lines_exit")
$three$, '{"params":[{"name":"short_period","type":"integer","default":5,"min":2,"max":60,"step":1,"labelKey":"strategyV2.params.shortPeriod","descriptionKey":"strategyV2.params.shortPeriodDesc"},{"name":"mid_period","type":"integer","default":10,"min":3,"max":120,"step":1,"labelKey":"strategyV2.params.midPeriod","descriptionKey":"strategyV2.params.midPeriodDesc"},{"name":"long_period","type":"integer","default":20,"min":5,"max":250,"step":1,"labelKey":"strategyV2.params.longPeriod","descriptionKey":"strategyV2.params.longPeriodDesc"},{"name":"min_body_pct","type":"percent","default":0.02,"min":0,"max":0.2,"step":0.005,"labelKey":"strategyV2.params.minBodyPct","descriptionKey":"strategyV2.params.minBodyPctDesc"},{"name":"target_pct","type":"percent","default":0.95,"min":0.05,"max":1,"step":0.05,"labelKey":"strategyV2.params.targetPosition","descriptionKey":"strategyV2.params.targetPositionDesc"}]}'::jsonb, '["strategy-v2","cta","candlestick","a-share"]'::jsonb, 'rise', 'red', 30, TRUE, '{"source":"system_seed","version":11,"apiVersion":2}'::jsonb, NOW()),

('strategy_v2_bullish_three_lines_trend', 'script', 'Bullish Three Averages With Trend Filter', 'The three-average breakout combined with a configurable rising trend filter.', $threetrend$"""
Bullish Three Averages With Trend Filter
Daily A-share breakout with a configurable rising trend filter.
"""

# @param short_period int 5 range=2:60:1
# @param mid_period int 10 range=3:120:1
# @param long_period int 20 range=5:250:1
# @param trend_period int 60 range=20:300:1
# @param trend_slope_bars int 5 range=1:30:1
# @param min_body_pct float 0.02 range=0:0.2:0.005
# @param target_pct float 0.95 range=0.05:1:0.05

def initialize(context):
    g.symbol = "CNStock:600519.SH"
    context.set_universe([g.symbol])
    context.set_benchmark(g.symbol)
    context.subscribe(frequency="1d")
    context.set_metadata(direction_mode="long_only")
    context.set_warmup(340)


def handle_data(context, data):
    periods = [int(context.params.get("short_period", 5)), int(context.params.get("mid_period", 10)), int(context.params.get("long_period", 20))]
    trend_period = int(context.params.get("trend_period", 60))
    slope_bars = int(context.params.get("trend_slope_bars", 5))
    min_body_pct = float(context.params.get("min_body_pct", 0.02))
    target_pct = float(context.params.get("target_pct", 0.95))
    required = max(periods[-1], trend_period) + slope_bars + 2
    bars = get_history(required, "1d", ["open", "close"], g.symbol)
    if len(bars) < required - 1 or not periods[0] < periods[1] < periods[2]:
        return
    close = bars["close"]
    current = bars.iloc[-1]
    averages = [float(close.iloc[:-1].tail(period).mean()) for period in periods]
    trend_now = float(close.iloc[:-1].tail(trend_period).mean())
    trend_before = float(close.iloc[:-1 - slope_bars].tail(trend_period).mean())
    open_price = float(current["open"])
    close_price = float(current["close"])
    body_pct = (close_price - open_price) / open_price if open_price > 0 else 0.0
    crossed = body_pct >= min_body_pct and open_price <= min(averages) and close_price >= max(averages)
    trend_ok = close_price > trend_now and trend_now > trend_before
    position = get_position(g.symbol)
    is_long = float(position.amount or 0.0) > 0
    if crossed and trend_ok and not is_long:
        order_target_percent(g.symbol, target_pct, reason="bullish_three_lines_trend_entry")
    elif is_long and (close_price < averages[-1] or not trend_ok):
        order_target_percent(g.symbol, 0.0, reason="bullish_three_lines_trend_exit")
$threetrend$, '{"params":[{"name":"short_period","type":"integer","default":5,"min":2,"max":60,"step":1,"labelKey":"strategyV2.params.shortPeriod"},{"name":"mid_period","type":"integer","default":10,"min":3,"max":120,"step":1,"labelKey":"strategyV2.params.midPeriod"},{"name":"long_period","type":"integer","default":20,"min":5,"max":250,"step":1,"labelKey":"strategyV2.params.longPeriod"},{"name":"trend_period","type":"integer","default":60,"min":20,"max":300,"step":1,"labelKey":"strategyV2.params.trendPeriod"},{"name":"trend_slope_bars","type":"integer","default":5,"min":1,"max":30,"step":1,"labelKey":"strategyV2.params.trendSlopeBars"},{"name":"min_body_pct","type":"percent","default":0.02,"min":0,"max":0.2,"step":0.005,"labelKey":"strategyV2.params.minBodyPct"},{"name":"target_pct","type":"percent","default":0.95,"min":0.05,"max":1,"step":0.05,"labelKey":"strategyV2.params.targetPosition"}]}'::jsonb, '["strategy-v2","cta","candlestick","trend","a-share"]'::jsonb, 'area-chart', 'orange', 40, TRUE, '{"source":"system_seed","version":11,"apiVersion":2}'::jsonb, NOW()),

('strategy_v2_turtle', 'script', 'Turtle Trading', 'A configurable Donchian breakout, channel exit, and ATR stop strategy on SPY.', $turtle$"""
Turtle Trading
Configurable Donchian breakout, channel exit, and ATR risk stop.
"""

# @param entry_period int 20 range=5:120:1
# @param exit_period int 10 range=2:60:1
# @param atr_period int 14 range=2:100:1
# @param atr_stop_mult float 2 range=0.5:10:0.25
# @param target_pct float 0.95 range=0.05:1:0.05

def initialize(context):
    g.symbol = "USStock:SPY"
    context.set_universe([g.symbol])
    context.set_benchmark(g.symbol)
    context.subscribe(frequency="1d")
    context.set_metadata(direction_mode="long_only")
    context.set_warmup(140)


def handle_data(context, data):
    entry_period = int(context.params.get("entry_period", 20))
    exit_period = int(context.params.get("exit_period", 10))
    atr_period = int(context.params.get("atr_period", 14))
    atr_stop_mult = float(context.params.get("atr_stop_mult", 2.0))
    target_pct = float(context.params.get("target_pct", 0.95))
    required = max(entry_period, exit_period, atr_period) + 2
    bars = get_history(required, "1d", ["high", "low", "close"], g.symbol)
    atr = indicator("ATR", g.symbol, timeperiod=atr_period)
    if len(bars) < required - 1 or len(atr) < 2:
        return
    close = float(bars["close"].iloc[-1])
    entry_high = float(bars["high"].iloc[-entry_period - 1:-1].max())
    exit_low = float(bars["low"].iloc[-exit_period - 1:-1].min())
    atr_value = float(atr.iloc[-1])
    position = get_position(g.symbol)
    is_long = float(position.amount or 0.0) > 0
    if not is_long and close > entry_high:
        order_target_percent(g.symbol, target_pct, reason="turtle_breakout")
    elif is_long:
        entry_price = float(position.avg_cost or close)
        stop_price = entry_price - atr_stop_mult * atr_value
        if close < exit_low or close < stop_price:
            order_target_percent(g.symbol, 0.0, reason="turtle_exit")
$turtle$, '{"params":[{"name":"entry_period","type":"integer","default":20,"min":5,"max":120,"step":1,"labelKey":"strategyV2.params.entryPeriod"},{"name":"exit_period","type":"integer","default":10,"min":2,"max":60,"step":1,"labelKey":"strategyV2.params.exitPeriod"},{"name":"atr_period","type":"integer","default":14,"min":2,"max":100,"step":1,"labelKey":"strategyV2.params.atrPeriod"},{"name":"atr_stop_mult","type":"number","default":2,"min":0.5,"max":10,"step":0.25,"labelKey":"strategyV2.params.atrStopMult"},{"name":"target_pct","type":"percent","default":0.95,"min":0.05,"max":1,"step":0.05,"labelKey":"strategyV2.params.targetPosition"}]}'::jsonb, '["strategy-v2","cta","breakout","turtle","us-stock"]'::jsonb, 'flag', 'cyan', 50, TRUE, '{"source":"system_seed","version":11,"apiVersion":2}'::jsonb, NOW()),

('strategy_v2_indicator_resonance', 'script', 'Indicator Resonance', 'A parameterized QQQ strategy requiring MACD, RSI, and ADX confirmation.', $resonance$"""
Indicator Resonance
MACD, RSI, and ADX confirm the same bullish regime.
"""

# @param fast_period int 12 range=2:100:1
# @param slow_period int 26 range=3:200:1
# @param signal_period int 9 range=2:100:1
# @param rsi_period int 14 range=2:100:1
# @param rsi_min float 50 range=0:100:1
# @param rsi_max float 75 range=0:100:1
# @param adx_period int 14 range=2:100:1
# @param adx_min float 20 range=0:100:1
# @param target_pct float 0.95 range=0.05:1:0.05

def initialize(context):
    g.symbol = "USStock:QQQ"
    context.set_universe([g.symbol])
    context.set_benchmark(g.symbol)
    context.subscribe(frequency="1d")
    context.set_metadata(direction_mode="long_only")
    context.set_warmup(210)


def handle_data(context, data):
    fast_period = int(context.params.get("fast_period", 12))
    slow_period = int(context.params.get("slow_period", 26))
    signal_period = int(context.params.get("signal_period", 9))
    rsi_period = int(context.params.get("rsi_period", 14))
    rsi_min = float(context.params.get("rsi_min", 50))
    rsi_max = float(context.params.get("rsi_max", 75))
    adx_period = int(context.params.get("adx_period", 14))
    adx_min = float(context.params.get("adx_min", 20))
    target_pct = float(context.params.get("target_pct", 0.95))
    macd = indicator("MACD", g.symbol, fastperiod=fast_period, slowperiod=slow_period, signalperiod=signal_period)
    rsi = indicator("RSI", g.symbol, timeperiod=rsi_period)
    adx = indicator("ADX", g.symbol, timeperiod=adx_period)
    if len(macd) < 2 or len(rsi) < 2 or len(adx) < 2:
        return
    histogram = float(macd["macdhist"].iloc[-1])
    rsi_value = float(rsi.iloc[-1])
    adx_value = float(adx.iloc[-1])
    if not all(value == value for value in (histogram, rsi_value, adx_value)):
        return
    bullish = histogram > 0 and rsi_min < rsi_value < rsi_max and adx_value > adx_min
    position = get_position(g.symbol)
    is_long = float(position.amount or 0.0) > 0
    if bullish and not is_long:
        order_target_percent(g.symbol, target_pct, reason="indicator_resonance_entry")
    elif not bullish and is_long:
        order_target_percent(g.symbol, 0.0, reason="indicator_resonance_exit")
$resonance$, '{"params":[{"name":"fast_period","type":"integer","default":12,"min":2,"max":100,"step":1,"labelKey":"trading-assistant.templateParam.fast_period.label"},{"name":"slow_period","type":"integer","default":26,"min":3,"max":200,"step":1,"labelKey":"trading-assistant.templateParam.slow_period.label"},{"name":"signal_period","type":"integer","default":9,"min":2,"max":100,"step":1,"labelKey":"strategyV2.params.signalPeriod"},{"name":"rsi_period","type":"integer","default":14,"min":2,"max":100,"step":1,"labelKey":"strategyV2.params.rsiPeriod"},{"name":"rsi_min","type":"number","default":50,"min":0,"max":100,"step":1,"labelKey":"strategyV2.params.rsiMin"},{"name":"rsi_max","type":"number","default":75,"min":0,"max":100,"step":1,"labelKey":"strategyV2.params.rsiMax"},{"name":"adx_period","type":"integer","default":14,"min":2,"max":100,"step":1,"labelKey":"strategyV2.params.adxPeriod"},{"name":"adx_min","type":"number","default":20,"min":0,"max":100,"step":1,"labelKey":"strategyV2.params.adxMin"},{"name":"target_pct","type":"percent","default":0.95,"min":0.05,"max":1,"step":0.05,"labelKey":"strategyV2.params.targetPosition"}]}'::jsonb, '["strategy-v2","cta","ta-lib","resonance","us-stock"]'::jsonb, 'fund', 'purple', 60, TRUE, '{"source":"system_seed","version":11,"apiVersion":2}'::jsonb, NOW()),

('strategy_v2_macd_kdj', 'script', 'MACD and KDJ Confirmation', 'A BTC perpetual strategy combining MACD momentum, stochastic KDJ confirmation, and explicit position protection.', $macdkdj$"""
MACD and KDJ Confirmation
BTC perpetual momentum with state-transition entries confirmed by MACD and stochastic KDJ.
"""

# @param fast_period int 12 range=2:100:1
# @param slow_period int 26 range=3:200:1
# @param signal_period int 9 range=2:100:1
# @param kdj_period int 9 range=2:100:1
# @param kdj_smooth_k int 3 range=1:20:1
# @param kdj_smooth_d int 3 range=1:20:1
# @param overbought float 85 range=50:100:1
# @param target_pct float 0.95 range=0.1:5:0.05
# @param stop_loss_pct float 0.02 range=0.005:0.2:0.005
# @param trailing_activation_pct float 0.05 range=0.005:0.5:0.005
# @param trailing_stop_pct float 0.01 range=0.005:0.2:0.005

def initialize(context):
    g.symbol = "Crypto:BTC/USDT@swap"
    context.set_universe([g.symbol])
    context.set_benchmark("Crypto:BTC/USDT@spot")
    context.subscribe(frequency="4h")
    context.set_metadata(direction_mode="long_only")
    context.set_warmup(210)
    context.allow_leverage(max_leverage=5)


def handle_data(context, data):
    fast_period = int(context.params.get("fast_period", 12))
    slow_period = int(context.params.get("slow_period", 26))
    signal_period = int(context.params.get("signal_period", 9))
    kdj_period = int(context.params.get("kdj_period", 9))
    kdj_smooth_k = int(context.params.get("kdj_smooth_k", 3))
    kdj_smooth_d = int(context.params.get("kdj_smooth_d", 3))
    overbought = float(context.params.get("overbought", 85))
    target_pct = float(context.params.get("target_pct", 0.95))
    stop_loss_pct = float(context.params.get("stop_loss_pct", 0.02))
    trailing_activation_pct = float(context.params.get("trailing_activation_pct", 0.05))
    trailing_stop_pct = float(context.params.get("trailing_stop_pct", 0.01))
    macd = indicator("MACD", g.symbol, fastperiod=fast_period, slowperiod=slow_period, signalperiod=signal_period)
    kdj = indicator("STOCH", g.symbol, fastk_period=kdj_period, slowk_period=kdj_smooth_k, slowd_period=kdj_smooth_d)
    if len(macd) < 2 or len(kdj) < 2:
        return
    previous_histogram = float(macd["macdhist"].iloc[-2])
    histogram = float(macd["macdhist"].iloc[-1])
    previous_k = float(kdj["slowk"].iloc[-2])
    previous_d = float(kdj["slowd"].iloc[-2])
    k_value = float(kdj["slowk"].iloc[-1])
    d_value = float(kdj["slowd"].iloc[-1])
    if not all(value == value for value in (previous_histogram, histogram, previous_k, previous_d, k_value, d_value)):
        return
    macd_cross_up = previous_histogram <= 0 < histogram
    kdj_cross_up = previous_k <= previous_d and k_value > d_value
    enter = histogram > 0 and (macd_cross_up or kdj_cross_up) and k_value < overbought
    exit_signal = histogram <= 0 or (previous_k >= previous_d and k_value < d_value)
    position = get_position(g.symbol, position_side="long")
    is_long = float(position.amount or 0.0) > 0
    if enter and not is_long:
        order_target_percent(
            g.symbol,
            target_pct,
            position_side="long",
            reason="macd_kdj_entry",
            stop_loss_pct=stop_loss_pct,
            trailing_activation_pct=trailing_activation_pct,
            trailing_stop_pct=trailing_stop_pct,
        )
    elif exit_signal and is_long:
        order_target_percent(g.symbol, 0.0, position_side="long", reason="macd_kdj_exit")
$macdkdj$, '{"params":[{"name":"fast_period","type":"integer","default":12,"min":2,"max":100,"step":1,"labelKey":"trading-assistant.templateParam.fast_period.label"},{"name":"slow_period","type":"integer","default":26,"min":3,"max":200,"step":1,"labelKey":"trading-assistant.templateParam.slow_period.label"},{"name":"signal_period","type":"integer","default":9,"min":2,"max":100,"step":1,"labelKey":"strategyV2.params.signalPeriod"},{"name":"kdj_period","type":"integer","default":9,"min":2,"max":100,"step":1,"labelKey":"strategyV2.params.kdjPeriod"},{"name":"kdj_smooth_k","type":"integer","default":3,"min":1,"max":20,"step":1,"labelKey":"strategyV2.params.kdjSmoothK"},{"name":"kdj_smooth_d","type":"integer","default":3,"min":1,"max":20,"step":1,"labelKey":"strategyV2.params.kdjSmoothD"},{"name":"overbought","type":"number","default":85,"min":50,"max":100,"step":1,"labelKey":"trading-assistant.templateParam.overbought.label"},{"name":"target_pct","type":"number","default":0.95,"min":0.1,"max":5,"step":0.05,"labelKey":"strategyV2.params.targetExposure"},{"name":"stop_loss_pct","type":"percent","default":0.02,"min":0.005,"max":0.2,"step":0.005,"labelKey":"strategyV2.params.stopLoss"},{"name":"trailing_activation_pct","type":"percent","default":0.05,"min":0.005,"max":0.5,"step":0.005,"labelKey":"strategyV2.params.trailingActivation"},{"name":"trailing_stop_pct","type":"percent","default":0.01,"min":0.005,"max":0.2,"step":0.005,"labelKey":"strategyV2.params.trailingDrawdown"}]}'::jsonb, '["strategy-v2","cta","ta-lib","macd","kdj","crypto","swap","risk"]'::jsonb, 'bar-chart', 'gold', 70, TRUE, '{"source":"system_seed","version":11,"apiVersion":2}'::jsonb, NOW()),

('strategy_v2_supertrend', 'script', 'SuperTrend', 'A configurable SPY SuperTrend strategy using ATR trailing bands.', $supertrend$"""
SuperTrend
ATR trailing bands define a stateful SPY trend regime.
"""

# @param atr_period int 10 range=2:100:1
# @param atr_multiplier float 3 range=0.5:10:0.25
# @param target_pct float 0.95 range=0.05:1:0.05

PERSIST_RUNTIME_STATE = True

def initialize(context):
    g.symbol = "USStock:SPY"
    g.trend = 0
    g.upper_band = None
    g.lower_band = None
    context.set_universe([g.symbol])
    context.set_benchmark(g.symbol)
    context.subscribe(frequency="1d")
    context.set_metadata(direction_mode="long_only")
    context.set_warmup(120)


def handle_data(context, data):
    atr_period = int(context.params.get("atr_period", 10))
    multiplier = float(context.params.get("atr_multiplier", 3.0))
    target_pct = float(context.params.get("target_pct", 0.95))
    bars = get_history(atr_period + 3, "1d", ["high", "low", "close"], g.symbol)
    atr = indicator("ATR", g.symbol, timeperiod=atr_period)
    if len(bars) < atr_period + 2 or len(atr) < 2:
        return
    high = float(bars["high"].iloc[-1])
    low = float(bars["low"].iloc[-1])
    close = float(bars["close"].iloc[-1])
    previous_close = float(bars["close"].iloc[-2])
    atr_value = float(atr.iloc[-1])
    middle = (high + low) / 2.0
    basic_upper = middle + multiplier * atr_value
    basic_lower = middle - multiplier * atr_value
    previous_upper = float(g.upper_band) if g.upper_band is not None else basic_upper
    previous_lower = float(g.lower_band) if g.lower_band is not None else basic_lower
    g.upper_band = basic_upper if basic_upper < previous_upper or previous_close > previous_upper else previous_upper
    g.lower_band = basic_lower if basic_lower > previous_lower or previous_close < previous_lower else previous_lower
    if close > previous_upper:
        g.trend = 1
    elif close < previous_lower:
        g.trend = -1
    position = get_position(g.symbol)
    is_long = float(position.amount or 0.0) > 0
    if g.trend > 0 and not is_long:
        order_target_percent(g.symbol, target_pct, reason="supertrend_entry")
    elif g.trend < 0 and is_long:
        order_target_percent(g.symbol, 0.0, reason="supertrend_exit")
$supertrend$, '{"params":[{"name":"atr_period","type":"integer","default":10,"min":2,"max":100,"step":1,"labelKey":"strategyV2.params.atrPeriod"},{"name":"atr_multiplier","type":"number","default":3,"min":0.5,"max":10,"step":0.25,"labelKey":"strategyV2.params.atrMultiplier"},{"name":"target_pct","type":"percent","default":0.95,"min":0.05,"max":1,"step":0.05,"labelKey":"strategyV2.params.targetPosition"}]}'::jsonb, '["strategy-v2","cta","supertrend","atr","us-stock"]'::jsonb, 'stock', 'lime', 80, TRUE, '{"source":"system_seed","version":11,"apiVersion":2}'::jsonb, NOW()),

('strategy_v2_market_cap_barbell', 'portfolio_strategy', 'Small and Large Cap Barbell', 'A weekly cross-sectional portfolio combining small and large eligible U.S. companies.', $marketcap$"""
Small and Large Cap Barbell
Weekly point-in-time market-cap barbell with a profitability filter.
"""

# @param per_side int 3 range=1:6:1
# @param min_roe float 0 range=-1:1:0.01
# @param max_weight float 0.2 range=0.05:1:0.05

def initialize(context):
    g.universe = [
        "USStock:AAPL", "USStock:MSFT", "USStock:NVDA", "USStock:AMZN", "USStock:META",
        "USStock:GOOGL", "USStock:AVGO", "USStock:COST", "USStock:JPM", "USStock:XOM",
    ]
    context.set_universe(g.universe)
    context.set_benchmark("USStock:SPY")
    context.subscribe(frequency="1d")
    context.set_metadata(direction_mode="long_only")
    context.set_warmup(10)
    run_weekly(rebalance, weekday=1, time="09:35")


def rebalance(context, data):
    per_side = int(context.params.get("per_side", 3))
    min_roe = float(context.params.get("min_roe", 0.0))
    max_weight = float(context.params.get("max_weight", 0.2))
    symbols = list(g.universe)
    fundamentals = get_fundamentals(["MARKET_CAP", "ROE"], symbols)
    if fundamentals.empty:
        return
    eligible = fundamentals.dropna(subset=["MARKET_CAP"])
    if "ROE" in eligible.columns:
        eligible = eligible[(eligible["ROE"].isna()) | (eligible["ROE"] >= min_roe)]
    ranking = eligible.sort_values("MARKET_CAP")
    selected = list(dict.fromkeys(list(ranking.head(per_side).index) + list(ranking.tail(per_side).index)))
    for symbol in get_positions().keys():
        if symbol not in selected:
            order_target_percent(symbol, 0.0, reason="market_cap_removed")
    weight = min(max_weight, 1.0 / len(selected)) if selected else 0.0
    for symbol in selected:
        order_target_percent(symbol, weight, reason="market_cap_barbell")
$marketcap$, '{"params":[{"name":"per_side","type":"integer","default":3,"min":1,"max":6,"step":1,"labelKey":"strategyV2.params.perSide"},{"name":"min_roe","type":"number","default":0,"min":-1,"max":1,"step":0.01,"labelKey":"strategyV2.params.minRoe"},{"name":"max_weight","type":"percent","default":0.2,"min":0.05,"max":1,"step":0.05,"labelKey":"strategyV2.params.maxWeight"}]}'::jsonb, '["strategy-v2","portfolio","cross-sectional","fundamental","market-cap"]'::jsonb, 'appstore', 'geekblue', 110, TRUE, '{"source":"system_seed","version":11,"apiVersion":2}'::jsonb, NOW()),

('strategy_v2_momentum_top_n', 'portfolio_strategy', 'Momentum Top-N Rotation', 'A weekly U.S. stock portfolio selecting the strongest trailing momentum.', $momentum$"""
Momentum Top-N Rotation
Weekly cross-sectional rotation into the strongest trailing momentum names.
"""

# @param lookback int 60 range=10:250:5
# @param top_n int 4 range=1:10:1
# @param max_weight float 0.25 range=0.05:1:0.05

def initialize(context):
    g.universe = [
        "USStock:AAPL", "USStock:MSFT", "USStock:NVDA", "USStock:AMZN", "USStock:META",
        "USStock:GOOGL", "USStock:AVGO", "USStock:COST", "USStock:JPM", "USStock:XOM",
    ]
    context.set_universe(g.universe)
    context.set_benchmark("USStock:SPY")
    context.subscribe(frequency="1d")
    context.set_metadata(direction_mode="long_only")
    context.set_warmup(260)
    run_weekly(rebalance, weekday=1, time="09:35")


def rebalance(context, data):
    lookback = int(context.params.get("lookback", 60))
    top_n = int(context.params.get("top_n", 4))
    max_weight = float(context.params.get("max_weight", 0.25))
    scores = {}
    for symbol in g.universe:
        bars = get_history(lookback + 1, "1d", "close", symbol)
        if len(bars) < lookback + 1:
            continue
        first = float(bars["close"].iloc[0])
        last = float(bars["close"].iloc[-1])
        if first > 0:
            scores[symbol] = last / first - 1.0
    selected = [symbol for symbol, score in sorted(scores.items(), key=lambda item: item[1], reverse=True)[:top_n] if score > 0]
    for symbol in get_positions().keys():
        if symbol not in selected:
            order_target_percent(symbol, 0.0, reason="momentum_removed")
    weight = min(max_weight, 1.0 / len(selected)) if selected else 0.0
    for symbol in selected:
        order_target_percent(symbol, weight, reason="momentum_top_n")
$momentum$, '{"params":[{"name":"lookback","type":"integer","default":60,"min":10,"max":250,"step":5,"labelKey":"strategyV2.params.lookback"},{"name":"top_n","type":"integer","default":4,"min":1,"max":10,"step":1,"labelKey":"strategyV2.params.topN"},{"name":"max_weight","type":"percent","default":0.25,"min":0.05,"max":1,"step":0.05,"labelKey":"strategyV2.params.maxWeight"}]}'::jsonb, '["strategy-v2","portfolio","cross-sectional","momentum","rotation"]'::jsonb, 'rocket', 'blue', 120, TRUE, '{"source":"system_seed","version":11,"apiVersion":2}'::jsonb, NOW()),

('strategy_v2_low_volatility', 'portfolio_strategy', 'Low Volatility Rotation', 'A weekly U.S. stock portfolio selecting the lowest realized volatility names.', $lowvol$"""
Low Volatility Rotation
Weekly cross-sectional rotation into the lowest realized volatility names.
"""

# @param lookback int 60 range=10:250:5
# @param top_n int 4 range=1:10:1
# @param max_weight float 0.25 range=0.05:1:0.05

def initialize(context):
    g.universe = [
        "USStock:AAPL", "USStock:MSFT", "USStock:NVDA", "USStock:AMZN", "USStock:META",
        "USStock:GOOGL", "USStock:AVGO", "USStock:COST", "USStock:JPM", "USStock:XOM",
    ]
    context.set_universe(g.universe)
    context.set_benchmark("USStock:SPY")
    context.subscribe(frequency="1d")
    context.set_metadata(direction_mode="long_only")
    context.set_warmup(260)
    run_weekly(rebalance, weekday=1, time="09:35")


def rebalance(context, data):
    lookback = int(context.params.get("lookback", 60))
    top_n = int(context.params.get("top_n", 4))
    max_weight = float(context.params.get("max_weight", 0.25))
    scores = {}
    for symbol in g.universe:
        bars = get_history(lookback + 1, "1d", "close", symbol)
        if len(bars) < lookback + 1:
            continue
        returns = bars["close"].pct_change().dropna()
        if len(returns):
            scores[symbol] = float(returns.std())
    selected = [symbol for symbol, _ in sorted(scores.items(), key=lambda item: item[1])[:top_n]]
    for symbol in get_positions().keys():
        if symbol not in selected:
            order_target_percent(symbol, 0.0, reason="low_vol_removed")
    weight = min(max_weight, 1.0 / len(selected)) if selected else 0.0
    for symbol in selected:
        order_target_percent(symbol, weight, reason="low_volatility")
$lowvol$, '{"params":[{"name":"lookback","type":"integer","default":60,"min":10,"max":250,"step":5,"labelKey":"strategyV2.params.lookback"},{"name":"top_n","type":"integer","default":4,"min":1,"max":10,"step":1,"labelKey":"strategyV2.params.topN"},{"name":"max_weight","type":"percent","default":0.25,"min":0.05,"max":1,"step":0.05,"labelKey":"strategyV2.params.maxWeight"}]}'::jsonb, '["strategy-v2","portfolio","cross-sectional","low-volatility","rotation"]'::jsonb, 'safety', 'cyan', 130, TRUE, '{"source":"system_seed","version":11,"apiVersion":2}'::jsonb, NOW()),

('strategy_v2_quality_growth', 'portfolio_strategy', 'Quality Growth Multi-Factor', 'A weekly point-in-time portfolio combining profitability, growth, and balance-sheet quality.', $quality$"""
Quality Growth Multi-Factor
Weekly point-in-time ranking by profitability, growth, and balance-sheet quality.
"""

# @param top_n int 5 range=1:10:1
# @param min_roe float 0.1 range=-1:1:0.01
# @param min_growth float 0 range=-1:5:0.01
# @param max_debt_to_equity float 2 range=0:10:0.1
# @param max_weight float 0.2 range=0.05:1:0.05

def initialize(context):
    g.universe = [
        "USStock:AAPL", "USStock:MSFT", "USStock:NVDA", "USStock:AMZN", "USStock:META",
        "USStock:GOOGL", "USStock:AVGO", "USStock:COST", "USStock:JPM", "USStock:XOM",
    ]
    context.set_universe(g.universe)
    context.set_benchmark("USStock:SPY")
    context.subscribe(frequency="1d")
    context.set_metadata(direction_mode="long_only")
    context.set_warmup(10)
    run_weekly(rebalance, weekday=1, time="09:35")


def rebalance(context, data):
    top_n = int(context.params.get("top_n", 5))
    min_roe = float(context.params.get("min_roe", 0.1))
    min_growth = float(context.params.get("min_growth", 0.0))
    max_debt = float(context.params.get("max_debt_to_equity", 2.0))
    max_weight = float(context.params.get("max_weight", 0.2))
    symbols = list(g.universe)
    factors = get_fundamentals(["ROE", "REVENUE_GROWTH", "DEBT_TO_EQUITY"], symbols)
    if factors.empty:
        return
    eligible = factors.dropna(subset=["ROE", "REVENUE_GROWTH", "DEBT_TO_EQUITY"])
    eligible = eligible[(eligible["ROE"] >= min_roe) & (eligible["REVENUE_GROWTH"] >= min_growth) & (eligible["DEBT_TO_EQUITY"] <= max_debt)]
    if eligible.empty:
        selected = []
    else:
        score = eligible["ROE"].rank(pct=True) + eligible["REVENUE_GROWTH"].rank(pct=True) - eligible["DEBT_TO_EQUITY"].rank(pct=True)
        selected = list(score.sort_values(ascending=False).head(top_n).index)
    for symbol in get_positions().keys():
        if symbol not in selected:
            order_target_percent(symbol, 0.0, reason="quality_removed")
    weight = min(max_weight, 1.0 / len(selected)) if selected else 0.0
    for symbol in selected:
        order_target_percent(symbol, weight, reason="quality_growth")
$quality$, '{"params":[{"name":"top_n","type":"integer","default":5,"min":1,"max":10,"step":1,"labelKey":"strategyV2.params.topN"},{"name":"min_roe","type":"number","default":0.1,"min":-1,"max":1,"step":0.01,"labelKey":"strategyV2.params.minRoe"},{"name":"min_growth","type":"number","default":0,"min":-1,"max":5,"step":0.01,"labelKey":"strategyV2.params.minGrowth"},{"name":"max_debt_to_equity","type":"number","default":2,"min":0,"max":10,"step":0.1,"labelKey":"strategyV2.params.maxDebtToEquity"},{"name":"max_weight","type":"percent","default":0.2,"min":0.05,"max":1,"step":0.05,"labelKey":"strategyV2.params.maxWeight"}]}'::jsonb, '["strategy-v2","portfolio","cross-sectional","fundamental","quality","growth"]'::jsonb, 'radar-chart', 'purple', 140, TRUE, '{"source":"system_seed","version":11,"apiVersion":2}'::jsonb, NOW()),
('strategy_v2_trend_pack', 'script', 'Trend Following Pack', '10 trend-following variants (variant=0~9) unified into one Strategy API V2 script.', $trendpack$"""
Trend Following Pack
Trend-following variants selected by context.params['variant'].
""" 

# @param variant int 0 range=0:9:1
# @param target_pct float 0.95 range=0.05:1:0.05
# @param allow_short bool true

def initialize(context):
    g.symbol = "USStock:SPY"
    context.set_universe([g.symbol])
    context.set_benchmark(g.symbol)
    context.subscribe(frequency="1d")
    context.set_metadata(direction_mode="both")
    context.set_warmup(260)


def handle_data(context, data):
    del data
    variant = int(context.params.get("variant", 0))
    target_pct = float(context.params.get("target_pct", 0.95))
    allow_short = bool(context.params.get("allow_short", True))

    bars = get_history(260, "1d", ["high", "low", "close", "volume"], g.symbol)
    if len(bars) < 210:
        return

    close = bars["close"].astype(float)
    high = bars["high"].astype(float)
    low = bars["low"].astype(float)
    volume = bars["volume"].astype(float)

    # Shared features
    ma20 = close.rolling(20).mean()
    ma50 = close.rolling(50).mean()
    ma100 = close.rolling(100).mean()
    ema20 = close.ewm(span=20, adjust=False).mean()
    ema60 = close.ewm(span=60, adjust=False).mean()
    roc126 = close.pct_change(126)
    ret1 = close.pct_change(1)
    vwap20 = (close * volume).rolling(20).sum() / volume.rolling(20).sum()
    donch_high55 = high.rolling(55).max()
    donch_low20 = low.rolling(20).min()
    adx14 = indicator("ADX", g.symbol, timeperiod=14)
    if len(adx14) < 2:
        return

    position = get_position(g.symbol)
    position_amt = float(position.amount or 0.0)
    is_long = position_amt > 1e-12
    is_short = position_amt < -1e-12

    desired = 0.0
    reason = ""

    # variant 0..9 mapping (top-level idea; exact rules are simplified for production stability)
    if variant == 0:
        # Single MA regime
        desired = target_pct if close.iloc[-1] > ma50.iloc[-1] else (-target_pct if allow_short else 0.0)
        reason = "trend_single_ma"
    elif variant == 1:
        # EMA slope
        slope = ema20.iloc[-1] - ema20.iloc[-2]
        desired = target_pct if slope > 0 else (-target_pct if allow_short else 0.0)
        reason = "trend_ema_slope"
    elif variant == 2:
        # EMA fast/slow
        desired = target_pct if ema20.iloc[-1] > ema60.iloc[-1] else (-target_pct if allow_short else 0.0)
        reason = "trend_ema_cross"
    elif variant == 3:
        # Time-series momentum
        roc = roc126.iloc[-1]
        desired = target_pct if roc > 0 else (-target_pct if allow_short else 0.0)
        reason = "trend_roc_126"
    elif variant == 4:
        # Donchian channel trend (breakout + exit on channel failure)
        near_high = close.iloc[-1] > donch_high55.iloc[-2]
        near_low = close.iloc[-1] < donch_low20.iloc[-2]
        if near_high:
            desired = target_pct
            reason = "trend_donchian_high"
        elif near_low:
            desired = -target_pct if allow_short else 0.0
            reason = "trend_donchian_low"
        else:
            desired = 0.0
            reason = "trend_donchian_flat"
    elif variant == 5:
        # Relative-strength proxy: 63d return vs mean daily return
        if len(close) < 63:
            return
        ret63 = (close.iloc[-1] / close.iloc[-63]) - 1.0
        mean_ret21 = ret1.tail(21).mean()
        desired = target_pct if ret63 > mean_ret21 else (-target_pct if allow_short else 0.0)
        reason = "trend_rs_proxy"
    elif variant == 6:
        # ADX-weighted regime
        adx_v = float(adx14.iloc[-1] or 0.0)
        trend_dir = close.iloc[-1] - ma50.iloc[-1]
        if adx_v > 25:
            desired = target_pct if trend_dir > 0 else (-target_pct if allow_short else 0.0)
            reason = "trend_adx_regime"
        else:
            desired = 0.0
            reason = "trend_adx_weak"
    elif variant == 7:
        # VWAP/cost-line regime
        vwap = float(vwap20.iloc[-1] or 0.0)
        desired = target_pct if close.iloc[-1] > vwap else (-target_pct if allow_short else 0.0)
        reason = "trend_vwap"
    elif variant == 8:
        # Multi-period MA fusion
        if ma20.iloc[-1] > ma50.iloc[-1] and close.iloc[-1] > ma20.iloc[-1]:
            desired = target_pct
            reason = "trend_fusion_long"
        elif ma20.iloc[-1] < ma50.iloc[-1] and close.iloc[-1] < ma20.iloc[-1]:
            desired = -target_pct if allow_short else 0.0
            reason = "trend_fusion_short"
        else:
            desired = 0.0
            reason = "trend_fusion_flat"
    else:
        # variant 9: trend + pullback confirmation (simplified)
        trend_up = close.iloc[-1] > ma100.iloc[-1]
        bounce_up = close.iloc[-1] > close.iloc[-2]
        trend_down = close.iloc[-1] < ma100.iloc[-1]
        bounce_down = close.iloc[-1] < close.iloc[-2]
        if trend_up and bounce_up:
            desired = target_pct
            reason = "trend_pullback_long"
        elif trend_down and bounce_down and allow_short:
            desired = -target_pct
            reason = "trend_pullback_short"
        else:
            desired = 0.0
            reason = "trend_pullback_flat"

    # Execute
    if desired > 0 and not is_long:
        order_target_percent(g.symbol, target_pct, reason=reason)
    elif desired < 0 and allow_short and not is_short:
        order_target_percent(g.symbol, -target_pct, reason=reason)
    elif abs(desired) <= 1e-12 and (is_long or is_short):
        order_target_percent(g.symbol, 0.0, reason=reason + "_exit")

$trendpack$, '{"params":[{"name":"variant","type":"integer","default":0,"min":0,"max":9,"step":1,"labelKey":"strategyV2.params.variant"},{"name":"target_pct","type":"percent","default":0.95,"min":0.05,"max":1,"step":0.05,"labelKey":"strategyV2.params.targetPosition"},{"name":"allow_short","type":"boolean","default":true,"labelKey":"strategyV2.params.allowShort"}]}'::jsonb, '["strategy-v2","cta","trend-following","pack","us-stock"]'::jsonb, 'line-chart', 'blue', 200, TRUE, '{"source":"system_seed","version":11,"apiVersion":2}'::jsonb, NOW()),
('strategy_v2_breakout_momentum_pack', 'script', 'Breakout & Momentum Pack', '10 breakout/momentum variants (variant=0~9) unified into one Strategy API V2 script.', $breakoutpack$"""
Breakout & Momentum Pack
Breakout & momentum variants selected by context.params['variant'].
"""

# @param variant int 0 range=0:9:1
# @param target_pct float 0.95 range=0.05:1:0.05
# @param allow_short bool true

def initialize(context):
    g.symbol = "USStock:SPY"
    context.set_universe([g.symbol])
    context.set_benchmark(g.symbol)
    context.subscribe(frequency="1d")
    context.set_metadata(direction_mode="both")
    context.set_warmup(260)


def handle_data(context, data):
    del data
    variant = int(context.params.get("variant", 0))
    target_pct = float(context.params.get("target_pct", 0.95))
    allow_short = bool(context.params.get("allow_short", True))

    bars = get_history(260, "1d", ["high", "low", "open", "close", "volume"], g.symbol)
    if len(bars) < 220:
        return

    close = bars["close"].astype(float)
    high = bars["high"].astype(float)
    low = bars["low"].astype(float)
    open_ = bars["open"].astype(float)
    volume = bars["volume"].astype(float)

    # Shared features
    ret1 = close.pct_change(1)
    avg_vol20 = volume.rolling(20).mean()

    # RSI (self-implemented to keep outputs stable)
    def _rsi(series, period):
        delta = series.diff()
        gain = delta.clip(lower=0)
        loss = (-delta).clip(lower=0)
        avg_gain = gain.rolling(period).mean()
        avg_loss = loss.rolling(period).mean()
        rs = avg_gain / avg_loss
        return 100.0 - (100.0 / (1.0 + rs))

    rsi14 = _rsi(close, 14)
    # MACD(12,26,9) histogram
    ema12 = close.ewm(span=12, adjust=False).mean()
    ema26 = close.ewm(span=26, adjust=False).mean()
    macd_line = ema12 - ema26
    signal_line = macd_line.ewm(span=9, adjust=False).mean()
    macd_hist = macd_line - signal_line

    # Bollinger(20,2)
    bb_mid = close.rolling(20).mean()
    bb_std = close.rolling(20).std()
    bb_upper = bb_mid + 2.0 * bb_std
    bb_lower = bb_mid - 2.0 * bb_std

    # Donchian-ish ranges
    high20 = high.rolling(20).max()
    low20 = low.rolling(20).min()
    high55 = high.rolling(55).max()
    low55 = low.rolling(55).min()
    high252 = high.rolling(252).max()
    low252 = low.rolling(252).min()

    position = get_position(g.symbol)
    position_amt = float(position.amount or 0.0)
    is_long = position_amt > 1e-12
    is_short = position_amt < -1e-12

    desired = 0.0
    reason = ""

    if variant == 0:
        # N-day high/low breakout
        desired = target_pct if close.iloc[-1] > high55.iloc[-2] else (-target_pct if close.iloc[-1] < low20.iloc[-2] and allow_short else 0.0)
        reason = "breakout_high55"
    elif variant == 1:
        # RSI breakout
        rsi_v = float(rsi14.iloc[-1] or 0.0)
        if rsi_v > 65:
            desired = target_pct
            reason = "breakout_rsi_long"
        elif rsi_v < 35 and allow_short:
            desired = -target_pct
            reason = "breakout_rsi_short"
        else:
            desired = 0.0
            reason = "breakout_rsi_flat"
    elif variant == 2:
        # MACD momentum
        hist_v = float(macd_hist.iloc[-1] or 0.0)
        desired = target_pct if hist_v > 0 else (-target_pct if allow_short else 0.0)
        reason = "breakout_macd_hist"
    elif variant == 3:
        # Bollinger band expansion
        c = close.iloc[-1]
        if c > bb_upper.iloc[-1]:
            desired = target_pct
            reason = "breakout_bb_upper"
        elif c < bb_lower.iloc[-1] and allow_short:
            desired = -target_pct
            reason = "breakout_bb_lower"
        else:
            desired = 0.0
            reason = "breakout_bb_flat"
    elif variant == 4:
        # Recent high breakout + simple confirmation
        recent_high = high20.iloc[-2]
        recent_low = low20.iloc[-2]
        if close.iloc[-1] > recent_high and close.iloc[-2] <= recent_high:
            desired = target_pct
            reason = "breakout_confirm_high"
        elif close.iloc[-1] < recent_low and close.iloc[-2] >= recent_low and allow_short:
            desired = -target_pct
            reason = "breakout_confirm_low"
        else:
            desired = 0.0
            reason = "breakout_confirm_flat"
    elif variant == 5:
        # Volume breakout with direction
        vol_now = volume.iloc[-1]
        vol_base = avg_vol20.iloc[-1] if avg_vol20.iloc[-1] else 0.0
        vol_ratio = vol_now / vol_base if vol_base else 0.0
        if vol_ratio >= 1.5 and close.iloc[-1] > close.iloc[-2]:
            desired = target_pct
            reason = "breakout_volume_long"
        elif vol_ratio >= 1.5 and close.iloc[-1] < close.iloc[-2] and allow_short:
            desired = -target_pct
            reason = "breakout_volume_short"
        else:
            desired = 0.0
            reason = "breakout_volume_flat"
    elif variant == 6:
        # 52-week extremes
        if close.iloc[-1] >= high252.iloc[-1] * 0.999:
            desired = target_pct
            reason = "breakout_52w_high"
        elif close.iloc[-1] <= low252.iloc[-1] * 1.001 and allow_short:
            desired = -target_pct
            reason = "breakout_52w_low"
        else:
            desired = 0.0
            reason = "breakout_52w_flat"
    elif variant == 7:
        # Gap/event-like breakout proxy
        prev_close = close.iloc[-2]
        gap_pct = (open_.iloc[-1] - prev_close) / prev_close if prev_close else 0.0
        if gap_pct >= 0.02 and close.iloc[-1] > open_.iloc[-1]:
            desired = target_pct
            reason = "breakout_gap_long"
        elif gap_pct <= -0.02 and close.iloc[-1] < open_.iloc[-1] and allow_short:
            desired = -target_pct
            reason = "breakout_gap_short"
        else:
            desired = 0.0
            reason = "breakout_gap_flat"
    elif variant == 8:
        # Term-structure momentum proxy: short/long MA spread
        ma20 = close.rolling(20).mean()
        ma60 = close.rolling(60).mean()
        if ma20.iloc[-1] > ma60.iloc[-1]:
            desired = target_pct
            reason = "breakout_term_mom_long"
        elif ma20.iloc[-1] < ma60.iloc[-1] and allow_short:
            desired = -target_pct
            reason = "breakout_term_mom_short"
        else:
            desired = 0.0
            reason = "breakout_term_mom_flat"
    else:
        # variant 9: volatility breakout proxy
        vol20 = ret1.rolling(20).std() * (252 ** 0.5)
        vol_base = vol20.rolling(60).mean().iloc[-1]
        if vol20.iloc[-1] > 1.2 * vol_base and ret1.iloc[-1] > 0:
            desired = target_pct
            reason = "breakout_vol_long"
        elif vol20.iloc[-1] > 1.2 * vol_base and ret1.iloc[-1] < 0 and allow_short:
            desired = -target_pct
            reason = "breakout_vol_short"
        else:
            desired = 0.0
            reason = "breakout_vol_flat"

    if desired > 0 and not is_long:
        order_target_percent(g.symbol, target_pct, reason=reason)
    elif desired < 0 and allow_short and not is_short:
        order_target_percent(g.symbol, -target_pct, reason=reason)
    elif abs(desired) <= 1e-12 and (is_long or is_short):
        order_target_percent(g.symbol, 0.0, reason=reason + "_exit")

$breakoutpack$, '{"params":[{"name":"variant","type":"integer","default":0,"min":0,"max":9,"step":1,"labelKey":"strategyV2.params.variant"},{"name":"target_pct","type":"percent","default":0.95,"min":0.05,"max":1,"step":0.05,"labelKey":"strategyV2.params.targetPosition"},{"name":"allow_short","type":"boolean","default":true,"labelKey":"strategyV2.params.allowShort"}]}'::jsonb, '["strategy-v2","cta","breakout","momentum","pack","us-stock"]'::jsonb, 'flag', 'cyan', 210, TRUE, '{"source":"system_seed","version":11,"apiVersion":2}'::jsonb, NOW()),
('strategy_v2_mean_reversion_pack', 'script', 'Mean Reversion Pack', '10 mean-reversion variants (variant=0~9) unified into one Strategy API V2 script.', $meanrevpack$"""
Mean Reversion Pack
Mean-reversion variants selected by context.params['variant'].
"""

# @param variant int 0 range=0:9:1
# @param target_pct float 0.95 range=0.05:1:0.05
# @param allow_short bool true

def initialize(context):
    g.symbol = "USStock:SPY"
    context.set_universe([g.symbol])
    context.set_benchmark(g.symbol)
    context.subscribe(frequency="1d")
    context.set_metadata(direction_mode="both")
    context.set_warmup(140)


def handle_data(context, data):
    del data
    variant = int(context.params.get("variant", 0))
    target_pct = float(context.params.get("target_pct", 0.95))
    allow_short = bool(context.params.get("allow_short", True))

    bars = get_history(140, "1d", ["high", "low", "close", "volume"], g.symbol)
    if len(bars) < 110:
        return

    close = bars["close"].astype(float)
    high = bars["high"].astype(float)
    low = bars["low"].astype(float)
    volume = bars["volume"].astype(float)

    # RSI (self-implemented)
    def _rsi(series, period):
        delta = series.diff()
        gain = delta.clip(lower=0)
        loss = (-delta).clip(lower=0)
        avg_gain = gain.rolling(period).mean()
        avg_loss = loss.rolling(period).mean()
        rs = avg_gain / avg_loss
        return 100.0 - (100.0 / (1.0 + rs))

    rsi14 = _rsi(close, 14)

    # Bollinger(20,2)
    bb_mid = close.rolling(20).mean()
    bb_std = close.rolling(20).std()
    bb_upper = bb_mid + 2.0 * bb_std
    bb_lower = bb_mid - 2.0 * bb_std

    # VWAP proxy
    vwap20 = (close * volume).rolling(20).sum() / volume.rolling(20).sum()

    # Z-score on price vs MA
    ma60 = close.rolling(60).mean()
    std60 = close.rolling(60).std()
    z60 = (close - ma60) / std60

    # Keltner-ish band (ATR proxy from high-low range)
    ema20 = close.ewm(span=20, adjust=False).mean()
    atr_proxy = (high - low).rolling(14).mean()
    kel_upper = ema20 + 1.5 * atr_proxy
    kel_lower = ema20 - 1.5 * atr_proxy

    # Range stats
    range30_high = high.rolling(30).max()
    range30_low = low.rolling(30).min()

    position = get_position(g.symbol)
    position_amt = float(position.amount or 0.0)
    is_long = position_amt > 1e-12
    is_short = position_amt < -1e-12

    desired = 0.0
    reason = ""
    c = close.iloc[-1]

    if variant == 0:
        # RSI extremes reversion
        r = float(rsi14.iloc[-1] or 0.0)
        if r <= 30:
            desired = target_pct
            reason = "meanrev_rsi_oversold"
        elif r >= 70 and allow_short:
            desired = -target_pct
            reason = "meanrev_rsi_overbought"
        else:
            desired = 0.0
            reason = "meanrev_rsi_flat"
    elif variant == 1:
        # Bollinger touch reversion
        if c < bb_lower.iloc[-1]:
            desired = target_pct
            reason = "meanrev_bb_lower"
        elif c > bb_upper.iloc[-1] and allow_short:
            desired = -target_pct
            reason = "meanrev_bb_upper"
        else:
            desired = 0.0
            reason = "meanrev_bb_flat"
    elif variant == 2:
        # Z-score reversion
        z = float(z60.iloc[-1] or 0.0)
        if z <= -1.5:
            desired = target_pct
            reason = "meanrev_z_low"
        elif z >= 1.5 and allow_short:
            desired = -target_pct
            reason = "meanrev_z_high"
        else:
            desired = 0.0
            reason = "meanrev_z_flat"
    elif variant == 3:
        # Keltner reversion proxy
        if c < kel_lower.iloc[-1]:
            desired = target_pct
            reason = "meanrev_keltner_lower"
        elif c > kel_upper.iloc[-1] and allow_short:
            desired = -target_pct
            reason = "meanrev_keltner_upper"
        else:
            desired = 0.0
            reason = "meanrev_keltner_flat"
    elif variant == 4:
        # VWAP deviation reversion
        v = float(vwap20.iloc[-1] or 0.0)
        dev = (c - v) / v if v else 0.0
        if dev <= -0.01:
            desired = target_pct
            reason = "meanrev_vwap_below"
        elif dev >= 0.01 and allow_short:
            desired = -target_pct
            reason = "meanrev_vwap_above"
        else:
            desired = 0.0
            reason = "meanrev_vwap_flat"
    elif variant == 5:
        # Range trading
        if c <= range30_low.iloc[-1] * 1.001:
            desired = target_pct
            reason = "meanrev_range_low"
        elif c >= range30_high.iloc[-1] * 0.999 and allow_short:
            desired = -target_pct
            reason = "meanrev_range_high"
        else:
            desired = 0.0
            reason = "meanrev_range_flat"
    elif variant == 6:
        # Residual EWMA mean reversion proxy
        ewma20 = close.ewm(span=20, adjust=False).mean()
        resid = close - ewma20
        resid_std = resid.rolling(20).std()
        z = (resid / resid_std).iloc[-1]
        if z <= -1.0:
            desired = target_pct
            reason = "meanrev_resid_low"
        elif z >= 1.0 and allow_short:
            desired = -target_pct
            reason = "meanrev_resid_high"
        else:
            desired = 0.0
            reason = "meanrev_resid_flat"
    elif variant == 7:
        # Volatility-adjusted reversion
        ret1 = close.pct_change(1)
        vol20 = ret1.rolling(20).std()
        ma20 = close.rolling(20).mean()
        dev = (c - ma20.iloc[-1]) / ma20.iloc[-1] if ma20.iloc[-1] else 0.0
        if vol20.iloc[-1] < vol20.rolling(60).mean().iloc[-1] and dev <= -0.02:
            desired = target_pct
            reason = "meanrev_vol_adj_long"
        elif vol20.iloc[-1] < vol20.rolling(60).mean().iloc[-1] and dev >= 0.02 and allow_short:
            desired = -target_pct
            reason = "meanrev_vol_adj_short"
        else:
            desired = 0.0
            reason = "meanrev_vol_adj_flat"
    elif variant == 8:
        # Relative price reversion proxy
        ratio = c / ma60.iloc[-1] if ma60.iloc[-1] else 1.0
        if ratio <= 0.95:
            desired = target_pct
            reason = "meanrev_ratio_low"
        elif ratio >= 1.05 and allow_short:
            desired = -target_pct
            reason = "meanrev_ratio_high"
        else:
            desired = 0.0
            reason = "meanrev_ratio_flat"
    else:
        # variant 9: short-term 5-day mean reversion
        ma5 = close.rolling(5).mean()
        dev = (c - ma5.iloc[-1]) / ma5.iloc[-1] if ma5.iloc[-1] else 0.0
        if dev <= -0.01:
            desired = target_pct
            reason = "meanrev_short_long"
        elif dev >= 0.01 and allow_short:
            desired = -target_pct
            reason = "meanrev_short_short"
        else:
            desired = 0.0
            reason = "meanrev_short_flat"

    if desired > 0 and not is_long:
        order_target_percent(g.symbol, target_pct, reason=reason)
    elif desired < 0 and allow_short and not is_short:
        order_target_percent(g.symbol, -target_pct, reason=reason)
    elif abs(desired) <= 1e-12 and (is_long or is_short):
        order_target_percent(g.symbol, 0.0, reason=reason + "_exit")

$meanrevpack$, '{"params":[{"name":"variant","type":"integer","default":0,"min":0,"max":9,"step":1,"labelKey":"strategyV2.params.variant"},{"name":"target_pct","type":"percent","default":0.95,"min":0.05,"max":1,"step":0.05,"labelKey":"strategyV2.params.targetPosition"},{"name":"allow_short","type":"boolean","default":true,"labelKey":"strategyV2.params.allowShort"}]}'::jsonb, '["strategy-v2","cta","mean-reversion","pack","us-stock"]'::jsonb, 'wave', 'green', 220, TRUE, '{"source":"system_seed","version":11,"apiVersion":2}'::jsonb, NOW()),
('strategy_v2_carry_pack', 'script', 'Carry Proxy Pack', '10 carry/value-risk variants (variant=0~9) unified into one Strategy API V2 script.', $carrypack$"""
Carry Proxy Pack
Carry proxy variants selected by context.params['variant'].
"""

# @param variant int 0 range=0:9:1
# @param target_pct float 0.95 range=0.05:1:0.05
# @param allow_short bool true

def initialize(context):
    g.symbol = "USStock:SPY"
    context.set_universe([g.symbol])
    context.set_benchmark(g.symbol)
    context.subscribe(frequency="1d")
    context.set_metadata(direction_mode="both")
    context.set_warmup(120)


def handle_data(context, data):
    del data
    variant = int(context.params.get("variant", 0))
    target_pct = float(context.params.get("target_pct", 0.95))
    allow_short = bool(context.params.get("allow_short", True))

    bars = get_history(120, "1d", ["close", "volume"], g.symbol)
    if len(bars) < 95:
        return

    close = bars["close"].astype(float)
    volume = bars["volume"].astype(float)

    ret1 = close.pct_change(1)
    mean_ret60 = ret1.rolling(60).mean()
    mean_ret20 = ret1.rolling(20).mean()
    vol20 = ret1.rolling(20).std() * (252 ** 0.5)
    vol20_base = vol20.rolling(60).mean()

    ma20 = close.rolling(20).mean()
    ma60 = close.rolling(60).mean()

    # RSI for tail-hedging proxy
    def _rsi(series, period):
        delta = series.diff()
        gain = delta.clip(lower=0)
        loss = (-delta).clip(lower=0)
        avg_gain = gain.rolling(period).mean()
        avg_loss = loss.rolling(period).mean()
        rs = avg_gain / avg_loss
        return 100.0 - (100.0 / (1.0 + rs))

    rsi14 = _rsi(close, 14)

    # Volume-weighted return mean proxy
    vw_ret = (ret1 * volume).rolling(20).sum() / volume.rolling(20).sum()

    position = get_position(g.symbol)
    position_amt = float(position.amount or 0.0)
    is_long = position_amt > 1e-12
    is_short = position_amt < -1e-12

    desired = 0.0
    reason = ""
    carry = mean_ret60.iloc[-1]

    if variant == 0:
        # Basic carry (time-average return)
        desired = target_pct if carry > 0 else (-target_pct if allow_short else 0.0)
        reason = "carry_basic"
    elif variant == 1:
        # Carry with trend risk filter
        regime_ok = close.iloc[-1] > ma60.iloc[-1]
        desired = target_pct if (carry > 0 and regime_ok) else 0.0
        if carry < 0 and close.iloc[-1] < ma60.iloc[-1] and allow_short:
            desired = -target_pct
        reason = "carry_trend_filter"
    elif variant == 2:
        # Roll-yield proxy: short mean > long mean
        if mean_ret20.iloc[-1] > mean_ret60.iloc[-1]:
            desired = target_pct
            reason = "carry_roll_long"
        elif mean_ret20.iloc[-1] < mean_ret60.iloc[-1] and allow_short:
            desired = -target_pct
            reason = "carry_roll_short"
        else:
            desired = 0.0
            reason = "carry_roll_flat"
    elif variant == 3:
        # Value/carry hybrid proxy: use debt-like risk as price volatility proxy
        risk_ok = vol20.iloc[-1] < vol20_base.iloc[-1] * 1.05
        desired = target_pct if (carry > 0 and risk_ok) else (-target_pct if carry < 0 and allow_short and risk_ok else 0.0)
        reason = "carry_value_risk"
    elif variant == 4:
        # Dividend/financing proxy: volume-weighted carry
        carry_vw = vw_ret.iloc[-1]
        desired = target_pct if carry_vw > 0 else (-target_pct if allow_short else 0.0)
        reason = "carry_volume_weighted"
    elif variant == 5:
        # Volatility carry: prefer low vol regimes
        if vol20.iloc[-1] < vol20_base.iloc[-1]:
            desired = target_pct if carry > 0 else (-target_pct if carry < 0 and allow_short else 0.0)
            reason = "carry_low_vol"
        else:
            desired = 0.0
            reason = "carry_high_vol_exit"
    elif variant == 6:
        # Trend-adjusted carry
        if close.iloc[-1] > ma20.iloc[-1] and carry > 0:
            desired = target_pct
            reason = "carry_trend_adj_long"
        elif close.iloc[-1] < ma20.iloc[-1] and carry < 0 and allow_short:
            desired = -target_pct
            reason = "carry_trend_adj_short"
        else:
            desired = 0.0
            reason = "carry_trend_adj_flat"
    elif variant == 7:
        # Mean/variance carry proxy: speed of returns (EWMA vs SMA)
        ew = ret1.ewm(span=20, adjust=False).mean().iloc[-1]
        sm = mean_ret20.iloc[-1]
        if ew > sm:
            desired = target_pct
            reason = "carry_mom_speed_long"
        elif ew < sm and allow_short:
            desired = -target_pct
            reason = "carry_mom_speed_short"
        else:
            desired = 0.0
            reason = "carry_mom_speed_flat"
    elif variant == 8:
        # Cross-sectional proxy cannot; use RSI & carry interaction
        r = float(rsi14.iloc[-1] or 50.0)
        if carry > 0 and r < 60:
            desired = target_pct
            reason = "carry_tail_safe_long"
        elif carry < 0 and r > 40 and allow_short:
            desired = -target_pct
            reason = "carry_tail_safe_short"
        else:
            desired = 0.0
            reason = "carry_tail_safe_flat"
    else:
        # variant 9: tail-hedged carry: RSI near middle only
        r = float(rsi14.iloc[-1] or 50.0)
        if 40 <= r <= 60:
            desired = target_pct if carry > 0 else (-target_pct if carry < 0 and allow_short else 0.0)
            reason = "carry_tail_hedged"
        else:
            desired = 0.0
            reason = "carry_tail_hedged_exit"

    if desired > 0 and not is_long:
        order_target_percent(g.symbol, target_pct, reason=reason)
    elif desired < 0 and allow_short and not is_short:
        order_target_percent(g.symbol, -target_pct, reason=reason)
    elif abs(desired) <= 1e-12 and (is_long or is_short):
        order_target_percent(g.symbol, 0.0, reason=reason + "_exit")

$carrypack$, '{"params":[{"name":"variant","type":"integer","default":0,"min":0,"max":9,"step":1,"labelKey":"strategyV2.params.variant"},{"name":"target_pct","type":"percent","default":0.95,"min":0.05,"max":1,"step":0.05,"labelKey":"strategyV2.params.targetPosition"},{"name":"allow_short","type":"boolean","default":true,"labelKey":"strategyV2.params.allowShort"}]}'::jsonb, '["strategy-v2","cta","carry","pack","us-stock"]'::jsonb, 'bar-chart', 'teal', 230, TRUE, '{"source":"system_seed","version":11,"apiVersion":2}'::jsonb, NOW()),
('strategy_v2_relative_value_pack', 'script', 'Relative Value Pack', '10 relative-value/stat-arb proxy variants (variant=0~9) unified into one Strategy API V2 script.', $relvalpack$"""
Relative Value Pack
Relative-value/stat-arb style proxies selected by context.params['variant'].
"""

# @param variant int 0 range=0:9:1
# @param target_pct float 0.95 range=0.05:1:0.05
# @param allow_short bool true

def initialize(context):
    g.symbol = "USStock:SPY"
    context.set_universe([g.symbol])
    context.set_benchmark(g.symbol)
    context.subscribe(frequency="1d")
    context.set_metadata(direction_mode="both")
    context.set_warmup(140)


def handle_data(context, data):
    del data
    variant = int(context.params.get("variant", 0))
    target_pct = float(context.params.get("target_pct", 0.95))
    allow_short = bool(context.params.get("allow_short", True))

    bars = get_history(140, "1d", ["high", "low", "close", "volume"], g.symbol)
    if len(bars) < 110:
        return

    close = bars["close"].astype(float)
    high = bars["high"].astype(float)
    low = bars["low"].astype(float)
    volume = bars["volume"].astype(float)

    ma20 = close.rolling(20).mean()
    ma50 = close.rolling(50).mean()
    ma60 = close.rolling(60).mean()
    std60 = close.rolling(60).std()
    z60 = (close - ma60) / std60

    # VWAP proxy
    vwap20 = (close * volume).rolling(20).sum() / volume.rolling(20).sum()

    # Spread proxies (price-vs-trend)
    spread1 = close - ma60
    spread1_std = spread1.rolling(60).std()
    zspread = spread1 / spread1_std

    # Range proxy
    range20 = (high - low).rolling(20).mean()

    position = get_position(g.symbol)
    position_amt = float(position.amount or 0.0)
    is_long = position_amt > 1e-12
    is_short = position_amt < -1e-12

    desired = 0.0
    reason = ""
    c = close.iloc[-1]

    if variant == 0:
        # Mean-revert on z-score
        z = float(z60.iloc[-1] or 0.0)
        if z >= 1.5 and allow_short:
            desired = -target_pct
        elif z <= -1.5:
            desired = target_pct
        else:
            desired = 0.0
        reason = "relval_zscore"
    elif variant == 1:
        # Ratio deviation reversion
        base = float(ma60.iloc[-1] or 0.0)
        ratio = c / base if base else 1.0
        if ratio >= 1.03 and allow_short:
            desired = -target_pct
        elif ratio <= 0.97:
            desired = target_pct
        else:
            desired = 0.0
        reason = "relval_ratio"
    elif variant == 2:
        # Spread between MA20 and MA50
        spread = ma20.iloc[-1] - ma50.iloc[-1]
        spread_z = spread / (abs(range20.iloc[-1] or 1.0))
        if spread_z > 0.01 and allow_short:
            desired = -target_pct
        elif spread_z < -0.01:
            desired = target_pct
        else:
            desired = 0.0
        reason = "relval_ma_spread"
    elif variant == 3:
        # Price vs VWAP deviation
        v = float(vwap20.iloc[-1] or 0.0)
        dev = (c - v) / v if v else 0.0
        if dev > 0.01 and allow_short:
            desired = -target_pct
        elif dev < -0.01:
            desired = target_pct
        else:
            desired = 0.0
        reason = "relval_vwap_dev"
    elif variant == 4:
        # Return extreme reversion proxy
        ret20 = c / close.iloc[-20] - 1.0 if len(close) >= 20 else 0.0
        if ret20 > 0.08 and allow_short:
            desired = -target_pct
        elif ret20 < -0.08:
            desired = target_pct
        else:
            desired = 0.0
        reason = "relval_ret_extreme"
    elif variant == 5:
        # Spread z-score on detrended series
        z = float(zspread.iloc[-1] or 0.0)
        if z > 1.2 and allow_short:
            desired = -target_pct
        elif z < -1.2:
            desired = target_pct
        else:
            desired = 0.0
        reason = "relval_spread_z"
    elif variant == 6:
        # Momentum reversal: opposite of ROC sign when stretched
        roc = close.pct_change(20).iloc[-1]
        if roc > 0.05 and allow_short:
            desired = -target_pct
        elif roc < -0.05:
            desired = target_pct
        else:
            desired = 0.0
        reason = "relval_mom_reversal"
    elif variant == 7:
        # Volatility-conditioned reversion proxy
        ret1 = close.pct_change(1)
        vol20 = ret1.rolling(20).std() * (252 ** 0.5)
        vol_ok = vol20.iloc[-1] < vol20.rolling(60).mean().iloc[-1]
        if vol_ok:
            dev = (c - ma20.iloc[-1]) / ma20.iloc[-1] if ma20.iloc[-1] else 0.0
            if dev > 0.02 and allow_short:
                desired = -target_pct
            elif dev < -0.02:
                desired = target_pct
            else:
                desired = 0.0
        else:
            desired = 0.0
        reason = "relval_vol_cond"
    elif variant == 8:
        # Value proxy with range: revert when price deviates but range is stable
        dev = (c - ma60.iloc[-1]) / ma60.iloc[-1] if ma60.iloc[-1] else 0.0
        stable = range20.iloc[-1] < range20.rolling(60).mean().iloc[-1]
        if stable and dev > 0.015 and allow_short:
            desired = -target_pct
        elif stable and dev < -0.015:
            desired = target_pct
        else:
            desired = 0.0
        reason = "relval_range_stable"
    else:
        # variant 9: RSI-proxy reversion (self-implemented)
        def _rsi(series, period):
            delta = series.diff()
            gain = delta.clip(lower=0)
            loss = (-delta).clip(lower=0)
            avg_gain = gain.rolling(period).mean()
            avg_loss = loss.rolling(period).mean()
            rs = avg_gain / avg_loss
            return 100.0 - (100.0 / (1.0 + rs))
        rsi14 = _rsi(close, 14).iloc[-1]
        r = float(rsi14 or 50.0)
        if r < 40:
            desired = target_pct
        elif r > 60 and allow_short:
            desired = -target_pct
        else:
            desired = 0.0
        reason = "relval_rsi_proxy"

    if desired > 0 and not is_long:
        order_target_percent(g.symbol, target_pct, reason=reason)
    elif desired < 0 and allow_short and not is_short:
        order_target_percent(g.symbol, -target_pct, reason=reason)
    elif abs(desired) <= 1e-12 and (is_long or is_short):
        order_target_percent(g.symbol, 0.0, reason=reason + "_exit")

$relvalpack$, '{"params":[{"name":"variant","type":"integer","default":0,"min":0,"max":9,"step":1,"labelKey":"strategyV2.params.variant"},{"name":"target_pct","type":"percent","default":0.95,"min":0.05,"max":1,"step":0.05,"labelKey":"strategyV2.params.targetPosition"},{"name":"allow_short","type":"boolean","default":true,"labelKey":"strategyV2.params.allowShort"}]}'::jsonb, '["strategy-v2","cta","relative-value","pack","us-stock"]'::jsonb, 'scatter', 'orange', 240, TRUE, '{"source":"system_seed","version":11,"apiVersion":2}'::jsonb, NOW()),
('strategy_v2_volatility_pack', 'script', 'Volatility / Risk Premia Pack', '10 volatility regime variants (variant=0~9) unified into one Strategy API V2 script.', $volpack$"""
Volatility / Risk Premia Pack
Volatility-regime style variants selected by context.params['variant'].
"""

# @param variant int 0 range=0:9:1
# @param target_pct float 0.95 range=0.05:1:0.05
# @param allow_short bool true

def initialize(context):
    g.symbol = "USStock:SPY"
    context.set_universe([g.symbol])
    context.set_benchmark(g.symbol)
    context.subscribe(frequency="1d")
    context.set_metadata(direction_mode="both")
    context.set_warmup(140)


def handle_data(context, data):
    del data
    variant = int(context.params.get("variant", 0))
    target_pct = float(context.params.get("target_pct", 0.95))
    allow_short = bool(context.params.get("allow_short", True))

    bars = get_history(140, "1d", ["high", "low", "close", "volume"], g.symbol)
    if len(bars) < 110:
        return

    close = bars["close"].astype(float)
    high = bars["high"].astype(float)
    low = bars["low"].astype(float)

    ret1 = close.pct_change(1)
    vol20 = ret1.rolling(20).std() * (252 ** 0.5)
    vol60 = ret1.rolling(60).std() * (252 ** 0.5)
    vol_base = vol20.rolling(60).mean()

    # Volatility width proxy (Bollinger band width)
    ma20 = close.rolling(20).mean()
    std20 = close.rolling(20).std()
    bb_width = (ma20 + 2.0 * std20) - (ma20 - 2.0 * std20)

    roc20 = close.pct_change(20).iloc[-1]
    c = close.iloc[-1]

    position = get_position(g.symbol)
    position_amt = float(position.amount or 0.0)
    is_long = position_amt > 1e-12
    is_short = position_amt < -1e-12

    desired = 0.0
    reason = ""

    if variant == 0:
        # Sell-vol proxy: long when vol is low and trend positive
        if vol20.iloc[-1] < vol_base.iloc[-1] and roc20 > 0:
            desired = target_pct
        elif vol20.iloc[-1] < vol_base.iloc[-1] and roc20 < 0 and allow_short:
            desired = -target_pct
        else:
            desired = 0.0
        reason = "vol_regime_sellvol"
    elif variant == 1:
        # Buy-vol proxy: short when vol high and trend negative
        if vol20.iloc[-1] > 1.2 * vol_base and roc20 > 0:
            desired = target_pct
            reason = "vol_regime_buyvol_long"
        elif vol20.iloc[-1] > 1.2 * vol_base and roc20 < 0 and allow_short:
            desired = -target_pct
            reason = "vol_regime_buyvol_short"
        else:
            desired = 0.0
            reason = "vol_regime_buyvol_flat"
    elif variant == 2:
        # Term structure proxy: if short vol < long vol => risk-on long
        if vol20.iloc[-1] < vol60.iloc[-1]:
            desired = target_pct if roc20 > 0 else (-target_pct if roc20 < 0 and allow_short else 0.0)
            reason = "vol_term_contraction"
        else:
            desired = 0.0
            reason = "vol_term_expansion_exit"
    elif variant == 3:
        # Skew proxy: down-vol vs up-vol approximation via signed returns
        up_std = ret1.where(ret1 > 0).rolling(20).std()
        dn_std = ret1.where(ret1 < 0).rolling(20).std()
        skew = float(up_std.iloc[-1] - dn_std.iloc[-1] or 0.0)
        if skew > 0 and allow_short:
            desired = -target_pct
            reason = "vol_skew_short"
        elif skew < 0:
            desired = target_pct
            reason = "vol_skew_long"
        else:
            desired = 0.0
            reason = "vol_skew_flat"
    elif variant == 4:
        # Calendar spread proxy: vol20 vs bb_width
        width = bb_width.iloc[-1] if bb_width.iloc[-1] else 0.0
        if width > 1.2 * bb_width.rolling(60).mean().iloc[-1]:
            desired = -target_pct if allow_short and roc20 < 0 else (target_pct if roc20 > 0 else 0.0)
            reason = "vol_calendar_wide"
        else:
            desired = 0.0
            reason = "vol_calendar_narrow_flat"
    elif variant == 5:
        # Risk-off: if vol too high, go short (or flat if not allowed)
        if vol20.iloc[-1] > 1.5 * vol_base.iloc[-1] and allow_short:
            desired = -target_pct
            reason = "vol_riskoff_short"
        else:
            desired = 0.0
            reason = "vol_riskoff_flat"
    elif variant == 6:
        # Trend + vol expansion: follow roc20 direction
        if vol20.iloc[-1] > vol_base.iloc[-1]:
            if roc20 > 0:
                desired = target_pct
                reason = "vol_trend_follow_long"
            elif roc20 < 0 and allow_short:
                desired = -target_pct
                reason = "vol_trend_follow_short"
            else:
                desired = 0.0
                reason = "vol_trend_follow_flat"
        else:
            desired = 0.0
            reason = "vol_trend_follow_exit"
    elif variant == 7:
        # Mean reversion in volatility: when vol high but stable, fade trend
        if vol20.iloc[-1] > vol_base.iloc[-1] and (vol20.iloc[-1] - vol20.shift(1).iloc[-1]) < 0:
            if roc20 < 0:
                desired = target_pct
                reason = "vol_fade_shorttrend_long"
            elif roc20 > 0 and allow_short:
                desired = -target_pct
                reason = "vol_fade_longtrend_short"
            else:
                desired = 0.0
                reason = "vol_fade_flat"
        else:
            desired = 0.0
            reason = "vol_fade_exit"
    elif variant == 8:
        # Carry-vs-vol interaction proxy: long carry when vol low
        mean_ret60 = ret1.rolling(60).mean()
        carry = mean_ret60.iloc[-1]
        if vol20.iloc[-1] < vol_base.iloc[-1]:
            desired = target_pct if carry > 0 else (-target_pct if carry < 0 and allow_short else 0.0)
            reason = "vol_carry_longshort"
        else:
            desired = 0.0
            reason = "vol_carry_exit"
    else:
        # variant 9: vol-of-vol proxy; trade direction by last return
        vol_change = vol20.diff()
        if vol_change.iloc[-1] > vol_change.rolling(60).mean().iloc[-1] and ret1.iloc[-1] > 0:
            desired = target_pct
            reason = "volofvol_long"
        elif vol_change.iloc[-1] > vol_change.rolling(60).mean().iloc[-1] and ret1.iloc[-1] < 0 and allow_short:
            desired = -target_pct
            reason = "volofvol_short"
        else:
            desired = 0.0
            reason = "volofvol_flat"

    if desired > 0 and not is_long:
        order_target_percent(g.symbol, target_pct, reason=reason)
    elif desired < 0 and allow_short and not is_short:
        order_target_percent(g.symbol, -target_pct, reason=reason)
    elif abs(desired) <= 1e-12 and (is_long or is_short):
        order_target_percent(g.symbol, 0.0, reason=reason + "_exit")

$volpack$, '{"params":[{"name":"variant","type":"integer","default":0,"min":0,"max":9,"step":1,"labelKey":"strategyV2.params.variant"},{"name":"target_pct","type":"percent","default":0.95,"min":0.05,"max":1,"step":0.05,"labelKey":"strategyV2.params.targetPosition"},{"name":"allow_short","type":"boolean","default":true,"labelKey":"strategyV2.params.allowShort"}]}'::jsonb, '["strategy-v2","cta","volatility","pack","us-stock"]'::jsonb, 'area-chart', 'red', 250, TRUE, '{"source":"system_seed","version":11,"apiVersion":2}'::jsonb, NOW()),
('strategy_v2_market_microstructure_pack', 'script', 'Market Microstructure Pack', '10 microstructure/execution proxy variants (variant=0~9) unified into one Strategy API V2 script.', $micropp$"""
Market Microstructure Pack
Microstructure/flow proxy variants selected by context.params['variant'].
"""

# @param variant int 0 range=0:9:1
# @param target_pct float 0.95 range=0.05:1:0.05
# @param allow_short bool true

def initialize(context):
    g.symbol = "USStock:SPY"
    context.set_universe([g.symbol])
    context.set_benchmark(g.symbol)
    context.subscribe(frequency="1d")
    context.set_metadata(direction_mode="both")
    context.set_warmup(60)


def handle_data(context, data):
    del data
    variant = int(context.params.get("variant", 0))
    target_pct = float(context.params.get("target_pct", 0.95))
    allow_short = bool(context.params.get("allow_short", True))

    bars = get_history(60, "1d", ["open", "high", "low", "close", "volume"], g.symbol)
    if len(bars) < 50:
        return

    open_ = bars["open"].astype(float)
    high = bars["high"].astype(float)
    low = bars["low"].astype(float)
    close = bars["close"].astype(float)
    volume = bars["volume"].astype(float)

    ret1 = close.pct_change(1)
    order_flow = (ret1 * volume).fillna(0.0)
    ofi5 = order_flow.tail(5).sum()

    range1 = (high - low) / close.replace(0.0, 1.0)
    spread5 = range1.tail(5).mean()

    vwap5 = (close * volume).tail(5).sum() / volume.tail(5).sum()

    position = get_position(g.symbol)
    position_amt = float(position.amount or 0.0)
    is_long = position_amt > 1e-12
    is_short = position_amt < -1e-12

    desired = 0.0
    reason = ""
    c = close.iloc[-1]

    if variant == 0:
        # OFI direction (imbalance following)
        desired = target_pct if ofi5 > 0 else (-target_pct if allow_short else 0.0)
        reason = "micro_ofi_follow"
    elif variant == 1:
        # Short-term reversal on large moves
        r = ret1.iloc[-1]
        if r > 0.02:
            desired = -target_pct if allow_short else 0.0
            reason = "micro_reversal_down"
        elif r < -0.02:
            desired = target_pct
            reason = "micro_reversal_up"
        else:
            desired = 0.0
            reason = "micro_reversal_flat"
    elif variant == 2:
        # Spread capture proxy: buy when close < vwap5 and spread is high
        spread_base = range1.tail(20).mean().iloc[-1]
        spread_high = spread5 > spread_base
        if spread_high and c < vwap5:
            desired = target_pct
            reason = "micro_spread_long"
        elif spread_high and c > vwap5 and allow_short:
            desired = -target_pct
            reason = "micro_spread_short"
        else:
            desired = 0.0
            reason = "micro_spread_flat"
    elif variant == 3:
        # VWAP mean reversion (short-term)
        dev = (c - vwap5) / vwap5 if vwap5 else 0.0
        if dev < -0.005:
            desired = target_pct
            reason = "micro_vwap_revert_long"
        elif dev > 0.005 and allow_short:
            desired = -target_pct
            reason = "micro_vwap_revert_short"
        else:
            desired = 0.0
            reason = "micro_vwap_revert_flat"
    elif variant == 4:
        # Gap proxy
        prev_close = close.iloc[-2]
        gap_pct = (open_.iloc[-1] - prev_close) / prev_close if prev_close else 0.0
        if gap_pct > 0.01 and close.iloc[-1] > open_.iloc[-1]:
            desired = target_pct
            reason = "micro_gap_long"
        elif gap_pct < -0.01 and close.iloc[-1] < open_.iloc[-1] and allow_short:
            desired = -target_pct
            reason = "micro_gap_short"
        else:
            desired = 0.0
            reason = "micro_gap_flat"
    elif variant == 5:
        # Persistence: OFI sign + ret sign
        if ofi5 > 0 and ret1.iloc[-1] > 0:
            desired = target_pct
            reason = "micro_persist_long"
        elif ofi5 < 0 and ret1.iloc[-1] < 0 and allow_short:
            desired = -target_pct
            reason = "micro_persist_short"
        else:
            desired = 0.0
            reason = "micro_persist_flat"
    elif variant == 6:
        # Liquidity/proxy: higher volume -> follow
        vol_now = volume.iloc[-1]
        vol_base = volume.tail(20).mean()
        vol_ratio = vol_now / vol_base if vol_base else 0.0
        if vol_ratio > 1.2:
            desired = target_pct if ret1.iloc[-1] > 0 else (-target_pct if allow_short else 0.0)
            reason = "micro_liquid_follow"
        else:
            desired = 0.0
            reason = "micro_liquid_flat"
    elif variant == 7:
        # Volatility + flow: risk guard
        vol20 = ret1.tail(20).std() * (252 ** 0.5)
        if vol20 < ret1.tail(60).std() * (252 ** 0.5) and ofi5 > 0:
            desired = target_pct
            reason = "micro_guard_long"
        elif vol20 < ret1.tail(60).std() * (252 ** 0.5) and ofi5 < 0 and allow_short:
            desired = -target_pct
            reason = "micro_guard_short"
        else:
            desired = 0.0
            reason = "micro_guard_flat"
    elif variant == 8:
        # Microprice proxy: mid of high/low vs close
        mid = (high.iloc[-1] + low.iloc[-1]) / 2.0
        if c < mid:
            desired = target_pct
            reason = "micro_mid_long"
        elif c > mid and allow_short:
            desired = -target_pct
            reason = "micro_mid_short"
        else:
            desired = 0.0
            reason = "micro_mid_flat"
    else:
        # variant 9: short-term spread threshold
        if spread5 > range1.tail(20).mean().iloc[-1] and ret1.iloc[-1] > 0:
            desired = target_pct
            reason = "micro_spread_thr_long"
        elif spread5 > range1.tail(20).mean().iloc[-1] and ret1.iloc[-1] < 0 and allow_short:
            desired = -target_pct
            reason = "micro_spread_thr_short"
        else:
            desired = 0.0
            reason = "micro_spread_thr_flat"

    if desired > 0 and not is_long:
        order_target_percent(g.symbol, target_pct, reason=reason)
    elif desired < 0 and allow_short and not is_short:
        order_target_percent(g.symbol, -target_pct, reason=reason)
    elif abs(desired) <= 1e-12 and (is_long or is_short):
        order_target_percent(g.symbol, 0.0, reason=reason + "_exit")

$micropp$, '{"params":[{"name":"variant","type":"integer","default":0,"min":0,"max":9,"step":1,"labelKey":"strategyV2.params.variant"},{"name":"target_pct","type":"percent","default":0.95,"min":0.05,"max":1,"step":0.05,"labelKey":"strategyV2.params.targetPosition"},{"name":"allow_short","type":"boolean","default":true,"labelKey":"strategyV2.params.allowShort"}]}'::jsonb, '["strategy-v2","cta","microstructure","pack","us-stock"]'::jsonb, 'candlestick', 'purple', 260, TRUE, '{"source":"system_seed","version":11,"apiVersion":2}'::jsonb, NOW())
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
