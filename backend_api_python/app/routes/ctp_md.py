"""CTP market-data (MdApi tick) status and subscription routes.

Market data only — these endpoints do not place CTP orders.
"""

from __future__ import annotations

from flask import jsonify, request

from app.openapi.blueprint import HumanBlueprint as Blueprint
from app.services.ctp_md.gateway import get_ctp_md_gateway
from app.services.ctp_md.service import ctp_md_status, ctp_ticker_for_symbol, latest_ctp_ticks
from app.utils.auth import login_required
from app.utils.logger import get_logger

logger = get_logger(__name__)

ctp_md_blp = Blueprint("ctp_md", __name__, description="CTP MdApi tick market data")


@ctp_md_blp.route("/status", methods=["GET"])
@login_required
def get_status():
    """Return CTP MdApi gateway status and cached tick count."""
    try:
        return jsonify({"success": True, "data": ctp_md_status()})
    except Exception as exc:
        logger.error("CTP status failed: %s", exc)
        return jsonify({"success": False, "error": str(exc)}), 500


@ctp_md_blp.route("/ticks", methods=["GET"])
@login_required
def list_ticks():
    """List latest cached CTP ticks."""
    try:
        max_age = request.args.get("maxAgeSeconds", type=float)
        rows = latest_ctp_ticks(max_age_seconds=max_age)
        return jsonify({"success": True, "data": rows})
    except Exception as exc:
        logger.error("CTP ticks list failed: %s", exc)
        return jsonify({"success": False, "error": str(exc)}), 500


@ctp_md_blp.route("/tick", methods=["GET"])
@login_required
def get_tick():
    """Return the latest tick/ticker for one instrument."""
    symbol = str(request.args.get("symbol") or "").strip()
    if not symbol:
        return jsonify({"success": False, "error": "symbol is required"}), 400
    try:
        max_age = request.args.get("maxAgeSeconds", type=float)
        ticker = ctp_ticker_for_symbol(symbol, max_age_seconds=max_age)
        if not ticker:
            return jsonify({"success": False, "error": "tick unavailable"}), 404
        return jsonify({"success": True, "data": ticker})
    except Exception as exc:
        logger.error("CTP tick lookup failed: %s", exc)
        return jsonify({"success": False, "error": str(exc)}), 500


@ctp_md_blp.route("/subscribe", methods=["POST"])
@login_required
def subscribe():
    """Subscribe additional CN futures instruments on the shared MdApi session."""
    body = request.get_json(silent=True) or {}
    instruments = body.get("instruments") or body.get("symbols") or []
    if isinstance(instruments, str):
        instruments = [item.strip() for item in instruments.replace(";", ",").split(",") if item.strip()]
    if not isinstance(instruments, list) or not instruments:
        return jsonify({"success": False, "error": "instruments is required"}), 400
    try:
        gateway = get_ctp_md_gateway()
        if gateway.settings.enabled and not gateway.running:
            gateway.start()
        subscribed = gateway.subscribe(instruments)
        return jsonify({
            "success": True,
            "data": {
                "subscribed": subscribed,
                "status": ctp_md_status(),
            },
        })
    except Exception as exc:
        logger.error("CTP subscribe failed: %s", exc)
        return jsonify({"success": False, "error": str(exc)}), 500
