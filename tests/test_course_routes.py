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
from recommendation.engine import build_recommendations  # noqa: E402


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
    }
    course.update(overrides)
    return course


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


def test_health(client):
    response = client.get("/api/v1/courses/health")
    assert response.status_code == 200
    assert response.get_json()["status"] == "ok"
    assert response.headers["X-Request-ID"]


def test_prometheus_metrics(client):
    client.get("/api/v1/courses/health")
    response = client.get("/metrics")

    body = response.get_data(as_text=True)
    assert response.status_code == 200
    assert "traininghub_http_requests_total" in body
    assert 'service="course-service"' in body


@patch("routes.courses.get_all_courses")
def test_list_courses(mock_get_all_courses, client):
    mock_get_all_courses.return_value = [_sample_course()]

    response = client.get("/api/v1/courses", headers=_auth_headers())

    assert response.status_code == 200
    assert len(response.get_json()) == 1


@patch("routes.courses.get_all_courses")
def test_list_courses_accepts_filters_and_sort(mock_get_all_courses, client):
    mock_get_all_courses.return_value = []

    response = client.get(
        "/api/v1/courses?category=Python&level=beginner&sort=popular",
        headers=_auth_headers(),
    )

    assert response.status_code == 200
    mock_get_all_courses.assert_called_once_with(
        sort="popular",
        category="Python",
        level="beginner",
    )


@patch("routes.courses.get_all_courses")
def test_list_courses_rejects_invalid_filter(mock_get_all_courses, client):
    response = client.get(
        "/api/v1/courses?sort=unknown",
        headers=_auth_headers(),
    )

    assert response.status_code == 400
    mock_get_all_courses.assert_not_called()


@patch("routes.courses.find_course_by_id")
def test_course_detail_contains_enrollment_statistics(mock_find_course, client):
    mock_find_course.return_value = _sample_course(
        enrollment_count=24,
        in_progress_count=8,
        completed_count=12,
        completion_rate=50.0,
    )

    response = client.get("/api/v1/courses/1", headers=_auth_headers())

    assert response.status_code == 200
    assert response.get_json()["completion_rate"] == 50.0
    assert response.get_json()["enrollment_count"] == 24


@patch("routes.courses.get_recommendation_data")
def test_recommendations_use_user_id_from_jwt(mock_get_recommendation_data, client):
    now = datetime.now(tz=timezone.utc)
    mock_get_recommendation_data.return_value = (
        [
            _sample_course(
                id=2,
                title="Python Intermediate",
                category="Python",
                level="intermediate",
                enrollment_count=10,
                created_at=now,
            )
        ],
        [
            {
                "course_id": 1,
                "status": "completed",
                "category": "Python",
                "level": "beginner",
            }
        ],
    )

    response = client.get(
        "/api/v1/courses/recommendations?limit=1",
        headers=_auth_headers(user_id=4),
    )

    assert response.status_code == 200
    body = response.get_json()
    assert body["user_id"] == 4
    assert body["algorithm"] == "rule-based-scoring"
    assert body["cold_start"] is False
    assert body["recommendations"][0]["course_id"] == 2
    assert "formation terminée" in body["recommendations"][0]["reason"]
    mock_get_recommendation_data.assert_called_once_with(4)


@patch("routes.courses.get_recommendation_data")
def test_recommendations_reject_invalid_limit(mock_get_recommendation_data, client):
    response = client.get(
        "/api/v1/courses/recommendations?limit=11",
        headers=_auth_headers(),
    )

    assert response.status_code == 400
    mock_get_recommendation_data.assert_not_called()


@patch("routes.courses.get_recommendation_data")
def test_recommendations_require_learner(mock_get_recommendation_data, client):
    response = client.get(
        "/api/v1/courses/recommendations",
        headers=_auth_headers(role="admin"),
    )

    assert response.status_code == 403
    mock_get_recommendation_data.assert_not_called()


@patch("routes.courses.get_recommendation_data")
def test_recommendations_require_token(mock_get_recommendation_data, client):
    response = client.get("/api/v1/courses/recommendations")

    assert response.status_code == 401
    mock_get_recommendation_data.assert_not_called()


def test_recommendation_engine_uses_highest_category_bonus():
    now = datetime.now(tz=timezone.utc)
    cold_start, recommendations = build_recommendations(
        [
            _sample_course(
                id=2,
                category="Python",
                level="intermediate",
                enrollment_count=10,
                created_at=now - timedelta(days=10),
            )
        ],
        [
            {
                "course_id": 1,
                "status": "completed",
                "category": "Python",
                "level": "beginner",
            },
            {
                "course_id": 3,
                "status": "in_progress",
                "category": "Python",
                "level": "beginner",
            },
        ],
        limit=1,
        now=now,
    )

    assert cold_start is False
    assert recommendations[0]["score"] == 95
    assert "formation terminée" in recommendations[0]["reason"]
    assert "formation en cours" not in recommendations[0]["reason"]


def test_recommendation_engine_cold_start_order_is_deterministic():
    now = datetime.now(tz=timezone.utc)
    courses = [
        _sample_course(id=3, enrollment_count=5, level="intermediate", created_at=now),
        _sample_course(id=2, enrollment_count=5, level="beginner", created_at=now),
        _sample_course(id=1, enrollment_count=5, level="beginner", created_at=now),
    ]

    cold_start, recommendations = build_recommendations(courses, [], limit=3, now=now)

    assert cold_start is True
    assert [item["course_id"] for item in recommendations] == [1, 2, 3]


def test_list_courses_without_token(client):
    response = client.get("/api/v1/courses")
    assert response.status_code == 401


def test_list_courses_rejects_expired_token(client):
    response = client.get(
        "/api/v1/courses",
        headers=_auth_headers(
            exp=datetime.now(tz=timezone.utc) - timedelta(minutes=1),
        ),
    )

    assert response.status_code == 401


def test_list_courses_rejects_unknown_role(client):
    response = client.get(
        "/api/v1/courses",
        headers=_auth_headers(role="superadmin"),
    )

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


@patch("routes.courses.db_create_course")
def test_create_course_rejects_unknown_field(mock_create_course, client):
    response = client.post(
        "/api/v1/courses",
        headers=_auth_headers(role="admin", user_id=2),
        json={
            "title": "DevSecOps Fundamentals",
            "description": "Introduction to secure delivery pipelines",
            "duration": 24,
            "category": "DevSecOps",
            "owner_id": 1,
        },
    )

    assert response.status_code == 400
    mock_create_course.assert_not_called()


@patch("routes.courses.db_create_course")
def test_create_course_rejects_invalid_duration(mock_create_course, client):
    response = client.post(
        "/api/v1/courses",
        headers=_auth_headers(role="admin", user_id=2),
        json={
            "title": "DevSecOps Fundamentals",
            "description": "Introduction to secure delivery pipelines",
            "duration": True,
            "category": "DevSecOps",
        },
    )

    assert response.status_code == 400
    mock_create_course.assert_not_called()


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


@patch("routes.courses.delete_enrollment")
def test_admin_cannot_unenroll_from_course(mock_delete_enrollment, client):
    response = client.delete(
        "/api/v1/courses/1/enroll",
        headers=_auth_headers(role="admin", user_id=2),
    )

    assert response.status_code == 403
    mock_delete_enrollment.assert_not_called()


@patch("routes.courses.get_enrollments_by_user")
def test_admin_cannot_list_personal_enrollments(mock_get_enrollments, client):
    response = client.get(
        "/api/v1/courses/enrollments/me",
        headers=_auth_headers(role="admin", user_id=2),
    )

    assert response.status_code == 403
    mock_get_enrollments.assert_not_called()
