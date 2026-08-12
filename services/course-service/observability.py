"""Runtime metrics and structured request logs for TrainingHub services."""

import json
import re
import time
from uuid import uuid4

from flask import Response, g, request
from prometheus_client import (
    CONTENT_TYPE_LATEST,
    CollectorRegistry,
    Counter,
    GCCollector,
    Gauge,
    Histogram,
    PlatformCollector,
    ProcessCollector,
    generate_latest,
)

REQUEST_ID_PATTERN = re.compile(r"^[A-Za-z0-9._-]{1,64}$")


def init_observability(app, service_name):
    """Expose Prometheus metrics and emit one safe JSON log per request."""
    registry = CollectorRegistry()
    GCCollector(registry=registry)
    PlatformCollector(registry=registry)
    ProcessCollector(registry=registry)

    requests_total = Counter(
        "traininghub_http_requests_total",
        "Total HTTP requests handled by a TrainingHub service.",
        ("service", "method", "endpoint", "status"),
        registry=registry,
    )
    request_duration = Histogram(
        "traininghub_http_request_duration_seconds",
        "HTTP request duration in seconds.",
        ("service", "method", "endpoint"),
        buckets=(0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5),
        registry=registry,
    )
    requests_in_progress = Gauge(
        "traininghub_http_requests_in_progress",
        "HTTP requests currently being processed.",
        ("service",),
        registry=registry,
    )

    @app.before_request
    def start_request_observation():
        request_id = request.headers.get("X-Request-ID", "")
        g.request_id = (
            request_id if REQUEST_ID_PATTERN.fullmatch(request_id) else uuid4().hex
        )
        g.request_started_at = time.perf_counter()
        g.request_is_observed = request.path != "/metrics"
        if g.request_is_observed:
            requests_in_progress.labels(service_name).inc()

    @app.after_request
    def finish_request_observation(response):
        response.headers["X-Request-ID"] = g.get("request_id", uuid4().hex)
        if not g.get("request_is_observed", False):
            return response

        duration = time.perf_counter() - g.get(
            "request_started_at",
            time.perf_counter(),
        )
        endpoint = request.url_rule.rule if request.url_rule else "unmatched"
        requests_in_progress.labels(service_name).dec()
        requests_total.labels(
            service_name,
            request.method,
            endpoint,
            str(response.status_code),
        ).inc()
        request_duration.labels(
            service_name,
            request.method,
            endpoint,
        ).observe(duration)

        app.logger.info(
            "%s",
            json.dumps(
                {
                    "event": "http_request",
                    "service": service_name,
                    "request_id": g.request_id,
                    "method": request.method,
                    "endpoint": endpoint,
                    "status": response.status_code,
                    "duration_ms": round(duration * 1000, 2),
                },
                separators=(",", ":"),
            ),
        )
        return response

    @app.get("/metrics")
    def metrics():
        return Response(generate_latest(registry), content_type=CONTENT_TYPE_LATEST)
