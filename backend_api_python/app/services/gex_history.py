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
    list_playback_bucket_bounds,
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
    code6 = _surface_code6(code6)
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


# ---------------------------------------------------------------------------
# ETF options surface history (IV smile / OI / TV yield / Max Pain)
# ---------------------------------------------------------------------------

_SURFACE_CHARTS = {
    "options.iv",
    "options.oi",
    "options.tv",
    "options.maxPain",
    "options.max_pain",
}


def is_etf_surface_history_chart(chart_key: str) -> bool:
    return str(chart_key or "").strip() in _SURFACE_CHARTS




def _near_month_atm_iv_from_smile(
    iv_smile: List[Dict[str, Any]],
    underlying: float,
) -> Optional[float]:
    """Average call/put IV at the strike nearest to underlying."""
    spot = float(underlying or 0.0)
    if spot <= 0:
        return None
    by_strike: Dict[float, Dict[str, float]] = {}
    for point in iv_smile or []:
        try:
            strike = float(point.get("strike") or 0.0)
            iv = float(point.get("iv") or 0.0)
        except (TypeError, ValueError):
            continue
        if strike <= 0 or iv <= 0:
            continue
        side = str(point.get("side") or "").strip().lower()
        bucket = by_strike.setdefault(strike, {})
        if side in {"call", "c"}:
            bucket["call"] = iv
        elif side in {"put", "p"}:
            bucket["put"] = iv
        else:
            bucket.setdefault("other", iv)
    if not by_strike:
        return None
    nearest = min(by_strike.keys(), key=lambda k: abs(k - spot))
    vals = [v for v in by_strike[nearest].values() if v and v > 0]
    if not vals:
        return None
    return float(sum(vals) / len(vals))


def _near_month_atm_iv_from_flat(
    flat_rows: List[Dict[str, Any]],
    *,
    underlying: float,
    asof: datetime,
    month: str = "all",
) -> Tuple[Optional[str], Optional[float]]:
    """Pick near-month ATM IV from flat ClickHouse contract rows."""
    spot = float(underlying or 0.0)
    if spot <= 0 or not flat_rows:
        return None, None

    month_raw = str(month or "all").strip().lower()
    asof_d = asof.date() if isinstance(asof, datetime) else date.today()
    by_month: Dict[str, List[Dict[str, Any]]] = {}
    for row in flat_rows:
        mkey = str(row.get("month") or "").strip()
        if not mkey:
            continue
        if month_raw not in {"", "all", "*", "全部"}:
            wanted = str(month or "").strip()
            if mkey != wanted and not mkey.endswith(wanted[-4:]):
                continue
        by_month.setdefault(mkey, []).append(row)
    if not by_month:
        return None, None

    def _month_still_live(rows: List[Dict[str, Any]]) -> bool:
        for row in rows:
            exp = _parse_ts(str(row.get("expire_date") or ""))
            if exp is None and row.get("expire_date"):
                try:
                    exp_d = datetime.strptime(str(row.get("expire_date"))[:10], "%Y-%m-%d").date()
                    return exp_d >= asof_d
                except Exception:
                    continue
            if exp and exp.date() >= asof_d:
                return True
        return True

    ranked = sorted(by_month.keys())
    near_month = None
    for mkey in ranked:
        if _month_still_live(by_month[mkey]):
            near_month = mkey
            break
    if near_month is None:
        near_month = ranked[0]
    rows = by_month.get(near_month) or []
    if not rows:
        return near_month, None

    strikes = sorted(
        {float(r.get("strike") or 0.0) for r in rows if float(r.get("strike") or 0.0) > 0}
    )
    if not strikes:
        return near_month, None
    atm = min(strikes, key=lambda k: abs(k - spot))
    ivs: List[float] = []
    for row in rows:
        if abs(float(row.get("strike") or 0.0) - atm) > 1e-9:
            continue
        iv = float(row.get("iv") or 0.0)
        if iv > 0:
            ivs.append(iv)
    if ivs:
        return near_month, float(sum(ivs) / len(ivs))

    chains = build_strike_chains_by_month(rows)
    chain = chains.get(near_month) or []
    if not chain:
        return near_month, None
    expire = next((_surface_row_expire(r) for r in chain if _surface_row_expire(r)), None)
    raw = compute_gex_raw(
        chain,
        underlying=spot,
        multiplier=_DEFAULT_MULT,
        T=_t_years(expire, asof),
    )
    smile_iv = _near_month_atm_iv_from_smile(list(raw.get("iv_smile") or []), spot)
    return near_month, smile_iv


def _near_month_max_pain_point(slice_row: Dict[str, Any]) -> Dict[str, Any]:
    """Extract near-month max-pain strike + underlying from one surface slice."""
    month_series = list(slice_row.get("month_series") or [])
    month_key = None
    max_pain = None
    if month_series:
        month_key = month_series[0].get("month")
        max_pain = month_series[0].get("max_pain")
    if not isinstance(max_pain, dict):
        max_pain = slice_row.get("max_pain")
    strike = None
    if isinstance(max_pain, dict) and max_pain.get("strike") is not None:
        try:
            strike = float(max_pain.get("strike"))
        except (TypeError, ValueError):
            strike = None
    underlying = slice_row.get("underlying")
    if underlying is None:
        underlying = slice_row.get("current_price")
    try:
        underlying_f = float(underlying) if underlying is not None else None
    except (TypeError, ValueError):
        underlying_f = None
    if underlying_f is not None and underlying_f <= 0:
        underlying_f = None
    return {
        "ts": slice_row.get("ts"),
        "label": slice_row.get("label") or slice_row.get("ts"),
        "date": str(slice_row.get("date") or (slice_row.get("ts") or ""))[:10],
        "month": month_key,
        "max_pain": strike,
        "underlying": underlying_f,
    }


def _build_near_month_max_pain_series(
    slices: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """Time series of near-month max pain vs underlying over playback slices."""
    return [_near_month_max_pain_point(item) for item in (slices or [])]


def _build_near_month_iv_klines(
    bounds: List[Dict[str, str]],
    by_ts: Dict[str, List[Dict[str, Any]]],
    underlyings: Dict[str, float],
    *,
    month: str = "all",
) -> List[Dict[str, Any]]:
    """Build near-month ATM IV OHLC candles aligned to playback buckets."""
    out: List[Dict[str, Any]] = []
    prev_close: Optional[float] = None
    for bound in bounds or []:
        open_ts = str(bound.get("open_ts") or "").strip()[:19]
        close_ts = str(bound.get("close_ts") or "").strip()[:19]
        if not close_ts:
            continue
        if not open_ts:
            open_ts = close_ts
        open_dt = _parse_ts(open_ts) or datetime.now()
        close_dt = _parse_ts(close_ts) or open_dt
        open_spot = float(underlyings.get(open_ts) or 0.0)
        close_spot = float(underlyings.get(close_ts) or 0.0)
        open_flat = by_ts.get(open_ts) or []
        close_flat = by_ts.get(close_ts) or []
        if open_spot <= 0:
            for row in open_flat:
                up = float(row.get("underlying_price") or 0.0)
                if up > 0:
                    open_spot = up
                    break
        if close_spot <= 0:
            for row in close_flat:
                up = float(row.get("underlying_price") or 0.0)
                if up > 0:
                    close_spot = up
                    break
        open_month, open_iv = _near_month_atm_iv_from_flat(
            open_flat,
            underlying=open_spot or close_spot,
            asof=open_dt,
            month=month,
        )
        close_month, close_iv = _near_month_atm_iv_from_flat(
            close_flat,
            underlying=close_spot or open_spot,
            asof=close_dt,
            month=month,
        )
        if open_iv is None and close_iv is None:
            out.append(
                {
                    "ts": close_ts,
                    "label": close_ts,
                    "date": close_ts[:10],
                    "month": close_month or open_month,
                    "open": None,
                    "high": None,
                    "low": None,
                    "close": None,
                    "underlying": close_spot or open_spot or None,
                }
            )
            continue
        close_v = float(close_iv if close_iv is not None else open_iv)
        if open_iv is not None:
            open_v = float(open_iv)
        elif prev_close is not None:
            open_v = float(prev_close)
        else:
            open_v = close_v
        high_v = max(open_v, close_v)
        low_v = min(open_v, close_v)
        prev_close = close_v
        out.append(
            {
                "ts": close_ts,
                "label": close_ts,
                "date": close_ts[:10],
                "month": close_month or open_month,
                "open": open_v,
                "high": high_v,
                "low": low_v,
                "close": close_v,
                "underlying": close_spot or open_spot or None,
            }
        )
    return out


def _surface_code6(root: str) -> str:
    digits = "".join(ch for ch in str(root or "") if ch.isdigit())
    return digits[:6]


def _surface_filter_months(
    chains_by_month: Dict[str, List[Dict[str, Any]]],
    month: str,
) -> Dict[str, List[Dict[str, Any]]]:
    month_raw = str(month or "all").strip().lower()
    if month_raw in {"", "all", "*", "全部"}:
        return dict(chains_by_month or {})
    wanted = str(month or "").strip()
    out = {
        key: rows
        for key, rows in (chains_by_month or {}).items()
        if str(key) == wanted or str(key).endswith(wanted[-4:])
    }
    return out or dict(chains_by_month or {})


def _surface_oi_distribution(chain: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    points: List[Dict[str, Any]] = []
    for row in chain or []:
        strike = float(row.get("strike") or 0.0)
        if strike <= 0:
            continue
        call_oi = float(row.get("call_oi") or 0.0)
        put_oi = float(row.get("put_oi") or 0.0)
        points.append(
            {
                "strike": strike,
                "call_oi": call_oi,
                "put_oi": put_oi,
                "total_oi": call_oi + put_oi,
                "net_oi": call_oi - put_oi,
            }
        )
    points.sort(key=lambda item: item["strike"])
    return points


def _surface_row_expire(row: Dict[str, Any]) -> Any:
    return (
        row.get("expire_date")
        or row.get("expiry_date")
        or row.get("expire")
        or row.get("expiry")
    )


def _compute_surface_slice(
    flat_rows: List[Dict[str, Any]],
    *,
    underlying: float,
    asof: datetime,
    multiplier: float,
    month: str,
) -> Dict[str, Any]:
    from app.services.cn_derivatives_analytics import compute_max_pain
    from app.services.cn_derivatives_etf_capital import compute_etf_time_value_annualized_yield

    chains_by_month = _surface_filter_months(build_strike_chains_by_month(flat_rows), month)
    month_series: List[Dict[str, Any]] = []
    agg_chain: List[Dict[str, Any]] = []
    oi_by_strike: Dict[float, Dict[str, float]] = {}

    for month_key, chain in sorted(chains_by_month.items()):
        if not chain:
            continue
        expire = next((_surface_row_expire(row) for row in chain if _surface_row_expire(row)), None)
        t_years = _t_years(expire, asof)
        raw = compute_gex_raw(
            chain,
            underlying=underlying,
            multiplier=multiplier,
            T=t_years,
        )
        smile = list(raw.get("iv_smile") or [])
        oi_points = _surface_oi_distribution(chain)
        tv_yield = compute_etf_time_value_annualized_yield(
            chain,
            underlying=underlying,
            multiplier=multiplier,
            margin_rate=0.15,
            T=t_years,
            month=month_key,
        )
        max_pain = compute_max_pain(chain)
        month_series.append(
            {
                "month": month_key,
                "T": t_years,
                "iv_smile": smile,
                "gex_distribution": list(raw.get("points") or []),
                "time_value_yield": tv_yield,
                "max_pain": max_pain,
            }
        )
        agg_chain.extend(chain)
        for point in oi_points:
            strike = float(point["strike"])
            cur = oi_by_strike.get(strike)
            if not cur:
                oi_by_strike[strike] = {
                    "strike": strike,
                    "call_oi": float(point.get("call_oi") or 0.0),
                    "put_oi": float(point.get("put_oi") or 0.0),
                }
            else:
                cur["call_oi"] += float(point.get("call_oi") or 0.0)
                cur["put_oi"] += float(point.get("put_oi") or 0.0)

    agg_oi: List[Dict[str, Any]] = []
    for strike in sorted(oi_by_strike):
        cur = oi_by_strike[strike]
        call_oi = float(cur.get("call_oi") or 0.0)
        put_oi = float(cur.get("put_oi") or 0.0)
        agg_oi.append(
            {
                "strike": strike,
                "call_oi": call_oi,
                "put_oi": put_oi,
                "total_oi": call_oi + put_oi,
                "net_oi": call_oi - put_oi,
            }
        )

    primary = month_series[0] if month_series else {}
    return {
        "current_price": underlying,
        "underlying": underlying,
        "iv_smile": primary.get("iv_smile") or [],
        "gex_distribution": agg_oi,
        "month_series": month_series,
        "max_pain": compute_max_pain(agg_chain) if agg_chain else primary.get("max_pain"),
        "time_value_yield": primary.get("time_value_yield") or {},
    }


def _surface_live_fallback_slice(code6: str, month: str) -> Dict[str, Any]:
    from app.services.cn_derivatives_etf import build_etf_options_panel

    panel = build_etf_options_panel(code6, month=month)
    asof = datetime.now().isoformat(timespec="seconds")
    return {
        "ts": asof,
        "date": asof[:10],
        "label": "当前",
        "current_price": panel.get("current_price") or panel.get("underlying"),
        "underlying": panel.get("underlying") or panel.get("current_price"),
        "iv_smile": panel.get("iv_smile") or [],
        "gex_distribution": panel.get("gex_distribution") or [],
        "month_series": panel.get("month_series") or [],
        "max_pain": panel.get("max_pain"),
        "time_value_yield": panel.get("time_value_yield") or {},
        "month": panel.get("month"),
    }


def build_etf_options_surface_history(
    root: str,
    *,
    chart_key: str = "options.iv",
    interval: str = "day",
    bars: int = 60,
    month: str = "all",
    multiplier: float = _DEFAULT_MULT,
) -> Dict[str, Any]:
    """Replay ETF option surfaces from ClickHouse for IV / OI / TV / Max Pain."""
    code6 = _surface_code6(root)
    chart = str(chart_key or "options.iv").strip() or "options.iv"
    interval_n = normalize_playback_interval(interval)
    bars_n = normalize_playback_bars(bars)
    asof = datetime.now().isoformat(timespec="seconds")
    want_iv_klines = chart == "options.iv"
    want_max_pain_series = chart in {"options.maxPain", "options.max_pain"}
    empty: Dict[str, Any] = {
        "root": code6,
        "chart_key": chart,
        "mode": "slices",
        "interval": interval_n,
        "bars": bars_n,
        "slices": [],
        "near_month_iv_klines": [],
        "near_month_max_pain_series": [],
        "note": "",
        "asof": asof,
    }
    if not code6:
        empty["note"] = "missing underlying code"
        return empty

    def _fallback_klines(live: Dict[str, Any]) -> List[Dict[str, Any]]:
        atm = _near_month_atm_iv_from_smile(
            list(live.get("iv_smile") or []),
            float(live.get("underlying") or live.get("current_price") or 0.0),
        )
        month_key = None
        ms = live.get("month_series") or []
        if ms:
            month_key = ms[0].get("month")
            if atm is None:
                atm = _near_month_atm_iv_from_smile(
                    list(ms[0].get("iv_smile") or []),
                    float(live.get("underlying") or live.get("current_price") or 0.0),
                )
        if atm is None:
            return []
        return [
            {
                "ts": live.get("ts"),
                "label": live.get("label") or live.get("ts"),
                "date": str(live.get("date") or (live.get("ts") or ""))[:10],
                "month": month_key,
                "open": atm,
                "high": atm,
                "low": atm,
                "close": atm,
                "underlying": live.get("underlying") or live.get("current_price"),
            }
        ]

    if not etf_options_ch_enabled() or not ch_ping():
        try:
            live = _surface_live_fallback_slice(code6, month)
            empty["slices"] = [live]
            empty["note"] = (
                "ClickHouse 不可用，已回退为当前 ETF 期权截面；"
                "恢复本地期权库后可按频率滑动回放 IV Smile / OI / 时间价值 / Max Pain。"
            )
            if want_iv_klines:
                empty["near_month_iv_klines"] = _fallback_klines(live)
            if want_max_pain_series:
                empty["near_month_max_pain_series"] = _build_near_month_max_pain_series([live])
        except Exception as exc:
            empty["note"] = f"ETF options history unavailable: {exc}"
        return empty

    bounds: List[Dict[str, str]] = []
    if want_iv_klines:
        bounds = list_playback_bucket_bounds(code6, interval=interval_n, bars=bars_n)
        timestamps = [
            str(item.get("close_ts") or "").strip()[:19]
            for item in bounds
            if item.get("close_ts")
        ]
        open_ts = [
            str(item.get("open_ts") or "").strip()[:19]
            for item in bounds
            if item.get("open_ts")
        ]
        fetch_ts = sorted({*timestamps, *open_ts})
    else:
        timestamps = list_playback_timestamps(code6, interval=interval_n, bars=bars_n)
        fetch_ts = list(timestamps)

    if not timestamps:
        try:
            live = _surface_live_fallback_slice(code6, month)
            empty["slices"] = [live]
            empty["note"] = "ClickHouse 无回放时间点，已回退为当前截面。"
            if want_iv_klines:
                empty["near_month_iv_klines"] = _fallback_klines(live)
            if want_max_pain_series:
                empty["near_month_max_pain_series"] = _build_near_month_max_pain_series([live])
        except Exception as exc:
            empty["note"] = f"no playback timestamps: {exc}"
        return empty

    underlyings = fetch_underlying_series(code6, fetch_ts)
    by_ts, meta = fetch_option_chain_rows_at_timestamps(code6, fetch_ts)

    slices: List[Dict[str, Any]] = []
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
        if not flat or spot <= 0:
            slices.append(
                {
                    "ts": ts,
                    "date": ts[:10],
                    "label": ts,
                    "underlying": spot or None,
                    "current_price": spot or None,
                    "iv_smile": [],
                    "gex_distribution": [],
                    "month_series": [],
                    "max_pain": None,
                    "time_value_yield": {},
                }
            )
            continue
        try:
            payload = _compute_surface_slice(
                flat,
                underlying=spot,
                asof=asof_dt,
                multiplier=multiplier,
                month=month,
            )
        except Exception as exc:
            logger.warning("ETF surface slice failed code=%s ts=%s: %s", code6, ts, exc)
            slices.append(
                {
                    "ts": ts,
                    "date": ts[:10],
                    "label": ts,
                    "underlying": spot,
                    "current_price": spot,
                    "iv_smile": [],
                    "gex_distribution": [],
                    "month_series": [],
                    "max_pain": None,
                    "time_value_yield": {},
                }
            )
            continue
        slices.append(
            {
                "ts": ts,
                "date": ts[:10],
                "label": ts,
                "underlying": spot,
                "current_price": spot,
                **payload,
            }
        )

    near_month_iv_klines: List[Dict[str, Any]] = []
    if want_iv_klines:
        if not bounds:
            bounds = [{"open_ts": ts, "close_ts": ts, "label": ts} for ts in timestamps]
        near_month_iv_klines = _build_near_month_iv_klines(
            bounds,
            by_ts,
            underlyings,
            month=month,
        )
        by_close = {str(item.get("ts") or ""): item for item in slices}
        for candle in near_month_iv_klines:
            if candle.get("close") is not None:
                continue
            slice_row = by_close.get(str(candle.get("ts") or "")) or {}
            smile = list(slice_row.get("iv_smile") or [])
            if not smile:
                ms = slice_row.get("month_series") or []
                if ms:
                    smile = list(ms[0].get("iv_smile") or [])
                    if not candle.get("month"):
                        candle["month"] = ms[0].get("month")
            atm = _near_month_atm_iv_from_smile(
                smile,
                float(slice_row.get("underlying") or slice_row.get("current_price") or 0.0),
            )
            if atm is None:
                continue
            open_v = float(candle["open"]) if candle.get("open") is not None else atm
            candle["open"] = open_v
            candle["close"] = atm
            candle["high"] = max(open_v, atm)
            candle["low"] = min(open_v, atm)

    loaded = sum(1 for item in slices if item.get("month_series"))
    note = (
        f"按 {interval_n} 取最近 {bars_n} 根，用 ClickHouse 期权分钟切片回放 "
        f"IV Smile / OI / 时间价值年化 / Max Pain；loaded={loaded}/{len(timestamps)}。"
    )
    near_month_max_pain_series: List[Dict[str, Any]] = []
    if want_max_pain_series:
        near_month_max_pain_series = _build_near_month_max_pain_series(slices)
        filled_mp = sum(1 for p in near_month_max_pain_series if p.get("max_pain") is not None)
        note += f" 近月MaxPain折线={filled_mp}/{len(near_month_max_pain_series)}。"
    if want_iv_klines:
        filled = sum(1 for c in near_month_iv_klines if c.get("close") is not None)
        note += f" 近月IV K线={filled}/{len(near_month_iv_klines)}。"
    if isinstance(meta, dict) and meta.get("error"):
        note += f" meta_error={meta.get('error')}"

    result: Dict[str, Any] = {
        "root": code6,
        "chart_key": chart,
        "mode": "slices",
        "interval": interval_n,
        "bars": bars_n,
        "slices": slices,
        "note": note,
        "asof": asof,
        "meta": meta,
    }
    if want_iv_klines:
        result["near_month_iv_klines"] = near_month_iv_klines
    if want_max_pain_series:
        result["near_month_max_pain_series"] = near_month_max_pain_series
    return result

