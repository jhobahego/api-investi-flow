# Background Jobs Candidates (Audit)

This document lists operations that are long-running or IO-heavy and could be
decoupled into background jobs in future iterations. No behavior changes are
proposed here.

## High Priority Candidates

- `app/services/document_extraction_service.py`
  - DOCX/PDF extraction and processing can be CPU/IO intensive.
- `app/services/document_generation_service.py`
  - Document generation pipelines can block request threads.
- `app/services/ai_service.py`
  - Gemini API calls for chat, suggestions, citations, and bibliography can be
    retried asynchronously and benefit from queueing.

## Medium Priority Candidates

- `app/services/attachment_service.py`
  - File uploads and disk operations may benefit from background processing for
    large files or batch operations.

## Notes

- Any future background job implementation should include idempotency keys and
  persisted job state transitions (pending/running/succeeded/failed).
- Consider a task queue (Celery/RQ/Dramatiq) aligned with the
  `python-background-jobs` skill guidelines.
