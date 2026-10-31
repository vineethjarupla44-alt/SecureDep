"""
OCR Extraction and Discrepancy Analysis Model for AICTE FDR Portal.

Phase 5: Secure Document Processing & OCR
Maintains OCR extraction fields, confidence levels, discrepancy detection
results, and human reviewer audit records.
"""

import json
from datetime import datetime
from models import db


class OCRResult(db.Model):
    """
    SQLAlchemy model representing the results of OCR document extraction
    and discrepancy analysis against an FDR record.

    Attributes:
        id (int): Primary key.
        document_id (int): Foreign key to the processed FDRDocument.
        fdr_record_id (int): Foreign key to the parent FDRRecord.
        raw_text (str): Raw text extracted from document.
        extracted_fdr_number (str): Extracted FDR certificate number.
        extracted_bank_name (str): Extracted issuing bank name.
        extracted_amount (Decimal): Extracted deposit amount in INR.
        extracted_issue_date (date): Extracted issue date.
        extracted_maturity_date (date): Extracted maturity date.
        extracted_institution_name (str): Extracted institution name.
        ocr_engine (str): OCR engine/method used ('Tesseract-OCR' or 'PDF-Native').
        confidence_score (float): Overall extraction confidence score (0.0 - 1.0).
        confidence_level (str): HIGH, MEDIUM, LOW, FAILED.
        review_required (bool): Flag indicating human review is required.
        has_discrepancy (bool): True if any field differs from the FDR record.
        discrepancy_details (str/json): JSON string with field-by-field comparison.
        discrepancy_count (int): Total count of flagged mismatches.
        reviewed_by_id (int): Foreign key to the reviewer User.
        reviewed_at (datetime): Timestamp of review.
        review_decision (str): PENDING_REVIEW, ACCEPTED, REJECTED, CORRECTION_PROPOSED.
        review_notes (str): Reviewer comments.
    """

    __tablename__ = "ocr_results"

    DECISION_PENDING = "PENDING_REVIEW"
    DECISION_ACCEPTED = "ACCEPTED"
    DECISION_REJECTED = "REJECTED"
    DECISION_CORRECTION_PROPOSED = "CORRECTION_PROPOSED"

    ALLOWED_DECISIONS = {
        DECISION_PENDING,
        DECISION_ACCEPTED,
        DECISION_REJECTED,
        DECISION_CORRECTION_PROPOSED,
    }

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)

    document_id = db.Column(
        db.Integer,
        db.ForeignKey("fdr_documents.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
        comment="References fdr_documents.id",
    )
    fdr_record_id = db.Column(
        db.Integer,
        db.ForeignKey("fdr_records.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="References fdr_records.id",
    )

    # Extracted Values
    raw_text = db.Column(db.Text, nullable=True, comment="Full extracted text")
    extracted_fdr_number = db.Column(db.String(100), nullable=True)
    extracted_bank_name = db.Column(db.String(150), nullable=True)
    extracted_amount = db.Column(db.Numeric(15, 2), nullable=True)
    extracted_issue_date = db.Column(db.Date, nullable=True)
    extracted_maturity_date = db.Column(db.Date, nullable=True)
    extracted_institution_name = db.Column(db.String(255), nullable=True)

    # Confidence and Reliability
    ocr_engine = db.Column(db.String(50), default="Tesseract-OCR", nullable=False)
    confidence_score = db.Column(db.Float, default=0.0, nullable=False)
    confidence_level = db.Column(db.String(20), default="LOW", nullable=False)
    review_required = db.Column(db.Boolean, default=True, nullable=False)

    # Discrepancy Detection Flags
    has_discrepancy = db.Column(db.Boolean, default=False, nullable=False)
    discrepancy_details = db.Column(db.Text, nullable=True, comment="JSON serialized discrepancy mapping")
    discrepancy_count = db.Column(db.Integer, default=0, nullable=False)

    # Reviewer Audit Trail
    reviewed_by_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="User ID of authorized reviewer",
    )
    reviewed_at = db.Column(db.DateTime, nullable=True)
    review_decision = db.Column(db.String(50), default=DECISION_PENDING, nullable=False)
    review_notes = db.Column(db.Text, nullable=True)

    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    document = db.relationship("FDRDocument", back_populates="ocr_result")
    fdr_record = db.relationship("FDRRecord", backref=db.backref("ocr_results", lazy="select"))
    reviewer = db.relationship("User", backref=db.backref("reviewed_ocr_results", lazy="select"))

    def get_parsed_discrepancies(self):
        """Parse JSON discrepancy details."""
        if not self.discrepancy_details:
            return {}
        try:
            return json.loads(self.discrepancy_details)
        except (ValueError, TypeError):
            return {"raw": self.discrepancy_details}

    def to_dict(self):
        """
        Serialize OCR results distinguishing OCR extraction, submitted record,
        and discrepancy detection analysis.
        """
        fdr = self.fdr_record
        return {
            "id": self.id,
            "document_id": self.document_id,
            "fdr_record_id": self.fdr_record_id,
            "ocr_engine": self.ocr_engine,
            "confidence_score": round(self.confidence_score, 2),
            "confidence_level": self.confidence_level,
            "review_required": self.review_required,

            # Section 1: OCR Extracted Fields
            "extracted_fields": {
                "fdr_number": self.extracted_fdr_number,
                "issuing_bank": self.extracted_bank_name,
                "deposit_amount": float(self.extracted_amount) if self.extracted_amount is not None else None,
                "issue_date": self.extracted_issue_date.isoformat() if self.extracted_issue_date else None,
                "maturity_date": self.extracted_maturity_date.isoformat() if self.extracted_maturity_date else None,
                "institution_name": self.extracted_institution_name,
            },

            # Section 2: Institution-Submitted Record Values
            "submitted_fdr_values": {
                "fdr_number": fdr.fdr_number if fdr else None,
                "issuing_bank": fdr.issuing_bank if fdr else None,
                "deposit_amount": float(fdr.deposit_amount) if fdr and fdr.deposit_amount is not None else None,
                "issue_date": fdr.issue_date.isoformat() if fdr and fdr.issue_date else None,
                "maturity_date": fdr.maturity_date.isoformat() if fdr and fdr.maturity_date else None,
                "institution_name": fdr.institution.name if fdr and fdr.institution else None,
            },

            # Section 3: Discrepancy Breakdown
            "discrepancy_analysis": {
                "has_discrepancy": self.has_discrepancy,
                "discrepancy_count": self.discrepancy_count,
                "details": self.get_parsed_discrepancies(),
            },

            # Section 4: Human Review & Audit Trail
            "review_audit": {
                "review_decision": self.review_decision,
                "reviewed_by_id": self.reviewed_by_id,
                "reviewer_email": self.reviewer.email if self.reviewer else None,
                "reviewed_at": self.reviewed_at.isoformat() if self.reviewed_at else None,
                "review_notes": self.review_notes,
            },

            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    def __repr__(self):
        return f"<OCRResult id={self.id} doc_id={self.document_id} has_discrepancy={self.has_discrepancy}>"
