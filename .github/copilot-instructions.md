# Copilot / AI Agent Instructions (Backend-focused, English)

Purpose: help an AI coding agent become productive quickly working on the backend API only (`investi-flow-api` subproject). This file focuses on backend architecture, dev workflows, conventions, integration points and git commit conventions.

1) Architecture (4-layer backend)
- Path: `app/` follows a strict 4-layer pattern: `api/endpoints/` → `services/` → `repositories/` → `models/`.
- Rule: Endpoints call Services; Services instantiate and call Repositories; Repositories encapsulate SQLAlchemy access.
- Example: `app/api/api_v1/endpoints/projects.py` → `app/services/project_service.py` → `app/repositories/project_repository.py` → `app/models/project.py`.

2) Essential commands (use the repository `Makefile`)
- `make dev` — run FastAPI dev server (uvicorn) for backend.
- `make test` — run pytest suite (backend uses SQLite in-memory by default).
- `make test-cov` — tests with coverage report.
- `make quality` — formatting, lint, and test checks used before PRs.
- `make docker-up` — start stack (Postgres, Redis, Celery) via docker-compose.
- DB migrations: `make db-migrate msg="<short description>"` → review migration → `make db-upgrade`.

3) Code conventions and patterns (backend)
- Repositories extend `BaseRepository[...]`. Prefer CRUD and query logic inside repository classes.
- Services are the place for business logic and orchestration. Instantiate repositories in service constructors: `ProjectService(ProjectRepository())`.
- Models use SQLAlchemy `Mapped[]` typing and `back_populates` on both sides of relationships (see `app/models/`).
- Pydantic schemas live in `app/schemas/` and are used by endpoints for request/response validation.

4) AI integration (backend)
- Service: `app/services/ai_service.py` — wrapper around Google GenAI SDK (`google-genai`).
- Model selection and feature gating in `app/core/ai_config.py`.
- System prompts and prompt constants in `app/core/ai_prompts.py`.
- Document extraction: `app/services/document_extraction_service.py` (uses `python-docx` to preserve formatting when possible).

5) Environment & config
- Backend settings: `app/core/config.py` (Pydantic Settings). Required envs: `DATABASE_URL`, `SECRET_KEY`, `GOOGLE_AI_API_KEY`.
- Uploads: `uploads/documents/` (check `app/services/attachment_service.py`) and `settings.MAX_FILE_SIZE` in config.

6) Testing patterns
- Tests live in `tests/`. Fixtures are in `tests/conftest.py` (e.g., `test_user`, `test_project`, `reset_database`).
- API tests use FastAPI TestClient with dependency overrides for authentication.

7) Git & commit message conventions
Note: the local agent could not inspect `git log` from this environment. Below are two options — prefer the first if you're not enforcing a different style in CI.

- Preferred (explicit): Follow Conventional Commits with short scopes for backend modules.
  Examples:
  - `feat(api): add projects list endpoint with pagination`
  - `fix(auth): refresh token race condition in interceptor`
  - `docs(migrations): clarify alembic revision steps for model change`
  - `test(service): add unit tests for ProjectService.create()`
  - `chore(deps): bump sqlalchemy to 2.1.0`

- Alternative (if your repo uses a different ad-hoc style): run locally and paste output of:
  ```bash
  git -C /path/to/your/clone log --pretty=format:'%h %s' -n 100
  ```
  I will adapt the guidance to match the observed style.

PR guidance:
- Branch names: `feature/<short-description>`, `fix/<short-description>`.
- Include short changelog + related issue numbers in description.
- Run `make quality` and backend tests before requesting review.

8) When to edit what
- Endpoints: `app/api/api_v1/endpoints/*` and `app/schemas/*` (Pydantic schemas).
- Business logic: `app/services/*` and tests in `tests/test_services/`.
- DB schema: `app/models/*` + `make db-migrate`, review generated alembic revision.

9) Quick file references
- App entry: `main.py`
- Services: `app/services/` (AI: `ai_service.py`, extraction: `document_extraction_service.py`)
- Repositories: `app/repositories/`
- Models: `app/models/`
- Config: `app/core/config.py`, `app/core/ai_config.py`, `app/core/ai_prompts.py`
- Tests: `tests/`, fixtures `tests/conftest.py`

10) If something is unclear
- See `docs/` inside `investi-flow-api/` (e.g., `IMPLEMENTACION_FINAL_EXTRACCION.md`).
- If you want, I can also add a `.github/PULL_REQUEST_TEMPLATE.md` or adapt commit conventions after you paste `git log` output.

---

If you want this translated to Spanish or prefer the instructions at repository root instead, tell me and I will move/translate them.
