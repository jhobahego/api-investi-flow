# Worker multi-environment + queue separation

## Objective

Run staging and production Celery RAG workers on the same Azure VM without
cross-consuming tasks, and make the queue name environment-specific.

## Problem

Today both environments share the Upstash broker and the default queue `rag`.
A single worker consumes everything. If a task from one environment is
consumed while the worker points to the other environment's database, the task
either silently indexes 0 chunks or, when attachment IDs collide, indexes the
wrong document.

## Decisions

- Keep one Azure VM and run one container per environment. Azure bills the VM,
  not the containers.
- Use the same Upstash Redis database but separate queue names:
  - staging: `rag_staging`
  - production: `rag_production`
- Each container has its own env file and compose project name:
  - staging: `/opt/investi-flow`, `.env.staging-worker`,
    project `investi-flow`
  - production: `/opt/investi-flow-production`, `.env.production-worker`,
    project `investi-flow-production`
- The API publishes to the queue from `CELERY_QUEUE_NAME`. Default stays `rag`
  for backward compatibility.
- The worker commands use `$${CELERY_QUEUE_NAME:-rag}` so the queue comes from
  the container env.

## Non-goals

- No merge of `develop` into `main`.
- No production database migration in this task.
- No Render environment changes from the repository.

## Tasks

- [x] T1 Add `CELERY_QUEUE_NAME` to `Settings` and use it as
      `task_default_queue` in `app/core/celery_app.py`.
- [x] T2 Update both compose files to run the worker with the queue from the
      environment and `--concurrency=1`.
- [x] T3 Parameterize `deploy/worker/bootstrap.sh` with `WORKER_ENV_FILE` and
      `COMPOSE_PROJECT_NAME` so two checkouts can coexist on one host.
- [x] T4 Update `.env.example` and `.env.staging-worker.example`; add
      `.env.production-worker.example`.
- [x] T5 Document the two-environment rollout in `deploy/worker/README.md`.
- [x] T6 Add a focused test for the queue default wiring.
- [x] T7 Verify `CELERY_QUEUE_NAME` overrides the default queue at import time.
- [x] T8 Apply staging VM changes: `CELERY_QUEUE_NAME=rag_staging`, recreate the
      worker with the new project name, and verify Celery listens on the
      expected queue(s). The worker currently listens to `rag_staging,rag` as a
      transition until the Render staging API sets `CELERY_QUEUE_NAME`.
- [x] T9 Prepare the production checkout and env file on the VM. Do not start
      the production container until `main` has the Celery/RAG code and the
      production database is migrated.

## Progress

- Code, compose, bootstrap, env templates, README and the focused test are
  implemented. Image tags are distinct per environment:
  `investi-flow-worker:staging` and `investi-flow-worker:production`.
- Staging VM: `investi-flow-worker-1` runs image `investi-flow-worker:staging`,
  concurrency 1, queues `rag_staging` and `rag`. A controlled upload indexed
  attachment 11 with 5 chunks in 6.4 s; the test project was archived and
  hard-deleted.
- Production VM prep: checkout `/opt/investi-flow-production` at `main`
  (`1dd700c`), env `/opt/investi-flow-production/.env.production-worker` with
  `CELERY_QUEUE_NAME=rag_production`, and compose
  `/opt/investi-flow-worker-production/docker-compose.yml`. Not started because
  `main` lacks `app/core/celery_app.py`, `app/tasks/rag_tasks.py` and
  `app/services/rag_service.py`.
- Local code changes are uncommitted. The Render staging API must deploy them
  and set `CELERY_QUEUE_NAME=rag_staging`; then remove `rag` from the staging
  worker override.
- `make quality` stops at a pre-existing mypy error in
  `.venv/lib/python3.12/site-packages/deprecated/sphinx.py`; focused black,
  isort, flake8, mypy and the new test pass.

## Verification

- `CELERY_QUEUE_NAME=rag_staging .venv/bin/python -c "from app.core.celery_app import celery_app; print(celery_app.conf.task_default_queue)"`
- `CELERY_QUEUE_NAME=rag_production .venv/bin/python -c "from app.core.celery_app import celery_app; print(celery_app.conf.task_default_queue)"`
- `make quality`
- Staging worker logs show the configured queue.
- An upload enqueues to `rag_staging` once the Render API sets
  `CELERY_QUEUE_NAME=rag_staging`.

## Risks and notes

- Until the Render staging API sets `CELERY_QUEUE_NAME=rag_staging`, it keeps
  publishing to `rag`. During the transition the staging worker may listen to
  both `rag` and `rag_staging`; remove `rag` after the API is redeployed.
- `main` currently lacks `app/core/celery_app.py`, `app/tasks/rag_tasks.py` and
  `app/services/rag_service.py`, so a production worker built from `main`
  cannot start yet. It must wait for the develop -> main merge.
- Production Neon is still at Alembic `f3a9c1d7b2e4`; run
  `alembic upgrade head` there before starting a worker that expects
  `attachments.indexing_status`.
