# Plan del TP Skills + MCP — preparación de C-08 y video

Proyecto: Turnos y Agenda para Consultorios Odontológicos · Fecha: 2026-10-30 · Equipo: Matías, Nico, Lauti

> Documento de coordinación interna del equipo. No es un entregable del TP: los entregables son
> `investigacion.md`, `aplicacion.md`, el video y el zip con `ENTREGA.md`.

## 1. Situación de partida

| Qué | Estado | Quién |
|-----|--------|-------|
| Skill propia `revisar-escenarios` (creada con `skill-creator`, registrada, en `AGENTS.md`/`CLAUDE.md`) | Hecha | Matías |
| MCP Context7 (`.mcp.json`, guía en `mcp.md`, evidencia) | Hecho | Matías |
| Ficha `investigacion.md` (eligió C-06, compara Context7 y Semgrep MCP) | Hecha | Matías |
| C-06 `auth-jwt-roles` preparado con la skill y el MCP | **Implementado y archivado** | Matías |

**Problema con la consigna**: el TP pide preparar un change pendiente y dejarlo listo para implementar
(*"No lo marquen como implementado, verificado o archivado"*). C-06 llegó hasta el archivo. Además, el
equipo pasa a tener tres integrantes desde este TP, y todo lo anterior lo hizo una sola persona.

**Decisión**: C-06 queda como **antecedente**: la skill y el MCP se crearon y probaron ahí antes de
que se armara el equipo. El change del TP pasa a ser **C-08**, que se prepara entre los tres y queda en
"listo para Apply". El cambio de elección respecto de la ficha se explica en `aplicacion.md`, como pide el
punto 7.

## 2. Por qué C-08

- **Se puede preparar ya**: depende solo de C-06, que está archivado.
- **Está en el camino crítico**: C-10 y C-11 dependen de C-08.
- **Encaja con el reparto existente**: Lauti hace el Apply y Matías es el padrino. La implementación queda
  para después, como dice la consigna.
- **Tiene reglas concretas para que la skill controle**: `duracion_min > 0`, múltiplo de 5 y ≤ 480 (DD-15),
  `requiere_sillon`, desactivación lógica que conserva historial, escritura solo de la recepcionista
  (RN-AU-03).
- **Tiene una migración propia** (CHECK de duración). Como C-07 también tiene migración y va en la misma
  ola, el riesgo de dos `005` en paralelo es real (ver §5).

Scope y "Leer antes": `CHANGES.md` §C-08 (US-001; `04_modelo_de_datos.md` §Profesional/§Sillon/§Prestacion;
`05_reglas_de_negocio.md` §RN-AU-03).

## 3. Reparto

Se respeta `docs/equipo/reparto-de-tareas.md`: en los changes de Lauti, el Propose lo hace el padrino con
Claude.

| Paso | Quién | Herramienta | Qué produce | Criterio del TP que cubre |
|------|-------|-------------|-------------|---------------------------|
| 1. Reproducir el MCP | Nico | Claude Code en **su** máquina | Sigue `mcp.md` desde cero: aprueba `context7`, corre `claude mcp list` y una consulta real. Registra si algo de la guía no funcionó | Reproducibilidad: *"otro integrante debe poder seguir las instrucciones"* |
| 2. Explore de C-08 con Context7 | Nico | `/opsx:explore` + Context7 | Notas en `evidencias/c-08/explore-context7.md`: pregunta hecha, resultado y qué decisión de diseño fundamenta | MCP con una herramienta real, usada en la preparación |
| 3. Propose de C-08 | Matías (padrino) | `/opsx:propose` | `proposal.md`, `design.md`, specs y `tasks.md` en `openspec/changes/gestion-recursos-consultorio/` | Artefactos SDD, ≥ 3 escenarios, cómo se verifica cada uno |
| 4a. Skill desde Claude | Matías | `revisar-escenarios` | `revision-escenarios.md` del change | Uso real de la skill |
| 4b. Skill desde OpenCode | Lauti | OpenCode (modelo free), leyendo `SKILL.md` a mano | `evidencias/c-08/revision-opencode.md` | Portabilidad y compatibilidad con otro agente |
| 5. Comparar y corregir | Matías + Lauti | `/opsx:update` | Tabla comparando los dos informes; specs corregidos | Revisión crítica (punto 8) |
| 6. Verificar la skill en una sesión nueva | Lauti | OpenCode, sesión limpia | Captura: pregunta "¿cómo reviso los escenarios de C-08?" y el agente encuentra la skill por `AGENTS.md` | Punto 5: *"en una sesión nueva, comprueben..."* |
| 7. Roadmap | Matías | Edición a mano | En `CHANGES.md`, C-08 queda pendiente y con referencia a los artefactos. **No se marca `[x]`** | Punto 7 |
| 8. Informe y entrega | Los tres; integra Lauti | — | `aplicacion.md` actualizado, `ENTREGA.md` y el zip | Entrega |

### Consultas a Context7 que tienen sentido para C-08

Son preguntas genéricas, sin datos del proyecto (límite fijado en `CLAUDE.md`):

- Cómo declarar un `CheckConstraint` en SQLAlchemy 2 y crearlo en una migración de Alembic (`op.create_check_constraint`).
- Validadores de Pydantic v2 para un entero múltiplo de 5 dentro de un rango (`field_validator` frente a `Annotated` + `Field`).
- Actualización parcial en FastAPI (`PATCH` con `model_dump(exclude_unset=True)`).

Cada respuesta tiene que terminar en una línea concreta de `design.md`. Si no, no aporta nada al change.

### Ramas y commits

- `feat/c-08-gestion-recursos-consultorio`: artefactos del change (Matías) y revisiones (Matías y Lauti).
- `docs/tp-skills-mcp`: `aplicacion.md`, evidencias y `ENTREGA.md` (los tres).
- Un PR por rama, aprobado por alguien con Claude Pro. Conventional Commits: `docs(c-08): ...`, `docs(skills-mcp): ...`.
- **Cada uno commitea lo suyo con su usuario de git**: el historial es la prueba de participación que pide el TP.

## 4. Revisión crítica (punto 8)

Hay dos fuentes posibles. No hay que inventar el error.

1. **Hallazgos de la skill sobre el Propose**: si `revisar-escenarios` marca un escenario mal planteado,
   se muestra el escenario antes, el hallazgo con su regla RN/DD y el escenario después.
2. **Diferencias entre Claude y OpenCode**: un hallazgo que solo ve uno de los dos, o que cita una regla
   que no existe en la KB. Se verifica contra `knowledge-base/` y se documenta cuál tenía razón.

Si ninguno de los dos aparece, Lauti prueba un caso de borde. Por ejemplo, pasarle a la skill un escenario
que invade C-10 (horarios) y ver si lo marca como fuera de scope. El resultado se documenta tal cual.

## 5. Riesgo conocido: migraciones de C-07 y C-08 en paralelo

C-07 (auditoría, Matías) y C-08 (CHECK de duración) crean migración en la ola 1. Si los dos usan `005`,
git mergea sin conflicto, porque los nombres de archivo son distintos, pero quedan dos cabezas y
`alembic upgrade head` falla.

- El `tasks.md` de C-08 incluye una tarea explícita: *"antes del merge, renumerar la revisión respecto de
  `main` y verificar que `alembic heads` muestre una sola cabeza"*.
- Si aparece en la práctica, es buen material para la revisión crítica. También puede justificar en el
  futuro una skill o un chequeo de CI para migraciones (fuera del alcance de este TP).

## 6. Video (hasta 5 minutos)

### Guion

| Tramo | Quién | Duración | Qué se ve en pantalla |
|-------|-------|----------|-----------------------|
| Intro | Matías | 0:20 | Repo abierto; en una frase: el problema (agenda odontológica), la skill y el MCP elegidos, y el change C-08 |
| Skill: cómo nació | Matías | 0:50 | `skill-creator` en `.claude/skills/`, `SKILL.md` de `revisar-escenarios`, su fila en `.atl/skill-registry.md` y la sección en `CLAUDE.md`. Mención breve de C-06 como primera prueba |
| MCP: conexión y uso | Nico | 1:20 | `.mcp.json` (sin secretos), `claude mcp list` con context7 conectado, una consulta real durante el explore de C-08 y la línea de `design.md` que salió de ahí |
| Skill aplicada a C-08 | Matías | 0:50 | Invocación de `revisar-escenarios` sobre C-08, veredicto y un hallazgo con su regla RN/DD |
| Otra herramienta y revisión crítica | Lauti | 1:20 | Sesión nueva en OpenCode donde el agente encuentra la skill por `AGENTS.md`, el informe de OpenCode al lado del de Claude, la diferencia encontrada y el antes y el después del spec |
| Cierre | Lauti | 0:20 | C-08 en `CHANGES.md` como pendiente y listo para Apply; qué queda para la instancia siguiente |

Total: 5:00. Si se pasa, recortar la intro y el tramo de cómo nació la skill, nunca el uso real.

### Qué grabar (y guardar como evidencia aunque no entre en el video)

- [ ] `claude mcp list` con `context7` conectado, en la máquina de Nico.
- [ ] La consulta a Context7 completa: solicitud, respuesta y la parte de `design.md` que fundamenta.
- [ ] La invocación de `revisar-escenarios` en Claude y el informe generado.
- [ ] Una sesión **nueva** de OpenCode encontrando la skill sin que se la nombre.
- [ ] El informe de OpenCode y la comparación con el de Claude.
- [ ] El antes y el después de un escenario (diff de git o dos capturas).
- [ ] `git log` mostrando commits de los tres autores.

El TP dice que *"mostrar únicamente una lista de herramientas instaladas no acredita su uso"*: cada captura
de una lista tiene que ir acompañada de una ejecución.

### Antes de grabar

- [ ] Cerrar `.env`, pestañas y terminales con tokens. Revisar que no se vea ninguna variable con secretos.
- [ ] Solo datos ficticios en pantalla (los del seed).
- [ ] Letra de terminal y editor grande (≥ 16 px) y tema claro u oscuro, pero el mismo para los tres.
- [ ] Cada uno graba su tramo por separado (OBS o la grabadora del sistema) y uno solo edita. Así ninguno
      depende de que los tres coincidan en horario.
- [ ] Ensayar con cronómetro: hablar del **porqué** de cada decisión, no leer la pantalla.
- [ ] Subir el video con un enlace accesible sin login y probarlo en una ventana privada antes de ponerlo
      en `ENTREGA.md`.

## 7. Cambios a los entregables existentes

| Archivo | Cambio | Quién |
|---------|--------|-------|
| `docs/skills-mcp/aplicacion.md` | Pasa a centrarse en C-08; C-06 queda como antecedente en un párrafo. Agregar: motivo del cambio de change, reparto entre los tres y revisión crítica. Máximo 2 páginas | Los tres; integra Lauti |
| `docs/skills-mcp/investigacion.md` | No se reescribe (se presentó en clase). Como mucho, una nota al pie que remita a `aplicacion.md` por el cambio de change | Matías |
| `docs/skills-mcp/evidencias/c-08/` | Carpeta nueva con las evidencias del §6 | Los tres |
| `ENTREGA.md` | Integrantes, enlace al repo, commit de entrega y enlace al video | Lauti |
| `CHANGES.md` | Referencia a los artefactos de C-08; sigue `[ ]` | Matías |

## 8. Pendientes de decidir

- Fecha de entrega y fecha límite interna para tener grabado cada tramo.
- Dónde se sube el video (Drive, YouTube no listado, etc.).
- Confirmar con el docente que presentar C-06 como antecedente y C-08 como change del TP es aceptable.
