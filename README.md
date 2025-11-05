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

### 🚧 **Sprint 2 - En Preparación** (16/08/2025 – 03/09/2025)
- 📄 **Gestión de Documentos**: Upload, download, validaciones
- 🔍 **Sistema de Búsqueda**: Proyectos, documentos, filtros

### ⏳ **Sprint 3 - Planificado** (04/09/2025 – 17/09/2025)
- 🤖 **Asistente IA**: Análisis de documentos, chat inteligente
- 📊 **Exportación**: Proyectos a PDF

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

## 🔗 API Endpoints

### Autenticación
- `POST /api/v1/auth/register` - Registro de usuarios
- `POST /api/v1/auth/login` - Inicio de sesión
- `POST /api/v1/auth/logout` - Cierre de sesión

### Proyectos
- `GET /api/v1/proyectos` - Listar proyectos del usuario
- `POST /api/v1/proyectos` - Crear nuevo proyecto
- `GET /api/v1/proyectos/{id}` - Obtener proyecto específico
- `PUT /api/v1/proyectos/{id}` - Actualizar proyecto
- `DELETE /api/v1/proyectos/{id}` - Eliminar proyecto

### Documentos 📄 **NUEVO**
- `GET /api/v1/documentos/{id}/extract-content` - Extraer contenido de .docx a HTML
- `GET /api/v1/documentos/{id}/preview` - Vista previa de documento

### Asistente IA 🤖
- `POST /api/v1/ia/sugerencias` - Obtener sugerencias de IA para documentos

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

- **Endpoints**: 8 endpoints principales implementados
- **Modelos**: 2 modelos principales (User, Project) con relaciones
- **Tests**: 3 suites completas (auth, projects, users)
- **Cobertura**: >85% código cubierto por tests
- **Migraciones**: 3 migraciones de base de datos ejecutadas

## 🤝 Contribuir

1. Fork el proyecto
2. Crear rama para feature (`git checkout -b feature/AmazingFeature`)
3. Commit cambios (`git commit -m 'Add AmazingFeature'`)
4. Push a la rama (`git push origin feature/AmazingFeature`)
5. Abrir Pull Request

**Antes de hacer commit**: `make quality`

---

**📅 Última actualización**: 15 de agosto de 2025
**🚀 Estado**: Sprint 1 Completado - Sistema core funcionando
**🎯 Próximo hito**: Sprint 2 - Documentos y búsqueda (16/08 - 03/09)
