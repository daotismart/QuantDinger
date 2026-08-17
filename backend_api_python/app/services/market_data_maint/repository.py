"""Persistence helpers for market data maintenance."""

from __future__ import annotations

import json
from typing import Any, Dict, Iterable, List, Optional, Sequence

from app.services.market_data_maint.config import WatchSpec
from app.utils.db import get_db_connection
from app.utils.logger import get_logger

logger = get_logger(__name__)


def claim_run(*, run_kind: str, trigger_type: str) -> Optional[int]:
    with get_db_connection() as db:
        cur = db.cursor()
        try:
            cur.execute(
                """
                UPDATE qd_market_data_maint_runs
                   SET status = 'failed', finished_at = NOW(),
                       result = '{"error":"interrupted"}'::jsonb
                 WHERE status = 'running'
                   AND run_kind = ?
                   AND started_at < NOW() - INTERVAL '2 hours'
                """,
                (run_kind,),
            )
            cur.execute(
                """
                INSERT INTO qd_market_data_maint_runs (run_kind, trigger_type, status)
                VALUES (?, ?, 'running')
                RETURNING id
                """,
                (run_kind, trigger_type),
            )
            row = cur.fetchone()
            db.commit()
            return int(row["id"]) if row else None
        except Exception:
            db.rollback()
            logger.exception("claim_run failed kind=%s", run_kind)
            return None
        finally:
            cur.close()


def finish_run(run_id: int, status: str, result: Dict[str, Any]) -> None:
    with get_db_connection() as db:
        cur = db.cursor()
        try:
            cur.execute(
                """
                UPDATE qd_market_data_maint_runs
                   SET status = ?, finished_at = NOW(), result = ?::jsonb
                 WHERE id = ?
                """,
                (status, json.dumps(result, ensure_ascii=False), run_id),
            )
            db.commit()
        finally:
            cur.close()


def list_watch_specs() -> List[WatchSpec]:
    with get_db_connection() as db:
        cur = db.cursor()
        try:
            cur.execute(
                """
                SELECT market, symbol, timeframe, exchange_id, market_type, lookback_bars
                  FROM qd_market_data_watch
                 WHERE enabled = TRUE
                 ORDER BY id
                """
            )
            rows = cur.fetchall() or []
        except Exception as exc:
            logger.debug("list_watch_specs unavailable: %s", exc)
            return []
        finally:
            cur.close()
    out: List[WatchSpec] = []
    for row in rows:
        out.append(
            WatchSpec(
                market=str(row["market"]),
                symbol=str(row["symbol"]),
                timeframe=str(row["timeframe"] or "1m"),
                exchange_id=str(row.get("exchange_id") or ""),
                market_type=str(row.get("market_type") or ""),
                lookback_bars=int(row.get("lookback_bars") or 1500),
            )
        )
    return out


def upsert_watch_specs(specs: Sequence[WatchSpec]) -> int:
    if not specs:
        return 0
    written = 0
    with get_db_connection() as db:
        cur = db.cursor()
        try:
            for spec in specs:
                cur.execute(
                    """
                    INSERT INTO qd_market_data_watch (
                        market, symbol, timeframe, exchange_id, market_type,
                        enabled, lookback_bars, updated_at
                    ) VALUES (?, ?, ?, ?, ?, TRUE, ?, NOW())
                    ON CONFLICT (market, symbol, timeframe, exchange_id, market_type)
                    DO UPDATE SET
                        enabled = TRUE,
                        lookback_bars = EXCLUDED.lookback_bars,
                        updated_at = NOW()
                    """,
                    (
                        spec.market,
                        spec.symbol,
                        spec.timeframe,
                        spec.exchange_id or "",
                        spec.market_type or "",
                        int(spec.lookback_bars or 1500),
                    ),
                )
                written += 1
            db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            cur.close()
    return written


def load_bars(
    spec: WatchSpec,
    *,
    start_ts: Optional[int] = None,
    end_ts: Optional[int] = None,
    limit: int = 5000,
) -> List[Dict[str, Any]]:
    clauses = [
        "market = ?",
        "symbol = ?",
        "timeframe = ?",
        "exchange_id = ?",
        "market_type = ?",
    ]
    params: List[Any] = [
        spec.market,
        spec.symbol,
        spec.timeframe,
        spec.exchange_id or "",
        spec.market_type or "",
    ]
    if start_ts is not None:
        clauses.append("bar_time >= ?")
        params.append(int(start_ts))
    if end_ts is not None:
        clauses.append("bar_time <= ?")
        params.append(int(end_ts))
    params.append(max(1, int(limit)))
    sql = f"""
        SELECT bar_time AS time, open, high, low, close, volume, source, quality_flags
          FROM qd_market_bars
         WHERE {' AND '.join(clauses)}
         ORDER BY bar_time ASC
         LIMIT ?
    """
    with get_db_connection() as db:
        cur = db.cursor()
        try:
            cur.execute(sql, tuple(params))
            rows = cur.fetchall() or []
        except Exception as exc:
            logger.debug("load_bars failed: %s", exc)
            return []
        finally:
            cur.close()
    out = []
    for row in rows:
        out.append(
            {
                "time": int(row["time"]),
                "open": float(row["open"]),
                "high": float(row["high"]),
                "low": float(row["low"]),
                "close": float(row["close"]),
                "volume": float(row["volume"] or 0),
                "source": str(row.get("source") or ""),
                "quality_flags": row.get("quality_flags") or [],
            }
        )
    return out


def upsert_bars(
    spec: WatchSpec,
    bars: Sequence[Dict[str, Any]],
    *,
    source: str,
    quality_flags: Optional[Sequence[str]] = None,
) -> int:
    if not bars:
        return 0
    flags = json.dumps(list(quality_flags or []), ensure_ascii=False)
    written = 0
    with get_db_connection() as db:
        cur = db.cursor()
        try:
            for bar in bars:
                cur.execute(
                    """
                    INSERT INTO qd_market_bars (
                        market, symbol, timeframe, exchange_id, market_type,
                        bar_time, open, high, low, close, volume, source, quality_flags, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?::jsonb, NOW())
                    ON CONFLICT (market, symbol, timeframe, exchange_id, market_type, bar_time)
                    DO UPDATE SET
                        open = EXCLUDED.open,
                        high = EXCLUDED.high,
                        low = EXCLUDED.low,
                        close = EXCLUDED.close,
                        volume = EXCLUDED.volume,
                        source = EXCLUDED.source,
                        quality_flags = EXCLUDED.quality_flags,
                        updated_at = NOW()
                    """,
                    (
                        spec.market,
                        spec.symbol,
                        spec.timeframe,
                        spec.exchange_id or "",
                        spec.market_type or "",
                        int(bar["time"]),
                        float(bar["open"]),
                        float(bar["high"]),
                        float(bar["low"]),
                        float(bar["close"]),
                        float(bar.get("volume") or 0),
                        source,
                        flags,
                    ),
                )
                written += 1
            db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            cur.close()
    return written


def insert_ticks(rows: Sequence[Dict[str, Any]]) -> int:
    if not rows:
        return 0
    written = 0
    with get_db_connection() as db:
        cur = db.cursor()
        try:
            for row in rows:
                cur.execute(
                    """
                    INSERT INTO qd_market_ticks (
                        market, symbol, exchange_id, tick_time_ms, last_price, volume,
                        bid, ask, open_interest, payload
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?::jsonb)
                    """,
                    (
                        str(row.get("market") or "Futures"),
                        str(row.get("symbol") or ""),
                        str(row.get("exchange_id") or "ctp"),
                        int(row.get("tick_time_ms") or 0),
                        float(row.get("last_price") or 0),
                        int(row.get("volume") or 0),
                        float(row.get("bid") or 0),
                        float(row.get("ask") or 0),
                        float(row.get("open_interest") or 0),
                        json.dumps(row.get("payload") or {}, ensure_ascii=False),
                    ),
                )
                written += 1
            db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            cur.close()
    return written


def purge_old_ticks(*, retention_days: int) -> int:
    with get_db_connection() as db:
        cur = db.cursor()
        try:
            cur.execute(
                """
                DELETE FROM qd_market_ticks
                 WHERE created_at < NOW() - (%s * INTERVAL '1 day')
                """,
                (int(retention_days),),
            )
            deleted = int(cur.rowcount or 0)
            db.commit()
            return deleted
        except Exception:
            db.rollback()
            logger.exception("purge_old_ticks failed")
            return 0
        finally:
            cur.close()


def purge_old_bars(*, retention_days: int) -> int:
    with get_db_connection() as db:
        cur = db.cursor()
        try:
            cur.execute(
                """
                DELETE FROM qd_market_bars
                 WHERE updated_at < NOW() - (%s * INTERVAL '1 day')
                """,
                (int(retention_days),),
            )
            deleted = int(cur.rowcount or 0)
            db.commit()
            return deleted
        except Exception:
            db.rollback()
            logger.exception("purge_old_bars failed")
            return 0
        finally:
            cur.close()


def latest_runs(limit: int = 20) -> List[Dict[str, Any]]:
    with get_db_connection() as db:
        cur = db.cursor()
        try:
            cur.execute(
                """
                SELECT id, run_kind, trigger_type, status, started_at, finished_at, result
                  FROM qd_market_data_maint_runs
                 ORDER BY id DESC
                 LIMIT ?
                """,
                (max(1, int(limit)),),
            )
            rows = cur.fetchall() or []
        except Exception as exc:
            logger.debug("latest_runs unavailable: %s", exc)
            return []
        finally:
            cur.close()
    out = []
    for row in rows:
        item = dict(row)
        for key in ("started_at", "finished_at"):
            value = item.get(key)
            if hasattr(value, "isoformat"):
                item[key] = value.isoformat()
        out.append(item)
    return out
