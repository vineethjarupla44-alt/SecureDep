"""
Institution Model for FDR Management Portal.

Represents an AICTE-affiliated institution that maintains Fixed Deposit
Receipts (FDRs) / Security Deposits.
"""

from datetime import datetime
from models import db


class Institution(db.Model):
    """
    SQLAlchemy model representing an educational institution.

    Attributes:
        id (int): Primary key, auto-incrementing integer identifier.
        institution_code (str): Unique official AICTE code (e.g., '1-1002345').
        name (str): Full registered name of the institution.
        address (str): Physical postal address of the institution campus.
        contact_email (str): Primary institutional contact email address.
        created_at (datetime): Timestamp when record was created.
        updated_at (datetime): Timestamp when record was last updated.
        fdr_records (relationship): One-to-many relationship with FDRRecord.
    """

    __tablename__ = "institutions"

    # Primary Key
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)

    # Core required fields with indexes for efficient lookups
    institution_code = db.Column(
        db.String(50),
        unique=True,
        nullable=False,
        index=True,
        comment="Unique AICTE Institution ID code",
    )
    name = db.Column(
        db.String(255),
        nullable=False,
        index=True,
        comment="Full institution name",
    )
    address = db.Column(
        db.Text,
        nullable=False,
        comment="Complete registered institutional campus address",
    )
    contact_email = db.Column(
        db.String(120),
        nullable=False,
        index=True,
        comment="Official contact email",
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

    # One-to-Many Relationship: One Institution has many FDR records
    fdr_records = db.relationship(
        "FDRRecord",
        back_populates="institution",
        cascade="all, delete-orphan",
        lazy="select",
    )

    def to_dict(self):
        """
        Serialize model instance to a standard Python dictionary for JSON responses.
        """
        return {
            "id": self.id,
            "institution_code": self.institution_code,
            "name": self.name,
            "address": self.address,
            "contact_email": self.contact_email,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "fdr_count": len(self.fdr_records) if self.fdr_records else 0,
        }

    def __repr__(self):
        return f"<Institution id={self.id} code='{self.institution_code}' name='{self.name}'>"
