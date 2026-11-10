## MODIFIED Requirements

### Requirement: URL base de la API
El cliente HTTP SHALL armar cada URL con la base configurada en `VITE_API_URL` y, si la variable no está definida o está vacía (como en `docker-compose.yml`), con `http://localhost:8000`. Una barra final en la base MUST NOT producir una barra doble.

#### Scenario: URL configurada
- **GIVEN** dado `VITE_API_URL` igual a `http://api.example.test:9000`
- **WHEN** cuando se pide `/auth/login`
- **THEN** entonces el pedido va a `http://api.example.test:9000/auth/login`

#### Scenario: Sin configuración
- **GIVEN** dado que `VITE_API_URL` no está definida
- **WHEN** cuando se pide `/auth/login`
- **THEN** entonces el pedido va a `http://localhost:8000/auth/login`

#### Scenario: Variable vacía
- **GIVEN** dado `VITE_API_URL` definida con una cadena vacía
- **WHEN** cuando se pide `/auth/login`
- **THEN** entonces el pedido va a `http://localhost:8000/auth/login`

#### Scenario: Base con barra final
- **GIVEN** dado `VITE_API_URL` igual a `http://api.example.test:9000/`
- **WHEN** cuando se pide `/auth/login`
- **THEN** entonces el pedido va a `http://api.example.test:9000/auth/login`

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

#### Scenario: Conexión cortada al leer el cuerpo de un error
- **GIVEN** dada una respuesta `401` cuya conexión se corta antes de terminar de leer el cuerpo, con una sesión activa
- **WHEN** cuando se completa el pedido
- **THEN** entonces el error tiene `status` `0` y `mensaje` `No se pudo conectar con el servidor.`, y no se cierra la sesión
