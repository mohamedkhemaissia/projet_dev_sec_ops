"""Sanitize untrusted alert content before it reaches a model or API response."""

import re

SENSITIVE_KEY_PATTERN = re.compile(
    r"(?:api[_-]?key|authorization|cookie|password|secret|token)",
    re.IGNORECASE,
)
BEARER_PATTERN = re.compile(r"\bBearer\s+[A-Za-z0-9._~+/=-]+", re.IGNORECASE)
ASSIGNMENT_PATTERN = re.compile(
    r"(?i)\b(password|secret|token|api[_-]?key)\s*[:=]\s*[^\s,;]+"
)


def sanitize_text(value, max_length):
    text = str(value)
    text = BEARER_PATTERN.sub("Bearer [REDACTED]", text)
    text = ASSIGNMENT_PATTERN.sub(lambda match: f"{match.group(1)}=[REDACTED]", text)
    return text[:max_length]


def sanitize_mapping(mapping, max_length):
    if not isinstance(mapping, dict):
        return {}

    sanitized = {}
    for raw_key, raw_value in mapping.items():
        key = sanitize_text(raw_key, 100)
        if SENSITIVE_KEY_PATTERN.search(key):
            sanitized[key] = "[REDACTED]"
        else:
            sanitized[key] = sanitize_text(raw_value, max_length)
    return sanitized
