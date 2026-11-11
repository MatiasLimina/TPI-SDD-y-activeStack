## Purpose

Historial de auditoría de un turno en la SPA, con el que la recepcionista consulta quién creó, reprogramó o canceló un turno y cuándo (US-011, RN-CU-01), sobre `GET /turnos/{id}/auditoria` (DD-25).

## ADDED Requirements

### Requirement: Acceso al historial desde el detalle del turno
El detalle de un turno en la agenda SHALL ofrecer `Ver historial` a la `recepcionista` para cualquier turno, programado o cancelado, pasado o futuro. Al `odontologo` MUST NOT ofrecérselo, porque la API se lo niega (DD-25 a). Elegirlo MUST cerrar el detalle y abrir el diálogo `Historial del turno`, con un solo diálogo abierto (DD-34 P15), y pedir `GET /turnos/{id}/auditoria`.

#### Scenario: Recepcionista abre el historial
- **GIVEN** dada una recepcionista con el detalle abierto de un turno
- **WHEN** cuando elige `Ver historial`
- **THEN** entonces hay un solo diálogo abierto, `Historial del turno`, y se hizo `GET /turnos/00000000-0000-4000-8000-0000000000f1/auditoria`

#### Scenario: Turno cancelado y pasado
- **GIVEN** dado el reloj en 2026-11-09 12:00 hora local, una recepcionista con `Mostrar cancelados` activa y un turno `cancelado` de las 10:00 de ese día
- **WHEN** cuando abre su detalle
- **THEN** entonces se ve `Ver historial` y no se ven `Reprogramar` ni `Cancelar turno`

#### Scenario: Odontólogo sin historial
- **GIVEN** dada una sesión de `odontologo` y un turno de su profesional
- **WHEN** cuando abre su detalle
- **THEN** entonces no se ve `Ver historial` y no se hizo ningún pedido a `/turnos/{id}/auditoria`

#### Scenario: Cerrar el historial
- **GIVEN** dado el diálogo `Historial del turno` abierto
- **WHEN** cuando se elige `Cerrar`
- **THEN** entonces no queda ningún diálogo abierto y se sigue viendo la agenda

### Requirement: Registros del historial
Cada registro SHALL mostrarse en el orden de la API (DD-25 c) con su acción (`Creación`, `Reprogramación` o `Cancelación`), su `ocurrido_en` como `DD/MM/AAAA HH:MM` en `America/Argentina/Buenos_Aires` y su autor: `Vos` si `usuario_id` es el usuario de la sesión, `Otro usuario` si no. El `usuario_id` MUST NOT mostrarse (DD-25 f, design D10).

#### Scenario: Tres registros en orden
- **GIVEN** dada una respuesta con un registro `crear` del usuario de la sesión, uno `reprogramar` y uno `cancelar` de otro usuario, en ese orden
- **WHEN** cuando se muestra el historial
- **THEN** entonces se ven, en ese orden, `Creación` con `Vos`, `Reprogramación` con `Otro usuario` y `Cancelación` con `Otro usuario`, y no se ve ningún `usuario_id`

#### Scenario: Instante en hora local
- **GIVEN** dada la suite en una zona horaria distinta de la del consultorio y un registro con `ocurrido_en` `2026-11-09T12:00:00Z`
- **WHEN** cuando se muestra
- **THEN** entonces se ve `09/11/2026 09:00`

#### Scenario: Sesión sin usuario
- **GIVEN** dada una sesión cuyo token no tiene `sub` y un registro `crear`
- **WHEN** cuando se muestra
- **THEN** entonces su autor es `Otro usuario`

### Requirement: Datos de una creación
Un registro `crear` SHALL mostrar los valores iniciales de `valores_nuevos`: horario (`DD/MM/AAAA HH:MM a HH:MM`; un turno nunca cruza la medianoche, porque debe entrar en una franja de un mismo día, DD-27 c y e), profesional, prestación, sillón (`Sin sillón` si es nulo) y duración en minutos. Los nombres MUST resolverse con los catálogos de la agenda, incluidos los recursos desactivados, y un id ausente MUST verse con el texto genérico de la agenda.

#### Scenario: Valores iniciales
- **GIVEN** dado un registro `crear` con `valores_nuevos` de "Ana Ficticia", "Limpieza", "Sillón 1", inicio `2026-11-12T10:00:00-03:00`, fin `2026-11-12T10:45:00-03:00` y 45 minutos
- **WHEN** cuando se muestra
- **THEN** entonces se ve `12/11/2026 10:00 a 10:45`, `Ficticia, Ana`, `Limpieza`, `Sillón 1` y `45 min`

#### Scenario: Recurso fuera del catálogo
- **GIVEN** dado un registro `crear` cuyo `sillon_id` no está en el catálogo cargado
- **WHEN** cuando se muestra
- **THEN** entonces el sillón se ve como `Sillón no disponible`, sin el id

### Requirement: Datos de una reprogramación
Un registro `reprogramar` SHALL mostrar solo los datos que difieren entre `valores_previos` y `valores_nuevos` (horario, profesional, sillón y duración), cada uno como `antes → después`. Un sillón nulo MUST verse como `Sin sillón`, igual que en la creación, porque un cambio de `requiere_sillon` de la prestación puede quitar o sumar el sillón al reprogramar (DD-26, Consecuencias). Si no cambió ninguno, MUST mostrar `Sin cambios en los datos.`, porque la API audita también la reprogramación sin cambios (DD-25 g).

#### Scenario: Cambio de horario y sillón
- **GIVEN** dado un registro `reprogramar` que pasa de 12/11 10:00 a 10:45 en "Sillón 1" a 12/11 11:00 a 11:45 en "Sillón 2", con el mismo profesional y la misma duración
- **WHEN** cuando se muestra
- **THEN** entonces se ve `Horario: 12/11/2026 10:00 a 10:45 → 12/11/2026 11:00 a 11:45` y `Sillón: Sillón 1 → Sillón 2`, y no se ven líneas de profesional ni de duración

#### Scenario: Sillón quitado al reprogramar
- **GIVEN** dado un registro `reprogramar` con `sillon_id` previo de "Sillón 1" y nuevo nulo, con el mismo horario, profesional y duración
- **WHEN** cuando se muestra
- **THEN** entonces se ve `Sillón: Sillón 1 → Sin sillón` y ninguna otra línea de cambios

#### Scenario: Reprogramación sin cambios
- **GIVEN** dado un registro `reprogramar` con `valores_previos` iguales a `valores_nuevos`
- **WHEN** cuando se muestra
- **THEN** entonces se ve `Sin cambios en los datos.`

### Requirement: Datos de una cancelación
Un registro `cancelar` SHALL mostrar `Motivo: ` seguido de `motivo_cancelacion` de `valores_nuevos`, o `Sin motivo` si es nulo.

#### Scenario: Cancelación con motivo
- **GIVEN** dado un registro `cancelar` con `motivo_cancelacion` "Viaje"
- **WHEN** cuando se muestra
- **THEN** entonces se ve `Motivo: Viaje`

#### Scenario: Cancelación sin motivo
- **GIVEN** dado un registro `cancelar` con `motivo_cancelacion` nulo
- **WHEN** cuando se muestra
- **THEN** entonces se ve `Sin motivo`

### Requirement: Historial sin datos del paciente
El historial SHALL omitir el paciente, que no cambia al reprogramar (DD-23), y MUST NOT pedir `/pacientes` ni mostrar `paciente_id` (minimización de datos, DD-25 b).

#### Scenario: Sin paciente
- **GIVEN** dado un historial con registros `crear` y `reprogramar`
- **WHEN** cuando se muestra
- **THEN** entonces no se ve el `paciente_id` y no se hizo ningún pedido a `/pacientes`

### Requirement: Historial vacío y errores
Un historial vacío SHALL mostrar `Este turno no tiene registros de auditoría.` (DD-25). `404 turno_inexistente` MUST mostrar `Este turno ya no existe.`; un `403`, `No tenés permiso para ver esta información.` sin cerrar la sesión; una falla de red, el `mensaje` del error con `Reintentar`.

#### Scenario: Sin registros
- **GIVEN** dada una respuesta `200` con `[]`
- **WHEN** cuando se abre el historial
- **THEN** entonces se ve `Este turno no tiene registros de auditoría.`

#### Scenario: Turno inexistente
- **GIVEN** dada una respuesta `404` con `{"detail": {"codigo": "turno_inexistente", "mensaje": "..."}}`
- **WHEN** cuando se abre el historial
- **THEN** entonces se ve `Este turno ya no existe.`

#### Scenario: Rol desactualizado
- **GIVEN** dada una sesión con rol `recepcionista` en el token y una respuesta `403` con código `rol_insuficiente`
- **WHEN** cuando se abre el historial
- **THEN** entonces se ve `No tenés permiso para ver esta información.` y el token sigue guardado

#### Scenario: Falla de red y reintento
- **GIVEN** dado un `GET /turnos/{id}/auditoria` que falla por red
- **WHEN** cuando se abre el historial, y luego se elige `Reintentar` y la API responde `200` con un registro
- **THEN** entonces primero se ve `No se pudo conectar con el servidor.`, y después el registro sin el error
