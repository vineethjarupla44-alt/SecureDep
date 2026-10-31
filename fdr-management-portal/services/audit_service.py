"""
Audit Logging Service for AICTE FDR Portal.

Phases 6 & 7: Advanced Audit Trail
Provides a centralized, tamper-resistant API to record state transitions,
administrative scrutiny, multi-level approvals, document actions, and security events.
"""

import json
from datetime import datetime
from flask import request, has_request_context
from flask_jwt_extended import current_user
from models import db, FDRAuditLog


def record_audit_event(
    action,
    entity_type="FDR_RECORD",
    entity_id=None,
    user=None,
    institution_id=None,
    fdr_record_id=None,
    release_request_id=None,
    previous_state=None,
    new_state=None,
    remarks=None,
    details=None,
    ip_address=None,
    commit=False,
):
    """
    Record an immutable audit log entry.

    Args:
        action (str): Event name (e.g. 'RELEASE_SUBMITTED', 'SCRUTINY_OBSERVATION', 'APPROVAL_GRANTED').
        entity_type (str): 'FDR_RECORD', 'RELEASE_REQUEST', 'RENEWAL_REQUEST', 'DOCUMENT', etc.
        entity_id (int): Primary key ID of the affected entity.
        user (User, optional): User instance. If omitted, uses current_user if in request context.
        institution_id (int, optional): Owning institution ID.
        fdr_record_id (int, optional): Parent FDRRecord ID if applicable.
        release_request_id (int, optional): Parent FDRReleaseRequest ID if applicable.
        previous_state (dict|str, optional): Snapshot before transition.
        new_state (dict|str, optional): Snapshot after transition.
        remarks (str, optional): User or reviewer remarks.
        details (dict|str, optional): Extra structured metadata.
        ip_address (str, optional): Client IP. Defaults to request.remote_addr.
        commit (bool): Whether to db.session.commit() immediately. Default False.

    Returns:
        FDRAuditLog: The created audit log entity.
    """
    # Resolve actor
    actor_user = user
    if actor_user is None and has_request_context():
        try:
            actor_user = current_user
        except Exception:
            actor_user = None

    user_id = actor_user.id if actor_user else None
    actor_role = actor_user.role if actor_user else None

    # Resolve IP address
    client_ip = ip_address
    if client_ip is None and has_request_context():
        try:
            client_ip = request.remote_addr
        except Exception:
            client_ip = None

    # Format snapshots as JSON if passed as dicts
    def _serialize_json(val):
        if val is None:
            return None
        if isinstance(val, (dict, list)):
            try:
                return json.dumps(val, default=str)
            except Exception:
                return str(val)
        return str(val)

    audit_entry = FDRAuditLog(
        entity_type=str(entity_type),
        entity_id=entity_id,
        fdr_record_id=fdr_record_id,
        release_request_id=release_request_id,
        institution_id=institution_id,
        user_id=user_id,
        actor_role=actor_role,
        action=str(action),
        previous_state=_serialize_json(previous_state),
        new_state=_serialize_json(new_state),
        remarks=str(remarks).strip() if remarks else None,
        details=_serialize_json(details),
        ip_address=client_ip,
        created_at=datetime.utcnow(),
    )

    db.session.add(audit_entry)

    if commit:
        try:
            db.session.commit()
        except Exception:
            db.session.rollback()
            raise

    return audit_entry
