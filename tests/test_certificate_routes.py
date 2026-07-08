import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

import jwt
import pytest

CERTIFICATE_SERVICE_PATH = Path(__file__).resolve().parents[1] / "services" / "certificate-service"
for module_name in ["app", "config", "routes", "routes.certificates", "db", "db.connection"]:
    sys.modules.pop(module_name, None)
sys.path.insert(0, str(CERTIFICATE_SERVICE_PATH))

from app import create_app  # noqa: E402
from config import Config  # noqa: E402


@pytest.fixture
def client():
    app = create_app()
    app.config["TESTING"] = True
    with app.test_client() as test_client:
        yield test_client


def _auth_headers(role="learner", user_id=1):
    token = jwt.encode(
        {
            "user_id": user_id,
            "email": "user@example.com",
            "role": role,
            "exp": datetime.now(tz=timezone.utc) + timedelta(minutes=60),
        },
        Config.JWT_SECRET_KEY,
        algorithm=Config.JWT_ALGORITHM,
    )
    return {"Authorization": f"Bearer {token}"}


def _sample_certificate(**overrides):
    certificate = {
        "id": 1,
        "user_id": 1,
        "course_id": 1,
        "certificate_code": "TH-ABC123",
        "status": "active",
        "learner_name": "Alice Demo",
        "course_title": "DevSecOps Fundamentals",
    }
    certificate.update(overrides)
    return certificate


def test_health(client):
    response = client.get("/api/v1/certificates/health")

    assert response.status_code == 200
    assert response.get_json()["status"] == "ok"


@patch("routes.certificates.create_certificate")
@patch("routes.certificates.get_completed_enrollment")
def test_issue_certificate_for_completed_enrollment(mock_enrollment, mock_create, client):
    mock_enrollment.return_value = {"id": 10, "status": "completed"}
    mock_create.return_value = (_sample_certificate(), True)

    response = client.post(
        "/api/v1/certificates/courses/1/issue",
        headers=_auth_headers(),
    )

    assert response.status_code == 201
    assert response.get_json()["certificate_code"] == "TH-ABC123"


@patch("routes.certificates.get_completed_enrollment", return_value=None)
def test_issue_certificate_requires_completed_enrollment(mock_enrollment, client):
    response = client.post(
        "/api/v1/certificates/courses/1/issue",
        headers=_auth_headers(),
    )

    assert response.status_code == 403


def test_issue_certificate_forbidden_for_admin(client):
    response = client.post(
        "/api/v1/certificates/courses/1/issue",
        headers=_auth_headers(role="admin", user_id=2),
    )

    assert response.status_code == 403


@patch("routes.certificates.get_certificates_by_user")
def test_list_my_certificates(mock_get_certificates, client):
    mock_get_certificates.return_value = [_sample_certificate()]

    response = client.get("/api/v1/certificates/me", headers=_auth_headers())

    assert response.status_code == 200
    assert len(response.get_json()) == 1


@patch("routes.certificates.verify_certificate")
def test_verify_certificate_by_code(mock_verify, client):
    mock_verify.return_value = _sample_certificate()

    response = client.get("/api/v1/certificates/verify/TH-ABC123")

    assert response.status_code == 200
    assert response.get_json()["valid"] is True


@patch("routes.certificates.verify_certificate", return_value=None)
def test_verify_missing_certificate(mock_verify, client):
    response = client.get("/api/v1/certificates/verify/UNKNOWN")

    assert response.status_code == 404
