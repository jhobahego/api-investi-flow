# 🐘 Testing Avanzado con PostgreSQL - InvestiFlow API

Esta guía cubre el testing avanzado usando PostgreSQL real, ideal para validación completa antes de hacer merge o deploy.

## 🎯 ¿Cuándo usar PostgreSQL para testing?

### ✅ Tests con PostgreSQL cuando:
- **Antes de merge** a rama principal
- **Testing de migraciones** reales de Alembic
- **CI/CD pipeline** completo
- **Queries específicas** de PostgreSQL (JSON, arrays, etc.)
- **Testing de rendimiento** con volumen de datos real
- **Validación final** antes de deploy

### ⚡ Tests con SQLite para:
- **Desarrollo diario** y TDD
- **Tests rápidos** de lógica de negocio
- **Feedback inmediato** durante coding
- Ver: [`docs/TESTING.md`](./TESTING.md)

## 🐳 Configuración con Docker

### 1. Levantar PostgreSQL para testing
```bash
# Usando Make (recomendado)
make docker-up

# O usando Docker Compose directamente
docker compose -f docker-compose.test.yml up -d
```

### 2. Verificar que PostgreSQL esté corriendo
```bash
# Verificar contenedor
docker ps

# Verificar conexión
docker compose -f docker-compose.test.yml exec db psql -U postgres -d test_investi_flow_db -c "\dt"
```

### 3. Ejecutar tests con PostgreSQL
```bash
# Tests completos con PostgreSQL
TESTING_DATABASE_URL=postgresql://postgres:postgres@localhost:5433/test_investi_flow_db pytest

# O usando configuración en conftest.py
pytest --postgresql
```

## ⚙️ Configuración de Testing PostgreSQL

### Variables de entorno para testing
```bash
# .env.test (crear si no existe)
TESTING_DATABASE_URL=postgresql://postgres:postgres@localhost:5433/test_investi_flow_db
ENVIRONMENT=testing
SECRET_KEY=test_secret_key_only_for_testing
ACCESS_TOKEN_EXPIRE_MINUTES=30
```

### Configuración en conftest.py
```python
# tests/conftest.py
import os
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Detectar si usar PostgreSQL o SQLite
TESTING_DATABASE_URL = os.getenv(
    "TESTING_DATABASE_URL",
    "sqlite:///:memory:"  # Default a SQLite para velocidad
)

@pytest.fixture(scope="session")
def postgresql_engine():
    """Engine PostgreSQL para tests completos"""
    if not TESTING_DATABASE_URL.startswith("postgresql"):
        pytest.skip("PostgreSQL not configured for testing")

    engine = create_engine(TESTING_DATABASE_URL)

    # Crear todas las tablas
    Base.metadata.create_all(bind=engine)

    yield engine

    # Limpiar después de la sesión
    Base.metadata.drop_all(bind=engine)
    engine.dispose()

@pytest.fixture
def db_postgresql(postgresql_engine):
    """Sesión de base de datos PostgreSQL con rollback automático"""
    connection = postgresql_engine.connect()
    transaction = connection.begin()

    Session = sessionmaker(bind=connection)
    session = Session()

    yield session

    session.close()
    transaction.rollback()
    connection.close()
```

## 🧪 Tests Específicos para PostgreSQL

### 1. Testing de Migraciones
```python
# tests/test_migrations/test_alembic_migrations.py
import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text

def test_migrations_upgrade_downgrade(postgresql_engine):
    """Test que las migraciones se aplican y revierten correctamente"""

    # Configurar Alembic para testing
    alembic_cfg = Config("alembic.ini")
    alembic_cfg.set_main_option("sqlalchemy.url", str(postgresql_engine.url))

    # Aplicar todas las migraciones
    command.upgrade(alembic_cfg, "head")

    # Verificar que las tablas existen
    with postgresql_engine.connect() as conn:
        result = conn.execute(text("SELECT tablename FROM pg_tables WHERE schemaname = 'public'"))
        tables = [row[0] for row in result]

        assert "users" in tables
        assert "projects" in tables
        assert "alembic_version" in tables

    # Revertir migraciones
    command.downgrade(alembic_cfg, "base")

    # Verificar que las tablas se eliminaron (excepto alembic_version)
    with postgresql_engine.connect() as conn:
        result = conn.execute(text("SELECT tablename FROM pg_tables WHERE schemaname = 'public'"))
        tables = [row[0] for row in result]

        assert "users" not in tables
        assert "projects" not in tables
```

### 2. Testing de Queries Específicas de PostgreSQL
```python
# tests/test_postgresql_features/test_json_queries.py
def test_user_profile_json_queries(db_postgresql):
    """Test queries con campos JSON específicos de PostgreSQL"""

    # Crear usuario con datos JSON complejos
    user_data = {
        "email": "test@example.com",
        "full_name": "Test User",
        "hashed_password": "hashed",
        "metadata": {  # Campo JSON
            "preferences": {"theme": "dark", "language": "es"},
            "analytics": {"last_login": "2025-08-15", "login_count": 42}
        }
    }

    user = User(**user_data)
    db_postgresql.add(user)
    db_postgresql.commit()

    # Query usando operadores JSON de PostgreSQL
    result = db_postgresql.query(User).filter(
        User.metadata["preferences"]["theme"].astext == "dark"
    ).first()

    assert result is not None
    assert result.email == "test@example.com"
```

### 3. Testing de Rendimiento con Volumen
```python
# tests/test_performance/test_bulk_operations.py
import pytest
from time import time

@pytest.mark.slow
def test_bulk_project_creation(db_postgresql, authenticated_user):
    """Test creación masiva de proyectos"""

    projects_count = 1000
    start_time = time()

    # Crear proyectos en lotes
    projects = []
    for i in range(projects_count):
        project = Project(
            name=f"Test Project {i}",
            description=f"Description {i}",
            owner_id=authenticated_user.id
        )
        projects.append(project)

    # Insert en lote
    db_postgresql.bulk_save_objects(projects)
    db_postgresql.commit()

    end_time = time()
    duration = end_time - start_time

    # Verificar rendimiento
    assert duration < 5.0, f"Bulk insert took {duration:.2f}s, expected < 5s"

    # Verificar que se crearon todos
    count = db_postgresql.query(Project).filter(
        Project.owner_id == authenticated_user.id
    ).count()
    assert count == projects_count
```

## 🚀 Comandos y Scripts

### Script para testing PostgreSQL
```bash
#!/bin/bash
# scripts/test_postgresql.sh

echo "🐘 Iniciando testing con PostgreSQL..."

# Levantar PostgreSQL
echo "📦 Levantando PostgreSQL..."
docker compose -f docker-compose.test.yml up -d

# Esperar a que PostgreSQL esté listo
echo "⏳ Esperando PostgreSQL..."
sleep 5

# Ejecutar tests
echo "🧪 Ejecutando tests..."
TESTING_DATABASE_URL=postgresql://postgres:postgres@localhost:5433/test_investi_flow_db \
pytest tests/ -v --tb=short

# Guardar resultado
TEST_RESULT=$?

# Limpiar
echo "🧹 Limpiando containers..."
docker compose -f docker-compose.test.yml down -v

echo "✅ Testing PostgreSQL completado"
exit $TEST_RESULT
```

### Makefile targets para PostgreSQL
```makefile
# En Makefile (agregar estos targets)

test-postgresql: ## Ejecutar tests con PostgreSQL real
	@echo "🐘 Testing with PostgreSQL..."
	docker compose -f docker-compose.test.yml up -d
	@sleep 5
	TESTING_DATABASE_URL=postgresql://postgres:postgres@localhost:5433/test_investi_flow_db \
	$(PYTEST) tests/ -v
	docker compose -f docker-compose.test.yml down -v

test-migrations: ## Test de migraciones con PostgreSQL
	@echo "🔄 Testing Alembic migrations..."
	docker compose -f docker-compose.test.yml up -d
	@sleep 5
	TESTING_DATABASE_URL=postgresql://postgres:postgres@localhost:5433/test_investi_flow_db \
	$(PYTEST) tests/test_migrations/ -v
	docker compose -f docker-compose.test.yml down -v

test-performance: ## Tests de rendimiento con PostgreSQL
	@echo "⚡ Performance testing..."
	docker compose -f docker-compose.test.yml up -d
	@sleep 5
	TESTING_DATABASE_URL=postgresql://postgres:postgres@localhost:5433/test_investi_flow_db \
	$(PYTEST) tests/test_performance/ -v -m "not slow"
	docker compose -f docker-compose.test.yml down -v
```

## 📊 CI/CD con PostgreSQL

### GitHub Actions workflow
```yaml
# .github/workflows/test-postgresql.yml
name: Tests with PostgreSQL

on:
  pull_request:
    branches: [main, develop]
  push:
    branches: [main]

jobs:
  test-postgresql:
    runs-on: ubuntu-latest

    services:
      postgres:
        image: postgres:13
        env:
          POSTGRES_PASSWORD: postgres
          POSTGRES_DB: test_investi_flow_db
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
        ports:
          - 5432:5432

    steps:
    - uses: actions/checkout@v3

    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'

    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements.txt

    - name: Run tests with PostgreSQL
      env:
        TESTING_DATABASE_URL: postgresql://postgres:postgres@localhost:5432/test_investi_flow_db
      run: |
        pytest tests/ -v --cov=app --cov-report=xml

    - name: Upload coverage
      uses: codecov/codecov-action@v3
      with:
        file: ./coverage.xml
```

## 🔍 Debugging con PostgreSQL

### Conectar directamente a la base de datos de test
```bash
# Conectar al container PostgreSQL
docker compose -f docker-compose.test.yml exec db psql -U postgres -d test_investi_flow_db

# Ver todas las tablas
\dt

# Ver contenido de una tabla
SELECT * FROM users LIMIT 5;

# Ver queries lentas
SELECT query, mean_time, calls
FROM pg_stat_statements
ORDER BY mean_time DESC LIMIT 10;
```

### Logs de PostgreSQL
```bash
# Ver logs del container
docker compose -f docker-compose.test.yml logs db

# Seguir logs en tiempo real
docker compose -f docker-compose.test.yml logs -f db
```

## 🎯 Estrategia de Testing Híbrida

### Flujo recomendado:

#### 1. Desarrollo diario (Rápido)
```bash
# Tests rápidos con SQLite
make test
```

#### 2. Antes de commit (Intermedio)
```bash
# Calidad + tests básicos
make quality
```

#### 3. Antes de merge (Completo)
```bash
# Tests completos con PostgreSQL
make test-postgresql
```

#### 4. CI/CD (Exhaustivo)
- Tests con PostgreSQL
- Tests de migraciones
- Tests de rendimiento
- Cobertura de código

## 🛠️ Troubleshooting PostgreSQL

### PostgreSQL no inicia
```bash
# Verificar si el puerto está ocupado
lsof -i :5433

# Limpiar containers anteriores
docker compose -f docker-compose.test.yml down -v --remove-orphans

# Verificar logs
docker compose -f docker-compose.test.yml logs db
```

### Tests fallan con PostgreSQL pero pasan con SQLite
```bash
# Ejecutar test específico con más información
TESTING_DATABASE_URL=postgresql://... pytest tests/test_specific.py -v -s --tb=long

# Verificar diferencias en schemas
docker compose -f docker-compose.test.yml exec db psql -U postgres -d test_investi_flow_db -c "\d users"
```

### Problemas de rendimiento
```bash
# Analizar queries lentas
TESTING_DATABASE_URL=postgresql://... pytest tests/ --postgresql-log-queries

# Configurar PostgreSQL para desarrollo
# En docker-compose.test.yml, agregar:
# command: postgres -c log_statement=all -c log_min_duration_statement=100
```

## 📈 Métricas y Monitoreo

### Reporte de cobertura con PostgreSQL
```bash
# Generar reporte específico para PostgreSQL
TESTING_DATABASE_URL=postgresql://... pytest --cov=app --cov-report=html --cov-branch
```

### Análisis de rendimiento
```bash
# Profile de tests con PostgreSQL
TESTING_DATABASE_URL=postgresql://... pytest --profile tests/
```

---

**Testing básico y rápido**: Ver [`docs/TESTING.md`](./TESTING.md)
**Configuración inicial**: Ver [`docs/SETUP.md`](./SETUP.md)

**Última actualización**: 15 de agosto de 2025
