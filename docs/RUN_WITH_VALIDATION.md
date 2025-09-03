# ✅ Validación y Calidad de Código - InvestiFlow API

Esta guía cubre todas las herramientas y procesos para mantener la calidad del código en el proyecto.

## 🎯 Filosofía de Calidad

El proyecto implementa **múltiples capas de validación**:
- **Formateo automático**: Código consistente y legible
- **Linting**: Detección de errores y malas prácticas
- **Type checking**: Validación de tipos con MyPy
- **Testing**: Cobertura completa de funcionalidades
- **Security**: Análisis de vulnerabilidades
- **Pre-commit hooks**: Validación antes de cada commit

## ⚡ Comandos Make para Calidad

### Comandos Principales
```bash
# Ver todos los comandos disponibles
make help

# Ejecutar todas las validaciones de calidad
make quality          # format + lint + test

# Formatear código automáticamente
make format           # black + isort

# Verificar formato sin cambios
make format-check     # útil para CI

# Análisis estático (linting)
make lint             # flake8 + mypy

# Tests con cobertura
make test-cov         # pytest con HTML coverage

# Análisis de seguridad
make security         # safety + bandit
```

### Flujo de Desarrollo Recomendado
```bash
# Durante desarrollo activo
make format           # Formatear frecuentemente

# Antes de commit
make quality          # Verificar todo está bien

# Análisis ocasional
make security         # Verificar vulnerabilidades
```

## 🎨 Formateo de Código

### Black - Formateo de Python
```bash
# Formatear todo el código
make format

# Solo verificar (sin cambios)
black --check app/

# Formatear archivos específicos
black app/models/user.py

# Ver qué cambios haría sin aplicarlos
black --diff app/
```

### isort - Organización de Imports
```bash
# Organizar imports
isort app/

# Solo verificar
isort --check-only app/

# Ver diferencias
isort --diff app/
```

### Configuración Black (.pyproject.toml)
```toml
[tool.black]
line-length = 88
target-version = ['py311']
include = '\.pyi?$'
extend-exclude = '''
/(
  # directories
  \.eggs
  | \.git
  | \.hg
  | \.mypy_cache
  | \.tox
  | \.venv
  | build
  | dist
)/
'''
```

### Configuración isort (.pyproject.toml)
```toml
[tool.isort]
profile = "black"
multi_line_output = 3
line_length = 88
known_first_party = ["app"]
known_third_party = ["fastapi", "sqlalchemy", "pydantic"]
```

## 🔍 Linting y Análisis Estático

### Flake8 - Análisis de Código
```bash
# Ejecutar flake8
make lint

# Solo flake8
flake8 app/

# Ignorar errores específicos
flake8 --ignore=E203,W503 app/
```

### MyPy - Type Checking
```bash
# Ejecutar mypy
mypy app/

# Verificar archivo específico
mypy app/models/user.py

# Generar reporte HTML
mypy app/ --html-report mypy-report/
```

### Configuración Flake8 (setup.cfg)
```ini
[flake8]
max-line-length = 88
extend-ignore =
    E203,  # whitespace before ':'
    W503,  # line break before binary operator
    F401,  # imported but unused (handled by isort)
exclude =
    .git,
    __pycache__,
    .venv,
    build,
    dist,
    *.egg-info
per-file-ignores =
    __init__.py:F401
    tests/*:S101  # assert statements ok in tests
```

### Configuración MyPy (mypy.ini)
```ini
[mypy]
python_version = 3.11
warn_return_any = True
warn_unused_configs = True
disallow_untyped_defs = True
disallow_incomplete_defs = True
check_untyped_defs = True
disallow_untyped_decorators = True
no_implicit_optional = True
warn_redundant_casts = True
warn_unused_ignores = True
warn_no_return = True
warn_unreachable = True
strict_equality = True

# Per-module options
[mypy-tests.*]
disallow_untyped_defs = False

[mypy-alembic.*]
ignore_errors = True
```

## 🔒 Análisis de Seguridad

### Safety - Vulnerabilidades en Dependencias
```bash
# Verificar vulnerabilidades conocidas
make security

# Solo safety
safety check

# Verificar requirements.txt específico
safety check -r requirements.txt

# Generar reporte JSON
safety check --json
```

### Bandit - Análisis de Seguridad en Código
```bash
# Análisis completo
bandit -r app/

# Con configuración específica
bandit -r app/ -f json -o bandit-report.json

# Excluir tests
bandit -r app/ --skip B101
```

### Configuración Bandit (.bandit)
```yaml
# .bandit
skips: ['B101', 'B601']  # Skip assert_used_in_tests, shell=True
exclude_dirs: ['tests', 'venv', '.venv']
```

## 🪝 Pre-commit Hooks

### Instalación y Configuración
```bash
# Instalar pre-commit
make pre-commit

# O manualmente
pip install pre-commit
pre-commit install
```

### Configuración (.pre-commit-config.yaml)
```yaml
repos:
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.4.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-added-large-files
      - id: check-merge-conflict

  - repo: https://github.com/psf/black
    rev: 23.3.0
    hooks:
      - id: black
        language_version: python3.11

  - repo: https://github.com/pycqa/isort
    rev: 5.12.0
    hooks:
      - id: isort

  - repo: https://github.com/pycqa/flake8
    rev: 6.0.0
    hooks:
      - id: flake8

  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.3.0
    hooks:
      - id: mypy
        additional_dependencies: [types-requests]
```

### Comandos Pre-commit
```bash
# Ejecutar en todos los archivos
pre-commit run --all-files

# Ejecutar solo en archivos staged
pre-commit run

# Actualizar hooks
pre-commit autoupdate

# Desinstalar hooks
pre-commit uninstall
```

## 📊 Cobertura de Código

### Configuración Coverage (.coveragerc)
```ini
[run]
source = app/
omit =
    app/tests/*
    app/__pycache__/*
    app/*/__pycache__/*
    app/utils/make_superuser.py
    app/utils/seed_database.py

[report]
exclude_lines =
    pragma: no cover
    def __repr__
    if self.debug:
    if settings.DEBUG
    raise AssertionError
    raise NotImplementedError
    if 0:
    if __name__ == .__main__.:

[html]
directory = htmlcov
```

### Comandos de Cobertura
```bash
# Generar reporte HTML
make test-cov

# Solo terminal
pytest --cov=app --cov-report=term-missing

# Generar múltiples formatos
pytest --cov=app --cov-report=html --cov-report=xml --cov-report=term

# Fallar si cobertura < 90%
pytest --cov=app --cov-fail-under=90
```

## 🎯 Integración con IDE

### VS Code Settings (.vscode/settings.json)
```json
{
    "python.formatting.provider": "black",
    "python.linting.enabled": true,
    "python.linting.flake8Enabled": true,
    "python.linting.mypyEnabled": true,
    "python.sortImports.path": "isort",
    "editor.formatOnSave": true,
    "editor.codeActionsOnSave": {
        "source.organizeImports": true
    },
    "python.testing.pytestEnabled": true,
    "python.testing.unittestEnabled": false,
    "python.testing.pytestArgs": [
        "tests"
    ]
}
```

### Extensiones Recomendadas (.vscode/extensions.json)
```json
{
    "recommendations": [
        "ms-python.python",
        "ms-python.flake8",
        "ms-python.mypy-type-checker",
        "ms-python.black-formatter",
        "ms-python.isort",
        "ms-vscode.test-adapter-converter",
        "littlefoxteam.vscode-python-test-adapter"
    ]
}
```

## 🚀 CI/CD y Validación Automática

### GitHub Actions Workflow
```yaml
# .github/workflows/quality.yml
name: Code Quality

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  quality:
    runs-on: ubuntu-latest

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

    - name: Format check
      run: |
        black --check app/
        isort --check-only app/

    - name: Lint
      run: |
        flake8 app/
        mypy app/

    - name: Security check
      run: |
        safety check
        bandit -r app/

    - name: Tests with coverage
      run: |
        pytest --cov=app --cov-report=xml --cov-fail-under=85

    - name: Upload coverage
      uses: codecov/codecov-action@v3
      with:
        file: ./coverage.xml
```

## 🔧 Configuración de Pytest

### pytest.ini
```ini
[tool:pytest]
minversion = 6.0
addopts =
    -ra
    -q
    --strict-markers
    --strict-config
    --disable-warnings
testpaths = tests
python_files = tests/*.py test_*.py *_test.py
python_classes = Test*
python_functions = test_*
markers =
    slow: marks tests as slow (deselect with '-m "not slow"')
    integration: marks tests as integration tests
    unit: marks tests as unit tests
    api: marks tests as API tests
filterwarnings =
    error
    ignore::UserWarning
    ignore::DeprecationWarning
```

## 📈 Métricas de Calidad

### Objetivos del Proyecto
- **Cobertura de código**: > 85%
- **Complejidad ciclomática**: < 10 por función
- **Duplicación de código**: < 3%
- **Vulnerabilidades**: 0 conocidas de alta severidad
- **Type coverage**: > 90%

### Monitoreo Continuo
```bash
# Reporte completo de calidad
make quality > quality-report.txt

# Métricas específicas
pytest --cov=app --cov-report=term | grep TOTAL
flake8 app/ --statistics
mypy app/ --txt-report mypy-report/
```

## 🛠️ Troubleshooting

### Conflictos entre herramientas
```bash
# Black vs Flake8 line length
# Asegurar que ambos usan 88 caracteres

# isort vs Black
# Usar profile = "black" en isort

# MyPy errors en tests
# Configurar [mypy-tests.*] con menos restricciones
```

### Problemas de rendimiento
```bash
# MyPy lento
mypy --cache-dir=.mypy_cache app/

# Pre-commit lento
pre-commit run --hook-stage manual
```

### Falsos positivos
```bash
# Ignorar línea específica
# flake8: noqa
# mypy: type: ignore
# bandit: # nosec

# Configurar en archivos de config para ignorar globalmente
```

## 🎯 Best Practices

### 1. Ejecutar validaciones frecuentemente
```bash
# Durante desarrollo
make format  # Cada vez que guardes cambios importantes

# Antes de commit
make quality  # Siempre antes de git commit
```

### 2. Configurar IDE correctamente
- Formateo automático al guardar
- Linting en tiempo real
- Type hints visibles

### 3. Usar pre-commit hooks
- Previene commits con problemas
- Feedback inmediato
- Mantiene historial limpio

### 4. Monitorear métricas
- Revisar cobertura regularmente
- Atender warnings de seguridad
- Mantener dependencias actualizadas

---

**Testing básico**: Ver [`docs/TESTING.md`](./TESTING.md)
**Testing avanzado**: Ver [`docs/TESTING_POSTGRESQL.md`](./TESTING_POSTGRESQL.md)
**Configuración inicial**: Ver [`docs/SETUP.md`](./SETUP.md)

**Última actualización**: 15 de agosto de 2025
