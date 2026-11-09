# Spec Delta

## Purpose

Define cómo un usuario inicia y termina su sesión en la SPA, cómo se conserva y vence esa sesión, y qué rutas y navegación ve según esté autenticado y según su rol (US-010, Flujo 1). La autorización real sigue siendo del backend.

## ADDED Requirements

### Requirement: Formulario de inicio de sesión
La ruta `/login` SHALL mostrar un formulario con email y contraseña que envía `POST /auth/login` con body JSON `{"email", "password"}`, sin alterar los valores: el backend normaliza el email (DD-24). Ambos campos MUST ser obligatorios en el formulario y, mientras el pedido está en curso, MUST NOT poder enviarse otro.

#### Scenario: Envío de las credenciales
- **GIVEN** dado el formulario de `/login`
- **WHEN** cuando se completa `recepcion@example.com`, una contraseña ficticia y se envía
- **THEN** entonces se hace un único `POST /auth/login` con ese email y esa contraseña en un body JSON

#### Scenario: Campos vacíos
- **GIVEN** dado el formulario de `/login` sin completar
- **WHEN** cuando se intenta enviar
- **THEN** entonces no se hace ningún pedido a la API

#### Scenario: Pedido en curso
- **GIVEN** dado un `POST /auth/login` que todavía no respondió
- **WHEN** cuando se intenta enviar el formulario de nuevo
- **THEN** entonces no se hace un segundo pedido y el botón de envío está deshabilitado

### Requirement: Redirección por rol tras el login
Tras un login exitoso, la SPA SHALL guardar la sesión y llevar al usuario a la pantalla de inicio de su rol, reemplazando `/login` en el historial: `/agenda` para `recepcionista` y `/agenda` para `odontologo` (design D7). La pantalla de inicio de cada rol MUST definirse en un único lugar.

#### Scenario: Recepcionista
- **GIVEN** dada una respuesta `200` con un token ficticio de rol `recepcionista`
- **WHEN** cuando se envía el formulario de `/login`
- **THEN** entonces se muestra `/agenda` con el layout de la recepcionista

#### Scenario: Odontólogo
- **GIVEN** dada una respuesta `200` con un token ficticio de rol `odontologo` y un `profesional_id`
- **WHEN** cuando se envía el formulario de `/login`
- **THEN** entonces se muestra `/agenda` con el layout del odontólogo

### Requirement: Login rechazado
Ante `401 credenciales_invalidas`, `/login` SHALL mostrar el mensaje de la API, sin indicar qué dato falló (DD-24), y MUST NOT guardar sesión ni avisar de sesión vencida. Ante cualquier otro error MUST mostrar el mensaje del error normalizado. El formulario MUST quedar disponible para reintentar.

#### Scenario: Credenciales inválidas
- **GIVEN** dada una respuesta `401` con `{"detail": {"codigo": "credenciales_invalidas", "mensaje": "Credenciales inválidas"}}`
- **WHEN** cuando se envía el formulario
- **THEN** entonces se ve `Credenciales inválidas`, sigue en `/login`, no hay token guardado y no se ve el aviso de sesión vencida

#### Scenario: Sin conexión
- **GIVEN** dado que la API no es alcanzable
- **WHEN** cuando se envía el formulario
- **THEN** entonces se ve el mensaje de falta de conexión, sigue en `/login` y el formulario se puede volver a enviar

#### Scenario: Reintento después de un error
- **GIVEN** dado un primer envío rechazado con `401 credenciales_invalidas`
- **WHEN** cuando se vuelve a enviar y la respuesta es `200` con un token ficticio vigente
- **THEN** entonces el error desaparece y se muestra la pantalla de inicio del rol

### Requirement: Datos de la sesión tomados del token
Como la API no informa el usuario de otra forma, la SPA SHALL leer `rol`, `profesional_id` y `exp` de los claims del JWT, sin verificar la firma y solo para decidir qué mostrar (design D1). Un token que no se pueda interpretar, sin `exp` numérico, ya vencido o con un `rol` distinto de `recepcionista` y `odontologo` MUST tratarse como inválido, sin crear sesión.

#### Scenario: Claims de la recepcionista
- **GIVEN** dado un token ficticio con `rol` `recepcionista`, `profesional_id` nulo y `exp` futuro
- **WHEN** cuando se interpretan sus claims
- **THEN** entonces la sesión tiene ese rol, `profesional_id` nulo y ese vencimiento

#### Scenario: Claims del odontólogo
- **GIVEN** dado un token ficticio con `rol` `odontologo`, un `profesional_id` ficticio y `exp` futuro
- **WHEN** cuando se interpretan sus claims
- **THEN** entonces la sesión tiene ese rol y ese `profesional_id`

#### Scenario: Token que no es un JWT
- **GIVEN** dada una respuesta `200` del login con `access_token` igual a `no-es-un-jwt`
- **WHEN** cuando se envía el formulario
- **THEN** entonces se ve un mensaje genérico de error, sigue en `/login` y no hay token guardado

#### Scenario: Rol desconocido
- **GIVEN** dada una respuesta `200` del login con un token ficticio de `rol` `administrador`
- **WHEN** cuando se envía el formulario
- **THEN** entonces se ve un mensaje genérico de error, sigue en `/login` y no hay token guardado

#### Scenario: Token sin vencimiento
- **GIVEN** dada una respuesta `200` del login con un token ficticio sin `exp`
- **WHEN** cuando se envía el formulario
- **THEN** entonces se ve un mensaje genérico de error, sigue en `/login` y no hay token guardado

### Requirement: Conservación de la sesión en la pestaña
La sesión SHALL conservarse al recargar la pestaña y MUST terminar al cerrarla: el token se guarda en `sessionStorage` y MUST NOT guardarse en `localStorage` (design D3). Al arrancar, un token vencido MUST descartarse con aviso de sesión vencida; uno que no se pueda interpretar MUST descartarse sin aviso.

#### Scenario: Dónde queda el token
- **WHEN** cuando un login termina con éxito
- **THEN** entonces el token está en `sessionStorage` y `localStorage` queda vacío

#### Scenario: Recarga con token vigente
- **GIVEN** dado un token ficticio vigente en `sessionStorage`
- **WHEN** cuando la aplicación arranca en `/agenda`
- **THEN** entonces se muestra `/agenda` sin pasar por el login

#### Scenario: Arranque con token vencido
- **GIVEN** dado un token ficticio vencido en `sessionStorage`
- **WHEN** cuando la aplicación arranca en `/agenda`
- **THEN** entonces el token se elimina y se muestra `/login` con el aviso de sesión vencida

#### Scenario: Arranque con token ilegible
- **GIVEN** dado el valor `no-es-un-jwt` en el almacenamiento de la sesión
- **WHEN** cuando la aplicación arranca en `/agenda`
- **THEN** entonces el valor se elimina y se muestra `/login` sin aviso de sesión vencida

### Requirement: Fin de la sesión por vencimiento
Al llegar el `exp` del token, o ante una respuesta `401 no_autenticado` en cualquier pedido (DD-24), la SPA SHALL eliminar el token y llevar al usuario a `/login` con un aviso de sesión vencida (design D4). No existe renovación del token: el usuario MUST iniciar sesión de nuevo.

#### Scenario: Llega el vencimiento
- **GIVEN** dado un usuario en `/agenda` con un token ficticio que vence en un minuto
- **WHEN** cuando pasa un minuto
- **THEN** entonces el token se elimina y se muestra `/login` con el aviso de sesión vencida

#### Scenario: Antes del vencimiento
- **GIVEN** dado un usuario en `/agenda` con un token ficticio que vence en un minuto
- **WHEN** cuando pasan 59 segundos
- **THEN** entonces sigue en `/agenda` y el token sigue guardado

#### Scenario: La API rechaza el token
- **GIVEN** dada una sesión activa con un token no vencido según su `exp`
- **WHEN** cuando un pedido responde `401` con `{"detail": {"codigo": "no_autenticado", "mensaje": "No autenticado"}}`
- **THEN** entonces el token se elimina y se muestra `/login` con el aviso de sesión vencida

#### Scenario: El aviso desaparece al iniciar sesión
- **GIVEN** dado `/login` con el aviso de sesión vencida
- **WHEN** cuando el usuario inicia sesión con éxito y después cierra la sesión
- **THEN** entonces `/login` ya no muestra el aviso

### Requirement: Un 403 de la API no cierra la sesión
Una respuesta `403` de la API MUST NOT cerrar la sesión ni eliminar el token: el usuario sigue autenticado y el error se entrega a la pantalla que hizo el pedido (DD-24).

#### Scenario: Rol insuficiente
- **GIVEN** dada una sesión activa
- **WHEN** cuando un pedido responde `403` con `{"detail": {"codigo": "rol_insuficiente", "mensaje": "Rol insuficiente"}}`
- **THEN** entonces el token sigue guardado, la ruta no cambia y el pedido falla con `codigo` `rol_insuficiente`

### Requirement: Cierre de sesión
El layout SHALL ofrecer una acción para cerrar la sesión que elimina el token y lleva a `/login` sin aviso de sesión vencida (design D8). El cierre es local, porque la API no tiene cierre de sesión ni revocación.

#### Scenario: El usuario cierra la sesión
- **GIVEN** dado un usuario en `/agenda`
- **WHEN** cuando elige cerrar la sesión
- **THEN** entonces el token se elimina y se muestra `/login` sin aviso de sesión vencida

#### Scenario: Volver atrás después de cerrar
- **GIVEN** dado un usuario que cerró la sesión desde `/agenda`
- **WHEN** cuando intenta volver a `/agenda`
- **THEN** entonces se muestra `/login`

### Requirement: Guarda de autenticación
Sin una sesión activa, toda ruta protegida MUST llevar a `/login`, reemplazando la ruta pedida en el historial. La ruta `/` MUST llevar a `/login` sin sesión. Después del login el usuario MUST ir a la pantalla de inicio de su rol, no a la ruta pedida (design D4).

#### Scenario: Agenda sin sesión
- **GIVEN** dado que no hay sesión
- **WHEN** cuando se navega a `/agenda`
- **THEN** entonces se muestra `/login` y no se ve el contenido de la agenda

#### Scenario: Ruta restringida sin sesión
- **GIVEN** dado que no hay sesión
- **WHEN** cuando se navega a `/configuracion`
- **THEN** entonces se muestra `/login`, no la pantalla de falta de permiso

#### Scenario: Raíz sin sesión
- **GIVEN** dado que no hay sesión
- **WHEN** cuando se navega a `/`
- **THEN** entonces se muestra `/login`

### Requirement: Usuario con sesión en rutas de entrada
Con una sesión activa, `/login` y `/` MUST llevar a la pantalla de inicio del rol, sin mostrar el formulario (design D6).

#### Scenario: Login con sesión
- **GIVEN** dada una sesión activa de rol `recepcionista`
- **WHEN** cuando se navega a `/login`
- **THEN** entonces se muestra `/agenda` y no el formulario

#### Scenario: Raíz con sesión
- **GIVEN** dada una sesión activa de rol `odontologo`
- **WHEN** cuando se navega a `/`
- **THEN** entonces se muestra `/agenda`

### Requirement: Guarda por rol
Una ruta restringida SHALL mostrar su contenido solo a los roles permitidos. A otro rol autenticado MUST mostrarle una pantalla de falta de permiso, sin cambiar la URL ni cerrar la sesión, con un enlace a su inicio (design D5). `/configuracion` es exclusiva de `recepcionista` (RN-AU-03). La guarda no reemplaza la autorización de la API.

#### Scenario: Rol permitido
- **GIVEN** dada una sesión activa de rol `recepcionista`
- **WHEN** cuando se navega a `/configuracion`
- **THEN** entonces se ve el contenido de configuración

#### Scenario: Rol no permitido
- **GIVEN** dada una sesión activa de rol `odontologo`
- **WHEN** cuando se navega a `/configuracion`
- **THEN** entonces se ve la pantalla de falta de permiso, la URL sigue siendo `/configuracion`, el token sigue guardado y no se ve el contenido de configuración

#### Scenario: Volver al inicio desde la falta de permiso
- **GIVEN** dada la pantalla de falta de permiso de un usuario `odontologo`
- **WHEN** cuando elige volver al inicio
- **THEN** entonces se muestra `/agenda`

#### Scenario: Ruta de ambos roles
- **GIVEN** dada una sesión activa de rol `odontologo`
- **WHEN** cuando se navega a `/agenda`
- **THEN** entonces se ve el contenido de la agenda

### Requirement: Layout de la aplicación
Las rutas protegidas SHALL mostrarse dentro de un layout con el rol del usuario, la navegación y la acción de cerrar sesión. El enlace a `/configuracion` MUST mostrarse solo a `recepcionista`. `/agenda` y `/configuracion` MUST ser pantallas provisorias, sin pedidos a la API y sin datos de pacientes.

#### Scenario: Navegación de la recepcionista
- **GIVEN** dada una sesión activa de rol `recepcionista`
- **WHEN** cuando se muestra el layout
- **THEN** entonces se ve el rol `Recepcionista` y los enlaces a la agenda y a la configuración

#### Scenario: Navegación del odontólogo
- **GIVEN** dada una sesión activa de rol `odontologo`
- **WHEN** cuando se muestra el layout
- **THEN** entonces se ve el rol `Odontólogo`, el enlace a la agenda y ningún enlace a la configuración

#### Scenario: Pantallas provisorias sin pedidos
- **GIVEN** dada una sesión activa de rol `recepcionista`
- **WHEN** cuando se navega a `/agenda` y después a `/configuracion`
- **THEN** entonces no se hace ningún pedido a la API

#### Scenario: El login no usa el layout
- **GIVEN** dado que no hay sesión
- **WHEN** cuando se muestra `/login`
- **THEN** entonces no se ve la navegación ni la acción de cerrar sesión

### Requirement: Ruta inexistente
Una ruta que no existe SHALL mostrar una pantalla de página no encontrada con un enlace a `/`, con o sin sesión.

#### Scenario: Sin sesión
- **GIVEN** dado que no hay sesión
- **WHEN** cuando se navega a `/no-existe`
- **THEN** entonces se ve la pantalla de página no encontrada

#### Scenario: Con sesión
- **GIVEN** dada una sesión activa
- **WHEN** cuando se navega a `/no-existe` y se elige el enlace a `/`
- **THEN** entonces se muestra la pantalla de inicio del rol
