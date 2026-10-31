"""
FDR Management Routes Module for AICTE FDR Portal.

Phase 4: Secured with JWT Authentication and Institution-Level Data Isolation (RBAC)
Endpoints:
- POST  /api/fdr         : Create new FDR record (scoped to institution for institution_user)
- GET   /api/fdr/search  : Search and filter FDR records (isolated by institution)
- GET   /api/fdr         : List FDR records with pagination (isolated by institution)
- GET   /api/fdr/<id>    : Retrieve single FDR record by ID (enforces ownership)
- PATCH /api/fdr/<id>    : Update permitted FDR fields with validation (enforces ownership)
"""

from datetime import datetime, date
from decimal import Decimal, InvalidOperation
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, current_user
from sqlalchemy import or_, and_, func
from models import db, FDRRecord, Institution, User
from utils.decorators import any_authenticated_user
from services.audit_service import record_audit_event

fdr_bp = Blueprint("fdr", __name__)

ALLOWED_STATUSES = {"ACTIVE", "MATURED", "RELEASED", "LIEN_MARKED"}
PROTECTED_FIELDS = {"id", "created_at", "updated_at"}


def parse_iso_date(date_str, field_name):
    """
    Parse an ISO format date string (YYYY-MM-DD).
    Returns (datetime.date, None) on success, or (None, error_message) on failure.
    """
    if not isinstance(date_str, str):
        return None, f"'{field_name}' must be a string in YYYY-MM-DD format."
    try:
        parsed_date = datetime.strptime(date_str.strip(), "%Y-%m-%d").date()
        return parsed_date, None
    except ValueError:
        return None, f"Invalid date format for '{field_name}'. Expected YYYY-MM-DD."


def parse_decimal_amount(amount_val):
    """
    Safely parse financial amount to Decimal.
    Returns (Decimal, None) on success, or (None, error_message) on failure.
    """
    try:
        if amount_val is None or isinstance(amount_val, bool):
            return None, "Deposit amount is required and must be a number."
        dec_amount = Decimal(str(amount_val)).quantize(Decimal("0.01"))
        if dec_amount <= Decimal("0.00"):
            return None, "Deposit amount must be a positive number greater than 0."
        return dec_amount, None
    except (InvalidOperation, TypeError, ValueError):
        return None, "Deposit amount must be a valid numeric value."


# ---------------------------------------------------------------------------
# 1. POST /api/fdr - Create New FDR Record (Authenticated & Isolated)
# ---------------------------------------------------------------------------
@fdr_bp.route("", methods=["POST"])
@fdr_bp.route("/", methods=["POST"])
@any_authenticated_user()
def create_fdr():
    """
    Create a new FDR record with strict data validation.
    Enforces that institution_user can only submit FDRs for their own institution.
    """
    if not request.is_json:
        return jsonify({
            "error": "Bad Request",
            "message": "Request body must be valid JSON with Content-Type: application/json."
        }), 400

    data = request.get_json()
    if not isinstance(data, dict):
        return jsonify({
            "error": "Bad Request",
            "message": "Request payload must be a JSON object."
        }), 400

    # 1. Determine and Validate Target Institution ID with Tenant Isolation
    target_inst_id = data.get("institution_id")
    if current_user.role == User.ROLE_INSTITUTION_USER:
        if not current_user.institution_id:
            return jsonify({
                "error": "Forbidden",
                "message": "User account is not associated with an institution."
            }), 403

        # If user explicitly supplied institution_id, verify it matches their assigned institution
        if target_inst_id is not None:
            try:
                if int(target_inst_id) != current_user.institution_id:
                    return jsonify({
                        "error": "Forbidden",
                        "message": "Access denied: You may only create FDR records for your assigned institution."
                    }), 403
            except (ValueError, TypeError):
                return jsonify({
                    "error": "Validation Error",
                    "message": "Field 'institution_id' must be a valid integer."
                }), 400

        institution_id = current_user.institution_id
    else:
        # AICTE Officials and Administrators must supply a valid institution_id
        if not target_inst_id:
            return jsonify({
                "error": "Validation Error",
                "message": "Field 'institution_id' is required."
            }), 400
        try:
            institution_id = int(target_inst_id)
        except (ValueError, TypeError):
            return jsonify({
                "error": "Validation Error",
                "message": "Field 'institution_id' must be an integer."
            }), 400

    # 2. Check required fields
    required_fields = ["fdr_number", "issuing_bank", "deposit_amount", "issue_date", "maturity_date"]
    missing = [f for f in required_fields if f not in data or data[f] is None or (isinstance(data[f], str) and not data[f].strip())]
    if missing:
        return jsonify({
            "error": "Validation Error",
            "message": f"Missing required fields: {', '.join(missing)}."
        }), 400

    # 3. Validate Institution exists
    institution = db.session.get(Institution, institution_id)
    if not institution:
        return jsonify({
            "error": "Not Found",
            "message": f"Institution with ID {institution_id} does not exist."
        }), 404

    # 4. Validate FDR Number & Normalized Duplicate Check
    fdr_number_raw = str(data.get("fdr_number", "")).strip()
    if not fdr_number_raw:
        return jsonify({
            "error": "Validation Error",
            "message": "Field 'fdr_number' cannot be blank."
        }), 400

    # Normalized duplicate check
    existing_fdr = FDRRecord.query.filter(
        func.upper(FDRRecord.fdr_number) == fdr_number_raw.upper()
    ).first()
    if existing_fdr:
        return jsonify({
            "error": "Conflict",
            "message": f"An FDR record with number '{fdr_number_raw}' already exists (ID: {existing_fdr.id})."
        }), 409

    # 5. Validate Issuing Bank
    issuing_bank_raw = str(data.get("issuing_bank", "")).strip()
    if not issuing_bank_raw:
        return jsonify({
            "error": "Validation Error",
            "message": "Field 'issuing_bank' cannot be blank."
        }), 400

    # 6. Validate Deposit Amount
    deposit_amount, err = parse_decimal_amount(data.get("deposit_amount"))
    if err:
        return jsonify({"error": "Validation Error", "message": err}), 400

    # 7. Validate Dates
    issue_date, err = parse_iso_date(data.get("issue_date"), "issue_date")
    if err:
        return jsonify({"error": "Validation Error", "message": err}), 400

    maturity_date, err = parse_iso_date(data.get("maturity_date"), "maturity_date")
    if err:
        return jsonify({"error": "Validation Error", "message": err}), 400

    if maturity_date <= issue_date:
        return jsonify({
            "error": "Validation Error",
            "message": "Maturity date must be strictly later than issue date."
        }), 400

    # 8. Validate Status (default: ACTIVE)
    status_raw = data.get("status", "ACTIVE")
    if not isinstance(status_raw, str):
        return jsonify({"error": "Validation Error", "message": "Field 'status' must be a string."}), 400
    status = status_raw.strip().upper()
    if status not in ALLOWED_STATUSES:
        return jsonify({
            "error": "Validation Error",
            "message": f"Invalid status '{status}'. Allowed values are: {', '.join(sorted(ALLOWED_STATUSES))}."
        }), 400

    # 9. Create and persist FDR Record
    new_fdr = FDRRecord(
        institution_id=institution.id,
        fdr_number=fdr_number_raw,
        issuing_bank=issuing_bank_raw,
        deposit_amount=deposit_amount,
        issue_date=issue_date,
        maturity_date=maturity_date,
        status=status,
    )

    try:
        db.session.add(new_fdr)
        db.session.flush()

        record_audit_event(
            action="FDR_CREATED",
            entity_type="FDR_RECORD",
            entity_id=new_fdr.id,
            user=current_user,
            institution_id=new_fdr.institution_id,
            fdr_record_id=new_fdr.id,
            new_state=new_fdr.to_dict(),
            remarks=f"FDR record '{new_fdr.fdr_number}' created for amount INR {new_fdr.deposit_amount:,.2f}.",
            ip_address=request.remote_addr,
        )

        db.session.commit()
        return jsonify({
            "message": "FDR record created successfully.",
            "data": new_fdr.to_dict()
        }), 201
    except Exception:
        db.session.rollback()
        return jsonify({
            "error": "Internal Server Error",
            "message": "A database error occurred while creating the FDR record."
        }), 500


# ---------------------------------------------------------------------------
# 2. GET /api/fdr/search - Search and Filter FDR Records (Isolated)
# ---------------------------------------------------------------------------
@fdr_bp.route("/search", methods=["GET"])
@any_authenticated_user()
def search_fdr():
    """
    Search and filter FDR records by fdr_number, bank_name, status, and maturity date.
    Strictly isolates institution_user to records from their own institution.
    """
    # 1. Parse pagination parameters
    try:
        page = int(request.args.get("page", 1))
        per_page = int(request.args.get("per_page", 10))
        if page < 1 or per_page < 1:
            raise ValueError()
    except (ValueError, TypeError):
        return jsonify({
            "error": "Bad Request",
            "message": "Query parameters 'page' and 'per_page' must be positive integers."
        }), 400

    per_page = min(per_page, 100)
    query = FDRRecord.query
    filters_applied = {}

    # 2. Enforce Institution Isolation for institution_user
    if current_user.role == User.ROLE_INSTITUTION_USER:
        query = query.filter(FDRRecord.institution_id == current_user.institution_id)
        filters_applied["institution_id"] = current_user.institution_id
    else:
        # AICTE / Admin can optionally filter by institution_id
        inst_id_query = request.args.get("institution_id")
        if inst_id_query and inst_id_query.strip():
            try:
                val_id = int(inst_id_query.strip())
                query = query.filter(FDRRecord.institution_id == val_id)
                filters_applied["institution_id"] = val_id
            except ValueError:
                return jsonify({"error": "Bad Request", "message": "Query parameter 'institution_id' must be an integer."}), 400

    # Filter: fdr_number (case-insensitive substring)
    fdr_number_query = request.args.get("fdr_number")
    if fdr_number_query and fdr_number_query.strip():
        val = fdr_number_query.strip()
        query = query.filter(FDRRecord.fdr_number.ilike(f"%{val}%"))
        filters_applied["fdr_number"] = val

    # Filter: bank_name / issuing_bank
    bank_query = request.args.get("bank_name") or request.args.get("issuing_bank")
    if bank_query and bank_query.strip():
        val_bank = bank_query.strip()
        query = query.filter(FDRRecord.issuing_bank.ilike(f"%{val_bank}%"))
        filters_applied["bank_name"] = val_bank

    # Filter: status
    status_query = request.args.get("status")
    if status_query and status_query.strip():
        val_status = status_query.strip().upper()
        if val_status not in ALLOWED_STATUSES:
            return jsonify({
                "error": "Bad Request",
                "message": f"Invalid status filter '{val_status}'. Allowed values: {', '.join(sorted(ALLOWED_STATUSES))}."
            }), 400
        query = query.filter(FDRRecord.status == val_status)
        filters_applied["status"] = val_status

    # Filter: maturity date range
    maturity_from_str = request.args.get("maturity_from")
    maturity_from_date = None
    if maturity_from_str and maturity_from_str.strip():
        maturity_from_date, err = parse_iso_date(maturity_from_str.strip(), "maturity_from")
        if err:
            return jsonify({"error": "Bad Request", "message": err}), 400
        query = query.filter(FDRRecord.maturity_date >= maturity_from_date)
        filters_applied["maturity_from"] = maturity_from_date.isoformat()

    maturity_to_str = request.args.get("maturity_to")
    maturity_to_date = None
    if maturity_to_str and maturity_to_str.strip():
        maturity_to_date, err = parse_iso_date(maturity_to_str.strip(), "maturity_to")
        if err:
            return jsonify({"error": "Bad Request", "message": err}), 400
        query = query.filter(FDRRecord.maturity_date <= maturity_to_date)
        filters_applied["maturity_to"] = maturity_to_date.isoformat()

    if maturity_from_date and maturity_to_date and maturity_from_date > maturity_to_date:
        return jsonify({
            "error": "Bad Request",
            "message": "'maturity_from' date cannot be after 'maturity_to' date."
        }), 400

    query = query.order_by(FDRRecord.maturity_date.asc(), FDRRecord.id.desc())
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)

    return jsonify({
        "status": "success",
        "total": pagination.total,
        "page": pagination.page,
        "per_page": pagination.per_page,
        "total_pages": pagination.pages,
        "has_next": pagination.has_next,
        "has_prev": pagination.has_prev,
        "filters_applied": filters_applied,
        "data": [item.to_dict() for item in pagination.items]
    }), 200


# ---------------------------------------------------------------------------
# 3. GET /api/fdr - Retrieve FDR Records (Authenticated & Scoped)
# ---------------------------------------------------------------------------
@fdr_bp.route("", methods=["GET"])
@fdr_bp.route("/", methods=["GET"])
@any_authenticated_user()
def get_all_fdrs():
    """
    Retrieve FDR records with pagination.
    Strictly limits institution_user to their assigned institution's records.
    """
    try:
        page = int(request.args.get("page", 1))
        per_page = int(request.args.get("per_page", 10))
        if page < 1 or per_page < 1:
            raise ValueError()
    except (ValueError, TypeError):
        return jsonify({
            "error": "Bad Request",
            "message": "Query parameters 'page' and 'per_page' must be positive integers."
        }), 400

    per_page = min(per_page, 100)
    query = FDRRecord.query

    # Enforce isolation: institution_user is hard-filtered to their institution
    if current_user.role == User.ROLE_INSTITUTION_USER:
        query = query.filter(FDRRecord.institution_id == current_user.institution_id)
    else:
        # AICTE / Admin can optionally filter by institution_id
        inst_id_param = request.args.get("institution_id")
        if inst_id_param:
            try:
                inst_id = int(inst_id_param)
                query = query.filter(FDRRecord.institution_id == inst_id)
            except ValueError:
                return jsonify({"error": "Bad Request", "message": "Query parameter 'institution_id' must be an integer."}), 400

    # Optional status filter
    status_param = request.args.get("status")
    if status_param:
        status_clean = status_param.strip().upper()
        if status_clean in ALLOWED_STATUSES:
            query = query.filter(FDRRecord.status == status_clean)

    query = query.order_by(FDRRecord.created_at.desc(), FDRRecord.id.desc())
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)

    return jsonify({
        "status": "success",
        "total": pagination.total,
        "page": pagination.page,
        "per_page": pagination.per_page,
        "total_pages": pagination.pages,
        "has_next": pagination.has_next,
        "has_prev": pagination.has_prev,
        "data": [record.to_dict() for record in pagination.items]
    }), 200


# ---------------------------------------------------------------------------
# 4. GET /api/fdr/<id> - Retrieve Single FDR Record (Authenticated & Scoped)
# ---------------------------------------------------------------------------
@fdr_bp.route("/<int:fdr_id>", methods=["GET"])
@any_authenticated_user()
def get_fdr_by_id(fdr_id):
    """
    Retrieve single FDR record details by ID.
    Enforces that institution_user cannot view records of other institutions.
    """
    record = db.session.get(FDRRecord, fdr_id)
    if not record:
        return jsonify({
            "error": "Not Found",
            "message": f"FDR record with ID {fdr_id} was not found."
        }), 404

    # Enforce Institution Ownership
    if current_user.role == User.ROLE_INSTITUTION_USER:
        if record.institution_id != current_user.institution_id:
            return jsonify({
                "error": "Forbidden",
                "message": "Access denied: You do not have permission to view FDR records belonging to another institution."
            }), 403

    result = record.to_dict()
    if record.institution:
        result["institution"] = {
            "id": record.institution.id,
            "institution_code": record.institution.institution_code,
            "name": record.institution.name,
            "contact_email": record.institution.contact_email,
        }

    return jsonify({"status": "success", "data": result}), 200


# ---------------------------------------------------------------------------
# 5. PATCH /api/fdr/<id> - Update Permitted FDR Details (Authenticated & Scoped)
# ---------------------------------------------------------------------------
@fdr_bp.route("/<int:fdr_id>", methods=["PATCH"])
@any_authenticated_user()
def update_fdr(fdr_id):
    """
    Update permitted fields of an existing FDR record with strict validation.
    Enforces that institution_user can only update their own records, and cannot
    reassign an FDR to another institution.
    """
    record = db.session.get(FDRRecord, fdr_id)
    if not record:
        return jsonify({
            "error": "Not Found",
            "message": f"FDR record with ID {fdr_id} was not found."
        }), 404

    # Enforce Institution Ownership
    if current_user.role == User.ROLE_INSTITUTION_USER:
        if record.institution_id != current_user.institution_id:
            return jsonify({
                "error": "Forbidden",
                "message": "Access denied: You do not have permission to update FDR records belonging to another institution."
            }), 403

    if not request.is_json:
        return jsonify({"error": "Bad Request", "message": "Request body must be valid JSON."}), 400

    data = request.get_json()
    if not isinstance(data, dict):
        return jsonify({"error": "Bad Request", "message": "Payload must be a JSON object."}), 400

    # Reject attempts to modify primary key or protected audit metadata
    disallowed_attempt = [f for f in PROTECTED_FIELDS if f in data]
    if disallowed_attempt:
        return jsonify({
            "error": "Bad Request",
            "message": f"Fields cannot be modified: {', '.join(disallowed_attempt)}."
        }), 400

    permitted_fields = {"institution_id", "fdr_number", "issuing_bank", "deposit_amount", "issue_date", "maturity_date", "status"}
    updates_to_apply = {k: v for k, v in data.items() if k in permitted_fields}

    if not updates_to_apply:
        return jsonify({
            "error": "Bad Request",
            "message": f"No valid editable fields provided. Permitted: {', '.join(sorted(permitted_fields))}."
        }), 400

    original_snapshot = record.to_dict()

    # Validate institution_id if changing institution
    if "institution_id" in updates_to_apply:
        # institution_user is NEVER permitted to reassign an FDR to another institution
        if current_user.role == User.ROLE_INSTITUTION_USER:
            return jsonify({
                "error": "Forbidden",
                "message": "Access denied: Institution users cannot reassign an FDR record to another institution."
            }), 403

        try:
            target_inst_id = int(updates_to_apply["institution_id"])
        except (ValueError, TypeError):
            return jsonify({"error": "Validation Error", "message": "Field 'institution_id' must be an integer."}), 400

        inst = db.session.get(Institution, target_inst_id)
        if not inst:
            return jsonify({"error": "Not Found", "message": f"Institution with ID {target_inst_id} does not exist."}), 404
        record.institution_id = target_inst_id

    # Validate fdr_number uniqueness if changing
    if "fdr_number" in updates_to_apply:
        new_fdr_num = str(updates_to_apply["fdr_number"]).strip()
        if not new_fdr_num:
            return jsonify({"error": "Validation Error", "message": "Field 'fdr_number' cannot be blank."}), 400
        duplicate = FDRRecord.query.filter(
            func.upper(FDRRecord.fdr_number) == new_fdr_num.upper(),
            FDRRecord.id != record.id
        ).first()
        if duplicate:
            return jsonify({
                "error": "Conflict",
                "message": f"An FDR record with number '{new_fdr_num}' already exists (ID: {duplicate.id})."
            }), 409
        record.fdr_number = new_fdr_num

    # Validate issuing_bank if provided
    if "issuing_bank" in updates_to_apply:
        new_bank = str(updates_to_apply["issuing_bank"]).strip()
        if not new_bank:
            return jsonify({"error": "Validation Error", "message": "Field 'issuing_bank' cannot be blank."}), 400
        record.issuing_bank = new_bank

    # Validate deposit_amount if provided
    if "deposit_amount" in updates_to_apply:
        new_amount, err = parse_decimal_amount(updates_to_apply["deposit_amount"])
        if err:
            return jsonify({"error": "Validation Error", "message": err}), 400
        record.deposit_amount = new_amount

    # Validate dates and cross-date constraint
    tentative_issue = record.issue_date
    tentative_maturity = record.maturity_date

    if "issue_date" in updates_to_apply:
        parsed_issue, err = parse_iso_date(updates_to_apply["issue_date"], "issue_date")
        if err:
            return jsonify({"error": "Validation Error", "message": err}), 400
        tentative_issue = parsed_issue

    if "maturity_date" in updates_to_apply:
        parsed_maturity, err = parse_iso_date(updates_to_apply["maturity_date"], "maturity_date")
        if err:
            return jsonify({"error": "Validation Error", "message": err}), 400
        tentative_maturity = parsed_maturity

    if tentative_maturity <= tentative_issue:
        return jsonify({
            "error": "Validation Error",
            "message": "Maturity date must be strictly later than issue date."
        }), 400

    record.issue_date = tentative_issue
    record.maturity_date = tentative_maturity

    # Validate status if provided
    if "status" in updates_to_apply:
        status_val = updates_to_apply["status"]
        if not isinstance(status_val, str):
            return jsonify({"error": "Validation Error", "message": "Field 'status' must be a string."}), 400
        cleaned_status = status_val.strip().upper()
        if cleaned_status not in ALLOWED_STATUSES:
            return jsonify({
                "error": "Validation Error",
                "message": f"Invalid status '{cleaned_status}'. Allowed: {', '.join(sorted(ALLOWED_STATUSES))}."
            }), 400
        record.status = cleaned_status

    try:
        record_audit_event(
            action="FDR_UPDATED",
            entity_type="FDR_RECORD",
            entity_id=record.id,
            user=current_user,
            institution_id=record.institution_id,
            fdr_record_id=record.id,
            previous_state=original_snapshot,
            new_state=record.to_dict(),
            remarks=f"Updated fields: {', '.join(sorted(updates_to_apply.keys()))}.",
            ip_address=request.remote_addr,
        )
        db.session.commit()
        return jsonify({
            "message": "FDR record updated successfully.",
            "data": record.to_dict()
        }), 200
    except Exception:
        db.session.rollback()
        return jsonify({
            "error": "Internal Server Error",
            "message": "Database error while updating the FDR record."
        }), 500
