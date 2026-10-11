# Spec Delta

## ADDED Requirements

### Requirement: Cancelación de un turno programado
El sistema SHALL exponer `POST /turnos/{id}/cancelar`. Cancelar un turno `programado` cuyo inicio todavía no llegó MUST cambiar su `estado` a `cancelado` y responder `200` con el turno actualizado, sus instantes expresados en `America/Argentina/Buenos_Aires`. El turno MUST NOT borrarse: se conserva con sus datos originales (DD-08). Sin autenticación en este change.

#### Scenario: Turno futuro cancelado
- **GIVEN** dado un turno `programado` del profesional A en el sillón 1 con inicio 2026-10-08 10:00-03:00 y fin 10:45-03:00, y que el reloj marca 2026-10-07 09:00 hora local
- **WHEN** cuando se envía `POST /turnos/{id}/cancelar` para ese turno
- **THEN** entonces la respuesta es `200`, el turno tiene `estado = cancelado`, `inicio` 2026-10-08T10:00-03:00 y `fin` 2026-10-08T10:45-03:00, y en la base la fila sigue existiendo con `estado = 'cancelado'` y los mismos profesional, sillón, paciente, prestación, inicio y fin

### Requirement: Motivo de cancelación opcional
El body del request de cancelación y su motivo SHALL ser opcionales. Si se informa un motivo, el sistema MUST guardarlo en `motivo_cancelacion` sin espacios iniciales ni finales y devolverlo en la respuesta; un motivo ausente, vacío o solo con espacios MUST quedar nulo. Un motivo de más de 255 caracteres MUST responder `422` sin cancelar el turno.

#### Scenario: Cancelación con motivo
- **GIVEN** dado un turno `programado` futuro
- **WHEN** cuando se cancela enviando `{"motivo": "  El paciente avisó que está con fiebre  "}`
- **THEN** entonces la respuesta es `200` y `motivo_cancelacion` vale "El paciente avisó que está con fiebre", también en la base

#### Scenario: Cancelación sin body
- **GIVEN** dado un turno `programado` futuro
- **WHEN** cuando se envía `POST /turnos/{id}/cancelar` sin body
- **THEN** entonces la respuesta es `200`, el turno queda `cancelado` y `motivo_cancelacion` es nulo

#### Scenario: Motivo en blanco
- **GIVEN** dado un turno `programado` futuro
- **WHEN** cuando se cancela enviando `{"motivo": "   "}`
- **THEN** entonces la respuesta es `200` y `motivo_cancelacion` es nulo

#### Scenario: Motivo demasiado largo
- **GIVEN** dado un turno `programado` futuro
- **WHEN** cuando se cancela enviando un motivo de 256 caracteres
- **THEN** entonces la respuesta es `422` y el turno sigue `programado`

### Requirement: La cancelación libera el horario de inmediato
Un turno cancelado MUST dejar de contar para la verificación de solape por profesional, por sillón y por paciente, tanto en la aplicación como en la base de datos (RN-AG-07). Inmediatamente después de cancelarlo MUST poder crearse otro turno en el mismo intervalo con los mismos recursos.

#### Scenario: Cancelar y volver a reservar el mismo horario
- **GIVEN** dado un turno `programado` del profesional A, sillón 1 y paciente P de 10:00 a 10:45 del día siguiente
- **WHEN** cuando se cancela ese turno y luego se envía `POST /turnos` con el profesional A, sillón 1, paciente P y el mismo horario
- **THEN** entonces la cancelación responde `200`, el alta responde `201` y en la base quedan dos filas en ese intervalo: una `cancelado` y una `programado`

#### Scenario: El horario liberado lo toma otro paciente
- **GIVEN** dado un turno `programado` del profesional A, sillón 1 y paciente P de 10:00 a 10:45 del día siguiente
- **WHEN** cuando se cancela ese turno y luego se crea un turno del profesional A, sillón 1 y paciente Q de 10:15 a 11:00
- **THEN** entonces el alta responde `201`

#### Scenario: Antes de cancelar el horario sigue ocupado
- **GIVEN** dado un turno `programado` del profesional A de 10:00 a 10:45 del día siguiente
- **WHEN** cuando se crea un turno del profesional A de 10:00 a 10:45 sin haber cancelado el primero
- **THEN** entonces la respuesta es `409` indicando el recurso `profesional`

### Requirement: Cancelable solo antes del inicio
Un turno MUST poder cancelarse solo mientras el instante actual del reloj del sistema sea anterior a su inicio (RN-AG-13). Un turno cuyo inicio es igual o anterior al instante actual se considera iniciado o pasado y su cancelación MUST responder `409` sin modificar el turno. No hay política de cancelación tardía: cancelar un minuto antes del inicio MUST aceptarse (DD-14).

#### Scenario: Cancelación un minuto antes del inicio
- **GIVEN** dado un turno `programado` con inicio 2026-10-07 10:00 hora local y que el reloj marca 2026-10-07 09:59 hora local
- **WHEN** cuando se cancela ese turno
- **THEN** entonces la respuesta es `200` y el turno queda `cancelado`

#### Scenario: Cancelación en el instante exacto del inicio
- **GIVEN** dado un turno `programado` con inicio 2026-10-07 10:00 hora local y que el reloj marca 2026-10-07 10:00 hora local
- **WHEN** cuando se cancela ese turno
- **THEN** entonces la respuesta es `409` y el turno sigue `programado`

#### Scenario: Turno en curso
- **GIVEN** dado un turno `programado` de 10:00 a 10:45 hora local y que el reloj marca 10:20 hora local del mismo día
- **WHEN** cuando se cancela ese turno
- **THEN** entonces la respuesta es `409` y el turno sigue `programado`

#### Scenario: Turno pasado
- **GIVEN** dado un turno `programado` del día anterior al que marca el reloj
- **WHEN** cuando se cancela ese turno
- **THEN** entonces la respuesta es `409` y el turno sigue `programado`

### Requirement: Turno ya cancelado
Cancelar un turno que ya está `cancelado` MUST responder `409` y MUST NOT modificar el turno, incluido su `motivo_cancelacion` (DD-22: la operación no es idempotente). Si el turno está cancelado y además ya inició, el conflicto informado MUST ser el de turno ya cancelado.

#### Scenario: Segunda cancelación del mismo turno
- **GIVEN** dado un turno futuro cancelado con motivo "Viaje imprevisto"
- **WHEN** cuando se lo vuelve a cancelar con motivo "Otro motivo"
- **THEN** entonces la respuesta es `409` indicando que el turno ya está cancelado, y `motivo_cancelacion` sigue siendo "Viaje imprevisto"

#### Scenario: Turno cancelado y pasado
- **GIVEN** dado un turno cancelado cuyo inicio ya pasó según el reloj del sistema
- **WHEN** cuando se lo cancela
- **THEN** entonces la respuesta es `409` indicando que el turno ya está cancelado

### Requirement: Turno a cancelar inexistente
Si el `id` del path no corresponde a ningún turno, el sistema MUST responder `404` (recurso del path, DD-21). Un `id` que no es un identificador válido MUST responder `422`.

#### Scenario: Turno inexistente
- **WHEN** cuando se envía `POST /turnos/{id}/cancelar` con un `id` con formato válido que no existe
- **THEN** entonces la respuesta es `404`

#### Scenario: Identificador con formato inválido
- **WHEN** cuando se envía `POST /turnos/no-es-un-id/cancelar`
- **THEN** entonces la respuesta es `422`

### Requirement: Cancelaciones simultáneas del mismo turno
Ante dos o más pedidos simultáneos de cancelación del mismo turno, exactamente uno MUST tener éxito y los demás MUST recibir `409` por turno ya cancelado; el motivo persistido MUST ser el del pedido que tuvo éxito.

#### Scenario: Doble cancelación concurrente
- **GIVEN** dados N pedidos simultáneos de cancelación del mismo turno `programado` futuro, cada uno en su propia conexión y con un motivo distinto
- **WHEN** cuando todos se ejecutan a la vez
- **THEN** entonces exactamente uno tiene éxito, los demás reciben conflicto por turno ya cancelado, y en la base el turno queda `cancelado` con el motivo del pedido exitoso
