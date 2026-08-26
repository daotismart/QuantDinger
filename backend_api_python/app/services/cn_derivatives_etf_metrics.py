"""ETF fund metrics: AUM/scale, fees, holdings profit, and history series."""

from __future__ import annotations

import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from app.utils.logger import get_logger

logger = get_logger(__name__)

_SPOT_EM_CACHE: Dict[str, Any] = {"ts": 0.0, "frame": None}
_SPOT_EM_TTL = 300.0
_METRICS_CACHE_TTL = 6 * 3600
_PROFIT_CACHE_TTL = 24 * 3600
_HIST_CACHE_TTL = 3600


def _code6(value: Any) -> str:
    digits = re.sub(r"\D", "", str(value or ""))
    return digits[:6] if len(digits) >= 6 else digits


def _safe_float(value: Any) -> Optional[float]:
    try:
        if value is None:
            return None
        text = str(value).strip().replace(",", "").replace("%", "")
        if not text or text in {"--", "-", "None", "nan", "NaN"}:
            return None
        return float(text)
    except Exception:
        return None


def _parse_fee_pct(raw: Any) -> Optional[float]:
    if raw is None:
        return None
    text = str(raw)
    match = re.search(r"(-?\d+(?:\.\d+)?)\s*%", text)
    if match:
        return float(match.group(1))
    return _safe_float(raw)


def _cache_get(key: str) -> Optional[Any]:
    try:
        from app.utils.cache import CacheManager

        return CacheManager().get(key)
    except Exception:
        return None


def _cache_set(key: str, value: Any, ttl: int) -> None:
    try:
        from app.utils.cache import CacheManager

        CacheManager().set(key, value, ttl=ttl)
    except Exception as exc:
        logger.debug("etf metrics cache set failed: %s", exc)


def _ak():
    from app.services.cn_derivatives_analytics import _ak as analytics_ak

    return analytics_ak()


def _load_etf_spot_em_frame():
    now = time.time()
    cached = _SPOT_EM_CACHE.get("frame")
    if cached is not None and (now - float(_SPOT_EM_CACHE.get("ts") or 0.0)) < _SPOT_EM_TTL:
        return cached
    try:
        frame = _ak().fund_etf_spot_em()
    except Exception as exc:
        logger.warning("fund_etf_spot_em failed: %s", exc)
        return _SPOT_EM_CACHE.get("frame")
    _SPOT_EM_CACHE["ts"] = now
    _SPOT_EM_CACHE["frame"] = frame
    return frame


def _spot_em_row(code6: str) -> Dict[str, Any]:
    frame = _load_etf_spot_em_frame()
    if frame is None or getattr(frame, "empty", True) or "代码" not in frame.columns:
        return {}
    for _, row in frame.iterrows():
        if _code6(row.get("代码")) != code6:
            continue
        return {
            "price": _safe_float(row.get("最新价")),
            "iopv": _safe_float(row.get("IOPV实时估值")),
            "premium_rate": _safe_float(row.get("基金折价率")),
            "volume": _safe_float(row.get("成交量")),
            "amount": _safe_float(row.get("成交额")),
            "shares": _safe_float(row.get("最新份额")),
            "scale": _safe_float(row.get("总市值")),
            "turnover_rate": _safe_float(row.get("换手率")),
            "source": "fund_etf_spot_em",
        }
    return {}


def _fee_metrics(code6: str) -> Dict[str, Any]:
    cache_key = f"etf:fee:{code6}"
    cached = _cache_get(cache_key)
    if isinstance(cached, dict):
        return cached
    out: Dict[str, Any] = {
        "management_fee_pct": None,
        "custodian_fee_pct": None,
        "total_fee_pct": None,
        "source": "fund_fee_em",
    }
    try:
        frame = _ak().fund_fee_em(symbol=code6, indicator="运作费用")
    except Exception as exc:
        logger.warning("fund_fee_em %s failed: %s", code6, exc)
        return out
    if frame is None or getattr(frame, "empty", True):
        return out
    labels: Dict[str, Optional[float]] = {}
    for _, row in frame.iterrows():
        values = list(row.values)
        for i in range(0, len(values) - 1, 2):
            label = str(values[i] or "").strip()
            labels[label] = _parse_fee_pct(values[i + 1])
    mgmt = labels.get("管理费率")
    custody = labels.get("托管费率")
    out["management_fee_pct"] = mgmt
    out["custodian_fee_pct"] = custody
    if mgmt is not None or custody is not None:
        out["total_fee_pct"] = float(mgmt or 0.0) + float(custody or 0.0)
    _cache_set(cache_key, out, _METRICS_CACHE_TTL)
    return out


def _stock_board_symbol(code6: str) -> str:
    if code6.startswith(("5", "6", "9")):
        return f"SH{code6}"
    return f"SZ{code6}"


def _latest_net_profit(stock_code: str) -> Optional[float]:
    code6 = _code6(stock_code)
    if not code6:
        return None
    cache_key = f"etf:stock_net_profit:{code6}"
    cached = _cache_get(cache_key)
    if isinstance(cached, (int, float)):
        return float(cached)
    if _cache_get(f"{cache_key}:miss") == 1:
        return None
    try:
        frame = _ak().stock_profit_sheet_by_report_em(symbol=_stock_board_symbol(code6))
    except Exception as exc:
        logger.debug("profit sheet %s failed: %s", code6, exc)
        _cache_set(f"{cache_key}:miss", 1, 3600)
        return None
    if frame is None or getattr(frame, "empty", True) or "NETPROFIT" not in getattr(frame, "columns", []):
        _cache_set(f"{cache_key}:miss", 1, 3600)
        return None
    value = _safe_float(frame.iloc[0].get("NETPROFIT"))
    if value is None:
        _cache_set(f"{cache_key}:miss", 1, 3600)
        return None
    _cache_set(cache_key, value, _PROFIT_CACHE_TTL)
    return value


def _holdings_profit_metrics(code6: str, *, top_n: int = 12) -> Dict[str, Any]:
    cache_key = f"etf:holdings_profit:{code6}:{top_n}"
    cached = _cache_get(cache_key)
    if isinstance(cached, dict):
        return cached

    out: Dict[str, Any] = {
        "holdings_count": 0,
        "holdings_quarter": "",
        "constituent_profit_sum": None,
        "constituent_profit_weighted": None,
        "constituent_profit_coverage": 0,
        "holdings_sample": [],
        "source": "fund_portfolio_hold_em",
    }
    year = str(datetime.now().year)
    frame = None
    for year_try in (year, str(int(year) - 1)):
        try:
            frame = _ak().fund_portfolio_hold_em(symbol=code6, date=year_try)
            if frame is not None and not getattr(frame, "empty", True):
                break
        except Exception as exc:
            logger.debug("fund_portfolio_hold_em %s %s failed: %s", code6, year_try, exc)
            frame = None
    if frame is None or getattr(frame, "empty", True):
        return out

    rows: List[Dict[str, Any]] = []
    for _, row in frame.head(max(top_n, 1)).iterrows():
        stock = _code6(row.get("股票代码"))
        if not stock:
            continue
        rows.append(
            {
                "code": stock,
                "name": str(row.get("股票名称") or stock),
                "weight_pct": _safe_float(row.get("占净值比例")),
                "shares": _safe_float(row.get("持股数")),
                "market_value": _safe_float(row.get("持仓市值")),
                "quarter": str(row.get("季度") or ""),
            }
        )
    out["holdings_count"] = int(len(frame))
    if rows:
        out["holdings_quarter"] = str(rows[0].get("quarter") or "")

    profits: List[Tuple[Dict[str, Any], Optional[float]]] = []
    workers = min(6, max(1, len(rows)))
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(_latest_net_profit, r["code"]): r for r in rows}
        try:
            # Keep ETF spot panel responsive; profit is best-effort.
            for fut in as_completed(futures, timeout=12):
                holding = futures[fut]
                try:
                    ni = fut.result(timeout=0)
                except Exception:
                    ni = None
                profits.append((holding, ni))
        except Exception as exc:
            logger.warning("holdings profit gather failed %s: %s", code6, exc)

    total = 0.0
    weighted = 0.0
    have = 0
    sample: List[Dict[str, Any]] = []
    for holding, ni in profits:
        item = dict(holding)
        item["net_profit"] = ni
        sample.append(item)
        if ni is None:
            continue
        have += 1
        total += float(ni)
        w = float(holding.get("weight_pct") or 0.0)
        weighted += float(ni) * (w / 100.0)
    sample.sort(key=lambda r: float(r.get("weight_pct") or 0.0), reverse=True)
    out["holdings_sample"] = sample[:10]
    out["constituent_profit_coverage"] = have
    if have:
        out["constituent_profit_sum"] = total
        out["constituent_profit_weighted"] = weighted
    _cache_set(cache_key, out, _PROFIT_CACHE_TTL)
    return out


def enrich_etf_metrics(code: str, etf_row: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Merge fund metrics onto an ETF spot row."""
    code6 = _code6(code)
    base = dict(etf_row or {})
    if not code6:
        return base

    cache_key = f"etf:metrics_bundle:{code6}"
    cached = _cache_get(cache_key)
    if isinstance(cached, dict) and cached.get("code") == code6:
        merged = dict(base)
        merged.update(cached.get("metrics") or {})
        return merged

    spot_em = _spot_em_row(code6)
    fees = _fee_metrics(code6)
    holdings: Dict[str, Any] = {
        "constituent_profit_sum": None,
        "constituent_profit_weighted": None,
        "constituent_profit_coverage": 0,
        "holdings_count": 0,
        "holdings_quarter": "",
        "holdings_sample": [],
        "source": "skipped",
    }
    try:
        with ThreadPoolExecutor(max_workers=1) as pool:
            fut = pool.submit(_holdings_profit_metrics, code6)
            holdings = fut.result(timeout=15)
    except Exception as exc:
        logger.warning("enrich holdings profit timed out/failed %s: %s", code6, exc)

    price = base.get("price") if base.get("price") not in (None, 0) else spot_em.get("price")
    shares = spot_em.get("shares")
    scale = spot_em.get("scale")
    if scale is None and shares is not None and price not in (None, 0):
        try:
            scale = float(shares) * float(price)
        except Exception:
            scale = None

    metrics: Dict[str, Any] = {
        "code": code6,
        "volume": base.get("volume") if base.get("volume") not in (None, 0) else spot_em.get("volume"),
        "amount": base.get("amount") if base.get("amount") not in (None, 0) else spot_em.get("amount"),
        "shares": shares,
        "scale": scale,
        "turnover_rate": spot_em.get("turnover_rate"),
        "management_fee_pct": fees.get("management_fee_pct"),
        "custodian_fee_pct": fees.get("custodian_fee_pct"),
        "total_fee_pct": fees.get("total_fee_pct"),
        "constituent_profit_sum": holdings.get("constituent_profit_sum"),
        "constituent_profit_weighted": holdings.get("constituent_profit_weighted"),
        "constituent_profit_coverage": holdings.get("constituent_profit_coverage"),
        "holdings_count": holdings.get("holdings_count"),
        "holdings_quarter": holdings.get("holdings_quarter"),
        "holdings_sample": holdings.get("holdings_sample") or [],
        "metrics_asof": datetime.now().isoformat(timespec="seconds"),
        "metrics_sources": {
            "spot": spot_em.get("source"),
            "fee": fees.get("source"),
            "holdings": holdings.get("source"),
        },
    }
    if base.get("iopv") in (None, 0) and spot_em.get("iopv") is not None:
        metrics["iopv"] = spot_em.get("iopv")
    if base.get("premium_rate") is None and spot_em.get("premium_rate") is not None:
        metrics["premium_rate"] = spot_em.get("premium_rate")
    if base.get("price") in (None, 0) and price is not None:
        metrics["price"] = price

    # Retry sooner when holdings profit is still missing.
    bundle_ttl = 900 if metrics.get("constituent_profit_sum") is not None else 120
    _cache_set(cache_key, {"code": code6, "metrics": metrics}, bundle_ttl)
    merged = dict(base)
    merged.update(metrics)
    return merged


def _sina_symbol(code6: str) -> str:
    if code6.startswith(("5", "6", "9")):
        return f"sh{code6}"
    return f"sz{code6}"


def _load_etf_ohlcv_history(code6: str, *, days: int) -> List[Dict[str, Any]]:
    cache_key = f"etf:ohlcv:{code6}:{days}"
    cached = _cache_get(cache_key)
    if isinstance(cached, list):
        return cached
    try:
        frame = _ak().fund_etf_hist_sina(symbol=_sina_symbol(code6))
    except Exception as exc:
        logger.warning("fund_etf_hist_sina %s failed: %s", code6, exc)
        return []
    if frame is None or getattr(frame, "empty", True):
        return []
    points: List[Dict[str, Any]] = []
    for _, row in frame.tail(max(days, 7)).iterrows():
        date_v = row.get("date")
        date_s = date_v.isoformat() if hasattr(date_v, "isoformat") else str(date_v or "")[:10]
        points.append(
            {
                "date": date_s,
                "price": _safe_float(row.get("close")),
                "open": _safe_float(row.get("open")),
                "high": _safe_float(row.get("high")),
                "low": _safe_float(row.get("low")),
                "volume": _safe_float(row.get("volume")),
                "amount": _safe_float(row.get("amount")),
            }
        )
    _cache_set(cache_key, points, _HIST_CACHE_TTL)
    return points


def _resample_metric_points(points: List[Dict[str, Any]], freq: str) -> List[Dict[str, Any]]:
    buckets: Dict[str, Dict[str, Any]] = {}
    for row in points:
        date_s = str(row.get("date") or "")[:10]
        if len(date_s) < 10:
            continue
        try:
            dt = datetime.strptime(date_s, "%Y-%m-%d")
        except Exception:
            continue
        if freq == "week":
            iso = dt.isocalendar()
            key = datetime.fromisocalendar(iso[0], iso[1], 1).date().isoformat()
        else:
            key = f"{dt.year:04d}-{dt.month:02d}-01"
        item = dict(row)
        item["date"] = key
        buckets[key] = item
    return [buckets[k] for k in sorted(buckets.keys())]


def build_etf_metrics_history(
    code: str,
    *,
    chart_key: str = "etf.metrics",
    days: int = 180,
    frequency: str = "day",
) -> Dict[str, Any]:
    code6 = _code6(code)
    days_i = max(7, min(int(days or 180), 800))
    freq = str(frequency or "day").strip().lower()
    if freq in {"w", "1w", "week", "weekly"}:
        freq = "week"
    elif freq in {"m", "1m", "month", "monthly"}:
        freq = "month"
    else:
        freq = "day"

    metrics = enrich_etf_metrics(code6, {})
    ohlcv = _load_etf_ohlcv_history(code6, days=days_i)
    shares = _safe_float(metrics.get("shares"))
    fee = _safe_float(metrics.get("total_fee_pct"))
    profit_sum = _safe_float(metrics.get("constituent_profit_sum"))

    points: List[Dict[str, Any]] = []
    for row in ohlcv:
        price = _safe_float(row.get("price"))
        scale_est = (float(price) * float(shares)) if price is not None and shares is not None else None
        points.append(
            {
                "date": row.get("date"),
                "price": price,
                "volume": row.get("volume"),
                "amount": row.get("amount"),
                "scale": scale_est,
                "fee_pct": fee,
                "constituent_profit_sum": profit_sum,
            }
        )
    if freq in {"week", "month"} and points:
        points = _resample_metric_points(points, freq)

    notes = [
        "价格/成交量/成交额来自新浪 ETF 日线。",
        "规模趋势按「最新份额 × 历史收盘价」估算。",
    ]
    if fee is not None:
        notes.append("费率按当前运作费用（管理费+托管费）画水平参考。")
    if profit_sum is not None:
        notes.append("成份股利润总和取最近持仓前 N 大成分最新财报净利润合计。")
    else:
        notes.append("成份股利润暂不可用或覆盖不足。")

    return {
        "root": code6,
        "chart_key": chart_key or "etf.metrics",
        "mode": "daily",
        "frequency": freq,
        "days": days_i,
        "points": points,
        "metrics": {
            "price": metrics.get("price"),
            "volume": metrics.get("volume"),
            "amount": metrics.get("amount"),
            "scale": metrics.get("scale"),
            "shares": metrics.get("shares"),
            "total_fee_pct": metrics.get("total_fee_pct"),
            "management_fee_pct": metrics.get("management_fee_pct"),
            "custodian_fee_pct": metrics.get("custodian_fee_pct"),
            "constituent_profit_sum": metrics.get("constituent_profit_sum"),
            "constituent_profit_weighted": metrics.get("constituent_profit_weighted"),
            "holdings_count": metrics.get("holdings_count"),
            "holdings_quarter": metrics.get("holdings_quarter"),
        },
        "note": " ".join(notes),
        "asof": datetime.now().isoformat(timespec="seconds"),
    }
