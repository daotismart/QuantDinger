"""CN futures / derivatives analytics HTTP routes."""

from __future__ import annotations

from flask import jsonify, request

from app.openapi.blueprint import HumanBlueprint as Blueprint
from app.services.cn_derivatives_analytics import (
    build_chart_history,
    build_futures_panel,
    build_options_panel,
    build_overview,
    build_spot_panel,
    list_derivative_products,
)
from app.services.cn_derivatives_etf import (
    build_etf_options_panel,
    build_etf_scope_spot_panel,
    list_etf_derivative_products,
)
from app.utils.auth import login_required
from app.utils.logger import get_logger

logger = get_logger(__name__)

cn_derivatives_bp = Blueprint("cn_derivatives", __name__)


def _is_etf_scope() -> bool:
    return str(request.args.get("scope") or "").strip().lower() == "etf"


@cn_derivatives_bp.route("/products", methods=["GET"])
@login_required
def products():
    try:
        if _is_etf_scope():
            tab = request.args.get("tab") or request.args.get("activeTab") or "index"
            rows = list_etf_derivative_products(tab)
        else:
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
        if _is_etf_scope():
            picker_kind = (request.args.get("picker_kind") or request.args.get("pickerKind") or "").strip()
            market = (request.args.get("market") or "").strip()
            data = build_etf_scope_spot_panel(
                root,
                picker_kind=picker_kind,
                market=market,
            )
        else:
            data = build_spot_panel(root)
        return jsonify({"code": 1, "msg": "ok", "data": data})
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
    month = (request.args.get("month") or "all").strip().lower() or "all"
    if not root:
        return jsonify({"code": 0, "msg": "root is required", "data": None}), 400
    try:
        if _is_etf_scope():
            data = build_etf_options_panel(root, month=month)
        else:
            data = build_options_panel(root, month=month)
        return jsonify({"code": 1, "msg": "ok", "data": data})
    except Exception as exc:
        logger.exception("cn derivatives options failed root=%s", root)
        return jsonify({"code": 0, "msg": str(exc), "data": None}), 500


@cn_derivatives_bp.route("/history", methods=["GET"])
@login_required
def chart_history():
    root = (request.args.get("root") or "").strip().upper()
    chart_key = (request.args.get("chart") or request.args.get("chart_key") or "").strip()
    month = (request.args.get("month") or "all").strip().lower() or "all"
    frequency = (request.args.get("frequency") or request.args.get("freq") or "day").strip().lower()
    days = request.args.get("days") or 30
    if not root:
        return jsonify({"code": 0, "msg": "root is required", "data": None}), 400
    if not chart_key:
        return jsonify({"code": 0, "msg": "chart is required", "data": None}), 400
    try:
        days_i = int(days)
    except Exception:
        days_i = 30
    try:
        data = build_chart_history(
            root,
            chart_key=chart_key,
            days=days_i,
            month=month,
            frequency=frequency,
        )
        return jsonify({"code": 1, "msg": "ok", "data": data})
    except Exception as exc:
        logger.exception("cn derivatives history failed root=%s chart=%s", root, chart_key)
        return jsonify({"code": 0, "msg": str(exc), "data": None}), 500
