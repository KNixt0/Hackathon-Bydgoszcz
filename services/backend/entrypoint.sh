#!/bin/sh
set -e
case "$1" in
  api)    exec uvicorn app.main:app --host 0.0.0.0 --port "${BACKEND_PORT:-8000}" ;;
  worker) exec celery -A app.celery_app:celery worker --loglevel=INFO --concurrency="${WORKER_CONCURRENCY:-2}" ;;
  beat)   exec celery -A app.celery_app:celery beat --loglevel=INFO --schedule=/tmp/celerybeat-schedule ;;
  *)      exec "$@" ;;
esac
