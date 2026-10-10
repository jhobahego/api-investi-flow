# Feature: project-archiving — backend (borrado lógico)

## Objective
Implementar el borrado lógico (archivado) de proyectos en la API según `TODO.md` §1 del proyecto padre.

## Problem
Eliminar un proyecto hace borrado físico con `cascade="all, delete-orphan"` (fases, tareas, adjuntos, historial). Verificado en este staging: `app/models/project.py:40-89` sin `deleted_at`; `DELETE /{project_id}` (`app/api/api_v1/endpoints/projects.py:335-361`) → `project_service.delete_user_project` (`app/services/project_service.py:148-179`, `db.delete+commit`); repositorio sin filtros (`app/repositories/project_repository.py:16-28,67-78`).

## Why
Pedido explícito del usuario 2026-10-10. Restricción vigente: trabajar siempre desde los staging (este worktree, rama `develop`).

## Scope
- Solo este repo (`api-investi-flow`), worktree staging, rama feature desde `develop`.
- Solo `TODO.md` §1 (archivado). §2 (renombrar) FUERA de alcance.
- No incluye: cambios en `main`/prod, push/PR/merge (decisión del usuario), frontend (vive en doc hermano).

## Sibling doc
- Frontend: `/home/jhobadev/Escritorio/Dev/investi-flow-project/investi-flow.worktrees/staging/odd/tasks/project-archiving-frontend.md`
- Índice padre (puntero, no fuente): `/home/jhobadev/Escritorio/Dev/investi-flow-project/odd/tasks/project-archiving.md`
- ESTE doc es dueño del contrato API. El frontend lo consume como copia congelada.

## Constraints
- Un solo writer; sin writers paralelos en este worktree.
- Commits convencionales en inglés; código/identificadores en inglés.
- UTC con `datetime.now(timezone.utc)` (NO `utcnow()` obsoleto que pide el TODO).
- `GET /archived` y `POST /{id}/restore` declarados ANTES de `GET /{project_id}` (si no, "archived" se parsea como int → 422).
- `alembic/env.py:15` solo importa `User`: asegurar que la migración detecte `projects.deleted_at` (importar modelos necesarios).
- Ramas feature desde `develop`; no tocar `main` ni el checkout raíz.

## API contract (FUENTE DE VERDAD)
- Modelo: `deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True, default=None, index=True)`.
- `DELETE /proyectos/{id}` → soft-delete (`deleted_at=now UTC`). Si ya archivado: idempotente (200/204). Solo owner; 404 si no existe o no es owner.
- `GET /proyectos/` → excluye archivados por defecto.
- `GET /proyectos/search` → excluye archivados.
- `GET /proyectos/archived` → solo archivados del owner (antes de `/{project_id}`).
- `GET /proyectos/{id}` (+ `/phases`, `/documentos`) → 404 si archivado.
- `POST /proyectos/{id}/restore` → `deleted_at=None`; 404 si no existe/no owner; 400/409 si no estaba archivado.
- `DELETE /proyectos/{id}/permanent` → hard-delete SOLO si ya archivado; 400 si no archivado; 404 si no existe/no owner. Único hard-delete.
- Schemas `ProjectResponse`/`ProjectListResponse`: añadir `deleted_at: Optional[datetime]`.

## Checklist
- [x] B1 Modelo `deleted_at` + migración Alembic (aplica y revierte limpio)
- [x] B2 Endpoints + repo/service/schemas según contrato
- [x] B3 Tests (actualizar delete + nuevos archived/restore/permanent)

## Authorized scope
- `app/models/project.py`
- `app/schemas/project.py`
- `app/repositories/project_repository.py`
- `app/services/project_service.py`
- `app/api/api_v1/endpoints/projects.py`
- `alembic/versions/` (nueva migración)
- `tests/test_api/test_projects.py`
- `tests/test_services/test_project_service.py`
- `tests/test_models/test_project.py` (si requiere ajuste)
- `odd/tasks/project-archiving-backend.md` (este archivo)

## Acceptance criteria
- `DELETE /{id}` archiva (fila sigue en DB con `deleted_at`); `GET /` y `search` lo excluyen; `GET /archived` lo lista; `POST /{id}/restore` lo restaura; `DELETE /{id}/permanent` lo borra solo si archivado (400 si no).
- `GET /{id}` de archivado → 404.
- Migración: `upgrade head` / `downgrade -1` / `upgrade head` limpio en staging.
- Todo fallo/skipped reportado honestamente.

## Applicable checks
- Cwd staging api. Runner: pytest del venv del checkout raíz o `make test`:
- Foco: pytest `tests/test_api/test_projects.py`, luego `tests/test_services/test_project_service.py` y `tests/test_models/test_project.py`.
- `make format` y `make lint` en verde.
- Parent spot check: un comando antes de entregar.

## Route declaration
- B1–B3: un solo delegated direct writer (7+ archivos no triviales + migración + lectura que prepara escritura). Triggers: writer + preparation. Sin re-lectura masiva de evidencia ya mapeada.

## Test-first policy
Aplica TDD: hay runner determinístico (pytest) y outcomes claros. El writer observa RED antes de GREEN (nuevos tests archived/restore/permanent fallando contra código actual, o test delete viejo fallando tras soft-delete como RED esperado), luego GREEN con refactor en verde. Excepción solo documentada si algún check no ejecutable. No inventar evidencia ni runners.

## Delivery strategy
Forecast backend: ~200–280 líneas autoradas. Estrategia `ask-on-risk`. Commits work-unit en rama `feat/project-archiving` desde `develop` (boundary inicial: base de `develop`); registrar identidades abajo. Sin push/PR/merge sin autorización.

## Progress
- 2026-10-10: creado este documento (B1 pending). Split del doc padre en dos docs versionados por repo (decisión del usuario).
- 2026-10-10: B1–B3 implementados en rama `feat/project-archiving` con TDD (RED observado antes de GREEN). Ver ## Commits y ## Verification evidence.

## Verification evidence
- RED (pre-implementación, solo tests nuevos contra código viejo): `tests/test_api/test_projects.py` 11 failed / 33 passed; `tests/test_services/test_project_service.py` + `tests/test_models/test_project.py` 11 failed / 28 passed.
- GREEN (post-implementación y post-`black`): `pytest tests/test_api/test_projects.py` → 44 passed; `pytest tests/test_services/test_project_service.py tests/test_models/test_project.py` → 39 passed (total 83 passed).
- Migración `e91e6743c3c1` (down `3569f95678a2`): verificada aislada en SQLite temporal (tabla `projects` sin `deleted_at` + `stamp 3569f95678a2`): `upgrade head` añade columna + índice `ix_projects_deleted_at`; `downgrade -1` los quita; re-`upgrade head` los restaura; `heads` único. PENDIENTE honesto: cadena completa `upgrade head` desde base no ejecutable aquí — migraciones preexistentes (`92f8daac04aa`) usan `ALTER COLUMN ... TYPE` solo-Postgres y no hay `DATABASE_URL` de staging configurado en este entorno.
- `make format` / `make lint`: fallan con Error 127 porque el worktree staging no tiene `.venv` (condición preexistente del entorno, no del cambio). Equivalentes ejecutados con el venv del checkout raíz: `black app/` + `isort app/` en verde (2 archivos reformateados), `flake8 app/` exit 0, `mypy app/` "Success: no issues found in 72 source files". Pre-commit hooks del repo en verde en ambos commits.
- Desviación de alcance registrada: `alembic/env.py` importa solo `User` (`user.py` solo referencia `Project` bajo `TYPE_CHECKING`), por lo que `Base.metadata` en env de Alembic no registra la tabla `projects` y un futuro `revision --autogenerate` no detectaría cambios en ella. `env.py` está fuera de las superficies autorizadas de este worker → no se tocó; la migración se escribió a mano. Seguimiento sugerido: añadir `from app.models.project import Project` (o `import app.models`) en `alembic/env.py`.

## Commits
- `f59cc7c` test(projects): cover soft-delete, archived listing, restore and permanent delete (RED)
- `e5675b2` feat(projects): soft-delete with deleted_at, archived listing, restore and permanent delete (GREEN)
- (este doc) docs(archiving): check off B1-B3 with commit hashes — pendiente hash al commitear

## Next step
- B1: writer backend modelo + migración.

## Engram mirror
- Pendiente (guardar bajo topic `odd/project-archiving/tasks`, proyecto `investi-flow-api`; bloqueado por `ambiguous_project` desde cwd padre — reintentar con cwd en este repo o elección del usuario).
