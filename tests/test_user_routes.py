import sys
from io import BytesIO
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
        "avatar_url": None,
    }
    user.update(overrides)
    return user


def _auth_headers(user=None):
    user = user or _sample_user()
    token = jwt.encode(
        {
            "user_id": user["id"],
            "email": user["email"],
            "role": user["role"],
            "exp": datetime.now(tz=timezone.utc) + timedelta(minutes=60),
        },
        Config.JWT_SECRET_KEY,
        algorithm=Config.JWT_ALGORITHM,
    )
    return {"Authorization": f"Bearer {token}"}


def test_health(client):
    response = client.get("/api/v1/users/health")
    assert response.status_code == 200
    assert response.get_json()["status"] == "ok"


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
            "role": "learner",
        },
    )

    assert response.status_code == 201
    body = response.get_json()
    assert body["email"] == "alice@example.com"
    assert body["role"] == "learner"
    mock_create_user.assert_called_once()

@patch("routes.users.create_user")
@patch("routes.users.get_user_by_email", return_value=None)
def test_register_ignores_privileged_role(mock_get_email, mock_create_user, client):
    mock_create_user.return_value = _sample_user(role="learner")

    response = client.post(
        "/api/v1/users/register",
        json={
            "name": "Mallory Demo",
            "email": "mallory@example.com",
            "password": "Password123!",
            "role": "admin",
        },
    )

    assert response.status_code == 201
    assert response.get_json()["role"] == "learner"
    mock_create_user.assert_called_once()
    assert mock_create_user.call_args.args[3] == "learner"    


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


@patch("routes.users.update_user")
@patch("routes.users.get_user_by_id")
def test_upload_avatar_success(mock_get_user_by_id, mock_update_user, client, tmp_path):
    mock_get_user_by_id.return_value = _sample_user()
    mock_update_user.return_value = _sample_user(
        avatar_url="http://localhost/api/v1/users/uploads/avatars/user-1-demo.png"
    )
    client.application.config["UPLOAD_FOLDER"] = str(tmp_path)

    response = client.post(
        "/api/v1/users/me/avatar",
        data={"avatar": (BytesIO(b"fake-image-content"), "avatar.png")},
        headers=_auth_headers(),
        content_type="multipart/form-data",
    )

    assert response.status_code == 200
    assert response.get_json()["avatar_url"].endswith(".png")
    mock_update_user.assert_called_once()


@patch("routes.users.get_user_by_id")
def test_upload_avatar_rejects_invalid_extension(mock_get_user_by_id, client):
    mock_get_user_by_id.return_value = _sample_user()

    response = client.post(
        "/api/v1/users/me/avatar",
        data={"avatar": (BytesIO(b"fake-content"), "avatar.exe")},
        headers=_auth_headers(),
        content_type="multipart/form-data",
    )

    assert response.status_code == 400
