# TPI-SDD-y-activeStack

Trabajo Práctico Integrador — Metodología I: del Discovery al primer Change con Spec-Driven Development (OpenSpec) y Active Stack.

Producto: sistema de gestión de turnos y agenda de pacientes para consultorios odontológicos (mercado argentino).

## Estructura

- `desarrollo-active-stack.pdf` — consigna del trabajo.
- `openspec/` — especificaciones y changes (OpenSpec).
- `.opencode/` — skills y comandos del agente.

## Requisitos

- Git, Node, Go
- CLI `openspec`
- Agente de código (OpenCode o Claude Code)

## Cómo correr el backend y los tests

Requisitos: Docker (con Docker Compose) y Python 3.13.

```bash
# 1. Variables de entorno (valores ficticios de desarrollo)
cp .env.example .env

# 2. Base de datos (crea `turnos` y `turnos_test`)
docker compose up -d db

# 3. Entorno virtual e instalación (desde backend/)
cd backend
python -m venv .venv
source .venv/bin/activate          # Linux/macOS
# .venvScriptsctivate          # Windows (cmd/PowerShell)
pip install -e ".[dev]"

# 4. Migraciones
alembic upgrade head

# 5. Tests y lint
pytest                             # todo (requiere la base levantada)
pytest -m "not integration"        # solo unitarios, sin Docker
ruff format --check . && ruff check .
```

API completa en contenedores: `docker compose up -d api` y luego `curl http://localhost:8000/health`
(devuelve `{"status":"ok","database":"ok"}`).

Si el puerto 5432 ya está ocupado (por ejemplo por un PostgreSQL local en Windows), cambiá
`POSTGRES_PORT` en `.env` (p. ej. `5433`) y ajustá el puerto en `DATABASE_URL` y `TEST_DATABASE_URL`.
