"""Coverage and dimension aggregates for data-service governance charts."""

from __future__ import annotations

from collections import defaultdict
from typing import Any, Dict, Iterable, List, Optional, Tuple

TF_ORDER = [
    "1m",
    "3m",
    "5m",
    "15m",
    "30m",
    "1h",
    "2h",
    "4h",
    "6h",
    "8h",
    "12h",
    "1d",
    "1w",
    "1M",
]


def _blank(value: Any, fallback: str = "未知") -> str:
    text = str(value or "").strip()
    return text if text else fallback


def _sym_key(row: Dict[str, Any]) -> Tuple[str, str, str]:
    return (
        _blank(row.get("market"), "").lower(),
        _blank(row.get("symbol"), "").upper(),
        _blank(row.get("exchange_id"), "").upper(),
    )


def _series_key(row: Dict[str, Any]) -> Tuple[str, str, str, str]:
    return (*_sym_key(row), _blank(row.get("timeframe"), "").lower())


def _tf_rank(tf: str) -> int:
    key = str(tf or "").lower()
    try:
        return TF_ORDER.index(key)
    except ValueError:
        return 1000


def _sane_ts(value: Any) -> Optional[int]:
    try:
        ts = int(value)
    except (TypeError, ValueError):
        return None
    if ts > 10_000_000_000:
        ts //= 1000
    # Ignore epoch-near / far-future timestamps that collapse the time axis.
    if ts < 946_684_800 or ts > 4_102_444_800:
        return None
    return ts


def _pct(num: int, den: int) -> Optional[float]:
    if den <= 0:
        return None
    return round(100.0 * num / den, 1)


def _agg_dimension(rows: Iterable[Dict[str, Any]], field: str) -> List[Dict[str, Any]]:
    buckets: Dict[str, Dict[str, Any]] = {}
    symbols: Dict[str, set] = defaultdict(set)
    for row in rows:
        name = _blank(row.get(field))
        bucket = buckets.setdefault(
            name,
            {"name": name, "barCount": 0, "seriesCount": 0, "symbolCount": 0},
        )
        bucket["barCount"] += int(row.get("bar_count") or 0)
        bucket["seriesCount"] += 1
        symbols[name].add(_sym_key(row))
    for name, bucket in buckets.items():
        bucket["symbolCount"] = len(symbols[name])
    return sorted(buckets.values(), key=lambda item: (-item["barCount"], item["name"]))


def _agg_symbols(rows: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    buckets: Dict[Tuple[str, str, str], Dict[str, Any]] = {}
    for row in rows:
        key = _sym_key(row)
        if not key[1]:
            continue
        market = _blank(row.get("market"))
        symbol = _blank(row.get("symbol"), "?")
        exchange = _blank(row.get("exchange_id"), "")
        name = f"{market}:{symbol}" + (f"@{exchange}" if exchange else "")
        bucket = buckets.setdefault(
            key,
            {
                "name": name,
                "market": market,
                "symbol": symbol,
                "exchangeId": exchange,
                "barCount": 0,
                "seriesCount": 0,
            },
        )
        bucket["barCount"] += int(row.get("bar_count") or 0)
        bucket["seriesCount"] += 1
    return sorted(buckets.values(), key=lambda item: (-item["barCount"], item["name"]))


def build_governance_charts(
    *,
    watch_rows: List[Dict[str, Any]],
    inventory_rows: List[Dict[str, Any]],
    symbol_limit: int = 40,
    timeline_limit: int = 120,
) -> Dict[str, Any]:
    inventory = [dict(row) for row in (inventory_rows or [])]
    with_data = [row for row in inventory if int(row.get("bar_count") or 0) > 0]
    watch = [
        dict(row)
        for row in (watch_rows or [])
        if row.get("enabled", True) and str(row.get("symbol") or "").strip()
    ]

    symbol_limit = max(1, int(symbol_limit or 40))
    timeline_limit = max(1, int(timeline_limit or 120))

    by_market = _agg_dimension(with_data, "market")
    by_exchange = _agg_dimension(with_data, "exchange_id")
    by_symbol_all = _agg_symbols(with_data)

    by_tf_bars: Dict[str, int] = defaultdict(int)
    by_tf_series: Dict[str, int] = defaultdict(int)
    for row in with_data:
        tf = _blank(row.get("timeframe"), "—")
        by_tf_bars[tf] += int(row.get("bar_count") or 0)
        by_tf_series[tf] += 1
    by_timeframe = [
        {"name": tf, "barCount": by_tf_bars[tf], "seriesCount": by_tf_series[tf]}
        for tf in sorted(by_tf_bars, key=_tf_rank)
    ]

    watch_symbols = {_sym_key(row) for row in watch}
    inv_symbols = {_sym_key(row) for row in with_data if row.get("symbol")}
    covered_symbols = watch_symbols & inv_symbols
    missing_symbols = [
        {"market": market or None, "symbol": symbol, "exchangeId": exchange or None}
        for market, symbol, exchange in sorted(watch_symbols - inv_symbols)
    ]

    watch_series = {
        _series_key(row) for row in watch if str(row.get("timeframe") or "").strip()
    }
    inv_series = {_series_key(row) for row in with_data}
    covered_series = watch_series & inv_series

    expected_tf: Dict[str, int] = defaultdict(int)
    covered_tf: Dict[str, int] = defaultdict(int)
    for row in watch:
        tf = _blank(row.get("timeframe"), "—")
        expected_tf[tf] += 1
        if int(row.get("bar_count") or 0) > 0 or _series_key(row) in inv_series:
            covered_tf[tf] += 1

    tf_coverage_rows = [
        {
            "timeframe": tf,
            "expected": expected_tf[tf],
            "covered": covered_tf[tf],
            "coveragePct": _pct(covered_tf[tf], expected_tf[tf]),
        }
        for tf in sorted(expected_tf, key=_tf_rank)
    ]

    depths: List[float] = []
    inv_by_series = {_series_key(row): int(row.get("bar_count") or 0) for row in with_data}
    for row in watch:
        lookback = max(1, int(row.get("lookback_bars") or 1500))
        count = int(row.get("bar_count") or 0)
        if count <= 0:
            count = inv_by_series.get(_series_key(row), 0)
        depths.append(min(1.0, count / lookback))
    avg_depth = round(100.0 * (sum(depths) / len(depths)), 1) if depths else None

    timeline_all: List[Dict[str, Any]] = []
    for row in with_data:
        min_t = _sane_ts(row.get("min_time"))
        max_t = _sane_ts(row.get("max_time"))
        if min_t is None or max_t is None or max_t < min_t:
            continue
        symbol = _blank(row.get("symbol"), "?")
        tf = _blank(row.get("timeframe"), "?")
        exchange = _blank(row.get("exchange_id"), "")
        label = f"{symbol} {tf}" + (f" ({exchange})" if exchange else "")
        timeline_all.append(
            {
                "label": label,
                "market": _blank(row.get("market")),
                "symbol": symbol,
                "timeframe": tf,
                "exchangeId": exchange,
                "minTime": int(min_t),
                "maxTime": int(max_t),
                "barCount": int(row.get("bar_count") or 0),
            }
        )
    timeline_all.sort(key=lambda item: (item["minTime"], item["symbol"], item["timeframe"]))

    return {
        "byMarket": by_market,
        "byExchange": by_exchange,
        "bySymbol": by_symbol_all[:symbol_limit],
        "byTimeframe": by_timeframe,
        "coverage": {
            "watchSymbols": len(watch_symbols),
            "symbolsWithData": len(covered_symbols) if watch_symbols else len(inv_symbols),
            "symbolCoveragePct": _pct(len(covered_symbols), len(watch_symbols)),
            "missingSymbols": missing_symbols[:30],
            "watchSeries": len(watch_series),
            "seriesWithData": len(covered_series) if watch_series else len(inv_series),
            "timeframeCoveragePct": _pct(len(covered_series), len(watch_series)),
            "avgDepthPct": avg_depth,
            "byTimeframe": tf_coverage_rows,
        },
        "timeline": timeline_all[:timeline_limit],
        "timelineTotal": len(timeline_all),
        "timelineTruncated": len(timeline_all) > timeline_limit,
        "symbolTruncated": len(by_symbol_all) > symbol_limit,
        "totals": {
            "series": len(with_data),
            "bars": sum(int(row.get("bar_count") or 0) for row in with_data),
            "symbols": len(inv_symbols),
        },
    }
