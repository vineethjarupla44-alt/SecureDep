"""
FDR Document Model for AICTE FDR Portal.

Phase 5: Secure Document Management
Maintains metadata for scanned FDR receipts, deposit certificates,
and verification documents uploaded by institutions or regulators.
"""

from datetime import datetime
from models import db


class FDRDocument(db.Model):
    """
    SQLAlchemy model representing an uploaded FDR supporting document.

    Attributes:
        id (int): Primary key.
        fdr_record_id (int): Foreign key to the parent FDRRecord.
        institution_id (int): Foreign key to the owning Institution (for multi-tenant isolation).
        uploader_id (int): Foreign key to the User who uploaded the file.
        original_filename (str): Sanitized original client-side filename.
        storage_key (str): Random UUID/hash storage filename (never reveals client filename).
        file_path (str): Relative path to document in private storage folder.
        content_type (str): Verified MIME type (application/pdf, image/jpeg, image/png).
        file_size_bytes (int): Size in bytes.
        file_hash (str): SHA-256 integrity checksum.
        processing_status (str): PENDING, PROCESSING, PROCESSED, FAILED, MANUAL_REVIEW_REQUIRED.
        created_at (datetime): Upload timestamp (UTC).
        updated_at (datetime): Last status update timestamp (UTC).
    """

    __tablename__ = "fdr_documents"

    # Status Constants
    STATUS_PENDING = "PENDING"
    STATUS_PROCESSING = "PROCESSING"
    STATUS_PROCESSED = "PROCESSED"
    STATUS_FAILED = "FAILED"
    STATUS_MANUAL_REVIEW = "MANUAL_REVIEW_REQUIRED"

    ALLOWED_STATUSES = {
        STATUS_PENDING,
        STATUS_PROCESSING,
        STATUS_PROCESSED,
        STATUS_FAILED,
        STATUS_MANUAL_REVIEW,
    }

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)

    # Foreign Keys
    fdr_record_id = db.Column(
        db.Integer,
        db.ForeignKey("fdr_records.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="References fdr_records.id",
    )
    institution_id = db.Column(
        db.Integer,
        db.ForeignKey("institutions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="References institutions.id for tenant isolation",
    )
    uploader_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="References users.id of uploader",
    )

    # File Metadata
    original_filename = db.Column(
        db.String(255),
        nullable=False,
        comment="Sanitized original client filename",
    )
    storage_key = db.Column(
        db.String(64),
        unique=True,
        nullable=False,
        index=True,
        comment="Cryptographically random storage identifier",
    )
    file_path = db.Column(
        db.String(500),
        nullable=False,
        comment="Internal storage path (never exposed in public API)",
    )
    content_type = db.Column(
        db.String(100),
        nullable=False,
        comment="Verified MIME type",
    )
    file_size_bytes = db.Column(
        db.Integer,
        nullable=False,
        comment="Size of file in bytes",
    )
    file_hash = db.Column(
        db.String(64),
        nullable=True,
        index=True,
        comment="SHA-256 file checksum for tamper detection and duplicate detection",
    )

    # Processing State
    processing_status = db.Column(
        db.String(50),
        default=STATUS_PENDING,
        nullable=False,
        index=True,
        comment="PENDING, PROCESSING, PROCESSED, FAILED, MANUAL_REVIEW_REQUIRED",
    )

    # Timestamps
    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        nullable=False,
        comment="UTC upload timestamp",
    )
    updated_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
        comment="UTC status update timestamp",
    )

    # Relationships
    fdr_record = db.relationship("FDRRecord", backref=db.backref("documents", lazy="select", cascade="all, delete-orphan"))
    institution = db.relationship("Institution", backref=db.backref("documents", lazy="select"))
    uploader = db.relationship("User", backref=db.backref("uploaded_documents", lazy="select"))
    ocr_result = db.relationship("OCRResult", back_populates="document", uselist=False, cascade="all, delete-orphan")

    def to_dict(self):
        """
        Serialize document metadata for API response.
        NEVER reveals absolute file_path or server directory structure.
        """
        return {
            "id": self.id,
            "fdr_record_id": self.fdr_record_id,
            "institution_id": self.institution_id,
            "original_filename": self.original_filename,
            "storage_key": self.storage_key,
            "content_type": self.content_type,
            "file_size_bytes": self.file_size_bytes,
            "file_size_formatted": f"{self.file_size_bytes / (1024 * 1024):.2f} MB" if self.file_size_bytes >= 1024 * 1024 else f"{self.file_size_bytes / 1024:.1f} KB",
            "file_hash": self.file_hash,
            "processing_status": self.processing_status,
            "uploader_id": self.uploader_id,
            "uploader_email": self.uploader.email if self.uploader else None,
            "has_ocr_result": self.ocr_result is not None,
            "download_url": f"/api/documents/{self.id}/download",
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    def __repr__(self):
        return f"<FDRDocument id={self.id} fdr_id={self.fdr_record_id} status='{self.processing_status}'>"
