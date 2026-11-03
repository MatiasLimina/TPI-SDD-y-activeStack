# horarios-atencion Specification

## Purpose
Permitir que la recepción configure las franjas de atención de cada profesional por día de la semana (varias por día), en hora local `America/Argentina/Buenos_Aires`, para que la agenda no dé turnos fuera de horario (RN-HB-01, US-002).

## Requirements

### Requirement: Alta de una franja de atención
El sistema SHALL exponer `POST /profesionales/{id}/horarios` con `dia_semana` (0 = lunes … 6 = domingo), `hora_inicio` y `hora_fin` en hora local sin zona horaria. Una franja válida MUST persistirse y responder `201` con `id`, `profesional_id`, `dia_semana`, `hora_inicio` y `hora_fin`. Un profesional MUST poder tener varias franjas el mismo día (RN-HB-01).

#### Scenario: Franja de la mañana creada
- **GIVEN** dado el profesional A activo sin franjas y una recepcionista autenticada
- **WHEN** cuando envía `POST /profesionales/{id de A}/horarios` con `{"dia_semana": 0, "hora_inicio": "09:00", "hora_fin": "13:00"}`
- **THEN** entonces la respuesta es `201` con `profesional_id` igual al id de A, `dia_semana = 0`, `hora_inicio = "09:00:00"` y `hora_fin = "13:00:00"`, y en la base existe esa franja

#### Scenario: Mañana y tarde el mismo día
- **GIVEN** dado el profesional A con la franja del lunes de 09:00 a 13:00
- **WHEN** cuando una recepcionista autenticada crea para A la franja del lunes de 14:00 a 18:00
- **THEN** entonces la respuesta es `201` y A tiene dos franjas el lunes

#### Scenario: Profesional del path inexistente
- **WHEN** cuando una recepcionista autenticada envía `POST /profesionales/{id}/horarios` con un body válido y un UUID que no corresponde a ningún profesional
- **THEN** entonces la respuesta es `404` con `{"detail": {"codigo": "recurso_inexistente", "recurso": "profesional"}}` y no se persiste ninguna franja

#### Scenario: Franja para un profesional desactivado
- **GIVEN** dado el profesional A desactivado
- **WHEN** cuando una recepcionista autenticada le crea la franja del martes de 09:00 a 13:00
- **THEN** entonces la respuesta es `201` y la franja queda persistida

### Requirement: Validación de la franja
Una franja MUST cumplir: `dia_semana` entero entre 0 y 6; `hora_fin` estrictamente mayor que `hora_inicio` en el mismo día (sin cruzar la medianoche); ambas horas alineadas a 5 minutos (minutos múltiplo de 5, segundos y fracciones en cero) y sin zona horaria. Cualquier violación MUST responder `422` con código `franja_invalida` sin persistir ni modificar franjas (RN-HB-01, DD-27).

#### Scenario: Fin igual al inicio
- **WHEN** cuando una recepcionista autenticada crea una franja con `hora_inicio = "09:00"` y `hora_fin = "09:00"`
- **THEN** entonces la respuesta es `422` con código `franja_invalida` y no se persiste ninguna franja

#### Scenario: Fin anterior al inicio
- **WHEN** cuando una recepcionista autenticada crea una franja con `hora_inicio = "22:00"` y `hora_fin = "02:00"`
- **THEN** entonces la respuesta es `422` con código `franja_invalida` y no se persiste ninguna franja

#### Scenario: Día de la semana fuera de rango
- **WHEN** cuando una recepcionista autenticada crea una franja con `dia_semana = 7`, o con `dia_semana = -1`
- **THEN** entonces cada respuesta es `422` con código `franja_invalida` y no se persiste ninguna franja

#### Scenario: Hora fuera de la grilla de 5 minutos
- **WHEN** cuando una recepcionista autenticada crea una franja con `hora_inicio = "09:07"`, o con `hora_fin = "13:00:30"`
- **THEN** entonces cada respuesta es `422` con código `franja_invalida` y no se persiste ninguna franja

#### Scenario: Hora con zona horaria
- **WHEN** cuando una recepcionista autenticada crea una franja con `hora_inicio = "09:00-03:00"`
- **THEN** entonces la respuesta es `422` con código `franja_invalida` y no se persiste ninguna franja

#### Scenario: Campo faltante o con tipo inválido
- **WHEN** cuando una recepcionista autenticada crea una franja sin `hora_fin`, o con `hora_inicio = "nueve"`
- **THEN** entonces cada respuesta es `422` y no se persiste ninguna franja

### Requirement: Franjas superpuestas del mismo profesional
Dos franjas del mismo profesional y el mismo `dia_semana` MUST NOT superponerse, con el criterio de intervalos semiabiertos `[hora_inicio, hora_fin)`: una franja que empieza justo cuando termina otra es válida. Una superposición MUST responder `409` con `{"detail": {"codigo": "franja_superpuesta"}}` sin persistir ni modificar franjas. Franjas de otro día u otro profesional no cuentan (RN-HB-01, DD-27).

#### Scenario: Franja superpuesta rechazada
- **GIVEN** dado el profesional A con la franja del lunes de 09:00 a 13:00
- **WHEN** cuando una recepcionista autenticada le crea la franja del lunes de 12:00 a 15:00
- **THEN** entonces la respuesta es `409` con código `franja_superpuesta` y A sigue con una sola franja el lunes

#### Scenario: Franja contenida en otra rechazada
- **GIVEN** dado el profesional A con la franja del lunes de 09:00 a 13:00
- **WHEN** cuando una recepcionista autenticada le crea la franja del lunes de 10:00 a 11:00
- **THEN** entonces la respuesta es `409` con código `franja_superpuesta`

#### Scenario: Franja contigua aceptada
- **GIVEN** dado el profesional A con la franja del lunes de 09:00 a 13:00
- **WHEN** cuando una recepcionista autenticada le crea la franja del lunes de 13:00 a 17:00
- **THEN** entonces la respuesta es `201`

#### Scenario: Mismo horario en otro día u otro profesional
- **GIVEN** dado el profesional A con la franja del lunes de 09:00 a 13:00
- **WHEN** cuando una recepcionista autenticada crea la franja del martes de 09:00 a 13:00 para A, y la del lunes de 09:00 a 13:00 para el profesional B
- **THEN** entonces ambas respuestas son `201`

### Requirement: Garantía de la franja en la base de datos
La base MUST rechazar por sí misma una franja con `dia_semana` fuera de 0-6, con `hora_fin <= hora_inicio`, con una hora fuera de la grilla de 5 minutos, o superpuesta con otra del mismo profesional y día, aunque se inserte sin pasar por la API. Ante dos altas simultáneas superpuestas, una MUST responder `201` y la otra `409 franja_superpuesta` (RN-HB-01, DD-27).

#### Scenario: Inserción directa inválida rechazada
- **WHEN** cuando se inserta directamente una franja con `hora_fin` igual a `hora_inicio`, otra con `dia_semana = 7` y otra con `hora_inicio = 09:07`
- **THEN** entonces la base rechaza cada inserción con una violación de restricción

#### Scenario: Inserción directa superpuesta rechazada
- **GIVEN** dada la franja del lunes de 09:00 a 13:00 del profesional A
- **WHEN** cuando se inserta directamente para A la franja del lunes de 12:55 a 14:00
- **THEN** entonces la base rechaza la inserción con una violación de exclusión

#### Scenario: Altas simultáneas superpuestas
- **GIVEN** dado el profesional A sin franjas
- **WHEN** cuando dos recepcionistas crean a la vez para A las franjas del lunes de 09:00 a 13:00 y de 12:00 a 16:00
- **THEN** entonces una respuesta es `201`, la otra es `409` con código `franja_superpuesta`, y A tiene una sola franja el lunes

### Requirement: Consulta de las franjas de un profesional
`GET /profesionales/{id}/horarios` SHALL devolver todas las franjas del profesional ordenadas por `dia_semana` y `hora_inicio`, o una lista vacía si no tiene. Profesional inexistente → `404`; identificador mal formado → `422`. Un profesional desactivado MUST seguir consultable (RN-HB-01, DD-27).

#### Scenario: Franjas en orden
- **GIVEN** dado el profesional A con las franjas martes 09:00-13:00, lunes 14:00-18:00 y lunes 09:00-13:00
- **WHEN** cuando una recepcionista autenticada envía `GET /profesionales/{id de A}/horarios`
- **THEN** entonces la respuesta es `200` con lunes 09:00-13:00, lunes 14:00-18:00 y martes 09:00-13:00, en ese orden

#### Scenario: Profesional sin franjas
- **GIVEN** dado el profesional A sin franjas
- **WHEN** cuando una recepcionista autenticada envía `GET /profesionales/{id de A}/horarios`
- **THEN** entonces la respuesta es `200` con una lista vacía

#### Scenario: Franjas de otro profesional excluidas
- **GIVEN** dados los profesionales A y B, cada uno con una franja
- **WHEN** cuando una recepcionista autenticada envía `GET /profesionales/{id de A}/horarios`
- **THEN** entonces la respuesta contiene solo la franja de A

#### Scenario: Profesional inexistente o identificador mal formado
- **WHEN** cuando una recepcionista autenticada envía `GET /profesionales/{id}/horarios` con un UUID que no corresponde a ningún profesional, y `GET /profesionales/no-es-un-id/horarios`
- **THEN** entonces la primera respuesta es `404` con `{"detail": {"codigo": "recurso_inexistente", "recurso": "profesional"}}` y la segunda es `422`

### Requirement: Edición parcial de una franja
`PATCH /profesionales/{id}/horarios/{horario_id}` SHALL modificar `dia_semana`, `hora_inicio` u `hora_fin`; lo omitido se conserva, `null` → `422` y los campos desconocidos se ignoran. La franja resultante MUST cumplir la validación y la no superposición en su día (el nuevo, si cambia), sin compararse consigo misma; responde `200`. Profesional inexistente → `404` (`recurso` `profesional`); franja inexistente o ajena → `404` (`recurso` `horario`) (RN-HB-01, DD-27).

#### Scenario: Extender el fin de una franja
- **GIVEN** dado el profesional A con la franja del lunes de 09:00 a 13:00
- **WHEN** cuando una recepcionista autenticada envía `PATCH` sobre esa franja con `{"hora_fin": "14:00"}`
- **THEN** entonces la respuesta es `200` con lunes de 09:00 a 14:00, y en la base la franja quedó así

#### Scenario: Achicar la propia franja no choca consigo misma
- **GIVEN** dado el profesional A con la franja del lunes de 09:00 a 13:00
- **WHEN** cuando una recepcionista autenticada envía `PATCH` sobre esa franja con `{"hora_inicio": "10:00"}`
- **THEN** entonces la respuesta es `200` con lunes de 10:00 a 13:00

#### Scenario: Resultado inválido al combinar con lo conservado
- **GIVEN** dado el profesional A con la franja del lunes de 09:00 a 13:00
- **WHEN** cuando una recepcionista autenticada envía `PATCH` sobre esa franja con `{"hora_fin": "08:00"}`
- **THEN** entonces la respuesta es `422` con código `franja_invalida` y la franja sigue de 09:00 a 13:00

#### Scenario: Edición que se superpone con otra franja
- **GIVEN** dado el profesional A con las franjas del lunes de 09:00 a 13:00 y de 14:00 a 18:00
- **WHEN** cuando una recepcionista autenticada envía `PATCH` sobre la primera con `{"hora_fin": "15:00"}`
- **THEN** entonces la respuesta es `409` con código `franja_superpuesta` y ambas franjas siguen igual

#### Scenario: Mover una franja a un día donde se superpone
- **GIVEN** dado el profesional A con la franja del lunes de 09:00 a 13:00 y la del martes de 10:00 a 12:00
- **WHEN** cuando una recepcionista autenticada envía `PATCH` sobre la del lunes con `{"dia_semana": 1}`
- **THEN** entonces la respuesta es `409` con código `franja_superpuesta`, y A sigue con lunes 09:00-13:00 y martes 10:00-12:00

#### Scenario: Mover una franja a un día libre
- **GIVEN** dado el profesional A con la franja del lunes de 09:00 a 13:00 y la del martes de 10:00 a 12:00
- **WHEN** cuando una recepcionista autenticada envía `PATCH` sobre la del lunes con `{"dia_semana": 2}`
- **THEN** entonces la respuesta es `200` con `dia_semana = 2`, `hora_inicio = "09:00:00"` y `hora_fin = "13:00:00"`, y A ya no tiene franjas el lunes

#### Scenario: Nulo explícito o campo desconocido
- **GIVEN** dado el profesional A con la franja del lunes de 09:00 a 13:00
- **WHEN** cuando una recepcionista autenticada envía `PATCH` sobre esa franja con `{"hora_inicio": null}`, y después con `{"color": "azul"}`
- **THEN** entonces la primera respuesta es `422`, la segunda es `200` sin `color` en la respuesta, y la franja sigue de 09:00 a 13:00

#### Scenario: Franja de otro profesional
- **GIVEN** dada la franja F del profesional B
- **WHEN** cuando una recepcionista autenticada envía `PATCH /profesionales/{id de A}/horarios/{id de F}` con un body válido
- **THEN** entonces la respuesta es `404` con `{"detail": {"codigo": "recurso_inexistente", "recurso": "horario"}}` y F no cambia

#### Scenario: Editar una franja o un profesional inexistente
- **GIVEN** dado el profesional A con la franja F
- **WHEN** cuando una recepcionista autenticada envía `PATCH /profesionales/{id de A}/horarios/{id}` con un body válido y un UUID que no corresponde a ninguna franja, y `PATCH /profesionales/{id}/horarios/{id de F}` con un body válido y un UUID que no corresponde a ningún profesional
- **THEN** entonces la primera respuesta es `404` con `{"detail": {"codigo": "recurso_inexistente", "recurso": "horario"}}`, la segunda es `404` con `{"detail": {"codigo": "recurso_inexistente", "recurso": "profesional"}}`, y F no cambia

### Requirement: Borrado de una franja
`DELETE /profesionales/{id}/horarios/{horario_id}` SHALL eliminar la franja y responder `204` sin cuerpo. Franja inexistente o de otro profesional → `404` con `recurso = "horario"`; profesional inexistente → `404` con `recurso = "profesional"` (RN-HB-01, DD-27).

#### Scenario: Franja borrada
- **GIVEN** dado el profesional A con las franjas del lunes de 09:00 a 13:00 y de 14:00 a 18:00
- **WHEN** cuando una recepcionista autenticada borra la de 14:00 a 18:00
- **THEN** entonces la respuesta es `204` y `GET /profesionales/{id de A}/horarios` devuelve solo la de 09:00 a 13:00

#### Scenario: Borrar una franja inexistente
- **WHEN** cuando una recepcionista autenticada envía `DELETE /profesionales/{id de A}/horarios/{id}` con un UUID que no corresponde a ninguna franja
- **THEN** entonces la respuesta es `404` con `{"detail": {"codigo": "recurso_inexistente", "recurso": "horario"}}`

#### Scenario: Borrar sobre un profesional inexistente
- **GIVEN** dado el profesional A con la franja F
- **WHEN** cuando una recepcionista autenticada envía `DELETE /profesionales/{id}/horarios/{id de F}` con un UUID que no corresponde a ningún profesional
- **THEN** entonces la respuesta es `404` con `{"detail": {"codigo": "recurso_inexistente", "recurso": "profesional"}}` y F sigue existiendo

### Requirement: Los cambios de horario no alteran los turnos existentes
Editar o borrar una franja MUST NOT modificar, cancelar ni borrar turnos ya registrados, aunque queden fuera del horario vigente: conservan su horario y estado y un turno `programado` futuro MUST poder cancelarse. Reprogramarlo MUST validar el horario vigente (requisito "Misma validación que el alta al reprogramar" de `agenda-turnos`) (RN-AG-08, DD-27).

#### Scenario: Turno intacto tras borrar su franja
- **GIVEN** dado un turno `programado` futuro del profesional A el lunes de 10:00 a 10:45, dentro de la franja del lunes de 09:00 a 13:00
- **WHEN** cuando una recepcionista autenticada borra esa franja
- **THEN** entonces la respuesta es `204` y en la base el turno sigue `programado` de 10:00 a 10:45

#### Scenario: Cancelar un turno que quedó fuera de horario
- **GIVEN** dado un turno `programado` futuro del lunes de 12:30 a 13:15 y su franja editada a lunes de 09:00 a 12:00
- **WHEN** cuando una recepcionista autenticada envía `POST /turnos/{id}/cancelar`
- **THEN** entonces la respuesta es `200` con `estado = cancelado`

### Requirement: Escritura de franjas reservada a la recepcionista
Alta, edición y borrado de franjas MUST exigir un usuario autenticado con rol `recepcionista` (RN-HB-01, RN-AU-03). Un `odontologo` MUST recibir `403` con `{"detail": {"codigo": "rol_insuficiente", "mensaje": "Rol insuficiente"}}`, también sobre su propio profesional. Autenticación y rol MUST evaluarse antes que el body y que la existencia del path; ante `401` o `403` nada cambia.

#### Scenario: Odontólogo no puede escribir sus franjas
- **GIVEN** dado un odontólogo autenticado vinculado al profesional A, que tiene la franja F
- **WHEN** cuando envía `POST /profesionales/{id de A}/horarios` con un body válido, `PATCH` sobre F con `{"hora_fin": "14:00"}` y `DELETE` sobre F
- **THEN** entonces cada respuesta es `403` con código `rol_insuficiente`, y A sigue con la franja F sin cambios y sin franjas nuevas

#### Scenario: Sin token en la escritura
- **GIVEN** dado el profesional A con la franja F
- **WHEN** cuando se envían sin encabezado `Authorization` `POST /profesionales/{id de A}/horarios` con un body válido, `PATCH` sobre F con `{"hora_fin": "14:00"}` y `DELETE` sobre F
- **THEN** entonces cada respuesta es `401` con `WWW-Authenticate: Bearer` y `{"detail": {"codigo": "no_autenticado", "mensaje": "No autenticado"}}`, y A sigue con la franja F sin cambios y sin franjas nuevas

#### Scenario: Rol evaluado antes que el body y que el path
- **GIVEN** dado un odontólogo autenticado
- **WHEN** cuando envía `POST /profesionales/{id de A}/horarios` con `{"dia_semana": 9}`, y `DELETE /profesionales/{id}/horarios/{id}` con UUIDs que no corresponden a nada
- **THEN** entonces ambas respuestas son `403`, no `422` ni `404`

### Requirement: Lectura de franjas según el rol
La consulta MUST exigir un usuario autenticado (sin token → `401` antes que validar el path). La `recepcionista` consulta las franjas de cualquier profesional; el `odontologo` solo las de su profesional (matriz de `03_actores_y_roles.md`): sobre otro → `403 profesional_ajeno`, antes que la existencia del profesional. Un id mal formado → `422` para ambos roles, antes que `profesional_ajeno` (DD-27).

#### Scenario: Odontólogo consulta sus franjas
- **GIVEN** dado un odontólogo autenticado vinculado al profesional A, que tiene la franja del lunes de 09:00 a 13:00
- **WHEN** cuando envía `GET /profesionales/{id de A}/horarios`
- **THEN** entonces la respuesta es `200` con esa franja

#### Scenario: Odontólogo no consulta franjas ajenas
- **GIVEN** dado un odontólogo autenticado vinculado al profesional A, y el profesional B
- **WHEN** cuando envía `GET /profesionales/{id de B}/horarios`, y `GET /profesionales/{id}/horarios` con un UUID que no corresponde a ningún profesional
- **THEN** entonces ambas respuestas son `403` con `{"detail": {"codigo": "profesional_ajeno", "mensaje": "Solo podés consultar tu propio horario"}}`

#### Scenario: Odontólogo con identificador mal formado
- **GIVEN** dado un odontólogo autenticado vinculado al profesional A
- **WHEN** cuando envía `GET /profesionales/no-es-un-id/horarios`
- **THEN** entonces la respuesta es `422`, no `403`

#### Scenario: Sin token en la lectura
- **WHEN** cuando se envía `GET /profesionales/no-es-un-id/horarios` sin encabezado `Authorization`
- **THEN** entonces la respuesta es `401` con `WWW-Authenticate: Bearer`, no `422`
