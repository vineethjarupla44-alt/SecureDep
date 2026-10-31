"""
FDRRecord Model for FDR Management Portal.

Represents a Fixed Deposit Receipt (FDR) / Security Deposit submitted by
an institution to AICTE as a security deposit.
Includes predecessor tracking for renewals and workflow status.
"""

from datetime import datetime, date
from decimal import Decimal
from models import db
from utils.time import local_business_date


class FDRRecord(db.Model):
    """
    SQLAlchemy model representing an FDR (Fixed Deposit Receipt) record.

    Attributes:
        id (int): Primary key, auto-incrementing integer identifier.
        institution_id (int): Foreign key referencing institutions.id.
        fdr_number (str): Unique FDR certificate receipt number.
        issuing_bank (str): Name of the bank issuing the FDR.
        deposit_amount (Decimal): Monetary value of the deposit (15 digits, 2 decimals).
        issue_date (date): Date on which the FDR was issued by the bank.
        maturity_date (date): Date on which the FDR reaches maturity.
        status (str): Status of the deposit ('ACTIVE', 'MATURED', 'RELEASED', 'LIEN_MARKED', 'RENEWED').
        workflow_status (str): Operational status ('NONE', 'RENEWAL_SUBMITTED', 'RENEWAL_APPROVED', 'RENEWAL_REJECTED').
        predecessor_id (int): Foreign key referencing prior FDR if this is a renewed instrument.
        renewal_notes (str): Contextual notes regarding renewal or replacement.
        created_at (datetime): Timestamp when record was created.
        updated_at (datetime): Timestamp when record was last updated.
        institution (relationship): Many-to-one relationship with Institution.
    """

    __tablename__ = "fdr_records"

    # Status Constants
    STATUS_ACTIVE = "ACTIVE"
    STATUS_MATURED = "MATURED"
    STATUS_RELEASED = "RELEASED"
    STATUS_LIEN_MARKED = "LIEN_MARKED"
    STATUS_RENEWED = "RENEWED"
    STATUS_PENDING_RENEWAL = "PENDING_RENEWAL"

    ALLOWED_STATUSES = {
        STATUS_ACTIVE,
        STATUS_MATURED,
        STATUS_RELEASED,
        STATUS_LIEN_MARKED,
        STATUS_RENEWED,
        STATUS_PENDING_RENEWAL,
    }

    # Workflow Status Constants
    WORKFLOW_NONE = "NONE"
    WORKFLOW_RENEWAL_SUBMITTED = "RENEWAL_SUBMITTED"
    WORKFLOW_RENEWAL_APPROVED = "RENEWAL_APPROVED"
    WORKFLOW_RENEWAL_REJECTED = "RENEWAL_REJECTED"

    ALLOWED_WORKFLOW_STATUSES = {
        WORKFLOW_NONE,
        WORKFLOW_RENEWAL_SUBMITTED,
        WORKFLOW_RENEWAL_APPROVED,
        WORKFLOW_RENEWAL_REJECTED,
    }

    # Primary Key
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)

    # Foreign Key to Institution
    institution_id = db.Column(
        db.Integer,
        db.ForeignKey("institutions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="References institutions.id",
    )

    # FDR Identification & Bank Details
    fdr_number = db.Column(
        db.String(100),
        unique=True,
        nullable=False,
        index=True,
        comment="Unique bank FDR receipt number",
    )
    issuing_bank = db.Column(
        db.String(150),
        nullable=False,
        index=True,
        comment="Name of the issuing bank / branch",
    )

    # Monetary value: Numeric(15, 2) guarantees exact precision for financial calculations
    deposit_amount = db.Column(
        db.Numeric(15, 2),
        nullable=False,
        comment="Deposit amount in INR with 2 decimal places",
    )

    # Important Dates
    issue_date = db.Column(
        db.Date,
        nullable=False,
        comment="Date of FDR creation/issue",
    )
    maturity_date = db.Column(
        db.Date,
        nullable=False,
        index=True,
        comment="Date when deposit matures",
    )

    # Lifecycle Status
    status = db.Column(
        db.String(50),
        default=STATUS_ACTIVE,
        nullable=False,
        index=True,
        comment="Status: ACTIVE, MATURED, RELEASED, LIEN_MARKED, RENEWED",
    )

    # Renewal & Workflow tracking (Phase 6)
    workflow_status = db.Column(
        db.String(50),
        default=WORKFLOW_NONE,
        nullable=False,
        index=True,
        comment="NONE, RENEWAL_SUBMITTED, RENEWAL_APPROVED, RENEWAL_REJECTED",
    )
    predecessor_id = db.Column(
        db.Integer,
        db.ForeignKey("fdr_records.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="References prior FDRRecord if this is a renewed instrument",
    )
    renewal_notes = db.Column(
        db.Text,
        nullable=True,
        comment="Historical notes for renewal/replacement",
    )

    # Auditing timestamps
    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        nullable=False,
        comment="Timestamp of creation (UTC)",
    )
    updated_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
        comment="Timestamp of last update (UTC)",
    )

    # Relationships
    institution = db.relationship("Institution", back_populates="fdr_records")
    predecessor = db.relationship("FDRRecord", remote_side=[id], backref=db.backref("successors", lazy="select"))

    @property
    def days_to_maturity(self):
        """Calculate days remaining until maturity relative to today."""
        if not self.maturity_date:
            return None
        return (self.maturity_date - local_business_date()).days

    @property
    def maturity_category(self):
        """
        Evaluate maturity category:
        - RENEWED: Instrument was already renewed by another instrument
        - RELEASED: Instrument was officially released
        - RENEWAL_PENDING: Has pending renewal submission
        - MATURED: days <= 0
        - EXPIRING_SOON: 1 <= days <= 30
        - ACTIVE: days > 30
        """
        if self.status == self.STATUS_RENEWED:
            return "RENEWED"
        if self.status == self.STATUS_RELEASED:
            return "RELEASED"
        if self.status == self.STATUS_PENDING_RENEWAL or self.workflow_status == self.WORKFLOW_RENEWAL_SUBMITTED:
            return "RENEWAL_PENDING"

        days = self.days_to_maturity
        if days is None:
            return "UNKNOWN"
        if days <= 0:
            return "MATURED"
        if days <= 30:
            return "EXPIRING_SOON"
        return "ACTIVE"

    def to_dict(self):
        """
        Serialize model instance to a standard Python dictionary for JSON responses.
        """
        return {
            "id": self.id,
            "institution_id": self.institution_id,
            "fdr_number": self.fdr_number,
            "issuing_bank": self.issuing_bank,
            "deposit_amount": float(self.deposit_amount) if self.deposit_amount is not None else 0.0,
            "deposit_amount_formatted": f"INR {self.deposit_amount:,.2f}" if self.deposit_amount is not None else "INR 0.00",
            "issue_date": self.issue_date.isoformat() if self.issue_date else None,
            "maturity_date": self.maturity_date.isoformat() if self.maturity_date else None,
            "status": self.status,
            "workflow_status": self.workflow_status,
            "predecessor_id": self.predecessor_id,
            "renewal_notes": self.renewal_notes,
            "days_to_maturity": self.days_to_maturity,
            "maturity_category": self.maturity_category,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    def __repr__(self):
        return f"<FDRRecord id={self.id} fdr='{self.fdr_number}' amount={self.deposit_amount} status='{self.status}' workflow='{self.workflow_status}'>"
