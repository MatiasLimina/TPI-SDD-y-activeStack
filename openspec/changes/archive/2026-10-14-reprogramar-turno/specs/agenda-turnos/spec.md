# Spec Delta

## ADDED Requirements

### Requirement: Reprogramación de un turno programado
El sistema SHALL exponer `PATCH /turnos/{id}/reprogramar`. Reprogramar un turno `programado` cuyo inicio todavía no llegó MUST actualizar la misma fila (mismo `id`, paciente, prestación y `estado = programado`), recalcular `fin = inicio + duración` y responder `200` con el turno, sus instantes en `America/Argentina/Buenos_Aires`. MUST NOT crearse una fila nueva. Sin autenticación en este change.

#### Scenario: Turno movido a un hueco libre
- **GIVEN** dado un turno `programado` del profesional A, sillón 1, paciente P y prestación "Limpieza" (45 min) de 2026-10-08 10:00 a 10:45 hora local, y que el reloj marca 2026-10-07 09:00 hora local
- **WHEN** cuando se envía `PATCH /turnos/{id}/reprogramar` con `inicio` 2026-10-08T15:00-03:00
- **THEN** entonces la respuesta es `200` con el mismo `id`, `estado = programado`, `inicio` 2026-10-08T15:00-03:00 y `fin` 2026-10-08T15:45-03:00, y en la base esa fila tiene `inicio` 2026-10-08T18:00Z y no existe ninguna otra fila para ese paciente

#### Scenario: Cambio de profesional y de sillón
- **GIVEN** dado un turno `programado` futuro del profesional A en el sillón 1 de 10:00 a 10:45, y el profesional B y el sillón 2 activos y libres en ese horario
- **WHEN** cuando se reprograma informando `profesional_id` del profesional B y `sillon_id` del sillón 2
- **THEN** entonces la respuesta es `200`, el turno conserva su `id`, inicio, fin, paciente y prestación, y en la base queda asignado al profesional B y al sillón 2

### Requirement: Reprogramación parcial
Los campos editables al reprogramar SHALL ser `inicio`, `profesional_id`, `sillon_id` y `duracion_min`. Un campo omitido MUST conservar el valor actual del turno, incluida una duración ajustada, que MUST NOT volver a la duración de la prestación (DD-23). Un campo informado con valor nulo MUST distinguirse de uno omitido: `sillon_id` nulo quita el sillón del turno resultante, y `inicio`, `profesional_id` o `duracion_min` nulos MUST responder `422` sin modificar el turno.

#### Scenario: Solo un nuevo inicio conserva la duración ajustada
- **GIVEN** dado un turno futuro de la prestación "Limpieza" (45 min) creado a las 10:00 con `duracion_min = 60`
- **WHEN** cuando se reprograma informando solo `inicio` a las 15:00 del mismo día
- **THEN** entonces la respuesta es `200`, el turno queda con `duracion_min = 60`, `fin` a las 16:00, y los mismos profesional y sillón

#### Scenario: Solo una nueva duración conserva el inicio
- **GIVEN** dado un turno futuro de 10:00 a 10:45 de la prestación "Limpieza"
- **WHEN** cuando se reprograma informando solo `duracion_min = 30`
- **THEN** entonces la respuesta es `200`, el turno conserva el inicio 10:00 y queda con `fin` a las 10:30

#### Scenario: Volver a la duración de la prestación informándola
- **GIVEN** dado un turno futuro de la prestación "Limpieza" (45 min) creado a las 10:00 con `duracion_min = 60`
- **WHEN** cuando se reprograma informando `duracion_min = 45`
- **THEN** entonces la respuesta es `200` y el turno queda con `duracion_min = 45` y `fin` a las 10:45

#### Scenario: Body sin campos editables
- **GIVEN** dado un turno `programado` futuro de 10:00 a 10:45 cuyas referencias siguen activas
- **WHEN** cuando se reprograma enviando `{}`
- **THEN** entonces la respuesta es `200` y el turno sigue de 10:00 a 10:45 con los mismos profesional, sillón y duración

#### Scenario: Nulo explícito en un campo obligatorio
- **GIVEN** dado un turno `programado` futuro de 10:00 a 10:45
- **WHEN** cuando se reprograma enviando `{"inicio": null}`, o `{"profesional_id": null}`, o `{"duracion_min": null}`
- **THEN** entonces la respuesta es `422` y el turno sigue de 10:00 a 10:45 con su profesional y su duración

#### Scenario: Sillón nulo explícito con prestación que lo requiere
- **GIVEN** dado un turno futuro de la prestación "Limpieza", que requiere sillón, en el sillón 1
- **WHEN** cuando se reprograma enviando `{"sillon_id": null}`
- **THEN** entonces la respuesta es `422` por sillón requerido y el turno sigue en el sillón 1

#### Scenario: Sillón informado con prestación que no lo requiere
- **GIVEN** dado un turno futuro de la prestación "Consulta", que no requiere sillón, sin sillón asignado
- **WHEN** cuando se reprograma informando un `sillon_id` válido y activo
- **THEN** entonces la respuesta es `422` por sillón que no corresponde y el turno sigue sin sillón

### Requirement: Paciente y prestación no editables
Si el body de la reprogramación incluye `paciente_id` o `prestacion_id`, con cualquier valor, el sistema MUST responder `422` con el código `campo_no_editable`, la lista de los campos rechazados y un mensaje que indique a la recepcionista cancelar el turno y crear uno nuevo, sin modificar el turno (DD-23). Este rechazo MUST evaluarse antes que el estado del turno. Otros campos desconocidos MUST ignorarse.

#### Scenario: Cambio de paciente rechazado
- **GIVEN** dado un turno `programado` futuro
- **WHEN** cuando se reprograma informando `paciente_id` y un nuevo `inicio`
- **THEN** entonces la respuesta es `422` con código `campo_no_editable`, la lista de campos `["paciente_id"]` y un mensaje que indica cancelar el turno y crear uno nuevo, y el turno no cambia

#### Scenario: Paciente y prestación rechazados juntos
- **GIVEN** dado un turno `programado` futuro
- **WHEN** cuando se reprograma informando `paciente_id` y `prestacion_id`
- **THEN** entonces la respuesta es `422` con código `campo_no_editable` y la lista de campos `["paciente_id", "prestacion_id"]`

#### Scenario: Mismo paciente informado igualmente rechazado
- **GIVEN** dado un turno `programado` futuro del paciente P
- **WHEN** cuando se reprograma informando `paciente_id` del mismo paciente P
- **THEN** entonces la respuesta es `422` con código `campo_no_editable`

#### Scenario: Campo no editable sobre un turno cancelado
- **GIVEN** dado un turno cancelado
- **WHEN** cuando se lo reprograma informando `prestacion_id`
- **THEN** entonces la respuesta es `422` con código `campo_no_editable`, no `409`

#### Scenario: Campo desconocido ignorado
- **GIVEN** dado un turno `programado` futuro de 10:00 a 10:45
- **WHEN** cuando se reprograma informando `inicio` a las 15:00 y un campo `observaciones`
- **THEN** entonces la respuesta es `200` y el turno queda de 15:00 a 15:45

### Requirement: Misma validación que el alta al reprogramar
Reprogramar MUST aplicar al turno resultante las mismas validaciones que el alta: referencias existentes y activas, duración y grilla de 5 minutos, inicio no anterior al instante actual y coherencia del sillón con la prestación, todas con `422` (RN-AG-08). Las validaciones que responden `422` MUST evaluarse antes que la verificación de solape, y ante cualquier `422` el turno MUST quedar intacto.

#### Scenario: Duración inválida
- **GIVEN** dado un turno `programado` futuro de 10:00 a 10:45
- **WHEN** cuando se reprograma informando `duracion_min = 42`
- **THEN** entonces la respuesta es `422` y en la base el turno sigue de 10:00 a 10:45 con `duracion_min = 45`

#### Scenario: Inicio no alineado a 5 minutos
- **GIVEN** dado un turno `programado` futuro de 10:00 a 10:45
- **WHEN** cuando se reprograma informando `inicio` a las 15:07 hora local
- **THEN** entonces la respuesta es `422` y el turno sigue de 10:00 a 10:45

#### Scenario: Inicio sin zona horaria
- **WHEN** cuando se reprograma un turno informando un `inicio` sin zona horaria
- **THEN** entonces la respuesta es `422` y el turno no cambia

#### Scenario: Nuevo inicio en el pasado
- **GIVEN** dado un turno `programado` con inicio 2026-10-08 10:00 hora local y que el reloj marca 2026-10-07 09:00 hora local
- **WHEN** cuando se lo reprograma con `inicio` 2026-10-07 08:55 hora local
- **THEN** entonces la respuesta es `422` y el turno sigue con inicio 2026-10-08 10:00

#### Scenario: Profesional destino inactivo
- **GIVEN** dado un turno `programado` futuro y un profesional B inactivo
- **WHEN** cuando se lo reprograma informando `profesional_id` del profesional B
- **THEN** entonces la respuesta es `422` indicando la referencia `profesional` y el turno sigue con su profesional original

#### Scenario: Sillón destino inexistente
- **WHEN** cuando se reprograma un turno `programado` futuro informando un `sillon_id` que no existe
- **THEN** entonces la respuesta es `422` indicando la referencia `sillon`, y no `404`

#### Scenario: Reprogramación inválida y en conflicto
- **GIVEN** dado un turno activo del profesional A de 15:00 a 15:45 y otro turno `programado` futuro del profesional A de 10:00 a 10:45
- **WHEN** cuando se reprograma el segundo a las 15:15 con `duracion_min = 42`
- **THEN** entonces la respuesta es `422`, no `409`

### Requirement: Sin solape al reprogramar, excluyendo al propio turno
El turno resultante MUST NOT solaparse con otro turno activo del mismo profesional, sillón o paciente (RN-AG-01, RN-AG-02, RN-AG-14); el intento MUST responder `409` listando todos los recursos en conflicto y dejar el turno intacto. El propio turno MUST NOT contar para esta verificación, por lo que solaparse con su intervalo anterior es válido; los turnos cancelados tampoco cuentan.

#### Scenario: Hueco ocupado por otro turno del profesional
- **GIVEN** dado un turno activo del profesional A de 15:00 a 15:45 y otro turno `programado` del profesional A de 10:00 a 10:45 del mismo día futuro
- **WHEN** cuando se reprograma el segundo a las 15:15
- **THEN** entonces la respuesta es `409` indicando el recurso `profesional`, y en la base el segundo turno sigue de 10:00 a 10:45

#### Scenario: Solaparse consigo mismo es válido
- **GIVEN** dado un turno `programado` futuro del profesional A, sillón 1 y paciente P de 10:00 a 10:45, sin otros turnos ese día
- **WHEN** cuando se lo reprograma a las 10:15
- **THEN** entonces la respuesta es `200` y el turno queda de 10:15 a 11:00

#### Scenario: Extender la duración sobre el propio intervalo
- **GIVEN** dado un turno `programado` futuro de 10:00 a 10:45, sin otros turnos ese día
- **WHEN** cuando se lo reprograma informando `duracion_min = 90`
- **THEN** entonces la respuesta es `200` y el turno queda de 10:00 a 11:30

#### Scenario: Solape con otro turno del mismo paciente
- **GIVEN** dado un turno activo del paciente P con el profesional B en el sillón 2 de 12:00 a 12:45, y otro turno `programado` del paciente P con el profesional A en el sillón 1 de 10:00 a 10:45 del mismo día futuro
- **WHEN** cuando se reprograma el segundo a las 12:15
- **THEN** entonces la respuesta es `409` indicando el recurso `paciente` y el segundo turno sigue de 10:00 a 10:45

#### Scenario: 409 que lista varios recursos
- **GIVEN** dado un turno activo del profesional A, sillón 1 y paciente P de 15:00 a 15:45, y otro turno `programado` del profesional A, sillón 1 y paciente P de 10:00 a 10:45 del mismo día futuro
- **WHEN** cuando se reprograma el segundo a las 15:15
- **THEN** entonces la respuesta es `409` y lista los recursos `profesional`, `sillon` y `paciente`

#### Scenario: Reprogramar a un horario contiguo
- **GIVEN** dado un turno activo del profesional A en el sillón 1 de 15:00 a 15:45 y otro turno `programado` del profesional A en el sillón 1 de 10:00 a 10:45 del mismo día futuro, con otro paciente
- **WHEN** cuando se reprograma el segundo a las 15:45
- **THEN** entonces la respuesta es `200` y el turno queda de 15:45 a 16:30

#### Scenario: Un turno cancelado en el destino no bloquea
- **GIVEN** dado un turno cancelado del profesional A, sillón 1 de 15:00 a 15:45 y otro turno `programado` del profesional A, sillón 1 de 10:00 a 10:45 del mismo día futuro
- **WHEN** cuando se reprograma el segundo a las 15:00
- **THEN** entonces la respuesta es `200`

### Requirement: Reprogramable solo antes del inicio
Un turno MUST poder reprogramarse solo mientras el instante actual del reloj del sistema sea anterior a su inicio actual. Si ese inicio es igual o anterior al instante actual, la reprogramación MUST responder `409` con el código `turno_ya_iniciado` sin modificar el turno, aunque el nuevo inicio informado sea futuro (DD-23).

#### Scenario: Reprogramación un minuto antes del inicio
- **GIVEN** dado un turno `programado` con inicio 2026-10-07 10:00 hora local y que el reloj marca 2026-10-07 09:59 hora local
- **WHEN** cuando se lo reprograma a 2026-10-08 10:00 hora local
- **THEN** entonces la respuesta es `200`

#### Scenario: Reprogramación en el instante exacto del inicio
- **GIVEN** dado un turno `programado` con inicio 2026-10-07 10:00 hora local y que el reloj marca 2026-10-07 10:00 hora local
- **WHEN** cuando se lo reprograma a 2026-10-08 10:00 hora local
- **THEN** entonces la respuesta es `409` con código `turno_ya_iniciado` y el turno sigue con inicio 2026-10-07 10:00

#### Scenario: Turno en curso movido al futuro
- **GIVEN** dado un turno `programado` de 10:00 a 10:45 hora local y que el reloj marca 10:20 hora local del mismo día
- **WHEN** cuando se lo reprograma al día siguiente a las 10:00
- **THEN** entonces la respuesta es `409` con código `turno_ya_iniciado` y el turno no cambia

#### Scenario: Turno pasado
- **GIVEN** dado un turno `programado` del día anterior al que marca el reloj
- **WHEN** cuando se lo reprograma a un horario futuro libre
- **THEN** entonces la respuesta es `409` con código `turno_ya_iniciado` y el turno no cambia

### Requirement: Turno cancelado no reprogramable
Reprogramar un turno `cancelado` MUST responder `409` con el código `turno_ya_cancelado`, el mismo que usa la cancelación, y MUST NOT modificar el turno (DD-23). El estado MUST evaluarse antes que el tiempo y antes que las validaciones del turno resultante.

#### Scenario: Turno cancelado
- **GIVEN** dado un turno futuro cancelado de 10:00 a 10:45
- **WHEN** cuando se lo reprograma a las 15:00
- **THEN** entonces la respuesta es `409` con código `turno_ya_cancelado`, y en la base sigue `cancelado` de 10:00 a 10:45

#### Scenario: Turno cancelado y pasado
- **GIVEN** dado un turno cancelado cuyo inicio ya pasó según el reloj del sistema
- **WHEN** cuando se lo reprograma a un horario futuro
- **THEN** entonces la respuesta es `409` con código `turno_ya_cancelado`

#### Scenario: Turno cancelado con datos inválidos
- **GIVEN** dado un turno futuro cancelado
- **WHEN** cuando se lo reprograma informando `duracion_min = 42`
- **THEN** entonces la respuesta es `409` con código `turno_ya_cancelado`, no `422`

### Requirement: Turno a reprogramar inexistente
Si el `id` del path no corresponde a ningún turno, la reprogramación MUST responder `404` (recurso del path, DD-21). Un `id` que no es un identificador válido MUST responder `422`.

#### Scenario: Turno inexistente
- **WHEN** cuando se envía `PATCH /turnos/{id}/reprogramar` con un `id` con formato válido que no existe
- **THEN** entonces la respuesta es `404`

#### Scenario: Identificador con formato inválido
- **WHEN** cuando se envía `PATCH /turnos/no-es-un-id/reprogramar`
- **THEN** entonces la respuesta es `422`

### Requirement: Reprogramaciones simultáneas hacia el mismo horario
Ante dos o más reprogramaciones simultáneas de turnos distintos hacia un mismo horario con un recurso compartido, exactamente una MUST tener éxito y las demás MUST recibir `409` por solape, con sus turnos intactos. La garantía MUST sostenerla la base de datos (RN-AG-09): si una carrera esquiva la verificación previa, el rechazo de la base MUST traducirse a `409` indicando el recurso.

#### Scenario: Turnos distintos movidos a la vez al mismo hueco
- **GIVEN** dados N turnos `programado` futuros del profesional A en horarios distintos y un hueco libre del profesional A, cada reprogramación en su propia conexión
- **WHEN** cuando todos se reprograman a la vez a ese hueco
- **THEN** entonces exactamente una reprogramación tiene éxito, las demás reciben conflicto por solape, en ese hueco queda un solo turno activo y los turnos perdedores conservan su horario original

#### Scenario: Carrera que esquiva la verificación previa
- **GIVEN** dado que la verificación previa no detecta conflicto pero la base rechaza la actualización por la exclusión de profesional
- **WHEN** cuando se procesa la reprogramación
- **THEN** entonces la respuesta es `409` indicando el recurso `profesional` y el turno conserva su horario original

### Requirement: Reprogramación y cancelación simultáneas del mismo turno
Una reprogramación y una cancelación simultáneas del mismo turno MUST serializarse: el resultado final MUST ser el mismo que si se hubieran ejecutado una después de la otra, en el orden en que obtuvieron el turno.

#### Scenario: La cancelación llega primero
- **GIVEN** dado un turno `programado` futuro de 10:00 a 10:45 y una cancelación y una reprogramación a las 15:00 simultáneas, en conexiones propias, donde la cancelación obtiene el turno primero
- **WHEN** cuando ambas terminan
- **THEN** entonces la cancelación tiene éxito, la reprogramación recibe `409` con código `turno_ya_cancelado`, y en la base el turno queda `cancelado` de 10:00 a 10:45

#### Scenario: La reprogramación llega primero
- **GIVEN** dado un turno `programado` futuro de 10:00 a 10:45 y una reprogramación a las 15:00 y una cancelación simultáneas, en conexiones propias, donde la reprogramación obtiene el turno primero
- **WHEN** cuando ambas terminan
- **THEN** entonces ambas tienen éxito y en la base el turno queda `cancelado` de 15:00 a 15:45
