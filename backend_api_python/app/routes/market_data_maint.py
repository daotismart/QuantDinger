"""Market data continuity / accuracy maintenance APIs."""

from __future__ import annotations

from flask import jsonify, request

from app.openapi.blueprint import HumanBlueprint as Blueprint
from app.services.market_data_maint import (
    maintenance_status,
    run_historical_cycle,
    run_retention_cycle,
)
from app.services.market_data_maint.config import WatchSpec, parse_watch_csv
from app.services.market_data_maint import repository
from app.utils.auth import login_required
from app.utils.logger import get_logger

logger = get_logger(__name__)

market_data_maint_blp = Blueprint(
    "market_data_maint",
    __name__,
    description="Market data continuity and accuracy maintenance",
)


@market_data_maint_blp.route("/status", methods=["GET"])
@login_required
def get_status():
    try:
        return jsonify({"success": True, "data": maintenance_status()})
    except Exception as exc:
        logger.error("market data maint status failed: %s", exc)
        return jsonify({"success": False, "error": str(exc)}), 500


@market_data_maint_blp.route("/historical/run", methods=["POST"])
@login_required
def run_historical():
    try:
        result = run_historical_cycle(trigger="api")
        return jsonify({"success": True, "data": result})
    except Exception as exc:
        logger.error("market data historical run failed: %s", exc)
        return jsonify({"success": False, "error": str(exc)}), 500


@market_data_maint_blp.route("/retention/run", methods=["POST"])
@login_required
def run_retention():
    try:
        result = run_retention_cycle(trigger="api")
        return jsonify({"success": True, "data": result})
    except Exception as exc:
        logger.error("market data retention run failed: %s", exc)
        return jsonify({"success": False, "error": str(exc)}), 500


@market_data_maint_blp.route("/watchlist", methods=["POST"])
@login_required
def upsert_watchlist():
    body = request.get_json(silent=True) or {}
    raw = body.get("watchlist") or body.get("symbols") or []
    if isinstance(raw, str):
        specs = parse_watch_csv(raw)
    elif isinstance(raw, list):
        specs = []
        for item in raw:
            if isinstance(item, str):
                specs.extend(parse_watch_csv(item))
            elif isinstance(item, dict):
                specs.append(
                    WatchSpec(
                        market=str(item.get("market") or "Futures"),
                        symbol=str(item.get("symbol") or ""),
                        timeframe=str(item.get("timeframe") or "1m"),
                        exchange_id=str(item.get("exchange_id") or item.get("exchangeId") or ""),
                        market_type=str(item.get("market_type") or item.get("marketType") or ""),
                        lookback_bars=int(item.get("lookback_bars") or item.get("lookbackBars") or 1500),
                    )
                )
    else:
        return jsonify({"success": False, "error": "watchlist must be string or list"}), 400
    specs = [spec for spec in specs if spec.symbol]
    if not specs:
        return jsonify({"success": False, "error": "no valid symbols"}), 400
    try:
        written = repository.upsert_watch_specs(specs)
        return jsonify({"success": True, "data": {"upserted": written, "items": [s.key() for s in specs]}})
    except Exception as exc:
        logger.error("watchlist upsert failed: %s", exc)
        return jsonify({"success": False, "error": str(exc)}), 500
