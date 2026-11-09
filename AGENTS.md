# AGENTS.md — InvestiFlow API (`api-investi-flow`)

Operational guide, engineering standards, and workflow instructions for AI agents working in this repository.

## Quick Reference / Ground Rules

1. **Virtual Environment First**: ALWAYS use or activate the virtual environment (`source .venv/bin/activate` or prefix commands with `.venv/bin/`) before running tests, linters, tools, or git operations.
2. **Quality Gate Before Commits**: Run `make quality` (or `.venv/bin/black --check app/ && .venv/bin/isort --check-only app/ && .venv/bin/flake8 app/ && .venv/bin/mypy app/ && .venv/bin/pytest`) before proposing or committing code changes.
3. **Commit Messages**: Follow Conventional Commits in **English** (e.g., `feat(projects): ...`, `fix(auth): ...`, `chore(deps): ...`). Never add "Co-Authored-By" or AI attribution.
4. **Secrets & Environment**: Never commit or expose secrets. Maintain environment variables in `.env` (template in `.env.example`).
5. **Layer Separation**: Maintain clean boundary separation (`Endpoint -> Service -> Repository -> Model`). Do not execute DB queries in routers or HTTP logic in models/services.

---

## Tech Stack & Architecture

- **Runtime**: Python 3.11+
- **Framework**: FastAPI (Pydantic v2 schemas and dependency injection)
- **Database & ORM**: PostgreSQL (Neon serverless with `sslmode=require`), SQLAlchemy 2 Declarative Base
- **Database Migrations**: Alembic (`alembic/` and `alembic.ini`)
- **AI & Rate Limiting**: Google Gemini GenAI via `app/services/ai_service.py` with layered token budget, semaphores, and rate limiting (`limits` + Upstash Redis with in-memory fallback in `app/core/gemini_guard.py`)
- **Code Quality**: Black (line length 88), isort (black profile), Flake8, Mypy (strict type checking enabled on `app/`)
- **Testing**: Pytest with SQLite in-memory / test database configuration (`tests/conftest.py`)
- **Containerization**: Docker Compose (`docker-compose.yml`, `Dockerfile`)

### Layered Architecture

```
app/
├── api/
│   └── api_v1/endpoints/  # HTTP routers, request/response serialization, status codes
├── services/               # Business logic, orchestration, AI service & cost guard integration
├── repositories/           # Database access layer, SQLAlchemy session queries, CRUD abstractions
├── models/                 # SQLAlchemy ORM declarative models (User, Project, Task, Phase, Document)
├── schemas/                # Pydantic schemas for data validation and API contracts
├── core/                   # Security (JWT, bcrypt), config (.env), database engine, gemini_guard
└── middleware/             # Middlewares (CORS, proxy headers, rate limiters)
```

---

## Development & Verification Commands

All commands assume the virtual environment is active or are run via `make` targets.

### 1. Environment Setup

```bash
# Initial setup (installs requirements, pre-commit, creates directories)
make setup

# Or activate manually
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Quality & Testing (MANDATORY before commits)

```bash
# Run all quality checks (format + lint + test)
make quality

# Targeted verification
make format        # Format with black and isort
make format-check  # Verify formatting without altering files
make lint          # Run flake8 and mypy on app/
make test          # Run pytest test suite
make test-cov      # Run pytest with HTML and terminal coverage
```

### 3. Database Migrations

Whenever modifying or adding SQLAlchemy models in `app/models/`:

1. Ensure the model is imported in `alembic/env.py` so `autogenerate` tracks all metadata.
2. Create migration:
   ```bash
   make db-migrate msg="add_field_or_table_name"
   ```
3. Apply migrations:
   ```bash
   make db-upgrade
   ```
4. Rollback last migration:
   ```bash
   make db-downgrade
   ```

### 4. Running the Application

```bash
# Local development server with reload on port 8000
make dev

# Docker Compose
make docker-up
make docker-logs
make docker-down
```

---

## Coding Standards & Conventions

| Domain | Guideline |
|--------|-----------|
| **Typing** | Strict typing enforced. All functions, arguments, and return types must have explicit type hints (`mypy` compliant). |
| **API Responses** | Always use Pydantic models for response serialization (`response_model=...`). Do not return raw SQLAlchemy instances directly. |
| **Async I/O** | Use `async def` for FastAPI endpoints and I/O-bound service methods. Do not block the event loop. |
| **Error Handling** | Raise standard FastAPI `HTTPException` with descriptive error details and proper HTTP status codes (e.g., 400, 401, 403, 404, 429). |
| **Soft Deletes** | Use `deleted_at` timestamps for soft-deletable resources (such as projects and documents) rather than physical deletion, unless a hard/permanent delete endpoint is explicitly invoked. |
| **AI Endpoints** | Route all Gemini interactions through `app/services/ai_service.py` to ensure rate limiting (`gemini_guard`), timeouts, token tracking, and truncation are strictly respected. |
| **Test Isolation** | Pytest uses SQLite and dedicated testing sessions (`test_db_config.py`). Tests must never connect to or mutate production Neon database instances. |

---

## Git & Contribution Standards

- **Target Branches**: Feature branches fork from `develop` and PRs target `develop`.
- **Commit Messages**: Conventional Commits in **English**:
  - `feat(scope): short description`
  - `fix(scope): short description`
  - `refactor(scope): short description`
  - `test(scope): short description`
  - `docs(scope): short description`
  - `chore(scope): short description`
- **Pre-commit**: Pre-commit hooks run Black, Flake8, and Mypy on commit. Ensure your virtual environment is active during `git commit`.
- **Attribution**: Do NOT include AI tags, co-author lines, or model metadata in commit messages.
