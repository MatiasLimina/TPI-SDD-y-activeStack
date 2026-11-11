# frontend-gestion Specification

## Purpose
Comportamiento compartido de las pantallas de gestión de la SPA (recursos, horarios, pacientes y bloqueos): carga de listados, formularios en diálogo, confirmaciones, relectura tras escribir y manejo uniforme de los errores de la API.

## Requirements

### Requirement: Carga de un listado
Cada pantalla de gestión SHALL pedir su listado al montarse e indicar la carga con un texto de estado. Un listado vacío MUST mostrar un mensaje propio de la pantalla, y una lista con elementos MUST mostrarse como una tabla con encabezados de columna (design D4).

#### Scenario: Carga en curso
- **GIVEN** dada una recepcionista y un `GET /sillones` que todavía no respondió
- **WHEN** cuando navega a `/configuracion/sillones`
- **THEN** entonces se ve `Cargando…` con rol `status` y no se ve la tabla

#### Scenario: Listado con elementos
- **GIVEN** dada una respuesta de `GET /sillones` con "Sillón 1" y "Sillón 2"
- **WHEN** cuando termina la carga
- **THEN** entonces no se ve `Cargando…` y hay una tabla con encabezados de columna y una fila por sillón

#### Scenario: Listado vacío
- **GIVEN** dada una respuesta `200` de `GET /sillones` con `[]`
- **WHEN** cuando termina la carga
- **THEN** entonces se ve `Todavía no hay sillones cargados.` y no hay tabla

### Requirement: Errores al cargar un listado
Si falla la carga de un listado, la pantalla SHALL mostrar un error con rol `alert` y un botón `Reintentar` que repite el pedido. Un `403` MUST mostrar `No tenés permiso para ver esta información.` sin cerrar la sesión; un `401 no_autenticado` lo resuelve la sesión, que se cierra con el aviso de sesión vencida (DD-33 d, spec `frontend-sesion`); cualquier otro error MUST mostrar el `mensaje` del error del cliente HTTP (DD-33 e).

#### Scenario: Falla de red y reintento
- **GIVEN** dada una recepcionista y un `GET /sillones` que falla por red
- **WHEN** cuando termina la carga, y luego elige `Reintentar` y la API responde `200`
- **THEN** entonces primero se ve `No se pudo conectar con el servidor.` con `Reintentar`, y después la tabla de sillones sin el error

#### Scenario: Rol desactualizado al cargar
- **GIVEN** dada una sesión de `recepcionista` y un `GET /sillones` que responde `403` con código `rol_insuficiente`
- **WHEN** cuando termina la carga
- **THEN** entonces se ve `No tenés permiso para ver esta información.`, el token sigue guardado y la URL no cambia

#### Scenario: Error del servidor
- **GIVEN** dado un `GET /sillones` que responde `500` sin cuerpo JSON
- **WHEN** cuando termina la carga
- **THEN** entonces se ve `Ocurrió un error. Intentá de nuevo.` con `Reintentar`

#### Scenario: Sesión vencida al cargar
- **GIVEN** dada una recepcionista y un `GET /sillones` que responde `401` con código `no_autenticado` para el token de la sesión actual
- **WHEN** cuando navega a `/configuracion/sillones`
- **THEN** entonces el token se elimina y se muestra `/login` con el aviso de sesión vencida, sin el error del listado

### Requirement: Respuestas fuera de orden
Cuando una pantalla pide de nuevo un listado antes de recibir la respuesta anterior (por un cambio de filtro, una búsqueda o una relectura), SHALL mostrarse solo la respuesta del último pedido. Una respuesta o un error de un pedido anterior MUST descartarse.

#### Scenario: La respuesta vieja llega después
- **GIVEN** dada la sección de horarios con el pedido de las franjas del profesional A pendiente
- **WHEN** cuando se elige el profesional B, llega la respuesta de B y después la de A
- **THEN** entonces se ven las franjas de B y no las de A

#### Scenario: Error de un pedido viejo
- **GIVEN** dada la sección de horarios con el pedido de las franjas del profesional A pendiente
- **WHEN** cuando se elige el profesional B, llega la respuesta `200` de B y después A falla por red
- **THEN** entonces se ven las franjas de B y no se ve ningún error

### Requirement: Formularios en diálogo
El alta y la edición SHALL hacerse en un formulario dentro de un diálogo modal con título, con `noValidate` (la API decide las reglas de negocio, DD-34 P8), un botón de envío y un botón `Volver` que cierra sin pedidos. MUST haber un solo diálogo abierto a la vez (DD-34 P15). La edición MUST abrir con los valores actuales cargados.

#### Scenario: Alta abre un formulario vacío
- **GIVEN** dada la pantalla de profesionales cargada
- **WHEN** cuando la recepcionista elige `Nuevo profesional`
- **THEN** entonces se abre un diálogo modal titulado `Nuevo profesional`, con los campos vacíos y sin pedidos a la API

#### Scenario: Edición con los valores actuales
- **GIVEN** dado el profesional "Ana Ficticia" con matrícula "MN-0001"
- **WHEN** cuando la recepcionista elige `Editar Ficticia, Ana`
- **THEN** entonces se abre el diálogo `Editar profesional` con `Ana`, `Ficticia` y `MN-0001` cargados

#### Scenario: Volver sin pedidos
- **GIVEN** dado el diálogo de edición de "Ana Ficticia" con el nombre modificado
- **WHEN** cuando elige `Volver`
- **THEN** entonces el diálogo se cierra, no se hizo ningún `PATCH` y la tabla muestra el nombre original

### Requirement: Campos obligatorios
Antes de enviar, el formulario SHALL comprobar que los campos obligatorios no estén vacíos ni formados solo por espacios. Cada uno vacío MUST marcarse con `Completá este campo.` asociado al control, sin hacer ningún pedido. Las demás reglas (largos, formatos, duplicados) MUST decidirlas la API (DD-34 P8, P9), salvo que la duración de una prestación sea un entero (spec `frontend-recursos`, design D15).

#### Scenario: Obligatorio vacío
- **GIVEN** dado el formulario `Nuevo profesional` con el nombre `Ana` y el apellido vacío
- **WHEN** cuando se envía
- **THEN** entonces el campo `Apellido` tiene la descripción accesible `Completá este campo.` y está marcado como inválido, y no se hizo ningún `POST /profesionales`

#### Scenario: Solo espacios
- **GIVEN** dado el formulario `Nuevo sillón` con el nombre `   `
- **WHEN** cuando se envía
- **THEN** entonces el campo `Nombre` muestra `Completá este campo.` y no se hizo ningún `POST /sillones`

#### Scenario: Opcional vacío
- **GIVEN** dado el formulario `Nuevo profesional` con nombre `Ana`, apellido `Ficticia` y matrícula vacía
- **WHEN** cuando se envía y la API responde `201`
- **THEN** entonces el `POST /profesionales` tiene cuerpo `{"nombre": "Ana", "apellido": "Ficticia"}`, sin `matricula`

### Requirement: Largo máximo de los textos
Cada campo de texto MUST limitar su largo con `maxLength` al de su columna en la API, para que no se pueda escribir un texto que la API rechazaría por largo (design D6).

#### Scenario: Largos de los campos
- **GIVEN** dado el formulario de cada pantalla de gestión
- **WHEN** cuando se inspeccionan sus campos de texto
- **THEN** entonces tienen `maxLength` 100 el nombre y el apellido del profesional, 30 la matrícula, 50 el nombre del sillón, 100 el nombre de la prestación, 100 el nombre y el apellido del paciente, 20 el documento, 30 el teléfono, 254 el email y 255 el motivo del bloqueo

### Requirement: Errores de validación de la API
Un `422` de validación (lista de errores) SHALL marcar con `Revisá este campo.` cada campo del formulario al que apunte un error. Un error sin campo o con un campo que el formulario no tiene MUST mostrarse como error general `Revisá los datos ingresados.` con rol `alert`. El `msg` de la API MUST NOT mostrarse (spec `frontend-cliente-http`).

#### Scenario: Error de un campo
- **GIVEN** dado el formulario `Nuevo paciente` completo
- **WHEN** cuando se envía y la API responde `422` con `detail` `[{"loc": ["body", "email"], "msg": "el email debe tener la forma algo@algo, sin espacios", "type": "value_error"}]`
- **THEN** entonces el campo `Email` muestra `Revisá este campo.` y no se ve el texto `algo@algo`

#### Scenario: Error sin campo
- **GIVEN** dado el formulario `Nuevo paciente` completo
- **WHEN** cuando se envía y la API responde `422` con `detail` `[{"loc": ["body"], "msg": "Field required", "type": "missing"}]`
- **THEN** entonces se ve `Revisá los datos ingresados.` con rol `alert`

### Requirement: Conservación de los datos ante un error
Ante cualquier error de envío, el formulario SHALL seguir abierto con todos los datos cargados y MUST permitir corregirlos y reenviar. Los errores previos MUST limpiarse al reenviar. Mientras un envío está en curso, el botón de envío MUST estar deshabilitado.

#### Scenario: Datos conservados tras un duplicado
- **GIVEN** dado el formulario `Nuevo sillón` con el nombre `Sillón 1`
- **WHEN** cuando se envía y la API responde `409` con código `recurso_duplicado` y `campo` `nombre`
- **THEN** entonces el diálogo sigue abierto y el campo `Nombre` sigue con `Sillón 1`

#### Scenario: Reenvío corregido
- **GIVEN** dado el formulario `Nuevo sillón` con un error de duplicado en pantalla
- **WHEN** cuando se cambia el nombre a `Sillón 3`, se reenvía y la API responde `201`
- **THEN** entonces hubo un segundo `POST /sillones`, el error ya no se ve y el diálogo se cierra

#### Scenario: Doble envío
- **GIVEN** dado el formulario `Nuevo sillón` completo y un `POST /sillones` que todavía no respondió
- **WHEN** cuando se intenta enviar de nuevo
- **THEN** entonces el botón de envío está deshabilitado y hubo un solo `POST /sillones`

### Requirement: Edición parcial
La edición SHALL enviar en el `PATCH` solo los campos cuyo valor, sin espacios en los extremos, difiere del actual, porque la API conserva lo omitido (DD-26 j, DD-31 i). Un campo opcional vaciado MUST enviarse como `null`. Sin cambios, MUST mostrar `No hiciste cambios.` sin hacer ningún pedido, como la reprogramación de turnos (DD-34 i).

#### Scenario: Solo el campo cambiado
- **GIVEN** dado el profesional "Ana Ficticia" con matrícula "MN-0001" en edición
- **WHEN** cuando se cambia el apellido a `Ficticia Segunda` y se envía
- **THEN** entonces el `PATCH /profesionales/{id}` tiene cuerpo `{"apellido": "Ficticia Segunda"}`

#### Scenario: Opcional vaciado
- **GIVEN** dado el profesional "Ana Ficticia" con matrícula "MN-0001" en edición
- **WHEN** cuando se borra la matrícula y se envía
- **THEN** entonces el `PATCH /profesionales/{id}` tiene cuerpo `{"matricula": null}`

#### Scenario: Sin cambios
- **GIVEN** dado el profesional "Ana Ficticia" en edición
- **WHEN** cuando se agrega un espacio al final del nombre y se envía
- **THEN** entonces se ve `No hiciste cambios.` con rol `status`, el diálogo sigue abierto y no se hizo ningún `PATCH`

### Requirement: Confirmación de acciones destructivas
Desactivar un recurso o un paciente y borrar una franja o un bloqueo SHALL pedir confirmación en un diálogo que nombra el elemento y explica la consecuencia, con un botón de confirmación y `Volver`. `Volver` MUST cerrar sin pedidos. Un error MUST mostrarse en el mismo diálogo, que sigue abierto.

#### Scenario: Confirmar una desactivación
- **GIVEN** dado el sillón "Sillón 1" activo
- **WHEN** cuando la recepcionista elige `Desactivar Sillón 1` y luego `Confirmar desactivación`
- **THEN** entonces se hizo un `POST /sillones/{id}/desactivar` y el diálogo se cierra

#### Scenario: Volver sin desactivar
- **GIVEN** dado el diálogo de confirmación para desactivar "Sillón 1"
- **WHEN** cuando se elige `Volver`
- **THEN** entonces el diálogo se cierra y no se hizo ningún pedido de desactivación

#### Scenario: Error en la confirmación
- **GIVEN** dado el diálogo de confirmación para desactivar "Sillón 1"
- **WHEN** cuando se confirma y el pedido falla por red
- **THEN** entonces el diálogo sigue abierto y muestra `No se pudo conectar con el servidor.`

### Requirement: Relectura y aviso tras una escritura
Tras un alta, una edición, una desactivación o un borrado exitosos, el diálogo SHALL cerrarse, MUST mostrarse un aviso con rol `status` y el listado MUST volver a pedirse a la API, sin caché local (DD-34 k). Si la relectura falla, el aviso MUST seguir visible y el listado MUST mostrar el error de carga con `Reintentar`, como en "Errores al cargar un listado", porque la escritura ya se hizo.

#### Scenario: Alta exitosa
- **GIVEN** dado el formulario `Nuevo sillón` con el nombre `Sillón 3`
- **WHEN** cuando se envía y la API responde `201`
- **THEN** entonces el diálogo se cierra, se ve `Sillón guardado.` con rol `status` y hubo un segundo `GET /sillones`

#### Scenario: El listado refleja la API
- **GIVEN** dada una desactivación exitosa de "Sillón 1" y un segundo `GET /sillones` que lo devuelve con `activo = false`
- **WHEN** cuando llega la relectura
- **THEN** entonces la fila de "Sillón 1" muestra `Inactivo`

#### Scenario: Relectura fallida
- **GIVEN** dado el formulario `Nuevo sillón` con el nombre `Sillón 3` y un segundo `GET /sillones` que falla por red
- **WHEN** cuando se envía, la API responde `201` y falla la relectura
- **THEN** entonces el diálogo está cerrado, se ve `Sillón guardado.` con rol `status` y `No se pudo conectar con el servidor.` con `Reintentar`, y no hubo un segundo `POST /sillones`

### Requirement: Registro que ya no existe
Un `404` con código `recurso_inexistente` al editar, desactivar o borrar SHALL mostrar `Este registro ya no existe.` como error general, MUST deshabilitar el envío o la confirmación y MUST volver a pedir el listado.

#### Scenario: Recurso borrado por otro usuario
- **GIVEN** dado el diálogo de edición de "Sillón 2"
- **WHEN** cuando se envía y la API responde `404` con `{"detail": {"codigo": "recurso_inexistente", "recurso": "sillon"}}`
- **THEN** entonces se ve `Este registro ya no existe.`, el botón de envío está deshabilitado y hubo un segundo `GET /sillones`

### Requirement: Falta de permiso y fallas de red al escribir
Al escribir, un `403` SHALL mostrar `No tenés permiso para esta operación.` sin cerrar la sesión (DD-33 e), y una falla de red o un error sin `codigo` MUST mostrar el `mensaje` del error. Ambos MUST conservar el diálogo abierto. Un `401 no_autenticado` MUST resolverlo la sesión (DD-33 d).

#### Scenario: Rol desactualizado
- **GIVEN** dada una sesión con rol `recepcionista` en el token y un `POST /sillones` que responde `403` con código `rol_insuficiente`
- **WHEN** cuando se recibe la respuesta
- **THEN** entonces se ve `No tenés permiso para esta operación.`, el token sigue guardado y el diálogo sigue abierto

#### Scenario: Sesión vencida en el servidor
- **GIVEN** dado un `POST /sillones` que responde `401` con código `no_autenticado` para el token de la sesión actual
- **WHEN** cuando se recibe la respuesta
- **THEN** entonces la sesión se cierra con el aviso de sesión vencida y se muestra `/login`

### Requirement: Recursos inactivos en los listados
Un registro inactivo SHALL mostrarse en el listado con el texto `Inactivo` y MUST NOT ofrecer la acción de desactivar, porque la API no permite reactivar (DD-26 d, DD-31 k). La edición MUST seguir disponible.

#### Scenario: Sillón inactivo
- **GIVEN** dado el sillón "Sillón 2" con `activo = false`
- **WHEN** cuando se muestra el listado
- **THEN** entonces su fila muestra `Inactivo`, ofrece `Editar Sillón 2` y no ofrece `Desactivar Sillón 2` ni ninguna acción de reactivar

### Requirement: Accesibilidad de las pantallas de gestión
Cada pantalla SHALL tener un título de nivel 1, los botones de acción de cada fila MUST tener un nombre accesible que incluya el registro y lo distinga de las demás filas (`Editar Sillón 1`; el documento en pacientes y el profesional y el horario en bloqueos, design D16), salvo en dos casos que la API admite y D16 acepta: dos profesionales homónimos sin matrícula y dos bloqueos del mismo profesional con el mismo `Desde` y `Hasta`, que comparten el nombre, cada campo MUST tener etiqueta, y los errores del formulario MUST tener rol `alert` o estar asociados a su control.

#### Scenario: Nombres accesibles de las acciones
- **GIVEN** dados los sillones "Sillón 1" y "Sillón 2" activos
- **WHEN** cuando se muestra el listado
- **THEN** entonces hay botones con nombre `Editar Sillón 1`, `Desactivar Sillón 1`, `Editar Sillón 2` y `Desactivar Sillón 2`

#### Scenario: Campos etiquetados
- **GIVEN** dado el formulario `Nuevo profesional`
- **WHEN** cuando se busca cada campo por su etiqueta
- **THEN** entonces se encuentran `Nombre`, `Apellido` y `Matrícula`
