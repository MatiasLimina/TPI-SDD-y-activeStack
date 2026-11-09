# TPI-SDD-y-activeStack

Trabajo Práctico Integrador — Metodología I: del Discovery al primer Change con Spec-Driven Development (OpenSpec) y Active Stack.

Producto: sistema de gestión de turnos y agenda de pacientes para consultorios odontológicos (mercado argentino).

## Estructura

- `desarrollo-active-stack.pdf` — consigna del trabajo.
- `openspec/` — especificaciones y changes (OpenSpec).
- `knowledge-base/` — base de conocimiento del dominio (fuente de verdad).
- `backend/` — API FastAPI, migraciones y tests (pytest).
- `frontend/` — SPA React + TypeScript + Vite, con sus tests (Vitest).
- `CHANGES.md` — roadmap de changes.
- `.agents/skills/` — skills del proyecto, instaladas a nivel proyecto (no globales).
- `skills-lock.json` — origen y hash de cada skill instalada.
- `.atl/skill-registry.md` — índice de skills con sus reglas compactas; lo usa el orquestador al delegar.
- `.claude/commands/opsx/` y `.opencode/commands/` — comandos `/opsx:*` para Claude Code y OpenCode.
- `AGENTS.md` / `CLAUDE.md` — instrucciones del proyecto para los agentes.
- `.mcp.json` — servidores MCP del proyecto (Context7), sin secretos.
- `docs/skills-mcp/` — investigación, configuración y evidencias de la skill propia y del MCP.

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
| `skill-creator` | anthropics/skills | Crear y evaluar skills (con ella se hizo `revisar-escenarios`) |
| `revisar-escenarios` | **propia** (este repo) | Revisa los escenarios de un change contra la KB antes de Apply |
| `revisar-migraciones` | **propia** (este repo) | Revisa en las ramas remotas que las migraciones de Alembic estén bien numeradas antes de mergear |

Por qué se eligieron estas y no otras: [docs/fundacion/skills-seleccionadas.md](docs/fundacion/skills-seleccionadas.md).

Para agregar o reinstalar una skill, desde la raíz del repo y **sin** `-g`:

```bash
npx skills add <repo> --skill <nombre>
```

El comando la deja en `.agents/skills/`, la registra en `skills-lock.json` y crea un enlace en
`.claude/skills/` para Claude Code (ese enlace es local y no se versiona). Después de agregar o
quitar skills hay que reconstruir `.atl/skill-registry.md` con `/active-orchestrator:registry`
(excepción: las filas de las skills propias, `revisar-escenarios` y `revisar-migraciones`, se agregaron a mano; ver `docs/fundacion/skills-seleccionadas.md`).

Al clonar el repo, Claude Code no ve las skills hasta recrear esos enlaces: correr el comando de
arriba para cada skill listada en `skills-lock.json` (fuente y nombre). OpenCode y los demás
agentes compatibles leen `.agents/skills/` directamente.

Si `openspec init` u `openspec update` vuelven a generar `.opencode/skills/openspec-*`, moverlas a
`.agents/skills/` (reemplazando las anteriores) para no tener dos copias.

### Skill propia `revisar-escenarios`

No viene de un repositorio externo, así que no está en `skills-lock.json` y `npx skills add` no la
reinstala: su fuente versionada es `.agents/skills/revisar-escenarios/`. Para que Claude Code la vea
después de clonar, crear el enlace a mano desde la raíz del repo:

```bash
mkdir -p .claude/skills
```

```bash
cmd //c "mklink /J .claude\\skills\\revisar-escenarios .agents\\skills\\revisar-escenarios"
```

`.claude/skills/` no se versiona, por eso el `mkdir -p`. Esos son los comandos para Git Bash en Windows; en cmd es `mklink /J .claude\skills\revisar-escenarios .agents\skills\revisar-escenarios`.
En Linux/macOS: `ln -s ../../.agents/skills/revisar-escenarios .claude/skills/revisar-escenarios`.

Se usa una *junction* porque en Windows `ln -s` falla sin modo desarrollador
("Operation not permitted"). Se comprueba abriendo una sesión nueva de Claude Code en la raíz y pidiendo
"qué skills tenés disponibles": `revisar-escenarios` debe figurar en la lista. Uso, entradas y criterios de
revisión: sección "Skill propia" de [AGENTS.md](AGENTS.md). Evidencia de las pruebas:
[docs/skills-mcp/evidencias/skill-evals/](docs/skills-mcp/evidencias/skill-evals/iteration-1/resumen.md).

### Skill propia `revisar-migraciones`

Igual que la anterior: no está en `skills-lock.json` y su fuente versionada es
`.agents/skills/revisar-migraciones/`. Para que Claude Code la vea después de clonar (Git Bash en Windows):

```bash
cmd //c "mklink /J .claude\\skills\\revisar-migraciones .agents\\skills\\revisar-migraciones"
```

En Linux/macOS: `ln -s ../../.agents/skills/revisar-migraciones .claude/skills/revisar-migraciones`.

El chequeo también se puede correr sin agente, desde la raíz del repo (necesita Python ≥ 3.13 y solo usa la
biblioteca estándar):

```bash
python .agents/skills/revisar-migraciones/scripts/revisar_migraciones.py
```

Hace `git fetch --prune`, compara cada rama de `origin` contra `origin/main` sin hacer checkout e informa
qué migraciones hay que renumerar. Solo ve ramas pusheadas. Sale con código 1 si encuentra algo para
corregir y con 2 si hay un error de uso o de git. Uso y lectura del informe: sección
"Skill propia: `revisar-migraciones`" de [AGENTS.md](AGENTS.md).

## MCP del proyecto

El repo versiona [`.mcp.json`](.mcp.json) con el servidor **Context7** (documentación actualizada de las
librerías del stack), remoto y sin secretos. Al abrir Claude Code en la raíz hay que aprobarlo una vez y
después comprobarlo con `claude mcp list`. Requisitos, API key opcional (fuera del repo), prueba de una
herramienta, solución del aviso "defined in multiple scopes" y límites de uso:
[docs/skills-mcp/mcp.md](docs/skills-mcp/mcp.md).

## Cómo correr el backend y los tests

Requisitos: Docker (con Docker Compose) y Python 3.13.

```bash
# 1. Variables de entorno (valores ficticios de desarrollo)
cp .env.example .env

# 2. Base de datos (crea `turnos` y `turnos_test`) y Redis (cola de recordatorios)
docker compose up -d db redis

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
pytest                             # todo (requiere db y redis levantados y TEST_REDIS_URL en .env)
pytest -m "not integration"        # solo unitarios, sin Docker
ruff format --check . && ruff check .
```

API completa en contenedores: `docker compose up -d api` y luego `curl http://localhost:8000/health`
(devuelve `{"status":"ok","database":"ok"}`).

Recordatorios: el servicio `worker` (`docker compose up -d worker`, o `python -m app.worker` desde
`backend/`) re-encola los recordatorios pendientes al iniciar y envía los vencidos con el adaptador
`mock`. Necesita la migración `008` aplicada (`alembic upgrade head`) y no recibe `JWT_SECRET`.
Es crash-only: ante un error de base o de Redis termina, y los recordatorios que ya había tomado de
la cola vuelven recién al reiniciar. Por eso tiene que correr bajo un supervisor (en Compose,
`restart: unless-stopped`); si lo levantás a mano, reinicialo cuando se caiga.
`TEST_REDIS_URL` (en `.env.example`, base 15) apunta a una base de Redis distinta de `REDIS_URL`: la
suite de contrato de la cola la usa y borra solo sus claves de prueba.

Si el puerto 5432 ya está ocupado (por ejemplo por un PostgreSQL local en Windows), cambiá
`POSTGRES_PORT` en `.env` (p. ej. `5433`) y ajustá el puerto en `DATABASE_URL` y `TEST_DATABASE_URL`.

## Cómo correr el frontend

Requisitos: Node 24 (`^24.15.0`, declarado en `frontend/package.json`) y la API corriendo (ver arriba).
Ejecutá los comandos desde `frontend/`.

```bash
npm ci                 # instala exactamente lo que fija package-lock.json
npm run dev            # servidor de desarrollo en http://localhost:5173

npm test               # tests (Vitest + React Testing Library, sin tocar la red real)
npm run typecheck && npm run lint && npm run format:check && npm test   # verificación completa
npm run build          # compilación de producción en dist/
```

- **URL de la API**: la SPA llama a `VITE_API_URL` (por defecto `http://localhost:8000`). Es una variable
  pública: la lee el navegador, por eso no puede ser `http://api:8000` ni contener ningún secreto.
- **Abrí `http://localhost:5173`, no `http://127.0.0.1:5173`**: la API solo acepta pedidos de los orígenes
  de `CORS_ORIGINS` (por defecto `http://localhost:5173`, coincidencia exacta). Con `127.0.0.1` el
  navegador bloquea las respuestas por CORS. `CORS_ORIGINS` es una lista separada por comas; vacía no
  permite ningún origen y `*` es inválido (la API no arranca).
- **Todo el stack**: `docker compose up --build` levanta `db`, `redis`, `api`, `worker` y `frontend`
  (puerto 5173), pero la imagen de la API no corre las migraciones ni el seed: sin tablas ni usuarios no
  se puede iniciar sesión. Hacelo en este orden (el entorno virtual y `pip install -e ".[dev]"` de la
  sección anterior ya tienen que estar hechos):

  ```bash
  docker compose up -d db redis          # 1. solo la base y Redis
  cd backend && alembic upgrade head     # 2. migraciones, desde el host
  python -m app.infrastructure.db.seed   # 3. usuarios y catálogo ficticios (desde backend/)
  cd .. && docker compose up --build     # 4. todo el stack
  ```

  El seed lee `SEED_RECEPCIONISTA_PASSWORD`, `SEED_ODONTOLOGO_1_PASSWORD` y `SEED_ODONTOLOGO_2_PASSWORD`
  del `.env` de la raíz (las trae el `.env` copiado de `.env.example`). Si una está sin definir o vacía,
  el seed omite a ese usuario **sin avisar**.
  **Síntoma de saltear la migración**: `POST /auth/login` responde `500`, y como esa respuesta no lleva
  encabezados CORS, el navegador muestra "No se pudo conectar con el servidor.", que parece un problema
  de CORS pero no lo es.
- El servicio `frontend` de Compose corre el servidor de desarrollo de Vite sin montar el código: los
  cambios se ven con `--build`, y el trabajo diario va con `npm run dev` en el host. **No es apto para
  producción.**
