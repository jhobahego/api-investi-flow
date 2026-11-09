# InvestiFlow API

API REST desarrollada con FastAPI para la plataforma de gestión de proyectos de investigación InvestiFlow.

## 🚀 Inicio Rápido

### Opción 1: Docker (Recomendado) 🐳

```bash
git clone https://github.com/jhobahego/api-investi-flow.git
cd investi-flow-api

cp .env.example .env # IMPORTANTE: Editar .env con tus configuraciones (DB Neon, secrets, Redis, Gemini, etc.)

docker compose up -d
```

### Opción 2: Make + Docker ⚡

```bash
git clone https://github.com/jhobahego/api-investi-flow.git
cd investi-flow-api
make setup

# IMPORTANTE: Editar .env con tus configuraciones antes de continuar
make docker-up
```

### Opción 3: Desarrollo Local 🛠️

```bash
git clone https://github.com/jhobahego/api-investi-flow.git
cd investi-flow-api
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env # IMPORTANTE: Configurar PostgreSQL (Neon) y editar .env con tus datos
alembic upgrade head
uvicorn main:app --reload
```

**🌐 Acceso**: `http://localhost:8000` | **📖 Docs**: `http://localhost:8000/docs`

## 🎯 Estado del Proyecto

### ✅ **Sprint 1 Completado** (07/08/2025 – 15/08/2025)

- ✅ **Sistema de Autenticación**: Registro, login, logout con JWT
- ✅ **Gestión de Proyectos**: CRUD completo con autorización
- ✅ **Base de Datos**: PostgreSQL con migraciones Alembic
- ✅ **Testing**: Suite completa con pytest (auth, projects, users)
- ✅ **Arquitectura**: 4 capas (API → Services → Repositories → Models)

### ✅ **Sprint 2 Completado** (16/08/2025 – 06/11/2025)

- ✅ **Gestión de Documentos**: Upload, download, validaciones y previsualización
- ✅ **Sistema de Búsqueda**: Proyectos, documentos, filtros

### ✅ **Sprint 3 Completado** (04/09/2025 – 03/12/2025)

- ✅ **Asistente IA**: Análisis de documentos, chat inteligente con memoria, sugerencias, búsqueda de bibliografía y citaciones
- ⏸️ **Exportación**: Proyectos a PDF *(Pospuesto para futuras versiones)*

### 🚀 **Post-Sprint 3 — Estabilización y producción** (octubre 2026)

Verificado en `develop` / `main` a la altura del merge PR #32:

| Tema | Qué hay hoy |
|------|-------------|
| Gemini cost guard (Fase 1) | Rate limit con `limits` + Redis (Upstash en prod, memoria como fallback), semáforo, timeout, truncado server-side y log de `usage_metadata`. Aplica a los 4 endpoints IA; responde 429/503 con `Retry-After` |
| Archivado de proyectos | Borrado lógico con `deleted_at`: `GET /archived`, `POST /{id}/restore`, `DELETE /{id}` (soft) y `DELETE /{id}/permanent` |
| Deploy en Render | Soporte de proxy headers vía `FORWARDED_ALLOW_IPS` y puerto dinámico con `PORT` |
| Base de datos | PostgreSQL en Neon (`DATABASE_URL` con `sslmode=require`); `alembic/env.py` importa todos los modelos para que el autogenerate detecte cada tabla |
| Docs nuevas | `rate-limit-gemini-fastapi.md`: guía de defensa en capas para costos de Gemini (tiers gratuitos) |

### 🔎 **RAG de documentos** (rama `feat/rag-documents-backend`, pendiente de merge)

| Tema | Qué hay hoy |
|------|-------------|
| Almacenamiento | `document_chunks` con `pgvector` (`vector(768)`) en Neon; `EmbeddingType` cae a TEXT/JSON en SQLite para los tests |
| Indexado | Celery + Redis (`app/core/celery_app.py`, `app/tasks/rag_tasks.py`); los endpoints extraen el texto y encolan `rag.index_attachment_text` con el texto en el payload, sin bloquear el request |
| Embeddings | `gemini-embedding-001` por defecto, configurable con `AI_MODEL_EMBEDDING`; `output_dimensionality=768` |
| Retrieval | Coseno con pgvector en PostgreSQL y fallback Python/léxico en SQLite; scoped por `project_id` y `attachment_id` |
| Seguridad | Se eliminó la lectura de `file_path` enviado por el cliente; el ownership se valida antes de recuperar fragmentos |
| Backfill | No hay backfill: solo se indexan uploads, reemplazos y guardados del editor posteriores al deploy |

> Nota: `app/api/api_v1/endpoints/collaboration.py`, `search.py`, `export.py` y `documents.py` existen como archivos vacíos sin router cableado; no se documentan como endpoints hasta que se implementen.

## 🛠️ Tecnologías

- **FastAPI** - Framework web moderno y rápido
- **SQLAlchemy** - ORM para manejo de base de datos
- **PostgreSQL (Neon)** - Base de datos principal
- **Pydantic** - Validación de datos y serialización
- **JWT** - Autenticación basada en tokens
- **Alembic** - Migraciones de base de datos
- **Pytest** - Framework de testing
- **Docker** - Containerización y desarrollo
- **Google GenAI (Gemini)** - Chat, sugerencias, citaciones y bibliografía
- **pgvector** - Búsqueda vectorial en PostgreSQL para el RAG de documentos
- **Celery + Redis** - Indexado asíncrono de documentos (cola `rag`)
- **limits + Redis (Upstash)** - Cost guard / rate limit de IA con fallback en memoria

## ⚡ Comandos Make

```bash
make help           # Ver todos los comandos disponibles
make setup          # Configuración inicial completa
make dev            # Iniciar servidor de desarrollo
make worker         # Iniciar el worker Celery de indexado RAG
make test           # Ejecutar todas las pruebas
make test-cov       # Pruebas con cobertura HTML
make quality        # format + lint + test
make docker-up      # Levantar servicios con Docker
make docker-logs    # Ver logs en tiempo real
make db-upgrade     # Aplicar migraciones (alembic upgrade head)
```

## 🔗 API Endpoints Destacados

### Sistema

- `GET /` - Mensaje de estado de la API
- `GET /health` - Health check (`status`, `environment`)

### Autenticación

- `POST /api/v1/auth/register` - Registro de usuarios
- `POST /api/v1/auth/login` - Inicio de sesión
- `POST /api/v1/auth/logout` - Cierre de sesión
- `POST /api/v1/auth/refresh` - Refrescar token

### Proyectos (incluye archivado lógico)

- `GET /api/v1/proyectos` - Listar proyectos (con filtros)
- `GET /api/v1/proyectos/search` - Buscar proyectos
- `GET /api/v1/proyectos/archived` - Listar archivados (declarada antes de `/{id}`)
- `POST /api/v1/proyectos` - Crear nuevo proyecto
- `GET /api/v1/proyectos/{id}` - Obtener proyecto específico
- `PUT /api/v1/proyectos/{id}` - Actualizar proyecto
- `DELETE /api/v1/proyectos/{id}` - Archivar (soft delete)
- `POST /api/v1/proyectos/{id}/restore` - Restaurar archivado
- `DELETE /api/v1/proyectos/{id}/permanent` - Eliminado definitivo
- `GET /api/v1/proyectos/{id}/descargar-documento` - Descargar documento del proyecto

### Fases y Tareas

- `GET /api/v1/proyectos/{id}/fases` - Listar fases de un proyecto
- `POST /api/v1/proyectos/{id}/fases` - Crear nueva fase
- `GET /api/v1/fases/{id}/tareas` - Listar tareas de una fase
- `POST /api/v1/fases/{id}/tareas` - Crear nueva tarea
- `PUT /api/v1/tareas/{id}/estado` - Cambiar estado de una tarea

### Documentos y Adjuntos

- `POST /api/v1/adjuntos` - Subir nuevo documento (soporta .pdf, .docx, etc.)
- `GET /api/v1/adjuntos/{id}/download` - Descargar documento
- `GET /api/v1/documentos/{id}/extract-content` - Extraer contenido de .docx a HTML
- `PUT /api/v1/documentos/{id}/content` - Guardar contenido editado y reindexar el RAG
- `GET /api/v1/documentos/{id}/search?q=...&top_k=5` - Búsqueda semántica sobre los fragmentos del documento
- `POST /api/v1/documentos/update-docx` - Actualizar contenido HTML a documento .docx

### Bibliografía

- `GET /api/v1/bibliografias` - Listar referencias (ver `bibliography.py`)
- `POST /api/v1/bibliografias` - Crear referencia
- `PUT /api/v1/bibliografias/{id}` - Actualizar referencia
- `DELETE /api/v1/bibliografias/{id}` - Eliminar referencia

### Asistente IA 🤖 (con cost guard Fase 1)

- `POST /api/v1/proyectos/{id}/ia/sugerencias` - Obtener sugerencias de autocompletado para textos
- `POST /api/v1/proyectos/{id}/chat` - Chat interactivo y contextual con IA (con memoria)
- `POST /api/v1/proyectos/{id}/ia/bibliografias` - Buscar y sugerir referencias bibliográficas reales (Formato JSON y verificado)
- `POST /api/v1/proyectos/{id}/ia/citaciones` - Formatear citas según norma APA 7
- `GET /api/v1/proyectos/{id}/conversaciones` - Listar historial de conversaciones del chat

## 📚 Documentación Completa

- **🔧 [Configuración Detallada](docs/SETUP.md)** - Instalación paso a paso, prerrequisitos
- **🧪 [Testing Básico](docs/TESTING.md)** - Tests rápidos con SQLite para desarrollo
- **🐘 [Testing PostgreSQL](docs/TESTING_POSTGRESQL.md)** - Testing avanzado y CI/CD
- **✅ [Calidad de Código](docs/RUN_WITH_VALIDATION.md)** - Linting, format, security
- **💸 [Costos Gemini (guía)](rate-limit-gemini-fastapi.md)** - Rate limit y topes de gasto con `limits` + Redis
- **🌐 [API Interactiva](http://localhost:8000/docs)** - Swagger UI (cuando esté corriendo)
- **📖 [API Alternativa](http://localhost:8000/redoc)** - ReDoc (documentación elegante)

Variables nuevas en `.env.example`: `RATE_LIMIT_REDIS_URL`, `RATE_LIMIT_ENABLED`, `GEMINI_GLOBAL_TOKENS_DAY`, `FORWARDED_ALLOW_IPS`, `AI_MODEL_*`, `AI_MODEL_EMBEDDING`, `CELERY_BROKER_URL`, `CELERY_RESULT_BACKEND`, `RAG_INDEXING_ENABLED`, `DATABASE_URL` (Neon).

### Despliegue del worker RAG en Render

1. La rama debe estar publicada en GitHub para que Render pueda crear el servicio desde el repo/rama.
2. Crear un **Background Worker** con el mismo repo/rama y el mismo build que la API.
3. Start command:
   ```bash
   celery -A app.core.celery_app.celery_app worker --loglevel=info --concurrency=2 -Q rag
   ```
4. Variables recomendadas en el worker y la API:
   - `CELERY_BROKER_URL` y `CELERY_RESULT_BACKEND`: Render Key Value (Redis) o Upstash con TLS (`rediss://...`). No reutilizar el Redis del cost guard si se quiere aislar el tráfico.
   - `RAG_INDEXING_ENABLED=true`
   - `AI_MODEL_EMBEDDING=gemini-embedding-001`
   - `GOOGLE_AI_API_KEY`, `DATABASE_URL`, `SECRET_KEY` (las mismas de la API).
5. **Almacenamiento**: el pipeline por defecto extrae el texto en la API y lo envía en el payload de Celery (`rag.index_attachment_text`), por lo que el worker **no necesita** acceder a `uploads/` ni compartir disco con la API. Si el texto supera 1 MB (`MAX_TASK_TEXT_CHARS`), la extracción falla o queda vacía, se cae a la tarea basada en archivo (`rag.index_attachment`), que sí requiere un disco compartido. Aun así se recomienda object storage (S3/R2) para durabilidad y reindexado.
6. Aplicar la migración en la base de producción/staging: `alembic upgrade head` (la revisión `f3a9c1d7b2e4` crea `document_chunks` y la extensión `vector`).

> **Plan free de Render**: los Background Workers son de pago. Alternativas gratuitas: (a) correr el worker dentro del mismo Web Service free (dos procesos con un supervisor), (b) usar una VM free de Fly.io u Oracle Cloud Always Free, o (c) dejar el worker en local para desarrollo. Con Upstash free los tasks quedan encolados aunque el worker esté dormido y se procesan al despertar; el plan free de Upstash tiene una sola base y solo `db 0`, así que Celery y el cost guard comparten esa base y su cuota (las claves no colisionan).

**Staging con worker local**: dejá la API en Render con `CELERY_BROKER_URL` / `CELERY_RESULT_BACKEND` apuntando a Upstash y corré el worker en tu máquina con un `.env.staging-worker` que apunte `DATABASE_URL` a Neon staging, `CELERY_*` a Upstash, `GOOGLE_AI_API_KEY` al proyecto y `RAG_INDEXING_ENABLED=true`. El worker local no necesita `uploads/` porque la API manda el texto extraído en el payload. Mientras tu máquina esté apagada, los tasks quedan en Upstash.

**Producción free**: Oracle Cloud Always Free (VM ARM) o Fly.io (VM chica) corriendo el mismo comando de worker. Solo necesita salida HTTPS a Neon, Upstash y Google; no abras puertos de entrada más allá de SSH.

**Futuro**: mover `extract_text` y `retrieve_context` de los endpoints `async` a `run_in_threadpool` (ver `odd/tasks/rag-documents-backend.md`) para no bloquear el event loop con documentos grandes o embeddings lentos.

## 🏗️ Arquitectura

**Arquitectura en 4 Capas** (API → Services → Repositories → Models):

- **API**: Endpoints FastAPI con validación Pydantic (`app/api/`)
- **Services**: Lógica de negocio y orquestación (`app/services/`)
- **Repositories**: Acceso a datos y queries optimizadas (`app/repositories/`)
- **Models**: Entidades SQLAlchemy con relaciones (`app/models/`)
- **Tasks**: Cola Celery para indexado RAG (`app/tasks/`) con `app/core/celery_app.py`

Capas transversales: `app/core/` (config, seguridad, `gemini_guard`, prompts IA), `app/middleware/` (logging/tracing) y `app/schemas/`.

## 📊 Métricas del Proyecto (corte 09/11/2026, verificado en el árbol)

- **Endpoints**: 58 decoradores `@router` en `app/` + `GET /` y `GET /health` en `main.py`
- **Modelos**: 10 modelos relacionales (User, Project, Phase, Task, Attachment, Document, DocumentChunk, Bibliography, Conversation, Collaboration)
- **Migraciones**: 9 revisiones Alembic en `alembic/versions/` (incluye `deleted_at`, bibliografías y `document_chunks` con pgvector)
- **Tests**: 32 archivos en `tests/`; **551 tests ejecutados** en la última corrida local (incluye 27 tests RAG en `tests/test_rag_service.py`; unitarios, API, servicios e integración)
- **Cobertura**: pendiente de reporte en este corte (sin número verificado; no se afirma el >85% anterior)

## 🤝 Contribuir

1. Fork el proyecto
2. Crear rama para feature (`git checkout -b feature/AmazingFeature`)
3. Commit cambios (`git commit -m 'Add AmazingFeature'`)
4. Push a la rama (`git push origin feature/AmazingFeature`)
5. Abrir Pull Request

**Antes de hacer commit**: `make quality`

---

**📅 Última actualización**: 9 de noviembre de 2026
**🚀 Estado**: `develop` con Sprints 1–3, Fase 1 del cost guard de Gemini y archivado de proyectos mergeados (PR #32, `226b520`). La rama `feat/rag-documents-backend` agrega RAG de documentos con pgvector + Celery/Redis y está pendiente de PR/merge.
**🎯 Próximo hito**: Configurar el worker Celery en Render, evaluar object storage para durabilidad/reindexado, y luego abrir el PR de la rama RAG. Exportación a PDF/bibliografía sigue pospuesta (TBD).
