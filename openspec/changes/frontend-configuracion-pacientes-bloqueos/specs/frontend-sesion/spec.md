## MODIFIED Requirements

### Requirement: Datos de la sesión tomados del token
Como la API no informa el usuario de otra forma, la SPA SHALL leer `rol`, `profesional_id` y `exp` (en segundos) de los claims del JWT, sin verificar la firma y solo para decidir qué mostrar (design D1). También MUST leer `sub` como id del usuario, nulo si falta o no es texto, sin que eso afecte la validez del token (C-16, design D10). Cualquier texto se acepta tal cual, sin comprobar que sea un UUID: solo se compara con el `usuario_id` de la auditoría. Un token ilegible, sin `exp` numérico o con `rol` distinto de `recepcionista` y `odontologo` es inválido; uno con `exp` menor o igual al reloj está vencido. En el login, ambos MUST rechazarse con `Ocurrió un error. Intentá de nuevo.`, sin crear sesión ni avisar de sesión vencida.

#### Scenario: Claims de la recepcionista
- **GIVEN** dado el reloj en `2026-11-09T12:00:00Z` (`1794225600` en segundos) y un token ficticio con `sub` `00000000-0000-4000-8000-0000000000b1`, `rol` `recepcionista`, `profesional_id` nulo y `exp` `1794229200`
- **WHEN** cuando se interpretan sus claims
- **THEN** entonces la sesión tiene ese rol, `profesional_id` nulo, vencimiento `1794229200` y usuario `00000000-0000-4000-8000-0000000000b1`

#### Scenario: Claims del odontólogo
- **GIVEN** dado el reloj en `2026-11-09T12:00:00Z` (`1794225600` en segundos) y un token ficticio con `rol` `odontologo`, un `profesional_id` ficticio y `exp` `1794229200`
- **WHEN** cuando se interpretan sus claims
- **THEN** entonces la sesión tiene ese rol y ese `profesional_id`

#### Scenario: Token sin sub
- **GIVEN** dado el reloj en `2026-11-09T12:00:00Z` y un token ficticio vigente de `rol` `recepcionista` sin `sub`, y otro con `sub` numérico `5`
- **WHEN** cuando se interpretan sus claims
- **THEN** entonces ambos son vigentes y la sesión tiene usuario nulo

#### Scenario: Token que no es un JWT
- **GIVEN** dada una respuesta `200` del login con `access_token` igual a `no-es-un-jwt`
- **WHEN** cuando se envía el formulario
- **THEN** entonces se ve `Ocurrió un error. Intentá de nuevo.`, sigue en `/login` y no hay token guardado

#### Scenario: Rol desconocido
- **GIVEN** dada una respuesta `200` del login con un token ficticio de `rol` `administrador`
- **WHEN** cuando se envía el formulario
- **THEN** entonces se ve `Ocurrió un error. Intentá de nuevo.`, sigue en `/login` y no hay token guardado

#### Scenario: Token sin vencimiento
- **GIVEN** dada una respuesta `200` del login con un token ficticio sin `exp`
- **WHEN** cuando se envía el formulario
- **THEN** entonces se ve `Ocurrió un error. Intentá de nuevo.`, sigue en `/login` y no hay token guardado

#### Scenario: Token ya vencido en el login
- **GIVEN** dado el reloj en `2026-11-09T12:00:00Z` (`1794225600` en segundos) y una respuesta `200` del login con un token ficticio de `exp` `1794225540`
- **WHEN** cuando se envía el formulario
- **THEN** entonces se ve `Ocurrió un error. Intentá de nuevo.`, sigue en `/login`, no hay token guardado y no se ve el aviso de sesión vencida

### Requirement: Guarda por rol
Una ruta restringida SHALL mostrar su contenido solo a los roles permitidos. A otro rol autenticado MUST mostrarle una pantalla de falta de permiso, sin cambiar la URL ni cerrar la sesión, con un enlace a su inicio (design D5). `/configuracion` y sus secciones son exclusivas de `recepcionista` (RN-AU-03), igual que `/pacientes` (DD-31 b); `/bloqueos` es de ambos roles (RN-HB-02). La guarda no reemplaza la autorización de la API.

#### Scenario: Rol permitido
- **GIVEN** dada una sesión activa de rol `recepcionista`
- **WHEN** cuando se navega a `/configuracion`
- **THEN** entonces se ve el contenido de configuración

#### Scenario: Rol no permitido
- **GIVEN** dada una sesión activa de rol `odontologo`
- **WHEN** cuando se navega a `/configuracion`
- **THEN** entonces se ve la pantalla de falta de permiso, la URL sigue siendo `/configuracion`, el token sigue guardado y no se ve el contenido de configuración

#### Scenario: Sección de configuración para el odontólogo
- **GIVEN** dada una sesión activa de rol `odontologo`
- **WHEN** cuando se navega a `/configuracion/horarios`
- **THEN** entonces se ve la pantalla de falta de permiso, la URL sigue siendo `/configuracion/horarios` y no se hace ningún pedido a la API

#### Scenario: Pacientes para el odontólogo
- **GIVEN** dada una sesión activa de rol `odontologo`
- **WHEN** cuando se navega a `/pacientes`
- **THEN** entonces se ve la pantalla de falta de permiso, la URL sigue siendo `/pacientes` y no se hace ningún pedido a `/pacientes`

#### Scenario: Volver al inicio desde la falta de permiso
- **GIVEN** dada la pantalla de falta de permiso de un usuario `odontologo`
- **WHEN** cuando elige volver al inicio
- **THEN** entonces se muestra `/agenda`

#### Scenario: Ruta de ambos roles
- **GIVEN** dada una sesión activa de rol `odontologo`
- **WHEN** cuando se navega a `/agenda`, y luego a `/bloqueos`
- **THEN** entonces se ve el contenido de la agenda, y luego el de los bloqueos

### Requirement: Layout de la aplicación
Las rutas protegidas SHALL mostrarse dentro de un layout con el rol del usuario, la navegación y la acción de cerrar sesión. Los enlaces a `/configuracion` y a `/pacientes` MUST mostrarse solo a `recepcionista`; los enlaces a `/agenda` y a `/bloqueos`, a ambos roles. El enlace de la sección actual MUST marcarse como página actual.

#### Scenario: Navegación de la recepcionista
- **GIVEN** dada una sesión activa de rol `recepcionista`
- **WHEN** cuando se muestra el layout
- **THEN** entonces se ve el rol `Recepcionista` y los enlaces `Agenda`, `Configuración`, `Pacientes` y `Bloqueos`

#### Scenario: Navegación del odontólogo
- **GIVEN** dada una sesión activa de rol `odontologo`
- **WHEN** cuando se muestra el layout
- **THEN** entonces se ve el rol `Odontólogo`, los enlaces `Agenda` y `Bloqueos`, y ningún enlace a la configuración ni a los pacientes

#### Scenario: Pantallas provisorias sin pedidos
- **GIVEN** dada una sesión activa de rol `recepcionista`
- **WHEN** cuando se navega directamente a `/configuracion`, a `/pacientes` y a `/bloqueos`
- **THEN** entonces ninguna muestra el texto `Pantalla provisoria`, porque desde C-16 ninguna ruta del layout es provisoria y todas piden sus datos a la API

#### Scenario: Sección actual marcada
- **GIVEN** dada una sesión activa de rol `recepcionista`
- **WHEN** cuando se navega a `/configuracion/sillones`
- **THEN** entonces el enlace `Configuración` tiene `aria-current="page"` y el enlace `Agenda` no

#### Scenario: El login no usa el layout
- **GIVEN** dado que no hay sesión
- **WHEN** cuando se muestra `/login`
- **THEN** entonces no se ve la navegación ni la acción de cerrar sesión
