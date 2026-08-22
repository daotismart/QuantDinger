#!/usr/bin/env python3
"""Sync listed China option contracts into qd_market_symbols.

Pulls the CTP option dump via AkShare (option_contract_info_ctp), upserts
commodity options into CNFuturesOptions and CFFEX/ETF options into
CNIndexOptions, and keeps static product roots as hot search entries.

Does not ingest per-contract history and does not subscribe CTP Md quotes
for the full chain (exchange limits typically allow on the order of 500
instruments).

Usage:
    python scripts/sync_cn_option_contracts.py
    python scripts/sync_cn_option_contracts.py --no-etf
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

_BACKEND_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_BACKEND_ROOT))

os.environ.setdefault("SKIP_STARTUP_HOOKS", "1")
os.environ.setdefault("CN_OPTIONS_CTP_SYNC", "true")


def main() -> None:
    parser = argparse.ArgumentParser(description="Sync listed China option contracts")
    parser.add_argument(
        "--no-etf",
        action="store_true",
        help="Skip SSE/SZSE ETF option codes (keep CFFEX + commodity options)",
    )
    args = parser.parse_args()
    if args.no_etf:
        os.environ["CN_OPTIONS_INCLUDE_ETF"] = "false"

    from app.services.symbol_master_sync import (
        fetch_cn_futures_options_symbols,
        fetch_cn_index_options_symbols,
        fetch_etf_option_index_symbols,
        fetch_etf_option_underlying_symbols,
        sync_symbol_master,
        upsert_symbol_master,
    )
    from app.services.cn_options_chain import catalog_stats

    stats = sync_symbol_master(["CNFutures", "CNFuturesOptions", "CNIndexFutures", "CNIndexOptions"])
    underlying_rows = fetch_etf_option_underlying_symbols()
    index_rows = fetch_etf_option_index_symbols()
    underlying_upserted = upsert_symbol_master(underlying_rows) if underlying_rows else 0
    index_upserted = upsert_symbol_master(index_rows) if index_rows else 0
    listed_opt = [row for row in fetch_cn_futures_options_symbols() if row.instrument_id]
    listed_idx = [row for row in fetch_cn_index_options_symbols() if row.instrument_id]
    summary = {
        "sync": stats,
        "listed_futures_options": len(listed_opt),
        "listed_index_options": len(listed_idx),
        "etf_underlyings": len(underlying_rows),
        "etf_underlyings_upserted": underlying_upserted,
        "etf_indices": len(index_rows),
        "etf_indices_upserted": index_upserted,
        "listed_stats": catalog_stats(
            [
                {"market": row.market, "exchange": row.exchange}
                for row in (*listed_opt, *listed_idx)
            ]
        ),
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))

    failed = [market for market, stat in stats.items() if not stat.get("ok")]
    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
