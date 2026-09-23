import sys
from pathlib import Path

import pytest

FRONTEND_PATH = Path(__file__).resolve().parents[1]
for module_name in ["app", "config", "api_client", "routes", "routes.web"]:
    sys.modules.pop(module_name, None)
sys.path.insert(0, str(FRONTEND_PATH))

from app import create_app  # noqa: E402
from config import TestConfig  # noqa: E402


class FakeAPI:
    def __init__(self):
        self.enrolled_course_ids = []
        self.course_items = [
            {
                "id": 1,
                "title": "DevSecOps Fundamentals",
                "description": "Construire et sécuriser une chaîne de livraison moderne.",
                "duration": 24,
                "level": "beginner",
                "category": "DevSecOps",
            }
        ]

    def login(self, email, password):
        role = "admin" if email.startswith("admin") else "learner"
        return {
            "token": f"{role}-token",
            "user": {"id": 1, "name": "Alice Demo", "email": email, "role": role},
        }

    def register(self, payload):
        return {"id": 2, "role": "learner", **payload}

    def courses(self, _token):
        return self.course_items

    def course(self, _token, course_id):
        return next(item for item in self.course_items if item["id"] == course_id)

    def enroll(self, _token, course_id):
        self.enrolled_course_ids.append(course_id)
        return {"course_id": course_id, "status": "enrolled"}

    def my_enrollments(self, _token):
        return []

    def my_certificates(self, _token):
        return []

    def users(self, _token):
        return [
            {
                "id": 1,
                "name": "Alice Demo",
                "email": "admin@training.com",
                "role": "admin",
            }
        ]

    def course_enrollments(self, _token, _course_id):
        return []

    def profile(self, _token):
        return {}

    def update_profile(self, _token, payload):
        return {
            "id": 1,
            "name": payload.get("name", "Alice Demo"),
            "email": payload.get("email", "alice@example.com"),
            "role": "learner",
        }


@pytest.fixture
def fake_api():
    return FakeAPI()


@pytest.fixture
def app(fake_api):
    return create_app(TestConfig, api_client=fake_api)


@pytest.fixture
def client(app):
    return app.test_client()


def authenticate(client, role="learner"):
    with client.session_transaction() as current_session:
        current_session["access_token"] = f"{role}-token"
        current_session["user"] = {
            "id": 1,
            "name": "Alice Demo",
            "email": f"{role}@training.com",
            "role": role,
        }


def test_home_has_custom_traininghub_identity(client):
    response = client.get("/")

    assert response.status_code == 200
    assert "Transformez vos compétences" in response.get_data(as_text=True)
    assert "Développé par Mohamed Khemaissia · © 2026" in response.get_data(
        as_text=True
    )
    assert response.headers["X-Frame-Options"] == "DENY"
    assert "frame-ancestors 'none'" in response.headers["Content-Security-Policy"]


def test_csrf_time_limit_is_expressed_in_seconds():
    assert isinstance(TestConfig.WTF_CSRF_TIME_LIMIT, int)
    assert TestConfig.WTF_CSRF_TIME_LIMIT == 7200


def test_login_creates_server_session(client):
    response = client.post(
        "/login",
        data={"email": "alice@example.com", "password": "Password123!"},
    )

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/dashboard")
    with client.session_transaction() as current_session:
        assert current_session["user"]["role"] == "learner"
        assert current_session["access_token"] == "learner-token"


def test_login_rejects_external_next_redirect(client):
    response = client.post(
        "/login?next=//malicious.example",
        data={"email": "alice@example.com", "password": "Password123!"},
    )

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/dashboard")
    assert "malicious.example" not in response.headers["Location"]


def test_learner_dashboard_renders_with_empty_state(client):
    authenticate(client)

    response = client.get("/learner")

    assert response.status_code == 200
    assert "Bonjour Alice" in response.get_data(as_text=True)
    assert "Votre parcours commence ici" in response.get_data(as_text=True)


def test_catalog_renders_api_courses(client):
    authenticate(client)

    response = client.get("/courses")

    assert response.status_code == 200
    assert "DevSecOps Fundamentals" in response.get_data(as_text=True)


def test_learner_can_enroll_without_referrer_redirect(client, fake_api):
    authenticate(client)

    response = client.post(
        "/courses/1/enroll",
        headers={"Referer": "https://malicious.example/phishing"},
    )

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/courses/1")
    assert fake_api.enrolled_course_ids == [1]


def test_admin_dashboard_is_role_protected(client):
    authenticate(client, role="learner")

    response = client.get("/admin")

    assert response.status_code == 403


def test_admin_dashboard_renders_platform_stats(client):
    authenticate(client, role="admin")

    response = client.get("/admin")

    assert response.status_code == 200
    assert "Centre de pilotage" in response.get_data(as_text=True)
    assert "Apprenants" in response.get_data(as_text=True)
