from datetime import datetime, timedelta, timezone
from functools import wraps
import re
from uuid import uuid4

import jwt
from flask import Blueprint, current_app, jsonify, request
from werkzeug.security import check_password_hash, generate_password_hash

from db.connection import (
    create_user,
    get_user_by_email,
    get_user_by_id,
    get_all_users,
    update_user,
    delete_user,
)
from models.user import public_user
from config import Config

users_bp = Blueprint("users", __name__, url_prefix="/api/v1/users")
ALLOWED_ROLES = {"learner", "admin"}
JWT_REQUIRED_CLAIMS = ["exp", "iat", "iss", "aud", "user_id", "email", "role"]
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
REGISTER_FIELDS = {"name", "email", "password"}
PROFILE_FIELDS = {"name", "email", "password"}
ADMIN_UPDATE_FIELDS = {"name", "role", "password"}
MIN_PASSWORD_LENGTH = 12
MAX_PASSWORD_LENGTH = 128


def json_error(status_code, error, message):
    return jsonify({"error": error, "message": message}), status_code


def get_json_object():
    if not request.is_json:
        return None, json_error(400, "bad_request", "JSON body required")
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return None, json_error(400, "bad_request", "JSON object required")
    return payload, None


def reject_unknown_fields(data, allowed_fields):
    unknown_fields = sorted(set(data) - allowed_fields)
    if unknown_fields:
        return json_error(
            400,
            "bad_request",
            f"Unknown fields: {', '.join(unknown_fields)}",
        )
    return None


def validate_name(value):
    if not isinstance(value, str):
        return None, "name must be a string"
    name = value.strip()
    if not 2 <= len(name) <= 100:
        return None, "name must contain between 2 and 100 characters"
    return name, None


def validate_email(value):
    if not isinstance(value, str):
        return None, "email must be a string"
    email = value.strip().lower()
    if len(email) > 254 or not EMAIL_RE.fullmatch(email):
        return None, "Invalid email format"
    return email, None


def validate_password(value):
    if not isinstance(value, str):
        return "password must be a string"
    if not MIN_PASSWORD_LENGTH <= len(value) <= MAX_PASSWORD_LENGTH:
        return "password must contain between 12 and 128 characters"
    if not re.search(r"[a-z]", value) or not re.search(r"[A-Z]", value):
        return "password must contain upper and lower case letters"
    if not re.search(r"\d", value) or not re.search(r"[^A-Za-z0-9]", value):
        return "password must contain a digit and a special character"
    return None

# ─── DÉCORATEURS ──────────────────────────────────────────────────────────────


def decode_current_user():
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return None, (
            jsonify({"error": "unauthorized", "message": "Bearer token requis"}),
            401,
        )

    token = auth_header.split(" ", 1)[1].strip()
    if not token:
        return None, (
            jsonify({"error": "unauthorized", "message": "Bearer token requis"}),
            401,
        )

    try:
        data = jwt.decode(
            token,
            current_app.config["JWT_SECRET_KEY"],
            algorithms=[current_app.config["JWT_ALGORITHM"]],
            issuer=current_app.config["JWT_ISSUER"],
            audience=current_app.config["JWT_AUDIENCE"],
            options={"require": JWT_REQUIRED_CLAIMS},
        )
    except jwt.ExpiredSignatureError:
        return None, (
            jsonify({"error": "unauthorized", "message": "Token expire"}),
            401,
        )
    except jwt.InvalidTokenError:
        return None, (
            jsonify({"error": "unauthorized", "message": "Token invalide"}),
            401,
        )

    if (
        type(data.get("user_id")) is not int
        or not isinstance(data.get("email"), str)
        or data.get("role") not in ALLOWED_ROLES
    ):
        return None, (
            jsonify({"error": "unauthorized", "message": "Claims JWT invalides"}),
            401,
        )

    current_user = get_user_by_id(data["user_id"])
    if not current_user:
        return None, (
            jsonify({"error": "unauthorized", "message": "Utilisateur introuvable"}),
            401,
        )
    return current_user, None


def token_required(f):
    """Vérifie que le JWT est présent et valide. Injecte current_user."""

    @wraps(f)
    def decorated(*args, **kwargs):
        current_user, error_response = decode_current_user()
        if error_response:
            return error_response
        return f(current_user, *args, **kwargs)

    return decorated


def admin_required(f):
    """Vérifie le JWT et le rôle admin."""

    @wraps(f)
    def decorated(*args, **kwargs):
        current_user, error_response = decode_current_user()
        if error_response:
            return error_response
        if current_user.get("role") != "admin":
            return (
                jsonify({"error": "forbidden", "message": "Accès réservé aux admins"}),
                403,
            )
        return f(current_user, *args, **kwargs)

    return decorated


# ─── ROUTES PUBLIQUES ─────────────────────────────────────────────────────────


@users_bp.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "service": Config.SERVICE_NAME}), 200


@users_bp.route("/register", methods=["POST"])
def register():
    data, error_response = get_json_object()
    if error_response:
        return error_response
    unknown_fields_error = reject_unknown_fields(data, REGISTER_FIELDS)
    if unknown_fields_error:
        return unknown_fields_error
    if not REGISTER_FIELDS.issubset(data):
        return json_error(400, "bad_request", "name, email and password are required")

    name, name_error = validate_name(data["name"])
    email, email_error = validate_email(data["email"])
    password_error = validate_password(data["password"])
    validation_error = name_error or email_error or password_error
    if validation_error:
        return json_error(400, "bad_request", validation_error)
    if get_user_by_email(email):
        return json_error(409, "conflict", "Email already used")

    hashed = generate_password_hash(data["password"])
    user = create_user(name, email, hashed, "learner")
    return jsonify(public_user(user)), 201


@users_bp.route("/login", methods=["POST"])
def login():
    data, error_response = get_json_object()
    if error_response:
        return error_response
    email = data.get("email")
    password = data.get("password")

    if not email or not password:
        return (
            jsonify(
                {"error": "bad_request", "message": "Email et mot de passe requis"}
            ),
            400,
        )

    normalized_email, email_error = validate_email(email)
    if email_error or not isinstance(password, str):
        return json_error(401, "unauthorized", "Invalid credentials")

    user = get_user_by_email(normalized_email)
    if not user or not check_password_hash(user["password_hash"], password):
        return (
            jsonify({"error": "unauthorized", "message": "Identifiants invalides"}),
            401,
        )

    issued_at = datetime.now(tz=timezone.utc)
    token = jwt.encode(
        {
            "user_id": user["id"],
            "email": user["email"],
            "role": user["role"],
            "iat": issued_at,
            "exp": issued_at
            + timedelta(minutes=current_app.config["JWT_EXPIRES_IN_MINUTES"]),
            "iss": current_app.config["JWT_ISSUER"],
            "aud": current_app.config["JWT_AUDIENCE"],
            "jti": uuid4().hex,
        },
        current_app.config["JWT_SECRET_KEY"],
        algorithm=current_app.config["JWT_ALGORITHM"],
    )

    return (
        jsonify(
            {"message": "Connexion réussie", "token": token, "user": public_user(user)}
        ),
        200,
    )


# ─── ROUTES PROTÉGÉES (utilisateur connecté) ──────────────────────────────────


@users_bp.route("/me", methods=["GET"])
@token_required  # ← bug corrigé : décorateur ajouté
def get_profile(current_user):
    return jsonify(public_user(current_user)), 200


@users_bp.route("/me", methods=["PUT"])
@token_required
def update_profile(current_user):
    data, error_response = get_json_object()
    if error_response:
        return error_response
    unknown_fields_error = reject_unknown_fields(data, PROFILE_FIELDS)
    if unknown_fields_error:
        return unknown_fields_error
    allowed = {}

    if "name" in data:
        name, validation_error = validate_name(data["name"])
        if validation_error:
            return json_error(400, "bad_request", validation_error)
        allowed["name"] = name
    if "email" in data:
        email, validation_error = validate_email(data["email"])
        if validation_error:
            return json_error(400, "bad_request", validation_error)
        existing = get_user_by_email(email)
        if existing and existing["id"] != current_user["id"]:
            return jsonify({"error": "conflict", "message": "Email déjà utilisé"}), 409
        allowed["email"] = email
    if "password" in data:
        validation_error = validate_password(data["password"])
        if validation_error:
            return json_error(400, "bad_request", validation_error)
        allowed["password_hash"] = generate_password_hash(data["password"])

    if not allowed:
        return (
            jsonify(
                {"error": "bad_request", "message": "Aucune donnée à mettre à jour"}
            ),
            400,
        )

    updated = update_user(current_user["id"], **allowed)
    return jsonify(public_user(updated)), 200


# ─── ROUTES ADMIN ─────────────────────────────────────────────────────────────


@users_bp.route("/", methods=["GET"])
@admin_required
def list_users(current_user):
    users = get_all_users()
    return jsonify([public_user(u) for u in users]), 200


@users_bp.route("/<int:user_id>", methods=["GET"])
@admin_required
def get_user(current_user, user_id):
    user = get_user_by_id(user_id)
    if not user:
        return (
            jsonify({"error": "not_found", "message": "Utilisateur introuvable"}),
            404,
        )
    return jsonify(public_user(user)), 200


@users_bp.route("/<int:user_id>", methods=["PUT"])
@admin_required
def update_user_admin(current_user, user_id):
    user = get_user_by_id(user_id)
    if not user:
        return (
            jsonify({"error": "not_found", "message": "Utilisateur introuvable"}),
            404,
        )

    data, error_response = get_json_object()
    if error_response:
        return error_response
    unknown_fields_error = reject_unknown_fields(data, ADMIN_UPDATE_FIELDS)
    if unknown_fields_error:
        return unknown_fields_error
    allowed = {}
    if "name" in data:
        name, validation_error = validate_name(data["name"])
        if validation_error:
            return json_error(400, "bad_request", validation_error)
        allowed["name"] = name
    if "role" in data:
        if data["role"] not in ALLOWED_ROLES:
            return (
                jsonify(
                    {
                        "error": "bad_request",
                        "message": f"Rôle invalide. Valeurs acceptées : {ALLOWED_ROLES}",
                    }
                ),
                400,
            )
        allowed["role"] = data["role"]
    if "password" in data:
        validation_error = validate_password(data["password"])
        if validation_error:
            return json_error(400, "bad_request", validation_error)
        allowed["password_hash"] = generate_password_hash(data["password"])

    if not allowed:
        return json_error(400, "bad_request", "No data to update")

    updated = update_user(user_id, **allowed)
    return jsonify(public_user(updated)), 200


@users_bp.route("/<int:user_id>", methods=["DELETE"])
@admin_required
def delete_user_route(current_user, user_id):
    if current_user["id"] == user_id:
        return (
            jsonify(
                {
                    "error": "bad_request",
                    "message": "Impossible de supprimer son propre compte",
                }
            ),
            400,
        )

    affected = delete_user(user_id)
    if affected == 0:
        return (
            jsonify({"error": "not_found", "message": "Utilisateur introuvable"}),
            404,
        )
    return jsonify({"message": "Utilisateur supprimé"}), 200
