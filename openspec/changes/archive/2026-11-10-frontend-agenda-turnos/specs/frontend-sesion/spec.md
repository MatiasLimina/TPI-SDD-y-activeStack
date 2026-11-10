## MODIFIED Requirements

### Requirement: Layout de la aplicación
Las rutas protegidas SHALL mostrarse dentro de un layout con el rol del usuario, la navegación y la acción de cerrar sesión. El enlace a `/configuracion` MUST mostrarse solo a `recepcionista`. `/configuracion` MUST ser una pantalla provisoria, sin pedidos a la API y sin datos de pacientes.

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
- **WHEN** cuando se navega directamente a `/configuracion`
- **THEN** entonces no se hace ningún pedido a la API

#### Scenario: El login no usa el layout
- **GIVEN** dado que no hay sesión
- **WHEN** cuando se muestra `/login`
- **THEN** entonces no se ve la navegación ni la acción de cerrar sesión
