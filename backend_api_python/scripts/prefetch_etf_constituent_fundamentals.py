#!/usr/bin/env python3
"""CLI: prefetch ETF-option constituent history + profit/PE caches.

Examples:
  python scripts/prefetch_etf_constituent_fundamentals.py
  python scripts/prefetch_etf_constituent_fundamentals.py --etf 510300,510050 --force
  python scripts/prefetch_etf_constituent_fundamentals.py --no-history --no-bundles
"""

from __future__ import annotations

import argparse
import json
import os
import sys


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Prefetch ETF option constituent stocks + profit/PE for faster ETF analysis"
    )
    parser.add_argument(
        "--etf",
        default="",
        help="Comma-separated ETF codes (default: all known/listed ETF option underlyings)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Ignore warm Redis/DB snapshots and refetch",
    )
    parser.add_argument(
        "--no-history",
        action="store_true",
        help="Do not register constituent CNStock daily watch specs",
    )
    parser.add_argument(
        "--no-bundles",
        action="store_true",
        help="Skip rebuilding ETF holdings/metrics Redis bundles",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print full JSON result",
    )
    args = parser.parse_args(argv)

    # Ensure backend package imports work when launched from repo scripts/.
    root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    if root not in sys.path:
        sys.path.insert(0, root)

    os.environ.setdefault("QD_PROCESS_ROLE", "cli")
    from app import create_app
    from app.services.cn_etf_constituent_prefetch import run_etf_constituent_prefetch_cycle

    etf_codes = [c.strip() for c in str(args.etf or "").split(",") if c.strip()]
    app = create_app(register_http_routes=False)
    with app.app_context():
        result = run_etf_constituent_prefetch_cycle(
            etf_codes=etf_codes or None,
            force=bool(args.force),
            include_history=not bool(args.no_history),
            warm_bundles=not bool(args.no_bundles),
            trigger="cli",
        )

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
    else:
        snaps = result.get("snapshots") or {}
        bundles = result.get("bundles") or {}
        print(
            "ETF constituent prefetch "
            f"etfs={result.get('etf_count')} stocks={result.get('constituent_count')} "
            f"warmed={snaps.get('warmed')}/{snaps.get('total')} "
            f"cached={snaps.get('cached')} failed={snaps.get('failed')} "
            f"history_watch={result.get('history_watch_written')} "
            f"bundles_ok={bundles.get('ok')} elapsed={result.get('elapsed_sec')}s"
        )
    return 0 if int((result.get("snapshots") or {}).get("failed") or 0) == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
