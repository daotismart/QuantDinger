"""Container health check for durable backend workers."""

from __future__ import annotations

import argparse
import os
import sys

from app.utils.db import get_db_connection


def _default_max_age(role: str) -> int:
    """Celery often runs long maintenance jobs with concurrency=1.

    Heartbeat tasks share that single slot, so the health window must tolerate
    historical/maintenance cycles (commonly several minutes).
    """
    if role == "celery":
        return max(45, int(os.getenv("CELERY_HEALTH_MAX_AGE_SEC", "900")))
    return max(15, int(os.getenv("WORKER_HEALTH_MAX_AGE_SEC", "45")))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("role", choices=("trading", "scheduler", "celery"))
    parser.add_argument("--max-age", type=int, default=None)
    args = parser.parse_args()
    max_age = int(args.max_age) if args.max_age is not None else _default_max_age(args.role)

    credential_key = str(os.getenv("CREDENTIAL_ENCRYPTION_KEY") or "").strip()
    session_key = str(os.getenv("SECRET_KEY") or "").strip()
    if args.role in {"trading", "scheduler"} and not credential_key:
        if (
            len(session_key.encode("utf-8")) < 10
            or session_key == "quantdinger-secret-key-change-me"
        ):
            sys.exit(1)

    with get_db_connection() as db:
        cur = db.cursor()
        try:
            cur.execute(
                """
                SELECT COUNT(*) AS count
                FROM qd_worker_heartbeats
                WHERE role = %s AND status = 'running'
                  AND heartbeat_at >= NOW() - (%s * INTERVAL '1 second')
                """,
                (args.role, max(1, max_age)),
            )
            row = cur.fetchone() or {}
        finally:
            cur.close()
    if int(row.get("count") or 0) < 1:
        sys.exit(1)


if __name__ == "__main__":
    main()
