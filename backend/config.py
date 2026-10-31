"""
Application Configuration Module for FDR Management Portal.

Loads settings from environment variables using python-dotenv.
Configures database, JWT token expiration, CORS origins, and rejects
insecure default credentials in production.
"""

import os
from datetime import timedelta
from pathlib import Path
from dotenv import load_dotenv

# Define base directory of the project
BASE_DIR = Path(__file__).resolve().parent

# Load environment variables from .env file if present
load_dotenv(BASE_DIR / ".env")


class Config:
    """Base configuration with default settings and environment fallbacks."""

    # Core Flask settings
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-fallback-key-replace-in-production")
    FLASK_ENV = os.getenv("FLASK_ENV", "development")
    DEBUG = os.getenv("FLASK_DEBUG", "True").lower() in ("true", "1", "yes")
    
    # Server network settings
    HOST = os.getenv("HOST", "127.0.0.1")
    PORT = int(os.getenv("PORT", 5000))
    # Maturity dates are calendar dates. Use the institution's configured
    # business timezone rather than the host machine timezone at midnight.
    APP_TIMEZONE = os.getenv("APP_TIMEZONE", "Asia/Kolkata")

    # JWT Authentication settings (Phase 4)
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "dev-jwt-secret-replace-in-production")
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(
        minutes=int(os.getenv("JWT_ACCESS_TOKEN_EXPIRES_MINUTES", "60"))
    )
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(
        days=int(os.getenv("JWT_REFRESH_TOKEN_EXPIRES_DAYS", "30"))
    )
    JWT_TOKEN_LOCATION = ["headers"]
    JWT_HEADER_NAME = "Authorization"
    JWT_HEADER_TYPE = "Bearer"

    # CORS configuration - restrictive list of origins (development defaults)
    # Never allow unrestricted "*" access in development or production
    _cors_env = os.getenv(
        "CORS_ALLOWED_ORIGINS",
        "http://localhost:3000,http://127.0.0.1:3000,http://localhost:5173",
    )
    CORS_ORIGINS = [origin.strip() for origin in _cors_env.split(",") if origin.strip()]

    # Database configuration for MySQL + PyMySQL
    DB_USER = os.getenv("DB_USER", "root")
    DB_PASSWORD = os.getenv("DB_PASSWORD", "")
    DB_HOST = os.getenv("DB_HOST", "localhost")
    DB_PORT = os.getenv("DB_PORT", "3306")
    DB_NAME = os.getenv("DB_NAME", "fdr_management")

    # Construct the PyMySQL connection string
    # Format: mysql+pymysql://<username>:<password>@<host>:<port>/<dbname>
    _default_db_uri = (
        f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    )
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL", _default_db_uri)
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ECHO = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_pre_ping": True,
        "pool_recycle": 280,
    }

    # File & Document uploads (Phase 5)
    UPLOAD_FOLDER = os.getenv("UPLOAD_FOLDER", str(BASE_DIR / "uploads"))
    DOCUMENTS_UPLOAD_FOLDER = os.getenv("DOCUMENTS_UPLOAD_FOLDER", str(BASE_DIR / "uploads" / "documents"))
    MAX_DOCUMENT_SIZE = int(os.getenv("MAX_DOCUMENT_SIZE", 10 * 1024 * 1024))  # 10 MB limit
    MAX_CONTENT_LENGTH = int(os.getenv("MAX_CONTENT_LENGTH", 16 * 1024 * 1024))  # 16 MB request limit
    ALLOWED_EXTENSIONS = {"pdf", "jpg", "jpeg", "png"}
    ALLOWED_MIME_TYPES = {"application/pdf", "image/jpeg", "image/png"}
    TESSERACT_CMD = os.getenv("TESSERACT_CMD", r"C:\Program Files\Tesseract-OCR\tesseract.exe")

    # Email & Alert notifications (Phase 6 - Optional, disabled by default)
    MAIL_ENABLED = os.getenv("MAIL_ENABLED", "False").lower() in ("true", "1", "yes")
    MAIL_SERVER = os.getenv("MAIL_SERVER", "smtp.gmail.com")
    MAIL_PORT = int(os.getenv("MAIL_PORT", 587))
    MAIL_USE_TLS = os.getenv("MAIL_USE_TLS", "True").lower() in ("true", "1", "yes")
    MAIL_USERNAME = os.getenv("MAIL_USERNAME", "")
    MAIL_PASSWORD = os.getenv("MAIL_PASSWORD", "")
    MAIL_DEFAULT_SENDER = os.getenv("MAIL_DEFAULT_SENDER", "noreply-fdr@aicte-india.org")


class DevelopmentConfig(Config):
    """Development environment specific configuration."""

    DEBUG = True


class TestingConfig(Config):
    """Testing environment specific configuration (uses SQLite in-memory)."""

    TESTING = True
    DEBUG = False
    # Use SQLite in-memory for unit tests so live MySQL is never required
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    # Use short token expiration during tests to test expiration logic
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(minutes=15)


class ProductionConfig(Config):
    """Production environment specific configuration."""

    DEBUG = False
    TESTING = False
    SQLALCHEMY_ECHO = False

    @classmethod
    def validate_secrets(cls):
        """Reject insecure default secrets in production configuration."""
        insecure_keys = [
            "dev-fallback-key-replace-in-production",
            "dev-jwt-secret-replace-in-production",
            "change-this-in-production",
            "secret",
            "",
        ]
        if cls.SECRET_KEY in insecure_keys:
            raise ValueError(
                "CRITICAL SECURITY ERROR: Insecure or default SECRET_KEY in production! "
                "Set a cryptographically strong SECRET_KEY environment variable."
            )
        if cls.JWT_SECRET_KEY in insecure_keys:
            raise ValueError(
                "CRITICAL SECURITY ERROR: Insecure or default JWT_SECRET_KEY in production! "
                "Set a cryptographically strong JWT_SECRET_KEY environment variable."
            )


# Configuration mapping
config_by_name = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
    "default": DevelopmentConfig,
}
