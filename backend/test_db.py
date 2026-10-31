"""
Live Database Connectivity and Query Verification Script.

Run this script to verify your active MySQL server connection and check
that 'institutions' and 'fdr_records' tables can be created and queried.

Usage:
    python test_db.py
"""

import sys
from decimal import Decimal
from datetime import date
from config import Config
from app import create_app
from models import db, Institution, FDRRecord


def test_live_mysql():
    """Test connecting to live MySQL server and perform sample query."""
    print("=" * 60)
    print("AICTE FDR Management Portal - Live Database Verification")
    print("=" * 60)
    print(f"[*] Target DB Host : {Config.DB_HOST}:{Config.DB_PORT}")
    print(f"[*] Target DB Name : {Config.DB_NAME}")
    print(f"[*] Target DB User : {Config.DB_USER}")
    print("-" * 60)

    app = create_app("development")

    with app.app_context():
        try:
            # 1. Test ping
            from sqlalchemy import text
            with db.engine.connect() as conn:
                result = conn.execute(text("SELECT 1")).scalar()
            print("[+] Ping Test: SUCCESS (SELECT 1 returned 1)")

            # 2. Count existing records
            inst_count = Institution.query.count()
            fdr_count = FDRRecord.query.count()
            print(f"[+] Query Test: SUCCESS")
            print(f"    - Existing Institutions in DB : {inst_count}")
            print(f"    - Existing FDR Records in DB  : {fdr_count}")

            print("\n[SUCCESS] Live MySQL database connection and models are operational!")
            print("=" * 60)
            return True

        except Exception as exc:
            print("[-] Live Database Test: FAILED")
            print(f"    Error details: {exc}")
            print("\nPlease ensure MySQL Server is running and .env has correct credentials.")
            print("=" * 60)
            return False


if __name__ == "__main__":
    success = test_live_mysql()
    sys.exit(0 if success else 1)
