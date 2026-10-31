"""
FDR Renewal Request Model for AICTE FDR Portal.

Phase 6: Renewal and Replacement Workflow
Tracks formal proposals to renew or replace an existing (maturing/matured) FDR.
Preserves predecessor records and links them to replacement instruments without
overwriting historical data.
"""

from datetime import datetime
from models import db


class FDRRenewalRequest(db.Model):
    """
    SQLAlchemy model tracking renewal and replacement proposals.

    Attributes:
        id (int): Primary key.
        original_fdr_id (int): Foreign key to the maturing/predecessor FDRRecord.
        replacement_fdr_id (int): Foreign key to the newly created replacement FDRRecord.
        institution_id (int): Foreign key to the institution for tenant isolation.
        submitted_by_id (int): User who submitted the renewal proposal.
        status (str): PENDING_REVIEW, APPROVED, REJECTED.
        submission_notes (str): Reason/context from the institution.
        reviewer_id (int): Official who reviewed the renewal.
        reviewed_at (datetime): Timestamp of review.
        review_decision (str): APPROVED, REJECTED.
        review_notes (str): Reviewer justification/feedback.
        created_at (datetime): Submission timestamp (UTC).
        updated_at (datetime): Status update timestamp (UTC).
    """

    __tablename__ = "fdr_renewals"

    STATUS_PENDING = "PENDING_REVIEW"
    STATUS_APPROVED = "APPROVED"
    STATUS_REJECTED = "REJECTED"

    ALLOWED_STATUSES = {STATUS_PENDING, STATUS_APPROVED, STATUS_REJECTED}

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)

    original_fdr_id = db.Column(
        db.Integer,
        db.ForeignKey("fdr_records.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="References maturing/predecessor FDRRecord",
    )
    replacement_fdr_id = db.Column(
        db.Integer,
        db.ForeignKey("fdr_records.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="References newly created replacement FDRRecord",
    )
    institution_id = db.Column(
        db.Integer,
        db.ForeignKey("institutions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="References institutions.id",
    )

    submitted_by_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    status = db.Column(
        db.String(50),
        default=STATUS_PENDING,
        nullable=False,
        index=True,
        comment="PENDING_REVIEW, APPROVED, REJECTED",
    )
    submission_notes = db.Column(db.Text, nullable=True)

    # Reviewer Audit Trail
    reviewer_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    reviewed_at = db.Column(db.DateTime, nullable=True)
    review_decision = db.Column(db.String(50), nullable=True)
    review_notes = db.Column(db.Text, nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    original_fdr = db.relationship("FDRRecord", foreign_keys=[original_fdr_id], backref=db.backref("renewal_requests", lazy="select"))
    replacement_fdr = db.relationship("FDRRecord", foreign_keys=[replacement_fdr_id])
    institution = db.relationship("Institution", backref=db.backref("renewal_requests", lazy="select"))
    submitted_by = db.relationship("User", foreign_keys=[submitted_by_id])
    reviewer = db.relationship("User", foreign_keys=[reviewer_id])

    def to_dict(self):
        """Serialize renewal request for API responses."""
        return {
            "id": self.id,
            "original_fdr_id": self.original_fdr_id,
            "original_fdr_number": self.original_fdr.fdr_number if self.original_fdr else None,
            "replacement_fdr_id": self.replacement_fdr_id,
            "replacement_fdr_number": self.replacement_fdr.fdr_number if self.replacement_fdr else None,
            "institution_id": self.institution_id,
            "institution_name": self.institution.name if self.institution else None,
            "status": self.status,
            "submission_notes": self.submission_notes,
            "submitted_by_id": self.submitted_by_id,
            "submitted_by_email": self.submitted_by.email if self.submitted_by else None,
            "reviewer_id": self.reviewer_id,
            "reviewer_email": self.reviewer.email if self.reviewer else None,
            "reviewed_at": self.reviewed_at.isoformat() if self.reviewed_at else None,
            "review_decision": self.review_decision,
            "review_notes": self.review_notes,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    def __repr__(self):
        return f"<FDRRenewalRequest id={self.id} orig_fdr={self.original_fdr_id} status='{self.status}'>"
