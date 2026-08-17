#!/usr/bin/env python3
"""Ingest mainland China futures history for the full product catalog.

Examples:
  PYTHONPATH=. python scripts/ingest_cn_futures_history.py --dry-run
  PYTHONPATH=. python scripts/ingest_cn_futures_history.py --persist --timeframes 1D,1W
  PYTHONPATH=. python scripts/ingest_cn_futures_history.py --persist --symbols RB0,IF0,AU0

Production (inside backend container):
  CN_FUTURES_INGEST_PERSIST=1 CN_FUTURES_INGEST_TIMEFRAMES=1D,1W \\
    python scripts/ingest_cn_futures_history.py --persist
"""

from __future__ import annotations

import argparse
import json
import os
import sys

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)


def _split_csv(raw: str) -> list[str]:
    return [part.strip() for part in str(raw or "").replace(";", ",").split(",") if part.strip()]


def main() -> int:
    parser = argparse.ArgumentParser(description="Ingest full CN futures OHLCV history into qd_market_bars")
    parser.add_argument("--timeframes", default=os.getenv("CN_FUTURES_INGEST_TIMEFRAMES", "1D,1W"))
    parser.add_argument("--symbols", default=os.getenv("CN_FUTURES_INGEST_SYMBOLS", ""), help="Optional subset, e.g. RB0,IF0")
    parser.add_argument("--exchanges", default=os.getenv("CN_FUTURES_INGEST_EXCHANGES", ""), help="CFFEX,SHFE,DCE,CZCE,INE,GFEX")
    parser.add_argument("--provider", default=os.getenv("CN_FUTURES_INGEST_PROVIDER", "akshare"))
    parser.add_argument("--retries", type=int, default=int(os.getenv("CN_FUTURES_INGEST_RETRIES", "3") or 3))
    parser.add_argument("--persist", action="store_true", help="Upsert bars into qd_market_bars")
    parser.add_argument("--dry-run", action="store_true", help="Fetch only; do not write the database")
    parser.add_argument("--no-watch", action="store_true", help="Do not register daily/weekly watchlist rows")
    parser.add_argument("-o", "--output", default="", help="Write JSON summary to this path")
    args, _unknown = parser.parse_known_args()

    persist = bool(args.persist) and not bool(args.dry_run)
    if str(os.getenv("CN_FUTURES_INGEST_PERSIST", "")).strip().lower() in ("1", "true", "yes", "on"):
        persist = not bool(args.dry_run)

    from app.services.market_data_maint.cn_futures_ingest import ingest_cn_futures_history

    summary = ingest_cn_futures_history(
        timeframes=_split_csv(args.timeframes),
        persist=persist,
        provider=args.provider,
        retries=max(1, int(args.retries)),
        symbols=_split_csv(args.symbols) or None,
        exchanges=_split_csv(args.exchanges) or None,
        register_watch=not args.no_watch,
    )
    text = json.dumps(summary, ensure_ascii=False, indent=2)
    if args.output:
        with open(args.output, "w", encoding="utf-8") as fh:
            fh.write(text)
        print(
            f"ingest {summary.get('status')} targets={summary.get('targets')} "
            f"ok={summary.get('ok_symbols')} upserted={summary.get('upserted_rows')} -> {args.output}"
        )
    else:
        print(text)
    status = str(summary.get("status") or "failed")
    if status == "success":
        return 0
    if status == "partial":
        return 1
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
