# ============================================================
# QuantDinger chart indicator: LSP (liquidity / signed-path)
# ------------------------------------------------------------
# Port of a Tongdaxin LSP script. Chart-only: no orders, no
# backtest columns, no live execution.
#
# Paste this file into the Indicator IDE. Convert to Strategy
# API V2 before backtesting or live trading.
# ============================================================

my_indicator_name = "LSP"
my_indicator_description = (
    "Pane oscillator from signed candle-path volume: dual-window LSP, "
    "KD, MPF, Kelly-style F/P, BUY0/SELL0 markers, and bagua labels. "
    "days_1 / days_2 are the two SUM/WMA windows (TDX days / days2)."
)

# @param days_1 int 5 Short LSP window (days) range=3:60:1
# @param days_2 int 10 Long LSP window (days2) range=5:120:1
# @param n_rsv int 9 RSV lookback N range=3:21:1
# @param mpfx float 1.0 Percent oscillator scale
# @param sigs int 1 MPFD lookback (refv of pf)
# @param trds int 20 Trend MA length for PRC / ppf
# @param b_xkd float 0.0 BUY0 min dlt_KD
# @param b_xdbb float 0.0 BUY0 min dlt_BB
# @param b_xdbb2 float 0.0 BUY0 min dlt_BB2
# @param b_xdmpf float 0.0 BUY0 min dlt_mpf
# @param show_force bool false Plot force / forceB oscillators
# @param show_path bool false Plot path volume / full-cash oscillators

days_1 = int(params.get("days_1", 5))
days_2 = int(params.get("days_2", 10))
n_rsv = int(params.get("n_rsv", 9))
mpfx = float(params.get("mpfx", 1.0))
sigs = int(params.get("sigs", 1))
trds = int(params.get("trds", 20))
b_xkd = float(params.get("b_xkd", 0.0))
b_xdbb = float(params.get("b_xdbb", 0.0))
b_xdbb2 = float(params.get("b_xdbb2", 0.0))
b_xdmpf = float(params.get("b_xdmpf", 0.0))
show_force = bool(params.get("show_force", False))
show_path = bool(params.get("show_path", False))

df = df.copy()

days_1 = max(1, days_1)
days_2 = max(1, days_2)
n_rsv = max(1, n_rsv)
sigs = max(1, sigs)
trds = max(1, trds)


def to_plot_list(series):
    out = []
    for value in series:
        if value is None or pd.isna(value) or np.isinf(value):
            out.append(None)
        else:
            out.append(float(value))
    return out


def refv(series, n=1):
    return series.shift(max(1, int(n)))


def ma(series, period):
    period = max(1, int(period))
    return series.astype(float).rolling(window=period, min_periods=period).mean()


def hhv(series, period):
    period = max(1, int(period))
    return series.astype(float).rolling(window=period, min_periods=period).max()


def llv(series, period):
    period = max(1, int(period))
    return series.astype(float).rolling(window=period, min_periods=period).min()


def rolling_sum(series, period):
    period = max(1, int(period))
    return series.astype(float).rolling(window=period, min_periods=period).sum()


def wma(series, period):
    """TDX WMA: oldest weight 1, newest weight N."""
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


def tdx_sma(series, period, weight=1.0):
    """TDX SMA(X,N,M) = (M*X + (N-M)*Y')/N  <=>  ewm(alpha=M/N)."""
    period = max(1, int(period))
    alpha = float(weight) / float(period)
    alpha = min(max(alpha, 1e-12), 1.0)
    return series.astype(float).ewm(alpha=alpha, adjust=False, min_periods=1).mean()


def safe_div(numer, denom):
    d = denom.astype(float).replace(0.0, np.nan)
    return numer.astype(float) / d


def scale_0_100(series, period):
    lo = llv(series, period)
    hi = hhv(series, period)
    return 100.0 * safe_div(series - lo, hi - lo)


def edge(condition):
    current = condition.fillna(False).astype(bool)
    previous = current.shift(1, fill_value=False).astype(bool)
    return current & ~previous


def line_plot(name, series, color, width=2):
    return {
        "name": name,
        "data": to_plot_list(series),
        "color": color,
        "type": "line",
        "overlay": False,
        "lineWidth": width,
    }


open_ = df["open"].astype(float)
high = df["high"].astype(float)
low = df["low"].astype(float)
close = df["close"].astype(float)
volume = df["volume"].astype(float)
if "amount" in df.columns:
    amount = df["amount"].astype(float)
elif "turnover" in df.columns:
    amount = df["turnover"].astype(float)
else:
    amount = volume * close * 100.0

# Signed path: body / (2*range - |body|). Doji uses close direction.
valuepath = close - open_
shortpath = 2.0 * (high - low) - (close - open_).abs()
doji = shortpath == 0
close_dir = pd.Series(
    np.where((close - refv(close, 1)) > 0, 1.0, -1.0),
    index=df.index,
)
valuepercent = safe_div(valuepath, shortpath).where(~doji, close_dir)

valuetrade = 100.0 * volume * close * valuepercent
valuevolume = volume * valuepercent


def lsp_window(n_days, smooth_lsp_with_wma):
    """One TDX window: SUM signed vol/amount, WMA cash, LSP ratios."""
    buyvolume = rolling_sum(valuevolume.where(valuevolume > 0, 0.0), n_days)
    buyamount = rolling_sum(valuetrade.where(valuetrade > 0, 0.0), n_days)
    sellamount = rolling_sum(valuetrade.where(valuetrade < 0, 0.0), n_days).abs()
    sellvolume = rolling_sum(valuevolume.where(valuevolume < 0, 0.0), n_days).abs()

    curvolume_b = buyvolume
    cv_b = wma(curvolume_b, n_days)
    curamount_b = curvolume_b * close * 100.0
    ca_b = wma(curamount_b, n_days)
    curcash_b = sellamount
    cc_b = wma(curcash_b, n_days)
    fullcash_b = curamount_b + curcash_b
    fc_bb_wma = wma(fullcash_b, n_days)

    curvolume_s = sellvolume
    cv_s = wma(curvolume_s, n_days)
    curamount_s = curvolume_s * close * 100.0
    ca_s = wma(curamount_s, n_days)
    curcash_s = buyamount
    cc_s = wma(curcash_s, n_days)
    fullcash_s = curamount_s + curcash_s
    fc_ss_wma = wma(fullcash_s, n_days)

    lsp_b = 100.0 * safe_div(curamount_b, fullcash_b)
    if smooth_lsp_with_wma:
        lsp_bb = wma(lsp_b, n_days)
        lsp_ss = wma(100.0 * safe_div(curamount_s, fullcash_s), n_days)
    else:
        lsp_bb = 100.0 * safe_div(ca_b, fc_bb_wma)
        # Original window-1 uses ca_S / fc_BB (the buy-side WMA full cash).
        lsp_ss = 100.0 * safe_div(ca_s, fc_bb_wma)
    lsp_s = 100.0 * safe_div(curamount_s, fullcash_s)
    dlt_bb = lsp_bb - refv(lsp_bb, 1)

    force_raw = curamount_b + curamount_s - curcash_b - curcash_s
    force_b_raw = ca_b + ca_s - cc_b - cc_s
    fc_b = scale_0_100(fullcash_b, n_days)
    fc_s = scale_0_100(fullcash_s, n_days)
    return {
        "lsp_b": lsp_b,
        "lsp_bb": lsp_bb,
        "dlt_bb": dlt_bb,
        "lsp_s": lsp_s,
        "lsp_ss": lsp_ss,
        "cv": scale_0_100(curvolume_b, n_days),
        "cv_bb": scale_0_100(cv_b, n_days),
        "fc_b": fc_b,
        "fc_bb": scale_0_100(fc_b, n_days),
        "fc_s": fc_s,
        "fc_ss": scale_0_100(fc_s, n_days),
        "force": scale_0_100(force_raw, n_days),
        "force_b": scale_0_100(force_b_raw, n_days),
        "fc_bb_wma": fc_bb_wma,
        "fc_ss_wma": fc_ss_wma,
    }


w1 = lsp_window(days_1, smooth_lsp_with_wma=False)
w2 = lsp_window(days_2, smooth_lsp_with_wma=True)

lsp_bb = w1["lsp_bb"]
dlt_bb = w1["dlt_bb"]
lsp_bb2 = w2["lsp_bb"]
dlt_bb2 = w2["dlt_bb"]

fc_b = w1["fc_b"]
fc_bb = w1["fc_bb"]
fc_s = w1["fc_s"]
fc_ss = w1["fc_ss"]
fc_b2 = w2["fc_b"]
fc_bb2 = w2["fc_bb"]
fc_s2 = w2["fc_s"]
fc_ss2 = w2["fc_ss"]

mpr = ma(close, days_1)
mpr2 = ma(close, days_2)
pc = safe_div(amount, volume * 100.0)
mpc = ma(pc, days_1)
dlt_pr = 50.0 + safe_div((close - refv(close, 1)) * 100.0 * mpfx, close)
dlt_pc = 50.0 + safe_div((pc - refv(pc, 1)) * 100.0 * mpfx, pc)
pf = 50.0 + safe_div((close - mpr) * 100.0 * mpfx, mpr)
pf2 = 50.0 + safe_div((close - mpr2) * 100.0 * mpfx, mpr2)
mpf = ma(pf, days_1)
mpfd = 50.0 + ma(pf - refv(pf, sigs), days_1)
mpf2 = ma(pf2, days_2)
mpf_opt = mpf - mpf2
dlt_mpf = mpf - refv(mpf, 1)
dlt_mpf2 = mpf2 - refv(mpf2, 1)

fin1 = scale_0_100(ma(amount, 2), n_rsv)
f1 = tdx_sma(fin1, days_1, 1)
ff1 = tdx_sma(f1, days_1, 1)
ppf = 50.0 + mpfx * 100.0 * safe_div(close - ma(close, trds), ma(close, trds))
prc = 50.0 + mpfx * 100.0 * safe_div(close - ma(close, days_1), ma(close, days_1))

rsv = 100.0 * safe_div(close - llv(low, n_rsv), hhv(high, n_rsv) - llv(low, n_rsv))
k1 = tdx_sma(rsv, days_1, 1)
d1 = tdx_sma(k1, days_1, 1)
kd = k1 - d1
dlt_kd = kd - refv(kd, 1)
dlt_k1 = k1 - refv(k1, 1)
dlt_d1 = d1 - refv(d1, 1)

tt = dlt_mpf
dd = dlt_bb
rr = dlt_k1

buy0_state = (
    (dlt_kd > b_xkd)
    & (refv(dlt_kd, 1) < 1)
    & (dlt_bb2 > b_xdbb2)
    & (dlt_bb > b_xdbb)
    & (dlt_mpf > b_xdmpf)
    & (lsp_bb < 80)
    & (lsp_bb2 < 80)
)
sell0_state = (dlt_bb < 0) & (refv(dlt_bb, 1) > 0) & (lsp_bb > 70)
buy0_event = edge(buy0_state)
sell0_event = edge(sell0_state)

# Bagua from sign(TT), sign(DD), sign(RR); zeros stay unlabeled.
gua_name = pd.Series(index=df.index, dtype=object)
gua_name = gua_name.where(~((tt > 0) & (dd > 0) & (rr > 0)), "乾")
gua_name = gua_name.where(~((tt < 0) & (dd < 0) & (rr < 0)), "坤")
gua_name = gua_name.where(~((tt > 0) & (dd > 0) & (rr < 0)), "离")
gua_name = gua_name.where(~((tt < 0) & (dd < 0) & (rr > 0)), "坎")
gua_name = gua_name.where(~((tt < 0) & (dd > 0) & (rr < 0)), "震")
gua_name = gua_name.where(~((tt > 0) & (dd < 0) & (rr > 0)), "巽")
gua_name = gua_name.where(~((tt > 0) & (dd < 0) & (rr < 0)), "艮")
gua_name = gua_name.where(~((tt < 0) & (dd > 0) & (rr > 0)), "兑")
gua_event = gua_name.notna() & (gua_name != gua_name.shift(1))

bias = pd.Series(
    np.where((lsp_bb2 < 100) & (dlt_bb2 > -2), 30.0, -30.0),
    index=df.index,
)
score = ((100.0 - (lsp_bb * 3.0 + lsp_bb2) / 4.0) + bias) / 100.0
p0 = score.where(~((dlt_bb < -2) & (dlt_bb2 < 0)), 0.0)
p1 = p0.clip(lower=0.0, upper=1.0)
p_line = 100.0 * p1
q = 1.0 - p1
bx = safe_div(100.0 - k1, k1)
f0 = safe_div(bx * p1 - q, bx)
f_clip = f0.where(f0 <= 100.0, 100.0)
f_line = f_clip.where(f_clip > 0, 0.0)

n = len(df)
band = []
for i in range(n):
    up = bool(dlt_bb.iloc[i] > 0) and bool(dlt_bb2.iloc[i] > 0)
    dn = bool(dlt_bb.iloc[i] < 0) and bool(dlt_bb2.iloc[i] < 0)
    left = lsp_bb.iloc[i]
    right = lsp_bb2.iloc[i]
    if (not up and not dn) or pd.isna(left) or pd.isna(right):
        band.append(None)
        continue
    color = "#EF4444" if up else "#22C55E"
    band.append({"value": float(left - right), "color": color})

buy_marks = [
    80.0 if bool(buy0_event.iloc[i]) else None for i in range(n)
]
sell_marks = [
    70.0 if bool(sell0_event.iloc[i]) else None for i in range(n)
]
gua_marks = [
    80.0 if bool(gua_event.iloc[i]) else None for i in range(n)
]
gua_text = [
    str(gua_name.iloc[i]) if bool(gua_event.iloc[i]) else None for i in range(n)
]

plots = [
    line_plot("LSP_BB", lsp_bb, "#111827", 4),
    line_plot("LSP_BB2", lsp_bb2, "#2563EB", 4),
    {
        "name": "LSP Band",
        "data": band,
        "color": "#9CA3AF",
        "type": "bar",
        "overlay": False,
        "baseValue": 0,
    },
    line_plot("Dlt_BB", dlt_bb, "#111827", 1),
    line_plot("Dlt_BB2", dlt_bb2, "#2563EB", 1),
    line_plot("MPF", mpf, "#C026D3", 4),
    line_plot("MPF2", mpf2, "#16A34A", 4),
    line_plot("MPFD", mpfd, "#06B6D4", 4),
    line_plot("Dlt_MPF", dlt_mpf, "#C026D3", 1),
    line_plot("Dlt_MPF2", dlt_mpf2, "#16A34A", 1),
    line_plot("K1", k1, "#EAB308", 4),
    line_plot("D1", d1, "#92400E", 4),
    line_plot("Dlt_KD", dlt_kd, "#EAB308", 1),
    line_plot("F1", f1, "#DC2626", 4),
    line_plot("FF1", ff1, "#F87171", 4),
    line_plot("PRC", prc, "#C026D3", 2),
    line_plot("P", p_line, "#2563EB", 5),
    line_plot("F", f_line, "#C026D3", 5),
    line_plot("80", pd.Series(80.0, index=df.index), "#9CA3AF", 1),
    line_plot("50", pd.Series(50.0, index=df.index), "#9CA3AF", 1),
    line_plot("20", pd.Series(20.0, index=df.index), "#9CA3AF", 1),
    line_plot("0", pd.Series(0.0, index=df.index), "#6B7280", 2),
]
if show_force:
    plots.extend(
        [
            line_plot("Force", w1["force"], "#4B5563", 2),
            line_plot("ForceB", w1["force_b"], "#92400E", 2),
            line_plot("Force2", w2["force"], "#4B5563", 4),
            line_plot("ForceB2", w2["force_b"], "#92400E", 4),
        ]
    )
if show_path:
    plots.extend(
        [
            line_plot("LSP_B", w1["lsp_b"], "#111827", 2),
            line_plot("CV", w1["cv"], "#6B7280", 1),
            line_plot("FC_B", fc_b, "#6B7280", 2),
            line_plot("FC_BB", fc_bb, "#6B7280", 2),
            line_plot("PF", pf, "#C026D3", 2),
            line_plot("PF2", pf2, "#16A34A", 2),
            line_plot("PPF", ppf, "#06B6D4", 4),
            line_plot("Dlt_PR", dlt_pr, "#6B7280", 5),
            line_plot("Dlt_PC", dlt_pc, "#6B7280", 5),
            line_plot("MPF_Opt", mpf_opt, "#6B7280", 5),
        ]
    )

output = {
    "name": my_indicator_name,
    "plots": plots,
    "signals": [
        {"type": "buy", "text": "BUY0", "color": "#EF4444", "data": buy_marks},
        {"type": "sell", "text": "SELL0", "color": "#22C55E", "data": sell_marks},
        {
            "type": "buy",
            "text": "Gua",
            "color": "#F59E0B",
            "data": gua_marks,
            "textData": gua_text,
        },
    ],
    "layers": [],
    "calculatedVars": {
        "days_1": days_1,
        "days_2": days_2,
        "n_rsv": n_rsv,
    },
}
