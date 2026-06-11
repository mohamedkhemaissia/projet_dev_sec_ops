from functools import wraps

import jwt
from flask import Blueprint, current_app, jsonify, request, g

from db.connection import (
    create_course as db_create_course,
    delete_course as db_delete_course,
    get_all_courses,
    get_course_by_id,
    update_course as db_update_course,
)


courses_bp = Blueprint("courses", __name__, url_prefix="/courses")


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
            issuer="user-service",
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
    instructor = data.get("instructor")

    if not title or not description or duration is None or not instructor:
        return json_error(400, "bad_request", "title, description, duration and instructor are required")

    try:
        duration_value = float(duration)
    except (TypeError, ValueError):
        return json_error(400, "bad_request", "duration must be a number")

    if duration_value <= 0:
        return json_error(400, "bad_request", "duration must be greater than 0")

    course = db_create_course(title, description, duration_value, instructor)
    return jsonify({"course": course, "created_by": g.current_user["email"]}), 201


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
    if "instructor" in data and data["instructor"]:
        course["instructor"] = data["instructor"]
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
        instructor=course.get("instructor"),
    )
    return jsonify(updated_course), 200


@courses_bp.route("/<int:course_id>", methods=["DELETE"])
@admin_required
def delete_course(course_id):
    deleted_count = db_delete_course(course_id)
    if deleted_count == 0:
        return json_error(404, "not_found", "Course not found")
    return jsonify({"message": "Course deleted"}), 200
