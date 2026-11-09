# frontend-cliente-http Specification

## Purpose
Define cómo la SPA se comunica con la API: de dónde sale la URL base, cómo viaja el token y cómo se presentan de forma uniforme a las pantallas todas las formas de error que la API y la red pueden producir.

## Requirements

### Requirement: URL base de la API
El cliente HTTP SHALL armar cada URL con la base configurada en `VITE_API_URL` y, si la variable no está definida, con `http://localhost:8000`. Una barra final en la base MUST NOT producir una barra doble.

#### Scenario: URL configurada
- **GIVEN** dado `VITE_API_URL` igual a `http://api.example.test:9000`
- **WHEN** cuando se pide `/auth/login`
- **THEN** entonces el pedido va a `http://api.example.test:9000/auth/login`

#### Scenario: Sin configuración
- **GIVEN** dado que `VITE_API_URL` no está definida
- **WHEN** cuando se pide `/auth/login`
- **THEN** entonces el pedido va a `http://localhost:8000/auth/login`

#### Scenario: Base con barra final
- **GIVEN** dado `VITE_API_URL` igual a `http://api.example.test:9000/`
- **WHEN** cuando se pide `/auth/login`
- **THEN** entonces el pedido va a `http://api.example.test:9000/auth/login`

### Requirement: Token en cada request
Con una sesión activa, el cliente SHALL enviar `Authorization: Bearer <token>` en cada request (Flujo 1). Sin sesión MUST NOT enviar ese encabezado. El token MUST NOT viajar en la URL ni escribirse en la consola.

#### Scenario: Con sesión
- **GIVEN** dada una sesión activa con un token ficticio
- **WHEN** cuando se pide `/turnos`
- **THEN** entonces el pedido lleva `Authorization: Bearer` con ese token y la URL no lo contiene

#### Scenario: Sin sesión
- **GIVEN** dado que no hay sesión
- **WHEN** cuando se pide `/auth/login`
- **THEN** entonces el pedido no lleva el encabezado `Authorization`

#### Scenario: El token no se registra
- **GIVEN** dada una sesión activa y una respuesta `500`
- **WHEN** cuando se completa el pedido
- **THEN** entonces ninguna llamada a la consola recibe el token

### Requirement: Respuesta exitosa
Ante una respuesta `2xx`, el cliente SHALL entregar el cuerpo JSON interpretado. Una respuesta sin contenido (`204`, usada por los `DELETE` de la API) MUST resolverse sin valor y sin error.

#### Scenario: Cuerpo JSON
- **GIVEN** dada una respuesta `200` con `{"status": "ok"}`
- **WHEN** cuando se completa el pedido
- **THEN** entonces el cliente entrega ese objeto

#### Scenario: Sin contenido
- **GIVEN** dada una respuesta `204` sin cuerpo
- **WHEN** cuando se completa el pedido
- **THEN** entonces el cliente resuelve sin valor y sin lanzar un error

### Requirement: Error de negocio de la API
Ante un error cuyo `detail` es un objeto con `codigo`, el cliente SHALL lanzar un error con `status`, `codigo` y `mensaje`, y MUST conservar los demás campos de `detail`. Si `detail` no trae `mensaje`, MUST usar `Ocurrió un error. Intentá de nuevo.`, porque varios errores reales de la API solo traen `codigo`. La forma de `detail`, no el `status`, MUST decidir el tratamiento: un `422` con objeto es un error de negocio, sin errores por campo.

#### Scenario: Con código y mensaje
- **GIVEN** dada una respuesta `403` con `{"detail": {"codigo": "rol_insuficiente", "mensaje": "Rol insuficiente"}}`
- **WHEN** cuando se completa el pedido
- **THEN** entonces el error tiene `status` `403`, `codigo` `rol_insuficiente` y `mensaje` `Rol insuficiente`

#### Scenario: Con campos adicionales y sin mensaje
- **GIVEN** dada una respuesta `409` con `{"detail": {"codigo": "solapamiento", "recursos": ["profesional", "sillon"]}}`
- **WHEN** cuando se completa el pedido
- **THEN** entonces el error tiene `codigo` `solapamiento`, `mensaje` `Ocurrió un error. Intentá de nuevo.` y conserva `recursos` con esos dos valores

#### Scenario: 422 con objeto y mensaje
- **GIVEN** dada una respuesta `422` con `{"detail": {"codigo": "rango_invalido", "mensaje": "Rango inválido"}}`
- **WHEN** cuando se completa el pedido
- **THEN** entonces el error tiene `status` `422`, `codigo` `rango_invalido`, `mensaje` `Rango inválido` y ningún error por campo

#### Scenario: 422 con objeto y sin mensaje
- **GIVEN** dada una respuesta `422` con `{"detail": {"codigo": "referencia_invalida", "referencia": "sillon", "motivo": "inactiva"}}`
- **WHEN** cuando se completa el pedido
- **THEN** entonces el error tiene `codigo` `referencia_invalida`, `mensaje` `Ocurrió un error. Intentá de nuevo.`, conserva `referencia` y `motivo` y no tiene ningún error por campo

### Requirement: Error de validación de la API
Ante un `422` cuyo `detail` es una lista, el cliente SHALL lanzar un error con `codigo` `validacion`, `mensaje` `Revisá los datos ingresados.` y una entrada de error por elemento, que MUST conservar el `msg` sin garantía de que sea apto para mostrar. El `campo` de la entrada MUST ser el último tramo de `loc` si es texto y no es el origen (`loc[0]`); si no, MUST ser nulo: es un error general del formulario, no asociado a ningún campo.

#### Scenario: Campo del body
- **GIVEN** dada una respuesta `422` con `{"detail": [{"type": "missing", "loc": ["body", "password"], "msg": "Field required"}]}`
- **WHEN** cuando se completa el pedido
- **THEN** entonces el error tiene `status` `422`, `codigo` `validacion`, `mensaje` `Revisá los datos ingresados.` y un error del campo `password` con el mensaje `Field required`

#### Scenario: Parámetro de la consulta
- **GIVEN** dada una respuesta `422` con `{"detail": [{"type": "date_from_datetime_parsing", "loc": ["query", "desde"], "msg": "Input should be a valid date or datetime, input is too short"}]}`
- **WHEN** cuando se completa el pedido
- **THEN** entonces el error incluye un error del campo `desde`

#### Scenario: Error del cuerpo completo
- **GIVEN** dada una respuesta `422` con `{"detail": [{"type": "value_error", "loc": ["body"], "msg": "Value error, inicio no admite null"}]}`
- **WHEN** cuando se completa el pedido
- **THEN** entonces el error tiene `codigo` `validacion` y una única entrada con `campo` nulo y el mensaje `Value error, inicio no admite null`

#### Scenario: Posición del JSON
- **GIVEN** dada una respuesta `422` con `{"detail": [{"type": "json_invalid", "loc": ["body", 5], "msg": "JSON decode error"}]}`
- **WHEN** cuando se completa el pedido
- **THEN** entonces el error tiene `codigo` `validacion` y una única entrada con `campo` nulo y el mensaje `JSON decode error`

### Requirement: Otras fallas
El cliente SHALL lanzar el mismo tipo de error, con `codigo` nulo y `mensaje` `Ocurrió un error. Intentá de nuevo.`, ante un `detail` de texto, un JSON sin `detail` o un cuerpo no JSON (también en un `2xx`), conservando el `status`. Ante una falla de red, incluso si la conexión se corta al leer el cuerpo, MUST lanzarlo con `status` `0` y `mensaje` `No se pudo conectar con el servidor.`. El `mensaje` MUST NOT ser el `detail` de texto ni el cuerpo de la respuesta.

#### Scenario: Detail de texto
- **GIVEN** dada una respuesta `404` con `{"detail": "Not Found"}`
- **WHEN** cuando se completa el pedido
- **THEN** entonces el error tiene `status` `404`, `codigo` nulo y `mensaje` `Ocurrió un error. Intentá de nuevo.`

#### Scenario: Cuerpo que no es JSON
- **GIVEN** dada una respuesta `500` con el cuerpo de texto `Internal Server Error`
- **WHEN** cuando se completa el pedido
- **THEN** entonces el error tiene `status` `500`, `codigo` nulo y `mensaje` `Ocurrió un error. Intentá de nuevo.`

#### Scenario: Éxito con cuerpo que no es JSON
- **GIVEN** dada una respuesta `200` con el cuerpo de texto `<html>Bienvenido</html>`
- **WHEN** cuando se completa el pedido
- **THEN** entonces el error tiene `status` `200`, `codigo` nulo y `mensaje` `Ocurrió un error. Intentá de nuevo.`, y no se lanza ningún otro tipo de error

#### Scenario: JSON sin detail
- **GIVEN** dada una respuesta `503` con `{"status": "degraded", "database": "unavailable"}`
- **WHEN** cuando se completa el pedido
- **THEN** entonces el error tiene `status` `503`, `codigo` nulo y `mensaje` `Ocurrió un error. Intentá de nuevo.`

#### Scenario: Falla de red
- **GIVEN** dado que la API no es alcanzable y el pedido se rechaza antes de obtener respuesta
- **WHEN** cuando se completa el pedido
- **THEN** entonces el error tiene `status` `0` y `mensaje` `No se pudo conectar con el servidor.`

#### Scenario: Conexión cortada al leer el cuerpo
- **GIVEN** dada una respuesta `200` cuya conexión se corta antes de terminar de leer el cuerpo
- **WHEN** cuando se completa el pedido
- **THEN** entonces el error tiene `status` `0` y `mensaje` `No se pudo conectar con el servidor.`
