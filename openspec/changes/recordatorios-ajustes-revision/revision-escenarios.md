# Revisión de escenarios — recordatorios-ajustes-revision (C-12, change de seguimiento)

- Fecha: 2026-11-03
- Specs revisados: `openspec/changes/recordatorios-ajustes-revision/specs/recordatorios/spec.md` (delta), contrastado con `openspec/specs/recordatorios/spec.md` (principal) y `openspec/specs/agenda-turnos/spec.md` (criterio de "iniciado")
- Artefactos leídos: `proposal.md`, `design.md` (D1..D8), `tasks.md`, bloque `[C-12]` y backlog de `CHANGES.md`
- Scope: bloque `[C-12]` de `CHANGES.md` más los 8 hallazgos de la revisión del PR #8. No hay bloque propio en `CHANGES.md` (lo declara el proposal)
- Reglas aplicables: RN-NO-01, RN-NO-02, RN-NO-04, RN-NO-05, RN-AG-13, DD-04, DD-08, DD-13, DD-14, DD-19, DD-21, DD-23, DD-28 (a, c, d, e), DD-29 (pendiente: D1..D4 **[A confirmar]**), 04 §Recordatorio, 07 Flujo 6, 08 (Compose), preguntas abiertas "Recordatorio procesado después del inicio del turno" y "Backoff perdido al reiniciar el worker" de `10_preguntas_abiertas.md`
- `openspec validate recordatorios-ajustes-revision --strict`: válido
- Veredicto: **LISTO PARA APPLY**, sin hallazgos BLOQUEANTE ni MAYOR. Condición de governance (no es un defecto del spec): el usuario aprueba D1..D4 antes del Apply, como exige `tasks.md`. Si alguna se aprueba con su alternativa, `/opsx:update` primero

## Cobertura

| Requirement | Escenarios | Esperado | Error de negocio | Borde | Reglas cubiertas |
|-------------|-----------:|:--------:|:----------------:|:-----:|------------------|
| Sin envío para turnos ya iniciados (ADDED) | 4 | ✅ | ✅ | ✅ | D1/DD-29, RN-AG-13, DD-23, RN-NO-01 (implícita) |
| Devolución a la cola de lo tomado y no procesado (ADDED) | 2 | — | ✅ (falla de infraestructura) | ✅ | D4/DD-29, DD-28 (crash-only) |
| La API depende de Redis en Compose (ADDED) | 1 | ✅ | — | — | D8, 08 |
| Envío del recordatorio vencido por el worker (MODIFIED) | 4 | ✅ | — | ✅ | RN-NO-01, Flujo 6, DD-04, D6 |
| Reintentos con backoff exponencial y estado fallido (MODIFIED) | 6 | ✅ | ✅ | ✅ | RN-NO-05, DD-19, DD-28 (d, e), D2/DD-29 |
| Re-encolado de pendientes al iniciar el worker (MODIFIED) | 4 | ✅ | — | ✅ | DD-28 (c), Flujo 6 (errores), D2/DD-29 |
| Integridad del recordatorio en la base (MODIFIED) | 5 | ✅ | ✅ | ✅ | DD-08, DD-21, DD-28 (a), D3/DD-29 |
| Cola de recordatorios con vencimiento (MODIFIED) | 4 | ✅ | — | ✅ | DD-04, 08 §Patrones aplicados, D7 |

Total: 30 escenarios (7 de requisitos nuevos y 23 de requisitos modificados).

Reglas del scope sin escenario: ninguna.

### Preservación de los requisitos MODIFIED

Se comparó cada bloque MODIFIED con su versión en `openspec/specs/recordatorios/spec.md`. Los nombres coinciden exactamente y **no se pierde ningún escenario**: los 17 escenarios originales de los cinco bloques siguen presentes (Cola 3/3, Envío 3/3, Reintentos 5/5, Re-encolado 3/3, Integridad 3/3), y se agregan 6.

| Requirement | Cambios respecto del principal |
|-------------|--------------------------------|
| Cola de recordatorios con vencimiento | Texto del requirement idéntico. Escenario nuevo: "Consumidores simultáneos no comparten elementos" |
| Envío del recordatorio vencido | Requirement: suma "el turno todavía no inició" y "el mock MUST NOT acumular". "El adaptador mock registra el envío": el THEN suma "en el log" y "sin guardar el mensaje en memoria". Escenario nuevo: "Envíos repetidos no acumulan estado" |
| Reintentos | Requirement: el próximo intento se persiste en `programado_para`, con el reloj del momento de la falla. Primer, segundo y tercer intento suman `programado_para` en el THEN (13:01Z, 13:03Z, y 13:03Z sin cambio en el tercero). Los otros dos escenarios no cambian. Escenario nuevo: "La espera se cuenta desde el momento de la falla" |
| Re-encolado | Requirement: aclara que `programado_para` es el próximo intento. Escenarios originales sin cambios. Escenario nuevo: "El reinicio conserva la espera del reintento" |
| Integridad | Requirement y "Valores inválidos rechazados" suman `pendiente` con 3 intentos. Escenarios nuevos: "Un pendiente no llega a 3 intentos" y "Restricción reversible" |

Ningún escenario de los requisitos que no se modifican (programación, cancelación, reprogramación, atomicidad, encolado, contenido, a lo sumo un pendiente, worker en Compose) queda contradicho. "Programación del recordatorio al crear un turno" sigue fijando `programado_para = inicio - REMINDER_LEAD_HOURS` **al crear**, lo que es compatible con el nuevo significado de D2.

### Evaluación de D1..D4 (reglas nuevas)

Las cuatro figuran como **[A confirmar]** en `design.md`, con su alternativa y el destino DD-29. Los requisitos las citan como "a registrar en DD-29", y la tarea 10.1 registra DD-29 y anota en DD-28 lo que reemplaza. No se asumen en silencio. Además, D1 y D2 resuelven las dos preguntas abiertas registradas en `10`, y la tarea 10.2 las mueve a resueltas.

- **D1 (sin envío si `inicio <= ahora`, queda `cancelado`)**: el criterio de "iniciado" tiene respaldo. RN-AG-13 y DD-14 dicen "ya iniciado o pasado", DD-23 (d) lo repite, y el spec archivado `agenda-turnos` (requirement de cancelación) lo fija como "inicio igual o anterior al instante actual". El código usa `inicio <= ahora` en `validar_modificable`. **Ojo**: RN-AG-12 y DD-11 usan otro borde ("inicio **anterior** a ahora", estricto) para crear y reprogramar. El spec hace bien en usar el criterio de RN-AG-13 y no el de RN-AG-12. Es coherente con RN-NO-01 ("recordatorio **previo**": uno enviado después del inicio no es previo). Respecto de RN-NO-02, reusar `cancelado` mezcla dos motivos (turno cancelado y turno ya iniciado). El design lo reconoce y deja la alternativa `vencido`. La pregunta abierta de `10` preguntaba justamente "¿con qué estado?", así que la elección es materia de DD-29. El orden "estado antes que hora" replica DD-22 y DD-23.
- **D2 (`programado_para` = próximo intento)**: es coherente con DD-19 y DD-28 (d), que no cambian (1 y 2 min, 3 intentos). En cambio, **revierte** dos puntos explícitos de DD-28: la alternativa descartada "columna `proximo_intento_en`" (se reusa la columna existente, no se agrega una) y la limitación aceptada "el re-encolado al reiniciar ignora el backoff restante". Por eso necesita DD-29 y no puede quedar como detalle de implementación. La tarea 10.1 lo cubre. Cambia la definición de 04 §Recordatorio (`inicio - REMINDER_LEAD_HOURS`), y la tarea 5.5 la actualiza. El disparador de 07 Flujo 6 ("llega `programado_para`") queda incluso más preciso.
- **D3 (CHECK `estado <> 'pendiente' OR intentos < 3`)**: casi se deduce de la KB. RN-NO-05 y DD-28 (e) dicen "agotados los intentos, `fallido`", así que un `pendiente` con 3 intentos ya es un dato imposible según la KB. Extiende la coherencia estado/intentos de DD-28 (a). Marcarla [A confirmar] es conservador y correcto.
- **D4 (devolver lo no procesado y relanzar)**: compatible con el diseño crash-only de DD-28. No cambia el contrato del puerto. Su respaldo es solo el hallazgo 5 del PR, así que está bien que pase por DD-29.

### Otros controles

- **C3 (scope)**: nada de C-10, C-11, C-13 ni del frontend. El endpoint de lectura del estado de los recordatorios queda explícitamente fuera. La línea del backlog "Persistir el vencimiento del próximo reintento..." se saca del backlog con un change nuevo, como pide `CLAUDE.md` ("nada de eso se implementa sin un change nuevo"), y la tarea 10.3 la quita.
- **C4 (HTTP)**: sin cambios de contrato. No aplica.
- **C5 y C6 (verificabilidad y reloj)**: todos los THEN se pueden afirmar con un assert (estado, `intentos`, `programado_para`, contenido de la cola, invocaciones del puerto, `depends_on`). Los escenarios que dependen de "ahora" fijan el reloj, incluido el borde `inicio == ahora` (13:00Z → `cancelado`) y su contraparte un minuto antes (12:59Z → `enviado`). "Envíos repetidos no acumulan estado" **no es tautológico**: con el código actual falla (crece `enviados`), así que es un RED válido.
- **D7 (un solo viaje a Redis)**: el spec **no** afirma "un viaje", solo entrega a un solo consumidor y consumidores simultáneos. Así que no queda ninguna afirmación del spec sin verificar. La justificación del design para no contar viajes es correcta: el test tendría que espiar internos de redis-py (`execute_command`, `EVALSHA` con caída a `EVAL`), quedaría acoplado a la implementación y no a un comportamiento, y pasaría o fallaría por razones ajenas al contrato. "Consumidores simultáneos" pasa con el código actual (la tarea 8.1 lo reconoce): es una red de seguridad del refactor 8.2, no un RED. Es legítimo en TDD (refactor con la suite en verde).
- **C8 (reglas duras)**: datos ficticios (R1..R3 e ids). Sin secretos. El contenido del log sigue sin prestación (RN-NO-04). La entrega a un solo consumidor tiene un escenario de concurrencia contra Redis real, y "Procesamiento simultáneo del mismo recordatorio" del principal sigue vigente.
- **C9 (tareas)**: todos los escenarios nuevos o modificados tienen tarea. Sin iniciar → 6.1 (los 4). Devolución → 7.2 y 7.3. Compose → 9.1. Mock → 3.2. Primer, segundo y tercer intento → 5.3. La espera desde la falla → 5.4. Reinicio con espera → 5.1. Integridad → 4.1 y 4.3. Consumidores simultáneos → 8.1. Los escenarios sin cambios los cubren los tests existentes, ajustados en 2.2 y 3.1. Las tareas sin escenario son de preparación, refactor, fakes o documentación (1.1, 2.1, 2.2, 3.1, 4.2, 5.2, 7.1, 8.2, 4.4, 5.5, 6.2, 9.2, 10.x, 11.x). Son legítimas.

## Hallazgos

### H1 — Cita ambigua "design D2, a registrar en DD-28" en Integridad · MENOR
- **Dónde**: `specs/recordatorios/spec.md`, requirement "Integridad del recordatorio en la base" (texto del requirement)
- **Problema**: el texto heredado del principal cita "design D2, a registrar en DD-28", que es el D2 del design de C-12, y agrega "design D3, a registrar en DD-29", que es el de este change. Dentro de este change, "design D2" ahora remite a otra decisión: el backoff persistido. Además, DD-28 ya está registrada.
- **Fuente**: `09_decisiones_y_supuestos.md` §DD-28 (a); `design.md` de este change, D2
- **Sugerencia**: reemplazar por "DD-28 (a); design D3, a registrar en DD-29", o directamente "DD-29" una vez registrada.

### H2 — Escenarios del worker sin inicio de turno explícito · MENOR
- **Dónde**: "Error a mitad de lote", "La devolución también falla", "La espera se cuenta desde el momento de la falla", "Primer/Segundo/Tercer intento fallido" y "El reinicio conserva la espera del reintento"
- **Problema**: con D1, el resultado de todo procesamiento depende de `inicio` frente al reloj, pero estos GIVEN dicen solo "de un turno `programado`", sin el inicio. Los tests no quedan indeterminados, porque `helpers_recordatorios.INICIO_TURNO` fija 2026-10-09T13:00Z, posterior a todos los relojes usados. El riesgo es solo de redacción.
- **Fuente**: `references/controles.md` C6; design D1
- **Sugerencia**: agregar al GIVEN "con inicio 2026-10-09T13:00Z", o una nota común al requisito: "salvo indicación, los turnos inician 2026-10-09T13:00Z".

### H3 — "No vuelve a encolarse" solo se afirma en uno de los cuatro escenarios de D1 · MENOR
- **Dónde**: requirement "Sin envío para turnos ya iniciados", escenarios "Recordatorio re-encolado después de una caída larga" y "Reintento pendiente de un turno ya iniciado"
- **Problema**: el requirement exige "MUST NOT volver a encolarse", pero solo "Turno que empieza en el momento de procesar" lo comprueba ("la cola ya no lo contiene"). En el caso del reintento conviene afirmarlo explícitamente, porque es el que viene del camino de reencolado.
- **Fuente**: texto del propio requirement (design D1: "sin envío y sin re-encolar")
- **Sugerencia**: sumar al THEN de ambos "y la cola ya no lo contiene".

### H4 — D1 no cita RN-NO-01 y la tarea 6.2 deja la RN a precisar sin decidir · MENOR
- **Dónde**: requirement "Sin envío para turnos ya iniciados"; `tasks.md` 6.2 ("RN-NO-01 o RN-NO-02, precisada en DD-29")
- **Problema**: el anclaje más directo de D1 en la KB es RN-NO-01 ("recordatorio **previo**"). La tarea deja abierta cuál RN se anota, y el que haga el Apply tendría que decidir algo que corresponde al Propose.
- **Fuente**: `05_reglas_de_negocio.md` RN-NO-01 y RN-NO-02; `references/controles.md` C2
- **Sugerencia**: citar RN-NO-01 en el requirement y fijar en 6.2 cuál se anota: RN-NO-01 por "no se envía después del inicio", y RN-NO-02 solo si DD-29 confirma `cancelado` como estado de descarte.

### H5 — Ninguna tarea documenta en 04 la nueva causa de `cancelado` · MENOR
- **Dónde**: `tasks.md` 4.4 y 5.5 (actualizan 04 §Recordatorio solo por el CHECK y por `programado_para`)
- **Problema**: 04 §Recordatorio dice "al cancelar el turno, el recordatorio pendiente pasa a `cancelado`", como si esa fuera la única causa. Con D1, `cancelado` también significa "descartado porque el turno ya inició". Las tareas 6.2 y 10.1 lo llevan a 07, 05 y 09, pero no a la entidad.
- **Fuente**: `04_modelo_de_datos.md` §Recordatorio; design D1 (riesgo "mezcla dos motivos")
- **Sugerencia**: ampliar 6.2 para incluir 04 §Recordatorio.

### H6 — Las tareas afirman detalles de log que el spec no fija · SUGERENCIA
- **Dónde**: `tasks.md` 3.2 ("sin `paciente_id`" en el log del mock) y 7.3 (`warning` en `caplog` sin datos de pacientes)
- **Problema**: los tests verifican comportamiento que figura en el design (D4, D6, commit `cc627a3`) pero no en los THEN del spec. No contradice nada. Pero la regla dura "nada en Apply que no esté en el spec aprobado" se lee mejor si el spec lo dice.
- **Fuente**: `CLAUDE.md` §Reglas duras · Proceso; design D4 y D6
- **Sugerencia**: sumar "sin el id del paciente" al THEN de "El adaptador mock registra el envío" y "se registra una advertencia sin datos de pacientes" al de "La devolución también falla". La otra opción es aceptar que son asserts de diseño.

### H7 — Bordes opcionales de D4 y de la migración 009 · SUGERENCIA
- **Dónde**: requirements "Devolución a la cola..." e "Integridad..."
- **Problema**: no hay escenario para (a) un error en el **último** elemento del lote (no hay nada que devolver), (b) un error de la **base**, no de la cola, a mitad de lote (R2 queda con sus `intentos` originales, porque la transacción se revirtió), ni (c) el `upgrade` de `009` sobre datos que violan el CHECK (el design dice que falla de forma explícita).
- **Fuente**: design D3 y D4
- **Sugerencia**: el equipo decide. Ninguno es exigido por la KB. El (b) es el más informativo, porque es el caso que motiva que "el recordatorio del error MUST NOT devolverse".

### H8 — Trazabilidad del change en el roadmap · SUGERENCIA
- **Dónde**: `CHANGES.md` (bloque `[C-12]`, marcado `[x]`), tarea 10.3
- **Problema**: el change no tiene bloque propio (es una decisión del proposal), y la tarea 10.3 solo borra la línea del backlog. Quien lea `CHANGES.md` no ve que C-12 tuvo un change de seguimiento con reglas nuevas (DD-29).
- **Fuente**: `CHANGES.md` §Fuera de alcance / backlog; `CLAUDE.md` §Roadmap
- **Sugerencia**: en 10.3, agregar al bloque `[C-12]` una línea "Seguimiento: `recordatorios-ajustes-revision` (revisión del PR #8, DD-29)".

## Preguntas abiertas

- **Estado del descarte por turno iniciado** (D1): `cancelado` (recomendado) o un estado nuevo `vencido`. Ya está planteada en el design. La decide el usuario al aprobar DD-29.
- **Margen mínimo antes del inicio** (opcional, no surge de la KB): con D1, un recordatorio atrasado se envía hasta un minuto antes del inicio (escenario "Recordatorio atrasado que todavía llega antes del inicio"). La KB no dice si un aviso con minutos de anticipación sigue siendo útil. Opciones: (a) dejarlo así, que es lo que hace el spec; (b) un umbral mínimo, que sería una regla nueva y requeriría su propia DD. No bloquea.
- **Lectura del estado de los recordatorios**: sigue abierta y fuera de este change, sin cambios.

## Fuera de esta revisión

- La implementación real de D5 a D8 (firmas, script Lua y fakes) y el baseline de tests: se verifican en el Apply (tareas 1.1 y 11.1).
- La aprobación de D1..D4: es una decisión del usuario (governance ALTO), no de esta revisión.
- El conteo de "29 llamadas a `ciclo(ahora)`" del design no se verificó contra el código.
