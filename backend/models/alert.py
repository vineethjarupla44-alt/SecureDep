"""
FDR Alert Model for AICTE FDR Portal.

Phase 6: Maturity Tracking, Renewal Monitoring and Alerts
Persists automated alerts generated before and at maturity (30d, 15d, 7d, matured, overdue).
Enforces idempotency using unique idempotency_key to prevent duplicate alerts.
"""

from datetime import datetime
from models import db


class FDRAlert(db.Model):
    """
    SQLAlchemy model representing an automated or persisted notification.

    Attributes:
        id (int): Primary key.
        fdr_record_id (int): Foreign key to the monitored FDRRecord.
        institution_id (int): Foreign key to the institution for tenant isolation.
        alert_type (str): EXPIRING_30_DAYS, EXPIRING_15_DAYS, EXPIRING_7_DAYS, MATURED, RENEWAL_OVERDUE.
        due_date (date): Maturity date of the FDR instrument.
        recipient_role (str): Target audience role ('institution_user', 'aicte_official', 'administrator').
        recipient_user_id (int): Optional specific recipient User ID.
        delivery_channel (str): 'IN_PORTAL' or 'EMAIL'.
        delivery_status (str): 'PENDING', 'SENT', 'FAILED'.
        idempotency_key (str): Unique constraint preventing duplicate alerts on repeat job executions.
        is_acknowledged (bool): Acknowledgment flag.
        acknowledged_at (datetime): Timestamp when acknowledged.
        acknowledged_by_id (int): User who acknowledged.
        title (str): Short summary title.
        message (str): Detailed alert body.
        created_at (datetime): Timestamp of alert creation (UTC).
    """

    __tablename__ = "fdr_alerts"

    # Alert Type Constants
    TYPE_EXPIRING_30 = "EXPIRING_30_DAYS"
    TYPE_EXPIRING_15 = "EXPIRING_15_DAYS"
    TYPE_EXPIRING_7 = "EXPIRING_7_DAYS"
    TYPE_MATURED = "MATURED"
    TYPE_RENEWAL_OVERDUE = "RENEWAL_OVERDUE"

    # Release / Refund Workflow Alert Types (Phase 7)
    TYPE_RELEASE_SUBMITTED = "RELEASE_SUBMITTED"
    TYPE_RELEASE_PENDING_SCRUTINY = "RELEASE_PENDING_SCRUTINY"
    TYPE_RELEASE_CORRECTION = "RELEASE_CORRECTION_REQUIRED"
    TYPE_RELEASE_RECOMMENDED = "RELEASE_RECOMMENDED"
    TYPE_RELEASE_APPROVED = "RELEASE_APPROVED"
    TYPE_RELEASE_REJECTED = "RELEASE_REJECTED"
    TYPE_RELEASE_CLOSED = "RELEASE_CLOSED"
    TYPE_RELEASE_OVERDUE = "RELEASE_OVERDUE"

    ALLOWED_TYPES = {
        TYPE_EXPIRING_30,
        TYPE_EXPIRING_15,
        TYPE_EXPIRING_7,
        TYPE_MATURED,
        TYPE_RENEWAL_OVERDUE,
        TYPE_RELEASE_SUBMITTED,
        TYPE_RELEASE_PENDING_SCRUTINY,
        TYPE_RELEASE_CORRECTION,
        TYPE_RELEASE_RECOMMENDED,
        TYPE_RELEASE_APPROVED,
        TYPE_RELEASE_REJECTED,
        TYPE_RELEASE_CLOSED,
        TYPE_RELEASE_OVERDUE,
    }

    # Delivery Channel Constants
    CHANNEL_IN_PORTAL = "IN_PORTAL"
    CHANNEL_EMAIL = "EMAIL"

    # Delivery Status
    STATUS_PENDING = "PENDING"
    STATUS_SENT = "SENT"
    STATUS_FAILED = "FAILED"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)

    fdr_record_id = db.Column(
        db.Integer,
        db.ForeignKey("fdr_records.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
        comment="References fdr_records.id",
    )
    release_request_id = db.Column(
        db.Integer,
        db.ForeignKey("fdr_release_requests.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
        comment="References fdr_release_requests.id if related to release workflow",
    )
    institution_id = db.Column(
        db.Integer,
        db.ForeignKey("institutions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="References institutions.id for isolation",
    )

    alert_type = db.Column(
        db.String(50),
        nullable=False,
        index=True,
        comment="Alert category: EXPIRING_30_DAYS, RELEASE_SUBMITTED, etc.",
    )
    due_date = db.Column(
        db.Date,
        nullable=True,
        comment="FDR maturity date or SLA target date",
    )

    recipient_role = db.Column(
        db.String(50),
        default="institution_user",
        nullable=False,
        index=True,
        comment="Target role: institution_user, aicte_official, administrator",
    )
    recipient_user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    delivery_channel = db.Column(
        db.String(50),
        default=CHANNEL_IN_PORTAL,
        nullable=False,
        comment="IN_PORTAL or EMAIL",
    )
    delivery_status = db.Column(
        db.String(50),
        default=STATUS_SENT,
        nullable=False,
        comment="PENDING, SENT, FAILED",
    )

    # Unique Idempotency Key: prevents duplicate alerts on repeat executions
    idempotency_key = db.Column(
        db.String(120),
        unique=True,
        nullable=False,
        index=True,
        comment="Unique key: e.g. fdr_{id}_{type}_{due_date}",
    )

    # Acknowledgment Tracking
    is_acknowledged = db.Column(
        db.Boolean,
        default=False,
        nullable=False,
        index=True,
    )
    acknowledged_at = db.Column(db.DateTime, nullable=True)
    acknowledged_by_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    title = db.Column(db.String(255), nullable=False)
    message = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    fdr_record = db.relationship("FDRRecord", backref=db.backref("alerts", lazy="select", cascade="all, delete-orphan"))
    institution = db.relationship("Institution", backref=db.backref("alerts", lazy="select"))
    acknowledged_by = db.relationship("User", foreign_keys=[acknowledged_by_id])

    def to_dict(self):
        """Serialize alert instance to dictionary."""
        return {
            "id": self.id,
            "fdr_record_id": self.fdr_record_id,
            "fdr_number": self.fdr_record.fdr_number if self.fdr_record else None,
            "release_request_id": self.release_request_id,
            "institution_id": self.institution_id,
            "institution_name": self.institution.name if self.institution else None,
            "alert_type": self.alert_type,
            "due_date": self.due_date.isoformat() if self.due_date else None,
            "recipient_role": self.recipient_role,
            "delivery_channel": self.delivery_channel,
            "delivery_status": self.delivery_status,
            "idempotency_key": self.idempotency_key,
            "is_acknowledged": self.is_acknowledged,
            "acknowledged_at": self.acknowledged_at.isoformat() if self.acknowledged_at else None,
            "acknowledged_by_id": self.acknowledged_by_id,
            "title": self.title,
            "message": self.message,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self):
        return f"<FDRAlert id={self.id} fdr_id={self.fdr_record_id} type='{self.alert_type}' ack={self.is_acknowledged}>"
