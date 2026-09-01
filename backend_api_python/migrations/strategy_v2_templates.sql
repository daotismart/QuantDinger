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
    'strategy_v2_market_microstructure_pack',
    'strategy_v2_gex_lsp_iron_condor'
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
('strategy_v2_trend_pack', 'portfolio_strategy', 'Trend Following Pack', 'Futures & options trend-following with 10 variants on 1m bars aggregated to 30m.', $trendpack$"""
Trend Following Pack
Futures & options trend-following variants on 1m bars aggregated to 30m.
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

    bars = get_history(8000, "1m", ["open", "high", "low", "close", "volume"], g.futures)
    o30, h30, l30, c30, v30 = _agg30(bars)
    if o30 is None or len(c30) < 100:
        return

    ma20 = _rolling_mean(c30, 20)
    ma50 = _rolling_mean(c30, 50)
    ma100 = _rolling_mean(c30, 100)

    position = get_position(g.futures)
    position_amt = float(position.amount or 0.0)
    is_long = position_amt > 1e-12
    is_short = position_amt < -1e-12

    desired = 0.0
    reason = ""

    if variant == 0:
        desired = target_pct if c30[-1] > ma50[-1] else (-target_pct if allow_short else 0.0)
        reason = "trend_single_ma"
    elif variant == 1:
        ema20 = _rolling_mean(c30, 20)
        if len(ema20) >= 2:
            slope = ema20[-1] - ema20[-2]
            desired = target_pct if slope > 0 else (-target_pct if allow_short else 0.0)
        reason = "trend_ema_slope"
    elif variant == 2:
        ema20 = _rolling_mean(c30, 20)
        ema60 = _rolling_mean(c30, 60)
        if ema20 and ema60:
            desired = target_pct if ema20[-1] > ema60[-1] else (-target_pct if allow_short else 0.0)
        reason = "trend_ema_cross"
    elif variant == 3:
        if len(c30) > 126:
            roc = (c30[-1] / c30[-126]) - 1.0
            desired = target_pct if roc > 0 else (-target_pct if allow_short else 0.0)
        reason = "trend_roc_126"
    elif variant == 4:
        donch_h55 = _rolling_max(h30, 55)
        donch_l20 = _rolling_min(l30, 20)
        if donch_h55 and donch_l20 and len(donch_h55) >= 2 and len(donch_l20) >= 2:
            if c30[-1] > donch_h55[-2]:
                desired = target_pct
                reason = "trend_donchian_high"
            elif c30[-1] < donch_l20[-2]:
                desired = -target_pct if allow_short else 0.0
                reason = "trend_donchian_low"
            else:
                desired = 0.0
                reason = "trend_donchian_flat"
        else:
            reason = "trend_donchian_flat"
    elif variant == 5:
        if len(c30) >= 63:
            ret63 = (c30[-1] / c30[-63]) - 1.0
            recent = [c30[i] / c30[i - 1] - 1.0 for i in range(max(1, len(c30) - 21), len(c30))]
            mean_ret21 = sum(recent) / len(recent) if recent else 0.0
            desired = target_pct if ret63 > mean_ret21 else (-target_pct if allow_short else 0.0)
        reason = "trend_rs_proxy"
    elif variant == 6:
        if ma50:
            trend_dir = c30[-1] - ma50[-1]
            desired = target_pct if trend_dir > 0 else (-target_pct if allow_short else 0.0)
        reason = "trend_adx_regime"
    elif variant == 7:
        vwap_vals = []
        for i in range(20, len(c30) + 1):
            cv = sum(c30[i - 20:i][j] * v30[i - 20:i][j] for j in range(20))
            sv = sum(v30[i - 20:i])
            vwap_vals.append(cv / sv if sv else c30[i - 1])
        if vwap_vals:
            desired = target_pct if c30[-1] > vwap_vals[-1] else (-target_pct if allow_short else 0.0)
        reason = "trend_vwap"
    elif variant == 8:
        if ma20 and ma50:
            if ma20[-1] > ma50[-1] and c30[-1] > ma20[-1]:
                desired = target_pct
                reason = "trend_fusion_long"
            elif ma20[-1] < ma50[-1] and c30[-1] < ma20[-1]:
                desired = -target_pct if allow_short else 0.0
                reason = "trend_fusion_short"
            else:
                desired = 0.0
                reason = "trend_fusion_flat"
        else:
            reason = "trend_fusion_flat"
    else:
        if ma100:
            trend_up = c30[-1] > ma100[-1]
            bounce_up = c30[-1] > c30[-2]
            trend_down = c30[-1] < ma100[-1]
            bounce_down = c30[-1] < c30[-2]
            if trend_up and bounce_up:
                desired = target_pct
                reason = "trend_pullback_long"
            elif trend_down and bounce_down and allow_short:
                desired = -target_pct
                reason = "trend_pullback_short"
            else:
                desired = 0.0
                reason = "trend_pullback_flat"
        else:
            reason = "trend_pullback_flat"

    if desired > 0 and not is_long:
        order_target_percent(g.futures, target_pct, reason=reason)
    elif desired < 0 and allow_short and not is_short:
        order_target_percent(g.futures, -target_pct, reason=reason)
    elif abs(desired) <= 1e-12 and (is_long or is_short):
        order_target_percent(g.futures, 0.0, reason=reason + "_exit")

$trendpack$, '{"params":[{"name":"variant","type":"integer","default":0,"min":0,"max":9,"step":1,"labelKey":"strategyV2.params.variant"},{"name":"target_pct","type":"percent","default":0.95,"min":0.05,"max":1,"step":0.05,"labelKey":"strategyV2.params.targetPosition"},{"name":"allow_short","type":"boolean","default":true,"labelKey":"strategyV2.params.allowShort"}]}'::jsonb, '["strategy-v2","cta","trend-following","pack","cn-futures","options"]'::jsonb, 'line-chart', 'blue', 200, TRUE, '{"source":"system_seed","version":11,"apiVersion":2}'::jsonb, NOW()),
('strategy_v2_breakout_momentum_pack', 'portfolio_strategy', 'Breakout & Momentum Pack', 'Futures & options breakout/momentum with 10 variants on 1m bars aggregated to 30m.', $breakoutpack$"""
Breakout & Momentum Pack
Futures & options breakout/momentum variants on 1m bars aggregated to 30m.
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
        result = []
        for i in range(period, len(arr) + 1):
            window = arr[i - period:i]
            m = sum(window) / period
            var = sum((x - m) ** 2 for x in window) / period
            result.append(var ** 0.5)
        return result

    def _rsi(arr, period):
        if len(arr) < period + 1:
            return []
        deltas = [arr[i] - arr[i - 1] for i in range(1, len(arr))]
        result = []
        for i in range(period, len(deltas) + 1):
            window = deltas[i - period:i]
            gains = [d if d > 0 else 0 for d in window]
            losses = [-d if d < 0 else 0 for d in window]
            ag = sum(gains) / period
            al = sum(losses) / period
            if al == 0:
                result.append(100.0)
            else:
                result.append(100.0 - 100.0 / (1.0 + ag / al))
        return result

    bars = get_history(8000, "1m", ["open", "high", "low", "close", "volume"], g.futures)
    o30, h30, l30, c30, v30 = _agg30(bars)
    if o30 is None or len(c30) < 100:
        return

    rsi14 = _rsi(c30, 14)
    high20 = _rolling_max(h30, 20)
    low20 = _rolling_min(l30, 20)
    high55 = _rolling_max(h30, 55)
    bb_mid = _rolling_mean(c30, 20)
    bb_std = _rolling_std(c30, 20)
    avg_vol20 = _rolling_mean(v30, 20)

    position = get_position(g.futures)
    position_amt = float(position.amount or 0.0)
    is_long = position_amt > 1e-12
    is_short = position_amt < -1e-12

    desired = 0.0
    reason = ""

    if variant == 0:
        if high55 and len(high55) >= 2 and low20 and len(low20) >= 2:
            desired = target_pct if c30[-1] > high55[-2] else (-target_pct if c30[-1] < low20[-2] and allow_short else 0.0)
        reason = "breakout_high55"
    elif variant == 1:
        if rsi14:
            rsi_v = rsi14[-1]
            if rsi_v > 65:
                desired = target_pct
                reason = "breakout_rsi_long"
            elif rsi_v < 35 and allow_short:
                desired = -target_pct
                reason = "breakout_rsi_short"
            else:
                reason = "breakout_rsi_flat"
        else:
            reason = "breakout_rsi_flat"
    elif variant == 2:
        ema12 = _rolling_mean(c30, 12)
        ema26 = _rolling_mean(c30, 26)
        if ema12 and ema26:
            ml = len(min(ema12, ema26, key=len))
            macd = [ema12[len(ema12) - ml + i] - ema26[len(ema26) - ml + i] for i in range(ml)]
            sig = _rolling_mean(macd, 9)
            if sig:
                hist_v = macd[-1] - sig[-1]
                desired = target_pct if hist_v > 0 else (-target_pct if allow_short else 0.0)
        reason = "breakout_macd_hist"
    elif variant == 3:
        if bb_mid and bb_std:
            bb_upper = bb_mid[-1] + 2.0 * bb_std[-1]
            bb_lower = bb_mid[-1] - 2.0 * bb_std[-1]
            if c30[-1] > bb_upper:
                desired = target_pct
                reason = "breakout_bb_upper"
            elif c30[-1] < bb_lower and allow_short:
                desired = -target_pct
                reason = "breakout_bb_lower"
            else:
                reason = "breakout_bb_flat"
        else:
            reason = "breakout_bb_flat"
    elif variant == 4:
        if high20 and low20 and len(high20) >= 2 and len(low20) >= 2:
            if c30[-1] > high20[-2] and c30[-2] <= high20[-2]:
                desired = target_pct
                reason = "breakout_confirm_high"
            elif c30[-1] < low20[-2] and c30[-2] >= low20[-2] and allow_short:
                desired = -target_pct
                reason = "breakout_confirm_low"
            else:
                reason = "breakout_confirm_flat"
        else:
            reason = "breakout_confirm_flat"
    elif variant == 5:
        if avg_vol20 and avg_vol20[-1] > 0:
            vol_ratio = v30[-1] / avg_vol20[-1]
            if vol_ratio >= 1.5 and c30[-1] > c30[-2]:
                desired = target_pct
                reason = "breakout_volume_long"
            elif vol_ratio >= 1.5 and c30[-1] < c30[-2] and allow_short:
                desired = -target_pct
                reason = "breakout_volume_short"
            else:
                reason = "breakout_volume_flat"
        else:
            reason = "breakout_volume_flat"
    elif variant == 6:
        if len(c30) > 252:
            high252 = max(h30[-252:])
            low252 = min(l30[-252:])
            rng = high252 - low252
            if rng > 0:
                pos = (c30[-1] - low252) / rng
                if pos > 0.8:
                    desired = target_pct
                    reason = "breakout_range_high"
                elif pos < 0.2 and allow_short:
                    desired = -target_pct
                    reason = "breakout_range_low"
                else:
                    reason = "breakout_range_flat"
            else:
                reason = "breakout_range_flat"
        else:
            reason = "breakout_range_flat"
    elif variant == 7:
        if rsi14 and len(rsi14) >= 2:
            if rsi14[-1] > 50 and rsi14[-2] <= 50:
                desired = target_pct
                reason = "breakout_rsi_cross_long"
            elif rsi14[-1] < 50 and rsi14[-2] >= 50 and allow_short:
                desired = -target_pct
                reason = "breakout_rsi_cross_short"
            else:
                reason = "breakout_rsi_cross_flat"
        else:
            reason = "breakout_rsi_cross_flat"
    elif variant == 8:
        if len(c30) >= 10:
            ret5 = (c30[-1] / c30[-5]) - 1.0
            ret10 = (c30[-1] / c30[-10]) - 1.0
            if ret5 > 0 and ret10 > 0:
                desired = target_pct
                reason = "breakout_dual_mom_long"
            elif ret5 < 0 and ret10 < 0 and allow_short:
                desired = -target_pct
                reason = "breakout_dual_mom_short"
            else:
                reason = "breakout_dual_mom_flat"
        else:
            reason = "breakout_dual_mom_flat"
    else:
        if high20 and low20:
            mid = (high20[-1] + low20[-1]) / 2.0
            if c30[-1] > mid:
                desired = target_pct
                reason = "breakout_channel_long"
            elif c30[-1] < mid and allow_short:
                desired = -target_pct
                reason = "breakout_channel_short"
            else:
                reason = "breakout_channel_flat"
        else:
            reason = "breakout_channel_flat"

    if desired > 0 and not is_long:
        order_target_percent(g.futures, target_pct, reason=reason)
    elif desired < 0 and allow_short and not is_short:
        order_target_percent(g.futures, -target_pct, reason=reason)
    elif abs(desired) <= 1e-12 and (is_long or is_short):
        order_target_percent(g.futures, 0.0, reason=reason + "_exit")

$breakoutpack$, '{"params":[{"name":"variant","type":"integer","default":0,"min":0,"max":9,"step":1,"labelKey":"strategyV2.params.variant"},{"name":"target_pct","type":"percent","default":0.95,"min":0.05,"max":1,"step":0.05,"labelKey":"strategyV2.params.targetPosition"},{"name":"allow_short","type":"boolean","default":true,"labelKey":"strategyV2.params.allowShort"}]}'::jsonb, '["strategy-v2","cta","breakout","momentum","pack","cn-futures","options"]'::jsonb, 'rocket', 'orange', 210, TRUE, '{"source":"system_seed","version":11,"apiVersion":2}'::jsonb, NOW()),
('strategy_v2_mean_reversion_pack', 'portfolio_strategy', 'Mean Reversion Pack', 'Futures & options mean-reversion with 10 variants on 1m bars aggregated to 30m.', $meanrevpack$"""
Mean Reversion Pack
Futures & options mean-reversion variants on 1m bars aggregated to 30m.
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

    def _rolling_std(arr, period):
        if len(arr) < period:
            return []
        result = []
        for i in range(period, len(arr) + 1):
            window = arr[i - period:i]
            m = sum(window) / period
            var = sum((x - m) ** 2 for x in window) / period
            result.append(var ** 0.5)
        return result

    def _rsi(arr, period):
        if len(arr) < period + 1:
            return []
        deltas = [arr[i] - arr[i - 1] for i in range(1, len(arr))]
        result = []
        for i in range(period, len(deltas) + 1):
            window = deltas[i - period:i]
            gains = [d if d > 0 else 0 for d in window]
            losses = [-d if d < 0 else 0 for d in window]
            ag = sum(gains) / period
            al = sum(losses) / period
            if al == 0:
                result.append(100.0)
            else:
                result.append(100.0 - 100.0 / (1.0 + ag / al))
        return result

    bars = get_history(8000, "1m", ["open", "high", "low", "close", "volume"], g.futures)
    o30, h30, l30, c30, v30 = _agg30(bars)
    if o30 is None or len(c30) < 100:
        return

    ma20 = _rolling_mean(c30, 20)
    bb_std = _rolling_std(c30, 20)
    rsi14 = _rsi(c30, 14)

    position = get_position(g.futures)
    position_amt = float(position.amount or 0.0)
    is_long = position_amt > 1e-12
    is_short = position_amt < -1e-12

    desired = 0.0
    reason = ""

    if variant == 0:
        if ma20 and bb_std and bb_std[-1] > 0:
            zscore = (c30[-1] - ma20[-1]) / bb_std[-1]
            if zscore < -2.0:
                desired = target_pct
                reason = "mr_bb_long"
            elif zscore > 2.0 and allow_short:
                desired = -target_pct
                reason = "mr_bb_short"
            else:
                reason = "mr_bb_flat"
        else:
            reason = "mr_bb_flat"
    elif variant == 1:
        if rsi14:
            rsi_v = rsi14[-1]
            if rsi_v < 30:
                desired = target_pct
                reason = "mr_rsi_oversold"
            elif rsi_v > 70 and allow_short:
                desired = -target_pct
                reason = "mr_rsi_overbought"
            else:
                reason = "mr_rsi_flat"
        else:
            reason = "mr_rsi_flat"
    elif variant == 2:
        ma50 = _rolling_mean(c30, 50)
        if ma50:
            dev = (c30[-1] - ma50[-1]) / ma50[-1] if ma50[-1] != 0 else 0
            if dev < -0.03:
                desired = target_pct
                reason = "mr_ma50_long"
            elif dev > 0.03 and allow_short:
                desired = -target_pct
                reason = "mr_ma50_short"
            else:
                reason = "mr_ma50_flat"
        else:
            reason = "mr_ma50_flat"
    elif variant == 3:
        if len(c30) >= 5:
            ret3 = (c30[-1] / c30[-3]) - 1.0
            if ret3 < -0.02:
                desired = target_pct
                reason = "mr_ret3_long"
            elif ret3 > 0.02 and allow_short:
                desired = -target_pct
                reason = "mr_ret3_short"
            else:
                reason = "mr_ret3_flat"
        else:
            reason = "mr_ret3_flat"
    elif variant == 4:
        if ma20 and bb_std and bb_std[-1] > 0 and rsi14:
            zscore = (c30[-1] - ma20[-1]) / bb_std[-1]
            rsi_v = rsi14[-1]
            if zscore < -1.5 and rsi_v < 35:
                desired = target_pct
                reason = "mr_combo_long"
            elif zscore > 1.5 and rsi_v > 65 and allow_short:
                desired = -target_pct
                reason = "mr_combo_short"
            else:
                reason = "mr_combo_flat"
        else:
            reason = "mr_combo_flat"
    elif variant == 5:
        if len(h30) >= 20 and len(l30) >= 20:
            h_max = max(h30[-20:])
            l_min = min(l30[-20:])
            rng = h_max - l_min
            if rng > 0:
                pos = (c30[-1] - l_min) / rng
                if pos < 0.2:
                    desired = target_pct
                    reason = "mr_range_long"
                elif pos > 0.8 and allow_short:
                    desired = -target_pct
                    reason = "mr_range_short"
                else:
                    reason = "mr_range_flat"
            else:
                reason = "mr_range_flat"
        else:
            reason = "mr_range_flat"
    elif variant == 6:
        if len(c30) >= 2 and ma20:
            gap = c30[-1] - c30[-2]
            diff_ma = c30[-1] - ma20[-1]
            if gap < 0 and diff_ma < 0:
                desired = target_pct
                reason = "mr_gap_long"
            elif gap > 0 and diff_ma > 0 and allow_short:
                desired = -target_pct
                reason = "mr_gap_short"
            else:
                reason = "mr_gap_flat"
        else:
            reason = "mr_gap_flat"
    elif variant == 7:
        if rsi14 and len(rsi14) >= 5:
            rsi_ma5 = sum(rsi14[-5:]) / 5.0
            if rsi14[-1] < 30 and rsi_ma5 < 40:
                desired = target_pct
                reason = "mr_rsi_smooth_long"
            elif rsi14[-1] > 70 and rsi_ma5 > 60 and allow_short:
                desired = -target_pct
                reason = "mr_rsi_smooth_short"
            else:
                reason = "mr_rsi_smooth_flat"
        else:
            reason = "mr_rsi_smooth_flat"
    elif variant == 8:
        if len(c30) >= 10 and ma20 and bb_std and bb_std[-1] > 0:
            zscore = (c30[-1] - ma20[-1]) / bb_std[-1]
            ret5 = (c30[-1] / c30[-5]) - 1.0
            if zscore < -1.0 and ret5 < -0.01:
                desired = target_pct
                reason = "mr_zscore_mom_long"
            elif zscore > 1.0 and ret5 > 0.01 and allow_short:
                desired = -target_pct
                reason = "mr_zscore_mom_short"
            else:
                reason = "mr_zscore_mom_flat"
        else:
            reason = "mr_zscore_mom_flat"
    else:
        ma10 = _rolling_mean(c30, 10)
        if ma10 and ma20:
            if c30[-1] < ma10[-1] and c30[-1] < ma20[-1]:
                desired = target_pct
                reason = "mr_double_ma_long"
            elif c30[-1] > ma10[-1] and c30[-1] > ma20[-1] and allow_short:
                desired = -target_pct
                reason = "mr_double_ma_short"
            else:
                reason = "mr_double_ma_flat"
        else:
            reason = "mr_double_ma_flat"

    if desired > 0 and not is_long:
        order_target_percent(g.futures, target_pct, reason=reason)
    elif desired < 0 and allow_short and not is_short:
        order_target_percent(g.futures, -target_pct, reason=reason)
    elif abs(desired) <= 1e-12 and (is_long or is_short):
        order_target_percent(g.futures, 0.0, reason=reason + "_exit")

$meanrevpack$, '{"params":[{"name":"variant","type":"integer","default":0,"min":0,"max":9,"step":1,"labelKey":"strategyV2.params.variant"},{"name":"target_pct","type":"percent","default":0.95,"min":0.05,"max":1,"step":0.05,"labelKey":"strategyV2.params.targetPosition"},{"name":"allow_short","type":"boolean","default":true,"labelKey":"strategyV2.params.allowShort"}]}'::jsonb, '["strategy-v2","cta","mean-reversion","pack","cn-futures","options"]'::jsonb, 'waves', 'green', 220, TRUE, '{"source":"system_seed","version":11,"apiVersion":2}'::jsonb, NOW()),
('strategy_v2_carry_pack', 'portfolio_strategy', 'Carry & Roll Yield Pack', 'Futures & options carry/roll-yield with 10 variants on 1m bars aggregated to 30m.', $carrypack$"""
Carry & Roll Yield Pack
Futures & options carry/roll-yield variants on 1m bars aggregated to 30m.
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

    def _rolling_std(arr, period):
        if len(arr) < period:
            return []
        result = []
        for i in range(period, len(arr) + 1):
            window = arr[i - period:i]
            m = sum(window) / period
            var = sum((x - m) ** 2 for x in window) / period
            result.append(var ** 0.5)
        return result

    bars = get_history(8000, "1m", ["open", "high", "low", "close", "volume"], g.futures)
    o30, h30, l30, c30, v30 = _agg30(bars)
    if o30 is None or len(c30) < 100:
        return

    ma20 = _rolling_mean(c30, 20)
    ma50 = _rolling_mean(c30, 50)

    position = get_position(g.futures)
    position_amt = float(position.amount or 0.0)
    is_long = position_amt > 1e-12
    is_short = position_amt < -1e-12

    desired = 0.0
    reason = ""

    basis = (c30[-1] - o30[-1]) / o30[-1] if o30[-1] != 0 else 0.0
    basis_ma = 0.0
    if len(c30) >= 20 and len(o30) >= 20:
        basis_arr = [(c30[i] - o30[i]) / o30[i] if o30[i] != 0 else 0.0 for i in range(len(c30))]
        basis_ma_arr = _rolling_mean(basis_arr, 20)
        if basis_ma_arr:
            basis_ma = basis_ma_arr[-1]

    if variant == 0:
        desired = target_pct if basis > 0 else (-target_pct if allow_short else 0.0)
        reason = "carry_basis_sign"
    elif variant == 1:
        desired = target_pct if basis > basis_ma else (-target_pct if allow_short else 0.0)
        reason = "carry_basis_vs_ma"
    elif variant == 2:
        if ma20 and ma50:
            trend_up = ma20[-1] > ma50[-1]
            if basis > 0 and trend_up:
                desired = target_pct
                reason = "carry_trend_long"
            elif basis < 0 and not trend_up and allow_short:
                desired = -target_pct
                reason = "carry_trend_short"
            else:
                reason = "carry_trend_flat"
        else:
            reason = "carry_trend_flat"
    elif variant == 3:
        if len(c30) >= 5:
            ret5 = (c30[-1] / c30[-5]) - 1.0
            if basis > 0 and ret5 > 0:
                desired = target_pct
                reason = "carry_mom_long"
            elif basis < 0 and ret5 < 0 and allow_short:
                desired = -target_pct
                reason = "carry_mom_short"
            else:
                reason = "carry_mom_flat"
        else:
            reason = "carry_mom_flat"
    elif variant == 4:
        vol_std = _rolling_std(c30, 20)
        if vol_std and vol_std[-1] > 0:
            carry_sharpe = basis / vol_std[-1]
            if carry_sharpe > 0.5:
                desired = target_pct
                reason = "carry_sharpe_long"
            elif carry_sharpe < -0.5 and allow_short:
                desired = -target_pct
                reason = "carry_sharpe_short"
            else:
                reason = "carry_sharpe_flat"
        else:
            reason = "carry_sharpe_flat"
    elif variant == 5:
        if len(c30) >= 60:
            basis_60 = [(c30[i] - o30[i]) / o30[i] if o30[i] != 0 else 0.0 for i in range(len(c30))]
            recent = basis_60[-20:]
            older = basis_60[-60:-40]
            recent_avg = sum(recent) / len(recent) if recent else 0
            older_avg = sum(older) / len(older) if older else 0
            if recent_avg > older_avg:
                desired = target_pct
                reason = "carry_improving"
            elif recent_avg < older_avg and allow_short:
                desired = -target_pct
                reason = "carry_deteriorating"
            else:
                reason = "carry_stable"
        else:
            reason = "carry_stable"
    elif variant == 6:
        avg_vol = _rolling_mean(v30, 20)
        if avg_vol and avg_vol[-1] > 0:
            vol_ratio = v30[-1] / avg_vol[-1]
            if basis > 0 and vol_ratio > 1.2:
                desired = target_pct
                reason = "carry_vol_confirm_long"
            elif basis < 0 and vol_ratio > 1.2 and allow_short:
                desired = -target_pct
                reason = "carry_vol_confirm_short"
            else:
                reason = "carry_vol_flat"
        else:
            reason = "carry_vol_flat"
    elif variant == 7:
        if len(c30) >= 10:
            basis_arr = [(c30[i] - o30[i]) / o30[i] if o30[i] != 0 else 0.0 for i in range(len(c30))]
            basis_std = _rolling_std(basis_arr, 10)
            if basis_std and basis_std[-1] > 0:
                z = (basis - sum(basis_arr[-10:]) / 10) / basis_std[-1]
                if z > 1.0:
                    desired = target_pct
                    reason = "carry_zscore_long"
                elif z < -1.0 and allow_short:
                    desired = -target_pct
                    reason = "carry_zscore_short"
                else:
                    reason = "carry_zscore_flat"
            else:
                reason = "carry_zscore_flat"
        else:
            reason = "carry_zscore_flat"
    elif variant == 8:
        if ma20:
            ma_slope = ma20[-1] - ma20[-2] if len(ma20) >= 2 else 0
            if basis > 0 and ma_slope > 0:
                desired = target_pct
                reason = "carry_slope_long"
            elif basis < 0 and ma_slope < 0 and allow_short:
                desired = -target_pct
                reason = "carry_slope_short"
            else:
                reason = "carry_slope_flat"
        else:
            reason = "carry_slope_flat"
    else:
        if len(c30) >= 20:
            rets = [c30[i] / c30[i - 1] - 1.0 for i in range(max(1, len(c30) - 20), len(c30))]
            pos_days = sum(1 for r in rets if r > 0)
            win_rate = pos_days / len(rets) if rets else 0.5
            if basis > 0 and win_rate > 0.55:
                desired = target_pct
                reason = "carry_winrate_long"
            elif basis < 0 and win_rate < 0.45 and allow_short:
                desired = -target_pct
                reason = "carry_winrate_short"
            else:
                reason = "carry_winrate_flat"
        else:
            reason = "carry_winrate_flat"

    if desired > 0 and not is_long:
        order_target_percent(g.futures, target_pct, reason=reason)
    elif desired < 0 and allow_short and not is_short:
        order_target_percent(g.futures, -target_pct, reason=reason)
    elif abs(desired) <= 1e-12 and (is_long or is_short):
        order_target_percent(g.futures, 0.0, reason=reason + "_exit")

$carrypack$, '{"params":[{"name":"variant","type":"integer","default":0,"min":0,"max":9,"step":1,"labelKey":"strategyV2.params.variant"},{"name":"target_pct","type":"percent","default":0.95,"min":0.05,"max":1,"step":0.05,"labelKey":"strategyV2.params.targetPosition"},{"name":"allow_short","type":"boolean","default":true,"labelKey":"strategyV2.params.allowShort"}]}'::jsonb, '["strategy-v2","cta","carry","roll-yield","pack","cn-futures","options"]'::jsonb, 'coins', 'yellow', 230, TRUE, '{"source":"system_seed","version":11,"apiVersion":2}'::jsonb, NOW()),
('strategy_v2_relative_value_pack', 'portfolio_strategy', 'Relative Value Pack', 'Futures & options relative-value with 10 variants on 1m bars aggregated to 30m.', $relvalpack$"""
Relative Value Pack
Futures & options relative-value variants on 1m bars aggregated to 30m.
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

    def _rolling_std(arr, period):
        if len(arr) < period:
            return []
        result = []
        for i in range(period, len(arr) + 1):
            window = arr[i - period:i]
            m = sum(window) / period
            var = sum((x - m) ** 2 for x in window) / period
            result.append(var ** 0.5)
        return result

    bars = get_history(8000, "1m", ["open", "high", "low", "close", "volume"], g.futures)
    o30, h30, l30, c30, v30 = _agg30(bars)
    if o30 is None or len(c30) < 100:
        return

    ma20 = _rolling_mean(c30, 20)
    ma50 = _rolling_mean(c30, 50)
    std20 = _rolling_std(c30, 20)

    hl_ratio = [(h30[i] - l30[i]) / c30[i] if c30[i] != 0 else 0 for i in range(len(c30))]
    hl_ma = _rolling_mean(hl_ratio, 20)

    position = get_position(g.futures)
    position_amt = float(position.amount or 0.0)
    is_long = position_amt > 1e-12
    is_short = position_amt < -1e-12

    desired = 0.0
    reason = ""

    if variant == 0:
        if ma20 and ma50:
            spread = ma20[-1] - ma50[-1]
            desired = target_pct if spread > 0 else (-target_pct if allow_short else 0.0)
        reason = "rv_ma_spread"
    elif variant == 1:
        if ma20 and std20 and std20[-1] > 0:
            zscore = (c30[-1] - ma20[-1]) / std20[-1]
            if zscore < -1.5:
                desired = target_pct
                reason = "rv_zscore_long"
            elif zscore > 1.5 and allow_short:
                desired = -target_pct
                reason = "rv_zscore_short"
            else:
                reason = "rv_zscore_flat"
        else:
            reason = "rv_zscore_flat"
    elif variant == 2:
        if hl_ma and len(hl_ma) >= 2:
            if hl_ratio[-1] < hl_ma[-1] and c30[-1] > c30[-2]:
                desired = target_pct
                reason = "rv_vol_compress_long"
            elif hl_ratio[-1] < hl_ma[-1] and c30[-1] < c30[-2] and allow_short:
                desired = -target_pct
                reason = "rv_vol_compress_short"
            else:
                reason = "rv_vol_compress_flat"
        else:
            reason = "rv_vol_compress_flat"
    elif variant == 3:
        if len(c30) >= 60:
            ret20 = (c30[-1] / c30[-20]) - 1.0
            ret60 = (c30[-1] / c30[-60]) - 1.0
            if ret20 > ret60:
                desired = target_pct
                reason = "rv_momentum_accel"
            elif ret20 < ret60 and allow_short:
                desired = -target_pct
                reason = "rv_momentum_decel"
            else:
                reason = "rv_momentum_flat"
        else:
            reason = "rv_momentum_flat"
    elif variant == 4:
        avg_vol = _rolling_mean(v30, 20)
        if avg_vol and len(avg_vol) >= 2:
            vol_trend = avg_vol[-1] - avg_vol[-2]
            price_trend = c30[-1] - c30[-2]
            if vol_trend > 0 and price_trend > 0:
                desired = target_pct
                reason = "rv_vol_price_long"
            elif vol_trend > 0 and price_trend < 0 and allow_short:
                desired = -target_pct
                reason = "rv_vol_price_short"
            else:
                reason = "rv_vol_price_flat"
        else:
            reason = "rv_vol_price_flat"
    elif variant == 5:
        if len(c30) >= 40:
            ret10 = [(c30[i] / c30[i - 10]) - 1.0 for i in range(10, len(c30))]
            ret_std = _rolling_std(ret10, 20)
            if ret_std and ret_std[-1] > 0:
                norm_ret = ret10[-1] / ret_std[-1]
                if norm_ret > 1.0:
                    desired = target_pct
                    reason = "rv_norm_ret_long"
                elif norm_ret < -1.0 and allow_short:
                    desired = -target_pct
                    reason = "rv_norm_ret_short"
                else:
                    reason = "rv_norm_ret_flat"
            else:
                reason = "rv_norm_ret_flat"
        else:
            reason = "rv_norm_ret_flat"
    elif variant == 6:
        if len(c30) >= 20:
            rets = [c30[i] / c30[i - 1] - 1.0 for i in range(max(1, len(c30) - 20), len(c30))]
            up = [r for r in rets if r > 0]
            down = [r for r in rets if r < 0]
            avg_up = sum(up) / len(up) if up else 0
            avg_down = abs(sum(down) / len(down)) if down else 0
            ratio = avg_up / avg_down if avg_down > 0 else 2.0
            if ratio > 1.2:
                desired = target_pct
                reason = "rv_updown_long"
            elif ratio < 0.8 and allow_short:
                desired = -target_pct
                reason = "rv_updown_short"
            else:
                reason = "rv_updown_flat"
        else:
            reason = "rv_updown_flat"
    elif variant == 7:
        if ma20 and len(ma20) >= 10:
            ma_rets = [(ma20[i] / ma20[i - 1]) - 1.0 for i in range(max(1, len(ma20) - 10), len(ma20))]
            ma_accel = ma_rets[-1] - ma_rets[0] if len(ma_rets) >= 2 else 0
            if ma_accel > 0:
                desired = target_pct
                reason = "rv_ma_accel_long"
            elif ma_accel < 0 and allow_short:
                desired = -target_pct
                reason = "rv_ma_accel_short"
            else:
                reason = "rv_ma_accel_flat"
        else:
            reason = "rv_ma_accel_flat"
    elif variant == 8:
        if len(c30) >= 5 and std20:
            recent_move = abs(c30[-1] - c30[-5])
            expected = std20[-1] * (5 ** 0.5) if std20[-1] > 0 else 1
            if recent_move < expected * 0.5:
                if c30[-1] > c30[-5]:
                    desired = target_pct
                    reason = "rv_quiet_up"
                elif allow_short:
                    desired = -target_pct
                    reason = "rv_quiet_down"
                else:
                    reason = "rv_quiet_flat"
            else:
                reason = "rv_quiet_flat"
        else:
            reason = "rv_quiet_flat"
    else:
        if len(c30) >= 40:
            half = len(c30) // 2
            first_half_std = _rolling_std(c30[:half], min(20, half))
            second_half_std = _rolling_std(c30[half:], min(20, len(c30) - half))
            if first_half_std and second_half_std:
                if second_half_std[-1] < first_half_std[-1]:
                    desired = target_pct if c30[-1] > c30[-2] else (-target_pct if allow_short else 0.0)
                    reason = "rv_vol_regime"
                else:
                    reason = "rv_vol_regime_flat"
            else:
                reason = "rv_vol_regime_flat"
        else:
            reason = "rv_vol_regime_flat"

    if desired > 0 and not is_long:
        order_target_percent(g.futures, target_pct, reason=reason)
    elif desired < 0 and allow_short and not is_short:
        order_target_percent(g.futures, -target_pct, reason=reason)
    elif abs(desired) <= 1e-12 and (is_long or is_short):
        order_target_percent(g.futures, 0.0, reason=reason + "_exit")

$relvalpack$, '{"params":[{"name":"variant","type":"integer","default":0,"min":0,"max":9,"step":1,"labelKey":"strategyV2.params.variant"},{"name":"target_pct","type":"percent","default":0.95,"min":0.05,"max":1,"step":0.05,"labelKey":"strategyV2.params.targetPosition"},{"name":"allow_short","type":"boolean","default":true,"labelKey":"strategyV2.params.allowShort"}]}'::jsonb, '["strategy-v2","cta","relative-value","pack","cn-futures","options"]'::jsonb, 'scale', 'teal', 240, TRUE, '{"source":"system_seed","version":11,"apiVersion":2}'::jsonb, NOW()),
('strategy_v2_volatility_pack', 'portfolio_strategy', 'Volatility Pack', 'Futures & options volatility with 10 variants on 1m bars aggregated to 30m.', $volpack$"""
Volatility Pack
Futures & options volatility variants on 1m bars aggregated to 30m.
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

    def _rolling_std(arr, period):
        if len(arr) < period:
            return []
        result = []
        for i in range(period, len(arr) + 1):
            window = arr[i - period:i]
            m = sum(window) / period
            var = sum((x - m) ** 2 for x in window) / period
            result.append(var ** 0.5)
        return result

    bars = get_history(8000, "1m", ["open", "high", "low", "close", "volume"], g.futures)
    o30, h30, l30, c30, v30 = _agg30(bars)
    if o30 is None or len(c30) < 100:
        return

    rets = [c30[i] / c30[i - 1] - 1.0 for i in range(1, len(c30))]
    vol20 = _rolling_std(rets, 20)
    vol60 = _rolling_std(rets, 60)
    ma20 = _rolling_mean(c30, 20)
    atr = [(h30[i] - l30[i]) / c30[i] if c30[i] != 0 else 0 for i in range(len(c30))]
    atr20 = _rolling_mean(atr, 20)

    position = get_position(g.futures)
    position_amt = float(position.amount or 0.0)
    is_long = position_amt > 1e-12
    is_short = position_amt < -1e-12

    desired = 0.0
    reason = ""

    if variant == 0:
        if vol20 and vol60:
            if vol20[-1] < vol60[-1]:
                desired = target_pct if c30[-1] > c30[-2] else (-target_pct if allow_short else 0.0)
                reason = "vol_low_regime"
            else:
                reason = "vol_high_regime"
        else:
            reason = "vol_regime_na"
    elif variant == 1:
        if vol20 and len(vol20) >= 2:
            if vol20[-1] > vol20[-2] * 1.5:
                desired = -target_pct if allow_short else 0.0
                reason = "vol_spike_short"
            elif vol20[-1] < vol20[-2] * 0.7:
                desired = target_pct
                reason = "vol_crush_long"
            else:
                reason = "vol_spike_flat"
        else:
            reason = "vol_spike_flat"
    elif variant == 2:
        if atr20 and len(atr20) >= 2:
            atr_trend = atr20[-1] - atr20[-2]
            if atr_trend < 0 and c30[-1] > c30[-2]:
                desired = target_pct
                reason = "vol_atr_compress_long"
            elif atr_trend > 0 and c30[-1] < c30[-2] and allow_short:
                desired = -target_pct
                reason = "vol_atr_expand_short"
            else:
                reason = "vol_atr_flat"
        else:
            reason = "vol_atr_flat"
    elif variant == 3:
        if vol20:
            vol_ma = _rolling_mean([v for v in vol20], min(20, len(vol20)))
            if vol_ma:
                if vol20[-1] < vol_ma[-1] * 0.8:
                    desired = target_pct if c30[-1] > c30[-2] else (-target_pct if allow_short else 0.0)
                    reason = "vol_mean_rev"
                else:
                    reason = "vol_mean_rev_flat"
            else:
                reason = "vol_mean_rev_flat"
        else:
            reason = "vol_mean_rev_flat"
    elif variant == 4:
        if len(rets) >= 20:
            skew_vals = rets[-20:]
            m = sum(skew_vals) / 20
            std = (sum((x - m) ** 2 for x in skew_vals) / 20) ** 0.5
            if std > 0:
                skew = sum((x - m) ** 3 for x in skew_vals) / (20 * std ** 3)
                if skew > 0.5:
                    desired = target_pct
                    reason = "vol_pos_skew"
                elif skew < -0.5 and allow_short:
                    desired = -target_pct
                    reason = "vol_neg_skew"
                else:
                    reason = "vol_skew_flat"
            else:
                reason = "vol_skew_flat"
        else:
            reason = "vol_skew_flat"
    elif variant == 5:
        if len(h30) >= 20 and len(l30) >= 20:
            ranges = [(h30[i] - l30[i]) for i in range(len(h30))]
            range_ma = _rolling_mean(ranges, 20)
            if range_ma and len(range_ma) >= 2:
                if range_ma[-1] < range_ma[-2]:
                    desired = target_pct if c30[-1] > c30[-2] else (-target_pct if allow_short else 0.0)
                    reason = "vol_range_contract"
                else:
                    reason = "vol_range_expand"
            else:
                reason = "vol_range_na"
        else:
            reason = "vol_range_na"
    elif variant == 6:
        if vol20 and ma20:
            vol_price = vol20[-1] * c30[-1] if vol20 else 0
            if vol_price > 0:
                desired = target_pct if c30[-1] > ma20[-1] else (-target_pct if allow_short else 0.0)
                reason = "vol_dollar_vol"
            else:
                reason = "vol_dollar_flat"
        else:
            reason = "vol_dollar_flat"
    elif variant == 7:
        if len(rets) >= 20:
            pos_rets = [r for r in rets[-20:] if r > 0]
            neg_rets = [r for r in rets[-20:] if r < 0]
            up_vol = (sum(r ** 2 for r in pos_rets) / len(pos_rets)) ** 0.5 if pos_rets else 0
            down_vol = (sum(r ** 2 for r in neg_rets) / len(neg_rets)) ** 0.5 if neg_rets else 0
            if down_vol > 0:
                vol_ratio = up_vol / down_vol
                if vol_ratio > 1.2:
                    desired = target_pct
                    reason = "vol_updown_long"
                elif vol_ratio < 0.8 and allow_short:
                    desired = -target_pct
                    reason = "vol_updown_short"
                else:
                    reason = "vol_updown_flat"
            else:
                reason = "vol_updown_flat"
        else:
            reason = "vol_updown_flat"
    elif variant == 8:
        if vol20 and vol60:
            vol_spread = vol20[-1] - vol60[-1]
            if vol_spread < 0:
                desired = target_pct if c30[-1] > c30[-2] else (-target_pct if allow_short else 0.0)
                reason = "vol_term_struct"
            else:
                reason = "vol_term_flat"
        else:
            reason = "vol_term_flat"
    else:
        if atr20 and vol20:
            if atr20[-1] > 0 and vol20[-1] > 0:
                consistency = vol20[-1] / atr20[-1]
                if consistency < 1.0:
                    desired = target_pct if c30[-1] > c30[-2] else (-target_pct if allow_short else 0.0)
                    reason = "vol_consistency"
                else:
                    reason = "vol_consistency_flat"
            else:
                reason = "vol_consistency_flat"
        else:
            reason = "vol_consistency_flat"

    if desired > 0 and not is_long:
        order_target_percent(g.futures, target_pct, reason=reason)
    elif desired < 0 and allow_short and not is_short:
        order_target_percent(g.futures, -target_pct, reason=reason)
    elif abs(desired) <= 1e-12 and (is_long or is_short):
        order_target_percent(g.futures, 0.0, reason=reason + "_exit")

$volpack$, '{"params":[{"name":"variant","type":"integer","default":0,"min":0,"max":9,"step":1,"labelKey":"strategyV2.params.variant"},{"name":"target_pct","type":"percent","default":0.95,"min":0.05,"max":1,"step":0.05,"labelKey":"strategyV2.params.targetPosition"},{"name":"allow_short","type":"boolean","default":true,"labelKey":"strategyV2.params.allowShort"}]}'::jsonb, '["strategy-v2","cta","volatility","pack","cn-futures","options"]'::jsonb, 'activity', 'red', 250, TRUE, '{"source":"system_seed","version":11,"apiVersion":2}'::jsonb, NOW()),
('strategy_v2_market_microstructure_pack', 'portfolio_strategy', 'Market Microstructure Pack', 'Futures & options microstructure with 10 variants on 1m bars aggregated to 30m.', $micropp$"""
Market Microstructure Pack
Futures & options microstructure variants on 1m bars aggregated to 30m.
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

    def _rolling_std(arr, period):
        if len(arr) < period:
            return []
        result = []
        for i in range(period, len(arr) + 1):
            window = arr[i - period:i]
            m = sum(window) / period
            var = sum((x - m) ** 2 for x in window) / period
            result.append(var ** 0.5)
        return result

    bars = get_history(8000, "1m", ["open", "high", "low", "close", "volume"], g.futures)
    o30, h30, l30, c30, v30 = _agg30(bars)
    if o30 is None or len(c30) < 100:
        return

    ma20 = _rolling_mean(c30, 20)
    avg_vol = _rolling_mean(v30, 20)
    spread = [(h30[i] - l30[i]) / c30[i] if c30[i] != 0 else 0 for i in range(len(c30))]
    spread_ma = _rolling_mean(spread, 20)

    position = get_position(g.futures)
    position_amt = float(position.amount or 0.0)
    is_long = position_amt > 1e-12
    is_short = position_amt < -1e-12

    desired = 0.0
    reason = ""

    if variant == 0:
        if avg_vol and avg_vol[-1] > 0:
            vol_ratio = v30[-1] / avg_vol[-1]
            if vol_ratio > 1.5 and c30[-1] > c30[-2]:
                desired = target_pct
                reason = "micro_vol_surge_long"
            elif vol_ratio > 1.5 and c30[-1] < c30[-2] and allow_short:
                desired = -target_pct
                reason = "micro_vol_surge_short"
            else:
                reason = "micro_vol_flat"
        else:
            reason = "micro_vol_flat"
    elif variant == 1:
        if spread_ma and spread_ma[-1] > 0:
            spread_ratio = spread[-1] / spread_ma[-1]
            if spread_ratio < 0.5:
                desired = target_pct if c30[-1] > c30[-2] else (-target_pct if allow_short else 0.0)
                reason = "micro_spread_tight"
            else:
                reason = "micro_spread_wide"
        else:
            reason = "micro_spread_na"
    elif variant == 2:
        if len(v30) >= 5:
            recent_vol = sum(v30[-5:])
            prev_vol = sum(v30[-10:-5]) if len(v30) >= 10 else recent_vol
            if prev_vol > 0:
                accel = recent_vol / prev_vol
                if accel > 1.3 and c30[-1] > c30[-2]:
                    desired = target_pct
                    reason = "micro_vol_accel_long"
                elif accel > 1.3 and c30[-1] < c30[-2] and allow_short:
                    desired = -target_pct
                    reason = "micro_vol_accel_short"
                else:
                    reason = "micro_vol_accel_flat"
            else:
                reason = "micro_vol_accel_flat"
        else:
            reason = "micro_vol_accel_flat"
    elif variant == 3:
        body = [abs(c30[i] - o30[i]) for i in range(len(c30))]
        wick = [(h30[i] - l30[i]) - body[i] for i in range(len(c30))]
        if body[-1] > 0:
            wick_ratio = wick[-1] / body[-1]
            if wick_ratio > 2.0 and c30[-1] > o30[-1]:
                desired = target_pct
                reason = "micro_wick_long"
            elif wick_ratio > 2.0 and c30[-1] < o30[-1] and allow_short:
                desired = -target_pct
                reason = "micro_wick_short"
            else:
                reason = "micro_wick_flat"
        else:
            reason = "micro_wick_flat"
    elif variant == 4:
        if len(c30) >= 20:
            up_vol = sum(v30[i] for i in range(len(c30) - 20, len(c30)) if c30[i] > c30[i - 1])
            down_vol = sum(v30[i] for i in range(len(c30) - 20, len(c30)) if c30[i] < c30[i - 1])
            total = up_vol + down_vol
            if total > 0:
                ratio = up_vol / total
                if ratio > 0.6:
                    desired = target_pct
                    reason = "micro_obv_long"
                elif ratio < 0.4 and allow_short:
                    desired = -target_pct
                    reason = "micro_obv_short"
                else:
                    reason = "micro_obv_flat"
            else:
                reason = "micro_obv_flat"
        else:
            reason = "micro_obv_flat"
    elif variant == 5:
        if len(c30) >= 10:
            price_move = abs(c30[-1] - c30[-10])
            vol_sum = sum(v30[-10:])
            if vol_sum > 0:
                efficiency = price_move / vol_sum
                eff_ma = []
                for j in range(10, min(30, len(c30))):
                    pm = abs(c30[-j + 9] - c30[-j])
                    vs = sum(v30[-j:-j + 10])
                    if vs > 0:
                        eff_ma.append(pm / vs)
                avg_eff = sum(eff_ma) / len(eff_ma) if eff_ma else efficiency
                if efficiency > avg_eff * 1.2:
                    desired = target_pct if c30[-1] > c30[-10] else (-target_pct if allow_short else 0.0)
                    reason = "micro_efficiency"
                else:
                    reason = "micro_efficiency_flat"
            else:
                reason = "micro_efficiency_flat"
        else:
            reason = "micro_efficiency_flat"
    elif variant == 6:
        if len(c30) >= 20:
            closes_above_open = sum(1 for i in range(len(c30) - 20, len(c30)) if c30[i] > o30[i])
            ratio = closes_above_open / 20.0
            if ratio > 0.65:
                desired = target_pct
                reason = "micro_bullish_bars"
            elif ratio < 0.35 and allow_short:
                desired = -target_pct
                reason = "micro_bearish_bars"
            else:
                reason = "micro_bars_flat"
        else:
            reason = "micro_bars_flat"
    elif variant == 7:
        if avg_vol and len(avg_vol) >= 5:
            vol_trend = avg_vol[-1] - avg_vol[-5]
            if vol_trend > 0 and c30[-1] > ma20[-1] if ma20 else False:
                desired = target_pct
                reason = "micro_vol_trend_long"
            elif vol_trend < 0 and c30[-1] < (ma20[-1] if ma20 else c30[-1]) and allow_short:
                desired = -target_pct
                reason = "micro_vol_trend_short"
            else:
                reason = "micro_vol_trend_flat"
        else:
            reason = "micro_vol_trend_flat"
    elif variant == 8:
        if len(c30) >= 3:
            gaps = [abs(o30[i] - c30[i - 1]) / c30[i - 1] if c30[i - 1] != 0 else 0 for i in range(1, len(c30))]
            gap_ma = _rolling_mean(gaps, 20)
            if gap_ma and gaps[-1] < gap_ma[-1] * 0.5:
                desired = target_pct if c30[-1] > c30[-2] else (-target_pct if allow_short else 0.0)
                reason = "micro_gap_small"
            else:
                reason = "micro_gap_flat"
        else:
            reason = "micro_gap_flat"
    else:
        if len(c30) >= 20:
            rets = [c30[i] / c30[i - 1] - 1.0 for i in range(max(1, len(c30) - 20), len(c30))]
            auto_corr = 0.0
            if len(rets) >= 2:
                m = sum(rets) / len(rets)
                var = sum((r - m) ** 2 for r in rets) / len(rets)
                if var > 0:
                    cov = sum((rets[i] - m) * (rets[i - 1] - m) for i in range(1, len(rets))) / (len(rets) - 1)
                    auto_corr = cov / var
            if auto_corr < -0.3:
                desired = target_pct if rets[-1] < 0 else (-target_pct if allow_short else 0.0)
                reason = "micro_autocorr_mr"
            elif auto_corr > 0.3:
                desired = target_pct if rets[-1] > 0 else (-target_pct if allow_short else 0.0)
                reason = "micro_autocorr_trend"
            else:
                reason = "micro_autocorr_flat"
        else:
            reason = "micro_autocorr_flat"

    if desired > 0 and not is_long:
        order_target_percent(g.futures, target_pct, reason=reason)
    elif desired < 0 and allow_short and not is_short:
        order_target_percent(g.futures, -target_pct, reason=reason)
    elif abs(desired) <= 1e-12 and (is_long or is_short):
        order_target_percent(g.futures, 0.0, reason=reason + "_exit")

$micropp$, '{"params":[{"name":"variant","type":"integer","default":0,"min":0,"max":9,"step":1,"labelKey":"strategyV2.params.variant"},{"name":"target_pct","type":"percent","default":0.95,"min":0.05,"max":1,"step":0.05,"labelKey":"strategyV2.params.targetPosition"},{"name":"allow_short","type":"boolean","default":true,"labelKey":"strategyV2.params.allowShort"}]}'::jsonb, '["strategy-v2","cta","microstructure","pack","cn-futures","options"]'::jsonb, 'candlestick', 'purple', 260, TRUE, '{"source":"system_seed","version":11,"apiVersion":2}'::jsonb, NOW())
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
