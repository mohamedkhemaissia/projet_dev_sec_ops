from functools import wraps

import jwt
from flask import Blueprint, current_app, jsonify, request, g

from db.connection import courses_storage
from models.course import make_course


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
    return next((course for course in courses_storage["courses"] if course["id"] == course_id), None)


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


@courses_bp.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "service": current_app.config["SERVICE_NAME"]}), 200


@courses_bp.route("", methods=["GET"])
def get_courses():
    return jsonify(courses_storage["courses"]), 200


@courses_bp.route("/<int:course_id>", methods=["GET"])
def get_course(course_id):
    course = find_course_by_id(course_id)
    if course is None:
        return json_error(404, "not_found", "Course not found")
    return jsonify(course), 200


@courses_bp.route("", methods=["POST"])
@jwt_required
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

    course_id = courses_storage["next_id"]
    courses_storage["next_id"] += 1
    course = make_course(course_id, title, description, duration_value, instructor)
    courses_storage["courses"].append(course)
    return jsonify({"course": course, "created_by": g.current_user["email"]}), 201


@courses_bp.route("/<int:course_id>", methods=["PUT"])
@jwt_required
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

    return jsonify(course), 200


@courses_bp.route("/<int:course_id>", methods=["DELETE"])
@jwt_required
def delete_course(course_id):
    for index, course in enumerate(courses_storage["courses"]):
        if course["id"] == course_id:
            courses_storage["courses"].pop(index)
            return jsonify({"message": "Course deleted"}), 200
    return json_error(404, "not_found", "Course not found")
