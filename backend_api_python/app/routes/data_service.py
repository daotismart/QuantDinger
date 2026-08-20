"""Local data service management APIs."""

from __future__ import annotations

from flask import jsonify, request

from app.openapi.blueprint import HumanBlueprint as Blueprint
from app.services.local_data.service import (
    collection_watchlist,
    governance_gaps,
    governance_inventory,
    governance_quality,
    overview,
    preview_kline,
    service_config,
    service_health,
    update_service_config,
    upsert_watchlist,
)
from app.services.market_data_maint import run_historical_cycle, run_retention_cycle
from app.services.market_data_maint import repository
from app.utils.auth import login_required
from app.utils.logger import get_logger

logger = get_logger(__name__)

data_service_blp = Blueprint(
    "data_service",
    __name__,
    description="Local market data service built on qd_market_bars",
)


@data_service_blp.route("/overview", methods=["GET"])
@login_required
def get_overview():
    try:
        return jsonify({"success": True, "data": overview()})
    except Exception as exc:
        logger.error("data service overview failed: %s", exc)
        return jsonify({"success": False, "error": str(exc)}), 500


@data_service_blp.route("/collection/watchlist", methods=["GET"])
@login_required
def get_collection_watchlist():
    try:
        include_disabled = str(request.args.get("includeDisabled", "true")).lower() != "false"
        return jsonify({"success": True, "data": collection_watchlist(include_disabled=include_disabled)})
    except Exception as exc:
        logger.error("collection watchlist failed: %s", exc)
        return jsonify({"success": False, "error": str(exc)}), 500


@data_service_blp.route("/collection/watchlist", methods=["POST"])
@login_required
def post_collection_watchlist():
    body = request.get_json(silent=True) or {}
    raw = body.get("watchlist") or body.get("symbols") or body.get("items") or []
    try:
        result = upsert_watchlist(raw)
        return jsonify({"success": True, "data": result})
    except ValueError as exc:
        return jsonify({"success": False, "error": str(exc)}), 400
    except Exception as exc:
        logger.error("collection watchlist upsert failed: %s", exc)
        return jsonify({"success": False, "error": str(exc)}), 500


@data_service_blp.route("/collection/historical/run", methods=["POST"])
@login_required
def post_collection_historical_run():
    try:
        result = run_historical_cycle(trigger="api")
        return jsonify({"success": True, "data": result})
    except Exception as exc:
        logger.error("collection historical run failed: %s", exc)
        return jsonify({"success": False, "error": str(exc)}), 500


@data_service_blp.route("/collection/retention/run", methods=["POST"])
@login_required
def post_collection_retention_run():
    try:
        result = run_retention_cycle(trigger="api")
        return jsonify({"success": True, "data": result})
    except Exception as exc:
        logger.error("collection retention run failed: %s", exc)
        return jsonify({"success": False, "error": str(exc)}), 500


@data_service_blp.route("/collection/runs", methods=["GET"])
@login_required
def get_collection_runs():
    try:
        limit = int(request.args.get("limit") or 20)
        return jsonify({"success": True, "data": repository.latest_runs(limit=limit)})
    except Exception as exc:
        logger.error("collection runs failed: %s", exc)
        return jsonify({"success": False, "error": str(exc)}), 500


@data_service_blp.route("/governance/inventory", methods=["GET"])
@login_required
def get_governance_inventory():
    try:
        limit = int(request.args.get("limit") or 100)
        return jsonify({"success": True, "data": governance_inventory(limit=limit)})
    except Exception as exc:
        logger.error("governance inventory failed: %s", exc)
        return jsonify({"success": False, "error": str(exc)}), 500


@data_service_blp.route("/governance/gaps", methods=["GET"])
@login_required
def get_governance_gaps():
    try:
        limit = int(request.args.get("limit") or 50)
        return jsonify({"success": True, "data": governance_gaps(limit=limit)})
    except Exception as exc:
        logger.error("governance gaps failed: %s", exc)
        return jsonify({"success": False, "error": str(exc)}), 500


@data_service_blp.route("/governance/quality", methods=["GET"])
@login_required
def get_governance_quality():
    try:
        limit = int(request.args.get("limit") or 100)
        return jsonify({"success": True, "data": governance_quality(limit=limit)})
    except Exception as exc:
        logger.error("governance quality failed: %s", exc)
        return jsonify({"success": False, "error": str(exc)}), 500


@data_service_blp.route("/service/config", methods=["GET"])
@login_required
def get_service_config():
    try:
        return jsonify({"success": True, "data": service_config()})
    except Exception as exc:
        logger.error("service config get failed: %s", exc)
        return jsonify({"success": False, "error": str(exc)}), 500


@data_service_blp.route("/service/config", methods=["POST"])
@login_required
def post_service_config():
    body = request.get_json(silent=True) or {}
    try:
        result = update_service_config(body)
        return jsonify({"success": True, "data": result})
    except ValueError as exc:
        return jsonify({"success": False, "error": str(exc)}), 400
    except Exception as exc:
        logger.error("service config update failed: %s", exc)
        return jsonify({"success": False, "error": str(exc)}), 500


@data_service_blp.route("/service/health", methods=["GET"])
@login_required
def get_service_health():
    try:
        return jsonify({"success": True, "data": service_health()})
    except Exception as exc:
        logger.error("service health failed: %s", exc)
        return jsonify({"success": False, "error": str(exc)}), 500


@data_service_blp.route("/service/preview", methods=["POST"])
@login_required
def post_service_preview():
    body = request.get_json(silent=True) or {}
    market = str(body.get("market") or "Futures")
    symbol = str(body.get("symbol") or "").strip()
    if not symbol:
        return jsonify({"success": False, "error": "symbol required"}), 400
    timeframe = str(body.get("timeframe") or "1m")
    limit = int(body.get("limit") or 100)
    try:
        result = preview_kline(
            market=market,
            symbol=symbol,
            timeframe=timeframe,
            limit=limit,
            exchange_id=body.get("exchange_id") or body.get("exchangeId"),
            market_type=body.get("market_type") or body.get("marketType"),
        )
        return jsonify({"success": True, "data": result})
    except Exception as exc:
        logger.error("service preview failed: %s", exc)
        return jsonify({"success": False, "error": str(exc)}), 500
