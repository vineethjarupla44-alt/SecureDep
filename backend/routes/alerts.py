"""
Alerts Management Routes for AICTE FDR Portal.

Phase 6: In-Portal Notifications & Acknowledgment
Endpoints:
- GET  /api/alerts                    : List alerts with pagination and filters
- POST /api/alerts/<id>/acknowledge   : Acknowledge an active notification
"""

from datetime import datetime
import json
from flask import Blueprint, request, jsonify
from flask_jwt_extended import current_user
from models import db, FDRAlert, User, FDRAuditLog
from utils.decorators import any_authenticated_user

alerts_bp = Blueprint("alerts", __name__)


# ---------------------------------------------------------------------------
# 1. GET /api/alerts - List Alerts
# ---------------------------------------------------------------------------
@alerts_bp.route("", methods=["GET"])
@alerts_bp.route("/", methods=["GET"])
@any_authenticated_user()
def list_alerts():
    """
    Retrieve alerts for the current user/role.
    Enforces that institution_user can only view alerts for their own institution.
    """
    try:
        page = int(request.args.get("page", 1))
        per_page = int(request.args.get("per_page", 10))
        if page < 1 or per_page < 1:
            raise ValueError()
    except (ValueError, TypeError):
        return jsonify({"error": "Bad Request", "message": "'page' and 'per_page' must be positive integers."}), 400

    per_page = min(per_page, 100)
    query = FDRAlert.query

    # Tenant isolation
    if current_user.role == User.ROLE_INSTITUTION_USER:
        query = query.filter(FDRAlert.institution_id == current_user.institution_id)
    else:
        inst_param = request.args.get("institution_id")
        if inst_param and not inst_param.isdigit():
            return jsonify({"error": "Bad Request", "message": "'institution_id' must be an integer."}), 400
        if inst_param:
            query = query.filter(FDRAlert.institution_id == int(inst_param))

    # Filter by alert_type
    alert_type = request.args.get("type")
    if alert_type and alert_type.strip().upper() in FDRAlert.ALLOWED_TYPES:
        query = query.filter(FDRAlert.alert_type == alert_type.strip().upper())

    # Filter by acknowledgment
    ack_param = request.args.get("acknowledged")
    if ack_param is not None:
        is_ack = ack_param.lower() in ("true", "1", "yes")
        query = query.filter(FDRAlert.is_acknowledged == is_ack)

    query = query.order_by(FDRAlert.is_acknowledged.asc(), FDRAlert.due_date.asc(), FDRAlert.id.desc())
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)

    return jsonify({
        "status": "success",
        "total": pagination.total,
        "page": pagination.page,
        "per_page": pagination.per_page,
        "total_pages": pagination.pages,
        "has_next": pagination.has_next,
        "has_prev": pagination.has_prev,
        "data": [a.to_dict() for a in pagination.items],
    }), 200


# ---------------------------------------------------------------------------
# 2. POST /api/alerts/<id>/acknowledge - Acknowledge Alert
# ---------------------------------------------------------------------------
@alerts_bp.route("/<int:alert_id>/acknowledge", methods=["POST"])
@any_authenticated_user()
def acknowledge_alert(alert_id):
    """
    Mark an alert as acknowledged.
    Enforces that institution_user can only acknowledge alerts for their own institution.
    """
    alert = db.session.get(FDRAlert, alert_id)
    if not alert:
        return jsonify({"error": "Not Found", "message": f"Alert with ID {alert_id} was not found."}), 404

    # Tenant check
    if current_user.role == User.ROLE_INSTITUTION_USER:
        if alert.institution_id != current_user.institution_id:
            return jsonify({
                "error": "Forbidden",
                "message": "Access denied: You cannot acknowledge alerts for another institution."
            }), 403

    if alert.is_acknowledged:
        return jsonify({
            "error": "Conflict",
            "message": "Alert was already acknowledged.",
            "data": alert.to_dict()
        }), 409

    alert.is_acknowledged = True
    alert.acknowledged_at = datetime.utcnow()
    alert.acknowledged_by_id = current_user.id
    db.session.add(FDRAuditLog(
        fdr_record_id=alert.fdr_record_id,
        institution_id=alert.institution_id,
        user_id=current_user.id,
        action="ALERT_ACKNOWLEDGED",
        details=json.dumps({"alert_id": alert.id, "alert_type": alert.alert_type}),
        ip_address=request.remote_addr,
    ))

    try:
        db.session.commit()
        return jsonify({
            "message": "Alert acknowledged successfully.",
            "data": alert.to_dict()
        }), 200
    except Exception:
        db.session.rollback()
        return jsonify({"error": "Internal Server Error", "message": "Failed to acknowledge alert."}), 500
