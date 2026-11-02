# Aplicación de la skill propia y del MCP en un change real

Proyecto: Turnos y Agenda para Consultorios Odontológicos · Fecha: 2026-10-28 · Actualizado: 2026-11-02 · Change del TP: `C-08` `gestion-recursos-consultorio` · Antecedente: `C-06` `auth-jwt-roles`

Este documento sigue a [investigacion.md](investigacion.md): allí se justificó qué skill y qué MCP se
instalaban; acá se registra cómo se usaron para preparar un change real, con la evidencia de cada paso.

## 1. Qué change se presenta y por qué cambió

La ficha de investigación eligió **C-06**. La skill y el MCP se crearon y probaron ahí (ver §6), pero C-06
llegó hasta el archivo, y la consigna pide un change "listo para implementar", sin marcarlo como implementado.
Por eso el change del TP pasó a ser **C-08** (profesionales, sillones y prestaciones):

- Dependía solo de C-06, ya archivado, y está en el camino crítico (C-10 y C-11 dependen de él).
- Tiene reglas concretas para que la skill controle: duración `> 0`, múltiplo de 5 y `≤ 480` (DD-15),
  desactivación lógica que conserva el historial y escritura solo de la recepcionista (RN-AU-03).
- Tiene una migración propia con un CHECK y elige APIs de Pydantic, Alembic, FastAPI y SQLAlchemy, que es
  donde sirve un MCP de documentación.

**Estado que se presenta**: con el reparto del 2026-11-02 (`docs/equipo/reparto-de-tareas.md`), C-08 se
implementó en la misma semana porque está en el camino crítico. El estado "listo para Apply" que pide la
consigna es el commit **`01c6b1c`**:

| Commit | Contenido |
|---|---|
| `9d120f3` `docs(c-08): propose gestion-recursos-consultorio` | `proposal.md`, `design.md`, 2 delta specs y `tasks.md`, ya con las correcciones de la revisión |
| `01c6b1c` `docs(c-08): add scenario review for gestion-recursos-consultorio` | `revision-escenarios.md`, veredicto **LISTO PARA APPLY** |

Ninguno de los dos tiene código: la implementación empieza en `cf88d63`. Se puede ver con
`git checkout 01c6b1c`. Los mismos artefactos quedaron en
[openspec/changes/archive/2026-11-02-gestion-recursos-consultorio/](../../openspec/changes/archive/2026-11-02-gestion-recursos-consultorio/).

**Reparto**: Matías hizo el propose, las consultas a Context7 y la revisión con la skill. Nico reproduce la
guía del MCP en su máquina, verifica la skill en una sesión nueva e integra la entrega. Lauti sigue en el
equipo, pero esta semana no tiene pasos asignados (ver
[plan-preparacion-c08.md](plan-preparacion-c08.md)).

## 2. Uso del MCP Context7

**Cuándo**: durante el `/opsx:propose` de C-08, antes de fijar en `design.md` cualquier API de terceros.
Evidencia completa, con las fuentes: [evidencias/c-08/explore-context7.md](evidencias/c-08/explore-context7.md).

**Regla de privacidad**: todas las consultas fueron genéricas sobre la librería. No se envió código del
proyecto, secretos, `.env` ni datos de pacientes (límite fijado en [mcp.md](mcp.md)).

| Biblioteca (id) | Pregunta | Qué decidió en `design.md` |
|---|---|---|
| Pydantic (`/websites/pydantic_dev_validation`) | `gt`, `le` y `multiple_of` en un `int`; si acepta `float` | **No** se usa `Field(multiple_of=5, le=480)`: el `422` tendría otra forma que el `{"detail": {"codigo": "duracion_invalida"}}` de los turnos. La regla vive en una función de dominio compartida (D2). El caso `45.0` aceptado y `45.5` rechazado pasó a ser un test |
| Alembic (`/websites/alembic_sqlalchemy`) | `op.create_check_constraint` con convención de nombres | Sin `op.f()` la convención de `base.py` duplicaría el prefijo `ck_prestacion_`. La migración `006` usa `op.f()` con el nombre completo (D3) |
| FastAPI (`/websites/fastapi_tiangolo`) | `PATCH` parcial y `null` explícito frente a campo omitido | La edición toma solo `model_fields_set` y rechaza `null` en campos obligatorios (D4). El cambio de la 0.151.0 quedó como riesgo y una tarea verifica la versión instalada |
| SQLAlchemy (`/websites/sqlalchemy_en_20_orm`) | `Session.get` con `with_for_update` y `populate_existing` | Las referencias de un turno se leen con `FOR SHARE` y relectura forzada: el alta espera a una desactivación en curso (D10) |

**Qué no decidió Context7**: el `409 recurso_duplicado`, la desactivación idempotente, la falta de
reactivación y qué pasa con los turnos de un recurso desactivado salen de la KB o de decisiones confirmadas
por el usuario, que quedaron registradas como **DD-26**.

## 3. Uso de la skill `revisar-escenarios`

**Cuándo**: entre el propose y el apply, como indica el paso 5 del flujo en `CLAUDE.md`. Solo reporta; las
correcciones pasan por `/opsx:update`, así que la decisión sigue siendo humana. Controles C1–C9 y formato
en [SKILL.md](../../.agents/skills/revisar-escenarios/SKILL.md).

Informe: [revision-escenarios.md](../../openspec/changes/archive/2026-11-02-gestion-recursos-consultorio/revision-escenarios.md).
Revisó 58 escenarios en 17 requirements, contra RN-AG, RN-AU, RN-CU, DD-05 a DD-24 y US-001. Veredicto:
**LISTO PARA APPLY**, con 0 bloqueantes, 0 mayores, 7 menores y 4 sugerencias. Todas las reglas del scope de
`CHANGES.md` §C-08 tenían escenario, y cada escenario tenía una tarea que lo verifica.

| Id | Sev. | Hallazgo | Decisión |
|---|---|---|---|
| H1 | MENOR | Rechazos cuyo THEN da solo el código, sin afirmar "no se persiste nada" | Corregir: se agregaron las aserciones de estado al spec y a las tareas |
| H3 | MENOR | "Rol evaluado antes que el body" no distinguía la validación del schema | Corregir: el caso pasa a `POST /sillones` con `{}` → `403`, no `422` |
| H4 | MENOR | El test de concurrencia (b) pasaba aunque faltara el `FOR SHARE` | Corregir, con un matiz (ver §5) |
| H5 | MENOR | Cláusulas del spec sin escenario (nombre demasiado largo, campo desconocido, reprogramación concurrente) | Corregir: 3 escenarios nuevos |
| H6 | MENOR | Requirements sin citar la decisión que los respalda | Corregir en parte: se citó DD-26 |
| H2, H7 | MENOR | Turnos sin reloj fijo en el spec; lecturas sin rol nombrado | Sin cambios: `tasks.md` ya fija el reloj y el rol |
| H8–H11 | SUGERENCIA | Tareas sin escenario, riesgos sin escenario, mayúsculas, texto de DD-15 | Sin cambios, a propósito |

Además señaló una inconsistencia **de la KB, no del spec**: `02_descripcion_general.md` decía "CRUD
(recepcionista)" sin la lectura del odontólogo, que sí figura en `03_actores_y_roles.md` y en US-001. Se
alineó `02` en el apply.

## 4. Resultado medible

| Medida | Antes | Después |
|---|---|---|
| Escenarios | 58 (propose) | 61 (tras `/opsx:update`) |
| Hallazgos MENOR | 7 | 2, dejados sin cambios con motivo |
| Decisiones de diseño sin registro en la KB | 6 (D5, D6, D7, D9, D11, D12) | 0, registradas en DD-26 |
| Tests (`pytest`) | 741 de base | 945 tras el apply |

Apply: 28 de 28 tareas con TDD estricto, `ruff` limpio, `alembic heads` con una sola cabeza (`006`) y
revisión final del advisor sin bloqueos. Entró a `main` por el PR #5.

## 5. Revisión crítica

**La skill se equivocó en parte en H4.** Decía que, sin `FOR SHARE`, la desactivación de un sillón nunca
espera a un alta de turno en curso. Al revisar el diseño se vio que eso vale solo si el alta todavía no hizo
el `INSERT`: después del `INSERT`, el lock de la clave foránea ya choca con el `FOR UPDATE` de la
desactivación. Si se seguía la sugerencia tal cual, el test podía quedar verde por la razón equivocada. La
corrección fija dónde se detiene el alta en el test (después de leer las referencias y antes del `INSERT`) y
exige ver el test en rojo antes del cambio. El matiz quedó escrito en el informe y en `design.md` §4.

Controles sobre el resto del informe:

- Cada hallazgo cita una regla o un control que existe (C5, DD-15, RN-AU-03, DD-24) y dice eso.
- Ningún escenario sugerido introduce una regla nueva: las decisiones que la KB no tomaba se confirmaron
  antes con el usuario y pasaron a DD-26.
- Nada de lo que marcó como faltante es de otro change: no pidió horarios (C-10) ni bloqueos (C-11).

## 6. Antecedente: C-06 `auth-jwt-roles`

La skill y el MCP se usaron por primera vez en C-06, el 2026-10-28, en el ciclo OPSX completo:

- **Context7** fundamentó el uso de `pwdlib`, `PyJWT` y la seguridad de FastAPI. En un caso **prevaleció la
  KB**: el tutorial de FastAPI responde `400` al usuario inactivo, pero el diseño mantuvo `401` uniforme para
  no revelar que la cuenta existe (DD-24). Detalle en
  [design.md](../../openspec/changes/archive/2026-10-28-auth-jwt-roles/design.md).
- **La skill** hizo dos pasadas. La primera dio **CORREGIR ANTES DE APPLY**, con 3 mayores, y obligó a crear
  DD-24 ([v1](../../openspec/changes/archive/2026-10-28-auth-jwt-roles/revision-escenarios-v1.md)). La
  segunda dio **LISTO PARA APPLY**
  ([v2](../../openspec/changes/archive/2026-10-28-auth-jwt-roles/revision-escenarios.md)). El change pasó de
  89 a 97 escenarios.
- **Lo que la skill no ve**: el advisor encontró problemas de diseño de tests y una fuga del hash en un
  camino de error del CLI, y un byte NUL en `tasks.md` solo lo detectó `git`. La skill revisa escenarios
  contra la KB, no el diseño técnico ni el código.

## 7. Archivos de la fundación

Comparación con lo previsto en [investigacion.md](investigacion.md) §5. Todos existen en el repo.

| Archivo | Estado |
|---|---|
| `.agents/skills/revisar-escenarios/` (`SKILL.md`, `references/`, `evals/`) | Creado según lo previsto; evals en [evidencias/skill-evals/](evidencias/skill-evals/) |
| `.agents/skills/skill-creator/`, `skills-lock.json` | Presentes, con origen fijado |
| `.claude/skills/revisar-escenarios` | Junction para que Claude Code la vea |
| `.atl/skill-registry.md` | Con la fila y las compact rules de la skill |
| `AGENTS.md` y `CLAUDE.md` | Rol "Revisión de specs", sección de la skill, sección de integraciones MCP y paso 5 del flujo |
| `.mcp.json` | Servidor `context7`, sin secretos |
| `docs/skills-mcp/` (`investigacion.md`, `mcp.md`, `evidencias/`, este archivo) | Documentación y evidencia |
| `knowledge-base/` y `CHANGES.md` | **Cambiaron**: DD-24 (C-06) y DD-26 (C-08). Difiere de lo previsto en §5, donde la KB no se tocaba: aquel supuesto valía para las herramientas, pero las revisiones sí produjeron decisiones de dominio |

## 8. Conclusión

En C-08 cada pieza aportó algo distinto. Context7 cambió dos decisiones de diseño: dejar la duración fuera
de `Field` y usar `op.f()` en la migración. La skill dejó el spec más verificable antes de escribir código y
obligó a registrar DD-26. El caso de H4 muestra que sus sugerencias también se revisan: un hallazgo correcto
en el fondo traía una explicación incompleta, y aplicarlo tal cual habría dado un test engañoso. Ninguna de
las dos reemplaza la revisión humana ni la del código; sí acortaron el camino hasta un Apply con el spec
cerrado.
