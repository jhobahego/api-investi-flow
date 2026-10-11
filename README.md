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
- **limits + Redis (Upstash)** - Cost guard / rate limit de IA con fallback en memoria

## ⚡ Comandos Make

```bash
make help           # Ver todos los comandos disponibles
make setup          # Configuración inicial completa
make dev            # Iniciar servidor de desarrollo
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

Variables nuevas en `.env.example`: `RATE_LIMIT_REDIS_URL`, `RATE_LIMIT_ENABLED`, `GEMINI_GLOBAL_TOKENS_DAY`, `FORWARDED_ALLOW_IPS`, `AI_MODEL_*`, `DATABASE_URL` (Neon).

## 🏗️ Arquitectura

**Arquitectura en 4 Capas** (API → Services → Repositories → Models):

- **API**: Endpoints FastAPI con validación Pydantic (`app/api/`)
- **Services**: Lógica de negocio y orquestación (`app/services/`)
- **Repositories**: Acceso a datos y queries optimizadas (`app/repositories/`)
- **Models**: Entidades SQLAlchemy con relaciones (`app/models/`)

Capas transversales: `app/core/` (config, seguridad, `gemini_guard`, prompts IA), `app/middleware/` (logging/tracing) y `app/schemas/`.

## 📊 Métricas del Proyecto (corte 11/10/2026, verificado en el árbol)

- **Endpoints**: 57 decoradores `@router` en `app/` + `GET /` y `GET /health` en `main.py`
- **Modelos**: 9 modelos relacionales (User, Project, Phase, Task, Attachment, Document, Bibliography, Conversation, Collaboration)
- **Migraciones**: 8 revisiones Alembic en `alembic/versions/` (incluye `deleted_at` y bibliografías)
- **Tests**: 31 archivos en `tests/` con 546 definiciones `def test_` (unitarios, API, servicios, integración)
- **Cobertura**: pendiente de reporte en este corte (sin número verificado; no se afirma el >85% anterior)

## 🤝 Contribuir

1. Fork el proyecto
2. Crear rama para feature (`git checkout -b feature/AmazingFeature`)
3. Commit cambios (`git commit -m 'Add AmazingFeature'`)
4. Push a la rama (`git push origin feature/AmazingFeature`)
5. Abrir Pull Request

**Antes de hacer commit**: `make quality`

---

**📅 Última actualización**: 11 de octubre de 2026
**🚀 Estado**: `main` sincronizado con `develop` en el merge PR #32 (`226b520`). Sprints 1–3 completados; Fase 1 del cost guard de Gemini y archivado de proyectos ya mergeados.
**🎯 Próximo hito**: Refinamiento general, corrección de bugs menores y soporte a exportación de bibliografía o PDF pospuestos para un futuro release (TBD).
