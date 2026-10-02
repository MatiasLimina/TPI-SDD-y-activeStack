# Selección de skills (find-skill)

**Fecha**: 2026-10-02
**Etapa**: 5 — Skills y reglas del agente

`find-skill` recomendó 8 skills a partir del stack de la knowledge-base (Python, FastAPI,
SQLAlchemy, PostgreSQL, Redis, JWT, pytest, Docker). Solo recomienda: la elección de qué
instalar fue del equipo. Se instalaron 5 de forma global.

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
