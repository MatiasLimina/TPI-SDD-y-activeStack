# agenda-turnos Specification

## Purpose
Permitir que la recepción agende turnos con duración propia por prestación, garantizando que ningún profesional, sillón ni paciente quede con dos turnos activos superpuestos, con la garantía asegurada por la base de datos y un contrato de errores HTTP claro.

## Requirements

### Requirement: Creación de un turno válido
El sistema SHALL exponer `POST /turnos` que recibe profesional, paciente, prestación, sillón opcional, inicio (con zona horaria) y duración opcional en minutos. Un turno válido MUST persistirse con `estado = programado`, `inicio` y `fin` almacenados en UTC, y responder `201` con el turno creado, sus instantes expresados en `America/Argentina/Buenos_Aires`. El autor del turno (`creado_por`) MUST ser el usuario autenticado que hizo el alta, y MUST NOT tomarse del body.

#### Scenario: Turno con sillón creado
- **GIVEN** dado un profesional, un paciente, un sillón activos y la prestación "Limpieza" (45 min, requiere sillón), una recepcionista R autenticada, y que el reloj marca 2026-10-07 09:00 hora local
- **WHEN** cuando R envía `POST /turnos` con esos recursos e inicio 2026-10-08 10:00-03:00
- **THEN** entonces la respuesta es `201`, el turno tiene `estado = programado`, `inicio` 2026-10-08T10:00-03:00, `fin` 2026-10-08T10:45-03:00 y `creado_por` igual al id de R, y en la base `inicio` vale 2026-10-08T13:00Z y `creado_por` es el id de R

#### Scenario: Inicio sin zona horaria rechazado
- **WHEN** cuando una recepcionista autenticada envía `POST /turnos` con un inicio sin zona horaria (por ejemplo `2026-10-08T10:00:00`)
- **THEN** entonces la respuesta es `422` y no se persiste ningún turno

#### Scenario: Autor informado en el body ignorado
- **GIVEN** dado dos recepcionistas activas R y S, con R autenticada
- **WHEN** cuando R envía `POST /turnos` con un body válido que además incluye `creado_por` con el id de S
- **THEN** entonces la respuesta es `201` y el turno queda con `creado_por` igual al id de R

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
El sistema SHALL exponer `POST /turnos/{id}/cancelar`. Cancelar un turno `programado` cuyo inicio todavía no llegó MUST cambiar su `estado` a `cancelado` y responder `200` con el turno actualizado, sus instantes expresados en `America/Argentina/Buenos_Aires`. El turno MUST NOT borrarse: se conserva con sus datos originales (DD-08), incluido su `creado_por`. Requiere un usuario autenticado con rol `recepcionista`.

#### Scenario: Turno futuro cancelado
- **GIVEN** dado un turno `programado` del profesional A en el sillón 1 con inicio 2026-10-08 10:00-03:00 y fin 10:45-03:00, una recepcionista autenticada, y que el reloj marca 2026-10-07 09:00 hora local
- **WHEN** cuando la recepcionista envía `POST /turnos/{id}/cancelar` para ese turno
- **THEN** entonces la respuesta es `200`, el turno tiene `estado = cancelado`, `inicio` 2026-10-08T10:00-03:00 y `fin` 2026-10-08T10:45-03:00, y en la base la fila sigue existiendo con `estado = 'cancelado'` y los mismos profesional, sillón, paciente, prestación, inicio y fin

#### Scenario: Cancelar no cambia el autor
- **GIVEN** dado un turno futuro creado por la recepcionista R
- **WHEN** cuando otra recepcionista S lo cancela
- **THEN** entonces la respuesta es `200` y el turno conserva `creado_por` igual al id de R

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

### Requirement: Reprogramación de un turno programado
El sistema SHALL exponer `PATCH /turnos/{id}/reprogramar`. Reprogramar un turno `programado` cuyo inicio todavía no llegó MUST actualizar la misma fila (mismo `id`, paciente, prestación, `creado_por` y `estado = programado`), recalcular `fin = inicio + duración` y responder `200` con el turno, sus instantes en `America/Argentina/Buenos_Aires`. MUST NOT crearse una fila nueva. Requiere un usuario autenticado con rol `recepcionista`.

#### Scenario: Turno movido a un hueco libre
- **GIVEN** dado un turno `programado` del profesional A, sillón 1, paciente P y prestación "Limpieza" (45 min) de 2026-10-08 10:00 a 10:45 hora local, una recepcionista autenticada, y que el reloj marca 2026-10-07 09:00 hora local
- **WHEN** cuando la recepcionista envía `PATCH /turnos/{id}/reprogramar` con `inicio` 2026-10-08T15:00-03:00
- **THEN** entonces la respuesta es `200` con el mismo `id`, `estado = programado`, `inicio` 2026-10-08T15:00-03:00 y `fin` 2026-10-08T15:45-03:00, y en la base esa fila tiene `inicio` 2026-10-08T18:00Z y no existe ninguna otra fila para ese paciente

#### Scenario: Cambio de profesional y de sillón
- **GIVEN** dado un turno `programado` futuro del profesional A en el sillón 1 de 10:00 a 10:45, el profesional B y el sillón 2 activos y libres en ese horario, y una recepcionista autenticada
- **WHEN** cuando se reprograma informando `profesional_id` del profesional B y `sillon_id` del sillón 2
- **THEN** entonces la respuesta es `200`, el turno conserva su `id`, inicio, fin, paciente y prestación, y en la base queda asignado al profesional B y al sillón 2

#### Scenario: Reprogramar no cambia el autor
- **GIVEN** dado un turno futuro creado por la recepcionista R
- **WHEN** cuando otra recepcionista S lo reprograma a un hueco libre
- **THEN** entonces la respuesta es `200` y el turno conserva `creado_por` igual al id de R

### Requirement: Reprogramación parcial
Los campos editables al reprogramar SHALL ser `inicio`, `profesional_id`, `sillon_id` y `duracion_min`. Un campo omitido MUST conservar el valor actual del turno, incluida una duración ajustada, que MUST NOT volver a la duración de la prestación (DD-23). Un campo informado con valor nulo MUST distinguirse de uno omitido: `sillon_id` nulo quita el sillón del turno resultante, y `inicio`, `profesional_id` o `duracion_min` nulos MUST responder `422` sin modificar el turno.

#### Scenario: Solo un nuevo inicio conserva la duración ajustada
- **GIVEN** dado un turno futuro de la prestación "Limpieza" (45 min) creado a las 10:00 con `duracion_min = 60`
- **WHEN** cuando se reprograma informando solo `inicio` a las 15:00 del mismo día
- **THEN** entonces la respuesta es `200`, el turno queda con `duracion_min = 60`, `fin` a las 16:00, y los mismos profesional y sillón

#### Scenario: Solo una nueva duración conserva el inicio
- **GIVEN** dado un turno futuro de 10:00 a 10:45 de la prestación "Limpieza"
- **WHEN** cuando se reprograma informando solo `duracion_min = 30`
- **THEN** entonces la respuesta es `200`, el turno conserva el inicio 10:00 y queda con `fin` a las 10:30

#### Scenario: Volver a la duración de la prestación informándola
- **GIVEN** dado un turno futuro de la prestación "Limpieza" (45 min) creado a las 10:00 con `duracion_min = 60`
- **WHEN** cuando se reprograma informando `duracion_min = 45`
- **THEN** entonces la respuesta es `200` y el turno queda con `duracion_min = 45` y `fin` a las 10:45

#### Scenario: Body sin campos editables
- **GIVEN** dado un turno `programado` futuro de 10:00 a 10:45 cuyas referencias siguen activas
- **WHEN** cuando se reprograma enviando `{}`
- **THEN** entonces la respuesta es `200` y el turno sigue de 10:00 a 10:45 con los mismos profesional, sillón y duración

#### Scenario: Nulo explícito en un campo obligatorio
- **GIVEN** dado un turno `programado` futuro de 10:00 a 10:45
- **WHEN** cuando se reprograma enviando `{"inicio": null}`, o `{"profesional_id": null}`, o `{"duracion_min": null}`
- **THEN** entonces la respuesta es `422` y el turno sigue de 10:00 a 10:45 con su profesional y su duración

#### Scenario: Sillón nulo explícito con prestación que lo requiere
- **GIVEN** dado un turno futuro de la prestación "Limpieza", que requiere sillón, en el sillón 1
- **WHEN** cuando se reprograma enviando `{"sillon_id": null}`
- **THEN** entonces la respuesta es `422` por sillón requerido y el turno sigue en el sillón 1

#### Scenario: Sillón informado con prestación que no lo requiere
- **GIVEN** dado un turno futuro de la prestación "Consulta", que no requiere sillón, sin sillón asignado
- **WHEN** cuando se reprograma informando un `sillon_id` válido y activo
- **THEN** entonces la respuesta es `422` por sillón que no corresponde y el turno sigue sin sillón

### Requirement: Paciente y prestación no editables
Si el body de la reprogramación incluye `paciente_id` o `prestacion_id`, con cualquier valor, el sistema MUST responder `422` con el código `campo_no_editable`, la lista de los campos rechazados y un mensaje que indique a la recepcionista cancelar el turno y crear uno nuevo, sin modificar el turno (DD-23). Este rechazo MUST evaluarse antes que el estado del turno. Otros campos desconocidos MUST ignorarse.

#### Scenario: Cambio de paciente rechazado
- **GIVEN** dado un turno `programado` futuro
- **WHEN** cuando se reprograma informando `paciente_id` y un nuevo `inicio`
- **THEN** entonces la respuesta es `422` con código `campo_no_editable`, la lista de campos `["paciente_id"]` y un mensaje que indica cancelar el turno y crear uno nuevo, y el turno no cambia

#### Scenario: Paciente y prestación rechazados juntos
- **GIVEN** dado un turno `programado` futuro
- **WHEN** cuando se reprograma informando `paciente_id` y `prestacion_id`
- **THEN** entonces la respuesta es `422` con código `campo_no_editable` y la lista de campos `["paciente_id", "prestacion_id"]`

#### Scenario: Mismo paciente informado igualmente rechazado
- **GIVEN** dado un turno `programado` futuro del paciente P
- **WHEN** cuando se reprograma informando `paciente_id` del mismo paciente P
- **THEN** entonces la respuesta es `422` con código `campo_no_editable`

#### Scenario: Campo no editable sobre un turno cancelado
- **GIVEN** dado un turno cancelado
- **WHEN** cuando se lo reprograma informando `prestacion_id`
- **THEN** entonces la respuesta es `422` con código `campo_no_editable`, no `409`

#### Scenario: Campo desconocido ignorado
- **GIVEN** dado un turno `programado` futuro de 10:00 a 10:45
- **WHEN** cuando se reprograma informando `inicio` a las 15:00 y un campo `observaciones`
- **THEN** entonces la respuesta es `200` y el turno queda de 15:00 a 15:45

### Requirement: Misma validación que el alta al reprogramar
Reprogramar MUST aplicar al turno resultante las mismas validaciones que el alta: referencias existentes y activas, duración y grilla de 5 minutos, inicio no anterior al instante actual, sillón coherente con la prestación, horario de atención y bloqueos del profesional (RN-AG-05, RN-AG-06), todas con `422` (RN-AG-08). Esas validaciones MUST evaluarse antes que el solape, y ante cualquier `422` el turno MUST quedar intacto. Los escenarios de bloqueos asumen el reloj en 2026-10-07 09:00 local.

#### Scenario: Duración inválida
- **GIVEN** dado un turno `programado` futuro de 10:00 a 10:45
- **WHEN** cuando se reprograma informando `duracion_min = 42`
- **THEN** entonces la respuesta es `422` y en la base el turno sigue de 10:00 a 10:45 con `duracion_min = 45`

#### Scenario: Inicio no alineado a 5 minutos
- **GIVEN** dado un turno `programado` futuro de 10:00 a 10:45
- **WHEN** cuando se reprograma informando `inicio` a las 15:07 hora local
- **THEN** entonces la respuesta es `422` y el turno sigue de 10:00 a 10:45

#### Scenario: Inicio sin zona horaria
- **WHEN** cuando se reprograma un turno informando un `inicio` sin zona horaria
- **THEN** entonces la respuesta es `422` y el turno no cambia

#### Scenario: Nuevo inicio en el pasado
- **GIVEN** dado un turno `programado` con inicio 2026-10-08 10:00 hora local y que el reloj marca 2026-10-07 09:00 hora local
- **WHEN** cuando se lo reprograma con `inicio` 2026-10-07 08:55 hora local
- **THEN** entonces la respuesta es `422` y el turno sigue con inicio 2026-10-08 10:00

#### Scenario: Profesional destino inactivo
- **GIVEN** dado un turno `programado` futuro y un profesional B inactivo
- **WHEN** cuando se lo reprograma informando `profesional_id` del profesional B
- **THEN** entonces la respuesta es `422` indicando la referencia `profesional` y el turno sigue con su profesional original

#### Scenario: Sillón destino inexistente
- **WHEN** cuando se reprograma un turno `programado` futuro informando un `sillon_id` que no existe
- **THEN** entonces la respuesta es `422` indicando la referencia `sillon`, y no `404`

#### Scenario: Reprogramación inválida y en conflicto
- **GIVEN** dado un turno activo del profesional A de 15:00 a 15:45 y otro turno `programado` futuro del profesional A de 10:00 a 10:45
- **WHEN** cuando se reprograma el segundo a las 15:15 con `duracion_min = 42`
- **THEN** entonces la respuesta es `422`, no `409`

#### Scenario: Nuevo inicio fuera del horario
- **GIVEN** dado el profesional A con la franja del jueves de 09:00 a 13:00 y un turno `programado` de A el jueves 2026-10-08 de 10:00 a 10:45
- **WHEN** cuando se lo reprograma informando `inicio` 2026-10-08 12:30 hora local
- **THEN** entonces la respuesta es `422` con código `fuera_de_horario` y el turno sigue de 10:00 a 10:45

#### Scenario: Profesional destino sin franja ese día
- **GIVEN** dado un turno `programado` del profesional A el jueves 2026-10-08 de 10:00 a 10:45, dentro de su horario, y el profesional B activo sin franjas el jueves
- **WHEN** cuando se lo reprograma informando `profesional_id` de B
- **THEN** entonces la respuesta es `422` con código `fuera_de_horario` y el turno sigue con el profesional A

#### Scenario: Turno que quedó fuera de horario al reprogramar otro campo
- **GIVEN** dado un turno `programado` futuro de A el jueves de 12:30 a 13:15 en el sillón 1, y la franja de A del jueves editada después a 09:00-12:00
- **WHEN** cuando se lo reprograma informando solo `sillon_id` del sillón 2
- **THEN** entonces la respuesta es `422` con código `fuera_de_horario` y el turno sigue en el sillón 1 de 12:30 a 13:15

#### Scenario: Ampliar la duración más allá de la franja
- **GIVEN** dado el profesional A con la franja del jueves de 09:00 a 13:00 y un turno `programado` de A el jueves de 12:15 a 13:00
- **WHEN** cuando se lo reprograma informando solo `duracion_min = 60`
- **THEN** entonces la respuesta es `422` con código `fuera_de_horario` y el turno sigue de 12:15 a 13:00

#### Scenario: Reprogramación que termina justo al cierre de la franja
- **GIVEN** dado el profesional A con la franja del jueves de 09:00 a 13:00 y un turno `programado` de A de 45 minutos el jueves 2026-10-08 de 10:00 a 10:45
- **WHEN** cuando se lo reprograma informando `inicio` 2026-10-08 12:15 hora local
- **THEN** entonces la respuesta es `200` con `inicio` 2026-10-08T12:15-03:00 y `fin` 2026-10-08T13:00-03:00, y en la base el turno quedó así

#### Scenario: Nuevo inicio dentro de un bloqueo
- **GIVEN** dado un bloqueo del profesional A el jueves 2026-10-08 de 10:00 a 12:00 hora local y un turno `programado` de A el 2026-10-08 de 15:00 a 15:45
- **WHEN** cuando se lo reprograma informando `inicio` 2026-10-08 10:30 hora local
- **THEN** entonces la respuesta es `422` con código `turno_en_bloqueo` y el turno sigue de 15:00 a 15:45

#### Scenario: Profesional destino con un bloqueo en el horario
- **GIVEN** dado un turno `programado` del profesional A el jueves 2026-10-08 de 10:30 a 11:15 y un bloqueo del profesional B el 2026-10-08 de 10:00 a 12:00 hora local
- **WHEN** cuando se lo reprograma informando `profesional_id` de B
- **THEN** entonces la respuesta es `422` con código `turno_en_bloqueo` y el turno sigue con el profesional A

#### Scenario: Ampliar la duración hacia un bloqueo
- **GIVEN** dado un turno `programado` del profesional A el jueves 2026-10-08 de 09:15 a 10:00 y un bloqueo de A el 2026-10-08 de 10:00 a 12:00 hora local
- **WHEN** cuando se lo reprograma informando solo `duracion_min = 60`
- **THEN** entonces la respuesta es `422` con código `turno_en_bloqueo` y el turno sigue de 09:15 a 10:00

#### Scenario: Reprogramación que termina justo al empezar un bloqueo
- **GIVEN** dado un bloqueo del profesional A el jueves 2026-10-08 de 10:00 a 12:00 hora local y un turno `programado` de A de 45 minutos el 2026-10-08 de 15:00 a 15:45
- **WHEN** cuando se lo reprograma informando `inicio` 2026-10-08 09:15 hora local
- **THEN** entonces la respuesta es `200` con `inicio` 2026-10-08T09:15:00-03:00 y `fin` 2026-10-08T10:00:00-03:00, y en la base el turno quedó así

#### Scenario: Reprogramación rechazada por un bloqueo conserva el recordatorio
- **GIVEN** dado un turno `programado` del profesional A el viernes 2026-10-09 de 15:00 a 15:45 con su recordatorio `pendiente`, y un bloqueo de A el 2026-10-09 de 10:00 a 12:00 hora local
- **WHEN** cuando se lo reprograma informando `inicio` 2026-10-09 10:30 hora local
- **THEN** entonces la respuesta es `422` con código `turno_en_bloqueo`, el recordatorio sigue `pendiente` con el mismo `programado_para`, no se crea otro y no se registra auditoría de reprogramación

### Requirement: Sin solape al reprogramar, excluyendo al propio turno
El turno resultante MUST NOT solaparse con otro turno activo del mismo profesional, sillón o paciente (RN-AG-01, RN-AG-02, RN-AG-14); el intento MUST responder `409` listando todos los recursos en conflicto y dejar el turno intacto. El propio turno MUST NOT contar para esta verificación, por lo que solaparse con su intervalo anterior es válido; los turnos cancelados tampoco cuentan.

#### Scenario: Hueco ocupado por otro turno del profesional
- **GIVEN** dado un turno activo del profesional A de 15:00 a 15:45 y otro turno `programado` del profesional A de 10:00 a 10:45 del mismo día futuro
- **WHEN** cuando se reprograma el segundo a las 15:15
- **THEN** entonces la respuesta es `409` indicando el recurso `profesional`, y en la base el segundo turno sigue de 10:00 a 10:45

#### Scenario: Solaparse consigo mismo es válido
- **GIVEN** dado un turno `programado` futuro del profesional A, sillón 1 y paciente P de 10:00 a 10:45, sin otros turnos ese día
- **WHEN** cuando se lo reprograma a las 10:15
- **THEN** entonces la respuesta es `200` y el turno queda de 10:15 a 11:00

#### Scenario: Extender la duración sobre el propio intervalo
- **GIVEN** dado un turno `programado` futuro de 10:00 a 10:45, sin otros turnos ese día
- **WHEN** cuando se lo reprograma informando `duracion_min = 90`
- **THEN** entonces la respuesta es `200` y el turno queda de 10:00 a 11:30

#### Scenario: Solape con otro turno del mismo paciente
- **GIVEN** dado un turno activo del paciente P con el profesional B en el sillón 2 de 12:00 a 12:45, y otro turno `programado` del paciente P con el profesional A en el sillón 1 de 10:00 a 10:45 del mismo día futuro
- **WHEN** cuando se reprograma el segundo a las 12:15
- **THEN** entonces la respuesta es `409` indicando el recurso `paciente` y el segundo turno sigue de 10:00 a 10:45

#### Scenario: 409 que lista varios recursos
- **GIVEN** dado un turno activo del profesional A, sillón 1 y paciente P de 15:00 a 15:45, y otro turno `programado` del profesional A, sillón 1 y paciente P de 10:00 a 10:45 del mismo día futuro
- **WHEN** cuando se reprograma el segundo a las 15:15
- **THEN** entonces la respuesta es `409` y lista los recursos `profesional`, `sillon` y `paciente`

#### Scenario: Reprogramar a un horario contiguo
- **GIVEN** dado un turno activo del profesional A en el sillón 1 de 15:00 a 15:45 y otro turno `programado` del profesional A en el sillón 1 de 10:00 a 10:45 del mismo día futuro, con otro paciente
- **WHEN** cuando se reprograma el segundo a las 15:45
- **THEN** entonces la respuesta es `200` y el turno queda de 15:45 a 16:30

#### Scenario: Un turno cancelado en el destino no bloquea
- **GIVEN** dado un turno cancelado del profesional A, sillón 1 de 15:00 a 15:45 y otro turno `programado` del profesional A, sillón 1 de 10:00 a 10:45 del mismo día futuro
- **WHEN** cuando se reprograma el segundo a las 15:00
- **THEN** entonces la respuesta es `200`

### Requirement: Reprogramable solo antes del inicio
Un turno MUST poder reprogramarse solo mientras el instante actual del reloj del sistema sea anterior a su inicio actual. Si ese inicio es igual o anterior al instante actual, la reprogramación MUST responder `409` con el código `turno_ya_iniciado` sin modificar el turno, aunque el nuevo inicio informado sea futuro (DD-23).

#### Scenario: Reprogramación un minuto antes del inicio
- **GIVEN** dado un turno `programado` con inicio 2026-10-07 10:00 hora local y que el reloj marca 2026-10-07 09:59 hora local
- **WHEN** cuando se lo reprograma a 2026-10-08 10:00 hora local
- **THEN** entonces la respuesta es `200`

#### Scenario: Reprogramación en el instante exacto del inicio
- **GIVEN** dado un turno `programado` con inicio 2026-10-07 10:00 hora local y que el reloj marca 2026-10-07 10:00 hora local
- **WHEN** cuando se lo reprograma a 2026-10-08 10:00 hora local
- **THEN** entonces la respuesta es `409` con código `turno_ya_iniciado` y el turno sigue con inicio 2026-10-07 10:00

#### Scenario: Turno en curso movido al futuro
- **GIVEN** dado un turno `programado` de 10:00 a 10:45 hora local y que el reloj marca 10:20 hora local del mismo día
- **WHEN** cuando se lo reprograma al día siguiente a las 10:00
- **THEN** entonces la respuesta es `409` con código `turno_ya_iniciado` y el turno no cambia

#### Scenario: Turno pasado
- **GIVEN** dado un turno `programado` del día anterior al que marca el reloj
- **WHEN** cuando se lo reprograma a un horario futuro libre
- **THEN** entonces la respuesta es `409` con código `turno_ya_iniciado` y el turno no cambia

### Requirement: Turno cancelado no reprogramable
Reprogramar un turno `cancelado` MUST responder `409` con el código `turno_ya_cancelado`, el mismo que usa la cancelación, y MUST NOT modificar el turno (DD-23). El estado MUST evaluarse antes que el tiempo y antes que las validaciones del turno resultante.

#### Scenario: Turno cancelado
- **GIVEN** dado un turno futuro cancelado de 10:00 a 10:45
- **WHEN** cuando se lo reprograma a las 15:00
- **THEN** entonces la respuesta es `409` con código `turno_ya_cancelado`, y en la base sigue `cancelado` de 10:00 a 10:45

#### Scenario: Turno cancelado y pasado
- **GIVEN** dado un turno cancelado cuyo inicio ya pasó según el reloj del sistema
- **WHEN** cuando se lo reprograma a un horario futuro
- **THEN** entonces la respuesta es `409` con código `turno_ya_cancelado`

#### Scenario: Turno cancelado con datos inválidos
- **GIVEN** dado un turno futuro cancelado
- **WHEN** cuando se lo reprograma informando `duracion_min = 42`
- **THEN** entonces la respuesta es `409` con código `turno_ya_cancelado`, no `422`

### Requirement: Turno a reprogramar inexistente
Si el `id` del path no corresponde a ningún turno, la reprogramación MUST responder `404` (recurso del path, DD-21). Un `id` que no es un identificador válido MUST responder `422`.

#### Scenario: Turno inexistente
- **WHEN** cuando se envía `PATCH /turnos/{id}/reprogramar` con un `id` con formato válido que no existe
- **THEN** entonces la respuesta es `404`

#### Scenario: Identificador con formato inválido
- **WHEN** cuando se envía `PATCH /turnos/no-es-un-id/reprogramar`
- **THEN** entonces la respuesta es `422`

### Requirement: Reprogramaciones simultáneas hacia el mismo horario
Ante dos o más reprogramaciones simultáneas de turnos distintos hacia un mismo horario con un recurso compartido, exactamente una MUST tener éxito y las demás MUST recibir `409` por solape, con sus turnos intactos. La garantía MUST sostenerla la base de datos (RN-AG-09): si una carrera esquiva la verificación previa, el rechazo de la base MUST traducirse a `409` indicando el recurso.

#### Scenario: Turnos distintos movidos a la vez al mismo hueco
- **GIVEN** dados N turnos `programado` futuros del profesional A en horarios distintos y un hueco libre del profesional A, cada reprogramación en su propia conexión
- **WHEN** cuando todos se reprograman a la vez a ese hueco
- **THEN** entonces exactamente una reprogramación tiene éxito, las demás reciben conflicto por solape, en ese hueco queda un solo turno activo y los turnos perdedores conservan su horario original

#### Scenario: Carrera que esquiva la verificación previa
- **GIVEN** dado que la verificación previa no detecta conflicto pero la base rechaza la actualización por la exclusión de profesional
- **WHEN** cuando se procesa la reprogramación
- **THEN** entonces la respuesta es `409` indicando el recurso `profesional` y el turno conserva su horario original

### Requirement: Reprogramación y cancelación simultáneas del mismo turno
Una reprogramación y una cancelación simultáneas del mismo turno MUST serializarse: el resultado final MUST ser el mismo que si se hubieran ejecutado una después de la otra, en el orden en que obtuvieron el turno.

#### Scenario: La cancelación llega primero
- **GIVEN** dado un turno `programado` futuro de 10:00 a 10:45 y una cancelación y una reprogramación a las 15:00 simultáneas, en conexiones propias, donde la cancelación obtiene el turno primero
- **WHEN** cuando ambas terminan
- **THEN** entonces la cancelación tiene éxito, la reprogramación recibe `409` con código `turno_ya_cancelado`, y en la base el turno queda `cancelado` de 10:00 a 10:45

#### Scenario: La reprogramación llega primero
- **GIVEN** dado un turno `programado` futuro de 10:00 a 10:45 y una reprogramación a las 15:00 y una cancelación simultáneas, en conexiones propias, donde la reprogramación obtiene el turno primero
- **WHEN** cuando ambas terminan
- **THEN** entonces ambas tienen éxito y en la base el turno queda `cancelado` de 15:00 a 15:45

### Requirement: Operaciones sobre turnos reservadas a la recepcionista
`POST /turnos`, `POST /turnos/{id}/cancelar` y `PATCH /turnos/{id}/reprogramar` MUST exigir un usuario autenticado con rol `recepcionista` (RN-AU-01, matriz de `03_actores_y_roles.md`, DD-24). Un `odontologo` autenticado MUST recibir `403` con `{"detail": {"codigo": "rol_insuficiente", "mensaje": "Rol insuficiente"}}`. Autenticación y rol MUST evaluarse antes que el body y que la existencia del turno; ante `401` o `403` nada cambia.

#### Scenario: Odontólogo no puede crear turnos
- **GIVEN** dado un odontólogo autenticado y un body de alta válido para su propio profesional
- **WHEN** cuando envía `POST /turnos`
- **THEN** entonces la respuesta es `403` con `detail = {"codigo": "rol_insuficiente", "mensaje": "Rol insuficiente"}` y no se persiste ningún turno

#### Scenario: Odontólogo no puede cancelar ni reprogramar
- **GIVEN** dado un turno `programado` futuro de su propio profesional y un odontólogo autenticado
- **WHEN** cuando envía `POST /turnos/{id}/cancelar`, o `PATCH /turnos/{id}/reprogramar` con un nuevo `inicio` libre
- **THEN** entonces ambas respuestas son `403` y en la base el turno sigue `programado` en su horario original

#### Scenario: Sin token en cancelar y reprogramar
- **GIVEN** dado un turno `programado` futuro
- **WHEN** cuando se envía `POST /turnos/{id}/cancelar`, o `PATCH /turnos/{id}/reprogramar`, sin encabezado `Authorization`
- **THEN** entonces ambas respuestas son `401` con `WWW-Authenticate: Bearer` y el turno no cambia

#### Scenario: Rol evaluado antes que la existencia del turno
- **GIVEN** dado un odontólogo autenticado
- **WHEN** cuando envía `POST /turnos/{id}/cancelar` con un UUID que no corresponde a ningún turno
- **THEN** entonces la respuesta es `403`, no `404`

#### Scenario: Autenticación evaluada antes que el body
- **WHEN** cuando se envía `POST /turnos` sin encabezado `Authorization` y con un body JSON al que le faltan campos obligatorios
- **THEN** entonces la respuesta es `401`, no `422`

#### Scenario: Rol evaluado antes que el body
- **GIVEN** dado un odontólogo autenticado
- **WHEN** cuando envía `PATCH /turnos/{id}/reprogramar` con `{"inicio": "no-es-una-fecha"}`
- **THEN** entonces la respuesta es `403`, no `422`

### Requirement: Autor del turno referenciado en la base
`creado_por` MUST referenciar a un usuario existente mediante una clave foránea que impida borrar a un usuario que creó turnos. `creado_por` MUST seguir admitiendo nulo para los turnos creados antes de que existiera la autenticación.

#### Scenario: Autor inexistente rechazado por la base
- **WHEN** cuando se inserta directamente un turno con `creado_por` igual a un UUID que no corresponde a ningún usuario
- **THEN** entonces la base rechaza la inserción con una violación de clave foránea

#### Scenario: Usuario con turnos no se puede borrar
- **GIVEN** dado un turno cuyo `creado_por` es el usuario U
- **WHEN** cuando se borra directamente la fila de U
- **THEN** entonces la base rechaza el borrado con una violación de clave foránea

#### Scenario: Turno previo sin autor
- **WHEN** cuando se inserta directamente un turno con `creado_por` nulo
- **THEN** entonces la base acepta la inserción

### Requirement: Turno dentro del horario de atención
Al crear y al reprogramar, el intervalo `[inicio, fin)` del turno, en hora local `America/Argentina/Buenos_Aires`, MUST caber completo en una única franja del profesional del día de la semana local de su inicio; el fin puede coincidir con el de la franja (RN-AG-05, RN-CU-04, DD-27). Si no cabe o no hay franjas, MUST responder `422 fuera_de_horario` sin persistir. Los escenarios asumen el reloj en 2026-10-07 09:00 local; los de turnos de otros requisitos, una franja que cubre el turno.

#### Scenario: Turno dentro de la franja
- **GIVEN** dado que el reloj marca 2026-10-07 09:00 hora local, y que el profesional A tiene la franja del jueves (`dia_semana = 3`) de 09:00 a 13:00
- **WHEN** cuando una recepcionista autenticada crea un turno de A de 45 minutos con inicio 2026-10-08 10:00-03:00 (jueves)
- **THEN** entonces la respuesta es `201` con `inicio` 2026-10-08T10:00-03:00 y `fin` 2026-10-08T10:45-03:00

#### Scenario: Turno que empieza al abrir y otro que termina al cerrar la franja
- **GIVEN** dado el profesional A con la franja del jueves de 09:00 a 13:00
- **WHEN** cuando se crean dos turnos de A de 45 minutos el jueves 2026-10-08, uno a las 09:00 y otro a las 12:15 hora local
- **THEN** entonces ambas respuestas son `201`, y el segundo queda con `fin` 2026-10-08T13:00-03:00

#### Scenario: Turno que excede el fin de la franja
- **GIVEN** dado el profesional A con la franja del jueves de 09:00 a 13:00
- **WHEN** cuando se crea un turno de A de 45 minutos el jueves 2026-10-08 a las 12:30 hora local
- **THEN** entonces la respuesta es `422` con `{"detail": {"codigo": "fuera_de_horario", "mensaje": "el turno no cabe en el horario de atención del profesional"}}` y no se persiste ningún turno

#### Scenario: Turno que empieza antes de la franja
- **GIVEN** dado el profesional A con la franja del jueves de 09:00 a 13:00
- **WHEN** cuando se crea un turno de A de 45 minutos el jueves 2026-10-08 a las 08:30 hora local
- **THEN** entonces la respuesta es `422` con código `fuera_de_horario` y no se persiste ningún turno

#### Scenario: Turno en la segunda franja del día
- **GIVEN** dado el profesional A con las franjas del jueves de 09:00 a 13:00 y de 14:00 a 18:00
- **WHEN** cuando se crea un turno de A de 45 minutos el jueves 2026-10-08 a las 15:00 hora local
- **THEN** entonces la respuesta es `201`

#### Scenario: Turno en el hueco entre franjas
- **GIVEN** dado el profesional A con las franjas del jueves de 09:00 a 13:00 y de 14:00 a 18:00
- **WHEN** cuando se crea un turno de A de 30 minutos el jueves 2026-10-08 a las 13:15 hora local
- **THEN** entonces la respuesta es `422` con código `fuera_de_horario`

#### Scenario: Turno que cruza dos franjas
- **GIVEN** dado el profesional A con las franjas del jueves de 09:00 a 13:00 y de 14:00 a 18:00
- **WHEN** cuando se crea un turno de A de 120 minutos el jueves 2026-10-08 a las 12:30 hora local
- **THEN** entonces la respuesta es `422` con código `fuera_de_horario`

#### Scenario: Turno que cruza dos franjas contiguas
- **GIVEN** dado el profesional A con las franjas del jueves de 09:00 a 13:00 y de 13:00 a 17:00
- **WHEN** cuando se crea un turno de A de 60 minutos el jueves 2026-10-08 a las 12:30 hora local
- **THEN** entonces la respuesta es `422` con código `fuera_de_horario`, porque no cabe completo en una única franja

#### Scenario: Día sin franjas
- **GIVEN** dado el profesional A con franjas solo de lunes a viernes
- **WHEN** cuando se crea un turno de A el sábado 2026-10-10 a las 10:00 hora local
- **THEN** entonces la respuesta es `422` con código `fuera_de_horario`

#### Scenario: Profesional sin franjas
- **GIVEN** dado el profesional A activo sin ninguna franja
- **WHEN** cuando se crea un turno de A el jueves 2026-10-08 a las 10:00 hora local con referencias activas y sin solapes
- **THEN** entonces la respuesta es `422` con código `fuera_de_horario` y no se persiste ningún turno

#### Scenario: Franja de otro profesional no habilita el turno
- **GIVEN** dado el profesional B con la franja del jueves de 09:00 a 13:00 y el profesional A sin franjas el jueves
- **WHEN** cuando se crea un turno de A el jueves 2026-10-08 a las 10:00 hora local
- **THEN** entonces la respuesta es `422` con código `fuera_de_horario`

#### Scenario: El horario se evalúa en hora local, no en UTC
- **GIVEN** dado el profesional A con las franjas del jueves de 09:00 a 13:00 y de 14:00 a 18:00
- **WHEN** cuando se crea un turno de A de 45 minutos con inicio `2026-10-08T15:30:00Z` (12:30 hora local)
- **THEN** entonces la respuesta es `422` con código `fuera_de_horario`, aunque en UTC el intervalo 15:30-16:15 quede dentro de 14:00-18:00

#### Scenario: El día de la semana es el local
- **GIVEN** dado el profesional A con la franja del jueves de 21:00 a 23:00 y sin franjas el viernes
- **WHEN** cuando se crea un turno de A de 45 minutos con inicio `2026-10-09T01:00:00Z` (jueves 2026-10-08 22:00 hora local, viernes en UTC)
- **THEN** entonces la respuesta es `201` con `inicio` 2026-10-08T22:00-03:00

#### Scenario: Fuera de horario y en conflicto
- **GIVEN** dado el profesional A con la franja del jueves de 09:00 a 13:00 y un turno activo de A el jueves de 12:15 a 13:00
- **WHEN** cuando se crea otro turno de A de 45 minutos el jueves 2026-10-08 a las 12:30 hora local
- **THEN** entonces la respuesta es `422` con código `fuera_de_horario`, no `409`

#### Scenario: Validaciones previas antes que el horario
- **GIVEN** dado el profesional A sin franjas el sábado
- **WHEN** cuando se crea un turno de A el sábado 2026-10-10 a las 10:00 hora local con `duracion_min = 42`
- **THEN** entonces la respuesta es `422` con código `duracion_invalida`, no `fuera_de_horario`

### Requirement: Turno fuera de los bloqueos de agenda
Al crear y al reprogramar, el intervalo `[inicio, fin)` del turno MUST NOT superponerse con un bloqueo de agenda de su profesional; un turno contiguo al bloqueo (empieza justo al terminar o termina justo al empezar) es válido (RN-AG-06, RN-AG-03). Si se superpone → `422 turno_en_bloqueo` sin persistir. Se evalúa después del horario de atención y antes del solape. Los escenarios asumen el reloj en 2026-10-07 09:00 local y una franja que cubre el turno.

#### Scenario: Turno dentro de un bloqueo
- **GIVEN** dado un bloqueo del profesional A el jueves 2026-10-08 de 10:00 a 12:00 hora local
- **WHEN** cuando una recepcionista autenticada crea un turno de A de 45 minutos el 2026-10-08 a las 10:30 hora local
- **THEN** entonces la respuesta es `422` con `{"detail": {"codigo": "turno_en_bloqueo", "mensaje": "el turno se superpone con un bloqueo de agenda del profesional"}}` y no se persiste ningún turno

#### Scenario: Turno que empieza antes y termina dentro del bloqueo
- **GIVEN** dado un bloqueo del profesional A el jueves 2026-10-08 de 10:00 a 12:00 hora local
- **WHEN** cuando se crea un turno de A de 45 minutos el 2026-10-08 a las 09:30 hora local
- **THEN** entonces la respuesta es `422` con código `turno_en_bloqueo` y no se persiste ningún turno

#### Scenario: Turno que empieza dentro y termina después del bloqueo
- **GIVEN** dado un bloqueo del profesional A el jueves 2026-10-08 de 10:00 a 12:00 hora local
- **WHEN** cuando se crea un turno de A de 45 minutos el 2026-10-08 a las 11:30 hora local
- **THEN** entonces la respuesta es `422` con código `turno_en_bloqueo` y no se persiste ningún turno

#### Scenario: Turno que contiene al bloqueo
- **GIVEN** dado un bloqueo del profesional A el jueves 2026-10-08 de 10:00 a 10:15 hora local
- **WHEN** cuando se crea un turno de A de 60 minutos el 2026-10-08 a las 09:45 hora local
- **THEN** entonces la respuesta es `422` con código `turno_en_bloqueo` y no se persiste ningún turno

#### Scenario: Turno que empieza justo al terminar el bloqueo
- **GIVEN** dado un bloqueo del profesional A el jueves 2026-10-08 de 10:00 a 12:00 hora local
- **WHEN** cuando se crea un turno de A de 45 minutos el 2026-10-08 a las 12:00 hora local
- **THEN** entonces la respuesta es `201` con `inicio` 2026-10-08T12:00:00-03:00

#### Scenario: Turno que termina justo al empezar el bloqueo
- **GIVEN** dado un bloqueo del profesional A el jueves 2026-10-08 de 10:00 a 12:00 hora local
- **WHEN** cuando se crea un turno de A de 45 minutos el 2026-10-08 a las 09:15 hora local
- **THEN** entonces la respuesta es `201` con `fin` 2026-10-08T10:00:00-03:00

#### Scenario: Bloqueo de otro profesional
- **GIVEN** dado un bloqueo del profesional B el jueves 2026-10-08 de 10:00 a 12:00 hora local
- **WHEN** cuando se crea un turno de A de 45 minutos el 2026-10-08 a las 10:30 hora local
- **THEN** entonces la respuesta es `201`

#### Scenario: Bloqueo de varios días
- **GIVEN** dado un bloqueo del profesional A desde 2026-10-08T00:00:00-03:00 hasta 2026-10-10T00:00:00-03:00
- **WHEN** cuando se crea un turno de A el viernes 2026-10-09 a las 15:00 hora local
- **THEN** entonces la respuesta es `422` con código `turno_en_bloqueo` y no se persiste ningún turno

#### Scenario: Fuera de horario y dentro de un bloqueo
- **GIVEN** dado el profesional A con la franja del jueves de 09:00 a 13:00 y un bloqueo de A el 2026-10-08 de 12:00 a 14:00 hora local
- **WHEN** cuando se crea un turno de A de 45 minutos el 2026-10-08 a las 12:30 hora local
- **THEN** entonces la respuesta es `422` con código `fuera_de_horario`, no `turno_en_bloqueo`, y no se persiste ningún turno

#### Scenario: Dentro de un bloqueo y en conflicto
- **GIVEN** dado un turno activo del profesional A el jueves 2026-10-08 de 09:30 a 10:15 y un bloqueo de A de 10:15 a 12:00 hora local
- **WHEN** cuando se crea otro turno de A de 45 minutos el 2026-10-08 a las 10:00 hora local
- **THEN** entonces la respuesta es `422` con código `turno_en_bloqueo`, no `409`, y no se persiste ningún turno

#### Scenario: Validaciones previas antes que el bloqueo
- **GIVEN** dado un bloqueo del profesional A el jueves 2026-10-08 de 10:00 a 12:00 hora local
- **WHEN** cuando se crea un turno de A el 2026-10-08 a las 10:30 hora local con `duracion_min = 42`
- **THEN** entonces la respuesta es `422` con código `duracion_invalida`, no `turno_en_bloqueo`, y no se persiste ningún turno

#### Scenario: Turno rechazado sin recordatorio
- **GIVEN** dado un bloqueo del profesional A el viernes 2026-10-09 de 10:00 a 12:00 hora local
- **WHEN** cuando se crea un turno de A el 2026-10-09 a las 10:30 hora local
- **THEN** entonces la respuesta es `422` con código `turno_en_bloqueo`, no se persiste ningún turno ni recordatorio, no se registra auditoría y no se encola nada en la cola de recordatorios
