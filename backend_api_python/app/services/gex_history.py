"""GEX distribution history playback from ETF option minute chains."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any, Dict, List, Optional, Tuple

from app.services.etf_options_clickhouse import (
    build_strike_chains_by_month,
    ch_ping,
    etf_options_ch_enabled,
    fetch_option_chain_rows_at_timestamps,
    fetch_underlying_series,
    list_playback_timestamps,
    normalize_playback_bars,
    normalize_playback_interval,
)
from app.services.gex_indicator import (
    compute_gex_raw,
    derive_gex_levels,
    indicator_from_gex_points,
    panel_fields_from_gex_indicator,
    summary_from_gex_points,
)
from app.utils.logger import get_logger

logger = get_logger(__name__)

_DEFAULT_MULT = 10000.0


def _parse_ts(value: str) -> Optional[datetime]:
    text = str(value or "").strip()[:19]
    if not text:
        return None
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue
    return None


def _t_years(expire_date: Any, asof: datetime) -> float:
    if expire_date is None:
        return 30 / 365.0
    if isinstance(expire_date, datetime):
        exp = expire_date.date()
    elif isinstance(expire_date, date):
        exp = expire_date
    else:
        text = str(expire_date).strip()[:10]
        try:
            exp = datetime.strptime(text, "%Y-%m-%d").date()
        except ValueError:
            return 30 / 365.0
    return max((exp - asof.date()).days, 1) / 365.0


def _enrich_chains(
    flat_rows: List[Dict[str, Any]],
) -> Tuple[List[Dict[str, Any]], Dict[str, List[Dict[str, Any]]]]:
    gamma_map: Dict[Tuple[str, float, str], float] = {}
    for row in flat_rows or []:
        month = str(row.get("month") or "")
        strike = float(row.get("strike") or 0.0)
        cp = str(row.get("cp") or "").upper()
        if not month or strike <= 0:
            continue
        side = "C" if cp in {"C", "CALL"} else ("P" if cp in {"P", "PUT"} else "")
        if side:
            gamma_map[(month, strike, side)] = float(row.get("gamma") or 0.0)

    chains_by_month = build_strike_chains_by_month(flat_rows)
    all_rows: List[Dict[str, Any]] = []
    for month, rows in chains_by_month.items():
        enriched = []
        for row in rows:
            item = dict(row)
            k = float(item.get("strike") or 0.0)
            item["call_gamma"] = gamma_map.get((month, k, "C"), 0.0)
            item["put_gamma"] = gamma_map.get((month, k, "P"), 0.0)
            item["month"] = month
            enriched.append(item)
            all_rows.append(item)
        chains_by_month[month] = enriched
    return all_rows, chains_by_month


def _aggregate_points(groups: List[List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
    bucket: Dict[float, Dict[str, float]] = {}
    for points in groups:
        for row in points or []:
            k = float(row.get("strike") or 0.0)
            if k <= 0:
                continue
            item = bucket.setdefault(
                k,
                {
                    "strike": k,
                    "call_oi": 0.0,
                    "put_oi": 0.0,
                    "call_gex": 0.0,
                    "put_gex": 0.0,
                    "net_gex": 0.0,
                },
            )
            item["call_oi"] += float(row.get("call_oi") or 0.0)
            item["put_oi"] += float(row.get("put_oi") or 0.0)
            item["call_gex"] += float(row.get("call_gex") or 0.0)
            item["put_gex"] += float(row.get("put_gex") or 0.0)
            item["net_gex"] += float(
                row.get("net_gex")
                if row.get("net_gex") is not None
                else (float(row.get("call_gex") or 0.0) + float(row.get("put_gex") or 0.0))
            )
    points = list(bucket.values())
    for p in points:
        p["total_oi"] = float(p["call_oi"]) + float(p["put_oi"])
        p["net_oi"] = float(p["call_oi"]) - float(p["put_oi"])
    points.sort(key=lambda p: p["strike"])
    return points


def _points_from_gamma(
    chain: List[Dict[str, Any]],
    *,
    underlying: float,
    multiplier: float,
) -> List[Dict[str, Any]]:
    spot = float(underlying or 0.0)
    mult = float(multiplier or _DEFAULT_MULT)
    if spot <= 0:
        return []
    groups: List[List[Dict[str, Any]]] = []
    # one "group" after summing months inside
    local: List[Dict[str, Any]] = []
    by_strike: Dict[float, Dict[str, float]] = {}
    for row in chain or []:
        k = float(row.get("strike") or 0.0)
        if k <= 0:
            continue
        item = by_strike.setdefault(
            k,
            {
                "strike": k,
                "call_oi": 0.0,
                "put_oi": 0.0,
                "call_gex": 0.0,
                "put_gex": 0.0,
                "net_gex": 0.0,
            },
        )
        call_oi = float(row.get("call_oi") or 0.0)
        put_oi = float(row.get("put_oi") or 0.0)
        call_gamma = float(row.get("call_gamma") or 0.0)
        put_gamma = float(row.get("put_gamma") or 0.0)
        item["call_oi"] += call_oi
        item["put_oi"] += put_oi
        item["call_gex"] += call_gamma * call_oi * mult * spot
        item["put_gex"] += -put_gamma * put_oi * mult * spot
        item["net_gex"] = item["call_gex"] + item["put_gex"]
    local = list(by_strike.values())
    for p in local:
        p["total_oi"] = float(p["call_oi"]) + float(p["put_oi"])
        p["net_oi"] = float(p["call_oi"]) - float(p["put_oi"])
    local.sort(key=lambda p: p["strike"])
    groups.append(local)
    return groups[0]


def _points_from_bs(
    chain: List[Dict[str, Any]],
    *,
    underlying: float,
    asof: datetime,
    multiplier: float,
) -> List[Dict[str, Any]]:
    by_month: Dict[str, List[Dict[str, Any]]] = {}
    for row in chain or []:
        by_month.setdefault(str(row.get("month") or "ALL"), []).append(row)
    groups: List[List[Dict[str, Any]]] = []
    for rows in by_month.values():
        expire = next((r.get("expire_date") for r in rows if r.get("expire_date")), None)
        raw = compute_gex_raw(
            rows,
            underlying=underlying,
            multiplier=multiplier,
            T=_t_years(expire, asof),
        )
        groups.append(list(raw.get("points") or []))
    return _aggregate_points(groups)


def _compute_slice_gex(
    flat_rows: List[Dict[str, Any]],
    *,
    underlying: float,
    asof: datetime,
    multiplier: float = _DEFAULT_MULT,
) -> Dict[str, Any]:
    chain, chains_by_month = _enrich_chains(flat_rows)
    gamma_hits = sum(
        1
        for row in chain
        if float(row.get("call_gamma") or 0.0) > 0 or float(row.get("put_gamma") or 0.0) > 0
    )
    use_gamma = gamma_hits >= max(3, len(chain) // 4)
    if use_gamma:
        points = _points_from_gamma(chain, underlying=underlying, multiplier=multiplier)
    else:
        points = _points_from_bs(
            chain,
            underlying=underlying,
            asof=asof,
            multiplier=multiplier,
        )

    levels = derive_gex_levels(points, underlying=underlying)
    summary = summary_from_gex_points(points, underlying=underlying)
    for key in ("call_wall", "put_wall", "pin", "flip"):
        summary[key] = levels.get(key)
    indicator = indicator_from_gex_points(
        points,
        underlying=underlying,
        multiplier=multiplier,
        T=30 / 365.0,
        name="GEX",
    )
    fields = panel_fields_from_gex_indicator(indicator)

    month_series: List[Dict[str, Any]] = []
    for month, rows in sorted(chains_by_month.items()):
        try:
            if use_gamma:
                m_points = _points_from_gamma(rows, underlying=underlying, multiplier=multiplier)
            else:
                expire = next((r.get("expire_date") for r in rows if r.get("expire_date")), None)
                raw = compute_gex_raw(
                    rows,
                    underlying=underlying,
                    multiplier=multiplier,
                    T=_t_years(expire, asof),
                )
                m_points = list(raw.get("points") or [])
        except Exception:
            m_points = []
        month_series.append({"month": month, "gex_distribution": m_points})

    return {
        "gex_distribution": fields.get("gex_distribution") or points,
        "gex_summary": fields.get("gex_summary") or summary,
        "month_series": month_series,
        "levels": levels,
        "underlying": underlying,
    }


def build_gex_playback_history(
    code6: str,
    *,
    interval: str = "day",
    bars: int = 60,
    multiplier: float = _DEFAULT_MULT,
) -> Dict[str, Any]:
    """Build GEX playback slices + Call/Put Wall / Flip / Pin time series."""
    code6 = str(code6 or "").strip()
    interval = normalize_playback_interval(interval)
    bars = normalize_playback_bars(bars)
    asof = datetime.now().isoformat(timespec="seconds")
    empty = {
        "root": code6,
        "chart_key": "options.gex",
        "mode": "gex_playback",
        "interval": interval,
        "bars": bars,
        "slices": [],
        "levels_series": [],
        "asof": asof,
    }

    if not code6:
        empty["note"] = "missing underlying code"
        return empty
    if not etf_options_ch_enabled() or not ch_ping():
        empty["note"] = "ETF options ClickHouse unavailable"
        return empty

    timestamps = list_playback_timestamps(code6, interval=interval, bars=bars)
    if not timestamps:
        empty["note"] = "no playback timestamps in ClickHouse for this underlying/interval"
        return empty

    underlyings = fetch_underlying_series(code6, timestamps)
    by_ts, meta = fetch_option_chain_rows_at_timestamps(code6, timestamps)

    slices: List[Dict[str, Any]] = []
    levels_series: List[Dict[str, Any]] = []
    for ts in timestamps:
        asof_dt = _parse_ts(ts) or datetime.now()
        spot = float(underlyings.get(ts) or 0.0)
        flat = by_ts.get(ts) or []
        if spot <= 0:
            for row in flat:
                up = float(row.get("underlying_price") or 0.0)
                if up > 0:
                    spot = up
                    break
        # Keep slices[] and levels_series[] index-aligned for the playback slider.
        if not flat or spot <= 0:
            slices.append(
                {
                    "ts": ts,
                    "date": ts[:10],
                    "label": ts,
                    "underlying": spot or None,
                    "current_price": spot or None,
                    "gex_distribution": [],
                    "gex_summary": {},
                    "month_series": [],
                }
            )
            levels_series.append(
                {
                    "ts": ts,
                    "label": ts,
                    "underlying": spot or None,
                    "call_wall": None,
                    "put_wall": None,
                    "flip": None,
                    "pin": None,
                }
            )
            continue
        try:
            payload = _compute_slice_gex(
                flat,
                underlying=spot,
                asof=asof_dt,
                multiplier=multiplier,
            )
        except Exception as exc:
            logger.warning("GEX slice failed code=%s ts=%s: %s", code6, ts, exc)
            slices.append(
                {
                    "ts": ts,
                    "date": ts[:10],
                    "label": ts,
                    "underlying": spot,
                    "current_price": spot,
                    "gex_distribution": [],
                    "gex_summary": {},
                    "month_series": [],
                }
            )
            levels_series.append(
                {
                    "ts": ts,
                    "label": ts,
                    "underlying": spot,
                    "call_wall": None,
                    "put_wall": None,
                    "flip": None,
                    "pin": None,
                }
            )
            continue

        levels = payload.get("levels") or {}
        slices.append(
            {
                "ts": ts,
                "date": ts[:10],
                "label": ts,
                "underlying": spot,
                "current_price": spot,
                "gex_distribution": payload.get("gex_distribution") or [],
                "gex_summary": payload.get("gex_summary") or {},
                "month_series": payload.get("month_series") or [],
            }
        )
        levels_series.append(
            {
                "ts": ts,
                "label": ts,
                "underlying": spot,
                "call_wall": levels.get("call_wall"),
                "put_wall": levels.get("put_wall"),
                "flip": levels.get("flip"),
                "pin": levels.get("pin"),
            }
        )

    note = (
        f"按 {interval} 取最近 {bars} 根，用 ClickHouse 期权分钟切片回放 GEX；"
        f"下方为标的价格与 Call/Put Wall、Gamma Flip、Pin 时间序列。"
        f" loaded={sum(1 for s in slices if s.get('gex_distribution'))}/{len(timestamps)}"
    )
    if meta.get("error"):
        note += f" meta_error={meta.get('error')}"

    return {
        "root": code6,
        "chart_key": "options.gex",
        "mode": "gex_playback",
        "interval": interval,
        "bars": bars,
        "slices": slices,
        "levels_series": levels_series,
        "note": note,
        "asof": asof,
        "meta": meta,
    }
