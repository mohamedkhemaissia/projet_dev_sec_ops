FROM python:3.11-slim

WORKDIR /app

COPY services/user-service/requirements.txt .

RUN pip install --no-cache-dir --upgrade pip setuptools wheel \
    && pip install --no-cache-dir -r requirements.txt \
    && pip uninstall --yes setuptools wheel

COPY services/user-service .

ENV FLASK_APP=app.py
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

RUN groupadd --system app \
    && useradd --system --gid app --no-create-home app

USER app

CMD ["python", "app.py"]
