# Spec Delta

## ADDED Requirements

### Requirement: Turno dentro del horario de atención
Al crear y al reprogramar, el intervalo `[inicio, fin)` del turno, en hora local `America/Argentina/Buenos_Aires`, MUST caber completo en una única franja del profesional del día de la semana local de su inicio; el fin puede coincidir con el de la franja (RN-AG-05, RN-CU-04, DD-27). Si no cabe o no hay franjas, MUST responder `422 fuera_de_horario` sin persistir. Los escenarios asumen el reloj en 2026-10-07 09:00 local; los de turnos de otros requisitos, una franja que cubre el turno.

#### Scenario: Turno dentro de la franja
- **GIVEN** dado que el reloj marca 2026-10-07 09:00 hora local, y que el profesional A tiene la franja del jueves (`dia_semana = 3`) de 09:00 a 13:00
- **WHEN** cuando una recepcionista autenticada crea un turno de A de 45 minutos con inicio 2026-10-08 10:00-03:00 (jueves)
- **THEN** entonces la respuesta es `201` con `inicio` 2026-10-08T10:00-03:00 y `fin` 2026-10-08T10:45-03:00

#### Scenario: Turno que empieza al abrir y otro que termina al cerrar la franja
- **GIVEN** dado el profesional A con la franja del jueves de 09:00 a 13:00
- **WHEN** cuando se crean dos turnos de A de 45 minutos el jueves 2026-10-08, uno a las 09:00 y otro a las 12:15 hora local
- **THEN** entonces ambas respuestas son `201`, y el segundo queda con `fin` 2026-10-08T13:00-03:00

#### Scenario: Turno que excede el fin de la franja
- **GIVEN** dado el profesional A con la franja del jueves de 09:00 a 13:00
- **WHEN** cuando se crea un turno de A de 45 minutos el jueves 2026-10-08 a las 12:30 hora local
- **THEN** entonces la respuesta es `422` con `{"detail": {"codigo": "fuera_de_horario", "mensaje": "el turno no cabe en el horario de atención del profesional"}}` y no se persiste ningún turno

#### Scenario: Turno que empieza antes de la franja
- **GIVEN** dado el profesional A con la franja del jueves de 09:00 a 13:00
- **WHEN** cuando se crea un turno de A de 45 minutos el jueves 2026-10-08 a las 08:30 hora local
- **THEN** entonces la respuesta es `422` con código `fuera_de_horario` y no se persiste ningún turno

#### Scenario: Turno en la segunda franja del día
- **GIVEN** dado el profesional A con las franjas del jueves de 09:00 a 13:00 y de 14:00 a 18:00
- **WHEN** cuando se crea un turno de A de 45 minutos el jueves 2026-10-08 a las 15:00 hora local
- **THEN** entonces la respuesta es `201`

#### Scenario: Turno en el hueco entre franjas
- **GIVEN** dado el profesional A con las franjas del jueves de 09:00 a 13:00 y de 14:00 a 18:00
- **WHEN** cuando se crea un turno de A de 30 minutos el jueves 2026-10-08 a las 13:15 hora local
- **THEN** entonces la respuesta es `422` con código `fuera_de_horario`

#### Scenario: Turno que cruza dos franjas
- **GIVEN** dado el profesional A con las franjas del jueves de 09:00 a 13:00 y de 14:00 a 18:00
- **WHEN** cuando se crea un turno de A de 120 minutos el jueves 2026-10-08 a las 12:30 hora local
- **THEN** entonces la respuesta es `422` con código `fuera_de_horario`

#### Scenario: Turno que cruza dos franjas contiguas
- **GIVEN** dado el profesional A con las franjas del jueves de 09:00 a 13:00 y de 13:00 a 17:00
- **WHEN** cuando se crea un turno de A de 60 minutos el jueves 2026-10-08 a las 12:30 hora local
- **THEN** entonces la respuesta es `422` con código `fuera_de_horario`, porque no cabe completo en una única franja

#### Scenario: Día sin franjas
- **GIVEN** dado el profesional A con franjas solo de lunes a viernes
- **WHEN** cuando se crea un turno de A el sábado 2026-10-10 a las 10:00 hora local
- **THEN** entonces la respuesta es `422` con código `fuera_de_horario`

#### Scenario: Profesional sin franjas
- **GIVEN** dado el profesional A activo sin ninguna franja
- **WHEN** cuando se crea un turno de A el jueves 2026-10-08 a las 10:00 hora local con referencias activas y sin solapes
- **THEN** entonces la respuesta es `422` con código `fuera_de_horario` y no se persiste ningún turno

#### Scenario: Franja de otro profesional no habilita el turno
- **GIVEN** dado el profesional B con la franja del jueves de 09:00 a 13:00 y el profesional A sin franjas el jueves
- **WHEN** cuando se crea un turno de A el jueves 2026-10-08 a las 10:00 hora local
- **THEN** entonces la respuesta es `422` con código `fuera_de_horario`

#### Scenario: El horario se evalúa en hora local, no en UTC
- **GIVEN** dado el profesional A con las franjas del jueves de 09:00 a 13:00 y de 14:00 a 18:00
- **WHEN** cuando se crea un turno de A de 45 minutos con inicio `2026-10-08T15:30:00Z` (12:30 hora local)
- **THEN** entonces la respuesta es `422` con código `fuera_de_horario`, aunque en UTC el intervalo 15:30-16:15 quede dentro de 14:00-18:00

#### Scenario: El día de la semana es el local
- **GIVEN** dado el profesional A con la franja del jueves de 21:00 a 23:00 y sin franjas el viernes
- **WHEN** cuando se crea un turno de A de 45 minutos con inicio `2026-10-09T01:00:00Z` (jueves 2026-10-08 22:00 hora local, viernes en UTC)
- **THEN** entonces la respuesta es `201` con `inicio` 2026-10-08T22:00-03:00

#### Scenario: Fuera de horario y en conflicto
- **GIVEN** dado el profesional A con la franja del jueves de 09:00 a 13:00 y un turno activo de A el jueves de 12:15 a 13:00
- **WHEN** cuando se crea otro turno de A de 45 minutos el jueves 2026-10-08 a las 12:30 hora local
- **THEN** entonces la respuesta es `422` con código `fuera_de_horario`, no `409`

#### Scenario: Validaciones previas antes que el horario
- **GIVEN** dado el profesional A sin franjas el sábado
- **WHEN** cuando se crea un turno de A el sábado 2026-10-10 a las 10:00 hora local con `duracion_min = 42`
- **THEN** entonces la respuesta es `422` con código `duracion_invalida`, no `fuera_de_horario`

## MODIFIED Requirements

### Requirement: Misma validación que el alta al reprogramar
Reprogramar MUST aplicar al turno resultante las mismas validaciones que el alta: referencias existentes y activas, duración y grilla de 5 minutos, inicio no anterior al instante actual, coherencia del sillón con la prestación y horario de atención del profesional (requisito "Turno dentro del horario de atención"), todas con `422` (RN-AG-08). Las validaciones que responden `422` MUST evaluarse antes que la verificación de solape, y ante cualquier `422` el turno MUST quedar intacto.

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
