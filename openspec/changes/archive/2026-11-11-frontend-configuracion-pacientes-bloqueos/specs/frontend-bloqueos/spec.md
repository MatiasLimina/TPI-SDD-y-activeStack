## Purpose

Pantalla `/bloqueos`, en la que la recepcionista y el odontólogo consultan, crean y borran bloqueos de agenda según su rol (US-003, RN-HB-02, RN-HB-03, RN-AU-02), sobre el contrato de `bloqueos-agenda` (DD-30).

## ADDED Requirements

### Requirement: Pantalla de bloqueos para ambos roles
`/bloqueos` SHALL estar disponible para `recepcionista` y `odontologo`, y pedir al montarse `GET /profesionales`, para mostrar los nombres, y `GET /bloqueos`. Cada bloqueo MUST mostrarse con su profesional como `Apellido, Nombre` (`Profesional no disponible` si no está en el catálogo), `Desde` y `Hasta` como `DD/MM/AAAA HH:MM` en `America/Argentina/Buenos_Aires`, y su motivo, en el orden de la API (DD-30 k).

#### Scenario: Bloqueo en hora local
- **GIVEN** dada la suite en una zona horaria distinta de la del consultorio y un bloqueo de "Ana Ficticia" de `2026-11-09T18:00:00Z` a `2026-11-09T19:00:00Z` con motivo "Congreso"
- **WHEN** cuando la recepcionista navega a `/bloqueos`
- **THEN** entonces la fila muestra `Ficticia, Ana`, `09/11/2026 15:00`, `09/11/2026 16:00` y `Congreso`

#### Scenario: Profesional fuera del catálogo
- **GIVEN** dado un bloqueo de un `profesional_id` que no figura en `GET /profesionales`
- **WHEN** cuando se muestra el listado
- **THEN** entonces su fila muestra `Profesional no disponible` y no muestra el id

### Requirement: Filtro por profesional de la recepcionista
La recepcionista SHALL tener el selector `Profesional` con `Todos` y los profesionales del catálogo, incluidos los inactivos marcados `(inactivo)` (DD-30 h). El valor MUST guardarse en el parámetro `profesional` de la URL y enviarse como `profesional_id`; `Todos` MUST pedir sin `profesional_id`. Un parámetro mal formado MUST ignorarse.

#### Scenario: Todos por defecto
- **GIVEN** dada una recepcionista
- **WHEN** cuando navega a `/bloqueos`
- **THEN** entonces `Profesional` muestra `Todos` y `GET /bloqueos` no incluye `profesional_id`

#### Scenario: Filtrar por un profesional
- **GIVEN** dada la pantalla de bloqueos de una recepcionista
- **WHEN** cuando elige `Ficticia, Ana`
- **THEN** entonces la URL tiene `profesional=00000000-0000-4000-8000-0000000000a1` y se pidió `GET /bloqueos` con ese `profesional_id`

#### Scenario: Parámetro mal formado
- **GIVEN** dada una recepcionista
- **WHEN** cuando navega a `/bloqueos?profesional=no-es-un-id`
- **THEN** entonces `GET /bloqueos` no incluye `profesional_id` y `Profesional` muestra `Todos`

### Requirement: Bloqueos del odontólogo
Para la `recepcionista`, la pantalla SHALL titularse `Bloqueos`, igual que su enlace del layout. Para el `odontologo` SHALL titularse `Mis bloqueos`, MUST pedir `GET /bloqueos` sin `profesional_id` aunque la URL lo traiga (la API devuelve los de su profesional, DD-30 k) y MUST NOT ofrecer el selector de profesional ni en el filtro ni en el formulario (RN-AU-02).

#### Scenario: Odontólogo sin filtro
- **GIVEN** dada una sesión de `odontologo`
- **WHEN** cuando navega a `/bloqueos?profesional=00000000-0000-4000-8000-0000000000a2`
- **THEN** entonces se ve el título `Mis bloqueos`, `GET /bloqueos` no incluye `profesional_id` y no hay ningún selector `Profesional`

#### Scenario: Título de la recepcionista
- **GIVEN** dada una sesión de `recepcionista`
- **WHEN** cuando navega a `/bloqueos`
- **THEN** entonces el título de nivel 1 es `Bloqueos`

### Requirement: Bloqueos terminados
Un bloqueo con `fin` menor o igual al reloj SHALL ocultarse por defecto y mostrarse con la casilla `Mostrar bloqueos terminados`, sin pedido nuevo, porque `GET /bloqueos` devuelve también los pasados y no tiene rango (DD-30 k, design D8). Si todos están ocultos, MUST mostrarse `No hay bloqueos vigentes ni próximos.`; si no hay ninguno, `No hay bloqueos cargados.`

#### Scenario: Terminado oculto
- **GIVEN** dado el reloj en 2026-11-09 09:00 hora local, un bloqueo de 08:00 a 09:00 y otro de 08:30 a 09:30 de ese día
- **WHEN** cuando se muestra el listado
- **THEN** entonces se ve solo el de 08:30 a 09:30

#### Scenario: Mostrar terminados
- **GIVEN** dado el listado anterior
- **WHEN** cuando se marca `Mostrar bloqueos terminados`
- **THEN** entonces se ven ambos bloqueos y no se hizo un segundo `GET /bloqueos`

#### Scenario: Solo terminados
- **GIVEN** dado el reloj en 2026-11-09 09:00 hora local y un único bloqueo que terminó el 2026-11-08
- **WHEN** cuando se muestra el listado
- **THEN** entonces se ve `No hay bloqueos vigentes ni próximos.`

### Requirement: Alta de un bloqueo
El formulario `Nuevo bloqueo` SHALL tener `Profesional` (solo para la recepcionista, con los mismos profesionales que el filtro, inactivos incluidos y marcados `(inactivo)`, porque la API admite bloquear a un profesional desactivado: DD-30 h, spec `bloqueos-agenda` "Profesional desactivado"), `Fecha desde`, `Hora desde`, `Fecha hasta`, `Hora hasta` y `Motivo`, todos obligatorios. Las fechas MUST empezar en el día actual del consultorio y las horas MUST admitir cualquier minuto (DD-30 f). `inicio` y `fin` MUST enviarse con el desfasaje de la zona del consultorio. El éxito MUST avisar `Bloqueo creado.` Si el bloqueo creado ya terminó (`fin` de la respuesta menor o igual al reloj) y `Mostrar bloqueos terminados` está desmarcada, el aviso MUST ser `Bloqueo creado. Está oculto porque ya terminó.` y la casilla MUST NOT cambiar (design D18).

#### Scenario: Alta de la recepcionista
- **GIVEN** dado el formulario con `Ficticia, Ana`, `2026-11-12` `10:03`, `2026-11-12` `10:07` y motivo `Trámite`
- **WHEN** cuando se envía y la API responde `201`
- **THEN** entonces el `POST /bloqueos` tiene cuerpo `{"profesional_id": "00000000-0000-4000-8000-0000000000a1", "inicio": "2026-11-12T10:03:00-03:00", "fin": "2026-11-12T10:07:00-03:00", "motivo": "Trámite"}` y se ve `Bloqueo creado.`

#### Scenario: Alta del odontólogo
- **GIVEN** dada una sesión de `odontologo` y el formulario `Nuevo bloqueo` abierto
- **WHEN** cuando se completa con `2026-11-12` `10:00`, `2026-11-13` `18:00` y motivo `Congreso` y se envía
- **THEN** entonces el formulario no tiene el campo `Profesional` (RN-AU-02) y el cuerpo del `POST /bloqueos` no tiene `profesional_id`

#### Scenario: Bloqueo de un profesional inactivo
- **GIVEN** dada una recepcionista y el profesional "Luis Inventado" inactivo
- **WHEN** cuando abre `Nuevo bloqueo`, elige `Inventado, Luis (inactivo)` en `Profesional`, completa el resto y envía
- **THEN** entonces el `POST /bloqueos` tiene `profesional_id` de Luis

#### Scenario: Fechas por defecto
- **GIVEN** dado el reloj en `2026-11-10T02:00:00Z` (23:00 del 9 en el consultorio)
- **WHEN** cuando se abre `Nuevo bloqueo`
- **THEN** entonces `Fecha desde` y `Fecha hasta` valen `2026-11-09` y las horas están vacías

#### Scenario: Profesional sin elegir
- **GIVEN** dado el formulario de la recepcionista completo salvo `Profesional`
- **WHEN** cuando se envía
- **THEN** entonces `Profesional` muestra `Completá este campo.` y no se hizo ningún `POST /bloqueos`

#### Scenario: Bloqueo creado que ya terminó
- **GIVEN** dado el reloj en 2026-11-09 09:00 hora local, `Mostrar bloqueos terminados` desmarcada y el formulario con `2026-11-08` `10:00`, `2026-11-08` `12:00` y motivo `Licencia`
- **WHEN** cuando se envía y la API responde `201` con ese bloqueo
- **THEN** entonces se ve `Bloqueo creado. Está oculto porque ya terminó.`, se volvió a pedir `GET /bloqueos`, la casilla sigue desmarcada y el bloqueo no aparece en el listado

#### Scenario: Bloqueo terminado con la casilla marcada
- **GIVEN** dado el mismo reloj y el mismo formulario, con `Mostrar bloqueos terminados` marcada
- **WHEN** cuando se envía, la API responde `201` y la relectura lo devuelve
- **THEN** entonces se ve `Bloqueo creado.` y el bloqueo aparece en el listado

### Requirement: Bloqueo rechazado por la API
`422 bloqueo_invalido` SHALL mostrarse como `El bloqueo debe terminar después de empezar y tener un motivo.` (DD-30 g); `422 profesional_requerido` MUST marcar `Profesional` con `Completá este campo.`; `422 referencia_invalida` MUST marcar `Profesional` con `El profesional ya no existe.` y volver a pedir `GET /profesionales`; `403 profesional_ajeno`, como `No tenés permiso para esta operación.` sin cerrar la sesión (DD-30 a). El formulario MUST seguir abierto y conservar los datos. `profesional_requerido` y el `403` no deberían ocurrir, porque la pantalla siempre manda el profesional de la recepcionista y nunca el del odontólogo; se tratan igual por defensa (design D11).

#### Scenario: Fin igual al inicio
- **GIVEN** dado el formulario con el mismo instante en `Desde` y `Hasta`
- **WHEN** cuando se envía y la API responde `422` con código `bloqueo_invalido`
- **THEN** entonces se ve `El bloqueo debe terminar después de empezar y tener un motivo.` y los datos siguen cargados

#### Scenario: Profesional inexistente
- **GIVEN** dado el formulario de la recepcionista completo
- **WHEN** cuando se envía y la API responde `422` con `{"detail": {"codigo": "referencia_invalida", "referencia": "profesional", "motivo": "inexistente"}}`
- **THEN** entonces `Profesional` muestra `El profesional ya no existe.` y se hizo un segundo `GET /profesionales`

#### Scenario: Profesional requerido por la API
- **GIVEN** dado el formulario de la recepcionista completo
- **WHEN** cuando se envía y la API responde `422` con `{"detail": {"codigo": "profesional_requerido", "mensaje": "indicá el profesional del bloqueo"}}`
- **THEN** entonces `Profesional` muestra `Completá este campo.`, no se ve el `mensaje` de la API y el diálogo sigue abierto con los datos cargados

#### Scenario: Odontólogo rechazado al crear
- **GIVEN** dada una sesión de `odontologo` y el formulario completo
- **WHEN** cuando se envía y la API responde `403` con `{"detail": {"codigo": "profesional_ajeno", "mensaje": "Solo podés operar sobre tus propios bloqueos"}}`
- **THEN** entonces se ve `No tenés permiso para esta operación.`, el diálogo sigue abierto con los datos cargados y el token sigue guardado

### Requirement: Bloqueo sobre turnos activos
Un `409 bloqueo_con_turnos` SHALL mostrar `Hay turnos activos en ese intervalo: reprogramalos o cancelalos antes de bloquear.` y la lista de `turnos` de la respuesta, cada uno con su horario en hora local y un enlace `Ver en la agenda` a la vista diaria de su fecha y su profesional (RN-HB-03, DD-30 i). MUST NOT mostrar ids ni pedir datos de pacientes.

#### Scenario: Turnos afectados
- **GIVEN** dado el formulario de la recepcionista para "Ana Ficticia" el 2026-11-12 de 10:00 a 12:00
- **WHEN** cuando se envía y la API responde `409` con código `bloqueo_con_turnos` y `turnos` `[{"id": "00000000-0000-4000-8000-0000000000f1", "inicio": "2026-11-12T10:30:00-03:00", "fin": "2026-11-12T11:15:00-03:00"}]`
- **THEN** entonces se ve el mensaje, el turno `12/11/2026 10:30 a 11:15` y un enlace `Ver en la agenda` a `/agenda?fecha=2026-11-12&profesional=00000000-0000-4000-8000-0000000000a1`, sin el id del turno ni pedidos a `/pacientes`

#### Scenario: Enlace del odontólogo
- **GIVEN** dada una sesión de `odontologo` y la misma respuesta `409`
- **WHEN** cuando se muestra el error
- **THEN** entonces el enlace `Ver en la agenda` lleva a `/agenda?fecha=2026-11-12`, sin `profesional`

#### Scenario: Turnos afectados en días distintos
- **GIVEN** dado el formulario de la recepcionista para "Ana Ficticia" del 2026-11-12 10:00 al 2026-11-13 12:00
- **WHEN** cuando se envía y la API responde `409` con código `bloqueo_con_turnos` y `turnos` `[{"id": "00000000-0000-4000-8000-0000000000f1", "inicio": "2026-11-12T10:30:00-03:00", "fin": "2026-11-12T11:15:00-03:00"}, {"id": "00000000-0000-4000-8000-0000000000f2", "inicio": "2026-11-13T09:00:00-03:00", "fin": "2026-11-13T09:30:00-03:00"}]`
- **THEN** entonces se ven `12/11/2026 10:30 a 11:15` con un enlace `Ver en la agenda` a `/agenda?fecha=2026-11-12&profesional=00000000-0000-4000-8000-0000000000a1` y `13/11/2026 09:00 a 09:30` con un enlace a `/agenda?fecha=2026-11-13&profesional=00000000-0000-4000-8000-0000000000a1`

### Requirement: Borrado de un bloqueo
Cada bloqueo SHALL ofrecer la acción `Borrar bloqueo de Apellido, Nombre del DD/MM/AAAA HH:MM al DD/MM/AAAA HH:MM` (profesional, `Desde` y `Hasta`, con `Profesional no disponible` si no está en el catálogo), en ambos roles, para que dos bloqueos con el mismo inicio no compartan el nombre accesible (DD-30 b permite superponerlos, design D16). La confirmación MUST aclarar que el horario vuelve a admitir turnos, enviar `DELETE /bloqueos/{id}` y avisar `Bloqueo borrado.` No hay edición (DD-30 c). Un `403 profesional_ajeno` MUST mostrar `No tenés permiso para esta operación.` y volver a pedir el listado.

#### Scenario: Borrar un bloqueo
- **GIVEN** dado un bloqueo de "Ana Ficticia" del 12/11/2026 de 15:00 a 16:00
- **WHEN** cuando se elige `Borrar bloqueo de Ficticia, Ana del 12/11/2026 15:00 al 12/11/2026 16:00`, el diálogo dice `El horario vuelve a admitir turnos.`, se confirma y la API responde `204`
- **THEN** entonces se hizo el `DELETE /bloqueos/{id}`, se ve `Bloqueo borrado.` y se volvió a pedir `GET /bloqueos`

#### Scenario: Bloqueos con el mismo inicio
- **GIVEN** dada una recepcionista con `Profesional` en `Todos` y tres bloqueos del 12/11/2026: de "Ana Ficticia" de 15:00 a 16:00, de "Luis Inventado" de 15:00 a 16:00 y otro de "Ana Ficticia" de 15:00 a 17:00
- **WHEN** cuando se muestra el listado
- **THEN** entonces hay exactamente un botón con cada nombre: `Borrar bloqueo de Ficticia, Ana del 12/11/2026 15:00 al 12/11/2026 16:00`, `Borrar bloqueo de Inventado, Luis del 12/11/2026 15:00 al 12/11/2026 16:00` y `Borrar bloqueo de Ficticia, Ana del 12/11/2026 15:00 al 12/11/2026 17:00`

#### Scenario: Sin edición
- **GIVEN** dado un bloqueo en el listado
- **WHEN** cuando se buscan sus acciones
- **THEN** entonces no hay ninguna acción `Editar`

#### Scenario: Odontólogo con un bloqueo que ya no es suyo
- **GIVEN** dada una sesión de `odontologo` y la confirmación para borrar un bloqueo
- **WHEN** cuando se confirma y la API responde `403` con código `profesional_ajeno`
- **THEN** entonces se ve `No tenés permiso para esta operación.`, el token sigue guardado y se volvió a pedir `GET /bloqueos`
