# Proposal

## Why

El repositorio todavía no tiene código: no hay backend, ni base de datos levantable, ni forma de correr tests. Todo el camino crítico (`C-02 → C-03 → ...`) necesita una base común —estructura en capas, configuración por entorno, PostgreSQL con `btree_gist` y un harness de pytest contra una BD real— para poder trabajar con TDD estricto desde el primer change de dominio. Además, la consigna exige que el repo sea testeable siguiendo solo el README.

## What Changes

- Estructura de backend en capas: `backend/app/{domain,application,infrastructure,api}` y `backend/tests/` (con `unit/` e `integration/`).
- `backend/pyproject.toml` con dependencias: FastAPI, Uvicorn, Pydantic v2 + pydantic-settings, SQLAlchemy 2, Alembic, psycopg 3; dependencias de desarrollo: pytest, httpx, ruff.
- `docker-compose.yml` con servicios `db` (PostgreSQL), `redis` y `api`; script de init que crea la BD de test.
- `.env.example` versionado (DATABASE_URL, TEST_DATABASE_URL, REDIS_URL, JWT_SECRET placeholder, JWT_EXPIRE_MINUTES, APP_TIMEZONE, NOTIFICATION_ADAPTER, CORS_ORIGINS); `.env` ignorado. Se corrige `.gitignore`, que hoy ignora `.env.*` y por lo tanto también `.env.example`.
- Configuración tipada leída de variables de entorno (Pydantic Settings), con fallo explícito si falta una variable obligatoria.
- Endpoint `GET /health` que informa el estado de la API y de la conexión a la base.
- Alembic inicializado con la migración `001` que ejecuta `CREATE EXTENSION IF NOT EXISTS btree_gist`.
- Harness de tests: fixtures de engine/sesión contra PostgreSQL real con rollback por test, marker `integration`, tests de humo de `/health`, conexión a BD y presencia de `btree_gist`.
- Utilidad de tiempo: normaliza a UTC para persistir, convierte a `America/Argentina/Buenos_Aires` para presentar y rechaza datetimes sin zona horaria.
- Sección del README: cómo levantar la BD con Docker Compose, crear el venv con pip, aplicar migraciones y correr los tests.

**Fuera de alcance**: modelos de dominio y seed (C-02), autenticación/JWT (C-06), lógica de worker/cola Redis (C-12), cualquier endpoint distinto de `/health`, frontend.

## Capabilities

### New Capabilities
- `service-health`: chequeo de salud de la API y de su conectividad con PostgreSQL vía `GET /health`.
- `app-configuration`: carga y validación de la configuración de la aplicación desde variables de entorno, sin secretos en el repo.
- `database-baseline`: esquema base versionado con Alembic, incluyendo la extensión `btree_gist` requerida por las futuras restricciones de exclusión.
- `datetime-handling`: política de tiempo del sistema: persistencia en UTC, presentación en `America/Argentina/Buenos_Aires` y rechazo de datetimes sin zona.

### Modified Capabilities
- (ninguna; `openspec/specs/` está vacío)

## Impact

- **Código nuevo**: `backend/` completo (app, tests, `alembic/`, `alembic.ini`, `pyproject.toml`, `Dockerfile`).
- **Infra**: `docker-compose.yml`, script de init de PostgreSQL, `.env.example`.
- **Archivos modificados**: `.gitignore` (permitir `.env.example`, ignorar `.venv/`, `__pycache__/`, caches de pytest/ruff), `README.md` (sección de ejecución y tests).
- **Dependencias externas**: imágenes Docker de PostgreSQL y Redis; Python 3.13 local con `venv` + `pip` (no se usa `uv`).
- **Reglas cubiertas**: RN-CU-02 (sin datos reales), RN-CU-03 (sin secretos, `.env.example`), RN-CU-04 (UTC / Buenos Aires).
- **Habilita**: C-02 (modelos + seed) y, transitivamente, C-03 (restricción de exclusión con `btree_gist`).
