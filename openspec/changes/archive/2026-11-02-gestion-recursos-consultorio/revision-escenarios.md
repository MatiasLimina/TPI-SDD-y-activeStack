# Revisión de escenarios — gestion-recursos-consultorio (C-08)

- Fecha: 2026-11-02
- Specs revisados: `openspec/changes/gestion-recursos-consultorio/specs/gestion-recursos/spec.md`, `openspec/changes/gestion-recursos-consultorio/specs/catalogo-consultorio/spec.md` (contrastados con `proposal.md`, `design.md`, `tasks.md`, `CHANGES.md` §C-08 y los specs archivados `catalogo-consultorio`, `agenda-turnos` y `autenticacion`)
- Reglas aplicables: RN-AG-04, RN-AG-10, RN-AU-01, RN-AU-02 (para descartar que restrinja el catálogo), RN-AU-03, RN-CU-02, RN-CU-03, DD-05, DD-08, DD-15, DD-16 (baja lógica), DD-18, DD-21, DD-23 (criterio `campo_no_editable`), DD-24 (`401`/`403`), US-001, matriz de `03_actores_y_roles.md`. Decisiones del change confirmadas por el usuario el 2026-11-02 y que se registran como DD-26 en la tarea 10.1: D5, D6, D7, D9, D11 y D12 (se tratan como decisiones aprobadas).
- Veredicto: **LISTO PARA APPLY**

`openspec validate gestion-recursos-consultorio --strict`: válido.

## Cobertura

| Requirement | Escenarios | Esperado | Error de negocio | Borde | Reglas cubiertas |
|-------------|-----------:|:--------:|:----------------:|:-----:|------------------|
| Alta de profesional | 2 | 2 | 0 | 0 | US-001 |
| Alta de sillón | 1 | 1 | 0 | 0 | US-001 |
| Alta de prestación con duración por defecto | 2 | 2 | 0 | 0 | RN-AG-10, US-001 |
| Duración de la prestación validada por la API | 6 | 0 | 3 | 3 | RN-AG-04, DD-15 |
| Atributos obligatorios y textos normalizados | 4 | 1 | 1 (validación) | 2 | D9, `catalogo-consultorio` §Atributos obligatorios |
| Identificadores naturales duplicados | 3 | 0 | 2 | 1 | D7, `catalogo-consultorio` §Unicidad |
| Edición parcial de un recurso | 6 | 3 | 1 | 2 | DD-21 (`404` del path), criterio de DD-23 a |
| Estado de actividad no editable | 2 | 0 | 2 | 0 | D6, criterio de DD-23 b |
| Consulta de recursos | 5 | 3 | 2 | 0 | D13, D14, DD-21 |
| Desactivación lógica de un recurso | 5 | 3 | 1 | 1 | D5, D12, DD-16 (baja lógica), DD-21 |
| Un recurso desactivado no admite turnos nuevos | 3 | 0 | 3 | 0 | US-001, DD-21 c |
| Un recurso desactivado conserva sus turnos | 3 | 2 | 0 | 1 | US-001, DD-08, D11 |
| Editar una prestación no altera los turnos existentes | 1 | 1 | 0 | 0 | RN-AG-04 |
| Desactivación y alta de turno simultáneas | 2 | 0 | 0 | 2 | D10, DD-18 |
| Escritura de recursos reservada a la recepcionista | 5 | 0 | 3 | 2 | RN-AU-03, DD-05, DD-24 b |
| Lectura de recursos para ambos roles | 3 | 1 | 1 | 1 | RN-AU-03, matriz de 03, DD-24 b |
| (catalogo-consultorio) Duración de la prestación en la grilla de 5 minutos | 5 | 0 | 2 | 3 | DD-15, RN-AG-04 |
| **Total** (antes de las correcciones; ver el final del informe) | **58** | **19** | **21** | **18** | |

C1 (tres tipos mínimos): cumplido. Esperado (altas `201`), error de negocio (`422 duracion_invalida`, `409 recurso_duplicado`, `422 referencia_invalida` por inactiva, `403 rol_insuficiente`) y borde (5 y 480 aceptados, 485 rechazado, contiguo de `[5, 480]` en API y en BD, concurrencia).

C9 (tareas): todos los escenarios tienen tarea que los verifica (6.1–6.6, 7.1, 7.2, 8.2–8.4, 4.2).

Reglas del scope sin escenario: ninguna. Las tres líneas de scope de `CHANGES.md` §C-08 (CRUD con desactivación lógica; duración > 0, múltiplo de 5 y ≤ 480 con CHECK; escritura solo recepcionista) y los dos criterios de tests (CRUD por rol; desactivación bloquea turnos nuevos con `422` y conserva los existentes) tienen escenarios.

## Hallazgos

### H1 — Escrituras rechazadas sin estado observable en el THEN · MENOR
- **Dónde**: `gestion-recursos/spec.md`, escenarios "Duración fuera de la grilla rechazada" (l. 62), "Prestación con nombre repetido" (l. 104), "Alta con una prestación desactivada" (l. 214) y "Rol evaluado antes que el body" (l. 280)
- **Problema**: el THEN solo da el código; no dice "no se persiste ninguna prestación/ningún turno". Por C5 sería `MAYOR`, pero se baja a `MENOR`: el texto normativo de cada requirement ya exige "sin persistir ni modificar" y las tareas 6.2 y 7.2 lo verifican para la duración 7 y para el `403`. Quedan sin aserción de estado en `tasks.md` la prestación duplicada (6.4) y el alta con prestación desactivada (8.2).
- **Fuente**: `references/controles.md` C5; texto de los requirements "Duración de la prestación validada por la API", "Identificadores naturales duplicados" y "Un recurso desactivado no admite turnos nuevos"
- **Sugerencia**: agregar al THEN "… y no se persiste ninguna prestación" (l. 64), "… y sigue existiendo una sola prestación «Limpieza»" (l. 107), "… y no se persiste ningún turno" (l. 217) y "… y no se persiste ninguna prestación" (l. 283), y llevar esas aserciones a 6.4 y 8.2.

### H2 — Turnos sin fecha, sin offset y sin reloj fijo en el spec · MENOR
- **Dónde**: `gestion-recursos/spec.md`, "Alta con un sillón desactivado" ("un horario futuro libre"), "Reprogramación hacia un profesional desactivado", "Turno futuro intacto tras desactivar su profesional" ("10:00 a 10:45"), "Cancelación de un turno cuyo sillón fue desactivado", "Nueva duración por defecto" ("10:00 a 10:45", "15:00")
- **Problema**: el resultado depende de "ahora" (RN-AG-12 para crear/reprogramar, RN-AG-13 para cancelar) y los instantes no tienen fecha ni zona. Es `MENOR` y no `MAYOR` porque `tasks.md` fija el reloj (cabecera: "reloj fijo inyectado (`get_reloj`) en los tests que crean turnos"; 8.2 lo repite explícito). La 8.3 no lo repite, pero la cabecera la alcanza.
- **Fuente**: C6; RN-CU-04, DD-06
- **Sugerencia**: GIVEN común "el reloj marca 2026-11-09 08:00 -03:00" y horarios "2026-11-10 10:00-03:00 a 10:45-03:00", "2026-11-10 15:00-03:00"; nombrar explícitamente el reloj fijo en la 8.3.

### H3 — "Rol evaluado antes que el body" no discrimina la validación del schema · MENOR
- **Dónde**: `gestion-recursos/spec.md`, requirement "Escritura de recursos reservada a la recepcionista", escenario "Rol evaluado antes que el body" (l. 280-283); tarea 7.2
- **Problema**: con `duracion_min = 7` el `422` lo produce el **dominio** (D2), dentro del handler, así que el `403` sale igual aunque FastAPI validara el body antes que la dependencia. El escenario no puede fallar por la propiedad que dice probar ("antes que el body"). El orden respecto de la validación Pydantic, que es la que puede ganarle a la dependencia, queda sin verificar.
- **Fuente**: C5 (verificabilidad); texto del requirement ("Autenticación y rol MUST evaluarse antes que el body"); design §2 "Orden de evaluación"
- **Sugerencia**: mantener el caso y sumar uno con un body que falle en el schema: "WHEN un odontólogo autenticado envía `POST /sillones` con `{}` (sin `nombre`) THEN la respuesta es `403`, no `422`".

### H4 — El escenario (b) de concurrencia pasa sin el cambio a `FOR SHARE` si no se afirma la espera · MENOR
- **Dónde**: `gestion-recursos/spec.md`, "Desactivación que espera a un alta en curso" (l. 258-261); tarea 8.4 (b)
- **Problema**: sin `FOR SHARE`, el `UPDATE` de la desactivación no espera (el `FOR KEY SHARE` del `INSERT` es compatible con `FOR NO KEY UPDATE`, design §4) y el estado final es el mismo que el THEN: turno con el sillón 1 y sillón inactivo. Solo "la desactivación espera al alta" distingue el comportamiento correcto, y la 8.4 exige RED real solo para (a).
- **Fuente**: C5; requirement "Desactivación y alta de turno simultáneas" ("Nunca MUST quedar un turno nuevo con una referencia que ya estaba inactiva al confirmarse"); design §4
- **Sugerencia**: volver observable la espera en el THEN, por ejemplo "… la desactivación no termina mientras el alta no confirma (con `lock_timeout` corto falla con `lock_not_available`)", y pedir en 8.4 que (b) también se vea fallar antes del cambio.

### H5 — Cláusulas normativas sin escenario · MENOR
- **Dónde**: `gestion-recursos/spec.md`
  - "Atributos obligatorios y textos normalizados": "no superar el largo de su columna; si no, `422`" (l. 72). No tiene escenario **ni tarea**. Design §2 dice que esa validación evita un `500` en la base.
  - "Edición parcial de un recurso": "Los campos desconocidos MUST ignorarse" (l. 110). Tiene tarea (6.5) pero no escenario.
  - "Desactivación y alta de turno simultáneas": "o reprogramación" (l. 251). No tiene escenario ni tarea; solo se prueba el alta.
- **Problema**: con TDD estricto, una cláusula sin escenario puede quedar sin test o con un test que no deriva del spec.
- **Fuente**: C2/C9; design §2 (largos 100/100/50/100 y matrícula 30) y §4 (la reprogramación usa el mismo `cargar_referencias`)
- **Sugerencia**: (1) escenario "`POST /sillones` con un `nombre` de 51 caracteres → `422` y no se persiste ningún sillón" y su caso en 6.1. (2) Escenario "`PATCH /sillones/{id}` con `{\"color\": \"azul\"}` → `200` sin cambios". (3) Agregar un escenario de reprogramación concurrente con la desactivación, o acotar el texto del requirement al alta. Como la reprogramación usa el mismo mecanismo, alcanza con acotar el texto.

### H6 — Requirements de dominio sin citar su decisión · MENOR
- **Dónde**: `gestion-recursos/spec.md`, requirements "Atributos obligatorios y textos normalizados" (D9), "Identificadores naturales duplicados" (D7), "Edición parcial de un recurso" (D4/DD-23 a), "Estado de actividad no editable" (D6/DD-23 b), "Consulta de recursos" (D13/DD-21), "Desactivación lógica de un recurso" (D5, D12, DD-21), "Desactivación y alta de turno simultáneas" (D10, DD-18)
- **Problema**: fijan comportamiento que la KB no fija o que deriva de una DD, pero no lo citan. Al archivar, el spec principal pierde la trazabilidad hacia la DD-26.
- **Fuente**: C2 ("cada requirement que fija un comportamiento de dominio debería citar su regla")
- **Sugerencia**: citar "DD-26" (o "DD-26, D7", etc.) en cada uno al registrar la DD en la tarea 10.1, antes del archive.

### H7 — Lecturas "autenticado" sin rol nombrado · MENOR
- **Dónde**: `gestion-recursos/spec.md`, "Profesionales por apellido", "Detalle de una prestación", "Detalle inexistente", "Identificador mal formado", "Recurso desactivado sigue consultable"
- **Problema**: "se envía … autenticado" no dice con qué rol. No cambia el resultado (ambos roles leen, D14), pero C5 pide el rol con su nombre exacto.
- **Fuente**: C5 (valores concretos)
- **Sugerencia**: "cuando una recepcionista autenticada envía …"; el caso del odontólogo ya está en "Odontólogo lee el catálogo completo".

### H8 — Tareas que verifican comportamiento sin escenario · SUGERENCIA
- **Dónde**: `tasks.md` 6.2 (`45.0` → `201` y `45.5` → `422`), 6.5 ("body inválido sobre un UUID inexistente → `422`, no `404`", orden de design §2), 7.2 (`PUT`/`DELETE` → `405`), 9.1 (conjunto exacto de rutas en OpenAPI)
- **Problema**: son comportamientos del framework o del design, legítimos, pero el spec no los menciona. La regla dura dice que Apply no implementa lo que no está en el spec: acá solo se prueban, no se agrega comportamiento.
- **Fuente**: C9 (tareas sin escenario → `SUGERENCIA`)
- **Sugerencia**: el equipo decide. Lo que tiene más valor de contrato es el orden `422` antes que `404`; si se quiere fijar, agregarlo como escenario de "Edición parcial de un recurso".

### H9 — Consecuencias aceptadas en Risks sin escenario que las documente · SUGERENCIA
- **Dónde**: `design.md` §Risks; `gestion-recursos/spec.md`, requirement "Un recurso desactivado conserva sus turnos"
- **Problema**: el design acepta que un turno futuro con prestación (o paciente) desactivada, o con su profesional o sillón desactivado, no se pueda reprogramar sin cambiar ese recurso. Pasa porque "Misma validación que el alta al reprogramar" de `agenda-turnos` revalida todas las referencias del turno resultante. También acepta que cambiar `requiere_sillon` haga que reprogramar aplique la regla nueva. El spec solo dice que esos turnos "se pueden cancelar". El comportamiento ya está especificado en `agenda-turnos`, así que no es un faltante, pero sí es la consecuencia de este change que más le va a sorprender a la recepcionista.
- **Fuente**: design §Risks; `agenda-turnos` §"Misma validación que el alta al reprogramar"; D11 (confirmada)
- **Sugerencia**: opcional, un escenario "GIVEN un turno futuro de «Limpieza» y «Limpieza» desactivada WHEN se reprograma solo el `inicio` THEN `422` con `referencia = prestacion` y el turno no cambia", o dejarlo solo en DD-26 (tarea 10.1).

### H10 — Unicidad sensible a mayúsculas no explicitada en el spec · SUGERENCIA
- **Dónde**: `gestion-recursos/spec.md`, requirement "Identificadores naturales duplicados"
- **Problema**: el spec dice "comparados tras quitar los espacios", pero no que la comparación distingue mayúsculas. El design (Risks) lo decide: "Sillón 1" y "sillón 1" conviven, como el `UNIQUE` de C-02.
- **Fuente**: design §Risks; `catalogo-consultorio` §Unicidad (archivado)
- **Sugerencia**: agregar "comparación exacta (distingue mayúsculas y acentos)" al texto del requirement. No agregar normalización: sería una regla nueva sin respaldo en la KB.

### H11 — Texto de "Prestación con duración positiva" queda incompleto frente a DD-15 · SUGERENCIA
- **Dónde**: `openspec/specs/catalogo-consultorio/spec.md` (archivado), requirement "Prestación con duración positiva"; delta `catalogo-consultorio` (ADDED)
- **Problema**: el texto archivado dice "duración … estrictamente mayor que cero", y desde este change 1 o 600 se rechazan. No hay contradicción formal: el ADDED lo aclara, el único escenario archivado usa 45 y la tarea 4.2 ajusta el test parametrizado `[1, 45, 600]`. Aun así, quien lea solo ese requirement puede entender que cualquier positivo es válido.
- **Fuente**: DD-15; proposal §Capabilities ("no cambia")
- **Sugerencia**: el equipo decide si pasarlo a MODIFIED con una remisión al requirement nuevo, o dejarlo como está (decisión ya tomada en la proposal).

## Preguntas abiertas

Ninguna nueva. Las decisiones que la KB no tomaba (desactivación idempotente, sin reactivación, `409` por duplicado, matrícula vacía como nula, desactivación con turnos futuros permitida, usuario `odontologo` intacto) están confirmadas por el usuario (2026-11-02) y pasan a DD-26 en la tarea 10.1. El backlog ya tiene la reactivación de recursos (tarea 10.1) y la advertencia en la UI (C-14..C-16).

## Fuera de esta revisión

- **Inconsistencia de la KB, no del spec**: `02_descripcion_general.md` §API dice "Sillones: CRUD (recepcionista)" y "Prestaciones: CRUD … (recepcionista)", sin la lectura del odontólogo, mientras que la matriz de `03_actores_y_roles.md` (R) y US-001 ("el odontólogo solo puede leer") sí la incluyen. El spec sigue a 03 y US-001, que es lo correcto, y la tarea 10.1 alinea 02. La matriz dice "CRUD", pero la "D" se implementa como desactivación lógica (US-001, `catalogo-consultorio` §"Recursos … activos por defecto"): no es un faltante.
- **D5 frente a DD-22**: desactivar dos veces responde `200` (D5) y cancelar dos veces un turno, `409` (DD-22). No se contradicen: DD-22 es de turnos y D5 está confirmada y se apoya en DD-24 h. Queda señalado para que DD-26 lo diga explícitamente.
- **No verificado**: el orden real dependencia → validación de body en la versión instalada de FastAPI (tarea 1.2 y riesgo C7-3); que la 8.4 (a) muestre un RED real antes de cambiar `cargar_referencias` (se comprueba en Apply).

## Correcciones aplicadas (2026-11-02)

Con `/opsx:update`, aprobadas por el usuario. H2, H7 y las SUGERENCIA H8..H11 quedan sin cambios, a propósito.

- **H1**: "Duración fuera de la grilla rechazada" y "Alta con una prestación desactivada" afirman "no se persiste ninguna prestación / ningún turno". "Prestación con nombre repetido" afirma que sigue existiendo una sola "Limpieza" con su duración original. El caso del rol se resolvió junto con H3. En `tasks.md`, 6.4 suma esas aserciones de estado para la prestación y la matrícula duplicadas, 8.2 suma "sin turno" para la prestación desactivada y 7.2 suma "sin filas nuevas" para el caso del rol. La 6.2 ya cubría la duración 7.
- **H3**: "Rol evaluado antes que el body" usa ahora `POST /sillones` con `{}`, un body que rechaza el schema de Pydantic, como odontólogo → `403`, no `422`, y sin sillones nuevos. Conserva el caso `duracion_min = 7` (lo rechaza el dominio), con su aserción de estado. La 7.2 se actualizó igual y aclara que el caso `{}` es el que prueba el orden.
- **H4**: el THEN de "Desactivación que espera a un alta en curso" afirma la espera: la desactivación no termina mientras el alta no confirma, y recién después responde `200`. La 8.4 (b) exige observarla (`pg_locks`/`pg_stat_activity` o `lock_timeout` → `lock_not_available`) y pide RED real en (a), (b) y (c) antes de tocar `cargar_referencias`. **Matiz al hallazgo**: sin `FOR SHARE`, la desactivación no espera solo si el alta todavía no hizo el `INSERT`. Después del `INSERT`, el `FOR KEY SHARE` de la FK choca con el `FOR UPDATE` de `obtener_para_actualizar`. Por eso la 8.4 (b) fija el punto de detención (después de `cargar_referencias`, antes del `INSERT`), y design §4 lo explica.
- **H5**: (1) escenario nuevo "Nombre más largo que su columna rechazado" (sillón de 51 caracteres → `422`, no `500`, sin persistir) y su caso en 6.1. (2) Escenario nuevo "Campo desconocido ignorado" (`PATCH /sillones/{id}` con `{"color": "azul"}` → `200` sin cambios), con la 6.5 alineada. (3) Se agregó un escenario en vez de acotar el texto, porque design §4 ya cubre la reprogramación con el mismo lock (pasa por el mismo `cargar_referencias`). El escenario nuevo es "Reprogramación que espera a una desactivación en curso" y su tarea es la 8.4 (c). El requirement pasó a llamarse "Desactivación simultánea con un alta o una reprogramación de turno" y se acortó su texto (`--strict` avisaba de más de 500 caracteres). Design (D10, §4, Risks) y proposal se alinearon.
- **H6** (parcial): "(DD-26)" agregado en "Atributos obligatorios y textos normalizados" (D9), "Identificadores naturales duplicados" (D7), "Estado de actividad no editable" (D6), "Desactivación lógica de un recurso" (D5, D12) y "Un recurso desactivado conserva sus turnos" (D11). La 10.1 avisa que, si se renumera la DD, hay que renumerar también esas citas. Los demás requirements de H6 (D4, D10, D13) quedan como estaban.

Resultado: 16 requirements y 56 escenarios en `gestion-recursos` (antes 53), 5 en `catalogo-consultorio`, 61 en total (antes 58). `openspec validate gestion-recursos-consultorio --strict`: válido.
