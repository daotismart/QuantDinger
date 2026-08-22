#!/usr/bin/env python3
"""Patch CN pack templates for session-limited 1m history depth."""

from __future__ import annotations

from app.utils.db import get_db_connection

REPLACEMENTS = [
    ("context.set_warmup(8000)", "context.set_warmup(800)"),
    ("context.set_warmup(3000)", "context.set_warmup(800)"),
    ("context.set_warmup(1500)", "context.set_warmup(800)"),
    ("context.set_warmup(1000)", "context.set_warmup(800)"),
    ('get_history(8000, "1m"', 'get_history(800, "1m"'),
    ('get_history(3000, "1m"', 'get_history(800, "1m"'),
    ('get_history(1500, "1m"', 'get_history(800, "1m"'),
    ('get_history(1000, "1m"', 'get_history(800, "1m"'),
    ("get_history(8000, '1m'", "get_history(800, '1m'"),
    ("get_history(3000, '1m'", "get_history(800, '1m'"),
    ("get_history(1500, '1m'", "get_history(800, '1m'"),
    ("get_history(1000, '1m'", "get_history(800, '1m'"),
    ("len(c30) < 100", "len(c30) < 25"),
    ("len(c30) < 40", "len(c30) < 25"),
    ("len(c30) < 30", "len(c30) < 25"),
]


def main() -> int:
    with get_db_connection() as db:
        cur = db.cursor()
        cur.execute(
            "SELECT id, template_key, code FROM qd_script_templates "
            "WHERE template_key LIKE 'strategy_v2_%_pack'"
        )
        rows = cur.fetchall() or []
        updated = 0
        for row in rows:
            code = str(row.get("code") or "")
            new = code
            for old, repl in REPLACEMENTS:
                new = new.replace(old, repl)
            if "ma100 = _rolling_mean(c30, 100)" in new and "if len(c30) < 50:" not in new:
                new = new.replace(
                    "ma100 = _rolling_mean(c30, 100)",
                    "ma100 = _rolling_mean(c30, 100)\n    if len(c30) < 50:\n        return",
                )
            if new == code:
                print(f"skip {row.get('template_key')}")
                continue
            cur.execute(
                "UPDATE qd_script_templates SET code = ?, updated_at = NOW() WHERE id = ?",
                (new, int(row["id"])),
            )
            updated += 1
            print(f"patched {row.get('template_key')}")
        db.commit()
        cur.close()
    print(f"updated={updated}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
