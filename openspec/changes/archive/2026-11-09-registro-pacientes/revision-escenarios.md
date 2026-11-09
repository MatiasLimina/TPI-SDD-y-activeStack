# Revisión de escenarios — registro-pacientes (C-09)

> **Actualización**: los hallazgos H1 a H11 se resolvieron con `/opsx:update` el 2026-11-09. P1 quedó resuelta como fuera de alcance. H12 no se aplicó. El resto del informe es la revisión original.

- Fecha: 2026-11-09
- Specs revisados: `openspec/changes/registro-pacientes/specs/registro-pacientes/spec.md` (20 requirements, 86 escenarios)
- Reglas aplicables: US-009, `04` §Paciente, matriz de `03` (fila Pacientes), RN-CU-01, RN-CU-02, RN-AU-01, RN-AU-02, RN-NO-01, RN-NO-02, RN-NO-05, DD-21 (c), DD-24 (b), DD-26 (a, c, d, e, f, g, i, j), DD-27 (i), DD-28 (f), DD-29 (a), DD-30 (l), requirement "Documento único" de `catalogo-consultorio`
- Veredicto: **CORREGIR ANTES DE APPLY**
- Conteo: 0 BLOQUEANTE · 2 MAYOR · 9 MENOR · 1 SUGERENCIA

Además de los hallazgos, la tarea 1.2 frena el Apply mientras las 13 decisiones **[A confirmar]** no estén aprobadas. Su evaluación está en "Preguntas abiertas".

## Cobertura

Clasificación: esperado, error de negocio (una RN/DD rechaza la operación) y borde.

| Requirement | Escenarios | Esperado | Error de negocio | Borde | Reglas cubiertas |
|-------------|-----------:|:--------:|:----------------:|:-----:|------------------|
| Alta de paciente | 3 | 3 | 0 | 0 | US-009, `04` §Paciente |
| Campos mínimos y textos normalizados | 8 | 2 | 2 | 4 | US-009, DD-26 (f) |
| Formato mínimo del email | 4 | 1 | 3 | 0 | D16 (sin regla en la KB) |
| Documento único | 4 | 0 | 3 | 1 | DD-26 (e), `catalogo-consultorio` |
| Edición parcial de un paciente | 9 | 4 | 3 | 2 | DD-26 (j), DD-21 (c) |
| Estado de actividad del paciente no editable | 2 | 0 | 2 | 0 | DD-26 (d) |
| Listado de pacientes | 2 | 1 | 0 | 1 | DD-26 (a) por analogía |
| Búsqueda de pacientes | 13 | 7 | 0 | 6 | US-009, D5, D6 |
| Paginación del listado de pacientes | 5 | 2 | 0 | 3 | D8 (sin regla en la KB) |
| Detalle de un paciente para la recepcionista | 4 | 2 | 1 | 1 | matriz de `03`, DD-21 (c) |
| Desactivación lógica de un paciente | 3 | 1 | 1 | 1 | DD-26 (c) |
| Un paciente desactivado no admite turnos nuevos | 2 | 0 | 2 | 0 | DD-21 (c), DD-26 (consecuencias) |
| Un paciente desactivado conserva sus turnos y recordatorios | 3 | 3 | 0 | 0 | DD-26 (g), RN-NO-01, RN-CU-01 |
| Desactivación de paciente simultánea con un alta de turno | 2 | 0 | 0 | 2 | DD-26 (i), parcial (H1) |
| Escritura de pacientes reservada a la recepcionista | 4 | 0 | 2 | 2 | DD-24 (b), matriz de `03` |
| Listado y búsqueda reservados a la recepcionista | 3 | 0 | 2 | 1 | DD-24 (b), US-009 |
| Lectura mínima del odontólogo | 3 | 1 | 0 | 2 | matriz de `03`, RN-AU-02 |
| Paciente ajeno para el odontólogo | 5 | 0 | 2 | 3 | DD-27 (i), DD-30 (l) |
| Errores sin datos personales | 5 | 1 | 0 | 4 | D17 (sin regla en la KB) |
| Log de acceso sin el texto buscado | 2 | 2 | 0 | 0 | D18 (sin regla en la KB) |
| **Total** | **86** | **30** | **23** | **33** | |

Reglas del scope sin escenario: DD-26 (i) en su rama de reprogramación (H1). RN-CU-02 no se ejercita con un escenario: se controló sobre los datos de ejemplo (H10).

Controles sin hallazgos:
- **C1**: están los tres tipos de escenario.
- **C3**: nada invade C-07, C-08, C-11, C-12, C-13 ni C-14..C-16, y todo lo que los escenarios usan ya existe en `main`. El escenario del worker usa C-12 y el de `POST /sillones`, C-08.
- **C4**: los códigos coinciden con DD-21, DD-24, DD-26 y DD-27. Los cuerpos de `rol_insuficiente`, `no_autenticado`, `recurso_duplicado` y `recurso_inexistente` coinciden con `app/api/auth.py` y `app/api/recursos.py`.
- **C9**: cada escenario tiene su tarea. Los conteos de 4.2, 6.1, 7.2, 7.3 y 8.1 coinciden con el spec.

## Hallazgos

### H1 — Falta la reprogramación concurrente con la desactivación · MAYOR
- **Dónde**: `spec.md`, requirement "Desactivación de paciente simultánea con un alta de turno", escenario "falta"; tarea 9.4
- **Problema**: DD-26 (i) serializa la desactivación con el alta **y** con la reprogramación, y el spec exige que reprogramar el turno de un paciente desactivado dé `422`, pero solo hay escenarios de alta. El requirement archivado de C-08 tiene los tres casos y un test propio (`test_reprogramacion_espera_a_una_desactivacion_en_curso_y_el_turno_no_se_mueve`). La reprogramación sí pasa por `cargar_referencias` y toma `FOR SHARE` sobre el paciente, así que falta cubrir una garantía que ya existe; no falta código.
- **Fuente**: DD-26 (i); `openspec/specs/gestion-recursos/spec.md`, requirement "Desactivación simultánea con un alta o una reprogramación de turno"
- **Sugerencia**: renombrar el requirement a "… con un alta o una reprogramación de turno", ajustar la tarea 9.4 a tres escenarios y agregar:
  - **GIVEN** dado un turno `programado` futuro del paciente P y una transacción que desactivó a P y todavía no confirmó
  - **WHEN** cuando en paralelo se reprograma ese turno a otro horario libre y después se confirma la desactivación
  - **THEN** entonces la reprogramación espera a la desactivación y responde `422` con `referencia = "paciente"`, y el turno conserva su horario original

### H2 — El texto del requirement obliga a enviar un recordatorio que DD-29 prohíbe enviar · MAYOR
- **Dónde**: `spec.md`, requirement "Un paciente desactivado conserva sus turnos y recordatorios", texto normativo
- **Problema**: "su recordatorio pendiente MUST enviarse mientras el turno siga `programado`" es falso en dos casos. Un turno `programado` con `inicio <= ahora` no se envía y su recordatorio queda `cancelado` (DD-29 a). Agotados los intentos, queda `fallido` (RN-NO-05). Baja de BLOQUEANTE porque ningún escenario contradice la regla y Apply no cambia el worker, pero este texto pasa tal cual al spec archivado.
- **Fuente**: RN-NO-01, RN-NO-05, DD-29 (a)
- **Sugerencia**: "Desactivar a un paciente MUST NOT alterar sus recordatorios: el de un turno `programado` sigue las mismas reglas que cualquier otro (RN-NO-01, RN-NO-02, DD-29)."

### H3 — D14 describe una limitación inexacta · MENOR
- **Dónde**: `design.md`, D14; `spec.md`, requirement "Edición parcial de un paciente", escenario "Edición de un paciente desactivado"
- **Problema**: D14 dice que el documento de un paciente dado de baja no se puede volver a registrar por API y que "haría falta tocar la base". El spec permite editar `documento` en un paciente desactivado: la recepcionista puede cambiarlo por un valor inventado y dar un alta nueva con el documento real. Es una salida mala (un dato falso en la fila, un `id` nuevo, el historial partido), pero la decisión se está tomando con una descripción errónea.
- **Fuente**: `spec.md`, requirement "Edición parcial de un paciente" ("también en un paciente desactivado"); `design.md`, D11 y D14
- **Sugerencia**: corregir la limitación en D14 y en DD-31. Si no se quiere habilitar ese camino, decidirlo de forma explícita (ver P1).

### H4 — D17 se presenta como "Regla del proyecto", pero no tiene fuente · MENOR
- **Dónde**: `design.md`, tabla de decisiones, D17; requirement "Errores sin datos personales"
- **Problema**: ni la KB ni las reglas duras de `CLAUDE.md` piden quitar los valores de los errores de validación; la regla dura sobre contenido habla solo de recordatorios. `design.md` define **[A confirmar]** como lo que "no surge de la KB", y D17 cumple esa definición. Hay precedentes de minimización (DD-25 b, DD-29 a, DD-30 i), pero ninguno cubre este caso.
- **Fuente**: `design.md` §Decisions; RN-CU-01; `CLAUDE.md` §Reglas Duras
- **Sugerencia**: marcarla **[A confirmar]** e incluirla en DD-31.

### H5 — Ningún `422` con datos se comprueba en `/pacientes/{id}` · MENOR
- **Dónde**: `spec.md`, requirement "Errores sin datos personales", escenario "falta"
- **Problema**: los tres escenarios de `422` van contra `/pacientes` exacto. D17 tiene dos ramas (la ruta exacta y el prefijo `/pacientes/`); un manejador que solo reconozca la primera pasa todos los tests y deja el `input` en el `PATCH`. "Edición con email inválido" no mira el cuerpo.
- **Fuente**: `design.md`, D17; `spec.md`, requirement "Errores sin datos personales" ("las rutas de `/pacientes`")
- **Sugerencia**:
  - **WHEN** cuando una recepcionista autenticada envía `PATCH /pacientes/{id}` con `{"email": "no-es-un-email"}`
  - **THEN** entonces la respuesta es `422`, indica el campo `email` y su cuerpo no contiene "no-es-un-email"

### H6 — El escenario del log no se comprueba de punta a punta y el filtro falla en silencio · MENOR
- **Dónde**: `spec.md`, requirement "Log de acceso sin el texto buscado"; `design.md` §Risks; tareas 10.2 y 10.3
- **Problema**: el THEN es verificable, pero solo sobre un `LogRecord` armado a mano. `TestClient` no pasa por `uvicorn`, y la comprobación real de 10.3 es manual. Design dice que "un test fija el formato de la versión instalada", pero un registro armado por el test fija lo que el test supone, no lo que `uvicorn` emite. Si `record.args` cambia, el filtro no toca el registro y la búsqueda vuelve al log sin que falle nada; `pyproject.toml` pide `uvicorn>=0.30`, sin tope.
- **Fuente**: control C5; `design.md` §Risks ("el filtro no lo toca"); tareas 10.2 y 10.3
- **Sugerencia**: que el escenario diga qué capa verifica, y reemplazar la comprobación manual por un test que levante `uvicorn` en un subproceso y lea su salida.

### H7 — Bordes incompletos en largo y carácter nulo · MENOR
- **Dónde**: `spec.md`, requirement "Campos mínimos y textos normalizados", escenarios "Texto más largo que su columna", "Texto con el largo máximo aceptado" y "Carácter nulo rechazado"
- **Problema**:
  - El requirement fija cinco largos, pero no hay escenario para `apellido` de 101 ni `email` de 255, ni máximos para `nombre`, `apellido` y `email`.
  - `U+0000` aparece solo en el escenario, no en el texto del requirement, y solo prueba `nombre` en `POST`. El `email` importa porque `email_valido` (D16) no lo rechaza, y design advierte que ese carácter produce `500`. Tampoco hay caso en `PATCH`.
- **Fuente**: `spec.md`, texto del requirement; `design.md` §Risks ("El carácter `U+0000`…"), que promete `422` "en los textos"
- **Sugerencia**: llevar `U+0000` al texto del requirement y parametrizar los escenarios por campo, en alta y en edición.

### H8 — Escenarios con "futuro" sin reloj fijo ni instantes con offset · MENOR
- **Dónde**: `spec.md`, escenarios "Corrección del documento", "Alta con un paciente desactivado", "Reprogramación del turno de un paciente desactivado", "Turno futuro intacto" ("de 10:00 a 10:45", sin fecha ni offset), "Turno futuro cancelable" y "Recordatorio pendiente enviado igual"
- **Problema**: el resultado depende de "ahora" (RN-AG-12, RN-AG-13, DD-29 a) y ni el spec ni las tareas 9.2 y 9.3 fijan el reloj. Por C6 sería MAYOR. Baja a MENOR porque el harness ya lo resuelve: `test_api_desactivacion_recursos.py` usa un `AHORA` fijo, `test_api_recordatorios.py` reemplaza `get_reloj`, y la tarea 9.3 cita `helpers_recordatorios` (`RelojManual`, `ciclo_a`).
- **Fuente**: control C6; RN-CU-04
- **Sugerencia**: decir en las tareas 9.2 y 9.3 que el reloj se fija, y dar fecha y offset en "Turno futuro intacto".

### H9 — Trece requirements no citan su regla · MENOR
- **Dónde**: todos menos "Alta de paciente", "Estado de actividad…", "Desactivación lógica…", "Un paciente desactivado no admite…", "Un paciente desactivado conserva…", "Escritura de pacientes…" y "Paciente ajeno…"
- **Problema**: varios tienen fuente directa y no la citan: "Documento único" (DD-26 e), "Edición parcial" (DD-26 j), "Desactivación… simultánea" (DD-26 i), "Lectura mínima" (matriz de `03`, RN-AU-02).
- **Fuente**: control C2
- **Sugerencia**: citar la regla existente, y DD-31 con el literal correspondiente en los que dependen de una decisión **[A confirmar]**.

### H10 — Un documento de ejemplo con forma de DNI real · MENOR
- **Dónde**: `spec.md`, escenario "Documento y teléfono sin formato propio" (`"documento": "30111222"`)
- **Problema**: es inventado, pero tiene la forma de un DNI posible, y el control pide que nada parezca real. C8 lo marca MAYOR. Baja a MENOR porque el mismo valor ya figura como ficticio en el spec archivado de `recordatorios`, y reemplazarlo es trivial.
- **Fuente**: RN-CU-02; control C8
- **Sugerencia**: usar un valor numérico que no pueda ser un DNI, como `00000104`.

### H11 — "Rol antes que el body" no vale para un JSON mal formado · MENOR
- **Dónde**: `spec.md`, requirement "Escritura de pacientes reservada a la recepcionista"; `design.md` §Orden de evaluación
- **Problema**: el requirement dice que autenticación y rol MUST evaluarse antes que el body, pero FastAPI parsea el JSON antes de las dependencias. En un caso mínimo con FastAPI 0.142.4, un body sintácticamente inválido dio `422` con una dependencia que responde `403`, y `{}` dio `403`. El escenario con `{}` pasa y el texto queda más amplio que lo que se cumple. El comportamiento ya existe y la misma frase está en `gestion-recursos`, así que no es un defecto nuevo de C-09.
- **Fuente**: `spec.md`, texto del requirement; DD-24 (b); prueba descrita arriba
- **Sugerencia**: acotar el texto a "antes que la validación del contenido del body".

### H12 — Tarea sin escenario · SUGERENCIA
- **Dónde**: `tasks.md`, tarea 11.3
- **Problema**: el test de `/openapi.json` (rutas exactas, sin `PUT` ni `DELETE`, descripciones de parámetros) no corresponde a ningún escenario. Es una práctica legítima del proyecto (`test_api_bloqueos_openapi.py`). Las tareas 2.x, 3.x y 10.3 son setup o capas internas y no se cuentan.
- **Fuente**: control C9
- **Sugerencia**: dejarla, o agregar un escenario si el conjunto de rutas se considera contrato.

## Preguntas abiertas

### P1 — ¿Reactivación de pacientes en C-09? (D14)
**Lo que dice la KB.** Ni US-009 ni el scope de C-09 en `CHANGES.md` la mencionan; piden registrar, buscar y desactivar. La matriz de `03` dice "CRU (baja lógica, **Suposición**)". DD-26 (d) la descartó para los recursos, con un motivo que vale igual acá ("la US-001 solo pide alta, edición y desactivación"), y DD-24 (j) hizo lo mismo con los usuarios. DD-26 (a) enumera tres recursos y no incluye a los pacientes, así que no es una regla ya tomada, sino un precedente. La reactivación de pacientes tampoco figura todavía en el backlog; la tarea 11.2 la agrega.

**Evaluación.** Sumar `POST /pacientes/{id}/reactivar` sería ampliar el alcance. El argumento fuerte son esos dos precedentes, no que "`CHANGES.md` solo pide desactivación": C-09 ya incorpora D8, D17 y D18, que `CHANGES.md` tampoco pide. A diferencia de un sillón, un paciente vuelve, y una desactivación por error no tiene salida limpia; la única es la de H3.

**Opciones** (decide el usuario):
- (a) Fuera de alcance: backlog, con la limitación corregida en DD-31. Es lo coherente con los precedentes.
- (b) Endpoint simétrico en C-09: 3 o 4 escenarios, pero requiere ajustar el scope y DD-31.
- (c) Prohibir editar el `documento` de un desactivado, si la salida de H3 se considera inaceptable.

### P2 — ¿Cómo llega el nombre del paciente a la agenda?
D1 y D2 dejan al odontólogo solo con `GET /pacientes/{id}`, y design delega en C-13 la decisión de embeber el nombre. Pero el scope de C-13 no lo menciona, `TurnoOut` trae solo `paciente_id` y US-008 no define qué se muestra. Sin definición, la agenda de C-15 necesita un pedido por paciente. Conviene acordarlo con el responsable de C-13 antes de aprobar D2.

### Decisiones de `design.md`

"Con base" significa que surge de una regla o de su lectura literal; "Precedente", que se traslada de otro recurso; "Regla nueva", que la KB no la tiene y debe quedar en DD-31.

| # | Decisión | Evaluación | Fundamento |
|---|----------|------------|------------|
| D1 | Campos `id`, `nombre`, `apellido` | Regla nueva | La matriz dice "R (…, **Suposición**)" y `CHANGES.md` "lectura mínima", sin campos. RN-AU-02 habla de agenda, no de campos. No contradice nada. |
| D2 | Solo `GET /pacientes/{id}` | Regla nueva, restrictiva | US-009 tiene como actor a la recepcionista. `TurnoOut` trae `paciente_id`, como afirma design. Ver P2. |
| D3 | Cualquier turno de su profesional | Con base | Lectura literal de la matriz ("pacientes de sus turnos") y de "Turnos: R solo propios". El argumento de "lo ve en su agenda" supone algo que C-13 aún no definió. |
| D4 | `403 paciente_ajeno` (no marcada) | Precedente firme | DD-27 (i) y DD-30 (l). El código `paciente_ajeno` es nuevo y debe figurar en DD-31. |
| D5 | `q` único, AND entre términos | Regla nueva de contrato | El scope pide buscar por nombre, apellido y documento; la forma del parámetro no está definida. |
| D6 | Ignorar mayúsculas y acentos | Regla nueva | La KB no lo menciona. |
| D7 | Inactivos en el listado | Precedente | DD-26 (a) lo define para los recursos; se traslada por analogía. |
| D8 | Paginación con tope | Regla nueva | Se aparta a propósito de DD-26 (a) y DD-30 (k), sin paginación. Tiene justificación (padrón sin tope), pero `CHANGES.md` no la pide. |
| D11 | `documento` editable | Precedente | La matriz da U, y DD-26 (e, j) trata la matrícula igual. La edición no deja rastro porque RN-CU-01 audita solo turnos. Ver H3. |
| D13 | Recordatorios se envían igual | Con base; podría dejar de ser **[A confirmar]** | RN-NO-01 ("todo turno activo"), RN-NO-02 (solo cancelar o reprogramar lo alteran), DD-26 (g) y sus consecuencias, que nombran al paciente. Falta corregir la redacción (H2). |
| D14 | Reactivación fuera de alcance | Precedente, con impacto mayor | DD-24 (j), DD-26 (d). Ver P1 y H3. |
| D15 | Sin formato para documento y teléfono | Con base | No agrega regla: la KB no define formato. El recorte viene de DD-26 (f). |
| D16 | Chequeo mínimo del email | Regla nueva | `04` dice solo "email (opcional)". DD-24 (d) es de usuarios. Nada lo consume en el MVP (DD-28 f dirige por `paciente_id`). |
| D17 | Errores sin datos (no marcada) | Regla nueva | Ver H4. Costo bajo y escenarios verificables, pero el beneficio es el menor de todo el change: el `input` vuelve solo a quien lo envió. Se justifica si importa lo que un cliente registre de sus errores. No es excesivo por tamaño; es opcional por motivo. |
| D18 | Query fuera del log | Regla nueva | Sin regla en la KB, pero la exposición es real: nombres y documentos en la salida del servidor. Es la más justificada de las dos y merece estar en el spec. Se puede verificar solo en parte (H6). |

## Fuera de esta revisión

- No se ejecutó ningún escenario. Las afirmaciones sobre el código salen de leerlo en `55b0f1d`.
- H11 se probó con la FastAPI de la instalación global de Python, en un caso mínimo fuera de la aplicación; `pyproject.toml` pide `fastapi>=0.122`.
- No se verificó el formato real de `record.args` de `uvicorn`, y no se hizo un análisis legal de la Ley 25.326 / 26.529.
- Las fallas previas de `openspec validate --specs --strict` sobre otros specs quedan fuera. `openspec validate registro-pacientes --strict` pasa.
