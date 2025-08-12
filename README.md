# InvestiFlow API

API REST desarrollada con FastAPI para la plataforma de gestión de proyectos de investigación InvestiFlow.

## 🏗️ Estructura del Proyecto

```
investi-flow-api/
├── 📁 alembic/                         # Migraciones de base de datos
│   ├── env.py                          # Configuración de entorno Alembic
│   └── versions/                       # Archivos de migración generados
├── 📁 app/                             # Aplicación principal FastAPI
│   ├── 📁 api/                         # Endpoints de la API
│   │   └── api_v1/                     # Versión 1 de la API
│   │       ├── endpoints/              # Controladores HTTP específicos
│   │       │   ├── auth.py             # Autenticación y autorización
│   │       │   ├── users.py            # Gestión de usuarios
│   │       │   ├── projects.py         # Gestión de proyectos
│   │       │   ├── tasks.py            # Gestión de tareas
│   │       │   ├── documents.py        # Gestión de documentos
│   │       │   ├── ai_assistant.py     # Asistente de IA
│   │       │   ├── bibliography.py     # Sistema de bibliografía
│   │       │   ├── search.py           # Búsqueda y filtros
│   │       │   ├── export.py           # Exportación de documentos
│   │       │   └── collaboration.py    # Colaboración y comentarios
│   │       └── api.py                  # Router principal de la API
│   ├── 📁 core/                        # Configuración central
│   │   ├── config.py                   # Configuración y variables de entorno
│   │   └── security.py                 # JWT, hashing, autenticación
│   ├── 📁 models/                      # Modelos SQLAlchemy (base de datos)
│   │   ├── user.py                     # Modelo de usuarios
│   │   ├── project.py                  # Modelo de proyectos
│   │   ├── task.py                     # Modelo de tareas
│   │   ├── document.py                 # Modelo de documentos
│   │   ├── bibliography.py             # Modelo de bibliografía
│   │   └── collaboration.py            # Modelo de colaboración
│   ├── 📁 repositories/                # Lógica de acceso a datos
│   │   ├── base.py                     # Repositorio base
│   │   ├── user_repository.py          # Repositorio de usuarios
│   │   ├── project_repository.py       # Repositorio de proyectos
│   │   ├── task_repository.py          # Repositorio de tareas
│   │   └── document_repository.py      # Repositorio de documentos
│   ├── 📁 schemas/                     # Esquemas Pydantic (validación)
│   │   ├── user.py                     # Esquemas de usuario
│   │   ├── project.py                  # Esquemas de proyecto
│   │   ├── task.py                     # Esquemas de tarea
│   │   ├── document.py                 # Esquemas de documento
│   │   ├── token.py                    # Esquemas de tokens JWT
│   │   └── bibliography.py             # Esquemas de bibliografía
│   ├── 📁 services/                    # Lógica de negocio
│   │   ├── base.py                     # Servicio base
│   │   ├── user_service.py             # Servicios de usuario
│   │   ├── project_service.py          # Servicios de proyecto
│   │   ├── task_service.py             # Servicios de tarea
│   │   ├── document_service.py         # Servicios de documento
│   │   └── ai_service.py               # Servicios de IA
│   ├── 📁 utils/                       # Scripts de utilidad
│   │   ├── make_superuser.py           # Crear superusuarios
│   │   └── seed_database.py            # Poblar base de datos inicial
│   ├── config.py                       # Configuración principal
│   ├── database.py                     # Configuración de SQLAlchemy
│   └── main.py                         # Punto de entrada FastAPI
├── 📁 tests/                           # Suite completa de testing
│   ├── 📁 test_api/                    # Tests de endpoints HTTP
│   │   ├── test_auth.py                # Tests de autenticación
│   │   ├── test_users.py               # Tests de endpoints de usuarios
│   │   ├── test_projects.py            # Tests de endpoints de proyectos
│   │   └── test_tasks.py               # Tests de endpoints de tareas
│   ├── 📁 test_integration/            # Tests de flujos completos
│   │   └── test_research_workflow.py   # Tests de flujos E2E
│   ├── 📁 test_models/                 # Tests de modelos SQLAlchemy
│   ├── 📁 test_schemas/                # Tests de esquemas Pydantic
│   ├── 📁 test_services/               # Tests de servicios de negocio
│   ├── conftest.py                     # Configuración de pytest y fixtures
│   └── factories.py                    # Factories para generación de datos
├── 📁 scripts/                         # Scripts de automatización
├── 📁 docs/                            # Documentación completa del proyecto
│   ├── SETUP.md                        # Guía detallada de configuración inicial
│   ├── TESTING.md                      # Guía completa de testing
│   ├── TESTING_POSTGRESQL.md           # Testing avanzado con PostgreSQL
│   └── RUN_WITH_VALIDATION.md          # Ejecución con validación automática
├── 📁 uploads/                         # Archivos subidos por usuarios
│   ├── documents/                      # Documentos permanentes
│   └── temp/                          # Archivos temporales
├── 🐳 docker-compose.yml               # Servicios principales (desarrollo)
├── 🐳 docker-compose.test.yml          # PostgreSQL para testing
├── 🐳 Dockerfile                       # Imagen Docker de la aplicación
├── 📋 Makefile                         # Comandos de automatización y desarrollo
├── 📋 alembic.ini                      # Configuración principal de Alembic
├── 📦 requirements.txt                 # Dependencias principales del proyecto
├── 🔧 .env                             # Variables de entorno (no en git)
├── 🔧 .env.example                     # Ejemplo de configuración
├── 🔧 .gitignore                       # Archivos ignorados por Git
├── 🔧 pytest.ini                       # Configuración de pytest
├── 📖 README.md                        # Esta documentación
└── 📖 TAREAS_BACKEND.md                # Lista de tareas pendientes del backend
```

## 🚀 Tecnologías Utilizadas

- **FastAPI**: Framework web moderno y rápido para construir APIs
- **SQLAlchemy**: ORM para manejo de base de datos
- **PostgreSQL**: Base de datos principal
- **Pydantic**: Validación de datos y serialización
- **JWT**: Autenticación basada en tokens
- **Alembic**: Migraciones de base de datos
- **Pytest**: Framework de testing
- **Uvicorn**: Servidor ASGI para FastAPI

## 🎯 Arquitectura por Capas

### 🌐 **Capa de API (app/api/)**
- **Endpoints**: Controladores HTTP que reciben requests y devuelven responses
- **Validación**: Validación de entrada usando schemas Pydantic
- **Documentación**: Auto-generación con OpenAPI/Swagger

### 🏢 **Capa de Servicios (app/services/)**
- **Lógica de Negocio**: Reglas y validaciones específicas del dominio
- **Orquestación**: Coordinación entre múltiples repositorios
- **Transacciones**: Manejo de operaciones complejas

### 🗃️ **Capa de Repositorios (app/repositories/)**
- **Acceso a Datos**: Operaciones CRUD con la base de datos
- **Abstracción**: Interfaz entre servicios y modelos
- **Consultas**: Queries optimizadas y reutilizables

### 📊 **Capa de Modelos (app/models/)**
- **Entidades**: Representación de tablas de base de datos
- **Relaciones**: Definición de FK y relaciones entre entidades
- **Validaciones**: Constraints a nivel de base de datos

### 🔧 **Capa de Configuración (app/core/)**
- **Configuración**: Variables de entorno y settings
- **Seguridad**: Autenticación, autorización y hashing
- **Database**: Configuración de conexión a BD

## 📋 Estado Actual

### ✅ Completado
- [x] Estructura de carpetas del proyecto
- [x] Configuración de dependencias
- [x] Archivos de configuración básicos
- [x] Arquitectura por capas definida

### 🚧 En Desarrollo
- [ ] Configuración de base de datos
- [ ] Sistema de autenticación
- [ ] CRUD de proyectos
- [ ] Gestión de documentos

## 🔧 Configuración

1. **Clonar el repositorio**
2. **Crear entorno virtual**: `python -m venv venv`
3. **Activar entorno virtual**: `source venv/bin/activate` (Linux/Mac) o `venv\Scripts\activate` (Windows)
4. **Instalar dependencias**: `pip install -r requirements.txt`
5. **Configurar variables de entorno**: Copiar `.env.example` a `.env`
6. **Configurar base de datos PostgreSQL**
7. **Ejecutar migraciones**: `alembic upgrade head`
8. **Iniciar servidor**: `uvicorn app.main:app --reload`

## 📚 Documentación

- **API Docs**: `http://localhost:8000/docs` (Swagger UI)
- **ReDoc**: `http://localhost:8000/redoc`
- **Configuración**: Ver `docs/SETUP.md`
- **Testing**: Ver `docs/TESTING.md`
- **Tareas Pendientes**: Ver `TAREAS_BACKEND.md`

## 🧪 Testing

```bash
# Ejecutar todas las pruebas
pytest

# Ejecutar con cobertura
pytest --cov=app

# Ejecutar pruebas específicas
pytest tests/test_api/test_auth.py

# Ejecutar tests de integración
pytest tests/test_integration/
```

## 🐳 Docker

```bash
# Desarrollo
docker-compose up -d

# Testing con PostgreSQL
docker-compose -f docker-compose.test.yml up -d

# Build de la aplicación
docker build -t investi-flow-api .
```

## 🚀 Deployment

(Instrucciones de deployment se añadirán cuando el proyecto esté listo)

---

**Última actualización**: 12 de agosto de 2025  
**Estado**: Estructura inicial creada con arquitectura por capas  
**Arquitectura**: Layered Architecture (API → Services → Repositories → Models)
