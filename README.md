# InvestiFlow API

API REST desarrollada con FastAPI para la plataforma de gestión de proyectos de investigación InvestiFlow.

## 🚀 Inicio Rápido

### Opción 1: Docker (Recomendado) 🐳

```bash
git clone https://github.com/jhobahego/api-investi-flow.git
cd investi-flow-api

cp .env.example .env # IMPORTANTE: Editar .env con tus configuraciones (DB, secrets, etc.)

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
cp .env.example .env # IMPORTANTE: Configurar PostgreSQL y editar .env con tus datos de BD
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

## 🛠️ Tecnologías

- **FastAPI** - Framework web moderno y rápido
- **SQLAlchemy** - ORM para manejo de base de datos
- **PostgreSQL** - Base de datos principal
- **Pydantic** - Validación de datos y serialización
- **JWT** - Autenticación basada en tokens
- **Alembic** - Migraciones de base de datos
- **Pytest** - Framework de testing
- **Docker** - Containerización y desarrollo

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
```

## 🔗 API Endpoints Destacados

### Autenticación

- `POST /api/v1/auth/register` - Registro de usuarios
- `POST /api/v1/auth/login` - Inicio de sesión
- `POST /api/v1/auth/logout` - Cierre de sesión
- `POST /api/v1/auth/refresh` - Refrescar token

### Proyectos

- `GET /api/v1/proyectos` - Listar y buscar proyectos (con filtros)
- `POST /api/v1/proyectos` - Crear nuevo proyecto
- `GET /api/v1/proyectos/{id}` - Obtener proyecto específico
- `PUT /api/v1/proyectos/{id}` - Actualizar proyecto
- `DELETE /api/v1/proyectos/{id}` - Eliminar proyecto

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

### Asistente IA 🤖

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
- **🌐 [API Interactiva](http://localhost:8000/docs)** - Swagger UI (cuando esté corriendo)
- **📖 [API Alternativa](http://localhost:8000/redoc)** - ReDoc (documentación elegante)

## 🏗️ Arquitectura

**Arquitectura en 4 Capas** (API → Services → Repositories → Models):

- **API**: Endpoints FastAPI con validación Pydantic
- **Services**: Lógica de negocio y orquestación
- **Repositories**: Acceso a datos y queries optimizadas
- **Models**: Entidades SQLAlchemy con relaciones

## 📊 Métricas del Proyecto

- **Endpoints**: 47 endpoints principales implementados
- **Modelos**: 9 modelos relacionales (User, Project, Phase, Task, Attachment, Bibliography, Conversation, etc.)
- **Tests**: Suites exhaustivas probando AI, Auth, Projects, Documents y Utils (>40 tests unitarios y de integración)
- **Cobertura**: >85% código cubierto por tests
- **Migraciones**: 8 migraciones de base de datos ejecutadas en revisiones mediante Alembic

## 🤝 Contribuir

1. Fork el proyecto
2. Crear rama para feature (`git checkout -b feature/AmazingFeature`)
3. Commit cambios (`git commit -m 'Add AmazingFeature'`)
4. Push a la rama (`git push origin feature/AmazingFeature`)
5. Abrir Pull Request

**Antes de hacer commit**: `make quality`

---

**📅 Última actualización**: 19 de marzo de 2026
**🚀 Estado**: Todos los sprints (1, 2, y 3) han sido completados exitosamente. Las integraciones de IA (módulo principal del Sprint 3) ya están activas en producción.
**🎯 Próximo hito**: Refinamiento general, corrección de bugs menores y soporte a exportación de bibliografía o PDF pospuestos para un futuro release (TBD).
