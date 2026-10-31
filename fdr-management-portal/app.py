"""
Main Application Entry Point for AICTE FDR Management Portal.

Phases 1-4:
- Application factory pattern
- Secure CORS configuration
- SQLAlchemy integration
- JWT authentication with token revocation and user lookup
- Role-based routing and standardized error responses
"""

import os
from flask import Flask, jsonify
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from config import config_by_name, ProductionConfig
from models import db, User, TokenBlocklist
from routes import api_bp

jwt = JWTManager()


def create_app(config_name=None):
    """
    Application factory pattern to configure and create the Flask application.

    Args:
        config_name (str, optional): The configuration environment name
                                     ('development', 'testing', 'production').
                                     Defaults to FLASK_ENV environment variable.

    Returns:
        Flask: The configured Flask application instance.
    """
    if config_name is None:
        config_name = os.getenv("FLASK_ENV", "development").lower()

    app = Flask(__name__)

    # Load configuration
    selected_config = config_by_name.get(config_name, config_by_name["default"])
    app.config.from_object(selected_config)

    # Validate production secrets
    if config_name == "production" and hasattr(selected_config, "validate_secrets"):
        selected_config.validate_secrets()

    # Configure CORS with development-appropriate restrictions
    allowed_origins = app.config.get("CORS_ORIGINS", ["http://localhost:3000", "http://127.0.0.1:3000"])
    CORS(
        app,
        resources={
            r"/api/*": {"origins": allowed_origins},
            r"/api/.*": {"origins": allowed_origins},
        },
        methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Content-Type", "Authorization"],
        supports_credentials=True,
    )

    # Initialize SQLAlchemy
    db.init_app(app)

    # Initialize Flask-JWT-Extended
    jwt.init_app(app)

    # JWT User Lookup: Automatically loads `current_user` object in protected routes
    @jwt.user_lookup_loader
    def user_lookup_callback(_jwt_header, jwt_data):
        identity = jwt_data.get("sub")
        try:
            user_id = int(identity)
            return db.session.get(User, user_id)
        except (ValueError, TypeError):
            return None

    # JWT Token Revocation: Checks database blocklist for revoked tokens
    @jwt.token_in_blocklist_loader
    def check_if_token_revoked(_jwt_header, jwt_payload):
        jti = jwt_payload.get("jti")
        token = db.session.query(TokenBlocklist.id).filter_by(jti=jti).scalar()
        return token is not None

    # Custom JWT Error Handlers
    @jwt.expired_token_loader
    def expired_token_callback(jwt_header, jwt_payload):
        return jsonify({
            "error": "Unauthorized",
            "message": "Token has expired. Please log in again."
        }), 401

    @jwt.invalid_token_loader
    def invalid_token_callback(error_string):
        return jsonify({
            "error": "Unauthorized",
            "message": "Signature verification failed or token is malformed."
        }), 401

    @jwt.unauthorized_loader
    def missing_token_callback(error_string):
        return jsonify({
            "error": "Unauthorized",
            "message": "Missing Authorization header with valid Bearer token."
        }), 401

    @jwt.revoked_token_loader
    def revoked_token_callback(jwt_header, jwt_payload):
        return jsonify({
            "error": "Unauthorized",
            "message": "Token has been revoked. Please log in again."
        }), 401

    # Register API blueprints
    app.register_blueprint(api_bp)

    # Root endpoint for basic discovery
    @app.route("/", methods=["GET"])
    def root_info():
        return jsonify({
            "service": "AICTE FDR Management Portal API",
            "phase": "Phase 8 - Advanced AI & Machine Learning Intelligence",
            "endpoints": {
                "health": "/api/health",
                "db_health": "/api/health/db",
                "auth": {
                    "login": "/api/auth/login",
                    "register": "/api/auth/register",
                    "logout": "/api/auth/logout",
                    "me": "/api/auth/me",
                    "refresh": "/api/auth/refresh",
                    "admin_provision_user": "/api/auth/admin/users"
                },
                "fdr_list_create": "/api/fdr",
                "fdr_search": "/api/fdr/search",
                "institutions": "/api/institutions",
                "documents": {
                    "upload": "/api/fdr/<id>/documents",
                    "list": "/api/fdr/<id>/documents",
                    "details": "/api/documents/<id>",
                    "download": "/api/documents/<id>/download",
                    "process_ocr": "/api/documents/<id>/process-ocr",
                    "review": "/api/documents/<id>/review"
                },
                "maturity": {
                    "summary": "/api/maturity/summary",
                    "expiring": "/api/maturity/expiring",
                    "pending_renewals": "/api/maturity/pending-renewals",
                    "trigger_scan": "/api/maturity/trigger-scan"
                },
                "alerts": {
                    "list": "/api/alerts",
                    "acknowledge": "/api/alerts/<id>/acknowledge"
                },
                "renewals": {
                    "submit": "/api/fdr/<id>/renew",
                    "list": "/api/renewals",
                    "details": "/api/renewals/<id>",
                    "review": "/api/renewals/<id>/review"
                },
                "release_requests": {
                    "submit": "/api/release-requests",
                    "list": "/api/release-requests",
                    "details": "/api/release-requests/<id>",
                    "update_resubmit": "/api/release-requests/<id>",
                    "scrutiny": "/api/release-requests/<id>/scrutiny",
                    "approval": "/api/release-requests/<id>/approval",
                    "close": "/api/release-requests/<id>/close",
                    "trigger_overdue_scan": "/api/release-requests/trigger-overdue-scan"
                },
                "audit_logs": "/api/audit-logs",
                "ai": {
                    "duplicate_scan": "/api/ai/duplicates/scan",
                    "duplicate_list": "/api/ai/duplicates",
                    "duplicate_review": "/api/ai/duplicates/<id>",
                    "anomalies": "/api/ai/anomalies",
                    "risk_score": "/api/ai/risk-score/<fdr_id>",
                    "batch_risk_score": "/api/ai/risk-score/batch",
                    "compliance_profile": "/api/ai/compliance/<institution_id>",
                    "compliance_summary": "/api/ai/compliance/summary",
                    "dossier_report": "/api/ai/report/<fdr_id>",
                    "model_health": "/api/ai/models/health",
                    "model_train": "/api/ai/models/train"
                }
            }
        }), 200

    # Security response headers
    @app.after_request
    def apply_security_headers(response):
        """Inject OWASP standard defensive security headers."""
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        return response

    # JSON Error Handlers for consistent API responses
    @app.errorhandler(404)
    def not_found_error(error):
        return jsonify({
            "error": "Not Found",
            "message": "The requested resource was not found on this server."
        }), 404

    @app.errorhandler(405)
    def method_not_allowed_error(error):
        return jsonify({
            "error": "Method Not Allowed",
            "message": "The method is not allowed for the requested URL."
        }), 405

    @app.errorhandler(500)
    def internal_error(error):
        return jsonify({
            "error": "Internal Server Error",
            "message": "An unexpected error occurred on the server."
        }), 500

    return app


# Create instance for WSGI runners or local execution
app = create_app()


if __name__ == "__main__":
    host = app.config.get("HOST", "127.0.0.1")
    port = app.config.get("PORT", 5000)
    debug = app.config.get("DEBUG", True)
    
    print(f"[*] Starting FDR Management Portal on http://{host}:{port}")
    print(f"[*] Health Check URL: http://{host}:{port}/api/health")
    app.run(host=host, port=port, debug=debug)
