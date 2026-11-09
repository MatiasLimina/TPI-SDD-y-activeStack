# app-configuration Specification

## Purpose

Define cómo la aplicación obtiene su configuración (conexiones, secretos, zona horaria) exclusivamente desde variables de entorno, sin secretos versionados (RN-CU-03).

## Requirements

### Requirement: Configuración leída de variables de entorno
El sistema SHALL leer su configuración desde variables de entorno (opcionalmente cargadas desde un archivo `.env` local): `DATABASE_URL`, `REDIS_URL`, `JWT_SECRET`, `JWT_EXPIRE_MINUTES`, `APP_TIMEZONE`, `NOTIFICATION_ADAPTER`, `CORS_ORIGINS`, `REMINDER_LEAD_HOURS` y `CONSULTORIO_NOMBRE`.

#### Scenario: Valores tomados del entorno
- **WHEN** la aplicación arranca con `DATABASE_URL` y `APP_TIMEZONE=America/Argentina/Buenos_Aires` definidos en el entorno
- **THEN** la configuración efectiva usa exactamente esos valores

#### Scenario: Valores por defecto no sensibles
- **WHEN** la aplicación arranca sin definir `APP_TIMEZONE` ni `JWT_EXPIRE_MINUTES`
- **THEN** la configuración usa `America/Argentina/Buenos_Aires` y `60` respectivamente

#### Scenario: Valores por defecto de los recordatorios
- **WHEN** la aplicación arranca sin definir `REMINDER_LEAD_HOURS`, `NOTIFICATION_ADAPTER` ni `CONSULTORIO_NOMBRE`
- **THEN** la configuración usa `24`, `mock` y `Consultorio odontológico` respectivamente

#### Scenario: Anticipación y consultorio tomados del entorno
- **WHEN** la aplicación arranca con `REMINDER_LEAD_HOURS=48` y `CONSULTORIO_NOMBRE=Consultorio Odontológico Ejemplo` en el entorno
- **THEN** la configuración efectiva usa `48` y `Consultorio Odontológico Ejemplo`

### Requirement: Fallo explícito ante configuración obligatoria faltante
El sistema MUST negarse a arrancar con un error que nombre la variable cuando falte una variable obligatoria sin valor por defecto (`DATABASE_URL`, `JWT_SECRET`) o cuando un valor sea inválido, en lugar de usar un valor implícito. `JWT_EXPIRE_MINUTES` MUST ser un entero mayor que cero; un valor no numérico también es inválido (DD-24 (f)). `REMINDER_LEAD_HOURS` MUST ser un entero mayor que cero, con el mismo criterio (design D16, a registrar en DD-28). `NOTIFICATION_ADAPTER` MUST valer `mock`, el único adaptador del MVP (DD-04; design D13), y `CONSULTORIO_NOMBRE` MUST NOT estar vacío ni ser solo espacios (design D16, a registrar en DD-28).

#### Scenario: Falta DATABASE_URL
- **WHEN** se carga la configuración sin `DATABASE_URL` en el entorno ni en `.env`
- **THEN** la carga falla con un error de validación que menciona `DATABASE_URL`

#### Scenario: Zona horaria inválida
- **WHEN** se carga la configuración con `APP_TIMEZONE=Mars/Olympus`
- **THEN** la carga falla con un error de validación que menciona `APP_TIMEZONE`

#### Scenario: Falta JWT_SECRET
- **WHEN** se carga la configuración sin `JWT_SECRET` en el entorno ni en `.env`
- **THEN** la carga falla con un error de validación que menciona `JWT_SECRET`

#### Scenario: Vigencia del token no positiva
- **WHEN** se carga la configuración con `JWT_EXPIRE_MINUTES=0`, o con `JWT_EXPIRE_MINUTES=-5`
- **THEN** la carga falla en ambos casos con un error de validación que menciona `JWT_EXPIRE_MINUTES`

#### Scenario: Vigencia del token no numérica
- **WHEN** se carga la configuración con `JWT_EXPIRE_MINUTES=abc`
- **THEN** la carga falla con un error de validación que menciona `JWT_EXPIRE_MINUTES`

#### Scenario: Vigencia mínima aceptada
- **WHEN** se carga la configuración con `JWT_EXPIRE_MINUTES=1`
- **THEN** la configuración efectiva usa `1`

#### Scenario: Anticipación del recordatorio inválida
- **WHEN** se carga la configuración con `REMINDER_LEAD_HOURS=0`, con `REMINDER_LEAD_HOURS=-24` o con `REMINDER_LEAD_HOURS=un-dia`
- **THEN** la carga falla en los tres casos con un error de validación que menciona `REMINDER_LEAD_HOURS`

#### Scenario: Anticipación mínima aceptada
- **WHEN** se carga la configuración con `REMINDER_LEAD_HOURS=1`
- **THEN** la configuración efectiva usa `1`

#### Scenario: Adaptador de notificación desconocido
- **WHEN** se carga la configuración con `NOTIFICATION_ADAPTER=whatsapp`
- **THEN** la carga falla con un error de validación que menciona `NOTIFICATION_ADAPTER`

#### Scenario: Nombre del consultorio vacío
- **WHEN** se carga la configuración con `CONSULTORIO_NOMBRE` vacío o con `CONSULTORIO_NOMBRE` formado solo por espacios
- **THEN** la carga falla en ambos casos con un error de validación que menciona `CONSULTORIO_NOMBRE`

### Requirement: Plantilla de entorno versionada sin secretos
El repositorio SHALL incluir un `.env.example` versionado que liste todas las variables de configuración con valores de ejemplo no sensibles (placeholders), y el archivo `.env` MUST estar excluido del control de versiones. `.env.example` MUST listar también las contraseñas de desarrollo del seed (`SEED_RECEPCIONISTA_PASSWORD`, `SEED_ODONTOLOGO_1_PASSWORD`, `SEED_ODONTOLOGO_2_PASSWORD`) con valores ficticios, evidentes y no productivos.

#### Scenario: .env ignorado y .env.example versionado
- **WHEN** se consulta a git si `.env` y `.env.example` están ignorados
- **THEN** `.env` está ignorado y `.env.example` no lo está

#### Scenario: Placeholders en lugar de secretos
- **WHEN** se inspecciona `.env.example`
- **THEN** `JWT_SECRET` tiene un valor placeholder evidente (por ejemplo `change-me`) y no hay credenciales reales

#### Scenario: Contraseñas de desarrollo del seed
- **WHEN** se inspecciona `.env.example`
- **THEN** declara `SEED_RECEPCIONISTA_PASSWORD`, `SEED_ODONTOLOGO_1_PASSWORD` y `SEED_ODONTOLOGO_2_PASSWORD`, cada una con un valor no vacío que la identifica como contraseña ficticia de desarrollo

#### Scenario: Contraseña del comando CLI fuera de la plantilla
- **WHEN** se inspecciona `.env.example`
- **THEN** no declara `USUARIO_PASSWORD`, que solo se define al invocar el comando de alta

### Requirement: Variables de recordatorios en la plantilla de entorno
`.env.example` MUST declarar `REMINDER_LEAD_HOURS`, `NOTIFICATION_ADAPTER` y `CONSULTORIO_NOMBRE` con valores de ejemplo no sensibles, y `TEST_REDIS_URL`, la conexión al Redis de tests, apuntando a una base de Redis distinta de la de `REDIS_URL` para que los tests no vacíen la cola de desarrollo.

#### Scenario: Variables de recordatorios en la plantilla
- **WHEN** se inspecciona `.env.example`
- **THEN** declara `REMINDER_LEAD_HOURS=24`, `NOTIFICATION_ADAPTER=mock` y `CONSULTORIO_NOMBRE` con un nombre de consultorio ficticio

#### Scenario: Redis de tests separado del de desarrollo
- **WHEN** se inspecciona `.env.example`
- **THEN** declara `TEST_REDIS_URL` y su número de base de Redis es distinto del de `REDIS_URL`

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
