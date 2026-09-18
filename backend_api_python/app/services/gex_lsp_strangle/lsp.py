"""LSP features: regime labels plus a continuous delta-targeting score.

``lsp_delta_score`` ∈ [-1, 1] maps dual-window LSP into portfolio delta bias:
  - positive → want net long delta
  - negative → want net short delta
  - near 0 → prefer delta-neutral short-vol structure
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd


def _wma(series: pd.Series, period: int) -> pd.Series:
    period = max(1, int(period))
    s = series.astype(float)
    if period == 1:
        return s.copy()
    weights = np.arange(1, period + 1, dtype=float)
    weights = weights / weights.sum()
    x = s.to_numpy(dtype=float, copy=True)
    n = x.size
    out = np.full(n, np.nan, dtype=float)
    valid = np.isfinite(x)
    filled = np.where(valid, x, 0.0)
    conv = np.convolve(filled, weights[::-1], mode="valid")
    nan_win = np.convolve((~valid).astype(float), np.ones(period), mode="valid")
    conv = np.where(nan_win > 0, np.nan, conv)
    out[period - 1 :] = conv
    return pd.Series(out, index=series.index)


def _safe_div(numer: pd.Series, denom: pd.Series) -> pd.Series:
    d = denom.astype(float).replace(0.0, np.nan)
    return numer.astype(float) / d


def compute_lsp_features(
    bars: pd.DataFrame,
    *,
    days_1: int = 5,
    days_2: int = 10,
    neutral_band: float = 8.0,
) -> pd.DataFrame:
    """Return LSP windows, regime, and continuous ``lsp_delta_score``."""
    df = bars.copy()
    for col in ("open", "high", "low", "close"):
        if col not in df.columns:
            raise ValueError(f"bars missing column: {col}")
    if "volume" not in df.columns:
        df["volume"] = 1.0

    open_ = df["open"].astype(float).fillna(df["close"].astype(float))
    high = df["high"].astype(float)
    low = df["low"].astype(float)
    close = df["close"].astype(float)
    volume = df["volume"].astype(float)
    volume = volume.where(volume >= 1000.0, (df["amount"].astype(float) if "amount" in df.columns else close * 1e6))
    volume = volume.replace(0.0, np.nan).fillna(close.abs() * 1e6)

    valuepath = close - open_
    shortpath = 2.0 * (high - low) - (close - open_).abs()
    doji = shortpath == 0
    close_dir = pd.Series(np.where((close - close.shift(1)) > 0, 1.0, -1.0), index=df.index)
    valuepercent = _safe_div(valuepath, shortpath).where(~doji, close_dir)
    valuetrade = 100.0 * volume * close * valuepercent
    valuevolume = volume * valuepercent

    def _window(n_days: int) -> pd.Series:
        buyvolume = valuevolume.where(valuevolume > 0, 0.0).rolling(n_days, min_periods=n_days).sum()
        buyamount = valuetrade.where(valuetrade > 0, 0.0).rolling(n_days, min_periods=n_days).sum()
        sellamount = valuetrade.where(valuetrade < 0, 0.0).rolling(n_days, min_periods=n_days).sum().abs()
        sellvolume = valuevolume.where(valuevolume < 0, 0.0).rolling(n_days, min_periods=n_days).sum().abs()
        curamount_b = buyvolume * close * 100.0
        ca_b = _wma(curamount_b, n_days)
        fullcash_b = curamount_b + sellamount
        fc_b = _wma(fullcash_b, n_days)
        return 100.0 * _safe_div(ca_b, fc_b)

    days_1 = max(1, int(days_1))
    days_2 = max(1, int(days_2))
    lsp_bb = _window(days_1)
    lsp_bb2 = _window(days_2)
    mid = 50.0
    band = max(0.0, float(neutral_band))
    bullish = (lsp_bb >= mid + band) & (lsp_bb2 >= mid + band)
    bearish = (lsp_bb <= mid - band) & (lsp_bb2 <= mid - band)
    neutral = ((lsp_bb - mid).abs() <= band) & ((lsp_bb2 - mid).abs() <= band)
    regime = np.where(bullish, "bullish", np.where(bearish, "bearish", np.where(neutral, "neutral", "mixed")))

    # Continuous score: average distance from 50, clipped to [-1, 1].
    raw = ((lsp_bb.fillna(mid) + lsp_bb2.fillna(mid)) / 2.0 - mid) / 50.0
    lsp_delta_score = raw.clip(-1.0, 1.0)

    return pd.DataFrame(
        {
            "lsp_bb": lsp_bb,
            "lsp_bb2": lsp_bb2,
            "lsp_regime": regime,
            "lsp_delta_score": lsp_delta_score,
            # Kept for compatibility with older gates / reports.
            "lsp_ok_for_short_vol": True,
        },
        index=df.index,
    )


def lsp_target_delta_shares(
    lsp_delta_score: float,
    *,
    lots: int,
    multiplier: float,
    max_abs_delta: float = 0.5,
) -> float:
    """Map LSP score to target net portfolio delta in underlying shares."""
    score = float(np.clip(lsp_delta_score, -1.0, 1.0))
    max_abs_delta = max(0.0, float(max_abs_delta))
    return score * max_abs_delta * max(int(lots), 1) * float(multiplier)


def lsp_option_skew_lots(
    lsp_delta_score: float,
    *,
    base_lots: int,
    max_skew_lots: int = 1,
) -> tuple[int, int]:
    """Translate LSP into short call/put lot skew for a seller book.

    Bullish (score>0): sell more puts than calls → residual long delta bias.
    Bearish (score<0): sell more calls than puts → residual short delta bias.
    Returns ``(call_lots, put_lots)`` as positive short sizes.
    """
    base = max(int(base_lots), 1)
    max_skew = max(int(max_skew_lots), 0)
    score = float(np.clip(lsp_delta_score, -1.0, 1.0))
    skew = int(round(abs(score) * max_skew))
    skew = min(skew, base)  # never reduce a leg below 0
    if score > 0:
        return base - skew, base + skew
    if score < 0:
        return base + skew, base - skew
    return base, base


def lsp_ok_row(row: dict[str, Any] | pd.Series) -> bool:
    val = row.get("lsp_ok_for_short_vol") if hasattr(row, "get") else row["lsp_ok_for_short_vol"]
    return bool(val)
