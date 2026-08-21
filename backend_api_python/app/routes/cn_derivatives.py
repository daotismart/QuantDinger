"""CN futures / derivatives analytics HTTP routes."""

from __future__ import annotations

from flask import jsonify, request

from app.openapi.blueprint import HumanBlueprint as Blueprint
from app.services.cn_derivatives_analytics import (
    build_futures_panel,
    build_options_panel,
    build_overview,
    build_spot_panel,
    list_derivative_products,
)
from app.utils.auth import login_required
from app.utils.logger import get_logger

logger = get_logger(__name__)

cn_derivatives_bp = Blueprint("cn_derivatives", __name__)


@cn_derivatives_bp.route("/products", methods=["GET"])
@login_required
def products():
    try:
        rows = list_derivative_products()
        return jsonify({"code": 1, "msg": "ok", "data": {"products": rows, "count": len(rows)}})
    except Exception as exc:
        logger.exception("cn derivatives products failed")
        return jsonify({"code": 0, "msg": str(exc), "data": None}), 500


@cn_derivatives_bp.route("/overview", methods=["GET"])
@login_required
def overview():
    root = (request.args.get("root") or request.args.get("symbol") or "").strip().upper()
    month = (request.args.get("month") or "").strip().lower() or None
    if not root:
        return jsonify({"code": 0, "msg": "root is required", "data": None}), 400
    try:
        data = build_overview(root, month=month)
        return jsonify({"code": 1, "msg": "ok", "data": data})
    except Exception as exc:
        logger.exception("cn derivatives overview failed root=%s", root)
        return jsonify({"code": 0, "msg": str(exc), "data": None}), 500


@cn_derivatives_bp.route("/spot", methods=["GET"])
@login_required
def spot_panel():
    root = (request.args.get("root") or "").strip().upper()
    if not root:
        return jsonify({"code": 0, "msg": "root is required", "data": None}), 400
    try:
        return jsonify({"code": 1, "msg": "ok", "data": build_spot_panel(root)})
    except Exception as exc:
        logger.exception("cn derivatives spot failed root=%s", root)
        return jsonify({"code": 0, "msg": str(exc), "data": None}), 500


@cn_derivatives_bp.route("/futures", methods=["GET"])
@login_required
def futures_panel():
    root = (request.args.get("root") or "").strip().upper()
    if not root:
        return jsonify({"code": 0, "msg": "root is required", "data": None}), 400
    try:
        return jsonify({"code": 1, "msg": "ok", "data": build_futures_panel(root)})
    except Exception as exc:
        logger.exception("cn derivatives futures failed root=%s", root)
        return jsonify({"code": 0, "msg": str(exc), "data": None}), 500


@cn_derivatives_bp.route("/options", methods=["GET"])
@login_required
def options_panel():
    root = (request.args.get("root") or "").strip().upper()
    month = (request.args.get("month") or "").strip().lower() or None
    if not root:
        return jsonify({"code": 0, "msg": "root is required", "data": None}), 400
    try:
        return jsonify({"code": 1, "msg": "ok", "data": build_options_panel(root, month=month)})
    except Exception as exc:
        logger.exception("cn derivatives options failed root=%s", root)
        return jsonify({"code": 0, "msg": str(exc), "data": None}), 500
