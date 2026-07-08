from functools import wraps

import jwt
from flask import Blueprint, current_app, g, jsonify, request

from db.connection import (
    create_course as db_create_course,
    create_enrollment,
    delete_enrollment,
    delete_course as db_delete_course,
    get_all_courses,
    get_course_by_id,
    get_enrollment,
    get_enrollments_by_course,
    get_enrollments_by_user,
    update_course as db_update_course,
    update_enrollment_status,
)

courses_bp = Blueprint("courses", __name__, url_prefix="/api/v1/courses")
ALLOWED_LEVELS = {"beginner", "intermediate", "advanced"}
ALLOWED_ENROLLMENT_STATUS = {"enrolled", "in_progress", "completed"}


def json_error(status_code, error, message):
    return jsonify({"error": error, "message": message}), status_code


def get_json_body():
    if not request.is_json:
        return None, json_error(400, "bad_request", "JSON body required")
    payload = request.get_json(silent=True)
    if payload is None:
        return None, json_error(400, "bad_request", "Invalid JSON payload")
    return payload, None


def find_course_by_id(course_id):
    return get_course_by_id(course_id)


def decode_token_from_request():
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return None, json_error(401, "unauthorized", "Bearer token required")

    token = auth_header.split(" ", 1)[1].strip()
    try:
        payload = jwt.decode(
            token,
            current_app.config["JWT_SECRET_KEY"],
            algorithms=[current_app.config["JWT_ALGORITHM"]],
        )
    except jwt.ExpiredSignatureError:
        return None, json_error(401, "unauthorized", "Token expired")
    except jwt.InvalidTokenError:
        return None, json_error(401, "unauthorized", "Invalid token")

    return payload, None


def jwt_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        payload, error_response = decode_token_from_request()
        if error_response:
            return error_response
        g.current_user = payload
        return fn(*args, **kwargs)

    return wrapper


def admin_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        payload, error_response = decode_token_from_request()
        if error_response:
            return error_response
        if payload.get("role") != "admin":
            return json_error(403, "forbidden", "Admin privileges required")
        g.current_user = payload
        return fn(*args, **kwargs)

    return wrapper


@courses_bp.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "service": current_app.config["SERVICE_NAME"]}), 200


@courses_bp.route("", methods=["GET"])
@jwt_required
def get_courses():
    return jsonify(get_all_courses()), 200


@courses_bp.route("/<int:course_id>", methods=["GET"])
@jwt_required
def get_course(course_id):
    course = find_course_by_id(course_id)
    if course is None:
        return json_error(404, "not_found", "Course not found")
    return jsonify(course), 200


@courses_bp.route("", methods=["POST"])
@admin_required
def create_course():
    data, error_response = get_json_body()
    if error_response:
        return error_response

    title = data.get("title")
    description = data.get("description")
    duration = data.get("duration")
    level = data.get("level", "beginner")
    category = data.get("category")

    if not title or not description or duration is None or not category:
        return json_error(
            400,
            "bad_request",
            "title, description, duration and category are required",
        )

    try:
        duration_value = float(duration)
    except (TypeError, ValueError):
        return json_error(400, "bad_request", "duration must be a number")

    if duration_value <= 0:
        return json_error(400, "bad_request", "duration must be greater than 0")

    if level not in ALLOWED_LEVELS:
        return json_error(400, "bad_request", "Invalid level")

    course = db_create_course(
        title,
        description,
        duration_value,
        level,
        category,
    )
    return jsonify({"course": course, "created_by": g.current_user.get("email")}), 201


@courses_bp.route("/<int:course_id>", methods=["PUT"])
@admin_required
def update_course(course_id):
    course = find_course_by_id(course_id)
    if course is None:
        return json_error(404, "not_found", "Course not found")

    data, error_response = get_json_body()
    if error_response:
        return error_response

    if "title" in data and data["title"]:
        course["title"] = data["title"]
    if "description" in data and data["description"]:
        course["description"] = data["description"]
    if "level" in data and data["level"]:
        if data["level"] not in ALLOWED_LEVELS:
            return json_error(400, "bad_request", "Invalid level")
        course["level"] = data["level"]
    if "category" in data and data["category"]:
        course["category"] = data["category"]
    if "duration" in data:
        try:
            duration_value = float(data["duration"])
        except (TypeError, ValueError):
            return json_error(400, "bad_request", "duration must be a number")
        if duration_value <= 0:
            return json_error(400, "bad_request", "duration must be greater than 0")
        course["duration"] = duration_value

    updated_course = db_update_course(
        course_id,
        title=course.get("title"),
        description=course.get("description"),
        duration=course.get("duration"),
        level=course.get("level"),
        category=course.get("category"),
    )
    return jsonify(updated_course), 200


@courses_bp.route("/<int:course_id>", methods=["DELETE"])
@admin_required
def delete_course(course_id):
    deleted_count = db_delete_course(course_id)
    if deleted_count == 0:
        return json_error(404, "not_found", "Course not found")
    return jsonify({"message": "Course deleted"}), 200


@courses_bp.route("/<int:course_id>/enroll", methods=["POST"])
@jwt_required
def enroll_in_course(course_id):
    if g.current_user.get("role") == "admin":
        return json_error(403, "forbidden", "Admins cannot enroll in courses")

    course = find_course_by_id(course_id)
    if course is None:
        return json_error(404, "not_found", "Course not found")

    user_id = g.current_user["user_id"]
    if get_enrollment(user_id, course_id):
        return json_error(409, "conflict", "User already enrolled in this course")

    enrollment = create_enrollment(user_id, course_id)
    return jsonify(enrollment), 201


@courses_bp.route("/<int:course_id>/enroll", methods=["DELETE"])
@jwt_required
def unenroll_from_course(course_id):
    course = find_course_by_id(course_id)
    if course is None:
        return json_error(404, "not_found", "Course not found")

    user_id = g.current_user["user_id"]
    deleted_count = delete_enrollment(user_id, course_id)
    if deleted_count == 0:
        return json_error(404, "not_found", "Enrollment not found")

    return jsonify({"message": "Enrollment cancelled"}), 200


@courses_bp.route("/enrollments/me", methods=["GET"])
@jwt_required
def get_my_enrollments():
    return jsonify(get_enrollments_by_user(g.current_user["user_id"])), 200


@courses_bp.route("/<int:course_id>/enrollments", methods=["GET"])
@admin_required
def get_course_enrollments(course_id):
    course = find_course_by_id(course_id)
    if course is None:
        return json_error(404, "not_found", "Course not found")
    return jsonify(get_enrollments_by_course(course_id)), 200


@courses_bp.route("/enrollments/<int:enrollment_id>/status", methods=["PUT"])
@admin_required
def change_enrollment_status(enrollment_id):
    data, error_response = get_json_body()
    if error_response:
        return error_response

    status = data.get("status")
    if status not in ALLOWED_ENROLLMENT_STATUS:
        return json_error(400, "bad_request", "Invalid enrollment status")

    enrollment = update_enrollment_status(enrollment_id, status)
    if enrollment is None:
        return json_error(404, "not_found", "Enrollment not found")

    return jsonify(enrollment), 200
