"""
Routes Package for FDR Management Portal.

Defines API Blueprints for modular route management:
- GET /api/health      : Service foundation health (independent of database)
- GET /api/health/db   : Database connectivity check
- /api/auth/*          : Authentication & RBAC APIs (Phase 4)
- /api/fdr/*           : FDR Management REST APIs (Phase 3 & 4)
- /api/institutions/*  : Institution Management APIs (Phase 3 & 4)
- /api/documents/*     : Document Upload & OCR Processing (Phase 5)
- /api/maturity/*      : Maturity Tracking & Monitoring (Phase 6)
- /api/alerts/*        : In-Portal Notifications & Acknowledgment (Phase 6)
- /api/renewals/*      : Renewal & Replacement Workflows (Phase 6)
- /api/release-requests/* : Release & Refund Workflow Management (Phase 7)
- /api/audit-logs      : Advanced Audit Trail Query (Phase 7)
- /api/ai/*            : Advanced AI & Machine Learning Intelligence (Phase 8)
"""

from flask import Blueprint, jsonify
from sqlalchemy import text
from models import db
from routes.auth import auth_bp
from routes.fdr import fdr_bp
from routes.institutions import institutions_bp
from routes.documents import documents_bp
from routes.maturity import maturity_bp
from routes.alerts import alerts_bp
from routes.renewals import renewals_bp
from routes.release import release_bp
from routes.audit import audit_bp
from routes.ai import ai_bp

# Define main API blueprint with the '/api' prefix
api_bp = Blueprint("api", __name__, url_prefix="/api")

# Register modular sub-blueprints
api_bp.register_blueprint(auth_bp, url_prefix="/auth")
api_bp.register_blueprint(fdr_bp, url_prefix="/fdr")
api_bp.register_blueprint(institutions_bp, url_prefix="/institutions")
api_bp.register_blueprint(documents_bp)  # Registers /fdr/<id>/documents and /documents/<id>
api_bp.register_blueprint(maturity_bp, url_prefix="/maturity")
api_bp.register_blueprint(alerts_bp, url_prefix="/alerts")
api_bp.register_blueprint(renewals_bp)   # Registers /fdr/<id>/renew and /renewals/*
api_bp.register_blueprint(release_bp)    # Registers /release-requests and /release-requests/*
api_bp.register_blueprint(audit_bp)      # Registers /audit-logs
api_bp.register_blueprint(ai_bp, url_prefix="/ai")


@api_bp.route("/health", methods=["GET"])
def health_check():
    """
    Service health check endpoint returning system operational status.
    Kept independent of the database so application boots and reports status
    even when database is offline.

    Returns:
        JSON response with status 200 OK:
        {
            "status": "healthy",
            "service": "FDR Backend",
            "phase": "Backend Foundation"
        }
    """
    return jsonify({
        "status": "healthy",
        "service": "FDR Backend",
        "phase": "Backend Foundation"
    }), 200


@api_bp.route("/health/db", methods=["GET"])
def db_health_check():
    """
    Database connectivity health check endpoint.
    Tests active connectivity to MySQL using a lightweight 'SELECT 1' query.

    Returns:
        200 OK if database is connected.
        503 Service Unavailable if database is unreachable.
        Never reveals credentials, hostnames, or internal stack traces.
    """
    try:
        with db.engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return jsonify({
            "status": "connected",
            "database": "MySQL",
            "message": "Database connection is healthy and responsive."
        }), 200
    except Exception:
        # Intentionally sanitized: no passwords, hostnames, or internal traces exposed
        return jsonify({
            "status": "disconnected",
            "database": "MySQL",
            "message": "Database server is unreachable or offline."
        }), 503
