import re
from functools import wraps

import jwt
from flask import Blueprint, current_app, g, jsonify, request, send_file

from certificate_pdf import generate_certificate_pdf

from db.connection import (
    create_certificate,
    get_certificate_by_id,
    get_certificates_by_user,
    get_completed_enrollment,
    verify_certificate,
)

certificates_bp = Blueprint("certificates", __name__, url_prefix="/api/v1/certificates")
ALLOWED_ROLES = {"learner", "admin"}
JWT_REQUIRED_CLAIMS = ["exp", "iat", "iss", "aud", "user_id", "email", "role"]


def json_error(status_code, error, message):
    return jsonify({"error": error, "message": message}), status_code


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
            issuer=current_app.config["JWT_ISSUER"],
            audience=current_app.config["JWT_AUDIENCE"],
            options={"require": JWT_REQUIRED_CLAIMS},
        )
    except jwt.ExpiredSignatureError:
        return None, json_error(401, "unauthorized", "Token expired")
    except jwt.InvalidTokenError:
        return None, json_error(401, "unauthorized", "Invalid token")

    if (
        type(payload.get("user_id")) is not int
        or not isinstance(payload.get("email"), str)
        or payload.get("role") not in ALLOWED_ROLES
    ):
        return None, json_error(401, "unauthorized", "Invalid token claims")

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


def learner_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        payload, error_response = decode_token_from_request()
        if error_response:
            return error_response
        if payload.get("role") != "learner":
            return json_error(403, "forbidden", "Only learners can issue certificates")
        g.current_user = payload
        return fn(*args, **kwargs)

    return wrapper


@certificates_bp.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "service": current_app.config["SERVICE_NAME"]}), 200


@certificates_bp.route("/courses/<int:course_id>/issue", methods=["POST"])
@learner_required
def issue_certificate(course_id):
    user_id = g.current_user["user_id"]
    enrollment = get_completed_enrollment(user_id, course_id)
    if enrollment is None:
        return json_error(
            403,
            "forbidden",
            "A completed enrollment is required before issuing a certificate",
        )

    certificate, created = create_certificate(user_id, course_id)
    status_code = 201 if created else 200
    return jsonify(certificate), status_code


@certificates_bp.route("/me", methods=["GET"])
@jwt_required
def get_my_certificates():
    if g.current_user.get("role") != "learner":
        return json_error(403, "forbidden", "Only learners can list their certificates")
    return jsonify(get_certificates_by_user(g.current_user["user_id"])), 200


@certificates_bp.route("/<int:certificate_id>", methods=["GET"])
@jwt_required
def get_certificate(certificate_id):
    user_id = None
    if g.current_user.get("role") == "learner":
        user_id = g.current_user["user_id"]

    certificate = get_certificate_by_id(certificate_id, user_id=user_id)
    if certificate is None:
        return json_error(404, "not_found", "Certificate not found")

    return jsonify(certificate), 200


@certificates_bp.route("/<int:certificate_id>/download", methods=["GET"])
@jwt_required
def download_certificate(certificate_id):
    role = g.current_user.get("role")
    if role not in {"admin", "learner"}:
        return json_error(403, "forbidden", "You are not allowed to download certificates")

    user_id = g.current_user["user_id"] if role == "learner" else None
    certificate = get_certificate_by_id(certificate_id, user_id=user_id)
    if certificate is None:
        return json_error(404, "not_found", "Certificate not found")
    if certificate["status"] != "active":
        return json_error(409, "certificate_revoked", "Revoked certificates cannot be downloaded")

    certificate_code = str(certificate["certificate_code"])
    safe_code = re.sub(r"[^A-Za-z0-9_-]", "-", certificate_code)
    verification_url = (
        f"{current_app.config['CERTIFICATE_VERIFY_BASE_URL']}/{certificate_code}"
    )
    pdf_buffer = generate_certificate_pdf(certificate, verification_url)
    response = send_file(
        pdf_buffer,
        mimetype="application/pdf",
        as_attachment=True,
        download_name=f"certificat-{safe_code}.pdf",
    )
    response.headers["Cache-Control"] = "private, no-store"
    response.headers["X-Content-Type-Options"] = "nosniff"
    return response


@certificates_bp.route("/verify/<certificate_code>", methods=["GET"])
def verify_certificate_by_code(certificate_code):
    certificate = verify_certificate(certificate_code)
    if certificate is None:
        return json_error(404, "not_found", "Certificate not found")

    return jsonify(
        {
            "valid": certificate["status"] == "active",
            "certificate": certificate,
        }
    ), 200
