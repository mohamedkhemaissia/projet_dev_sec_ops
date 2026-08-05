import hmac
from datetime import datetime, timezone
from functools import wraps
from uuid import uuid4

from flask import Blueprint, current_app, jsonify, request

from sanitization import sanitize_mapping, sanitize_text

incidents_bp = Blueprint("incidents", __name__, url_prefix="/api/v1")


def token_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        configured = current_app.config["AIOPS_WEBHOOK_TOKEN"]
        authorization = request.headers.get("Authorization", "")
        bearer_token = (
            authorization[7:]
            if authorization.lower().startswith("bearer ")
            else ""
        )
        supplied = bearer_token or request.headers.get("X-AIOPS-Token", "")
        if not configured or not hmac.compare_digest(configured, supplied):
            return jsonify({"error": "unauthorized"}), 401
        return view(*args, **kwargs)

    return wrapped


@incidents_bp.get("/health")
def health():
    return jsonify(
        {
            "status": "ok",
            "service": "ai-ops-service",
            "model_provider": current_app.config["AIOPS_MODEL_PROVIDER"],
            "read_only": True,
        }
    )


@incidents_bp.post("/alerts")
@token_required
def receive_alerts():
    payload = request.get_json(silent=True)
    validation_error = _validate_payload(payload)
    if validation_error:
        return jsonify({"error": "invalid_alert", "message": validation_error}), 400

    incident = _build_incident(payload)
    metrics_client = current_app.extensions["aiops_metrics_client"]
    incident["metrics"] = metrics_client.collect(incident["service"])
    analyzer = current_app.extensions["aiops_analyzer"]
    incident["analysis"] = analyzer.analyze(incident.copy())
    current_app.extensions["aiops_store"].add(incident)
    return jsonify(incident), 201


@incidents_bp.get("/incidents")
@token_required
def list_incidents():
    items = current_app.extensions["aiops_store"].list_all()
    return jsonify({"items": items, "count": len(items)})


@incidents_bp.get("/incidents/<incident_id>")
@token_required
def get_incident(incident_id):
    incident = current_app.extensions["aiops_store"].get(incident_id)
    if incident is None:
        return jsonify({"error": "not_found"}), 404
    return jsonify(incident)


def _validate_payload(payload):
    if not isinstance(payload, dict):
        return "A JSON object is required."
    alerts = payload.get("alerts")
    if not isinstance(alerts, list) or not alerts:
        return "At least one alert is required."
    if len(alerts) > current_app.config["MAX_ALERTS_PER_REQUEST"]:
        return "Too many alerts in one request."
    if not all(isinstance(alert, dict) for alert in alerts):
        return "Every alert must be an object."
    return None


def _build_incident(payload):
    max_length = current_app.config["MAX_TEXT_LENGTH"]
    first_alert = payload["alerts"][0]
    common_labels = sanitize_mapping(payload.get("commonLabels", {}), max_length)
    alert_labels = sanitize_mapping(first_alert.get("labels", {}), max_length)
    annotations = sanitize_mapping(
        {**payload.get("commonAnnotations", {}), **first_alert.get("annotations", {})},
        max_length,
    )
    labels = {**alert_labels, **common_labels}

    service = labels.get("service", "")
    if service not in current_app.config["ALLOWED_SERVICES"]:
        service = "unknown"

    severity = labels.get("severity", "warning")
    if severity not in {"info", "warning", "critical"}:
        severity = "warning"

    return {
        "id": uuid4().hex,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "status": sanitize_text(payload.get("status", "firing"), 20),
        "service": service,
        "alertname": sanitize_text(labels.get("alertname", "UnknownAlert"), 100),
        "severity": severity,
        "summary": sanitize_text(annotations.get("summary", ""), max_length),
        "description": sanitize_text(annotations.get("description", ""), max_length),
        "labels": labels,
    }
