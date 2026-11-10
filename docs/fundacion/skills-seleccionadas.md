# Selección de skills (find-skill)

**Fecha**: 2026-10-02
**Etapa**: 5 — Skills y reglas del agente

`find-skill` recomendó 8 skills a partir del stack de la knowledge-base (Python, FastAPI,
SQLAlchemy, PostgreSQL, Redis, JWT, pytest, Docker). Solo recomienda: la elección de qué
instalar fue del equipo. Se instalaron 5, a nivel proyecto en `.agents/skills/`.

> **Rectificación (2026-10-15)**: en la fundación las 5 skills se instalaron de forma global
> (`npx skills add … -g`), así que no quedaban en el repo y el registry apuntaba a rutas de la
> máquina de un integrante. Se reinstalaron a nivel proyecto (`npx skills add <repo> --skill <nombre>`,
> sin `-g`): ahora viven en `.agents/skills/`, se versionan con el repo y `skills-lock.json`
> fija su origen. También se movieron ahí las skills `openspec-*`, que antes estaban en
> `.opencode/skills/`. El registry (`.atl/skill-registry.md`) usa rutas relativas al proyecto.

| Skill | Fuente | Instalada | Justificación |
|---|---|---|---|
| `tdd` | mattpocock/skills | Sí | el ciclo OPSX se implementa con TDD estricto y refuerza la disciplina red-green-refactor. |
| `python-testing-patterns` | wshobson/agents | Sí | los tests por escenario del spec se escriben con pytest (fixtures, parametrize). |
| `fastapi-python` | mindrally/skills | Sí | la API del change C-03 (POST /turnos) se construye con FastAPI. |
| `supabase-postgres-best-practices` | supabase/agent-skills | Sí | la garantía de no solapamiento vive en constraints de PostgreSQL; es la más adoptada (426K) y no depende de Supabase. |
| `sqlalchemy-alembic-expert-best-practices-code-review` | wispbit-ai/skills | No | muy pocas instalaciones (1.8K) para una fuente desconocida; SQLAlchemy/Alembic se cubren con la documentación oficial. |
| `auth-implementation-patterns` | wshobson/agents | Sí | el MVP incluye JWT con dos roles (C-06) y datos de salud que exigen control de acceso. |
| `docker-patterns` | affaan-m/ecc | No | el Docker Compose del proyecto es simple (API + Postgres + Redis) y no justifica una skill. |
| `async-python-patterns` | wshobson/agents | No | no está decidido que FastAPI y SQLAlchemy corran en modo async; se reevalúa si se adopta. |

**Sin cobertura**: no se encontraron skills específicas para Redis ni para restricciones de
exclusión de PostgreSQL (`btree_gist`); se resuelven con la documentación oficial.

## Ampliación (2026-10-16) — skill propia y MCP

Para el TP de skills y MCP se agregaron, **sin re-ejecutar** las etapas de la fundación
(`find-skill` no se volvió a correr; `.active-orchestrator-state.json` no se tocó):

| Incorporación | Tipo | Ubicación | Motivo |
|---|---|---|---|
| `skill-creator` (anthropics/skills) | Skill instalada | `.agents/skills/skill-creator/`, fijada en `skills-lock.json` | Herramienta para crear y evaluar la skill propia |
| `revisar-escenarios` | Skill **propia** | `.agents/skills/revisar-escenarios/` | Revisar los escenarios de un change contra la KB antes de Apply; primer uso: C-06 |
| `revisar-migraciones` | Skill **propia** | `.agents/skills/revisar-migraciones/` | Detectar antes del merge migraciones de Alembic mal numeradas entre ramas (revisiones escritas a mano: dos ramas con el mismo número dejan dos cabezas). Agregada el 2026-11-03, con el trabajo repartido entre dos personas |
| Context7 (Upstash) | Servidor MCP (integración, no skill) | `.mcp.json` | Documentación actualizada de PyJWT, pwdlib y FastAPI para el design de C-06 |

El registry (`.atl/skill-registry.md`) se actualizó a mano (fila y compact rules de
`revisar-escenarios` y de `revisar-migraciones`), sin regenerarlo con `/active-orchestrator:registry`, para no reescribir las reglas
compactas existentes. Investigación y comparación: [docs/skills-mcp/investigacion.md](../skills-mcp/investigacion.md).

## Reevaluación para el frontend (2026-11-09)

Al llegar a C-14 (base del frontend y login) se reevaluaron las skills del Frontend, que hasta entonces no tenía ninguna instalada. Se instaló a nivel proyecto (`npx skills add antfu/skills --skill vitest`, sin `-g`), fijada en `skills-lock.json`.

| Skill | Fuente | Instalada | Justificación |
|---|---|---|---|
| `vitest` | antfu/skills | Sí | desde C-14 se trabaja con TDD estricto y se consulta en cada test (jsdom, mocks, fake timers, hooks). Documenta Vitest 5.1.0-beta.1 (pre-release): verificar la versión instalada antes de usar comportamiento propio de v5. No cubre React Testing Library. |
| `vite` | antfu/skills | No | su documentación ya la cubre Context7 y la configuración es chica y se escribe una sola vez. Las tareas deben exigir consultar Context7 antes de escribir `vite.config.ts`. |
| Skills de React y TypeScript | varias | No | los candidatos encontrados apuntan a Next.js o tienen poco respaldo; el modo `strict` de TypeScript ya hace cumplir los tipos. |
| `vercel-react-best-practices` | vercel-labs/agent-skills | No | es una guía de rendimiento, en parte exclusiva de Next.js, y no cubre login, guards de rutas ni formularios. Se reevaluó para C-15 y tampoco se instaló (ver la decisión abajo). |

La documentación de React Router y de React Testing Library sale de Context7 (ver [docs/skills-mcp/mcp.md](../skills-mcp/mcp.md)). El registry (`.atl/skill-registry.md`) se actualizó agregando solo la fila y las reglas compactas de `vitest`, sin reescribir el resto.

**Decisión para C-15 (2026-11-10)**: `vercel-react-best-practices` (vercel-labs/agent-skills) **no se instala**, y con esto se cierra la reevaluación que quedaba pendiente en la tabla. Motivos:

- El volumen de la agenda es chico: como máximo 7 días, de 1 a 5 profesionales y decenas de turnos por vista, así que los re-renders no son el problema a resolver.
- La dificultad de C-15 está en los formularios, el manejo de 409 y 422, el selector de pacientes y la presentación de horarios, temas que la skill no cubre.
- Muchas de sus 70 reglas son exclusivas de Next.js o empujan a sumar librerías.

> **Gotcha de instalación**: `npx skills add` con `--agent claude-code` copia la skill en `.claude/skills/` en lugar de `.agents/skills/`. La convención del proyecto exige `.agents/skills/` (versionado), así que el comando se ejecuta sin esa bandera. `.claude/skills/vitest` es solo un enlace local no versionado hacia `.agents/skills/vitest`.
