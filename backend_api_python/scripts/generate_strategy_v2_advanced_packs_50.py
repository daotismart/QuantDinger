#!/usr/bin/env python3
"""Generate 5 CN futures/options pack templates (10 variants each = 50 strategies)."""

from __future__ import annotations

from pathlib import Path

OUTPUT = Path(__file__).resolve().parents[1] / "migrations" / "strategy_v2_advanced_packs_50.sql"

PARAM_SCHEMA = (
    '{"params":[{"name":"variant","type":"integer","default":0,"min":0,"max":9,"step":1,'
    '"labelKey":"strategyV2.params.variant"},{"name":"target_pct","type":"percent","default":0.95,'
    '"min":0.05,"max":1,"step":0.05,"labelKey":"strategyV2.params.targetPosition"},'
    '{"name":"allow_short","type":"boolean","default":true,"labelKey":"strategyV2.params.allowShort"}]}'
)

PACK_META = [
    (
        "strategy_v2_stat_arb_pack",
        "statpack",
        "Statistical Arbitrage Pack",
        "Z-score, spread, and ratio mean-reversion on SA701 futures vs options.",
        "stat-arb",
        "geekblue",
        270,
    ),
    (
        "strategy_v2_options_vol_pack",
        "optvolpack",
        "Options Volatility Pack",
        "Volatility regime and option-lead signals on SA701 futures/options.",
        "options-vol",
        "volcano",
        280,
    ),
    (
        "strategy_v2_session_alpha_pack",
        "sesspack",
        "Session Alpha Pack",
        "Day/night session momentum and open-drive patterns on 30m bars.",
        "session-alpha",
        "gold",
        290,
    ),
    (
        "strategy_v2_regime_switch_pack",
        "regpack",
        "Regime Switch Pack",
        "Trend/volatility regime switching with adaptive exposure.",
        "regime-switch",
        "cyan",
        300,
    ),
    (
        "strategy_v2_orderflow_proxy_pack",
        "flowpack",
        "Order Flow Proxy Pack",
        "Volume delta, OBV, and microstructure flow proxies.",
        "orderflow",
        "green",
        310,
    ),
]

VARIANT_SNIPPETS: dict[str, list[tuple[str, str]]] = {
    "strategy_v2_stat_arb_pack": [
        ("stat_zscore_mr", "        std20 = _rolling_std(c30, 20)\n        if std20:\n            z = (c30[-1] - _rolling_mean(c30, 20)[-1]) / std20[-1] if std20[-1] else 0\n            if z < -1.5:\n                desired = target_pct\n            elif z > 1.5 and allow_short:\n                desired = -target_pct\n"),
        ("stat_zscore_momo", "        std20 = _rolling_std(c30, 20)\n        if std20:\n            z = (c30[-1] - _rolling_mean(c30, 20)[-1]) / std20[-1] if std20[-1] else 0\n            if z > 1.0:\n                desired = target_pct\n            elif z < -1.0 and allow_short:\n                desired = -target_pct\n"),
        ("stat_spread_z", "        opt = get_history(8000, '1m', 'close', g.option)\n        if len(opt) >= 30 and len(c30) >= 20:\n            spread = [c30[i] - float(opt['close'].values[-len(c30) + i]) for i in range(len(c30))]\n            mz = _rolling_mean(spread, 20)\n            sz = _rolling_std(spread, 20)\n            if mz and sz and sz[-1]:\n                z = (spread[-1] - mz[-1]) / sz[-1]\n                desired = target_pct if z < -1.2 else (-target_pct if z > 1.2 and allow_short else 0.0)\n"),
        ("stat_ratio_mr", "        opt = get_history(8000, '1m', 'close', g.option)\n        if len(opt) >= 30:\n            ratio = [c30[i] / max(1e-6, float(opt['close'].values[-len(c30) + i])) for i in range(len(c30))]\n            mr = _rolling_mean(ratio, 30)\n            if mr and ratio[-1] < mr[-1] * 0.995:\n                desired = target_pct\n            elif mr and ratio[-1] > mr[-1] * 1.005 and allow_short:\n                desired = -target_pct\n"),
        ("stat_dual_z", "        z5 = _rolling_std(c30, 5)\n        z20 = _rolling_std(c30, 20)\n        if z5 and z20:\n            fast = (c30[-1] - _rolling_mean(c30, 5)[-1]) / (z5[-1] or 1)\n            slow = (c30[-1] - _rolling_mean(c30, 20)[-1]) / (z20[-1] or 1)\n            if fast > 0 and slow > 0:\n                desired = target_pct\n            elif fast < 0 and slow < 0 and allow_short:\n                desired = -target_pct\n"),
        ("stat_percentile_mr", "        if len(c30) >= 60:\n            window = c30[-60:]\n            rank = sum(1 for x in window if x <= c30[-1]) / len(window)\n            if rank < 0.2:\n                desired = target_pct\n            elif rank > 0.8 and allow_short:\n                desired = -target_pct\n"),
        ("stat_diff_ma", "        ma5 = _rolling_mean(c30, 5)\n        ma40 = _rolling_mean(c30, 40)\n        if ma5 and ma40:\n            diff = ma5[-1] - ma40[-1]\n            pdiff = ma5[-2] - ma40[-2] if len(ma5) > 1 else diff\n            if diff < 0 and diff > pdiff:\n                desired = target_pct\n            elif diff > 0 and diff < pdiff and allow_short:\n                desired = -target_pct\n"),
        ("stat_variance_ratio", "        if len(c30) > 40:\n            r1 = c30[-1] / c30[-2] - 1\n            r5 = c30[-1] / c30[-6] - 1\n            if abs(r5) > abs(r1) * 2 and r5 > 0:\n                desired = target_pct\n            elif abs(r5) > abs(r1) * 2 and r5 < 0 and allow_short:\n                desired = -target_pct\n"),
        ("stat_autocorr_mr", "        rets = [c30[i] / c30[i - 1] - 1 for i in range(1, len(c30))]\n        if len(rets) >= 20:\n            m = sum(rets[-20:]) / 20\n            if rets[-1] < m - 0.001:\n                desired = target_pct\n            elif rets[-1] > m + 0.001 and allow_short:\n                desired = -target_pct\n"),
        ("stat_band_walk", "        ma = _rolling_mean(c30, 20)\n        sd = _rolling_std(c30, 20)\n        if ma and sd:\n            upper = ma[-1] + 2 * sd[-1]\n            lower = ma[-1] - 2 * sd[-1]\n            if c30[-1] <= lower:\n                desired = target_pct\n            elif c30[-1] >= upper and allow_short:\n                desired = -target_pct\n"),
    ],
    "strategy_v2_options_vol_pack": [
        ("opt_vol_ratio", "        opt = get_history(8000, '1m', ['close', 'volume'], g.option)\n        if len(opt) >= 30:\n            fv = float(opt['volume'].values[-1] or 0)\n            ratio = fv / max(1.0, float(v30[-1]))\n            avg = sum(float(x) for x in opt['volume'].values[-30:]) / 30\n            if ratio > 1.5 and c30[-1] > c30[-2]:\n                desired = target_pct\n            elif ratio > 1.5 and c30[-1] < c30[-2] and allow_short:\n                desired = -target_pct\n"),
        ("opt_lead", "        opt = get_history(8000, '1m', 'close', g.option)\n        if len(opt) >= 5:\n            oc = opt['close'].values\n            if float(oc[-1]) > float(oc[-2]) and c30[-1] <= c30[-2]:\n                desired = target_pct\n            elif float(oc[-1]) < float(oc[-2]) and c30[-1] >= c30[-2] and allow_short:\n                desired = -target_pct\n"),
        ("opt_straddle_proxy", "        opt = get_history(8000, '1m', 'close', g.option)\n        if len(opt) >= 20:\n            ov = [abs(float(opt['close'].values[-len(c30) + i]) - c30[i]) for i in range(max(0, len(c30)-20), len(c30))]\n            if ov and ov[-1] > sum(ov) / len(ov) * 1.2:\n                desired = target_pct if c30[-1] > c30[-2] else (-target_pct if allow_short else 0.0)\n"),
        ("opt_iv_momo", "        opt = get_history(8000, '1m', 'close', g.option)\n        if len(opt) >= 10:\n            oc = [float(x) for x in opt['close'].values[-10:]]\n            if oc[-1] > oc[0] * 1.01:\n                desired = target_pct\n            elif oc[-1] < oc[0] * 0.99 and allow_short:\n                desired = -target_pct\n"),
        ("opt_skew_proxy", "        opt = get_history(8000, '1m', 'close', g.option)\n        if len(opt) >= 2:\n            skew = float(opt['close'].values[-1]) / max(1e-6, c30[-1])\n            skew_prev = float(opt['close'].values[-2]) / max(1e-6, c30[-2])\n            if skew < skew_prev:\n                desired = target_pct\n            elif skew > skew_prev and allow_short:\n                desired = -target_pct\n"),
        ("opt_vol_break", "        rng = [h30[i] - l30[i] for i in range(len(h30))]\n        if len(rng) >= 20:\n            if rng[-1] > sum(rng[-20:]) / 20 * 1.3:\n                desired = target_pct if c30[-1] > o30[-1] else (-target_pct if allow_short else 0.0)\n"),
        ("opt_gamma_proxy", "        opt = get_history(8000, '1m', 'close', g.option)\n        if len(opt) >= 3:\n            accel = float(opt['close'].values[-1]) - 2 * float(opt['close'].values[-2]) + float(opt['close'].values[-3])\n            desired = target_pct if accel > 0 else (-target_pct if accel < 0 and allow_short else 0.0)\n"),
        ("opt_vega_flat", "        std20 = _rolling_std(c30, 20)\n        if std20 and std20[-1] < sum(std20[-20:]) / min(20, len(std20)) * 0.8:\n            desired = 0.0\n        elif std20 and c30[-1] > _rolling_mean(c30, 20)[-1]:\n            desired = target_pct\n"),
        ("opt_delta_hedge", "        opt = get_history(8000, '1m', 'close', g.option)\n        if len(opt) >= 2:\n            beta = (float(opt['close'].values[-1]) - float(opt['close'].values[-2])) / max(1e-6, c30[-1] - c30[-2])\n            if beta > 1.2:\n                desired = target_pct\n            elif beta < 0.8 and allow_short:\n                desired = -target_pct\n"),
        ("opt_vol_mean_rev", "        rng = [h30[i] - l30[i] for i in range(len(h30))]\n        mr = _rolling_mean(rng, 20)\n        if mr and rng[-1] < mr[-1] * 0.85:\n            desired = target_pct if c30[-1] > c30[-5] else 0.0\n        elif mr and rng[-1] > mr[-1] * 1.15 and allow_short:\n            desired = -target_pct\n"),
    ],
    "strategy_v2_session_alpha_pack": [
        ("sess_open_drive", "        if len(c30) >= 3:\n            drive = c30[-1] - o30[-1]\n            desired = target_pct if drive > 0 else (-target_pct if drive < 0 and allow_short else 0.0)\n"),
        ("sess_first_hour", "        if len(c30) >= 4:\n            fh = c30[-1] - c30[-4]\n            desired = target_pct if fh > 0 else (-target_pct if fh < 0 and allow_short else 0.0)\n"),
        ("sess_midday_fade", "        if len(c30) >= 6:\n            if c30[-3] > c30[-6] and c30[-1] < c30[-3]:\n                desired = -target_pct if allow_short else 0.0\n            elif c30[-3] < c30[-6] and c30[-1] > c30[-3]:\n                desired = target_pct\n"),
        ("sess_close_momo", "        if len(c30) >= 5:\n            desired = target_pct if c30[-1] > c30[-5] else (-target_pct if allow_short else 0.0)\n"),
        ("sess_gap_fade", "        if len(c30) >= 2:\n            gap = o30[-1] - c30[-2]\n            desired = -target_pct if gap > 0 and allow_short else (target_pct if gap < 0 else 0.0)\n"),
        ("sess_gap_go", "        if len(c30) >= 2:\n            gap = o30[-1] - c30[-2]\n            desired = target_pct if gap > 0 else (-target_pct if gap < 0 and allow_short else 0.0)\n"),
        ("sess_night_momo", "        if len(c30) >= 8:\n            desired = target_pct if c30[-1] > c30[-8] else (-target_pct if allow_short else 0.0)\n"),
        ("sess_day_night_spread", "        if len(c30) >= 16:\n            day_ret = c30[-8] / c30[-16] - 1\n            night_ret = c30[-1] / c30[-8] - 1\n            desired = target_pct if night_ret > day_ret else (-target_pct if allow_short else 0.0)\n"),
        ("sess_vwap_bias", "        if len(c30) >= 20:\n            num = sum(c30[i] * v30[i] for i in range(-20, 0))\n            den = sum(v30[-20:])\n            vwap = num / den if den else c30[-1]\n            desired = target_pct if c30[-1] > vwap else (-target_pct if allow_short else 0.0)\n"),
        ("sess_range_break", "        if len(h30) >= 10:\n            hi = max(h30[-10:-1])\n            lo = min(l30[-10:-1])\n            if c30[-1] > hi:\n                desired = target_pct\n            elif c30[-1] < lo and allow_short:\n                desired = -target_pct\n"),
    ],
    "strategy_v2_regime_switch_pack": [
        ("reg_trend_vol", "        ma50 = _rolling_mean(c30, 50)\n        sd20 = _rolling_std(c30, 20)\n        if ma50 and sd20:\n            if sd20[-1] > sum(sd20[-10:]) / min(10, len(sd20)) and c30[-1] > ma50[-1]:\n                desired = target_pct\n            elif sd20[-1] > sum(sd20[-10:]) / min(10, len(sd20)) and c30[-1] < ma50[-1] and allow_short:\n                desired = -target_pct\n"),
        ("reg_low_vol_mr", "        sd = _rolling_std(c30, 20)\n        if sd and sd[-1] < sum(sd[-20:]) / min(20, len(sd)) * 0.85:\n            desired = target_pct if c30[-1] < _rolling_mean(c30, 20)[-1] else (-target_pct if allow_short else 0.0)\n"),
        ("reg_high_vol_break", "        sd = _rolling_std(c30, 20)\n        if sd and sd[-1] > sum(sd[-20:]) / min(20, len(sd)) * 1.2:\n            desired = target_pct if c30[-1] > h30[-2] else (-target_pct if allow_short else 0.0)\n"),
        ("reg_ma_fan", "        ma10 = _rolling_mean(c30, 10)\n        ma30 = _rolling_mean(c30, 30)\n        ma60 = _rolling_mean(c30, 60)\n        if ma10 and ma30 and ma60:\n            if ma10[-1] > ma30[-1] > ma60[-1]:\n                desired = target_pct\n            elif ma10[-1] < ma30[-1] < ma60[-1] and allow_short:\n                desired = -target_pct\n"),
        ("reg_adx_proxy", "        if len(c30) >= 20:\n            up = sum(max(c30[i]-c30[i-1],0) for i in range(-19,0))\n            dn = sum(max(c30[i-1]-c30[i],0) for i in range(-19,0))\n            if up > dn * 1.5:\n                desired = target_pct\n            elif dn > up * 1.5 and allow_short:\n                desired = -target_pct\n"),
        ("reg_vol_target", "        sd = _rolling_std(c30, 20)\n        if sd and sd[-1]:\n            scale = min(1.0, 0.01 / sd[-1])\n            desired = target_pct * scale if c30[-1] > _rolling_mean(c30, 20)[-1] else (-target_pct * scale if allow_short else 0.0)\n"),
        ("reg_chop_filter", "        if len(c30) >= 20:\n            chop = sum(abs(c30[i]-c30[i-1]) for i in range(-19,0))\n            net = abs(c30[-1]-c30[-20])\n            if net > chop * 0.35:\n                desired = target_pct if c30[-1] > c30[-20] else (-target_pct if allow_short else 0.0)\n"),
        ("reg_dual_regime", "        ma20 = _rolling_mean(c30, 20)\n        sd = _rolling_std(c30, 20)\n        if ma20 and sd:\n            trending = sd[-1] > sum(sd[-10:])/min(10,len(sd))\n            if trending:\n                desired = target_pct if c30[-1] > ma20[-1] else (-target_pct if allow_short else 0.0)\n            else:\n                desired = target_pct if c30[-1] < ma20[-1] else (-target_pct if allow_short else 0.0)\n"),
        ("reg_breakout_regime", "        hi = _rolling_max(h30, 55)\n        lo = _rolling_min(l30, 20)\n        sd = _rolling_std(c30, 20)\n        if hi and lo and sd and sd[-1] > sum(sd[-20:])/min(20,len(sd)):\n            if c30[-1] > hi[-2]:\n                desired = target_pct\n            elif c30[-1] < lo[-2] and allow_short:\n                desired = -target_pct\n"),
        ("reg_mean_regime", "        sd = _rolling_std(c30, 20)\n        ma = _rolling_mean(c30, 20)\n        if sd and ma and sd[-1] < sum(sd[-20:])/min(20,len(sd))*0.9:\n            desired = target_pct if c30[-1] < ma[-1] else (-target_pct if c30[-1] > ma[-1] and allow_short else 0.0)\n"),
    ],
    "strategy_v2_orderflow_proxy_pack": [
        ("flow_obv", "        obv = 0.0\n        for i in range(1, len(c30)):\n            if c30[i] > c30[i-1]:\n                obv += v30[i]\n            elif c30[i] < c30[i-1]:\n                obv -= v30[i]\n        desired = target_pct if obv > 0 else (-target_pct if allow_short else 0.0)\n"),
        ("flow_vol_delta", "        if len(c30) >= 2:\n            upv = v30[-1] if c30[-1] >= c30[-2] else 0\n            dnv = v30[-1] if c30[-1] < c30[-2] else 0\n            desired = target_pct if upv > dnv else (-target_pct if allow_short else 0.0)\n"),
        ("flow_mfi_proxy", "        if len(c30) >= 15:\n            tp = [(h30[i]+l30[i]+c30[i])/3 for i in range(-14,0)]\n            rmf_pos = sum(tp[i]*v30[-14+i] for i in range(14) if i>0 and tp[i]>tp[i-1])\n            rmf_neg = sum(tp[i]*v30[-14+i] for i in range(14) if i>0 and tp[i]<tp[i-1])\n            if rmf_pos > rmf_neg:\n                desired = target_pct\n            elif rmf_neg > rmf_pos and allow_short:\n                desired = -target_pct\n"),
        ("flow_vwap_dev", "        if len(c30) >= 20:\n            num = sum(c30[i]*v30[i] for i in range(-20,0))\n            den = sum(v30[-20:])\n            vwap = num/den if den else c30[-1]\n            dev = (c30[-1]-vwap)/vwap if vwap else 0\n            desired = target_pct if dev > 0.001 else (-target_pct if dev < -0.001 and allow_short else 0.0)\n"),
        ("flow_absorption", "        if len(c30) >= 5 and v30[-1] > sum(v30[-5:])/5*1.5:\n            desired = target_pct if c30[-1] > c30[-2] else (-target_pct if allow_short else 0.0)\n"),
        ("flow_climax", "        if v30[-1] > sum(v30[-20:])/min(20,len(v30))*2:\n            desired = -target_pct if c30[-1] > c30[-2] and allow_short else (target_pct if c30[-1] < c30[-2] else 0.0)\n"),
        ("flow_divergence", "        if len(c30) >= 10:\n            price_up = c30[-1] > c30[-10]\n            vol_up = v30[-1] > sum(v30[-10:])/10\n            if price_up and not vol_up and allow_short:\n                desired = -target_pct\n            elif not price_up and vol_up:\n                desired = target_pct\n"),
        ("flow_imbalance_ma", "        imb = [v30[i] if c30[i] >= c30[i-1] else -v30[i] for i in range(1,len(c30))]\n        if len(imb) >= 10:\n            desired = target_pct if sum(imb[-10:]) > 0 else (-target_pct if allow_short else 0.0)\n"),
        ("flow_tick_rule", "        ups = sum(1 for i in range(-20,0) if c30[i] > c30[i-1])\n        desired = target_pct if ups >= 12 else (-target_pct if ups <= 8 and allow_short else 0.0)\n"),
        ("flow_effort_result", "        if len(c30) >= 5:\n            effort = sum(v30[-5:])\n            result = abs(c30[-1]-c30[-5])\n            if effort > 0 and result/effort < 0.0001:\n                desired = -target_pct if c30[-1] > c30[-5] and allow_short else (target_pct if c30[-1] < c30[-5] else 0.0)\n"),
    ],
}

HEADER = '''{title}
{description}
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
'''

FOOTER = '''
    if desired > 0 and not is_long:
        order_target_percent(g.futures, target_pct, reason=reason)
    elif desired < 0 and allow_short and not is_short:
        order_target_percent(g.futures, -target_pct, reason=reason)
    elif abs(desired) <= 1e-12 and (is_long or is_short):
        order_target_percent(g.futures, 0.0, reason=reason + "_exit")
'''


def _build_variant_block(variant: int, reason: str, body: str) -> str:
    kw = "if" if variant == 0 else "elif"
    return f"    {kw} variant == {variant}:\n{body}        reason = \"{reason}\"\n"


def build_pack_code(title: str, description: str, pack_key: str) -> str:
    parts = [HEADER.format(title=title, description=description)]
    for idx, (reason, body) in enumerate(VARIANT_SNIPPETS[pack_key]):
        parts.append(_build_variant_block(idx, reason, body))
    parts.append(FOOTER)
    return "".join(parts)


def main() -> None:
    keys = [meta[0] for meta in PACK_META]
    lines = [
        "-- Strategy API V2 advanced pack seed (5 packs x 10 variants = 50 strategies)",
        "",
        "INSERT INTO qd_script_templates",
        "(template_key, asset_type, title, description, code, param_schema, tags, icon, accent, sort_order, is_active, metadata, updated_at)",
        "VALUES",
    ]
    value_rows: list[str] = []
    for key, tag, title, desc, tag_slug, accent, sort_order in PACK_META:
        code = build_pack_code(title, desc, key)
        tags = f'["strategy-v2","cta","pack","cn-futures","options","{tag_slug}"]'
        row = (
            f"('{key}', 'portfolio_strategy', '{title}', '{desc}', ${tag}$\"\"\"\n"
            f"{code}\n"
            f"${tag}$, '{PARAM_SCHEMA}'::jsonb, '{tags}'::jsonb, 'experiment', '{accent}', {sort_order}, TRUE, "
            f"'{{\"source\":\"system_seed\",\"version\":11,\"apiVersion\":2}}'::jsonb, NOW())"
        )
        value_rows.append(row)
    lines.append(",\n".join(value_rows))
    lines.append("ON CONFLICT (template_key) DO UPDATE SET")
    lines.append("    asset_type = EXCLUDED.asset_type,")
    lines.append("    title = EXCLUDED.title,")
    lines.append("    description = EXCLUDED.description,")
    lines.append("    code = EXCLUDED.code,")
    lines.append("    param_schema = EXCLUDED.param_schema,")
    lines.append("    tags = EXCLUDED.tags,")
    lines.append("    icon = EXCLUDED.icon,")
    lines.append("    accent = EXCLUDED.accent,")
    lines.append("    sort_order = EXCLUDED.sort_order,")
    lines.append("    is_active = TRUE,")
    lines.append("    metadata = EXCLUDED.metadata,")
    lines.append("    updated_at = NOW();")
    lines.append("")
    lines.append(f"-- pack_keys: {', '.join(keys)}")
    OUTPUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"wrote {OUTPUT} ({OUTPUT.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
