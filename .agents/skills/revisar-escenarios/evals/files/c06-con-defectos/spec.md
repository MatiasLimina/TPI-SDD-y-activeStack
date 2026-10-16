# Delta for autenticacion

## ADDED Requirements

### Requirement: Inicio de sesión
El sistema SHALL exponer `POST /auth/login` que recibe email y contraseña y devuelve un JWT con `sub`, `rol` y `profesional_id`.

#### Scenario: Login válido de recepcionista
- **GIVEN** dada la usuaria ficticia `recepcion@consultorio.test` con rol `recepcionista` y contraseña de desarrollo
- **WHEN** cuando envía `POST /auth/login` con sus credenciales
- **THEN** entonces la respuesta es `200` con un `access_token` cuyo `rol` es `recepcionista`

#### Scenario: Usuario desactivado
- **GIVEN** dado un usuario con `activo = false`
- **WHEN** cuando intenta iniciar sesión con credenciales correctas
- **THEN** entonces la respuesta es `400 Inactive user`

#### Scenario: Token con expiración
- **WHEN** cuando pasa el tiempo de expiración
- **THEN** entonces el sistema maneja el token correctamente

### Requirement: Protección de endpoints de turnos
`POST /turnos`, cancelar y reprogramar deberían requerir rol `recepcionista`.

#### Scenario: Odontólogo no puede crear turnos
- **GIVEN** dado un odontólogo autenticado
- **WHEN** cuando envía `POST /turnos`
- **THEN** entonces la respuesta es `401`

#### Scenario: Se registra la auditoría del alta
- **GIVEN** dada una recepcionista autenticada
- **WHEN** cuando crea un turno
- **THEN** entonces se inserta una fila en `turno_auditoria` con `accion = crear` y su `usuario_id`
