# Proposal

## Why

Con C-03 y C-04 la recepción puede crear y cancelar turnos, pero cuando el paciente pide otro horario, o hay que pasarlo a otro profesional o a otro sillón, la única salida es cancelar y volver a crear: se pierde la identidad del turno, el paso no es atómico (entre la cancelación y el alta otro pedido puede ocupar el horario) y la duración ajustada hay que volver a cargarla a mano. US-005 y el Flujo 3 piden mover el turno en una sola operación con **exactamente la misma validación** que el alta (RN-AG-08), y DD-23 ya fijó el contrato (PATCH parcial, campos no editables, turno cancelado o iniciado no reprogramable).

## What Changes

- Nuevo endpoint `PATCH /turnos/{id}/reprogramar` que actualiza **la misma fila** del turno y responde `200` con el turno reprogramado (mismo `id`, `estado = programado`, instantes en `America/Argentina/Buenos_Aires`).
- **PATCH parcial** (DD-23a): los campos editables son `inicio`, `profesional_id`, `sillon_id` y `duracion_min`; los omitidos conservan el valor actual del turno, incluida una duración ajustada (no vuelve a `Prestacion.duracion_min`). Se distingue "omitido" de "nulo explícito": `sillon_id: null` quita el sillón y cae en las reglas de coherencia existentes (`422 sillon_requerido`); informar un sillón para una prestación que no lo usa responde `422 sillon_no_corresponde` (DD-21).
- **Campos no editables** (DD-23b): si el body trae `paciente_id` o `prestacion_id` → `422 campo_no_editable` con la lista de campos rechazados y un mensaje dirigido a la recepcionista (cancelar este turno y crear uno nuevo). Otros campos desconocidos se ignoran, igual que en `POST /turnos`.
- **Misma validación que el alta** (RN-AG-08, garantizada por diseño): referencias activas, duración y grilla de 5 min (RN-AG-04, DD-15), inicio no pasado (RN-AG-12), coherencia del sillón (RN-AG-10) y pre-chequeo de solape por profesional, sillón y paciente (RN-AG-01, 02, 14) excluyendo al propio turno. Solaparse con el propio intervalo anterior es válido.
- **Turno no modificable**: turno cancelado → `409 turno_ya_cancelado` (reusa el código de C-04, DD-23c); turno cuyo inicio original ya llegó → `409 turno_ya_iniciado` aunque el nuevo inicio sea futuro (DD-23d). El estado se evalúa antes que la hora. Turno inexistente → `404`.
- **Atomicidad**: lectura con bloqueo de fila (`FOR UPDATE`, reutilizado de C-04) y `UPDATE` dentro de un SAVEPOINT que traduce la violación de exclusión (`23P01`) a `409 solapamiento`. Ante cualquier `409`/`422` el turno original queda intacto.
- **Refactors previos protegidos por los tests existentes**: (1) la secuencia de validación de `CrearTurno` se extrae a una función compartida que usan alta y reprogramación (RN-AG-08 por construcción); `buscar_conflictos` acepta un `excluir_id` opcional; (2) la regla de cancelabilidad de C-04 se generaliza a una regla de "turno modificable" compartida por cancelar y reprogramar, sin cambiar códigos ni estados HTTP.
- Sin migración: el `UPDATE` de la misma fila lo cubren las exclusiones parciales de la migración `003`.

## Non-goals

Las fuentes citan estos puntos para la reprogramación (US-005, Flujo 3, RN-AG-08), pero dependen de changes que todavía no existen. Este change deja los puntos de extensión donde se enchufan y **sus escenarios no los cubren**:

- **Auditoría con valores previos y nuevos** (US-005, Flujo 3 paso 3): requiere la tabla `TurnoAuditoria` y el usuario autenticado, que llegan en C-07 (y C-06). Se enchufa como observador de reprogramación, que recibe el turno anterior y el nuevo.
- **Reprogramar el recordatorio** (US-005, Flujo 3 paso 3, RN-NO-02): los recordatorios y la cola llegan en C-12. Se enchufa también como observador.
- **Autenticación y permiso por rol** (recepcionista): C-06. El endpoint queda abierto, igual que `POST /turnos` y `POST /turnos/{id}/cancelar`.
- **Horario de atención y bloqueos** (RN-AG-05, RN-AG-06, que RN-AG-08 incluye en "la misma validación"): llegan en C-10 y C-11 como validadores del turno propuesto. Al enchufarse en la validación compartida, aplicarán al alta y a la reprogramación a la vez, sin tocar este change.
- Cambiar paciente o prestación de un turno existente (DD-23b), mover un turno ya iniciado o pasado (ausentismo, fuera del MVP), endpoint de lectura o listado (C-13).

## Capabilities

### New Capabilities
<!-- Ninguna: la reprogramación es parte del ciclo de vida del turno y se agrega a `agenda-turnos`. -->

### Modified Capabilities
- `agenda-turnos`: se agregan los requisitos de reprogramación (actualización de la misma fila, PATCH parcial, campos no editables, misma validación que el alta excluyendo al propio turno, turno cancelado o iniciado no reprogramable, turno inexistente, garantía de la base ante reprogramaciones concurrentes y serialización con la cancelación). Los requisitos existentes de alta y cancelación no cambian.

## Impact

- **Código nuevo**: `backend/app/application/reprogramar_turno.py` (caso de uso `ReprogramarTurno`, solicitud parcial y fusión con el turno actual) y `backend/app/application/validacion_turno.py` (validación compartida con el alta).
- **Código modificado**: `backend/app/application/crear_turno.py` (delega en la validación compartida, comportamiento idéntico), `backend/app/application/cancelar_turno.py` (usa la regla de turno modificable), `backend/app/domain/turnos.py` (regla y error de turno modificable, error de campo no editable), `backend/app/infrastructure/db/repositorio_turnos.py` (`excluir_id` en el pre-chequeo y `actualizar` con SAVEPOINT), `backend/app/api/turnos.py` (ruta `PATCH`, schema de entrada y manejador `422 campo_no_editable`).
- **API**: nuevo `PATCH /turnos/{id}/reprogramar` sin autenticación. `POST /turnos` y `POST /turnos/{id}/cancelar` no cambian su contrato.
- **Base de datos**: sin cambios de esquema ni migración nueva.
- **Tests**: unitarios de dominio y de fusión, de repositorio, de caso de uso, de API y dos tests de concurrencia contra PostgreSQL real; los tests de C-03 y C-04 son la red de seguridad de los refactors.
- **Changes posteriores**: C-07 y C-12 registran observadores de reprogramación; C-10 y C-11 registran validadores en la validación compartida.
