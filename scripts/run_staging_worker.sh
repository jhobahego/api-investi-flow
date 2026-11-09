#!/usr/bin/env bash
# Run the Celery RAG worker against staging using .env.staging-worker.
#
# Using `dotenv run` avoids the shell `source` pitfall: a Neon DATABASE_URL
# contains `&` in the query string (sslmode=require&channel_binding=require),
# and an unquoted `&` breaks `source`, leaving DATABASE_URL unset and making
# the worker fall back to the local .env database (0 chunks indexed).
set -euo pipefail

cd "$(dirname "$0")/.."

if [ ! -f .env.staging-worker ]; then
  echo "Falta .env.staging-worker. Copiá .env.staging-worker.example y completalo." >&2
  exit 1
fi

exec .venv/bin/dotenv -f .env.staging-worker run -- \
  .venv/bin/celery -A app.core.celery_app.celery_app worker \
  --loglevel=info --concurrency=1 -Q rag
