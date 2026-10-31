"""
Institutions Routes Module for AICTE FDR Portal.

Phase 4: Protected with JWT Authentication & RBAC:
- GET  /api/institutions        : List institutions (isolated for institution_user)
- GET  /api/institutions/<id>   : Retrieve single institution with linked FDRs (enforces isolation)
- POST /api/institutions       : Create new institution (restricted to administrators & AICTE officials)
"""

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, current_user
from models import db, Institution, User
from utils.decorators import any_authenticated_user, aicte_or_admin_required

institutions_bp = Blueprint("institutions", __name__)


@institutions_bp.route("/public", methods=["GET"])
def get_public_institutions():
    """
    Public listing of affiliated institutions for registration dropdown.
    Returns id, institution_code, and name without requiring authentication.
    """
    institutions = Institution.query.order_by(Institution.name.asc()).all()
    return jsonify({
        "status": "success",
        "total": len(institutions),
        "data": [
            {
                "id": inst.id,
                "institution_code": inst.institution_code,
                "name": inst.name,
                "contact_email": inst.contact_email,
            }
            for inst in institutions
        ]
    }), 200


@institutions_bp.route("", methods=["GET"])
@institutions_bp.route("/", methods=["GET"])
@any_authenticated_user()
def get_all_institutions():
    """
    Retrieve institutions with pagination.
    Institution users are isolated to their own institution.
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
    query = Institution.query

    # Enforce isolation: institution_user only sees their own institution
    if current_user.role == User.ROLE_INSTITUTION_USER:
        query = query.filter(Institution.id == current_user.institution_id)
    else:
        # Search filter for privileged users
        search_term = request.args.get("search")
        if search_term and search_term.strip():
            term = f"%{search_term.strip()}%"
            query = query.filter(
                (Institution.name.ilike(term)) | (Institution.institution_code.ilike(term))
            )

    query = query.order_by(Institution.id.asc())
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)

    return jsonify({
        "status": "success",
        "total": pagination.total,
        "page": pagination.page,
        "per_page": pagination.per_page,
        "total_pages": pagination.pages,
        "has_next": pagination.has_next,
        "has_prev": pagination.has_prev,
        "data": [inst.to_dict() for inst in pagination.items]
    }), 200


@institutions_bp.route("/<int:inst_id>", methods=["GET"])
@any_authenticated_user()
def get_institution_by_id(inst_id):
    """
    Retrieve a single institution by ID including its list of FDR records.
    Enforces that institution_user can only access their own institution.
    """
    if current_user.role == User.ROLE_INSTITUTION_USER:
        if inst_id != current_user.institution_id:
            return jsonify({
                "error": "Forbidden",
                "message": "Access denied: You do not have permission to view other institutions."
            }), 403

    inst = db.session.get(Institution, inst_id)
    if not inst:
        return jsonify({
            "error": "Not Found",
            "message": f"Institution with ID {inst_id} was not found."
        }), 404

    inst_data = inst.to_dict()
    # If institution_user, fdr_records are already filtered to their institution
    inst_data["fdr_records"] = [fdr.to_dict() for fdr in inst.fdr_records]

    return jsonify({
        "status": "success",
        "data": inst_data
    }), 200


@institutions_bp.route("", methods=["POST"])
@institutions_bp.route("/", methods=["POST"])
@aicte_or_admin_required()
def create_institution():
    """
    Register a new institution.
    Restricted to AICTE Officials and System Administrators.
    """
    if not request.is_json:
        return jsonify({
            "error": "Bad Request",
            "message": "Request body must be valid JSON."
        }), 400

    data = request.get_json()
    if not isinstance(data, dict):
        return jsonify({"error": "Bad Request", "message": "Payload must be a JSON object."}), 400

    required = ["institution_code", "name", "address", "contact_email"]
    missing = [f for f in required if not data.get(f) or not str(data.get(f)).strip()]
    if missing:
        return jsonify({
            "error": "Validation Error",
            "message": f"Missing required fields: {', '.join(missing)}."
        }), 400

    code = str(data["institution_code"]).strip()
    existing = Institution.query.filter_by(institution_code=code).first()
    if existing:
        return jsonify({
            "error": "Conflict",
            "message": f"Institution with code '{code}' already exists (ID: {existing.id})."
        }), 409

    inst = Institution(
        institution_code=code,
        name=str(data["name"]).strip(),
        address=str(data["address"]).strip(),
        contact_email=str(data["contact_email"]).strip(),
    )

    try:
        db.session.add(inst)
        db.session.commit()
        return jsonify({
            "message": "Institution created successfully.",
            "data": inst.to_dict()
        }), 201
    except Exception:
        db.session.rollback()
        return jsonify({
            "error": "Internal Server Error",
            "message": "A database error occurred while creating the institution."
        }), 500


@institutions_bp.route("/<int:inst_id>", methods=["PATCH"])
@aicte_or_admin_required()
def update_institution(inst_id):
    """
    Update an institution's details (name, address, contact_email).
    Restricted to AICTE Officials and Administrators.
    """
    inst = db.session.get(Institution, inst_id)
    if not inst:
        return jsonify({
            "error": "Not Found",
            "message": f"Institution with ID {inst_id} was not found."
        }), 404

    if not request.is_json:
        return jsonify({"error": "Bad Request", "message": "Request body must be valid JSON."}), 400

    data = request.get_json()
    if not isinstance(data, dict):
        return jsonify({"error": "Bad Request", "message": "Payload must be a JSON object."}), 400

    if "name" in data and str(data["name"]).strip():
        inst.name = str(data["name"]).strip()
    if "address" in data and str(data["address"]).strip():
        inst.address = str(data["address"]).strip()
    if "contact_email" in data and str(data["contact_email"]).strip():
        inst.contact_email = str(data["contact_email"]).strip()

    try:
        db.session.commit()
        return jsonify({
            "status": "success",
            "message": "Institution updated successfully.",
            "data": inst.to_dict()
        }), 200
    except Exception:
        db.session.rollback()
        return jsonify({"error": "Internal Server Error", "message": "Failed to update institution."}), 500

