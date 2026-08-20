#!/usr/bin/env python3
"""Run a unified Strategy V2 backtest batch for every active template.

Classics run once with default params. Packs that declare a ``variant`` param
run variants 0..N (default 0..9). Results persist into ``qd_backtest_runs``.

Example::

    PYTHONPATH=. python scripts/run_unified_strategy_backtests.py \\
      --tag UNIFIED-20260820 \\
      --start 2026-06-01 --end 2026-08-18 \\
      --pack-start 2026-08-05 --pack-end 2026-08-18 \\
      -o /tmp/unified_backtests.json
"""

from __future__ import annotations

import argparse
import json
import sys
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeout
from datetime import datetime
from typing import Any

from app.services.script_source import get_script_source_service
from app.services.strategy_v2 import StrategyV2BacktestService

USER_ID = 1
DEFAULT_TIMEOUT_SEC = 300


def compose_strategy_display_name(
    *,
    name: str = "",
    template_title: str = "",
    template_key: str = "",
    params: dict[str, Any] | None = None,
    metadata: dict[str, Any] | None = None,
) -> str:
    """Local label helper so the runner can run from a writable hotfix path."""
    base = str(name or template_title or "").strip()
    if not base and template_key:
        base = template_key.removeprefix("strategy_v2_").replace("_", " ").strip().title()
    if not base:
        base = "Strategy"
    if not params or params.get("variant") is None:
        return base
    try:
        index = int(params["variant"])
    except (TypeError, ValueError):
        return f"{base} · {params['variant']}"
    labels = (metadata or {}).get("variant_labels")
    if isinstance(labels, list) and 0 <= index < len(labels) and str(labels[index] or "").strip():
        variant_text = str(labels[index]).strip()
    else:
        variant_text = f"Variant {index + 1}"
    return f"{base} · {variant_text}"


def _parse_dt(raw: str) -> datetime:
    text = str(raw or "").strip()
    if not text:
        raise ValueError("empty datetime")
    if "T" in text:
        return datetime.fromisoformat(text.replace("Z", ""))
    if len(text) == 10:
        return datetime.strptime(text, "%Y-%m-%d")
    return datetime.strptime(text, "%Y-%m-%d %H:%M:%S")


def _iter_param_specs(param_schema: Any) -> list[dict[str, Any]]:
    """Normalize template param schemas (list form or JSON-Schema properties)."""
    if isinstance(param_schema, list):
        return [item for item in param_schema if isinstance(item, dict) and item.get("name")]
    if not isinstance(param_schema, dict):
        return []
    if isinstance(param_schema.get("params"), list):
        return [item for item in param_schema["params"] if isinstance(item, dict) and item.get("name")]
    props = param_schema.get("properties")
    if isinstance(props, dict):
        out: list[dict[str, Any]] = []
        for name, spec in props.items():
            if not isinstance(spec, dict):
                continue
            item = dict(spec)
            item.setdefault("name", name)
            if "maximum" in item and "max" not in item:
                item["max"] = item["maximum"]
            if "minimum" in item and "min" not in item:
                item["min"] = item["minimum"]
            out.append(item)
        return out
    return []


def _has_variant_param(param_schema: Any) -> bool:
    return any(str(item.get("name") or "") == "variant" for item in _iter_param_specs(param_schema))


def _variant_range(param_schema: Any, *, max_variants: int) -> range:
    variant = next((item for item in _iter_param_specs(param_schema) if str(item.get("name") or "") == "variant"), None)
    if not isinstance(variant, dict):
        return range(0, max_variants)
    maximum = variant.get("max", variant.get("maximum"))
    try:
        hi = int(maximum) + 1 if maximum is not None else max_variants
    except (TypeError, ValueError):
        hi = max_variants
    return range(0, min(hi, max_variants))


def _default_params(param_schema: Any, *, variant: int | None) -> dict[str, Any]:
    params: dict[str, Any] = {}
    for spec in _iter_param_specs(param_schema):
        name = str(spec.get("name") or "").strip()
        if not name:
            continue
        if "default" in spec:
            params[name] = spec["default"]
    if variant is not None:
        params["variant"] = variant
        params.setdefault("target_pct", 0.95)
        params.setdefault("allow_short", True)
    return params


def _is_pack(template_key: str, param_schema: Any) -> bool:
    key = str(template_key or "")
    return key.endswith("_pack") or _has_variant_param(param_schema)


def _run_one(
    *,
    service: StrategyV2BacktestService,
    template: dict[str, Any],
    params: dict[str, Any],
    start: datetime,
    end: datetime,
    tag: str,
    timeout_sec: int,
    capital: float,
    commission: float,
    slippage: float,
) -> dict[str, Any]:
    code = str(template.get("code") or "")
    title = str(template.get("title") or template.get("template_key") or "Strategy")
    key = str(template.get("template_key") or "")
    metadata = template.get("metadata") if isinstance(template.get("metadata"), dict) else {}
    display = compose_strategy_display_name(
        name=title,
        template_title=title,
        template_key=key,
        params=params,
        metadata=metadata,
    )
    strategy_name = f"[{tag}] {display}" if tag else display

    def _call() -> tuple[int | None, dict[str, Any]]:
        return service.run(
            user_id=USER_ID,
            code=code,
            start_date=start,
            end_date=end,
            initial_capital=capital,
            commission=commission,
            slippage=slippage,
            params=params,
            persist=True,
            strategy_name=strategy_name,
        )

    try:
        with ThreadPoolExecutor(max_workers=1) as pool:
            fut = pool.submit(_call)
            run_id, result = fut.result(timeout=timeout_sec)
        metrics = result.get("metrics") if isinstance(result.get("metrics"), dict) else result
        return {
            "template_key": key,
            "strategy_name": strategy_name,
            "params": params,
            "runId": run_id,
            "status": "ok",
            "totalReturn": metrics.get("totalReturn", metrics.get("total_return")),
            "sharpeRatio": metrics.get("sharpeRatio"),
            "maxDrawdown": metrics.get("maxDrawdown"),
            "totalTrades": result.get("totalTrades", metrics.get("totalTrades")),
        }
    except FuturesTimeout:
        return {
            "template_key": key,
            "strategy_name": strategy_name,
            "params": params,
            "status": "timeout",
            "error": f"exceeded {timeout_sec}s",
        }
    except Exception as exc:  # noqa: BLE001 - batch runner must keep going
        return {
            "template_key": key,
            "strategy_name": strategy_name,
            "params": params,
            "status": "error",
            "error": f"{type(exc).__name__}: {exc}",
        }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tag", default=datetime.utcnow().strftime("UNIFIED-%Y%m%d"))
    parser.add_argument("--start", default="2026-06-01")
    parser.add_argument("--end", default="2026-08-18")
    parser.add_argument("--pack-start", default="2026-08-05")
    parser.add_argument("--pack-end", default="2026-08-18")
    parser.add_argument("--templates", default="", help="Comma-separated template_key filter")
    parser.add_argument("--max-variants", type=int, default=10)
    parser.add_argument("--timeout-sec", type=int, default=DEFAULT_TIMEOUT_SEC)
    parser.add_argument("--capital", type=float, default=100_000.0)
    parser.add_argument("--commission", type=float, default=0.0003)
    parser.add_argument("--slippage", type=float, default=0.0002)
    parser.add_argument("--include-inactive", action="store_true")
    parser.add_argument("-o", "--output", default="")
    args = parser.parse_args(argv)

    start = _parse_dt(args.start)
    end = _parse_dt(args.end)
    if end.hour == 0 and end.minute == 0 and len(args.end) == 10:
        end = end.replace(hour=23, minute=59, second=59)
    pack_start = _parse_dt(args.pack_start)
    pack_end = _parse_dt(args.pack_end)
    if pack_end.hour == 0 and pack_end.minute == 0 and len(args.pack_end) == 10:
        pack_end = pack_end.replace(hour=23, minute=59, second=59)

    wanted = {p.strip() for p in str(args.templates).split(",") if p.strip()}
    templates = get_script_source_service().list_templates()
    if args.include_inactive:
        # list_templates already filters active; fall back to raw query only if needed
        pass
    if wanted:
        templates = [t for t in templates if str(t.get("template_key") or "") in wanted]

    service = StrategyV2BacktestService()
    results: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []

    print(
        json.dumps(
            {
                "status": "start",
                "tag": args.tag,
                "templates": len(templates),
                "start": start.isoformat(),
                "end": end.isoformat(),
                "pack_start": pack_start.isoformat(),
                "pack_end": pack_end.isoformat(),
            }
        ),
        flush=True,
    )

    for template in templates:
        key = str(template.get("template_key") or "")
        schema = template.get("param_schema") or template.get("paramSchema") or {}
        is_pack = _is_pack(key, schema)
        variants: list[int | None]
        if is_pack:
            variants = list(_variant_range(schema, max_variants=args.max_variants))
            window_start, window_end = pack_start, pack_end
        else:
            variants = [None]
            window_start, window_end = start, end

        for variant in variants:
            params = _default_params(schema, variant=variant)
            row = _run_one(
                service=service,
                template=template,
                params=params,
                start=window_start,
                end=window_end,
                tag=args.tag,
                timeout_sec=args.timeout_sec,
                capital=args.capital,
                commission=args.commission,
                slippage=args.slippage,
            )
            print(json.dumps(row, ensure_ascii=False), flush=True)
            if row.get("status") == "ok":
                results.append(row)
            else:
                errors.append(row)

    summary = {
        "status": "done",
        "tag": args.tag,
        "ok": len(results),
        "failed": len(errors),
        "results": results,
        "errors": errors,
    }
    print(json.dumps(summary, ensure_ascii=False), flush=True)
    if args.output:
        with open(args.output, "w", encoding="utf-8") as fh:
            json.dump(summary, fh, ensure_ascii=False, indent=2)
    return 0 if not errors else 2


if __name__ == "__main__":
    raise SystemExit(main())
