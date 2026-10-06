# Funcionalidades (MVP)

Solo el alcance D.4. Lo diferido está en `01_vision_y_objetivos.md` (Fuera de alcance), no aquí. Historias derivadas de los 5 casos de uso del Discovery.

## Épica 1: Configuración del consultorio

### US-001 — Gestionar profesionales, sillones y prestaciones
**Como** recepcionista **quiero** dar de alta/editar/desactivar profesionales, sillones y prestaciones (con duración por defecto) **para** poder agendar turnos.

**Criterios de aceptación**:
- [ ] Una prestación exige `duracion_min` > 0, múltiplo de 5 y ≤ 480 (CHECK en BD; DD-15) e indica si requiere sillón (`requiere_sillon`).
- [ ] Un recurso desactivado no admite turnos nuevos pero conserva su historial.
- [ ] El odontólogo solo puede leer estos recursos.

**Reglas relacionadas**: RN-AG-04, RN-AU-03

### US-002 — Definir horarios de atención
**Como** recepcionista **quiero** configurar las franjas de atención por profesional y día **para** que no se den turnos fuera de horario.

**Criterios de aceptación**:
- [ ] Se admiten varias franjas por día; `hora_fin > hora_inicio`.
- [ ] Un turno fuera de franja es rechazado (422).

**Reglas relacionadas**: RN-HB-01, RN-AG-05

### US-003 — Bloquear franjas de agenda
**Como** odontólogo (o recepcionista) **quiero** bloquear franjas **para** que no me asignen turnos cuando no atiendo.

**Criterios de aceptación**:
- [ ] El odontólogo solo bloquea sus franjas; la recepcionista, las de cualquiera.
- [ ] Un turno que solapa un bloqueo es rechazado; uno que empieza justo al terminar el bloqueo es válido.
- [ ] Un bloqueo sobre una franja con turnos activos se rechaza (409) e informa los turnos afectados.

**Reglas relacionadas**: RN-HB-02, RN-HB-03, RN-AG-06, RN-AU-02

## Épica 2: Turnos

### US-004 — Crear turno sin solapamientos
**Como** recepcionista **quiero** crear un turno con prestación, profesional, sillón y paciente **para** evitar dobles reservas.

**Criterios de aceptación**:
- [ ] La duración toma por defecto la de la prestación y puede ajustarse.
- [ ] Duración que no es múltiplo de 5 min o mayor a 480 min, o inicio no alineado a 5 min -> 422.
- [ ] Solape con otro turno del mismo profesional o del mismo sillón -> 409.
- [ ] Un turno que empieza exactamente cuando termina otro es aceptado.
- [ ] Dos creaciones concurrentes sobre el mismo horario: una se acepta y la otra recibe 409 (garantía en BD).
- [ ] Se registra auditoría y se genera el recordatorio.

**Reglas relacionadas**: RN-AG-01, 02, 03, 04, 05, 06, 09, 10, RN-CU-01, RN-NO-01

### US-005 — Reprogramar turno
**Como** recepcionista **quiero** mover un turno a otro horario/profesional/sillón con la misma validación **para** mantener la agenda consistente.

**Criterios de aceptación**:
- [ ] Se aplican las mismas validaciones que al crear (incluida la duración y la grilla de 5 min, 422), excluyendo al propio turno.
- [ ] Si falla, el turno original queda intacto.
- [ ] Se audita (valores previos y nuevos) y se reprograma el recordatorio.

**Reglas relacionadas**: RN-AG-08, RN-AG-01..06, RN-NO-02, RN-CU-01

### US-006 — Cancelar turno y liberar el horario
**Como** recepcionista **quiero** cancelar un turno **para** que el horario pueda reutilizarse.

**Criterios de aceptación**:
- [ ] El turno pasa a `cancelado` (no se borra) y deja de contar para solapamientos.
- [ ] El horario puede reservarse inmediatamente después.
- [ ] Se audita y se cancela el recordatorio pendiente.
- [ ] Se puede cancelar hasta el inicio del turno; cancelar un turno ya iniciado o pasado -> 409. Sin política de cancelación tardía (DD-14).

**Reglas relacionadas**: RN-AG-07, RN-AG-13, RN-NO-02, RN-CU-01

### US-007 — Consultar disponibilidad
**Como** recepcionista **quiero** ver los huecos libres de un profesional/sillón para una prestación **para** elegir horario rápido. (**Suposición**: derivada de la necesidad de crear turnos; no figura como caso de uso explícito.)

**Criterios de aceptación**:
- [ ] Los huecos respetan horario de atención, bloqueos, turnos activos y la duración de la prestación.

**Reglas relacionadas**: RN-AG-01..06

## Épica 3: Agenda

### US-008 — Ver agenda diaria y semanal
**Como** recepcionista **quiero** ver la agenda diaria/semanal de todos los profesionales y sillones **para** coordinar el consultorio.
**Como** odontólogo **quiero** ver mi agenda diaria/semanal **para** planificar mi día.

**Criterios de aceptación**:
- [ ] Vistas diaria y semanal, filtrables por profesional y sillón.
- [ ] El odontólogo solo ve sus turnos.
- [ ] Horarios mostrados en `America/Argentina/Buenos_Aires`.

**Reglas relacionadas**: RN-AU-02, RN-CU-04

## Épica 4: Pacientes

### US-009 — Registro básico de pacientes
**Como** recepcionista **quiero** registrar y buscar pacientes **para** asignarlos a turnos.

**Criterios de aceptación**:
- [ ] Datos mínimos: nombre, apellido, documento, teléfono (todos ficticios en repo/seed/tests).
- [ ] Sin ficha clínica ni odontograma (fuera de alcance).

**Reglas relacionadas**: RN-CU-02

## Épica 5: Seguridad y cumplimiento

### US-010 — Autenticación con roles
**Como** usuario **quiero** iniciar sesión con JWT **para** acceder según mi rol.

**Criterios de aceptación**:
- [ ] Dos roles: recepcionista y odontólogo; endpoints protegidos por rol.

**Reglas relacionadas**: RN-AU-01, RN-AU-02, RN-AU-03

### US-011 — Auditoría de cambios de turnos
**Como** recepcionista **quiero** consultar quién creó, reprogramó o canceló cada turno y cuándo **para** cumplir Ley 25.326/26.529.

**Criterios de aceptación**:
- [ ] Cada cambio genera un registro append-only con usuario, acción, valores previos/nuevos y marca de tiempo UTC.

**Reglas relacionadas**: RN-CU-01

## Épica 6: Recordatorios

### US-012 — Recordatorio previo al turno
**Como** sistema **quiero** generar un recordatorio previo a cada turno **para** reducir el ausentismo.

**Criterios de aceptación**:
- [ ] El recordatorio se encola en Redis y lo procesa un worker mediante el puerto de notificación (adaptador mock).
- [ ] Cancelar/reprogramar el turno ajusta el recordatorio.
- [ ] La anticipación es configurable (`REMINDER_LEAD_HOURS`, 24 por defecto; DD-13).
- [ ] Si el turno se crea o reprograma con menos de 24 h de anticipación, no se programa recordatorio.
- [ ] El envío fallido se reintenta 3 veces con backoff exponencial; agotados, el recordatorio queda `fallido` (DD-19).

**Reglas relacionadas**: RN-NO-01, RN-NO-02, RN-NO-03, RN-NO-04, RN-NO-05
