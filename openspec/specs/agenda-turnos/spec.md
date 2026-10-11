# agenda-turnos Specification

## Purpose
Permitir que la recepción agende turnos con duración propia por prestación, garantizando que ningún profesional, sillón ni paciente quede con dos turnos activos superpuestos, con la garantía asegurada por la base de datos y un contrato de errores HTTP claro.

## Requirements

### Requirement: Creación de un turno válido
El sistema SHALL exponer `POST /turnos` que recibe profesional, paciente, prestación, sillón opcional, inicio (con zona horaria) y duración opcional en minutos. Un turno válido MUST persistirse con `estado = programado`, `inicio` y `fin` almacenados en UTC, y responder `201` con el turno creado, sus instantes expresados en `America/Argentina/Buenos_Aires`. Sin autenticación en este change, el autor del turno (`creado_por`) MUST quedar vacío.

#### Scenario: Turno con sillón creado
- **GIVEN** dado un profesional, un paciente, un sillón activos y la prestación "Limpieza" (45 min, requiere sillón), y que el reloj marca 2026-10-07 09:00 hora local
- **WHEN** cuando se envía `POST /turnos` con esos recursos e inicio 2026-10-08 10:00-03:00
- **THEN** entonces la respuesta es `201`, el turno tiene `estado = programado`, `inicio` 2026-10-08T10:00-03:00, `fin` 2026-10-08T10:45-03:00 y `creado_por` vacío, y en la base `inicio` vale 2026-10-08T13:00Z

#### Scenario: Inicio sin zona horaria rechazado
- **WHEN** cuando se envía `POST /turnos` con un inicio sin zona horaria (por ejemplo `2026-10-08T10:00:00`)
- **THEN** entonces la respuesta es `422` y no se persiste ningún turno

### Requirement: Duración efectiva por defecto y ajustable
La duración efectiva del turno SHALL ser la `duracion_min` de la prestación cuando el request no informa duración, y la informada cuando sí lo hace (RN-AG-04). El sistema MUST calcular `fin = inicio + duración efectiva` y persistir esa duración efectiva en el turno.

#### Scenario: Duración por defecto de la prestación
- **GIVEN** dada la prestación "Limpieza" con duración de 45 minutos
- **WHEN** cuando se crea un turno a las 10:00 sin informar duración
- **THEN** entonces el turno queda con `duracion_min = 45` y `fin` a las 10:45

#### Scenario: Duración ajustada por la recepción
- **GIVEN** dada la prestación "Limpieza" con duración de 45 minutos
- **WHEN** cuando se crea un turno a las 10:00 informando `duracion_min = 60`
- **THEN** entonces el turno queda con `duracion_min = 60` y `fin` a las 11:00

### Requirement: Duración y grilla de 5 minutos
La duración efectiva MUST ser mayor que cero, múltiplo de 5 y no mayor a 480 minutos, y el inicio MUST estar alineado a 5 minutos (minutos múltiplo de 5, segundos y fracciones en cero) evaluado en hora local `America/Argentina/Buenos_Aires` (DD-15). Cualquier violación MUST responder `422` sin persistir el turno.

#### Scenario: Duración no múltiplo de 5
- **WHEN** cuando se crea un turno informando `duracion_min = 42`
- **THEN** entonces la respuesta es `422` y no se persiste ningún turno

#### Scenario: Duración mayor a 480 minutos
- **WHEN** cuando se crea un turno informando `duracion_min = 485`
- **THEN** entonces la respuesta es `422`

#### Scenario: Duración de 480 minutos aceptada
- **WHEN** cuando se crea un turno a las 08:00 informando `duracion_min = 480`
- **THEN** entonces la respuesta es `201` y `fin` es a las 16:00

#### Scenario: Duración cero o negativa
- **WHEN** cuando se crea un turno informando `duracion_min = 0`
- **THEN** entonces la respuesta es `422`

#### Scenario: Inicio no alineado a 5 minutos
- **WHEN** cuando se crea un turno con inicio a las 10:07 hora local
- **THEN** entonces la respuesta es `422`

#### Scenario: Inicio con segundos
- **WHEN** cuando se crea un turno con inicio a las 10:05:30 hora local
- **THEN** entonces la respuesta es `422`

### Requirement: Rechazo de inicio en el pasado
El sistema MUST rechazar con `422` la creación de un turno cuyo inicio sea anterior al instante actual del reloj del sistema (RN-AG-12).

#### Scenario: Inicio anterior al momento actual
- **GIVEN** dado que el reloj del sistema marca 2026-10-07 09:00 hora local
- **WHEN** cuando se crea un turno con inicio 2026-10-07 08:55 hora local
- **THEN** entonces la respuesta es `422` y no se persiste ningún turno

#### Scenario: Inicio posterior al momento actual
- **GIVEN** dado que el reloj del sistema marca 2026-10-07 09:00 hora local
- **WHEN** cuando se crea un turno válido con inicio 2026-10-07 09:05 hora local
- **THEN** entonces la respuesta es `201`

### Requirement: Coherencia del sillón con la prestación
Si la prestación requiere sillón, el request MUST informar un sillón; si falta, el sistema MUST responder `422`. Si la prestación no requiere sillón, el turno no ocupa sillón y, si el request informa un sillón, el sistema MUST responder `422` en lugar de ignorarlo o guardarlo (RN-AG-10, DD-21).

#### Scenario: Sillón faltante con prestación que lo requiere
- **GIVEN** dada la prestación "Limpieza" que requiere sillón
- **WHEN** cuando se crea un turno sin `sillon_id`
- **THEN** entonces la respuesta es `422` y no se persiste ningún turno

#### Scenario: Sillón sobrante con prestación que no lo requiere
- **GIVEN** dada la prestación "Consulta" que no requiere sillón
- **WHEN** cuando se crea un turno informando un `sillon_id` válido y activo
- **THEN** entonces la respuesta es `422` y no se persiste ningún turno

#### Scenario: Prestación sin sillón creada sin sillón
- **GIVEN** dada la prestación "Consulta" que no requiere sillón
- **WHEN** cuando se crea un turno sin `sillon_id`
- **THEN** entonces la respuesta es `201` y el turno queda sin sillón asignado

### Requirement: Referencias del body existentes y activas
Profesional, paciente, prestación y sillón referenciados en el body MUST existir y estar activos. Una referencia inexistente MUST responder `422`, igual que una referencia inactiva, indicando qué referencia falla; `404` queda reservado para recursos del path (DD-21).

#### Scenario: Profesional inexistente
- **WHEN** cuando se crea un turno con un `profesional_id` que no existe
- **THEN** entonces la respuesta es `422` indicando la referencia `profesional`, y no `404`

#### Scenario: Paciente, prestación o sillón inexistente
- **WHEN** cuando se crea un turno con un `paciente_id`, `prestacion_id` o `sillon_id` que no existe
- **THEN** entonces la respuesta es `422` indicando la referencia que falla

#### Scenario: Recurso inactivo
- **GIVEN** dado un sillón dado de baja (inactivo)
- **WHEN** cuando se crea un turno con ese sillón
- **THEN** entonces la respuesta es `422` indicando la referencia `sillon`

#### Scenario: Prestación inactiva
- **GIVEN** dada una prestación inactiva
- **WHEN** cuando se crea un turno con esa prestación
- **THEN** entonces la respuesta es `422` indicando la referencia `prestacion`

### Requirement: Sin solape por profesional
Un profesional MUST NOT tener dos turnos activos superpuestos (RN-AG-01). El intento MUST responder `409` sin persistir el nuevo turno.

#### Scenario: Solape por profesional
- **GIVEN** dado un turno activo del profesional A de 10:00 a 10:45 en el sillón 1
- **WHEN** cuando se crea un turno del profesional A de 10:30 a 11:00 en el sillón 2 con otro paciente
- **THEN** entonces la respuesta es `409` indicando el recurso `profesional`, y no se persiste el nuevo turno

### Requirement: Sin solape por sillón
Un sillón MUST NOT tener dos turnos activos superpuestos (RN-AG-02). Un turno sin sillón MUST NOT participar de esta regla.

#### Scenario: Solape por sillón
- **GIVEN** dado un turno activo en el sillón 1 de 10:00 a 10:45 con el profesional A
- **WHEN** cuando se crea un turno en el sillón 1 de 10:15 a 10:45 con el profesional B y otro paciente
- **THEN** entonces la respuesta es `409` indicando el recurso `sillon`

#### Scenario: Prestación sin sillón no genera conflicto de sillón
- **GIVEN** dado un turno activo sin sillón (prestación "Consulta") de 10:00 a 10:30 con el profesional A
- **WHEN** cuando se crea un turno en el sillón 1 de 10:00 a 10:45 con el profesional B y otro paciente
- **THEN** entonces la respuesta es `201`

### Requirement: Sin solape por paciente
Un paciente MUST NOT tener dos turnos activos superpuestos, aunque sean con profesionales y sillones distintos (RN-AG-14, DD-20).

#### Scenario: Solape por paciente con distinto profesional
- **GIVEN** dado un turno activo del paciente P con el profesional A en el sillón 1 de 10:00 a 10:45
- **WHEN** cuando se crea un turno del paciente P con el profesional B en el sillón 2 de 10:30 a 11:00
- **THEN** entonces la respuesta es `409` indicando el recurso `paciente`

### Requirement: Intervalos semiabiertos e independencia de recursos
Los intervalos de turno SHALL ser semiabiertos `[inicio, fin)`: dos turnos se solapan solo si `inicioA < finB` y `inicioB < finA` (RN-AG-03). Un turno que empieza exactamente cuando termina otro MUST aceptarse, y turnos en el mismo horario sin recursos compartidos MUST aceptarse.

#### Scenario: Turnos contiguos del mismo profesional y sillón
- **GIVEN** dado un turno activo del profesional A en el sillón 1 de 10:00 a 10:45
- **WHEN** cuando se crea un turno del profesional A en el sillón 1 de 10:45 a 11:30 con otro paciente
- **THEN** entonces la respuesta es `201`

#### Scenario: Mismo paciente en turnos contiguos
- **GIVEN** dado un turno activo del paciente P de 10:00 a 10:45 con el profesional A
- **WHEN** cuando se crea un turno del paciente P de 10:45 a 11:15 con el profesional B
- **THEN** entonces la respuesta es `201`

#### Scenario: Mismo horario con recursos distintos
- **GIVEN** dado un turno activo del profesional A, sillón 1 y paciente P de 10:00 a 10:45
- **WHEN** cuando se crea un turno del profesional B, sillón 2 y paciente Q de 10:00 a 10:45
- **THEN** entonces la respuesta es `201`

#### Scenario: Regla de solape en el dominio sin base de datos
- **WHEN** cuando se evalúa la regla de solape con [10:00, 10:45) contra [10:45, 11:30), contra [10:30, 11:00) y contra [09:00, 12:00)
- **THEN** entonces el primero no se solapa y los otros dos sí, sin acceder a la base de datos

### Requirement: Conflicto 409 con todos los recursos en conflicto
Ante un solape, la respuesta `409` MUST listar **todos** los recursos en conflicto (`profesional`, `sillon`, `paciente`) detectados en una verificación previa al alta (DD-21). Las validaciones que responden `422` MUST evaluarse antes que la verificación de solape.

#### Scenario: 409 que lista varios recursos
- **GIVEN** dado un turno activo del profesional A, sillón 1 y paciente P de 10:00 a 10:45
- **WHEN** cuando se crea un turno del profesional A, sillón 1 y paciente P de 10:15 a 11:00
- **THEN** entonces la respuesta es `409` y lista los recursos `profesional`, `sillon` y `paciente`

#### Scenario: Solicitud inválida y en conflicto
- **GIVEN** dado un turno activo del profesional A de 10:00 a 10:45
- **WHEN** cuando se crea un turno del profesional A a las 10:15 con `duracion_min = 42`
- **THEN** entonces la respuesta es `422`, no `409`

### Requirement: Garantía de no superposición en la base de datos
La base de datos MUST impedir por sí misma dos turnos activos superpuestos del mismo profesional, del mismo sillón o del mismo paciente, aunque la escritura no pase por la aplicación (RN-AG-09). Los turnos cancelados MUST NOT contar. Si una carrera esquiva la verificación previa, el rechazo de la base MUST traducirse a `409` indicando el recurso que lo provocó.

#### Scenario: Inserción directa superpuesta rechazada por la base
- **GIVEN** dado un turno activo del profesional A de 10:00 a 10:45 persistido en la base
- **WHEN** cuando se inserta directamente en la base otro turno activo del profesional A de 10:30 a 11:00
- **THEN** entonces la base rechaza la inserción con una violación de exclusión

#### Scenario: Turno cancelado no bloquea el horario
- **GIVEN** dado un turno con `estado = cancelado` del profesional A, sillón 1 y paciente P de 10:00 a 10:45 persistido en la base
- **WHEN** cuando se crea por la API un turno del profesional A, sillón 1 y paciente P de 10:00 a 10:45
- **THEN** entonces la respuesta es `201`

#### Scenario: Concurrencia sobre el mismo horario
- **GIVEN** dados N pedidos simultáneos de alta para el mismo profesional, sillón y horario, cada uno en su propia conexión
- **WHEN** cuando todos se ejecutan a la vez
- **THEN** entonces exactamente uno tiene éxito, los demás reciben conflicto, y en la base queda un solo turno activo en ese horario

#### Scenario: Carrera que esquiva la verificación previa
- **GIVEN** dado que la verificación previa no detecta conflicto pero la base rechaza el alta por la exclusión de sillón
- **WHEN** cuando se procesa el alta
- **THEN** entonces la respuesta es `409` indicando el recurso `sillon`

### Requirement: Integridad del estado y del intervalo en la base
El estado del turno MUST persistirse como texto restringido a `programado` o `cancelado` mediante una restricción CHECK, no como tipo enumerado nativo (DD-21). La base MUST rechazar un turno con `fin` menor o igual que `inicio`.

#### Scenario: Estado inválido rechazado por la base
- **WHEN** cuando se inserta directamente un turno con `estado = 'reprogramado'`
- **THEN** entonces la base rechaza la inserción con una violación de CHECK

#### Scenario: Fin no posterior al inicio rechazado por la base
- **WHEN** cuando se inserta directamente un turno con `fin` igual a `inicio`
- **THEN** entonces la base rechaza la inserción con una violación de CHECK

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
