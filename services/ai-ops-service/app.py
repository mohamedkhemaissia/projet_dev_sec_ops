from pathlib import Path

from flask import Flask, jsonify

from aiops_observability import init_observability
from aiops_routes.dashboard import dashboard_bp
from aiops_routes.incidents import incidents_bp
from analyzer import build_analyzer
from config import Config
from metrics_context import PrometheusContextClient
from store import IncidentStore

SERVICE_ROOT = Path(__file__).resolve().parent


def create_app(test_config=None, analyzer=None, metrics_client=None, store=None):
    app = Flask(__name__, root_path=str(SERVICE_ROOT))
    app.config.from_object(Config)
    if test_config:
        app.config.update(test_config)

    if not app.config.get("TESTING") and not app.config["AIOPS_WEBHOOK_TOKEN"]:
        raise RuntimeError("AIOPS_WEBHOOK_TOKEN must be configured")

    app.extensions["aiops_analyzer"] = analyzer or build_analyzer(app.config)
    app.extensions["aiops_metrics_client"] = metrics_client or PrometheusContextClient(
        app.config["PROMETHEUS_URL"],
        app.config["PROMETHEUS_TIMEOUT_SECONDS"],
        app.config["ALLOWED_SERVICES"],
    )
    app.extensions["aiops_store"] = store or IncidentStore(
        app.config["INCIDENT_HISTORY_LIMIT"]
    )

    app.register_blueprint(incidents_bp)
    app.register_blueprint(dashboard_bp)
    init_observability(app)

    @app.after_request
    def add_security_headers(response):
        response.headers["Cache-Control"] = "no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        return response

    @app.errorhandler(413)
    def payload_too_large(_error):
        return jsonify({"error": "payload_too_large"}), 413

    @app.errorhandler(500)
    def internal_error(_error):
        return jsonify({"error": "internal_server_error"}), 500

    return app


if __name__ == "__main__":
    application = create_app()
    application.run(host=Config.HOST, port=Config.PORT, debug=Config.DEBUG)
