"""Persistence for data-service runtime configuration."""

from __future__ import annotations

import json
from typing import Any, Dict, Optional

from app.utils.db import get_db_connection
from app.utils.logger import get_logger

logger = get_logger(__name__)


def get_config_value(key: str) -> Any:
    with get_db_connection() as db:
        cur = db.cursor()
        try:
            cur.execute(
                """
                SELECT value
                  FROM qd_data_service_config
                 WHERE config_key = ?
                """,
                (str(key),),
            )
            row = cur.fetchone()
            if not row:
                return None
            value = row.get("value") if isinstance(row, dict) else row[0]
            if isinstance(value, str):
                return json.loads(value)
            return value
        except Exception as exc:
            logger.debug("get_config_value(%s) failed: %s", key, exc)
            return None
        finally:
            cur.close()


def set_config_value(key: str, value: Any) -> None:
    payload = json.dumps(value, ensure_ascii=False)
    with get_db_connection() as db:
        cur = db.cursor()
        try:
            cur.execute(
                """
                INSERT INTO qd_data_service_config (config_key, value, updated_at)
                VALUES (?, ?::jsonb, NOW())
                ON CONFLICT (config_key)
                DO UPDATE SET value = EXCLUDED.value, updated_at = NOW()
                """,
                (str(key), payload),
            )
            db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            cur.close()


def list_config() -> Dict[str, Any]:
    with get_db_connection() as db:
        cur = db.cursor()
        try:
            cur.execute(
                """
                SELECT config_key, value, updated_at
                  FROM qd_data_service_config
                 ORDER BY config_key
                """
            )
            rows = cur.fetchall() or []
        except Exception as exc:
            logger.debug("list_config failed: %s", exc)
            return {}
        finally:
            cur.close()
    out: Dict[str, Any] = {}
    for row in rows:
        key = str(row["config_key"])
        value = row.get("value")
        if isinstance(value, str):
            try:
                value = json.loads(value)
            except Exception:
                pass
        out[key] = {
            "value": value,
            "updatedAt": row.get("updated_at").isoformat()
            if hasattr(row.get("updated_at"), "isoformat")
            else row.get("updated_at"),
        }
    return out
