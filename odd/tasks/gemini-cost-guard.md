# Feature: gemini-cost-guard — Phase 1 rate limit with Upstash

## Objective
Protect the Gemini bill with in-app rate limiting (Phase 1), using free Upstash Redis and limits tuned to the project's real plans/features.

## Problem
There is currently no enforcement: `PLAN_LIMITS` in `app/core/ai_config.py:80-99` says "for future implementation", no endpoint in `app/api/api_v1/endpoints/ai_assistant.py` checks quotas, `AIService` (`app/services/ai_service.py:183,262,321,393,639`) calls Gemini with no semaphore/timeout/usage-log, and the real prompts are 10-20x the ones in the guide (chat builds `project_context` with 50k/25k/15k previews in `ai_assistant.py:882,913,942`; real `max_output_tokens`: chat 4096, suggestions 512, citations 1024, bibliography 8192 in `ai_config.py:114-131`). An authenticated attacker (or a compromised account) can burn tokens with no in-app brake. The user already has the AI Studio Spend Cap (safety net); the main in-app control is missing.

## Why
Explicit user request 2026-10-11: adapt the `rate-limit-gemini-fastapi.md` guide to the current limits, use free Upstash Redis, apply the detected adaptations, implement Phase 1. Celery is not used in code today (zero `@shared_task`/`delay()`; only local `docker-compose.yml:36-42`) — answered and left out of scope to enable workers in prod.

## Scope
- This repo only, staging worktree, `feat/gemini-cost-guard` branch from `develop`.
- Phase 1: guard with `limits` + Upstash + memory fallback + local prefilter, only on the 4 Gemini routes, `usage_metadata` logging, semaphore + timeout, `Request` for the real IP.
- Excludes: enabling Celery workers in prod, 3006-aoi, Neon migration for counters (discarded: the user chose Upstash), Spend Cap (already done by the user), push/PR/merge.

## Constraints
- A single writer; no parallel writers in this worktree.
- Conventional Commits in English; code/identifiers in English.
- Upstash free: 256 MB, 500k commands/month, TLS (`rediss://`). Budget: ~5 Redis hits/req × ~2 cmds/hit ≈ 10 cmds/req → ~50k req/month. Measure on the dashboard at 24h.
- Render Key Value Free is NOT used as the primary store (no persistence, restart = wipe).
- Do not limit `/`, `/health`, `/docs`.
- Never read `X-Forwarded-For` by hand; `request.client.host` with correctly configured `--proxy-headers`.
- `limits` not yet installed (verified `ModuleNotFoundError`); add `limits[async-redis]`.

## Project-tuned limits (source of truth)
Conservative estimate: `tokens ≈ len(chars)//3`. Cost per req = estimated prompt + max_output_tokens (worst case).

| Feature | max_output | Typical prompt (Phase 1 bounded) | USER/min | USER/day count (per plan) | USER tokens/day (per plan) |
|---|---|---|---|---|---|
| chat | 4096 | user msg ≤5000 + truncated context ≤12000 chars | 5/min | STU 50 / INV 200 / PRO unlimited (-1 = skip count) | STU 100k / INV 400k / PRO 1M |
| suggestions | 512 | text ≤1000 + doc ≤20000 (schema already bounds) + server truncated ≤12000 | 10/min | STU 100 / INV 500 / PRO unlimited | shares USER tokens/day pool |
| citations | 1024 | small JSON ≤8000 chars | 10/min | STU 20 / INV 100 / PRO unlimited | shares pool |
| bibliography | 8192 + grounding | query ≤2000 + context ≤6000 | 3/min | STU 0 (blocked) / INV 50 / PRO unlimited | shares pool, but with 300k/day per-user feature sub-cap |
| IP/min (all) | — | — | 20/min per IP (Redis) | — | — |
| Local prefilter | — | — | 60/min per IP (memory, 0 cmds) | — | — |
| Global | — | — | — | — | 1M tokens/day (env `GEMINI_GLOBAL_TOKENS_DAY`, starting point; guide formula: `(monthly_budget/30)/price_per_token`) |

Notes: PROFESIONAL is unlimited in count but ALWAYS bounded by the token pool + global (otherwise a compromised PRO account is an infinite bill). Bibliography STU 0 = 403 with upgrade message (that pattern already exists in the endpoint). Phase 1 server-side truncations: chat context ≤12000 chars, suggestions doc ≤12000, bibliography context ≤6000. `Content-Length` guard 32k in middleware only for `/api/v1/ia/*`, `/api/v1/proyectos/*/ia/*`, `/api/v1/proyectos/*/chat` routes.

## Checklist
- [x] G1 Guard `app/core/gemini_guard.py` + settings (`RATE_LIMIT_REDIS_URL`, `GEMINI_GLOBAL_TOKENS_DAY`, `RATE_LIMIT_ENABLED`) + `limits[async-redis]` dep in `requirements.txt`
- [x] G2 Instrument `app/services/ai_service.py`: `usage_metadata` log + async semaphore (5) + timeout (30s) via `asyncio.to_thread` + `wait_for`; `generate_conversation_title` became `async def`
- [x] G3 Enforcement in `app/api/api_v1/endpoints/ai_assistant.py` (4 endpoints + title-generation counts toward chat): `http_request: Request` + hardcoded plan with TODO intact + 429/503 with `Retry-After`
- [x] G4 Tests + `.env.example` + Upstash/Render deployment docs
- [x] G5 Translate all Spanish introduced by this PR to English (descriptions, comments, docstrings, logs, new guard HTTP messages); functional Gemini prompts in Spanish and pre-existing Spanish left intact

## Authorized scope
- `app/core/gemini_guard.py` (new)
- `app/core/config.py`
- `app/core/ai_config.py` (only add token ceilings/pools if needed; do not change models)
- `app/services/ai_service.py`
- `app/api/api_v1/endpoints/ai_assistant.py`
- `app/middleware/` (only Content-Length guard scoped to AI routes, if created)
- `requirements.txt`
- `.env.example`
- `tests/test_core/test_gemini_guard.py` (new)
- `tests/test_api/test_ai_assistant.py` (extend, with mocks and no Redis)
- `odd/tasks/gemini-cost-guard.md` (this file)

## Acceptance criteria
- With `USER_PER_MIN=5` chat: 5×200 then 429 with `Retry-After`; prompt over cap → 413; `GLOBAL_TOKENS_DAY` lowered to 1 → 503.
- Redis off/invalid URL: still limits with memory fallback + `Redis unavailable` log.
- Every Gemini call logs `gemini_usage prompt=%s output=%s total=%s feature=%s user=%s`.
- Bibliography with ESTUDIANTE plan → 403 without spending tokens.
- `pytest tests/test_core/test_gemini_guard.py tests/test_api/test_ai_assistant.py` green; `black/isort/flake8/mypy` green (with root venv).
- Upstash commands measured/documented for review at 24h.
- G5: `git diff develop...HEAD -- app/ tests/ .env.example Dockerfile | grep '^+' | grep -P '[áéíóúñÁÉÍÓÚÑ]'` (excluding functional `CONTEXTO|BÚSQUEDA|ESPAÑOL` prompts) returns EMPTY; tests assert the new English messages.

## Applicable checks
- Staging api cwd. Runner: `/home/jhobadev/Escritorio/Dev/investi-flow-project/investi-flow-api/.venv/bin/python -m pytest` (the worktree has no `.venv`, pre-existing).
- Focus: `tests/test_core/test_gemini_guard.py`, then `tests/test_api/test_ai_assistant.py`.
- Format/lint: `black --check app/`, `isort --check-only app/`, `flake8 app/`, `mypy app/` with the root venv.
- Parent spot check: one command before delivery.

## Route declaration
- G1–G4: a single delegated direct writer (5+ non-trivial files + reading that prepares writing). Triggers: writer + preparation. No mass re-reading of already mapped evidence. TDD where applicable (pure guard yes; endpoints with mocks do not require costly prior RED).
- G5: a single direct writer for translation (comments/messages/tests/docs); no behavior change, status codes unchanged.

## Test-first policy
Applies partially: `test_gemini_guard.py` with `MemoryStorage` has a deterministic runner and clear outcomes → RED before GREEN. Endpoints are verified with `ai_service` mocks + guard in memory mode (no Upstash-integration RED is invented). Documented exception: without an Upstash URL in CI, memory is used.
- G5 exception: pure message/comment translation with no behavior change; no RED applies. Verification is the focused green suite plus the empty-accent grep.

## Delivery strategy
Forecast: ~350–450 authored lines (guard ~220 + instrumentation ~60 + endpoints ~80 + tests ~120, docs aside). `ask-on-risk` strategy (default). Work-unit commits on `feat/gemini-cost-guard` from `develop` (initial boundary: `bc58914`); record identities below. No push/PR/merge without authorization.

## Progress
- 2026-10-11: created this document, `feat/gemini-cost-guard` branch from `develop`. G1 pending.
- 2026-10-11: G1 done (`4dbae4b`). TDD RED observed (missing-guard ImportError) and GREEN 9/9. Decisions: USER tokens/day pools in `ai_config.py` (STU 100k/INV 400k/PRO 1M + biblio 300k sub-cap); `limits` not yet installed => the module still imports with stubs (fail-open + warning).
- 2026-10-11: G2 done (`632ea4c`). Server-side truncation in `ai_service.py` (single place, protects all callers): chat <=12000, suggestions doc <=12000, biblio contexts <=6000. `gemini_usage prompt=%s output=%s total=%s feature=%s` log (parent format; no `user=` to avoid changing signatures). `check_api_health` stays sync (probe outside the request path).
- 2026-10-11: G3 done (`6f10342`). `http_request: Request` on the 4 endpoints; cheap pre-check enforce with message/query/text; `except HTTPException: raise` added in `generate_suggestion` (the other 3 already had it); chat enforces before creating the conversation.
- 2026-10-11: G4 done (`6eebe66`). `disable_gemini_guard` fixture in `test_ai_assistant.py` (global memory counters would accumulate across tests); 4 new tests with mocks. `tests/test_services/test_ai_service.py` regression: 25 passed.
- 2026-10-11: G5 done (`9adcf1b`). Translated all Spanish introduced by this PR to English: guard module docstring/comments/docstrings, `logger.*` messages (`Redis unavailable, using in-memory limits`, `limits not installed, rate limiting disabled`), new guard HTTP details (413/429/403/503), endpoint cost-guard comments, token-pool comments in `ai_config.py`, `.env.example` + `Dockerfile` comments. Kept intact: functional Spanish prompts for Gemini (`CONTEXTO DE LA BÚSQUEDA`, `EN ESPAÑOL`, system prompts), user-content fixtures in tests, and all pre-existing Spanish. Updated `test_gemini_guard.py:146` log assert and guard-message fixtures in `test_ai_assistant.py` to English. Old pushed message with "Fase 1" in `81908d2` untouched.

## Verification evidence
- `/home/jhobadev/Escritorio/Dev/investi-flow-project/investi-flow-api/.venv/bin/python -m pytest tests/test_core/test_gemini_guard.py -v`: 9 passed (prior RED: missing-guard ImportError; GREEN after G1).
- `/home/jhobadev/Escritorio/Dev/investi-flow-project/investi-flow-api/.venv/bin/python -m pytest tests/test_api/test_ai_assistant.py -v`: 26 passed (22 existing + 4 new TestCostGuard).
- `/home/jhobadev/Escritorio/Dev/investi-flow-project/investi-flow-api/.venv/bin/python -m black --check app/ tests/test_core/test_gemini_guard.py`: 74 files unchanged, pass.
- `/home/jhobadev/Escritorio/Dev/investi-flow-project/investi-flow-api/.venv/bin/python -m isort --check-only app/`: pass (no output).
- `/home/jhobadev/Escritorio/Dev/investi-flow-project/investi-flow-api/.venv/bin/python -m flake8 app/`: pass (no output).
- `/home/jhobadev/Escritorio/Dev/investi-flow-project/investi-flow-api/.venv/bin/python -m mypy app/`: ENVIRONMENTAL FAIL — `deprecated/sphinx.py:35: error: Type statement is only supported in Python 3.12 and greater [syntax]` (transitive from `limits[async-redis]` via `limits/strategies.py`; `deprecated` ships `py.typed` with 3.12 syntax that mypy 1.7.1 with `python_version=3.11` cannot parse; zero errors in own files — the pre-commit mypy hook passed on all 4 commits). Proposed fix (parent): bump mypy or `[[tool.mypy.overrides]]` for `deprecated.*` — outside allowed surfaces.
- Extra: `pytest tests/test_services/test_ai_service.py -q`: 25 passed (G2 regression, sync mocks still valid with `to_thread`).
- G5: `pytest tests/test_core/test_gemini_guard.py tests/test_api/test_ai_assistant.py` → 35 passed; `black --check app/ tests/test_core/test_gemini_guard.py` → 74 files unchanged; `flake8 app/` → pass; `isort --check-only app/` → pass; accent grep on new `app/|tests/|.env.example|Dockerfile` lines (excluding functional `CONTEXTO|BÚSQUEDA|ESPAÑOL|bibliografías|Bibliografía`) → EMPTY.

## Commits
- `4dbae4b` feat(guard): add Gemini cost guard with Upstash Redis and memory fallback (G1)
- `632ea4c` feat(ai): add usage logging, semaphore, timeout and server-side truncation (G2)
- `6f10342` feat(api): enforce Gemini cost guard on the four AI endpoints (G3)
- `6eebe66` test(ai): cover Gemini cost guard on endpoints and document rate-limit env (G4)
- `81908d2` docs(guard): close Fase 1 with checklist, verification evidence and hashes
- `9adcf1b` docs(guard): translate Phase 1 descriptions and messages to English (G5)

## Delivery
- Branch pushed to `origin/feat/gemini-cost-guard`; PR #30 against `develop`: https://github.com/jhobahego/api-investi-flow/pull/30 (merge pending, user decision; on merge, Render redeploys and applies guard + proxy-headers).
- Parent spot check 2026-10-11: `pytest tests/test_core/test_gemini_guard.py tests/test_api/test_ai_assistant.py` → 35 passed.
- 2026-10-11: proxy-headers for Render applied to the `Dockerfile` (no `--reload`, `${PORT:-8000}` port, `--forwarded-allow-ips="${FORWARDED_ALLOW_IPS:-127.0.0.1}"`). On Render set `FORWARDED_ALLOW_IPS=*` (or observed internal CIDR) as env var; the user configures `.env`/`.env.example` in the dashboard (reads blocked by repo rule).

## Next step
- Phase 1 closed on `feat/gemini-cost-guard` (5 commits, no push/PR). Next: configure Upstash `RATE_LIMIT_REDIS_URL` on Render + measure commands at 24h and tune `GEMINI_GLOBAL_TOKENS_DAY` with the guide formula; out of scope: Celery workers in prod, `deprecated`-mypy fix (proposed: bump mypy or per-module override).
- G5 follow-up: merge this translation commit (no push/PR by the writer); suggested 24h task: measure Upstash commands and tune `GEMINI_GLOBAL_TOKENS_DAY`.

## Engram mirror
- Save full mirror under topic `odd/gemini-cost-guard/tasks`, project `api-investi-flow`.
