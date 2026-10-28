# Spec Delta

## MODIFIED Requirements

### Requirement: Creación de un turno válido
El sistema SHALL exponer `POST /turnos` que recibe profesional, paciente, prestación, sillón opcional, inicio (con zona horaria) y duración opcional en minutos. Un turno válido MUST persistirse con `estado = programado`, `inicio` y `fin` almacenados en UTC, y responder `201` con el turno creado, sus instantes expresados en `America/Argentina/Buenos_Aires`. El autor del turno (`creado_por`) MUST ser el usuario autenticado que hizo el alta, y MUST NOT tomarse del body.

#### Scenario: Turno con sillón creado
- **GIVEN** dado un profesional, un paciente, un sillón activos y la prestación "Limpieza" (45 min, requiere sillón), una recepcionista R autenticada, y que el reloj marca 2026-10-07 09:00 hora local
- **WHEN** cuando R envía `POST /turnos` con esos recursos e inicio 2026-10-08 10:00-03:00
- **THEN** entonces la respuesta es `201`, el turno tiene `estado = programado`, `inicio` 2026-10-08T10:00-03:00, `fin` 2026-10-08T10:45-03:00 y `creado_por` igual al id de R, y en la base `inicio` vale 2026-10-08T13:00Z y `creado_por` es el id de R

#### Scenario: Inicio sin zona horaria rechazado
- **WHEN** cuando una recepcionista autenticada envía `POST /turnos` con un inicio sin zona horaria (por ejemplo `2026-10-08T10:00:00`)
- **THEN** entonces la respuesta es `422` y no se persiste ningún turno

#### Scenario: Autor informado en el body ignorado
- **GIVEN** dado dos recepcionistas activas R y S, con R autenticada
- **WHEN** cuando R envía `POST /turnos` con un body válido que además incluye `creado_por` con el id de S
- **THEN** entonces la respuesta es `201` y el turno queda con `creado_por` igual al id de R

### Requirement: Cancelación de un turno programado
El sistema SHALL exponer `POST /turnos/{id}/cancelar`. Cancelar un turno `programado` cuyo inicio todavía no llegó MUST cambiar su `estado` a `cancelado` y responder `200` con el turno actualizado, sus instantes expresados en `America/Argentina/Buenos_Aires`. El turno MUST NOT borrarse: se conserva con sus datos originales (DD-08), incluido su `creado_por`. Requiere un usuario autenticado con rol `recepcionista`.

#### Scenario: Turno futuro cancelado
- **GIVEN** dado un turno `programado` del profesional A en el sillón 1 con inicio 2026-10-08 10:00-03:00 y fin 10:45-03:00, una recepcionista autenticada, y que el reloj marca 2026-10-07 09:00 hora local
- **WHEN** cuando la recepcionista envía `POST /turnos/{id}/cancelar` para ese turno
- **THEN** entonces la respuesta es `200`, el turno tiene `estado = cancelado`, `inicio` 2026-10-08T10:00-03:00 y `fin` 2026-10-08T10:45-03:00, y en la base la fila sigue existiendo con `estado = 'cancelado'` y los mismos profesional, sillón, paciente, prestación, inicio y fin

#### Scenario: Cancelar no cambia el autor
- **GIVEN** dado un turno futuro creado por la recepcionista R
- **WHEN** cuando otra recepcionista S lo cancela
- **THEN** entonces la respuesta es `200` y el turno conserva `creado_por` igual al id de R

### Requirement: Reprogramación de un turno programado
El sistema SHALL exponer `PATCH /turnos/{id}/reprogramar`. Reprogramar un turno `programado` cuyo inicio todavía no llegó MUST actualizar la misma fila (mismo `id`, paciente, prestación, `creado_por` y `estado = programado`), recalcular `fin = inicio + duración` y responder `200` con el turno, sus instantes en `America/Argentina/Buenos_Aires`. MUST NOT crearse una fila nueva. Requiere un usuario autenticado con rol `recepcionista`.

#### Scenario: Turno movido a un hueco libre
- **GIVEN** dado un turno `programado` del profesional A, sillón 1, paciente P y prestación "Limpieza" (45 min) de 2026-10-08 10:00 a 10:45 hora local, una recepcionista autenticada, y que el reloj marca 2026-10-07 09:00 hora local
- **WHEN** cuando la recepcionista envía `PATCH /turnos/{id}/reprogramar` con `inicio` 2026-10-08T15:00-03:00
- **THEN** entonces la respuesta es `200` con el mismo `id`, `estado = programado`, `inicio` 2026-10-08T15:00-03:00 y `fin` 2026-10-08T15:45-03:00, y en la base esa fila tiene `inicio` 2026-10-08T18:00Z y no existe ninguna otra fila para ese paciente

#### Scenario: Cambio de profesional y de sillón
- **GIVEN** dado un turno `programado` futuro del profesional A en el sillón 1 de 10:00 a 10:45, el profesional B y el sillón 2 activos y libres en ese horario, y una recepcionista autenticada
- **WHEN** cuando se reprograma informando `profesional_id` del profesional B y `sillon_id` del sillón 2
- **THEN** entonces la respuesta es `200`, el turno conserva su `id`, inicio, fin, paciente y prestación, y en la base queda asignado al profesional B y al sillón 2

#### Scenario: Reprogramar no cambia el autor
- **GIVEN** dado un turno futuro creado por la recepcionista R
- **WHEN** cuando otra recepcionista S lo reprograma a un hueco libre
- **THEN** entonces la respuesta es `200` y el turno conserva `creado_por` igual al id de R

## ADDED Requirements

### Requirement: Operaciones sobre turnos reservadas a la recepcionista
`POST /turnos`, `POST /turnos/{id}/cancelar` y `PATCH /turnos/{id}/reprogramar` MUST exigir un usuario autenticado con rol `recepcionista` (RN-AU-01, matriz de `03_actores_y_roles.md`, DD-24). Un `odontologo` autenticado MUST recibir `403` con `{"detail": {"codigo": "rol_insuficiente", "mensaje": "Rol insuficiente"}}`. Autenticación y rol MUST evaluarse antes que el body y que la existencia del turno; ante `401` o `403` nada cambia.

#### Scenario: Odontólogo no puede crear turnos
- **GIVEN** dado un odontólogo autenticado y un body de alta válido para su propio profesional
- **WHEN** cuando envía `POST /turnos`
- **THEN** entonces la respuesta es `403` con `detail = {"codigo": "rol_insuficiente", "mensaje": "Rol insuficiente"}` y no se persiste ningún turno

#### Scenario: Odontólogo no puede cancelar ni reprogramar
- **GIVEN** dado un turno `programado` futuro de su propio profesional y un odontólogo autenticado
- **WHEN** cuando envía `POST /turnos/{id}/cancelar`, o `PATCH /turnos/{id}/reprogramar` con un nuevo `inicio` libre
- **THEN** entonces ambas respuestas son `403` y en la base el turno sigue `programado` en su horario original

#### Scenario: Sin token en cancelar y reprogramar
- **GIVEN** dado un turno `programado` futuro
- **WHEN** cuando se envía `POST /turnos/{id}/cancelar`, o `PATCH /turnos/{id}/reprogramar`, sin encabezado `Authorization`
- **THEN** entonces ambas respuestas son `401` con `WWW-Authenticate: Bearer` y el turno no cambia

#### Scenario: Rol evaluado antes que la existencia del turno
- **GIVEN** dado un odontólogo autenticado
- **WHEN** cuando envía `POST /turnos/{id}/cancelar` con un UUID que no corresponde a ningún turno
- **THEN** entonces la respuesta es `403`, no `404`

#### Scenario: Autenticación evaluada antes que el body
- **WHEN** cuando se envía `POST /turnos` sin encabezado `Authorization` y con un body JSON al que le faltan campos obligatorios
- **THEN** entonces la respuesta es `401`, no `422`

#### Scenario: Rol evaluado antes que el body
- **GIVEN** dado un odontólogo autenticado
- **WHEN** cuando envía `PATCH /turnos/{id}/reprogramar` con `{"inicio": "no-es-una-fecha"}`
- **THEN** entonces la respuesta es `403`, no `422`

### Requirement: Autor del turno referenciado en la base
`creado_por` MUST referenciar a un usuario existente mediante una clave foránea que impida borrar a un usuario que creó turnos. `creado_por` MUST seguir admitiendo nulo para los turnos creados antes de que existiera la autenticación.

#### Scenario: Autor inexistente rechazado por la base
- **WHEN** cuando se inserta directamente un turno con `creado_por` igual a un UUID que no corresponde a ningún usuario
- **THEN** entonces la base rechaza la inserción con una violación de clave foránea

#### Scenario: Usuario con turnos no se puede borrar
- **GIVEN** dado un turno cuyo `creado_por` es el usuario U
- **WHEN** cuando se borra directamente la fila de U
- **THEN** entonces la base rechaza el borrado con una violación de clave foránea

#### Scenario: Turno previo sin autor
- **WHEN** cuando se inserta directamente un turno con `creado_por` nulo
- **THEN** entonces la base acepta la inserción
