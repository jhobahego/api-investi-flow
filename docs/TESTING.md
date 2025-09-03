# 🧪 Guía de Testing - InvestiFlow API

Esta guía cubre el testing básico y rápido para desarrollo diario usando SQLite como base de datos de prueba.

## 🎯 Filosofía de Testing

El proyecto utiliza un enfoque de **testing en capas**:
- **Tests unitarios**: Servicios y repositorios individuales
- **Tests de integración**: Endpoints completos con base de datos
- **Tests end-to-end**: Flujos completos de usuario

## ⚡ Testing Rápido (Desarrollo Diario)

### Comandos Make para Testing
```bash
# Ejecutar todas las pruebas
make test

# Pruebas con reporte de cobertura
make test-cov

# Ejecutar solo tests específicos
pytest tests/test_api/test_auth.py

# Ejecutar con salida detallada
pytest -v

# Ejecutar tests que fallan y parar en el primero
pytest -x
```

### Estructura de Tests
```
tests/
├── conftest.py              # Configuración global de pytest
├── factories.py             # Factories para generar datos de prueba
├── test_api/                # Tests de endpoints HTTP
│   ├── test_auth.py         # Tests de autenticación
│   ├── test_projects.py     # Tests de proyectos
│   └── test_users.py        # Tests de usuarios
├── test_models/             # Tests de modelos SQLAlchemy
├── test_schemas/            # Tests de esquemas Pydantic
├── test_services/           # Tests de servicios de negocio
└── test_integration/        # Tests end-to-end
    └── test_research_workflow.py
```

## 🔧 Configuración de Testing

### Fixtures Principales

#### Base de datos de prueba (SQLite)
```python
# En conftest.py
@pytest.fixture
def db():
    """Base de datos SQLite en memoria para tests rápidos"""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    # ... configuración adicional
```

#### Cliente de prueba
```python
@pytest.fixture
def client():
    """Cliente FastAPI para tests de endpoints"""
    with TestClient(app) as client:
        yield client
```

#### Usuario autenticado
```python
@pytest.fixture
def auth_headers(db):
    """Headers con token JWT para tests autenticados"""
    # Crear usuario y generar token
    # Retornar headers con Authorization
```

### Factories para Datos de Prueba

#### Factory de Usuario
```python
# En factories.py
def create_user_factory(**kwargs):
    """Crear usuario de prueba con datos aleatorios"""
    defaults = {
        "email": fake.email(),
        "full_name": fake.name(),
        "password": "TestPassword123!",
        "phone_number": "+573001234567",
        "university": "Universidad de Prueba",
    }
    defaults.update(kwargs)
    return defaults
```

#### Factory de Proyecto
```python
def create_project_factory(**kwargs):
    """Crear proyecto de prueba"""
    defaults = {
        "name": fake.sentence(nb_words=3),
        "description": fake.text(),
        "research_type": "applied",
        "institution": fake.company(),
    }
    defaults.update(kwargs)
    return defaults
```

## 📊 Tipos de Tests

### 1. Tests de Autenticación
```python
# tests/test_api/test_auth.py
def test_register_user_success(client, db):
    """Test registro exitoso de usuario"""
    user_data = create_user_factory()
    response = client.post("/api/v1/auth/register", json=user_data)

    assert response.status_code == 201
    assert "email" in response.json()
    assert response.json()["email"] == user_data["email"]

def test_login_success(client, db, test_user):
    """Test login exitoso"""
    response = client.post("/api/v1/auth/login", data={
        "username": test_user.email,
        "password": "TestPassword123!"
    })

    assert response.status_code == 200
    assert "access_token" in response.json()
    assert response.json()["token_type"] == "bearer"
```

### 2. Tests de Proyectos
```python
# tests/test_api/test_projects.py
def test_create_project(client, auth_headers):
    """Test crear proyecto autenticado"""
    project_data = create_project_factory()
    response = client.post(
        "/api/v1/proyectos",
        json=project_data,
        headers=auth_headers
    )

    assert response.status_code == 201
    assert response.json()["name"] == project_data["name"]

def test_list_user_projects(client, auth_headers, user_projects):
    """Test listar proyectos del usuario"""
    response = client.get("/api/v1/proyectos", headers=auth_headers)

    assert response.status_code == 200
    assert len(response.json()) == len(user_projects)
```

### 3. Tests de Servicios
```python
# tests/test_services/test_user_service.py
def test_create_user_service(db):
    """Test crear usuario via servicio"""
    user_data = UserCreate(**create_user_factory())
    user = user_service.create_user(db, user_data)

    assert user.email == user_data.email
    assert user.hashed_password != user_data.password  # Verificar hash
    assert user.is_active is True
```

## 🏃‍♂️ Ejecutar Tests Específicos

### Por archivo
```bash
# Solo tests de autenticación
pytest tests/test_api/test_auth.py

# Solo tests de proyectos
pytest tests/test_api/test_projects.py

# Solo servicios
pytest tests/test_services/
```

### Por nombre de test
```bash
# Test específico
pytest tests/test_api/test_auth.py::test_register_user_success

# Tests que contengan "login" en el nombre
pytest -k "login"

# Tests que NO contengan "integration"
pytest -k "not integration"
```

### Por marcadores (si están configurados)
```bash
# Solo tests unitarios
pytest -m unit

# Solo tests de API
pytest -m api

# Solo tests rápidos
pytest -m "not slow"
```

## 📈 Reporte de Cobertura

### Generar reporte HTML
```bash
make test-cov
# Abre htmlcov/index.html en el navegador
```

### Ver cobertura en terminal
```bash
pytest --cov=app --cov-report=term-missing
```

### Configuración de cobertura (.coveragerc)
```ini
[run]
source = app/
omit =
    app/tests/*
    app/__pycache__/*
    app/*/__pycache__/*

[report]
exclude_lines =
    pragma: no cover
    def __repr__
    raise AssertionError
    raise NotImplementedError
```

## 🐛 Debugging Tests

### Usar pdb para debugging
```python
def test_complex_logic(client, db):
    import pdb; pdb.set_trace()  # Breakpoint
    # ... código del test
```

### Ejecutar un test en modo debug
```bash
pytest --pdb tests/test_api/test_auth.py::test_register_user_success
```

### Ver output completo (sin captura)
```bash
pytest -s tests/test_api/test_auth.py
```

## ⚡ Tests Rápidos vs Completos

### Tests Rápidos (SQLite)
- **Cuándo usar**: Desarrollo diario, TDD, CI básico
- **Ventajas**: Muy rápidos, sin dependencias externas
- **Limitaciones**: No testa migraciones reales, algunas queries específicas de PostgreSQL

### Tests Completos (PostgreSQL)
- **Cuándo usar**: Antes de merge, testing de migraciones, CI completo
- **Ver**: [`docs/TESTING_POSTGRESQL.md`](./TESTING_POSTGRESQL.md)

## 🎯 Best Practices

### 1. Nomenclatura de Tests
```python
def test_[accion]_[condicion]_[resultado_esperado]:
    """Descripción clara del test"""
    # Arrange - Preparar datos
    # Act - Ejecutar acción
    # Assert - Verificar resultado
```

### 2. Fixtures Reutilizables
```python
@pytest.fixture
def authenticated_user(db):
    """Usuario autenticado reutilizable"""
    user = create_user_in_db(db)
    token = create_access_token(user.email)
    return {"user": user, "token": token}
```

### 3. Tests Independientes
- Cada test debe poder ejecutarse independientemente
- Usar factories para datos únicos
- Limpiar estado después de cada test

### 4. Assertions Claras
```python
# ❌ Malo
assert response.status_code == 200

# ✅ Bueno
assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
```

## 🚀 Integración con Make

### Comandos Make disponibles
```bash
make test           # Tests básicos rápidos
make test-cov       # Tests con cobertura HTML
make quality        # format + lint + test
```

### Flujo de desarrollo recomendado
```bash
# Durante desarrollo
make test           # Ejecutar frecuentemente

# Antes de commit
make quality        # Verificar todo esté bien

# Testing completo (ocasional)
# Ver TESTING_POSTGRESQL.md
```

## 📞 Troubleshooting

### Tests lentos
```bash
# Identificar tests lentos
pytest --durations=10

# Ejecutar solo tests rápidos
pytest -m "not slow"
```

### Problemas con fixtures
```bash
# Ver qué fixtures están disponibles
pytest --fixtures

# Ejecutar con más información
pytest -v --tb=long
```

### Base de datos no se limpia
- Verificar que cada test use la fixture `db` correctamente
- Asegurar que conftest.py configure transacciones rollback

---

**Próximo paso**: Para testing avanzado con PostgreSQL, ver [`docs/TESTING_POSTGRESQL.md`](./TESTING_POSTGRESQL.md)

**Última actualización**: 15 de agosto de 2025
