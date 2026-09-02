#!/usr/bin/env python3
"""Run iron condor backtests with synthetic 510050 ETF option data and parameter sweep."""

from __future__ import annotations

import json
import math
import os
import sys
from dataclasses import dataclass
from itertools import product
from pathlib import Path

import numpy as np
import pandas as pd

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from app.services.strategy_v2 import StrategyV2BacktestRunner

STRATEGY_PATH = _ROOT.parent / "docs" / "examples" / "strategy_v2_iron_condor.py"
UNDERLYING_KEY = "CNStock:510050.SH"
PUT_LONG_KEY = "CNIndexOptions:90000001"
PUT_SHORT_KEY = "CNIndexOptions:90000002"
CALL_SHORT_KEY = "CNIndexOptions:90000003"
CALL_LONG_KEY = "CNIndexOptions:90000004"

# Synthetic strikes aligned with strategy defaults (spot ~2.80, 3% OTM, 0.10 wing).
STRIKES = {
    PUT_LONG_KEY: 2.60,
    PUT_SHORT_KEY: 2.70,
    CALL_SHORT_KEY: 2.90,
    CALL_LONG_KEY: 3.00,
}


def _load_code() -> str:
    return STRATEGY_PATH.read_text(encoding="utf-8")


def _norm_cdf(x: float) -> float:
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def _bs_price(spot: float, strike: float, tte_years: float, sigma: float, is_call: bool) -> float:
    if spot <= 0.0 or strike <= 0.0 or tte_years <= 1e-6 or sigma <= 0.0:
        intrinsic = max(spot - strike, 0.0) if is_call else max(strike - spot, 0.0)
        return max(intrinsic, 0.001)
    vol_t = sigma * math.sqrt(tte_years)
    d1 = (math.log(spot / strike) + 0.5 * sigma * sigma * tte_years) / vol_t
    d2 = d1 - vol_t
    if is_call:
        return spot * _norm_cdf(d1) - strike * _norm_cdf(d2)
    return strike * _norm_cdf(-d2) - spot * _norm_cdf(-d1)


def _ohlc_from_close(close: np.ndarray, index: pd.DatetimeIndex, rng: np.random.Generator, width: float = 0.012):
    opened = np.roll(close, 1)
    opened[0] = close[0]
    noise = np.abs(rng.normal(0.0, width * 0.35, size=len(close)))
    high = np.maximum.reduce([close, opened, close * (1.0 + noise + width)])
    low = np.minimum.reduce([close, opened, close * (1.0 - noise - width)])
    return pd.DataFrame(
        {
            "open": opened,
            "high": high,
            "low": low,
            "close": close,
            "volume": np.full(len(close), 5_000_000.0),
            "lot_size": np.full(len(close), 1.0),
        },
        index=index,
    )


def build_synthetic_frames(
    *,
    periods: int = 520,
    seed: int = 42,
    start: str = "2024-06-03",
    spot_start: float = 2.80,
    drift: float = 0.0,
    base_vol: float = 0.18,
    vol_bump_periods: tuple[int, int] | None = (180, 220),
    vol_bump: float = 0.14,
    cycle_bars: int = 42,
    cycle_dte: int = 45,
) -> dict[str, pd.DataFrame]:
    """Generate daily underlying plus four option legs with rolling monthly expiries."""
    rng = np.random.default_rng(seed)
    index = pd.bdate_range(start, periods=periods)
    sigma_path = np.full(periods, base_vol)
    if vol_bump_periods:
        lo, hi = vol_bump_periods
        sigma_path[lo:hi] = base_vol + vol_bump

    spot = spot_start
    spots = []
    for idx in range(periods):
        dt = 1.0 / 244.0
        shock = rng.normal(drift * dt, sigma_path[idx] * math.sqrt(dt))
        spot = max(spot * math.exp(shock), 1.5)
        spots.append(spot)
    spot_arr = np.asarray(spots, dtype=float)

    option_closes: dict[str, list[float]] = {key: [] for key in STRIKES}
    for idx, ts in enumerate(index):
        cycle_idx = idx // cycle_bars
        cycle_start = index[cycle_idx * cycle_bars]
        expiry_ts = cycle_start + pd.Timedelta(days=cycle_dte)
        tte_days = max((expiry_ts - ts).days, 1)
        tte_years = tte_days / 365.0
        sigma = float(sigma_path[idx])
        s = float(spot_arr[idx])
        option_closes[PUT_LONG_KEY].append(_bs_price(s, STRIKES[PUT_LONG_KEY], tte_years, sigma, False))
        option_closes[PUT_SHORT_KEY].append(_bs_price(s, STRIKES[PUT_SHORT_KEY], tte_years, sigma, False))
        option_closes[CALL_SHORT_KEY].append(_bs_price(s, STRIKES[CALL_SHORT_KEY], tte_years, sigma, True))
        option_closes[CALL_LONG_KEY].append(_bs_price(s, STRIKES[CALL_LONG_KEY], tte_years, sigma, True))

    frames = {
        UNDERLYING_KEY: _ohlc_from_close(spot_arr, index, rng, width=0.010),
    }
    for key in STRIKES:
        closes = np.maximum(np.asarray(option_closes[key], dtype=float), 0.001)
        frames[key] = _ohlc_from_close(closes, index, rng, width=0.025)
    frames["_meta"] = pd.DataFrame({"cycle_bars": [cycle_bars], "cycle_dte": [cycle_dte]})
    return frames


def _cycle_expiry_params(ts: pd.Timestamp, cycle_bars: int, cycle_dte: int, index: pd.DatetimeIndex) -> dict:
    loc = index.get_indexer([ts], method="pad")[0]
    if loc < 0:
        loc = 0
    cycle_start = index[(loc // cycle_bars) * cycle_bars]
    expiry = cycle_start + pd.Timedelta(days=cycle_dte)
    return {
        "expiry_year": int(expiry.year),
        "expiry_month": int(expiry.month),
        "expiry_day": int(expiry.day),
    }


def run_single(
    frames: dict[str, pd.DataFrame],
    params: dict,
    *,
    initial_capital: float = 200_000.0,
    commission: float = 0.0003,
    slippage: float = 0.0002,
) -> dict:
    meta = frames.get("_meta")
    cycle_bars = int(meta["cycle_bars"].iloc[0]) if meta is not None else 42
    cycle_dte = int(meta["cycle_dte"].iloc[0]) if meta is not None else 45
    trade_frames = {key: value for key, value in frames.items() if not key.startswith("_")}

    # Rolling expiry: run segmented backtests per cycle and chain equity.
    index = trade_frames[UNDERLYING_KEY].index
    warmup_bars = 35
    segments = []
    for cycle_idx in range(0, len(index), cycle_bars):
        seg_end = min(cycle_idx + cycle_bars, len(index))
        if seg_end - cycle_idx < 10:
            continue
        seg_start = max(0, cycle_idx - warmup_bars)
        seg_index = index[seg_start:seg_end]
        seg_frames = {key: df.loc[seg_index].copy() for key, df in trade_frames.items()}
        expiry = _cycle_expiry_params(index[cycle_idx], cycle_bars, cycle_dte, index)
        seg_params = dict(params)
        seg_params.update(expiry)
        result = StrategyV2BacktestRunner(
            code=_load_code(),
            frames=seg_frames,
            initial_capital=initial_capital if not segments else segments[-1]["finalEquity"],
            commission=commission,
            slippage=slippage,
            params=seg_params,
        ).run(
            start_date=index[cycle_idx],
            end_date=index[seg_end - 1],
        )
        segments.append(result)

    if not segments:
        raise RuntimeError("no backtest segments produced")

    combined_executions = []
    for seg in segments:
        combined_executions.extend(seg.get("executions") or [])
    last = segments[-1]
    metrics = _metrics(last)
    metrics["cycles"] = len(segments)
    metrics["totalExecutions"] = len(combined_executions)
    metrics["totalTrades"] = sum(int(seg.get("totalTrades") or 0) for seg in segments)
    if len(segments) > 1:
        start_eq = float(segments[0].get("initialCapital") or initial_capital)
        end_eq = float(last.get("finalEquity") or start_eq)
        metrics["totalReturn"] = (end_eq - start_eq) / start_eq if start_eq else 0.0
    metrics["reasons"] = sorted(
        {str(item.get("reason") or "") for item in combined_executions if str(item.get("reason") or "")}
    )
    return metrics


@dataclass(frozen=True)
class SweepCase:
    put_otm_pct: float
    wing_width: float
    profit_target_pct: float
    stop_loss_mult: float


def _metrics(result: dict) -> dict:
    metrics = result.get("metrics") if isinstance(result.get("metrics"), dict) else result
    curve = result.get("equityCurve") or []
    peak = float(result.get("initialCapital") or result.get("initial_capital") or 0.0)
    max_dd = 0.0
    for point in curve:
        equity = float(point.get("equity") or point.get("value") or 0.0)
        peak = max(peak, equity)
        if peak > 0.0:
            max_dd = min(max_dd, (equity - peak) / peak)
    executions = result.get("executions") or []
    reasons = {str(item.get("reason") or "") for item in executions}
    return {
        "totalReturn": float(metrics.get("totalReturn") or metrics.get("total_return") or 0.0),
        "sharpe": float(metrics.get("sharpe") or metrics.get("sharpeRatio") or 0.0),
        "maxDrawdown": float(metrics.get("maxDrawdown") or metrics.get("max_drawdown") or max_dd),
        "totalTrades": int(result.get("totalTrades") or metrics.get("totalTrades") or 0),
        "totalExecutions": len(executions),
        "finalEquity": float(result.get("finalEquity") or 0.0),
        "reasons": sorted(reason for reason in reasons if reason),
    }


def default_grid() -> list[SweepCase]:
    return [
        SweepCase(*combo)
        for combo in product(
            (0.02, 0.03, 0.05),
            (0.05, 0.10, 0.15),
            (0.40, 0.50, 0.65),
            (1.5, 2.0, 3.0),
        )
    ]


def run_sweep(frames: dict[str, pd.DataFrame], grid: list[SweepCase] | None = None) -> list[dict]:
    grid = grid or default_grid()
    rows: list[dict] = []
    for case in grid:
        params = {
            "put_otm_pct": case.put_otm_pct,
            "call_otm_pct": case.put_otm_pct,
            "wing_width": case.wing_width,
            "profit_target_pct": case.profit_target_pct,
            "stop_loss_mult": case.stop_loss_mult,
            "contracts": 1,
            "min_credit": 0.015,
            "min_entry_dte": 21,
            "max_entry_dte": 45,
            "exit_dte": 7,
            "max_realized_vol": 0.45,
        }
        metrics = run_single(frames, params)
        rows.append(
            {
                **case.__dict__,
                **metrics,
            }
        )
    rows.sort(key=lambda item: (item["totalReturn"], item["sharpe"]), reverse=True)
    return rows


def main() -> int:
    frames = build_synthetic_frames()
    baseline = run_single(
        frames,
        {
            "put_otm_pct": 0.03,
            "call_otm_pct": 0.03,
            "wing_width": 0.10,
            "profit_target_pct": 0.50,
            "stop_loss_mult": 2.0,
            "contracts": 1,
            "min_credit": 0.015,
            "min_entry_dte": 21,
            "max_entry_dte": 45,
            "exit_dte": 7,
            "max_realized_vol": 0.45,
        },
    )
    sweep = run_sweep(frames)
    top = sweep[:5]
    summary = {
        "status": "ok",
        "strategy": str(STRATEGY_PATH),
        "baseline": baseline,
        "gridSize": len(sweep),
        "top5": top,
        "recommended": top[0] if top else None,
    }
    out_path = os.getenv("IRON_CONDOR_BACKTEST_OUTPUT", "")
    text = json.dumps(summary, ensure_ascii=False, indent=2)
    if out_path:
        Path(out_path).write_text(text, encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
