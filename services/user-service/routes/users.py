from datetime import datetime, timezone, timedelta
import os
from uuid import uuid4
import jwt
from flask import Blueprint, current_app, jsonify, request, send_from_directory
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from functools import wraps
import re
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


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
ALLOWED_ROLES = {"learner", "trainer", "admin"}
ALLOWED_AVATAR_EXTENSIONS = {"jpg", "jpeg", "png", "webp"}

# ─── DÉCORATEURS ──────────────────────────────────────────────────────────────


def token_required(f):
    """Vérifie que le JWT est présent et valide. Injecte current_user."""

    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]

        if not token:
            return jsonify({"error": "unauthorized", "message": "Token manquant"}), 401

        try:
            data = jwt.decode(
                token, Config.JWT_SECRET_KEY, algorithms=[Config.JWT_ALGORITHM]
            )
            current_user = get_user_by_id(data["user_id"])
            if not current_user:
                return (
                    jsonify(
                        {"error": "unauthorized", "message": "Utilisateur introuvable"}
                    ),
                    401,
                )
        except jwt.ExpiredSignatureError:
            return jsonify({"error": "unauthorized", "message": "Token expiré"}), 401
        except jwt.InvalidTokenError:
            return jsonify({"error": "unauthorized", "message": "Token invalide"}), 401

        return f(current_user, *args, **kwargs)

    return decorated


def admin_required(f):
    """Vérifie le JWT ET le rôle admin, sans imbriquer token_required."""

    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]

        if not token:
            return jsonify({"error": "unauthorized", "message": "Token manquant"}), 401

        try:
            data = jwt.decode(
                token, Config.JWT_SECRET_KEY, algorithms=[Config.JWT_ALGORITHM]
            )
            current_user = get_user_by_id(data["user_id"])
            if not current_user:
                return (
                    jsonify(
                        {"error": "unauthorized", "message": "Utilisateur introuvable"}
                    ),
                    401,
                )
        except jwt.ExpiredSignatureError:
            return jsonify({"error": "unauthorized", "message": "Token expiré"}), 401
        except jwt.InvalidTokenError:
            return jsonify({"error": "unauthorized", "message": "Token invalide"}), 401

        if current_user.get("role") != "admin":
            return (
                jsonify({"error": "forbidden", "message": "Accès réservé aux admins"}),
                403,
            )

        return f(current_user, *args, **kwargs)

    return decorated


def allowed_avatar(filename):
    return (
        "." in filename
        and filename.rsplit(".", 1)[1].lower() in ALLOWED_AVATAR_EXTENSIONS
    )


def avatar_url(filename):
    base_url = request.host_url.rstrip("/")
    return f"{base_url}/api/v1/users/uploads/avatars/{filename}"


# ─── ROUTES PUBLIQUES ─────────────────────────────────────────────────────────


@users_bp.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "service": Config.SERVICE_NAME}), 200


@users_bp.route("/register", methods=["POST"])
def register():
    data = request.get_json() or {}
    if not data.get("name") or not data.get("email") or not data.get("password"):
        return (
            jsonify({"error": "bad_request", "message": "Champs requis manquants"}),
            400,
        )

    if get_user_by_email(data["email"]):
        return jsonify({"error": "conflict", "message": "Email déjà utilisé"}), 409

    role = "learner"
    if not EMAIL_RE.match(data["email"]):
        return jsonify({"error": "bad_request", "message": "Format d'email invalide"}), 400

    hashed = generate_password_hash(data["password"])
    user = create_user(data["name"], data["email"], hashed, role)
    return jsonify(public_user(user)), 201


@users_bp.route("/login", methods=["POST"])
def login():
    data = request.get_json() or {}
    email = data.get("email")
    password = data.get("password")

    if not email or not password:
        return (
            jsonify(
                {"error": "bad_request", "message": "Email et mot de passe requis"}
            ),
            400,
        )

    user = get_user_by_email(email)
    if not user or not check_password_hash(user["password_hash"], password):
        return (
            jsonify({"error": "unauthorized", "message": "Identifiants invalides"}),
            401,
        )

    token = jwt.encode(
        {
            "user_id": user["id"],
            "email": user["email"],
            "role": user["role"],
            "exp": datetime.now(tz=timezone.utc)
              + timedelta(minutes=Config.JWT_EXPIRES_IN_MINUTES),
        },
        Config.JWT_SECRET_KEY,
        algorithm=Config.JWT_ALGORITHM,
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
    data = request.get_json() or {}
    allowed = {}

    if "name" in data:
        allowed["name"] = data["name"]
    if "email" in data:
        existing = get_user_by_email(data["email"])
        if existing and existing["id"] != current_user["id"]:
            return jsonify({"error": "conflict", "message": "Email déjà utilisé"}), 409
        allowed["email"] = data["email"]
    if "password" in data:
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


@users_bp.route("/me/avatar", methods=["POST"])
@token_required
def upload_avatar(current_user):
    if "avatar" not in request.files:
        return jsonify({"error": "bad_request", "message": "Fichier avatar manquant"}), 400

    file = request.files["avatar"]

    if not file.filename:
        return jsonify({"error": "bad_request", "message": "Nom de fichier manquant"}), 400

    if not allowed_avatar(file.filename):
        return (
            jsonify(
                {
                    "error": "bad_request",
                    "message": "Formats acceptes : jpg, jpeg, png, webp",
                }
            ),
            400,
        )

    if file.mimetype and not file.mimetype.startswith("image/"):
        return jsonify({"error": "bad_request", "message": "Le fichier doit etre une image"}), 400

    upload_folder = current_app.config["UPLOAD_FOLDER"]
    os.makedirs(upload_folder, exist_ok=True)

    original_filename = secure_filename(file.filename)
    extension = original_filename.rsplit(".", 1)[1].lower()
    stored_filename = f"user-{current_user['id']}-{uuid4().hex}.{extension}"
    destination = os.path.join(upload_folder, stored_filename)

    file.save(destination)

    updated = update_user(current_user["id"], avatar_url=avatar_url(stored_filename))
    return jsonify(public_user(updated)), 200


@users_bp.route("/uploads/avatars/<path:filename>", methods=["GET"])
def get_avatar(filename):
    return send_from_directory(current_app.config["UPLOAD_FOLDER"], filename)


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

    data = request.get_json() or {}
    allowed = {}
    if "name" in data:
        allowed["name"] = data["name"]
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
        allowed["password_hash"] = generate_password_hash(data["password"])

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
