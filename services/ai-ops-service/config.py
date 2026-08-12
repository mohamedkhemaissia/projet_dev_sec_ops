import os


class Config:
    DEBUG = os.getenv("FLASK_DEBUG", "false").lower() == "true"
    HOST = os.getenv("APP_HOST", "127.0.0.1")
    PORT = int(os.getenv("APP_PORT", "5005"))
    SERVICE_NAME = "ai-ops-service"

    AIOPS_WEBHOOK_TOKEN = os.getenv("AIOPS_WEBHOOK_TOKEN", "")
    ALLOWED_SERVICES = tuple(
        item.strip()
        for item in os.getenv(
            "AIOPS_ALLOWED_SERVICES",
            "user-service,course-service,certificate-service,frontend-service",
        ).split(",")
        if item.strip()
    )
    INCIDENT_HISTORY_LIMIT = int(os.getenv("AIOPS_INCIDENT_HISTORY_LIMIT", "100"))
    MAX_ALERTS_PER_REQUEST = int(os.getenv("AIOPS_MAX_ALERTS_PER_REQUEST", "10"))
    MAX_TEXT_LENGTH = int(os.getenv("AIOPS_MAX_TEXT_LENGTH", "2000"))
    MAX_CONTENT_LENGTH = int(os.getenv("AIOPS_MAX_CONTENT_LENGTH", "65536"))

    PROMETHEUS_URL = os.getenv("PROMETHEUS_URL", "http://localhost:9090").rstrip("/")
    PROMETHEUS_TIMEOUT_SECONDS = float(
        os.getenv("PROMETHEUS_TIMEOUT_SECONDS", "3")
    )

    AIOPS_MODEL_PROVIDER = os.getenv("AIOPS_MODEL_PROVIDER", "rules").lower()
    OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434").rstrip("/")
    OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "gemma3:4b")
    OLLAMA_API_KEY = os.getenv("OLLAMA_API_KEY", "")
    MODEL_TIMEOUT_SECONDS = float(os.getenv("AIOPS_MODEL_TIMEOUT_SECONDS", "30"))
