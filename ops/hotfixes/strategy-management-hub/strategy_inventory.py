"""Strategy management inventory: script sources + backtest/live summaries."""

from __future__ import annotations

import json
from typing import Any

from app.services.backtest_ranking import score_run_row
from app.utils.db import get_db_connection


def _as_dict(row: Any) -> dict[str, Any]:
    if row is None:
        return {}
    if isinstance(row, dict):
        return dict(row)
    try:
        return dict(row)
    except Exception:
        return {}


def _parse_json(value: Any) -> Any:
    if isinstance(value, (dict, list)):
        return value
    text = str(value or "").strip()
    if not text:
        return {}
    try:
        return json.loads(text)
    except (TypeError, ValueError):
        return {}


def _to_iso(value: Any) -> str:
    if value is None:
        return ""
    if hasattr(value, "isoformat"):
        try:
            return value.isoformat()
        except Exception:
            pass
    return str(value)


def _pick_float(row: dict[str, Any], *keys: str) -> float | None:
    for key in keys:
        if key in row and row.get(key) is not None:
            try:
                return float(row.get(key))
            except (TypeError, ValueError):
                continue
    return None


def build_strategy_inventory(
    *,
    user_id: int,
    keyword: str = "",
    status: str = "",
    asset_type: str = "",
    visibility: str = "",
    limit: int = 500,
) -> dict[str, Any]:
    """Return the current user's strategies with sortable summary attributes."""
    uid = int(user_id)
    limit = max(1, min(int(limit or 500), 2000))
    keyword = str(keyword or "").strip().lower()
    status = str(status or "").strip().lower()
    asset_type = str(asset_type or "").strip().lower()
    visibility = str(visibility or "").strip().lower()

    with get_db_connection() as db:
        cur = db.cursor()
        cur.execute(
            """
            SELECT s.id, s.user_id, s.name, s.description, s.asset_type, s.template_key,
                   s.visibility, s.status, s.metadata, s.created_at, s.updated_at,
                   COALESCE(v.version_count, 0) AS version_count,
                   COALESCE(v.latest_version, 0) AS latest_version
            FROM qd_script_sources s
            LEFT JOIN (
              SELECT source_id,
                     COUNT(*)::int AS version_count,
                     MAX(version_no)::int AS latest_version
              FROM qd_script_source_versions
              WHERE user_id = ?
              GROUP BY source_id
            ) v ON v.source_id = s.id
            WHERE s.user_id = ?
            ORDER BY s.updated_at DESC, s.id DESC
            LIMIT ?
            """,
            (uid, uid, limit),
        )
        sources = [_as_dict(row) for row in (cur.fetchall() or [])]

        cur.execute(
            """
            SELECT id, user_id, strategy_id, source_id, strategy_name, market, symbol, timeframe,
                   start_date, end_date, initial_capital, result_json, created_at, status
            FROM qd_backtest_runs
            WHERE user_id = ? AND status = 'success' AND COALESCE(source_id, 0) > 0
            ORDER BY id DESC
            LIMIT ?
            """,
            (uid, max(limit * 20, 500)),
        )
        backtests = [_as_dict(row) for row in (cur.fetchall() or [])]

        cur.execute(
            """
            SELECT id, strategy_name, status, market_category, symbol, timeframe,
                   trading_config, updated_at
            FROM qd_strategies_trading
            WHERE user_id = ?
            ORDER BY id DESC
            """,
            (uid,),
        )
        live_rows = [_as_dict(row) for row in (cur.fetchall() or [])]
        cur.close()

    best_by_source: dict[int, dict[str, Any]] = {}
    backtest_counts: dict[int, int] = {}
    for row in backtests:
        source_id = int(row.get("source_id") or 0)
        if source_id <= 0:
            continue
        backtest_counts[source_id] = backtest_counts.get(source_id, 0) + 1
        scored = score_run_row(row)
        score = _pick_float(scored, "score") or 0.0
        prev = best_by_source.get(source_id)
        prev_score = _pick_float(prev or {}, "score") or -1e18
        if prev is None or score > prev_score:
            best_by_source[source_id] = scored

    live_by_source: dict[int, list[dict[str, Any]]] = {}
    for row in live_rows:
        cfg = _parse_json(row.get("trading_config"))
        if not isinstance(cfg, dict):
            cfg = {}
        source_id = int(
            cfg.get("script_source_id")
            or cfg.get("source_id")
            or cfg.get("sourceId")
            or 0
        )
        if source_id <= 0:
            continue
        live_by_source.setdefault(source_id, []).append(
            {
                "id": int(row.get("id") or 0),
                "name": str(row.get("strategy_name") or ""),
                "status": str(row.get("status") or ""),
                "market": str(row.get("market_category") or ""),
                "symbol": str(row.get("symbol") or ""),
                "timeframe": str(row.get("timeframe") or ""),
                "updated_at": _to_iso(row.get("updated_at")),
            }
        )

    items: list[dict[str, Any]] = []
    for source in sources:
        source_id = int(source.get("id") or 0)
        metadata = _parse_json(source.get("metadata"))
        if not isinstance(metadata, dict):
            metadata = {}
        best = best_by_source.get(source_id) or {}
        live_list = live_by_source.get(source_id) or []
        running = sum(
            1
            for item in live_list
            if str(item.get("status") or "").lower() in {"running", "active", "started"}
        )
        item = {
            "id": source_id,
            "name": str(source.get("name") or ""),
            "description": str(source.get("description") or ""),
            "asset_type": str(source.get("asset_type") or ""),
            "template_key": str(source.get("template_key") or ""),
            "visibility": str(source.get("visibility") or ""),
            "status": str(source.get("status") or ""),
            "version_count": int(source.get("version_count") or 0),
            "latest_version": int(source.get("latest_version") or 0),
            "backtest_count": int(backtest_counts.get(source_id) or 0),
            "best_score": _pick_float(best, "score"),
            "best_return": _pick_float(best, "total_return", "totalReturn"),
            "best_sharpe": _pick_float(best, "sharpe", "sharpe_ratio"),
            "best_drawdown": _pick_float(best, "max_drawdown", "maxDrawdown"),
            "best_flag": str(best.get("flag") or best.get("flag_label") or ""),
            "best_market": str(best.get("market") or ""),
            "best_timeframe": str(best.get("timeframe") or ""),
            "live_count": len(live_list),
            "live_running_count": running,
            "tags": metadata.get("tags") if isinstance(metadata.get("tags"), list) else [],
            "created_at": _to_iso(source.get("created_at")),
            "updated_at": _to_iso(source.get("updated_at")),
        }

        haystack = " ".join(
            [
                item["name"],
                item["description"],
                item["asset_type"],
                item["template_key"],
                item["status"],
                item["visibility"],
                " ".join(str(tag) for tag in item["tags"]),
            ]
        ).lower()
        if keyword and keyword not in haystack:
            continue
        if status and item["status"].lower() != status:
            continue
        if asset_type and item["asset_type"].lower() != asset_type:
            continue
        if visibility and item["visibility"].lower() != visibility:
            continue
        items.append(item)

    return {
        "count": len(items),
        "items": items,
        "facets": {
            "statuses": sorted({str(item.get("status") or "") for item in items if item.get("status")}),
            "asset_types": sorted(
                {str(item.get("asset_type") or "") for item in items if item.get("asset_type")}
            ),
            "visibilities": sorted(
                {str(item.get("visibility") or "") for item in items if item.get("visibility")}
            ),
        },
    }
