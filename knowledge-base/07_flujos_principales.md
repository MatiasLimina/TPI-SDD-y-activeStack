# Flujos Principales

## Flujo 1: Autenticación
**Disparador**: usuario envía credenciales. **Actor**: recepcionista u odontólogo.

1. Frontend `POST /auth/login`.
2. API valida hash de contraseña y emite JWT con `sub`, `rol` y `profesional_id` (si aplica) y expiración corta.
3. Frontend adjunta el token en cada request; la API valida firma, expiración y rol por endpoint.

**Errores**: credenciales inválidas -> 401; rol insuficiente -> 403; token vencido -> 401.

## Flujo 2: Crear turno
**Disparador**: la recepcionista agenda a un paciente. **Actor**: recepcionista.

1. Selecciona paciente, prestación, profesional, sillón y hora de inicio (opcionalmente consulta `GET /disponibilidad`).
2. API calcula `fin = inicio + duración` (por defecto `Prestacion.duracion_min`, o la ajustada; RN-AG-04).
3. API valida que las referencias existan y estén activas, duración y grilla de 5 min (RN-AG-04), coherencia del sillón con la prestación (RN-AG-10), horario de atención del profesional (RN-AG-05) y ausencia de bloqueo (RN-AG-06); hace un pre-chequeo de solape por profesional, sillón y paciente (RN-AG-01/02/14) que reúne todos los recursos en conflicto.
4. API abre una transacción e inserta `Turno`; PostgreSQL verifica las restricciones de exclusión por profesional, por sillón y por paciente (RN-AG-01/02/03/09/14).
5. En la misma transacción inserta `TurnoAuditoria` (acción `crear`) y, si faltan 24 h o más para el turno, un `Recordatorio` pendiente (RN-NO-03); commit.
6. API encola el recordatorio en Redis para su `programado_para`.

```
Recepcionista -> Frontend -> API -> PostgreSQL (INSERT + EXCLUDE)
                                 \-> Redis (cola recordatorios)
                           <- 201 Turno
```

**Errores**: solape -> 409 (lista todos los recursos en conflicto: profesional, sillón y/o paciente; DD-21); fuera de horario / en bloqueo -> 422; `sillon_id` con prestación que no requiere sillón -> 422; referencia inexistente en el body (profesional, paciente, prestación, sillón) -> 422; duración inválida (no múltiplo de 5, mayor a 480) o inicio no alineado a 5 min -> 422; recurso inactivo -> 422. Si dos recepciones reservan a la vez el mismo hueco, una recibe 409 (la BD es la fuente de verdad, no la validación previa).

## Flujo 3: Reprogramar turno
**Disparador**: cambio de horario/profesional/sillón. **Actor**: recepcionista.

1. `PATCH /turnos/{id}/reprogramar` con nuevos valores.
2. API recalcula `fin` y repite validaciones 3-4 del flujo 2 excluyendo el propio turno (se actualiza la misma fila, por lo que la restricción de exclusión no se auto-conflictúa).
3. En la misma transacción: `UPDATE` del turno, `TurnoAuditoria` (`reprogramar`, valores previos y nuevos), reprogramación del recordatorio.

**Errores**: solape -> 409 y el turno original queda intacto (RN-AG-08); duración inválida o inicio no alineado a 5 min -> 422 (RN-AG-04); `paciente_id` o `prestacion_id` en el request -> 422 `campo_no_editable`; turno cancelado -> 409 `turno_ya_cancelado`; turno ya iniciado o pasado -> 409 `turno_ya_iniciado` (DD-23). Los campos omitidos conservan su valor actual (DD-23).

## Flujo 4: Cancelar turno
**Disparador**: el paciente avisa que no asistirá. **Actor**: recepcionista.

1. `POST /turnos/{id}/cancelar` (con motivo opcional).
2. API marca `estado = cancelado`; la restricción parcial deja de considerarlo (RN-AG-07).
3. Se registra auditoría (`cancelar`) y se cancela el recordatorio pendiente.
4. El horario queda disponible de inmediato.

**Errores**: turno ya cancelado -> 409, sin modificar el turno (DD-22); turno ya iniciado o pasado -> 409 (RN-AG-13). Sin política de cancelación tardía en el MVP (DD-14).

## Flujo 5: Bloquear franja (odontólogo)
**Disparador**: el odontólogo no atiende en cierta franja. **Actor**: odontólogo.

1. `POST /bloqueos` con `[inicio, fin)` y motivo; la API fuerza `profesional_id` = el del token.
2. Validación contra turnos activos existentes: si hay alguno en `[inicio, fin)`, se rechaza con `409` y la lista de turnos afectados (RN-HB-03).
3. El bloqueo se refleja en la agenda y en la disponibilidad.

## Flujo 6: Envío de recordatorio (asincrónico)
**Disparador**: llega `programado_para`. **Actor**: worker.

1. Worker consume la cola Redis y verifica que el turno siga activo.
2. Invoca `NotificationSender.send(...)`; el adaptador mock registra el envío (no hay mensajería real).
3. Marca el recordatorio `enviado` o `fallido` (hasta 3 intentos con backoff exponencial; agotados, `fallido`; sin reintento manual, DD-19).

**Errores**: Redis caído -> los recordatorios pendientes persisten en BD y se re-encolan al reiniciar (**Suposición**).

## Flujo 7: Consulta de agenda
1. `GET /turnos?desde&hasta&profesional&sillon` (el odontólogo queda filtrado a su profesional).
2. API convierte el rango local a UTC, consulta y devuelve UTC; el frontend presenta en `America/Argentina/Buenos_Aires`.
