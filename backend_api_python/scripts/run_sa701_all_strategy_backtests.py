#!/usr/bin/env python3
"""Batch-backtest all Strategy V2 templates on CNFutures:SA701 for 1m and 1d."""
from __future__ import annotations

import argparse
import json
import math
import re
import traceback
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FuturesTimeout
from datetime import datetime
from pathlib import Path
from typing import Any

SYMBOL = "CNFutures:SA701"
OPTION = "CNFuturesOptions:SA701-C-1000"
USER_ID = 1

FUNDAMENTAL_KEYS = {
    "strategy_v2_market_cap_barbell",
    "strategy_v2_quality_growth",
}


def force_sa701(code: str, *, timeframe: str, is_pack: bool) -> str:
    out = code
    # Packs aggregate 1m→30m and need enough coarse bars for MA100/Donchian.
    if is_pack and timeframe == "1m":
        warmup, hist_n = 300, 3600
    elif timeframe == "1m":
        warmup, hist_n = 200, 2000
    else:
        warmup, hist_n = 20, 120

    out = re.sub(r'g\.symbol\s*=\s*["\'][^"\']+["\']', f'g.symbol = "{SYMBOL}"', out)
    out = re.sub(r'g\.futures\s*=\s*["\'][^"\']+["\']', f'g.futures = "{SYMBOL}"', out)
    out = re.sub(r'g\.option\s*=\s*["\'][^"\']+["\']', f'g.option = "{OPTION}"', out)
    out = re.sub(r'g\.universe\s*=\s*\[[^\]]*\]', f'g.universe = ["{SYMBOL}"]', out, flags=re.S)

    universe = f'["{SYMBOL}", "{OPTION}"]' if is_pack else f'["{SYMBOL}"]'
    out = re.sub(
        r'context\.set_universe\(\[[^\]]*\]\)',
        f'context.set_universe({universe})',
        out,
        flags=re.S,
    )
    out = re.sub(r'context\.set_benchmark\([^\)]*\)', f'context.set_benchmark("{SYMBOL}")', out)
    out = re.sub(
        r'context\.subscribe\(\s*frequency\s*=\s*["\'][^"\']+["\']\s*\)',
        f'context.subscribe(frequency="{timeframe}")',
        out,
    )
    out = re.sub(r'frequency\s*=\s*["\'][^"\']+["\']', f'frequency="{timeframe}"', out)
    out = re.sub(r'context\.set_warmup\(\s*\d+\s*\)', f'context.set_warmup({warmup})', out)
    out = re.sub(r'^\s*context\.allow_leverage\([^\)]*\)\s*$', '', out, flags=re.M)
    # Rewrite timeframe arg for both literal and expression lookbacks:
    # get_history(120, "1d", ...) and get_history(ma_period + 2, "1d", ...)
    out = re.sub(
        r'get_history\(\s*([^,]+)\s*,\s*["\'][^"\']+["\']',
        lambda m: (
            f'get_history({hist_n}, "{timeframe}"'
            if re.fullmatch(r"\d+", m.group(1).strip())
            else f'get_history({m.group(1).strip()}, "{timeframe}"'
        ),
        out,
    )
    out = re.sub(
        r'["\'](?:USStock|CNStock|Crypto|CNFutures):(?!Options)[^"\']+["\']',
        f'"{SYMBOL}"',
        out,
    )
    out = re.sub(r'["\']CNFuturesOptions:[^"\']+["\']', f'"{OPTION}"', out)

    if is_pack:
        # Daily: treat bars as already coarse. Minute: lower gates so ~3600/30 bars can trade.
        if timeframe == "1d":
            out = re.sub(
                r"def _agg30\(bars_1m\):.*?return \(opens, highs, lows, closes, volumes\)",
                (
                    "def _agg30(bars_1m):\n"
                    "    opens = list(bars_1m['open'])\n"
                    "    highs = list(bars_1m['high'])\n"
                    "    lows = list(bars_1m['low'])\n"
                    "    closes = list(bars_1m['close'])\n"
                    "    volumes = list(bars_1m['volume'])\n"
                    "    return (opens, highs, lows, closes, volumes)"
                ),
                out,
                count=1,
                flags=re.S,
            )
            min_bars = 20
        else:
            min_bars = 50
        out = re.sub(r"len\(closes\)\s*<\s*\d+", f"len(closes) < {min_bars}", out)
        out = re.sub(r"len\(c30\)\s*<\s*\d+", f"len(c30) < {min_bars}", out)
        # Many pack variants need MA100 / Donchian55 — clamp those periods for short windows.
        out = re.sub(
            r"_rolling_mean\(closes,\s*100\)",
            "_rolling_mean(closes, 40)",
            out,
        )
        out = re.sub(
            r"_rolling_mean\(closes,\s*60\)",
            "_rolling_mean(closes, 30)",
            out,
        )
        out = re.sub(
            r"_rolling_max\(highs,\s*55\)",
            "_rolling_max(highs, 30)",
            out,
        )
        out = re.sub(
            r"_rolling_min\(lows,\s*55\)",
            "_rolling_min(lows, 30)",
            out,
        )
        out = re.sub(
            r"_rolling_min\(lows,\s*20\)",
            "_rolling_min(lows, 15)",
            out,
        )
    return out


def default_params(template_key: str, timeframe: str, variant: int | None) -> dict[str, Any]:
    params: dict[str, Any] = {}
    if variant is not None:
        params["variant"] = variant
        params["target_pct"] = 0.95
        params["allow_short"] = True
    if timeframe != "1d":
        return params
    if "single_ma" in template_key:
        params["ma_period"] = 10
    if "double_ma" in template_key:
        params["fast_period"] = 5
        params["slow_period"] = 20
    if "turtle" in template_key:
        params["entry_period"] = 10
        params["exit_period"] = 5
    if "supertrend" in template_key:
        params["atr_period"] = 7
    if "bullish_three" in template_key:
        params["short_period"] = 3
        params["mid_period"] = 5
        params["long_period"] = 10
        params["trend_period"] = 20
    return params


def as_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None or value == "":
            return default
        out = float(value)
        if math.isnan(out) or math.isinf(out):
            return default
        return out
    except (TypeError, ValueError):
        return default


def normalize_return(raw: float) -> float:
    if abs(raw) > 2.0:
        return raw / 100.0
    return raw


def normalize_drawdown(raw: float) -> float:
    dd = raw
    if abs(dd) > 2.0:
        dd = dd / 100.0
    if dd > 0:
        dd = -abs(dd)
    return dd


def score_row(row: dict[str, Any]) -> dict[str, Any]:
    total_return = normalize_return(as_float(row.get("total_return")))
    sharpe = as_float(row.get("sharpe"))
    drawdown = normalize_drawdown(as_float(row.get("max_drawdown")))
    profit_factor = as_float(row.get("profit_factor"), 0.0)
    trades = int(as_float(row.get("total_trades")))

    ret_score = max(0.0, min(100.0, (total_return + 0.20) / 0.40 * 100.0))
    sharpe_score = max(0.0, min(100.0, (sharpe + 2.0) / 5.0 * 100.0))
    dd_score = max(0.0, min(100.0, (drawdown + 0.40) / 0.40 * 100.0))
    pf_score = max(0.0, min(100.0, (min(max(profit_factor, 0.0), 5.0) / 5.0) * 100.0))
    traded_score = 100.0 if trades > 0 else 0.0
    score = (
        ret_score * 0.40
        + sharpe_score * 0.25
        + dd_score * 0.20
        + pf_score * 0.10
        + traded_score * 0.05
    )

    flag = str(row.get("flag") or "ok")
    if row.get("status") == "skipped":
        flag = "not_applicable"
        score = 0.0
    elif trades <= 0 and row.get("status") == "ok":
        flag = "no_trades"
        score *= 0.35
    elif abs(total_return) > 5.0 or abs(sharpe) > 20.0:
        flag = "extreme_outlier"
        score *= 0.25

    out = dict(row)
    out.update(
        {
            "total_return": total_return,
            "sharpe": sharpe,
            "max_drawdown": drawdown,
            "profit_factor": profit_factor,
            "total_trades": trades,
            "score": round(score, 3),
            "flag": flag,
        }
    )
    return out


def run_one(
    *,
    service: Any,
    template: dict[str, Any],
    timeframe: str,
    variant: int | None,
    start: datetime,
    end: datetime,
    tag: str,
    timeout_sec: int,
    capital: float,
    commission: float,
    slippage: float,
) -> dict[str, Any]:
    key = template["template_key"]
    title = template["title"]
    is_pack = bool(template.get("is_pack"))
    name = f"[{tag}] {title}" + (f" · Variant {variant + 1}" if variant is not None else "")

    if key in FUNDAMENTAL_KEYS:
        return score_row(
            {
                "template_key": key,
                "title": title,
                "timeframe": timeframe,
                "variant": variant,
                "strategy_name": name,
                "status": "skipped",
                "error": "requires equity fundamentals; not applicable on single SA701 futures",
                "total_return": 0,
                "sharpe": 0,
                "max_drawdown": 0,
                "profit_factor": 0,
                "total_trades": 0,
                "family": "Classic",
                "flag": "not_applicable",
            }
        )

    code = force_sa701(template["code"], timeframe=timeframe, is_pack=is_pack)
    params = default_params(key, timeframe, variant)

    def _call():
        return service.run(
            user_id=USER_ID,
            code=code,
            start_date=start,
            end_date=end,
            initial_capital=capital,
            commission=commission,
            slippage=slippage,
            params=params or None,
            persist=True,
            strategy_name=name,
        )

    try:
        with ThreadPoolExecutor(max_workers=1) as pool:
            run_id, result = pool.submit(_call).result(timeout=timeout_sec)
        return score_row(
            {
                "template_key": key,
                "title": title,
                "timeframe": timeframe,
                "variant": variant,
                "strategy_name": name,
                "run_id": run_id,
                "status": "ok",
                "total_return": result.get("totalReturn"),
                "sharpe": result.get("sharpeRatio"),
                "max_drawdown": result.get("maxDrawdown"),
                "win_rate": result.get("winRate"),
                "profit_factor": result.get("profitFactor"),
                "total_trades": result.get("totalTrades"),
                "final_equity": result.get("finalEquity"),
                "family": "Pack" if is_pack else "Classic",
            }
        )
    except FuturesTimeout:
        return score_row(
            {
                "template_key": key,
                "title": title,
                "timeframe": timeframe,
                "variant": variant,
                "strategy_name": name,
                "status": "timeout",
                "error": f"exceeded {timeout_sec}s",
                "total_return": 0,
                "sharpe": 0,
                "max_drawdown": 0,
                "profit_factor": 0,
                "total_trades": 0,
                "family": "Pack" if is_pack else "Classic",
            }
        )
    except Exception as exc:  # noqa: BLE001
        return score_row(
            {
                "template_key": key,
                "title": title,
                "timeframe": timeframe,
                "variant": variant,
                "strategy_name": name,
                "status": "error",
                "error": f"{type(exc).__name__}: {exc}",
                "trace": traceback.format_exc()[-800:],
                "total_return": 0,
                "sharpe": 0,
                "max_drawdown": 0,
                "profit_factor": 0,
                "total_trades": 0,
                "family": "Pack" if is_pack else "Classic",
            }
        )


def pct(value: float) -> str:
    return f"{value * 100:.2f}%"


def render_markdown(rows: list[dict[str, Any]], *, tag: str, timeframe: str) -> str:
    traded = [r for r in rows if int(r.get("total_trades") or 0) > 0 and r.get("status") == "ok"]
    positive = [r for r in traded if float(r.get("total_return") or 0) > 0]
    ranked = sorted(rows, key=lambda r: (-float(r.get("score") or 0), str(r.get("title") or "")))
    lines = [
        f"# SA701 {timeframe} 全策略回测排名",
        "",
        f"- 批次 tag：`{tag}`",
        f"- 标的：`{SYMBOL}`（期权腿 `{OPTION}`，仅 Pack）",
        f"- 样本数：{len(rows)}；有成交：{len(traded)}；正收益：{len(positive)}",
        "- 评分：收益40% + Sharpe25% + 回撤20% + 盈亏比10% + 有成交5%；零成交×0.35；极端异常×0.25",
        "- 基本面多因子美股策略在单品种期货上标记为 not_applicable",
        "",
        "## Top 15",
        "",
        "| 排名 | 得分 | 策略 | 收益 | 回撤 | Sharpe | 成交 | 标记 |",
        "|------|------|------|------|------|--------|------|------|",
    ]
    for i, row in enumerate(ranked[:15], 1):
        suffix = f" · V{int(row['variant']) + 1}" if row.get("variant") is not None else ""
        lines.append(
            f"| {i} | {float(row.get('score') or 0):.1f} | {row.get('title')}{suffix} "
            f"| {pct(float(row.get('total_return') or 0))} | {pct(float(row.get('max_drawdown') or 0))} "
            f"| {float(row.get('sharpe') or 0):.2f} | {int(row.get('total_trades') or 0)} "
            f"| {row.get('flag')}/{row.get('status')} |"
        )
    lines.extend(["", "## 有成交排名", ""])
    traded_ranked = sorted(traded, key=lambda r: (-float(r.get("score") or 0), str(r.get("title") or "")))
    lines += [
        "| 排名 | 得分 | 策略 | 收益 | 回撤 | Sharpe | 盈亏比 | 成交 |",
        "|------|------|------|------|------|--------|--------|------|",
    ]
    for i, row in enumerate(traded_ranked[:50], 1):
        suffix = f" · V{int(row['variant']) + 1}" if row.get("variant") is not None else ""
        lines.append(
            f"| {i} | {float(row.get('score') or 0):.1f} | {row.get('title')}{suffix} "
            f"| {pct(float(row.get('total_return') or 0))} | {pct(float(row.get('max_drawdown') or 0))} "
            f"| {float(row.get('sharpe') or 0):.2f} | {float(row.get('profit_factor') or 0):.2f} "
            f"| {int(row.get('total_trades') or 0)} |"
        )
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--templates-json", required=True)
    parser.add_argument("--timeframes", default="1m,1d")
    parser.add_argument("--start", default="2026-06-01")
    parser.add_argument("--end", default="2026-08-19")
    parser.add_argument("--tag-prefix", default="SA701")
    parser.add_argument("--max-variants", type=int, default=10)
    parser.add_argument("--classics-only", action="store_true")
    parser.add_argument("--packs-only", action="store_true")
    parser.add_argument("--timeout-sec", type=int, default=240)
    parser.add_argument("--capital", type=float, default=100_000.0)
    parser.add_argument("--commission", type=float, default=0.0003)
    parser.add_argument("--slippage", type=float, default=0.0002)
    parser.add_argument("--outdir", default="/tmp/sa701_batch")
    args = parser.parse_args(argv)

    templates = json.loads(Path(args.templates_json).read_text(encoding="utf-8"))
    if args.classics_only:
        templates = [t for t in templates if not t.get("is_pack")]
    if args.packs_only:
        templates = [t for t in templates if t.get("is_pack")]

    start = datetime.strptime(args.start, "%Y-%m-%d")
    end = datetime.strptime(args.end, "%Y-%m-%d").replace(hour=23, minute=59, second=59)
    timeframes = [x.strip() for x in args.timeframes.split(",") if x.strip()]
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    from app.services.strategy_v2.service import StrategyV2BacktestService

    service = StrategyV2BacktestService()
    summary: dict[str, Any] = {"started_at": datetime.utcnow().isoformat() + "Z", "by_tf": {}}

    for tf in timeframes:
        tag = f"{args.tag_prefix}-{tf.upper()}-{start.strftime('%Y%m%d')}"
        rows: list[dict[str, Any]] = []
        print(
            json.dumps(
                {"event": "tf_start", "timeframe": tf, "tag": tag, "templates": len(templates)},
                ensure_ascii=False,
            ),
            flush=True,
        )
        for template in templates:
            variants: list[int | None]
            if template.get("is_pack"):
                variants = list(range(0, max(1, args.max_variants)))
            else:
                variants = [None]
            for variant in variants:
                row = run_one(
                    service=service,
                    template=template,
                    timeframe=tf,
                    variant=variant,
                    start=start,
                    end=end,
                    tag=tag,
                    timeout_sec=args.timeout_sec,
                    capital=args.capital,
                    commission=args.commission,
                    slippage=args.slippage,
                )
                rows.append(row)
                print(
                    json.dumps(
                        {
                            "event": "row",
                            **{
                                k: row.get(k)
                                for k in (
                                    "template_key",
                                    "title",
                                    "timeframe",
                                    "variant",
                                    "status",
                                    "score",
                                    "total_return",
                                    "sharpe",
                                    "max_drawdown",
                                    "total_trades",
                                    "run_id",
                                    "error",
                                    "flag",
                                )
                            },
                        },
                        ensure_ascii=False,
                    ),
                    flush=True,
                )

        rows_sorted = sorted(rows, key=lambda r: (-float(r.get("score") or 0), str(r.get("title") or "")))
        payload = {
            "tag": tag,
            "symbol": SYMBOL,
            "timeframe": tf,
            "start": args.start,
            "end": args.end,
            "count": len(rows_sorted),
            "traded": sum(1 for r in rows_sorted if int(r.get("total_trades") or 0) > 0),
            "rows": rows_sorted,
        }
        json_path = outdir / f"sa701_{tf}_ranking.json"
        md_path = outdir / f"sa701_{tf}_ranking.md"
        json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        md_path.write_text(render_markdown(rows_sorted, tag=tag, timeframe=tf), encoding="utf-8")
        summary["by_tf"][tf] = {
            "tag": tag,
            "json": str(json_path),
            "md": str(md_path),
            "count": len(rows_sorted),
            "traded": payload["traded"],
            "top5": rows_sorted[:5],
        }

    summary["finished_at"] = datetime.utcnow().isoformat() + "Z"
    summary_path = outdir / "sa701_summary.json"
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    print(json.dumps({"event": "done", "summary": str(summary_path)}, ensure_ascii=False), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
