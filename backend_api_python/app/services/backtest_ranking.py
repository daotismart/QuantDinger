"""Score and rank Strategy API V2 backtest runs.

Weights match the offline ranking report used in production batch notes:
  return 40% + Sharpe 25% + drawdown 20% + profit factor 10% + traded 5%
  extreme outliers ×0.25, zero-trade ×0.35
"""

from __future__ import annotations

import json
import math
import re
from typing import Any

from app.utils.db import get_db_connection

WEIGHTS = {
    "return": 0.40,
    "sharpe": 0.25,
    "drawdown": 0.20,
    "profit_factor": 0.10,
    "traded": 0.05,
}

FAMILY_RULES: list[tuple[str, re.Pattern[str]]] = [
    ("AS Options MM", re.compile(r"AS Options Market Maker", re.I)),
    ("US Portfolio", re.compile(r"Quality Growth|Low Volatility|Momentum Top|Cap Barbell|Market Cap", re.I)),
    ("CTA Classic", re.compile(r"Moving Average|Turtle|Resonance|MACD|SuperTrend|Bullish|Three Averag", re.I)),
    ("Trend Pack", re.compile(r"Trend Following Pack", re.I)),
    ("Breakout Pack", re.compile(r"Breakout.*Momentum Pack|Breakout & Momentum", re.I)),
    ("Mean Reversion Pack", re.compile(r"Mean Reversion Pack", re.I)),
    ("Carry Pack", re.compile(r"Carry.*Pack", re.I)),
    ("Relative Value Pack", re.compile(r"Relative Value Pack", re.I)),
    ("Volatility Pack", re.compile(r"(?:^|]\s)Volatility Pack|Options Volatility Pack", re.I)),
    ("Microstructure Pack", re.compile(r"Market Microstructure Pack", re.I)),
    ("Stat Arb Pack", re.compile(r"Statistical Arbitrage Pack", re.I)),
    ("Session Alpha Pack", re.compile(r"Session Alpha Pack", re.I)),
    ("Regime Switch Pack", re.compile(r"Regime Switch Pack", re.I)),
    ("Order Flow Pack", re.compile(r"Order Flow", re.I)),
]


def _as_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        out = float(value)
        if math.isnan(out) or math.isinf(out):
            return default
        return out
    except (TypeError, ValueError):
        return default


def _normalize_return(raw: float) -> float:
    """Accept either ratio (0.0749) or percent (7.49)."""
    if abs(raw) > 1.0:
        return raw / 100.0
    return raw


def _normalize_win_rate(raw: float) -> float:
    if abs(raw) > 1.0:
        return max(0.0, min(1.0, raw / 100.0))
    return max(0.0, min(1.0, raw))


def _normalize_drawdown(raw: float) -> float:
    if abs(raw) > 1.0:
        raw = raw / 100.0
    if raw > 0:
        raw = -raw
    return raw


def _parse_result(raw: Any) -> dict[str, Any]:
    if isinstance(raw, dict):
        return raw
    text = str(raw or "").strip()
    if not text:
        return {}
    try:
        data = json.loads(text)
    except (TypeError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def canonical_strategy_name(name: str) -> str:
    text = str(name or "").strip()
    text = re.sub(r"^\[UNIFIED-[^\]]+\]\s*", "", text)
    text = re.sub(r"^\[(?:AUTO-BT\d*|PR14-BT|FIX-BT)\]\s*", "", text, flags=re.I)
    return text.strip()


def family_for(name: str) -> str:
    for label, pattern in FAMILY_RULES:
        if pattern.search(canonical_strategy_name(name)):
            return label
    return "Other"


def score_metrics(
    *,
    total_return: float,
    sharpe: float,
    max_drawdown: float,
    profit_factor: float,
    total_trades: int,
    win_rate: float = 0.0,
    strategy_name: str = "",
    **extra: Any,
) -> dict[str, Any]:
    total_return = _normalize_return(_as_float(total_return))
    sharpe = _as_float(sharpe)
    drawdown = _normalize_drawdown(_as_float(max_drawdown))
    profit_factor = _as_float(profit_factor)
    trades = int(_as_float(total_trades))
    win_rate = _normalize_win_rate(_as_float(win_rate))

    ret_score = max(0.0, min(100.0, (total_return + 0.20) / 0.40 * 100.0))
    sharpe_score = max(0.0, min(100.0, (sharpe + 2.0) / 5.0 * 100.0))
    dd_score = max(0.0, min(100.0, (drawdown + 0.40) / 0.40 * 100.0))
    pf_score = max(0.0, min(100.0, (profit_factor / 5.0) * 100.0)) if profit_factor > 0 else 0.0
    traded_score = 100.0 if trades > 0 else 0.0

    score = (
        ret_score * WEIGHTS["return"]
        + sharpe_score * WEIGHTS["sharpe"]
        + dd_score * WEIGHTS["drawdown"]
        + pf_score * WEIGHTS["profit_factor"]
        + traded_score * WEIGHTS["traded"]
    )

    flag = "ok"
    if trades <= 0:
        flag = "no_trades"
        score *= 0.35
    elif abs(total_return) > 5.0 or abs(sharpe) > 20.0:
        flag = "extreme_outlier"
        score *= 0.25

    row = {
        "strategy_name": canonical_strategy_name(strategy_name),
        "total_return": total_return,
        "sharpe": sharpe,
        "max_drawdown": drawdown,
        "profit_factor": profit_factor,
        "win_rate": win_rate,
        "total_trades": trades,
        "score": round(score, 4),
        "flag": flag,
        "family": family_for(strategy_name),
    }
    row.update(extra)
    return row


def score_run_row(row: dict[str, Any]) -> dict[str, Any]:
    result = _parse_result(row.get("result_json") or row.get("result"))
    initial = _as_float(row.get("initial_capital"), 0.0)
    final = _as_float(result.get("finalEquity") or result.get("final_equity"), 0.0)
    if initial > 0 and final > 0:
        total_return = (final / initial) - 1.0
    else:
        total_return = _as_float(
            result.get("totalReturn", result.get("total_return", row.get("total_return")))
        )

    return score_metrics(
        total_return=total_return,
        sharpe=_as_float(result.get("sharpeRatio", result.get("sharpe", row.get("sharpe")))),
        max_drawdown=_as_float(
            result.get("maxDrawdown", result.get("max_drawdown", row.get("max_drawdown")))
        ),
        profit_factor=_as_float(
            result.get("profitFactor", result.get("profit_factor", row.get("profit_factor")))
        ),
        total_trades=int(
            _as_float(result.get("totalTrades", result.get("total_trades", row.get("total_trades"))))
        ),
        win_rate=_as_float(result.get("winRate", result.get("win_rate", row.get("win_rate")))),
        strategy_name=str(row.get("strategy_name") or ""),
        run_id=int(row.get("id") or 0) or None,
        source_id=int(row.get("source_id") or 0) or None,
        strategy_id=int(row.get("strategy_id") or 0) or None,
        market=str(row.get("market") or ""),
        symbol=str(row.get("symbol") or ""),
        timeframe=str(row.get("timeframe") or ""),
        start_date=str(row.get("start_date") or ""),
        end_date=str(row.get("end_date") or ""),
        created_at=str(row.get("created_at") or ""),
    )


def dedupe_best(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    best: dict[tuple[str, str], dict[str, Any]] = {}
    for row in rows:
        key = (str(row.get("strategy_name") or ""), str(row.get("timeframe") or ""))
        prev = best.get(key)
        if prev is None or float(row["score"]) > float(prev["score"]):
            best[key] = row
    return sorted(
        best.values(),
        key=lambda item: (-float(item["score"]), int(item.get("run_id") or 0)),
    )


def load_user_runs(
    *,
    user_id: int,
    market: str = "",
    timeframe: str = "",
    tag: str = "",
    limit: int = 500,
) -> list[dict[str, Any]]:
    clauses = ["user_id = ?", "status = 'success'"]
    params: list[Any] = [int(user_id)]
    if market:
        clauses.append("market = ?")
        params.append(str(market))
    if timeframe:
        clauses.append("timeframe = ?")
        params.append(str(timeframe))
    if tag:
        clauses.append("strategy_name LIKE ?")
        params.append(f"%[{tag}]%")
    where = " AND ".join(clauses)
    sql = f"""
        SELECT id, user_id, strategy_id, source_id, strategy_name, market, symbol, timeframe,
               start_date, end_date, initial_capital, result_json, created_at
        FROM qd_backtest_runs
        WHERE {where}
        ORDER BY id DESC
        LIMIT ?
    """
    params.append(max(1, min(int(limit), 2000)))
    with get_db_connection() as db:
        cur = db.cursor()
        cur.execute(sql, tuple(params))
        rows = cur.fetchall() or []
        cur.close()
    return [dict(row) for row in rows]


def build_ranking(
    *,
    user_id: int,
    market: str = "",
    timeframe: str = "",
    tag: str = "",
    limit: int = 100,
    dedupe: bool = True,
) -> dict[str, Any]:
    raw_rows = load_user_runs(
        user_id=user_id,
        market=market,
        timeframe=timeframe,
        tag=tag,
        limit=max(limit * 5, 200),
    )
    scored = [score_run_row(row) for row in raw_rows]
    ranked = dedupe_best(scored) if dedupe else sorted(
        scored, key=lambda item: (-float(item["score"]), int(item.get("run_id") or 0))
    )
    ranked = ranked[: max(1, min(int(limit), 500))]
    for index, row in enumerate(ranked, start=1):
        row["rank"] = index
    return {
        "weights": dict(WEIGHTS),
        "count": len(ranked),
        "items": ranked,
    }
