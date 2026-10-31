"""
Database Initialization Script for FDR Management Portal.

Phases 1-8: Database Tables and Schema Verification

Performs a safe, non-destructive initialization:
1. Verifies connectivity to the MySQL server.
2. Creates the 'fdr_management' database if it does not already exist (does NOT drop or reset existing data).
3. Creates all tables using SQLAlchemy models (db.create_all).
4. Verifies table creation and schema indexes.

Tables verified:
- institutions
- fdr_records
- users
- token_blocklist
- fdr_documents
- ocr_results
- fdr_alerts
- fdr_renewals
- fdr_audit_logs
- fdr_release_requests
- fdr_duplicate_candidates
- fdr_risk_assessments

Usage:
    python init_db.py
"""

import sys
import pymysql
from sqlalchemy import inspect
from config import Config
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
from migrations import ensure_phase8_schema


def initialize_database():
    """
    Safely initialize MySQL database and tables without dropping existing data.
    """
    print("=" * 60)
    print("AICTE FDR Management Portal - Database Initialization")
    print("=" * 60)

    db_host = Config.DB_HOST
    db_port = int(Config.DB_PORT)
    db_user = Config.DB_USER
    db_password = Config.DB_PASSWORD
    db_name = Config.DB_NAME

    print(f"[*] Target Database Host : {db_host}:{db_port}")
    print(f"[*] Target Database Name : {db_name}")
    print(f"[*] Database Username    : {db_user}")

    # Step 1: Connect to MySQL server and ensure database exists
    print("\n[Step 1/3] Checking MySQL Server connection and database existence...")
    try:
        connection = pymysql.connect(
            host=db_host,
            port=db_port,
            user=db_user,
            password=db_password,
            charset="utf8mb4",
            autocommit=True,
        )
        print("  [+] Successfully connected to MySQL Server.")

        with connection.cursor() as cursor:
            # Safe creation: IF NOT EXISTS ensures no existing database is overwritten
            safe_create_db_query = (
                f"CREATE DATABASE IF NOT EXISTS `{db_name}` "
                f"CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
            )
            cursor.execute(safe_create_db_query)
            print(f"  [+] Database '{db_name}' verified (created if not present).")
        connection.close()

    except pymysql.MySQLError as err:
        print("\n" + "!" * 60)
        print("[-] Error connecting to MySQL Server.")
        print(f"    Message: {err.args[1] if len(err.args) > 1 else err}")
        print("!" * 60)
        print("\nTroubleshooting tips for beginners:")
        print("1. Is MySQL Server installed and running?")
        print("   - Check Windows Services: Win+R -> services.msc -> find 'MySQL' or 'MySQL80'")
        print("   - Or if using XAMPP: open XAMPP Control Panel and click 'Start' next to MySQL.")
        print("2. Check credentials in your .env file:")
        print("   - DB_HOST, DB_PORT, DB_USER, DB_PASSWORD")
        print("=" * 60)
        return False

    # Step 2: Create application tables using SQLAlchemy models
    print("\n[Step 2/3] Initializing tables via SQLAlchemy (db.create_all)...")
    app = create_app("development")

    with app.app_context():
        try:
            # The migration is additive and repeatable. It creates missing
            # tables and adds only missing Phase 6, 7 & 8 columns/indexes.
            migration_result = ensure_phase8_schema()
            print("  [+] Safe schema initialization completed successfully.")
            if migration_result["added_columns"]:
                print(f"  [+] Added columns: {', '.join(migration_result['added_columns'])}")
        except Exception as err:
            print(f"[-] Failed to create tables: {err}")
            return False

        # Step 3: Verify created tables and structure
        print("\n[Step 3/3] Inspecting database tables...")
        inspector = inspect(db.engine)
        existing_tables = inspector.get_table_names()

        required_tables = [
            "institutions",
            "fdr_records",
            "users",
            "token_blocklist",
            "fdr_documents",
            "ocr_results",
            "fdr_alerts",
            "fdr_renewals",
            "fdr_audit_logs",
            "fdr_release_requests",
            "fdr_duplicate_candidates",
            "fdr_risk_assessments",
        ]
        all_present = True
        for table in required_tables:
            if table in existing_tables:
                columns = [col["name"] for col in inspector.get_columns(table)]
                print(f"  [+] Table '{table}' verified. Columns: {', '.join(columns)}")
            else:
                print(f"  [-] Table '{table}' was NOT found.")
                all_present = False

        if all_present:
            print("\n" + "=" * 60)
            print("[SUCCESS] All Phase 1-8 database tables are verified and ready!")
            print("=" * 60)
            try:
                from seed_data import seed_database
                seed_database(app)
            except Exception as e:
                print(f"[!] Warning: Seeding check skipped: {e}")
            return True
        else:
            print("\n[-] Some tables were not created.")
            return False


if __name__ == "__main__":
    success = initialize_database()
    sys.exit(0 if success else 1)
