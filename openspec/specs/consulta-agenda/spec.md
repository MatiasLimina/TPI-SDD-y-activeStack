# consulta-agenda Specification

## Purpose

Permite que la recepcionista consulte la agenda diaria o semanal de todos los profesionales y sillones, y que el odontólogo consulte solo la suya, con los turnos y los bloqueos de un rango de días locales y los horarios presentados en `America/Argentina/Buenos_Aires` (US-008, RN-AU-02, RN-CU-04).

## Requirements


### Requirement: Consulta de la agenda por rango de días
El sistema SHALL exponer `GET /turnos` con los parámetros obligatorios `desde` y `hasta`, fechas `YYYY-MM-DD` del calendario local, ambas incluidas, y los filtros opcionales `profesional_id` y `sillon_id`. MUST responder `200` con un objeto cuyas claves son exactamente `turnos` y `bloqueos`, dos listas con los turnos y los bloqueos del rango. Un parámetro de fecha faltante o mal formado MUST responder `422` (Flujo 7, US-008).

#### Scenario: Agenda diaria de la recepcionista
- **GIVEN** dado un turno `programado` del profesional A el 2026-10-08 de 10:00 a 10:45 hora local, un bloqueo de B el 2026-10-08 de 15:00 a 16:00 hora local y una recepcionista autenticada
- **WHEN** cuando envía `GET /turnos?desde=2026-10-08&hasta=2026-10-08`
- **THEN** entonces la respuesta es `200`, sus claves son exactamente `turnos` y `bloqueos`, `turnos` contiene solo ese turno y `bloqueos` contiene solo ese bloqueo

#### Scenario: Día sin turnos ni bloqueos
- **GIVEN** dado que no hay turnos ni bloqueos el 2026-10-09 y una recepcionista autenticada
- **WHEN** cuando envía `GET /turnos?desde=2026-10-09&hasta=2026-10-09`
- **THEN** entonces la respuesta es `200` con `{"turnos": [], "bloqueos": []}`

#### Scenario: Falta un extremo del rango
- **GIVEN** dado una recepcionista autenticada
- **WHEN** cuando envía `GET /turnos?desde=2026-10-08`, y después `GET /turnos` sin parámetros
- **THEN** entonces ambas respuestas son `422`

#### Scenario: Fecha mal formada
- **GIVEN** dado una recepcionista autenticada
- **WHEN** cuando envía `GET /turnos?desde=08/10/2026&hasta=2026-10-08`, y después `GET /turnos?desde=2026-10-08&hasta=2026-02-30`
- **THEN** entonces ambas respuestas son `422`

### Requirement: Rango local convertido a instantes UTC
El rango MUST interpretarse en `America/Argentina/Buenos_Aires`: abarca desde las 00:00 hora local de `desde` hasta las 00:00 hora local del día siguiente a `hasta`, convertidas a UTC con la zona IANA, sin asumir un desfasaje fijo (RN-CU-04, SU-08). Un turno o bloqueo pertenece al día local en que transcurre, aunque en UTC caiga en otra fecha.

#### Scenario: Turno de la noche local que en UTC es del día siguiente
- **GIVEN** dado un turno del profesional A el 2026-10-08 de 22:30 a 23:00 hora local (en la base, 2026-10-09T01:30Z a 02:00Z) y una recepcionista autenticada
- **WHEN** cuando envía `GET /turnos?desde=2026-10-08&hasta=2026-10-08`, y después `GET /turnos?desde=2026-10-09&hasta=2026-10-09`
- **THEN** entonces el turno aparece en la primera respuesta y no aparece en la segunda

#### Scenario: Turno de la madrugada local que en UTC es del mismo día
- **GIVEN** dado un turno del profesional A el 2026-10-09 de 00:00 a 00:30 hora local (en la base, 2026-10-09T03:00Z a 03:30Z) y una recepcionista autenticada
- **WHEN** cuando envía `GET /turnos?desde=2026-10-08&hasta=2026-10-08`, y después `GET /turnos?desde=2026-10-09&hasta=2026-10-09`
- **THEN** entonces el turno no aparece en la primera respuesta y aparece en la segunda

#### Scenario: Bloqueo con fecha UTC del día pedido pero de la noche local anterior
- **GIVEN** dado un bloqueo del profesional A de 2026-10-09T02:00Z a 2026-10-09T02:59Z (2026-10-08 de 23:00 a 23:59 hora local) y una recepcionista autenticada
- **WHEN** cuando envía `GET /turnos?desde=2026-10-09&hasta=2026-10-09`
- **THEN** entonces `bloqueos` está vacía

### Requirement: Inclusión por superposición con el rango
Un turno o bloqueo MUST incluirse si su intervalo `[inicio, fin)` se superpone con el rango `[inicio del rango, fin del rango)`: empieza antes del fin del rango y termina después de su inicio (DD-03). Uno que termina justo al empezar el rango, o empieza justo al terminar, MUST NOT incluirse. Uno que empieza antes del rango o termina después MUST incluirse completo, con su `inicio` y `fin` reales.

#### Scenario: Bloqueo de varios días en una vista diaria
- **GIVEN** dado un bloqueo del profesional A del 2026-10-05 08:00 al 2026-10-09 20:00 hora local y una recepcionista autenticada
- **WHEN** cuando envía `GET /turnos?desde=2026-10-07&hasta=2026-10-07`
- **THEN** entonces `bloqueos` contiene ese bloqueo con `inicio` 2026-10-05T08:00:00-03:00 y `fin` 2026-10-09T20:00:00-03:00

#### Scenario: Bloqueo que termina justo al empezar el día
- **GIVEN** dado un bloqueo del profesional A del 2026-10-07 20:00 al 2026-10-08 00:00 hora local y una recepcionista autenticada
- **WHEN** cuando envía `GET /turnos?desde=2026-10-08&hasta=2026-10-08`
- **THEN** entonces `bloqueos` está vacía

#### Scenario: Bloqueo que empieza justo al terminar el día
- **GIVEN** dado un bloqueo del profesional A del 2026-10-09 00:00 al 2026-10-09 08:00 hora local y una recepcionista autenticada
- **WHEN** cuando envía `GET /turnos?desde=2026-10-08&hasta=2026-10-08`
- **THEN** entonces `bloqueos` está vacía

#### Scenario: Bloqueo que cruza la medianoche al inicio del día
- **GIVEN** dado un bloqueo del profesional A del 2026-10-07 22:00 al 2026-10-08 01:00 hora local y una recepcionista autenticada
- **WHEN** cuando envía `GET /turnos?desde=2026-10-08&hasta=2026-10-08`
- **THEN** entonces `bloqueos` contiene ese bloqueo

#### Scenario: Turno que cruza la medianoche local aparece en ambos días
- **GIVEN** dado un turno del profesional A del 2026-10-07 23:30 al 2026-10-08 00:30 hora local y una recepcionista autenticada
- **WHEN** cuando envía `GET /turnos?desde=2026-10-07&hasta=2026-10-07` y después `GET /turnos?desde=2026-10-08&hasta=2026-10-08`
- **THEN** entonces `turnos` contiene ese turno completo, con su `inicio` y `fin` reales, en ambas respuestas

### Requirement: Rango válido de hasta una semana
`hasta` MUST ser igual o posterior a `desde`, y el rango MUST abarcar a lo sumo 7 días locales. En otro caso MUST responder `422` con `{"detail": {"codigo": "rango_invalido", "mensaje": ...}}`. Un rango de un día (`desde = hasta`) y uno de 7 días MUST aceptarse (US-008: vistas diaria y semanal). Un `hasta` cuyo día siguiente no se puede representar (`9999-12-31`) MUST dar el mismo `422`, nunca un error interno.

#### Scenario: Agenda semanal
- **GIVEN** dado un turno del profesional A el lunes 2026-10-05 a las 09:00, otro el domingo 2026-10-11 a las 18:00 y otro el lunes 2026-10-12 a las 09:00 hora local, y una recepcionista autenticada
- **WHEN** cuando envía `GET /turnos?desde=2026-10-05&hasta=2026-10-11`
- **THEN** entonces la respuesta es `200` y `turnos` contiene los dos primeros y no el del 2026-10-12

#### Scenario: Rango invertido
- **GIVEN** dado una recepcionista autenticada
- **WHEN** cuando envía `GET /turnos?desde=2026-10-09&hasta=2026-10-08`
- **THEN** entonces la respuesta es `422` con código `rango_invalido`

#### Scenario: Rango de más de una semana
- **GIVEN** dado una recepcionista autenticada
- **WHEN** cuando envía `GET /turnos?desde=2026-10-05&hasta=2026-10-12`
- **THEN** entonces la respuesta es `422` con código `rango_invalido`

#### Scenario: Fin de rango no representable
- **GIVEN** dado un usuario autenticado
- **WHEN** cuando envía `GET /turnos?desde=9999-12-25&hasta=9999-12-31`
- **THEN** entonces la respuesta es `422` con código `rango_invalido`, porque el fin del intervalo semiabierto (`hasta + 1 día`) no se puede representar; caso de borde, no `500`

### Requirement: Filtro por profesional
Con `profesional_id`, la agenda MUST contener solo los turnos y los bloqueos de ese profesional. Sin el filtro, la recepcionista MUST recibir los de todos los profesionales. Un `profesional_id` que no corresponde a ningún profesional MUST dar `200` con ambas listas vacías para la recepcionista, y uno mal formado MUST dar `422`. Un profesional desactivado conserva su agenda (DD-26 g).

#### Scenario: Recepcionista filtra por profesional
- **GIVEN** dado un turno y un bloqueo del profesional A y un turno y un bloqueo de B el 2026-10-08, y una recepcionista autenticada
- **WHEN** cuando envía `GET /turnos?desde=2026-10-08&hasta=2026-10-08&profesional_id=<id de A>`
- **THEN** entonces la respuesta es `200` y contiene solo el turno y el bloqueo de A

#### Scenario: Recepcionista ve todos los profesionales
- **GIVEN** dado un turno y un bloqueo del profesional A y un turno y un bloqueo de B el 2026-10-08, y una recepcionista autenticada
- **WHEN** cuando envía `GET /turnos?desde=2026-10-08&hasta=2026-10-08`
- **THEN** entonces la respuesta contiene los dos turnos y los dos bloqueos

#### Scenario: Profesional inexistente
- **GIVEN** dado una recepcionista autenticada
- **WHEN** cuando envía `GET /turnos?desde=2026-10-08&hasta=2026-10-08&profesional_id=<UUID que no corresponde a ningún profesional>`
- **THEN** entonces la respuesta es `200` con `{"turnos": [], "bloqueos": []}`

#### Scenario: Profesional desactivado
- **GIVEN** dado un turno `programado` del profesional A el 2026-10-08, A desactivado después, y una recepcionista autenticada
- **WHEN** cuando envía `GET /turnos?desde=2026-10-08&hasta=2026-10-08&profesional_id=<id de A>`
- **THEN** entonces la respuesta es `200` y `turnos` contiene ese turno

#### Scenario: Filtro de profesional mal formado
- **GIVEN** dado una recepcionista autenticada
- **WHEN** cuando envía `GET /turnos?desde=2026-10-08&hasta=2026-10-08&profesional_id=no-es-un-id`
- **THEN** entonces la respuesta es `422`

### Requirement: Filtro por sillón
Con `sillon_id`, `turnos` MUST contener solo los turnos asignados a ese sillón; los turnos sin sillón MUST quedar fuera. El filtro MUST NOT aplicarse a `bloqueos`, que son por profesional (DD-30 d) y siguen solo el filtro de profesional. Combinado con `profesional_id`, ambos filtros MUST aplicarse a la vez. Un sillón inexistente MUST dar `turnos` vacía y uno mal formado `422`.

#### Scenario: Recepcionista filtra por sillón
- **GIVEN** dado el 2026-10-08 un turno de A en el sillón 1, uno de B en el sillón 1, uno de A en el sillón 2, uno de A sin sillón, un bloqueo de A, y una recepcionista autenticada
- **WHEN** cuando envía `GET /turnos?desde=2026-10-08&hasta=2026-10-08&sillon_id=<id del sillón 1>`
- **THEN** entonces `turnos` contiene solo los dos turnos del sillón 1 y `bloqueos` contiene el bloqueo de A

#### Scenario: Filtros combinados
- **GIVEN** dado el 2026-10-08 un turno de A en el sillón 1, uno de B en el sillón 1, uno de A en el sillón 2, un bloqueo de A, un bloqueo de B, y una recepcionista autenticada
- **WHEN** cuando envía `GET /turnos?desde=2026-10-08&hasta=2026-10-08&profesional_id=<id de A>&sillon_id=<id del sillón 1>`
- **THEN** entonces `turnos` contiene solo el turno de A en el sillón 1 y `bloqueos` solo el bloqueo de A

#### Scenario: Sillón inexistente
- **GIVEN** dado un turno de A en el sillón 1 el 2026-10-08, y una recepcionista autenticada
- **WHEN** cuando envía `GET /turnos?desde=2026-10-08&hasta=2026-10-08&sillon_id=<UUID que no corresponde a ningún sillón>`
- **THEN** entonces la respuesta es `200` y `turnos` está vacía

#### Scenario: Filtro de sillón mal formado
- **GIVEN** dado una recepcionista autenticada
- **WHEN** cuando envía `GET /turnos?desde=2026-10-08&hasta=2026-10-08&sillon_id=no-es-un-id`
- **THEN** entonces la respuesta es `422`

### Requirement: Turnos en cualquier estado y fecha
La agenda MUST incluir los turnos `programado` y los `cancelado` del rango, cada uno con su `estado` (DD-08). Un turno cancelado y uno programado en el mismo horario MUST aparecer los dos. La consulta MUST aceptar rangos pasados y futuros, sin restricción respecto del reloj.

#### Scenario: Turno cancelado visible con su estado
- **GIVEN** dado un turno del profesional A el 2026-10-08 de 10:00 a 10:45 hora local, cancelado con motivo "Viaje", otro `programado` de A creado después en ese mismo horario, y una recepcionista autenticada
- **WHEN** cuando envía `GET /turnos?desde=2026-10-08&hasta=2026-10-08`
- **THEN** entonces `turnos` contiene ambos: uno con `estado = cancelado` y `motivo_cancelacion = "Viaje"`, y el otro con `estado = programado`

#### Scenario: Agenda de un día pasado
- **GIVEN** dado que el reloj marca 2026-10-08 09:00 hora local y un turno del profesional A el 2026-10-06 de 10:00 a 10:45 hora local
- **WHEN** cuando una recepcionista envía `GET /turnos?desde=2026-10-06&hasta=2026-10-06`
- **THEN** entonces la respuesta es `200` y `turnos` contiene ese turno

### Requirement: Datos de cada turno de la agenda
Cada elemento de `turnos` MUST tener exactamente `id`, `profesional_id`, `paciente`, `prestacion_id`, `sillon_id`, `inicio`, `fin`, `duracion_min`, `estado`, `creado_por` y `motivo_cancelacion`, con `inicio` y `fin` en `America/Argentina/Buenos_Aires` (RN-CU-04). `paciente` MUST tener exactamente `id`, `nombre` y `apellido`, para ambos roles y aunque el paciente esté desactivado (DD-31 a, c).

#### Scenario: Campos y hora local del turno
- **GIVEN** dado un turno `programado` del profesional A, sillón 1, prestación "Limpieza" (45 min) y paciente "Carla Imaginaria", el 2026-10-08 de 10:00 a 10:45 hora local (en la base, 13:00Z a 13:45Z), y una recepcionista autenticada
- **WHEN** cuando envía `GET /turnos?desde=2026-10-08&hasta=2026-10-08`
- **THEN** entonces el turno tiene exactamente las claves del requisito, `inicio` 2026-10-08T10:00:00-03:00, `fin` 2026-10-08T10:45:00-03:00, `duracion_min = 45`, `motivo_cancelacion` nulo y `paciente` = `{id, nombre: "Carla", apellido: "Imaginaria"}`

#### Scenario: Sin datos de contacto del paciente
- **GIVEN** dado un turno del profesional A con un paciente que tiene documento, teléfono y email, y un odontólogo autenticado vinculado a A
- **WHEN** cuando envía `GET /turnos?desde=<día del turno>&hasta=<día del turno>`
- **THEN** entonces `paciente` tiene solo `id`, `nombre` y `apellido`, y la respuesta no contiene el documento, el teléfono ni el email

#### Scenario: Turno sin sillón y paciente desactivado
- **GIVEN** dado un turno de A sin sillón el 2026-10-08 cuyo paciente fue desactivado después, y una recepcionista autenticada
- **WHEN** cuando envía `GET /turnos?desde=2026-10-08&hasta=2026-10-08`
- **THEN** entonces el turno aparece con `sillon_id` nulo y `paciente` con su `id`, `nombre` y `apellido`

### Requirement: Datos de cada bloqueo de la agenda
Cada elemento de `bloqueos` MUST tener exactamente `id`, `profesional_id`, `inicio`, `fin`, `motivo` y `creado_por`, los mismos campos que `GET /bloqueos` (DD-30 k), con `inicio` y `fin` en `America/Argentina/Buenos_Aires`.

#### Scenario: Campos y hora local del bloqueo
- **GIVEN** dado un bloqueo del profesional A el 2026-10-08 de 15:00 a 16:00 hora local (en la base, 18:00Z a 19:00Z) con motivo "Congreso", y una recepcionista autenticada
- **WHEN** cuando envía `GET /turnos?desde=2026-10-08&hasta=2026-10-08`
- **THEN** entonces el bloqueo tiene exactamente `id`, `profesional_id`, `inicio` 2026-10-08T15:00:00-03:00, `fin` 2026-10-08T16:00:00-03:00, `motivo = "Congreso"` y `creado_por`

#### Scenario: Bloqueos superpuestos del mismo profesional
- **GIVEN** dado dos bloqueos superpuestos del profesional A el 2026-10-08 (DD-30 b), y una recepcionista autenticada
- **WHEN** cuando envía `GET /turnos?desde=2026-10-08&hasta=2026-10-08`
- **THEN** entonces `bloqueos` contiene los dos, sin fusionarlos

### Requirement: Orden de la agenda
`turnos` y `bloqueos` MUST estar ordenadas por `inicio` y, ante el mismo `inicio`, por `id`, sin agrupar por profesional ni por día.

#### Scenario: Orden por inicio entre profesionales
- **GIVEN** dado el 2026-10-08 un turno de A a las 11:00, uno de B a las 09:00 y uno de A a las 10:00 hora local, y una recepcionista autenticada
- **WHEN** cuando envía `GET /turnos?desde=2026-10-08&hasta=2026-10-08`
- **THEN** entonces `turnos` está en el orden: B 09:00, A 10:00, A 11:00

#### Scenario: Mismo inicio
- **GIVEN** dado el 2026-10-08 un turno de A y uno de B, ambos a las 10:00 hora local, y una recepcionista autenticada
- **WHEN** cuando envía `GET /turnos?desde=2026-10-08&hasta=2026-10-08`
- **THEN** entonces los dos aparecen ordenados por `id` ascendente

### Requirement: El odontólogo solo consulta su agenda
Un `odontologo` MUST recibir solo los turnos y los bloqueos de su profesional (RN-AU-02). Si omite `profesional_id` MUST usarse el suyo; si informa otro, exista o no, MUST responder `403` con `{"detail": {"codigo": "profesional_ajeno", "mensaje": "Solo podés consultar tu propia agenda"}}`, evaluado antes que la validez del rango (DD-27 i, DD-30 k). `sillon_id` MUST restringir solo sus propios turnos.

#### Scenario: Odontólogo sin filtro
- **GIVEN** dado un odontólogo autenticado vinculado al profesional A, y el 2026-10-08 un turno y un bloqueo de A y un turno y un bloqueo de B
- **WHEN** cuando envía `GET /turnos?desde=2026-10-08&hasta=2026-10-08`
- **THEN** entonces la respuesta es `200` y contiene solo el turno y el bloqueo de A

#### Scenario: Odontólogo filtra por su profesional
- **GIVEN** dado un odontólogo autenticado vinculado al profesional A, y el 2026-10-08 un turno de A y uno de B
- **WHEN** cuando envía `GET /turnos?desde=2026-10-08&hasta=2026-10-08&profesional_id=<id de A>`
- **THEN** entonces la respuesta es `200` y `turnos` contiene solo el turno de A

#### Scenario: Odontólogo pide otro profesional
- **GIVEN** dado un odontólogo autenticado vinculado al profesional A, y el profesional B con turnos el 2026-10-08
- **WHEN** cuando envía `GET /turnos?desde=2026-10-08&hasta=2026-10-08&profesional_id=<id de B>`, y después con un UUID que no corresponde a ningún profesional
- **THEN** entonces ambas respuestas son `403` con código `profesional_ajeno`, cuerpos idénticos y ningún turno

#### Scenario: Odontólogo filtra por un sillón compartido
- **GIVEN** dado un odontólogo autenticado vinculado al profesional A, y el 2026-10-08 un turno de A y uno de B, ambos en el sillón 1, y un bloqueo de A y uno de B
- **WHEN** cuando envía `GET /turnos?desde=2026-10-08&hasta=2026-10-08&sillon_id=<id del sillón 1>`
- **THEN** entonces `turnos` contiene solo el turno de A y `bloqueos` contiene solo el bloqueo de A, sin filtrarse por sillón

#### Scenario: Profesional ajeno antes que el rango inválido
- **GIVEN** dado un odontólogo autenticado vinculado al profesional A, y el profesional B
- **WHEN** cuando envía `GET /turnos?desde=2026-10-09&hasta=2026-10-08&profesional_id=<id de B>`
- **THEN** entonces la respuesta es `403` con código `profesional_ajeno`, no `422`

### Requirement: Agenda accesible solo con autenticación
`GET /turnos` MUST exigir un usuario autenticado de rol `recepcionista` u `odontologo` (RN-AU-01). Sin token, o con un token inválido o vencido, MUST responder `401` con `WWW-Authenticate: Bearer` y código `no_autenticado`, antes de validar los parámetros (DD-24 b).

#### Scenario: Sin token
- **GIVEN** dado un turno del profesional A el 2026-10-08
- **WHEN** cuando se envía `GET /turnos?desde=2026-10-08&hasta=2026-10-08` sin encabezado `Authorization`
- **THEN** entonces la respuesta es `401` con `WWW-Authenticate: Bearer`, código `no_autenticado` y ningún turno

#### Scenario: Autenticación antes que los parámetros
- **WHEN** cuando se envía `GET /turnos?desde=no-es-fecha` sin encabezado `Authorization`
- **THEN** entonces la respuesta es `401`, no `422`

#### Scenario: Token vencido
- **GIVEN** dado el token vencido de una recepcionista
- **WHEN** cuando envía `GET /turnos?desde=2026-10-08&hasta=2026-10-08`
- **THEN** entonces la respuesta es `401` con código `no_autenticado`
