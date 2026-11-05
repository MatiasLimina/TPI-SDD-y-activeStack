# bloqueos-agenda Specification

## Purpose
Permitir que la recepción y cada odontólogo bloqueen franjas de la agenda de un profesional (un congreso, un trámite, unas vacaciones) para que no se le asignen turnos en esas horas, sin dejar nunca turnos activos dentro de un bloqueo (RN-HB-02, RN-HB-03, US-003).

## Requirements

### Requirement: Alta de un bloqueo de agenda
El sistema SHALL exponer `POST /bloqueos` con `profesional_id`, `inicio`, `fin` (con zona horaria) y `motivo`. Un bloqueo válido MUST persistirse con `inicio` y `fin` en UTC como intervalo semiabierto `[inicio, fin)` y responder `201` con `id`, `profesional_id`, `inicio`, `fin` (en hora local `America/Argentina/Buenos_Aires`), `motivo` y `creado_por` (el usuario autenticado) (RN-HB-02, RN-CU-04). Los escenarios asumen el reloj en 2026-10-07 09:00 local.

#### Scenario: Recepcionista bloquea una franja
- **GIVEN** dado una recepcionista autenticada y el profesional A activo sin turnos el jueves 2026-10-08
- **WHEN** cuando envía `POST /bloqueos` con `profesional_id` de A, `inicio` 2026-10-08T10:00:00-03:00, `fin` 2026-10-08T12:00:00-03:00 y `motivo` "Congreso"
- **THEN** entonces la respuesta es `201` con `profesional_id` de A, `inicio` 2026-10-08T10:00:00-03:00, `fin` 2026-10-08T12:00:00-03:00, `motivo` "Congreso" y `creado_por` igual al id de la recepcionista, y en la base el bloqueo queda con `inicio` 2026-10-08T13:00:00Z y `fin` 2026-10-08T15:00:00Z

#### Scenario: Instantes informados en UTC
- **GIVEN** dado una recepcionista autenticada y el profesional A
- **WHEN** cuando crea un bloqueo de A con `inicio` `2026-10-08T13:00:00Z` y `fin` `2026-10-08T15:00:00Z`
- **THEN** entonces la respuesta es `201` con `inicio` 2026-10-08T10:00:00-03:00 y `fin` 2026-10-08T12:00:00-03:00

#### Scenario: Bloqueo de varios días
- **GIVEN** dado el profesional A sin turnos entre el 2026-10-12 y el 2026-10-16
- **WHEN** cuando la recepcionista crea un bloqueo de A desde 2026-10-12T00:00:00-03:00 hasta 2026-10-17T00:00:00-03:00 con `motivo` "Vacaciones"
- **THEN** entonces la respuesta es `201` con `inicio` 2026-10-12T00:00:00-03:00 y `fin` 2026-10-17T00:00:00-03:00, y en la base el bloqueo queda con `inicio` 2026-10-12T03:00:00Z y `fin` 2026-10-17T03:00:00Z

#### Scenario: Bloqueo fuera del horario de atención
- **GIVEN** dado el profesional A con franjas solo de lunes a viernes de 09:00 a 13:00
- **WHEN** cuando la recepcionista crea un bloqueo de A el sábado 2026-10-10 de 10:00 a 11:00 hora local
- **THEN** entonces la respuesta es `201`: el bloqueo no depende del horario de atención

#### Scenario: Bloqueo en el pasado
- **GIVEN** dado que el reloj marca 2026-10-07 09:00 hora local y el profesional A sin turnos el 2026-10-06
- **WHEN** cuando la recepcionista crea un bloqueo de A el 2026-10-06 de 10:00 a 11:00 hora local
- **THEN** entonces la respuesta es `201` (DD-30)

#### Scenario: Profesional desactivado
- **GIVEN** dado el profesional B desactivado
- **WHEN** cuando la recepcionista crea un bloqueo de B con `inicio` 2026-10-08T10:00:00-03:00, `fin` 2026-10-08T11:00:00-03:00 y `motivo` "Trámite"
- **THEN** entonces la respuesta es `201` con `profesional_id` de B (DD-30)

#### Scenario: Bloqueo fuera de la grilla de 5 minutos
- **GIVEN** dado el profesional A sin turnos el jueves 2026-10-08
- **WHEN** cuando la recepcionista crea un bloqueo de A con `inicio` 2026-10-08T10:03:00-03:00, `fin` 2026-10-08T10:07:00-03:00 y `motivo` "Trámite"
- **THEN** entonces la respuesta es `201` con `inicio` 2026-10-08T10:03:00-03:00 y `fin` 2026-10-08T10:07:00-03:00: el bloqueo no exige la grilla de 5 minutos (DD-30)

### Requirement: Profesional del bloqueo según el rol
La `recepcionista` MUST indicar el `profesional_id` del bloqueo: sin él → `422 profesional_requerido`. Para el `odontologo` el profesional MUST ser el de su usuario: si lo omite se usa el suyo, y uno distinto (exista o no) → `403 profesional_ajeno` sin persistir, antes que la existencia y la forma del bloqueo (RN-HB-02, RN-AU-02, Flujo 5, DD-27 i, DD-30). Un profesional inexistente → `422 referencia_invalida`.

#### Scenario: Odontólogo bloquea su agenda sin indicar profesional
- **GIVEN** dado un odontólogo autenticado vinculado al profesional A
- **WHEN** cuando envía `POST /bloqueos` sin `profesional_id`, con `inicio` 2026-10-08T10:00:00-03:00, `fin` 2026-10-08T11:00:00-03:00 y `motivo` "Trámite"
- **THEN** entonces la respuesta es `201` con `profesional_id` de A y `creado_por` igual al id del odontólogo

#### Scenario: Odontólogo indica su propio profesional
- **GIVEN** dado un odontólogo autenticado vinculado al profesional A
- **WHEN** cuando envía `POST /bloqueos` con `profesional_id` de A, `inicio` 2026-10-08T10:00:00-03:00, `fin` 2026-10-08T11:00:00-03:00 y `motivo` "Trámite"
- **THEN** entonces la respuesta es `201` con `profesional_id` de A

#### Scenario: Odontólogo intenta bloquear la agenda de otro
- **GIVEN** dado un odontólogo autenticado vinculado al profesional A, y el profesional B
- **WHEN** cuando envía `POST /bloqueos` con `profesional_id` de B, y luego con un UUID que no corresponde a ningún profesional
- **THEN** entonces ambas respuestas son `403` con `{"detail": {"codigo": "profesional_ajeno", "mensaje": "Solo podés operar sobre tus propios bloqueos"}}` y no se persiste ningún bloqueo

#### Scenario: Profesional ajeno antes que el bloqueo inválido
- **GIVEN** dado un odontólogo autenticado vinculado al profesional A, y el profesional B
- **WHEN** cuando envía `POST /bloqueos` con `profesional_id` de B y `fin` igual a `inicio`
- **THEN** entonces la respuesta es `403` con código `profesional_ajeno`, no `422`, y no se persiste ningún bloqueo

#### Scenario: Recepcionista sin profesional
- **GIVEN** dado una recepcionista autenticada
- **WHEN** cuando envía `POST /bloqueos` sin `profesional_id`, con `inicio` 2026-10-08T10:00:00-03:00, `fin` 2026-10-08T11:00:00-03:00 y `motivo` "Trámite"
- **THEN** entonces la respuesta es `422` con `{"detail": {"codigo": "profesional_requerido", "mensaje": "indicá el profesional del bloqueo"}}` y no se persiste ningún bloqueo

#### Scenario: Profesional inexistente
- **GIVEN** dado una recepcionista autenticada
- **WHEN** cuando envía `POST /bloqueos` con un `profesional_id` que no corresponde a ningún profesional
- **THEN** entonces la respuesta es `422` con `{"detail": {"codigo": "referencia_invalida", "referencia": "profesional", "motivo": "inexistente"}}` y no se persiste ningún bloqueo

### Requirement: Validación del bloqueo
Un bloqueo MUST tener `fin` posterior a `inicio` y un `motivo` no vacío; el motivo se guarda sin espacios en los extremos y su largo (a lo sumo 255) se mide ya recortado. Si no → `422` sin persistir: `bloqueo_invalido` para el intervalo o el motivo vacío, evaluado después de `profesional_requerido` y `referencia_invalida`; el `422` del request para un campo faltante, un motivo largo o un datetime sin zona (RN-HB-02, `04` §Bloqueo, DD-30).

#### Scenario: Fin igual al inicio
- **WHEN** cuando la recepcionista crea un bloqueo de A con `inicio` y `fin` 2026-10-08T10:00:00-03:00
- **THEN** entonces la respuesta es `422` con `{"detail": {"codigo": "bloqueo_invalido", "mensaje": "el bloqueo debe tener fin posterior a inicio y un motivo no vacío"}}` y no se persiste ningún bloqueo

#### Scenario: Fin anterior al inicio
- **WHEN** cuando la recepcionista crea un bloqueo de A con `inicio` 2026-10-08T12:00:00-03:00 y `fin` 2026-10-08T10:00:00-03:00
- **THEN** entonces la respuesta es `422` con código `bloqueo_invalido` y no se persiste ningún bloqueo

#### Scenario: Motivo vacío o solo espacios
- **WHEN** cuando la recepcionista crea un bloqueo de A con `motivo` "" y luego con `motivo` "   "
- **THEN** entonces ambas respuestas son `422` con código `bloqueo_invalido` y no se persiste ningún bloqueo

#### Scenario: Motivo con espacios en los extremos
- **WHEN** cuando la recepcionista crea un bloqueo válido de A con `motivo` "  Congreso  "
- **THEN** entonces la respuesta es `201` con `motivo` "Congreso", y así queda en la base

#### Scenario: Motivo de 255 caracteres
- **WHEN** cuando la recepcionista crea un bloqueo de A el 2026-10-08 de 10:00 a 11:00 hora local con un `motivo` de 255 letras, y otro de A el 2026-10-08 de 11:00 a 12:00 con esas mismas 255 letras precedidas y seguidas por dos espacios
- **THEN** entonces ambas respuestas son `201` con el `motivo` de 255 letras, sin espacios, y así queda en la base

#### Scenario: Campos faltantes o fuera de forma
- **WHEN** cuando la recepcionista envía `POST /bloqueos` sin `motivo`, luego sin `fin`, luego con un `motivo` de 256 letras
- **THEN** entonces cada respuesta es `422` y no se persiste ningún bloqueo

#### Scenario: Profesional requerido antes que el bloqueo inválido
- **WHEN** cuando la recepcionista envía `POST /bloqueos` sin `profesional_id`, con `inicio` y `fin` 2026-10-08T10:00:00-03:00 y `motivo` "Congreso"
- **THEN** entonces la respuesta es `422` con código `profesional_requerido`, no `bloqueo_invalido`, y no se persiste ningún bloqueo

#### Scenario: Profesional inexistente antes que el bloqueo inválido
- **WHEN** cuando la recepcionista envía `POST /bloqueos` con un `profesional_id` que no corresponde a ningún profesional, `inicio` 2026-10-08T10:00:00-03:00, `fin` 2026-10-08T12:00:00-03:00 y `motivo` "   "
- **THEN** entonces la respuesta es `422` con código `referencia_invalida`, no `bloqueo_invalido`, y no se persiste ningún bloqueo

#### Scenario: Datetime sin zona horaria
- **WHEN** cuando la recepcionista crea un bloqueo de A con `inicio` `2026-10-08T10:00:00` (sin zona)
- **THEN** entonces la respuesta es `422` y no se persiste ningún bloqueo

### Requirement: Bloqueo sobre turnos activos rechazado
Crear un bloqueo cuyo intervalo se superpone con turnos activos (no cancelados) del mismo profesional MUST rechazarse con `409` y la lista de esos turnos, sin persistir el bloqueo ni modificar los turnos ni sus recordatorios (RN-HB-03, DD-12, DD-30). Se usa el criterio `[)`: un turno contiguo al bloqueo no cuenta (RN-AG-03). Los escenarios asumen el reloj en 2026-10-07 09:00 local.

#### Scenario: Turno activo dentro del intervalo
- **GIVEN** dado un turno `programado` T1 del profesional A el jueves 2026-10-08 de 10:30 a 11:15 hora local
- **WHEN** cuando la recepcionista crea un bloqueo de A el 2026-10-08 de 10:00 a 12:00 hora local
- **THEN** entonces la respuesta es `409` con `{"detail": {"codigo": "bloqueo_con_turnos", "mensaje": "hay turnos activos en el intervalo: reprogramalos o cancelalos antes de bloquear", "turnos": [{"id": <id de T1>, "inicio": "2026-10-08T10:30:00-03:00", "fin": "2026-10-08T11:15:00-03:00"}]}}` y no se persiste ningún bloqueo

#### Scenario: Varios turnos afectados, ordenados por inicio
- **GIVEN** dado los turnos `programado` del profesional A el jueves 2026-10-08 de 11:00 a 11:45 (T2) y de 09:30 a 10:15 (T1, que empieza antes del bloqueo y termina dentro), y un turno cancelado de A de 10:30 a 10:45
- **WHEN** cuando la recepcionista crea un bloqueo de A el 2026-10-08 de 10:00 a 12:00 hora local
- **THEN** entonces la respuesta es `409` y `turnos` lista exactamente T1 y luego T2, sin el turno cancelado, y no se persiste ningún bloqueo

#### Scenario: Turno que termina justo al empezar el bloqueo
- **GIVEN** dado un turno `programado` del profesional A el jueves 2026-10-08 de 09:15 a 10:00 hora local
- **WHEN** cuando la recepcionista crea un bloqueo de A el 2026-10-08 de 10:00 a 12:00 hora local
- **THEN** entonces la respuesta es `201`

#### Scenario: Turno que empieza justo al terminar el bloqueo
- **GIVEN** dado un turno `programado` del profesional A el jueves 2026-10-08 de 12:00 a 12:45 hora local
- **WHEN** cuando la recepcionista crea un bloqueo de A el 2026-10-08 de 10:00 a 12:00 hora local
- **THEN** entonces la respuesta es `201`

#### Scenario: Turno cancelado en el intervalo
- **GIVEN** dado un turno cancelado del profesional A el jueves 2026-10-08 de 10:30 a 11:15 hora local
- **WHEN** cuando la recepcionista crea un bloqueo de A el 2026-10-08 de 10:00 a 12:00 hora local
- **THEN** entonces la respuesta es `201` (RN-AG-07)

#### Scenario: Turno de otro profesional en el intervalo
- **GIVEN** dado un turno `programado` del profesional B el jueves 2026-10-08 de 10:30 a 11:15 hora local
- **WHEN** cuando la recepcionista crea un bloqueo de A el 2026-10-08 de 10:00 a 12:00 hora local
- **THEN** entonces la respuesta es `201`

#### Scenario: Odontólogo con turnos propios en el intervalo
- **GIVEN** dado un odontólogo autenticado vinculado al profesional A y un turno `programado` T1 de A el jueves 2026-10-08 de 10:30 a 11:15 hora local
- **WHEN** cuando el odontólogo crea un bloqueo sin `profesional_id` el 2026-10-08 de 10:00 a 12:00 hora local
- **THEN** entonces la respuesta es `409` con código `bloqueo_con_turnos` y `turnos` con T1, y no se persiste ningún bloqueo

#### Scenario: El rechazo no toca el turno ni su recordatorio
- **GIVEN** dado un turno `programado` T1 del profesional A el viernes 2026-10-09 de 10:30 a 11:15 hora local, creado con un recordatorio `pendiente`
- **WHEN** cuando la recepcionista crea un bloqueo de A el 2026-10-09 de 10:00 a 12:00 hora local
- **THEN** entonces la respuesta es `409`, no se persiste ningún bloqueo, T1 sigue `programado` de 10:30 a 11:15, su recordatorio sigue `pendiente` con el mismo `programado_para`, y no se registra auditoría para T1

#### Scenario: Turno ya resuelto, el bloqueo entra
- **GIVEN** dado un turno `programado` T1 del profesional A el jueves 2026-10-08 de 10:30 a 11:15, y un bloqueo de A de 10:00 a 12:00 rechazado con `409`
- **WHEN** cuando la recepcionista cancela T1 y vuelve a crear el mismo bloqueo
- **THEN** entonces la respuesta es `201`

#### Scenario: Bloqueo retroactivo sobre un turno pasado
- **GIVEN** dado un turno `programado` T1 del profesional A el martes 2026-10-06 de 10:30 a 11:15 hora local, creado cuando el reloj marcaba 2026-10-05 09:00, y el reloj ahora en 2026-10-07 09:00 hora local
- **WHEN** cuando la recepcionista crea un bloqueo de A el 2026-10-06 de 10:00 a 12:00 hora local
- **THEN** entonces la respuesta es `409` con código `bloqueo_con_turnos` y `turnos` = `[{"id": <id de T1>, "inicio": "2026-10-06T10:30:00-03:00", "fin": "2026-10-06T11:15:00-03:00"}]`, y no se persiste ningún bloqueo (DD-30)

### Requirement: Bloqueos superpuestos del mismo profesional
El alta MUST aceptar un bloqueo aunque se superponga con otro del mismo profesional: no los compara entre sí, cada uno conserva su motivo y borrar uno deja vigente al otro (DD-30).

#### Scenario: Bloqueo dentro de otro
- **GIVEN** dado un bloqueo del profesional A el 2026-10-08 de 09:00 a 18:00 hora local con motivo "Congreso"
- **WHEN** cuando el odontólogo de A crea un bloqueo propio el 2026-10-08 de 10:00 a 11:00 con motivo "Trámite"
- **THEN** entonces la respuesta es `201` y A tiene los dos bloqueos

#### Scenario: Borrar uno deja vigente al otro
- **GIVEN** dado dos bloqueos superpuestos del profesional A el 2026-10-08, de 09:00 a 18:00 y de 10:00 a 11:00 hora local
- **WHEN** cuando se borra el de 10:00 a 11:00 y la recepcionista crea un turno de A el 2026-10-08 a las 10:00
- **THEN** entonces el borrado responde `204` y el alta del turno responde `422` con código `turno_en_bloqueo`

### Requirement: Consulta de bloqueos
El sistema SHALL exponer `GET /bloqueos`, con filtro opcional `profesional_id`, que responde `200` con la lista de bloqueos (mismos campos que el alta) ordenada por `inicio`, incluidos los pasados. La `recepcionista` ve los de todos los profesionales o los del filtrado (uno inexistente da lista vacía). El `odontologo` ve solo los de su profesional; un filtro con otro profesional → `403 profesional_ajeno` (RN-AU-02, DD-27 i, DD-30).

#### Scenario: Recepcionista lista todos los bloqueos
- **GIVEN** dado un bloqueo de A el 2026-10-09 de 10:00 a 11:00 y uno de B el 2026-10-08 de 15:00 a 16:00 hora local
- **WHEN** cuando la recepcionista envía `GET /bloqueos`
- **THEN** entonces la respuesta es `200` con ambos bloqueos, primero el de B y después el de A

#### Scenario: Recepcionista filtra por profesional
- **GIVEN** dado un bloqueo de A y uno de B
- **WHEN** cuando la recepcionista envía `GET /bloqueos?profesional_id=<id de A>`
- **THEN** entonces la respuesta es `200` solo con el bloqueo de A

#### Scenario: Incluye los bloqueos pasados
- **GIVEN** dado que el reloj marca 2026-10-07 09:00 hora local, y dos bloqueos del profesional A: el 2026-10-06 de 10:00 a 11:00 y el 2026-10-08 de 10:00 a 11:00 hora local
- **WHEN** cuando la recepcionista envía `GET /bloqueos?profesional_id=<id de A>`
- **THEN** entonces la respuesta es `200` con ambos bloqueos, primero el del 2026-10-06 y después el del 2026-10-08

#### Scenario: Filtro por un profesional inexistente
- **WHEN** cuando la recepcionista envía `GET /bloqueos?profesional_id=<UUID que no corresponde a ningún profesional>`
- **THEN** entonces la respuesta es `200` con una lista vacía

#### Scenario: Odontólogo ve solo sus bloqueos
- **GIVEN** dado un odontólogo autenticado vinculado al profesional A, un bloqueo de A y uno de B
- **WHEN** cuando envía `GET /bloqueos` y luego `GET /bloqueos?profesional_id=<id de A>`
- **THEN** entonces ambas respuestas son `200` solo con el bloqueo de A

#### Scenario: Odontólogo filtra por otro profesional
- **GIVEN** dado un odontólogo autenticado vinculado al profesional A, y el profesional B
- **WHEN** cuando envía `GET /bloqueos?profesional_id=<id de B>`
- **THEN** entonces la respuesta es `403` con `{"detail": {"codigo": "profesional_ajeno", "mensaje": "Solo podés operar sobre tus propios bloqueos"}}`

#### Scenario: Filtro mal formado
- **WHEN** cuando un usuario autenticado envía `GET /bloqueos?profesional_id=no-es-un-id`
- **THEN** entonces la respuesta es `422`

### Requirement: Borrado de un bloqueo
El sistema SHALL exponer `DELETE /bloqueos/{id}`, que borra el bloqueo y responde `204` sin cuerpo; el intervalo vuelve a admitir turnos. Para la `recepcionista`, un bloqueo inexistente → `404 recurso_inexistente`. El `odontologo` solo borra bloqueos de su profesional, los haya creado él o la recepción; sobre uno de otro profesional o uno inexistente → `403 profesional_ajeno`, sin revelar si existe, y nada cambia (RN-HB-02, RN-AU-02, DD-27 i, DD-30).

#### Scenario: Recepcionista borra un bloqueo
- **GIVEN** dado un bloqueo de A el 2026-10-08 de 10:00 a 12:00 hora local
- **WHEN** cuando la recepcionista envía `DELETE /bloqueos/{id}`
- **THEN** entonces la respuesta es `204` sin cuerpo y `GET /bloqueos` ya no lo lista

#### Scenario: El intervalo liberado admite turnos
- **GIVEN** dado un bloqueo de A el 2026-10-08 de 10:00 a 12:00 hora local, ya borrado
- **WHEN** cuando la recepcionista crea un turno de A el 2026-10-08 a las 10:30
- **THEN** entonces la respuesta es `201`

#### Scenario: Odontólogo borra un bloqueo de su agenda creado por la recepción
- **GIVEN** dado un odontólogo autenticado vinculado al profesional A, y un bloqueo de A creado por la recepcionista
- **WHEN** cuando el odontólogo envía `DELETE /bloqueos/{id}`
- **THEN** entonces la respuesta es `204`

#### Scenario: Odontólogo no borra bloqueos ajenos
- **GIVEN** dado un odontólogo autenticado vinculado al profesional A, y un bloqueo del profesional B
- **WHEN** cuando el odontólogo envía `DELETE /bloqueos/{id}`
- **THEN** entonces la respuesta es `403` con código `profesional_ajeno` y el bloqueo sigue en la base

#### Scenario: Bloqueo inexistente
- **WHEN** cuando la recepcionista envía `DELETE /bloqueos/{id}` con un UUID que no corresponde a ningún bloqueo
- **THEN** entonces la respuesta es `404` con `{"detail": {"codigo": "recurso_inexistente", "recurso": "bloqueo"}}`

#### Scenario: Odontólogo con un bloqueo inexistente
- **GIVEN** dado un odontólogo autenticado vinculado al profesional A, y un bloqueo B1 de A
- **WHEN** cuando el odontólogo envía `DELETE /bloqueos/{id}` con un UUID que no corresponde a ningún bloqueo
- **THEN** entonces la respuesta es `403` con `{"detail": {"codigo": "profesional_ajeno", "mensaje": "Solo podés operar sobre tus propios bloqueos"}}`, no `404`, y B1 sigue en la base

#### Scenario: Identificador mal formado
- **WHEN** cuando la recepcionista envía `DELETE /bloqueos/no-es-un-id`
- **THEN** entonces la respuesta es `422`

### Requirement: Bloqueos accesibles solo con autenticación
Alta, consulta y borrado de bloqueos MUST exigir un usuario autenticado de rol `recepcionista` u `odontologo` (RN-AU-01). Sin token, o con un token inválido o vencido, MUST responder `401` con `WWW-Authenticate: Bearer` y `{"detail": {"codigo": "no_autenticado", "mensaje": "No autenticado"}}`, antes de validar el body o el path, sin cambios en la base (DD-24 b).

#### Scenario: Sin token
- **GIVEN** dado un bloqueo B1 del profesional A
- **WHEN** cuando se envían sin encabezado `Authorization` `POST /bloqueos` con un body válido, `GET /bloqueos` y `DELETE /bloqueos/{id de B1}`
- **THEN** entonces cada respuesta es `401` con `WWW-Authenticate: Bearer` y código `no_autenticado`, y B1 sigue siendo el único bloqueo

#### Scenario: Autenticación antes que el body y el path
- **WHEN** cuando se envían sin token `POST /bloqueos` con `{"fin": "no-es-fecha"}` y `DELETE /bloqueos/no-es-un-id`
- **THEN** entonces ambas respuestas son `401`, no `422`, y no se persiste ningún bloqueo

#### Scenario: Token vencido o con firma alterada
- **GIVEN** dado un bloqueo B1 del profesional A
- **WHEN** cuando se envía `POST /bloqueos` con un body válido, primero con el token vencido de una recepcionista y después con un token de recepcionista cuya firma fue alterada
- **THEN** entonces cada respuesta es `401` con `WWW-Authenticate: Bearer` y código `no_autenticado`, y B1 sigue siendo el único bloqueo

### Requirement: Integridad del bloqueo en la base
La base MUST rechazar, aun con escrituras directas, un bloqueo con `fin <= inicio`, con un motivo vacío o solo espacios, sin `creado_por` o con un profesional o un autor inexistentes. Los instantes se guardan como `timestamptz` (DD-17, RN-CU-04).

#### Scenario: Escrituras directas inválidas
- **WHEN** cuando se inserta directamente en la base un bloqueo con `fin` igual a `inicio`, otro con `motivo` "   ", otro sin `creado_por`, otro con un `profesional_id` inexistente y otro con un `creado_por` que no corresponde a ningún usuario
- **THEN** entonces la base rechaza cada inserción con una violación de integridad

#### Scenario: Escritura directa válida
- **WHEN** cuando se inserta directamente un bloqueo con `fin` posterior a `inicio`, motivo "Congreso", un profesional y un autor existentes
- **THEN** entonces la base lo acepta

### Requirement: Bloqueo y turno simultáneos
Un alta de bloqueo y un alta o reprogramación que lleva un turno al mismo profesional en un intervalo superpuesto MUST quedar serializadas por el profesional destino: la que lo toma primero hace esperar a la otra. Si confirma antes el bloqueo, el turno MUST responder `422 turno_en_bloqueo`; si confirma antes el turno, el bloqueo MUST responder `409 bloqueo_con_turnos`. Nunca queda un turno activo dentro de un bloqueo (RN-HB-03, RN-AG-06, `08` §Concurrencia, DD-18, DD-30).

#### Scenario: Alta de turno que espera a un bloqueo en curso
- **GIVEN** dada una transacción que creó un bloqueo del profesional A el jueves 2026-10-08 de 10:00 a 12:00 hora local y todavía no confirmó
- **WHEN** cuando en paralelo se crea un turno de A de 45 minutos el 2026-10-08 a las 10:30 hora local y después se confirma el bloqueo
- **THEN** entonces el alta espera al bloqueo y responde `422` con código `turno_en_bloqueo`, no se persiste ningún turno y el bloqueo queda persistido

#### Scenario: Bloqueo que espera a un alta de turno en curso
- **GIVEN** dada un alta de turno del profesional A de 45 minutos el jueves 2026-10-08 a las 10:30 hora local que ya validó sus referencias y todavía no confirmó
- **WHEN** cuando en paralelo se crea un bloqueo de A el 2026-10-08 de 10:00 a 12:00 hora local y después se confirma el alta
- **THEN** entonces el bloqueo no termina mientras el alta no confirma; al confirmarse, responde `409` con código `bloqueo_con_turnos` y `turnos` con ese turno de 10:30 a 11:15, no se persiste ningún bloqueo y el turno queda persistido

#### Scenario: Reprogramación que espera a un bloqueo en curso
- **GIVEN** dado un turno `programado` T1 del profesional A el jueves 2026-10-08 de 15:00 a 15:45 hora local, y una transacción que creó un bloqueo de A el 2026-10-08 de 10:00 a 12:00 y todavía no confirmó
- **WHEN** cuando en paralelo se reprograma T1 informando `inicio` 2026-10-08 10:30 hora local y después se confirma el bloqueo
- **THEN** entonces la reprogramación espera al bloqueo y responde `422` con código `turno_en_bloqueo`, T1 sigue de 15:00 a 15:45 y el bloqueo queda persistido

#### Scenario: Bloqueo que espera a una reprogramación en curso
- **GIVEN** dado un turno `programado` T1 del profesional A el jueves 2026-10-08 de 15:00 a 15:45 hora local, y una reprogramación de T1 a las 10:30 que ya validó sus referencias y todavía no confirmó
- **WHEN** cuando en paralelo se crea un bloqueo de A el 2026-10-08 de 10:00 a 12:00 hora local y después se confirma la reprogramación
- **THEN** entonces el bloqueo no termina mientras la reprogramación no confirma; al confirmarse, responde `409` con código `bloqueo_con_turnos` y `turnos` con T1 de 10:30 a 11:15, no se persiste ningún bloqueo y T1 queda de 10:30 a 11:15

#### Scenario: Reprogramación hacia otro profesional que espera a su bloqueo
- **GIVEN** dado un turno `programado` T2 del profesional B el jueves 2026-10-08 de 10:30 a 11:15 hora local, y una transacción que creó un bloqueo del profesional A el 2026-10-08 de 10:00 a 12:00 y todavía no confirmó
- **WHEN** cuando en paralelo se reprograma T2 informando `profesional_id` de A y después se confirma el bloqueo
- **THEN** entonces la reprogramación espera al bloqueo de A (el profesional destino) y responde `422` con código `turno_en_bloqueo`, T2 sigue con el profesional B de 10:30 a 11:15 y el bloqueo queda persistido
