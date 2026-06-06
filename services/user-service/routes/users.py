from datetime import datetime, timedelta, timezone
from functools import wraps

import jwt
from flask import Blueprint, current_app, jsonify, request, g
from werkzeug.security import check_password_hash, generate_password_hash

from db.connection import users_storage
from models.user import make_user, public_user


users_bp = Blueprint("users", __name__, url_prefix="/users")


def json_error(status_code, error, message):
    return jsonify({"error": error, "message": message}), status_code


def get_json_body():
    if not request.is_json:
        return None, json_error(400, "bad_request", "JSON body required")
    payload = request.get_json(silent=True)
    if payload is None:
        return None, json_error(400, "bad_request", "Invalid JSON payload")
    return payload, None


def find_user_by_id(user_id):
    return next((user for user in users_storage["users"] if user["id"] == user_id), None)


def find_user_by_email(email):
    return next((user for user in users_storage["users"] if user["email"].lower() == email.lower()), None)


def build_token(user):
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user["id"]),
        "user_id": user["id"],
        "email": user["email"],
        "name": user["name"],
        "role": user.get("role", "user"),
        "iss": current_app.config["SERVICE_NAME"],
        "iat": now,
        "exp": now + timedelta(minutes=current_app.config["JWT_EXPIRES_IN_MINUTES"]),
    }
    token = jwt.encode(
        payload,
        current_app.config["JWT_SECRET_KEY"],
        algorithm=current_app.config["JWT_ALGORITHM"],
    )
    return token if isinstance(token, str) else token.decode("utf-8")


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
            issuer=current_app.config["SERVICE_NAME"],
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


def self_or_admin_required(user_id):
    payload, error_response = decode_token_from_request()
    if error_response:
        return None, error_response
    current_user_id = payload.get("user_id")
    if payload.get("role") != "admin" and current_user_id != user_id:
        return None, json_error(403, "forbidden", "You can only access your own account")
    g.current_user = payload
    return payload, None


@users_bp.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "service": current_app.config["SERVICE_NAME"]}), 200


@users_bp.route("", methods=["GET"])
@admin_required
def get_users():
    return jsonify([public_user(user) for user in users_storage["users"]]), 200


@users_bp.route("/me", methods=["GET"])
@jwt_required
def get_me():
    user = find_user_by_id(g.current_user["user_id"])
    if user is None:
        return json_error(404, "not_found", "User not found")
    return jsonify(public_user(user)), 200


@users_bp.route("/<int:user_id>", methods=["GET"])
def get_user(user_id):
    _, error_response = self_or_admin_required(user_id)
    if error_response:
        return error_response

    user = find_user_by_id(user_id)
    if user is None:
        return json_error(404, "not_found", "User not found")
    return jsonify(public_user(user)), 200


@users_bp.route("", methods=["POST"])
def create_user():
    data, error_response = get_json_body()
    if error_response:
        return error_response

    name = data.get("name")
    email = data.get("email")
    password = data.get("password")
    role = data.get("role", "user")

    if not name or not email or not password:
        return json_error(400, "bad_request", "name, email and password are required")
    if "@" not in email:
        return json_error(400, "bad_request", "Invalid email address")
    if len(password) < 8:
        return json_error(400, "bad_request", "Password must contain at least 8 characters")
    if role != "user":
        return json_error(403, "forbidden", "Public registration cannot assign elevated roles")
    if find_user_by_email(email):
        return json_error(409, "conflict", "Email already exists")

    user_id = users_storage["next_id"]
    users_storage["next_id"] += 1
    password_hash = generate_password_hash(password)
    user = make_user(user_id, name, email, password_hash, role=role)
    users_storage["users"].append(user)

    token = build_token(user)
    return jsonify({"user": public_user(user), "token": token}), 201


@users_bp.route("/login", methods=["POST"])
def login():
    data, error_response = get_json_body()
    if error_response:
        return error_response

    email = data.get("email")
    password = data.get("password")
    if not email or not password:
        return json_error(400, "bad_request", "email and password are required")

    user = find_user_by_email(email)
    if user is None or not check_password_hash(user["password_hash"], password):
        return json_error(401, "unauthorized", "Invalid credentials")

    token = build_token(user)
    return jsonify({"message": "Login successful", "token": token, "user": public_user(user)}), 200


@users_bp.route("/<int:user_id>", methods=["PUT"])
def update_user(user_id):
    acting_user, error_response = self_or_admin_required(user_id)
    if error_response:
        return error_response

    user = find_user_by_id(user_id)
    if user is None:
        return json_error(404, "not_found", "User not found")

    data, error_response = get_json_body()
    if error_response:
        return error_response

    name = data.get("name")
    email = data.get("email")
    password = data.get("password")
    role = data.get("role")

    if name:
        user["name"] = name
    if email:
        if "@" not in email:
            return json_error(400, "bad_request", "Invalid email address")
        existing_user = find_user_by_email(email)
        if existing_user and existing_user["id"] != user_id:
            return json_error(409, "conflict", "Email already exists")
        user["email"] = email
    if password:
        if len(password) < 8:
            return json_error(400, "bad_request", "Password must contain at least 8 characters")
        user["password_hash"] = generate_password_hash(password)
    if role is not None:
        if acting_user.get("role") != "admin":
            return json_error(403, "forbidden", "Only an admin can update roles")
        if role not in {"user", "admin"}:
            return json_error(400, "bad_request", "Invalid role")
        user["role"] = role

    return jsonify(public_user(user)), 200


@users_bp.route("/<int:user_id>", methods=["DELETE"])
def delete_user(user_id):
    _, error_response = self_or_admin_required(user_id)
    if error_response:
        return error_response

    for index, user in enumerate(users_storage["users"]):
        if user["id"] == user_id:
            users_storage["users"].pop(index)
            return jsonify({"message": "User deleted"}), 200
    return json_error(404, "not_found", "User not found")
