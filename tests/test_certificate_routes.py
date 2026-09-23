import sys
from datetime import datetime, timedelta, timezone
from io import BytesIO
from pathlib import Path
from unittest.mock import patch

import jwt
import pytest

CERTIFICATE_SERVICE_PATH = Path(__file__).resolve().parents[1] / "services" / "certificate-service"
for module_name in ["app", "config", "routes", "routes.certificates", "db", "db.connection"]:
    sys.modules.pop(module_name, None)
sys.path.insert(0, str(CERTIFICATE_SERVICE_PATH))

from app import create_app  # noqa: E402
from certificate_pdf import generate_certificate_pdf  # noqa: E402
from config import Config  # noqa: E402


@pytest.fixture
def client():
    app = create_app()
    app.config["TESTING"] = True
    with app.test_client() as test_client:
        yield test_client


def _auth_headers(role="learner", user_id=1, **overrides):
    issued_at = datetime.now(tz=timezone.utc)
    payload = {
        "user_id": user_id,
        "email": "user@example.com",
        "role": role,
        "iat": issued_at,
        "exp": issued_at + timedelta(minutes=60),
        "iss": Config.JWT_ISSUER,
        "aud": Config.JWT_AUDIENCE,
    }
    payload.update(overrides)
    token = jwt.encode(
        payload,
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
        "issued_at": "2026-07-15 10:30:00",
        "learner_name": "Alice Demo",
        "course_title": "DevSecOps Fundamentals",
        "category": "DevSecOps",
        "level": "beginner",
    }
    certificate.update(overrides)
    return certificate


def test_generate_certificate_pdf():
    pdf_buffer = generate_certificate_pdf(
        _sample_certificate(),
        "http://localhost:5004/api/v1/certificates/verify/TH-ABC123",
    )

    pdf_bytes = pdf_buffer.getvalue()
    assert pdf_bytes.startswith(b"%PDF-")
    assert len(pdf_bytes) > 1_000


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


def test_issue_certificate_rejects_missing_required_claim(client):
    issued_at = datetime.now(tz=timezone.utc)
    token = jwt.encode(
        {
            "user_id": 1,
            "email": "user@example.com",
            "role": "learner",
            "iat": issued_at,
            "exp": issued_at + timedelta(minutes=60),
            "iss": Config.JWT_ISSUER,
        },
        Config.JWT_SECRET_KEY,
        algorithm=Config.JWT_ALGORITHM,
    )

    response = client.post(
        "/api/v1/certificates/courses/1/issue",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 401


@patch("routes.certificates.get_certificates_by_user")
def test_list_my_certificates(mock_get_certificates, client):
    mock_get_certificates.return_value = [_sample_certificate()]

    response = client.get("/api/v1/certificates/me", headers=_auth_headers())

    assert response.status_code == 200
    assert len(response.get_json()) == 1


@patch("routes.certificates.generate_certificate_pdf")
@patch("routes.certificates.get_certificate_by_id")
def test_download_own_certificate_as_pdf(
    mock_get_certificate,
    mock_generate_pdf,
    client,
):
    mock_get_certificate.return_value = _sample_certificate()
    mock_generate_pdf.return_value = BytesIO(b"%PDF-1.4\nmock certificate")

    response = client.get(
        "/api/v1/certificates/1/download",
        headers=_auth_headers(),
    )

    assert response.status_code == 200
    assert response.mimetype == "application/pdf"
    assert response.data.startswith(b"%PDF-")
    assert "certificat-TH-ABC123.pdf" in response.headers["Content-Disposition"]
    assert response.headers["Cache-Control"] == "private, no-store"
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    mock_get_certificate.assert_called_once_with(1, user_id=1)
    mock_generate_pdf.assert_called_once()


@patch("routes.certificates.get_certificate_by_id", return_value=None)
def test_download_cannot_access_another_learners_certificate(mock_get_certificate, client):
    response = client.get(
        "/api/v1/certificates/2/download",
        headers=_auth_headers(),
    )

    assert response.status_code == 404
    mock_get_certificate.assert_called_once_with(2, user_id=1)


@patch("routes.certificates.get_certificate_by_id")
def test_download_revoked_certificate_is_rejected(mock_get_certificate, client):
    mock_get_certificate.return_value = _sample_certificate(status="revoked")

    response = client.get(
        "/api/v1/certificates/1/download",
        headers=_auth_headers(),
    )

    assert response.status_code == 409
    assert response.get_json()["error"] == "certificate_revoked"


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
