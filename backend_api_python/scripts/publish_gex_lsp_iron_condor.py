#!/usr/bin/env python3
"""Publish the ETF iron-condor source + research backtest into QuantDinger tables.

Creates/updates:
  - qd_script_templates (strategy_v2_gex_lsp_iron_condor)
  - qd_script_sources for the admin user (default user_id=1)
  - qd_backtest_runs (+ equity/trade details) from docs/reports JSON

This is what the Strategy Hub / Backtest Center UI reads. The research CLI
alone does not appear in production.

Example (inside backend container):
  PYTHONPATH=/app python /tmp/publish_gex_lsp_iron_condor.py \\
    --code /tmp/strategy_v2_gex_lsp_iron_condor.py \\
    --report /tmp/GEX_LSP_IRON_CONDOR_510050.json \\
    --user-id 1
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from app.services.gex_lsp_strangle.v2_adapter import (
    ENGINE_VERSION,
    research_to_v2_result as _research_to_v2_result,
)
from app.utils.db import get_db_connection


TEMPLATE_KEY = "strategy_v2_gex_lsp_iron_condor"
SOURCE_NAME_510050 = "GEX+LSP 铁鹰（ETF期权·510050）"


def _load_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _upsert_template(cur, *, code: str, title: str, description: str) -> None:
    cur.execute(
        """
        INSERT INTO qd_script_templates
          (template_key, asset_type, title, description, code, param_schema, tags,
           icon, accent, sort_order, is_active, metadata, updated_at)
        VALUES (%s, 'script', %s, %s, %s, %s::jsonb, %s::jsonb,
                'activity', 'orange', 80, TRUE, %s::jsonb, NOW())
        ON CONFLICT (template_key) DO UPDATE SET
          title = EXCLUDED.title,
          description = EXCLUDED.description,
          code = EXCLUDED.code,
          param_schema = EXCLUDED.param_schema,
          tags = EXCLUDED.tags,
          is_active = TRUE,
          metadata = EXCLUDED.metadata,
          updated_at = NOW()
        """,
        (
            TEMPLATE_KEY,
            title,
            description,
            code,
            json.dumps({"params": []}, ensure_ascii=False),
            json.dumps(["strategy-v2", "options", "iron-condor", "etf", "gex", "short-vol"], ensure_ascii=False),
            json.dumps({"source": "gex_lsp_iron_condor", "apiVersion": 2, "version": 1}, ensure_ascii=False),
        ),
    )


def _upsert_source(cur, *, user_id: int, name: str, description: str, code: str) -> int:
    cur.execute(
        """
        SELECT id FROM qd_script_sources
        WHERE user_id = %s AND (template_key = %s OR name = %s)
        ORDER BY id DESC LIMIT 1
        """,
        (int(user_id), TEMPLATE_KEY, name),
    )
    row = cur.fetchone()
    metadata = json.dumps(
        {
            "template_key": TEMPLATE_KEY,
            "underlying_etf": "510050",
            "strategy_family": "options_short_vol_iron_condor",
            "research_engine": ENGINE_VERSION,
            "contract_selection": "listed_chain_gex_walls",
        },
        ensure_ascii=False,
    )
    if row:
        source_id = int(row["id"] if isinstance(row, dict) else row[0])
        cur.execute(
            """
            UPDATE qd_script_sources
            SET name = %s, description = %s, code = %s, asset_type = 'script',
                template_key = %s, metadata = %s::jsonb, status = 'draft', updated_at = NOW()
            WHERE id = %s AND user_id = %s
            """,
            (name, description, code, TEMPLATE_KEY, metadata, source_id, int(user_id)),
        )
    else:
        cur.execute(
            """
            INSERT INTO qd_script_sources
              (user_id, name, description, code, asset_type, template_key, param_schema,
               visibility, status, metadata, created_at, updated_at)
            VALUES (%s, %s, %s, %s, 'script', %s, '{}'::jsonb, 'private', 'draft', %s::jsonb, NOW(), NOW())
            RETURNING id
            """,
            (int(user_id), name, description, code, TEMPLATE_KEY, metadata),
        )
        created = cur.fetchone()
        source_id = int(created["id"] if isinstance(created, dict) else created[0])
    cur.execute(
        """
        SELECT COALESCE(MAX(version_no), 0) + 1 AS next_version
        FROM qd_script_source_versions
        WHERE source_id = %s AND user_id = %s
        """,
        (int(source_id), int(user_id)),
    )
    version_row = cur.fetchone() or {}
    version_no = int(
        version_row["next_version"] if isinstance(version_row, dict) else version_row[0]
    )
    cur.execute(
        """
        INSERT INTO qd_script_source_versions
          (source_id, user_id, version_no, name, description, code,
           template_key, param_schema, metadata, created_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s, '{}'::jsonb, %s::jsonb, NOW())
        """,
        (int(source_id), int(user_id), version_no, name, description, code, TEMPLATE_KEY, metadata),
    )
    return source_id


def _replace_backtest(
    cur,
    *,
    user_id: int,
    source_id: int,
    strategy_name: str,
    code: str,
    result: dict[str, Any],
    start_date: str,
    end_date: str,
    initial_capital: float,
) -> int:
    cur.execute(
        """
        DELETE FROM qd_backtest_equity_points
        WHERE run_id IN (
          SELECT id FROM qd_backtest_runs
          WHERE user_id = %s AND source_id = %s AND engine_version = %s
        )
        """,
        (int(user_id), int(source_id), ENGINE_VERSION),
    )
    cur.execute(
        """
        DELETE FROM qd_backtest_trades
        WHERE run_id IN (
          SELECT id FROM qd_backtest_runs
          WHERE user_id = %s AND source_id = %s AND engine_version = %s
        )
        """,
        (int(user_id), int(source_id), ENGINE_VERSION),
    )
    cur.execute(
        """
        DELETE FROM qd_backtest_runs
        WHERE user_id = %s AND source_id = %s AND engine_version = %s
        """,
        (int(user_id), int(source_id), ENGINE_VERSION),
    )
    cur.execute(
        """
        INSERT INTO qd_backtest_runs
          (user_id, strategy_id, source_id, strategy_name, market, symbol, market_type,
           timeframe, start_date, end_date, initial_capital, commission, slippage, leverage,
           params_json, manifest_json, engine_version, code_hash, status, error_message,
           result_json, created_at)
        VALUES (%s, NULL, %s, %s, %s, %s, 'spot', '1d', %s, %s, %s, 5.0, 0.02, 1.0,
                %s, %s, %s, %s, 'success', '', %s, NOW())
        RETURNING id
        """,
        (
            int(user_id),
            int(source_id),
            strategy_name,
            "CNStock,CNIndexOptions",
            "510050 + iron-condor",
            start_date,
            end_date,
            float(initial_capital),
            json.dumps(result.get("researchSummary", {}).get("config") or {}, ensure_ascii=False),
            json.dumps(result.get("manifest") or {}, ensure_ascii=False),
            ENGINE_VERSION,
            hashlib.sha256(code.encode("utf-8")).hexdigest(),
            json.dumps(result, ensure_ascii=False),
        ),
    )
    run = cur.fetchone()
    run_id = int(run["id"] if isinstance(run, dict) else run[0])
    for index, point in enumerate(result.get("equityCurve") or [], start=1):
        cur.execute(
            """
            INSERT INTO qd_backtest_equity_points
              (run_id, point_index, point_time, point_value, created_at)
            VALUES (%s, %s, %s, %s, NOW())
            """,
            (run_id, index, str(point.get("time") or ""), float(point.get("value") or 0)),
        )
    for index, trade in enumerate(result.get("closedTrades") or [], start=1):
        cur.execute(
            """
            INSERT INTO qd_backtest_trades
              (run_id, user_id, strategy_id, trade_index, trade_time, trade_type, side,
               price, amount, profit, balance, reason, payload_json, created_at)
            VALUES (%s, %s, NULL, %s, %s, 'close', %s, %s, %s, %s, %s, %s, %s, NOW())
            """,
            (
                run_id,
                int(user_id),
                index,
                str(trade.get("exit_time") or ""),
                str(trade.get("side") or "short"),
                float(trade.get("exit_price") or 0),
                float(trade.get("quantity") or 0),
                float(trade.get("profit") or 0),
                float(trade.get("balance") or 0),
                str(trade.get("close_reason") or "")[:64],
                json.dumps(trade, ensure_ascii=False),
            ),
        )
    return run_id


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--code", type=Path, default=Path("docs/examples/strategy_v2_gex_lsp_iron_condor.py"))
    parser.add_argument("--report", type=Path, default=Path("docs/reports/GEX_LSP_IRON_CONDOR_510050.json"))
    parser.add_argument("--user-id", type=int, default=1)
    args = parser.parse_args()

    code = _load_text(args.code)
    payload = json.loads(_load_text(args.report))
    summary = payload.get("summary") or {}
    curve = payload.get("equityCurve") or []
    start_date = str((curve[0] or {}).get("date") or "2026-04-01")
    end_date = str((curve[-1] or {}).get("date") or "2026-08-28")
    result = _research_to_v2_result(payload, code=code)
    title = "GEX+LSP 铁鹰（ETF期权）"
    description = (
        "在 GEX 墙附近卖虚值 call/put，并买入更虚值翅膀构成有限风险铁鹰。"
        "默认 120 张/100 万、次月合约、破短腿即平；20 日涨跌超 8% 停开。"
        "研究样本 510050 年化约 45%（约 90 个交易日）。"
    )

    with get_db_connection() as db:
        cur = db.cursor()
        _upsert_template(cur, code=code, title=title, description=description)
        source_id = _upsert_source(
            cur,
            user_id=int(args.user_id),
            name=SOURCE_NAME_510050,
            description=description,
            code=code,
        )
        run_id = _replace_backtest(
            cur,
            user_id=int(args.user_id),
            source_id=source_id,
            strategy_name=SOURCE_NAME_510050,
            code=code,
            result=result,
            start_date=start_date,
            end_date=end_date,
            initial_capital=float(summary.get("initialCapital") or 1_000_000),
        )
        db.commit()
        cur.close()

    print(json.dumps({
        "templateKey": TEMPLATE_KEY,
        "sourceId": source_id,
        "runId": run_id,
        "userId": int(args.user_id),
        "totalReturn": result["totalReturn"],
        "annualizedReturn": result["annualizedReturn"],
        "trades": result["totalTrades"],
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
