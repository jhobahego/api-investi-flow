# Variables
PYTHON = .venv/bin/python
PIP = .venv/bin/pip
UVICORN = .venv/bin/uvicorn
PYTEST = .venv/bin/pytest
BLACK = .venv/bin/black
ISORT = .venv/bin/isort
FLAKE8 = .venv/bin/flake8
MYPY = .venv/bin/mypy
ALEMBIC = .venv/bin/alembic

.PHONY: help install dev lint format test clean docker-build docker-up docker-down

help: ## Mostrar ayuda
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}'

install: ## Instalar dependencias
	$(PIP) install -r requirements.txt

dev: ## Ejecutar en modo desarrollo
	$(UVICORN) main:app --reload --host 0.0.0.0 --port 8000

lint: ## Ejecutar linting (flake8 y mypy)
	$(FLAKE8) app/
	$(MYPY) app/

format: ## Formatear código
	$(BLACK) app/
	$(ISORT) app/

format-check: ## Verificar formato sin cambios
	$(BLACK) --check app/
	$(ISORT) --check-only app/

test: ## Ejecutar pruebas
	$(PYTEST) -v

test-cov: ## Ejecutar pruebas con cobertura
	$(PYTEST) --cov=app --cov-report=html --cov-report=term-missing

clean: ## Limpiar archivos temporales
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	find . -type d -name ".mypy_cache" -exec rm -rf {} +

# Docker commands
docker-build: ## Construir imagen Docker
	docker compose build

docker-up: ## Iniciar servicios con Docker
	docker compose up -d

docker-down: ## Detener servicios Docker
	docker compose down

docker-logs: ## Ver logs de Docker
	docker compose logs -f

# Database commands
db-upgrade: ## Aplicar migraciones de base de datos
	$(ALEMBIC) upgrade head

db-downgrade: ## Revertir última migración
	$(ALEMBIC) downgrade -1

db-migrate: ## Crear nueva migración
	$(ALEMBIC) revision --autogenerate -m "$(msg)"

db-reset: ## Resetear base de datos (cuidado!)
	$(ALEMBIC) downgrade base
	$(ALEMBIC) upgrade head

# Development setup
setup: ## Configuración inicial del proyecto
	$(PIP) install -r requirements.txt
	$(PIP) install pre-commit
	.venv/bin/pre-commit install
	mkdir -p uploads/documents uploads/temp

pre-commit: ## Instalar pre-commit hooks
	$(PIP) install pre-commit
	.venv/bin/pre-commit install

# Quality checks
quality: format lint test ## Ejecutar todas las verificaciones de calidad

# Security
security: ## Verificar vulnerabilidades de seguridad
	$(PIP) install safety bandit
	.venv/bin/safety check
	.venv/bin/bandit -r app/
