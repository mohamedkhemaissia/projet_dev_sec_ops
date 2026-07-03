import os


class Config:
    DEBUG = os.getenv("FLASK_DEBUG", "true").lower() == "true"
    SERVICE_NAME = "user-service"
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key-for-flask-jwt-demo-2026")
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", SECRET_KEY)
    JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
    JWT_EXPIRES_IN_MINUTES = int(os.getenv("JWT_EXPIRES_IN_MINUTES", "60"))
    UPLOAD_FOLDER = os.getenv(
        "UPLOAD_FOLDER",
        os.path.join(os.path.dirname(__file__), "uploads", "avatars"),
    )
    MAX_CONTENT_LENGTH = int(os.getenv("MAX_UPLOAD_BYTES", str(2 * 1024 * 1024)))
