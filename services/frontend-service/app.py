import os

from cachelib.file import FileSystemCache
from flask import Flask, flash, jsonify, redirect, render_template, request, session, url_for
from flask_session import Session
from flask_wtf.csrf import CSRFError, CSRFProtect

from api_client import TrainingHubAPI
from config import Config
from observability import init_observability
from routes.web import web_bp


def create_app(config_object=Config, api_client=None):
    app = Flask(__name__)
    app.config.from_object(config_object)

    session_dir = app.config["SESSION_FILE_DIR"]
    os.makedirs(session_dir, exist_ok=True)
    app.config["SESSION_CACHELIB"] = FileSystemCache(str(session_dir), threshold=500)

    Session(app)
    CSRFProtect(app)

    app.extensions["traininghub_api"] = api_client or TrainingHubAPI(
        app.config["USER_SERVICE_URL"],
        app.config["COURSE_SERVICE_URL"],
        app.config["CERTIFICATE_SERVICE_URL"],
        app.config["API_TIMEOUT_SECONDS"],
    )
    app.register_blueprint(web_bp)
    init_observability(app, "frontend-service")

    @app.context_processor
    def inject_identity():
        return {
            "current_user": session.get("user"),
            "is_authenticated": bool(session.get("access_token")),
        }

    @app.template_filter("status_label")
    def status_label(value):
        return {
            "enrolled": "Inscrit",
            "in_progress": "En cours",
            "completed": "Terminée",
            "active": "Valide",
            "revoked": "Révoqué",
            "beginner": "Débutant",
            "intermediate": "Intermédiaire",
            "advanced": "Avancé",
        }.get(value, value)

    @app.after_request
    def add_security_headers(response):
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = (
            "camera=(), microphone=(), geolocation=()"
        )
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "style-src 'self' https://cdn.jsdelivr.net; "
            "script-src 'self' https://cdn.jsdelivr.net; "
            "font-src 'self' https://cdn.jsdelivr.net data:; "
            "img-src 'self' data:; "
            "connect-src 'self'; "
            "frame-ancestors 'none'; "
            "base-uri 'self'; "
            "form-action 'self'"
        )
        if request_is_sensitive(response):
            response.headers["Cache-Control"] = "private, no-store"
        return response

    @app.get("/health")
    def health():
        return jsonify({"status": "ok", "service": "frontend-service"})

    @app.errorhandler(403)
    def forbidden(_error):
        return render_template("errors/error.html", code=403), 403

    @app.errorhandler(CSRFError)
    def csrf_error(_error):
        flash(
            "Le formulaire a expiré. Actualisez la page puis recommencez.",
            "warning",
        )
        return redirect(request.referrer or url_for("web.home"))

    @app.errorhandler(404)
    def not_found(_error):
        return render_template("errors/error.html", code=404), 404

    @app.errorhandler(500)
    def internal_error(_error):
        return render_template("errors/error.html", code=500), 500

    return app


def request_is_sensitive(response):
    return response.content_type.startswith("text/html") or bool(session)


if __name__ == "__main__":
    application = create_app()
    application.run(
        host=application.config["HOST"],
        port=application.config["PORT"],
        debug=application.config["DEBUG"],
    )
