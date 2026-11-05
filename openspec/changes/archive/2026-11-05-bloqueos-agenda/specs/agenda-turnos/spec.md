# Spec Delta

## ADDED Requirements

### Requirement: Turno fuera de los bloqueos de agenda
Al crear y al reprogramar, el intervalo `[inicio, fin)` del turno MUST NOT superponerse con un bloqueo de agenda de su profesional; un turno contiguo al bloqueo (empieza justo al terminar o termina justo al empezar) es válido (RN-AG-06, RN-AG-03). Si se superpone → `422 turno_en_bloqueo` sin persistir. Se evalúa después del horario de atención y antes del solape. Los escenarios asumen el reloj en 2026-10-07 09:00 local y una franja que cubre el turno.

#### Scenario: Turno dentro de un bloqueo
- **GIVEN** dado un bloqueo del profesional A el jueves 2026-10-08 de 10:00 a 12:00 hora local
- **WHEN** cuando una recepcionista autenticada crea un turno de A de 45 minutos el 2026-10-08 a las 10:30 hora local
- **THEN** entonces la respuesta es `422` con `{"detail": {"codigo": "turno_en_bloqueo", "mensaje": "el turno se superpone con un bloqueo de agenda del profesional"}}` y no se persiste ningún turno

#### Scenario: Turno que empieza antes y termina dentro del bloqueo
- **GIVEN** dado un bloqueo del profesional A el jueves 2026-10-08 de 10:00 a 12:00 hora local
- **WHEN** cuando se crea un turno de A de 45 minutos el 2026-10-08 a las 09:30 hora local
- **THEN** entonces la respuesta es `422` con código `turno_en_bloqueo` y no se persiste ningún turno

#### Scenario: Turno que empieza dentro y termina después del bloqueo
- **GIVEN** dado un bloqueo del profesional A el jueves 2026-10-08 de 10:00 a 12:00 hora local
- **WHEN** cuando se crea un turno de A de 45 minutos el 2026-10-08 a las 11:30 hora local
- **THEN** entonces la respuesta es `422` con código `turno_en_bloqueo` y no se persiste ningún turno

#### Scenario: Turno que contiene al bloqueo
- **GIVEN** dado un bloqueo del profesional A el jueves 2026-10-08 de 10:00 a 10:15 hora local
- **WHEN** cuando se crea un turno de A de 60 minutos el 2026-10-08 a las 09:45 hora local
- **THEN** entonces la respuesta es `422` con código `turno_en_bloqueo` y no se persiste ningún turno

#### Scenario: Turno que empieza justo al terminar el bloqueo
- **GIVEN** dado un bloqueo del profesional A el jueves 2026-10-08 de 10:00 a 12:00 hora local
- **WHEN** cuando se crea un turno de A de 45 minutos el 2026-10-08 a las 12:00 hora local
- **THEN** entonces la respuesta es `201` con `inicio` 2026-10-08T12:00:00-03:00

#### Scenario: Turno que termina justo al empezar el bloqueo
- **GIVEN** dado un bloqueo del profesional A el jueves 2026-10-08 de 10:00 a 12:00 hora local
- **WHEN** cuando se crea un turno de A de 45 minutos el 2026-10-08 a las 09:15 hora local
- **THEN** entonces la respuesta es `201` con `fin` 2026-10-08T10:00:00-03:00

#### Scenario: Bloqueo de otro profesional
- **GIVEN** dado un bloqueo del profesional B el jueves 2026-10-08 de 10:00 a 12:00 hora local
- **WHEN** cuando se crea un turno de A de 45 minutos el 2026-10-08 a las 10:30 hora local
- **THEN** entonces la respuesta es `201`

#### Scenario: Bloqueo de varios días
- **GIVEN** dado un bloqueo del profesional A desde 2026-10-08T00:00:00-03:00 hasta 2026-10-10T00:00:00-03:00
- **WHEN** cuando se crea un turno de A el viernes 2026-10-09 a las 15:00 hora local
- **THEN** entonces la respuesta es `422` con código `turno_en_bloqueo` y no se persiste ningún turno

#### Scenario: Fuera de horario y dentro de un bloqueo
- **GIVEN** dado el profesional A con la franja del jueves de 09:00 a 13:00 y un bloqueo de A el 2026-10-08 de 12:00 a 14:00 hora local
- **WHEN** cuando se crea un turno de A de 45 minutos el 2026-10-08 a las 12:30 hora local
- **THEN** entonces la respuesta es `422` con código `fuera_de_horario`, no `turno_en_bloqueo`, y no se persiste ningún turno

#### Scenario: Dentro de un bloqueo y en conflicto
- **GIVEN** dado un turno activo del profesional A el jueves 2026-10-08 de 09:30 a 10:15 y un bloqueo de A de 10:15 a 12:00 hora local
- **WHEN** cuando se crea otro turno de A de 45 minutos el 2026-10-08 a las 10:00 hora local
- **THEN** entonces la respuesta es `422` con código `turno_en_bloqueo`, no `409`, y no se persiste ningún turno

#### Scenario: Validaciones previas antes que el bloqueo
- **GIVEN** dado un bloqueo del profesional A el jueves 2026-10-08 de 10:00 a 12:00 hora local
- **WHEN** cuando se crea un turno de A el 2026-10-08 a las 10:30 hora local con `duracion_min = 42`
- **THEN** entonces la respuesta es `422` con código `duracion_invalida`, no `turno_en_bloqueo`, y no se persiste ningún turno

#### Scenario: Turno rechazado sin recordatorio
- **GIVEN** dado un bloqueo del profesional A el viernes 2026-10-09 de 10:00 a 12:00 hora local
- **WHEN** cuando se crea un turno de A el 2026-10-09 a las 10:30 hora local
- **THEN** entonces la respuesta es `422` con código `turno_en_bloqueo`, no se persiste ningún turno ni recordatorio, no se registra auditoría y no se encola nada en la cola de recordatorios

## MODIFIED Requirements

### Requirement: Misma validación que el alta al reprogramar
Reprogramar MUST aplicar al turno resultante las mismas validaciones que el alta: referencias existentes y activas, duración y grilla de 5 minutos, inicio no anterior al instante actual, sillón coherente con la prestación, horario de atención y bloqueos del profesional (RN-AG-05, RN-AG-06), todas con `422` (RN-AG-08). Esas validaciones MUST evaluarse antes que el solape, y ante cualquier `422` el turno MUST quedar intacto. Los escenarios de bloqueos asumen el reloj en 2026-10-07 09:00 local.

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

#### Scenario: Nuevo inicio fuera del horario
- **GIVEN** dado el profesional A con la franja del jueves de 09:00 a 13:00 y un turno `programado` de A el jueves 2026-10-08 de 10:00 a 10:45
- **WHEN** cuando se lo reprograma informando `inicio` 2026-10-08 12:30 hora local
- **THEN** entonces la respuesta es `422` con código `fuera_de_horario` y el turno sigue de 10:00 a 10:45

#### Scenario: Profesional destino sin franja ese día
- **GIVEN** dado un turno `programado` del profesional A el jueves 2026-10-08 de 10:00 a 10:45, dentro de su horario, y el profesional B activo sin franjas el jueves
- **WHEN** cuando se lo reprograma informando `profesional_id` de B
- **THEN** entonces la respuesta es `422` con código `fuera_de_horario` y el turno sigue con el profesional A

#### Scenario: Turno que quedó fuera de horario al reprogramar otro campo
- **GIVEN** dado un turno `programado` futuro de A el jueves de 12:30 a 13:15 en el sillón 1, y la franja de A del jueves editada después a 09:00-12:00
- **WHEN** cuando se lo reprograma informando solo `sillon_id` del sillón 2
- **THEN** entonces la respuesta es `422` con código `fuera_de_horario` y el turno sigue en el sillón 1 de 12:30 a 13:15

#### Scenario: Ampliar la duración más allá de la franja
- **GIVEN** dado el profesional A con la franja del jueves de 09:00 a 13:00 y un turno `programado` de A el jueves de 12:15 a 13:00
- **WHEN** cuando se lo reprograma informando solo `duracion_min = 60`
- **THEN** entonces la respuesta es `422` con código `fuera_de_horario` y el turno sigue de 12:15 a 13:00

#### Scenario: Reprogramación que termina justo al cierre de la franja
- **GIVEN** dado el profesional A con la franja del jueves de 09:00 a 13:00 y un turno `programado` de A de 45 minutos el jueves 2026-10-08 de 10:00 a 10:45
- **WHEN** cuando se lo reprograma informando `inicio` 2026-10-08 12:15 hora local
- **THEN** entonces la respuesta es `200` con `inicio` 2026-10-08T12:15-03:00 y `fin` 2026-10-08T13:00-03:00, y en la base el turno quedó así

#### Scenario: Nuevo inicio dentro de un bloqueo
- **GIVEN** dado un bloqueo del profesional A el jueves 2026-10-08 de 10:00 a 12:00 hora local y un turno `programado` de A el 2026-10-08 de 15:00 a 15:45
- **WHEN** cuando se lo reprograma informando `inicio` 2026-10-08 10:30 hora local
- **THEN** entonces la respuesta es `422` con código `turno_en_bloqueo` y el turno sigue de 15:00 a 15:45

#### Scenario: Profesional destino con un bloqueo en el horario
- **GIVEN** dado un turno `programado` del profesional A el jueves 2026-10-08 de 10:30 a 11:15 y un bloqueo del profesional B el 2026-10-08 de 10:00 a 12:00 hora local
- **WHEN** cuando se lo reprograma informando `profesional_id` de B
- **THEN** entonces la respuesta es `422` con código `turno_en_bloqueo` y el turno sigue con el profesional A

#### Scenario: Ampliar la duración hacia un bloqueo
- **GIVEN** dado un turno `programado` del profesional A el jueves 2026-10-08 de 09:15 a 10:00 y un bloqueo de A el 2026-10-08 de 10:00 a 12:00 hora local
- **WHEN** cuando se lo reprograma informando solo `duracion_min = 60`
- **THEN** entonces la respuesta es `422` con código `turno_en_bloqueo` y el turno sigue de 09:15 a 10:00

#### Scenario: Reprogramación que termina justo al empezar un bloqueo
- **GIVEN** dado un bloqueo del profesional A el jueves 2026-10-08 de 10:00 a 12:00 hora local y un turno `programado` de A de 45 minutos el 2026-10-08 de 15:00 a 15:45
- **WHEN** cuando se lo reprograma informando `inicio` 2026-10-08 09:15 hora local
- **THEN** entonces la respuesta es `200` con `inicio` 2026-10-08T09:15:00-03:00 y `fin` 2026-10-08T10:00:00-03:00, y en la base el turno quedó así

#### Scenario: Reprogramación rechazada por un bloqueo conserva el recordatorio
- **GIVEN** dado un turno `programado` del profesional A el viernes 2026-10-09 de 15:00 a 15:45 con su recordatorio `pendiente`, y un bloqueo de A el 2026-10-09 de 10:00 a 12:00 hora local
- **WHEN** cuando se lo reprograma informando `inicio` 2026-10-09 10:30 hora local
- **THEN** entonces la respuesta es `422` con código `turno_en_bloqueo`, el recordatorio sigue `pendiente` con el mismo `programado_para`, no se crea otro y no se registra auditoría de reprogramación
