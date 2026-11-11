# frontend-pacientes Specification

## Purpose
Pantalla `/pacientes`, en la que la recepcionista busca, registra, edita y desactiva pacientes desde la SPA (US-009, DD-31), sobre el contrato de `registro-pacientes`, sin exponer datos personales fuera de la pantalla.

## Requirements

### Requirement: Listado de pacientes
`/pacientes` SHALL pedir al montarse `GET /pacientes` con `limite=21` y `desplazamiento=0`, sin `q`, y mostrar hasta 20 pacientes en el orden de la API (apellido, nombre e id, DD-31 h) con su nombre como `Apellido, Nombre`, documento, teléfono, email (`Sin email` si es nulo) y estado. Sin pacientes, MUST mostrar `Todavía no hay pacientes registrados.`

#### Scenario: Primera carga
- **GIVEN** dada una recepcionista
- **WHEN** cuando navega a `/pacientes`
- **THEN** entonces se hizo `GET /pacientes` con `limite=21`, `desplazamiento=0` y sin `q`

#### Scenario: Datos de cada paciente
- **GIVEN** dada una respuesta con "Carla Imaginaria", documento `00000104`, teléfono `011-0000-0104` y sin email
- **WHEN** cuando se muestra el listado
- **THEN** entonces su fila muestra `Imaginaria, Carla`, `00000104`, `011-0000-0104` y `Sin email`

#### Scenario: Sin pacientes
- **GIVEN** dada una respuesta `200` con `[]` y la búsqueda vacía
- **WHEN** cuando termina la carga
- **THEN** entonces se ve `Todavía no hay pacientes registrados.`

### Requirement: Búsqueda de pacientes
El campo `Buscar` (`type="search"`, `maxLength` 100) SHALL pedir `GET /pacientes` 300 ms después de la última tecla, con `q` igual al texto sin espacios en los extremos, `limite=21` y `desplazamiento=0`. Sin largo mínimo (DD-31 e). Un texto vacío o en blanco MUST pedir sin `q`. Sin resultados MUST mostrar `No se encontraron pacientes.` (design D7)

#### Scenario: Espera antes de buscar
- **GIVEN** dado el listado cargado
- **WHEN** cuando se escribe `pe` y pasan 299 ms
- **THEN** entonces no se hizo un segundo `GET /pacientes`; a los 300 ms se hizo uno con `q=pe`

#### Scenario: Un solo carácter
- **GIVEN** dado el listado cargado
- **WHEN** cuando se escribe `4` y pasan 300 ms
- **THEN** entonces se hizo `GET /pacientes` con `q=4`

#### Scenario: Texto en blanco
- **GIVEN** dada una búsqueda activa `pe`
- **WHEN** cuando se reemplaza por `   ` y pasan 300 ms
- **THEN** entonces el último `GET /pacientes` no incluye `q`

#### Scenario: Sin resultados
- **GIVEN** dada una búsqueda `zzz` y una respuesta `200` con `[]`
- **WHEN** cuando termina la carga
- **THEN** entonces se ve `No se encontraron pacientes.`

#### Scenario: Búsquedas fuera de orden
- **GIVEN** dadas las búsquedas `pe` y luego `per`, con la respuesta de `pe` pendiente
- **WHEN** cuando llega la respuesta de `per` y después la de `pe`
- **THEN** entonces se ven los resultados de `per`

### Requirement: Texto buscado fuera de la URL
El texto buscado y la página SHALL vivir solo en el estado de la pantalla: la URL MUST seguir siendo `/pacientes`, sin parámetros, para que nombres y documentos no queden en el historial del navegador, en analogía con DD-31 o (design D7). Los datos de pacientes MUST NOT escribirse en la consola.

#### Scenario: URL sin la búsqueda
- **GIVEN** dada una recepcionista en `/pacientes`
- **WHEN** cuando busca `Imaginaria` y avanza a la página siguiente
- **THEN** entonces la ruta es `/pacientes` y la búsqueda de la URL está vacía

#### Scenario: Consola sin datos personales
- **GIVEN** dada una búsqueda `Imaginaria` que falla por red
- **WHEN** cuando se muestra el error
- **THEN** entonces ninguna llamada a `console` incluye `Imaginaria`

### Requirement: Paginación sin total
La API no informa el total (DD-31 h), así que la pantalla SHALL pedir 21 pacientes y mostrar 20: `Siguiente` MUST habilitarse solo si llegaron 21, y `Anterior` solo desde la segunda página. Cada página MUST pedir `desplazamiento` igual a 20 por las páginas anteriores y mostrar `Página N`. Una búsqueda nueva MUST volver a la página 1.

#### Scenario: Hay página siguiente
- **GIVEN** dada una respuesta con 21 pacientes
- **WHEN** cuando se muestra el listado
- **THEN** entonces se ven 20 filas, `Página 1`, `Siguiente` habilitado y `Anterior` deshabilitado

#### Scenario: Última página exacta
- **GIVEN** dada una respuesta con exactamente 20 pacientes
- **WHEN** cuando se muestra el listado
- **THEN** entonces se ven 20 filas y `Siguiente` está deshabilitado

#### Scenario: Avanzar y volver
- **GIVEN** dada la página 1 con `Siguiente` habilitado
- **WHEN** cuando se elige `Siguiente`, y luego `Anterior`
- **THEN** entonces se pidió `desplazamiento=20` con `Página 2`, y luego `desplazamiento=0` con `Página 1`

#### Scenario: Búsqueda desde la página 2
- **GIVEN** dada la página 2
- **WHEN** cuando se busca `pe`
- **THEN** entonces el pedido tiene `desplazamiento=0` y se ve `Página 1`

### Requirement: Alta y edición de un paciente
El formulario de paciente SHALL tener `Nombre`, `Apellido`, `Documento` y `Teléfono` obligatorios y `Email` opcional (DD-31 l, m). En el alta, un email vacío MUST omitirse; en la edición, vaciarlo MUST enviar `email: null`. El documento MUST poder editarse, también en un paciente desactivado (DD-31 i). El éxito MUST avisar `Paciente guardado.` Las acciones de cada fila MUST nombrarse con el nombre y el documento, `Editar Apellido, Nombre (documento)` y `Desactivar Apellido, Nombre (documento)`, porque el nombre puede repetirse y el documento no (DD-31 i, design D16).

#### Scenario: Alta sin email
- **GIVEN** dado el formulario `Nuevo paciente` con `Carla`, `Imaginaria`, `00000104`, `011-0000-0104` y email vacío
- **WHEN** cuando se envía y la API responde `201`
- **THEN** entonces el `POST /pacientes` tiene cuerpo `{"nombre": "Carla", "apellido": "Imaginaria", "documento": "00000104", "telefono": "011-0000-0104"}` y se ve `Paciente guardado.`

#### Scenario: Quitar el email
- **GIVEN** dada la paciente "Carla Imaginaria" con email `carla@ejemplo.test` en edición
- **WHEN** cuando se vacía el email y se envía
- **THEN** entonces el `PATCH /pacientes/{id}` tiene cuerpo `{"email": null}`

#### Scenario: Corregir el documento de un paciente desactivado
- **GIVEN** dada la paciente "Carla Imaginaria" desactivada
- **WHEN** cuando la recepcionista elige `Editar Imaginaria, Carla (00000104)`, cambia el documento a `00000105` y envía
- **THEN** entonces el `PATCH /pacientes/{id}` tiene cuerpo `{"documento": "00000105"}`

#### Scenario: Pacientes homónimos
- **GIVEN** dada una página con dos pacientes "Carla Imaginaria" activas, con documentos `00000104` y `00000105`
- **WHEN** cuando se muestra el listado
- **THEN** entonces hay exactamente un botón con cada nombre: `Editar Imaginaria, Carla (00000104)`, `Desactivar Imaginaria, Carla (00000104)`, `Editar Imaginaria, Carla (00000105)` y `Desactivar Imaginaria, Carla (00000105)`

### Requirement: Documento repetido
Un `409 recurso_duplicado` con `campo` `documento` SHALL marcar el campo `Documento` con `Ya existe un paciente con ese documento, activo o desactivado.`, porque el documento es único entre todos los pacientes (DD-31 i).

#### Scenario: Documento de un paciente desactivado
- **GIVEN** dado el formulario `Nuevo paciente` con el documento `00000104`
- **WHEN** cuando se envía y la API responde `409` con `{"detail": {"codigo": "recurso_duplicado", "campo": "documento"}}`
- **THEN** entonces el campo `Documento` muestra `Ya existe un paciente con ese documento, activo o desactivado.` y el diálogo sigue abierto

### Requirement: Desactivación de un paciente
La confirmación para desactivar un paciente SHALL decir `No va a poder recibir turnos nuevos. Sus turnos ya agendados no cambian y se pueden cancelar. No se puede reactivar.` (DD-26 g, DD-31 k). Al confirmar MUST enviar `POST /pacientes/{id}/desactivar` y avisar `Paciente desactivado.`

#### Scenario: Desactivar un paciente
- **GIVEN** dada la paciente "Carla Imaginaria" activa
- **WHEN** cuando la recepcionista elige `Desactivar Imaginaria, Carla (00000104)`, confirma y la API responde `200`
- **THEN** entonces se hizo `POST /pacientes/{id}/desactivar`, se ve `Paciente desactivado.` y se volvió a pedir la página actual con la búsqueda actual
