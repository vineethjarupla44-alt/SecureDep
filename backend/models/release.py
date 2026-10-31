"""
FDR Release and Refund Request Model for AICTE FDR Portal.

Phase 7: Release/Refund Workflow and Advanced Audit Trail
Tracks the complete lifecycle of FDR release/refund requests submitted by institutions:
- Unique request tracking number (e.g. REL-2026-XXXX)
- Multi-level official scrutiny and recommendations
- Multi-level administrator approval and closure
- Strict state machine validation preventing arbitrary status jumps
- Document ownership verification
- Immutable audit logging and notification triggers
"""

import json
from datetime import datetime
from decimal import Decimal
from models import db


class FDRReleaseRequest(db.Model):
    """
    SQLAlchemy model tracking release and refund requests.

    Attributes:
        id (int): Primary key.
        request_number (str): Unique human-readable reference number.
        institution_id (int): Foreign key to the requesting institution.
        fdr_record_id (int): Foreign key to the subject FDR record.
        request_type (str): 'RELEASE', 'REFUND', 'PARTIAL_RELEASE'.
        reason (str): Justification text submitted by institution.
        requested_amount (Decimal): Monetary amount requested for release/refund.
        supporting_document_ids (str): JSON-encoded list of FDRDocument primary keys.
        bank_details (str): JSON-encoded disbursement account/branch details for verification.
        status (str): Workflow state machine status.
        requested_by_id (int): Foreign key to User who created the request.
        assigned_reviewer_id (int): Assigned scrutinizing official.
        created_at (datetime): Submission timestamp (UTC).
        updated_at (datetime): Last status update timestamp (UTC).
    """

    __tablename__ = "fdr_release_requests"

    # Request Types
    TYPE_RELEASE = "RELEASE"
    TYPE_REFUND = "REFUND"
    TYPE_PARTIAL_RELEASE = "PARTIAL_RELEASE"

    ALLOWED_REQUEST_TYPES = {
        TYPE_RELEASE,
        TYPE_REFUND,
        TYPE_PARTIAL_RELEASE,
    }

    # Workflow Statuses (Strict Phase 7 State Machine)
    STATUS_PENDING_SCRUTINY = "PENDING_SCRUTINY"
    STATUS_UNDER_REVIEW = "UNDER_REVIEW"
    STATUS_CORRECTION_REQUIRED = "CORRECTION_REQUIRED"
    STATUS_RESUBMITTED = "RESUBMITTED"
    STATUS_RECOMMENDED_FOR_APPROVAL = "RECOMMENDED_FOR_APPROVAL"
    STATUS_REJECTED = "REJECTED"
    STATUS_APPROVED = "APPROVED"
    STATUS_RELEASED_CLOSED = "RELEASED_CLOSED"

    ALLOWED_STATUSES = {
        STATUS_PENDING_SCRUTINY,
        STATUS_UNDER_REVIEW,
        STATUS_CORRECTION_REQUIRED,
        STATUS_RESUBMITTED,
        STATUS_RECOMMENDED_FOR_APPROVAL,
        STATUS_REJECTED,
        STATUS_APPROVED,
        STATUS_RELEASED_CLOSED,
    }

    TERMINAL_STATUSES = {STATUS_REJECTED, STATUS_RELEASED_CLOSED}

    # Valid State Transitions
    VALID_TRANSITIONS = {
        STATUS_PENDING_SCRUTINY: {
            STATUS_UNDER_REVIEW,
            STATUS_CORRECTION_REQUIRED,
            STATUS_RECOMMENDED_FOR_APPROVAL,
            STATUS_REJECTED,
        },
        STATUS_UNDER_REVIEW: {
            STATUS_CORRECTION_REQUIRED,
            STATUS_RECOMMENDED_FOR_APPROVAL,
            STATUS_REJECTED,
        },
        STATUS_CORRECTION_REQUIRED: {
            STATUS_RESUBMITTED,
        },
        STATUS_RESUBMITTED: {
            STATUS_UNDER_REVIEW,
            STATUS_CORRECTION_REQUIRED,
            STATUS_RECOMMENDED_FOR_APPROVAL,
            STATUS_REJECTED,
        },
        STATUS_RECOMMENDED_FOR_APPROVAL: {
            STATUS_APPROVED,
            STATUS_REJECTED,
            STATUS_CORRECTION_REQUIRED,
        },
        STATUS_APPROVED: {
            STATUS_RELEASED_CLOSED,
        },
        STATUS_REJECTED: set(),
        STATUS_RELEASED_CLOSED: set(),
    }

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)

    request_number = db.Column(
        db.String(50),
        unique=True,
        nullable=False,
        index=True,
        comment="Unique reference number, e.g. REL-2026-XXXX",
    )

    institution_id = db.Column(
        db.Integer,
        db.ForeignKey("institutions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="References institutions.id for multi-tenant isolation",
    )

    fdr_record_id = db.Column(
        db.Integer,
        db.ForeignKey("fdr_records.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="References fdr_records.id",
    )

    request_type = db.Column(
        db.String(50),
        default=TYPE_RELEASE,
        nullable=False,
        index=True,
        comment="RELEASE, REFUND, PARTIAL_RELEASE",
    )

    reason = db.Column(
        db.Text,
        nullable=False,
        comment="Detailed reason and justification for deposit release/refund",
    )

    requested_amount = db.Column(
        db.Numeric(15, 2),
        nullable=False,
        comment="Amount to be released or refunded in INR",
    )

    # Document references (stored as JSON array of document IDs, e.g. "[1, 2]")
    supporting_document_ids = db.Column(
        db.Text,
        nullable=True,
        comment="JSON array of associated FDRDocument IDs",
    )

    # Recorded recipient account info for disbursement verification (no external bank API transfer claimed)
    bank_details = db.Column(
        db.Text,
        nullable=True,
        comment="JSON object of account/branch details for manual finance verification",
    )

    status = db.Column(
        db.String(50),
        default=STATUS_PENDING_SCRUTINY,
        nullable=False,
        index=True,
        comment="Current workflow state",
    )

    requested_by_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="References users.id of submitter",
    )

    assigned_reviewer_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="References users.id of assigned official",
    )

    # -------------------------------------------------------------------------
    # Stage 1: Official Scrutiny Details
    # -------------------------------------------------------------------------
    scrutinized_by_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    scrutiny_action = db.Column(db.String(50), nullable=True)
    scrutiny_remarks = db.Column(db.Text, nullable=True)
    scrutiny_completed_at = db.Column(db.DateTime, nullable=True)
    correction_remarks = db.Column(db.Text, nullable=True)

    # -------------------------------------------------------------------------
    # Stage 2: Final Multi-Level Approval Details (Admin Authority)
    # -------------------------------------------------------------------------
    approved_by_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    approval_decision = db.Column(db.String(50), nullable=True)
    approval_remarks = db.Column(db.Text, nullable=True)
    approved_at = db.Column(db.DateTime, nullable=True)

    # -------------------------------------------------------------------------
    # Stage 3: Settlement & Closure Details
    # -------------------------------------------------------------------------
    closed_by_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    closure_reference = db.Column(
        db.String(100),
        nullable=True,
        comment="Physical AICTE sanction order or manual disbursement voucher reference",
    )
    closure_remarks = db.Column(db.Text, nullable=True)
    closed_at = db.Column(db.DateTime, nullable=True)

    # Timestamps
    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        nullable=False,
        comment="Submission timestamp (UTC)",
    )
    updated_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
        comment="Last update timestamp (UTC)",
    )

    # Relationships
    institution = db.relationship("Institution", backref=db.backref("release_requests", lazy="select"))
    fdr_record = db.relationship("FDRRecord", backref=db.backref("release_requests", lazy="select"))
    requested_by = db.relationship("User", foreign_keys=[requested_by_id])
    assigned_reviewer = db.relationship("User", foreign_keys=[assigned_reviewer_id])
    scrutinizer = db.relationship("User", foreign_keys=[scrutinized_by_id])
    approver = db.relationship("User", foreign_keys=[approved_by_id])
    closer = db.relationship("User", foreign_keys=[closed_by_id])

    audit_logs = db.relationship(
        "FDRAuditLog",
        foreign_keys="FDRAuditLog.release_request_id",
        backref="release_request",
        lazy="dynamic",
        order_by="FDRAuditLog.created_at.desc()",
    )

    @classmethod
    def generate_request_number(cls):
        """Generate a sequential unique reference number (e.g. REL-2026-00001)."""
        year = datetime.utcnow().year
        count = cls.query.filter(cls.request_number.like(f"REL-{year}-%")).count() + 1
        return f"REL-{year}-{count:05d}"

    def can_transition_to(self, target_status):
        """
        Validate whether transitioning to target_status is valid according to
        the Phase 7 workflow state machine.

        Returns:
            (bool, str): (True, None) if permitted, or (False, error_reason).
        """
        if self.status in self.TERMINAL_STATUSES:
            return False, f"Request {self.request_number} is in a terminal state ({self.status}) and cannot be modified."

        allowed_targets = self.VALID_TRANSITIONS.get(self.status, set())
        if target_status not in allowed_targets:
            return False, (
                f"Invalid status transition from '{self.status}' to '{target_status}'. "
                f"Permitted next states: {', '.join(sorted(allowed_targets)) or 'None'}."
            )

        return True, None

    def get_document_ids_list(self):
        """Safely parse supporting_document_ids from JSON."""
        if not self.supporting_document_ids:
            return []
        try:
            parsed = json.loads(self.supporting_document_ids)
            if isinstance(parsed, list):
                return [int(x) for x in parsed if str(x).isdigit()]
            return []
        except (ValueError, TypeError):
            return []

    def set_document_ids_list(self, doc_ids):
        """Serialize a list of document IDs to JSON."""
        if not doc_ids:
            self.supporting_document_ids = "[]"
        else:
            clean_ids = [int(x) for x in doc_ids if str(x).isdigit()]
            self.supporting_document_ids = json.dumps(clean_ids)

    def get_bank_details_dict(self):
        """Safely parse bank_details from JSON."""
        if not self.bank_details:
            return {}
        try:
            parsed = json.loads(self.bank_details)
            return parsed if isinstance(parsed, dict) else {}
        except (ValueError, TypeError):
            return {}

    def set_bank_details_dict(self, bank_dict):
        """Serialize bank details dictionary to JSON."""
        if not bank_dict or not isinstance(bank_dict, dict):
            self.bank_details = "{}"
        else:
            self.bank_details = json.dumps(bank_dict)

    def to_dict(self, include_audit=False):
        """
        Serialize release request to dictionary for API responses.
        """
        data = {
            "id": self.id,
            "request_number": self.request_number,
            "institution_id": self.institution_id,
            "institution_name": self.institution.name if self.institution else None,
            "institution_code": self.institution.institution_code if self.institution else None,
            "fdr_record_id": self.fdr_record_id,
            "fdr_number": self.fdr_record.fdr_number if self.fdr_record else None,
            "fdr_deposit_amount": float(self.fdr_record.deposit_amount) if self.fdr_record else 0.0,
            "fdr_status": self.fdr_record.status if self.fdr_record else None,
            "fdr_issuing_bank": self.fdr_record.issuing_bank if self.fdr_record else None,
            "fdr_maturity_date": self.fdr_record.maturity_date.isoformat() if (self.fdr_record and self.fdr_record.maturity_date) else None,
            "request_type": self.request_type,
            "reason": self.reason,
            "requested_amount": float(self.requested_amount) if self.requested_amount is not None else 0.0,
            "requested_amount_formatted": f"INR {self.requested_amount:,.2f}" if self.requested_amount is not None else "INR 0.00",
            "supporting_document_ids": self.get_document_ids_list(),
            "bank_details": self.get_bank_details_dict(),
            "status": self.status,
            "requested_by_id": self.requested_by_id,
            "requested_by_email": self.requested_by.email if self.requested_by else None,
            "requested_by_name": self.requested_by.full_name if self.requested_by else None,
            "assigned_reviewer_id": self.assigned_reviewer_id,
            "assigned_reviewer_name": self.assigned_reviewer.full_name if self.assigned_reviewer else None,
            "scrutiny": {
                "scrutinized_by_id": self.scrutinized_by_id,
                "scrutinized_by_email": self.scrutinizer.email if self.scrutinizer else None,
                "scrutiny_action": self.scrutiny_action,
                "scrutiny_remarks": self.scrutiny_remarks,
                "correction_remarks": self.correction_remarks,
                "scrutiny_completed_at": self.scrutiny_completed_at.isoformat() if self.scrutiny_completed_at else None,
            },
            "approval": {
                "approved_by_id": self.approved_by_id,
                "approved_by_email": self.approver.email if self.approver else None,
                "approval_decision": self.approval_decision,
                "approval_remarks": self.approval_remarks,
                "approved_at": self.approved_at.isoformat() if self.approved_at else None,
            },
            "closure": {
                "closed_by_id": self.closed_by_id,
                "closed_by_email": self.closer.email if self.closer else None,
                "closure_reference": self.closure_reference,
                "closure_remarks": self.closure_remarks,
                "closed_at": self.closed_at.isoformat() if self.closed_at else None,
            },
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

        if include_audit:
            data["audit_history"] = [log.to_dict() for log in self.audit_logs.all()]

        return data

    def __repr__(self):
        return f"<FDRReleaseRequest id={self.id} ref='{self.request_number}' status='{self.status}'>"
