#!/usr/bin/env bash
set -e
# load .env if present
if [ -f /app/backend/.env ]; then
  export $(cat /app/backend/.env | xargs)
fi
# run uvicorn for development; in prod replace with gunicorn or uvicorn workers
uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload