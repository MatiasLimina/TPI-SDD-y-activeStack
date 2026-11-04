# Spec Delta

## Purpose

Permitir que la recepción y cada odontólogo bloqueen franjas de la agenda de un profesional (un congreso, un trámite, unas vacaciones) para que no se le asignen turnos en esas horas, sin dejar nunca turnos activos dentro de un bloqueo (RN-HB-02, RN-HB-03, US-003).

## ADDED Requirements

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
- **THEN** entonces la respuesta es `201` y el bloqueo cubre los cinco días

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
- **WHEN** cuando la recepcionista crea un bloqueo de B con un intervalo y un motivo válidos
- **THEN** entonces la respuesta es `201` (DD-30)

### Requirement: Profesional del bloqueo según el rol
La `recepcionista` MUST indicar el `profesional_id` del bloqueo: sin él → `422 profesional_requerido`. Para el `odontologo` el profesional MUST ser el de su usuario: si omite `profesional_id` se usa el suyo, y uno distinto → `403 profesional_ajeno` sin persistir (RN-HB-02, RN-AU-02, Flujo 5). Un profesional inexistente → `422 referencia_invalida`.

#### Scenario: Odontólogo bloquea su agenda sin indicar profesional
- **GIVEN** dado un odontólogo autenticado vinculado al profesional A
- **WHEN** cuando envía `POST /bloqueos` sin `profesional_id`, con `inicio` 2026-10-08T10:00:00-03:00, `fin` 2026-10-08T11:00:00-03:00 y `motivo` "Trámite"
- **THEN** entonces la respuesta es `201` con `profesional_id` de A y `creado_por` igual al id del odontólogo

#### Scenario: Odontólogo indica su propio profesional
- **GIVEN** dado un odontólogo autenticado vinculado al profesional A
- **WHEN** cuando envía `POST /bloqueos` con `profesional_id` de A y un intervalo y un motivo válidos
- **THEN** entonces la respuesta es `201` con `profesional_id` de A

#### Scenario: Odontólogo intenta bloquear la agenda de otro
- **GIVEN** dado un odontólogo autenticado vinculado al profesional A, y el profesional B
- **WHEN** cuando envía `POST /bloqueos` con `profesional_id` de B, y luego con un UUID que no corresponde a ningún profesional
- **THEN** entonces ambas respuestas son `403` con `{"detail": {"codigo": "profesional_ajeno", "mensaje": "Solo podés operar sobre tus propios bloqueos"}}` y no se persiste ningún bloqueo

#### Scenario: Profesional ajeno antes que el bloqueo inválido
- **GIVEN** dado un odontólogo autenticado vinculado al profesional A, y el profesional B
- **WHEN** cuando envía `POST /bloqueos` con `profesional_id` de B y `fin` igual a `inicio`
- **THEN** entonces la respuesta es `403` con código `profesional_ajeno`, no `422`

#### Scenario: Recepcionista sin profesional
- **GIVEN** dado una recepcionista autenticada
- **WHEN** cuando envía `POST /bloqueos` sin `profesional_id`, con un intervalo y un motivo válidos
- **THEN** entonces la respuesta es `422` con `{"detail": {"codigo": "profesional_requerido", "mensaje": "indicá el profesional del bloqueo"}}` y no se persiste ningún bloqueo

#### Scenario: Profesional inexistente
- **GIVEN** dado una recepcionista autenticada
- **WHEN** cuando envía `POST /bloqueos` con un `profesional_id` que no corresponde a ningún profesional
- **THEN** entonces la respuesta es `422` con `{"detail": {"codigo": "referencia_invalida", "referencia": "profesional", "motivo": "inexistente"}}` y no se persiste ningún bloqueo

### Requirement: Validación del bloqueo
Un bloqueo MUST tener `fin` posterior a `inicio` y un `motivo` no vacío; el motivo se guarda sin espacios en los extremos y tiene a lo sumo 255 caracteres. Si no → `422` sin persistir: `bloqueo_invalido` para el intervalo o el motivo vacío, y el `422` de validación del request para un campo faltante, un motivo demasiado largo o un datetime sin zona horaria (RN-HB-02, `04_modelo_de_datos.md` §Bloqueo).

#### Scenario: Fin igual al inicio
- **WHEN** cuando la recepcionista crea un bloqueo de A con `inicio` y `fin` 2026-10-08T10:00:00-03:00
- **THEN** entonces la respuesta es `422` con `{"detail": {"codigo": "bloqueo_invalido", "mensaje": "el bloqueo debe tener fin posterior a inicio y un motivo no vacío"}}` y no se persiste ningún bloqueo

#### Scenario: Fin anterior al inicio
- **WHEN** cuando la recepcionista crea un bloqueo de A con `inicio` 2026-10-08T12:00:00-03:00 y `fin` 2026-10-08T10:00:00-03:00
- **THEN** entonces la respuesta es `422` con código `bloqueo_invalido`

#### Scenario: Motivo vacío o solo espacios
- **WHEN** cuando la recepcionista crea un bloqueo de A con `motivo` "" y luego con `motivo` "   "
- **THEN** entonces ambas respuestas son `422` con código `bloqueo_invalido` y no se persiste ningún bloqueo

#### Scenario: Motivo con espacios en los extremos
- **WHEN** cuando la recepcionista crea un bloqueo válido de A con `motivo` "  Congreso  "
- **THEN** entonces la respuesta es `201` con `motivo` "Congreso", y así queda en la base

#### Scenario: Campos faltantes o fuera de forma
- **WHEN** cuando la recepcionista envía `POST /bloqueos` sin `motivo`, luego sin `fin`, luego con un `motivo` de 256 caracteres
- **THEN** entonces cada respuesta es `422` y no se persiste ningún bloqueo

#### Scenario: Datetime sin zona horaria
- **WHEN** cuando la recepcionista crea un bloqueo de A con `inicio` `2026-10-08T10:00:00` (sin zona)
- **THEN** entonces la respuesta es `422` y no se persiste ningún bloqueo

### Requirement: Bloqueo sobre turnos activos rechazado
Crear un bloqueo cuyo intervalo se superpone con turnos activos (no cancelados) del mismo profesional MUST rechazarse con `409` y la lista de esos turnos, sin persistir el bloqueo ni modificar los turnos ni sus recordatorios (RN-HB-03, DD-12). Se usa el criterio `[)`: un turno contiguo al bloqueo no cuenta (RN-AG-03).

#### Scenario: Turno activo dentro del intervalo
- **GIVEN** dado un turno `programado` T1 del profesional A el jueves 2026-10-08 de 10:30 a 11:15 hora local
- **WHEN** cuando la recepcionista crea un bloqueo de A el 2026-10-08 de 10:00 a 12:00 hora local
- **THEN** entonces la respuesta es `409` con `{"detail": {"codigo": "bloqueo_con_turnos", "mensaje": "hay turnos activos en el intervalo: reprogramalos o cancelalos antes de bloquear", "turnos": [{"id": <id de T1>, "inicio": "2026-10-08T10:30:00-03:00", "fin": "2026-10-08T11:15:00-03:00"}]}}` y no se persiste ningún bloqueo

#### Scenario: Varios turnos afectados, ordenados por inicio
- **GIVEN** dado los turnos `programado` del profesional A el jueves 2026-10-08 de 11:00 a 11:45 (T2) y de 09:30 a 10:15 (T1, que empieza antes del bloqueo y termina dentro), y un turno cancelado de A de 10:30 a 10:45
- **WHEN** cuando la recepcionista crea un bloqueo de A el 2026-10-08 de 10:00 a 12:00 hora local
- **THEN** entonces la respuesta es `409` y `turnos` lista exactamente T1 y luego T2, sin el turno cancelado

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
- **THEN** entonces la respuesta es `409` con código `bloqueo_con_turnos` y `turnos` con T1

#### Scenario: El rechazo no toca el turno ni su recordatorio
- **GIVEN** dado un turno `programado` T1 del profesional A el viernes 2026-10-09 de 10:30 a 11:15 hora local, creado con un recordatorio `pendiente`
- **WHEN** cuando la recepcionista crea un bloqueo de A el 2026-10-09 de 10:00 a 12:00 hora local
- **THEN** entonces la respuesta es `409`, T1 sigue `programado` de 10:30 a 11:15, su recordatorio sigue `pendiente` con el mismo `programado_para`, y no se registra auditoría para T1

#### Scenario: Turno ya resuelto, el bloqueo entra
- **GIVEN** dado un turno `programado` T1 del profesional A el jueves 2026-10-08 de 10:30 a 11:15, y un bloqueo de A de 10:00 a 12:00 rechazado con `409`
- **WHEN** cuando la recepcionista cancela T1 y vuelve a crear el mismo bloqueo
- **THEN** entonces la respuesta es `201`

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
El sistema SHALL exponer `GET /bloqueos`, con filtro opcional `profesional_id`, que responde `200` con la lista de bloqueos (mismos campos que el alta) ordenada por `inicio`, incluidos los pasados. La `recepcionista` ve los de todos los profesionales o los del filtrado (uno inexistente da lista vacía). El `odontologo` ve solo los de su profesional; un filtro con otro profesional → `403 profesional_ajeno` (RN-AU-02).

#### Scenario: Recepcionista lista todos los bloqueos
- **GIVEN** dado un bloqueo de A el 2026-10-09 de 10:00 a 11:00 y uno de B el 2026-10-08 de 15:00 a 16:00 hora local
- **WHEN** cuando la recepcionista envía `GET /bloqueos`
- **THEN** entonces la respuesta es `200` con ambos bloqueos, primero el de B y después el de A

#### Scenario: Recepcionista filtra por profesional
- **GIVEN** dado un bloqueo de A y uno de B
- **WHEN** cuando la recepcionista envía `GET /bloqueos?profesional_id=<id de A>`
- **THEN** entonces la respuesta es `200` solo con el bloqueo de A

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
El sistema SHALL exponer `DELETE /bloqueos/{id}`, que borra el bloqueo y responde `204` sin cuerpo; el intervalo vuelve a admitir turnos. Un bloqueo inexistente → `404 recurso_inexistente` con `recurso = "bloqueo"`. El `odontologo` solo borra bloqueos de su profesional, los haya creado él o la recepción: sobre uno de otro profesional → `403 profesional_ajeno` y el bloqueo sigue (RN-HB-02, RN-AU-02).

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

#### Scenario: Identificador mal formado
- **WHEN** cuando la recepcionista envía `DELETE /bloqueos/no-es-un-id`
- **THEN** entonces la respuesta es `422`

### Requirement: Bloqueos accesibles solo con autenticación
Alta, consulta y borrado de bloqueos MUST exigir un usuario autenticado de rol `recepcionista` u `odontologo` (RN-AU-01). Sin token, o con un token inválido, MUST responder `401` con `WWW-Authenticate: Bearer` y `{"detail": {"codigo": "no_autenticado", "mensaje": "No autenticado"}}`, antes de validar el body o el path, sin cambios en la base.

#### Scenario: Sin token
- **GIVEN** dado un bloqueo B1 del profesional A
- **WHEN** cuando se envían sin encabezado `Authorization` `POST /bloqueos` con un body válido, `GET /bloqueos` y `DELETE /bloqueos/{id de B1}`
- **THEN** entonces cada respuesta es `401` con `WWW-Authenticate: Bearer` y código `no_autenticado`, y B1 sigue siendo el único bloqueo

#### Scenario: Autenticación antes que el body y el path
- **WHEN** cuando se envían sin token `POST /bloqueos` con `{"fin": "no-es-fecha"}` y `DELETE /bloqueos/no-es-un-id`
- **THEN** entonces ambas respuestas son `401`, no `422`

### Requirement: Integridad del bloqueo en la base
La base MUST rechazar, aun con escrituras directas, un bloqueo con `fin <= inicio`, con un motivo vacío o solo espacios, sin `creado_por` o con un profesional o un autor inexistentes. Los instantes se guardan como `timestamptz` (DD-17, RN-CU-04).

#### Scenario: Escrituras directas inválidas
- **WHEN** cuando se inserta directamente en la base un bloqueo con `fin` igual a `inicio`, otro con `motivo` "   ", otro sin `creado_por` y otro con un `profesional_id` inexistente
- **THEN** entonces la base rechaza cada inserción con una violación de integridad

#### Scenario: Escritura directa válida
- **WHEN** cuando se inserta directamente un bloqueo con `fin` posterior a `inicio`, motivo "Congreso", un profesional y un autor existentes
- **THEN** entonces la base lo acepta

### Requirement: Bloqueo y turno simultáneos
Un alta de bloqueo concurrente con un alta o una reprogramación de turno del mismo profesional sobre intervalos superpuestos MUST terminar con a lo sumo uno de los dos persistido: o el bloqueo se rechaza con `409 bloqueo_con_turnos`, o el turno con `422 turno_en_bloqueo`. Nunca queda un turno activo dentro de un bloqueo (RN-HB-03, RN-AG-06).

#### Scenario: Alta de bloqueo y alta de turno en paralelo
- **GIVEN** dado el profesional A sin turnos ni bloqueos el jueves 2026-10-08
- **WHEN** cuando en paralelo la recepcionista crea un bloqueo de A de 10:00 a 12:00 y un turno de A de 10:30 a 11:15 hora local, cada request en su propia conexión
- **THEN** entonces exactamente uno responde con éxito (`201`) y el otro con `409 bloqueo_con_turnos` o `422 turno_en_bloqueo`, y en la base no hay un turno activo de A dentro de un bloqueo de A

#### Scenario: Alta de bloqueo y reprogramación hacia el intervalo en paralelo
- **GIVEN** dado un turno `programado` T1 del profesional A el jueves 2026-10-08 de 15:00 a 15:45 hora local
- **WHEN** cuando en paralelo la recepcionista crea un bloqueo de A de 10:00 a 12:00 y reprograma T1 a las 10:30 del mismo día, cada request en su propia conexión
- **THEN** entonces exactamente uno responde con éxito y el otro con `409 bloqueo_con_turnos` o `422 turno_en_bloqueo`, y en la base no hay un turno activo de A dentro de un bloqueo de A
