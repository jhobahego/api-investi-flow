# 🔧 Guía Completa de Configuración - InvestiFlow API

Esta guía te llevará paso a paso para configurar el entorno de desarrollo de InvestiFlow API en tu máquina local.

## 📋 Prerrequisitos

### Para Desarrollo Local
- **Python 3.11+** (con pip)
- **PostgreSQL 12+**
- **Git**
- **Make** (para usar comandos automatizados)

### Para Docker (Recomendado)
- **Docker Engine 20.10+**
- **Docker Compose V2** (incluido con Docker Desktop)

## 🐳 Instalación de Docker

### 🐧 Linux
- Seguir la [guía oficial de Docker Desktop para Linux](https://docs.docker.com/desktop/setup/install/linux/)
- O instalar Docker Engine: [Instrucciones para Ubuntu](https://docs.docker.com/engine/install/ubuntu/)

### 🪟 Windows
- Descargar [Docker Desktop para Windows](https://docs.docker.com/desktop/install/windows-install/)
- Seguir la [guía de instalación oficial](https://docs.docker.com/desktop/setup/install/windows-install/)

### 🍎 macOS
- Descargar [Docker Desktop para Mac](https://docs.docker.com/desktop/install/mac-install/)
- Seguir la [guía de instalación oficial](https://docs.docker.com/desktop/setup/install/mac-install/)

### ✅ Verificar instalación Docker
```bash
docker --version
docker compose version
```

## 🚀 Métodos de Instalación

### Opción 1: Usando Make (Recomendado) ⚡

#### 1. Clonar el repositorio
```bash
git clone https://github.com/jhobahego/api-investi-flow.git
cd investi-flow-api
```

#### 2. Crear entorno virtual
```bash
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# .venv\Scripts\activate   # Windows
```

#### 3. Configuración automática
```bash
# Ver todos los comandos disponibles
make help

# Configuración inicial completa
make setup

# Instalar dependencias
make install
```

#### 4. Configurar variables de entorno
```bash
cp .env.example .env
# Editar .env con tu configuración
```

#### 5. Iniciar con Docker
```bash
# Construir y levantar servicios
make docker-up

# Ver logs en tiempo real
make docker-logs
```

#### 6. O iniciar en modo desarrollo local
```bash
# Aplicar migraciones
make db-upgrade

# Iniciar servidor de desarrollo
make dev
```

### Opción 2: Instalación Manual 🛠️

#### 1. Clonar y configurar entorno
```bash
git clone https://github.com/jhobahego/api-investi-flow.git
cd investi-flow-api
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# .venv\Scripts\activate   # Windows
```

#### 2. Instalar dependencias
```bash
pip install -r requirements.txt
```

#### 3. Configurar variables de entorno
```bash
cp .env.example .env
```

Editar el archivo `.env` con tu configuración:
```env
# Base de datos
DATABASE_URL=postgresql://usuario:contraseña@localhost/investi_flow_db

# JWT
SECRET_KEY=tu_clave_secreta_muy_segura
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Entorno
ENVIRONMENT=development
PROJECT_NAME=InvestiFlow API

# CORS
BACKEND_CORS_ORIGIN=http://localhost:5173
```

#### 4. Configurar PostgreSQL
```bash
# Crear base de datos
createdb investi_flow_db

# O usando psql
psql -U postgres
CREATE DATABASE investi_flow_db;
\q
```

#### 5. Ejecutar migraciones
```bash
alembic upgrade head
```

#### 6. Iniciar servidor
```bash
uvicorn main:app --reload
```

### Opción 3: Solo Docker (Más Simple) 🐳

#### 1. Clonar y configurar
```bash
git clone https://github.com/jhobahego/api-investi-flow.git
cd investi-flow-api
cp .env.example .env
```

#### 2. Levantar todo con Docker
```bash
docker compose up -d
```

## ⚙️ Configuración Detallada

### Variables de Entorno (.env)

#### Base de Datos
```env
# Para desarrollo local
DATABASE_URL=postgresql://usuario:contraseña@localhost/investi_flow_db

# Para Docker
DATABASE_URL=postgresql://postgres:postgres@db:5432/investi_flow_db
```

#### Seguridad
```env
# Generar una clave secreta segura
SECRET_KEY=openssl rand -hex 32

# Tiempo de expiración del token (en minutos)
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7
```

#### CORS
```env
# URLs permitidas para CORS (separadas por comas)
BACKEND_CORS_ORIGIN=http://localhost:5173
```

#### Entorno
```env
ENVIRONMENT=development
PROJECT_NAME=InvestiFlow API
API_V1_STR=/api/v1
```

### Configuración de PostgreSQL

#### Instalación PostgreSQL en diferentes SO

**Ubuntu/Debian:**
```bash
sudo apt update
sudo apt install postgresql postgresql-contrib
sudo systemctl start postgresql
sudo systemctl enable postgresql
```

**macOS (con Homebrew):**
```bash
brew install postgresql
brew services start postgresql
```

**Windows:**
- Descargar desde [postgresql.org](https://www.postgresql.org/download/windows/)

#### Crear usuario y base de datos
```sql
-- Conectar como superusuario
sudo -u postgres psql

-- Crear usuario
CREATE USER investi_user WITH PASSWORD 'tu_contraseña';

-- Crear base de datos
CREATE DATABASE investi_flow_db OWNER investi_user;

-- Otorgar permisos
GRANT ALL PRIVILEGES ON DATABASE investi_flow_db TO investi_user;

-- Salir
\q
```

## 🔍 Verificación de la Instalación

### 1. Verificar servicios
```bash
# API principal
curl http://localhost:8000/health

# Documentación
open http://localhost:8000/docs
```

### 2. Verificar base de datos
```bash
# Conectar a la base de datos
psql -U investi_user -d investi_flow_db

# Verificar tablas
\dt

# Verificar datos de ejemplo
SELECT * FROM users LIMIT 1;
```

### 3. Ejecutar tests
```bash
# Tests básicos
make test

# Tests con cobertura
make test-cov
```

## 🛠️ Solución de Problemas Comunes

### Problemas de Permisos (Linux)
```bash
# Docker permissions
sudo usermod -aG docker $USER
newgrp docker

# PostgreSQL permissions
sudo chmod 755 /var/run/postgresql
```

### Puerto ya en uso
```bash
# Ver qué proceso usa el puerto 8000
lsof -i :8000

# Matar proceso si es necesario
kill -9 PID_DEL_PROCESO

# O usar otro puerto
uvicorn main:app --reload --port 8001
```

### Problemas con migraciones
```bash
# Verificar estado de migraciones
alembic current

# Resetear migraciones (CUIDADO: Borra datos)
make db-reset

# Crear migración manualmente
make db-migrate msg="descripcion_del_cambio"
```

### Variables de entorno no cargadas
```bash
# Verificar que el archivo .env existe
ls -la .env

# Verificar contenido
cat .env

# Reactivar entorno virtual
deactivate
source .venv/bin/activate
```

### Problemas con Docker
```bash
# Limpiar containers y volúmenes
docker compose down -v --remove-orphans

# Rebuild completo
docker compose up --build

# Ver logs de errores
docker compose logs app
```

## 🎯 Próximos Pasos

Una vez configurado el entorno:

1. **Leer documentación de testing**: [`docs/TESTING.md`](./TESTING.md)
2. **Configurar herramientas de calidad**: [`docs/RUN_WITH_VALIDATION.md`](./RUN_WITH_VALIDATION.md)
3. **Testing con PostgreSQL**: [`docs/TESTING_POSTGRESQL.md`](./TESTING_POSTGRESQL.md)
4. **Explorar la API**: `http://localhost:8000/docs`

## 📞 Soporte

Si encuentras problemas no cubiertos en esta guía:
1. Revisar los logs: `make docker-logs` o `docker compose logs`
2. Verificar issues en el repositorio
3. Consultar la documentación oficial de cada herramienta

---

**Última actualización**: 15 de agosto de 2025
