#!/usr/bin/env python3
"""Build a comparative backtest ranking report from ``qd_backtest_runs``.

Scoring (same weights as the production ranking note):
  return 40% + Sharpe 25% + drawdown 20% + profit factor 10% + traded 5%
  extreme outliers ×0.25, zero-trade ×0.35

Example::

    PYTHONPATH=. python scripts/build_backtest_ranking_report.py \\
      --tag UNIFIED-20260820 \\
      --md docs/BACKTEST_RANKING_REPORT.md \\
      --json reports/backtest_ranking_summary.json
"""

from __future__ import annotations

import argparse
import json
import math
import re
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
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
    ("Options Vol Pack", re.compile(r"Options Volatility Pack", re.I)),
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
    """Historical rows sometimes store percent (7.49) vs ratio (0.0749)."""
    if abs(raw) > 2.5:
        return raw / 100.0
    return raw


def _normalize_drawdown(raw: float) -> float:
    # Prefer negative fraction; convert percent magnitudes.
    if abs(raw) > 2.5:
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


def _family_for(name: str) -> str:
    for label, pattern in FAMILY_RULES:
        if pattern.search(name or ""):
            return label
    return "Other"


def _score_row(row: dict[str, Any]) -> dict[str, Any]:
    total_return = _normalize_return(_as_float(row.get("total_return")))
    sharpe = _as_float(row.get("sharpe"))
    drawdown = _normalize_drawdown(_as_float(row.get("max_drawdown")))
    profit_factor = _as_float(row.get("profit_factor"))
    trades = int(_as_float(row.get("total_trades")))

    # Component scores in 0..100
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

    row = dict(row)
    row.update(
        {
            "total_return": total_return,
            "sharpe": sharpe,
            "max_drawdown": drawdown,
            "profit_factor": profit_factor,
            "total_trades": trades,
            "score": round(score, 4),
            "flag": flag,
            "family": _family_for(str(row.get("strategy_name") or "")),
        }
    )
    return row


def _dedupe(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    best: dict[tuple[str, str], dict[str, Any]] = {}
    for row in rows:
        key = (str(row.get("strategy_name") or ""), str(row.get("timeframe") or ""))
        prev = best.get(key)
        if prev is None or float(row["score"]) > float(prev["score"]):
            best[key] = row
    return sorted(best.values(), key=lambda r: (-float(r["score"]), int(r["id"])))


def load_runs(*, tag: str = "", min_id: int = 0, max_id: int = 0) -> list[dict[str, Any]]:
    clauses = ["status = 'success'"]
    params: list[Any] = []
    if tag:
        clauses.append("strategy_name LIKE ?")
        params.append(f"%[{tag}]%")
    if min_id > 0:
        clauses.append("id >= ?")
        params.append(int(min_id))
    if max_id > 0:
        clauses.append("id <= ?")
        params.append(int(max_id))
    where = " AND ".join(clauses)
    sql = f"""
        SELECT id, strategy_name, market, symbol, timeframe, start_date, end_date,
               result_json, created_at
        FROM qd_backtest_runs
        WHERE {where}
        ORDER BY id ASC
    """
    with get_db_connection() as db:
        cur = db.cursor()
        cur.execute(sql, tuple(params))
        raw_rows = cur.fetchall() or []
        cur.close()

    rows: list[dict[str, Any]] = []
    for raw in raw_rows:
        result = _parse_result(raw.get("result_json"))
        metrics = result.get("metrics") if isinstance(result.get("metrics"), dict) else result
        row = {
            "id": int(raw.get("id") or 0),
            "strategy_name": str(raw.get("strategy_name") or ""),
            "market": str(raw.get("market") or ""),
            "symbol": str(raw.get("symbol") or ""),
            "timeframe": str(raw.get("timeframe") or ""),
            "start_date": str(raw.get("start_date") or ""),
            "end_date": str(raw.get("end_date") or ""),
            "created_at": str(raw.get("created_at") or ""),
            "total_return": metrics.get("totalReturn", metrics.get("total_return")),
            "annual_return": metrics.get("annualReturn", metrics.get("annualizedReturn")),
            "sharpe": metrics.get("sharpeRatio", metrics.get("sharpe")),
            "max_drawdown": metrics.get("maxDrawdown", metrics.get("max_drawdown")),
            "win_rate": metrics.get("winRate", metrics.get("win_rate")),
            "profit_factor": metrics.get("profitFactor", metrics.get("profit_factor")),
            "total_trades": metrics.get("totalTrades", metrics.get("total_trades")),
        }
        rows.append(_score_row(row))
    return rows


def _pct(value: float) -> str:
    return f"{value * 100:.2f}%"


def _md_escape(text: str) -> str:
    return str(text or "").replace("|", "\\|")


def render_markdown(rows: list[dict[str, Any]], *, deduped: list[dict[str, Any]], title_note: str) -> str:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    traded = [r for r in deduped if int(r["total_trades"]) > 0]
    zero = [r for r in deduped if int(r["total_trades"]) <= 0]
    positive = [r for r in traded if float(r["total_return"]) > 0]
    top = deduped[0] if deduped else None

    families: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in deduped:
        families[str(row["family"])].append(row)

    family_rows = []
    for family, items in families.items():
        traded_n = sum(1 for i in items if int(i["total_trades"]) > 0)
        avg_score = sum(float(i["score"]) for i in items) / max(1, len(items))
        # average return among traded only when available
        traded_items = [i for i in items if int(i["total_trades"]) > 0]
        avg_ret = (
            sum(float(i["total_return"]) for i in traded_items) / len(traded_items)
            if traded_items
            else 0.0
        )
        total_trades = sum(int(i["total_trades"]) for i in items)
        best = max(items, key=lambda i: float(i["score"]))
        family_rows.append(
            {
                "family": family,
                "n": len(items),
                "traded": traded_n,
                "avg_score": avg_score,
                "avg_ret": avg_ret,
                "total_trades": total_trades,
                "best": best,
            }
        )
    family_rows.sort(key=lambda r: (-float(r["avg_score"]), r["family"]))

    lines: list[str] = []
    lines.append("# QuantDinger 回测综合排名与分析报告")
    lines.append("")
    lines.append(f"- 生成时间：{now}")
    lines.append(f"- 数据来源：`qd_backtest_runs`（**{len(rows)}** 条）")
    lines.append(f"- 去重后策略样本：**{len(deduped)}**（同名+同周期保留最高分）")
    lines.append(
        "- 评分：收益 40% + Sharpe 25% + 回撤 20% + 盈亏比 10% + 有成交 5%；"
        "极端异常值×0.25，零成交×0.35"
    )
    lines.append("- 指标已统一为小数收益率（自动识别历史百分比口径）")
    if title_note:
        lines.append(f"- 过滤条件：{title_note}")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## 1. 执行摘要")
    lines.append("")
    lines.append("| 项目 | 数值 |")
    lines.append("|------|------|")
    lines.append(f"| 回测总数 | {len(rows)} |")
    lines.append(f"| 去重策略数 | {len(deduped)} |")
    lines.append(f"| 有成交（去重） | {len(traded)} |")
    lines.append(f"| 零成交（去重） | {len(zero)} |")
    lines.append(f"| 策略族 | {len(family_rows)} |")
    if top:
        lines.append(
            f"| 综合第 1（去重） | **{_md_escape(top['strategy_name'])}**"
            f"（#{top['id']}，得分 {top['score']:.2f}，收益 {_pct(float(top['total_return']))}） |"
        )
    lines.append(f"| 有成交且正收益 | {len(positive)} / {max(1, len(traded))} |")
    lines.append("")
    lines.append("### 核心结论")
    lines.append("")
    if traded:
        best_traded = max(traded, key=lambda r: float(r["score"]))
        lines.append(
            f"1. **可交易样本榜首**：`{_md_escape(best_traded['strategy_name'])}`"
            f"（得分 {best_traded['score']:.2f}，收益 {_pct(float(best_traded['total_return']))}，"
            f"回撤 {_pct(float(best_traded['max_drawdown']))}，Sharpe {float(best_traded['sharpe']):.2f}）。"
        )
    else:
        lines.append("1. 本批样本**无有成交**；排名主要反映风控惩罚与数据约束，而非策略 alpha。")
    if family_rows:
        top_fam = family_rows[0]
        lines.append(
            f"2. **策略族均值最高**：`{top_fam['family']}`"
            f"（平均得分 {top_fam['avg_score']:.1f}，有成交 {top_fam['traded']}/{top_fam['n']}）。"
        )
    zero_packs = [f for f in family_rows if f["traded"] == 0 and "Pack" in f["family"]]
    if zero_packs:
        names = ", ".join(f["family"] for f in zero_packs[:5])
        lines.append(
            f"3. **零成交 Pack**：{names}"
            " — 回测链路成功但未触发交易，通常是分钟线深度/合约符号不足（如 `SA701`）。"
        )
    outliers = [r for r in deduped if r["flag"] == "extreme_outlier"]
    if outliers:
        lines.append(
            f"4. **极端异常值 {len(outliers)} 个**已降权，不作为可信 alpha 依据。"
        )
    lines.append("")
    lines.append("## 2. 综合排名（去重 Top 15）")
    lines.append("")
    lines.append(
        "| 排名 | 得分 | 策略 | 族 | Run | 周期 | 总收益 | 最大回撤 | Sharpe | 胜率 | 成交 | 标记 |"
    )
    lines.append(
        "|------|------|------|----|-----|------|--------|----------|--------|------|------|------|"
    )
    for idx, row in enumerate(deduped[:15], start=1):
        lines.append(
            "| {rank} | {score:.1f} | {name} | {family} | #{rid} | {tf} | {ret} | {dd} | {sharpe:.2f} | {wr} | {trades} | {flag} |".format(
                rank=idx,
                score=float(row["score"]),
                name=_md_escape(row["strategy_name"]),
                family=row["family"],
                rid=row["id"],
                tf=row["timeframe"] or "-",
                ret=_pct(float(row["total_return"])),
                dd=_pct(float(row["max_drawdown"])),
                sharpe=float(row["sharpe"]),
                wr=_pct(_normalize_return(_as_float(row.get("win_rate")))),
                trades=int(row["total_trades"]),
                flag=row["flag"],
            )
        )
    lines.append("")
    lines.append("## 3. 有成交策略排名（去重）")
    lines.append("")
    if not traded:
        lines.append("_本批无有成交策略。_")
    else:
        lines.append("| 排名 | 得分 | 策略 | 族 | 总收益 | 回撤 | Sharpe | 盈亏比 | 成交 | Run |")
        lines.append("|------|------|------|----|--------|------|--------|--------|------|-----|")
        for idx, row in enumerate(sorted(traded, key=lambda r: -float(r["score"])), start=1):
            lines.append(
                "| {rank} | {score:.1f} | {name} | {family} | {ret} | {dd} | {sharpe:.2f} | {pf:.2f} | {trades} | #{rid} |".format(
                    rank=idx,
                    score=float(row["score"]),
                    name=_md_escape(row["strategy_name"]),
                    family=row["family"],
                    ret=_pct(float(row["total_return"])),
                    dd=_pct(float(row["max_drawdown"])),
                    sharpe=float(row["sharpe"]),
                    pf=float(row["profit_factor"]),
                    trades=int(row["total_trades"]),
                    rid=row["id"],
                )
            )
    lines.append("")
    lines.append("## 4. 策略族排行榜")
    lines.append("")
    lines.append("| 排名 | 策略族 | 策略数 | 有成交 | 平均得分 | 平均收益* | 总成交 | 族内最佳 |")
    lines.append("|------|--------|--------|--------|----------|-----------|--------|----------|")
    for idx, fam in enumerate(family_rows, start=1):
        best = fam["best"]
        lines.append(
            "| {rank} | {family} | {n} | {traded} | {avg:.1f} | {ret} | {trades} | {best} (#{rid}) |".format(
                rank=idx,
                family=fam["family"],
                n=fam["n"],
                traded=fam["traded"],
                avg=float(fam["avg_score"]),
                ret=_pct(float(fam["avg_ret"])),
                trades=fam["total_trades"],
                best=_md_escape(best["strategy_name"]),
                rid=best["id"],
            )
        )
    lines.append("")
    lines.append("\\*平均收益仅统计有成交样本。")
    lines.append("")
    lines.append("## 5. 方法说明与限制")
    lines.append("")
    lines.append("- 跨族不可直接比绝对收益：标的、周期、资金、费率可能不同。")
    lines.append("- 同策略重复回测时，总榜以去重结果为主；附录保留全量。")
    lines.append("- Pack 依赖国内期货分钟线与期权合约键；连续合约 `SA0` 与月份码 `SA701` 不是同一符号。")
    lines.append("")
    lines.append("## 附录 A：全量回测清单（按得分）")
    lines.append("")
    lines.append("| Run | 策略 | 族 | 标的 | 周期 | 收益 | Sharpe | 成交 | 得分 | 标记 |")
    lines.append("|-----|------|----|------|------|------|--------|------|------|------|")
    for row in sorted(rows, key=lambda r: (-float(r["score"]), int(r["id"]))):
        symbol = str(row.get("symbol") or "")
        if len(symbol) > 40:
            symbol = symbol[:39] + "…"
        lines.append(
            "| #{rid} | {name} | {family} | {symbol} | {tf} | {ret} | {sharpe:.2f} | {trades} | {score:.1f} | {flag} |".format(
                rid=row["id"],
                name=_md_escape(row["strategy_name"]),
                family=row["family"],
                symbol=_md_escape(symbol),
                tf=row["timeframe"] or "-",
                ret=_pct(float(row["total_return"])),
                sharpe=float(row["sharpe"]),
                trades=int(row["total_trades"]),
                score=float(row["score"]),
                flag=row["flag"],
            )
        )
    lines.append("")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tag", default="", help="Only runs whose strategy_name contains [TAG]")
    parser.add_argument("--min-id", type=int, default=0)
    parser.add_argument("--max-id", type=int, default=0)
    parser.add_argument("--md", default="docs/BACKTEST_RANKING_REPORT.md")
    parser.add_argument("--json", dest="json_path", default="reports/backtest_ranking_summary.json")
    args = parser.parse_args(argv)

    rows = load_runs(tag=args.tag, min_id=args.min_id, max_id=args.max_id)
    deduped = _dedupe(rows)
    note_parts = []
    if args.tag:
        note_parts.append(f"tag=`{args.tag}`")
    if args.min_id:
        note_parts.append(f"id>={args.min_id}")
    if args.max_id:
        note_parts.append(f"id<={args.max_id}")
    note = ", ".join(note_parts) if note_parts else "全部成功回测"

    md = render_markdown(rows, deduped=deduped, title_note=note)
    md_path = Path(args.md)
    md_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.write_text(md, encoding="utf-8")

    summary = {
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "filter": {"tag": args.tag, "minId": args.min_id, "maxId": args.max_id},
        "totalRuns": len(rows),
        "dedupedStrategies": len(deduped),
        "tradedStrategies": sum(1 for r in deduped if int(r["total_trades"]) > 0),
        "top": deduped[:20],
        "all": rows,
    }
    json_path = Path(args.json_path)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2, default=str), encoding="utf-8")

    print(
        json.dumps(
            {
                "status": "ok",
                "runs": len(rows),
                "deduped": len(deduped),
                "md": str(md_path),
                "json": str(json_path),
                "top": [
                    {
                        "id": r["id"],
                        "name": r["strategy_name"],
                        "score": r["score"],
                        "flag": r["flag"],
                    }
                    for r in deduped[:5]
                ],
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
