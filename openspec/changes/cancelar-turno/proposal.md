# Proposal

## Why

Con C-03 la recepción ya puede crear turnos sin solapamientos, pero no tiene forma de liberar un horario cuando el paciente avisa que no asistirá (US-006, Flujo 4). Sin cancelación, el turno sigue ocupando profesional, sillón y paciente y el horario no puede reasignarse, lo que genera turnos fantasma. El esquema de C-03 ya prevé el estado `cancelado`, `motivo_cancelacion` y restricciones de exclusión parciales que ignoran cancelados (RN-AG-07): este change expone la operación y fija sus reglas (RN-AG-13, DD-14, DD-08).

## What Changes

- Nuevo endpoint `POST /turnos/{id}/cancelar` con body opcional `{"motivo": ...}`: pasa el turno a `estado = cancelado`, guarda `motivo_cancelacion` y responde `200` con el turno actualizado. El turno **no se borra** (DD-08).
- El horario queda libre de inmediato: el turno cancelado deja de contar para la verificación previa de solape y para las restricciones de exclusión de la base (RN-AG-07), así que se puede crear otro turno en el mismo intervalo con los mismos recursos.
- Errores: turno inexistente → `404` (recurso del path, DD-21); turno ya cancelado → `409`, no idempotente (DD-22); turno ya iniciado o pasado → `409` (RN-AG-13). Se puede cancelar hasta el inicio, sin política de cancelación tardía (DD-14).
- Regla de dominio pura `validar_cancelable(estado, inicio, ahora)` evaluada con el reloj inyectable de C-03 (sin BD ni reloj real).
- Caso de uso `CancelarTurno` en `application/` con bloqueo de fila (`SELECT ... FOR UPDATE`) para que dos cancelaciones simultáneas del mismo turno no terminen ambas en éxito, y un punto de extensión de observadores (vacío) donde C-07 (auditoría `cancelar`) y C-12 (cancelar el recordatorio pendiente) se enchufan.
- Sin migración: la tabla `turno` de la migración `003` ya tiene `estado`, `motivo_cancelacion` y las exclusiones parciales.
- Fuera de alcance: autenticación y permisos por rol (C-06; el endpoint queda abierto como `POST /turnos`), auditoría (C-07), recordatorios (C-12), horarios y bloqueos (C-10, C-11), reprogramación (C-05) y cualquier política de cancelación tardía (backlog, DD-14).

## Capabilities

### New Capabilities
<!-- Ninguna: la cancelación es parte del ciclo de vida del turno y se agrega a `agenda-turnos`. -->

### Modified Capabilities
- `agenda-turnos`: se agregan los requisitos de cancelación de un turno (transición a `cancelado` sin borrado, motivo opcional, liberación inmediata del horario, cancelable solo antes del inicio, contrato de errores `404`/`409`/`422` y comportamiento ante cancelaciones concurrentes). Los requisitos existentes de creación no cambian.

## Impact

- **Código nuevo**: `backend/app/application/cancelar_turno.py` (caso de uso `CancelarTurno`).
- **Código modificado**: `backend/app/domain/turnos.py` (regla `validar_cancelable`, errores `TurnoInexistenteError` y `TurnoNoCancelableError`, snapshot `TurnoRegistrado`), `backend/app/infrastructure/db/repositorio_turnos.py` (lectura con bloqueo y actualización a `cancelado`), `backend/app/api/turnos.py` (ruta, schema de entrada, campo `motivo_cancelacion` en la respuesta y manejadores `404`/`409`).
- **API**: nuevo `POST /turnos/{id}/cancelar` sin autenticación. La respuesta de turno suma el campo `motivo_cancelacion` (nulo al crear); es un agregado compatible para `POST /turnos`.
- **Base de datos**: sin cambios de esquema ni migración nueva.
- **Tests**: unitarios de dominio, de repositorio, de caso de uso, de API y un test de cancelaciones concurrentes contra PostgreSQL real.
- **Changes posteriores**: C-05 reutiliza la lectura con bloqueo; C-07 y C-12 registran observadores de cancelación.
