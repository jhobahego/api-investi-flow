# Feature: gemini-cost-guard — rate limit Fase 1 con Upstash

## Objective
Proteger la factura de Gemini con rate limit en app (Fase 1), usando Upstash Redis free y límites ajustados a los planes/features reales del proyecto.

## Problem
Hoy no hay ningún enforcement: `PLAN_LIMITS` en `app/core/ai_config.py:80-99` dice "para implementación futura", ningún endpoint de `app/api/api_v1/endpoints/ai_assistant.py` chequea cuotas, `AIService` (`app/services/ai_service.py:183,262,321,393,639`) llama a Gemini sin semáforo/timeout/usage-log, y los prompts reales son 10-20x los de la guía (chat arma `project_context` con previews de 50k/25k/15k en `ai_assistant.py:882,913,942`; `max_output_tokens` reales: chat 4096, suggestions 512, citations 1024, bibliography 8192 en `ai_config.py:114-131`). Un atacante autenticado (o una cuenta comprometida) puede quemar tokens sin freno a nivel app. Spend Cap de AI Studio ya lo tiene el usuario (red de seguridad), falta el control principal en app.

## Why
Pedido explícito del usuario 2026-10-11: ajustar la guía `rate-limit-gemini-fastapi.md` a los límites actuales, usar Upstash Redis free, aplicar las adaptaciones detectadas, implementar Fase 1. Celery hoy no se usa en código (cero `@shared_task`/`delay()`; solo `docker-compose.yml:36-42` local) — se responde y se deja fuera de alcance activar workers en prod.

## Scope
- Solo este repo, worktree staging, rama `feat/gemini-cost-guard` desde `develop`.
- Fase 1: guard con `limits` + Upstash + fallback memoria + prefiltro local, solo en las 4 rutas Gemini, logging de `usage_metadata`, semáforo + timeout, `Request` para IP real.
- No incluye: activar Celery workers en prod,3006-aoi, migración Neon para contadores (se descarta: el usuario eligió Upstash), Spend Cap (ya hecho por el usuario), push/PR/merge.

## Constraints
- Un solo writer; sin writers paralelos en este worktree.
- Commits convencionales en inglés; código/identificadores en inglés.
- Upstash free: 256 MB, 500k comandos/mes, TLS (`rediss://`). Presupuesto: ~5 hits Redis/req × ~2 cmds/hit ≈ 10 cmds/req → ~50k req/mes. Medir en dashboard 24h.
- Render Key Value Free NO se usa como store primario (no persiste, restart = wipe).
- No limitar `/`, `/health`, `/docs`.
- Nunca leer `X-Forwarded-For` a mano; `request.client.host` con `--proxy-headers` bien configurado.
- `limits` aún no instalado (`ModuleNotFoundError` verificado); añadir `limits[async-redis]`.

## Limites ajustados al proyecto (fuente de verdad)
Estimación conservadora: `tokens ≈ len(chars)//3`. Costo por req = prompt_estimado + max_output_tokens (peor caso).

| Feature | max_output | Prompt típico (acotado Fase 1) | USER/min | USER/día count (por plan) | USER tokens/día (por plan) |
|---|---|---|---|---|---|
| chat | 4096 | user msg ≤5000 + contexto truncado ≤12000 chars | 5/min | EST 50 / INV 200 / PRO ilimitado (-1 = skip count) | EST 100k / INV 400k / PRO 1M |
| suggestions | 512 | text ≤1000 + doc ≤20000 (schema ya acota) + truncado server ≤12000 | 10/min | EST 100 / INV 500 / PRO ilimitado | comparte bolsa USER tokens/día |
| citations | 1024 | JSON chico ≤8000 chars | 10/min | EST 20 / INV 100 / PRO ilimitado | comparte bolsa |
| bibliography | 8192 + grounding | query ≤2000 + contexto ≤6000 | 3/min | EST 0 (bloqueado) / INV 50 / PRO ilimitado | comparte bolsa, pero con sub-techo feature 300k/día por usuario |
| IP/min (todas) | — | — | 20/min por IP (Redis) | — | — |
| Prefiltro local | — | — | 60/min por IP (memoria, 0 cmds) | — | — |
| Global | — | — | — | — | 1M tokens/día (env `GEMINI_GLOBAL_TOKENS_DAY`, punto de partida; fórmula guía: `(presupuesto_mensual/30)/precio_por_token`) |

Notas: PROFESIONAL ilimitado en count pero SIEMPRE acotado por bolsa tokens + global (si no, una cuenta PRO comprometida es factura infinita). Bibliography EST 0 = 403 con mensaje de upgrade (ya existe ese patrón en el endpoint). Truncados server-side Fase 1: chat contexto ≤12000 chars, suggestions doc ≤12000, bibliography contexto ≤6000. `Content-Length` guard 32k en middleware solo para rutas `/api/v1/ia/*` y `/api/v1/proyectos/*/ia/*`, `/api/v1/proyectos/*/chat`.

## Checklist
- [x] G1 Guard `app/core/gemini_guard.py` + settings (`RATE_LIMIT_REDIS_URL`, `GEMINI_GLOBAL_TOKENS_DAY`, `RATE_LIMIT_ENABLED`) + dep `limits[async-redis]` en `requirements.txt`
- [x] G2 Instrumentar `app/services/ai_service.py`: `usage_metadata` log + semáforo async (5) + timeout (30s) vía `asyncio.to_thread` + `wait_for`; `generate_conversation_title` pasó a `async def`
- [x] G3 Enforcement en `app/api/api_v1/endpoints/ai_assistant.py` (4 endpoints + title-generation cuenta dentro de chat): `http_request: Request` + plan hardcodeado con TODO intacto + 429/503 con `Retry-After`
- [x] G4 Tests + `.env.example` + docs despliegue Upstash/Render

## Authorized scope
- `app/core/gemini_guard.py` (nuevo)
- `app/core/config.py`
- `app/core/ai_config.py` (solo añadirốc techos tokens/bolsas si hace falta; no cambiar modelos)
- `app/services/ai_service.py`
- `app/api/api_v1/endpoints/ai_assistant.py`
- `app/middleware/` (solo guard Content-Length acotado a rutas IA, si se crea)
- `requirements.txt`
- `.env.example`
- `tests/test_core/test_gemini_guard.py` (nuevo)
- `tests/test_api/test_ai_assistant.py` (ampliar, con mocks sin Redis)
- `odd/tasks/gemini-cost-guard.md` (este archivo)

## Acceptance criteria
- Con `USER_PER_MIN=5` chat: 5×200 luego 429 con `Retry-After`; prompt > cap → 413; `GLOBAL_TOKENS_DAY` bajado a 1 → 503.
- Redis apagado/URL inválida: sigue limitando con fallback memoria + log `Redis no disponible`.
- Cada llamada Gemini loguea `gemini_usage prompt=%s output=%s total=%s feature=%s user=%s`.
- Bibliography con plan ESTUDIANTE → 403 sin gastar tokens.
- `pytest tests/test_core/test_gemini_guard.py tests/test_api/test_ai_assistant.py` en verde; `black/isort/flake8/mypy` en verde (con venv raíz).
- Upstash comandos medidos/documentados para revisar a las 24h.

## Applicable checks
- Cwd staging api. Runner: `/home/jhobadev/Escritorio/Dev/investi-flow-project/investi-flow-api/.venv/bin/python -m pytest` (el worktree no tiene `.venv`, preexistente).
- Foco: `tests/test_core/test_gemini_guard.py`, luego `tests/test_api/test_ai_assistant.py`.
- Formato/lint: `black --check app/`, `isort --check-only app/`, `flake8 app/`, `mypy app/` con el venv raíz.
- Parent spot check: un comando antes de entregar.

## Route declaration
- G1–G4: un solo delegated direct writer (5+ archivos no triviales + lectura que prepara escritura). Triggers: writer + preparation. Sin re-lectura masiva de evidencia ya mapeada. TDD donde aplique (guard puro sí; endpoints con mocks no requieren RED previo costoso).

## Test-first policy
Aplica parcial: `test_gemini_guard.py` con `MemoryStorage` sí tiene runner determinístico y outcomes claros → RED antes de GREEN. Endpoints se verifican con mocks de `ai_service` + guard en modo memoria (no se inventa RED de integración con Upstash real). Excepción documentada: sin URL Upstash en CI se usa memoria.

## Delivery strategy
Forecast: ~350–450 líneas autoradas (guard ~220 + instrumentación ~60 + endpoints ~80 + tests ~120, docs aparte). Estrategia `ask-on-risk` (default). Commits work-unit en `feat/gemini-cost-guard` desde `develop` (boundary inicial: `bc58914`); registrar identidades abajo. Sin push/PR/merge sin autorización.

## Progress
- 2026-10-11: creado este documento, rama `feat/gemini-cost-guard` desde `develop`. G1 pending.
- 2026-10-11: G1 done (`4dbae4b`). TDD RED observado (ImportError guard ausente) y GREEN 9/9. Decisiones: bolsas USER tokens/día en `ai_config.py` (EST 100k/INV 400k/PRO 1M + sub-techo biblio 300k); `limits` aún no instalado => el módulo importa igual con stubs (fail-open + warning).
- 2026-10-11: G2 done (`632ea4c`). Truncado server-side en `ai_service.py` (único lugar, protege a todos los callers): chat <=12000, suggestions doc <=12000, biblio contextos <=6000. Log `gemini_usage prompt=%s output=%s total=%s feature=%s` (formato parent; sin `user=` para no cambiar firmas). `check_api_health` sigue sync (probe fuera del request path).
- 2026-10-11: G3 done (`6f10342`). `http_request: Request` en los 4 endpoints; enforce pre-check barato con mensaje/query/texto; `except HTTPException: raise` añadido en `generate_suggestion` (los otros 3 ya lo tenían); chat hace enforce antes de crear la conversación.
- 2026-10-11: G4 done (`6eebe66`). Fixture `disable_gemini_guard` en `test_ai_assistant.py` (contadores memoria globales se acumularían entre tests); 4 tests nuevos con mocks. `tests/test_services/test_ai_service.py` regresión: 25 passed.

## Verification evidence
- `/home/jhobadev/Escritorio/Dev/investi-flow-project/investi-flow-api/.venv/bin/python -m pytest tests/test_core/test_gemini_guard.py -v`: 9 passed (RED previo: ImportError guard ausente; GREEN tras G1).
- `/home/jhobadev/Escritorio/Dev/investi-flow-project/investi-flow-api/.venv/bin/python -m pytest tests/test_api/test_ai_assistant.py -v`: 26 passed (22 existentes + 4 TestCostGuard nuevos).
- `/home/jhobadev/Escritorio/Dev/investi-flow-project/investi-flow-api/.venv/bin/python -m black --check app/ tests/test_core/test_gemini_guard.py`: 74 files unchanged, pass.
- `/home/jhobadev/Escritorio/Dev/investi-flow-project/investi-flow-api/.venv/bin/python -m isort --check-only app/`: pass (sin salida).
- `/home/jhobadev/Escritorio/Dev/investi-flow-project/investi-flow-api/.venv/bin/python -m flake8 app/`: pass (sin salida).
- `/home/jhobadev/Escritorio/Dev/investi-flow-project/investi-flow-api/.venv/bin/python -m mypy app/`: FAIL ambiental — `deprecated/sphinx.py:35: error: Type statement is only supported in Python 3.12 and greater [syntax]` (transitivo de `limits[async-redis]` via `limits/strategies.py`; `deprecated` trae `py.typed` con sintaxis 3.12 que mypy 1.7.1 con `python_version=3.11` no parsea; cero errores en archivos propios — el hook pre-commit mypy pasó en los 4 commits). Fix propuesto (parent): subir mypy o `[[tool.mypy.overrides]]` para `deprecated.*` — fuera de allowed surfaces.
- Extra: `pytest tests/test_services/test_ai_service.py -q`: 25 passed (regresión G2, mocks sync siguen válidos con `to_thread`).

## Commits
- `4dbae4b` feat(guard): add Gemini cost guard with Upstash Redis and memory fallback (G1)
- `632ea4c` feat(ai): add usage logging, semaphore, timeout and server-side truncation (G2)
- `6f10342` feat(api): enforce Gemini cost guard on the four AI endpoints (G3)
- `6eebe66` test(ai): cover Gemini cost guard on endpoints and document rate-limit env (G4)

## Next step
- G1: writer guard + settings + dep.

## Engram mirror
- Guardar espejo completo bajo topic `odd/gemini-cost-guard/tasks`, proyecto `api-investi-flow`.
