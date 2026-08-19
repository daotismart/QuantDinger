#!/usr/bin/env python3
"""Repair auto-generated script source and backtest display names in the database."""

from __future__ import annotations

import json
from typing import Any

from app.services.script_source import get_script_source_service
from app.services.strategy_v2.display_names import (
    compose_strategy_display_name,
    format_universe_symbol,
    is_auto_generated_strategy_name,
    resolve_template_title,
)
from app.utils.db import get_db_connection


def _template_titles() -> dict[str, str]:
    service = get_script_source_service()
    return service._template_titles()


def _match_template_key(code: str, template_titles: dict[str, str]) -> str:
    from app.services.strategy_v2.display_names import extract_code_doc_title

    doc_title = extract_code_doc_title(code)
    if not doc_title:
        return ""
    for key, title in template_titles.items():
        if title == doc_title:
            return key
    return ""


def repair_script_sources(*, dry_run: bool = False) -> dict[str, Any]:
    template_titles = _template_titles()
    updated = 0
    with get_db_connection() as db:
        cur = db.cursor()
        cur.execute(
            """
            SELECT id, name, description, code, template_key, metadata
            FROM qd_script_sources
            ORDER BY id ASC
            """
        )
        rows = cur.fetchall() or []
        for row in rows:
            source_id = int(row.get("id") or 0)
            old_name = str(row.get("name") or "")
            code = str(row.get("code") or "")
            template_key = str(row.get("template_key") or "").strip()
            if not template_key:
                template_key = _match_template_key(code, template_titles)
            metadata = row.get("metadata")
            if isinstance(metadata, str):
                try:
                    metadata = json.loads(metadata)
                except (TypeError, ValueError):
                    metadata = {}
            if not isinstance(metadata, dict):
                metadata = {}
            new_name = compose_strategy_display_name(
                name=old_name,
                code=code,
                template_title=resolve_template_title(template_key, template_titles),
                template_key=template_key,
                metadata=metadata,
            )
            if new_name == old_name and template_key == str(row.get("template_key") or ""):
                continue
            updated += 1
            if dry_run:
                print(f"source {source_id}: {old_name!r} -> {new_name!r} (template_key={template_key!r})")
                continue
            cur.execute(
                """
                UPDATE qd_script_sources
                SET name = ?, template_key = ?, updated_at = NOW()
                WHERE id = ?
                """,
                (new_name, template_key, source_id),
            )
        if not dry_run:
            db.commit()
        cur.close()
    return {"updated_sources": updated, "dry_run": dry_run}


def repair_backtest_runs(*, dry_run: bool = False) -> dict[str, Any]:
    template_titles = _template_titles()
    updated = 0
    with get_db_connection() as db:
        cur = db.cursor()
        cur.execute(
            """
            SELECT r.id, r.strategy_name, r.symbol, r.source_id, r.params_json, r.manifest_json,
                   s.name AS source_name, s.template_key, s.code
            FROM qd_backtest_runs r
            LEFT JOIN qd_script_sources s ON s.id = r.source_id
            ORDER BY r.id ASC
            """
        )
        rows = cur.fetchall() or []
        for row in rows:
            run_id = int(row.get("id") or 0)
            old_name = str(row.get("strategy_name") or "")
            old_symbol = str(row.get("symbol") or "")
            try:
                params = json.loads(row.get("params_json") or "{}")
            except (TypeError, ValueError):
                params = {}
            try:
                manifest = json.loads(row.get("manifest_json") or "{}")
            except (TypeError, ValueError):
                manifest = {}
            universe = manifest.get("universe") if isinstance(manifest.get("universe"), dict) else {}
            instruments = [
                item for item in (universe.get("instruments") or []) if isinstance(item, dict)
            ]
            template_key = str(row.get("template_key") or "").strip()
            if not template_key:
                template_key = _match_template_key(str(row.get("code") or ""), template_titles)
            template = get_script_source_service().get_template_by_key(template_key) if template_key else None
            metadata = {}
            template_title = resolve_template_title(template_key, template_titles)
            if template:
                metadata = template.get("metadata") if isinstance(template.get("metadata"), dict) else {}
                template_title = str(template.get("title") or template_title)
            new_name = compose_strategy_display_name(
                name=old_name or str(row.get("source_name") or ""),
                code=str(row.get("code") or ""),
                template_title=template_title,
                template_key=template_key,
                params=params if isinstance(params, dict) else {},
                metadata=metadata,
                symbol=old_symbol,
                instruments=instruments,
                universe_reference=str(universe.get("reference") or ""),
            )
            new_symbol = format_universe_symbol(
                instruments=instruments,
                fallback_symbol=old_symbol,
                universe_reference=str(universe.get("reference") or ""),
            )
            if new_name == old_name and new_symbol == old_symbol:
                continue
            updated += 1
            if dry_run:
                print(
                    f"run {run_id}: name {old_name!r} -> {new_name!r}; "
                    f"symbol {old_symbol!r} -> {new_symbol!r}"
                )
                continue
            cur.execute(
                """
                UPDATE qd_backtest_runs
                SET strategy_name = ?, symbol = ?
                WHERE id = ?
                """,
                (new_name, new_symbol, run_id),
            )
        if not dry_run:
            db.commit()
        cur.close()
    return {"updated_runs": updated, "dry_run": dry_run}


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    source_result = repair_script_sources(dry_run=args.dry_run)
    run_result = repair_backtest_runs(dry_run=args.dry_run)
    print(json.dumps({"sources": source_result, "runs": run_result}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
