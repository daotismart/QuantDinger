#!/usr/bin/env python3
"""Persist specific CN futures / options contracts into qd_market_bars.

The catalog ingest only writes continuous roots (``SA0``). Strategy packs that
hard-code month codes (``SA701``) or option keys need those symbols persisted
explicitly so local-bar reads and warmup can succeed.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)


DEFAULT_TARGETS = (
    {"market": "CNFutures", "symbol": "SA701", "market_type": "futures"},
    {"market": "CNFuturesOptions", "symbol": "SA701-C-1000", "market_type": "options"},
)


def _derive_frames(bars_1m: list[dict[str, Any]], timeframe: str) -> list[dict[str, Any]]:
    from app.data_sources.base import TIMEFRAME_SECONDS

    seconds = int(TIMEFRAME_SECONDS.get(timeframe) or 0)
    if seconds <= 60 or not bars_1m:
        return list(bars_1m)
    bucket = max(1, seconds // 60)
    out: list[dict[str, Any]] = []
    for i in range(0, len(bars_1m) - bucket + 1, bucket):
        chunk = bars_1m[i : i + bucket]
        if len(chunk) < bucket:
            break
        out.append(
            {
                "time": int(chunk[-1]["time"]),
                "open": float(chunk[0]["open"]),
                "high": max(float(r["high"]) for r in chunk),
                "low": min(float(r["low"]) for r in chunk),
                "close": float(chunk[-1]["close"]),
                "volume": float(sum(float(r.get("volume") or 0.0) for r in chunk)),
            }
        )
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--symbols",
        default="SA701,SA701-C-1000",
        help="Comma-separated symbols (default SA701,SA701-C-1000)",
    )
    parser.add_argument("--timeframes", default="1m,5m,15m,30m,1H")
    parser.add_argument("--stitch-months", type=int, default=24)
    parser.add_argument("--provider", default="akshare")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("-o", "--output", default="")
    args = parser.parse_args(argv)

    os.environ["CN_FUTURES_MARKET_DATA_PROVIDER"] = args.provider
    os.environ["CN_FUTURES_MINUTE_STITCH_MONTHS"] = str(args.stitch_months)

    from app.data_sources.cn_futures import CnFuturesDataSource
    from app.services.market_data_maint import repository
    from app.services.market_data_maint.config import WatchSpec
    from app.services.market_data_maint.validators import sanitize_bars

    wanted = {s.strip().upper() for s in str(args.symbols).split(",") if s.strip()}
    targets = [t for t in DEFAULT_TARGETS if t["symbol"].upper() in wanted]
    # Allow ad-hoc futures symbols not in DEFAULT_TARGETS
    known = {t["symbol"].upper() for t in targets}
    for sym in wanted:
        if sym in known:
            continue
        if "-C-" in sym or "-P-" in sym:
            targets.append({"market": "CNFuturesOptions", "symbol": sym, "market_type": "options"})
        else:
            targets.append({"market": "CNFutures", "symbol": sym, "market_type": "futures"})

    tfs = [p.strip() for p in str(args.timeframes).split(",") if p.strip()]
    src = CnFuturesDataSource()
    summary: dict[str, Any] = {"targets": [], "upserted": 0}

    for target in targets:
        symbol = str(target["symbol"])
        market = str(target["market"])
        market_type = str(target.get("market_type") or "futures")
        item: dict[str, Any] = {"market": market, "symbol": symbol, "timeframes": {}}
        try:
            raw_1m = list(src.get_history(symbol, "1m") or [])
        except Exception as exc:  # noqa: BLE001
            item["error"] = f"{type(exc).__name__}: {exc}"
            summary["targets"].append(item)
            print(json.dumps(item, ensure_ascii=False), flush=True)
            continue

        clean_1m = sanitize_bars(raw_1m).clean_bars
        item["fetched_1m"] = len(raw_1m)
        item["clean_1m"] = len(clean_1m)

        for tf in tfs:
            bars = clean_1m if tf == "1m" else _derive_frames(clean_1m, tf)
            bars = sanitize_bars(bars).clean_bars
            written = 0
            if bars and not args.dry_run:
                spec = WatchSpec(
                    market=market,
                    symbol=symbol,
                    timeframe=tf,
                    exchange_id="",
                    market_type=market_type,
                    lookback_bars=max(len(bars), 20000),
                )
                written = int(
                    repository.upsert_bars(
                        spec,
                        bars,
                        source="cn_futures_contract_backfill",
                    )
                    or 0
                )
                summary["upserted"] += written
            item["timeframes"][tf] = {"bars": len(bars), "upserted": written}
        summary["targets"].append(item)
        print(json.dumps(item, ensure_ascii=False), flush=True)

    print(json.dumps(summary, ensure_ascii=False), flush=True)
    if args.output:
        with open(args.output, "w", encoding="utf-8") as fh:
            json.dump(summary, fh, ensure_ascii=False, indent=2)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
