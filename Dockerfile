FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/src \
    REAQUA_DB=/data/reaqua.gpkg \
    REAQUA_INBOX=/data/inbox \
    REAQUA_OUTPUT=/data/output

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src ./src
COPY data ./data

RUN useradd --create-home reaqua && mkdir -p /data/inbox /data/output && chown -R reaqua /data
USER reaqua

EXPOSE 8000

CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "2", "--timeout", "120", "reaqua.web.app:create_app()"]
