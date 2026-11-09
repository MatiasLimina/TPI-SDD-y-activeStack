# Spec Delta

## ADDED Requirements

### Requirement: Orígenes CORS restringidos
La API SHALL aceptar pedidos de navegador solo desde los orígenes listados en `CORS_ORIGINS`, permitiendo los métodos `GET`, `POST`, `PATCH` y `DELETE` y los encabezados `Authorization` y `Content-Type`, sin credenciales de cookie (08 §Seguridad). A otro origen MUST NOT informarle `Access-Control-Allow-Origin`, y un preflight con otro método o encabezado MUST responder `400`. CORS no reemplaza la autenticación.

#### Scenario: Preflight desde un origen permitido
- **GIVEN** dado `CORS_ORIGINS` igual a `http://localhost:5173`
- **WHEN** cuando se envía `OPTIONS /turnos` con `Origin: http://localhost:5173`, `Access-Control-Request-Method: GET` y `Access-Control-Request-Headers: authorization`
- **THEN** entonces la respuesta es `200`, con `Access-Control-Allow-Origin: http://localhost:5173`, permite el encabezado `Authorization` y no incluye `Access-Control-Allow-Credentials`

#### Scenario: Preflight del login
- **GIVEN** dado `CORS_ORIGINS` igual a `http://localhost:5173`
- **WHEN** cuando se envía `OPTIONS /auth/login` con `Origin: http://localhost:5173`, `Access-Control-Request-Method: POST` y `Access-Control-Request-Headers: content-type`
- **THEN** entonces la respuesta es `200`, con `Access-Control-Allow-Origin: http://localhost:5173` y permite el encabezado `Content-Type`

#### Scenario: Preflight de PATCH
- **GIVEN** dado `CORS_ORIGINS` igual a `http://localhost:5173`
- **WHEN** cuando se envía `OPTIONS /pacientes/00000000-0000-4000-8000-000000000001` con `Origin: http://localhost:5173`, `Access-Control-Request-Method: PATCH` y `Access-Control-Request-Headers: authorization, content-type`
- **THEN** entonces la respuesta es `200`, con `Access-Control-Allow-Origin: http://localhost:5173`

#### Scenario: Preflight de DELETE
- **GIVEN** dado `CORS_ORIGINS` igual a `http://localhost:5173`
- **WHEN** cuando se envía `OPTIONS /bloqueos/00000000-0000-4000-8000-000000000002` con `Origin: http://localhost:5173`, `Access-Control-Request-Method: DELETE` y `Access-Control-Request-Headers: authorization`
- **THEN** entonces la respuesta es `200`, con `Access-Control-Allow-Origin: http://localhost:5173`

#### Scenario: Preflight con un método no permitido
- **GIVEN** dado `CORS_ORIGINS` igual a `http://localhost:5173`
- **WHEN** cuando se envía `OPTIONS /turnos` con `Origin: http://localhost:5173` y `Access-Control-Request-Method: PUT`
- **THEN** entonces la respuesta es `400`; es el estado el que rechaza el pedido, porque esta respuesta sí incluye `Access-Control-Allow-Origin`

#### Scenario: Preflight con un encabezado no permitido
- **GIVEN** dado `CORS_ORIGINS` igual a `http://localhost:5173`
- **WHEN** cuando se envía `OPTIONS /turnos` con `Origin: http://localhost:5173`, `Access-Control-Request-Method: GET` y `Access-Control-Request-Headers: x-otro`
- **THEN** entonces la respuesta es `400`; es el estado el que rechaza el pedido, porque esta respuesta sí incluye `Access-Control-Allow-Origin`

#### Scenario: Preflight desde otro origen
- **GIVEN** dado `CORS_ORIGINS` igual a `http://localhost:5173`
- **WHEN** cuando se envía `OPTIONS /turnos` con `Origin: http://sitio-ajeno.example.com` y `Access-Control-Request-Method: GET`
- **THEN** entonces la respuesta es `400` y no incluye `Access-Control-Allow-Origin`

#### Scenario: El navegador puede leer un error de autenticación
- **GIVEN** dado `CORS_ORIGINS` igual a `http://localhost:5173`
- **WHEN** cuando se envía `GET /turnos?desde=2026-11-09&hasta=2026-11-09` sin token y con `Origin: http://localhost:5173`
- **THEN** entonces la respuesta es `401` con `detail.codigo = "no_autenticado"`, con `Access-Control-Allow-Origin: http://localhost:5173` y sin `Access-Control-Allow-Credentials`

#### Scenario: Otro origen tampoco evita la autenticación
- **GIVEN** dado `CORS_ORIGINS` igual a `http://localhost:5173`
- **WHEN** cuando se envía `GET /turnos?desde=2026-11-09&hasta=2026-11-09` sin token y con `Origin: http://sitio-ajeno.example.com`
- **THEN** entonces la respuesta es `401` y no incluye `Access-Control-Allow-Origin`

#### Scenario: Pedido sin origen
- **WHEN** cuando se envía `GET /health` sin encabezado `Origin`
- **THEN** entonces la respuesta es `200` y no incluye `Access-Control-Allow-Origin`

### Requirement: Valor de CORS_ORIGINS
`CORS_ORIGINS` SHALL ser una lista separada por comas, con espacios opcionales, y valer por defecto `http://localhost:5173`. Una lista vacía MUST significar que ningún origen está permitido. Un valor que contenga `*` es configuración inválida y MUST impedir que la API arranque, con un error que nombre la variable, sin impedir que se importe el módulo de la aplicación (design D2).

#### Scenario: Varios orígenes con espacios
- **GIVEN** dado `CORS_ORIGINS` igual a `http://localhost:5173, http://consultorio.example.com`
- **WHEN** cuando se envía un preflight con `Origin: http://consultorio.example.com`
- **THEN** entonces la respuesta incluye `Access-Control-Allow-Origin: http://consultorio.example.com`

#### Scenario: Valor por defecto
- **GIVEN** dado que `CORS_ORIGINS` no está definida en el entorno y no se carga ningún archivo `.env`
- **WHEN** cuando se carga la configuración de CORS
- **THEN** entonces la lista de orígenes es únicamente `http://localhost:5173`

#### Scenario: Lista vacía
- **GIVEN** dado `CORS_ORIGINS` vacío
- **WHEN** cuando se envía un preflight con `Origin: http://localhost:5173` y `Access-Control-Request-Method: GET`
- **THEN** entonces la respuesta es `400` y no incluye `Access-Control-Allow-Origin`

#### Scenario: Comodín
- **GIVEN** dado `CORS_ORIGINS` igual a `*`
- **WHEN** cuando la API arranca
- **THEN** entonces el arranque falla con un error de validación que menciona `CORS_ORIGINS`

#### Scenario: Comodín dentro de una lista
- **GIVEN** dado `CORS_ORIGINS` igual a `http://localhost:5173, *`
- **WHEN** cuando la API arranca
- **THEN** entonces el arranque falla con un error de validación que menciona `CORS_ORIGINS`

#### Scenario: Importar la aplicación con un comodín
- **GIVEN** dado `CORS_ORIGINS` igual a `*`
- **WHEN** cuando se crea la aplicación sin arrancarla y se le envía un preflight con `Origin: http://sitio-ajeno.example.com`
- **THEN** entonces la creación no falla y la respuesta no incluye `Access-Control-Allow-Origin`
