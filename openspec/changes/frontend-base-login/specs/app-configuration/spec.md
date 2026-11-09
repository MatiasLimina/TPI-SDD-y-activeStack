# Spec Delta

## ADDED Requirements

### Requirement: Orígenes CORS restringidos
La API SHALL aceptar pedidos de navegador solo desde los orígenes listados en `CORS_ORIGINS`, una lista separada por comas con espacios opcionales, permitiendo los métodos `GET`, `POST`, `PATCH` y `DELETE` y los encabezados `Authorization` y `Content-Type`, sin credenciales de cookie (08 §Seguridad). A otro origen MUST NOT informarle `Access-Control-Allow-Origin`. CORS no reemplaza la autenticación.

#### Scenario: Preflight desde un origen permitido
- **GIVEN** dado `CORS_ORIGINS` igual a `http://localhost:5173`
- **WHEN** cuando se envía `OPTIONS /turnos` con `Origin: http://localhost:5173`, `Access-Control-Request-Method: GET` y `Access-Control-Request-Headers: authorization`
- **THEN** entonces la respuesta es `200`, con `Access-Control-Allow-Origin: http://localhost:5173` y permitiendo el encabezado `Authorization`

#### Scenario: Preflight desde otro origen
- **GIVEN** dado `CORS_ORIGINS` igual a `http://localhost:5173`
- **WHEN** cuando se envía `OPTIONS /turnos` con `Origin: http://sitio-ajeno.example.com` y `Access-Control-Request-Method: GET`
- **THEN** entonces la respuesta no incluye `Access-Control-Allow-Origin`

#### Scenario: Varios orígenes con espacios
- **GIVEN** dado `CORS_ORIGINS` igual a `http://localhost:5173, http://consultorio.example.com`
- **WHEN** cuando se envía un preflight con `Origin: http://consultorio.example.com`
- **THEN** entonces la respuesta incluye `Access-Control-Allow-Origin: http://consultorio.example.com`

#### Scenario: Valor por defecto
- **GIVEN** dado que `CORS_ORIGINS` no está definida
- **WHEN** cuando se envía un preflight con `Origin: http://localhost:5173`
- **THEN** entonces la respuesta incluye `Access-Control-Allow-Origin: http://localhost:5173`

#### Scenario: El navegador puede leer un error de autenticación
- **GIVEN** dado `CORS_ORIGINS` igual a `http://localhost:5173`
- **WHEN** cuando se envía `GET /turnos?desde=2026-11-09&hasta=2026-11-09` sin token y con `Origin: http://localhost:5173`
- **THEN** entonces la respuesta es `401` con `detail.codigo = "no_autenticado"` y con `Access-Control-Allow-Origin: http://localhost:5173`

#### Scenario: Otro origen tampoco evita la autenticación
- **GIVEN** dado `CORS_ORIGINS` igual a `http://localhost:5173`
- **WHEN** cuando se envía `GET /turnos?desde=2026-11-09&hasta=2026-11-09` sin token y con `Origin: http://sitio-ajeno.example.com`
- **THEN** entonces la respuesta es `401` y no incluye `Access-Control-Allow-Origin`

#### Scenario: Pedido sin origen
- **WHEN** cuando se envía `GET /health` sin encabezado `Origin`
- **THEN** entonces la respuesta es `200` y no incluye `Access-Control-Allow-Origin`
