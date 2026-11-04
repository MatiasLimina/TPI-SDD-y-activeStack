# Revisión de escenarios — bloqueos-agenda (C-11)

> **Estado (2026-11-04)**: los hallazgos H1-H12 se resolvieron con `/opsx:update` el 2026-11-04, después de que el usuario aprobara las decisiones D1-D9 y D11-D13. **D12 cambió**: el odontólogo recibe `403 profesional_ajeno` antes de la existencia (bloqueo ajeno o inexistente), como DD-27 (i), así que el orden `404` → `403` que citan H5 y la tabla de D12 ya no aplica. **H13 no se aplicó** (opcional). El resto de este informe queda como se escribió.

- Fecha: 2026-11-04
- Specs revisados:
  - `openspec/changes/bloqueos-agenda/specs/bloqueos-agenda/spec.md` (capacidad nueva: 10 requirements, 47 escenarios)
  - `openspec/changes/bloqueos-agenda/specs/agenda-turnos/spec.md` (1 ADDED con 12 escenarios; 1 MODIFIED con 17 escenarios, de los cuales 5 son nuevos y 12 se copian sin cambios del spec archivado)
  - Contexto: `proposal.md`, `design.md`, `tasks.md`, `CHANGES.md` §C-11, `openspec/specs/agenda-turnos/spec.md`, `openspec/specs/gestion-recursos/spec.md` (precedente de concurrencia)
- Reglas aplicables: RN-HB-02, RN-HB-03, RN-AG-03, RN-AG-06, RN-AG-07, RN-AG-08, RN-AG-09 (por la regla dura de concurrencia), RN-AU-01, RN-AU-02, RN-CU-04, DD-02, DD-12, DD-17, DD-18, DD-21 (c), DD-24 (b), DD-26 (i), DD-27 (i, j, k, l), US-003, Flujo 5, `04_modelo_de_datos.md` §Bloqueo, `08_arquitectura_propuesta.md` §Concurrencia, matriz de `03_actores_y_roles.md`
- Escenarios nuevos revisados: **64** (47 + 12 + 5). Los 12 escenarios heredados del requirement MODIFIED se verificaron idénticos al spec archivado (solo cambia el texto del requirement, que suma RN-AG-06).
- Veredicto: **LISTO PARA APPLY**, condicionado a que el usuario confirme las decisiones **[A confirmar]** (D1-D9, D11-D13), como ya exigen `design.md` y `tasks.md`. No hay hallazgos BLOQUEANTE ni MAYOR. Los MENOR conviene corregirlos en el mismo `/opsx:update`, si alguna decisión cambia.

## Cobertura

Cada escenario se cuenta en una sola columna. Los `422` de validación del request (campo faltante, datetime sin zona, UUID mal formado) no cuentan como error de negocio (C1). Por eso, en esas filas, las columnas no suman el total.

| Requirement | Escenarios | Esperado | Error de negocio | Borde | Reglas cubiertas |
|-------------|-----------:|:--------:|:----------------:|:-----:|------------------|
| Alta de un bloqueo de agenda | 6 | 3 | 0 | 3 | RN-HB-02, RN-CU-04, D5, D8 |
| Profesional del bloqueo según el rol | 6 | 2 | 3 | 1 | RN-HB-02, RN-AU-02, Flujo 5, DD-21 (c), DD-27 (i) |
| Validación del bloqueo | 6 (2 de validación del request) | 0 | 2 | 2 | RN-HB-02, `04` §Bloqueo, D7 |
| Bloqueo sobre turnos activos rechazado | 9 | 1 | 4 | 4 | RN-HB-03, DD-12, RN-AG-03, RN-AG-07, US-003 |
| Bloqueos superpuestos del mismo profesional | 2 | 1 | 0 | 1 | D2, RN-AG-06 |
| Consulta de bloqueos | 6 (1 de validación del request) | 3 | 1 | 1 | RN-AU-02, D11 |
| Borrado de un bloqueo | 6 (1 de validación del request) | 3 | 2 | 0 | RN-HB-02, RN-AU-02, DD-21 (c), D12 |
| Bloqueos accesibles solo con autenticación | 2 | 0 | 1 | 1 | RN-AU-01, DD-24 (b) |
| Integridad del bloqueo en la base | 2 | 1 | 1 | 0 | `04` §Bloqueo, DD-17, RN-CU-04 |
| Bloqueo y turno simultáneos | 2 | 0 | 0 | 2 | RN-HB-03, RN-AG-06, `08` §Concurrencia, DD-18 |
| (agenda-turnos, ADDED) Turno fuera de los bloqueos de agenda | 12 | 1 | 6 | 5 | RN-AG-06, RN-AG-03, DD-27 (l), RN-AG-08, global "bloqueo → 422" |
| (agenda-turnos, MODIFIED) Misma validación que el alta al reprogramar | 17 (5 nuevos) | 0 | 4 | 1 | RN-AG-08, RN-AG-06 (solo se cuentan los 5 nuevos) |
| **Total nuevos** | **64** (4 de validación del request) | **15** | **24** | **21** | |

Mínimo de tres tipos (C1): cumplido.

Correspondencia entre escenarios y tareas (C9): los 64 escenarios tienen una tarea que los verifica (2.1-2.2, 3.2, 5.1-5.7, 6.1-6.3 y 7.1).

Reglas del scope sin escenario: ninguna. Los tres criterios de US-003, los cuatro ítems de `CHANGES.md` §C-11 y el Flujo 5 (pasos 1 y 2) están cubiertos. El paso 3 del Flujo 5 ("se refleja en la agenda y en la disponibilidad") pertenece a C-13 y al backlog (US-007), así que no se pide.

## Hallazgos

### H1 — Rechazos de escritura sin "no se persiste" en el THEN · MENOR (rebajado desde MAYOR)
- **Dónde**:
  - `bloqueos-agenda/spec.md`:
    - "Varios turnos afectados, ordenados por inicio"
    - "Odontólogo con turnos propios en el intervalo"
    - "Fin anterior al inicio"
    - "Profesional ajeno antes que el bloqueo inválido"
  - `agenda-turnos/spec.md` (ADDED):
    - "Turno que empieza antes y termina dentro del bloqueo"
    - "…empieza dentro y termina después…"
    - "…contiene al bloqueo"
    - "Bloqueo de varios días"
    - "Fuera de horario y dentro de un bloqueo"
    - "Dentro de un bloqueo y en conflicto"
    - "Validaciones previas antes que el bloqueo"
- **Problema**: son operaciones de escritura rechazadas, y el THEN no dice que no queda nada persistido. C5 lo trata como MAYOR por defecto. Se rebaja por tres motivos:
  - El texto de cada requirement ya exige "sin persistir".
  - Las tareas 5.2 ("sin filas en todos los rechazos") y 6.2 ("sin turno persistido en los rechazos") lo afirman en el test.
  - En los dos casos con `fin <= inicio`, el CHECK `ck_bloqueo_fin_mayor` hace imposible la fila.

  El único hueco real está en los `409`: la tarea 5.3 solo verifica "sin bloqueo" en el primer escenario.
- **Fuente**: `references/controles.md` C5; requirement "Bloqueo sobre turnos activos rechazado" ("sin persistir el bloqueo").
- **Sugerencia**: agregar "y no se persiste ningún bloqueo" a los dos `409` y "y no se persiste ningún turno" a los `422` del ADDED. En la tarea 5.3, contar las filas de `bloqueo` después de cada `409`.

### H2 — Concurrencia: THEN disyuntivo, sin un escenario por orden de llegada · MENOR
- **Dónde**: `bloqueos-agenda/spec.md`, requirement "Bloqueo y turno simultáneos", los dos escenarios.
- **Problema**: el THEN acepta "`409 bloqueo_con_turnos` **o** `422 turno_en_bloqueo`". Con eso el test verifica la invariante, pero no prueba cada rama de la serialización que describe D13 (el bloqueo espera al turno, y el turno espera al bloqueo). Si el entrelazado sale siempre igual, una de las dos ramas nunca se ejercita. El spec archivado de C-08 (`gestion-recursos`, "Desactivación simultánea con un alta o una reprogramación de turno", DD-26 i) resolvió el mismo patrón de lock con escenarios deterministas para cada orden. La tarea 7.1 lo mitiga a medias: pide RED sin el `FOR NO KEY UPDATE` y prevé un punto de espera "si la carrera no se reproduce".
- **Fuente**: RN-HB-03; `08_arquitectura_propuesta.md` §Concurrencia (punto 4); DD-18; precedente archivado de DD-26 (i).
- **Sugerencia**: mantener los dos escenarios en paralelo (la invariante) y sumar dos deterministas, al estilo de C-08:
  - GIVEN una transacción que creó un bloqueo de A de 10:00 a 12:00 y todavía no confirmó / WHEN en paralelo se crea un turno de A a las 10:30 y después se confirma el bloqueo / THEN el alta espera y responde `422 turno_en_bloqueo`, sin turno persistido.
  - GIVEN un alta de turno de A a las 10:30 que ya validó sus referencias y no confirmó / WHEN en paralelo se crea el bloqueo y después se confirma el alta / THEN el bloqueo espera y responde `409 bloqueo_con_turnos` con el turno, sin bloqueo persistido.

### H3 — Orden entre los `422` del alta sin escenario · MENOR
- **Dónde**: `bloqueos-agenda/spec.md`, requirements "Profesional del bloqueo según el rol" y "Validación del bloqueo" (falta).
- **Problema**: `design.md` §2 fija el orden `profesional_requerido` → `referencia_invalida` → `bloqueo_invalido`, pero el spec solo pinta el orden `403` antes de `422`. Dos pedidos con dos defectos (una recepcionista sin `profesional_id` y con `fin = inicio`; un profesional inexistente y un motivo vacío) dan códigos distintos según el orden. Sin escenario, el test no lo fija.
- **Fuente**: `design.md` §2 "Orden de evaluación"; `references/controles.md` C7.
- **Sugerencia**: un escenario "Profesional inexistente y bloqueo inválido → `422 referencia_invalida`" y otro "Recepcionista sin profesional y bloqueo inválido → `422 profesional_requerido`", o los que resulten si el usuario cambia el orden.

### H4 — Borde del largo del motivo · MENOR
- **Dónde**: `bloqueos-agenda/spec.md`, requirement "Validación del bloqueo", escenario "Campos faltantes o fuera de forma".
- **Problema**: se prueba el rechazo de 256 caracteres, pero no la aceptación de exactamente 255. Además, el requirement no dice si el largo se mide antes o después de quitar los espacios extremos. Con `Field(max_length=255)` (D7) se mide antes: "  " + 254 letras se rechaza aunque guardado ocuparía 254.
- **Fuente**: D7 (**[A confirmar]** el largo); `04_modelo_de_datos.md` §Bloqueo ("texto corto"); C6/C5 (bordes exactos).
- **Sugerencia**: escenario "Motivo de 255 caracteres → `201`" y una frase en el requirement: "el largo se mide sobre el texto recibido".

### H5 — Decisiones sin escenario que las fije · MENOR
- **Dónde**: `bloqueos-agenda/spec.md` (falta).
- **Problema**: tres decisiones del design no tienen ningún escenario, así que Apply podría contradecirlas sin que un test falle:
  - D6: un bloqueo no alineado a 5 minutos, por ejemplo de 10:03 a 10:07, se acepta.
  - D11: `GET /bloqueos` incluye los bloqueos pasados. Lo dice el requirement, pero no hay escenario.
  - D12: un odontólogo que borra un UUID inexistente recibe `404`, no `403`. Es el orden `404` → `403`.
- **Fuente**: `design.md` D6, D11, D12; `references/controles.md` C2/C9.
- **Sugerencia**: un escenario por decisión, después de que el usuario las confirme.

### H6 — Token inválido o vencido solo en el texto del requirement · MENOR
- **Dónde**: `bloqueos-agenda/spec.md`, requirement "Bloqueos accesibles solo con autenticación".
- **Problema**: el requirement dice "sin token, o con un token inválido", pero los dos escenarios son sin token. La tarea 5.7 sí agrega "un token vencido o con firma inválida → `401`", sin un escenario detrás.
- **Fuente**: DD-24 (b); `references/controles.md` C9.
- **Sugerencia**: escenario "Token vencido o con firma alterada → `401 no_autenticado` en `POST /bloqueos`, sin filas".

### H7 — Integridad: autor inexistente sin escenario ni tarea · MENOR
- **Dónde**: `bloqueos-agenda/spec.md`, requirement "Integridad del bloqueo en la base", escenario "Escrituras directas inválidas".
- **Problema**: el requirement exige rechazar "un profesional o un autor inexistentes", pero el escenario y la tarea 3.2 solo prueban el profesional inexistente.
- **Fuente**: texto del requirement; D14 (FK `creado_por` → `usuario` `RESTRICT`).
- **Sugerencia**: agregar al escenario "otro con un `creado_por` que no corresponde a ningún usuario" y a la tarea 3.2.

### H8 — Valores no concretos y reloj implícito · MENOR
- **Dónde**:
  - `bloqueos-agenda/spec.md`:
    - "Bloqueo de varios días" (THEN "el bloqueo cubre los cinco días")
    - "Profesional desactivado", "Odontólogo indica su propio profesional" y "Recepcionista sin profesional" (GIVEN o WHEN "un intervalo y un motivo válidos")
  - Requirement "Bloqueo sobre turnos activos rechazado" y escenarios nuevos del MODIFIED: crean turnos futuros sin fijar el reloj en el requirement.
- **Problema**: un THEN chequeable, pero sin valores, deja que el test elija los valores esperados. El reloj sí lo fija `tasks.md` (2026-10-07 09:00 local, tareas 5.3 y 6.x), así que por C6 queda en riesgo de redacción.
- **Fuente**: `references/controles.md` C5 y C6.
- **Sugerencia**: THEN "`201` con `inicio` 2026-10-12T00:00:00-03:00 y `fin` 2026-10-17T00:00:00-03:00"; valores concretos en los GIVEN; la frase "Los escenarios asumen el reloj en 2026-10-07 09:00 local" en el requirement de los `409`.

### H9 — Citas incompletas en los requirements · MENOR
- **Dónde**: `bloqueos-agenda/spec.md`.
- **Problema**: hay requirements que no citan la decisión que fija su contrato o que citan una que todavía no existe:
  - "Bloqueos accesibles solo con autenticación" no cita DD-24 (b), que fija `401 no_autenticado` y `WWW-Authenticate`.
  - "Bloqueo y turno simultáneos" no cita `08` §Concurrencia, DD-18 ni D13.
  - "Profesional del bloqueo según el rol" no cita DD-27 (i), origen de `profesional_ajeno` y del `403` antes de la existencia.
  - "Bloqueos superpuestos…", "Bloqueo en el pasado" y "Profesional desactivado" citan **DD-30**, que todavía no existe en `09_decisiones_y_supuestos.md`. Se crea en la tarea 9.1 con lo que el usuario apruebe.
- **Fuente**: `references/controles.md` C2.
- **Sugerencia**: agregar las citas. Si C-13 toma DD-30 antes, renumerar (la tarea 9.1 ya lo prevé).

### H10 — Consecuencia de D5 sin escenario: bloqueo retroactivo sobre un turno pasado · SUGERENCIA
- **Dónde**: `bloqueos-agenda/spec.md`, requirement "Bloqueo sobre turnos activos rechazado" (falta).
- **Problema**: con D5 (sin restricción temporal) y RN-HB-03 (cuenta todo turno no cancelado), un bloqueo sobre un turno `programado` ya pasado da `409`. Ese turno no se puede cancelar (RN-AG-13) ni reprogramar (DD-23 d), así que el bloqueo es imposible para siempre. El design lo documenta como consecuencia aceptada, pero ningún escenario lo hace visible para quien aprueba D5.
- **Fuente**: D5; RN-HB-03; RN-AG-13; DD-23 (d).
- **Sugerencia**: si D5 se confirma, el escenario "Bloqueo sobre un turno pasado → `409` con ese turno". Si el usuario prefiere evitarlo, es una pregunta abierta (contar solo turnos con `fin > ahora`), no una regla para inventar acá.

### H11 — D13: falta la carrera de una reprogramación que cambia de profesional · SUGERENCIA
- **Dónde**: `bloqueos-agenda/spec.md`, requirement "Bloqueo y turno simultáneos"; tarea 7.1.
- **Problema**: el caso (b) reprograma T1 dentro del mismo profesional. No se prueba el caso de un turno de B que se reprograma hacia A mientras se crea un bloqueo de A, donde el lock relevante es el del profesional **destino**. Hoy el mecanismo lo cubre: `ReprogramarTurno` resuelve el destino con `_valor(solicitud.profesional_id, actual.profesional_id)` y `cargar_referencias` lo lee con `FOR SHARE`. Pero ningún test lo protege si esa resolución cambia.
- **Fuente**: D13; `backend/app/application/reprogramar_turno.py`; `backend/app/infrastructure/db/repositorio_turnos.py` (`_activa`, `with_for_update={"read": True}`).
- **Sugerencia**: un tercer caso en 7.1, la reprogramación de un turno de B hacia A a las 10:30 en paralelo con el bloqueo de A.

### H12 — D13: registrar el contrato del lock en DD-30 · SUGERENCIA
- **Dónde**: `design.md` D13; tarea 9.1.
- **Problema**: la garantía de RN-HB-03 depende de un protocolo que la base aplica, pero que la aplicación tiene que pedir. Todo escritor de `turno` que pueda mover un turno en el tiempo o de profesional debe leer el profesional con `FOR SHARE` antes de validar, y todo escritor de `bloqueo` debe tomar `FOR NO KEY UPDATE`. Un change futuro que agregue otra vía de escritura de turnos (C-13 o el backlog) podría saltearlo sin que ningún test falle. Además, D13 resuelve la **Suposición** abierta de `08` ("o con triggers, Suposición a decidir").
- **Fuente**: `08_arquitectura_propuesta.md` §Concurrencia (Nota); DD-02 (trade-off: "horario y bloqueos siguen validándose en aplicación").
- **Sugerencia**: que DD-30 enuncie ese contrato como invariante, marque resuelta la Suposición de `08` y deje "trigger + lock" como defensa en profundidad en el backlog, junto al rol de base de datos de mínimo privilegio (ya presente).

### H13 — Tareas sin escenario · SUGERENCIA
- **Dónde**: `tasks.md` 2.2 (regresión del cuerpo de `profesional_ajeno` de horarios), 3.1 (migración, índice, FKs), 3.2 (`CASCADE` del profesional) y 8.1 (OpenAPI sin `PATCH`/`PUT`, por D3).
- **Problema**: son setup o regresión legítimos. Se señalan solo porque D3 ("sin edición") y el `CASCADE` se verifican sin un escenario que los respalde.
- **Fuente**: `references/controles.md` C9.
- **Sugerencia**: opcional: un escenario "`PATCH /bloqueos/{id}` → `405`" si D3 se confirma.

## Preguntas abiertas

No surgen preguntas nuevas para `10_preguntas_abiertas.md`. Lo pendiente es la confirmación de las decisiones **[A confirmar]**, que el design ya plantea con opción recomendada y alternativas. Para cada una, si está fundada en la KB o introduce una regla nueva:

| Id | Veredicto | Fundamento |
|----|-----------|------------|
| D1 | Fundada, con interpretación | Flujo 5 y `CHANGES.md` ("fuerza `profesional_id` del token") + RN-AU-02. Rechazar con `403` en vez de ignorar sigue el antipatrón del dato ignorado en silencio (DD-21 a, DD-23 b), y `profesional_ajeno` antes de la existencia viene de DD-27 (i). `profesional_requerido` es un código nuevo, pero es contrato, no regla de dominio. La lectura literal de "fuerza" (ignorar el id del cliente) es la alternativa a elegir. |
| D2 | Fundada (por ausencia) | La KB no prohíbe bloqueos superpuestos. Permitirlos no agrega regla; la regla nueva sería la alternativa (`409 bloqueo_superpuesto`). |
| D3 | Fundada | `CHANGES.md` §C-11 (`POST`/`GET`/`DELETE`) y `02` (`POST`/`DELETE`) contra la matriz de `03` ("CRUD (todos)"): es una inconsistencia de la KB que la decisión resuelve a favor del roadmap. Debe quedar registrada en DD-30 y corregida en `03` (tarea 9.1). |
| D4 | Fundada | El bloqueo por sillón es una **Suposición** de `04` que el scope de C-11 no lista. Pasarlo al backlog es correcto. |
| D5 | Fundada (por ausencia), con consecuencia a aceptar | RN-AG-12 es de turnos; no hay regla temporal para bloqueos. La consecuencia (H10) sale de leer "turnos activos" como "no cancelados", que es la definición de la KB (RN-AG-07, DD-21 d). |
| D6 | Fundada (por ausencia) | DD-15 y DD-27 (c) alinean turnos y franjas; exigir grilla al bloqueo sería la regla nueva. Falta escenario (H5). |
| D7 | Fundada; el largo es un parámetro nuevo menor | RN-HB-02 ("con motivo"), `04` (`fin > inicio`, "texto corto"); recorte y no vacío por precedente (DD-26 f, `franja_invalida`). Los 255 caracteres copian `motivo_cancelacion`; no hay fuente en la KB, pero es un parámetro técnico, no una regla de negocio. |
| D8 | Fundada por analogía | DD-27 (j) (franjas de un profesional desactivado) y DD-26 (h). |
| D9 | Fundada; los campos son precisión de contrato | RN-HB-03, DD-12 y US-003 piden listar los turnos afectados. Omitir paciente y prestación es coherente con la minimización de DD-25 (f) y RN-CU-01. |
| D11 | Fundada; el filtro es precisión de contrato | `CHANGES.md` pide `GET`; RN-AU-02 limita al odontólogo. Dejar los rangos para C-13 respeta el scope. `[]` ante un filtro inexistente es coherente con DD-21 (c): el query no es body ni path. |
| D12 | Fundada, con un matiz | "CRD solo propios" (`03`) más "solo bloquea sus propias franjas" (RN-AU-02) sostienen leer "propios" como "de su profesional". El orden `404` → `403` se aparta del criterio de DD-27 (i) (`403` antes de la existencia, para no revelarla). Lo justifica que la propiedad exige leer el bloqueo, pero es una precisión nueva que conviene aprobar de forma explícita (y fijar con un escenario, H5). |
| D13 | Fundada; satisface la intención de la regla dura | Ver el detalle abajo. |

**D13 en detalle.** La regla dura ("NUNCA confiar solo en la validación de la aplicación para evitar solapamientos") nombra la exclusión por profesional, por sillón y por paciente, es decir, turno contra turno, y esa garantía queda intacta. Para bloqueo contra turno, la propia KB reconoce que una `EXCLUDE` no alcanza:
- `08` (Nota): "las restricciones de exclusión no cubren horario de atención ni bloqueos".
- DD-02, trade-off: "horario y bloqueos siguen validándose en aplicación".
- `05`, excepciones globales: distingue "solapamiento → 409" de "bloqueo → 422".

D13 aplica la alternativa 2 de `08` §Concurrencia, con el mismo patrón ya aprobado y archivado en DD-26 (i) (desactivación) y DD-27 (k) (franjas). Así elimina el "comprobar y luego insertar" sin serialización, que es lo que la regla dura busca evitar.

Verificado en el código:
- `cargar_referencias` lee el profesional con `FOR SHARE` (`with_for_update={"read": True}`) antes de los validadores, en el alta y en la reprogramación. En la reprogramación usa el profesional destino.
- `RepositorioHorarios.bloquear_profesional` usa `FOR NO KEY UPDATE` (`key_share=True`). Los dos modos se excluyen.
- `FOR SHARE` es compartido, así que dos altas de turno no se serializan entre sí.

El límite (SQL directo) está declarado, igual que en DD-25, con el rol de mínimo privilegio en el backlog. El test de concurrencia obligatorio existe (tarea 7.1), contra PostgreSQL real, con RED verificado sin el lock. Las mejoras de cobertura son H2 y H11, y la de documentación es H12.

## Fuera de esta revisión

- No se ejecutaron tests ni se probó empíricamente el entrelazado de locks en PostgreSQL. La semántica de D13 se verificó leyendo el código actual (`validacion_turno.py`, `repositorio_turnos.py`, `repositorio_horarios.py`, `api/turnos.py`) y la matriz de conflictos de locks de fila de PostgreSQL.
- No se consultó Context7. El change no fija APIs de terceros nuevas; reusa `AwareDatetime`, `Field(max_length=…)` y `with_for_update`, que ya están en uso.
- No se verificó si la rama de C-13 reclama la migración `010` ni DD-30. Lo cubren las tareas 9.1 y 9.2.
- No se revisaron los 12 escenarios heredados del requirement MODIFIED más allá de confirmar que son idénticos al spec archivado.
