#!/usr/bin/env python3
"""Run backtests for the 5 advanced Strategy V2 packs (10 variants each)."""

from __future__ import annotations

import json
import sys
from datetime import datetime

from app.services.script_source import get_script_source_service
from app.services.strategy_v2 import StrategyV2BacktestService
from app.services.strategy_display_names import compose_strategy_display_name

ADVANCED_PACKS = (
    "strategy_v2_stat_arb_pack",
    "strategy_v2_options_vol_pack",
    "strategy_v2_session_alpha_pack",
    "strategy_v2_regime_switch_pack",
    "strategy_v2_orderflow_proxy_pack",
)

START_DATE = datetime(2026, 8, 5)
END_DATE = datetime(2026, 8, 18, 23, 59, 59)
USER_ID = 1


def main() -> int:
    templates = {
        str(item["template_key"]): item
        for item in get_script_source_service().list_templates()
    }
    missing = [key for key in ADVANCED_PACKS if key not in templates]
    if missing:
        print(json.dumps({"status": "error", "missing": missing}), flush=True)
        return 1

    service = StrategyV2BacktestService()
    results: list[dict] = []
    errors: list[dict] = []

    for pack_key in ADVANCED_PACKS:
        template = templates[pack_key]
        code = str(template.get("code") or "")
        title = str(template.get("title") or pack_key)
        metadata = template.get("metadata") if isinstance(template.get("metadata"), dict) else {}
        for variant in range(10):
            strategy_name = compose_strategy_display_name(
                name=title,
                template_title=title,
                template_key=pack_key,
                params={"variant": variant},
                metadata=metadata,
            )
            try:
                run_id, result = service.run(
                    user_id=USER_ID,
                    code=code,
                    start_date=START_DATE,
                    end_date=END_DATE,
                    initial_capital=100_000,
                    commission=0.0003,
                    slippage=0.0002,
                    params={
                        "variant": variant,
                        "target_pct": 0.95,
                        "allow_short": True,
                    },
                    persist=True,
                    strategy_name=strategy_name,
                )
                metrics = result.get("metrics") if isinstance(result.get("metrics"), dict) else result
                results.append(
                    {
                        "pack": pack_key,
                        "variant": variant,
                        "runId": run_id,
                        "status": "ok",
                        "totalReturn": metrics.get("totalReturn", metrics.get("total_return")),
                        "totalTrades": result.get("totalTrades"),
                        "totalExecutions": result.get("totalExecutions"),
                    }
                )
                print(json.dumps(results[-1]), flush=True)
            except Exception as exc:
                errors.append({"pack": pack_key, "variant": variant, "error": str(exc)})
                print(json.dumps({"pack": pack_key, "variant": variant, "status": "error", "error": str(exc)}), flush=True)

    summary = {
        "status": "done",
        "ok": len(results),
        "failed": len(errors),
        "results": results,
        "errors": errors,
    }
    print(json.dumps(summary), flush=True)
    return 0 if not errors else 2


if __name__ == "__main__":
    raise SystemExit(main())
