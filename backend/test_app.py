"""
Comprehensive Master Test Suite for AICTE FDR Management Portal.

Phases 1-5 Test Coverage:
- Phase 1: Health checks & error handling
- Phase 2: MySQL models & schema persistence
- Phase 3: FDR management APIs with pagination
- Phase 4: Authentication, Werkzeug password hashing, JWT revocation, RBAC
- Phase 5: Secure Document Management & OCR:
  - Valid PDF, PNG, JPG uploads with signature & size validation
  - Extension spoofing & oversized file rejection
  - Multi-tenant cross-institution document isolation
  - Secure streaming download without path leakage
  - OCR field extraction & date/amount normalization
  - Discrepancy detection (amount, bank, dates, numbers, unreadable fields)
  - Reviewer-only actions & audit trails (AICTE/Admin only)
- Phase 6: Maturity Tracking, Renewal Monitoring and Alerts:
  - Maturity calculations (Active, Expiring Soon 30d/15d/7d, Matured, Overdue, Renewed, Released)
  - Tenant-isolated maturity summaries and metrics
  - Repeatable, idempotent background alert scanning
  - In-portal alert listing and single-action acknowledgment
  - End-to-end FDR renewal proposal submission with predecessor-successor linking
  - AICTE Official renewal review approval/rejection with lifecycle transitions and audit logging
- Phase 7: Release/Refund Workflow and Advanced Audit Trail:
  - Release/refund request submission with unique request number and defaults
  - Strict multi-tenant isolation across submission, listing, and direct retrieval
  - Eligibility validation (released/renewed instruments blocked) & concurrent duplicate prevention
  - Request updates and resubmission transitions from CORRECTION_REQUIRED
  - Multi-level official scrutiny state machine (start review, request correction, recommend, reject)
  - Multi-level final approval with self-approval prevention (conflict of interest)
  - Settlement closure with FDR status transition to RELEASED & financial disclaimer audit
  - Advanced immutable audit trail query endpoint with entity filters & tenant scoping
  - Overdue escalation scan with deterministic idempotency
- Phase 8: Advanced AI & Machine Learning Intelligence:
  - Exact, normalized, and fuzzy Levenshtein duplicate FDR detection
  - Cross-institution bank reference detection and cryptographic document SHA-256 hash collision
  - Explainable Isolation Forest anomaly detection with statistical Z-score/IQR attribution fallback
  - Explainable multi-factor composite risk scoring (0-100) across 4 categories (LOW, MEDIUM, HIGH, CRITICAL)
  - Institutional predictive compliance intelligence profiling and regulatory grading (A, B, C, D)
  - Model registry versioning (v1.0.0), health status, and metadata tracking
  - Duplicate candidate official review lifecycle with audit logging
  - Multi-tenant isolation across anomaly detection, risk evaluation, compliance profiles, and 360-degree dossiers
  - Admin-only synthetic benchmark model retraining
"""

import os
import io
import sys
import shutil
import tempfile
import unittest
from datetime import datetime, timedelta, date
from decimal import Decimal
from pathlib import Path
from PIL import Image

# Ensure backend directory is on sys.path
PROJECT_DIR = Path(__file__).resolve().parent
if str(PROJECT_DIR) not in sys.path:
    sys.path.insert(0, str(PROJECT_DIR))

from flask_jwt_extended import create_access_token
from app import create_app
from models import (
    db,
    Institution,
    FDRRecord,
    User,
    TokenBlocklist,
    FDRDocument,
    OCRResult,
    FDRAlert,
    FDRRenewalRequest,
    FDRAuditLog,
    FDRReleaseRequest,
    FDRDuplicateCandidate,
    FDRRiskAssessment,
)
from ml.duplicate_detector import (
    evaluate_fdr_pair_similarity,
    detect_document_hash_duplicates,
    run_full_duplicate_scan,
)
from ml.anomaly_detector import FDRAnomalyDetector
from ml.risk_scorer import calculate_fdr_risk
from ml.compliance_intelligence import analyze_institution_compliance
from ml.model_registry import get_model_health_status, save_trained_model, load_registered_model
from ml.trainer import generate_synthetic_benchmark_dataset, train_and_register_isolation_forest
from services.ocr_service import (
    extract_fields_from_text,
    compare_extracted_with_fdr,
    check_tesseract_availability,
)
from services.maturity_service import (
    calculate_fdr_maturity_metrics,
    get_maturity_summary,
    get_expiring_fdrs,
)
from services.alert_service import scan_and_generate_maturity_alerts
from utils.time import local_business_date


class FDRMasterSecurityAndDocumentTestCase(unittest.TestCase):
    """Isolated unit and integration test suite using SQLite in-memory."""

    def setUp(self):
        """Set up test application, in-memory tables, and test fixtures."""
        self.app = create_app("testing")
        self.client = self.app.test_client()
        self.app_context = self.app.app_context()
        self.app_context.push()

        # Create isolated temporary directory for document uploads
        self.test_upload_dir = tempfile.mkdtemp()
        self.app.config["DOCUMENTS_UPLOAD_FOLDER"] = self.test_upload_dir

        # Create all tables in memory
        db.create_all()

        # Seed educational institutions
        self.inst1 = Institution(
            institution_code="1-DIT-1001",
            name="Delhi Institute of Technology",
            address="1 AICTE Institutional Area, Vasant Kunj, New Delhi 110070",
            contact_email="principal@dit.edu.in",
        )
        self.inst2 = Institution(
            institution_code="1-MIT-2002",
            name="Mumbai Institute of Technology",
            address="45 Marine Drive, Nariman Point, Mumbai 400021",
            contact_email="principal@mit.edu.in",
        )
        db.session.add_all([self.inst1, self.inst2])
        db.session.commit()

        # Seed FDR Records for each institution
        self.fdr1 = FDRRecord(
            institution_id=self.inst1.id,
            fdr_number="FDR-SBI-2026-9001",
            issuing_bank="State Bank of India",
            deposit_amount=Decimal("2500000.00"),
            issue_date=date(2026, 1, 15),
            maturity_date=date(2031, 1, 15),
            status="ACTIVE",
        )
        self.fdr2 = FDRRecord(
            institution_id=self.inst2.id,
            fdr_number="FDR-HDFC-2026-8002",
            issuing_bank="HDFC Bank",
            deposit_amount=Decimal("1500000.00"),
            issue_date=date(2026, 2, 1),
            maturity_date=date(2031, 2, 1),
            status="ACTIVE",
        )
        db.session.add_all([self.fdr1, self.fdr2])
        db.session.commit()

        # Seed test users
        self.admin = User(
            email="admin@aicte-india.org",
            full_name="AICTE Central Admin",
            role=User.ROLE_ADMINISTRATOR,
            account_status=User.STATUS_ACTIVE,
            institution_id=None,
        )
        self.admin.set_password("AdminSecure2026!")

        self.official = User(
            email="regulator@aicte-india.org",
            full_name="AICTE Chief Regulator",
            role=User.ROLE_AICTE_OFFICIAL,
            account_status=User.STATUS_ACTIVE,
            institution_id=None,
        )
        self.official.set_password("OfficialSecure2026!")

        self.inst1_user = User(
            email="officer@dit.edu.in",
            full_name="DIT Finance Officer",
            role=User.ROLE_INSTITUTION_USER,
            account_status=User.STATUS_ACTIVE,
            institution_id=self.inst1.id,
        )
        self.inst1_user.set_password("DITSecret2026!")

        self.inst2_user = User(
            email="officer@mit.edu.in",
            full_name="MIT Finance Officer",
            role=User.ROLE_INSTITUTION_USER,
            account_status=User.STATUS_ACTIVE,
            institution_id=self.inst2.id,
        )
        self.inst2_user.set_password("MITSecret2026!")

        db.session.add_all([self.admin, self.official, self.inst1_user, self.inst2_user])
        db.session.commit()

        # Generate tokens
        self.admin_token = self.generate_token(self.admin)
        self.official_token = self.generate_token(self.official)
        self.inst1_token = self.generate_token(self.inst1_user)
        self.inst2_token = self.generate_token(self.inst2_user)

    def tearDown(self):
        """Clean up in-memory database and test upload directory."""
        db.session.remove()
        db.drop_all()
        self.app_context.pop()
        if os.path.exists(self.test_upload_dir):
            shutil.rmtree(self.test_upload_dir, ignore_errors=True)

    def generate_token(self, user):
        """Helper to create an access token with claims."""
        return create_access_token(
            identity=str(user.id),
            additional_claims={
                "role": user.role,
                "institution_id": user.institution_id,
                "email": user.email,
            },
        )

    def auth_header(self, token):
        """Helper to build authorization header."""
        return {"Authorization": f"Bearer {token}"}

    def create_dummy_png(self):
        """Create a valid in-memory PNG byte stream."""
        img = Image.new("RGB", (80, 80), color="white")
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        buf.seek(0)
        return buf

    def create_dummy_jpg(self):
        """Create a valid in-memory JPEG byte stream."""
        img = Image.new("RGB", (80, 80), color="white")
        buf = io.BytesIO()
        img.save(buf, format="JPEG")
        buf.seek(0)
        return buf

    def create_dummy_pdf(self, content_text=""):
        """Create a valid minimal PDF byte stream."""
        pdf_bytes = (
            b"%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
            b"2 0 obj<</Type/Pages/Count 1/Kids[3 0 R]>>endobj\n"
            b"3 0 obj<</Type/Page/MediaBox[0 0 612 792]/Parent 2 0 R/Resources<<>>/Contents 4 0 R>>endobj\n"
            b"4 0 obj<</Length 80>>stream\n"
            b"BT /F1 12 Tf 72 712 Td (AICTE Security Deposit Receipt) Tj ET\n"
            b"endstream\nendobj\nxref\n0 5\n0000000000 65535 f \n0000000009 00000 n \n0000000052 00000 n \n0000000101 00000 n \n0000000199 00000 n \ntrailer<</Size 5/Root 1 0 R>>\nstartxref\n330\n%%EOF"
        )
        return io.BytesIO(pdf_bytes)

    # =========================================================================
    # Phase 1 & 2 Preserved Tests
    # =========================================================================

    def test_health_check_status_code(self):
        """Verify public GET /api/health returns HTTP 200 OK without token."""
        response = self.client.get("/api/health")
        self.assertEqual(response.status_code, 200)

    def test_db_health_endpoint_connected(self):
        """Verify public GET /api/health/db reports connected status."""
        response = self.client.get("/api/health/db")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["status"], "connected")

    # =========================================================================
    # Phase 4 Auth & RBAC Preserved Tests
    # =========================================================================

    def test_login_success(self):
        """Verify login returns valid JWT token."""
        response = self.client.post("/api/auth/login", json={
            "email": "admin@aicte-india.org",
            "password": "AdminSecure2026!"
        })
        self.assertEqual(response.status_code, 200)
        self.assertIn("access_token", response.get_json())

    def test_public_registration_blocks_privileged_role(self):
        """Verify public registration blocks assigning administrator role."""
        response = self.client.post("/api/auth/register", json={
            "email": "fakeadmin@test.com",
            "password": "Password123!",
            "full_name": "Fake Admin",
            "institution_id": self.inst1.id,
            "role": "administrator"
        })
        self.assertEqual(response.status_code, 403)

    # =========================================================================
    # Phase 5: Secure Document Upload Tests
    # =========================================================================

    def test_upload_valid_pdf_success(self):
        """Verify uploading a valid PDF document succeeds and saves metadata."""
        pdf_file = self.create_dummy_pdf()
        data = {"file": (pdf_file, "receipt.pdf", "application/pdf")}
        headers = self.auth_header(self.inst1_token)

        response = self.client.post(
            f"/api/fdr/{self.fdr1.id}/documents",
            headers=headers,
            data=data,
            content_type="multipart/form-data"
        )
        self.assertEqual(response.status_code, 201)
        resp_json = response.get_json()
        doc_data = resp_json["data"]
        self.assertEqual(doc_data["original_filename"], "receipt.pdf")
        self.assertEqual(doc_data["content_type"], "application/pdf")
        self.assertTrue(doc_data["storage_key"].endswith(".pdf"))
        self.assertNotIn("c:", doc_data.get("file_path", "").lower())  # Never leak absolute server path

        # Verify record in database
        doc = db.session.get(FDRDocument, doc_data["id"])
        self.assertIsNotNone(doc)
        self.assertTrue(os.path.exists(doc.file_path))

    def test_upload_valid_png_and_jpg_success(self):
        """Verify uploading valid PNG and JPEG images succeeds."""
        headers = self.auth_header(self.inst1_token)

        # 1. PNG Upload
        png_file = self.create_dummy_png()
        data_png = {"file": (png_file, "fdr_scan.png", "image/png")}
        res_png = self.client.post(
            f"/api/fdr/{self.fdr1.id}/documents",
            headers=headers,
            data=data_png,
            content_type="multipart/form-data"
        )
        self.assertEqual(res_png.status_code, 201)

        # 2. JPG Upload
        jpg_file = self.create_dummy_jpg()
        data_jpg = {"file": (jpg_file, "certificate.jpg", "image/jpeg")}
        res_jpg = self.client.post(
            f"/api/fdr/{self.fdr1.id}/documents",
            headers=headers,
            data=data_jpg,
            content_type="multipart/form-data"
        )
        self.assertEqual(res_jpg.status_code, 201)

    def test_upload_invalid_extension_rejected(self):
        """Verify uploading disallowed file types (.exe, .txt) returns 400."""
        headers = self.auth_header(self.inst1_token)
        fake_file = io.BytesIO(b"echo malicious payload")
        data = {"file": (fake_file, "script.exe", "application/octet-stream")}

        response = self.client.post(
            f"/api/fdr/{self.fdr1.id}/documents",
            headers=headers,
            data=data,
            content_type="multipart/form-data"
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("Invalid file extension", response.get_json()["message"])

    def test_upload_spoofed_file_signature_rejected(self):
        """Verify extension spoofing (e.g. text file renamed to .pdf) is rejected."""
        headers = self.auth_header(self.inst1_token)
        spoofed_file = io.BytesIO(b"This is just plain text, not a PDF header.")
        data = {"file": (spoofed_file, "malicious.pdf", "application/pdf")}

        response = self.client.post(
            f"/api/fdr/{self.fdr1.id}/documents",
            headers=headers,
            data=data,
            content_type="multipart/form-data"
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("Invalid file signature", response.get_json()["message"])

    def test_upload_cross_institution_isolation(self):
        """Verify institution_user cannot upload documents to another institution's FDR."""
        headers = self.auth_header(self.inst1_token)  # DIT user
        pdf_file = self.create_dummy_pdf()
        data = {"file": (pdf_file, "intruder.pdf", "application/pdf")}

        # Attempt to upload to FDR 2 (owned by MIT)
        response = self.client.post(
            f"/api/fdr/{self.fdr2.id}/documents",
            headers=headers,
            data=data,
            content_type="multipart/form-data"
        )
        self.assertEqual(response.status_code, 403)
        self.assertIn("another institution", response.get_json()["message"])

    # =========================================================================
    # Phase 5: Document Listing, Retrieval & Streaming Download Tests
    # =========================================================================

    def test_list_and_download_document_with_authorization(self):
        """Verify document listing and secure streaming download with RBAC."""
        # 1. Upload document as DIT user
        pdf_file = self.create_dummy_pdf()
        data = {"file": (pdf_file, "audit_receipt.pdf", "application/pdf")}
        headers_dit = self.auth_header(self.inst1_token)
        res_up = self.client.post(
            f"/api/fdr/{self.fdr1.id}/documents",
            headers=headers_dit,
            data=data,
            content_type="multipart/form-data"
        )
        doc_id = res_up.get_json()["data"]["id"]

        # 2. DIT user lists documents -> 200
        res_list = self.client.get(f"/api/fdr/{self.fdr1.id}/documents", headers=headers_dit)
        self.assertEqual(res_list.status_code, 200)
        self.assertEqual(res_list.get_json()["total_documents"], 1)

        # 3. DIT user downloads document -> 200 stream
        res_dl = self.client.get(f"/api/documents/{doc_id}/download", headers=headers_dit)
        self.assertEqual(res_dl.status_code, 200)
        self.assertEqual(res_dl.mimetype, "application/pdf")

        # 4. MIT user attempts to download DIT's document -> 403 Forbidden
        headers_mit = self.auth_header(self.inst2_token)
        res_unauth = self.client.get(f"/api/documents/{doc_id}/download", headers=headers_mit)
        self.assertEqual(res_unauth.status_code, 403)

        # 5. Anonymous caller attempts download -> 401 Unauthorized
        res_anon = self.client.get(f"/api/documents/{doc_id}/download")
        self.assertEqual(res_anon.status_code, 401)

    # =========================================================================
    # Phase 5: OCR Field Extraction & Discrepancy Detection Tests
    # =========================================================================

    def test_ocr_field_extraction_heuristics(self):
        """Verify heuristic regex extraction of FDR fields from fictional certificate text."""
        fictional_ocr_text = (
            "STATE BANK OF INDIA\n"
            "PARLIAMENT STREET BRANCH, NEW DELHI\n"
            "FIXED DEPOSIT RECEIPT\n"
            "FDR Number: FDR-SBI-2026-9001\n"
            "Account In Favor of: Delhi Institute of Technology\n"
            "Deposit Amount: INR 2,500,000.00\n"
            "Date of Issue: 15/01/2026\n"
            "Maturity Date: 15/01/2031\n"
            "Interest Rate: 7.25% p.a.\n"
        )
        fields = extract_fields_from_text(fictional_ocr_text)

        self.assertEqual(fields["fdr_number"], "FDR-SBI-2026-9001")
        self.assertEqual(fields["issuing_bank"], "State Bank of India")
        self.assertEqual(fields["deposit_amount"], Decimal("2500000.00"))
        self.assertEqual(fields["issue_date"], date(2026, 1, 15))
        self.assertEqual(fields["maturity_date"], date(2031, 1, 15))
        self.assertIn("Delhi Institute of Technology", fields["institution_name"])
        self.assertEqual(fields["confidence_level"], "HIGH")

    def test_discrepancy_detection_perfect_match(self):
        """Verify discrepancy detection flags no mismatches when extracted data matches FDRRecord."""
        matching_fields = {
            "fdr_number": "FDR-SBI-2026-9001",
            "issuing_bank": "State Bank of India",
            "deposit_amount": Decimal("2500000.00"),
            "issue_date": date(2026, 1, 15),
            "maturity_date": date(2031, 1, 15),
            "institution_name": "Delhi Institute of Technology",
        }
        has_disc, count, details = compare_extracted_with_fdr(matching_fields, self.fdr1)

        self.assertFalse(has_disc)
        self.assertEqual(count, 0)
        self.assertEqual(details["deposit_amount"]["status"], "MATCH")
        self.assertEqual(details["fdr_number"]["status"], "MATCH")

    def test_discrepancy_detection_amount_and_date_mismatch(self):
        """Verify discrepancy detection flags amount and date discrepancies."""
        mismatched_fields = {
            "fdr_number": "FDR-SBI-2026-9001",
            "issuing_bank": "State Bank of India",
            "deposit_amount": Decimal("2000000.00"),  # Record is 25,00,000.00 (5 Lakhs difference!)
            "issue_date": date(2026, 1, 15),
            "maturity_date": date(2028, 1, 15),       # Record maturity is 2031 (Mismatch!)
            "institution_name": "Delhi Institute of Technology",
        }
        has_disc, count, details = compare_extracted_with_fdr(mismatched_fields, self.fdr1)

        self.assertTrue(has_disc)
        self.assertGreaterEqual(count, 2)
        self.assertEqual(details["deposit_amount"]["status"], "MISMATCH")
        self.assertEqual(details["deposit_amount"]["difference"], 500000.0)
        self.assertEqual(details["maturity_date"]["status"], "MISMATCH")

    def test_discrepancy_detection_unreadable_fields(self):
        """Verify unreadable or missing fields are flagged as UNREADABLE."""
        unreadable_fields = {
            "fdr_number": None,
            "issuing_bank": None,
            "deposit_amount": None,
            "issue_date": None,
            "maturity_date": None,
            "institution_name": None,
        }
        has_disc, count, details = compare_extracted_with_fdr(unreadable_fields, self.fdr1)

        self.assertTrue(has_disc)
        self.assertEqual(details["fdr_number"]["status"], "UNREADABLE")
        self.assertEqual(details["deposit_amount"]["status"], "UNREADABLE")

    # =========================================================================
    # Phase 5: Reviewer Authorization & Audit Tests
    # =========================================================================

    def test_reviewer_decision_audit(self):
        """Verify authorized reviewers (AICTE/Admin) can record review decisions, and regular users are blocked."""
        # 1. Upload document and simulate OCR result
        pdf_file = self.create_dummy_pdf()
        headers_dit = self.auth_header(self.inst1_token)
        res_up = self.client.post(
            f"/api/fdr/{self.fdr1.id}/documents",
            headers=headers_dit,
            data={"file": (pdf_file, "fdr_review.pdf", "application/pdf")},
            content_type="multipart/form-data"
        )
        doc_id = res_up.get_json()["data"]["id"]

        # 2. Institution user attempts to approve their own document -> 403 Forbidden
        res_unauth = self.client.post(
            f"/api/documents/{doc_id}/review",
            headers=headers_dit,
            json={"decision": "ACCEPTED", "notes": "I approve my own document"}
        )
        self.assertEqual(res_unauth.status_code, 403)

        # 3. AICTE Official reviews and accepts document -> 200 OK
        headers_official = self.auth_header(self.official_token)
        res_rev = self.client.post(
            f"/api/documents/{doc_id}/review",
            headers=headers_official,
            json={"decision": "ACCEPTED", "notes": "Verified against bank confirmation."}
        )
        self.assertEqual(res_rev.status_code, 200)
        rev_data = res_rev.get_json()["data"]["review_audit"]
        self.assertEqual(rev_data["review_decision"], "ACCEPTED")
        self.assertEqual(rev_data["reviewer_email"], "regulator@aicte-india.org")
        self.assertIsNotNone(rev_data["reviewed_at"])

    # =========================================================================
    # Phase 6: Maturity Tracking, Calculation & Summary Tests
    # =========================================================================

    def test_maturity_calculation_metrics(self):
        """Verify days remaining and tiered categories are computed accurately."""
        ref_today = date(2026, 6, 1)

        # 1. Active FDR (> 30 days remaining)
        fdr_active = FDRRecord(
            institution_id=self.inst1.id,
            fdr_number="FDR-ACT-001",
            issuing_bank="SBI",
            deposit_amount=Decimal("1000000.00"),
            issue_date=date(2025, 6, 1),
            maturity_date=date(2026, 8, 1),  # 61 days
            status="ACTIVE",
        )
        metrics_active = calculate_fdr_maturity_metrics(fdr_active, reference_date=ref_today)
        self.assertEqual(metrics_active["category"], "ACTIVE")
        self.assertEqual(metrics_active["days_remaining"], 61)
        self.assertEqual(metrics_active["urgency"], "NORMAL")

        # 2. Expiring Soon (20 days remaining -> ATTENTION_30D)
        fdr_exp30 = FDRRecord(
            institution_id=self.inst1.id,
            fdr_number="FDR-EXP-030",
            issuing_bank="SBI",
            deposit_amount=Decimal("1000000.00"),
            issue_date=date(2025, 6, 1),
            maturity_date=date(2026, 6, 21),  # 20 days
            status="ACTIVE",
        )
        metrics_exp30 = calculate_fdr_maturity_metrics(fdr_exp30, reference_date=ref_today)
        self.assertEqual(metrics_exp30["category"], "EXPIRING_SOON")
        self.assertEqual(metrics_exp30["days_remaining"], 20)
        self.assertEqual(metrics_exp30["urgency"], "ATTENTION_30D")

        # 3. Expiring Soon (10 days remaining -> WARNING_15D)
        fdr_exp15 = FDRRecord(
            institution_id=self.inst1.id,
            fdr_number="FDR-EXP-015",
            issuing_bank="SBI",
            deposit_amount=Decimal("1000000.00"),
            issue_date=date(2025, 6, 1),
            maturity_date=date(2026, 6, 11),  # 10 days
            status="ACTIVE",
        )
        metrics_exp15 = calculate_fdr_maturity_metrics(fdr_exp15, reference_date=ref_today)
        self.assertEqual(metrics_exp15["category"], "EXPIRING_SOON")
        self.assertEqual(metrics_exp15["days_remaining"], 10)
        self.assertEqual(metrics_exp15["urgency"], "WARNING_15D")

        # 4. Expiring Soon (5 days remaining -> CRITICAL_7D)
        fdr_exp7 = FDRRecord(
            institution_id=self.inst1.id,
            fdr_number="FDR-EXP-007",
            issuing_bank="SBI",
            deposit_amount=Decimal("1000000.00"),
            issue_date=date(2025, 6, 1),
            maturity_date=date(2026, 6, 6),  # 5 days
            status="ACTIVE",
        )
        metrics_exp7 = calculate_fdr_maturity_metrics(fdr_exp7, reference_date=ref_today)
        self.assertEqual(metrics_exp7["category"], "EXPIRING_SOON")
        self.assertEqual(metrics_exp7["days_remaining"], 5)
        self.assertEqual(metrics_exp7["urgency"], "CRITICAL_7D")

        # 5. Matured (0 days remaining)
        fdr_mat0 = FDRRecord(
            institution_id=self.inst1.id,
            fdr_number="FDR-MAT-000",
            issuing_bank="SBI",
            deposit_amount=Decimal("1000000.00"),
            issue_date=date(2025, 6, 1),
            maturity_date=date(2026, 6, 1),  # 0 days
            status="ACTIVE",
        )
        metrics_mat0 = calculate_fdr_maturity_metrics(fdr_mat0, reference_date=ref_today)
        self.assertEqual(metrics_mat0["category"], "MATURED")
        self.assertEqual(metrics_mat0["days_remaining"], 0)
        self.assertEqual(metrics_mat0["urgency"], "CRITICAL_MATURED")

        # 6. Renewed status instrument is classified as RENEWED regardless of dates
        fdr_renewed = FDRRecord(
            institution_id=self.inst1.id,
            fdr_number="FDR-REN-001",
            issuing_bank="SBI",
            deposit_amount=Decimal("1000000.00"),
            issue_date=date(2024, 1, 1),
            maturity_date=date(2025, 1, 1),
            status="RENEWED",
        )
        metrics_renewed = calculate_fdr_maturity_metrics(fdr_renewed, reference_date=ref_today)
        self.assertEqual(metrics_renewed["category"], "RENEWED")
        self.assertEqual(metrics_renewed["urgency"], "NONE")

        # 7. Workflow status renewal submitted -> RENEWAL_PENDING
        fdr_pending = FDRRecord(
            institution_id=self.inst1.id,
            fdr_number="FDR-PEN-001",
            issuing_bank="SBI",
            deposit_amount=Decimal("1000000.00"),
            issue_date=date(2025, 1, 1),
            maturity_date=date(2026, 6, 2),
            status="ACTIVE",
            workflow_status="RENEWAL_SUBMITTED",
        )
        metrics_pending = calculate_fdr_maturity_metrics(fdr_pending, reference_date=ref_today)
        self.assertEqual(metrics_pending["category"], "RENEWAL_PENDING")

    def test_maturity_summary_and_tenant_isolation(self):
        """Verify GET /api/maturity/summary respects institution tenant isolation."""
        # Add an expiring FDR for inst1 (maturity in 15 days)
        fdr_exp = FDRRecord(
            institution_id=self.inst1.id,
            fdr_number="FDR-EXP-101",
            issuing_bank="Punjab National Bank",
            deposit_amount=Decimal("500000.00"),
            issue_date=date.today() - timedelta(days=350),
            maturity_date=date.today() + timedelta(days=15),
            status="ACTIVE",
        )
        # Add a matured FDR for inst2 (maturity 10 days ago)
        fdr_mat = FDRRecord(
            institution_id=self.inst2.id,
            fdr_number="FDR-MAT-202",
            issuing_bank="Bank of Baroda",
            deposit_amount=Decimal("750000.00"),
            issue_date=date.today() - timedelta(days=400),
            maturity_date=date.today() - timedelta(days=10),
            status="ACTIVE",
        )
        db.session.add_all([fdr_exp, fdr_mat])
        db.session.commit()

        # 1. Institution 1 user requests summary -> Scoped to Inst 1
        res_inst1 = self.client.get("/api/maturity/summary", headers=self.auth_header(self.inst1_token))
        self.assertEqual(res_inst1.status_code, 200)
        data_inst1 = res_inst1.get_json()["data"]
        self.assertEqual(data_inst1["institution_id"], self.inst1.id)
        self.assertEqual(data_inst1["categories"]["expiring_soon_count"], 1)
        self.assertEqual(data_inst1["categories"]["matured_count"], 0)  # Cannot see inst2's matured record

        # 2. Central Admin requests summary -> Global across all institutions
        res_admin = self.client.get("/api/maturity/summary", headers=self.auth_header(self.admin_token))
        self.assertEqual(res_admin.status_code, 200)
        data_admin = res_admin.get_json()["data"]
        self.assertIsNone(data_admin["institution_id"])
        self.assertGreaterEqual(data_admin["categories"]["expiring_soon_count"], 1)
        self.assertGreaterEqual(data_admin["categories"]["matured_count"], 1)

    def test_expiring_fdrs_api(self):
        """Verify GET /api/maturity/expiring returns paginated results with filters."""
        # Create an expiring FDR for inst1
        fdr_exp = FDRRecord(
            institution_id=self.inst1.id,
            fdr_number="FDR-EXP-303",
            issuing_bank="Canara Bank",
            deposit_amount=Decimal("1200000.00"),
            issue_date=date.today() - timedelta(days=350),
            maturity_date=date.today() + timedelta(days=10),
            status="ACTIVE",
        )
        db.session.add(fdr_exp)
        db.session.commit()

        # Request expiring FDRs
        res = self.client.get(
            "/api/maturity/expiring?category=EXPIRING_SOON",
            headers=self.auth_header(self.inst1_token)
        )
        self.assertEqual(res.status_code, 200)
        json_data = res.get_json()
        self.assertIn("data", json_data)
        self.assertTrue(any(item["fdr_number"] == "FDR-EXP-303" for item in json_data["data"]))

    # =========================================================================
    # Phase 6: Alert Generation & Idempotency Tests
    # =========================================================================

    def test_alert_generation_and_idempotency(self):
        """Verify background alert scanning generates alerts idempotently without duplicates."""
        # Create an FDR expiring in 20 days
        fdr_alert_target = FDRRecord(
            institution_id=self.inst1.id,
            fdr_number="FDR-ALERT-TEST",
            issuing_bank="Union Bank of India",
            deposit_amount=Decimal("800000.00"),
            issue_date=date.today() - timedelta(days=300),
            maturity_date=date.today() + timedelta(days=20),
            status="ACTIVE",
        )
        db.session.add(fdr_alert_target)
        db.session.commit()

        # First scan run
        result_run1 = scan_and_generate_maturity_alerts()
        self.assertGreaterEqual(result_run1["alerts_created"], 1)

        # Check alert in database
        alert_rec = FDRAlert.query.filter_by(
            fdr_record_id=fdr_alert_target.id,
            alert_type=FDRAlert.TYPE_EXPIRING_30
        ).first()
        self.assertIsNotNone(alert_rec)
        self.assertEqual(alert_rec.institution_id, self.inst1.id)
        self.assertFalse(alert_rec.is_acknowledged)

        # Second scan run on same date -> Idempotency skips already-created alert
        result_run2 = scan_and_generate_maturity_alerts()
        self.assertEqual(result_run2["alerts_created"], 0)
        self.assertGreaterEqual(result_run2["skipped_duplicates"], 1)

        # Check that total alert count for this instrument did not increase
        count = FDRAlert.query.filter_by(
            fdr_record_id=fdr_alert_target.id,
            alert_type=FDRAlert.TYPE_EXPIRING_30
        ).count()
        self.assertEqual(count, 1)

    def test_trigger_scan_endpoint_rbac(self):
        """Verify POST /api/maturity/trigger-scan requires AICTE Official or Admin role."""
        # Institution user is denied
        res_user = self.client.post("/api/maturity/trigger-scan", headers=self.auth_header(self.inst1_token))
        self.assertEqual(res_user.status_code, 403)

        # Official is permitted
        res_off = self.client.post("/api/maturity/trigger-scan", headers=self.auth_header(self.official_token))
        self.assertEqual(res_off.status_code, 200)
        self.assertEqual(res_off.get_json()["status"], "success")

    def test_alert_listing_and_acknowledgment(self):
        """Verify GET /api/alerts and POST /api/alerts/<id>/acknowledge with tenant protection."""
        alert = FDRAlert(
            fdr_record_id=self.fdr1.id,
            institution_id=self.inst1.id,
            alert_type=FDRAlert.TYPE_EXPIRING_15,
            due_date=self.fdr1.maturity_date,
            recipient_role="institution_user",
            delivery_channel=FDRAlert.CHANNEL_IN_PORTAL,
            delivery_status=FDRAlert.STATUS_SENT,
            idempotency_key=f"fdr_{self.fdr1.id}_EXPIRING_15_test",
            title="Action Required: FDR Expiring",
            message="Please arrange renewal.",
        )
        db.session.add(alert)
        db.session.commit()

        # 1. Institution 2 cannot see Institution 1's alert
        res_list_inst2 = self.client.get("/api/alerts", headers=self.auth_header(self.inst2_token))
        self.assertEqual(res_list_inst2.status_code, 200)
        self.assertEqual(res_list_inst2.get_json()["total"], 0)

        # 2. Institution 2 cannot acknowledge Institution 1's alert -> 403 Forbidden
        res_ack_inst2 = self.client.post(f"/api/alerts/{alert.id}/acknowledge", headers=self.auth_header(self.inst2_token))
        self.assertEqual(res_ack_inst2.status_code, 403)

        # 3. Institution 1 user lists and acknowledges their alert
        res_list_inst1 = self.client.get("/api/alerts", headers=self.auth_header(self.inst1_token))
        self.assertEqual(res_list_inst1.status_code, 200)
        self.assertEqual(res_list_inst1.get_json()["total"], 1)

        res_ack_inst1 = self.client.post(f"/api/alerts/{alert.id}/acknowledge", headers=self.auth_header(self.inst1_token))
        self.assertEqual(res_ack_inst1.status_code, 200)
        self.assertTrue(res_ack_inst1.get_json()["data"]["is_acknowledged"])

        # 4. Duplicate acknowledgment returns 409 Conflict
        res_dup_ack = self.client.post(f"/api/alerts/{alert.id}/acknowledge", headers=self.auth_header(self.inst1_token))
        self.assertEqual(res_dup_ack.status_code, 409)

    # =========================================================================
    # Phase 6: Renewal Workflow, Linking and Review Tests
    # =========================================================================

    def test_renewal_submission_workflow(self):
        """Verify submitting replacement FDR links to predecessor and creates pending renewal."""
        payload = {
            "replacement_fdr_number": "FDR-SBI-2031-REPLACE",
            "issuing_bank": "State Bank of India",
            "deposit_amount": 2500000.00,
            "issue_date": "2031-01-15",
            "maturity_date": "2036-01-15",
            "submission_notes": "Submitted replacement FDR with matching principal for five more years.",
        }
        res = self.client.post(
            f"/api/fdr/{self.fdr1.id}/renew",
            headers=self.auth_header(self.inst1_token),
            json=payload,
        )
        self.assertEqual(res.status_code, 201)
        resp_data = res.get_json()["data"]
        self.assertEqual(resp_data["status"], "PENDING_REVIEW")
        self.assertEqual(resp_data["original_fdr_id"], self.fdr1.id)

        # Verify predecessor FDR workflow status
        original_db = db.session.get(FDRRecord, self.fdr1.id)
        self.assertEqual(original_db.workflow_status, "RENEWAL_SUBMITTED")

        # Verify successor FDR in database
        replacement_db = db.session.get(FDRRecord, resp_data["replacement_fdr_id"])
        self.assertIsNotNone(replacement_db)
        self.assertEqual(replacement_db.predecessor_id, self.fdr1.id)
        self.assertEqual(replacement_db.status, "PENDING_RENEWAL")

        # Verify audit log was recorded
        audit = FDRAuditLog.query.filter_by(
            fdr_record_id=self.fdr1.id,
            action="RENEWAL_SUBMITTED"
        ).first()
        self.assertIsNotNone(audit)
        self.assertEqual(audit.user_id, self.inst1_user.id)

    def test_renewal_cross_tenant_isolation(self):
        """Verify institution_user cannot submit renewal for another institution's FDR."""
        payload = {
            "replacement_fdr_number": "FDR-HACK-001",
            "issuing_bank": "HDFC Bank",
            "deposit_amount": 1500000.00,
            "issue_date": "2031-02-01",
            "maturity_date": "2036-02-01",
        }
        # Inst 1 user attempts renewal on Inst 2's FDR (fdr2)
        res = self.client.post(
            f"/api/fdr/{self.fdr2.id}/renew",
            headers=self.auth_header(self.inst1_token),
            json=payload,
        )
        self.assertEqual(res.status_code, 403)

    def test_renewal_approval_lifecycle_transition(self):
        """Verify AICTE Official approval transitions predecessor to RENEWED and successor to ACTIVE."""
        # 1. Submit renewal
        payload = {
            "replacement_fdr_number": "FDR-SBI-2031-APPROVED",
            "issuing_bank": "State Bank of India",
            "deposit_amount": 2500000.00,
            "issue_date": "2031-01-15",
            "maturity_date": "2036-01-15",
        }
        res_sub = self.client.post(
            f"/api/fdr/{self.fdr1.id}/renew",
            headers=self.auth_header(self.inst1_token),
            json=payload,
        )
        self.assertEqual(res_sub.status_code, 201)
        renewal_id = res_sub.get_json()["data"]["id"]
        replacement_id = res_sub.get_json()["data"]["replacement_fdr_id"]

        # 2. Institution user cannot review -> 403 Forbidden
        res_unauth = self.client.post(
            f"/api/renewals/{renewal_id}/review",
            headers=self.auth_header(self.inst1_token),
            json={"decision": "APPROVED", "notes": "I approve my own renewal"}
        )
        self.assertEqual(res_unauth.status_code, 403)

        # 3. AICTE Official approves renewal
        res_app = self.client.post(
            f"/api/renewals/{renewal_id}/review",
            headers=self.auth_header(self.official_token),
            json={"decision": "APPROVED", "notes": "Replacement deposit verified against bank scroll."}
        )
        self.assertEqual(res_app.status_code, 200)
        self.assertEqual(res_app.get_json()["data"]["status"], "APPROVED")

        # 4. Verify instrument lifecycle transitions
        orig_fdr = db.session.get(FDRRecord, self.fdr1.id)
        repl_fdr = db.session.get(FDRRecord, replacement_id)

        self.assertEqual(orig_fdr.status, "RENEWED")
        self.assertEqual(orig_fdr.workflow_status, "RENEWAL_APPROVED")
        self.assertEqual(repl_fdr.status, "ACTIVE")
        self.assertEqual(repl_fdr.workflow_status, "RENEWAL_APPROVED")

        # 5. Verify audit log entry
        audit_app = FDRAuditLog.query.filter_by(
            fdr_record_id=self.fdr1.id,
            action="RENEWAL_APPROVED"
        ).first()
        self.assertIsNotNone(audit_app)
        self.assertEqual(audit_app.user_id, self.official.id)

    def test_renewal_rejection_workflow(self):
        """Verify AICTE Official rejection updates workflow statuses without marking predecessor renewed."""
        payload = {
            "replacement_fdr_number": "FDR-SBI-2031-REJECTED",
            "issuing_bank": "State Bank of India",
            "deposit_amount": 2500000.00,
            "issue_date": "2031-01-15",
            "maturity_date": "2036-01-15",
        }
        res_sub = self.client.post(
            f"/api/fdr/{self.fdr1.id}/renew",
            headers=self.auth_header(self.inst1_token),
            json=payload,
        )
        renewal_id = res_sub.get_json()["data"]["id"]
        replacement_id = res_sub.get_json()["data"]["replacement_fdr_id"]

        # Reject renewal
        res_rej = self.client.post(
            f"/api/renewals/{renewal_id}/review",
            headers=self.auth_header(self.official_token),
            json={"decision": "REJECTED", "notes": "Deposit receipt signature is missing."}
        )
        self.assertEqual(res_rej.status_code, 200)
        self.assertEqual(res_rej.get_json()["data"]["status"], "REJECTED")

        orig_fdr = db.session.get(FDRRecord, self.fdr1.id)
        repl_fdr = db.session.get(FDRRecord, replacement_id)

        # Predecessor was NOT renewed
        self.assertEqual(orig_fdr.status, "ACTIVE")
        self.assertEqual(orig_fdr.workflow_status, "RENEWAL_REJECTED")
        self.assertEqual(repl_fdr.workflow_status, "RENEWAL_REJECTED")

    # =========================================================================
    # Phase 6: Boundary, Escalation, and Security Regression Tests
    # =========================================================================

    def test_phase6_exact_boundaries_and_excluded_lifecycles(self):
        """Verify exact 30/15/7-day boundaries, maturity, overdue, and exclusions."""
        reference_date = date(2026, 6, 1)
        cases = (
            (30, FDRAlert.TYPE_EXPIRING_30),
            (15, FDRAlert.TYPE_EXPIRING_15),
            (7, FDRAlert.TYPE_EXPIRING_7),
            (0, FDRAlert.TYPE_MATURED),
            (-14, FDRAlert.TYPE_MATURED),
        )
        records = []
        for offset, _ in cases:
            record = FDRRecord(
                institution_id=self.inst1.id,
                fdr_number=f"FDR-BOUNDARY-{offset.replace('-', 'N') if isinstance(offset, str) else offset}",
                issuing_bank="SBI",
                deposit_amount=Decimal("1000.00"),
                issue_date=date(2025, 1, 1),
                maturity_date=reference_date + timedelta(days=offset),
                status=FDRRecord.STATUS_ACTIVE,
            )
            records.append(record)

        renewed = FDRRecord(
            institution_id=self.inst1.id, fdr_number="FDR-BOUNDARY-RENEWED", issuing_bank="SBI",
            deposit_amount=Decimal("1000.00"), issue_date=date(2025, 1, 1),
            maturity_date=reference_date + timedelta(days=7), status=FDRRecord.STATUS_RENEWED,
        )
        released = FDRRecord(
            institution_id=self.inst1.id, fdr_number="FDR-BOUNDARY-RELEASED", issuing_bank="SBI",
            deposit_amount=Decimal("1000.00"), issue_date=date(2025, 1, 1),
            maturity_date=reference_date + timedelta(days=7), status=FDRRecord.STATUS_RELEASED,
        )
        db.session.add_all(records + [renewed, released])
        db.session.commit()

        for record, (offset, expected_type) in zip(records, cases):
            metrics = calculate_fdr_maturity_metrics(record, reference_date)
            expected_category = "MATURED" if offset <= 0 else "EXPIRING_SOON"
            self.assertEqual(metrics["days_remaining"], offset)
            self.assertEqual(metrics["category"], expected_category)

        first = scan_and_generate_maturity_alerts(reference_date=reference_date)
        second = scan_and_generate_maturity_alerts(reference_date=reference_date)
        self.assertEqual(first["alerts_created"], 6)  # 5 maturity alerts + 1 overdue
        self.assertEqual(second["alerts_created"], 0)
        self.assertGreaterEqual(second["skipped_duplicates"], 6)
        self.assertEqual(FDRAlert.query.filter_by(fdr_record_id=renewed.id).count(), 0)
        self.assertEqual(FDRAlert.query.filter_by(fdr_record_id=released.id).count(), 0)

        for record, (_, expected_type) in zip(records, cases):
            self.assertIsNotNone(FDRAlert.query.filter_by(
                fdr_record_id=record.id, alert_type=expected_type
            ).first())
        self.assertIsNotNone(FDRAlert.query.filter_by(
            fdr_record_id=records[-1].id, alert_type=FDRAlert.TYPE_RENEWAL_OVERDUE
        ).first())

    def test_phase6_expiring_api_reference_date_and_category_pagination(self):
        """Verify API date-boundary filtering returns consistent category pagination."""
        reference_date = date(2026, 6, 1)
        record = FDRRecord(
            institution_id=self.inst1.id, fdr_number="FDR-API-30D", issuing_bank="SBI",
            deposit_amount=Decimal("1000.00"), issue_date=date(2025, 1, 1),
            maturity_date=reference_date + timedelta(days=30), status=FDRRecord.STATUS_ACTIVE,
        )
        db.session.add(record)
        db.session.commit()
        response = self.client.get(
            "/api/maturity/expiring?reference_date=2026-06-01&days_ahead=30"
            "&category=EXPIRING_SOON&page=1&per_page=1",
            headers=self.auth_header(self.inst1_token),
        )
        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertGreaterEqual(payload["total"], 1)
        self.assertLessEqual(len(payload["data"]), 1)
        self.assertTrue(all(item["category"] == "EXPIRING_SOON" for item in payload["data"]))

    def test_phase6_overdue_escalation_requires_authority_and_tenant_isolation(self):
        """Verify scan authorization and alert/renewal tenant restrictions."""
        response = self.client.post(
            "/api/maturity/trigger-scan",
            headers=self.auth_header(self.inst1_token),
            json={"reference_date": "2026-06-01"},
        )
        self.assertEqual(response.status_code, 403)

        response = self.client.get(
            "/api/maturity/summary?institution_id=2",
            headers=self.auth_header(self.inst1_token),
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["data"]["institution_id"], self.inst1.id)

        response = self.client.get(
            "/api/maturity/expiring?institution_id=not-an-id",
            headers=self.auth_header(self.admin_token),
        )
        self.assertEqual(response.status_code, 400)

        response = self.client.post(
            f"/api/fdr/{self.fdr1.id}/renew",
            headers=self.auth_header(self.official_token),
            json={
                "replacement_fdr_number": "FDR-OFFICIAL-MUST-NOT-SUBMIT",
                "issuing_bank": "SBI", "deposit_amount": 1000,
                "issue_date": "2031-01-15", "maturity_date": "2036-01-15",
            },
        )
        self.assertEqual(response.status_code, 403)

    def test_phase6_timezone_date_source_is_configurable(self):
        """Verify maturity calculations use configured business date, not host date."""
        self.app.config["APP_TIMEZONE"] = "Pacific/Kiritimati"
        record = FDRRecord(
            institution_id=self.inst1.id, fdr_number="FDR-TZ-BOUNDARY", issuing_bank="SBI",
            deposit_amount=Decimal("1000.00"), issue_date=date(2025, 1, 1),
            maturity_date=local_business_date(), status=FDRRecord.STATUS_ACTIVE,
        )
        self.assertEqual(record.days_to_maturity, 0)

    # =========================================================================
    # Phase 7: Release/Refund Workflow & Advanced Audit Trail Tests
    # =========================================================================

    def test_phase7_release_request_submission_and_defaults(self):
        """Verify submitting release request creates PENDING_SCRUTINY state, audit entry & alert."""
        payload = {
            "fdr_id": self.fdr1.id,
            "request_type": "RELEASE",
            "reason": "Institution has fulfilled all accreditation guidelines and completed 5-year deposit lock-in.",
            "bank_details": {
                "account_name": "Delhi Institute of Technology Operational A/C",
                "bank_name": "State Bank of India",
                "ifsc_code": "SBIN0001234",
                "account_number": "112233445566",
            },
        }
        response = self.client.post(
            "/api/release-requests",
            headers=self.auth_header(self.inst1_token),
            json=payload,
        )
        self.assertEqual(response.status_code, 201)
        data = response.get_json()["data"]

        # Verify defaults & fields
        self.assertTrue(data["request_number"].startswith("REL-"))
        self.assertEqual(data["status"], "PENDING_SCRUTINY")
        self.assertEqual(data["request_type"], "RELEASE")
        self.assertEqual(data["requested_amount"], float(self.fdr1.deposit_amount))
        self.assertEqual(data["institution_id"], self.inst1.id)
        self.assertEqual(data["fdr_record_id"], self.fdr1.id)

        # Verify audit log was recorded
        audit = FDRAuditLog.query.filter_by(
            action="RELEASE_REQUEST_SUBMITTED",
            release_request_id=data["id"],
        ).first()
        self.assertIsNotNone(audit)
        self.assertEqual(audit.user_id, self.inst1_user.id)
        self.assertEqual(audit.actor_role, "institution_user")
        self.assertEqual(audit.entity_type, "RELEASE_REQUEST")

        # Verify alert created for official
        alert = FDRAlert.query.filter_by(
            release_request_id=data["id"],
            alert_type=FDRAlert.TYPE_RELEASE_SUBMITTED,
        ).first()
        self.assertIsNotNone(alert)
        self.assertEqual(alert.recipient_role, "aicte_official")

    def test_phase7_release_request_tenant_isolation(self):
        """Verify strict tenant isolation: institution cannot submit or view another's release requests."""
        # Inst 1 user attempts to request release on Inst 2's FDR (fdr2) -> 403 Forbidden
        payload = {
            "fdr_id": self.fdr2.id,
            "request_type": "RELEASE",
            "reason": "Unauthorized cross-tenant release attempt on another institution's FDR.",
        }
        res_cross = self.client.post(
            "/api/release-requests",
            headers=self.auth_header(self.inst1_token),
            json=payload,
        )
        self.assertEqual(res_cross.status_code, 403)
        self.assertIn("another institution", res_cross.get_json()["message"])

        # Create valid release request for Inst 2
        req_inst2 = FDRReleaseRequest(
            request_number="REL-2026-99999",
            institution_id=self.inst2.id,
            fdr_record_id=self.fdr2.id,
            request_type=FDRReleaseRequest.TYPE_RELEASE,
            reason="Valid completion of statutory period for MIT.",
            requested_amount=self.fdr2.deposit_amount,
            status=FDRReleaseRequest.STATUS_PENDING_SCRUTINY,
            requested_by_id=self.inst2_user.id,
        )
        db.session.add(req_inst2)
        db.session.commit()

        # Inst 1 user lists release requests -> Must NOT contain Inst 2's request
        res_list = self.client.get("/api/release-requests", headers=self.auth_header(self.inst1_token))
        self.assertEqual(res_list.status_code, 200)
        items = res_list.get_json()["data"]
        self.assertTrue(all(item["institution_id"] == self.inst1.id for item in items))

        # Inst 1 user attempts direct GET on Inst 2's release request -> 403 Forbidden
        res_get_unauth = self.client.get(f"/api/release-requests/{req_inst2.id}", headers=self.auth_header(self.inst1_token))
        self.assertEqual(res_get_unauth.status_code, 403)

    def test_phase7_release_request_eligibility_and_duplicate_prevention(self):
        """Verify release requests cannot be filed on already released/renewed FDRs or duplicated."""
        # 1. Released FDR
        self.fdr1.status = FDRRecord.STATUS_RELEASED
        db.session.commit()

        res_rel = self.client.post(
            "/api/release-requests",
            headers=self.auth_header(self.inst1_token),
            json={"fdr_id": self.fdr1.id, "reason": "Attempting release on already released FDR."},
        )
        self.assertEqual(res_rel.status_code, 409)

        # 2. Reset to ACTIVE and create active release request
        self.fdr1.status = FDRRecord.STATUS_ACTIVE
        db.session.commit()

        res_ok = self.client.post(
            "/api/release-requests",
            headers=self.auth_header(self.inst1_token),
            json={"fdr_id": self.fdr1.id, "reason": "First valid release request in progress."},
        )
        self.assertEqual(res_ok.status_code, 201)

        # 3. Concurrent duplicate request on same FDR -> 409 Conflict
        res_dup = self.client.post(
            "/api/release-requests",
            headers=self.auth_header(self.inst1_token),
            json={"fdr_id": self.fdr1.id, "reason": "Concurrent second release request on same FDR."},
        )
        self.assertEqual(res_dup.status_code, 409)
        self.assertIn("already in progress", res_dup.get_json()["message"])

    def test_phase7_release_request_update_and_resubmit(self):
        """Verify updating permitted fields and resubmitting from CORRECTION_REQUIRED."""
        # Submit initial request
        res_sub = self.client.post(
            "/api/release-requests",
            headers=self.auth_header(self.inst1_token),
            json={"fdr_id": self.fdr1.id, "reason": "Initial submission reason with ten chars."},
        )
        req_id = res_sub.get_json()["data"]["id"]

        # Update while in PENDING_SCRUTINY
        res_patch1 = self.client.patch(
            f"/api/release-requests/{req_id}",
            headers=self.auth_header(self.inst1_token),
            json={"reason": "Updated submission reason with ten chars."},
        )
        self.assertEqual(res_patch1.status_code, 200)
        self.assertEqual(res_patch1.get_json()["data"]["reason"], "Updated submission reason with ten chars.")

        # Official marks CORRECTION_REQUIRED
        self.client.post(
            f"/api/release-requests/{req_id}/scrutiny",
            headers=self.auth_header(self.official_token),
            json={"action": "REQUEST_CORRECTION", "remarks": "Please attach bank confirmation letter."},
        )

        # User updates and resubmits
        res_resubmit = self.client.patch(
            f"/api/release-requests/{req_id}",
            headers=self.auth_header(self.inst1_token),
            json={
                "reason": "Updated with additional compliance information requested by AICTE.",
                "resubmit": True,
            },
        )
        self.assertEqual(res_resubmit.status_code, 200)
        self.assertEqual(res_resubmit.get_json()["data"]["status"], "RESUBMITTED")

    def test_phase7_official_scrutiny_workflow_and_state_machine(self):
        """Verify strict official scrutiny state machine and blocking of arbitrary transitions."""
        # Submit request
        res_sub = self.client.post(
            "/api/release-requests",
            headers=self.auth_header(self.inst1_token),
            json={"fdr_id": self.fdr1.id, "reason": "Request for official scrutiny testing."},
        )
        req_id = res_sub.get_json()["data"]["id"]

        # Regular user cannot scrutinize -> 403 Forbidden
        res_unauth = self.client.post(
            f"/api/release-requests/{req_id}/scrutiny",
            headers=self.auth_header(self.inst1_token),
            json={"action": "START_REVIEW", "remarks": "Unauthorized scrutiny."},
        )
        self.assertEqual(res_unauth.status_code, 403)

        # 1. Official starts review: PENDING_SCRUTINY -> UNDER_REVIEW
        res_review = self.client.post(
            f"/api/release-requests/{req_id}/scrutiny",
            headers=self.auth_header(self.official_token),
            json={"action": "START_REVIEW", "remarks": "Commencing scrutiny of FDR deposit documents."},
        )
        self.assertEqual(res_review.status_code, 200)
        self.assertEqual(res_review.get_json()["data"]["status"], "UNDER_REVIEW")

        # 2. Official recommends for approval: UNDER_REVIEW -> RECOMMENDED_FOR_APPROVAL
        res_rec = self.client.post(
            f"/api/release-requests/{req_id}/scrutiny",
            headers=self.auth_header(self.official_token),
            json={"action": "RECOMMEND_APPROVAL", "remarks": "All documents verified in order. Recommended to Admin."},
        )
        self.assertEqual(res_rec.status_code, 200)
        self.assertEqual(res_rec.get_json()["data"]["status"], "RECOMMENDED_FOR_APPROVAL")

        # 3. Invalid jump: Attempting to repeat START_REVIEW on RECOMMENDED_FOR_APPROVAL -> 409 Conflict
        res_bad_jump = self.client.post(
            f"/api/release-requests/{req_id}/scrutiny",
            headers=self.auth_header(self.official_token),
            json={"action": "START_REVIEW", "remarks": "Invalid backwards jump."},
        )
        self.assertEqual(res_bad_jump.status_code, 409)

    def test_phase7_multi_level_approval_and_self_approval_prevention(self):
        """Verify admin-only final approval and prevention of self-approval."""
        # 1. Submit request as inst1_user
        res_sub = self.client.post(
            "/api/release-requests",
            headers=self.auth_header(self.inst1_token),
            json={"fdr_id": self.fdr1.id, "reason": "Test multi-level approval workflow."},
        )
        req_id = res_sub.get_json()["data"]["id"]

        # 2. Official scrutiny moves to RECOMMENDED_FOR_APPROVAL
        self.client.post(
            f"/api/release-requests/{req_id}/scrutiny",
            headers=self.auth_header(self.official_token),
            json={"action": "RECOMMEND_APPROVAL", "remarks": "Scrutiny passed."},
        )

        # 3. Official attempts approval -> 403 (Requires Admin role)
        res_off_app = self.client.post(
            f"/api/release-requests/{req_id}/approval",
            headers=self.auth_header(self.official_token),
            json={"decision": "APPROVE", "remarks": "Official attempting final admin approval."},
        )
        self.assertEqual(res_off_app.status_code, 403)

        # 4. Self-approval prevention test:
        # If admin is also the requester, approval must be rejected with 403 Forbidden
        req_rec = db.session.get(FDRReleaseRequest, req_id)
        req_rec.requested_by_id = self.admin.id
        db.session.commit()

        res_self_app = self.client.post(
            f"/api/release-requests/{req_id}/approval",
            headers=self.auth_header(self.admin_token),
            json={"decision": "APPROVE", "remarks": "Admin attempting self-approval."},
        )
        self.assertEqual(res_self_app.status_code, 403)
        self.assertIn("Conflict of interest", res_self_app.get_json()["message"])

        # 5. Restore original requester and perform valid approval
        req_rec.requested_by_id = self.inst1_user.id
        db.session.commit()

        res_valid_app = self.client.post(
            f"/api/release-requests/{req_id}/approval",
            headers=self.auth_header(self.admin_token),
            json={"decision": "APPROVE", "remarks": "Sanctioned release under AICTE Finance Regulation 2026."},
        )
        self.assertEqual(res_valid_app.status_code, 200)
        self.assertEqual(res_valid_app.get_json()["data"]["status"], "APPROVED")

    def test_phase7_release_closure_and_fdr_status_update(self):
        """Verify release closure transitions FDR to RELEASED and records financial disclaimer."""
        # 1. Create APPROVED release request
        req = FDRReleaseRequest(
            request_number="REL-2026-CLOSURE",
            institution_id=self.inst1.id,
            fdr_record_id=self.fdr1.id,
            request_type=FDRReleaseRequest.TYPE_RELEASE,
            reason="Release approved by council.",
            requested_amount=self.fdr1.deposit_amount,
            status=FDRReleaseRequest.STATUS_APPROVED,
            requested_by_id=self.inst1_user.id,
        )
        db.session.add(req)
        db.session.commit()

        # 2. Close request
        res_close = self.client.post(
            f"/api/release-requests/{req.id}/close",
            headers=self.auth_header(self.official_token),
            json={
                "closure_reference": "AICTE-SANCTION-2026-9081",
                "remarks": "FDR marked RELEASED upon issuance of bank advice letter.",
            },
        )
        self.assertEqual(res_close.status_code, 200)
        self.assertEqual(res_close.get_json()["data"]["status"], "RELEASED_CLOSED")

        # 3. Verify underlying FDRRecord status is updated to RELEASED
        fdr_db = db.session.get(FDRRecord, self.fdr1.id)
        self.assertEqual(fdr_db.status, FDRRecord.STATUS_RELEASED)

        # 4. Verify audit log contains financial disbursement disclaimer
        audit_close = FDRAuditLog.query.filter_by(
            action="RELEASE_REQUEST_CLOSED",
            release_request_id=req.id,
        ).first()
        self.assertIsNotNone(audit_close)
        self.assertIn("Physical bank disbursement", audit_close.remarks)

        # 5. Terminal state check: Closed request cannot be scrutinized or closed again
        res_reclose = self.client.post(
            f"/api/release-requests/{req.id}/close",
            headers=self.auth_header(self.official_token),
            json={"remarks": "Attempting second closure."},
        )
        self.assertEqual(res_reclose.status_code, 409)

    def test_phase7_advanced_audit_trail_immutability_and_filters(self):
        """Verify audit trail endpoint filters, tenant isolation, and lack of modification endpoints."""
        # 1. Record sample audit entries
        log1 = FDRAuditLog(
            entity_type="RELEASE_REQUEST",
            entity_id=1,
            institution_id=self.inst1.id,
            user_id=self.inst1_user.id,
            actor_role="institution_user",
            action="RELEASE_REQUEST_SUBMITTED",
            remarks="DIT submitted release.",
        )
        log2 = FDRAuditLog(
            entity_type="RELEASE_REQUEST",
            entity_id=2,
            institution_id=self.inst2.id,
            user_id=self.inst2_user.id,
            actor_role="institution_user",
            action="RELEASE_REQUEST_SUBMITTED",
            remarks="MIT submitted release.",
        )
        db.session.add_all([log1, log2])
        db.session.commit()

        # 2. Institution 1 user queries audit logs -> Scoped to Inst 1 only
        res_inst1 = self.client.get("/api/audit-logs", headers=self.auth_header(self.inst1_token))
        self.assertEqual(res_inst1.status_code, 200)
        data_inst1 = res_inst1.get_json()["data"]
        self.assertTrue(all(log["institution_id"] == self.inst1.id for log in data_inst1))

        # 3. Administrator queries audit logs -> Can view all and filter by entity_type
        res_admin = self.client.get("/api/audit-logs?entity_type=RELEASE_REQUEST", headers=self.auth_header(self.admin_token))
        self.assertEqual(res_admin.status_code, 200)
        data_admin = res_admin.get_json()["data"]
        self.assertGreaterEqual(len(data_admin), 2)

        # 4. Immutability verification: POST / PATCH / DELETE on audit logs must be 404 or 405
        res_post_audit = self.client.post("/api/audit-logs", headers=self.auth_header(self.admin_token), json={})
        self.assertEqual(res_post_audit.status_code, 405)

        res_patch_audit = self.client.patch("/api/audit-logs/1", headers=self.auth_header(self.admin_token), json={})
        self.assertEqual(res_patch_audit.status_code, 404)

        res_del_audit = self.client.delete("/api/audit-logs/1", headers=self.auth_header(self.admin_token))
        self.assertEqual(res_del_audit.status_code, 404)

    def test_phase7_overdue_escalation_scanner_idempotency(self):
        """Verify overdue scan triggers escalation alerts without duplicate generation."""
        # Create a lingering release request with updated_at in the past
        past_date = datetime.utcnow() - timedelta(days=10)
        lingering_req = FDRReleaseRequest(
            request_number="REL-2026-OVERDUE",
            institution_id=self.inst1.id,
            fdr_record_id=self.fdr1.id,
            request_type=FDRReleaseRequest.TYPE_RELEASE,
            reason="Lingering in scrutiny for 10 days.",
            requested_amount=self.fdr1.deposit_amount,
            status=FDRReleaseRequest.STATUS_PENDING_SCRUTINY,
            requested_by_id=self.inst1_user.id,
            created_at=past_date,
            updated_at=past_date,
        )
        db.session.add(lingering_req)
        db.session.commit()

        # Regular user cannot trigger overdue scan -> 403 Forbidden
        res_unauth = self.client.post(
            "/api/release-requests/trigger-overdue-scan",
            headers=self.auth_header(self.inst1_token),
        )
        self.assertEqual(res_unauth.status_code, 403)

        # Official triggers scan -> 200 OK
        res_scan1 = self.client.post(
            "/api/release-requests/trigger-overdue-scan",
            headers=self.auth_header(self.official_token),
            json={"overdue_days": 7},
        )
        self.assertEqual(res_scan1.status_code, 200)
        self.assertGreaterEqual(res_scan1.get_json()["alerts_created"], 1)

        # Rerun scan immediately on same reference date -> Idempotency prevents duplicates
        res_scan2 = self.client.post(
            "/api/release-requests/trigger-overdue-scan",
            headers=self.auth_header(self.official_token),
            json={"overdue_days": 7},
        )
        self.assertEqual(res_scan2.status_code, 200)
        self.assertEqual(res_scan2.get_json()["alerts_created"], 0)
        self.assertGreaterEqual(res_scan2.get_json()["skipped_duplicates"], 1)

    # =========================================================================
    # Phase 8: Advanced AI & Machine Learning Intelligence Tests
    # =========================================================================

    def test_phase8_exact_and_fuzzy_duplicate_detection(self):
        """Verify intelligent duplicate detection catches normalized and fuzzy duplicates."""
        # Create an FDR in inst2 with normalized string match to fdr1 ("FDR-SBI-2026-9001")
        fdr_dup = FDRRecord(
            institution_id=self.inst2.id,
            fdr_number="FDRSBI20269001",  # Stripped hyphens
            issuing_bank="State Bank of India",
            deposit_amount=Decimal("2500000.00"),
            issue_date=date(2026, 1, 15),
            maturity_date=date(2031, 1, 15),
            status="ACTIVE",
        )
        db.session.add(fdr_dup)
        db.session.commit()

        candidate = evaluate_fdr_pair_similarity(self.fdr1, fdr_dup)
        self.assertIsNotNone(candidate)
        self.assertGreaterEqual(candidate["similarity_score"], 0.85)
        self.assertIn(
            candidate["match_type"],
            [FDRDuplicateCandidate.MATCH_FUZZY_NUMBER, FDRDuplicateCandidate.MATCH_CROSS_INSTITUTION],
        )

        scan_result = run_full_duplicate_scan()
        self.assertGreaterEqual(scan_result["duplicate_candidates_found"], 1)
        self.assertGreaterEqual(FDRDuplicateCandidate.query.count(), 1)

    def test_phase8_document_hash_collision_duplicate(self):
        """Verify duplicate detection identifies identical file SHA-256 hashes across instruments."""
        test_hash = "a1b2c3d4e5f60718293a4b5c6d7e8f901234567890abcdef1234567890abcdef"
        doc1 = FDRDocument(
            fdr_record_id=self.fdr1.id,
            institution_id=self.inst1.id,
            uploader_id=self.inst1_user.id,
            original_filename="receipt_primary.pdf",
            storage_key="test-key-doc-1",
            file_path="store_prim.pdf",
            content_type="application/pdf",
            file_size_bytes=1024,
            file_hash=test_hash,
            processing_status=FDRDocument.STATUS_PROCESSED,
        )
        doc2 = FDRDocument(
            fdr_record_id=self.fdr2.id,
            institution_id=self.inst2.id,
            uploader_id=self.inst2_user.id,
            original_filename="receipt_duplicate.pdf",
            storage_key="test-key-doc-2",
            file_path="store_dup.pdf",
            content_type="application/pdf",
            file_size_bytes=1024,
            file_hash=test_hash,
            processing_status=FDRDocument.STATUS_PENDING,
        )
        db.session.add_all([doc1, doc2])
        db.session.commit()

        hash_matches = detect_document_hash_duplicates()
        self.assertGreaterEqual(len(hash_matches), 1)
        self.assertEqual(hash_matches[0]["similarity_score"], 1.0)
        self.assertEqual(hash_matches[0]["match_type"], FDRDuplicateCandidate.MATCH_DOC_HASH)
        self.assertIn("Cryptographic SHA-256", hash_matches[0]["explanation"])

    def test_phase8_anomaly_detector_statistical_fallback_and_explainability(self):
        """Verify anomaly detector operates reliably with explainable feature attribution."""
        detector = FDRAnomalyDetector()
        analysis = detector.analyze_record(self.fdr1)

        self.assertIn("anomaly_score", analysis)
        self.assertIn("is_anomaly", analysis)
        self.assertIn("engine", analysis)
        self.assertIn("contributing_factors", analysis)
        self.assertIn("feature_values", analysis)
        self.assertGreaterEqual(analysis["anomaly_score"], 0.0)
        self.assertLessEqual(analysis["anomaly_score"], 1.0)

        # Test extreme outlier record generates explainable factors
        outlier_fdr = FDRRecord(
            institution_id=self.inst1.id,
            fdr_number="FDR-OUTLIER-9999",
            issuing_bank="State Bank of India",
            deposit_amount=Decimal("999999999.00"),  # Highly anomalous deposit amount
            issue_date=date(2026, 1, 1),
            maturity_date=date(2050, 1, 1),           # Extremely long tenor
            status="ACTIVE",
        )
        db.session.add(outlier_fdr)
        db.session.commit()

        outlier_analysis = detector.analyze_record(outlier_fdr)
        self.assertGreater(len(outlier_analysis["contributing_factors"]), 0)
        factor_features = [f["feature"] for f in outlier_analysis["contributing_factors"]]
        self.assertTrue("log_deposit_amount" in factor_features or "tenor_days" in factor_features)

    def test_phase8_explainable_risk_scoring(self):
        """Verify composite risk scoring produces bounded scores (0-100) and actionable categories."""
        result = calculate_fdr_risk(self.fdr1)
        self.assertIn("risk_score", result)
        self.assertIn("risk_category", result)
        self.assertIn("rule_score", result)
        self.assertIn("ml_score", result)
        self.assertIn("contributing_factors", result)
        self.assertIn("evidence", result)
        self.assertIn("recommended_action", result)

        self.assertGreaterEqual(result["risk_score"], 0.0)
        self.assertLessEqual(result["risk_score"], 100.0)
        self.assertIn(result["risk_category"], ["LOW", "MEDIUM", "HIGH", "CRITICAL"])

    def test_phase8_institution_compliance_profiling(self):
        """Verify institution compliance intelligence computes regulatory index, grade, and metrics."""
        profile = analyze_institution_compliance(self.inst1.id)
        self.assertIsNotNone(profile)
        self.assertEqual(profile["institution_id"], self.inst1.id)
        self.assertEqual(profile["institution_code"], self.inst1.institution_code)
        self.assertIn(profile["compliance_grade"], ["A", "B", "C", "D"])
        self.assertGreaterEqual(profile["compliance_score"], 0.0)
        self.assertLessEqual(profile["compliance_score"], 100.0)
        self.assertIn(profile["risk_level"], ["LOW", "MEDIUM", "HIGH", "CRITICAL"])
        self.assertIn("total_fdrs", profile["metrics"])
        self.assertIn("active_fdrs", profile["metrics"])
        self.assertIn("warning_indicators", profile)
        self.assertIn("recommendations", profile)

    def test_phase8_model_health_and_registry(self):
        """Verify model registry status and metadata versioning."""
        health = get_model_health_status()
        self.assertIn("model_version", health)
        self.assertIn("algorithm", health)
        self.assertIn("status", health)
        self.assertIn("features", health)
        self.assertEqual(health["model_version"], "v1.0.0")
        self.assertEqual(len(health["features"]), 8)

    def test_phase8_api_duplicate_scan_and_listing_rbac(self):
        """Verify RBAC and tenant isolation on duplicate scan and listing endpoints."""
        # 1. Inst user cannot trigger scan -> 403 Forbidden
        res_scan_unauth = self.client.post(
            "/api/ai/duplicates/scan",
            headers=self.auth_header(self.inst1_token),
        )
        self.assertEqual(res_scan_unauth.status_code, 403)

        # 2. AICTE Official triggers scan -> 200 OK
        res_scan_official = self.client.post(
            "/api/ai/duplicates/scan",
            headers=self.auth_header(self.official_token),
        )
        self.assertEqual(res_scan_official.status_code, 200)
        self.assertIn("total_fdrs_scanned", res_scan_official.get_json()["data"])

        # 3. Listing duplicates: Inst user only sees their own; Official sees all
        res_list_inst = self.client.get(
            "/api/ai/duplicates",
            headers=self.auth_header(self.inst1_token),
        )
        self.assertEqual(res_list_inst.status_code, 200)

        res_list_official = self.client.get(
            "/api/ai/duplicates",
            headers=self.auth_header(self.official_token),
        )
        self.assertEqual(res_list_official.status_code, 200)

    def test_phase8_api_duplicate_review_workflow(self):
        """Verify official review lifecycle of duplicate candidate with audit logging."""
        cand = FDRDuplicateCandidate(
            primary_fdr_id=self.fdr1.id,
            duplicate_fdr_id=self.fdr2.id,
            match_type=FDRDuplicateCandidate.MATCH_EXACT_NUMBER,
            similarity_score=1.0,
            status=FDRDuplicateCandidate.STATUS_UNREVIEWED,
        )
        db.session.add(cand)
        db.session.commit()

        # 1. Inst user attempts review -> 403 Forbidden
        res_review_unauth = self.client.patch(
            f"/api/ai/duplicates/{cand.id}",
            headers=self.auth_header(self.inst1_token),
            json={"status": "CONFIRMED_DUPLICATE", "remarks": "Review attempt."},
        )
        self.assertEqual(res_review_unauth.status_code, 403)

        # 2. Official provides invalid status -> 400 Bad Request
        res_invalid_status = self.client.patch(
            f"/api/ai/duplicates/{cand.id}",
            headers=self.auth_header(self.official_token),
            json={"status": "INVALID_STATE"},
        )
        self.assertEqual(res_invalid_status.status_code, 400)

        # 3. Official confirms duplicate -> 200 OK
        res_confirm = self.client.patch(
            f"/api/ai/duplicates/{cand.id}",
            headers=self.auth_header(self.official_token),
            json={
                "status": "CONFIRMED_DUPLICATE",
                "remarks": "Investigated with bank manager; duplicate submission confirmed.",
            },
        )
        self.assertEqual(res_confirm.status_code, 200)
        data = res_confirm.get_json()["data"]
        self.assertEqual(data["status"], "CONFIRMED_DUPLICATE")
        self.assertEqual(data["reviewed_by_id"], self.official.id)

    def test_phase8_api_anomaly_and_risk_score_tenant_isolation(self):
        """Verify tenant isolation and RBAC on anomaly analysis and risk evaluation APIs."""
        # 1. Inst1 user analyzes own FDR anomaly -> 200 OK
        res_anom_own = self.client.get(
            f"/api/ai/anomalies/{self.fdr1.id}",
            headers=self.auth_header(self.inst1_token),
        )
        self.assertEqual(res_anom_own.status_code, 200)

        # 2. Inst1 user analyzes Inst2 FDR anomaly -> 403 Forbidden
        res_anom_cross = self.client.get(
            f"/api/ai/anomalies/{self.fdr2.id}",
            headers=self.auth_header(self.inst1_token),
        )
        self.assertEqual(res_anom_cross.status_code, 403)

        # 3. Inst1 user queries own risk score -> 200 OK
        res_risk_own = self.client.get(
            f"/api/ai/risk-score/{self.fdr1.id}",
            headers=self.auth_header(self.inst1_token),
        )
        self.assertEqual(res_risk_own.status_code, 200)
        self.assertIn("risk_score", res_risk_own.get_json()["data"])

        # 4. Inst1 user queries Inst2 risk score -> 403 Forbidden
        res_risk_cross = self.client.get(
            f"/api/ai/risk-score/{self.fdr2.id}",
            headers=self.auth_header(self.inst1_token),
        )
        self.assertEqual(res_risk_cross.status_code, 403)

        # 5. Official queries any risk score -> 200 OK
        res_risk_official = self.client.get(
            f"/api/ai/risk-score/{self.fdr2.id}",
            headers=self.auth_header(self.official_token),
        )
        self.assertEqual(res_risk_official.status_code, 200)

        # 6. Batch risk scoring (Official / Admin only)
        res_batch = self.client.post(
            "/api/ai/risk-score/batch",
            headers=self.auth_header(self.official_token),
            json={"fdr_ids": [self.fdr1.id, self.fdr2.id]},
        )
        self.assertEqual(res_batch.status_code, 200)
        self.assertEqual(res_batch.get_json()["total_evaluated"], 2)

    def test_phase8_api_compliance_endpoints_and_tenant_isolation(self):
        """Verify compliance profiling APIs enforce institutional scoping and RBAC."""
        # 1. Inst1 user requests own compliance profile -> 200 OK
        res_comp_own = self.client.get(
            f"/api/ai/compliance/{self.inst1.id}",
            headers=self.auth_header(self.inst1_token),
        )
        self.assertEqual(res_comp_own.status_code, 200)
        self.assertEqual(res_comp_own.get_json()["data"]["institution_id"], self.inst1.id)

        # 2. Inst1 user requests Inst2 compliance profile -> 403 Forbidden
        res_comp_cross = self.client.get(
            f"/api/ai/compliance/{self.inst2.id}",
            headers=self.auth_header(self.inst1_token),
        )
        self.assertEqual(res_comp_cross.status_code, 403)

        # 3. Inst1 user requests council-wide compliance summary -> 403 Forbidden
        res_sum_unauth = self.client.get(
            "/api/ai/compliance/summary",
            headers=self.auth_header(self.inst1_token),
        )
        self.assertEqual(res_sum_unauth.status_code, 403)

        # 4. Official requests council-wide compliance summary -> 200 OK
        res_sum_official = self.client.get(
            "/api/ai/compliance/summary",
            headers=self.auth_header(self.official_token),
        )
        self.assertEqual(res_sum_official.status_code, 200)
        self.assertIn("grade_distribution", res_sum_official.get_json())

    def test_phase8_api_360_dossier_report(self):
        """Verify 360-degree AI intelligence dossier compiles multifaceted audit metadata."""
        # 1. Inst1 user retrieves own dossier -> 200 OK
        res_rep_own = self.client.get(
            f"/api/ai/report/{self.fdr1.id}",
            headers=self.auth_header(self.inst1_token),
        )
        self.assertEqual(res_rep_own.status_code, 200)
        dossier = res_rep_own.get_json()["data"]
        self.assertIn("fdr_details", dossier)
        self.assertIn("institution", dossier)
        self.assertIn("risk_assessment", dossier)
        self.assertIn("anomaly_analysis", dossier)
        self.assertIn("duplicate_detection", dossier)
        self.assertIn("documents_verification", dossier)
        self.assertIn("regulatory_disclaimer", dossier)

        # 2. Inst1 user attempts cross-institution dossier retrieval -> 403 Forbidden
        res_rep_cross = self.client.get(
            f"/api/ai/report/{self.fdr2.id}",
            headers=self.auth_header(self.inst1_token),
        )
        self.assertEqual(res_rep_cross.status_code, 403)

    def test_phase8_api_model_management_admin_only(self):
        """Verify ML model management and synthetic retraining are strictly restricted to Administrators."""
        # 1. Authenticated user can view model health status -> 200 OK
        res_health = self.client.get(
            "/api/ai/models/health",
            headers=self.auth_header(self.inst1_token),
        )
        self.assertEqual(res_health.status_code, 200)
        self.assertEqual(res_health.get_json()["data"]["model_version"], "v1.0.0")

        # 2. Inst user attempts retraining -> 403 Forbidden
        res_train_inst = self.client.post(
            "/api/ai/models/train",
            headers=self.auth_header(self.inst1_token),
            json={"n_samples": 100},
        )
        self.assertEqual(res_train_inst.status_code, 403)

        # 3. AICTE Official attempts retraining -> 403 Forbidden
        res_train_official = self.client.post(
            "/api/ai/models/train",
            headers=self.auth_header(self.official_token),
            json={"n_samples": 100},
        )
        self.assertEqual(res_train_official.status_code, 403)

        # 4. Administrator triggers synthetic retraining -> 200 OK
        res_train_admin = self.client.post(
            "/api/ai/models/train",
            headers=self.auth_header(self.admin_token),
            json={"n_samples": 100},
        )
        self.assertEqual(res_train_admin.status_code, 200)
        data = res_train_admin.get_json()["data"]
        self.assertEqual(data["samples_trained"], 100)
        self.assertEqual(data["model_version"], "v1.0.0")


if __name__ == "__main__":
    unittest.main()

