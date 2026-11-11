## Purpose

Sección `/configuracion/horarios`, en la que la recepcionista consulta y edita las franjas de atención de cada profesional (US-002, RN-HB-01), sobre el contrato de `horarios-atencion` (DD-27).

## ADDED Requirements

### Requirement: Elección del profesional
La sección SHALL ofrecer el selector `Profesional` con todos los profesionales de `GET /profesionales`, incluidos los inactivos marcados `(inactivo)`, porque la API admite franjas de un profesional desactivado (DD-27 j). El profesional elegido MUST guardarse en el parámetro `profesional` de la URL. Sin profesional elegido, MUST mostrar `Elegí un profesional para ver o cargar su horario.` sin pedir franjas, y el botón `Nueva franja` MUST verse deshabilitado, con ese texto como descripción accesible (design D17).

#### Scenario: Sin profesional elegido
- **GIVEN** dada una recepcionista
- **WHEN** cuando navega a `/configuracion/horarios`
- **THEN** entonces se ve `Elegí un profesional para ver o cargar su horario.` y no se hizo ningún pedido a `/profesionales/{id}/horarios`

#### Scenario: Nueva franja sin profesional
- **GIVEN** dada la sección de horarios sin profesional elegido
- **WHEN** cuando se busca el botón `Nueva franja`
- **THEN** entonces está visible y deshabilitado, con la descripción accesible `Elegí un profesional para ver o cargar su horario.`; al elegir `Ficticia, Ana` en `Profesional`, queda habilitado

#### Scenario: Profesional elegido
- **GIVEN** dada la sección de horarios con "Ana Ficticia" en el catálogo
- **WHEN** cuando elige `Ficticia, Ana` en `Profesional`
- **THEN** entonces la URL tiene `profesional=00000000-0000-4000-8000-0000000000a1` y se hizo `GET /profesionales/00000000-0000-4000-8000-0000000000a1/horarios`

#### Scenario: Profesional inactivo elegible
- **GIVEN** dado el profesional "Luis Inventado" inactivo
- **WHEN** cuando se abre el selector `Profesional`
- **THEN** entonces ofrece `Inventado, Luis (inactivo)` y se puede elegir

#### Scenario: Profesional desde la URL
- **GIVEN** dada una recepcionista
- **WHEN** cuando navega a `/configuracion/horarios?profesional=00000000-0000-4000-8000-0000000000a1`
- **THEN** entonces `Profesional` muestra `Ficticia, Ana` y se piden sus franjas

#### Scenario: Parámetro inválido o desconocido
- **GIVEN** dada una recepcionista y un catálogo sin el id `00000000-0000-4000-8000-0000000000ff`
- **WHEN** cuando navega a `/configuracion/horarios?profesional=no-es-un-id`, y luego a `/configuracion/horarios?profesional=00000000-0000-4000-8000-0000000000ff`
- **THEN** entonces en ambos casos se ve `Elegí un profesional para ver o cargar su horario.`, `Nueva franja` está deshabilitado y no se pidieron franjas

### Requirement: Franjas agrupadas por día
Las franjas del profesional SHALL mostrarse agrupadas por día de la semana, de `Lunes` a `Domingo` (`dia_semana` 0 a 6, DD-27 a), cada una como `HH:MM a HH:MM` sin segundos y sin conversión de zona, porque ya son hora local del consultorio (DD-27 b). Un día sin franjas MUST mostrar `Sin atención`.

#### Scenario: Semana con dos franjas por día
- **GIVEN** dada una respuesta con las franjas de lunes `09:00:00` a `13:00:00` y `14:00:00` a `18:00:00`
- **WHEN** cuando se muestran
- **THEN** entonces `Lunes` lista `09:00 a 13:00` y `14:00 a 18:00`, y de `Martes` a `Domingo` se ve `Sin atención`

#### Scenario: Horas sin conversión de zona
- **GIVEN** dada la suite en una zona horaria distinta de la del consultorio y una franja de miércoles de `09:00:00` a `13:00:00`
- **WHEN** cuando se muestra
- **THEN** entonces `Miércoles` lista `09:00 a 13:00`

#### Scenario: Profesional sin horario
- **GIVEN** dada una respuesta `200` con `[]`
- **WHEN** cuando se muestran las franjas
- **THEN** entonces se ve `Este profesional no tiene horario cargado: no admite turnos.` y los siete días con `Sin atención`

### Requirement: Alta de una franja
El formulario `Nueva franja` SHALL tener `Día` (de `Lunes` a `Domingo`), `Desde` y `Hasta`, los tres obligatorios, con `Desde` y `Hasta` como `<input type="time" step="300">` (pasos de 5 minutos, como ayuda: la regla la decide la API, design D9), y la ayuda `Un turno debe entrar completo en una franja: dos franjas contiguas no se suman.` (DD-27 e). MUST enviar `POST /profesionales/{id}/horarios` con `dia_semana` numérico y las horas como `HH:MM`, y avisar `Franja guardada.`

#### Scenario: Alta de franja
- **GIVEN** dado el formulario `Nueva franja` de "Ana Ficticia" con `Martes`, `09:00` y `13:00`
- **WHEN** cuando se envía y la API responde `201`
- **THEN** entonces el `POST /profesionales/{id de Ana}/horarios` tiene cuerpo `{"dia_semana": 1, "hora_inicio": "09:00", "hora_fin": "13:00"}`, se ve `Franja guardada.` y se volvieron a pedir las franjas

#### Scenario: Horas en pasos de 5 minutos
- **GIVEN** dado el formulario `Nueva franja` abierto
- **WHEN** cuando se inspeccionan `Desde` y `Hasta`
- **THEN** entonces ambos son de tipo `time` con `step` `300`

#### Scenario: Día sin elegir
- **GIVEN** dado el formulario `Nueva franja` con `Desde` y `Hasta` completos y sin día
- **WHEN** cuando se envía
- **THEN** entonces `Día` muestra `Completá este campo.` y no se hizo ningún `POST`

### Requirement: Franja rechazada por la API
`422 franja_invalida` SHALL mostrarse como error general `La franja debe terminar después de empezar, el mismo día, y en horas múltiplo de 5 minutos.`, y `409 franja_superpuesta` como `Se superpone con otra franja de ese día.` (DD-27 c, d). Ambos MUST conservar el formulario.

#### Scenario: Fin antes del inicio
- **GIVEN** dado el formulario con `Lunes`, `22:00` y `02:00`
- **WHEN** cuando se envía y la API responde `422` con código `franja_invalida`
- **THEN** entonces se ve `La franja debe terminar después de empezar, el mismo día, y en horas múltiplo de 5 minutos.` y los datos siguen cargados

#### Scenario: Franja superpuesta
- **GIVEN** dada la franja de lunes de 09:00 a 13:00 y el formulario con `Lunes`, `12:00` y `15:00`
- **WHEN** cuando se envía y la API responde `409` con `{"detail": {"codigo": "franja_superpuesta"}}`
- **THEN** entonces se ve `Se superpone con otra franja de ese día.` con rol `alert`

### Requirement: Edición de una franja
Cada franja SHALL ofrecer la acción `Editar <día> HH:MM a HH:MM`, con el día en minúscula como en el borrado (`Editar lunes 09:00 a 13:00`), que MUST abrir el formulario `Editar franja` con su día y sus horas como `HH:MM`, y enviar `PATCH /profesionales/{id}/horarios/{horario_id}` solo con lo que cambió (spec `frontend-gestion`).

#### Scenario: Cambio de la hora de fin
- **GIVEN** dada la franja de lunes de `09:00:00` a `13:00:00`
- **WHEN** cuando se elige `Editar lunes 09:00 a 13:00`, el formulario muestra `Lunes`, `09:00` y `13:00`, se cambia `Hasta` a `12:00` y se envía
- **THEN** entonces el `PATCH` tiene cuerpo `{"hora_fin": "12:00"}`

#### Scenario: Cambio de día
- **GIVEN** dada la franja de lunes de 09:00 a 13:00 en edición
- **WHEN** cuando se cambia `Día` a `Viernes` y se envía
- **THEN** entonces el `PATCH` tiene cuerpo `{"dia_semana": 4}`

### Requirement: Borrado de una franja
`Borrar` en una franja SHALL pedir confirmación nombrando el día y las horas y aclarando que los turnos ya agendados no cambian (DD-27 g), y al confirmar MUST enviar `DELETE /profesionales/{id}/horarios/{horario_id}` y avisar `Franja borrada.`

#### Scenario: Borrar una franja
- **GIVEN** dada la franja de lunes de 14:00 a 18:00 de "Ana Ficticia"
- **WHEN** cuando elige `Borrar lunes 14:00 a 18:00`, el diálogo dice `Los turnos ya agendados no cambian.`, confirma y la API responde `204`
- **THEN** entonces se hizo el `DELETE`, se ve `Franja borrada.` y se volvieron a pedir las franjas

#### Scenario: Franja ya borrada
- **GIVEN** dada la confirmación para borrar una franja
- **WHEN** cuando se confirma y la API responde `404` con `{"detail": {"codigo": "recurso_inexistente", "recurso": "horario"}}`
- **THEN** entonces se ve `Este registro ya no existe.` y se volvieron a pedir las franjas
