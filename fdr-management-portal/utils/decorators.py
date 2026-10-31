"""
Security Decorators and RBAC Helpers for AICTE FDR Portal.

Provides:
- role_required(*roles): Enforces role-based permissions
- admin_required: Enforces administrator role
- aicte_or_admin_required: Allows AICTE officials and administrators
- validate_password_strength: Validates password complexity
- validate_email_format: Validates email syntax
"""

import re
from functools import wraps
from flask import jsonify
from flask_jwt_extended import jwt_required, current_user


def role_required(*allowed_roles):
    """
    Decorator to protect routes with JWT authentication and Role-Based Access Control.

    Ensures:
    1. User presents a valid, unrevoked JWT.
    2. User account exists in database and is ACTIVE.
    3. User has one of the specified allowed roles.
    """
    def wrapper(fn):
        @wraps(fn)
        @jwt_required()
        def decorator(*args, **kwargs):
            if not current_user:
                return jsonify({
                    "error": "Unauthorized",
                    "message": "User not found or token identity invalid."
                }), 401

            if not current_user.is_active:
                return jsonify({
                    "error": "Forbidden",
                    "message": f"Account is {current_user.account_status.lower()}. Access denied."
                }), 403

            if current_user.role not in allowed_roles:
                return jsonify({
                    "error": "Forbidden",
                    "message": f"Access denied. Requires one of the following roles: {', '.join(allowed_roles)}."
                }), 403

            return fn(*args, **kwargs)
        return decorator
    return wrapper


def admin_required():
    """Decorator requiring the 'administrator' role."""
    return role_required("administrator")


def aicte_or_admin_required():
    """Decorator requiring either 'aicte_official' or 'administrator' role."""
    return role_required("aicte_official", "administrator")


def any_authenticated_user():
    """Decorator requiring any valid active authenticated user."""
    return role_required("institution_user", "aicte_official", "administrator")


def institution_user_or_admin_required():
    """Decorator for institution submissions and administrator operations."""
    return role_required("institution_user", "administrator")


def validate_password_strength(password):
    """
    Validate password complexity:
    - Minimum 8 characters
    - Must contain at least one digit and one alphabet letter
    Returns (True, None) or (False, error_message).
    """
    if not isinstance(password, str):
        return False, "Password must be a string."
    if len(password) < 8:
        return False, "Password must be at least 8 characters long."
    if not re.search(r"[A-Za-z]", password):
        return False, "Password must contain at least one letter."
    if not re.search(r"\d", password):
        return False, "Password must contain at least one digit."
    return True, None


def validate_email_format(email):
    """
    Validate email address format.
    Returns (True, None) or (False, error_message).
    """
    if not isinstance(email, str):
        return False, "Email must be a string."
    email = email.strip()
    pattern = r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"
    if not re.match(pattern, email):
        return False, "Invalid email address format."
    return True, None
