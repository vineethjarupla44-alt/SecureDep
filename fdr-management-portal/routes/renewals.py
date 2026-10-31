"""
FDR Renewal and Replacement Workflow Routes for AICTE FDR Portal.

Phase 6: Renewal Workflow, Linking and Review
Endpoints:
- POST /api/fdr/<fdr_id>/renew       : Submit replacement FDR proposal linked to predecessor
- GET  /api/renewals                 : List renewal proposals (institution-isolated)
- GET  /api/renewals/<id>            : Retrieve renewal details
- POST /api/renewals/<id>/review     : Reviewer action to approve or reject renewal (AICTE/Admin)
"""

import json
from datetime import datetime, date
from decimal import Decimal
from flask import Blueprint, request, jsonify
from flask_jwt_extended import current_user
from sqlalchemy import func
from models import (
    db,
    FDRRecord,
    FDRRenewalRequest,
    FDRAuditLog,
    User,
    Institution,
)
from utils.decorators import any_authenticated_user, aicte_or_admin_required, institution_user_or_admin_required
from routes.fdr import parse_decimal_amount, parse_iso_date

renewals_bp = Blueprint("renewals", __name__)


# ---------------------------------------------------------------------------
# 1. POST /api/fdr/<fdr_id>/renew - Submit Renewal Proposal
# ---------------------------------------------------------------------------
@renewals_bp.route("/fdr/<int:fdr_id>/renew", methods=["POST"])
@institution_user_or_admin_required()
def submit_fdr_renewal(fdr_id):
    """
    Submit a replacement FDR proposal linked to a maturing/matured predecessor FDR.
    Preserves historical instrument details and creates a renewal workflow record.
    """
    original_fdr = db.session.get(FDRRecord, fdr_id)
    if not original_fdr:
        return jsonify({"error": "Not Found", "message": f"FDR record with ID {fdr_id} was not found."}), 404

    # Enforce tenant isolation
    if current_user.role == User.ROLE_INSTITUTION_USER:
        if original_fdr.institution_id != current_user.institution_id:
            return jsonify({
                "error": "Forbidden",
                "message": "Access denied: You cannot submit renewals for another institution's FDR."
            }), 403

    # Check if a pending renewal already exists
    pending_existing = FDRRenewalRequest.query.filter_by(
        original_fdr_id=fdr_id,
        status=FDRRenewalRequest.STATUS_PENDING
    ).first()
    if pending_existing:
        return jsonify({
            "error": "Conflict",
            "message": f"A renewal request for FDR '{original_fdr.fdr_number}' is already pending review (ID: {pending_existing.id})."
        }), 409

    if not request.is_json:
        return jsonify({"error": "Bad Request", "message": "Request body must be valid JSON."}), 400

    data = request.get_json()
    required = ["replacement_fdr_number", "issuing_bank", "deposit_amount", "issue_date", "maturity_date"]
    missing = [f for f in required if not data.get(f) or not str(data.get(f)).strip()]
    if missing:
        return jsonify({"error": "Validation Error", "message": f"Missing required fields: {', '.join(missing)}."}), 400

    # Validate replacement FDR Number uniqueness
    replacement_num = str(data["replacement_fdr_number"]).strip()
    existing_num = FDRRecord.query.filter(func.upper(FDRRecord.fdr_number) == replacement_num.upper()).first()
    if existing_num:
        return jsonify({
            "error": "Conflict",
            "message": f"An FDR record with number '{replacement_num}' already exists (ID: {existing_num.id})."
        }), 409

    # Validate amount and dates
    deposit_amt, err_amt = parse_decimal_amount(data["deposit_amount"])
    if err_amt:
        return jsonify({"error": "Validation Error", "message": err_amt}), 400

    issue_date, err_issue = parse_iso_date(data["issue_date"], "issue_date")
    if err_issue:
        return jsonify({"error": "Validation Error", "message": err_issue}), 400

    maturity_date, err_mat = parse_iso_date(data["maturity_date"], "maturity_date")
    if err_mat:
        return jsonify({"error": "Validation Error", "message": err_mat}), 400

    if maturity_date <= issue_date:
        return jsonify({"error": "Validation Error", "message": "Maturity date must be strictly later than issue date."}), 400

    submission_notes = data.get("submission_notes", "")

    # 1. Create the replacement FDRRecord linked to predecessor
    replacement_fdr = FDRRecord(
        institution_id=original_fdr.institution_id,
        fdr_number=replacement_num,
        issuing_bank=str(data["issuing_bank"]).strip(),
        deposit_amount=deposit_amt,
        issue_date=issue_date,
        maturity_date=maturity_date,
        status=FDRRecord.STATUS_PENDING_RENEWAL,
        workflow_status=FDRRecord.WORKFLOW_RENEWAL_SUBMITTED,
        predecessor_id=original_fdr.id,
        renewal_notes=f"Renewal replacement for predecessor FDR ID {original_fdr.id} ({original_fdr.fdr_number}).",
    )
    db.session.add(replacement_fdr)
    db.session.flush()  # Get replacement_fdr.id

    # 2. Update predecessor FDR workflow status
    original_fdr.workflow_status = FDRRecord.WORKFLOW_RENEWAL_SUBMITTED

    # 3. Create the FDRRenewalRequest workflow entity
    renewal_req = FDRRenewalRequest(
        original_fdr_id=original_fdr.id,
        replacement_fdr_id=replacement_fdr.id,
        institution_id=original_fdr.institution_id,
        submitted_by_id=current_user.id,
        status=FDRRenewalRequest.STATUS_PENDING,
        submission_notes=str(submission_notes).strip() if submission_notes else None,
    )
    db.session.add(renewal_req)

    # 4. Audit Log
    audit = FDRAuditLog(
        fdr_record_id=original_fdr.id,
        institution_id=original_fdr.institution_id,
        user_id=current_user.id,
        action="RENEWAL_SUBMITTED",
        details=json.dumps({
            "original_fdr_number": original_fdr.fdr_number,
            "replacement_fdr_number": replacement_fdr.fdr_number,
            "amount": float(deposit_amt),
        }),
        ip_address=request.remote_addr,
    )
    db.session.add(audit)

    try:
        db.session.commit()
        return jsonify({
            "message": "Renewal request submitted successfully and is pending review.",
            "data": renewal_req.to_dict(),
        }), 201
    except Exception:
        db.session.rollback()
        return jsonify({"error": "Internal Server Error", "message": "Failed to submit renewal request."}), 500


# ---------------------------------------------------------------------------
# 2. GET /api/renewals - List Renewal Requests
# ---------------------------------------------------------------------------
@renewals_bp.route("/renewals", methods=["GET"])
@any_authenticated_user()
def list_renewals():
    """
    List renewal requests.
    Enforces that institution_user can only see renewals for their own institution.
    """
    try:
        page = int(request.args.get("page", 1))
        per_page = int(request.args.get("per_page", 10))
        if page < 1 or per_page < 1:
            raise ValueError()
    except (ValueError, TypeError):
        return jsonify({"error": "Bad Request", "message": "'page' and 'per_page' must be positive integers."}), 400

    per_page = min(per_page, 100)
    query = FDRRenewalRequest.query

    # Tenant check
    if current_user.role == User.ROLE_INSTITUTION_USER:
        query = query.filter(FDRRenewalRequest.institution_id == current_user.institution_id)
    else:
        inst_query = request.args.get("institution_id")
        if inst_query and inst_query.isdigit():
            query = query.filter(FDRRenewalRequest.institution_id == int(inst_query))

    status_filter = request.args.get("status")
    if status_filter and status_filter.strip().upper() in FDRRenewalRequest.ALLOWED_STATUSES:
        query = query.filter(FDRRenewalRequest.status == status_filter.strip().upper())

    query = query.order_by(FDRRenewalRequest.created_at.desc())
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)

    return jsonify({
        "status": "success",
        "total": pagination.total,
        "page": pagination.page,
        "per_page": pagination.per_page,
        "total_pages": pagination.pages,
        "has_next": pagination.has_next,
        "has_prev": pagination.has_prev,
        "data": [r.to_dict() for r in pagination.items],
    }), 200


# ---------------------------------------------------------------------------
# 3. GET /api/renewals/<id> - Retrieve Renewal Request Details
# ---------------------------------------------------------------------------
@renewals_bp.route("/renewals/<int:renewal_id>", methods=["GET"])
@any_authenticated_user()
def get_renewal_details(renewal_id):
    """
    Retrieve single renewal proposal details.
    """
    renewal = db.session.get(FDRRenewalRequest, renewal_id)
    if not renewal:
        return jsonify({"error": "Not Found", "message": f"Renewal request {renewal_id} was not found."}), 404

    if current_user.role == User.ROLE_INSTITUTION_USER:
        if renewal.institution_id != current_user.institution_id:
            return jsonify({
                "error": "Forbidden",
                "message": "Access denied: You cannot view renewal requests belonging to another institution."
            }), 403

    return jsonify({"status": "success", "data": renewal.to_dict()}), 200


# ---------------------------------------------------------------------------
# 4. POST /api/renewals/<id>/review - Review Renewal Proposal (AICTE/Admin Only)
# ---------------------------------------------------------------------------
@renewals_bp.route("/renewals/<int:renewal_id>/review", methods=["POST"])
@aicte_or_admin_required()
def review_renewal_request(renewal_id):
    """
    Review and approve/reject a renewal proposal.
    Restricted to AICTE Officials and Administrators.
    Transitions predecessor to RENEWED on approval and activates successor.
    """
    renewal = db.session.get(FDRRenewalRequest, renewal_id)
    if not renewal:
        return jsonify({"error": "Not Found", "message": f"Renewal request {renewal_id} was not found."}), 404

    if renewal.status != FDRRenewalRequest.STATUS_PENDING:
        return jsonify({
            "error": "Conflict",
            "message": f"This renewal request has already been reviewed ({renewal.status})."
        }), 409

    if not request.is_json:
        return jsonify({"error": "Bad Request", "message": "Request body must be valid JSON."}), 400

    data = request.get_json()
    decision = data.get("decision")
    notes = data.get("notes", "")

    if not decision or str(decision).strip().upper() not in (FDRRenewalRequest.STATUS_APPROVED, FDRRenewalRequest.STATUS_REJECTED):
        return jsonify({
            "error": "Validation Error",
            "message": "Field 'decision' is required and must be either 'APPROVED' or 'REJECTED'."
        }), 400

    decision_clean = str(decision).strip().upper()
    now_utc = datetime.utcnow()

    # Update renewal record
    renewal.status = decision_clean
    renewal.reviewer_id = current_user.id
    renewal.reviewed_at = now_utc
    renewal.review_decision = decision_clean
    renewal.review_notes = str(notes).strip() if notes else None

    original_fdr = renewal.original_fdr
    replacement_fdr = renewal.replacement_fdr

    if decision_clean == FDRRenewalRequest.STATUS_APPROVED:
        # Predecessor FDR is archived as RENEWED
        if original_fdr:
            original_fdr.status = FDRRecord.STATUS_RENEWED
            original_fdr.workflow_status = FDRRecord.WORKFLOW_RENEWAL_APPROVED
        # Replacement FDR is officially marked ACTIVE
        if replacement_fdr:
            replacement_fdr.status = FDRRecord.STATUS_ACTIVE
            replacement_fdr.workflow_status = FDRRecord.WORKFLOW_RENEWAL_APPROVED
    else:
        # Rejection: revert workflow statuses
        if original_fdr:
            original_fdr.workflow_status = FDRRecord.WORKFLOW_RENEWAL_REJECTED
        if replacement_fdr:
            replacement_fdr.workflow_status = FDRRecord.WORKFLOW_RENEWAL_REJECTED

    # Audit log
    audit = FDRAuditLog(
        fdr_record_id=renewal.original_fdr_id,
        institution_id=renewal.institution_id,
        user_id=current_user.id,
        action=f"RENEWAL_{decision_clean}",
        details=json.dumps({
            "renewal_id": renewal.id,
            "decision": decision_clean,
            "notes": str(notes).strip() if notes else None,
        }),
        ip_address=request.remote_addr,
    )
    db.session.add(audit)

    try:
        db.session.commit()
        return jsonify({
            "message": f"Renewal proposal {decision_clean.lower()} successfully.",
            "data": renewal.to_dict(),
        }), 200
    except Exception:
        db.session.rollback()
        return jsonify({"error": "Internal Server Error", "message": "Failed to record renewal review."}), 500
