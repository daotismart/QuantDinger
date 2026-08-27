"""Read ETF option chains from the local etf_options ClickHouse service.

Prefer this over live Sina/SSE fetches when the local DB is reachable and fresh.
Uses ClickHouse HTTP interface (no extra Python dependency).
"""

from __future__ import annotations

import json
import os
import time
import urllib.parse
import urllib.request
from datetime import date, datetime
from typing import Any, Dict, List, Optional, Tuple

from app.utils.logger import get_logger

logger = get_logger(__name__)

_DEFAULT_URL = "http://172.17.0.1:18123"
_DEFAULT_DB = "etf_options"


def etf_options_ch_enabled() -> bool:
    raw = os.getenv("ETF_OPTIONS_CH_ENABLED", "true").strip().lower()
    return raw in {"1", "true", "yes", "on"}


def etf_options_ch_url() -> str:
    return (
        os.getenv("ETF_OPTIONS_CH_URL")
        or os.getenv("CLICKHOUSE_HTTP_URL")
        or _DEFAULT_URL
    ).rstrip("/")


def etf_options_ch_database() -> str:
    return (
        os.getenv("ETF_OPTIONS_CH_DATABASE")
        or os.getenv("CLICKHOUSE_DATABASE")
        or _DEFAULT_DB
    ).strip() or _DEFAULT_DB


def etf_options_ch_max_age_hours() -> float:
    try:
        return float(os.getenv("ETF_OPTIONS_CH_MAX_AGE_HOURS", "96") or 96)
    except ValueError:
        return 96.0


def etf_options_panel_cache_ttl() -> int:
    try:
        return max(0, int(os.getenv("ETF_OPTIONS_PANEL_CACHE_TTL", "60") or 60))
    except ValueError:
        return 60


def _to_float(value: Any) -> float:
    try:
        if value is None or value == "":
            return 0.0
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _parse_dt(value: Any) -> Optional[datetime]:
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value
    text = str(value).strip()
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(text[:19], fmt)
        except ValueError:
            continue
    return None


def _month_key_from_expire(expire_date: Any) -> str:
    dt = _parse_dt(expire_date)
    if not dt:
        digits = "".join(ch for ch in str(expire_date or "") if ch.isdigit())
        if len(digits) >= 6:
            return digits[:6]
        return ""
    return f"{dt.year:04d}{dt.month:02d}"


def _t_from_expire(expire_date: Any) -> float:
    dt = _parse_dt(expire_date)
    if not dt:
        return 30 / 365.0
    days = max((dt.date() - date.today()).days, 1)
    return days / 365.0


def _ch_query(sql: str, timeout: float = 20.0) -> Tuple[List[str], List[List[Any]]]:
    params = urllib.parse.urlencode(
        {
            "database": etf_options_ch_database(),
            "default_format": "JSONCompact",
        }
    )
    url = f"{etf_options_ch_url()}/?{params}"
    req = urllib.request.Request(
        url,
        data=sql.encode("utf-8"),
        method="POST",
        headers={"Content-Type": "text/plain; charset=utf-8"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        payload = json.loads(resp.read().decode("utf-8"))
    meta = payload.get("meta") or []
    cols = [str(item.get("name") or "") for item in meta]
    rows = payload.get("data") or []
    return cols, rows


def ch_ping(timeout: float = 2.0) -> bool:
    try:
        url = f"{etf_options_ch_url()}/ping"
        with urllib.request.urlopen(url, timeout=timeout) as resp:
            body = resp.read()
            return resp.status == 200 and b"Ok" in body
    except Exception:
        return False


def fetch_underlying_spot(code6: str) -> Tuple[float, Optional[str]]:
    code6 = str(code6 or "").strip()
    if not code6:
        return 0.0, None
    sql = f"""
    SELECT ts_minute, ifNull(last_price, close) AS px
    FROM opt_underlying_1m
    WHERE underlying_code = '{code6}'
    ORDER BY ts_minute DESC
    LIMIT 1
    """
    try:
        cols, rows = _ch_query(sql, timeout=8.0)
        if not rows:
            return 0.0, None
        row = dict(zip(cols, rows[0]))
        return _to_float(row.get("px")), str(row.get("ts_minute") or "") or None
    except Exception as exc:
        logger.info("etf_options CH underlying spot failed for %s: %s", code6, exc)
        return 0.0, None


def fetch_latest_quote_ts(code6: str) -> Optional[datetime]:
    code6 = str(code6 or "").strip()
    if not code6:
        return None
    sql = f"""
    SELECT max(ts_minute) AS mx
    FROM opt_quotes_bar_1m
    WHERE underlying_code = '{code6}'
    """
    try:
        cols, rows = _ch_query(sql, timeout=8.0)
        if not rows:
            return None
        return _parse_dt(dict(zip(cols, rows[0])).get("mx"))
    except Exception as exc:
        logger.info("etf_options CH freshness failed for %s: %s", code6, exc)
        return None


def is_quote_data_fresh(code6: str) -> bool:
    latest = fetch_latest_quote_ts(code6)
    if latest is None:
        return False
    age_h = abs((datetime.now() - latest).total_seconds()) / 3600.0
    return age_h <= etf_options_ch_max_age_hours()


def fetch_option_chain_rows(
    code6: str,
    *,
    lookback_days: int = 5,
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """Return flat contract rows joined with latest quote + analytics."""
    code6 = str(code6 or "").strip()
    meta: Dict[str, Any] = {"source": "clickhouse", "lookback_days": lookback_days}
    if not code6:
        return [], meta

    sql = f"""
    SELECT
      c.contract_code AS contract_code,
      c.contract_id AS contract_id,
      c.strike AS strike,
      c.cp AS cp,
      c.expire_date AS expire_date,
      q.close AS close,
      q.open_interest AS open_interest,
      a.iv AS iv,
      a.delta AS delta,
      a.gamma AS gamma,
      a.vega AS vega,
      a.theta AS theta,
      a.underlying_price AS underlying_price,
      q.ts AS quote_ts
    FROM (
      SELECT contract_code, contract_id, strike, cp, expire_date
      FROM opt_contracts_daily
      WHERE underlying_code = '{code6}'
        AND trade_date = (
          SELECT max(trade_date) FROM opt_contracts_daily WHERE underlying_code = '{code6}'
        )
        AND contract_id IS NOT NULL AND contract_id != ''
    ) c
    INNER JOIN (
      SELECT
        toString(ifNull(nullIf(contract_id, ''), contract_code)) AS jid,
        argMax(close, ts_minute) AS close,
        argMax(open_interest, ts_minute) AS open_interest,
        max(ts_minute) AS ts
      FROM opt_quotes_bar_1m
      WHERE underlying_code = '{code6}'
        AND ts_minute >= (now('Asia/Shanghai') - INTERVAL {int(lookback_days)} DAY)
      GROUP BY jid
    ) q ON toString(c.contract_id) = q.jid
    LEFT JOIN (
      SELECT
        toString(ifNull(nullIf(contract_id, ''), contract_code)) AS jid,
        argMax(iv, ts_minute) AS iv,
        argMax(delta, ts_minute) AS delta,
        argMax(gamma, ts_minute) AS gamma,
        argMax(vega, ts_minute) AS vega,
        argMax(theta, ts_minute) AS theta,
        argMax(underlying_price, ts_minute) AS underlying_price
      FROM opt_analytics_1m
      WHERE underlying_code = '{code6}'
        AND ts_minute >= (now('Asia/Shanghai') - INTERVAL {int(lookback_days)} DAY)
      GROUP BY jid
    ) a ON toString(c.contract_id) = a.jid
    SETTINGS max_execution_time = 30
    """
    t0 = time.perf_counter()
    try:
        cols, raw_rows = _ch_query(sql, timeout=35.0)
    except Exception as exc:
        logger.warning("etf_options CH chain query failed for %s: %s", code6, exc)
        return [], meta

    rows: List[Dict[str, Any]] = []
    for raw in raw_rows:
        item = dict(zip(cols, raw))
        rows.append(
            {
                "contract_code": str(item.get("contract_code") or ""),
                "contract_id": str(item.get("contract_id") or ""),
                "strike": _to_float(item.get("strike")),
                "cp": str(item.get("cp") or "").strip().upper(),
                "expire_date": item.get("expire_date"),
                "month": _month_key_from_expire(item.get("expire_date")),
                "close": _to_float(item.get("close")),
                "open_interest": _to_float(item.get("open_interest")),
                "iv": _to_float(item.get("iv")),
                "delta": _to_float(item.get("delta")),
                "gamma": _to_float(item.get("gamma")),
                "vega": _to_float(item.get("vega")),
                "theta": _to_float(item.get("theta")),
                "underlying_price": _to_float(item.get("underlying_price")),
                "quote_ts": item.get("quote_ts"),
            }
        )
    meta["elapsed_s"] = round(time.perf_counter() - t0, 4)
    meta["row_count"] = len(rows)
    return rows, meta


def build_strike_chains_by_month(
    flat_rows: List[Dict[str, Any]],
) -> Dict[str, List[Dict[str, Any]]]:
    """Group flat C/P rows into per-month strike buckets (call_*/put_*)."""
    by_month: Dict[str, Dict[float, Dict[str, Any]]] = {}
    for row in flat_rows:
        month = str(row.get("month") or "")
        strike = float(row.get("strike") or 0.0)
        if not month or strike <= 0:
            continue
        bucket = by_month.setdefault(month, {}).setdefault(
            strike,
            {
                "strike": strike,
                "call_mid": 0.0,
                "put_mid": 0.0,
                "call_oi": 0.0,
                "put_oi": 0.0,
                "call_last": 0.0,
                "put_last": 0.0,
                "call_bid": 0.0,
                "call_ask": 0.0,
                "put_bid": 0.0,
                "put_ask": 0.0,
                "call_iv": 0.0,
                "put_iv": 0.0,
                "expire_date": row.get("expire_date"),
            },
        )
        px = float(row.get("close") or 0.0)
        oi = float(row.get("open_interest") or 0.0)
        iv = float(row.get("iv") or 0.0)
        cp = str(row.get("cp") or "").upper()
        if cp in {"C", "CALL"}:
            bucket["call_mid"] = px
            bucket["call_last"] = px
            bucket["call_oi"] = oi
            bucket["call_iv"] = iv
        elif cp in {"P", "PUT"}:
            bucket["put_mid"] = px
            bucket["put_last"] = px
            bucket["put_oi"] = oi
            bucket["put_iv"] = iv
        if row.get("expire_date"):
            bucket["expire_date"] = row.get("expire_date")

    out: Dict[str, List[Dict[str, Any]]] = {}
    for month, strikes in by_month.items():
        rows = list(strikes.values())
        rows.sort(key=lambda item: float(item["strike"]))
        out[month] = rows
    return out



def fetch_option_chain_rows_via_view(
    code6: str,
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """Prefer the host view `v_opt_chain_latest` (one round-trip)."""
    code6 = str(code6 or "").strip()
    meta: Dict[str, Any] = {"source": "clickhouse_view", "view": "v_opt_chain_latest"}
    if not code6:
        return [], meta
    sql = f"""
    SELECT
      contract_code, contract_id, strike, cp, expire_date, expire_ym,
      close, open_interest, quote_ts, iv, delta, gamma, vega, theta, underlying_price
    FROM v_opt_chain_latest
    WHERE underlying_code = '{code6}'
    """
    t0 = time.perf_counter()
    try:
        cols, raw_rows = _ch_query(sql, timeout=20.0)
    except Exception as exc:
        logger.info("etf_options CH view query failed for %s: %s", code6, exc)
        return [], meta
    rows: List[Dict[str, Any]] = []
    for raw in raw_rows:
        item = dict(zip(cols, raw))
        rows.append(
            {
                "contract_code": str(item.get("contract_code") or ""),
                "contract_id": str(item.get("contract_id") or ""),
                "strike": _to_float(item.get("strike")),
                "cp": str(item.get("cp") or "").strip().upper(),
                "expire_date": item.get("expire_date"),
                "month": str(item.get("expire_ym") or _month_key_from_expire(item.get("expire_date"))),
                "close": _to_float(item.get("close")),
                "open_interest": _to_float(item.get("open_interest")),
                "iv": _to_float(item.get("iv")),
                "delta": _to_float(item.get("delta")),
                "gamma": _to_float(item.get("gamma")),
                "vega": _to_float(item.get("vega")),
                "theta": _to_float(item.get("theta")),
                "underlying_price": _to_float(item.get("underlying_price")),
                "quote_ts": item.get("quote_ts"),
            }
        )
    meta["elapsed_s"] = round(time.perf_counter() - t0, 4)
    meta["row_count"] = len(rows)
    return rows, meta


def try_load_etf_option_chains(code6: str) -> Optional[Dict[str, Any]]:
    """High-level helper: months + chains + underlying from ClickHouse, or None."""
    if not etf_options_ch_enabled():
        return None
    if not ch_ping():
        logger.info("etf_options CH ping failed url=%s", etf_options_ch_url())
        return None
    if not is_quote_data_fresh(code6):
        logger.info("etf_options CH data stale for %s", code6)
        return None

    flat_rows, meta = fetch_option_chain_rows_via_view(code6)
    if not flat_rows:
        flat_rows, meta = fetch_option_chain_rows(code6)
    if not flat_rows:
        return None

    chains_by_month = build_strike_chains_by_month(flat_rows)
    months = sorted(chains_by_month.keys())
    if not months:
        return None

    underlying, underlying_ts = fetch_underlying_spot(code6)
    if underlying <= 0:
        for row in flat_rows:
            up = float(row.get("underlying_price") or 0.0)
            if up > 0:
                underlying = up
                break

    month_meta: Dict[str, Dict[str, Any]] = {}
    for month, chain in chains_by_month.items():
        expire = None
        for row in chain:
            if row.get("expire_date"):
                expire = row.get("expire_date")
                break
        month_meta[month] = {
            "T": _t_from_expire(expire),
            "expire_date": expire,
            "multiplier": 10000.0,
        }

    return {
        "months": months,
        "chains_by_month": chains_by_month,
        "month_meta": month_meta,
        "underlying": underlying,
        "underlying_ts": underlying_ts,
        "source": "clickhouse",
        "meta": meta,
    }


_PLAYBACK_INTERVALS = {"1m", "30m", "day", "week"}
_PLAYBACK_BARS = {30, 60, 90, 240}


def normalize_playback_interval(value: Any) -> str:
    raw = str(value or "day").strip().lower()
    aliases = {
        "1": "1m",
        "1min": "1m",
        "1minute": "1m",
        "min": "1m",
        "30": "30m",
        "30min": "30m",
        "30minute": "30m",
        "d": "day",
        "1d": "day",
        "daily": "day",
        "w": "week",
        "1w": "week",
        "weekly": "week",
    }
    raw = aliases.get(raw, raw)
    return raw if raw in _PLAYBACK_INTERVALS else "day"


def normalize_playback_bars(value: Any) -> int:
    try:
        bars = int(value)
    except Exception:
        bars = 60
    if bars in _PLAYBACK_BARS:
        return bars
    # nearest allowed
    return min(_PLAYBACK_BARS, key=lambda x: abs(x - bars))


def _sql_ts_list(timestamps: List[str]) -> str:
    cleaned = []
    for ts in timestamps:
        text = str(ts or "").strip()[:19]
        if not text:
            continue
        cleaned.append("'" + text.replace("'", "") + "'")
    return ", ".join(cleaned) if cleaned else "''"


def list_playback_timestamps(
    code6: str,
    *,
    interval: str = "day",
    bars: int = 60,
) -> List[str]:
    """Return ascending timestamps (len <= bars) for GEX playback buckets."""
    code6 = str(code6 or "").strip()
    interval = normalize_playback_interval(interval)
    bars = normalize_playback_bars(bars)
    if not code6:
        return []

    # Playback stamps must come from opt_quotes_bar_1m, not opt_underlying_1m.
    # Underlying bars often extend to 15:00 while option quotes stop ~14:56;
    # using underlying max yields empty chains and gaps in capital/GEX history.
    if interval == "1m":
        sql = f"""
        SELECT ts_minute AS bucket_ts
        FROM opt_quotes_bar_1m
        WHERE underlying_code = '{code6}'
        GROUP BY ts_minute
        ORDER BY bucket_ts DESC
        LIMIT {bars}
        """
    elif interval == "30m":
        sql = f"""
        SELECT max(ts_minute) AS bucket_ts
        FROM opt_quotes_bar_1m
        WHERE underlying_code = '{code6}'
        GROUP BY toStartOfInterval(ts_minute, INTERVAL 30 MINUTE)
        ORDER BY bucket_ts DESC
        LIMIT {bars}
        """
    elif interval == "week":
        sql = f"""
        SELECT max(ts_minute) AS bucket_ts
        FROM opt_quotes_bar_1m
        WHERE underlying_code = '{code6}'
        GROUP BY toStartOfWeek(toDate(ts_minute), 1)
        ORDER BY bucket_ts DESC
        LIMIT {bars}
        """
    else:  # day
        sql = f"""
        SELECT max(ts_minute) AS bucket_ts
        FROM opt_quotes_bar_1m
        WHERE underlying_code = '{code6}'
        GROUP BY toDate(ts_minute)
        ORDER BY bucket_ts DESC
        LIMIT {bars}
        """
    try:
        cols, rows = _ch_query(sql, timeout=30.0)
    except Exception as exc:
        logger.warning("list_playback_timestamps failed code=%s: %s", code6, exc)
        return []
    out: List[str] = []
    for raw in rows:
        row = dict(zip(cols, raw))
        ts = str(row.get("bucket_ts") or row.get("ts_minute") or "").strip()[:19]
        if ts:
            out.append(ts)
    out.reverse()  # ascending for slider
    return out


def fetch_underlying_series(
    code6: str,
    timestamps: List[str],
) -> Dict[str, float]:
    """Map timestamp -> underlying price for exact playback minutes."""
    code6 = str(code6 or "").strip()
    if not code6 or not timestamps:
        return {}
    sql = f"""
    SELECT
      ts_minute,
      ifNull(last_price, close) AS px
    FROM opt_underlying_1m
    WHERE underlying_code = '{code6}'
      AND ts_minute IN ({_sql_ts_list(timestamps)})
    """
    try:
        cols, rows = _ch_query(sql, timeout=30.0)
    except Exception as exc:
        logger.warning("fetch_underlying_series failed code=%s: %s", code6, exc)
        return {}
    out: Dict[str, float] = {}
    for raw in rows:
        row = dict(zip(cols, raw))
        ts = str(row.get("ts_minute") or "").strip()[:19]
        px = _to_float(row.get("px"))
        if ts and px > 0:
            out[ts] = px
    return out


def fetch_option_chain_rows_at_timestamps(
    code6: str,
    timestamps: List[str],
) -> Tuple[Dict[str, List[Dict[str, Any]]], Dict[str, Any]]:
    """Bulk-load flat option rows for each playback timestamp.

    Uses exact-minute joins against quotes/analytics at the playback stamps,
    and contracts for the matching trade_date (or nearest prior listing day).
    """
    code6 = str(code6 or "").strip()
    meta: Dict[str, Any] = {"source": "clickhouse_playback", "timestamps": len(timestamps)}
    if not code6 or not timestamps:
        return {}, meta

    ts_sql = _sql_ts_list(timestamps)
    # ClickHouse disallows correlated subqueries that reference outer columns
    # in JOIN ON; map each stamp to the nearest prior trade_date via join.
    sql = f"""
    WITH
      stamps AS (
        SELECT toDateTime(arrayJoin([{ts_sql}]), 'Asia/Shanghai') AS ts_minute
      ),
      stamp_dates AS (
        SELECT ts_minute, toDate(ts_minute) AS d FROM stamps
      ),
      stamp_trade AS (
        SELECT
          sd.ts_minute AS ts_minute,
          max(c.trade_date) AS trade_date
        FROM stamp_dates sd
        CROSS JOIN opt_contracts_daily c
        WHERE c.underlying_code = '{code6}'
          AND c.trade_date <= sd.d
        GROUP BY sd.ts_minute
      ),
      contracts AS (
        SELECT
          st.ts_minute AS ts_minute,
          c.contract_code AS contract_code,
          c.contract_id AS contract_id,
          c.strike AS strike,
          c.cp AS cp,
          c.expire_date AS expire_date
        FROM stamp_trade st
        INNER JOIN opt_contracts_daily c
          ON c.underlying_code = '{code6}'
         AND c.trade_date = st.trade_date
        WHERE c.contract_id IS NOT NULL AND c.contract_id != ''
      )
    SELECT
      ct.ts_minute AS ts_minute,
      ct.contract_code AS contract_code,
      ct.contract_id AS contract_id,
      ct.strike AS strike,
      ct.cp AS cp,
      ct.expire_date AS expire_date,
      q.close AS close,
      q.open_interest AS open_interest,
      a.iv AS iv,
      a.gamma AS gamma,
      a.underlying_price AS underlying_price
    FROM contracts ct
    INNER JOIN (
      SELECT
        ts_minute,
        toString(ifNull(nullIf(contract_id, ''), contract_code)) AS jid,
        close,
        open_interest
      FROM opt_quotes_bar_1m
      WHERE underlying_code = '{code6}'
        AND ts_minute IN ({ts_sql})
    ) q ON q.ts_minute = ct.ts_minute
       AND q.jid = toString(ct.contract_id)
    LEFT JOIN (
      SELECT
        ts_minute,
        toString(ifNull(nullIf(contract_id, ''), contract_code)) AS jid,
        iv,
        gamma,
        underlying_price
      FROM opt_analytics_1m
      WHERE underlying_code = '{code6}'
        AND ts_minute IN ({ts_sql})
    ) a ON a.ts_minute = ct.ts_minute
       AND a.jid = toString(ct.contract_id)
    SETTINGS max_execution_time = 90
    """
    t0 = time.perf_counter()
    try:
        cols, raw_rows = _ch_query(sql, timeout=100.0)
    except Exception as exc:
        logger.warning("fetch_option_chain_rows_at_timestamps failed code=%s: %s", code6, exc)
        meta["error"] = str(exc)
        return {}, meta

    by_ts: Dict[str, List[Dict[str, Any]]] = {}
    for raw in raw_rows:
        item = dict(zip(cols, raw))
        ts = str(item.get("ts_minute") or "").strip()[:19]
        if not ts:
            continue
        by_ts.setdefault(ts, []).append(
            {
                "contract_code": str(item.get("contract_code") or ""),
                "contract_id": str(item.get("contract_id") or ""),
                "strike": _to_float(item.get("strike")),
                "cp": str(item.get("cp") or "").strip().upper(),
                "expire_date": item.get("expire_date"),
                "month": _month_key_from_expire(item.get("expire_date")),
                "close": _to_float(item.get("close")),
                "open_interest": _to_float(item.get("open_interest")),
                "iv": _to_float(item.get("iv")),
                "gamma": _to_float(item.get("gamma")),
                "underlying_price": _to_float(item.get("underlying_price")),
                "quote_ts": ts,
            }
        )
    meta["elapsed_s"] = round(time.perf_counter() - t0, 4)
    meta["row_count"] = sum(len(v) for v in by_ts.values())
    meta["stamp_count"] = len(by_ts)
    return by_ts, meta
