"""
Initial Administrator Setup Utility for AICTE FDR Management Portal.

Phase 4: Controlled Setup Procedure
Allows provisioning the root/first administrator account safely.
Passwords are collected via getpass so they are never printed to the screen,
never saved to shell history, and never logged in console outputs.

Usage:
    Interactive mode:
        python create_admin.py

    Automated/Scripted mode (reading password from environment variable):
        $env:ADMIN_PASSWORD = "YourStrongPassword123"
        python create_admin.py --email admin@aicte-india.org --name "AICTE Central Admin" --use-env
"""

import os
import sys
import getpass
import argparse
from sqlalchemy import func
from app import create_app
from models import db, User
from utils.decorators import validate_email_format, validate_password_strength


def create_initial_admin(email, full_name, password):
    """
    Provision or update an administrator account.
    """
    app = create_app("development")
    with app.app_context():
        email_clean = email.strip().lower()

        # Check existing user
        existing_user = User.query.filter(func.lower(User.email) == email_clean).first()
        if existing_user:
            if existing_user.role == User.ROLE_ADMINISTRATOR:
                print(f"[!] User '{email_clean}' is already an active Administrator (ID: {existing_user.id}).")
                return True
            else:
                print(f"[*] User '{email_clean}' exists with role '{existing_user.role}'. Promoting to Administrator...")
                existing_user.role = User.ROLE_ADMINISTRATOR
                existing_user.account_status = User.STATUS_ACTIVE
                existing_user.institution_id = None
                existing_user.set_password(password)
                db.session.commit()
                print(f"[SUCCESS] User '{email_clean}' promoted to Administrator successfully.")
                return True

        # Create new Administrator
        admin = User(
            email=email_clean,
            full_name=full_name.strip(),
            role=User.ROLE_ADMINISTRATOR,
            account_status=User.STATUS_ACTIVE,
            institution_id=None,
        )
        admin.set_password(password)

        try:
            db.session.add(admin)
            db.session.commit()
            print("\n" + "=" * 60)
            print("[SUCCESS] Initial Administrator account provisioned successfully!")
            print(f"[*] Email     : {admin.email}")
            print(f"[*] Name      : {admin.full_name}")
            print(f"[*] Role      : {admin.role}")
            print(f"[*] Status    : {admin.account_status}")
            print("=" * 60)
            print("[NOTE] Password was securely hashed with PBKDF2-HMAC-SHA256 and stored.")
            return True
        except Exception as exc:
            db.session.rollback()
            print(f"[-] Database error creating administrator: {exc}")
            return False


def main():
    parser = argparse.ArgumentParser(description="Create initial administrator account for AICTE FDR Portal.")
    parser.add_argument("--email", help="Administrator email address")
    parser.add_argument("--name", help="Administrator full name")
    parser.add_argument("--use-env", action="store_true", help="Read password from ADMIN_PASSWORD environment variable")

    args = parser.parse_args()

    print("=" * 60)
    print("AICTE FDR Portal - Administrator Provisioning")
    print("=" * 60)

    # 1. Email
    email = args.email
    if not email:
        email = input("Enter Administrator Email: ").strip()

    valid_email, err_email = validate_email_format(email)
    if not valid_email:
        print(f"[-] Error: {err_email}")
        sys.exit(1)

    # 2. Name
    name = args.name
    if not name:
        name = input("Enter Administrator Full Name: ").strip()
        if not name:
            name = "AICTE System Administrator"

    # 3. Password
    if args.use_env:
        password = os.getenv("ADMIN_PASSWORD", "")
        if not password:
            print("[-] Error: --use-env specified but ADMIN_PASSWORD environment variable is empty.")
            sys.exit(1)
    else:
        # Prompt password securely without terminal echo
        password = getpass.getpass("Enter Administrator Password (min 8 chars, 1 letter, 1 number): ")
        confirm = getpass.getpass("Confirm Password: ")
        if password != confirm:
            print("[-] Error: Passwords do not match.")
            sys.exit(1)

    valid_pass, err_pass = validate_password_strength(password)
    if not valid_pass:
        print(f"[-] Error: {err_pass}")
        sys.exit(1)

    success = create_initial_admin(email, name, password)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
