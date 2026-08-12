FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    APP_HOST=0.0.0.0 \
    APP_PORT=3000 \
    SESSION_FILE_DIR=/tmp/traininghub-frontend-sessions

WORKDIR /app

RUN addgroup --system --gid 10001 traininghub \
    && adduser --system --uid 10001 --ingroup traininghub traininghub

COPY services/frontend-service/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir --requirement requirements.txt \
    && pip uninstall --yes setuptools wheel \
    && pip uninstall --yes pip \
    && rm -rf /usr/local/lib/python*/ensurepip

COPY services/frontend-service/app.py services/frontend-service/config.py services/frontend-service/api_client.py services/frontend-service/observability.py ./
COPY services/frontend-service/routes ./routes
COPY services/frontend-service/templates ./templates
COPY services/frontend-service/static ./static

RUN mkdir -p /tmp/traininghub-frontend-sessions \
    && chown -R traininghub:traininghub /app /tmp/traininghub-frontend-sessions

USER 10001:10001

EXPOSE 3000

HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:3000/health', timeout=2)"

CMD ["gunicorn", "--bind", "0.0.0.0:3000", "--workers", "1", "--threads", "4", "--worker-tmp-dir", "/tmp", "--no-control-socket", "--access-logfile", "-", "--error-logfile", "-", "app:create_app()"]
