"""Durable store for ETF constituent profit / PE / market-cap snapshots.

Redis remains the hot path for ETF analysis. This Postgres table survives Redis
flushes and lets request-time enrichment skip AkShare when a fresh row exists.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Iterable, List

from app.utils.db import get_db_connection
from app.utils.logger import get_logger

logger = get_logger(__name__)

_SCHEMA_READY = False
_TABLE = "qd_etf_constituent_fundamentals"
_DEFAULT_MAX_AGE_HOURS = 72


def ensure_schema() -> None:
    global _SCHEMA_READY
    if _SCHEMA_READY:
        return
    with get_db_connection() as db:
        cur = db.cursor()
        cur.execute(
            f"""
            CREATE TABLE IF NOT EXISTS {_TABLE} (
              code VARCHAR(16) PRIMARY KEY,
              name VARCHAR(128),
              net_profit DOUBLE PRECISION,
              profit_margin DOUBLE PRECISION,
              pe_ratio DOUBLE PRECISION,
              market_cap DOUBLE PRECISION,
              source VARCHAR(64),
              asof TIMESTAMPTZ,
              updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
            """
        )
        cur.execute(
            f"CREATE INDEX IF NOT EXISTS idx_{_TABLE}_updated_at ON {_TABLE} (updated_at DESC)"
        )
        db.commit()
        cur.close()
    _SCHEMA_READY = True


def _as_mapping(row: Any) -> Dict[str, Any]:
    if not row:
        return {}
    if isinstance(row, dict):
        return dict(row)
    keys = (
        "code",
        "name",
        "net_profit",
        "profit_margin",
        "pe_ratio",
        "market_cap",
        "source",
        "asof",
        "updated_at",
    )
    return dict(zip(keys, row))


def _to_snapshot(row: Any) -> Dict[str, Any]:
    data = _as_mapping(row)
    if not data:
        return {}
    snap = {
        "net_profit": data.get("net_profit"),
        "profit_margin": data.get("profit_margin"),
        "pe_ratio": data.get("pe_ratio"),
        "market_cap": data.get("market_cap"),
        "name": data.get("name"),
        "source": data.get("source") or "db",
        "asof": str(data.get("asof") or "")[:19] or None,
        "updated_at": str(data.get("updated_at") or "")[:19] or None,
    }
    if not any(snap.get(k) is not None for k in ("net_profit", "pe_ratio", "market_cap", "profit_margin")):
        return {}
    return snap


def load_snapshot(code6: str, *, max_age_hours: int = _DEFAULT_MAX_AGE_HOURS) -> Dict[str, Any]:
    code6 = str(code6 or "").strip()
    if not code6:
        return {}
    try:
        ensure_schema()
        cutoff = datetime.now(timezone.utc) - timedelta(hours=max(1, int(max_age_hours)))
        with get_db_connection() as db:
            cur = db.cursor()
            cur.execute(
                f"""
                SELECT code, name, net_profit, profit_margin, pe_ratio, market_cap,
                       source, asof, updated_at
                FROM {_TABLE}
                WHERE code = %s AND updated_at >= %s
                LIMIT 1
                """,
                (code6, cutoff),
            )
            row = cur.fetchone()
            cur.close()
        return _to_snapshot(row)
    except Exception as exc:
        logger.debug("load constituent fundamental %s failed: %s", code6, exc)
        return {}


def load_snapshots(
    codes: Iterable[str],
    *,
    max_age_hours: int = _DEFAULT_MAX_AGE_HOURS,
) -> Dict[str, Dict[str, Any]]:
    code_list = [str(c or "").strip() for c in codes if str(c or "").strip()]
    if not code_list:
        return {}
    try:
        ensure_schema()
        cutoff = datetime.now(timezone.utc) - timedelta(hours=max(1, int(max_age_hours)))
        with get_db_connection() as db:
            cur = db.cursor()
            cur.execute(
                f"""
                SELECT code, name, net_profit, profit_margin, pe_ratio, market_cap,
                       source, asof, updated_at
                FROM {_TABLE}
                WHERE code = ANY(%s) AND updated_at >= %s
                """,
                (code_list, cutoff),
            )
            rows = cur.fetchall() or []
            cur.close()
        out: Dict[str, Dict[str, Any]] = {}
        for row in rows:
            data = _as_mapping(row)
            code = str(data.get("code") or "").strip()
            snap = _to_snapshot(data)
            if code and snap:
                out[code] = snap
        return out
    except Exception as exc:
        logger.debug("load constituent fundamentals batch failed: %s", exc)
        return {}


def upsert_snapshot(
    code6: str,
    snapshot: Dict[str, Any],
    *,
    name: str = "",
    source: str = "akshare",
) -> None:
    code6 = str(code6 or "").strip()
    if not code6 or not isinstance(snapshot, dict):
        return
    if not any(snapshot.get(k) is not None for k in ("net_profit", "pe_ratio", "market_cap", "profit_margin")):
        return
    try:
        ensure_schema()
        asof = snapshot.get("asof") or datetime.now(timezone.utc)
        with get_db_connection() as db:
            cur = db.cursor()
            cur.execute(
                f"""
                INSERT INTO {_TABLE}
                  (code, name, net_profit, profit_margin, pe_ratio, market_cap, source, asof, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, NOW())
                ON CONFLICT (code) DO UPDATE SET
                  name = COALESCE(EXCLUDED.name, {_TABLE}.name),
                  net_profit = COALESCE(EXCLUDED.net_profit, {_TABLE}.net_profit),
                  profit_margin = COALESCE(EXCLUDED.profit_margin, {_TABLE}.profit_margin),
                  pe_ratio = COALESCE(EXCLUDED.pe_ratio, {_TABLE}.pe_ratio),
                  market_cap = COALESCE(EXCLUDED.market_cap, {_TABLE}.market_cap),
                  source = EXCLUDED.source,
                  asof = EXCLUDED.asof,
                  updated_at = NOW()
                """,
                (
                    code6,
                    str(name or snapshot.get("name") or "")[:128] or None,
                    snapshot.get("net_profit"),
                    snapshot.get("profit_margin"),
                    snapshot.get("pe_ratio"),
                    snapshot.get("market_cap"),
                    str(source or "akshare")[:64],
                    asof,
                ),
            )
            db.commit()
            cur.close()
    except Exception as exc:
        logger.debug("upsert constituent fundamental %s failed: %s", code6, exc)
