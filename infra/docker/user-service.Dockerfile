FROM python:3.11-slim

WORKDIR /app

COPY services/user-service/requirements.txt .

RUN pip install --no-cache-dir --upgrade pip setuptools wheel \
    && pip install --no-cache-dir -r requirements.txt \
    && pip uninstall --yes setuptools wheel \
    && pip uninstall --yes pip \
    && rm -rf /usr/local/lib/python*/ensurepip

COPY services/user-service .

ENV FLASK_APP=app.py
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

RUN groupadd --system --gid 10001 app \
    && useradd --system --uid 10001 --gid 10001 --no-create-home app

USER 10001:10001

CMD ["python", "app.py"]
