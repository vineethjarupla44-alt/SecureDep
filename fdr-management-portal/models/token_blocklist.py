"""
Token Blocklist Model for AICTE FDR Management Portal.

Phase 4: JWT Token Revocation
Maintains a registry of revoked token JTIs (JWT IDs) upon logout.
Used by Flask-JWT-Extended token_in_blocklist_loader to reject revoked tokens.
"""

from datetime import datetime
from models import db


class TokenBlocklist(db.Model):
    """
    Registry of revoked JWT identifiers.

    Attributes:
        id (int): Primary key.
        jti (str): Unique JWT Identifier (UUID).
        token_type (str): Type of token ('access' or 'refresh').
        user_id (int): ID of the user who owned the token.
        revoked_at (datetime): Timestamp when the token was revoked.
        expires_at (datetime): When the token originally expired.
    """

    __tablename__ = "token_blocklist"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    jti = db.Column(
        db.String(36),
        nullable=False,
        unique=True,
        index=True,
        comment="Unique JWT ID (UUID)",
    )
    token_type = db.Column(
        db.String(10),
        nullable=False,
        comment="'access' or 'refresh'",
    )
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
        comment="User ID who logged out",
    )
    revoked_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        nullable=False,
        comment="UTC timestamp when revoked",
    )
    expires_at = db.Column(
        db.DateTime,
        nullable=False,
        comment="UTC timestamp when token expires",
    )

    def __repr__(self):
        return f"<TokenBlocklist id={self.id} jti='{self.jti}' type='{self.token_type}'>"
