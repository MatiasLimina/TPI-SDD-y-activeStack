# Turnos y Agenda para Consultorios Odontológicos — Instrucciones para Agentes

> Este archivo (y su copia `CLAUDE.md`) es lo PRIMERO que todo agente lee al entrar al repo.
> Generado a partir de `knowledge-base/`, `CHANGES.md` y `.atl/skill-registry.md`. No editar a mano sin re-sincronizar ambos archivos.

Sistema de agenda para consultorios odontológicos chicos de Argentina (1 a 5 profesionales, 1 a 4 sillones). El MVP ataca el vacío detectado en el Discovery: prestaciones con duración propia y sillones como recurso, con prevención de solapamientos por profesional, por sillón y por paciente garantizada en la base de datos.

---

## Stack Tecnológico

| Capa | Tecnologías | Notas |
|------|-------------|-------|
| Backend | Python + FastAPI | API REST, validación con Pydantic |
| ORM / migraciones | SQLAlchemy + Alembic | |
| Base de datos | PostgreSQL | Requiere extensión `btree_gist` para la restricción de exclusión |
| Cola / caché | Redis | Cola de recordatorios asincrónicos |
| Autenticación | JWT | 2 roles: recepcionista, odontólogo |
| Frontend | React + TypeScript + Vite | Agenda diaria/semanal (changes C-14..C-16, al final) |
| Infra | Docker / Docker Compose | api, db, redis, worker, frontend |
| Tests | pytest | TDD estricto (ver `~/.claude/CLAUDE.md`) |

Versiones mínimas (DD-17): Python ≥ 3.13, PostgreSQL 16, Node 22 LTS (a confirmar en C-14). Detalle completo: [knowledge-base/02_descripcion_general.md](knowledge-base/02_descripcion_general.md)

---

## Base de Conocimiento

La fuente de verdad del dominio vive en `knowledge-base/`. **Leé el archivo relevante ANTES de implementar.** El origen de cada decisión de producto está en `docs/discovery/` (informe de mercado y checklist).

| Archivo | Cuándo leerlo |
|---------|---------------|
| [01_vision_y_objetivos.md](knowledge-base/01_vision_y_objetivos.md) | Propósito, alcance del MVP (D.4) y lo que queda fuera |
| [02_descripcion_general.md](knowledge-base/02_descripcion_general.md) | Stack, arquitectura, API |
| [03_actores_y_roles.md](knowledge-base/03_actores_y_roles.md) | Auth, RBAC, permisos |
| [04_modelo_de_datos.md](knowledge-base/04_modelo_de_datos.md) | Entidades, ERD, constraints de exclusión, seed |
| [05_reglas_de_negocio.md](knowledge-base/05_reglas_de_negocio.md) | Reglas codificadas (RN-AG, RN-HB, RN-NO, RN-AU, RN-CU) |
| [06_funcionalidades.md](knowledge-base/06_funcionalidades.md) | Historias de usuario por épica |
| [07_flujos_principales.md](knowledge-base/07_flujos_principales.md) | Flujos de punta a punta |
| [08_arquitectura_propuesta.md](knowledge-base/08_arquitectura_propuesta.md) | Patrones, concurrencia, estructura, env vars |
| [09_decisiones_y_supuestos.md](knowledge-base/09_decisiones_y_supuestos.md) | Decisiones DD-xx y supuestos SU-xx |
| [10_preguntas_abiertas.md](knowledge-base/10_preguntas_abiertas.md) | ⚠️ Preguntas abiertas e inconsistencias |

> ⚠️ Antes de cada change, revisá `10_preguntas_abiertas.md`. Al 2026-10-07 no quedan preguntas abiertas: todas se resolvieron en DD-13..DD-21 (`09_decisiones_y_supuestos.md`).

---

## Skills Disponibles

| Agente | Rol | Skills que carga |
|--------|-----|------------------|
| **Backend Core** | Dominio de agenda, API FastAPI, modelos y migraciones | `fastapi-python`, `supabase-postgres-best-practices`, `tdd`, `python-testing-patterns` |
| **Backend Seguridad** | JWT, roles, auditoría (C-06, C-07) | `auth-implementation-patterns`, `python-testing-patterns` |
| **Frontend** | React + TypeScript + Vite (C-14..C-16) | Ninguna instalada todavía; reevaluar con `find-skill` al llegar a esos changes |
| **Orquestación** | Fundación y ciclo OPSX | `active-orchestrator`, `kb-creator`, `roadmap-generator`, `skill-registry`, `agent-instruction`, skills `openspec-*` |
| **Revisión de specs** | Control de escenarios entre Propose y Apply | `revisar-escenarios` (skill propia), `skill-creator` (para mantenerla) |

Las skills de dominio y las `openspec-*` están instaladas **a nivel proyecto** en `.agents/skills/` (versionadas, con origen fijado en `skills-lock.json`); no dependen de instalaciones globales. Para agregar una: `npx skills add <repo> --skill <nombre>` **sin** `-g`, y después `/active-orchestrator:registry`. Las de orquestación (`active-orchestrator`, `kb-creator`, etc.) son del stack y siguen siendo globales.

Cargá la skill correspondiente al contexto ANTES de escribir código. Justificación de qué se instaló y qué no: [docs/fundacion/skills-seleccionadas.md](docs/fundacion/skills-seleccionadas.md).

> Los compact rules de cada skill los resuelve el orquestador desde `.atl/skill-registry.md` (generado por `skill-registry`). En este proyecto el registry **sí está versionado**, porque la consigna lo exige como entregable. Esta tabla solo mapea skill→rol.

### Skill propia: `revisar-escenarios`

Skill del proyecto, creada con `skill-creator` (anthropics/skills). Vive en `.agents/skills/revisar-escenarios/`, y Claude Code la ve por la unión de directorios `.claude/skills/revisar-escenarios` (ver README).

- **Cuándo usarla**: después de cada `/opsx:propose` o `/opsx:update` y **antes** de `/opsx:apply`, o cuando se pida revisar, validar o chequear los escenarios de un change.
- **Qué necesita**: el nombre del change, con sus delta specs ya escritos en `openspec/changes/<change>/specs/`. Lee por su cuenta `CHANGES.md` y la KB.
- **Qué produce**: `openspec/changes/<change>/revision-escenarios.md`, con un veredicto, una tabla de cobertura y hallazgos con severidad y fuente. **Solo reporta**: las correcciones se hacen con `/opsx:update`.
- **Cómo revisar su resultado**: cada hallazgo BLOQUEANTE o MAYOR cita una regla RN/DD que existe y dice eso. Ningún escenario sugerido introduce una regla que no esté en la KB (si la introduce, debe figurar como pregunta abierta). Nada de lo que marca como faltante pertenece a otro change.

---

## Integraciones MCP

Los MCP son **integraciones**, no skills: no se registran en `.atl/skill-registry.md`. Configuración, comprobación y solución de problemas: [docs/skills-mcp/mcp.md](docs/skills-mcp/mcp.md).

| Servidor | Configuración | Propósito | Herramientas | Cuándo | Límites |
|----------|---------------|-----------|--------------|--------|---------|
| `context7` (Upstash, remoto) | `.mcp.json` (ámbito project, sin secretos) | Documentación actual y versionada de las librerías del stack (FastAPI, PyJWT, pwdlib, SQLAlchemy, redis-py…) | `resolve-library-id`, `query-docs` | Al explorar o diseñar un change que elige o usa una librería, y antes de fijar en `design.md` una API de terceros | Solo lectura de documentación pública. En `query` van preguntas genéricas: nunca datos de pacientes, secretos, contenido de `.env` ni código del proyecto. No es fuente de verdad del dominio: ante un conflicto con la KB, prevalece la KB y la diferencia se registra en el design |

---

## Roadmap de Changes

El plan de implementación completo está en [CHANGES.md](CHANGES.md). Resumen:

- **Total**: 16 changes en 6 fases (backend primero, frontend al final).
- **Camino crítico** (12): `C-01 → C-02 → C-03 → C-05 → C-06 → C-08 → C-10 → C-11 → C-13 → C-14 → C-15 → C-16`.
- **Primer change**: `C-01` (`foundation-scaffolding-test-harness`).
- **Change elegido para el ciclo OPSX**: `C-03` (`crear-turno-sin-solapamientos`). Depende solo de C-01 y C-02. No incluye autenticación (llega en C-06) ni validación de horarios y bloqueos (llegan en C-10 y C-11): sus escenarios no deben cubrir esas reglas.
- **Change grabado para la defensa**: `C-05` (`reprogramar-turno`), ciclo OPSX completo desde cero. Depende solo de C-03. No incluye autenticación (C-06), horarios ni bloqueos (C-10, C-11), auditoría (C-07) ni recordatorio (C-12): sus escenarios no deben cubrir esas reglas.
- **Fuera de alcance**: ver la sección "Fuera de alcance / backlog" de `CHANGES.md`. Nada de eso se implementa sin un change nuevo.

**Antes de cualquier `/opsx:propose`**: leé [CHANGES.md](CHANGES.md), identificá las dependencias del change y los archivos de "Leer antes".

---

## Reglas Duras (específicas del proyecto)

> Reglas **globales** ya definidas en `~/.claude/CLAUDE.md` (orquestador, governance, TDD estricto, engram): el proyecto las **hereda**, no se repiten acá. Acá viven solo las reglas **específicas de este proyecto** y las universales que el global no cubre.

Son contrato; romperlas es un defecto.

### Datos y dominio
- **NUNCA** usar datos reales de pacientes en código, seeds, tests, ejemplos ni capturas → solo datos ficticios (nombres, DNI, teléfonos y emails inventados).
- **NUNCA** commitear claves, tokens ni credenciales → todo por variables de entorno, con `.env.example` versionado y `.env` ignorado.
- **NUNCA** confiar solo en la validación de la aplicación para evitar solapamientos → la restricción de exclusión en PostgreSQL (`tstzrange '[)'` + `btree_gist`, por profesional, por sillón y por paciente) es obligatoria, y va acompañada de un test de concurrencia.
- **NUNCA** usar datetimes sin zona horaria → persistir como `timestamptz` en UTC y presentar en `America/Argentina/Buenos_Aires`.
- **NUNCA** incluir la prestación ni datos de salud en el contenido de un recordatorio → solo fecha, hora y consultorio.

### Stack Python
- **NUNCA** dejar firmas públicas sin type hints → `snake_case`, type hints completos, y `ruff format` + `ruff check` sin errores antes de dar una tarea por terminada.
- **NUNCA** mockear la base ni usar SQLite en tests de persistencia → PostgreSQL real en contenedor, porque las restricciones de exclusión solo existen en PostgreSQL.

### Proceso
- **NUNCA** commitear ni pushear sin pedido explícito del usuario.
- **NUNCA** usar mensajes de commit libres → Conventional Commits (`feat`, `fix`, `docs`, `test`, `refactor`, `chore` con scope), un commit por etapa o tarea, para que el historial muestre el proceso.
- **NUNCA** implementar en Apply algo que no esté en el spec aprobado → si falta algo, se vuelve a Propose y se ajusta el spec.

---

## Flujo de Trabajo

```
1. Leer la KB relevante (knowledge-base/)        → entender el dominio
2. Identificar el change en CHANGES.md           → respetar dependencias
3. /opsx:explore C-NN-nombre (opcional)          → relevar antes de proponer (Context7 para docs del stack)
4. /opsx:propose C-NN-nombre                     → proposal + design + specs + tasks
5. revisar-escenarios C-NN-nombre                → informe; si hay BLOQUEANTE/MAYOR, /opsx:update
6. /opsx:apply C-NN-nombre (cargando skills)     → TDD estricto, respetando las reglas duras
7. Verificar: pytest en verde por cada escenario → nada se archiva en rojo
8. /opsx:archive C-NN-nombre + marcar [x]        → cerrar el change
```

Aplicar TODAS las reglas duras en cada paso. Ante conflicto entre la KB y este archivo, las reglas duras prevalecen.
