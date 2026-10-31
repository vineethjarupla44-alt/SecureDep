"""
Maturity Tracking and Monitoring Routes for AICTE FDR Portal.

Phase 6: Maturity Tracking and Alerts
Endpoints:
- GET  /api/maturity/summary          : High-level maturity metrics and financial totals
- GET  /api/maturity/expiring         : Filtered and paginated list of expiring/matured FDRs
- GET  /api/maturity/pending-renewals : List instruments with pending renewal workflows
- POST /api/maturity/trigger-scan     : Trigger idempotent alert generation scan (Admin/AICTE)
"""

from datetime import datetime, date
from flask import Blueprint, request, jsonify
from flask_jwt_extended import current_user
from models import db, FDRRecord, User
from utils.decorators import any_authenticated_user, aicte_or_admin_required
from services.maturity_service import (
    get_maturity_summary,
    get_expiring_fdrs,
    calculate_fdr_maturity_metrics,
)
from services.alert_service import scan_and_generate_maturity_alerts

maturity_bp = Blueprint("maturity", __name__)


# ---------------------------------------------------------------------------
# 1. GET /api/maturity/summary
# ---------------------------------------------------------------------------
@maturity_bp.route("/summary", methods=["GET"])
@any_authenticated_user()
def maturity_summary():
    """
    Retrieve aggregated maturity counts and financial summaries.
    Institution users receive statistics scoped strictly to their institution.
    """
    institution_id = current_user.institution_id if current_user.role == User.ROLE_INSTITUTION_USER else None
    
    # Optional date override for back-testing
    ref_date = None
    ref_str = request.args.get("reference_date")
    if ref_str:
        try:
            ref_date = datetime.strptime(ref_str.strip(), "%Y-%m-%d").date()
        except ValueError:
            return jsonify({"error": "Bad Request", "message": "Expected reference_date in YYYY-MM-DD format."}), 400

    summary = get_maturity_summary(institution_id=institution_id, reference_date=ref_date)
    return jsonify({"status": "success", "data": summary}), 200


# ---------------------------------------------------------------------------
# 2. GET /api/maturity/expiring
# ---------------------------------------------------------------------------
@maturity_bp.route("/expiring", methods=["GET"])
@any_authenticated_user()
def expiring_fdrs():
    """
    List expiring and matured FDRs with pagination and filters.
    Query parameters: days_ahead (default 30), status, date_from, date_to, page, per_page.
    """
    # 1. Determine institution_id
    if current_user.role == User.ROLE_INSTITUTION_USER:
        institution_id = current_user.institution_id
    else:
        inst_query = request.args.get("institution_id")
        if inst_query and not inst_query.isdigit():
            return jsonify({"error": "Bad Request", "message": "'institution_id' must be an integer."}), 400
        institution_id = int(inst_query) if inst_query else None

    # 2. Pagination parameters
    try:
        page = int(request.args.get("page", 1))
        per_page = int(request.args.get("per_page", 10))
        if page < 1 or per_page < 1:
            raise ValueError()
    except (ValueError, TypeError):
        return jsonify({"error": "Bad Request", "message": "Parameters 'page' and 'per_page' must be positive integers."}), 400

    per_page = min(per_page, 100)

    # 3. Filters
    days_ahead = request.args.get("days_ahead", 30)
    try:
        days_ahead = int(days_ahead) if days_ahead is not None else None
    except ValueError:
        return jsonify({"error": "Bad Request", "message": "'days_ahead' must be an integer."}), 400

    status = request.args.get("status")
    category = request.args.get("category")
    allowed_categories = {"ACTIVE", "EXPIRING_SOON", "MATURED", "RENEWAL_PENDING"}
    if category and category.strip().upper() not in allowed_categories:
        return jsonify({
            "error": "Bad Request",
            "message": f"Invalid category. Allowed values: {', '.join(sorted(allowed_categories))}."
        }), 400
    
    date_from = None
    date_to = None
    if request.args.get("date_from"):
        try:
            date_from = datetime.strptime(request.args.get("date_from").strip(), "%Y-%m-%d").date()
        except ValueError:
            return jsonify({"error": "Bad Request", "message": "'date_from' must be YYYY-MM-DD."}), 400

    if request.args.get("date_to"):
        try:
            date_to = datetime.strptime(request.args.get("date_to").strip(), "%Y-%m-%d").date()
        except ValueError:
            return jsonify({"error": "Bad Request", "message": "'date_to' must be YYYY-MM-DD."}), 400

    reference_date = None
    if request.args.get("reference_date"):
        try:
            reference_date = datetime.strptime(request.args.get("reference_date").strip(), "%Y-%m-%d").date()
        except ValueError:
            return jsonify({"error": "Bad Request", "message": "'reference_date' must be YYYY-MM-DD."}), 400

    results = get_expiring_fdrs(
        institution_id=institution_id,
        days_ahead=days_ahead,
        status=status,
        date_from=date_from,
        date_to=date_to,
        page=page,
        per_page=per_page,
        category=category,
        reference_date=reference_date,
    )
    return jsonify(results), 200


# ---------------------------------------------------------------------------
# 3. GET /api/maturity/pending-renewals
# ---------------------------------------------------------------------------
@maturity_bp.route("/pending-renewals", methods=["GET"])
@any_authenticated_user()
def pending_renewals():
    """
    List instruments with pending renewal workflows.
    """
    query = FDRRecord.query.filter(FDRRecord.workflow_status == FDRRecord.WORKFLOW_RENEWAL_SUBMITTED)

    if current_user.role == User.ROLE_INSTITUTION_USER:
        query = query.filter(FDRRecord.institution_id == current_user.institution_id)

    records = query.order_by(FDRRecord.maturity_date.asc()).all()

    enriched = []
    for item in records:
        d = item.to_dict()
        d.update(calculate_fdr_maturity_metrics(item))
        enriched.append(d)

    return jsonify({
        "status": "success",
        "total_pending_renewals": len(enriched),
        "data": enriched,
    }), 200


# ---------------------------------------------------------------------------
# 4. POST /api/maturity/trigger-scan
# ---------------------------------------------------------------------------
@maturity_bp.route("/trigger-scan", methods=["POST"])
@aicte_or_admin_required()
def trigger_maturity_scan():
    """
    Manually trigger an idempotent maturity scan and alert generation.
    Protected for AICTE Officials and System Administrators.
    """
    ref_date = None
    if request.is_json and request.get_json().get("reference_date"):
        try:
            ref_date = datetime.strptime(request.get_json()["reference_date"].strip(), "%Y-%m-%d").date()
        except ValueError:
            return jsonify({"error": "Bad Request", "message": "Expected YYYY-MM-DD format."}), 400

    result = scan_and_generate_maturity_alerts(reference_date=ref_date)
    return jsonify(result), 200
