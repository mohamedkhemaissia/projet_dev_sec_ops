FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN groupadd --system app && useradd --system --gid app --no-create-home app

COPY services/ai-ops-service/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
    && pip uninstall --yes setuptools wheel \
    && pip uninstall --yes pip \
    && rm -rf /usr/local/lib/python*/ensurepip

COPY services/ai-ops-service/ .

USER app
EXPOSE 5005

CMD ["gunicorn", "--bind", "0.0.0.0:5005", "--workers", "1", "--threads", "4", "--worker-tmp-dir", "/tmp", "--no-control-socket", "app:create_app()"]
