"""
Audit Trail Query Routes for AICTE FDR Portal.

Phase 7: Advanced Audit Trail
Endpoints:
- GET /api/audit-logs : Query immutable audit trail logs with tenant isolation and filters
"""

from flask import Blueprint, request, jsonify
from flask_jwt_extended import current_user
from models import db, FDRAuditLog, User
from utils.decorators import any_authenticated_user

audit_bp = Blueprint("audit", __name__)


@audit_bp.route("/audit-logs", methods=["GET"])
@any_authenticated_user()
def list_audit_logs():
    """
    Retrieve immutable audit logs.
    Strictly read-only: no update or delete routes exist.
    Enforces tenant isolation: institution users only see logs for their institution.
    """
    try:
        page = int(request.args.get("page", 1))
        per_page = int(request.args.get("per_page", 20))
        if page < 1 or per_page < 1:
            raise ValueError()
    except (ValueError, TypeError):
        return jsonify({"error": "Bad Request", "message": "'page' and 'per_page' must be positive integers."}), 400

    per_page = min(per_page, 100)
    query = FDRAuditLog.query

    # Tenant Isolation
    if current_user.role == User.ROLE_INSTITUTION_USER:
        query = query.filter(FDRAuditLog.institution_id == current_user.institution_id)
    else:
        inst_id = request.args.get("institution_id")
        if inst_id and inst_id.isdigit():
            query = query.filter(FDRAuditLog.institution_id == int(inst_id))

    # Filters
    entity_type = request.args.get("entity_type")
    if entity_type:
        query = query.filter(FDRAuditLog.entity_type == entity_type.strip().upper())

    entity_id = request.args.get("entity_id")
    if entity_id and entity_id.isdigit():
        query = query.filter(FDRAuditLog.entity_id == int(entity_id))

    fdr_id = request.args.get("fdr_id") or request.args.get("fdr_record_id")
    if fdr_id and fdr_id.isdigit():
        query = query.filter(FDRAuditLog.fdr_record_id == int(fdr_id))

    release_id = request.args.get("release_id") or request.args.get("release_request_id")
    if release_id and release_id.isdigit():
        query = query.filter(FDRAuditLog.release_request_id == int(release_id))

    action_filter = request.args.get("action")
    if action_filter:
        query = query.filter(FDRAuditLog.action == action_filter.strip().upper())

    user_id = request.args.get("user_id")
    if user_id and user_id.isdigit():
        query = query.filter(FDRAuditLog.user_id == int(user_id))

    query = query.order_by(FDRAuditLog.created_at.desc())
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)

    return jsonify({
        "status": "success",
        "total": pagination.total,
        "page": pagination.page,
        "per_page": pagination.per_page,
        "total_pages": pagination.pages,
        "has_next": pagination.has_next,
        "has_prev": pagination.has_prev,
        "data": [log.to_dict() for log in pagination.items],
    }), 200
