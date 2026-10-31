"""
FDR Audit Log Model for AICTE FDR Portal.

Phases 6 & 7: Advanced Audit Trail and Compliance Logging
Provides an immutable, tamper-resistant audit trail of:
- Instrument lifecycle transitions (active, matured, renewed, released)
- Renewal submissions and reviews
- Release and refund requests, scrutiny observations, multi-level approvals, and closures
- Document uploads, OCR discrepancy reviews, and alert acknowledgments

All entries record:
- Actor user ID and role
- Action performed
- Entity type and entity ID
- Previous and new values
- Timestamp (UTC)
- Reason or remarks
- Relevant request or FDR reference
- Caller IP address
"""

from datetime import datetime
from models import db


class FDRAuditLog(db.Model):
    """
    SQLAlchemy model tracking immutable audit log entries.
    Ordinary users cannot modify or delete these records.
    """

    __tablename__ = "fdr_audit_logs"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)

    # Entity Identification
    entity_type = db.Column(
        db.String(50),
        default="FDR_RECORD",
        nullable=False,
        index=True,
        comment="FDR_RECORD, RELEASE_REQUEST, RENEWAL_REQUEST, DOCUMENT, ALERT, USER",
    )
    entity_id = db.Column(
        db.Integer,
        nullable=True,
        index=True,
        comment="Primary key of the affected entity",
    )

    # Foreign Keys
    fdr_record_id = db.Column(
        db.Integer,
        db.ForeignKey("fdr_records.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="References fdr_records.id if applicable",
    )
    release_request_id = db.Column(
        db.Integer,
        db.ForeignKey("fdr_release_requests.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="References fdr_release_requests.id if applicable",
    )
    institution_id = db.Column(
        db.Integer,
        db.ForeignKey("institutions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="References institutions.id for multi-tenant isolation",
    )
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="References users.id of actor",
    )

    # Actor Details
    actor_role = db.Column(
        db.String(50),
        nullable=True,
        index=True,
        comment="Role of the actor at time of action (institution_user, aicte_official, administrator)",
    )

    # Event Details
    action = db.Column(
        db.String(100),
        nullable=False,
        index=True,
        comment="Action performed (e.g. RELEASE_SUBMITTED, SCRUTINY_RECOMMENDED, RELEASE_APPROVED)",
    )
    previous_state = db.Column(
        db.Text,
        nullable=True,
        comment="JSON snapshot or string of state before action",
    )
    new_state = db.Column(
        db.Text,
        nullable=True,
        comment="JSON snapshot or string of state after action",
    )
    remarks = db.Column(
        db.Text,
        nullable=True,
        comment="Reason, scrutiny notes, or justification provided by actor",
    )
    details = db.Column(
        db.Text,
        nullable=True,
        comment="Additional contextual JSON metadata",
    )
    ip_address = db.Column(
        db.String(45),
        nullable=True,
        comment="Client IP address",
    )
    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        nullable=False,
        index=True,
        comment="Audit timestamp (UTC)",
    )

    # Relationships
    user = db.relationship("User", foreign_keys=[user_id])
    fdr_record = db.relationship("FDRRecord", foreign_keys=[fdr_record_id])
    institution = db.relationship("Institution", foreign_keys=[institution_id])

    def to_dict(self):
        """Serialize audit log to dictionary."""
        return {
            "id": self.id,
            "entity_type": self.entity_type,
            "entity_id": self.entity_id,
            "fdr_record_id": self.fdr_record_id,
            "release_request_id": self.release_request_id,
            "institution_id": self.institution_id,
            "user_id": self.user_id,
            "actor_email": self.user.email if self.user else None,
            "actor_name": self.user.full_name if self.user else None,
            "actor_role": self.actor_role or (self.user.role if self.user else None),
            "action": self.action,
            "previous_state": self.previous_state,
            "new_state": self.new_state,
            "remarks": self.remarks,
            "details": self.details,
            "ip_address": self.ip_address,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self):
        return f"<FDRAuditLog id={self.id} action='{self.action}' entity='{self.entity_type}:{self.entity_id}'>"
