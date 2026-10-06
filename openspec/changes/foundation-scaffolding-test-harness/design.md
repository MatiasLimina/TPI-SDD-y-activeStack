# Design

## Context

Repo greenfield: solo documentación (`knowledge-base/`, `CHANGES.md`, `openspec/`). Ver proposal.md (Why). Restricciones que moldean el diseño:

- Entorno del equipo: Windows, Python 3.13 local, Docker Compose disponible, **sin `uv`** (se usa `python -m venv` + `pip`).
- Reglas duras: PostgreSQL real en tests (nada de SQLite ni mocks), datetimes siempre con zona, sin secretos en el repo, `ruff format` + `ruff check` limpios, type hints completos.
- `.gitignore` actual contiene `.env.*`, que también ignora `.env.example` (contradice RN-CU-03).
- La consigna exige que el repo sea testeable siguiendo solo el README.

## Goals / Non-Goals

**Goals:**
- Un único comando por paso (levantar BD, instalar, migrar, testear) documentado en el README.
- Tests unitarios corren sin Docker; tests de integración (marker `integration`) requieren la BD de test.
- Dejar listo el patrón de sesión/transacción que C-02 y C-03 reutilizan.

**Non-Goals:**
- Async SQLAlchemy, pool tuning, observabilidad, CI.
- Cliente Redis en código (el servicio existe en compose, pero no se usa todavía).
- Imagen Docker optimizada para producción.

## Decisions

1. **Layout `backend/` autocontenido.** `backend/pyproject.toml`, `backend/alembic.ini`, `backend/alembic/`, `backend/app/`, `backend/tests/{unit,integration}/`. Todos los comandos se corren desde `backend/`. *Alternativa*: pyproject en la raíz; descartada porque el frontend (C-14) vivirá aparte.

2. **SQLAlchemy 2 síncrono + psycopg 3.** `create_engine("postgresql+psycopg://...")`, `sessionmaker`, dependencia `get_session()` con `Depends`. *Por qué*: más simple de testear con rollback y suficiente para el volumen del MVP; FastAPI corre endpoints `def` en threadpool. *Alternativa*: `AsyncSession`+asyncpg; descartada por complejidad de fixtures sin beneficio en el MVP.

3. **Configuración con `pydantic-settings`.** Clase `Settings` en `app/config.py` con `DATABASE_URL` y `JWT_SECRET` obligatorios, defaults no sensibles para el resto, validador de `APP_TIMEZONE` vía `zoneinfo.ZoneInfo` y `get_settings()` cacheado (`lru_cache`) para poder sobreescribir en tests. Lee `.env` si existe. `tzdata` se agrega como dependencia porque Windows no trae base IANA.

4. **Health check en capa `api` con dependencia inyectable.** Router `app/api/health.py` ejecuta `SELECT 1` vía un puerto simple (`check_database()` en `infrastructure/db`). Si lanza `OperationalError`/`SQLAlchemyError` → 503 `{"status":"degraded","database":"unavailable"}` sin detalle. El test del caso degradado sobreescribe la dependencia con un engine apuntando a un puerto cerrado (BD real inexistente, no mock del comportamiento de la BD). App creada con `create_app()` + `lifespan` (no `on_event`).

5. **BD de test separada en el mismo contenedor.** `docker-compose.yml` monta `docker/postgres/init/01-create-test-db.sql` que crea `turnos_test`. Variable `TEST_DATABASE_URL` (en `.env.example`, consumida solo por `tests/conftest.py`). Puerto expuesto `5432` en host (configurable vía `POSTGRES_PORT`). *Alternativa*: testcontainers; descartada para no sumar dependencia y porque compose ya es requisito.

6. **Harness pytest.**
   - Fixture `engine` (scope session): crea engine sobre `TEST_DATABASE_URL`, corre `alembic upgrade head` programáticamente sobre esa URL una vez por sesión.
   - Fixture `db_session` (scope function): conexión → `begin()` → `Session(bind=connection, join_transaction_mode="create_savepoint")` → rollback al final. Garantiza aislamiento (spec database-baseline).
   - Fixture `client`: `TestClient(create_app())` con override de `get_session` hacia `db_session`.
   - Si `TEST_DATABASE_URL` no responde, los tests `integration` fallan con mensaje claro indicando `docker compose up -d db` (no se saltean silenciosamente).
   - Markers registrados en `pyproject.toml`; `pytest -m "not integration"` corre solo unitarios.

7. **Migración `001` escrita a mano.** `op.execute("CREATE EXTENSION IF NOT EXISTS btree_gist")` / downgrade `DROP EXTENSION IF EXISTS btree_gist`. `alembic/env.py` toma la URL de `Settings` (o de `-x db_url=` / variable para tests), nunca de `alembic.ini`. Revision id fijo `001` para trazabilidad con CHANGES.md.

8. **Utilidad de tiempo como función pura de dominio.** `app/domain/time.py`: `to_utc(dt) -> datetime`, `to_local(dt, tz=...) -> datetime`, excepción `NaiveDatetimeError(ValueError)`. Sin dependencias de framework → tests unitarios sin BD. La zona de presentación por defecto se recibe por parámetro (el llamador pasa `settings.APP_TIMEZONE`), para que el dominio no dependa de la config.

9. **Herramientas.** `ruff` (format + check, `target-version = "py313"`, line-length 100). Versiones con piso (`>=`) en `pyproject.toml`; PostgreSQL 16 y Redis 7 en imágenes oficiales.

10. **Servicio `api` en compose.** `backend/Dockerfile` simple (python:3.13-slim, `pip install .`, `uvicorn app.main:app`). Se incluye para cumplir el scope, pero los tests se corren desde el venv local contra la BD del compose.

## Risks / Trade-offs

- [Puerto 5432 ocupado por un PostgreSQL local en Windows] → `POSTGRES_PORT` parametrizable en `.env`; README lo menciona.
- [Correr `alembic upgrade` en la fixture de sesión hace lento el arranque] → una sola vez por sesión; aceptable con una migración.
- [`.env.*` en `.gitignore` oculta `.env.example`] → se agrega excepción `!.env.example` y un test/chequeo en tasks.
- [Suposición RN-CU-04: Argentina sin horario de verano] → se usa `zoneinfo` (no offset fijo `-03:00`), por lo que un eventual cambio de reglas lo absorbe `tzdata`.
- [Test de 503 depende de que el puerto elegido esté cerrado] → usar host/puerto inválido determinístico (p.ej. `127.0.0.1:1`) con `connect_timeout` bajo.

## Migration Plan

No hay datos previos. Aplicación: `docker compose up -d db` → `alembic upgrade head`. Rollback: `alembic downgrade base` (elimina `btree_gist`).

## Open Questions

- Versiones mínimas exactas del stack siguen abiertas en `knowledge-base/10_preguntas_abiertas.md`; se fijan pisos razonables (FastAPI ≥0.115, SQLAlchemy ≥2.0, Alembic ≥1.13, psycopg ≥3.2, pydantic-settings ≥2.4) y se pueden ajustar sin cambiar specs.
