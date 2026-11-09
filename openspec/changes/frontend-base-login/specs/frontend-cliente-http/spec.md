# Spec Delta

## Purpose

Define cómo la SPA se comunica con la API: de dónde sale la URL base, cómo viaja el token y cómo se presentan de forma uniforme a las pantallas todas las formas de error que la API y la red pueden producir.

## ADDED Requirements

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
Ante un error con cuerpo `{"detail": {"codigo": ...}}`, el cliente SHALL lanzar un error con `status`, `codigo` y `mensaje`, y MUST conservar los demás campos de `detail`. Si `detail` no trae `mensaje`, MUST usar un mensaje genérico en español, porque varios errores reales de la API solo traen `codigo`.

#### Scenario: Con código y mensaje
- **GIVEN** dada una respuesta `403` con `{"detail": {"codigo": "rol_insuficiente", "mensaje": "Rol insuficiente"}}`
- **WHEN** cuando se completa el pedido
- **THEN** entonces el error tiene `status` `403`, `codigo` `rol_insuficiente` y `mensaje` `Rol insuficiente`

#### Scenario: Con campos adicionales y sin mensaje
- **GIVEN** dada una respuesta `409` con `{"detail": {"codigo": "solapamiento", "recursos": ["profesional", "sillon"]}}`
- **WHEN** cuando se completa el pedido
- **THEN** entonces el error tiene `codigo` `solapamiento`, un `mensaje` genérico no vacío y conserva `recursos` con esos dos valores

### Requirement: Error de validación de la API
Ante un `422` cuyo `detail` es una lista, el cliente SHALL lanzar un error con `codigo` `validacion`, un `mensaje` genérico y una lista de errores por campo. El campo MUST ser el último tramo de `loc`, sin el origen `body` o `query`, y MUST conservar el texto de `msg`.

#### Scenario: Campo del body
- **GIVEN** dada una respuesta `422` con `{"detail": [{"type": "missing", "loc": ["body", "password"], "msg": "Field required"}]}`
- **WHEN** cuando se completa el pedido
- **THEN** entonces el error tiene `status` `422`, `codigo` `validacion` y un error del campo `password` con el mensaje `Field required`

#### Scenario: Parámetro de la consulta
- **GIVEN** dada una respuesta `422` con `{"detail": [{"type": "date_from_datetime_parsing", "loc": ["query", "desde"], "msg": "Input should be a valid date"}]}`
- **WHEN** cuando se completa el pedido
- **THEN** entonces el error incluye un error del campo `desde`

### Requirement: Otras fallas
El cliente SHALL lanzar el mismo tipo de error, con `codigo` nulo y un `mensaje` genérico en español, ante un `detail` de texto o un cuerpo no JSON, conservando el `status`. Ante una falla de red MUST lanzarlo con `status` `0` y un `mensaje` que indique que no se pudo conectar. Nunca MUST mostrar al usuario el texto crudo del servidor.

#### Scenario: Detail de texto
- **GIVEN** dada una respuesta `404` con `{"detail": "Not Found"}`
- **WHEN** cuando se completa el pedido
- **THEN** entonces el error tiene `status` `404`, `codigo` nulo y un `mensaje` genérico que no es `Not Found`

#### Scenario: Cuerpo que no es JSON
- **GIVEN** dada una respuesta `500` con el cuerpo de texto `Internal Server Error`
- **WHEN** cuando se completa el pedido
- **THEN** entonces el error tiene `status` `500`, `codigo` nulo y un `mensaje` genérico

#### Scenario: Falla de red
- **GIVEN** dado que la API no es alcanzable y el pedido se rechaza antes de obtener respuesta
- **WHEN** cuando se completa el pedido
- **THEN** entonces el error tiene `status` `0` y un `mensaje` que indica que no se pudo conectar con el servidor
