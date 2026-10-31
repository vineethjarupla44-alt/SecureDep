"""
Authentication and Role-Based User Management Routes for AICTE FDR Portal.

Phase 4: Authentication & RBAC
Endpoints:
- POST  /api/auth/register    : Public registration (restricted to institution_user)
- POST  /api/auth/login       : Authenticate user & issue JWT tokens
- POST  /api/auth/logout      : Revoke current JWT via database blocklist
- GET   /api/auth/me          : Retrieve current authenticated user profile
- PATCH /api/auth/me          : Update own profile (blocks role/status/institution tampering)
- POST  /api/auth/refresh     : Refresh access token using refresh token
- POST  /api/auth/admin/users : Administrator-only user provisioning for privileged roles
"""

from datetime import datetime
from flask import Blueprint, request, jsonify
from flask_jwt_extended import (
    create_access_token,
    create_refresh_token,
    jwt_required,
    get_jwt,
    get_jwt_identity,
    current_user,
)
from sqlalchemy import func
from models import db, User, Institution, TokenBlocklist, FDRAuditLog
from utils.decorators import (
    admin_required,
    validate_email_format,
    validate_password_strength,
)

auth_bp = Blueprint("auth", __name__)


# ---------------------------------------------------------------------------
# 0. GET /api/auth/institutions (Public Listing for Registration)
# ---------------------------------------------------------------------------
@auth_bp.route("/institutions", methods=["GET"])
def get_auth_institutions():
    """
    Public listing of accredited institutions for user registration selection.
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


# ---------------------------------------------------------------------------
# 1. POST /api/auth/register (Public Registration - Institution Users ONLY)
# ---------------------------------------------------------------------------
@auth_bp.route("/register", methods=["POST"])
def register():
    """
    Public registration endpoint.
    Strictly permits creating 'institution_user' accounts only.
    Privileged accounts (AICTE Official, Administrator) are blocked.
    """
    if not request.is_json:
        return jsonify({
            "error": "Bad Request",
            "message": "Request body must be valid JSON."
        }), 400

    data = request.get_json()
    if not isinstance(data, dict):
        return jsonify({"error": "Bad Request", "message": "Payload must be a JSON object."}), 400

    # 1. Security Check: Prevent privilege escalation on public registration
    requested_role = data.get("role")
    if requested_role and requested_role.strip().lower() != User.ROLE_INSTITUTION_USER:
        return jsonify({
            "error": "Forbidden",
            "message": "Public registration only permits creating 'institution_user' accounts. "
                       "Privileged accounts (AICTE Official, Administrator) must be provisioned by an Administrator."
        }), 403

    # 2. Check required fields
    required = ["email", "password", "full_name", "institution_id"]
    missing = [f for f in required if not data.get(f) or not str(data.get(f)).strip()]
    if missing:
        return jsonify({
            "error": "Validation Error",
            "message": f"Missing required fields: {', '.join(missing)}."
        }), 400

    # 3. Validate Email Format
    email_clean = str(data["email"]).strip().lower()
    valid_email, err_email = validate_email_format(email_clean)
    if not valid_email:
        return jsonify({"error": "Validation Error", "message": err_email}), 400

    # 4. Validate Password Complexity
    password_raw = str(data["password"])
    valid_pass, err_pass = validate_password_strength(password_raw)
    if not valid_pass:
        return jsonify({"error": "Validation Error", "message": err_pass}), 400

    # 5. Validate Institution Exists
    try:
        inst_id = int(data["institution_id"])
    except (ValueError, TypeError):
        return jsonify({
            "error": "Validation Error",
            "message": "Field 'institution_id' must be a valid integer."
        }), 400

    institution = db.session.get(Institution, inst_id)
    if not institution:
        return jsonify({
            "error": "Not Found",
            "message": f"Selected institution (ID: {inst_id}) does not exist in the AICTE directory. Please select a valid accredited institution from the directory."
        }), 404

    # 6. Check Duplicate Email (Normalized lowercase)
    existing_user = User.query.filter(func.lower(User.email) == email_clean).first()
    if existing_user:
        return jsonify({
            "error": "Conflict",
            "message": "An account with this email address already exists. Please sign in or use a different email."
        }), 409

    # 7. Create User with Werkzeug PBKDF2 Password Hashing with PENDING status
    user = User(
        email=email_clean,
        full_name=str(data["full_name"]).strip(),
        role=User.ROLE_INSTITUTION_USER,
        account_status=User.STATUS_PENDING,
        institution_id=institution.id,
    )
    user.set_password(password_raw)

    try:
        db.session.add(user)
        db.session.flush()

        audit = FDRAuditLog(
            action="USER_REGISTRATION_SUBMITTED",
            entity_type="user",
            entity_id=user.id,
            user_id=None,
            remarks=f"Institution registration requested by {user.full_name} ({user.email}) for institution '{institution.name}' [{institution.institution_code}]. Pending admin approval.",
        )
        db.session.add(audit)
        db.session.commit()
        return jsonify({
            "status": "success",
            "message": "Registration submitted successfully. Your institutional account is currently pending administrative approval by AICTE before portal access is activated.",
            "data": user.to_dict()
        }), 201
    except Exception:
        db.session.rollback()
        return jsonify({
            "error": "Internal Server Error",
            "message": "A database error occurred while registering user."
        }), 500


# ---------------------------------------------------------------------------
# 2. POST /api/auth/login
# ---------------------------------------------------------------------------
@auth_bp.route("/login", methods=["POST"])
def login():
    """
    Authenticate user with email and password.
    Issues JWT access and refresh tokens.
    """
    if not request.is_json:
        return jsonify({
            "error": "Bad Request",
            "message": "Request body must be valid JSON."
        }), 400

    data = request.get_json()
    email = data.get("email")
    password = data.get("password")

    if not email or not password:
        return jsonify({
            "error": "Validation Error",
            "message": "Email and password are required."
        }), 400

    email_clean = str(email).strip().lower()

    # Look up user by lowercase email
    user = User.query.filter(func.lower(User.email) == email_clean).first()

    # Generic error message: Never reveal whether email exists or password was incorrect
    if not user or not user.check_password(str(password)):
        return jsonify({
            "error": "Unauthorized",
            "message": "Invalid email or password."
        }), 401

    # Check account status
    if not user.is_active:
        if user.account_status == User.STATUS_PENDING:
            return jsonify({
                "error": "Forbidden",
                "account_status": "PENDING",
                "message": "Your institutional account registration is pending administrative approval. An AICTE administrator must verify and activate your account before you can log in."
            }), 403
        elif user.account_status == User.STATUS_REJECTED:
            return jsonify({
                "error": "Forbidden",
                "account_status": "REJECTED",
                "message": "Your institutional account registration was rejected by the administrator. Please contact AICTE support."
            }), 403
        elif user.account_status == User.STATUS_SUSPENDED:
            return jsonify({
                "error": "Forbidden",
                "account_status": "SUSPENDED",
                "message": "Your account has been suspended by AICTE administration. Please contact support."
            }), 403
        else:
            return jsonify({
                "error": "Forbidden",
                "account_status": user.account_status,
                "message": f"Account is {user.account_status.lower()}. Please contact system administration."
            }), 403

    # Generate JWT tokens
    additional_claims = {
        "role": user.role,
        "institution_id": user.institution_id,
        "email": user.email,
    }
    access_token = create_access_token(
        identity=str(user.id),
        additional_claims=additional_claims,
    )
    refresh_token = create_refresh_token(identity=str(user.id))

    return jsonify({
        "message": "Authentication successful.",
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "Bearer",
        "user": user.to_dict()
    }), 200


# ---------------------------------------------------------------------------
# 3. POST /api/auth/logout
# ---------------------------------------------------------------------------
@auth_bp.route("/logout", methods=["POST"])
@jwt_required()
def logout():
    """
    Revoke current JWT by adding its JTI to the database blocklist.
    Prevents token reuse before its natural expiration.
    """
    jwt_payload = get_jwt()
    jti = jwt_payload["jti"]
    token_type = jwt_payload.get("type", "access")
    exp_timestamp = jwt_payload.get("exp")
    expires_at = datetime.utcfromtimestamp(exp_timestamp) if exp_timestamp else datetime.utcnow()

    # Add to blocklist
    revoked_entry = TokenBlocklist(
        jti=jti,
        token_type=token_type,
        user_id=current_user.id if current_user else None,
        expires_at=expires_at,
    )

    try:
        db.session.add(revoked_entry)
        db.session.commit()
        return jsonify({
            "message": "Successfully logged out. Token has been revoked."
        }), 200
    except Exception:
        db.session.rollback()
        return jsonify({
            "error": "Internal Server Error",
            "message": "Failed to revoke token on logout."
        }), 500


# ---------------------------------------------------------------------------
# 4. GET /api/auth/me
# ---------------------------------------------------------------------------
@auth_bp.route("/me", methods=["GET"])
@jwt_required()
def get_current_user_profile():
    """
    Retrieve profile details for the currently authenticated user.
    """
    if not current_user:
        return jsonify({"error": "Unauthorized", "message": "User not found."}), 401

    return jsonify({
        "status": "success",
        "data": current_user.to_dict()
    }), 200


# ---------------------------------------------------------------------------
# 5. PATCH /api/auth/me (Profile Updates with Role Protection)
# ---------------------------------------------------------------------------
@auth_bp.route("/me", methods=["PATCH"])
@jwt_required()
def update_current_user_profile():
    """
    Update own profile details.
    Strictly forbids users from modifying their own role, account status,
    or institution assignment.
    """
    if not current_user:
        return jsonify({"error": "Unauthorized", "message": "User not found."}), 401

    if not request.is_json:
        return jsonify({"error": "Bad Request", "message": "Request body must be valid JSON."}), 400

    data = request.get_json()

    # Security check: Block tampering with role, status, institution_id, id, email
    tamper_fields = {"role", "account_status", "institution_id", "id", "email"}
    attempted_tamper = [f for f in tamper_fields if f in data]
    if attempted_tamper:
        return jsonify({
            "error": "Forbidden",
            "message": f"You do not have permission to modify protected fields: {', '.join(attempted_tamper)}."
        }), 403

    # Permitted updates
    if "full_name" in data and str(data["full_name"]).strip():
        current_user.full_name = str(data["full_name"]).strip()

    # Password change
    if "new_password" in data:
        current_pass = data.get("current_password")
        if not current_pass or not current_user.check_password(str(current_pass)):
            return jsonify({
                "error": "Unauthorized",
                "message": "Current password is incorrect or missing."
            }), 401

        valid_pass, err_pass = validate_password_strength(str(data["new_password"]))
        if not valid_pass:
            return jsonify({"error": "Validation Error", "message": err_pass}), 400

        current_user.set_password(str(data["new_password"]))

    try:
        db.session.commit()
        return jsonify({
            "message": "Profile updated successfully.",
            "data": current_user.to_dict()
        }), 200
    except Exception:
        db.session.rollback()
        return jsonify({"error": "Internal Server Error", "message": "Failed to update profile."}), 500


# ---------------------------------------------------------------------------
# 6. POST /api/auth/refresh
# ---------------------------------------------------------------------------
@auth_bp.route("/refresh", methods=["POST"])
@jwt_required(refresh=True)
def refresh_token():
    """
    Issue a new access token using a valid, unrevoked refresh token.
    """
    identity = get_jwt_identity()
    user = db.session.get(User, int(identity))
    if not user or not user.is_active:
        return jsonify({"error": "Unauthorized", "message": "User inactive or not found."}), 401

    new_access_token = create_access_token(
        identity=str(user.id),
        additional_claims={
            "role": user.role,
            "institution_id": user.institution_id,
            "email": user.email,
        }
    )
    return jsonify({
        "access_token": new_access_token,
        "token_type": "Bearer"
    }), 200


# ---------------------------------------------------------------------------
# 7. POST /api/auth/admin/users (Administrator Provisioning for Privileged Roles)
# ---------------------------------------------------------------------------
@auth_bp.route("/admin/users", methods=["POST"])
@admin_required()
def admin_provision_user():
    """
    Provision users with privileged roles (aicte_official, administrator, institution_user).
    Restricted to system administrators only.
    """
    if not request.is_json:
        return jsonify({"error": "Bad Request", "message": "Request body must be valid JSON."}), 400

    data = request.get_json()
    required = ["email", "password", "full_name", "role"]
    missing = [f for f in required if not data.get(f) or not str(data.get(f)).strip()]
    if missing:
        return jsonify({
            "error": "Validation Error",
            "message": f"Missing required fields: {', '.join(missing)}."
        }), 400

    role = str(data["role"]).strip().lower()
    if role not in User.ALLOWED_ROLES:
        return jsonify({
            "error": "Validation Error",
            "message": f"Invalid role '{role}'. Allowed roles: {', '.join(sorted(User.ALLOWED_ROLES))}."
        }), 400

    email_clean = str(data["email"]).strip().lower()
    valid_email, err_email = validate_email_format(email_clean)
    if not valid_email:
        return jsonify({"error": "Validation Error", "message": err_email}), 400

    valid_pass, err_pass = validate_password_strength(str(data["password"]))
    if not valid_pass:
        return jsonify({"error": "Validation Error", "message": err_pass}), 400

    # Role specific checks
    institution_id = None
    if role == User.ROLE_INSTITUTION_USER:
        if not data.get("institution_id"):
            return jsonify({
                "error": "Validation Error",
                "message": "Field 'institution_id' is mandatory for role 'institution_user'."
            }), 400
        inst = db.session.get(Institution, int(data["institution_id"]))
        if not inst:
            return jsonify({
                "error": "Not Found",
                "message": f"Institution with ID {data['institution_id']} does not exist."
            }), 404
        institution_id = inst.id

    # Check duplicate email
    existing_user = User.query.filter(func.lower(User.email) == email_clean).first()
    if existing_user:
        return jsonify({
            "error": "Conflict",
            "message": f"User with email '{email_clean}' already exists."
        }), 409

    account_status = data.get("account_status", User.STATUS_ACTIVE)
    if account_status not in User.ALLOWED_STATUSES:
        return jsonify({
            "error": "Validation Error",
            "message": f"Invalid account status. Allowed: {', '.join(sorted(User.ALLOWED_STATUSES))}."
        }), 400

    new_user = User(
        email=email_clean,
        full_name=str(data["full_name"]).strip(),
        role=role,
        account_status=account_status,
        institution_id=institution_id,
    )
    new_user.set_password(str(data["password"]))

    try:
        db.session.add(new_user)
        db.session.commit()
        return jsonify({
            "message": f"User provisioned successfully with role '{role}'.",
            "data": new_user.to_dict()
        }), 201
    except Exception:
        db.session.rollback()
        return jsonify({
            "error": "Internal Server Error",
            "message": "Database error while provisioning user."
        }), 500


# ---------------------------------------------------------------------------
# 8. GET /api/auth/admin/users (Administrator View Users / Registration Requests)
# ---------------------------------------------------------------------------
@auth_bp.route("/admin/users", methods=["GET"])
@admin_required()
def list_admin_users():
    """
    List registered users with filtering (status, role, institution, search).
    Restricted to system administrators.
    """
    status_filter = request.args.get("status")
    role_filter = request.args.get("role")
    inst_filter = request.args.get("institution_id")
    search = request.args.get("search")

    query = User.query

    if status_filter and status_filter.upper() in User.ALLOWED_STATUSES:
        query = query.filter(User.account_status == status_filter.upper())
    if role_filter and role_filter.lower() in User.ALLOWED_ROLES:
        query = query.filter(User.role == role_filter.lower())
    if inst_filter:
        try:
            query = query.filter(User.institution_id == int(inst_filter))
        except ValueError:
            pass
    if search and search.strip():
        term = f"%{search.strip().lower()}%"
        query = query.filter(
            (func.lower(User.email).like(term)) | (func.lower(User.full_name).like(term))
        )

    try:
        page = int(request.args.get("page", 1))
        per_page = int(request.args.get("per_page", 20))
    except (ValueError, TypeError):
        page = 1
        per_page = 20

    pagination = query.order_by(User.created_at.desc()).paginate(page=page, per_page=per_page, error_out=False)

    users_data = []
    for u in pagination.items:
        u_dict = u.to_dict()
        if u.institution:
            u_dict["institution"] = {
                "id": u.institution.id,
                "institution_code": u.institution.institution_code,
                "name": u.institution.name,
                "contact_email": u.institution.contact_email,
            }
        users_data.append(u_dict)

    return jsonify({
        "status": "success",
        "total": pagination.total,
        "page": pagination.page,
        "per_page": pagination.per_page,
        "total_pages": pagination.pages,
        "data": users_data,
    }), 200


# ---------------------------------------------------------------------------
# 9. PATCH /api/auth/admin/users/<int:user_id>/status (Approve / Reject Account)
# ---------------------------------------------------------------------------
@auth_bp.route("/admin/users/<int:user_id>/status", methods=["PATCH"])
@admin_required()
def update_user_status(user_id):
    """
    Approve, reject, or change user account status.
    Payload: {"status": "ACTIVE" | "REJECTED" | "SUSPENDED" | "PENDING", "remarks": "..."}
    """
    user = db.session.get(User, user_id)
    if not user:
        return jsonify({"error": "Not Found", "message": f"User with ID {user_id} was not found."}), 404

    if not request.is_json:
        return jsonify({"error": "Bad Request", "message": "Request body must be valid JSON."}), 400

    data = request.get_json()
    new_status = data.get("status")
    if not new_status or new_status.upper() not in User.ALLOWED_STATUSES:
        return jsonify({
            "error": "Validation Error",
            "message": f"Invalid status '{new_status}'. Allowed: {', '.join(sorted(User.ALLOWED_STATUSES))}."
        }), 400

    target_status = new_status.upper()
    old_status = user.account_status
    user.account_status = target_status
    user.updated_at = datetime.utcnow()

    # Determine action for audit log
    if target_status == User.STATUS_ACTIVE and old_status == User.STATUS_PENDING:
        action = "USER_REGISTRATION_APPROVED"
    elif target_status == User.STATUS_REJECTED:
        action = "USER_REGISTRATION_REJECTED"
    else:
        action = f"USER_STATUS_CHANGED_TO_{target_status}"

    remarks = data.get("remarks") or f"Admin updated account status of {user.email} from {old_status} to {target_status}."

    audit = FDRAuditLog(
        action=action,
        entity_type="user",
        entity_id=user.id,
        user_id=current_user.id if current_user else None,
        remarks=remarks,
    )
    db.session.add(audit)

    try:
        db.session.commit()
        return jsonify({
            "status": "success",
            "message": f"User account status updated to {target_status}.",
            "data": user.to_dict(),
        }), 200
    except Exception:
        db.session.rollback()
        return jsonify({"error": "Internal Server Error", "message": "Failed to update user status."}), 500


# ---------------------------------------------------------------------------
# 10. GET /api/auth/admin/users/<int:user_id>
# ---------------------------------------------------------------------------
@auth_bp.route("/admin/users/<int:user_id>", methods=["GET"])
@admin_required()
def get_admin_user_details(user_id):
    """
    Get detailed profile of a specific user including institution info.
    """
    user = db.session.get(User, user_id)
    if not user:
        return jsonify({"error": "Not Found", "message": f"User with ID {user_id} was not found."}), 404

    data = user.to_dict()
    if user.institution:
        data["institution"] = user.institution.to_dict()
    return jsonify({"status": "success", "data": data}), 200

