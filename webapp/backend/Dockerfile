FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONIOENCODING=utf-8 \
    PYTHONPATH=/app:/app/webapp/backend
WORKDIR /app

COPY webapp/backend/requirements.txt /app/webapp/backend/requirements.txt
RUN pip install --no-cache-dir -r /app/webapp/backend/requirements.txt

COPY . /app
RUN useradd --create-home --uid 10001 appuser \
    && mkdir -p /app/research_results /app/webapp_data \
    && chown -R appuser:appuser /app

USER appuser
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--app-dir", "/app/webapp/backend", "--host", "0.0.0.0", "--port", "8000"]
