## MODIFIED Requirements

### Requirement: Alta exitosa
Un envío válido MUST hacer un único `POST /turnos`. Ante un `201`, MUST cerrar el formulario, confirmar con el día y la hora del turno y mostrar el turno creado (D20): si el día del turno en `America/Argentina/Buenos_Aires` cae dentro del período visible, MUST releer la agenda del período en curso; si cae fuera, la agenda MUST navegar a ese día cambiando solo `fecha` en la URL, conservando la vista, los filtros y el resto de los parámetros, de modo que la lectura del período nuevo lo muestre. Con un pedido en curso, MUST NOT enviarse otro.

#### Scenario: Turno creado
- **GIVEN** dado un formulario completo con paciente, profesional, prestación, sillón, fecha `2026-11-12` y hora `10:00`
- **WHEN** cuando se envía y la API responde `201`
- **THEN** entonces el formulario se cierra, se hace un `GET /turnos` nuevo y se ve `Turno creado para el 12/11 a las 10:00.`

#### Scenario: Doble envío
- **GIVEN** dado un `POST /turnos` sin responder
- **WHEN** cuando se intenta enviar otra vez
- **THEN** entonces el botón de envío está deshabilitado y hubo un solo `POST /turnos`

#### Scenario: Relectura fallida después del alta
- **GIVEN** dado un formulario completo y una agenda con datos en pantalla
- **WHEN** cuando se envía, la API responde `201` y el `GET /turnos` posterior falla por red
- **THEN** entonces el formulario se cierra, se ve la confirmación del turno creado y se ve `No se pudo conectar con el servidor.` junto con los datos anteriores

#### Scenario: Turno creado para otro día en la vista diaria
- **GIVEN** dada la agenda en la vista diaria del 2026-11-09 con un filtro de profesional, y un formulario completo para el `2026-11-10`
- **WHEN** cuando se envía y la API responde `201`
- **THEN** entonces la URL pasa a `fecha=2026-11-10` conservando `vista` y `profesional`, el último `GET /turnos` pide ese día, se ve el rótulo `Martes 10/11/2026`, el turno en pantalla y `Turno creado para el 10/11 a las 10:00.`

#### Scenario: Turno creado dentro de la semana visible
- **GIVEN** dada la agenda en la vista semanal del 2026-11-09 al 2026-11-15, y un formulario completo para el `2026-11-13`
- **WHEN** cuando se envía y la API responde `201`
- **THEN** entonces la URL no cambia, se hace un `GET /turnos` nuevo del mismo rango y se ve la confirmación

#### Scenario: Turno creado para otra semana en la vista semanal
- **GIVEN** dada la agenda en la vista semanal del 2026-11-09 al 2026-11-15, y un formulario completo para el `2026-11-17`
- **WHEN** cuando se envía y la API responde `201`
- **THEN** entonces la URL pasa a `fecha=2026-11-17` con `vista=semana` y se ve el rótulo `Semana del 16/11 al 22/11/2026`

#### Scenario: Día del turno en la zona del consultorio
- **GIVEN** dado un navegador en `Asia/Tokyo`, la agenda en la vista diaria del 2026-11-12 y un formulario para el `2026-11-12` a las `22:00`, que en Tokio ya es el día 13
- **WHEN** cuando se envía y la API responde `201`
- **THEN** entonces la URL no cambia y se hace un `GET /turnos` nuevo del 2026-11-12

## ADDED Requirements

### Requirement: Agenda sigue al turno reprogramado
Ante un `200` de la reprogramación, MUST valer la misma regla que para el alta (D20): si el nuevo día del turno en la zona del consultorio cae fuera del período visible, la agenda MUST navegar a ese día cambiando solo `fecha`; si cae dentro, MUST releer el período en curso. `Turno reprogramado.` MUST seguir mostrándose en ambos casos.

#### Scenario: Reprogramado a otro día en la vista diaria
- **GIVEN** dado un turno visible del 2026-11-09 en la vista diaria
- **WHEN** cuando se lo reprograma al `2026-11-11` y la API responde `200`
- **THEN** entonces la URL pasa a `fecha=2026-11-11`, se ve el rótulo `Miércoles 11/11/2026` y `Turno reprogramado.`

#### Scenario: Reprogramado dentro del período visible
- **GIVEN** dado un turno visible en la vista diaria del 2026-11-09
- **WHEN** cuando se cambia solo la hora y la API responde `200`
- **THEN** entonces la URL no cambia y se hace un `GET /turnos` nuevo del mismo día
