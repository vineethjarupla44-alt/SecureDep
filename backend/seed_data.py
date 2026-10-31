"""
Database Seeding Script for AICTE FDR Management Portal.

Creates clearly labelled FICTIONAL demonstration institutions and test accounts
without deleting or overwriting any existing data.

Demonstration data is strictly labelled as '(Fictional AICTE Demo)' and not
presented as real AICTE-verified institutions.
"""

import os
import sys
from models import db, Institution, User
from app import create_app

FICTIONAL_INSTITUTIONS = [
    {
        "institution_code": "1-DEMO-001",
        "name": "Delhi Institute of Technology (Fictional AICTE Demo)",
        "address": "Plot 12, Institutional Area, Phase 2, New Delhi 110016",
        "contact_email": "finance@dit-demo.edu.in",
    },
    {
        "institution_code": "1-DEMO-002",
        "name": "Mumbai Academy of Science & Technology (Fictional AICTE Demo)",
        "address": "Campus Road, Andheri East, Mumbai, Maharashtra 400069",
        "contact_email": "accounts@mast-demo.edu.in",
    },
    {
        "institution_code": "1-DEMO-003",
        "name": "Bengaluru Institute of Advanced Research (Fictional AICTE Demo)",
        "address": "Electronic City, Phase 1, Hosur Road, Bengaluru, Karnataka 560100",
        "contact_email": "fdrdesk@biar-demo.edu.in",
    },
    {
        "institution_code": "1-DEMO-004",
        "name": "Chennai Engineering College (Fictional AICTE Demo)",
        "address": "Guindy Industrial Estate, Anna Salai, Chennai, Tamil Nadu 600032",
        "contact_email": "registrar@cec-demo.edu.in",
    },
]

DEMO_USERS = [
    {
        "email": "admin@aicte-india.org",
        "full_name": "AICTE Central Administrator",
        "role": User.ROLE_ADMINISTRATOR,
        "account_status": User.STATUS_ACTIVE,
        "password": os.getenv("DEMO_ADMIN_PASSWORD", "AdminSecure2026!"),
        "institution_code": None,
    },
    {
        "email": "regulator@aicte-india.org",
        "full_name": "AICTE Chief Scrutiny Officer",
        "role": User.ROLE_AICTE_OFFICIAL,
        "account_status": User.STATUS_ACTIVE,
        "password": os.getenv("DEMO_OFFICIAL_PASSWORD", "OfficialSecure2026!"),
        "institution_code": None,
    },
    {
        "email": "officer@dit.edu.in",
        "full_name": "Dr. Rajesh Sharma (Finance Desk)",
        "role": User.ROLE_INSTITUTION_USER,
        "account_status": User.STATUS_ACTIVE,
        "password": os.getenv("DEMO_INST_PASSWORD", "DITSecret2026!"),
        "institution_code": "1-DEMO-001",
    },
    {
        "email": "pending.desk@mast.edu.in",
        "full_name": "Prof. Ananya Sen (Pending Verification)",
        "role": User.ROLE_INSTITUTION_USER,
        "account_status": User.STATUS_PENDING,
        "password": os.getenv("DEMO_PENDING_PASSWORD", "PendingSecure2026!"),
        "institution_code": "1-DEMO-002",
    },
]


def seed_database(app=None):
    """
    Safely seed fictional demonstration institutions and baseline test accounts.
    Never overwrites or deletes existing records.
    """
    if app is None:
        app = create_app(os.getenv("FLASK_ENV", "development"))

    with app.app_context():
        print("[*] Checking and seeding demonstration institutions...")
        inst_map = {}

        # 1. Seed Fictional Institutions
        for item in FICTIONAL_INSTITUTIONS:
            existing = Institution.query.filter_by(institution_code=item["institution_code"]).first()
            if not existing:
                inst = Institution(
                    institution_code=item["institution_code"],
                    name=item["name"],
                    address=item["address"],
                    contact_email=item["contact_email"],
                )
                db.session.add(inst)
                db.session.flush()
                print(f"  [+] Created institution: [{inst.institution_code}] {inst.name} (ID: {inst.id})")
                inst_map[inst.institution_code] = inst
            else:
                print(f"  [.] Institution already exists: [{existing.institution_code}] {existing.name} (ID: {existing.id})")
                inst_map[existing.institution_code] = existing

        db.session.commit()

        # 2. Seed Baseline Demo Users
        print("\n[*] Checking and seeding demonstration users...")
        for u_data in DEMO_USERS:
            existing_user = User.query.filter_by(email=u_data["email"].lower()).first()
            if not existing_user:
                inst_id = None
                if u_data["institution_code"]:
                    target_inst = inst_map.get(u_data["institution_code"]) or Institution.query.filter_by(
                        institution_code=u_data["institution_code"]
                    ).first()
                    if target_inst:
                        inst_id = target_inst.id

                user = User(
                    email=u_data["email"].lower(),
                    full_name=u_data["full_name"],
                    role=u_data["role"],
                    account_status=u_data["account_status"],
                    institution_id=inst_id,
                )
                user.set_password(u_data["password"])
                db.session.add(user)
                print(f"  [+] Created user: {user.email} (Role: {user.role}, Status: {user.account_status})")
            else:
                print(f"  [.] User already exists: {existing_user.email} (Status: {existing_user.account_status})")

        db.session.commit()
        print("\n[SUCCESS] Demonstration data successfully initialized.")


if __name__ == "__main__":
    seed_database()
