#!/usr/bin/env python3
"""Persist US stock / ETF bars into qd_market_bars for local-first backtests.

Uses Nasdaq historical API with ETF-aware assetclass fallback so SPY/QQQ work
even when yfinance is rate-limited and older USStockDataSource builds only
request ``assetclass=stocks``.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime, timedelta, timezone
from typing import Any

import requests

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)


DEFAULT_SYMBOLS = (
    "SPY",
    "QQQ",
    "AAPL",
    "MSFT",
    "NVDA",
    "AMZN",
    "META",
    "GOOGL",
    "AVGO",
    "COST",
    "JPM",
    "XOM",
)

KNOWN_ETFS = frozenset({
    "SPY", "QQQ", "IWM", "DIA", "VOO", "VTI", "IVV", "SPLG", "RSP",
    "XLK", "XLF", "XLE", "XLV", "XLY", "XLP", "XLI", "XLB", "XLU", "XLRE",
    "ARKK", "SMH", "SOXX", "GLD", "SLV", "USO", "TLT", "HYG", "LQD", "AGG",
    "EEM", "EFA", "VEA", "VWO", "IEMG",
})

NASDAQ_HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Accept": "application/json, text/plain, */*",
    "Origin": "https://www.nasdaq.com",
    "Referer": "https://www.nasdaq.com/market-activity/stocks",
}


def _parse_num(value: Any, default: float = 0.0) -> float:
    if value is None:
        return default
    try:
        text = str(value).strip().replace("$", "").replace(",", "").replace("%", "").replace("+", "")
        if not text or text in {"--", "N/A"}:
            return default
        return float(text)
    except Exception:
        return default


def _asset_classes(symbol: str) -> tuple[str, ...]:
    if symbol.upper() in KNOWN_ETFS:
        return ("etf", "stocks")
    return ("stocks", "etf")


def fetch_nasdaq_daily(symbol: str, *, days: int, limit: int) -> list[dict[str, Any]]:
    end = datetime.now(timezone.utc)
    start = end - timedelta(days=max(30, int(days)))
    for assetclass in _asset_classes(symbol):
        try:
            resp = requests.get(
                f"https://api.nasdaq.com/api/quote/{symbol}/historical",
                params={
                    "assetclass": assetclass,
                    "fromdate": start.strftime("%Y-%m-%d"),
                    "todate": end.strftime("%Y-%m-%d"),
                    "limit": max(int(limit or 100), 100),
                },
                timeout=20,
                headers=NASDAQ_HEADERS,
            )
            resp.raise_for_status()
            rows = ((((resp.json().get("data") or {}).get("tradesTable")) or {}).get("rows")) or []
            bars: list[dict[str, Any]] = []
            for row in rows:
                try:
                    dt = datetime.strptime(str(row.get("date")), "%m/%d/%Y").replace(tzinfo=timezone.utc)
                    open_price = _parse_num(row.get("open"))
                    high = _parse_num(row.get("high"))
                    low = _parse_num(row.get("low"))
                    close = _parse_num(row.get("close"))
                    if min(open_price, high, low, close) <= 0:
                        continue
                    bars.append(
                        {
                            "time": int(dt.timestamp()),
                            "open": open_price,
                            "high": high,
                            "low": low,
                            "close": close,
                            "volume": _parse_num(row.get("volume")),
                        }
                    )
                except Exception:
                    continue
            if bars:
                bars.sort(key=lambda b: b["time"])
                return bars[-limit:] if limit and len(bars) > limit else bars
        except Exception:
            continue
    return []


def derive_weekly(bars_1d: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not bars_1d:
        return []
    out: list[dict[str, Any]] = []
    bucket: list[dict[str, Any]] = []
    current_week: int | None = None
    for bar in bars_1d:
        week = int(bar["time"]) // 604800
        if current_week is None:
            current_week = week
        if week != current_week:
            if bucket:
                out.append(
                    {
                        "time": int(bucket[-1]["time"]),
                        "open": float(bucket[0]["open"]),
                        "high": max(float(b["high"]) for b in bucket),
                        "low": min(float(b["low"]) for b in bucket),
                        "close": float(bucket[-1]["close"]),
                        "volume": float(sum(float(b.get("volume") or 0) for b in bucket)),
                    }
                )
            bucket = []
            current_week = week
        bucket.append(bar)
    if bucket:
        out.append(
            {
                "time": int(bucket[-1]["time"]),
                "open": float(bucket[0]["open"]),
                "high": max(float(b["high"]) for b in bucket),
                "low": min(float(b["low"]) for b in bucket),
                "close": float(bucket[-1]["close"]),
                "volume": float(sum(float(b.get("volume") or 0) for b in bucket)),
            }
        )
    return out


def upsert(market: str, symbol: str, timeframe: str, bars: list[dict[str, Any]], *, dry_run: bool) -> int:
    if dry_run or not bars:
        return 0
    from app.services.market_data_maint import repository
    from app.services.market_data_maint.config import WatchSpec
    from app.services.market_data_maint.validators import sanitize_bars

    clean = sanitize_bars(bars).clean_bars
    if not clean:
        return 0
    spec = WatchSpec(
        market=market,
        symbol=symbol,
        timeframe=timeframe,
        exchange_id="",
        market_type="spot",
        lookback_bars=max(len(clean), 2000),
    )
    return int(repository.upsert_bars(spec, clean, source="us_stock_nasdaq_backfill") or 0)


def backfill_cn_stock(symbols: list[str], *, limit: int, dry_run: bool, sleep_s: float) -> dict[str, Any]:
    from app.data_sources.cn_stock import CNStockDataSource
    from app.services.market_data_maint.validators import sanitize_bars

    src = CNStockDataSource()
    summary: dict[str, Any] = {"targets": [], "upserted": 0}
    for i, symbol in enumerate(symbols):
        if i:
            time.sleep(max(0.0, sleep_s))
        item: dict[str, Any] = {"market": "CNStock", "symbol": symbol, "timeframes": {}}
        for tf in ("1D", "1W"):
            try:
                raw = list(src.get_kline(symbol, tf, int(limit)) or [])
                clean = sanitize_bars(raw).clean_bars
                written = upsert("CNStock", symbol, tf, clean, dry_run=dry_run)
                summary["upserted"] += written
                item["timeframes"][tf] = {"fetched": len(raw), "clean": len(clean), "upserted": written}
            except Exception as exc:  # noqa: BLE001
                item["timeframes"][tf] = {"error": f"{type(exc).__name__}: {exc}"}
        summary["targets"].append(item)
        print(json.dumps(item, ensure_ascii=False), flush=True)
    return summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--symbols", default=",".join(DEFAULT_SYMBOLS))
    parser.add_argument("--cn-symbols", default="600519.SH", help="CNStock symbols to backfill")
    parser.add_argument("--skip-us", action="store_true")
    parser.add_argument("--skip-cn", action="store_true")
    parser.add_argument("--days", type=int, default=1100)
    parser.add_argument("--limit", type=int, default=1500)
    parser.add_argument("--sleep", type=float, default=0.4)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("-o", "--output", default="")
    args = parser.parse_args(argv)

    summary: dict[str, Any] = {"us": {"targets": [], "upserted": 0}, "cn": {}, "upserted": 0}

    if not args.skip_us:
        symbols = [s.strip().upper() for s in str(args.symbols).split(",") if s.strip()]
        for i, symbol in enumerate(symbols):
            if i:
                time.sleep(max(0.0, float(args.sleep)))
            item: dict[str, Any] = {"market": "USStock", "symbol": symbol, "timeframes": {}}
            daily = fetch_nasdaq_daily(symbol, days=int(args.days), limit=int(args.limit))
            weekly = derive_weekly(daily)
            for tf, bars in (("1D", daily), ("1W", weekly)):
                written = upsert("USStock", symbol, tf, bars, dry_run=args.dry_run)
                summary["us"]["upserted"] += written
                summary["upserted"] += written
                item["timeframes"][tf] = {"bars": len(bars), "upserted": written}
            summary["us"]["targets"].append(item)
            print(json.dumps(item, ensure_ascii=False), flush=True)

    if not args.skip_cn:
        cn_symbols = [s.strip() for s in str(args.cn_symbols).split(",") if s.strip()]
        cn = backfill_cn_stock(cn_symbols, limit=int(args.limit), dry_run=args.dry_run, sleep_s=float(args.sleep))
        summary["cn"] = cn
        summary["upserted"] += int(cn.get("upserted") or 0)

    print(json.dumps({"upserted": summary["upserted"]}, ensure_ascii=False), flush=True)
    if args.output:
        with open(args.output, "w", encoding="utf-8") as fh:
            json.dump(summary, fh, ensure_ascii=False, indent=2)
    return 0 if summary["upserted"] or args.dry_run else 1


if __name__ == "__main__":
    raise SystemExit(main())
