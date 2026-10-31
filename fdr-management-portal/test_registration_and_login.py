"""
Comprehensive Integration & Verification Suite for Institution Registration & Login.
SIH 26265 - AICTE FDR Management Portal.

Tests:
1. Public Institution Listing (/api/institutions/public & /api/auth/institutions)
2. Invalid Institution Rejection during Registration (e.g. Non-existent ID 99999)
3. Valid Institution Registration with PENDING status by default
4. Duplicate Email Conflict Detection (HTTP 409)
5. Weak Password Rejection (<8 chars)
6. Login with Incorrect Password (HTTP 401)
7. Login with PENDING Account (HTTP 403 with descriptive pending message)
8. Admin User Queue & Pending User Review (/api/auth/admin/users)
9. Admin User Approval (/api/auth/admin/users/<id>/status -> ACTIVE)
10. Login with APPROVED Account (HTTP 200 with JWT access token)
11. Multi-Tenant Data Isolation (Institution user blocked from other institutions)
12. Admin User Rejection (/api/auth/admin/users/<id>/status -> REJECTED)
13. Login with REJECTED Account (HTTP 403 with rejection message)
14. Admin User Suspension (/api/auth/admin/users/<id>/status -> SUSPENDED)
15. Login with SUSPENDED Account (HTTP 403 with suspension message)
16. Admin Provisioning of New Accredited Institution (/api/institutions POST)
"""

import unittest
import json
from app import create_app
from models import db, Institution, User, FDRAuditLog


class TestRegistrationAndLoginWorkflow(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = create_app("testing")
        cls.client = cls.app.test_client()

    def setUp(self):
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()

        # Seed baseline institution and admin
        self.inst1 = Institution(
            institution_code="1-TEST-001",
            name="Delhi Institute of Technology (Test Demo)",
            address="Delhi Campus, New Delhi 110001",
            contact_email="finance@dit-test.edu.in",
        )
        self.inst2 = Institution(
            institution_code="1-TEST-002",
            name="Mumbai Academy of Science & Tech (Test Demo)",
            address="Mumbai Campus, Mumbai 400001",
            contact_email="accounts@mast-test.edu.in",
        )
        db.session.add_all([self.inst1, self.inst2])
        db.session.commit()

        # Create system administrator
        self.admin = User(
            email="admin@test.org",
            full_name="AICTE Central Admin",
            role=User.ROLE_ADMINISTRATOR,
            account_status=User.STATUS_ACTIVE,
        )
        self.admin.set_password("AdminSecure2026!")
        db.session.add(self.admin)
        db.session.commit()

        # Authenticate admin to obtain JWT
        res = self.client.post("/api/auth/login", json={
            "email": "admin@test.org",
            "password": "AdminSecure2026!"
        })
        self.admin_token = res.get_json()["access_token"]
        self.admin_header = {"Authorization": f"Bearer {self.admin_token}"}

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    # -------------------------------------------------------------------------
    # TEST 1: Public Institution Directory Listing
    # -------------------------------------------------------------------------
    def test_01_public_institutions_listing(self):
        """Verify unauthenticated visitors can fetch institutions for registration."""
        res = self.client.get("/api/institutions/public")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data["status"], "success")
        self.assertGreaterEqual(data["total"], 2)
        inst_codes = [i["institution_code"] for i in data["data"]]
        self.assertIn("1-TEST-001", inst_codes)

        # Test auth alias endpoint as well
        res_alias = self.client.get("/api/auth/institutions")
        self.assertEqual(res_alias.status_code, 200)
        self.assertEqual(res_alias.get_json()["total"], data["total"])

    # -------------------------------------------------------------------------
    # TEST 2: Registration with Invalid Institution Rejection
    # -------------------------------------------------------------------------
    def test_02_registration_invalid_institution_rejected(self):
        """Verify registration with non-existent institution ID returns 404 Not Found."""
        res = self.client.post("/api/auth/register", json={
            "full_name": "Test Applicant",
            "email": "applicant@unknown.edu",
            "password": "ValidPassword2026!",
            "institution_id": 99999,
        })
        self.assertEqual(res.status_code, 404)
        data = res.get_json()
        self.assertIn("does not exist", data["message"])

    # -------------------------------------------------------------------------
    # TEST 3: Registration with Valid Selection & PENDING Default Status
    # -------------------------------------------------------------------------
    def test_03_registration_success_sets_pending_status(self):
        """Verify valid registration sets PENDING status and logs audit entry."""
        res = self.client.post("/api/auth/register", json={
            "full_name": "Dr. Rajesh Sharma",
            "email": "rajesh@dit-test.edu.in",
            "password": "SecurePassword2026!",
            "institution_id": self.inst1.id,
        })
        self.assertEqual(res.status_code, 201)
        data = res.get_json()
        self.assertEqual(data["status"], "success")
        self.assertEqual(data["data"]["account_status"], "PENDING")
        self.assertEqual(data["data"]["role"], "institution_user")
        self.assertEqual(data["data"]["institution_id"], self.inst1.id)
        self.assertIn("pending administrative approval", data["message"].lower())

        # Verify audit log recorded
        audit = FDRAuditLog.query.filter_by(action="USER_REGISTRATION_SUBMITTED").first()
        self.assertIsNotNone(audit)
        self.assertIn("rajesh@dit-test.edu.in", audit.remarks)

    # -------------------------------------------------------------------------
    # TEST 4: Duplicate Email Registration Rejection
    # -------------------------------------------------------------------------
    def test_04_duplicate_email_rejected(self):
        """Verify attempting to register with existing email returns 409 Conflict."""
        # First registration
        self.client.post("/api/auth/register", json={
            "full_name": "First User",
            "email": "duplicate@test.edu",
            "password": "SecurePassword2026!",
            "institution_id": self.inst1.id,
        })
        # Duplicate registration attempt (case insensitive)
        res = self.client.post("/api/auth/register", json={
            "full_name": "Second User",
            "email": "DUPLICATE@TEST.EDU",
            "password": "SecurePassword2026!",
            "institution_id": self.inst1.id,
        })
        self.assertEqual(res.status_code, 409)
        self.assertIn("already exists", res.get_json()["message"])

    # -------------------------------------------------------------------------
    # TEST 5: Weak Password Rejection
    # -------------------------------------------------------------------------
    def test_05_weak_password_rejected(self):
        """Verify short password (<8 chars) returns 400 Validation Error."""
        res = self.client.post("/api/auth/register", json={
            "full_name": "Weak Pass User",
            "email": "weak@test.edu",
            "password": "short",
            "institution_id": self.inst1.id,
        })
        self.assertEqual(res.status_code, 400)
        self.assertIn("at least 8 characters", res.get_json()["message"])

    # -------------------------------------------------------------------------
    # TEST 6: Login with Incorrect Password
    # -------------------------------------------------------------------------
    def test_06_login_incorrect_password_rejected(self):
        """Verify incorrect password returns 401 Unauthorized."""
        res = self.client.post("/api/auth/login", json={
            "email": "admin@test.org",
            "password": "WrongPassword123!"
        })
        self.assertEqual(res.status_code, 401)
        self.assertIn("Invalid email or password", res.get_json()["message"])

    # -------------------------------------------------------------------------
    # TEST 7: Login with PENDING Account Blocked
    # -------------------------------------------------------------------------
    def test_07_login_pending_account_blocked(self):
        """Verify user with PENDING account cannot log in and receives clear explanation."""
        self.client.post("/api/auth/register", json={
            "full_name": "Pending Applicant",
            "email": "pending@dit-test.edu.in",
            "password": "SecurePassword2026!",
            "institution_id": self.inst1.id,
        })

        res = self.client.post("/api/auth/login", json={
            "email": "pending@dit-test.edu.in",
            "password": "SecurePassword2026!"
        })
        self.assertEqual(res.status_code, 403)
        data = res.get_json()
        self.assertEqual(data.get("account_status"), "PENDING")
        self.assertIn("pending administrative approval", data["message"].lower())

    # -------------------------------------------------------------------------
    # TEST 8 & 9: Admin User Queue & Approval Workflow
    # -------------------------------------------------------------------------
    def test_08_admin_approval_workflow(self):
        """Verify admin can view pending users and approve applicant."""
        reg_res = self.client.post("/api/auth/register", json={
            "full_name": "Prof. Amit Verma",
            "email": "amit@dit-test.edu.in",
            "password": "SecurePassword2026!",
            "institution_id": self.inst1.id,
        })
        user_id = reg_res.get_json()["data"]["id"]

        # Admin lists pending users
        list_res = self.client.get(
            "/api/auth/admin/users?status=PENDING",
            headers=self.admin_header
        )
        self.assertEqual(list_res.status_code, 200)
        pending_users = list_res.get_json()["data"]
        self.assertTrue(any(u["id"] == user_id for u in pending_users))

        # Admin approves user
        approve_res = self.client.patch(
            f"/api/auth/admin/users/{user_id}/status",
            headers=self.admin_header,
            json={"status": "ACTIVE", "remarks": "Approved by AICTE Admin after credential check"}
        )
        self.assertEqual(approve_res.status_code, 200)
        self.assertEqual(approve_res.get_json()["data"]["account_status"], "ACTIVE")

        # Verify audit log
        audit = FDRAuditLog.query.filter_by(action="USER_REGISTRATION_APPROVED").first()
        self.assertIsNotNone(audit)

        # Approved user can now log in
        login_res = self.client.post("/api/auth/login", json={
            "email": "amit@dit-test.edu.in",
            "password": "SecurePassword2026!"
        })
        self.assertEqual(login_res.status_code, 200)
        login_data = login_res.get_json()
        self.assertIn("access_token", login_data)
        self.assertEqual(login_data["user"]["account_status"], "ACTIVE")

    # -------------------------------------------------------------------------
    # TEST 10: Multi-Tenant Data Isolation Enforcement
    # -------------------------------------------------------------------------
    def test_10_multitenant_isolation_enforced(self):
        """Verify approved institution user cannot access other institution records."""
        # Create user belonging to inst1
        user1 = User(
            email="officer1@dit-test.edu.in",
            full_name="Desk Officer 1",
            role=User.ROLE_INSTITUTION_USER,
            account_status=User.STATUS_ACTIVE,
            institution_id=self.inst1.id,
        )
        user1.set_password("SecurePassword2026!")
        db.session.add(user1)
        db.session.commit()

        login_res = self.client.post("/api/auth/login", json={
            "email": "officer1@dit-test.edu.in",
            "password": "SecurePassword2026!"
        })
        user1_token = login_res.get_json()["access_token"]
        user1_header = {"Authorization": f"Bearer {user1_token}"}

        # Access own institution: ALLOWED (200)
        own_res = self.client.get(f"/api/institutions/{self.inst1.id}", headers=user1_header)
        self.assertEqual(own_res.status_code, 200)

        # Access other institution: BLOCKED (403 Forbidden)
        other_res = self.client.get(f"/api/institutions/{self.inst2.id}", headers=user1_header)
        self.assertEqual(other_res.status_code, 403)
        self.assertIn("Access denied", other_res.get_json()["message"])

    # -------------------------------------------------------------------------
    # TEST 11: Admin Rejection & Suspension Workflow
    # -------------------------------------------------------------------------
    def test_11_admin_rejection_and_suspension(self):
        """Verify rejected and suspended accounts are blocked from logging in."""
        reg_res = self.client.post("/api/auth/register", json={
            "full_name": "Rejected Applicant",
            "email": "rejected@test.edu",
            "password": "SecurePassword2026!",
            "institution_id": self.inst1.id,
        })
        user_id = reg_res.get_json()["data"]["id"]

        # Admin rejects user
        self.client.patch(
            f"/api/auth/admin/users/{user_id}/status",
            headers=self.admin_header,
            json={"status": "REJECTED", "remarks": "Invalid affiliation documents"}
        )

        # Login returns 403 REJECTED
        rej_login = self.client.post("/api/auth/login", json={
            "email": "rejected@test.edu",
            "password": "SecurePassword2026!"
        })
        self.assertEqual(rej_login.status_code, 403)
        self.assertEqual(rej_login.get_json().get("account_status"), "REJECTED")

        # Admin reactivates then suspends
        self.client.patch(
            f"/api/auth/admin/users/{user_id}/status",
            headers=self.admin_header,
            json={"status": "ACTIVE"}
        )
        self.client.patch(
            f"/api/auth/admin/users/{user_id}/status",
            headers=self.admin_header,
            json={"status": "SUSPENDED", "remarks": "Audit non-compliance suspension"}
        )

        susp_login = self.client.post("/api/auth/login", json={
            "email": "rejected@test.edu",
            "password": "SecurePassword2026!"
        })
        self.assertEqual(susp_login.status_code, 403)
        self.assertEqual(susp_login.get_json().get("account_status"), "SUSPENDED")

    # -------------------------------------------------------------------------
    # TEST 12: Admin Enroll New Institution
    # -------------------------------------------------------------------------
    def test_12_admin_enroll_institution(self):
        """Verify system administrator can enroll a new institution."""
        res = self.client.post(
            "/api/institutions",
            headers=self.admin_header,
            json={
                "institution_code": "1-NEW-999",
                "name": "Kolkata Institute of Technology (Demo)",
                "address": "Salt Lake Sector V, Kolkata 700091",
                "contact_email": "finance@kit-demo.edu.in",
            }
        )
        self.assertEqual(res.status_code, 201)
        data = res.get_json()["data"]
        self.assertEqual(data["institution_code"], "1-NEW-999")

        # Verify it now appears in public institutions list
        pub_res = self.client.get("/api/institutions/public")
        codes = [i["institution_code"] for i in pub_res.get_json()["data"]]
        self.assertIn("1-NEW-999", codes)


if __name__ == "__main__":
    unittest.main(verbosity=2)
