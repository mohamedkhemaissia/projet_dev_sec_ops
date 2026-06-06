import os


class Config:
    DEBUG = os.getenv("FLASK_DEBUG", "true").lower() == "true"
    SERVICE_NAME = "user-service"
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key-for-flask-jwt-demo-2026")
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", SECRET_KEY)
    JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
    JWT_EXPIRES_IN_MINUTES = int(os.getenv("JWT_EXPIRES_IN_MINUTES", "60"))
