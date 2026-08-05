"""Fetch a small, allow-listed operational context from Prometheus."""

import re

import requests

SERVICE_PATTERN = re.compile(r"^[a-z0-9-]{1,64}$")


class PrometheusContextClient:
    def __init__(self, base_url, timeout_seconds, allowed_services):
        self.base_url = base_url
        self.timeout_seconds = timeout_seconds
        self.allowed_services = set(allowed_services)

    def collect(self, service):
        if service not in self.allowed_services or not SERVICE_PATTERN.fullmatch(service):
            return {"available": False, "reason": "service_not_allowed"}

        selector = f'job="traininghub-services",service="{service}"'
        queries = {
            "availability": f"max(up{{{selector}}})",
            "http_5xx_rate": (
                "sum(rate(traininghub_http_requests_total{"
                f'{selector},status=~"5.."}}[5m]))'
            ),
            "p95_latency_seconds": (
                "histogram_quantile(0.95, sum by (le) "
                "(rate(traininghub_http_request_duration_seconds_bucket{"
                f"{selector}}}[5m])))"
            ),
        }

        values = {}
        try:
            for name, query in queries.items():
                values[name] = self._query_scalar(query)
        except (requests.RequestException, ValueError, KeyError, TypeError):
            return {"available": False, "reason": "prometheus_unavailable"}

        return {"available": True, "values": values}

    def _query_scalar(self, query):
        response = requests.get(
            f"{self.base_url}/api/v1/query",
            params={"query": query},
            timeout=self.timeout_seconds,
        )
        response.raise_for_status()
        payload = response.json()
        if payload.get("status") != "success":
            raise ValueError("Prometheus query was not successful")

        result = payload.get("data", {}).get("result", [])
        if not result:
            return None
        return float(result[0]["value"][1])
