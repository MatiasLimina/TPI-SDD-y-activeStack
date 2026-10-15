# TPI-SDD-y-activeStack

Trabajo Práctico Integrador — Metodología I: del Discovery al primer Change con Spec-Driven Development (OpenSpec) y Active Stack.

Producto: sistema de gestión de turnos y agenda de pacientes para consultorios odontológicos (mercado argentino).

## Estructura

- `desarrollo-active-stack.pdf` — consigna del trabajo.
- `openspec/` — especificaciones y changes (OpenSpec).
- `knowledge-base/` — base de conocimiento del dominio (fuente de verdad).
- `CHANGES.md` — roadmap de changes.
- `.agents/skills/` — skills del proyecto, instaladas a nivel proyecto (no globales).
- `skills-lock.json` — origen y hash de cada skill instalada.
- `.atl/skill-registry.md` — índice de skills con sus reglas compactas; lo usa el orquestador al delegar.
- `.claude/commands/opsx/` y `.opencode/commands/` — comandos `/opsx:*` para Claude Code y OpenCode.
- `AGENTS.md` / `CLAUDE.md` — instrucciones del proyecto para los agentes.

## Requisitos

- Git, Node, Go
- CLI `openspec`
- Agente de código (OpenCode o Claude Code)

## Skills del proyecto

Las skills viven en `.agents/skills/` y se versionan con el repo, así quien clona el proyecto
trabaja con las mismas skills sin instalar nada global.

| Skill | Fuente | Para qué |
|---|---|---|
| `tdd` | mattpocock/skills | Ciclo red-green-refactor (TDD estricto) |
| `python-testing-patterns` | wshobson/agents | Tests con pytest: fixtures, parametrize, markers |
| `fastapi-python` | mindrally/skills | API REST con FastAPI y Pydantic |
| `supabase-postgres-best-practices` | supabase/agent-skills | Esquema, constraints e índices en PostgreSQL |
| `auth-implementation-patterns` | wshobson/agents | JWT y control de acceso por rol (C-06) |
| `openspec-*` | `openspec init` | Flujo OPSX: explore, propose, apply, archive, sync, update |

Por qué se eligieron estas y no otras: [docs/fundacion/skills-seleccionadas.md](docs/fundacion/skills-seleccionadas.md).

Para agregar o reinstalar una skill, desde la raíz del repo y **sin** `-g`:

```bash
npx skills add <repo> --skill <nombre>
```

El comando la deja en `.agents/skills/`, la registra en `skills-lock.json` y crea un enlace en
`.claude/skills/` para Claude Code (ese enlace es local y no se versiona). Después de agregar o
quitar skills hay que reconstruir `.atl/skill-registry.md` con `/active-orchestrator:registry`.

Al clonar el repo, Claude Code no ve las skills hasta recrear esos enlaces: correr el comando de
arriba para cada skill listada en `skills-lock.json` (fuente y nombre). OpenCode y los demás
agentes compatibles leen `.agents/skills/` directamente.

Si `openspec init` u `openspec update` vuelven a generar `.opencode/skills/openspec-*`, moverlas a
`.agents/skills/` (reemplazando las anteriores) para no tener dos copias.

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
# .venv\Scripts\activate          # Windows (cmd/PowerShell)
pip install -e ".[dev]"

# 4. Migraciones
alembic upgrade head

# 4b. (opcional, solo desarrollo) Datos ficticios: 2 profesionales, 2 sillones, 4 prestaciones, 4 pacientes.
# Idempotente: se puede correr varias veces sin duplicar ni pisar cambios.
python -m app.infrastructure.db.seed

# 5. Tests y lint
pytest                             # todo (requiere la base levantada)
pytest -m "not integration"        # solo unitarios, sin Docker
ruff format --check . && ruff check .
```

API completa en contenedores: `docker compose up -d api` y luego `curl http://localhost:8000/health`
(devuelve `{"status":"ok","database":"ok"}`).

Si el puerto 5432 ya está ocupado (por ejemplo por un PostgreSQL local en Windows), cambiá
`POSTGRES_PORT` en `.env` (p. ej. `5433`) y ajustá el puerto en `DATABASE_URL` y `TEST_DATABASE_URL`.
