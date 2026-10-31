"""
AI and Machine Learning Models for AICTE FDR Portal.

Phase 8: Advanced AI & Machine Learning Intelligence
Persists:
- FDRDuplicateCandidate : Flagged exact and near-duplicate FDR candidate pairs with similarity scores
- FDRRiskAssessment     : Explainable risk scores, anomaly metrics, and rule/ML factor breakdowns
"""

import json
from datetime import datetime
from models import db


class FDRDuplicateCandidate(db.Model):
    """
    SQLAlchemy model tracking suspect duplicate FDR pairs detected by AI engine.

    Attributes:
        id (int): Primary key.
        primary_fdr_id (int): Original or reference FDRRecord.
        duplicate_fdr_id (int): Suspected duplicate FDRRecord.
        match_type (str): EXACT_FDR_NUMBER, DUPLICATE_DOC_HASH, FUZZY_FDR_NUMBER, CROSS_INSTITUTION_BANK_REF, SIMILAR_METRICS.
        similarity_score (float): Confidence score between 0.0 and 1.0.
        matching_fields (str): JSON list of matching attributes.
        explanation (str): Human-readable explanation of duplicate indicators.
        status (str): UNREVIEWED, CONFIRMED_DUPLICATE, FALSE_POSITIVE, RESOLVED.
        reviewed_by_id (int): Reviewing official.
        reviewed_at (datetime): Review timestamp.
        review_remarks (str): Reviewer observations.
    """

    __tablename__ = "fdr_duplicate_candidates"

    MATCH_EXACT_NUMBER = "EXACT_FDR_NUMBER"
    MATCH_DOC_HASH = "DUPLICATE_DOC_HASH"
    MATCH_FUZZY_NUMBER = "FUZZY_FDR_NUMBER"
    MATCH_CROSS_INSTITUTION = "CROSS_INSTITUTION_BANK_REF"
    MATCH_SIMILAR_METRICS = "SIMILAR_METRICS"

    STATUS_UNREVIEWED = "UNREVIEWED"
    STATUS_CONFIRMED = "CONFIRMED_DUPLICATE"
    STATUS_FALSE_POSITIVE = "FALSE_POSITIVE"
    STATUS_RESOLVED = "RESOLVED"

    ALLOWED_STATUSES = {
        STATUS_UNREVIEWED,
        STATUS_CONFIRMED,
        STATUS_FALSE_POSITIVE,
        STATUS_RESOLVED,
    }

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)

    primary_fdr_id = db.Column(
        db.Integer,
        db.ForeignKey("fdr_records.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    duplicate_fdr_id = db.Column(
        db.Integer,
        db.ForeignKey("fdr_records.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    match_type = db.Column(
        db.String(50),
        nullable=False,
        index=True,
    )
    similarity_score = db.Column(
        db.Float,
        nullable=False,
    )
    matching_fields = db.Column(
        db.Text,
        nullable=True,
    )
    explanation = db.Column(
        db.Text,
        nullable=True,
        default="",
    )
    status = db.Column(
        db.String(50),
        default=STATUS_UNREVIEWED,
        nullable=False,
        index=True,
    )

    # Review Audit Trail
    reviewed_by_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    reviewed_at = db.Column(db.DateTime, nullable=True)
    review_remarks = db.Column(db.Text, nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    primary_fdr = db.relationship("FDRRecord", foreign_keys=[primary_fdr_id], backref=db.backref("duplicate_flags_as_primary", lazy="dynamic"))
    duplicate_fdr = db.relationship("FDRRecord", foreign_keys=[duplicate_fdr_id], backref=db.backref("duplicate_flags_as_duplicate", lazy="dynamic"))
    reviewed_by = db.relationship("User", foreign_keys=[reviewed_by_id])

    def get_matching_fields_list(self):
        """Safely parse matching_fields from JSON."""
        if not self.matching_fields:
            return []
        try:
            parsed = json.loads(self.matching_fields)
            return parsed if isinstance(parsed, list) else []
        except (ValueError, TypeError):
            return []

    def set_matching_fields_list(self, fields_list):
        """Serialize matching fields list to JSON."""
        self.matching_fields = json.dumps(fields_list) if fields_list else "[]"

    def to_dict(self):
        """Serialize candidate record to dictionary."""
        return {
            "id": self.id,
            "primary_fdr_id": self.primary_fdr_id,
            "primary_fdr_number": self.primary_fdr.fdr_number if self.primary_fdr else None,
            "primary_institution_id": self.primary_fdr.institution_id if self.primary_fdr else None,
            "primary_institution_name": self.primary_fdr.institution.name if (self.primary_fdr and self.primary_fdr.institution) else None,
            "duplicate_fdr_id": self.duplicate_fdr_id,
            "duplicate_fdr_number": self.duplicate_fdr.fdr_number if self.duplicate_fdr else None,
            "duplicate_institution_id": self.duplicate_fdr.institution_id if self.duplicate_fdr else None,
            "duplicate_institution_name": self.duplicate_fdr.institution.name if (self.duplicate_fdr and self.duplicate_fdr.institution) else None,
            "match_type": self.match_type,
            "similarity_score": round(self.similarity_score, 4),
            "similarity_percentage": f"{self.similarity_score * 100:.1f}%",
            "matching_fields": self.get_matching_fields_list(),
            "explanation": self.explanation,
            "status": self.status,
            "reviewed_by_id": self.reviewed_by_id,
            "reviewed_by_email": self.reviewed_by.email if self.reviewed_by else None,
            "reviewed_at": self.reviewed_at.isoformat() if self.reviewed_at else None,
            "review_remarks": self.review_remarks,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    def __repr__(self):
        return f"<FDRDuplicateCandidate id={self.id} type='{self.match_type}' score={self.similarity_score:.2f} status='{self.status}'>"


class FDRRiskAssessment(db.Model):
    """
    SQLAlchemy model tracking explainable risk and anomaly evaluations for FDR instruments.

    Attributes:
        id (int): Primary key.
        fdr_record_id (int): Monitored FDRRecord.
        institution_id (int): Owning institution (tenant isolation).
        risk_score (float): Composite risk score from 0 to 100.
        risk_category (str): LOW, MEDIUM, HIGH, CRITICAL.
        anomaly_score (float): Isolation Forest decision score or z-score.
        is_anomaly (bool): True if ML model flags an anomalous pattern.
        rule_score (float): Deterministic rule-based score component.
        ml_score (float): Machine-learning generated score component.
        contributing_factors (str): JSON list of factor dicts with evidence.
        evidence (str): JSON dictionary of raw feature inputs and findings.
        recommended_action (str): Recommended administrative or scrutiny response.
        model_version (str): Identifier of ML/rule model pipeline.
    """

    __tablename__ = "fdr_risk_assessments"

    CATEGORY_LOW = "LOW"
    CATEGORY_MEDIUM = "MEDIUM"
    CATEGORY_HIGH = "HIGH"
    CATEGORY_CRITICAL = "CRITICAL"

    ALLOWED_CATEGORIES = {
        CATEGORY_LOW,
        CATEGORY_MEDIUM,
        CATEGORY_HIGH,
        CATEGORY_CRITICAL,
    }

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)

    fdr_record_id = db.Column(
        db.Integer,
        db.ForeignKey("fdr_records.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    institution_id = db.Column(
        db.Integer,
        db.ForeignKey("institutions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    risk_score = db.Column(db.Float, nullable=False, index=True)
    risk_category = db.Column(db.String(50), nullable=False, index=True)

    anomaly_score = db.Column(db.Float, nullable=True)
    is_anomaly = db.Column(db.Boolean, default=False, nullable=False, index=True)

    rule_score = db.Column(db.Float, default=0.0, nullable=False)
    ml_score = db.Column(db.Float, default=0.0, nullable=False)

    contributing_factors = db.Column(db.Text, nullable=True)
    evidence = db.Column(db.Text, nullable=True)
    recommended_action = db.Column(db.Text, nullable=True)
    model_version = db.Column(db.String(50), default="v1.0.0", nullable=False)

    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)

    # Relationships
    fdr_record = db.relationship("FDRRecord", backref=db.backref("risk_assessments", lazy="dynamic", cascade="all, delete-orphan"))
    institution = db.relationship("Institution", backref=db.backref("risk_assessments", lazy="dynamic"))

    def get_contributing_factors_list(self):
        """Safely parse contributing_factors from JSON."""
        if not self.contributing_factors:
            return []
        try:
            parsed = json.loads(self.contributing_factors)
            return parsed if isinstance(parsed, list) else []
        except (ValueError, TypeError):
            return []

    def set_contributing_factors_list(self, factors):
        """Serialize contributing factors to JSON."""
        self.contributing_factors = json.dumps(factors) if factors else "[]"

    def get_evidence_dict(self):
        """Safely parse evidence from JSON."""
        if not self.evidence:
            return {}
        try:
            parsed = json.loads(self.evidence)
            return parsed if isinstance(parsed, dict) else {}
        except (ValueError, TypeError):
            return {}

    def set_evidence_dict(self, ev_dict):
        """Serialize evidence dictionary to JSON."""
        self.evidence = json.dumps(ev_dict) if ev_dict else "{}"

    def to_dict(self):
        """Serialize risk assessment to dictionary."""
        return {
            "id": self.id,
            "fdr_record_id": self.fdr_record_id,
            "fdr_number": self.fdr_record.fdr_number if self.fdr_record else None,
            "institution_id": self.institution_id,
            "institution_name": self.institution.name if self.institution else None,
            "risk_score": round(self.risk_score, 1),
            "risk_category": self.risk_category,
            "is_anomaly": self.is_anomaly,
            "anomaly_score": round(self.anomaly_score, 4) if self.anomaly_score is not None else None,
            "rule_score": round(self.rule_score, 1),
            "ml_score": round(self.ml_score, 1),
            "contributing_factors": self.get_contributing_factors_list(),
            "evidence": self.get_evidence_dict(),
            "recommended_action": self.recommended_action,
            "model_version": self.model_version,
            "assessed_at": self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self):
        return f"<FDRRiskAssessment id={self.id} fdr_id={self.fdr_record_id} score={self.risk_score:.1f} category='{self.risk_category}'>"
