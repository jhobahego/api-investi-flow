# Feature: rag-documents-backend — Document RAG with pgvector on Neon

File locator: `odd/tasks/rag-documents-backend.md`

## Objective
Implement Retrieval-Augmented Generation (RAG) using pgvector on the existing Neon PostgreSQL database to chunk, embed, and semantically retrieve document contents for Gemini Chat and AI Suggestions, replacing naïve prompt stuffing and fixing arbitrary disk path access.

## Problem
1. **No persisted document text**: Documents exist only as raw DOCX/PDF files on the local filesystem (`uploads/documents/...`). On ephemeral hosting (Render), redeployments risk data loss.
2. **Brittle & slow on-demand extraction**: On every chat request, `document_extraction_service` parses DOCX/PDF synchronously from disk.
3. **Severe context truncation**: Chat attempts to build context with up to 50k chars from project docs, 25k from phases, and 15k from tasks, but `truncate_context(project_context, 12000)` in `app/core/gemini_guard.py` abruptly truncates everything to the first 12,000 characters. Any document content past the first ~3-4 pages is silently ignored by the AI.
4. **Security vulnerability**: `app/api/api_v1/endpoints/ai_assistant.py:927-997` reads `file_path` directly from the client-sent `project_context.attachment_document` dictionary with no ownership validation, allowing authenticated users to read arbitrary files from disk if their paths are known.
5. **Test harness incompatibility**: Test suite runs on SQLite (`test.db`), which does not support the PostgreSQL `vector` extension natively.

## Why
User requested RAG viability assessment and implementation roadmap. The current prompt stuffing wastes tokens, misses document content past page 3, and presents a security flaw. Adding RAG gives pinpoint context, lowers token consumption, scales to large research documents, and eliminates client-supplied disk paths.

## Database Decision: Neon (pgvector) vs Supabase
**Chosen: Neon PostgreSQL with `pgvector`**.
- **Zero new infrastructure**: The backend already runs on Neon (`sa-east-1.aws.neon.tech`). Adding Supabase would introduce a split-brain architecture (two PostgreSQL databases), requiring dual-write synchronization, extra connection pools, and two distinct auth/network boundaries.
- **Transactional integrity**: `document_chunks` maintains strict Foreign Keys with `attachments(id) ON DELETE CASCADE` and `projects(id) ON DELETE CASCADE`. Deleting a project or attachment automatically purges vectors.
- **Latency & Speed**: Vector similarity search and metadata joins (e.g. scoping to `project_id` and verifying user ownership) happen in a single query with sub-100ms execution, avoiding multi-hop cross-database network latency.
- **Operational stability**: Supabase Free tier automatically pauses after 7 days of low traffic with a ~30-second cold start. Neon scales compute transparently with ~300-500ms cold resume.

## Technical Architecture
- **Embedding Model**: Google GenAI `text-embedding-004` (768 dimensions), utilizing the existing `google-genai` SDK and `GOOGLE_AI_API_KEY`.
- **Table**: `document_chunks`
  - `id`: UUID / Integer PK
  - `attachment_id`: FK `attachments.id` ON DELETE CASCADE
  - `project_id`: FK `projects.id` ON DELETE CASCADE
  - `chunk_index`: Integer
  - `content`: Text (clean chunk text, ~500-1000 characters with 100 character overlap)
  - `embedding`: Vector(768) (indexed with HNSW cosine distance `vector_cosine_ops`)
  - `token_count`: Integer
  - `created_at`: DateTime
- **Chunking Pipeline**:
  - Triggers: On document upload (`attachment_service.py`), on file replace, and on `PUT /documentos/{id}/content` (editor save).
  - Execution: Asynchronous via FastAPI `BackgroundTasks` to keep API response times immediate.
  - Parser: Heading-aware paragraph chunking from `DocumentExtractionService`.
- **Retrieval Pipeline**:
  - Query embedding generated via `genai.Client.models.embed_content`.
  - Single SQL query: `SELECT content, similarity FROM document_chunks WHERE project_id = :project_id ORDER BY embedding <=> :query_vector LIMIT 5`.
  - Injected directly into Gemini Chat / Suggestion system prompt as verified citations, bounded by token budget.

## Checklist
- [x] B1 Alembic migration & ORM model for `document_chunks` with `pgvector` support and SQLite test fallback (TypeDecorator or conditional dialect)
- [x] B2 RAG service (`app/services/rag_service.py`): text chunking (500-1000 chars, sliding window) and embedding generation via `google-genai`
- [x] B3 Background indexing pipeline hooked into document upload (`attachment_service.py`) and editor save (`documentos.py:PUT /content`) via a Celery worker over Redis (originally planned as FastAPI `BackgroundTasks`)
- [x] B4 Secure semantic retrieval endpoint/method scoping chunks strictly by `project_id` and verified user ownership, deprecating client-supplied `file_path`
- [x] B5 Update AI prompts & assistant endpoints (`ai_assistant.py`, `ai_service.py`) to inject top-K retrieved chunks with source metadata into Gemini context
- [x] B6 Unit & integration tests for chunking, embedding service, and RAG retrieval

## Authorized Scope
- `app/models/document_chunk.py` (new)
- `alembic/versions/*_add_document_chunks_pgvector.py` (new)
- `app/services/rag_service.py` (new)
- `app/services/attachment_service.py`
- `app/services/ai_service.py`
- `app/api/api_v1/endpoints/documentos.py`
- `app/api/api_v1/endpoints/ai_assistant.py`
- `app/core/ai_prompts.py`
- `app/core/gemini_guard.py`
- `requirements.txt` (`pgvector>=0.2.4`)
- `tests/test_rag_service.py` (new)
- `odd/tasks/rag-documents-backend.md` (this file)

## Acceptance Criteria
- `CREATE EXTENSION IF NOT EXISTS vector;` runs seamlessly via Alembic in Neon.
- Uploading or modifying a DOCX generates chunks and embeddings in `document_chunks` in the background without blocking the HTTP request.
- Chat endpoint retrieves the top-K relevant chunks for the query within the user's project; Gemini answers citing the document accurately.
- `truncate_context(12000)` no longer chops off relevant content because retrieved chunks total under 4,000 tokens of high-signal text.
- Arbitrary `file_path` reading from disk in `ai_assistant.py` is removed; all document context comes from authenticated DB chunks.
- Existing test suite passes with `make test` without failing on SQLite.

## Applicable Checks
- `source .venv/bin/activate && make quality` (flake8, black, isort, mypy, pytest)
- Unit tests: `pytest tests/test_rag_service.py -v`
- Integration test with mock embeddings

## Route
- Delegated direct. Triggers: touches multiple non-trivial files (models, migrations, services, endpoints, tests), involves vector extension and prompt pipeline changes.

## Delivery Strategy
- Strategy: `single-pr` or `feature-branch-chain` (`feat/rag-documents-backend` from `develop`). Estimated ~350-450 lines of code.

## Implementation Notes

- Alembic revision: `f3a9c1d7b2e4` (`down_revision = "e91e6743c3c1"`), file `alembic/versions/rag_document_chunks_pgvector.py`. On PostgreSQL it runs `CREATE EXTENSION IF NOT EXISTS vector`, creates `embedding Vector(768)` and the HNSW cosine index; on SQLite it uses `TEXT` plus a plain index. `downgrade()` drops indexes/table but keeps the extension.
- Model: `app/models/document_chunk.py` (`EMBEDDING_DIMENSION = 768`, `EmbeddingType(TypeDecorator)`, `DocumentChunk`), registered in `app/models/__init__.py` and imported in `alembic/env.py`.
- Service: `app/services/rag_service.py` implements chunking, batched embeddings, indexing/re-indexing, project resolution, pgvector retrieval, Python cosine/lexical fallback, `retrieve_for_attachment` ownership checks and prompt formatting.
- Embeddings: `AI_MODEL_EMBEDDING` (default `gemini-embedding-001`) is read from settings inside `_embed_batch`; `DEFAULT_EMBEDDING_MODEL` remains the fallback. `output_dimensionality=768` is kept so the pgvector column stays valid. `text-embedding-004` is retired and returns `404 NOT_FOUND` on `v1beta`; switching models is an env-var-only change.
- Indexing execution: requests only enqueue. `rag_service.enqueue_attachment_indexing()` calls `index_attachment_task.delay()` and never raises; the Celery task runs `rag_service.index_attachment_in_session()`, which opens its own `SessionLocal`, rolls back and re-raises on failure so Celery retries (max 3, backoff + jitter). `index_attachment_background()` is kept as a harmless compatibility wrapper.

### Extended files (beyond the original Authorized Scope list)

- `app/api/api_v1/endpoints/projects.py`, `phases.py`, `tasks.py`: upload/replace endpoints no longer take `BackgroundTasks`; `attachment_service` enqueues the Celery task after commit.
- `tests/conftest.py`: sets `RAG_INDEXING_ENABLED=false` before app imports so endpoint tests never enqueue embeddings/DB writes. Also repaired two dormant global fixtures that could not run against the current models: `User` has no `is_superuser` field and `Phase` has no `description` field.
- `docker-compose.yml`: local Postgres image changed to `pgvector/pgvector:pg16`; added Celery broker/backend env to `api` and a `worker` service running `celery -A app.core.celery_app.celery_app worker --loglevel=info --concurrency=2 -Q rag`.
- `app/models/__init__.py`, `alembic/env.py`: register the new model.
- `requirements.txt`: add `pgvector>=0.2.4` (alphabetical, after `pathspec`).
- `app/core/gemini_guard.py`: add `RAG_CONTEXT_MAX_CHARS = 8000` and document it.
- `app/core/ai_prompts.py`: add the `FRAGMENTOS RECUPERADOS DEL DOCUMENTO (RAG)` section/instructions while keeping existing placeholders.
- `app/services/ai_service.py`: `chat()` and `suggest_text()` accept `rag_context`, truncate it and pass it into the prompt.
- `app/api/api_v1/endpoints/ai_assistant.py`: removed all client `attachment_document`/`file_path` reads and filesystem extraction; phases/tasks summaries now come from request context or DB metadata only; RAG retrieval is injected into chat and suggestions.
- `app/api/api_v1/documentos.py`: enqueues re-indexing after `PUT /content` and adds authenticated `GET /documentos/{attachment_id}/search`.
- `app/core/celery_app.py` (new): Celery app `investi_flow` with `include=["app.tasks.rag_tasks"]`, JSON serializers, UTF/UTC, `task_acks_late`, prefetch 1 and default queue `rag`.
- `app/tasks/rag_tasks.py` (new): `rag.index_attachment` task (bound, autoretry on `Exception`, exponential backoff + jitter, max 3). `app/tasks/__init__.py` is empty.
- `app/core/config.py` / `.env.example`: `AI_MODEL_EMBEDDING`, `CELERY_BROKER_URL`, `CELERY_RESULT_BACKEND`.

### Celery + Redis indexing

- Broker/backend: `CELERY_BROKER_URL` / `CELERY_RESULT_BACKEND`, falling back to `REDIS_URL` and then `redis://localhost:6379/0`.
- HTTP requests extract the document text in the API and enqueue `rag.index_attachment_text` with `(attachment_id, text)`; the worker does not read `uploads/`. Enqueue failures are logged and never fail the request.
- `rag.index_attachment` (file-based) remains as a fallback when extraction fails/returns empty, or when the text exceeds `MAX_TASK_TEXT_CHARS` (1,000,000 characters); that fallback requires a shared disk.
- The worker consumes queue `rag`; task names are `rag.index_attachment_text` (default) and `rag.index_attachment` (fallback).
- `RAG_INDEXING_ENABLED=false` disables enqueueing (used by endpoint tests through `tests/conftest.py`).

### Data state

- No backfill for existing documents: only new uploads, replacements and editor saves enqueue indexing.
- Production/staging Neon data was wiped with snapshot `snap-autumn-smoke-ac575sux` (`pre-rag-wipe-2026-11-08`, 32,210,944 bytes). All application rows were truncated; `alembic_version` was preserved.
- Production Neon (`aged-truth-08942612`, branch `br-crimson-art-aczv0a11`, `neondb`) applied the equivalent migration DDL and was stamped to `f3a9c1d7b2e4`: `vector` extension 0.8.0, `embedding vector(768)`, 6 indexes including the HNSW cosine index, 0 rows in `document_chunks`.
- Local Postgres (`pgvector/pgvector:pg16`) was migrated with Alembic `upgrade head` to `f3a9c1d7b2e4` and wiped (all application table counts = 0).

### Deployment note (Render)

- Add a Background Worker service using the same image/repo, the same environment (`DATABASE_URL`, `GOOGLE_AI_API_KEY`, `AI_MODEL_EMBEDDING`, `CELERY_BROKER_URL`, `CELERY_RESULT_BACKEND`) and start command `celery -A app.core.celery_app.celery_app worker --loglevel=info --concurrency=2 -Q rag`.
- Staging/production must run `alembic upgrade head` and have Redis reachable; the RAG worker connection is independent from the rate-limit Redis.
- The default pipeline sends the extracted text in the task payload (`rag.index_attachment_text`), so the API and worker do **not** need a shared disk. The file-based `rag.index_attachment` fallback (text over 1 MB or extraction failure) still needs `UPLOAD_FOLDER` shared between services. Object storage is recommended for durability and re-indexing.

### Worker deployment alternatives

- **Staging: local worker.** Keep the API deployed on Render with the same Upstash `CELERY_BROKER_URL` / `CELERY_RESULT_BACKEND`, and run the worker on the developer machine with a `.env.staging-worker` that points `DATABASE_URL` to the staging Neon branch, `CELERY_*` to Upstash, `GOOGLE_AI_API_KEY` to the project key, `AI_MODEL_EMBEDDING=gemini-embedding-001` and `RAG_INDEXING_ENABLED=true`. Tasks remain queued in Upstash while the local worker is offline. No shared disk is needed because the default path sends the extracted text in the payload.
- **Production free: Oracle Cloud Always Free or Fly.io.** Run the same worker command on a small VM:
  `celery -A app.core.celery_app.celery_app worker --loglevel=info --concurrency=2 -Q rag`
  with the production `DATABASE_URL`, Upstash `CELERY_*`, `GOOGLE_AI_API_KEY` and `AI_MODEL_EMBEDDING`. Only outbound HTTPS is required (Neon, Upstash, Google); no inbound ports beyond SSH.
- **Render:** Background Workers are paid. The free fallback is to run the worker in the same free Web Service as the API (shares the disk, but the service sleeps) or to use one of the VM options above.

### Post-verification corrections (independent verifier)

- `/documentos/{id}/search` was returning sibling attachment chunks: `retrieve_context()` now accepts an optional `attachment_id` and filters the PostgreSQL, Python and lexical paths; `retrieve_for_attachment()` passes it. A new test covers a project attachment plus a phase attachment in the same project.
- Extraction failures no longer wipe a good index: `extract_text()` raises `RAGServiceError` on read/parse failures, and `index_attachment()` only deletes after embeddings succeed. PDF error strings (`"Error al extraer PDF: ..."`) are rejected instead of being embedded. Legacy `.doc` is skipped with a warning.
- Chunks with NULL embeddings now fall back to lexical scoring instead of returning an empty result on SQLite.
- `GET /documentos/{id}/search` bounds `top_k` to 1..20.
- `RAG_INDEXING_ENABLED` moved to `Settings` (env override still works) and documented in `.env.example`.

### Design decisions / deviations

- `EmbeddingType` is declared as `TypeDecorator[Text]` (type parameter only) so mypy accepts `impl = Text`; behavior matches the specified `TypeDecorator`.
- A `TypeDecorator` column does not expose pgvector's `cosine_distance()` comparator at runtime (`hasattr(...) == False`). `_retrieve_postgres` therefore uses the equivalent `DocumentChunk.embedding.op("<=>")(literal(query_vector, type_=EmbeddingType()))`; it compiles to `document_chunks.embedding <=> :param` and the bind processor converts the 768-float list to the pgvector literal.
- Re-indexing test asserts content replacement and stable count instead of asserting old ids disappear, because SQLite reuses deleted rowids when the table is emptied.
- `delete_attachment_chunks()` deletes and flushes but does not commit; `index_attachment()` performs the single commit for delete + insert.
- Celery task uses `bind=True` (Celery's actual keyword for a bound task). `bound=True` is not recognized by Celery and would make `self` receive the attachment id.
- `include=["app.tasks.rag_tasks"]` is intentionally not eagerly imported in `celery_app.py`. A plain `celery_app.tasks` read lists only Celery built-ins; when the worker loader runs (`celery_app.loader.import_default_modules()`) `rag.index_attachment` is registered.

### Verification evidence

- `.venv/bin/black app/ tests/test_rag_service.py` → 1 file reformatted on the first pass; idempotent afterwards (79 files checked).
- `.venv/bin/isort app/ tests/test_rag_service.py` → no changes.
- `.venv/bin/flake8 app/` → clean (no output).
- `.venv/bin/pytest tests/test_rag_service.py -q` → 27 passed (adds text-payload enqueue, extraction-failure fallback, and `index_attachment_text` persistence).
- `.venv/bin/pytest tests/test_api/test_ai_assistant.py tests/test_api/test_attachments.py tests/test_services/test_ai_service.py -q` → 89 passed.
- `.venv/bin/python -c "from app.core.celery_app import celery_app; print(sorted(celery_app.tasks.keys()))"` → Celery built-ins only (`celery.accumulate`, ..., `celery.starmap`). With `celery_app.loader.import_default_modules()` (what the worker does at startup) the list also contains `rag.index_attachment` and `rag.index_attachment_text`.
- `.venv/bin/mypy app/` → fails **pre-existing/environmental** while parsing `.venv/lib/python3.12/site-packages/deprecated/sphinx.py:35` (`Type statement is only supported in Python 3.12 and greater`) because `mypy.ini` targets Python 3.11. The new Celery import is annotated `# type: ignore[import-untyped]`, and with `--python-version 3.12` only the same 7 pre-existing `gemini_guard.py` errors remain.
- Full suite `.venv/bin/pytest -q` → **551 passed** (run before the text-payload change; the 27 RAG + 89 targeted suites passed after it).
- Live local E2E: Redis (docker) + Celery worker (`queue=rag`) + local Postgres with pgvector + real Google API. A DOCX was seeded, `enqueue_attachment_indexing()` returned `True`, the worker logged `Task rag.index_attachment ... succeeded`, 1 chunk was stored with `vector_dims = 768`, and `retrieve_context()` / `retrieve_for_attachment()` returned the chunk (similarity `0.723` after the correction; `0.7513` in the first run). `retrieve_for_attachment()` with a non-owner user returned HTTP 403.
- Live Google model check: `text-embedding-004` returns `404 NOT_FOUND` on `v1beta`; `gemini-embedding-001` with `output_dimensionality=768` returns 768 dims. The default was changed to `gemini-embedding-001` and remains overridable via `AI_MODEL_EMBEDDING`.
- Regression found and fixed during E2E: the `<=>` scalar inherited the `Vector` column type, so pgvector tried to parse a float as a vector. `_distance_expression()` now uses `return_type=Float()`; the test asserts the compiled PG expression type.

### Future improvements

- **Move API-side extraction/retrieval to `run_in_threadpool`.** `extract_text` (DOCX/PDF) and `retrieve_context` are synchronous and currently run inside `async` endpoints. For large documents or slow embedding calls, wrap them with `fastapi.concurrency.run_in_threadpool` (or `anyio.to_thread.run_sync`):
  ```python
  from fastapi.concurrency import run_in_threadpool

  text = await run_in_threadpool(rag_service.extract_text, attachment)
  results = await run_in_threadpool(
      rag_service.retrieve_context, db, project_id, query
  )
  ```
  Do not share the request's SQLAlchemy `Session` across threads. For DB work inside the thread, open a fresh `SessionLocal()` and close it in `finally`, or split the work: run only the embedding/HTTP call in the thread and keep DB access in the request thread. The Celery worker path does not need this change.

### Live staging-like smoke test (2026-11-09)

- API local + worker Celery local conectado al **Upstash real** (misma base que la API) + Postgres local con pgvector.
- Documento `Planteamiento del problema.docx` (7.684 bytes, 3.818 caracteres): 5 chunks, similitudes `0.655`, `0.629`, `0.602`, `0.600`, `0.589`.
- Chat `gemini-2.5-flash-lite` respondió citando el documento; sugerencias devolvieron una continuación académica.
- Hallazgos operativos corregidos:
  - Celery exige `ssl_cert_reqs` para `rediss://`; `app/core/celery_app.py` ahora configura `broker_use_ssl`/`redis_backend_use_ssl` cuando el esquema es TLS.
  - API y worker deben usar el **mismo** broker; en la prueba la API apuntaba a Upstash y el worker a Redis local, por eso no se procesaban los tasks.
  - El token local expira en 1 minuto (`ACCESS_TOKEN_EXPIRE_MINUTES=1`); el smoke test re-loguea una vez ante 401.
  - El hard delete de proyectos exige archivarlos primero; el smoke test hace archive + permanent.
