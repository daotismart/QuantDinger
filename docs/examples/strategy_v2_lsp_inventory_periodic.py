"""LSP Inventory Periodic Book Trading
Uses Tongdaxin-style LSP (signed candle-path volume) as the inventory
controller. On a fixed bar cadence the strategy trades toward the LSP target
inventory at book-style prices: take liquidity near mid±half-spread (market)
or post a limit at the bid/ask (maker).

Default universe is USStock:SPY on 1h bars (long-only inventory in [0, max]).
Set direction_mode=both and a swap symbol for signed inventory.
"""

import math

# @param days_1 int 5 Short LSP window range=3:60:1
# @param days_2 int 10 Long LSP window range=5:120:1
# @param rebalance_every int 4 Trade every N completed bars range=1:48:1
# @param max_position_pct float 0.95 Max |target| portfolio weight range=0.05:1:0.05
# @param long_only bool true Clamp inventory target to [0, max]
# @param deadband_pct float 0.05 Skip rebalance when |error| below this range=0:0.5:0.01
# @param book_spread_bps float 4.0 Half book spread in bps around mid range=0:50:0.5
# @param fill_mode str take take=cross book; make=post limit at bid/ask
# @param min_lsp_bars int 30 Warm bars required before first trade range=20:200:1

PERSIST_RUNTIME_STATE = True

SYMBOL = "USStock:SPY"
BAR_FREQUENCY = "1h"


def initialize(context):
    g.symbol = SYMBOL
    g.bar_index = 0
    g.last_target = 0.0
    g.bid_oid = ""
    g.ask_oid = ""
    context.set_universe([g.symbol])
    context.set_benchmark(g.symbol)
    context.subscribe(
        frequency=BAR_FREQUENCY,
        fields=["open", "high", "low", "close", "volume"],
    )
    context.set_warmup(120)
    context.set_metadata(
        direction_mode="long_only",
        strategy_family="inventory_lsp_periodic",
    )


def handle_data(context, data):
    if not is_trade():
        return
    if context.current_dt is None:
        return

    days_1 = max(int(context.params.get("days_1", 5) or 5), 1)
    days_2 = max(int(context.params.get("days_2", 10) or 10), 1)
    rebalance_every = max(int(context.params.get("rebalance_every", 4) or 4), 1)
    max_position_pct = _clip(
        float(context.params.get("max_position_pct", 0.95) or 0.95),
        0.05,
        1.0,
    )
    long_only = _as_bool(context.params.get("long_only", True), True)
    deadband_pct = max(float(context.params.get("deadband_pct", 0.05) or 0.0), 0.0)
    book_spread_bps = max(float(context.params.get("book_spread_bps", 4.0) or 0.0), 0.0)
    fill_mode = str(context.params.get("fill_mode", "take") or "take").strip().lower()
    min_lsp_bars = max(int(context.params.get("min_lsp_bars", 30) or 30), 20)

    lookback = max(days_2 * 4, min_lsp_bars) + 5
    bars = data.history(
        g.symbol,
        count=lookback,
        fields=["open", "high", "low", "close", "volume"],
    )
    if bars is None or len(bars) < min_lsp_bars:
        return

    g.bar_index = int(g.bar_index) + 1
    features = compute_lsp_inventory_features(
        opens=bars["open"].astype(float),
        highs=bars["high"].astype(float),
        lows=bars["low"].astype(float),
        closes=bars["close"].astype(float),
        volumes=bars["volume"].astype(float),
        days_1=days_1,
        days_2=days_2,
    )
    if features is None:
        return

    score = float(features["inventory_score"])
    target_pct = score * max_position_pct
    if long_only:
        target_pct = max(0.0, target_pct)

    mid = float(data.current(g.symbol, "close"))
    if mid <= 0.0:
        return

    position = get_position(g.symbol)
    current_amount = float(position.amount or 0.0)
    equity = float(context.portfolio.total_value or 0.0)
    current_pct = 0.0
    if equity > 0.0 and mid > 0.0:
        current_pct = current_amount * mid / equity

    # Cancel resting maker quotes every bar; recreate on rebalance if still needed.
    _cancel_working(g.bid_oid)
    _cancel_working(g.ask_oid)
    g.bid_oid = ""
    g.ask_oid = ""

    if g.bar_index % rebalance_every != 0:
        return
    if abs(target_pct - current_pct) < deadband_pct:
        g.last_target = target_pct
        return

    half_spread = mid * book_spread_bps / 10000.0
    delta_pct = target_pct - current_pct
    reason = (
        f"lsp_inv_rebalance score={score:.3f} "
        f"lsp_bb={features['lsp_bb']:.2f} lsp_bb2={features['lsp_bb2']:.2f}"
    )

    tag = str(context.current_dt).replace(" ", "").replace(":", "").replace("-", "")[:14]
    if fill_mode == "make":
        # Post at bid when buying inventory, at ask when selling (book prices).
        target_value = target_pct * equity
        target_amount = target_value / mid if mid > 0 else 0.0
        delta_amount = target_amount - current_amount
        if abs(delta_amount) < 1e-8:
            g.last_target = target_pct
            return
        if delta_amount > 0:
            limit_px = max(mid - half_spread, 1e-6)
            g.bid_oid = order(
                g.symbol,
                abs(delta_amount),
                order_type="limit",
                limit_price=float(limit_px),
                client_order_id=("lsp-bid-" + tag)[:100],
                reason=reason + " side=bid",
            ) or ""
        else:
            limit_px = mid + half_spread
            g.ask_oid = order(
                g.symbol,
                -abs(delta_amount),
                order_type="limit",
                limit_price=float(limit_px),
                client_order_id=("lsp-ask-" + tag)[:100],
                reason=reason + " side=ask",
            ) or ""
    else:
        # Take liquidity: marketable order toward target; engine slippage
        # approximates crossing the book around mid.
        order_target_percent(
            g.symbol,
            target_pct,
            reason=reason + f" side={'buy' if delta_pct > 0 else 'sell'}",
        )

    g.last_target = target_pct


def compute_lsp_inventory_features(
    *,
    opens,
    highs,
    lows,
    closes,
    volumes,
    days_1=5,
    days_2=10,
):
    """Return latest LSP inventory score in [-1, 1] (positive => long bias)."""
    import numpy as np
    import pandas as pd

    open_ = pd.Series(opens).astype(float)
    high = pd.Series(highs).astype(float)
    low = pd.Series(lows).astype(float)
    close = pd.Series(closes).astype(float)
    volume = pd.Series(volumes).astype(float)
    if len(close) < max(days_1, days_2) + 2:
        return None

    amount = volume * close * 100.0
    valuepath = close - open_
    shortpath = 2.0 * (high - low) - (close - open_).abs()
    doji = shortpath == 0
    close_dir = pd.Series(
        np.where((close - close.shift(1)) > 0, 1.0, -1.0),
        index=close.index,
    )
    valuepercent = _safe_div(valuepath, shortpath).where(~doji, close_dir)
    valuetrade = 100.0 * volume * close * valuepercent
    valuevolume = volume * valuepercent

    w1 = _lsp_window(valuevolume, valuetrade, close, days_1, smooth=False)
    w2 = _lsp_window(valuevolume, valuetrade, close, days_2, smooth=True)
    lsp_bb = w1["lsp_bb"]
    lsp_bb2 = w2["lsp_bb"]
    dlt_bb = w1["dlt_bb"]
    dlt_bb2 = w2["dlt_bb"]

    # Tongdaxin-style Kelly proxy: high LSP => crowded buy side => cut inventory.
    bias = pd.Series(
        np.where((lsp_bb2 < 100) & (dlt_bb2 > -2), 30.0, -30.0),
        index=close.index,
    )
    score01 = ((100.0 - (lsp_bb * 3.0 + lsp_bb2) / 4.0) + bias) / 100.0
    score01 = score01.where(~((dlt_bb < -2) & (dlt_bb2 < 0)), 0.0).clip(0.0, 1.0)
    # Map [0,1] -> [-1,1] for signed inventory controllers.
    inventory_score = (score01 * 2.0) - 1.0

    i = -1
    if not math.isfinite(float(inventory_score.iloc[i])):
        return None
    return {
        "lsp_bb": float(lsp_bb.iloc[i]),
        "lsp_bb2": float(lsp_bb2.iloc[i]),
        "dlt_bb": float(dlt_bb.iloc[i]),
        "dlt_bb2": float(dlt_bb2.iloc[i]),
        "score01": float(score01.iloc[i]),
        "inventory_score": float(inventory_score.iloc[i]),
    }


def _lsp_window(valuevolume, valuetrade, close, n_days, smooth):
    import pandas as pd

    n_days = max(1, int(n_days))
    buyvolume = _rolling_sum(valuevolume.where(valuevolume > 0, 0.0), n_days)
    buyamount = _rolling_sum(valuetrade.where(valuetrade > 0, 0.0), n_days)
    sellamount = _rolling_sum(valuetrade.where(valuetrade < 0, 0.0), n_days).abs()
    sellvolume = _rolling_sum(valuevolume.where(valuevolume < 0, 0.0), n_days).abs()

    curvolume_b = buyvolume
    curamount_b = curvolume_b * close * 100.0
    ca_b = _wma(curamount_b, n_days)
    curcash_b = sellamount
    fullcash_b = curamount_b + curcash_b
    fc_bb_wma = _wma(fullcash_b, n_days)

    curvolume_s = sellvolume
    curamount_s = curvolume_s * close * 100.0
    ca_s = _wma(curamount_s, n_days)
    fullcash_s = curamount_s + buyamount

    lsp_b = 100.0 * _safe_div(curamount_b, fullcash_b)
    if smooth:
        lsp_bb = _wma(lsp_b, n_days)
    else:
        lsp_bb = 100.0 * _safe_div(ca_b, fc_bb_wma)
    dlt_bb = lsp_bb - lsp_bb.shift(1)
    return {
        "lsp_bb": lsp_bb,
        "dlt_bb": dlt_bb,
        "lsp_b": lsp_b,
        "fullcash_s": fullcash_s,
        "ca_s": ca_s,
    }


def _rolling_sum(series, period):
    period = max(1, int(period))
    return series.astype(float).rolling(window=period, min_periods=period).sum()


def _wma(series, period):
    import numpy as np
    import pandas as pd

    period = max(1, int(period))
    s = series.astype(float)
    if period == 1:
        return s.copy()
    x = s.to_numpy(dtype=float, copy=True)
    n = x.size
    out = np.full(n, np.nan, dtype=float)
    weights = np.arange(1, period + 1, dtype=float)
    weights = weights / weights.sum()
    valid = np.isfinite(x)
    filled = np.where(valid, x, 0.0)
    conv = np.convolve(filled, weights[::-1], mode="valid")
    nan_win = np.convolve((~valid).astype(float), np.ones(period), mode="valid")
    conv = np.where(nan_win > 0, np.nan, conv)
    out[period - 1 :] = conv
    return pd.Series(out, index=series.index)


def _safe_div(numer, denom):
    d = denom.astype(float).replace(0.0, float("nan"))
    return numer.astype(float) / d


def _clip(value, lo, hi):
    return max(lo, min(hi, float(value)))


def _as_bool(value, default):
    if isinstance(value, bool):
        return value
    if value is None:
        return default
    text = str(value).strip().lower()
    if text in {"1", "true", "yes", "on"}:
        return True
    if text in {"0", "false", "no", "off"}:
        return False
    return default


def _cancel_working(order_id):
    if not order_id:
        return
    try:
        cancel_order(order_id)
    except Exception:
        pass
