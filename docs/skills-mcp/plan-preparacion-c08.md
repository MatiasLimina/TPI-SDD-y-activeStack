# Plan del TP Skills + MCP — preparación de C-08

Proyecto: Turnos y Agenda para Consultorios Odontológicos · Fecha: 2026-10-30 · Actualizado: 2026-11-02 · Equipo: Matías, Nico, Lauti

> Documento de coordinación interna del equipo. No es un entregable del TP: los entregables son
> `investigacion.md`, `aplicacion.md` y el zip con `ENTREGA.md`.

> **Actualización 2026-11-02.** Con la versión 2 del reparto (`docs/equipo/reparto-de-tareas.md`), esta
> semana Matías y Nico se hacen cargo de los pasos que tenía Lauti, que sigue en el equipo. Además, C-08 se
> implementó y archivó (PR #5), así que el estado "listo para Apply" que pide el TP se acredita con un commit
> concreto (ver §1). Se descartan los pasos con OpenCode y el video.

## 1. Situación actual

| Qué | Estado | Quién |
|-----|--------|-------|
| Skill propia `revisar-escenarios` (creada con `skill-creator`, registrada, en `AGENTS.md`/`CLAUDE.md`) | Hecha | Matías |
| MCP Context7 (`.mcp.json`, guía en `mcp.md`, evidencia) | Hecho | Matías |
| Ficha `investigacion.md` (eligió C-06, compara Context7 y Semgrep MCP) | Hecha | Matías |
| C-06 `auth-jwt-roles` preparado con la skill y el MCP | Implementado y archivado (antecedente) | Matías |
| C-08 `gestion-recursos-consultorio` preparado con la skill y el MCP | Implementado, archivado y en `main` (PR #5) | Matías |

**Problema con la consigna**: el TP pide preparar un change pendiente y dejarlo listo para implementar
(*"No lo marquen como implementado, verificado o archivado"*). C-06 llegó hasta el archivo, y con el reparto
v2 C-08 también se implementó, porque está en el camino crítico (C-10 y C-11 dependen de él).

**Decisión**: C-06 queda como **antecedente**: la skill y el MCP se crearon y probaron ahí. El change del TP
es **C-08**, y el estado "listo para Apply" que se presenta es el commit **`01c6b1c`**:

| Commit | Qué contiene |
|--------|--------------|
| `9d120f3` `docs(c-08): propose gestion-recursos-consultorio` | `proposal.md`, `design.md`, specs y `tasks.md` |
| `01c6b1c` `docs(c-08): add scenario review for gestion-recursos-consultorio` | `revision-escenarios.md`, veredicto **LISTO PARA APPLY** |

Ninguno de los dos tiene código: la implementación empieza en el commit siguiente (`cf88d63`). Para ver ese
estado: `git checkout 01c6b1c` (o navegar el árbol de ese commit en GitHub). Los mismos artefactos quedaron en
`openspec/changes/archive/2026-11-02-gestion-recursos-consultorio/`. El cambio de elección respecto de la ficha
y el motivo de la implementación se explican en `aplicacion.md`, como pide el punto 7.

## 2. Por qué C-08

- **Se podía preparar ya**: dependía solo de C-06, que estaba archivado.
- **Está en el camino crítico**: C-10 y C-11 dependen de C-08.
- **Tiene reglas concretas para que la skill controle**: `duracion_min > 0`, múltiplo de 5 y ≤ 480 (DD-15),
  `requiere_sillon`, desactivación lógica que conserva historial, escritura solo de la recepcionista
  (RN-AU-03).
- **Tiene una migración propia** (CHECK de duración), en la misma ola que la de C-07 (ver §5).

Scope y "Leer antes": `CHANGES.md` §C-08 (US-001; `04_modelo_de_datos.md` §Profesional/§Sillon/§Prestacion;
`05_reglas_de_negocio.md` §RN-AU-03).

## 3. Reparto

| Paso | Quién | Herramienta | Qué produce | Criterio del TP que cubre | Estado |
|------|-------|-------------|-------------|---------------------------|--------|
| 1. Reproducir el MCP | Nico | Claude Code en **su** máquina | Sigue `mcp.md` desde cero: aprueba `context7`, corre `claude mcp list` y una consulta real. Registra si algo de la guía no funcionó | Reproducibilidad: *"otro integrante debe poder seguir las instrucciones"* | Pendiente |
| 2. Context7 en la preparación de C-08 | Matías | Context7 durante `/opsx:propose` | `evidencias/c-08/explore-context7.md`: pregunta, resultado y qué decisión de `design.md` fundamenta | MCP con una herramienta real, usada en la preparación | Hecho |
| 3. Propose de C-08 | Matías | `/opsx:propose` | `proposal.md`, `design.md`, specs y `tasks.md` (commit `9d120f3`) | Artefactos SDD, ≥ 3 escenarios, cómo se verifica cada uno | Hecho |
| 4. Revisión con la skill | Matías | `revisar-escenarios` | `revision-escenarios.md` del change (commit `01c6b1c`) | Uso real de la skill | Hecho |
| 5. Corregir según la revisión | Matías | `/opsx:update` | Specs o tasks ajustados por los hallazgos, o constancia de por qué no hizo falta | Revisión crítica (punto 8) | Pendiente de documentar |
| 6. Verificar la skill en una sesión nueva | Nico | Claude Code, sesión limpia | Captura: pregunta "¿cómo reviso los escenarios de C-08?" y el agente encuentra la skill por `AGENTS.md`/`CLAUDE.md` sin que se la nombre | Punto 5: *"en una sesión nueva, comprueben..."* | Pendiente |
| 7. Roadmap | Matías | Edición a mano | C-08 figura `[x]` en `CHANGES.md`; para el TP vale el estado del commit `01c6b1c` (§1) | Punto 7 | Hecho |
| 8. Informe y entrega | Matías y Nico; integra Nico | — | `aplicacion.md` actualizado, `ENTREGA.md` y el zip | Entrega | Pendiente |

### Consultas a Context7 que tienen sentido para C-08

Son preguntas genéricas, sin datos del proyecto (límite fijado en `CLAUDE.md`):

- Cómo declarar un `CheckConstraint` en SQLAlchemy 2 y crearlo en una migración de Alembic (`op.create_check_constraint`).
- Validadores de Pydantic v2 para un entero múltiplo de 5 dentro de un rango (`field_validator` frente a `Annotated` + `Field`).
- Actualización parcial en FastAPI (`PATCH` con `model_dump(exclude_unset=True)`).

Cada respuesta tiene que terminar en una línea concreta de `design.md`. Si no, no aporta nada al change. Las
dos primeras ya están registradas en `evidencias/c-08/explore-context7.md`.

### Ramas y commits

- `feat/c-08-gestion-recursos-consultorio`: artefactos, revisión e implementación de C-08. Mergeada en `main` (PR #5).
- Lo que falta del TP (`aplicacion.md`, evidencias de Nico, `ENTREGA.md`) va en una rama `docs/...` con su PR,
  aprobado por el otro integrante. Conventional Commits: `docs(skills-mcp): ...`.
- **Cada uno commitea lo suyo con su usuario de git**: el historial es la prueba de participación que pide el TP.

## 4. Revisión crítica (punto 8)

La fuente son los **hallazgos de la skill sobre el Propose**. No hay que inventar el error.

- Si `revisar-escenarios` marca un escenario mal planteado, se muestra el escenario antes, el hallazgo con su
  regla RN/DD y el escenario después. El informe de C-08 dio **LISTO PARA APPLY** con hallazgos `MENOR`
  (por ejemplo, escenarios de rechazo que no afirman "no se persiste nada" y escenarios que dependen de
  "ahora" sin fijar el reloj). Hay que revisar si alguno se corrigió y documentarlo, o explicar por qué se
  dejó así.
- Se verifica cada hallazgo contra `knowledge-base/`: que la regla citada exista y diga eso.
- Si no alcanza, Nico prueba un caso de borde: pasarle a la skill un escenario que invade C-10 (horarios) y
  ver si lo marca como fuera de scope. El resultado se documenta tal cual.

## 5. Riesgo de migraciones de C-07 y C-08 en paralelo (resuelto)

C-07 (auditoría) y C-08 (CHECK de duración) creaban migración en la ola 1. Si los dos usaban `005`, git
mergeaba sin conflicto, pero quedaban dos cabezas y `alembic upgrade head` fallaba.

**Cómo se resolvió**: C-07 se mergeó primero con `005` (PR #3) y C-08 tomó `006`
(`backend/alembic/versions/006_prestacion_duracion_grilla.py`), con una sola cabeza. La regla quedó en
`CLAUDE.md`: el que mergea segundo renumera su revisión. Un chequeo de CI para migraciones queda fuera del
alcance de este TP.

## 6. Cambios a los entregables existentes

| Archivo | Cambio | Quién |
|---------|--------|-------|
| `docs/skills-mcp/aplicacion.md` | Pasa a centrarse en C-08; C-06 queda como antecedente en un párrafo. Agregar: motivo del cambio de change, por qué C-08 se implementó y que el estado del TP es `01c6b1c`, reparto y revisión crítica. Máximo 2 páginas | Matías y Nico; integra Nico |
| `docs/skills-mcp/investigacion.md` | No se reescribe (se presentó en clase). Como mucho, una nota al pie que remita a `aplicacion.md` por el cambio de change | Matías |
| `docs/skills-mcp/evidencias/c-08/` | Agregar la reproducción del MCP (paso 1) y la verificación en sesión nueva (paso 6) | Nico |
| `ENTREGA.md` | Integrantes, enlace al repo y commit de entrega | Nico |

## 7. Pendientes de decidir

- Fecha de entrega y fecha límite interna para los pasos pendientes.
- Confirmar con el docente que presentar C-06 como antecedente y C-08 como change del TP, con el estado de
  `01c6b1c`, es aceptable.
