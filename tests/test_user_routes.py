import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

import jwt
import pytest
from werkzeug.security import generate_password_hash

USER_SERVICE_PATH = Path(__file__).resolve().parents[1] / "services" / "user-service"
for module_name in ["app", "config", "routes", "routes.users", "db", "db.connection"]:
    sys.modules.pop(module_name, None)
sys.path.insert(0, str(USER_SERVICE_PATH))

from app import create_app  # noqa: E402
from config import Config  # noqa: E402


@pytest.fixture
def client():
    app = create_app()
    app.config["TESTING"] = True
    with app.test_client() as test_client:
        yield test_client


def _sample_user(**overrides):
    user = {
        "id": 1,
        "name": "Alice Demo",
        "email": "alice@example.com",
        "password_hash": generate_password_hash("Password123!"),
        "role": "learner",
    }
    user.update(overrides)
    return user


def _auth_headers(user=None, **overrides):
    user = user or _sample_user()
    issued_at = datetime.now(tz=timezone.utc)
    payload = {
        "user_id": user["id"],
        "email": user["email"],
        "role": user["role"],
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


def test_health(client):
    response = client.get("/api/v1/users/health")
    assert response.status_code == 200
    assert response.get_json()["status"] == "ok"
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"
    assert response.headers["Referrer-Policy"] == "no-referrer"


@patch("routes.users.create_user")
@patch("routes.users.get_user_by_email", return_value=None)
def test_register_success(mock_get_email, mock_create_user, client):
    mock_create_user.return_value = _sample_user()

    response = client.post(
        "/api/v1/users/register",
        json={
            "name": "Alice Demo",
            "email": "alice@example.com",
            "password": "Password123!",
        },
    )

    assert response.status_code == 201
    body = response.get_json()
    assert body["email"] == "alice@example.com"
    assert body["role"] == "learner"
    mock_create_user.assert_called_once()

@patch("routes.users.create_user")
@patch("routes.users.get_user_by_email", return_value=None)
def test_register_rejects_privileged_role(mock_get_email, mock_create_user, client):

    response = client.post(
        "/api/v1/users/register",
        json={
            "name": "Mallory Demo",
            "email": "mallory@example.com",
            "password": "Password123!",
            "role": "admin",
        },
    )

    assert response.status_code == 400
    mock_create_user.assert_not_called()


@patch("routes.users.create_user")
@patch("routes.users.get_user_by_email", return_value=None)
def test_register_normalizes_identity(mock_get_email, mock_create_user, client):
    mock_create_user.return_value = _sample_user()

    response = client.post(
        "/api/v1/users/register",
        json={
            "name": "  Alice Demo  ",
            "email": "  ALICE@EXAMPLE.COM  ",
            "password": "Password123!",
        },
    )

    assert response.status_code == 201
    assert mock_create_user.call_args.args[0] == "Alice Demo"
    assert mock_create_user.call_args.args[1] == "alice@example.com"


@patch("routes.users.create_user")
@patch("routes.users.get_user_by_email", return_value=None)
def test_register_rejects_weak_password(mock_get_email, mock_create_user, client):
    response = client.post(
        "/api/v1/users/register",
        json={
            "name": "Alice Demo",
            "email": "alice@example.com",
            "password": "password",
        },
    )

    assert response.status_code == 400
    mock_create_user.assert_not_called()


def test_register_requires_json_object(client):
    response = client.post("/api/v1/users/register", json=["invalid"])

    assert response.status_code == 400


@patch("routes.users.get_user_by_email")
def test_register_conflict(mock_get_email, client):
    mock_get_email.return_value = _sample_user()

    response = client.post(
        "/api/v1/users/register",
        json={
            "name": "Alice Demo",
            "email": "alice@example.com",
            "password": "Password123!",
        },
    )

    assert response.status_code == 409


@patch("routes.users.get_user_by_email")
def test_login_success(mock_get_email, client):
    mock_get_email.return_value = _sample_user()

    response = client.post(
        "/api/v1/users/login",
        json={"email": "alice@example.com", "password": "Password123!"},
    )

    assert response.status_code == 200
    body = response.get_json()
    assert "token" in body
    assert body["user"]["email"] == "alice@example.com"
    payload = jwt.decode(
        body["token"],
        Config.JWT_SECRET_KEY,
        algorithms=[Config.JWT_ALGORITHM],
        issuer=Config.JWT_ISSUER,
        audience=Config.JWT_AUDIENCE,
    )
    assert payload["iss"] == Config.JWT_ISSUER
    assert payload["aud"] == Config.JWT_AUDIENCE
    assert payload["jti"]


@patch("routes.users.get_user_by_email", return_value=None)
def test_login_invalid_credentials(mock_get_email, client):
    response = client.post(
        "/api/v1/users/login",
        json={"email": "alice@example.com", "password": "wrong-password"},
    )

    assert response.status_code == 401


@patch("routes.users.get_user_by_id")
def test_get_profile(mock_get_user_by_id, client):
    mock_get_user_by_id.return_value = _sample_user()

    response = client.get("/api/v1/users/me", headers=_auth_headers())

    assert response.status_code == 200
    assert response.get_json()["email"] == "alice@example.com"


def test_get_profile_without_token(client):
    response = client.get("/api/v1/users/me")
    assert response.status_code == 401


@patch("routes.users.get_user_by_id")
def test_get_profile_rejects_wrong_jwt_audience(mock_get_user_by_id, client):
    response = client.get(
        "/api/v1/users/me",
        headers=_auth_headers(aud="another-api"),
    )

    assert response.status_code == 401
    mock_get_user_by_id.assert_not_called()


@patch("routes.users.get_user_by_id")
def test_update_profile_rejects_role_change(mock_get_user_by_id, client):
    mock_get_user_by_id.return_value = _sample_user()

    response = client.put(
        "/api/v1/users/me",
        json={"role": "admin"},
        headers=_auth_headers(),
    )

    assert response.status_code == 400
