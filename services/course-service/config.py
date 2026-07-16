import os


class Config:
    DEBUG = os.getenv("FLASK_DEBUG", "false").lower() == "true"
    HOST = os.getenv("APP_HOST", "127.0.0.1")
    SERVICE_NAME = "course-service"
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key-for-flask-jwt-demo-2026")
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", SECRET_KEY)
    JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
    JWT_ISSUER = os.getenv("JWT_ISSUER", "traininghub-user-service")
    JWT_AUDIENCE = os.getenv("JWT_AUDIENCE", "traininghub-api")
    CORS_ORIGINS = [
        origin.strip()
        for origin in os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")
        if origin.strip()
    ]
