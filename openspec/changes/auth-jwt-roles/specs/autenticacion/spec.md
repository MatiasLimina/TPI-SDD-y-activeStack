# Spec Delta

## Purpose

Permitir que la recepcionista y los odontólogos inicien sesión con email y contraseña y obtengan un JWT de vida corta, y que la API identifique al usuario de cada request protegido con un contrato `401` uniforme (RN-AU-01, Flujo 1, DD-24).

## ADDED Requirements

### Requirement: Inicio de sesión con credenciales válidas
El sistema SHALL exponer `POST /auth/login`, público, con body JSON `{"email", "password"}`. Si el email corresponde a un usuario activo y la contraseña es correcta, MUST responder `200` con exactamente `{"access_token": <JWT>, "token_type": "bearer"}`. El email MUST compararse sin distinguir mayúsculas y sin espacios al principio ni al final. Un body sin `email` o sin `password` MUST responder `422`.

#### Scenario: Recepcionista inicia sesión
- **GIVEN** dado un usuario activo con rol `recepcionista`, email `recepcion@example.com` y una contraseña ficticia conocida
- **WHEN** cuando se envía `POST /auth/login` con ese email y esa contraseña
- **THEN** entonces la respuesta es `200`, el cuerpo tiene solo las claves `access_token` y `token_type`, `token_type` vale `bearer` y `access_token` es un JWT no vacío

#### Scenario: Odontólogo inicia sesión
- **GIVEN** dado un usuario activo con rol `odontologo` vinculado al profesional A
- **WHEN** cuando inicia sesión con su email y su contraseña
- **THEN** entonces la respuesta es `200` con un `access_token` cuyo rol es `odontologo` y cuyo `profesional_id` es el del profesional A

#### Scenario: Email con mayúsculas y espacios
- **GIVEN** dado un usuario activo con email `recepcion@example.com`
- **WHEN** cuando se inicia sesión con el email `"  Recepcion@Example.COM "` y la contraseña correcta
- **THEN** entonces la respuesta es `200` con un `access_token`

#### Scenario: Body incompleto
- **WHEN** cuando se envía `POST /auth/login` con `{"email": "recepcion@example.com"}`, sin `password`
- **THEN** entonces la respuesta es `422` y no se emite ningún token

### Requirement: Rechazo uniforme de credenciales
Si el email no corresponde a ningún usuario, si la contraseña es incorrecta o si el usuario está inactivo, `POST /auth/login` MUST responder `401` con el encabezado `WWW-Authenticate: Bearer` y el cuerpo `{"detail": {"codigo": "credenciales_invalidas", "mensaje": "Credenciales inválidas"}}`, con ese mensaje constante e idéntico en los tres casos, sin emitir token (DD-24). El sistema MUST verificar una contraseña contra un hash también cuando el email no existe, para no revelar qué emails están registrados.

#### Scenario: Contraseña incorrecta
- **GIVEN** dado un usuario activo con email `recepcion@example.com`
- **WHEN** cuando se inicia sesión con ese email y una contraseña distinta de la suya
- **THEN** entonces la respuesta es `401` con `WWW-Authenticate: Bearer`, `detail.codigo = "credenciales_invalidas"` y sin `access_token`

#### Scenario: Los tres rechazos son indistinguibles
- **GIVEN** dado un usuario activo A, un usuario inactivo B con contraseña conocida, y un email `nadie@example.com` que no existe
- **WHEN** cuando se inicia sesión con A y una contraseña incorrecta, con B y su contraseña correcta, y con `nadie@example.com`
- **THEN** entonces las tres respuestas tienen el mismo estado `401`, el mismo encabezado `WWW-Authenticate` y exactamente el mismo cuerpo `{"detail": {"codigo": "credenciales_invalidas", "mensaje": "Credenciales inválidas"}}`

#### Scenario: Usuario desactivado con su contraseña correcta
- **GIVEN** dado un usuario que fue desactivado
- **WHEN** cuando inicia sesión con su email y su contraseña correcta
- **THEN** entonces la respuesta es `401` con `detail.codigo = "credenciales_invalidas"`

#### Scenario: Email inexistente también verifica una contraseña
- **WHEN** cuando se inicia sesión con un email que no existe
- **THEN** entonces se ejecuta exactamente una verificación de contraseña contra un hash, igual que cuando el email existe, y la respuesta es `401`

#### Scenario: Contraseña vacía
- **GIVEN** dado un usuario activo con email `recepcion@example.com`
- **WHEN** cuando se inicia sesión con ese email y `password` igual a `""`
- **THEN** entonces la respuesta es `401` con `detail.codigo = "credenciales_invalidas"`

### Requirement: Contenido y vigencia del token
El token emitido MUST ser un JWT firmado con HS256 y la clave `JWT_SECRET`, con los claims `sub` (id del usuario como texto), `rol`, `profesional_id` (nulo para la recepcionista) y `exp`. `exp` MUST ser el instante de emisión más `JWT_EXPIRE_MINUTES` minutos. El emisor usa el reloj del sistema, sin reloj inyectado: los escenarios acotan el instante de emisión entre `t0` y `t1`, los instantes UTC medidos inmediatamente antes y después del login, con una tolerancia de 5 segundos (la resolución de `exp` es de un segundo).

#### Scenario: Claims de la recepcionista
- **GIVEN** dado un usuario activo con rol `recepcionista` y `JWT_EXPIRE_MINUTES = 60`
- **WHEN** cuando inicia sesión entre los instantes `t0` y `t1` y se decodifica el `access_token` con `JWT_SECRET` y HS256
- **THEN** entonces `sub` es el id del usuario, `rol` es `recepcionista`, `profesional_id` es nulo y `exp` está entre `t0 + 60 min − 5 s` y `t1 + 60 min + 5 s`

#### Scenario: Claims del odontólogo
- **GIVEN** dado un usuario activo con rol `odontologo` vinculado al profesional A
- **WHEN** cuando inicia sesión y se decodifica el `access_token`
- **THEN** entonces `rol` es `odontologo` y `profesional_id` es el id del profesional A

#### Scenario: Vigencia configurable
- **GIVEN** dado `JWT_EXPIRE_MINUTES = 15`
- **WHEN** cuando un usuario activo inicia sesión entre los instantes `t0` y `t1`
- **THEN** entonces `exp` del token está entre `t0 + 15 min − 5 s` y `t1 + 15 min + 5 s`

### Requirement: Token ausente o mal formado en una ruta protegida
Una ruta protegida invocada sin encabezado `Authorization`, con un esquema distinto de `Bearer` o con un valor que no es un JWT MUST responder `401` con `WWW-Authenticate: Bearer` y el cuerpo `{"detail": {"codigo": "no_autenticado", "mensaje": "No autenticado"}}`, con ese mensaje constante e idéntico en todos los casos de token, sin ejecutar la operación (DD-24).

#### Scenario: Sin encabezado Authorization
- **WHEN** cuando se envía `POST /turnos` con un body válido y sin encabezado `Authorization`
- **THEN** entonces la respuesta es `401` con `WWW-Authenticate: Bearer`, `detail.codigo = "no_autenticado"` y no se persiste ningún turno

#### Scenario: Esquema distinto de Bearer
- **WHEN** cuando se envía `POST /turnos` con `Authorization: Basic dXN1YXJpbzpjbGF2ZQ==`
- **THEN** entonces la respuesta es `401` con `detail.codigo = "no_autenticado"`

#### Scenario: Valor que no es un JWT
- **WHEN** cuando se envía `POST /turnos` con `Authorization: Bearer no-es-un-jwt`
- **THEN** entonces la respuesta es `401` con `detail.codigo = "no_autenticado"`

### Requirement: Token inválido o vencido
Un token con firma inválida, firmado con un algoritmo distinto de HS256 o sin firma, vencido (su `exp` es anterior al instante del request), sin los claims `sub` o `exp`, o con un `sub` que no es un UUID MUST rechazarse con el mismo `401` y el mismo cuerpo de token ausente (`no_autenticado`, `WWW-Authenticate: Bearer`), sin ejecutar la operación (DD-24). Un token cuyo `exp` todavía no llegó MUST aceptarse. Los tokens de estos escenarios se firman en el test con un `exp` explícito, sin reloj inyectado.

#### Scenario: Token vencido
- **GIVEN** dado un token de una recepcionista activa, firmado con `JWT_SECRET` y HS256, cuyo `exp` se fija explícitamente una hora antes del instante del request
- **WHEN** cuando se lo usa en `POST /turnos` con un body válido
- **THEN** entonces la respuesta es `401` con `detail.codigo = "no_autenticado"` y no se persiste ningún turno

#### Scenario: Firma con otra clave
- **GIVEN** dado un token con claims válidos de una recepcionista activa pero firmado con una clave distinta de `JWT_SECRET`
- **WHEN** cuando se lo usa en una ruta protegida
- **THEN** entonces la respuesta es `401` con `detail.codigo = "no_autenticado"`

#### Scenario: Token sin firma
- **GIVEN** dado un token con algoritmo `none` y claims válidos de una recepcionista activa
- **WHEN** cuando se lo usa en una ruta protegida
- **THEN** entonces la respuesta es `401` con `detail.codigo = "no_autenticado"`

#### Scenario: Token sin claim obligatorio
- **GIVEN** dado un token firmado con `JWT_SECRET` y HS256 al que le falta `exp`, u otro al que le falta `sub`
- **WHEN** cuando se lo usa en una ruta protegida
- **THEN** entonces la respuesta es `401` con `detail.codigo = "no_autenticado"` en ambos casos

#### Scenario: Token recién vencido
- **GIVEN** dado un token de una recepcionista activa, firmado con `JWT_SECRET` y HS256, cuyo `exp` se fija explícitamente 60 segundos antes del instante del request
- **WHEN** cuando se lo usa en `POST /turnos` con un body válido
- **THEN** entonces la respuesta es `401` con `detail.codigo = "no_autenticado"` y no se persiste ningún turno

#### Scenario: Token a punto de vencer todavía vale
- **GIVEN** dado un token de una recepcionista activa, firmado con `JWT_SECRET` y HS256, cuyo `exp` se fija explícitamente 60 segundos después del instante del request
- **WHEN** cuando se lo usa en `POST /turnos` con un body válido
- **THEN** entonces la respuesta es `201` y el turno queda creado con `creado_por` igual al id de la recepcionista

#### Scenario: Sub que no es un UUID
- **GIVEN** dado un token firmado con `JWT_SECRET` y HS256, no vencido, cuyo `sub` es `"abc"`
- **WHEN** cuando se lo usa en una ruta protegida
- **THEN** entonces la respuesta es `401` con `detail.codigo = "no_autenticado"`

### Requirement: Usuario vigente en cada request
En cada request protegido el sistema MUST cargar de la base el usuario indicado por `sub`. Si no existe o está inactivo, MUST responder `401` (`no_autenticado`, DD-24) aunque el token sea válido y no esté vencido. El rol y el profesional que valen para autorizar MUST ser los de la base, no los del token.

#### Scenario: Usuario desactivado después de emitido el token
- **GIVEN** dado un token válido y no vencido emitido para una recepcionista activa
- **WHEN** cuando la recepcionista se desactiva y después se usa ese token en `POST /turnos`
- **THEN** entonces la respuesta es `401` con `detail.codigo = "no_autenticado"` y no se persiste ningún turno

#### Scenario: Sub que no corresponde a ningún usuario
- **GIVEN** dado un token firmado con `JWT_SECRET`, no vencido, cuyo `sub` es un UUID que no existe en la base
- **WHEN** cuando se lo usa en una ruta protegida
- **THEN** entonces la respuesta es `401` con `detail.codigo = "no_autenticado"`

#### Scenario: Rol del token distinto del rol en la base
- **GIVEN** dado un usuario activo con rol `odontologo` y un token firmado con `JWT_SECRET` con su `sub` pero con `rol = "recepcionista"`
- **WHEN** cuando se lo usa en `POST /turnos`
- **THEN** entonces la respuesta es `403`, porque vale el rol de la base

### Requirement: Rutas públicas
`POST /auth/login` y `GET /health` MUST responder sin exigir token; un encabezado `Authorization` inválido en ellas MUST ignorarse. Toda otra ruta de datos MUST exigir autenticación. Una ruta inexistente MUST seguir respondiendo `404`, no `401`.

#### Scenario: Health sin token
- **WHEN** cuando se envía `GET /health` sin encabezado `Authorization` y la base está operativa
- **THEN** entonces la respuesta es `200` con `{"status": "ok", "database": "ok"}`

#### Scenario: Health con un token inválido
- **WHEN** cuando se envía `GET /health` con `Authorization: Bearer no-es-un-jwt`
- **THEN** entonces la respuesta es `200`

#### Scenario: Login con un token inválido en el encabezado
- **GIVEN** dado un usuario activo con contraseña conocida
- **WHEN** cuando inicia sesión enviando además `Authorization: Bearer no-es-un-jwt`
- **THEN** entonces la respuesta es `200` con un `access_token`

#### Scenario: Ruta inexistente sin token
- **WHEN** cuando se envía `GET /no-existe` sin token
- **THEN** entonces la respuesta es `404`
