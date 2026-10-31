"""Safe, repeatable schema upgrades for Phases 6 & 7.

This project does not use Alembic. The initializer therefore performs only
additive checks: missing tables are created and missing Phase 6 & 7 columns/indexes
are safely added. Existing tables and rows are never dropped, truncated, or rewritten.
"""

from sqlalchemy import inspect, text
from models import db


PHASE6_FDR_COLUMNS = {
    "workflow_status": "VARCHAR(50) NOT NULL DEFAULT 'NONE'",
    "predecessor_id": "INTEGER NULL",
    "renewal_notes": "TEXT NULL",
}

PHASE6_INDEXES = {
    "ix_fdr_records_workflow_status": "workflow_status",
    "ix_fdr_records_predecessor_id": "predecessor_id",
}

PHASE7_AUDIT_COLUMNS = {
    "entity_type": "VARCHAR(50) NOT NULL DEFAULT 'FDR_RECORD'",
    "entity_id": "INTEGER NULL",
    "actor_role": "VARCHAR(50) NULL",
    "previous_state": "TEXT NULL",
    "new_state": "TEXT NULL",
    "remarks": "TEXT NULL",
    "release_request_id": "INTEGER NULL",
}

PHASE7_ALERT_COLUMNS = {
    "release_request_id": "INTEGER NULL",
}


def ensure_phase6_schema():
    """Apply only additive Phase 6 schema changes to the active database."""
    db.create_all()
    inspector = inspect(db.engine)
    existing_columns = {column["name"] for column in inspector.get_columns("fdr_records")}

    with db.engine.begin() as connection:
        for name, definition in PHASE6_FDR_COLUMNS.items():
            if name not in existing_columns:
                connection.execute(text(f"ALTER TABLE fdr_records ADD COLUMN {name} {definition}"))

    inspector = inspect(db.engine)
    existing_indexes = {index["name"] for index in inspector.get_indexes("fdr_records")}
    with db.engine.begin() as connection:
        for index_name, column_name in PHASE6_INDEXES.items():
            if index_name not in existing_indexes:
                connection.execute(text(
                    f"CREATE INDEX {index_name} ON fdr_records ({column_name})"
                ))

    return {
        "status": "success",
        "tables": inspector.get_table_names(),
        "added_columns": sorted(set(PHASE6_FDR_COLUMNS) - existing_columns),
    }


def ensure_phase7_schema():
    """Apply safe, non-destructive additive Phase 7 schema changes."""
    # 1. Ensure all new tables (such as fdr_release_requests) are created
    db.create_all()

    # 2. Add Phase 6 columns if missing
    ensure_phase6_schema()

    added_cols = []
    inspector = inspect(db.engine)

    # 3. Add additive columns to fdr_audit_logs if missing
    if "fdr_audit_logs" in inspector.get_table_names():
        audit_cols = {c["name"] for c in inspector.get_columns("fdr_audit_logs")}
        with db.engine.begin() as connection:
            for col_name, col_def in PHASE7_AUDIT_COLUMNS.items():
                if col_name not in audit_cols:
                    connection.execute(text(f"ALTER TABLE fdr_audit_logs ADD COLUMN {col_name} {col_def}"))
                    added_cols.append(f"fdr_audit_logs.{col_name}")

    # 4. Add additive columns to fdr_alerts if missing
    if "fdr_alerts" in inspector.get_table_names():
        alert_cols = {c["name"] for c in inspector.get_columns("fdr_alerts")}
        with db.engine.begin() as connection:
            for col_name, col_def in PHASE7_ALERT_COLUMNS.items():
                if col_name not in alert_cols:
                    connection.execute(text(f"ALTER TABLE fdr_alerts ADD COLUMN {col_name} {col_def}"))
                    added_cols.append(f"fdr_alerts.{col_name}")

    inspector = inspect(db.engine)
    return {
        "status": "success",
        "tables": inspector.get_table_names(),
        "added_columns": added_cols,
    }


def ensure_phase8_schema():
    """Apply safe, non-destructive additive Phase 8 schema changes."""
    # 1. Ensure Phase 7 baseline
    phase7_res = ensure_phase7_schema()

    # 2. Ensure all Phase 8 models (fdr_duplicate_candidates, fdr_risk_assessments) are created
    db.create_all()

    inspector = inspect(db.engine)
    return {
        "status": "success",
        "tables": inspector.get_table_names(),
        "added_columns": phase7_res.get("added_columns", []),
    }
