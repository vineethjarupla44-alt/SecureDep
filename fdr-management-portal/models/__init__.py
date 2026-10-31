"""
Database Models Package for FDR Management Portal.

Initializes Flask-SQLAlchemy `db` and exports all application models:
- Institution
- FDRRecord
- User
- TokenBlocklist
- FDRDocument
- OCRResult
- FDRAlert (Phase 6)
- FDRRenewalRequest (Phase 6)
- FDRAuditLog (Phase 6 & 7)
- FDRReleaseRequest (Phase 7)
- FDRDuplicateCandidate (Phase 8)
- FDRRiskAssessment (Phase 8)
"""

from flask_sqlalchemy import SQLAlchemy

# Initialize the SQLAlchemy instance without binding to an app yet.
# Binding occurs inside create_app() in app.py via db.init_app(app).
db = SQLAlchemy()

# Import models to register metadata with db.Model
from models.institution import Institution
from models.fdr_record import FDRRecord
from models.user import User
from models.token_blocklist import TokenBlocklist
from models.document import FDRDocument
from models.ocr_result import OCRResult
from models.alert import FDRAlert
from models.renewal import FDRRenewalRequest
from models.audit import FDRAuditLog
from models.release import FDRReleaseRequest
from models.ai_models import FDRDuplicateCandidate, FDRRiskAssessment

__all__ = [
    "db",
    "Institution",
    "FDRRecord",
    "User",
    "TokenBlocklist",
    "FDRDocument",
    "OCRResult",
    "FDRAlert",
    "FDRRenewalRequest",
    "FDRAuditLog",
    "FDRReleaseRequest",
    "FDRDuplicateCandidate",
    "FDRRiskAssessment",
]
