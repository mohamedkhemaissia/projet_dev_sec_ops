FROM python:3.11-slim

WORKDIR /app

COPY services/user-service/requirements.txt .

RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

COPY services/user-service .

ENV FLASK_APP=app.py
ENV PYTHONUNBUFFERED=1

CMD ["python", "app.py"]