#!/usr/bin/env bash
# Provider-neutral bootstrap for the InvestiFlow Celery worker.
#
# Design goal: the worker is a Docker container plus environment variables.
# Nothing in this script references a cloud provider. The only provider-specific
# part is the transport you use to run this script on the host:
#   - Azure:  az vm run-command invoke ... --scripts @deploy/worker/bootstrap.sh
#   - GCP:    gcloud compute ssh VM --command 'sudo bash -s' < deploy/worker/bootstrap.sh
#   - Any:    ssh user@host 'sudo bash -s' < deploy/worker/bootstrap.sh
#
# Environment inputs:
#   REPO_URL  (default: https://github.com/jhobahego/api-investi-flow.git)
#   BRANCH    (default: feat/rag-documents-backend)
#   APP_DIR   (default: /opt/investi-flow)
#   ENV_B64   (base64 of the worker env file; written to $APP_DIR/.env.staging-worker)
set -euo pipefail

REPO_URL="${REPO_URL:-https://github.com/jhobahego/api-investi-flow.git}"
BRANCH="${BRANCH:-feat/rag-documents-backend}"
APP_DIR="${APP_DIR:-/opt/investi-flow}"
COMPOSE="$APP_DIR/deploy/worker/docker-compose.yml"
ENV_FILE="$APP_DIR/.env.staging-worker"

log() { echo "[bootstrap] $*"; }

# 1) Docker Engine + Compose plugin.
if ! command -v docker >/dev/null 2>&1; then
  log "installing Docker"
  curl -fsSL https://get.docker.com | sh
fi
systemctl enable --now docker >/dev/null 2>&1 || true

# 2) Application code (public repository, no credentials required).
if [ -d "$APP_DIR/.git" ]; then
  log "updating $BRANCH"
  git -C "$APP_DIR" fetch --all --prune
  git -C "$APP_DIR" checkout "$BRANCH"
  git -C "$APP_DIR" reset --hard "origin/$BRANCH"
else
  log "cloning $BRANCH"
  mkdir -p "$(dirname "$APP_DIR")"
  git clone --branch "$BRANCH" "$REPO_URL" "$APP_DIR"
fi

# 3) Canonical compose file fallback for branches that do not ship it yet.
if [ ! -f "$COMPOSE" ]; then
  log "writing fallback compose file"
  mkdir -p "$(dirname "$COMPOSE")"
  cat > "$COMPOSE" <<'YAML'
services:
  worker:
    build:
      context: ../..
      dockerfile: Dockerfile
    image: investi-flow-worker:local
    env_file:
      - ../../.env.staging-worker
    command: celery -A app.core.celery_app.celery_app worker --loglevel=info --concurrency=2 -Q rag
    restart: unless-stopped
YAML
fi

# 4) Secrets: injected by the transport, never committed or baked into the image.
if [ -n "${ENV_B64:-}" ]; then
  printf '%s' "$ENV_B64" | base64 -d > "$ENV_FILE"
  chmod 600 "$ENV_FILE"
fi
[ -f "$ENV_FILE" ] || { log "missing $ENV_FILE (set ENV_B64)"; exit 1; }

# 5) Build and start.
cd "$APP_DIR"
log "building image"
docker compose -f "$COMPOSE" build
log "starting worker"
docker compose -f "$COMPOSE" up -d
docker compose -f "$COMPOSE" ps
log "READY"
