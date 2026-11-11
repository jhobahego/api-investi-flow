# Feature: rag-chat-sources-and-indexing-status — Expose RAG sources and indexing state

File locator: `odd/tasks/rag-chat-sources-and-indexing-status.md`

GitHub issue: `jhobahego/api-investi-flow#34`

## Objective
Unblock the frontend (`rag-documents-frontend`) by exposing which documents produced a chat answer and whether an attachment's vector embeddings are ready.

## Problem
- `retrieve_context()` already returns `attachment_id`, `file_name`, `chunk_index`, `content`, and `similarity`, but `chat_with_persistent_history` discards the list after formatting the prompt.
- `ChatWithHistoryResponse` and `MessageResponse` do not expose `sources`, so the conversation history cannot show citations after reload.
- `Message` does not persist sources.
- Indexing is asynchronous (Celery or background task). `AttachmentResponse` cannot tell the UI whether embeddings are pending, in progress, ready, or failed. The frontend needs a badge in `AttachmentUpload.vue`.

## Why
Issue #34 acceptance criteria: OpenAPI must expose the new fields; chat must return `sources` when RAG retrieval happened and `[]` otherwise. The frontend F3 task requires a document indexing status indicator.

## Scope
### In scope
1. `sources` in `POST /api/v1/proyectos/{project_id}/chat` and in conversation history messages.
2. Persist sources with the assistant message so they survive reload.
3. `indexing_status` (`pending` | `indexing` | `indexed` | `error`) on `AttachmentResponse`.
4. Status transitions in the indexing service/worker.
5. Alembic migration, tests, verification.

### Out of scope
- `/ia/sugerencias` (no `sources` needed).
- Frontend changes.
- Reindex endpoint or UI retry action.

## Technical decisions
- `sources` payload shape per source: `{attachment_id, file_name, chunk_index, snippet, similarity}`. `snippet = content[:300]`.
- `Message.sources`: nullable `JSON` column; `None` when the message has no sources. API always serializes `[]`.
- `Attachment.indexing_status`: `String(20)` with a named check constraint, default `pending`. Python enum `IndexingStatus` for type safety.
- Migration backfills existing attachments: `indexed` when chunks exist, otherwise `pending`.
- Status transitions owned by `rag_service` session entry points:
  - worker start → `indexing`
  - chunks > 0 → `indexed`
  - exception or zero chunks → `error`
  - enqueue failure while indexing is enabled → `error`

## Checklist
- [x] T1 `ChatSource` schema; `sources` in `MessageResponse` and `ChatWithHistoryResponse` (default `[]`, `None` → `[]`)
- [x] T2 `Message.sources` JSON column + Alembic migration
- [x] T3 `create_message` persists `sources`
- [x] T4 Chat endpoint builds `sources` from retrieved chunks and persists them on the assistant message
- [x] T5 `IndexingStatus` enum + `Attachment.indexing_status` column + `AttachmentResponse` field
- [x] T6 Status transitions in `rag_service` for Celery and background paths
- [x] T7 Tests: chat sources (present and empty), persistence on history, attachment `indexing_status`, status transitions
- [x] T8 `make quality`: black, isort, flake8, pre-commit mypy and pytest green; bare `mypy app/` is blocked by a pre-existing environment mismatch (`mypy.ini` pins Python 3.11 while the venv runs 3.12 and the `deprecated` package uses a 3.12-only statement)

## Authorized Scope
- `app/models/conversation.py`
- `app/models/attachment.py`
- `app/schemas/conversation.py`
- `app/schemas/attachment.py`
- `app/schemas/__init__.py`
- `app/repositories/conversation_repository.py`
- `app/api/api_v1/endpoints/ai_assistant.py`
- `app/services/rag_service.py`
- `alembic/versions/` (one new revision)
- `tests/test_api/test_ai_assistant.py`
- `tests/test_api/test_attachments.py`
- `tests/test_rag_service.py`
- `odd/tasks/rag-chat-sources-and-indexing-status.md` (this file)

## Acceptance Criteria
- `ChatWithHistoryResponse` and history `MessageResponse` include `sources`, default `[]`.
- `sources` reappear after reloading a conversation (persisted).
- Sources contain only safe metadata plus a bounded snippet (≤ 300 chars).
- `AttachmentResponse` includes `indexing_status` with the four documented values.
- A successful indexing run ends as `indexed`; extraction/embedding failure ends as `error`.
- OpenAPI schema reflects the new fields.
- Existing test suite passes.

## Applicable Checks
- `.venv/bin/pytest tests/test_api/test_ai_assistant.py tests/test_api/test_attachments.py tests/test_rag_service.py -v`
- `make quality`

## Route
- Implementation: delegated to one bounded writer (`gentle-ai-worker`).
- Verification: writer runs the exact commands above; parent spot check on one reported command.
- Delivery: work-unit commit on `feat/rag-chat-sources-indexing-status`.

## Verification evidence
- Targeted suite: 102 passed (`tests/test_api/test_ai_assistant.py`, `tests/test_api/test_attachments.py`, `tests/test_rag_service.py`).
- Full suite: 565 passed.
- Parent spot check: 4 passed (`-k "sources or indexing_status"`).
- Local migration applied: `f3a9c1d7b2e4` → `7c1d9e4a2b6f`; schema verified in Postgres (`attachments.indexing_status` with check, `messages.sources` JSON).
- Live E2E on project 9: upload `pending` → `indexing` → `indexed` (~1 s); chat returned one source (`t.docx`, chunk 0, similarity 0.90); reloading the conversation returned the same persisted source.
- Environment fix during E2E: the `api` Docker image was stale and lacked `pgvector`, so retrieval failed silently; rebuilding `api` and `worker` fixed it. Not a code defect.
- Work-unit commit: `e3b4800` on `feat/rag-chat-sources-indexing-status`.

## Progress log
- 2026-11-10: Feature document created after exploration. No source changes yet.
- 2026-11-10: Implementation completed by bounded writer; tests and migration reviewed.
- 2026-11-11: Local migration applied and verified; E2E chat sources validated by the frontend; work-unit commit created.
