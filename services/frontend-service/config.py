import os
import tempfile
from datetime import timedelta
from pathlib import Path


class Config:
    DEBUG = os.getenv("FLASK_DEBUG", "false").lower() == "true"
    HOST = os.getenv("APP_HOST", "127.0.0.1")
    PORT = int(os.getenv("APP_PORT", "3000"))
    SECRET_KEY = os.getenv(
        "FRONTEND_SECRET_KEY",
        "dev-only-change-me-traininghub-frontend",
    )

    USER_SERVICE_URL = os.getenv("USER_SERVICE_URL", "http://127.0.0.1:5001")
    COURSE_SERVICE_URL = os.getenv("COURSE_SERVICE_URL", "http://127.0.0.1:5002")
    CERTIFICATE_SERVICE_URL = os.getenv(
        "CERTIFICATE_SERVICE_URL",
        "http://127.0.0.1:5004",
    )
    API_TIMEOUT_SECONDS = float(os.getenv("API_TIMEOUT_SECONDS", "5"))

    SESSION_TYPE = "cachelib"
    SESSION_FILE_DIR = Path(
        os.getenv(
            "SESSION_FILE_DIR",
            str(Path(tempfile.gettempdir()) / "traininghub-frontend-sessions"),
        )
    )
    SESSION_PERMANENT = True
    PERMANENT_SESSION_LIFETIME = timedelta(minutes=60)
    SESSION_COOKIE_NAME = "traininghub_session"
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = os.getenv("SESSION_COOKIE_SECURE", "false").lower() == "true"

    WTF_CSRF_TIME_LIMIT = 7200
    MAX_CONTENT_LENGTH = 1024 * 1024


class TestConfig(Config):
    TESTING = True
    WTF_CSRF_ENABLED = False
    SESSION_TYPE = "cachelib"
