# Feature: rag-documents-backend — Document RAG with pgvector on Neon

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
- [ ] B1 Alembic migration & ORM model for `document_chunks` with `pgvector` support and SQLite test fallback (TypeDecorator or conditional dialect)
- [ ] B2 RAG service (`app/services/rag_service.py`): text chunking (500-1000 chars, sliding window) and embedding generation via `google-genai`
- [ ] B3 Background indexing pipeline hooked into document upload (`attachment_service.py`) and editor save (`documentos.py:PUT /content`) via FastAPI `BackgroundTasks`
- [ ] B4 Secure semantic retrieval endpoint/method scoping chunks strictly by `project_id` and verified user ownership, deprecating client-supplied `file_path`
- [ ] B5 Update AI prompts & assistant endpoints (`ai_assistant.py`, `ai_service.py`) to inject top-K retrieved chunks with source metadata into Gemini context
- [ ] B6 Unit & integration tests for chunking, embedding service, and RAG retrieval

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
