FROM python:3.11-slim

WORKDIR /app

COPY services/course-service/requirements.txt .

RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

COPY services/course-service .

ENV FLASK_APP=app.py
ENV PYTHONUNBUFFERED=1

CMD ["python", "app.py"]