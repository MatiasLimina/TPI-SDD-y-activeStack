# Spec Delta

## Purpose

Dejar constancia inmutable de cada cambio de turno (crear, reprogramar, cancelar) con el usuario que lo hizo, el momento y los valores antes y después, en la misma transacción que el cambio, y permitir que la recepcionista consulte ese historial, como exigen la Ley 25.326 y la Ley 26.529 (RN-CU-01).

## ADDED Requirements

### Requirement: Registro de auditoría al crear un turno
Cada `POST /turnos` exitoso MUST insertar exactamente un registro de auditoría con `accion = crear`, el `turno_id` del turno creado, `valores_previos` nulo y `valores_nuevos` con la instantánea del turno recién creado (RN-CU-01, US-011).

#### Scenario: Alta auditada
- **GIVEN** dado un profesional A, un paciente P, el sillón 1 y la prestación "Limpieza" (45 min, requiere sillón) activos, una recepcionista R autenticada, y que el reloj marca 2026-10-07 09:00 hora local
- **WHEN** cuando R envía `POST /turnos` con esos recursos e inicio 2026-10-08T10:00-03:00
- **THEN** entonces la respuesta es `201` y en la base existe exactamente un registro de auditoría para ese turno, con `accion = crear`, `usuario_id` igual al id de R, `ocurrido_en` 2026-10-07T12:00Z, `valores_previos` nulo y `valores_nuevos` con `profesional_id` de A, `paciente_id` de P, `sillon_id` del sillón 1, `inicio` 2026-10-08T13:00Z, `fin` 2026-10-08T13:45Z, `duracion_min` 45, `estado` `programado` y `motivo_cancelacion` nulo

#### Scenario: Alta con duración ajustada y sin sillón
- **GIVEN** dada la prestación "Consulta" (30 min, sin sillón), una recepcionista autenticada y que el reloj marca 2026-10-07 09:00 hora local
- **WHEN** cuando crea un turno de esa prestación sin sillón y con `duracion_min` 20 e inicio 2026-10-08T11:00-03:00
- **THEN** entonces el registro `crear` tiene en `valores_nuevos` `sillon_id` nulo, `duracion_min` 20 e `inicio` 2026-10-08T14:00Z y `fin` 2026-10-08T14:20Z

### Requirement: Registro de auditoría al reprogramar un turno
Cada `PATCH /turnos/{id}/reprogramar` exitoso MUST insertar exactamente un registro con `accion = reprogramar`, `valores_previos` con la instantánea del turno antes del cambio y `valores_nuevos` con la instantánea después del cambio. Los registros anteriores del turno MUST NOT modificarse. Una reprogramación exitosa sin cambio efectivo (DD-23a) también MUST generar su registro, con `valores_previos` iguales a `valores_nuevos`.

#### Scenario: Reprogramación auditada con valores previos y nuevos
- **GIVEN** dado un turno `programado` del profesional A, sillón 1 y "Limpieza" de 2026-10-08 10:00 a 10:45 hora local creado por la recepcionista R, otra recepcionista S autenticada, y que el reloj marca 2026-10-07 09:30 hora local
- **WHEN** cuando S envía `PATCH /turnos/{id}/reprogramar` con `inicio` 2026-10-08T15:00-03:00
- **THEN** entonces la respuesta es `200` y el turno tiene dos registros: el `crear` original sin cambios y uno nuevo con `accion = reprogramar`, `usuario_id` igual al id de S, `ocurrido_en` 2026-10-07T12:30Z, `valores_previos` con `inicio` 2026-10-08T13:00Z y `fin` 2026-10-08T13:45Z, y `valores_nuevos` con `inicio` 2026-10-08T18:00Z y `fin` 2026-10-08T18:45Z, con el resto de los campos iguales en ambas instantáneas

#### Scenario: Cambio de profesional y sillón auditado
- **GIVEN** dado un turno `programado` futuro del profesional A en el sillón 1, y el profesional B y el sillón 2 activos y libres en ese horario, y que el reloj marca 2026-10-07 09:00 hora local
- **WHEN** cuando una recepcionista lo reprograma informando `profesional_id` de B y `sillon_id` del sillón 2
- **THEN** entonces el registro `reprogramar` tiene en `valores_previos` el profesional A y el sillón 1, y en `valores_nuevos` el profesional B y el sillón 2, con el mismo `inicio` y `fin` en ambas

#### Scenario: Dos reprogramaciones generan dos registros
- **GIVEN** dado un turno `programado` futuro de 2026-10-08 10:00 a 10:45 hora local, una recepcionista autenticada y que el reloj marca 2026-10-07 09:00 hora local
- **WHEN** cuando una recepcionista lo reprograma dos veces con éxito, a las 15:00 y después a las 16:00 hora local
- **THEN** entonces el turno tiene tres registros (`crear`, `reprogramar`, `reprogramar`) y los `valores_previos` del segundo `reprogramar` coinciden con los `valores_nuevos` del primero

#### Scenario: Reprogramación sin cambio efectivo auditada
- **GIVEN** dado un turno `programado` futuro de 2026-10-08 10:00 a 10:45 hora local con un único registro `crear`, una recepcionista autenticada y que el reloj marca 2026-10-07 09:00 hora local
- **WHEN** cuando envía `PATCH /turnos/{id}/reprogramar` con el mismo `inicio` 2026-10-08T10:00-03:00 y sin cambiar profesional, sillón ni duración (DD-23a)
- **THEN** entonces la respuesta es `200` y el turno tiene dos registros: el `crear` original y uno nuevo con `accion = reprogramar` cuyos `valores_previos` son iguales a sus `valores_nuevos`

### Requirement: Registro de auditoría al cancelar un turno
Cada `POST /turnos/{id}/cancelar` exitoso MUST insertar exactamente un registro con `accion = cancelar`, `valores_previos` con la instantánea del turno antes de cancelarlo y `valores_nuevos` con la instantánea ya cancelada, incluido el motivo normalizado.

#### Scenario: Cancelación con motivo auditada
- **GIVEN** dado un turno `programado` futuro creado por la recepcionista R, otra recepcionista S autenticada, y que el reloj marca 2026-10-07 10:00 hora local
- **WHEN** cuando S envía `POST /turnos/{id}/cancelar` con motivo `"  El paciente avisó que no viene  "`
- **THEN** entonces la respuesta es `200` y existe un registro con `accion = cancelar`, `usuario_id` igual al id de S, `ocurrido_en` 2026-10-07T13:00Z, `valores_previos` con `estado` `programado` y `motivo_cancelacion` nulo, y `valores_nuevos` con `estado` `cancelado` y `motivo_cancelacion` `"El paciente avisó que no viene"`, con el mismo horario y recursos en ambas instantáneas

#### Scenario: Cancelación sin motivo auditada
- **GIVEN** dado un turno `programado` de 2026-10-08 10:00 a 10:45 hora local, una recepcionista autenticada y que el reloj marca 2026-10-07 09:00 hora local
- **WHEN** cuando envía `POST /turnos/{id}/cancelar` sin body
- **THEN** entonces el registro `cancelar` tiene `motivo_cancelacion` nulo en `valores_previos` y en `valores_nuevos`

### Requirement: Instantánea del turno en los valores auditados
`valores_previos` y `valores_nuevos`, cuando no son nulos, MUST contener siempre el mismo conjunto de campos del turno: `profesional_id`, `paciente_id`, `prestacion_id`, `sillon_id`, `inicio`, `fin`, `duracion_min`, `estado` y `motivo_cancelacion`. `inicio` y `fin` MUST persistirse en UTC con zona explícita (RN-CU-04). La instantánea MUST NOT incluir datos personales del paciente más allá de su identificador.

#### Scenario: Campos de la instantánea
- **GIVEN** dado un turno creado y luego cancelado, con un registro `crear` y un registro `cancelar`, y el reloj marca 2026-10-07 09:00 hora local
- **WHEN** cuando se leen directamente de la base `valores_nuevos` del registro `crear` y `valores_previos` y `valores_nuevos` del registro `cancelar`
- **THEN** entonces cada uno tiene exactamente las claves `profesional_id`, `paciente_id`, `prestacion_id`, `sillon_id`, `inicio`, `fin`, `duracion_min`, `estado` y `motivo_cancelacion`, y ninguna otra

#### Scenario: Instantes en UTC
- **GIVEN** dado un turno creado con inicio 2026-10-08T10:00-03:00 y duración 45 min, y el reloj marca 2026-10-07 09:00 hora local
- **WHEN** cuando se lee directamente de la base el `valores_nuevos` de su registro `crear`
- **THEN** entonces `inicio` es el texto `2026-10-08T13:00:00+00:00` y `fin` es `2026-10-08T13:45:00+00:00`, ambos con desplazamiento UTC cero

### Requirement: Autor e instante del registro
El `usuario_id` de cada registro MUST ser el usuario autenticado que hizo el cambio, nunca un valor del body. `ocurrido_en` MUST ser el instante actual del sistema al hacer el cambio, persistido en UTC.

#### Scenario: Autor informado en el body ignorado
- **GIVEN** dadas dos recepcionistas activas R y S, con R autenticada, y que el reloj marca 2026-10-07 09:00 hora local
- **WHEN** cuando R crea un turno con un body válido que además incluye `usuario_id` y `creado_por` con el id de S
- **THEN** entonces la respuesta es `201` y el registro `crear` tiene `usuario_id` igual al id de R

#### Scenario: Cada operación registra a quien la hizo
- **GIVEN** dadas dos recepcionistas R y S, y que el reloj marca 2026-10-07 09:00 hora local durante las tres operaciones
- **WHEN** cuando R crea un turno para 2026-10-08 10:00 hora local, S lo reprograma y R lo cancela
- **THEN** entonces los registros `crear`, `reprogramar` y `cancelar` tienen `usuario_id` de R, S y R respectivamente

### Requirement: Una operación rechazada no genera registro
Una operación de crear, reprogramar o cancelar que no modifica el turno (respuesta `401`, `403`, `404`, `409` o `422`) MUST NOT insertar registros de auditoría.

#### Scenario: Alta en conflicto no auditada
- **GIVEN** dado un turno `programado` del profesional A de 10:00 a 10:45 hora local, y el reloj marca 2026-10-07 09:00 hora local
- **WHEN** cuando una recepcionista intenta crear otro turno del profesional A de 10:30 a 11:15
- **THEN** entonces la respuesta es `409` y la cantidad total de registros de auditoría en la base no cambia

#### Scenario: Reprogramación inválida no auditada
- **GIVEN** dado un turno `programado` futuro con un único registro `crear`, y que el reloj marca 2026-10-07 09:00 hora local
- **WHEN** cuando una recepcionista lo reprograma con `duracion_min` 7
- **THEN** entonces la respuesta es `422` y el turno sigue teniendo un único registro

#### Scenario: Segunda cancelación no auditada
- **GIVEN** dado un turno ya cancelado, con registros `crear` y `cancelar`, y que el reloj marca 2026-10-07 09:00 hora local
- **WHEN** cuando una recepcionista vuelve a enviar `POST /turnos/{id}/cancelar`
- **THEN** entonces la respuesta es `409` con código `turno_ya_cancelado` y el turno sigue teniendo exactamente esos dos registros

#### Scenario: Escritura sin token no auditada
- **GIVEN** dado un turno `programado` futuro con un único registro `crear`
- **WHEN** cuando se envía `POST /turnos/{id}/cancelar` sin encabezado `Authorization`
- **THEN** entonces la respuesta es `401` con `WWW-Authenticate: Bearer` y el turno sigue teniendo un único registro y sigue `programado`

#### Scenario: Escritura sobre turno inexistente no auditada
- **GIVEN** dada una recepcionista autenticada, el reloj en 2026-10-07 09:00 hora local y un UUID que no corresponde a ningún turno
- **WHEN** cuando envía `POST /turnos/{id}/cancelar` y, por separado, `PATCH /turnos/{id}/reprogramar` con un `inicio` futuro, sobre ese UUID
- **THEN** entonces ambas respuestas son `404` con `detail.codigo = "turno_inexistente"` y la cantidad total de registros de auditoría en la base no cambia

#### Scenario: Odontólogo rechazado no audita
- **GIVEN** dado un turno `programado` futuro, un odontólogo autenticado y que el reloj marca 2026-10-07 09:00 hora local
- **WHEN** cuando envía `POST /turnos/{id}/cancelar`
- **THEN** entonces la respuesta es `403` y no se inserta ningún registro de auditoría

### Requirement: Atomicidad del cambio con su registro
El cambio del turno y su registro de auditoría MUST confirmarse en la misma transacción: si el registro no puede persistirse, el cambio del turno MUST revertirse por completo y la operación MUST fallar (a nivel de caso de uso, con un error de integridad de la base; no se define una respuesta HTTP para este caso, que no puede ocurrir por la API porque el autor se relee de la base), y si el cambio del turno falla, MUST NOT quedar registro.

#### Scenario: Falla de auditoría revierte el alta
- **GIVEN** dado, con el reloj en 2026-10-07 09:00 hora local, un alta de turno válida cuyo registro de auditoría no puede persistirse, porque su autor no existe en la base
- **WHEN** cuando se ejecuta el alta
- **THEN** entonces el caso de uso lanza un error de integridad de la base, no se persiste ningún turno y no se persiste ningún registro de auditoría

#### Scenario: Falla de auditoría revierte la reprogramación
- **GIVEN** dado, con el reloj en 2026-10-07 09:00 hora local, un turno `programado` futuro de 10:00 a 10:45 y una reprogramación válida a las 15:00 cuyo registro de auditoría no puede persistirse
- **WHEN** cuando se ejecuta la reprogramación
- **THEN** entonces el caso de uso lanza un error de integridad de la base, el turno conserva su horario de 10:00 a 10:45 y no se agrega ningún registro de auditoría

#### Scenario: Falla de auditoría revierte la cancelación
- **GIVEN** dado, con el reloj en 2026-10-07 09:00 hora local, un turno `programado` futuro y una cancelación cuyo registro de auditoría no puede persistirse
- **WHEN** cuando se ejecuta la cancelación
- **THEN** entonces el caso de uso lanza un error de integridad de la base, el turno sigue `programado` sin motivo de cancelación y su horario sigue ocupado

### Requirement: Registro append-only garantizado por la base
Los registros de auditoría MUST ser inmutables: la base de datos MUST rechazar cualquier `UPDATE`, `DELETE` o `TRUNCATE` sobre ellos, aunque no provenga de la aplicación. La API MUST NOT exponer ninguna operación que modifique o borre registros de auditoría.

#### Scenario: Modificación directa rechazada
- **GIVEN** dado un registro de auditoría persistido
- **WHEN** cuando se ejecuta directamente en la base un `UPDATE` que cambia su `usuario_id` o su `valores_nuevos`
- **THEN** entonces la base rechaza la sentencia con un error y el registro conserva sus valores

#### Scenario: Borrado directo rechazado
- **GIVEN** dado un registro de auditoría persistido
- **WHEN** cuando se ejecuta directamente en la base un `DELETE` de esa fila
- **THEN** entonces la base rechaza la sentencia con un error y el registro sigue existiendo

#### Scenario: Vaciado de la tabla rechazado
- **WHEN** cuando se ejecuta directamente en la base un `TRUNCATE` de la tabla de auditoría
- **THEN** entonces la base rechaza la sentencia con un error

#### Scenario: Inserción directa aceptada
- **GIVEN** dado un turno y un usuario existentes
- **WHEN** cuando se inserta directamente en la base un registro `cancelar` válido para ellos
- **THEN** entonces la base acepta la inserción

#### Scenario: Sin rutas de escritura sobre la auditoría
- **GIVEN** dado un turno con registros de auditoría y una recepcionista autenticada
- **WHEN** cuando envía `POST`, `PUT`, `PATCH` o `DELETE` a `/turnos/{id}/auditoria`
- **THEN** entonces la respuesta es `405` y los registros no cambian

### Requirement: Integridad del registro en la base
La base MUST garantizar que `accion` sea `crear`, `reprogramar` o `cancelar`; que `valores_previos` sea nulo si y solo si la acción es `crear`; que `valores_nuevos` y `ocurrido_en` no sean nulos; y que `turno_id` y `usuario_id` referencien filas existentes, impidiendo borrar un turno o un usuario que tenga registros (DD-08, DD-16).

#### Scenario: Acción inválida rechazada
- **WHEN** cuando se inserta directamente un registro con `accion = 'borrar'`
- **THEN** entonces la base rechaza la inserción con una violación de CHECK

#### Scenario: Alta con valores previos rechazada
- **WHEN** cuando se inserta directamente un registro `crear` con `valores_previos` no nulo
- **THEN** entonces la base rechaza la inserción con una violación de CHECK

#### Scenario: Reprogramación sin valores previos rechazada
- **WHEN** cuando se inserta directamente un registro `reprogramar` o `cancelar` con `valores_previos` nulo
- **THEN** entonces la base rechaza la inserción con una violación de CHECK

#### Scenario: Valores nuevos o instante nulos rechazados
- **WHEN** cuando se inserta directamente un registro con `valores_nuevos` nulo o con `ocurrido_en` nulo
- **THEN** entonces la base rechaza la inserción con una violación de NOT NULL

#### Scenario: Referencias inexistentes rechazadas
- **WHEN** cuando se inserta directamente un registro con un `turno_id` o un `usuario_id` que no corresponde a ninguna fila
- **THEN** entonces la base rechaza la inserción con una violación de clave foránea

#### Scenario: Turno auditado no se puede borrar
- **GIVEN** dado un turno con al menos un registro de auditoría
- **WHEN** cuando se borra directamente la fila del turno
- **THEN** entonces la base rechaza el borrado con una violación de clave foránea

#### Scenario: Usuario con registros no se puede borrar
- **GIVEN** dado un usuario U autor de al menos un registro de auditoría
- **WHEN** cuando se borra directamente la fila de U
- **THEN** entonces la base rechaza el borrado con una violación de clave foránea

### Requirement: Consulta del historial de auditoría de un turno
El sistema SHALL exponer `GET /turnos/{id}/auditoria`, que responde `200` con la lista de registros del turno en el orden en que ocurrieron. Los registros con el mismo `ocurrido_en` MUST salir en el orden de inserción (por `id`). Cada elemento MUST incluir `id`, `accion`, `usuario_id`, `ocurrido_en`, `valores_previos` y `valores_nuevos`, con `ocurrido_en` y los `inicio` y `fin` de las instantáneas expresados en `America/Argentina/Buenos_Aires`.

#### Scenario: Historial completo en orden cronológico
- **GIVEN** dado un turno creado por la recepcionista R con inicio 2026-10-08 10:00 hora local, reprogramado por S a las 15:00 y cancelado por R, con el reloj fijo en 2026-10-07 09:00 hora local durante las tres operaciones
- **WHEN** cuando una recepcionista autenticada envía `GET /turnos/{id}/auditoria`
- **THEN** entonces la respuesta es `200` con tres elementos en el orden `crear`, `reprogramar`, `cancelar`, con `usuario_id` de R, S y R, y cada `ocurrido_en` igual a 2026-10-07T09:00-03:00

#### Scenario: Instantes presentados en hora local
- **GIVEN** dado un turno creado con inicio 2026-10-08T10:00-03:00 y fin 10:45-03:00, y el reloj marca 2026-10-07 09:00 hora local
- **WHEN** cuando una recepcionista consulta su auditoría
- **THEN** entonces el registro `crear` muestra `valores_previos` nulo y en `valores_nuevos` `inicio` 2026-10-08T10:00-03:00 y `fin` 2026-10-08T10:45-03:00

#### Scenario: Consulta que no modifica nada
- **GIVEN** dado un turno con dos registros de auditoría
- **WHEN** cuando una recepcionista consulta su auditoría dos veces
- **THEN** entonces ambas respuestas son iguales y el turno sigue teniendo dos registros

#### Scenario: Solo los registros del turno pedido
- **GIVEN** dados dos turnos distintos, T1 con dos registros y T2 con uno
- **WHEN** cuando una recepcionista consulta la auditoría de T1
- **THEN** entonces la respuesta contiene exactamente los dos registros de T1

### Requirement: Turno sin registros, inexistente o con identificador inválido
Si el turno existe pero no tiene registros (por ejemplo, creado antes de que existiera la auditoría), la consulta MUST responder `200` con una lista vacía. Si el `id` del path no corresponde a ningún turno, MUST responder `404` con código `turno_inexistente` (recurso del path, DD-21). Un `id` que no es un identificador válido MUST responder `422`.

#### Scenario: Turno previo sin registros
- **GIVEN** dado un turno insertado directamente en la base, sin registros de auditoría
- **WHEN** cuando una recepcionista consulta su auditoría
- **THEN** entonces la respuesta es `200` con una lista vacía

#### Scenario: Turno previo con un cambio posterior
- **GIVEN** dado un turno `programado` futuro insertado directamente en la base, sin registros, y que el reloj marca 2026-10-07 09:00 hora local
- **WHEN** cuando una recepcionista lo cancela y después consulta su auditoría
- **THEN** entonces la respuesta contiene un único registro, `cancelar`

#### Scenario: Turno inexistente
- **WHEN** cuando una recepcionista envía `GET /turnos/{id}/auditoria` con un `id` con formato válido que no corresponde a ningún turno
- **THEN** entonces la respuesta es `404` con `detail.codigo = "turno_inexistente"`

#### Scenario: Identificador con formato inválido
- **WHEN** cuando una recepcionista envía `GET /turnos/no-es-un-id/auditoria`
- **THEN** entonces la respuesta es `422`

### Requirement: Consulta de auditoría reservada a la recepcionista
`GET /turnos/{id}/auditoria` MUST exigir un usuario autenticado con rol `recepcionista` (matriz de `03_actores_y_roles.md`, RN-CU-01, DD-24). Sin token o con un token inválido MUST responder `401` con `WWW-Authenticate: Bearer`; un `odontologo` MUST recibir `403` con código `rol_insuficiente`, aunque el turno sea de su propio profesional. Autenticación y rol MUST evaluarse antes que el `id` y la existencia del turno.

#### Scenario: Odontólogo no puede consultar la auditoría
- **GIVEN** dado un turno de su propio profesional con registros de auditoría y un odontólogo autenticado
- **WHEN** cuando envía `GET /turnos/{id}/auditoria`
- **THEN** entonces la respuesta es `403` con `detail = {"codigo": "rol_insuficiente", "mensaje": "Rol insuficiente"}` y el cuerpo no contiene ningún registro

#### Scenario: Sin token
- **GIVEN** dado un turno con registros de auditoría
- **WHEN** cuando se envía `GET /turnos/{id}/auditoria` sin encabezado `Authorization`
- **THEN** entonces la respuesta es `401` con `WWW-Authenticate: Bearer` y `detail.codigo = "no_autenticado"`

#### Scenario: Rol evaluado antes que la existencia del turno
- **GIVEN** dado un odontólogo autenticado
- **WHEN** cuando envía `GET /turnos/{id}/auditoria` con un UUID que no corresponde a ningún turno
- **THEN** entonces la respuesta es `403`, no `404`

#### Scenario: Autenticación evaluada antes que el identificador
- **WHEN** cuando se envía `GET /turnos/no-es-un-id/auditoria` sin encabezado `Authorization`
- **THEN** entonces la respuesta es `401`, no `422`
