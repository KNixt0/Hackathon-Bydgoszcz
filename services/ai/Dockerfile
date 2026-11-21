FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    AI_PORT=8001 \
    AI_DATA_DIR=/data

WORKDIR /srv

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY data/registries ./data/registries

# Non-root user; /data is the only writable path (runtime register snapshots).
RUN useradd --system --uid 10001 --no-create-home app \
    && mkdir -p /data \
    && chown app /data
USER app
VOLUME ["/data"]

EXPOSE 8001
HEALTHCHECK --interval=10s --timeout=4s --start-period=5s --retries=5 \
    CMD ["python", "-c", "import os, urllib.request; urllib.request.urlopen(f\"http://127.0.0.1:{os.environ.get('AI_PORT', '8001')}/health\", timeout=3)"]

CMD ["sh", "-c", "exec uvicorn app.main:app --host 0.0.0.0 --port ${AI_PORT}"]
