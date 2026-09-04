"""ETF derivatives analytics for the market-composite ETF page."""

from __future__ import annotations

import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, datetime
from typing import Any, Dict, List, Optional, Tuple

from app.utils.logger import get_logger

logger = get_logger(__name__)

ETF_INDEX_ROOTS = ("IF", "IH", "IC", "IM")
# Sina/East Money often hang from this host; never block the ETF spot panel on them.
_SINA_TIMEOUT_SEC = 4.0
_ENRICH_TIMEOUT_SEC = 3.0
_TIMED_POOL = ThreadPoolExecutor(max_workers=4, thread_name_prefix="etf-spot")


def _call_with_timeout(fn, timeout: float, default: Any = None) -> Any:
    """Run ``fn`` with a hard timeout; do not join the worker if it hangs."""
    try:
        return _TIMED_POOL.submit(fn).result(timeout=max(0.05, float(timeout)))
    except Exception as exc:
        logger.warning("timed ETF fetch failed: %s", exc)
        return default

def _etf_code6(value: str) -> str:
    digits = re.sub(r"\D", "", str(value or ""))
    return digits[:6] if len(digits) >= 6 else digits


ETF_SSE_LIST_NAME: Dict[str, str] = {
    "510050": "50ETF",
    "510300": "300ETF",
    "510500": "500ETF",
    "588000": "科创50ETF",
    "588080": "科创50ETF",
    "159901": "100ETF",
    "159915": "创业板ETF",
    "159919": "300ETF",
    "159922": "500ETF",
}

ETF_CN_NAMES: Dict[str, str] = {
    "510050": "上证50ETF",
    "510300": "沪深300ETF",
    "510500": "中证500ETF",
    "588000": "科创50ETF",
    "588080": "科创50ETF",
    "159901": "深证100ETF",
    "159915": "创业板ETF",
    "159919": "沪深300ETF",
    "159922": "中证500ETF",
}

SPOT_INDEX_CN_NAMES: Dict[str, str] = {
    "000016.SH": "上证50指数",
    "000300.SH": "沪深300指数",
    "000905.SH": "中证500指数",
    "000688.SH": "科创50指数",
    "399006.SZ": "创业板指",
    "399330.SZ": "深证100指数",
    "399300.SZ": "沪深300指数",
    "399905.SZ": "中证500指数",
}

# ETF underlying -> related CFFEX index-futures root (if any).
ETF_INDEX_FUTURES_ROOT: Dict[str, str] = {
    "510050": "IH",
    "510300": "IF",
    "510500": "IC",
    "159919": "IF",
    "159922": "IC",
}


def _cn_display_name(symbol: str, fallback: str = "") -> str:
    sym = str(symbol or "").strip().upper()
    code6 = _etf_code6(sym)
    if sym in SPOT_INDEX_CN_NAMES:
        return SPOT_INDEX_CN_NAMES[sym]
    if code6 in ETF_CN_NAMES:
        return ETF_CN_NAMES[code6]
    return str(fallback or sym).strip() or sym


def _product_row(
    *,
    root: str,
    name_cn: str,
    picker_kind: str,
    market: str,
    **extra: Any,
) -> Dict[str, Any]:
    row: Dict[str, Any] = {
        "root": root,
        "name": name_cn,
        "name_cn": name_cn,
        "picker_kind": picker_kind,
        "market": market,
        "has_options": False,
        "has_option_chain": False,
    }
    row.update(extra)
    return row


def _etf_picker_row(item: Dict[str, Any]) -> Dict[str, Any]:
    """One shared picker row for an ETF option underlying (used by all tabs)."""
    from app.markets.cn_options import etf_benchmark_display_name, etf_benchmark_symbol

    sym = str(item.get("symbol") or "").strip().upper()
    code6 = _etf_code6(sym)
    name = _cn_display_name(code6, str(item.get("name") or sym))
    index_symbol = etf_benchmark_symbol(code6) or ""
    index_name = (
        _cn_display_name(index_symbol, etf_benchmark_display_name(code6))
        if index_symbol
        else ""
    )
    futures_root = ETF_INDEX_FUTURES_ROOT.get(code6, "")
    return _product_row(
        root=sym or code6,
        name_cn=name,
        picker_kind="cn_etf",
        market="CNStock",
        underlying_code=code6,
        product_class="etf",
        stock_symbol=sym or code6,
        exchange=str(item.get("exchange") or "CN").upper(),
        multiplier=10000.0,
        option_multiplier=10000.0,
        has_options=True,
        has_option_chain=True,
        index_symbol=index_symbol,
        index_name=index_name,
        index_futures_root=futures_root,
    )


def list_etf_derivative_products(tab: str = "") -> List[Dict[str, Any]]:
    """Return the shared ETF picker list.

    The ETF workbench selects an ETF once; index / ETF / options tabs all reuse
    the same underlying. ``tab`` is kept for API compatibility but ignored.
    """
    from app.services.cn_options_chain import listed_etf_underlying_catalog

    _ = str(tab or "").strip().lower()
    rows: List[Dict[str, Any]] = []
    seen: set[str] = set()
    for item in listed_etf_underlying_catalog():
        code6 = _etf_code6(item.get("symbol"))
        if not code6 or code6 in seen:
            continue
        seen.add(code6)
        rows.append(_etf_picker_row(item))
    rows.sort(key=lambda r: r.get("underlying_code") or r["root"])
    return rows


def _etf_product_payload(code6: str) -> Dict[str, Any]:
    code6 = _etf_code6(code6)
    for row in list_etf_derivative_products("etf"):
        if row.get("underlying_code") == code6 or _etf_code6(row.get("root")) == code6:
            return row
    from app.markets.cn_options import etf_underlying_display_name

    name = _cn_display_name(code6, etf_underlying_display_name(code6))
    return {
        "root": code6,
        "name": name,
        "name_cn": name,
        "underlying_code": code6,
        "has_options": True,
        "has_option_chain": True,
        "multiplier": 10000.0,
        "option_multiplier": 10000.0,
    }


def build_spot_index_panel(symbol: str) -> Dict[str, Any]:
    """Spot benchmark index panel for the ETF composite index tab."""
    from app.services.cn_derivatives_analytics import _ak, _safe_float

    sym = str(symbol or "").strip().upper()
    if not sym:
        raise ValueError("index symbol is required")

    name = _cn_display_name(sym, sym)
    index_row = _index_row_from_local_bars(sym)
    index_frame = _call_with_timeout(lambda: _ak().stock_zh_index_spot_sina(), _SINA_TIMEOUT_SEC)
    if index_frame is not None:
        live = _index_row_from_spot(index_frame, sym.split(".")[0].lower(), _safe_float)
        if live and float(live.get("price") or 0.0) > 0:
            index_row = live
    price = float((index_row or {}).get("price") or 0.0)
    analysis: List[str] = []
    if price > 0:
        analysis.append(f"{name} 最新点位 {price:.2f}。")
    else:
        analysis.append("暂无指数现货行情，请稍后重试。")

    return {
        "root": sym,
        "name_cn": name,
        "product": _product_row(
            root=sym,
            name_cn=name,
            picker_kind="spot_index",
            market="CNStock",
            stock_symbol=sym,
        ),
        "spot": {
            "index": index_row or {"code": sym, "name": name, "price": price},
            "index_symbol": sym,
        },
        "spot_price": price,
        "continuous": {"price": price, "volume": 0, "open_interest": 0},
        "analysis": analysis,
        "asof": datetime.now().isoformat(timespec="seconds"),
    }


def build_us_hk_etf_panel(market: str, symbol: str) -> Dict[str, Any]:
    """Basic quote panel for US/HK listed ETFs."""
    from app.services.market.quotes import get_single_price

    market = str(market or "").strip()
    sym = str(symbol or "").strip().upper()
    if not market or not sym:
        raise ValueError("market and symbol are required")

    quote = get_single_price(market, sym) or {}
    price = float(quote.get("price") or quote.get("last") or quote.get("close") or 0.0)
    name = str(quote.get("name") or sym)
    analysis: List[str] = []
    if price > 0:
        analysis.append(f"{name} 最新价 {price:.4f}。")
    else:
        analysis.append("暂无该 ETF 行情，请稍后重试或在 AI 面板检索。")

    return {
        "root": sym,
        "name_cn": name,
        "product": _product_row(
            root=sym,
            name_cn=name,
            picker_kind="us_hk_etf",
            market=market,
            stock_symbol=sym,
        ),
        "spot": {
            "etf": {"symbol": sym, "name": name, "price": price},
        },
        "spot_price": price,
        "continuous": {"price": price, "volume": quote.get("volume"), "open_interest": 0},
        "analysis": analysis,
        "asof": datetime.now().isoformat(timespec="seconds"),
    }


def build_etf_scope_spot_panel(
    root: str,
    *,
    picker_kind: str = "",
    market: str = "",
) -> Dict[str, Any]:
    kind = str(picker_kind or "").strip().lower()
    root_s = str(root or "").strip()
    if kind == "spot_index":
        return build_spot_index_panel(root_s)
    if kind == "us_hk_etf":
        return build_us_hk_etf_panel(market or "USStock", root_s)
    if kind == "cn_etf" or "." in root_s:
        return build_etf_spot_panel(root_s)
    return build_etf_spot_panel(root_s)


def build_etf_spot_panel(code: str) -> Dict[str, Any]:
    from app.markets.cn_options import etf_benchmark_index, etf_benchmark_symbol, etf_underlying_display_name
    from app.services.cn_derivatives_analytics import _ak, _safe_float

    code6 = _etf_code6(code)
    if not code6:
        raise ValueError("ETF code is required")

    etf = _etf_row_from_local_bars(code6) or {
        "code": code6,
        "name": _cn_display_name(code6, etf_underlying_display_name(code6)),
        "price": 0.0,
        "source": "none",
    }
    sina_frame = _call_with_timeout(lambda: _load_etf_spot_frame_sina(_ak), _SINA_TIMEOUT_SEC)
    sina_row = _etf_row_from_spot(sina_frame, code6, _safe_float) if sina_frame is not None else None
    if sina_row and float(sina_row.get("price") or 0.0) > 0:
        merged = dict(etf)
        for key, value in sina_row.items():
            if value not in (None, ""):
                merged[key] = value
        if etf.get("source") == "qd_market_bars":
            merged["source"] = "sina+local"
        else:
            merged["source"] = "sina"
        etf = merged

    bench = etf_benchmark_index(code6)
    index_symbol = etf_benchmark_symbol(code6) if bench else ""
    index_row = _index_row_from_local_bars(index_symbol) if index_symbol else None
    index_frame = _call_with_timeout(lambda: _ak().stock_zh_index_spot_sina(), _SINA_TIMEOUT_SEC)
    if bench and index_frame is not None:
        live = _index_row_from_spot(index_frame, str(bench[0] or "").strip().lower(), _safe_float)
        if live and float(live.get("price") or 0.0) > 0:
            index_row = live

    try:
        from app.services.cn_derivatives_etf_metrics import enrich_etf_metrics

        enriched = _call_with_timeout(
            lambda: enrich_etf_metrics(code6, etf),
            _ENRICH_TIMEOUT_SEC,
            default=None,
        )
        if isinstance(enriched, dict):
            etf = enriched
    except Exception as exc:
        logger.warning("enrich_etf_metrics %s failed: %s", code6, exc)

    etf_price = float(etf.get("price") or 0.0)
    index_price = float((index_row or {}).get("price") or 0.0)
    analysis: List[str] = []
    if etf_price > 0:
        analysis.append(f"{etf.get('name')} 最新价 {etf_price:.4f}。")
    if etf.get("iopv"):
        analysis.append(
            f"IOPV {float(etf['iopv']):.4f}，折价率 {float(etf.get('premium_rate') or 0):.2f}%。"
        )
    if etf.get("scale"):
        analysis.append(f"基金规模（总市值）约 {float(etf['scale']):,.0f} 元。")
    if etf.get("amount"):
        analysis.append(f"成交额 {float(etf['amount']):,.0f} 元，成交量 {float(etf.get('volume') or 0):,.0f}。")
    if etf.get("total_fee_pct") is not None:
        analysis.append(
            f"运作费率约 {float(etf['total_fee_pct']):.2f}%/年"
            f"（管理费 {float(etf.get('management_fee_pct') or 0):.2f}% + "
            f"托管费 {float(etf.get('custodian_fee_pct') or 0):.2f}%）。"
        )
    if etf.get("constituent_profit_sum") is not None:
        coverage = int(etf.get("constituent_profit_coverage") or 0)
        total = int(etf.get("holdings_count") or 0)
        analysis.append(
            f"成份股最新财报净利润合计约 {float(etf['constituent_profit_sum']):,.0f} 元"
            f"（覆盖 {coverage}/{total} 只成份）。"
        )
    if etf.get("constituent_market_value_sum") is not None:
        analysis.append(
            f"成份持仓市值合计约 {float(etf['constituent_market_value_sum']):,.0f} 元。"
        )
    if etf.get("constituent_market_cap_sum") is not None:
        cov = int(etf.get("market_cap_coverage") or 0)
        total = int(etf.get("holdings_count") or 0)
        analysis.append(
            f"成份股总市值合计约 {float(etf['constituent_market_cap_sum']):,.0f} 元"
            f"（覆盖 {cov}/{total} 只）。"
        )
    if etf.get("avg_pe") is not None:
        analysis.append(
            f"成份加权平均 PE 约 {float(etf['avg_pe']):.2f}"
            f"（覆盖 {int(etf.get('pe_coverage') or 0)} 只）。"
        )
    if etf.get("avg_profit_margin") is not None:
        analysis.append(
            f"成份加权平均利润率约 {float(etf['avg_profit_margin']):.2f}%"
            f"（覆盖 {int(etf.get('margin_coverage') or 0)} 只）。"
        )
    if index_row and index_price > 0:
        analysis.append(f"基准指数 {index_row.get('name')} 最新 {index_price:.2f}。")
    if not analysis:
        analysis.append("暂无 ETF 现货行情，请稍后重试。")

    return {
        "root": code6,
        "name_cn": _cn_display_name(code6, etf.get("name") or code6),
        "product": _etf_product_payload(code6),
        "spot": {
            "etf": etf,
            "index": index_row,
            "index_symbol": index_symbol,
        },
        "spot_price": etf_price,
        "continuous": {"price": etf_price, "volume": etf.get("volume"), "open_interest": 0},
        "analysis": analysis,
        "asof": datetime.now().isoformat(timespec="seconds"),
    }



def _etf_options_cache_get(key: str) -> Optional[Dict[str, Any]]:
    try:
        from app.utils.cache import CacheManager

        cached = CacheManager().get(key)
        return cached if isinstance(cached, dict) else None
    except Exception as exc:
        logger.debug("etf options cache get failed: %s", exc)
        return None


def _etf_options_cache_set(key: str, value: Dict[str, Any], ttl: int) -> None:
    if ttl <= 0:
        return
    try:
        from app.utils.cache import CacheManager

        CacheManager().set(key, value, ttl=ttl)
    except Exception as exc:
        logger.debug("etf options cache set failed: %s", exc)


def _assemble_etf_options_panel(
    *,
    code6: str,
    name_cn: str,
    months: List[str],
    selected_months: List[str],
    select_all: bool,
    underlying: float,
    chains_by_month: Dict[str, List[Dict[str, Any]]],
    month_meta: Dict[str, Dict[str, Any]],
    compute_gex,
    compute_max_pain,
    time_value_fn,
    data_source: str,
) -> Dict[str, Any]:
    """Assemble ETF options panel with GEX as a chart-style indicator.

    Flow mirrors the Indicator IDE: compute indicator output
    (plots/signals/layers/summary), then map to display fields. Legacy
    ``gex_distribution`` / ``gex_summary`` remain for older clients.
    """
    from app.services.gex_indicator import (
        aggregate_gex_points,
        indicator_from_gex_points,
        panel_fields_from_gex_indicator,
        run_gex_indicator,
    )

    mult = 10000.0
    # Short-margin pct for ETF options opening-margin formula (peer uses 15%).
    margin_rate = 0.15
    month_series: List[Dict[str, Any]] = []
    chains_for_agg: List[List[Dict[str, Any]]] = []
    underlyings: List[float] = []
    Ts: List[float] = []

    from app.services.cn_derivatives_etf_capital import (
        build_capital_curve_by_month,
        combine_market_tv_yields,
        compute_option_capital_metrics,
    )

    def _gex_fields(chain: List[Dict[str, Any]], *, spot: float, T: float, label: str) -> Dict[str, Any]:
        indicator = run_gex_indicator(
            chain or [],
            underlying=float(spot or 0.0),
            multiplier=mult,
            T=T,
            name=label,
        )
        fields = panel_fields_from_gex_indicator(indicator)
        # Optional injectable raw compute (tests) can override legacy arrays only.
        if compute_gex is not None and chain and spot:
            try:
                raw = compute_gex(chain, underlying=spot, multiplier=mult, T=T) or {}
            except TypeError:
                raw = {}
            if isinstance(raw, dict) and raw.get("points") is not None:
                fields["gex_distribution"] = list(raw.get("points") or [])
                if isinstance(raw.get("summary"), dict):
                    fields["gex_summary"] = dict(raw.get("summary") or {})
                if isinstance(raw.get("portfolio_greeks"), dict):
                    fields["greeks"] = dict(raw.get("portfolio_greeks") or {})
                if isinstance(raw.get("iv_smile"), list):
                    fields["iv_smile"] = list(raw.get("iv_smile") or [])
        return fields

    for m in selected_months:
        chain = chains_by_month.get(m) or []
        if not chain:
            continue
        meta = month_meta.get(m) or {}
        mult = float(meta.get("multiplier") or mult)
        T = float(meta.get("T") or (30 / 365.0))
        underlyings.append(underlying)
        Ts.append(T)
        chains_for_agg.append(chain)
        gex_fields = _gex_fields(chain, spot=underlying, T=T, label=f"GEX {m}")
        max_pain = compute_max_pain(chain) if chain else None
        tv_yield = time_value_fn(
            chain,
            underlying=underlying,
            multiplier=mult,
            margin_rate=margin_rate,
            T=T,
            month=m,
        )
        capital_metrics = compute_option_capital_metrics(
            chain,
            underlying=underlying,
            multiplier=mult,
            margin_rate=margin_rate,
        )
        month_series.append(
            {
                "month": m,
                "underlying": underlying,
                "T": T,
                "gex_distribution": gex_fields.get("gex_distribution") or [],
                "gex_summary": gex_fields.get("gex_summary") or {},
                "greeks": gex_fields.get("greeks") or {},
                "iv_smile": gex_fields.get("iv_smile") or [],
                "max_pain": max_pain,
                "time_value_yield": tv_yield,
                "capital_metrics": capital_metrics,
                "indicators": gex_fields.get("indicators") or {},
            }
        )

    if not month_series:
        empty_ind = run_gex_indicator(
            [], underlying=float(underlying or 0.0), multiplier=mult, T=30 / 365.0, name="GEX"
        )
        return {
            "root": code6,
            "name_cn": name_cn,
            "available": True,
            "has_option_chain": True,
            "months": months,
            "month": "all" if select_all else selected_months[0],
            "underlying": underlying,
            "current_price": underlying,
            "multiplier": mult,
            "margin_rate": margin_rate,
            "chain": [],
            "greeks": {},
            "gex_summary": {},
            "gex_distribution": [],
            "iv_smile": [],
            "max_pain": None,
            "time_value_yield": [],
            "capital_curve": {"points": [], "total": {}, "note": ""},
            "indicators": {"gex": empty_ind},
            "message": "已连接期权数据源，但当前月份链截面为空。",
            "data_source": data_source,
            "asof": datetime.now().isoformat(timespec="seconds"),
        }

    primary = month_series[0]
    u_avg = sum(underlyings) / len(underlyings) if underlyings else underlying
    t_avg = sum(Ts) / len(Ts) if Ts else 30 / 365.0
    if select_all and len(month_series) > 1:
        # Sum per-month GEX by strike (each month keeps its own T/gamma).
        # Do NOT merge OI then recompute with average T — that inflates deep-OTM
        # walls (e.g. 588000 Call Wall at 2.55 while spot≈1.69).
        agg_points = aggregate_gex_points(
            [list(ms.get("gex_distribution") or []) for ms in month_series]
        )
        gex_indicator = indicator_from_gex_points(
            agg_points,
            underlying=float(u_avg or underlying or 0.0),
            multiplier=mult,
            T=t_avg,
            name="GEX all",
        )
        gex_fields = panel_fields_from_gex_indicator(gex_indicator)
        agg_chain = _aggregate_etf_chains_by_strike(chains_for_agg)
        chain_out = agg_chain
        greeks = primary.get("greeks") or {}
        for ms in month_series:
            g = ms.get("greeks") or {}
            for k in ("delta", "gamma", "vega", "theta"):
                greeks[k] = float(greeks.get(k) or 0.0) + float(g.get(k) or 0.0)
        gex_summary = gex_fields.get("gex_summary") or {}
        gex_distribution = gex_fields.get("gex_distribution") or agg_points
        max_pain = compute_max_pain(agg_chain) if agg_chain else primary.get("max_pain")
        iv_smile = primary.get("iv_smile") or []
    else:
        chain_out = chains_for_agg[0] if chains_for_agg else []
        greeks = primary.get("greeks") or {}
        gex_summary = primary.get("gex_summary") or {}
        gex_distribution = primary.get("gex_distribution") or []
        gex_indicator = (primary.get("indicators") or {}).get("gex")
        max_pain = primary.get("max_pain")
        iv_smile = primary.get("iv_smile") or []
    if gex_indicator is None:
        gex_indicator = run_gex_indicator(
            chain_out,
            underlying=float(underlying or u_avg or 0.0),
            multiplier=mult,
            T=t_avg,
            name="GEX",
        )

    capital_curve = build_capital_curve_by_month(
        {ms["month"]: (chains_by_month.get(ms["month"]) or []) for ms in month_series},
        underlying=float(underlying or u_avg or 0.0),
        multiplier=mult,
        margin_rate=margin_rate,
        months=[ms["month"] for ms in month_series],
    )

    tv_primary = primary.get("time_value_yield") or {}
    if not isinstance(tv_primary, dict):
        tv_primary = {}
    market_combo = combine_market_tv_yields(
        [ms.get("time_value_yield") or {} for ms in month_series]
    )
    if market_combo.get("market_yield") is not None:
        tv_primary = dict(tv_primary)
        tv_primary["market_yield"] = market_combo.get("market_yield")
        tv_primary["market_yield_weight"] = market_combo.get("market_yield_weight") or ""

    return {
        "root": code6,
        "name_cn": name_cn,
        "available": True,
        "has_option_chain": True,
        "months": months,
        "month": "all" if select_all else selected_months[0],
        "underlying": underlying,
        "current_price": underlying,
        "multiplier": mult,
        "margin_rate": margin_rate,
        "chain": chain_out,
        "greeks": greeks,
        "gex_summary": gex_summary,
        "gex_distribution": gex_distribution,
        "iv_smile": iv_smile,
        "max_pain": max_pain,
        "time_value_yield": tv_primary,
        "month_series": month_series,
        "capital_curve": capital_curve,
        "indicators": {"gex": gex_indicator},
        "data_source": data_source,
        "asof": datetime.now().isoformat(timespec="seconds"),
    }


def build_etf_options_panel(code: str, month: Optional[str] = None) -> Dict[str, Any]:
    from app.markets.cn_options import etf_underlying_display_name
    from app.services.cn_derivatives_analytics import (
        _ak,
        _mid,
        _safe_float,
        compute_gex,
        compute_max_pain,
    )
    from app.services.cn_derivatives_etf_capital import (
        compute_etf_time_value_annualized_yield,
    )
    from app.services.etf_options_clickhouse import (
        etf_options_panel_cache_ttl,
        try_load_etf_option_chains,
    )

    code6 = _etf_code6(code)
    if not code6:
        raise ValueError("underlying ETF code is required")

    month_raw = (month or "all").strip().lower()
    cache_key = f"etf_options_panel:v3:{code6}:{month_raw or 'all'}"
    cache_ttl = etf_options_panel_cache_ttl()
    cached = _etf_options_cache_get(cache_key)
    if cached:
        out = dict(cached)
        out["cache_hit"] = True
        return out

    name_cn = etf_underlying_display_name(code6)
    select_all = month_raw in {"", "all", "*", "全部"}

    ch_bundle = try_load_etf_option_chains(code6)
    if ch_bundle:
        months = list(ch_bundle.get("months") or [])
        selected_months = months[:8] if select_all else [month_raw]
        if not select_all and selected_months[0] not in months:
            selected_months = [months[0]] if months else selected_months
        underlying = float(ch_bundle.get("underlying") or 0.0)
        panel = _assemble_etf_options_panel(
            code6=code6,
            name_cn=name_cn,
            months=months,
            selected_months=selected_months,
            select_all=select_all,
            underlying=underlying,
            chains_by_month=ch_bundle.get("chains_by_month") or {},
            month_meta=ch_bundle.get("month_meta") or {},
            compute_gex=compute_gex,
            compute_max_pain=compute_max_pain,
            time_value_fn=compute_etf_time_value_annualized_yield,
            data_source="clickhouse",
        )
        if panel.get("month_series"):
            _etf_options_cache_set(cache_key, panel, cache_ttl)
            panel["cache_hit"] = False
            return panel
        logger.info("etf_options CH path empty for %s; falling back to Sina/SSE", code6)

    months = _etf_option_months(code6, _ak)
    if not months:
        return {
            "root": code6,
            "name_cn": name_cn,
            "months": [],
            "month": None,
            "available": False,
            "has_option_chain": False,
            "message": "暂未获取到该 ETF 期权的到期月份列表。",
            "data_source": "sina",
            "asof": datetime.now().isoformat(timespec="seconds"),
        }

    selected_months = months[:8] if select_all else [month_raw]
    if not select_all and selected_months[0] not in months:
        selected_months = [months[0]]

    etf_panel = build_etf_spot_panel(code6)
    underlying = float(etf_panel.get("spot_price") or 0.0)

    chains_by_month: Dict[str, List[Dict[str, Any]]] = {}
    month_meta: Dict[str, Dict[str, Any]] = {}
    for m in selected_months:
        chain, chain_meta = _etf_option_chain_from_current_day(code6, m, _ak, _mid, _safe_float)
        if not chain:
            continue
        chains_by_month[m] = chain
        month_meta[m] = {
            "multiplier": float(chain_meta.get("multiplier") or 10000.0),
            "T": float(chain_meta.get("T") or (30 / 365.0)),
        }

    panel = _assemble_etf_options_panel(
        code6=code6,
        name_cn=name_cn,
        months=months,
        selected_months=selected_months,
        select_all=select_all,
        underlying=underlying,
        chains_by_month=chains_by_month,
        month_meta=month_meta,
        compute_gex=compute_gex,
        compute_max_pain=compute_max_pain,
        time_value_fn=compute_etf_time_value_annualized_yield,
        data_source="sina",
    )
    if panel.get("month_series"):
        _etf_options_cache_set(cache_key, panel, cache_ttl)
    panel["cache_hit"] = False
    return panel


def _aggregate_etf_chains_by_strike(chains: List[List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
    """Merge option chains across months: sum OI, OI-weighted mids."""
    bucket: Dict[float, Dict[str, float]] = {}
    for chain in chains:
        for row in chain:
            k = float(row["strike"])
            item = bucket.setdefault(
                k,
                {
                    "strike": k,
                    "call_oi": 0.0,
                    "put_oi": 0.0,
                    "call_mid_w": 0.0,
                    "put_mid_w": 0.0,
                    "call_mid_n": 0.0,
                    "put_mid_n": 0.0,
                },
            )
            call_oi = float(row.get("call_oi") or 0.0)
            put_oi = float(row.get("put_oi") or 0.0)
            call_mid = float(row.get("call_mid") or 0.0)
            put_mid = float(row.get("put_mid") or 0.0)
            item["call_oi"] += call_oi
            item["put_oi"] += put_oi
            if call_oi > 0 and call_mid > 0:
                item["call_mid_w"] += call_mid * call_oi
                item["call_mid_n"] += call_oi
            if put_oi > 0 and put_mid > 0:
                item["put_mid_w"] += put_mid * put_oi
                item["put_mid_n"] += put_oi
    rows: List[Dict[str, Any]] = []
    for item in sorted(bucket.values(), key=lambda x: x["strike"]):
        rows.append(
            {
                "strike": item["strike"],
                "call_oi": item["call_oi"],
                "put_oi": item["put_oi"],
                "call_mid": (item["call_mid_w"] / item["call_mid_n"]) if item["call_mid_n"] > 0 else 0.0,
                "put_mid": (item["put_mid_w"] / item["put_mid_n"]) if item["put_mid_n"] > 0 else 0.0,
                "call_last": 0.0,
                "put_last": 0.0,
                "call_bid": 0.0,
                "call_ask": 0.0,
                "put_bid": 0.0,
                "put_ask": 0.0,
            }
        )
    return rows


def _query_local_daily_bars(symbol: str) -> List[Dict[str, Any]]:
    try:
        from app.data_sources.local_bar import query_local_kline

        return query_local_kline("CNStock", symbol, "1D", 1) or []
    except Exception:
        pass
    try:
        from app.services.market_data_maint import repository

        return repository.query_kline_bars(
            market="CNStock",
            symbol=symbol,
            timeframe="1D",
            limit=1,
        ) or []
    except Exception as exc:
        logger.debug("local ETF bar query %s failed: %s", symbol, exc)
        return []


def _last_local_bar(symbol: str) -> Optional[Dict[str, Any]]:
    """Latest daily bar from ``qd_market_bars`` (no upstream fallback)."""
    from app.markets.cn_options import cn_etf_stock_symbol

    raw = str(symbol or "").strip().upper()
    if not raw:
        return None
    candidates = [raw]
    if "." not in raw:
        candidates.append(cn_etf_stock_symbol(raw))
    seen: set[str] = set()
    for sym in candidates:
        if not sym or sym in seen:
            continue
        seen.add(sym)
        try:
            bars = _query_local_daily_bars(sym)
        except Exception as exc:
            logger.debug("local ETF bar %s failed: %s", sym, exc)
            continue
        if not bars:
            continue
        bar = bars[-1]
        try:
            price = float(bar.get("close") or 0.0)
        except (TypeError, ValueError):
            price = 0.0
        if price <= 0:
            continue
        try:
            volume = float(bar.get("volume") or 0.0)
        except (TypeError, ValueError):
            volume = 0.0
        return {
            "symbol": sym,
            "price": price,
            "volume": volume,
            "time": bar.get("time"),
            "source": "qd_market_bars",
        }
    return None


def _etf_row_from_local_bars(code6: str) -> Optional[Dict[str, Any]]:
    from app.markets.cn_options import cn_etf_stock_symbol, etf_underlying_display_name

    bar = _last_local_bar(cn_etf_stock_symbol(code6))
    if not bar:
        return None
    return {
        "code": code6,
        "name": _cn_display_name(code6, etf_underlying_display_name(code6)),
        "price": bar["price"],
        "volume": bar.get("volume"),
        "source": "qd_market_bars",
    }


def _index_row_from_local_bars(index_symbol: str) -> Optional[Dict[str, Any]]:
    sym = str(index_symbol or "").strip().upper()
    if not sym:
        return None
    bar = _last_local_bar(sym)
    if not bar:
        return None
    return {
        "code": sym,
        "name": _cn_display_name(sym, sym),
        "price": bar["price"],
        "source": "qd_market_bars",
    }


def _load_etf_spot_frame_sina(ak_fn) -> Any:
    """Load CN ETF spot quotes from Sina (no East Money)."""
    try:
        ak = ak_fn() if callable(ak_fn) else ak_fn
        return ak.fund_etf_category_sina(symbol="ETF基金")
    except Exception as exc:
        logger.warning("fund_etf_category_sina failed: %s", exc)
        return None


def _etf_row_from_spot(frame: Any, code6: str, safe_float) -> Optional[Dict[str, Any]]:
    if frame is None or getattr(frame, "empty", True):
        return None
    code_col = "代码" if "代码" in frame.columns else "code"
    for _, row in frame.iterrows():
        code = _etf_code6(row.get(code_col))
        if code != code6:
            continue
        return {
            "code": code6,
            "name": str(row.get("名称") or row.get("name") or code6),
            "price": safe_float(row.get("最新价") or row.get("price")),
            "iopv": safe_float(row.get("IOPV实时估值")),
            "premium_rate": safe_float(row.get("基金折价率")),
            "volume": safe_float(row.get("成交量")),
            "amount": safe_float(row.get("成交额")),
            "bid": safe_float(row.get("买入")),
            "ask": safe_float(row.get("卖出")),
        }
    return None


def _index_row_from_spot(frame: Any, index_code: str, safe_float) -> Optional[Dict[str, Any]]:
    if frame is None or getattr(frame, "empty", True):
        return None
    want = str(index_code or "").strip().lower()
    code_col = "代码" if "代码" in frame.columns else "code"
    for _, row in frame.iterrows():
        code = str(row.get(code_col) or "").strip().lower()
        if not code:
            continue
        if code == want or code.endswith(want) or want in code:
            return {
                "code": index_code,
                "name": str(row.get("名称") or row.get("name") or index_code),
                "price": safe_float(row.get("最新价") or row.get("price")),
            }
    return None


def _etf_option_exchange(code6: str) -> str:
    from app.markets.cn_options import infer_cn_etf_board

    board = infer_cn_etf_board(code6)
    return "SZSE" if board == "SZ" else "SSE"


def _etf_sse_list_symbol(code6: str) -> str:
    return ETF_SSE_LIST_NAME.get(code6, "50ETF")


def _etf_underlying_col_matches(underlying_col: str, code6: str) -> bool:
    col = str(underlying_col or "")
    if not col or not code6:
        return False
    if re.search(rf"(?:^|\D){re.escape(code6)}(?:\D|$)", col):
        return True
    return code6 in col


def _etf_option_months(code6: str, ak_fn) -> List[str]:
    list_symbol = _etf_sse_list_symbol(code6)
    try:
        months = ak_fn().option_sse_list_sina(symbol=list_symbol)
        return [str(m).strip().lower() for m in (months or []) if str(m).strip()]
    except Exception as exc:
        logger.warning("etf option months %s failed: %s", code6, exc)
        return []


def _etf_option_T_from_month(month_yyyymm: str) -> float:
    month_digits = "".join(ch for ch in str(month_yyyymm or "") if ch.isdigit())
    if len(month_digits) == 4:
        yy = int(month_digits[:2])
        mm = int(month_digits[2:])
        expiry = date(2000 + yy, mm, 25)
        return max((expiry - date.today()).days / 365.0, 1 / 365.0)
    if len(month_digits) == 6:
        yy = int(month_digits[:4])
        mm = int(month_digits[4:6])
        expiry = date(yy, max(1, min(mm, 12)), 25)
        return max((expiry - date.today()).days / 365.0, 1 / 365.0)
    return 30 / 365.0


def _etf_option_T_from_expiry_key(expiry_key: str) -> Optional[float]:
    digits = re.sub(r"\D", "", str(expiry_key or ""))
    if len(digits) < 8:
        return None
    try:
        expiry = date(int(digits[:4]), int(digits[4:6]), int(digits[6:8]))
        return max((expiry - date.today()).days / 365.0, 1 / 365.0)
    except ValueError:
        return None


def _etf_option_T_from_row(row: Any, month_yyyymm: str, safe_float) -> float:
    for key in ("期权行权日", "到期日", "行权日"):
        raw = row.get(key)
        if raw is None:
            continue
        if hasattr(raw, "strftime"):
            expiry_key = raw.strftime("%Y%m%d")
        else:
            expiry_key = str(raw)
        t_val = _etf_option_T_from_expiry_key(expiry_key)
        if t_val is not None:
            return t_val
    return _etf_option_T_from_month(month_yyyymm)


def _load_option_current_day_frame(ak_fn, exchange: str) -> Any:
    fn_name = "option_current_day_szse" if exchange == "SZSE" else "option_current_day_sse"
    for attempt in range(3):
        try:
            fn = getattr(ak_fn(), fn_name, None)
            if not callable(fn):
                return None
            return fn()
        except Exception as exc:
            if attempt + 1 >= 3:
                logger.warning("%s failed: %s", fn_name, exc)
            else:
                time.sleep(0.35 * (attempt + 1))
    return None


def _normalize_option_listing_row(row: Any, exchange: str) -> Dict[str, Any]:
    if exchange == "SZSE":
        expiry = row.get("行权日")
        if hasattr(expiry, "strftime"):
            expiry_key = expiry.strftime("%Y%m%d")
        else:
            expiry_key = str(expiry or "")
        return {
            "underlying_col": str(row.get("标的证券简称(代码)") or ""),
            "contract_id": str(row.get("合约代码") or ""),
            "code": str(row.get("合约编码") or "").strip(),
            "strike": row.get("行权价"),
            "opt_type": str(row.get("合约类型") or "").strip(),
            "contract_unit": row.get("合约单位"),
            "expiry_row": row,
            "listing_oi": row.get("合约总持仓"),
            "prev_settle": row.get("前结算价"),
        }
    return {
        "underlying_col": str(row.get("标的券名称及代码") or ""),
        "contract_id": str(row.get("合约交易代码") or ""),
        "code": str(row.get("合约编码") or "").strip(),
        "strike": row.get("行权价"),
        "opt_type": str(row.get("类型") or "").strip(),
        "contract_unit": row.get("合约单位"),
        "expiry_row": row,
        "listing_oi": None,
        "prev_settle": None,
    }


def _normalize_sse_option_month_key(month_yyyymm: str) -> str:
    month_key = str(month_yyyymm or "").strip().lower()
    if len(month_key) == 6 and month_key.isdigit():
        return month_key[2:]
    return month_key


def _empty_etf_option_chain_bucket(strike: float) -> Dict[str, Any]:
    return {
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
    }


def _sse_option_spot_values(spot_frame: Any, safe_float, mid_fn) -> Dict[str, float]:
    """Parse akshare option_sse_spot_price_sina key/value frame into quote fields."""
    if spot_frame is None or getattr(spot_frame, "empty", True):
        return {}
    values = {
        str(row.get("字段") or "").strip(): str(row.get("值") or "").strip()
        for _, row in spot_frame.iterrows()
    }
    bid = safe_float(values.get("买价") or values.get("申买价一"))
    ask = safe_float(values.get("卖价") or values.get("申卖价一"))
    last = safe_float(values.get("最新价"))
    oi = safe_float(values.get("持仓量"))
    mid = mid_fn(bid, ask, last)
    underlying = str(values.get("标的股票") or values.get("标的证券") or "").strip()
    return {
        "bid": bid,
        "ask": ask,
        "last": last,
        "mid": mid,
        "oi": oi,
        "underlying": underlying,
    }


def _apply_sse_option_quote(
    bucket: Dict[str, Any],
    opt_type: str,
    quote: Dict[str, float],
    *,
    listing_oi: float = 0.0,
    prev_settle: float = 0.0,
) -> None:
    bid = float(quote.get("bid") or 0.0)
    ask = float(quote.get("ask") or 0.0)
    last = float(quote.get("last") or 0.0)
    mid = float(quote.get("mid") or 0.0)
    oi = float(quote.get("oi") or 0.0)
    if oi <= 0 and listing_oi > 0:
        oi = float(listing_oi)
    if mid <= 0 and prev_settle > 0:
        mid = float(prev_settle)
        if last <= 0:
            last = mid
    if opt_type == "认购":
        bucket["call_bid"] = bid
        bucket["call_ask"] = ask
        bucket["call_last"] = last if last > 0 else mid
        bucket["call_mid"] = mid
        bucket["call_oi"] = oi
    elif opt_type == "认沽":
        bucket["put_bid"] = bid
        bucket["put_ask"] = ask
        bucket["put_last"] = last if last > 0 else mid
        bucket["put_mid"] = mid
        bucket["put_oi"] = oi


def _fetch_sse_option_quote(
    ak_fn,
    contract_code: str,
    code6: str,
    safe_float,
    mid_fn,
    *,
    retries: int = 3,
) -> Dict[str, float]:
    code = str(contract_code or "").strip()
    if not code:
        return {}
    for attempt in range(max(1, retries)):
        try:
            spot = ak_fn().option_sse_spot_price_sina(symbol=code)
            quote = _sse_option_spot_values(spot, safe_float, mid_fn)
            if not quote:
                continue
            underlying = _etf_code6(quote.get("underlying") or "")
            if underlying and underlying != code6:
                return {}
            return quote
        except Exception as exc:
            if attempt + 1 >= retries:
                logger.debug("etf option quote %s failed: %s", code, exc)
            else:
                time.sleep(0.12 * (attempt + 1))
    return {}


def _apply_listing_fallback_quote(
    bucket: Dict[str, Any],
    opt_type: str,
    listing_oi: float,
    prev_settle: float,
    safe_float,
) -> None:
    oi = safe_float(listing_oi)
    mid = safe_float(prev_settle)
    if oi <= 0 and mid <= 0:
        return
    _apply_sse_option_quote(
        bucket,
        opt_type,
        {"bid": 0.0, "ask": 0.0, "last": mid, "mid": mid, "oi": oi},
        listing_oi=oi,
        prev_settle=mid,
    )


def _etf_option_chain_from_current_day(
    code6: str,
    month_yyyymm: str,
    ak_fn,
    mid_fn,
    safe_float,
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    exchange = _etf_option_exchange(code6)
    meta: Dict[str, Any] = {
        "multiplier": 10000.0,
        "T": _etf_option_T_from_month(month_yyyymm),
        "exchange": exchange,
    }
    frame = _load_option_current_day_frame(ak_fn, exchange)
    if frame is None or getattr(frame, "empty", True):
        return [], meta

    month_key = _normalize_sse_option_month_key(month_yyyymm)
    pending: List[Dict[str, Any]] = []
    strikes: Dict[float, Dict[str, Any]] = {}
    for _, row in frame.iterrows():
        norm = _normalize_option_listing_row(row, exchange)
        if not _etf_underlying_col_matches(norm["underlying_col"], code6):
            continue
        contract_id = norm["contract_id"]
        if month_key and month_key not in contract_id:
            continue
        strike = safe_float(norm["strike"])
        if strike <= 0:
            continue
        opt_type = norm["opt_type"]
        contract_unit = safe_float(norm["contract_unit"])
        if contract_unit > 0:
            meta["multiplier"] = contract_unit
        expiry_row = norm.get("expiry_row")
        if expiry_row is not None:
            meta["T"] = _etf_option_T_from_row(expiry_row, month_yyyymm, safe_float)
        bucket = strikes.setdefault(strike, _empty_etf_option_chain_bucket(strike))
        code = norm["code"]
        if not code:
            continue
        listing_oi = safe_float(norm.get("listing_oi"))
        prev_settle = safe_float(norm.get("prev_settle"))
        pending.append(
            {
                "code": code,
                "strike": strike,
                "opt_type": opt_type,
                "bucket": bucket,
                "listing_oi": listing_oi,
                "prev_settle": prev_settle,
            }
        )

    if not pending:
        return [], meta

    quote_by_code: Dict[str, Dict[str, float]] = {}
    max_workers = min(8, len(pending))
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = {
            pool.submit(
                _fetch_sse_option_quote,
                ak_fn,
                item["code"],
                code6,
                safe_float,
                mid_fn,
            ): item["code"]
            for item in pending
        }
        for future in as_completed(futures):
            code = futures[future]
            try:
                quote = future.result()
            except Exception as exc:
                logger.debug("etf option quote task %s failed: %s", code, exc)
                quote = {}
            if quote:
                quote_by_code[code] = quote

    for item in pending:
        quote = quote_by_code.get(item["code"])
        if quote:
            _apply_sse_option_quote(
                item["bucket"],
                item["opt_type"],
                quote,
                listing_oi=item.get("listing_oi") or 0.0,
                prev_settle=item.get("prev_settle") or 0.0,
            )
        else:
            _apply_listing_fallback_quote(
                item["bucket"],
                item["opt_type"],
                item.get("listing_oi") or 0.0,
                item.get("prev_settle") or 0.0,
                safe_float,
            )

    rows = list(strikes.values())
    rows.sort(key=lambda item: item["strike"])
    return rows, meta
