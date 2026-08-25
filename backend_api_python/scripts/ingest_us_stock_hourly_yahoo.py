#!/usr/bin/env python3
""".Ingest US equity/ETF hourly bars from Yahoo chart API into qd_market_bars.

Production hosts in CN often get Yahoo HTTP 403, so this script is intended to
run from an egress-friendly environment, then upsert into the app DB (or write
JSON for offline load).

Examples:
  PYTHONPATH=. python scripts/ingest_us_stock_hourly_yahoo.py --symbols SPY --persist
  PYTHONPATH=. python scripts/ingest_us_stock_hourly_yahoo.py --symbols SPY --out /tmp/spy_1h.json
"""

from __future__ import annotations

import argparse
import json
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List


UA = {"User-Agent": "Mozilla/5.0 (compatible; QuantDingerHourlyIngest/1.0)"}


def fetch_yahoo_hourly(symbol: str, *, lookback_days: int = 730) -> List[Dict[str, Any]]:
    end = int(time.time())
    start = end - max(30, int(lookback_days)) * 86400
    url = (
        f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
        f"?period1={start}&period2={end}&interval=1h&includePrePost=false&events=history"
    )
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=60) as resp:
        payload = json.loads(resp.read().decode())
    result = ((payload.get("chart") or {}).get("result") or [None])[0]
    if not result:
        return []
    timestamps = result.get("timestamp") or []
    quote = ((result.get("indicators") or {}).get("quote") or [{}])[0]
    bars: List[Dict[str, Any]] = []
    for i, ts in enumerate(timestamps):
        o = quote.get("open", [None])[i]
        h = quote.get("high", [None])[i]
        l = quote.get("low", [None])[i]
        c = quote.get("close", [None])[i]
        if None in (o, h, l, c):
            continue
        v = (quote.get("volume") or [0] * len(timestamps))[i] or 0
        bars.append(
            {
                "time": int(ts),
                "open": float(o),
                "high": float(h),
                "low": float(l),
                "close": float(c),
                "volume": float(v),
            }
        )
    return bars


def persist_bars(symbol: str, bars: List[Dict[str, Any]], *, market: str = "USStock") -> int:
    from app.services.market_data_maint.config import WatchSpec
    from app.services.market_data_maint import repository as repo

    spec = WatchSpec(
        market=market,
        symbol=symbol.upper(),
        timeframe="1H",
        exchange_id="",
        market_type="",
        lookback_bars=max(1500, len(bars)),
    )
    return int(
        repo.upsert_bars(
            spec,
            bars,
            source="yahoo_chart_1h_backfill",
            quality_flags=["manual_backfill"],
        )
        or 0
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--symbols", default="SPY", help="Comma-separated Yahoo symbols")
    parser.add_argument("--lookback-days", type=int, default=730)
    parser.add_argument("--persist", action="store_true", help="Upsert into qd_market_bars")
    parser.add_argument("--out", type=Path, default=None, help="Optional JSON dump path")
    parser.add_argument("--market", default="USStock")
    args = parser.parse_args()

    symbols = [s.strip().upper() for s in str(args.symbols).split(",") if s.strip()]
    summary = []
    for symbol in symbols:
        bars = fetch_yahoo_hourly(symbol, lookback_days=args.lookback_days)
        item = {
            "symbol": symbol,
            "bars": len(bars),
            "first": datetime.fromtimestamp(bars[0]["time"], tz=timezone.utc).isoformat() if bars else None,
            "last": datetime.fromtimestamp(bars[-1]["time"], tz=timezone.utc).isoformat() if bars else None,
            "written": 0,
        }
        if args.out:
            out = args.out if len(symbols) == 1 else args.out.with_name(f"{args.out.stem}_{symbol}{args.out.suffix}")
            out.write_text(json.dumps(bars))
            item["out"] = str(out)
        if args.persist:
            item["written"] = persist_bars(symbol, bars, market=args.market)
        summary.append(item)
        print(json.dumps(item, ensure_ascii=False))
        time.sleep(1.0)
    return 0 if all(row["bars"] > 0 for row in summary) else 2


if __name__ == "__main__":
    raise SystemExit(main())
