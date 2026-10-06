# Tasks

> TDD estricto: en cada grupo con comportamiento, el test (RED) va antes del código (GREEN). Todos los comandos Python se corren desde `backend/` con el venv activado. Cerrar cada grupo con `ruff format --check . && ruff check .` sin errores.

## 1. Scaffolding y dependencias

- [x] 1.1 Crear `backend/app/__init__.py` con los paquetes `domain/`, `application/`, `infrastructure/db/`, `api/` (con `__init__.py`) y `backend/tests/{unit,integration}/`; verificar con `ls -R backend` que la estructura coincide con KB 08 §Estructura de directorios
- [x] 1.2 Crear `backend/pyproject.toml` (deps: fastapi, uvicorn, pydantic-settings, sqlalchemy>=2, alembic, psycopg[binary], tzdata; dev: pytest, httpx, ruff; config de ruff py313 y de pytest con marker `integration` y `--strict-markers`); verificar con `python -m venv .venv && pip install -e ".[dev]"` y `pytest --markers` mostrando `integration`
- [x] 1.3 Actualizar `.gitignore` (agregar `!.env.example`, `.venv/`, `__pycache__/`, `.pytest_cache/`, `.ruff_cache/`); verificar con `git check-ignore .env` (ignorado) y `git check-ignore .env.example` (no ignorado)

## 2. Utilidad de tiempo (datetime-handling)

- [x] 2.1 RED: escribir `tests/unit/test_time.py` con los escenarios del spec (BA→UTC, UTC→UTC, UTC→BA, cambio de día, naive al normalizar, naive al presentar); verificar que `pytest tests/unit/test_time.py` falla por import inexistente
- [x] 2.2 GREEN: implementar `app/domain/time.py` (`to_utc`, `to_local`, `NaiveDatetimeError`) usando `zoneinfo`; verificar `pytest tests/unit/test_time.py` en verde
- [x] 2.3 REFACTOR: constante `DEFAULT_TIMEZONE`, type hints completos; verificar tests verdes y ruff limpio

## 3. Configuración (app-configuration)

- [x] 3.1 RED: escribir `tests/unit/test_config.py` (valores del entorno vía `monkeypatch`, defaults `APP_TIMEZONE`/`JWT_EXPIRE_MINUTES`, falta `DATABASE_URL` → error que la menciona, `APP_TIMEZONE=Mars/Olympus` → error); verificar que falla
- [x] 3.2 GREEN: implementar `app/config.py` (`Settings` con pydantic-settings, validador de zona, `get_settings()` cacheado); verificar `pytest tests/unit/test_config.py` en verde
- [x] 3.3 Crear `.env.example` en la raíz con todas las variables (incluyendo `TEST_DATABASE_URL`, `POSTGRES_USER/PASSWORD/DB/PORT`) y placeholders ficticios (`JWT_SECRET=change-me`); verificar con un test unitario `tests/unit/test_env_example.py` que parsea el archivo y comprueba que contiene cada campo de `Settings` y que `JWT_SECRET` es placeholder

## 4. Infraestructura local (Docker Compose)

- [x] 4.1 Crear `docker-compose.yml` con `db` (postgres:16, healthcheck `pg_isready`, volumen, puerto `${POSTGRES_PORT:-5432}`), `redis` (redis:7) y `api` (build `backend/`, depende de `db` healthy); verificar con `docker compose config` sin errores
- [x] 4.2 Crear `docker/postgres/init/01-create-test-db.sql` que crea la BD `turnos_test`; verificar con `docker compose up -d db` y `docker compose exec db psql -U <user> -lqt` listando `turnos` y `turnos_test`
- [x] 4.3 Crear `backend/Dockerfile` (python:3.13-slim, `pip install .`, `uvicorn app.main:app --host 0.0.0.0`); verificar con `docker compose build api` exitoso

## 5. Base de datos y harness (database-baseline)

- [ ] 5.1 Implementar `app/infrastructure/db/session.py` (engine síncrono psycopg, `sessionmaker`, `get_session()` generador para `Depends`); verificar ruff limpio (se ejercita en 5.3)
- [ ] 5.2 Inicializar Alembic en `backend/` (`alembic.ini`, `alembic/env.py` que toma la URL de `Settings` u override `-x db_url`); verificar `alembic current` contra la BD de dev sin error
- [ ] 5.3 RED: escribir `tests/conftest.py` (fixtures `engine` session-scope que corre `alembic upgrade head` sobre `TEST_DATABASE_URL` y falla con mensaje claro si la BD no responde; `db_session` con savepoint + rollback) y `tests/integration/test_database.py` (SELECT 1 + `version()` contiene PostgreSQL; `btree_gist` en `pg_extension`; aislamiento: test A inserta en una tabla creada por el test, test B no la ve); verificar que el test de `btree_gist` falla sin la migración
- [ ] 5.4 GREEN: crear migración `alembic/versions/001_enable_btree_gist.py` (revision `"001"`, upgrade `CREATE EXTENSION IF NOT EXISTS btree_gist`, downgrade `DROP EXTENSION IF EXISTS btree_gist`); verificar `pytest -m integration tests/integration/test_database.py` en verde
- [ ] 5.5 Agregar test de integración de migraciones (upgrade→`current` = `001`, upgrade repetido sin cambios, downgrade base elimina `btree_gist`, re-upgrade); verificar en verde

## 6. Health check (service-health)

- [ ] 6.1 RED: escribir `tests/integration/test_health.py` (200 `{"status":"ok","database":"ok"}`; 503 `{"status":"degraded","database":"unavailable"}` sobreescribiendo la dependencia con un engine a `127.0.0.1:1` y `connect_timeout` bajo, asegurando que el cuerpo no contenga la URL; `GET /turnos` → 404); verificar que falla
- [ ] 6.2 GREEN: implementar `app/infrastructure/db/health.py` (`check_database`), `app/api/health.py` (router) y `app/main.py` (`create_app()` con `lifespan`, incluye router); verificar `pytest -m integration tests/integration/test_health.py` en verde
- [ ] 6.3 REFACTOR: schema Pydantic de respuesta `HealthResponse`; verificar tests verdes y ruff limpio

## 7. README y verificación de punta a punta

- [ ] 7.1 Agregar sección "Cómo correr el backend y los tests" al `README.md` (requisitos: Docker + Python 3.13; `cp .env.example .env`; `docker compose up -d db`; crear venv con `python -m venv .venv` y activación en Windows/Linux; `pip install -e ".[dev]"`; `alembic upgrade head`; `pytest`, `pytest -m "not integration"`; `ruff`; nota sobre `POSTGRES_PORT` ocupado; reemplazar "Tests: Pendiente"); verificar siguiendo el README literalmente desde un clon limpio
- [ ] 7.2 Verificación integral: `docker compose up -d db` + `pytest` completo en verde, `ruff format --check . && ruff check .` limpio y `docker compose up -d api` + `curl http://localhost:8000/health` devuelve `{"status":"ok","database":"ok"}`
