import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

import jwt
import pytest

COURSE_SERVICE_PATH = Path(__file__).resolve().parents[1] / "services" / "course-service"
for module_name in ["app", "config", "routes", "routes.courses", "db", "db.connection"]:
    sys.modules.pop(module_name, None)
sys.path.insert(0, str(COURSE_SERVICE_PATH))

from app import create_app  # noqa: E402
from config import Config  # noqa: E402


@pytest.fixture
def client():
    app = create_app()
    app.config["TESTING"] = True
    with app.test_client() as test_client:
        yield test_client


def _sample_course(**overrides):
    course = {
        "id": 1,
        "title": "DevSecOps Fundamentals",
        "description": "Introduction to secure delivery pipelines",
        "duration": 24.0,
        "level": "beginner",
        "category": "DevSecOps",
        "trainer_id": 2,
    }
    course.update(overrides)
    return course


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


def test_health(client):
    response = client.get("/api/v1/courses/health")
    assert response.status_code == 200
    assert response.get_json()["status"] == "ok"


@patch("routes.courses.get_all_courses")
def test_list_courses(mock_get_all_courses, client):
    mock_get_all_courses.return_value = [_sample_course()]

    response = client.get("/api/v1/courses", headers=_auth_headers())

    assert response.status_code == 200
    assert len(response.get_json()) == 1


def test_list_courses_without_token(client):
    response = client.get("/api/v1/courses")
    assert response.status_code == 401


@patch("routes.courses.db_create_course")
def test_create_course_as_admin(mock_create_course, client):
    mock_create_course.return_value = _sample_course()

    response = client.post(
        "/api/v1/courses",
        headers=_auth_headers(role="admin", user_id=2),
        json={
            "title": "DevSecOps Fundamentals",
            "description": "Introduction to secure delivery pipelines",
            "duration": 24,
            "level": "beginner",
            "category": "DevSecOps",
        },
    )

    assert response.status_code == 201
    assert response.get_json()["course"]["title"] == "DevSecOps Fundamentals"


def test_create_course_forbidden_for_learner(client):
    response = client.post(
        "/api/v1/courses",
        headers=_auth_headers(role="learner"),
        json={
            "title": "DevSecOps Fundamentals",
            "description": "Introduction to secure delivery pipelines",
            "duration": 24,
            "level": "beginner",
            "category": "DevSecOps",
        },
    )

    assert response.status_code == 403


@patch("routes.courses.create_enrollment")
@patch("routes.courses.get_enrollment", return_value=None)
@patch("routes.courses.find_course_by_id")
def test_enroll_in_course(mock_find_course, mock_get_enrollment, mock_create_enrollment, client):
    mock_find_course.return_value = _sample_course()
    mock_create_enrollment.return_value = {
        "id": 1,
        "user_id": 1,
        "course_id": 1,
        "status": "enrolled",
    }

    response = client.post("/api/v1/courses/1/enroll", headers=_auth_headers())

    assert response.status_code == 201
    assert response.get_json()["status"] == "enrolled"


@patch("routes.courses.delete_enrollment")
@patch("routes.courses.find_course_by_id")
def test_unenroll_from_course(mock_find_course, mock_delete_enrollment, client):
    mock_find_course.return_value = _sample_course()
    mock_delete_enrollment.return_value = 1

    response = client.delete("/api/v1/courses/1/enroll", headers=_auth_headers())

    assert response.status_code == 200
    assert response.get_json()["message"] == "Enrollment cancelled"
    mock_delete_enrollment.assert_called_once_with(1, 1)


@patch("routes.courses.delete_enrollment")
@patch("routes.courses.find_course_by_id")
def test_unenroll_from_course_not_enrolled(mock_find_course, mock_delete_enrollment, client):
    mock_find_course.return_value = _sample_course()
    mock_delete_enrollment.return_value = 0

    response = client.delete("/api/v1/courses/1/enroll", headers=_auth_headers())

    assert response.status_code == 404


@patch("routes.courses.delete_enrollment")
@patch("routes.courses.find_course_by_id")
def test_unenroll_from_missing_course(mock_find_course, mock_delete_enrollment, client):
    mock_find_course.return_value = None

    response = client.delete("/api/v1/courses/999/enroll", headers=_auth_headers())

    assert response.status_code == 404
    assert response.get_json()["message"] == "Course not found"
    mock_delete_enrollment.assert_not_called()
