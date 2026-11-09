# Worker cloud-agnostic deployment

## Objective
Run the Celery RAG worker on a Linux host using only a Docker container and
environment variables, so the host provider can change without touching
application code.

## Problem
The worker was being prepared on an Azure VM. The deployment must not couple the
implementation to Azure (or any other provider).

## Scope
- `deploy/worker/docker-compose.yml`
- `deploy/worker/bootstrap.sh`
- `deploy/worker/README.md`
- `.dockerignore` (exclude `.env*` from the image build context)
- `odd/tasks/worker-cloud-agnostic-deploy.md`

## Constraints
- No cloud SDK in `requirements.txt` or in worker code.
- Secrets only through environment variables.
- The worker only needs outbound HTTPS; no inbound ports.
- The provider-specific part is only the transport used to run `bootstrap.sh`.

## Tasks
- [x] Add portable compose file (worker only).
- [x] Add portable bootstrap script (Docker + clone + env + build + up).
- [x] Document transport examples (Azure / GCP / SSH).
- [x] Exclude `.env*` from the Docker build context.
- [x] Deploy on the current host and verify the worker consumes the `rag` queue.

## Verification
- `docker compose -f deploy/worker/docker-compose.yml ps` shows `worker-worker-1` as `Up`.
- Celery log: `Connected to rediss://***@...upstash.io:6379`, `queues: rag`,
  `celery@... ready`.
- Registered tasks: `rag.index_attachment`, `rag.index_attachment_text`.

## Route
Direct inline for the small file set. The deployment runs over Azure
`run-command` as the transport, but no artifact references Azure.
