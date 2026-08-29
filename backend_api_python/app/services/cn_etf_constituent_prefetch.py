"""Prefetch ETF-option constituent history + profit/PE for faster ETF analysis.

Workflow:
1. Resolve ETF option underlyings (known + currently listed).
2. Load full benchmark-index constituents (fallback: fund portfolio).
3. Warm per-stock profit / PE / market-cap snapshots into Redis + Postgres.
4. Rebuild ETF holdings/metrics Redis bundles so the UI hits cache.
5. Optionally register constituent CNStock daily bars into market-data maint.
"""

from __future__ import annotations

import os
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Sequence, Set

from app.utils.logger import get_logger

logger = get_logger(__name__)


def _bool_env(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return str(raw).strip().lower() in {"1", "true", "yes", "on"}


def _int_env(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except Exception:
        return default


def _code6(value: Any) -> str:
    digits = re.sub(r"\D", "", str(value or ""))
    return digits[:6] if len(digits) >= 6 else digits


def list_etf_option_underlyings(*, include_listed: bool = True) -> List[str]:
    """ETF codes that have (or historically had) listed options."""
    from app.markets.cn_options import KNOWN_ETF_UNDERLYINGS

    codes: List[str] = []
    seen: Set[str] = set()
    for code in KNOWN_ETF_UNDERLYINGS.keys():
        c = _code6(code)
        if c and c not in seen:
            seen.add(c)
            codes.append(c)
    if include_listed:
        try:
            from app.services.cn_options_chain import listed_etf_underlying_codes

            for code in listed_etf_underlying_codes() or []:
                c = _code6(code)
                if c and c not in seen:
                    seen.add(c)
                    codes.append(c)
        except Exception as exc:
            logger.warning("listed_etf_underlying_codes failed: %s", exc)
    codes.sort()
    return codes


def collect_constituent_universe(
    etf_codes: Optional[Sequence[str]] = None,
) -> Dict[str, Any]:
    """Map ETF underlyings -> constituent stocks (prefer full index members)."""
    from app.services import cn_derivatives_etf_metrics as metrics

    etfs = [_code6(c) for c in (etf_codes or list_etf_option_underlyings()) if _code6(c)]
    by_etf: Dict[str, Dict[str, Any]] = {}
    all_codes: Set[str] = set()
    index_codes: Set[str] = set()

    for etf in etfs:
        rows, source, quarter = metrics._load_constituent_base_rows(etf)
        codes = [_code6(r.get("code")) for r in rows if _code6(r.get("code"))]
        names = {
            _code6(r.get("code")): str(r.get("name") or "")
            for r in rows
            if _code6(r.get("code"))
        }
        index_code = metrics._benchmark_index_code(etf)
        if index_code:
            index_codes.add(str(index_code))
        by_etf[etf] = {
            "etf": etf,
            "index_code": index_code,
            "source": source,
            "quarter": quarter,
            "count": len(codes),
            "codes": codes,
            "names": names,
        }
        all_codes.update(codes)

    return {
        "etf_codes": etfs,
        "index_codes": sorted(index_codes),
        "constituent_codes": sorted(all_codes),
        "constituent_count": len(all_codes),
        "by_etf": by_etf,
        "asof": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }


def _stock_board_symbol(code6: str) -> str:
    from app.markets.cn_options import cn_symbol_with_board

    board = "SH" if code6.startswith(("5", "6", "9")) else "SZ"
    return cn_symbol_with_board(code6, board)


def register_constituent_history_watch(
    codes: Sequence[str],
    *,
    timeframe: str = "1D",
    lookback_bars: Optional[int] = None,
) -> int:
    """Register CNStock daily watch specs so market-data maint keeps history."""
    from app.services.market_data_maint.config import WatchSpec
    from app.services.market_data_maint import repository

    lookback = lookback_bars or _int_env("ETF_CONSTITUENT_HISTORY_LOOKBACK_BARS", 800)
    specs: List[WatchSpec] = []
    for code in codes or []:
        code6 = _code6(code)
        if not code6:
            continue
        specs.append(
            WatchSpec(
                market="CNStock",
                symbol=_stock_board_symbol(code6),
                timeframe=timeframe,
                exchange_id="",
                market_type="spot",
                lookback_bars=lookback,
            )
        )
    if not specs:
        return 0
    try:
        return int(repository.upsert_watch_specs(specs) or 0)
    except Exception as exc:
        logger.warning("register constituent history watch failed: %s", exc)
        return 0


def warm_constituent_snapshots(
    codes: Sequence[str],
    *,
    names: Optional[Dict[str, str]] = None,
    force: bool = False,
    workers: Optional[int] = None,
    persist: bool = True,
) -> Dict[str, Any]:
    """Fetch + cache per-stock profit/PE/mcap; optionally persist to Postgres."""
    from app.services import cn_derivatives_etf_metrics as metrics
    from app.services import cn_etf_constituent_store as store

    unique: List[str] = []
    seen: Set[str] = set()
    for code in codes or []:
        c = _code6(code)
        if c and c not in seen:
            seen.add(c)
            unique.append(c)

    if not unique:
        return {
            "total": 0,
            "warmed": 0,
            "cached": 0,
            "failed": 0,
            "persisted": 0,
            "pending": 0,
        }

    if persist:
        try:
            store.ensure_schema()
        except Exception as exc:
            logger.warning("constituent store schema ensure failed: %s", exc)

    pending: List[str] = []
    cached_hits = 0
    if force:
        pending = list(unique)
    else:
        db_map = store.load_snapshots(unique) if persist else {}
        for code in unique:
            hit = metrics._cache_get(f"etf:constituent_snapshot:{code}")
            if isinstance(hit, dict) and any(
                hit.get(k) is not None
                for k in ("net_profit", "pe_ratio", "market_cap", "profit_margin")
            ):
                cached_hits += 1
                continue
            db_hit = db_map.get(code) or {}
            if db_hit:
                metrics._cache_set(
                    f"etf:constituent_snapshot:{code}",
                    db_hit,
                    metrics._PROFIT_CACHE_TTL,
                )
                if db_hit.get("net_profit") is not None:
                    metrics._cache_set(
                        f"etf:stock_net_profit:{code}",
                        db_hit["net_profit"],
                        metrics._PROFIT_CACHE_TTL,
                    )
                cached_hits += 1
                continue
            pending.append(code)

    workers_n = max(1, min(int(workers or _int_env("ETF_CONSTITUENT_PREFETCH_WORKERS", 4)), 8))
    warmed = 0
    failed = 0
    persisted = 0
    name_map = names or {}

    def _one(code: str) -> Dict[str, Any]:
        snap = metrics._stock_constituent_snapshot(code) or {}
        if persist and snap:
            store.upsert_snapshot(
                code,
                snap,
                name=name_map.get(code, ""),
                source="prefetch",
            )
        return snap

    if pending:
        with ThreadPoolExecutor(max_workers=workers_n) as pool:
            futures = {pool.submit(_one, code): code for code in pending}
            for fut in as_completed(futures):
                code = futures[fut]
                try:
                    snap = fut.result() or {}
                    if any(
                        snap.get(k) is not None
                        for k in ("net_profit", "pe_ratio", "market_cap", "profit_margin")
                    ):
                        warmed += 1
                        if persist:
                            persisted += 1
                    else:
                        failed += 1
                except Exception as exc:
                    failed += 1
                    logger.debug("warm snapshot %s failed: %s", code, exc)

    return {
        "total": len(unique),
        "pending": len(pending),
        "warmed": warmed,
        "cached": cached_hits,
        "failed": failed,
        "persisted": persisted,
        "workers": workers_n,
    }


def warm_etf_metric_bundles(
    etf_codes: Sequence[str],
    *,
    force: bool = False,
) -> Dict[str, Any]:
    """Rebuild holdings/metrics Redis bundles for ETF underlyings."""
    from app.services import cn_derivatives_etf_metrics as metrics
    from app.utils.cache import CacheManager

    ok = 0
    failed = 0
    skipped = 0
    details: List[Dict[str, Any]] = []
    cache = None
    try:
        cache = CacheManager()
    except Exception:
        cache = None

    for raw in etf_codes or []:
        code = _code6(raw)
        if not code:
            continue
        if not force:
            cached = metrics._cache_get(f"etf:holdings_profit:v3:{code}")
            if isinstance(cached, dict) and int(cached.get("holdings_count") or 0) > 0:
                skipped += 1
                details.append(
                    {
                        "etf": code,
                        "status": "cached",
                        "holdings": cached.get("holdings_count"),
                    }
                )
                continue
        try:
            if force and cache is not None:
                for key in (
                    f"etf:holdings_profit:v3:{code}",
                    f"etf:holdings_base:v1:{code}",
                    f"etf:metrics_bundle:v2:{code}",
                ):
                    try:
                        cache.delete(key)
                    except Exception:
                        pass
            enriched = metrics.enrich_etf_metrics(code)
            ok += 1
            details.append(
                {
                    "etf": code,
                    "status": "ok",
                    "holdings": enriched.get("holdings_count"),
                    "profit_coverage": enriched.get("constituent_profit_coverage"),
                    "pe_coverage": enriched.get("pe_coverage"),
                }
            )
        except Exception as exc:
            failed += 1
            details.append({"etf": code, "status": "failed", "error": str(exc)[:200]})
            logger.warning("warm etf metrics %s failed: %s", code, exc)
    return {"ok": ok, "failed": failed, "skipped": skipped, "details": details}


def run_etf_constituent_prefetch_cycle(
    *,
    etf_codes: Optional[Sequence[str]] = None,
    force: bool = False,
    include_history: Optional[bool] = None,
    warm_bundles: bool = True,
    trigger: str = "manual",
) -> Dict[str, Any]:
    """End-to-end prefetch cycle used by CLI and Celery Beat."""
    started = time.time()
    if include_history is None:
        include_history = _bool_env("ETF_CONSTITUENT_PREFETCH_HISTORY", True)

    universe = collect_constituent_universe(etf_codes)
    name_map: Dict[str, str] = {}
    for item in (universe.get("by_etf") or {}).values():
        name_map.update(item.get("names") or {})

    snap_stats = warm_constituent_snapshots(
        universe.get("constituent_codes") or [],
        names=name_map,
        force=force,
    )

    history_written = 0
    if include_history:
        history_written = register_constituent_history_watch(
            universe.get("constituent_codes") or []
        )

    bundle_stats: Dict[str, Any] = {"ok": 0, "failed": 0, "skipped": 0, "details": []}
    if warm_bundles:
        bundle_stats = warm_etf_metric_bundles(universe.get("etf_codes") or [], force=force)

    elapsed = round(time.time() - started, 2)
    result = {
        "trigger": trigger,
        "elapsed_sec": elapsed,
        "etf_count": len(universe.get("etf_codes") or []),
        "index_codes": universe.get("index_codes") or [],
        "constituent_count": universe.get("constituent_count") or 0,
        "snapshots": snap_stats,
        "history_watch_written": history_written,
        "bundles": {
            "ok": bundle_stats.get("ok"),
            "failed": bundle_stats.get("failed"),
            "skipped": bundle_stats.get("skipped"),
            "details": bundle_stats.get("details") or [],
        },
        "asof": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    logger.info(
        "etf constituent prefetch done trigger=%s etfs=%s stocks=%s warmed=%s/%s history=%s elapsed=%.1fs",
        trigger,
        result["etf_count"],
        result["constituent_count"],
        snap_stats.get("warmed"),
        snap_stats.get("total"),
        history_written,
        elapsed,
    )
    return result
