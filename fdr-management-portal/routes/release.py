"""
Release and Refund Workflow Routes for AICTE FDR Portal.

Phase 7: Release/Refund Workflow and Advanced Audit Trail
Endpoints:
- POST /api/release-requests                        : Submit new release/refund request
- GET  /api/release-requests                        : List requests (tenant-isolated & paginated)
- GET  /api/release-requests/<id>                   : Retrieve request details with audit history
- PATCH /api/release-requests/<id>                  : Update or resubmit request (correction required)
- POST /api/release-requests/<id>/scrutiny          : Official scrutiny actions (AICTE Official / Admin)
- POST /api/release-requests/<id>/approval          : Final approval/rejection (Admin only, no self-approval)
- POST /api/release-requests/<id>/close             : Release closure & instrument settlement confirmation
- POST /api/release-requests/trigger-overdue-scan   : Scan for overdue requests (AICTE Official / Admin)
"""

import json
from datetime import datetime, date
from decimal import Decimal, InvalidOperation
from flask import Blueprint, request, jsonify
from flask_jwt_extended import current_user
from sqlalchemy import or_

from models import (
    db,
    FDRRecord,
    FDRReleaseRequest,
    FDRDocument,
    FDRAuditLog,
    User,
    Institution,
    FDRAlert,
)
from utils.decorators import (
    any_authenticated_user,
    aicte_or_admin_required,
    admin_required,
)
from services.audit_service import record_audit_event
from services.alert_service import (
    create_release_workflow_alert,
    scan_and_generate_release_overdue_alerts,
)

release_bp = Blueprint("release", __name__)


def _parse_amount(value):
    """Safely parse decimal monetary amount."""
    if value is None:
        return None
    try:
        dec = Decimal(str(value).strip().replace(",", ""))
        if dec <= 0:
            return None
        return dec.quantize(Decimal("0.01"))
    except (InvalidOperation, ValueError, TypeError):
        return None


# -----------------------------------------------------------------------------
# 1. POST /api/release-requests - Submit Release / Refund Request
# -----------------------------------------------------------------------------
@release_bp.route("/release-requests", methods=["POST"])
@any_authenticated_user()
def submit_release_request():
    """
    Submit a formal security deposit release or refund request.
    Institution users can only submit for FDR records owned by their institution.
    """
    if not request.is_json:
        return jsonify({"error": "Bad Request", "message": "Request body must be valid JSON."}), 400

    data = request.get_json()

    # Validate fdr_id
    fdr_id = data.get("fdr_id") or data.get("fdr_record_id")
    if not fdr_id or not str(fdr_id).isdigit():
        return jsonify({"error": "Validation Error", "message": "Field 'fdr_id' is required and must be an integer."}), 400

    fdr = db.session.get(FDRRecord, int(fdr_id))
    if not fdr:
        return jsonify({"error": "Not Found", "message": f"FDR record with ID {fdr_id} was not found."}), 404

    # Enforce Tenant Isolation
    if current_user.role == User.ROLE_INSTITUTION_USER:
        if fdr.institution_id != current_user.institution_id:
            return jsonify({
                "error": "Forbidden",
                "message": "Access denied: You cannot request release for an FDR belonging to another institution."
            }), 403

    # Check FDR Eligibility
    if fdr.status == FDRRecord.STATUS_RELEASED:
        return jsonify({
            "error": "Conflict",
            "message": f"FDR '{fdr.fdr_number}' has already been released and closed."
        }), 409

    if fdr.status == FDRRecord.STATUS_RENEWED:
        return jsonify({
            "error": "Conflict",
            "message": f"FDR '{fdr.fdr_number}' was renewed. Release requests must be filed on the active successor instrument."
        }), 409

    if fdr.status == FDRRecord.STATUS_PENDING_RENEWAL or fdr.workflow_status == FDRRecord.WORKFLOW_RENEWAL_SUBMITTED:
        return jsonify({
            "error": "Conflict",
            "message": f"FDR '{fdr.fdr_number}' has an unresolved renewal request pending review."
        }), 409

    # Check for active unresolved release requests on this FDR
    existing_active = FDRReleaseRequest.query.filter(
        FDRReleaseRequest.fdr_record_id == fdr.id,
        FDRReleaseRequest.status.notin_(list(FDRReleaseRequest.TERMINAL_STATUSES))
    ).first()
    if existing_active:
        return jsonify({
            "error": "Conflict",
            "message": f"An active release request ({existing_active.request_number}) is already in progress for this FDR ({existing_active.status})."
        }), 409

    # Request Type
    request_type = data.get("request_type", FDRReleaseRequest.TYPE_RELEASE)
    if not isinstance(request_type, str) or request_type.strip().upper() not in FDRReleaseRequest.ALLOWED_REQUEST_TYPES:
        return jsonify({
            "error": "Validation Error",
            "message": f"Field 'request_type' must be one of: {', '.join(sorted(FDRReleaseRequest.ALLOWED_REQUEST_TYPES))}."
        }), 400
    request_type = request_type.strip().upper()

    # Reason
    reason = data.get("reason")
    if not reason or not isinstance(reason, str) or len(reason.strip()) < 10:
        return jsonify({
            "error": "Validation Error",
            "message": "Field 'reason' is required and must contain at least 10 characters."
        }), 400
    reason_clean = reason.strip()

    # Requested Amount (defaults to FDR deposit amount)
    req_amount_raw = data.get("requested_amount")
    if req_amount_raw is not None:
        requested_amount = _parse_amount(req_amount_raw)
        if requested_amount is None:
            return jsonify({
                "error": "Validation Error",
                "message": "Field 'requested_amount' must be a positive number."
            }), 400
        if requested_amount > fdr.deposit_amount:
            return jsonify({
                "error": "Validation Error",
                "message": f"Requested amount (INR {requested_amount:,.2f}) cannot exceed FDR deposit amount (INR {fdr.deposit_amount:,.2f})."
            }), 400
    else:
        requested_amount = fdr.deposit_amount

    # Validate supporting documents
    doc_ids_input = data.get("supporting_document_ids", [])
    valid_doc_ids = []
    if doc_ids_input:
        if not isinstance(doc_ids_input, list):
            return jsonify({"error": "Validation Error", "message": "'supporting_document_ids' must be a list of document IDs."}), 400
        for doc_id in doc_ids_input:
            if not str(doc_id).isdigit():
                continue
            doc = db.session.get(FDRDocument, int(doc_id))
            if not doc:
                return jsonify({"error": "Validation Error", "message": f"Document ID {doc_id} was not found."}), 400
            if doc.institution_id != fdr.institution_id:
                return jsonify({"error": "Forbidden", "message": f"Document ID {doc_id} belongs to another institution."}), 403
            valid_doc_ids.append(int(doc_id))

    # Bank details (for verification)
    bank_details_input = data.get("bank_details", {})
    if not isinstance(bank_details_input, dict):
        bank_details_input = {}

    request_number = FDRReleaseRequest.generate_request_number()

    release_req = FDRReleaseRequest(
        request_number=request_number,
        institution_id=fdr.institution_id,
        fdr_record_id=fdr.id,
        request_type=request_type,
        reason=reason_clean,
        requested_amount=requested_amount,
        status=FDRReleaseRequest.STATUS_PENDING_SCRUTINY,
        requested_by_id=current_user.id,
        created_at=datetime.utcnow(),
    )
    release_req.set_document_ids_list(valid_doc_ids)
    release_req.set_bank_details_dict(bank_details_input)
    db.session.add(release_req)
    db.session.flush()

    # Record Audit Event
    record_audit_event(
        action="RELEASE_REQUEST_SUBMITTED",
        entity_type="RELEASE_REQUEST",
        entity_id=release_req.id,
        user=current_user,
        institution_id=fdr.institution_id,
        fdr_record_id=fdr.id,
        release_request_id=release_req.id,
        previous_state=None,
        new_state=release_req.to_dict(),
        remarks=f"Submitted {request_type} request for INR {requested_amount:,.2f}",
        ip_address=request.remote_addr,
    )

    # In-portal notification to AICTE Officials
    create_release_workflow_alert(
        release_req=release_req,
        event_type=FDRAlert.TYPE_RELEASE_SUBMITTED,
        remarks=reason_clean,
        target_role="aicte_official",
    )

    try:
        db.session.commit()
        return jsonify({
            "message": "Release/refund request submitted successfully and is pending official scrutiny.",
            "data": release_req.to_dict(),
        }), 201
    except Exception:
        db.session.rollback()
        return jsonify({"error": "Internal Server Error", "message": "Failed to submit release request."}), 500


# -----------------------------------------------------------------------------
# 2. GET /api/release-requests - List Requests (Tenant Isolated)
# -----------------------------------------------------------------------------
@release_bp.route("/release-requests", methods=["GET"])
@any_authenticated_user()
def list_release_requests():
    """
    List release and refund requests with pagination and filters.
    Enforces multi-tenant isolation: institution_user sees only their institution's requests.
    """
    try:
        page = int(request.args.get("page", 1))
        per_page = int(request.args.get("per_page", 10))
        if page < 1 or per_page < 1:
            raise ValueError()
    except (ValueError, TypeError):
        return jsonify({"error": "Bad Request", "message": "'page' and 'per_page' must be positive integers."}), 400

    per_page = min(per_page, 100)
    query = FDRReleaseRequest.query

    # Tenant isolation
    if current_user.role == User.ROLE_INSTITUTION_USER:
        query = query.filter(FDRReleaseRequest.institution_id == current_user.institution_id)
    else:
        inst_param = request.args.get("institution_id")
        if inst_param and inst_param.isdigit():
            query = query.filter(FDRReleaseRequest.institution_id == int(inst_param))

    # Filters
    status_filter = request.args.get("status")
    if status_filter and status_filter.strip().upper() in FDRReleaseRequest.ALLOWED_STATUSES:
        query = query.filter(FDRReleaseRequest.status == status_filter.strip().upper())

    type_filter = request.args.get("request_type")
    if type_filter and type_filter.strip().upper() in FDRReleaseRequest.ALLOWED_REQUEST_TYPES:
        query = query.filter(FDRReleaseRequest.request_type == type_filter.strip().upper())

    fdr_filter = request.args.get("fdr_id")
    if fdr_filter and fdr_filter.isdigit():
        query = query.filter(FDRReleaseRequest.fdr_record_id == int(fdr_filter))

    query = query.order_by(FDRReleaseRequest.created_at.desc())
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


# -----------------------------------------------------------------------------
# 3. GET /api/release-requests/<id> - Retrieve Single Request
# -----------------------------------------------------------------------------
@release_bp.route("/release-requests/<int:request_id>", methods=["GET"])
@any_authenticated_user()
def get_release_request(request_id):
    """
    Retrieve full details of a release request, including multi-level audit history.
    """
    req = db.session.get(FDRReleaseRequest, request_id)
    if not req:
        return jsonify({"error": "Not Found", "message": f"Release request with ID {request_id} was not found."}), 404

    # Tenant check
    if current_user.role == User.ROLE_INSTITUTION_USER:
        if req.institution_id != current_user.institution_id:
            return jsonify({
                "error": "Forbidden",
                "message": "Access denied: You cannot view release requests belonging to another institution."
            }), 403

    include_audit = request.args.get("include_audit", "true").lower() in ("true", "1", "yes")
    return jsonify({
        "status": "success",
        "data": req.to_dict(include_audit=include_audit),
    }), 200


# -----------------------------------------------------------------------------
# 4. PATCH /api/release-requests/<id> - Update or Resubmit Request
# -----------------------------------------------------------------------------
@release_bp.route("/release-requests/<int:request_id>", methods=["PATCH"])
@any_authenticated_user()
def update_or_resubmit_request(request_id):
    """
    Update request details or resubmit after corrections.
    Allowed only when status is PENDING_SCRUTINY or CORRECTION_REQUIRED.
    Institution users can only update their own institution's requests.
    """
    req = db.session.get(FDRReleaseRequest, request_id)
    if not req:
        return jsonify({"error": "Not Found", "message": f"Release request with ID {request_id} was not found."}), 404

    # Tenant check
    if current_user.role == User.ROLE_INSTITUTION_USER:
        if req.institution_id != current_user.institution_id:
            return jsonify({
                "error": "Forbidden",
                "message": "Access denied: You cannot modify release requests belonging to another institution."
            }), 403

    # Check modifiable status
    if req.status not in (FDRReleaseRequest.STATUS_PENDING_SCRUTINY, FDRReleaseRequest.STATUS_CORRECTION_REQUIRED):
        return jsonify({
            "error": "Conflict",
            "message": f"Request cannot be modified in '{req.status}' status. Editing is only permitted during PENDING_SCRUTINY or CORRECTION_REQUIRED."
        }), 409

    if not request.is_json:
        return jsonify({"error": "Bad Request", "message": "Request body must be valid JSON."}), 400

    data = request.get_json()
    prev_snapshot = req.to_dict()
    updated_fields = []

    # Update reason if provided
    if "reason" in data:
        new_reason = str(data["reason"]).strip()
        if len(new_reason) < 10:
            return jsonify({"error": "Validation Error", "message": "Field 'reason' must be at least 10 characters."}), 400
        req.reason = new_reason
        updated_fields.append("reason")

    # Update requested amount if provided
    if "requested_amount" in data:
        new_amt = _parse_amount(data["requested_amount"])
        if new_amt is None:
            return jsonify({"error": "Validation Error", "message": "Field 'requested_amount' must be a positive number."}), 400
        if req.fdr_record and new_amt > req.fdr_record.deposit_amount:
            return jsonify({"error": "Validation Error", "message": "Requested amount exceeds FDR deposit amount."}), 400
        req.requested_amount = new_amt
        updated_fields.append("requested_amount")

    # Update supporting documents
    if "supporting_document_ids" in data:
        doc_ids_input = data["supporting_document_ids"]
        if not isinstance(doc_ids_input, list):
            return jsonify({"error": "Validation Error", "message": "'supporting_document_ids' must be a list of document IDs."}), 400
        clean_doc_ids = []
        for doc_id in doc_ids_input:
            if not str(doc_id).isdigit():
                continue
            doc = db.session.get(FDRDocument, int(doc_id))
            if not doc:
                return jsonify({"error": "Validation Error", "message": f"Document ID {doc_id} not found."}), 400
            if doc.institution_id != req.institution_id:
                return jsonify({"error": "Forbidden", "message": f"Document ID {doc_id} belongs to another institution."}), 403
            clean_doc_ids.append(int(doc_id))
        req.set_document_ids_list(clean_doc_ids)
        updated_fields.append("supporting_document_ids")

    # Update bank details
    if "bank_details" in data:
        b_details = data["bank_details"]
        if isinstance(b_details, dict):
            req.set_bank_details_dict(b_details)
            updated_fields.append("bank_details")

    # Resubmission handling
    resubmit_flag = data.get("resubmit", False)
    transitioned_to_resubmitted = False
    if resubmit_flag:
        if req.status != FDRReleaseRequest.STATUS_CORRECTION_REQUIRED:
            return jsonify({
                "error": "Conflict",
                "message": f"Cannot resubmit request from '{req.status}'. Resubmission is only valid when status is CORRECTION_REQUIRED."
            }), 409
        
        valid, err = req.can_transition_to(FDRReleaseRequest.STATUS_RESUBMITTED)
        if not valid:
            return jsonify({"error": "Conflict", "message": err}), 409

        req.status = FDRReleaseRequest.STATUS_RESUBMITTED
        transitioned_to_resubmitted = True
        updated_fields.append("status:RESUBMITTED")

    req.updated_at = datetime.utcnow()

    # Record Audit Event
    action_name = "RELEASE_REQUEST_RESUBMITTED" if transitioned_to_resubmitted else "RELEASE_REQUEST_UPDATED"
    record_audit_event(
        action=action_name,
        entity_type="RELEASE_REQUEST",
        entity_id=req.id,
        user=current_user,
        institution_id=req.institution_id,
        fdr_record_id=req.fdr_record_id,
        release_request_id=req.id,
        previous_state=prev_snapshot,
        new_state=req.to_dict(),
        remarks=f"Updated fields: {', '.join(updated_fields)}",
        ip_address=request.remote_addr,
    )

    # If resubmitted, alert AICTE Official
    if transitioned_to_resubmitted:
        create_release_workflow_alert(
            release_req=req,
            event_type=FDRAlert.TYPE_RELEASE_PENDING_SCRUTINY,
            remarks="Corrections submitted by institution; ready for renewed scrutiny.",
            target_role="aicte_official",
        )

    try:
        db.session.commit()
        return jsonify({
            "message": "Release request updated successfully." if not transitioned_to_resubmitted else "Release request resubmitted for official scrutiny.",
            "data": req.to_dict(),
        }), 200
    except Exception:
        db.session.rollback()
        return jsonify({"error": "Internal Server Error", "message": "Failed to update release request."}), 500


# -----------------------------------------------------------------------------
# 5. POST /api/release-requests/<id>/scrutiny - Official Scrutiny
# -----------------------------------------------------------------------------
@release_bp.route("/release-requests/<int:request_id>/scrutiny", methods=["POST"])
@aicte_or_admin_required()
def scrutinize_release_request(request_id):
    """
    Official scrutiny of release/refund requests.
    Authorized actions:
    - START_REVIEW         : Moves to UNDER_REVIEW
    - REQUEST_CORRECTION   : Moves to CORRECTION_REQUIRED (asks for missing docs/clarification)
    - RECOMMEND_APPROVAL   : Moves to RECOMMENDED_FOR_APPROVAL (forwards to Administrator)
    - REJECT               : Moves to REJECTED (disapproves request)
    """
    req = db.session.get(FDRReleaseRequest, request_id)
    if not req:
        return jsonify({"error": "Not Found", "message": f"Release request with ID {request_id} was not found."}), 404

    if not request.is_json:
        return jsonify({"error": "Bad Request", "message": "Request body must be valid JSON."}), 400

    data = request.get_json()
    action = str(data.get("action", "")).strip().upper()
    remarks = data.get("remarks")

    if not remarks or not isinstance(remarks, str) or len(remarks.strip()) < 5:
        return jsonify({"error": "Validation Error", "message": "Field 'remarks' is required (minimum 5 characters)."}), 400
    remarks_clean = remarks.strip()

    allowed_scrutiny_actions = {
        "START_REVIEW": FDRReleaseRequest.STATUS_UNDER_REVIEW,
        "REQUEST_CORRECTION": FDRReleaseRequest.STATUS_CORRECTION_REQUIRED,
        "RECOMMEND_APPROVAL": FDRReleaseRequest.STATUS_RECOMMENDED_FOR_APPROVAL,
        "REJECT": FDRReleaseRequest.STATUS_REJECTED,
    }

    if action not in allowed_scrutiny_actions:
        return jsonify({
            "error": "Validation Error",
            "message": f"Field 'action' must be one of: {', '.join(allowed_scrutiny_actions.keys())}."
        }), 400

    target_status = allowed_scrutiny_actions[action]
    valid, err_msg = req.can_transition_to(target_status)
    if not valid:
        return jsonify({"error": "Conflict", "message": err_msg}), 409

    prev_snapshot = req.to_dict()
    now_utc = datetime.utcnow()

    # Update scrutiny details
    req.status = target_status
    req.scrutinized_by_id = current_user.id
    req.assigned_reviewer_id = current_user.id
    req.scrutiny_action = action
    req.scrutiny_remarks = remarks_clean
    req.updated_at = now_utc

    if action == "REQUEST_CORRECTION":
        req.correction_remarks = remarks_clean
    elif action in ("RECOMMEND_APPROVAL", "REJECT"):
        req.scrutiny_completed_at = now_utc

    # Record Audit Event
    record_audit_event(
        action=f"SCRUTINY_{action}",
        entity_type="RELEASE_REQUEST",
        entity_id=req.id,
        user=current_user,
        institution_id=req.institution_id,
        fdr_record_id=req.fdr_record_id,
        release_request_id=req.id,
        previous_state=prev_snapshot,
        new_state=req.to_dict(),
        remarks=remarks_clean,
        ip_address=request.remote_addr,
    )

    # Notifications based on action
    if target_status == FDRReleaseRequest.STATUS_CORRECTION_REQUIRED:
        create_release_workflow_alert(
            release_req=req,
            event_type=FDRAlert.TYPE_RELEASE_CORRECTION,
            remarks=remarks_clean,
            target_role="institution_user",
        )
    elif target_status == FDRReleaseRequest.STATUS_RECOMMENDED_FOR_APPROVAL:
        create_release_workflow_alert(
            release_req=req,
            event_type=FDRAlert.TYPE_RELEASE_RECOMMENDED,
            remarks=remarks_clean,
            target_role="administrator",
        )
    elif target_status == FDRReleaseRequest.STATUS_REJECTED:
        create_release_workflow_alert(
            release_req=req,
            event_type=FDRAlert.TYPE_RELEASE_REJECTED,
            remarks=remarks_clean,
            target_role="institution_user",
        )

    try:
        db.session.commit()
        return jsonify({
            "message": f"Scrutiny action '{action}' recorded successfully. Request status updated to {target_status}.",
            "data": req.to_dict(),
        }), 200
    except Exception:
        db.session.rollback()
        return jsonify({"error": "Internal Server Error", "message": "Failed to record scrutiny action."}), 500


# -----------------------------------------------------------------------------
# 6. POST /api/release-requests/<id>/approval - Final Approval (Admin Only)
# -----------------------------------------------------------------------------
@release_bp.route("/release-requests/<int:request_id>/approval", methods=["POST"])
@admin_required()
def approve_release_request(request_id):
    """
    Final decision by authorized Administrator.
    Valid decisions:
    - APPROVE    : Moves to APPROVED
    - REJECT     : Moves to REJECTED
    - SEND_BACK  : Moves to CORRECTION_REQUIRED
    Enforces that the administrator cannot self-approve their own submitted request.
    """
    req = db.session.get(FDRReleaseRequest, request_id)
    if not req:
        return jsonify({"error": "Not Found", "message": f"Release request with ID {request_id} was not found."}), 404

    # Prevent Self-Approval
    if req.requested_by_id == current_user.id:
        return jsonify({
            "error": "Forbidden",
            "message": "Conflict of interest: Users are prohibited from approving their own release requests."
        }), 403

    if not request.is_json:
        return jsonify({"error": "Bad Request", "message": "Request body must be valid JSON."}), 400

    data = request.get_json()
    decision = str(data.get("decision", "")).strip().upper()
    remarks = data.get("remarks")

    if not remarks or not isinstance(remarks, str) or len(remarks.strip()) < 5:
        return jsonify({"error": "Validation Error", "message": "Field 'remarks' is required (minimum 5 characters)."}), 400
    remarks_clean = remarks.strip()

    allowed_decisions = {
        "APPROVE": FDRReleaseRequest.STATUS_APPROVED,
        "REJECT": FDRReleaseRequest.STATUS_REJECTED,
        "SEND_BACK": FDRReleaseRequest.STATUS_CORRECTION_REQUIRED,
    }

    if decision not in allowed_decisions:
        return jsonify({
            "error": "Validation Error",
            "message": f"Field 'decision' must be one of: {', '.join(allowed_decisions.keys())}."
        }), 400

    target_status = allowed_decisions[decision]
    valid, err_msg = req.can_transition_to(target_status)
    if not valid:
        return jsonify({"error": "Conflict", "message": err_msg}), 409

    prev_snapshot = req.to_dict()
    now_utc = datetime.utcnow()

    req.status = target_status
    req.approved_by_id = current_user.id
    req.approval_decision = decision
    req.approval_remarks = remarks_clean
    req.approved_at = now_utc
    req.updated_at = now_utc

    # Record Audit Event
    record_audit_event(
        action=f"FINAL_APPROVAL_{decision}",
        entity_type="RELEASE_REQUEST",
        entity_id=req.id,
        user=current_user,
        institution_id=req.institution_id,
        fdr_record_id=req.fdr_record_id,
        release_request_id=req.id,
        previous_state=prev_snapshot,
        new_state=req.to_dict(),
        remarks=remarks_clean,
        ip_address=request.remote_addr,
    )

    # Alerts
    if target_status == FDRReleaseRequest.STATUS_APPROVED:
        create_release_workflow_alert(
            release_req=req,
            event_type=FDRAlert.TYPE_RELEASE_APPROVED,
            remarks=remarks_clean,
            target_role="institution_user",
        )
    elif target_status == FDRReleaseRequest.STATUS_REJECTED:
        create_release_workflow_alert(
            release_req=req,
            event_type=FDRAlert.TYPE_RELEASE_REJECTED,
            remarks=remarks_clean,
            target_role="institution_user",
        )
    elif target_status == FDRReleaseRequest.STATUS_CORRECTION_REQUIRED:
        create_release_workflow_alert(
            release_req=req,
            event_type=FDRAlert.TYPE_RELEASE_CORRECTION,
            remarks=remarks_clean,
            target_role="institution_user",
        )

    try:
        db.session.commit()
        return jsonify({
            "message": f"Final approval decision '{decision}' recorded successfully.",
            "data": req.to_dict(),
        }), 200
    except Exception:
        db.session.rollback()
        return jsonify({"error": "Internal Server Error", "message": "Failed to record approval decision."}), 500


# -----------------------------------------------------------------------------
# 7. POST /api/release-requests/<id>/close - Final Closure / Settlement
# -----------------------------------------------------------------------------
@release_bp.route("/release-requests/<int:request_id>/close", methods=["POST"])
@aicte_or_admin_required()
def close_and_settle_release_request(request_id):
    """
    Final administrative closure of an approved release request.
    Transitions request to RELEASED_CLOSED and updates FDRRecord.status to RELEASED.
    Disclaimer: Records that physical banking disbursement must follow official finance
    channels outside this application.
    """
    req = db.session.get(FDRReleaseRequest, request_id)
    if not req:
        return jsonify({"error": "Not Found", "message": f"Release request with ID {request_id} was not found."}), 404

    if req.status != FDRReleaseRequest.STATUS_APPROVED:
        return jsonify({
            "error": "Conflict",
            "message": f"Cannot close release request in '{req.status}' status. Request must be in APPROVED status before closure."
        }), 409

    if not request.is_json:
        return jsonify({"error": "Bad Request", "message": "Request body must be valid JSON."}), 400

    data = request.get_json()
    remarks = data.get("remarks", "Release confirmed and instrument marked RELEASED.")
    closure_ref = data.get("closure_reference", "")

    valid, err_msg = req.can_transition_to(FDRReleaseRequest.STATUS_RELEASED_CLOSED)
    if not valid:
        return jsonify({"error": "Conflict", "message": err_msg}), 409

    prev_snapshot = req.to_dict()
    now_utc = datetime.utcnow()

    # Transition release request
    req.status = FDRReleaseRequest.STATUS_RELEASED_CLOSED
    req.closed_by_id = current_user.id
    req.closure_reference = str(closure_ref).strip() if closure_ref else None
    req.closure_remarks = str(remarks).strip()
    req.closed_at = now_utc
    req.updated_at = now_utc

    # Transition underlying FDR Record to RELEASED
    fdr = req.fdr_record
    if fdr:
        fdr.status = FDRRecord.STATUS_RELEASED
        fdr.updated_at = now_utc

    # Record Audit Event
    record_audit_event(
        action="RELEASE_REQUEST_CLOSED",
        entity_type="RELEASE_REQUEST",
        entity_id=req.id,
        user=current_user,
        institution_id=req.institution_id,
        fdr_record_id=req.fdr_record_id,
        release_request_id=req.id,
        previous_state=prev_snapshot,
        new_state=req.to_dict(),
        remarks=(
            f"Release finalized by {current_user.email}. "
            f"FDR '{fdr.fdr_number if fdr else req.fdr_record_id}' marked RELEASED. "
            f"Physical bank disbursement occurs via institutional finance accounts."
        ),
        details={"closure_reference": closure_ref},
        ip_address=request.remote_addr,
    )

    # In-portal alert to institution
    create_release_workflow_alert(
        release_req=req,
        event_type=FDRAlert.TYPE_RELEASE_CLOSED,
        remarks=f"Security deposit released successfully. Reference: {closure_ref or 'N/A'}",
        target_role="institution_user",
    )

    try:
        db.session.commit()
        return jsonify({
            "message": "Release request successfully closed. Instrument status updated to RELEASED.",
            "data": req.to_dict(),
        }), 200
    except Exception:
        db.session.rollback()
        return jsonify({"error": "Internal Server Error", "message": "Failed to finalize release closure."}), 500


# -----------------------------------------------------------------------------
# 8. POST /api/release-requests/trigger-overdue-scan - Escalation Scanner
# -----------------------------------------------------------------------------
@release_bp.route("/release-requests/trigger-overdue-scan", methods=["POST"])
@aicte_or_admin_required()
def trigger_release_overdue_scan():
    """
    Trigger scan for release requests that have exceeded review turnaround SLAs.
    Generates escalation alerts to regulators without duplicates.
    """
    days = 7
    if request.is_json:
        req_days = request.get_json().get("overdue_days")
        if req_days and str(req_days).isdigit() and int(req_days) > 0:
            days = int(req_days)

    res = scan_and_generate_release_overdue_alerts(overdue_days=days)
    return jsonify(res), 200
