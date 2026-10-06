# Reglas de Negocio

Códigos `RN-{DOMINIO}-{NN}`. Las reglas del Discovery (RN1-RN6) se conservan con trazabilidad explícita; las marcadas **Suposición** se infieren y requieren validación.

## Trazabilidad con Discovery

| Discovery | KB | Tema |
|-----------|----|------|
| RN1 | RN-AG-01 | Sin solape por profesional |
| RN2 | RN-AG-02 | Sin solape por sillón |
| RN3 | RN-AG-03 | Intervalos semiabiertos `[inicio, fin)` |
| RN4 | RN-AG-04 | Duración por prestación, ajustable |
| RN5 | RN-AG-05, RN-AG-06 | Horario de atención y bloqueos |
| RN6 | RN-AG-07, RN-AG-13 | Cancelación libera el horario (cancelable hasta el inicio) |

## Dominio: Agenda y turnos (RN-AG)

- **RN-AG-01** (RN1): un profesional no puede tener dos turnos activos superpuestos.
- **RN-AG-02** (RN2): un sillón no puede tener dos turnos activos superpuestos. Un turno ocupa **un** sillón y **un** profesional durante todo su intervalo.
- **RN-AG-03** (RN3): los intervalos son semiabiertos `[inicio, fin)`. Dos turnos se solapan si `inicioA < finB` y `inicioB < finA`. **Caso borde:** un turno que empieza exactamente cuando termina otro (mismo profesional o mismo sillón) **es válido**.
- **RN-AG-04** (RN4): la duración del turno es por defecto `Prestacion.duracion_min`; la recepcionista puede ajustarla al crearlo (y al reprogramar). `fin = inicio + duración efectiva`. La duración efectiva debe ser > 0, múltiplo de 5 minutos y ≤ 480 minutos, y el inicio debe estar alineado a 5 minutos (minutos múltiplo de 5, segundos y microsegundos en 0, evaluado en hora local `America/Argentina/Buenos_Aires`). Cualquier violación -> `422` (decisión del equipo, 2026-10-06, DD-15). Se aplica al crear, al reprogramar y a `Prestacion.duracion_min` del catálogo.
- **RN-AG-05** (RN5): no se dan turnos fuera del horario de atención del profesional (el intervalo completo `[inicio, fin)` debe caber en una franja de `HorarioAtencion`).
- **RN-AG-06** (RN5): no se dan turnos que se solapen con un bloqueo de agenda del profesional (mismo criterio de intervalos semiabiertos; un turno que empieza justo al terminar un bloqueo es válido).
- **RN-AG-07** (RN6): un turno cancelado libera el horario (profesional y sillón) y **deja de contar** para la validación de solapamientos; el horario puede reasignarse de inmediato. El turno cancelado se conserva (no se borra) para auditoría.
- **RN-AG-08**: reprogramar un turno aplica **exactamente la misma validación** que crearlo (RN-AG-01..06), excluyendo al propio turno de la comprobación de solapamiento. Si la validación falla, el turno original no cambia (operación atómica).
- **RN-AG-09**: la garantía de no superposición debe existir **a nivel de base de datos** (restricción de exclusión sobre `tstzrange(inicio, fin, '[)')` por profesional y por sillón, parcial sobre `estado <> 'cancelado'`), no solo como validación de aplicación; ante reservas concurrentes sobre el mismo horario una gana y la otra recibe conflicto (409). Ver 08 y 09.
- **RN-AG-10** (decisión del equipo, 2026-10-02): un turno referencia obligatoriamente profesional, paciente y prestación. El sillón depende de la prestación: si `Prestacion.requiere_sillon` es verdadero, el turno **debe** tener sillón asignado (si falta → `422`); si es falso (por ejemplo, una consulta), el turno no ocupa sillón y solo se valida la agenda del profesional. Un turno sin sillón no participa de RN-AG-02.
- **RN-AG-11** (decisión del equipo, 2026-10-02): no hay sobreturnos en el MVP; todo solape se rechaza. Bilog los evidencia como tipo de turno; quedan como extensión posterior (ver 01, fuera de alcance).
- **RN-AG-12** (decisión del equipo, 2026-10-02): no se crean ni se reprograman turnos con inicio anterior al momento actual (→ `422`).
- **RN-AG-13** (decisión del equipo, 2026-10-06, DD-14): un turno se puede cancelar hasta su inicio; cancelar un turno ya iniciado o pasado se rechaza con `409`. No hay política de cancelación tardía en el MVP (sin cobros, marcas ni penalidades; quedan en el backlog).

## Dominio: Horarios y bloqueos (RN-HB)

- **RN-HB-01**: los horarios de atención se definen por profesional, día de semana y franjas (varias por día); los configura la recepcionista.
- **RN-HB-02**: un bloqueo se define con `[inicio, fin)` y motivo; lo crea la recepcionista (cualquier profesional) o el odontólogo (solo los suyos).
- **RN-HB-03** (decisión del equipo, 2026-10-02): crear un bloqueo sobre un intervalo con turnos activos del mismo profesional se rechaza con `409`, y la respuesta lista los turnos afectados. Primero hay que reprogramarlos o cancelarlos; nunca quedan turnos activos dentro de un bloqueo.

## Dominio: Notificaciones (RN-NO)

- **RN-NO-01**: todo turno activo genera un recordatorio previo mediante el **puerto de notificación**; en el MVP el adaptador es **mock**, procesado asincrónicamente vía cola Redis.
- **RN-NO-02**: cancelar un turno cancela su recordatorio pendiente; reprogramarlo lo reprograma.
- **RN-NO-03** (decisión del equipo, 2026-10-06, DD-13): el recordatorio se programa 24 h antes del turno (`REMINDER_LEAD_HOURS=24`, configurable por variable de entorno). Si el turno se crea o reprograma con menos de 24 h de anticipación, **no** se programa recordatorio.
- **RN-NO-04**: el contenido de los recordatorios no debe exponer datos clínicos (solo fecha, hora, consultorio) — **Suposición** por privacidad.
- **RN-NO-05** (decisión del equipo, 2026-10-06, DD-19): el envío se reintenta hasta 3 veces con backoff exponencial; agotados los intentos, el recordatorio queda `fallido`. No hay reintento manual en el MVP.

## Dominio: Autenticación y autorización (RN-AU)

- **RN-AU-01**: autenticación con JWT; solo existen los roles `recepcionista` y `odontologo`.
- **RN-AU-02**: el odontólogo solo ve su propia agenda y solo bloquea sus propias franjas; la recepcionista opera sobre todos los profesionales.
- **RN-AU-03**: la configuración (profesionales, sillones, prestaciones, horarios) es exclusiva de la recepcionista (no hay administrador separado en el MVP).

## Dominio: Cumplimiento y datos (RN-CU)

- **RN-CU-01**: Ley 25.326 y 26.529 — acceso por rol y **auditoría** de todo cambio de turno (crear, reprogramar, cancelar) con usuario y momento; registro append-only.
- **RN-CU-02**: solo datos ficticios en repositorio, ejemplos, tests y capturas.
- **RN-CU-03**: sin secretos en el repositorio; configuración por variables de entorno con `.env.example` versionado.
- **RN-CU-04**: horarios persistidos en UTC y presentados en `America/Argentina/Buenos_Aires`. Los horarios de atención (hora local) se convierten a UTC al evaluar disponibilidad. Argentina no usa horario de verano, lo que simplifica la conversión (**Suposición** a verificar).

## Excepciones globales
- Cualquier violación de solapamiento -> `409 Conflict` con indicación del recurso en conflicto (profesional o sillón).
- Cualquier violación de horario/bloqueo -> `422 Unprocessable Entity`.
- Las operaciones de crear/reprogramar/cancelar son atómicas junto con su registro de auditoría.
