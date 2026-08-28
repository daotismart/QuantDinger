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


def _tencent_code(code6: str) -> str:
    code6 = _code6(code6)
    if not code6:
        return ""
    if code6.startswith(("5", "6", "9")):
        return f"sh{code6}"
    return f"sz{code6}"


def _weighted_avg(
    rows: List[Dict[str, Any]],
    value_key: str,
    *,
    weight_key: str = "weight_pct",
) -> Optional[float]:
    """Weight-weighted average using portfolio weight %."""
    w_total = 0.0
    v_total = 0.0
    for row in rows or []:
        weight = _safe_float(row.get(weight_key)) or 0.0
        if weight <= 0:
            continue
        value = _safe_float(row.get(value_key))
        if value is None:
            continue
        if value_key == "pe_ratio" and value <= 0:
            continue
        w_total += weight
        v_total += float(value) * weight
    if w_total <= 0:
        return None
    return round(v_total / w_total, 2)


def _individual_info_map(symbol_6: str) -> Dict[str, Any]:
    """Lightweight Eastmoney individual info (market cap, industry)."""
    out: Dict[str, Any] = {}
    try:
        with ThreadPoolExecutor(max_workers=1) as pool:
            fut = pool.submit(_ak().stock_individual_info_em, symbol=symbol_6)
            df = fut.result(timeout=8)
    except Exception as exc:
        logger.debug("stock_individual_info_em failed %s: %s", symbol_6, exc)
        return out
    if df is None or getattr(df, "empty", True) or len(df.columns) < 2:
        return out
    kcol, vcol = df.columns[0], df.columns[1]
    for _, row in df.iterrows():
        k = str(row[kcol]).strip()
        if k:
            out[k] = row[vcol]
    return out


def _stock_constituent_snapshot(stock_code: str) -> Dict[str, Any]:
    """Per-stock profit, margin, PE, and total market cap (best-effort)."""
    code6 = _code6(stock_code)
    if not code6:
        return {}
    cache_key = f"etf:constituent_snapshot:{code6}"
    cached = _cache_get(cache_key)
    if isinstance(cached, dict):
        return cached

    out: Dict[str, Any] = {
        "net_profit": None,
        "profit_margin": None,
        "pe_ratio": None,
        "market_cap": None,
    }
    ni = _latest_net_profit(code6)
    out["net_profit"] = ni
    try:
        frame = _ak().stock_profit_sheet_by_report_em(symbol=_stock_board_symbol(code6))
        if frame is not None and not getattr(frame, "empty", True):
            row0 = frame.iloc[0]
            rev = _safe_float(row0.get("营业总收入")) or _safe_float(row0.get("TOTALOPERATEREVE"))
            if ni is not None and rev and rev > 0:
                out["profit_margin"] = round(float(ni) / float(rev) * 100, 2)
    except Exception as exc:
        logger.debug("constituent margin %s failed: %s", code6, exc)

    try:
        info = _individual_info_map(code6)
        mcap = _safe_float(info.get("总市值"))
        if mcap is not None:
            out["market_cap"] = mcap
    except Exception as exc:
        logger.debug("constituent market cap %s failed: %s", code6, exc)

    try:
        from app.data_sources.cn_hk_fundamentals import fetch_cn_fundamental_akshare

        fund = fetch_cn_fundamental_akshare(_tencent_code(code6))
        if fund.get("pe_ratio") is not None:
            out["pe_ratio"] = fund.get("pe_ratio")
        if out.get("market_cap") is None and fund.get("market_cap") is not None:
            out["market_cap"] = fund.get("market_cap")
    except Exception as exc:
        logger.debug("constituent fundamentals %s failed: %s", code6, exc)

    _cache_set(cache_key, out, _PROFIT_CACHE_TTL)
    return out


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


def _benchmark_index_code(code6: str) -> Optional[str]:
    """Map ETF code to CSI/index code (e.g. 510300 -> 000300)."""
    try:
        from app.markets.cn_options import etf_benchmark_index

        item = etf_benchmark_index(code6)
        if not item:
            return None
        return str(item[0] or "").strip() or None
    except Exception:
        return None


def _load_index_constituent_rows(index_code: str) -> List[Dict[str, Any]]:
    """Full benchmark index constituents with weights (typically 300+ rows)."""
    index_code = str(index_code or "").strip()
    if not index_code:
        return []
    cache_key = f"etf:index_constituents:{index_code}"
    cached = _cache_get(cache_key)
    if isinstance(cached, list):
        return cached

    rows: List[Dict[str, Any]] = []
    try:
        frame = _ak().index_stock_cons_weight_csindex(symbol=index_code)
    except Exception as exc:
        logger.warning("index_stock_cons_weight_csindex %s failed: %s", index_code, exc)
        return rows
    if frame is None or getattr(frame, "empty", True):
        return rows

    asof = ""
    for _, row in frame.iterrows():
        stock = _code6(row.get("成分券代码"))
        if not stock:
            continue
        if not asof:
            date_v = row.get("日期")
            asof = date_v.isoformat() if hasattr(date_v, "isoformat") else str(date_v or "")[:10]
        weight = _safe_float(row.get("权重"))
        rows.append(
            {
                "code": stock,
                "name": str(row.get("成分券名称") or stock),
                "weight_pct": weight,
                "shares": None,
                "market_value": None,
                "quarter": f"{index_code} index {asof}".strip(),
            }
        )
    rows.sort(key=lambda r: float(r.get("weight_pct") or 0.0), reverse=True)
    _cache_set(cache_key, rows, _METRICS_CACHE_TTL)
    return rows


def _load_fund_portfolio_rows(code6: str) -> List[Dict[str, Any]]:
    """Fund disclosed holdings; dedupe by stock code keeping latest quarter row."""
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
        return []

    by_code: Dict[str, Dict[str, Any]] = {}
    for _, row in frame.iterrows():
        stock = _code6(row.get("股票代码"))
        if not stock:
            continue
        item = {
            "code": stock,
            "name": str(row.get("股票名称") or stock),
            "weight_pct": _safe_float(row.get("占净值比例")),
            "shares": _safe_float(row.get("持股数")),
            "market_value": _safe_float(row.get("持仓市值")),
            "quarter": str(row.get("季度") or ""),
        }
        prev = by_code.get(stock)
        if not prev or str(item.get("quarter") or "") >= str(prev.get("quarter") or ""):
            by_code[stock] = item
    rows = list(by_code.values())
    rows.sort(key=lambda r: float(r.get("weight_pct") or 0.0), reverse=True)
    return rows


def _load_constituent_base_rows(code6: str) -> Tuple[List[Dict[str, Any]], str, str]:
    """Prefer full benchmark index constituents; fallback to fund portfolio disclosure."""
    index_code = _benchmark_index_code(code6)
    if index_code:
        rows = _load_index_constituent_rows(index_code)
        if rows:
            quarter = str(rows[0].get("quarter") or "")
            return rows, "index_stock_cons_weight_csindex", quarter
    rows = _load_fund_portfolio_rows(code6)
    quarter = str(rows[0].get("quarter") or "") if rows else ""
    return rows, "fund_portfolio_hold_em", quarter


def _enrich_constituent_snapshots(codes: List[str], *, timeout: float = 90.0, batch_size: int = 50) -> Dict[str, Dict[str, Any]]:
    unique = []
    seen = set()
    for code in codes or []:
        c = _code6(code)
        if c and c not in seen:
            seen.add(c)
            unique.append(c)
    snapshots: Dict[str, Dict[str, Any]] = {}
    if not unique:
        return snapshots

    # Pre-fill from per-stock cache so we skip network for warm symbols.
    pending: List[str] = []
    for code in unique:
        cached = _cache_get(f"etf:constituent_snapshot:{code}")
        if isinstance(cached, dict) and cached:
            snapshots[code] = cached
        else:
            pending.append(code)

    if not pending:
        return snapshots

    per_batch = max(20.0, float(timeout) / max(1, (len(pending) + batch_size - 1) // batch_size))
    workers = min(6, max(1, batch_size // 4))
    for start in range(0, len(pending), batch_size):
        batch = pending[start : start + batch_size]
        with ThreadPoolExecutor(max_workers=workers) as pool:
            futures = {pool.submit(_stock_constituent_snapshot, code): code for code in batch}
            try:
                for fut in as_completed(futures, timeout=per_batch):
                    code = futures[fut]
                    try:
                        snapshots[code] = fut.result(timeout=0) or {}
                    except Exception:
                        snapshots[code] = {}
            except Exception as exc:
                logger.warning("constituent snapshot batch incomplete: %s", exc)
                for fut, code in futures.items():
                    if code in snapshots:
                        continue
                    if fut.done():
                        try:
                            snapshots[code] = fut.result(timeout=0) or {}
                        except Exception:
                            snapshots[code] = {}
    return snapshots


def _apply_etf_scale_to_rows(rows: List[Dict[str, Any]], etf_scale: Optional[float]) -> None:
    scale = _safe_float(etf_scale)
    if scale is None or scale <= 0:
        return
    for row in rows:
        if row.get("market_value") is not None:
            continue
        weight = _safe_float(row.get("weight_pct"))
        if weight is None:
            continue
        row["market_value"] = float(scale) * float(weight) / 100.0


def _merge_holdings_metrics(base_rows: List[Dict[str, Any]], snapshots: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    holdings: List[Dict[str, Any]] = []
    profit_total = 0.0
    profit_weighted = 0.0
    profit_have = 0
    cap_sum = 0.0
    cap_have = 0
    enriched_for_avg: List[Dict[str, Any]] = []

    for row in base_rows:
        item = dict(row)
        snap = snapshots.get(row["code"]) or {}
        for key in ("net_profit", "profit_margin", "pe_ratio", "market_cap"):
            if snap.get(key) is not None:
                item[key] = snap.get(key)
        holdings.append(item)
        if item.get("net_profit") is not None:
            ni = float(item["net_profit"])
            profit_have += 1
            profit_total += ni
            w = float(item.get("weight_pct") or 0.0)
            profit_weighted += ni * (w / 100.0)
        if item.get("market_cap") is not None:
            cap_sum += float(item["market_cap"])
            cap_have += 1
        if item.get("pe_ratio") is not None or item.get("profit_margin") is not None:
            enriched_for_avg.append(item)

    out: Dict[str, Any] = {
        "holdings": holdings,
        "holdings_sample": holdings[:10],
        "constituent_profit_coverage": profit_have,
        "constituent_profit_sum": profit_total if profit_have else None,
        "constituent_profit_weighted": profit_weighted if profit_have else None,
        "constituent_market_cap_sum": cap_sum if cap_have else None,
        "market_cap_coverage": cap_have,
        "pe_coverage": sum(1 for r in enriched_for_avg if r.get("pe_ratio") is not None),
        "margin_coverage": sum(1 for r in enriched_for_avg if r.get("profit_margin") is not None),
        "avg_pe": _weighted_avg(enriched_for_avg, "pe_ratio"),
        "avg_profit_margin": _weighted_avg(enriched_for_avg, "profit_margin"),
    }
    return out


def _holdings_base_bundle(code6: str, *, etf_scale: Optional[float] = None) -> Dict[str, Any]:
    cache_key = f"etf:holdings_base:v1:{code6}"
    cached = _cache_get(cache_key)
    if isinstance(cached, dict) and cached.get("rows"):
        rows = [dict(r) for r in cached["rows"]]
        _apply_etf_scale_to_rows(rows, etf_scale)
        bundle = dict(cached)
        bundle["rows"] = rows
        return bundle

    base_rows, source, quarter = _load_constituent_base_rows(code6)
    rows = [dict(r) for r in base_rows]
    _apply_etf_scale_to_rows(rows, etf_scale)
    mv_sum = 0.0
    mv_have = 0
    for row in rows:
        mv = _safe_float(row.get("market_value"))
        if mv is not None:
            mv_sum += float(mv)
            mv_have += 1
    bundle = {
        "rows": [dict(r) for r in base_rows],
        "source": source,
        "quarter": quarter,
        "holdings_count": len(rows),
        "constituent_market_value_sum": mv_sum if mv_have else None,
    }
    _cache_set(cache_key, bundle, _METRICS_CACHE_TTL)
    bundle["rows"] = rows
    return bundle


def _holdings_profit_metrics(
    code6: str,
    *,
    top_n: int = 0,
    etf_scale: Optional[float] = None,
) -> Dict[str, Any]:
    cache_key = f"etf:holdings_profit:v3:{code6}"
    cached = _cache_get(cache_key)
    if isinstance(cached, dict):
        return cached

    out: Dict[str, Any] = {
        "holdings_count": 0,
        "holdings_quarter": "",
        "constituent_profit_sum": None,
        "constituent_profit_weighted": None,
        "constituent_profit_coverage": 0,
        "constituent_market_value_sum": None,
        "constituent_market_cap_sum": None,
        "avg_pe": None,
        "avg_profit_margin": None,
        "pe_coverage": 0,
        "margin_coverage": 0,
        "market_cap_coverage": 0,
        "holdings": [],
        "holdings_sample": [],
        "source": "fund_portfolio_hold_em",
    }

    base = _holdings_base_bundle(code6, etf_scale=etf_scale)
    base_rows = base.get("rows") or []
    if not base_rows:
        return out

    out["source"] = base.get("source") or out["source"]
    out["holdings_count"] = int(base.get("holdings_count") or len(base_rows))
    out["holdings_quarter"] = str(base.get("quarter") or "")
    out["constituent_market_value_sum"] = base.get("constituent_market_value_sum")

    codes = [r["code"] for r in base_rows]
    if top_n and int(top_n) > 0:
        codes = codes[: int(top_n)]
    snapshots = _enrich_constituent_snapshots(codes, timeout=120.0)
    merged = _merge_holdings_metrics(base_rows, snapshots)
    out.update(merged)

    total = out["holdings_count"] or len(base_rows)
    cov = int(out.get("constituent_profit_coverage") or 0)
    cache_ttl = _PROFIT_CACHE_TTL if total and cov >= max(20, total // 2) else 1800
    _cache_set(cache_key, out, cache_ttl)
    return out


def enrich_etf_metrics(code: str, etf_row: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Merge fund metrics onto an ETF spot row."""
    code6 = _code6(code)
    base = dict(etf_row or {})
    if not code6:
        return base

    cache_key = f"etf:metrics_bundle:v2:{code6}"
    cached = _cache_get(cache_key)
    if isinstance(cached, dict) and cached.get("code") == code6:
        merged = dict(base)
        merged.update(cached.get("metrics") or {})
        return merged

    spot_em = _spot_em_row(code6)
    fees = _fee_metrics(code6)
    price = base.get("price") if base.get("price") not in (None, 0) else spot_em.get("price")
    shares = spot_em.get("shares")
    scale = spot_em.get("scale")
    if scale is None and shares is not None and price not in (None, 0):
        try:
            scale = float(shares) * float(price)
        except Exception:
            scale = None

    holdings: Dict[str, Any] = {
        "constituent_profit_sum": None,
        "constituent_profit_weighted": None,
        "constituent_profit_coverage": 0,
        "constituent_market_value_sum": None,
        "constituent_market_cap_sum": None,
        "avg_pe": None,
        "avg_profit_margin": None,
        "pe_coverage": 0,
        "margin_coverage": 0,
        "market_cap_coverage": 0,
        "holdings_count": 0,
        "holdings_quarter": "",
        "holdings": [],
        "holdings_sample": [],
        "source": "skipped",
    }
    try:
        with ThreadPoolExecutor(max_workers=1) as pool:
            fut = pool.submit(_holdings_profit_metrics, code6, etf_scale=scale)
            holdings = fut.result(timeout=120)
    except Exception as exc:
        logger.warning("enrich holdings profit timed out/failed %s: %s", code6, exc)
        try:
            base_bundle = _holdings_base_bundle(code6, etf_scale=scale)
            rows = base_bundle.get("rows") or []
            if rows:
                holdings = {
                    "holdings_count": len(rows),
                    "holdings_quarter": base_bundle.get("quarter") or "",
                    "constituent_market_value_sum": base_bundle.get("constituent_market_value_sum"),
                    "holdings": rows,
                    "holdings_sample": rows[:10],
                    "source": base_bundle.get("source"),
                    "constituent_profit_coverage": 0,
                    "pe_coverage": 0,
                    "margin_coverage": 0,
                    "market_cap_coverage": 0,
                }
        except Exception as fallback_exc:
            logger.debug("holdings base fallback failed %s: %s", code6, fallback_exc)

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
        "constituent_market_value_sum": holdings.get("constituent_market_value_sum"),
        "constituent_market_cap_sum": holdings.get("constituent_market_cap_sum"),
        "avg_pe": holdings.get("avg_pe"),
        "avg_profit_margin": holdings.get("avg_profit_margin"),
        "pe_coverage": holdings.get("pe_coverage"),
        "margin_coverage": holdings.get("margin_coverage"),
        "market_cap_coverage": holdings.get("market_cap_coverage"),
        "holdings_count": holdings.get("holdings_count"),
        "holdings_quarter": holdings.get("holdings_quarter"),
        "holdings": holdings.get("holdings") or [],
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

    # Retry sooner when holdings enrichment is still missing.
    bundle_ttl = 900 if (metrics.get("holdings_count") or 0) > 0 else 120
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
        cov = int(metrics.get("constituent_profit_coverage") or 0)
        total = int(metrics.get("holdings_count") or 0)
        notes.append(f"成份股利润总和为全部成份最新财报净利润合计（覆盖 {cov}/{total} 只）。")
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
            "constituent_market_value_sum": metrics.get("constituent_market_value_sum"),
            "constituent_market_cap_sum": metrics.get("constituent_market_cap_sum"),
            "avg_pe": metrics.get("avg_pe"),
            "avg_profit_margin": metrics.get("avg_profit_margin"),
            "holdings_count": metrics.get("holdings_count"),
            "holdings_quarter": metrics.get("holdings_quarter"),
        },
        "note": " ".join(notes),
        "asof": datetime.now().isoformat(timespec="seconds"),
    }
