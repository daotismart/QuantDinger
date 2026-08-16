#!/usr/bin/env python3
"""Fetch complete mainland China futures history to stdout or a JSON file.

Examples:
  PYTHONPATH=. python scripts/fetch_cn_futures_history.py --symbol RB0 --timeframe 1D
  PYTHONPATH=. python scripts/fetch_cn_futures_history.py --symbol IF2509 --start 2024-01-01 --end 2024-12-31 -o if.json
"""

from __future__ import annotations

import argparse
import json
import os
import sys

# Ensure backend package imports resolve when run from repo root / scripts/.
_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)


def main() -> int:
    parser = argparse.ArgumentParser(description="Fetch full CN futures OHLCV history")
    parser.add_argument("--symbol", required=True, help="RB0 / rb2509 / IF2509 / ...")
    parser.add_argument("--timeframe", default="1D", help="1D / 1W / 1m / 5m / 15m / 30m / 1H / 4H")
    parser.add_argument("--start", default="", help="YYYY-MM-DD start date (CST)")
    parser.add_argument("--end", default="", help="YYYY-MM-DD end date (CST, inclusive day)")
    parser.add_argument("--provider", default="", help="auto|akshare|compliance")
    parser.add_argument("-o", "--output", default="", help="Write JSON to this path")
    args = parser.parse_args()

    if args.provider:
        os.environ["CN_FUTURES_MARKET_DATA_PROVIDER"] = args.provider

    from app.data_sources.cn_futures import CnFuturesDataSource, resolve_history_symbol

    feed, mode = resolve_history_symbol(args.symbol)
    src = CnFuturesDataSource()
    rows = src.get_history(
        args.symbol,
        args.timeframe,
        start_date=args.start or None,
        end_date=args.end or None,
    )
    payload = {
        "symbol": args.symbol,
        "history_symbol": feed,
        "mode": mode,
        "timeframe": args.timeframe,
        "bar_count": len(rows),
        "start_time": rows[0]["time"] if rows else None,
        "end_time": rows[-1]["time"] if rows else None,
        "data": rows,
    }
    text = json.dumps(payload, ensure_ascii=False, indent=2)
    if args.output:
        with open(args.output, "w", encoding="utf-8") as fh:
            fh.write(text)
        print(f"wrote {len(rows)} bars -> {args.output} (feed={feed}/{mode})")
    else:
        print(text)
    return 0 if rows else 2


if __name__ == "__main__":
    raise SystemExit(main())
