# Cloud-agnostic worker deployment

The Celery worker is a Docker container plus environment variables. Nothing in
this directory references a cloud provider, so moving hosts is a transport
change, not a code change.

## Artifacts

| File | Purpose |
| --- | --- |
| `docker-compose.yml` | Staging worker service: builds the repo `Dockerfile`, runs Celery. |
| `docker-compose.production.yml` | Production worker service: same image, production env file. |
| `bootstrap.sh` | Installs Docker, clones the branch, writes the env file, builds and starts. |
| `../../.env.staging-worker.example` | Staging environment template (copy to `.env.staging-worker`). |
| `../../.env.production-worker.example` | Production environment template (copy to `.env.production-worker`). |

## Run on any Linux host

The only provider-specific step is how `bootstrap.sh` reaches the host.

Azure (no public IP required):

```bash
az vm run-command invoke -g <resource-group> -n <vm> \
  --command-id RunShellScript --scripts @deploy/worker/bootstrap.sh
```

GCP:

```bash
gcloud compute ssh <vm> --command 'sudo bash -s' < deploy/worker/bootstrap.sh
```

Generic SSH:

```bash
ssh user@host 'sudo bash -s' < deploy/worker/bootstrap.sh
```

## Secrets

The env file is passed as base64 through `ENV_B64`; `bootstrap.sh` writes it to
`$WORKER_ENV_FILE` (default `$APP_DIR/.env.staging-worker`) with mode `600`. It
is never committed and never baked into the image because `.dockerignore`
excludes `.env*`.

## Two environments on one host

The same host can run staging and production workers as separate Compose
projects. Each project has its own checkout, env file, container name and
queue.

| Environment | Checkout | Env file | Compose project | Queue |
| --- | --- | --- | --- | --- |
| Staging | `/opt/investi-flow` | `.env.staging-worker` | `investi-flow` | `rag_staging` |
| Production | `/opt/investi-flow-production` | `.env.production-worker` | `investi-flow-production` | `rag_production` |

- `main` currently lacks the Celery/RAG code, so do not start the production
  container until `develop` is merged to `main`.
- The production Neon database must run `alembic upgrade head` before starting
  a worker that expects the `attachments.indexing_status` column.
- Never reuse the same queue across environments: both workers would consume
  each other's jobs.

## Why this stays portable

- No cloud SDK in `requirements.txt` or in the worker code.
- Connection strings come only from environment variables: `DATABASE_URL`,
  `CELERY_BROKER_URL`, `CELERY_RESULT_BACKEND`, `GOOGLE_AI_API_KEY`.
- The worker only needs outbound HTTPS to the database, the broker and the AI
  provider, so it needs no inbound port and no cloud-specific networking.
- Migrating to another provider means provisioning a Linux host with Docker and
  running the same `bootstrap.sh` over that provider's transport.
