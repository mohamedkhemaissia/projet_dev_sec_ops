"""Prometheus metrics for the AIOps service."""

import time

from flask import Response, g, request
from prometheus_client import (
    CONTENT_TYPE_LATEST,
    CollectorRegistry,
    Counter,
    Histogram,
    generate_latest,
)


def init_observability(app):
    registry = CollectorRegistry()
    requests_total = Counter(
        "traininghub_aiops_requests_total",
        "Total requests handled by the TrainingHub AIOps service.",
        ("method", "endpoint", "status"),
        registry=registry,
    )
    request_duration = Histogram(
        "traininghub_aiops_request_duration_seconds",
        "AIOps HTTP request duration in seconds.",
        ("method", "endpoint"),
        registry=registry,
    )

    @app.before_request
    def start_observation():
        g.aiops_started_at = time.perf_counter()

    @app.after_request
    def finish_observation(response):
        if request.path != "/metrics":
            endpoint = request.url_rule.rule if request.url_rule else "unmatched"
            requests_total.labels(
                request.method,
                endpoint,
                str(response.status_code),
            ).inc()
            request_duration.labels(request.method, endpoint).observe(
                time.perf_counter() - g.get("aiops_started_at", time.perf_counter())
            )
        return response

    @app.get("/metrics")
    def metrics():
        return Response(generate_latest(registry), content_type=CONTENT_TYPE_LATEST)
