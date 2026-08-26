import sys
from json import dumps
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

AIOPS_SERVICE_PATH = Path(__file__).resolve().parents[1] / "services" / "ai-ops-service"
for module_name in [
    "app",
    "config",
    "analyzer",
    "aiops_observability",
    "aiops_routes",
    "aiops_routes.dashboard",
    "aiops_routes.incidents",
    "metrics_context",
    "sanitization",
    "store",
]:
    sys.modules.pop(module_name, None)
sys.path.insert(0, str(AIOPS_SERVICE_PATH))

from analyzer import OllamaAnalyzer, ResilientAnalyzer, RuleBasedAnalyzer  # noqa: E402
from app import create_app  # noqa: E402


class FakeMetricsClient:
    def collect(self, service):
        return {
            "available": True,
            "values": {
                "availability": 1.0,
                "http_5xx_rate": 0.12,
                "p95_latency_seconds": 0.4,
            },
            "service": service,
        }


class FakeAnalyzer:
    def analyze(self, incident):
        return {
            "summary": f"Analyse de {incident['alertname']}",
            "probable_cause": "Dependance indisponible",
            "severity": "critical",
            "confidence": 0.8,
            "recommendations": ["Verifier la dependance"],
            "analysis_mode": "ollama",
            "model_severity": "warning",
            "model_metrics": {"model": "gemma3:1b"},
        }


class BrokenAnalyzer:
    def analyze(self, _incident):
        raise ValueError("invalid model output")


@pytest.fixture
def client():
    app = create_app(
        {
            "TESTING": True,
            "AIOPS_WEBHOOK_TOKEN": "test-token",
            "ALLOWED_SERVICES": ("course-service",),
        },
        analyzer=FakeAnalyzer(),
        metrics_client=FakeMetricsClient(),
    )
    with app.test_client() as test_client:
        yield test_client


def _alert_payload(**overrides):
    payload = {
        "status": "firing",
        "commonLabels": {
            "alertname": "TrainingHubHighErrorRate",
            "service": "course-service",
            "severity": "warning",
        },
        "commonAnnotations": {
            "summary": "Taux d'erreurs eleve",
            "description": "Le service produit plus de 5 % d'erreurs.",
        },
        "alerts": [{"status": "firing", "labels": {}, "annotations": {}}],
    }
    payload.update(overrides)
    return payload


def _headers(token="test-token"):
    return {"X-AIOPS-Token": token}


def test_health_is_public_and_read_only(client):
    response = client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.get_json()["read_only"] is True


def test_metrics_are_exposed(client):
    response = client.get("/metrics")

    assert response.status_code == 200
    assert b"traininghub_aiops_requests_total" in response.data


def test_dashboard_displays_empty_state_without_incidents(client):
    response = client.get("/dashboard")

    assert response.status_code == 200
    assert "Aucun incident AIOps détecté." in response.get_data(as_text=True)
    assert b'<meta http-equiv="refresh" content="10">' in response.data


def test_dashboard_displays_ollama_analysis_without_webhook_token(client):
    created = client.post(
        "/api/v1/alerts",
        json=_alert_payload(),
        headers=_headers(),
    )

    assert created.status_code == 201

    response = client.get("/dashboard")
    page = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "course-service" in page
    assert "TrainingHubHighErrorRate" in page
    assert "OLLAMA" in page
    assert "gemma3:1b" in page
    assert "80 %" in page
    assert "Dependance indisponible" in page
    assert "400.0 ms" in page
    assert "test-token" not in page


def test_dashboard_lists_newest_incident_first(client):
    older = _alert_payload()
    older["commonAnnotations"]["summary"] = "Incident plus ancien"
    newer = _alert_payload()
    newer["commonAnnotations"]["summary"] = "Incident le plus recent"

    client.post("/api/v1/alerts", json=older, headers=_headers())
    client.post("/api/v1/alerts", json=newer, headers=_headers())

    page = client.get("/dashboard").get_data(as_text=True)
    assert page.index("Incident le plus recent") < page.index("Incident plus ancien")


@pytest.mark.parametrize(
    ("status", "alertname", "severity", "expected_tone"),
    [
        ("firing", "TrainingHubServiceDown", "critical", "tone-critical"),
        ("firing", "TrainingHubHighErrorRate", "warning", "tone-warning"),
        ("resolved", "TrainingHubServiceDown", "critical", "tone-resolved"),
    ],
)
def test_dashboard_applies_incident_color_priority(
    client,
    status,
    alertname,
    severity,
    expected_tone,
):
    payload = _alert_payload(status=status)
    payload["commonLabels"]["alertname"] = alertname
    payload["commonLabels"]["severity"] = severity

    client.post("/api/v1/alerts", json=payload, headers=_headers())

    page = client.get("/dashboard").get_data(as_text=True)
    assert expected_tone in page


def test_alert_webhook_requires_token(client):
    response = client.post("/api/v1/alerts", json=_alert_payload())

    assert response.status_code == 401


def test_alert_webhook_accepts_bearer_token_from_alertmanager(client):
    response = client.post(
        "/api/v1/alerts",
        json=_alert_payload(),
        headers={"Authorization": "Bearer test-token"},
    )

    assert response.status_code == 201


def test_alert_is_enriched_analyzed_and_stored(client):
    response = client.post(
        "/api/v1/alerts",
        json=_alert_payload(),
        headers=_headers(),
    )

    assert response.status_code == 201
    incident = response.get_json()
    assert incident["service"] == "course-service"
    assert incident["metrics"]["available"] is True
    assert incident["analysis"]["confidence"] == 0.8

    history = client.get("/api/v1/incidents", headers=_headers()).get_json()
    assert history["count"] == 1
    assert history["items"][0]["id"] == incident["id"]


def test_sensitive_alert_values_are_redacted(client):
    payload = _alert_payload()
    payload["commonLabels"]["api_key"] = "super-secret"
    payload["commonAnnotations"]["description"] = "token=abc123 failure"

    incident = client.post(
        "/api/v1/alerts",
        json=payload,
        headers=_headers(),
    ).get_json()

    assert incident["labels"]["api_key"] == "[REDACTED]"
    assert "abc123" not in incident["description"]


def test_invalid_alert_payload_is_rejected(client):
    response = client.post(
        "/api/v1/alerts",
        json={"alerts": []},
        headers=_headers(),
    )

    assert response.status_code == 400


def test_unknown_service_never_reaches_prometheus_as_user_input(client):
    payload = _alert_payload()
    payload["commonLabels"]["service"] = 'course-service"} or vector(1)'

    incident = client.post(
        "/api/v1/alerts",
        json=payload,
        headers=_headers(),
    ).get_json()

    assert incident["service"] == "unknown"
    assert incident["metrics"]["service"] == "unknown"


def test_model_failure_uses_read_only_rules_fallback():
    analyzer = ResilientAnalyzer(BrokenAnalyzer(), RuleBasedAnalyzer())

    result = analyzer.analyze(
        {"alertname": "TrainingHubServiceDown", "severity": "critical"}
    )

    assert result["analysis_mode"] == "rules_fallback"
    assert result["severity"] == "critical"


def test_ollama_valid_json_is_bounded_and_records_model_metrics():
    model_response = Mock()
    model_response.raise_for_status.return_value = None
    model_response.json.return_value = {
        "model": "gemma3:1b",
        "message": {
            "content": dumps(
                {
                    "summary": "Le service ne repond plus.",
                    "probable_cause": "Le conteneur est probablement arrete.",
                    "severity": "info",
                    "confidence": 0.74,
                    "recommendations": ["Verifier l'etat du conteneur."],
                }
            )
        },
        "total_duration": 1_500_000_000,
        "prompt_eval_count": 120,
        "eval_count": 45,
    }
    analyzer = OllamaAnalyzer(
        "http://ollama:11434",
        "gemma3:1b",
        timeout_seconds=10,
    )

    with patch("analyzer.requests.post", return_value=model_response) as post:
        result = analyzer.analyze(
            {
                "alertname": "TrainingHubServiceDown",
                "service": "user-service",
                "severity": "critical",
            }
        )

    assert result["analysis_mode"] == "ollama"
    assert result["confidence"] == 0.74
    assert result["model_severity"] == "info"
    assert result["severity"] == "critical"
    assert result["severity_adjusted"] is True
    assert result["model_metrics"]["output_tokens"] == 45
    assert post.call_args.kwargs["json"]["stream"] is False
    schema = post.call_args.kwargs["json"]["format"]
    assert schema["properties"]["severity"]["enum"] == [
        "critical",
        "info",
        "warning",
    ]
    assert schema["additionalProperties"] is False
