"""
User Model for AICTE FDR Management Portal.

Phase 4: Authentication and Role-Based Access Control (RBAC)
Supports roles:
- institution_user : Restricted to their assigned institution's records
- aicte_official   : AICTE regulator with read/review access across all institutions
- administrator    : System administrator with full privileges and user provisioning
"""

from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from models import db


class User(db.Model):
    """
    SQLAlchemy model representing application users with role-based access.

    Attributes:
        id (int): Primary key.
        email (str): Unique contact & login email address (indexed, lowercase).
        password_hash (str): Secure salted hash (PBKDF2-HMAC-SHA256).
        full_name (str): Full display name of the user.
        role (str): Role identifier ('institution_user', 'aicte_official', 'administrator').
        account_status (str): Current status ('ACTIVE', 'INACTIVE', 'SUSPENDED').
        institution_id (int): Foreign key referencing institutions.id (required for institution_user).
        created_at (datetime): Timestamp of creation (UTC).
        updated_at (datetime): Timestamp of last update (UTC).
    """

    __tablename__ = "users"

    # Supported System Roles
    ROLE_INSTITUTION_USER = "institution_user"
    ROLE_AICTE_OFFICIAL = "aicte_official"
    ROLE_ADMINISTRATOR = "administrator"

    ALLOWED_ROLES = {ROLE_INSTITUTION_USER, ROLE_AICTE_OFFICIAL, ROLE_ADMINISTRATOR}

    # Supported Account Statuses
    STATUS_ACTIVE = "ACTIVE"
    STATUS_INACTIVE = "INACTIVE"
    STATUS_SUSPENDED = "SUSPENDED"
    STATUS_PENDING = "PENDING"
    STATUS_REJECTED = "REJECTED"

    ALLOWED_STATUSES = {
        STATUS_ACTIVE,
        STATUS_INACTIVE,
        STATUS_SUSPENDED,
        STATUS_PENDING,
        STATUS_REJECTED,
    }

    # Primary Key
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)

    # Authentication credentials
    email = db.Column(
        db.String(120),
        unique=True,
        nullable=False,
        index=True,
        comment="Normalized login email address",
    )
    password_hash = db.Column(
        db.String(255),
        nullable=False,
        comment="Secure Werkzeug salted password hash",
    )
    full_name = db.Column(
        db.String(150),
        nullable=False,
        comment="User full legal name",
    )

    # Authorization & Access Control
    role = db.Column(
        db.String(50),
        nullable=False,
        default=ROLE_INSTITUTION_USER,
        index=True,
        comment="Role: institution_user, aicte_official, administrator",
    )
    account_status = db.Column(
        db.String(50),
        nullable=False,
        default=STATUS_ACTIVE,
        index=True,
        comment="Account lifecycle status: ACTIVE, INACTIVE, SUSPENDED",
    )

    # Multi-tenant link: Institution users are strictly bound to an institution
    institution_id = db.Column(
        db.Integer,
        db.ForeignKey("institutions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="Assigned institution ID for institution_user; NULL for AICTE/admin",
    )

    # Auditing timestamps
    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        nullable=False,
        comment="Timestamp of account creation (UTC)",
    )
    updated_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
        comment="Timestamp of last update (UTC)",
    )

    # Relationship to Institution
    institution = db.relationship("Institution", backref=db.backref("users", lazy="select"))

    def set_password(self, password):
        """
        Hash plaintext password using Werkzeug's PBKDF2-HMAC-SHA256.
        Plaintext passwords are never saved.
        """
        if not password or len(password.strip()) < 8:
            raise ValueError("Password must be at least 8 characters long.")
        self.password_hash = generate_password_hash(password.strip(), method="pbkdf2:sha256")

    def check_password(self, password):
        """
        Verify plaintext password against the stored salted hash.
        """
        if not self.password_hash or not password:
            return False
        return check_password_hash(self.password_hash, password.strip())

    @property
    def is_active(self):
        """Returns True if the account is ACTIVE and not suspended or disabled."""
        return self.account_status == self.STATUS_ACTIVE

    def to_dict(self):
        """
        Serialize user details for JSON response.
        NEVER includes password_hash.
        """
        return {
            "id": self.id,
            "email": self.email,
            "full_name": self.full_name,
            "role": self.role,
            "account_status": self.account_status,
            "institution_id": self.institution_id,
            "institution_name": self.institution.name if self.institution else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    def __repr__(self):
        return f"<User id={self.id} email='{self.email}' role='{self.role}' status='{self.account_status}'>"
