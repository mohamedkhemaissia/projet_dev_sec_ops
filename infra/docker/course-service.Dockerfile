FROM python:3.11-slim
WORKDIR /app
COPY services/course-service/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt
COPY services/course-service /app
ENV FLASK_APP=app.py
CMD ["python", "app.py"]
