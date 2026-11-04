# Modelo de Datos

> Modelo propuesto (las fuentes definen reglas y entidades implícitas, no el esquema). Lo no evidenciado en Discovery se marca como **Suposición**.

## Dominios
- **Identidad**: usuarios y roles.
- **Recursos del consultorio**: profesionales, sillones, prestaciones.
- **Disponibilidad**: horarios de atención y bloqueos.
- **Agenda**: turnos.
- **Pacientes**: registro básico (datos ficticios).
- **Soporte**: auditoría de turnos y recordatorios.

## ERD

```
Usuario 1---0..1 Profesional
Profesional 1---* HorarioAtencion
Profesional 1---* Bloqueo
Profesional 1---* Turno
Sillon      1---* Turno          (sillon_id NULLABLE: obligatorio solo si la prestación requiere sillón, RN-AG-10)
Prestacion  1---* Turno
Paciente    1---* Turno          (sin solape por paciente, RN-AG-14)
Turno       1---* TurnoAuditoria
Turno       1---* Recordatorio
```

## Entidades

### Usuario
- `id` (uuid, PK), `email` (unique, normalizado sin espacios y en minúsculas, garantizado por `CHECK (email = lower(btrim(email)) AND email <> '')`), `password_hash`, `rol` (`varchar` + `CHECK (rol IN ('recepcionista','odontologo'))`), `profesional_id` (FK nullable, obligatoria si y solo si rol = odontologo), `activo` (bool).
- A lo sumo un usuario activo por profesional: índice único parcial `ON (profesional_id) WHERE activo` (DD-24).
- `turno.creado_por` referencia a `usuario.id` con FK nullable `ON DELETE RESTRICT` (las filas previas a C-06 quedan en `NULL`).
- Sin contraseñas en claro; hash con bcrypt/argon2.
- Alta por seed y por comando CLI (alta y desactivación); la baja es `activo = false`, nunca borrado, porque la auditoría referencia al usuario (DD-16).

### Profesional
- `id`, `nombre`, `apellido`, `matricula` (opcional, ficticia), `activo`.
- Relaciones: 1:N con HorarioAtencion, Bloqueo, Turno.

### Sillon
- `id`, `nombre` (p. ej. "Sillón 1"), `activo`. Entre 1 y 4 en el segmento objetivo.

### Prestacion
- `id`, `nombre`, `duracion_min` (int > 0, múltiplo de 5 y ≤ 480, duración por defecto, RN4; CHECK en BD desde C-08: `ck_prestacion_duracion_min_positiva`, `ck_prestacion_duracion_min_multiplo_5` y `ck_prestacion_duracion_min_maxima`, migración `006`; DD-15, DD-26), `requiere_sillon` (bool, default `true`; RN-AG-10), `activa`.
- Sin precios ni cobertura en el MVP (ARCA/caja fuera de alcance).

### HorarioAtencion
- `id`, `profesional_id` (FK `ON DELETE CASCADE`), `dia_semana` (`smallint`, **0 = lunes … 6 = domingo**), `hora_inicio`, `hora_fin` (`time` sin zona, hora local, `hora_fin > hora_inicio`, sin cruzar la medianoche).
- Varias franjas por día permitidas (p. ej. mañana y tarde). Se interpreta en `America/Argentina/Buenos_Aires`.
- **Garantías en la BD (migración `007`, DD-27)**: `ck_horario_atencion_dia_semana_valido` (`dia_semana BETWEEN 0 AND 6`), `ck_horario_atencion_hora_fin_mayor`, `ck_horario_atencion_grilla` (ambas horas en múltiplos de 5 minutos) y la exclusión `horario_atencion_sin_superposicion` (`EXCLUDE USING gist (profesional_id WITH =, dia_semana WITH =, tsrange(DATE '2000-01-03' + hora_inicio, DATE '2000-01-03' + hora_fin, '[)') WITH &&)`): sin franjas superpuestas del mismo profesional y día; las contiguas valen.

### Bloqueo
- `id`, `profesional_id`, `inicio`, `fin` (timestamptz UTC, `fin > inicio`), `motivo` (texto corto), `creado_por`.
- Opcionalmente por sillón (**Suposición**, `sillon_id` nullable) para mantenimiento.

### Paciente
- `id`, `nombre`, `apellido`, `documento` (ficticio), `telefono` (ficticio), `email` (opcional), `activo`.
- Solo datos ficticios en repo/seed/tests/capturas.

### Turno
- `id`, `profesional_id`, `sillon_id` (nullable; requerido cuando `prestacion.requiere_sillon`, validado en el dominio, RN-AG-10), `paciente_id`, `prestacion_id`.
- `inicio`, `fin` (timestamptz UTC; `fin = inicio + duración efectiva`), `duracion_min` (efectiva, ajustable, RN4; > 0, múltiplo de 5 y ≤ 480; `inicio` alineado a 5 min en hora local; validado en el dominio, 422, DD-15).
- `estado` (`varchar` + `CHECK (estado IN ('programado','cancelado'))`, no enum nativo de PostgreSQL, DD-21; **Suposición**: reprogramar actualiza el mismo turno y deja huella en auditoría, sin estado propio).
- `motivo_cancelacion` (nullable), `creado_por`, `creado_en`, `actualizado_en`.
- **Constraints (garantía a nivel de BD)** — requieren `CREATE EXTENSION btree_gist`:
  ```sql
  ALTER TABLE turno ADD CONSTRAINT turno_sin_solape_profesional
    EXCLUDE USING gist (profesional_id WITH =, tstzrange(inicio, fin, '[)') WITH &&)
    WHERE (estado <> 'cancelado');
  ALTER TABLE turno ADD CONSTRAINT turno_sin_solape_sillon
    EXCLUDE USING gist (sillon_id WITH =, tstzrange(inicio, fin, '[)') WITH &&)
    WHERE (estado <> 'cancelado' AND sillon_id IS NOT NULL);
  ALTER TABLE turno ADD CONSTRAINT turno_sin_solape_paciente
    EXCLUDE USING gist (paciente_id WITH =, tstzrange(inicio, fin, '[)') WITH &&)
    WHERE (estado <> 'cancelado');
  ALTER TABLE turno ADD CONSTRAINT ck_turno_estado_valido CHECK (estado IN ('programado','cancelado'));
  ALTER TABLE turno ADD CONSTRAINT ck_turno_fin_mayor CHECK (fin > inicio);
  ```
  `turno_sin_solape_paciente` implementa RN-AG-14 (DD-20). `[)` implementa RN3: dos turnos contiguos (fin = inicio del siguiente) **no** se solapan. El `WHERE estado <> 'cancelado'` implementa RN6.
- Índices: GiST (los de las constraints), `(profesional_id, inicio)`, `(sillon_id, inicio)`. El índice simple `(paciente_id)` ya no se crea: lo cubre el GiST de `turno_sin_solape_paciente`.

### TurnoAuditoria
- `id` (`bigint GENERATED ALWAYS AS IDENTITY`; el historial se ordena por `id`), `turno_id` (FK a `turno`, `RESTRICT`), `usuario_id` (FK a `usuario`, `RESTRICT`), `accion` (`varchar` + `CHECK (accion IN ('crear','reprogramar','cancelar'))`), `valores_previos` (jsonb, nulo si y solo si la acción es `crear`: `CHECK ((accion = 'crear') = (valores_previos IS NULL))`), `valores_nuevos` (jsonb, no nulo), `ocurrido_en` (timestamptz UTC, no nulo, sin `DEFAULT`: lo informa la aplicación con su reloj).
- `valores_previos` y `valores_nuevos` son una instantánea completa y fija del turno: `profesional_id`, `paciente_id`, `prestacion_id`, `sillon_id`, `inicio`, `fin`, `duracion_min`, `estado`, `motivo_cancelacion` (instantes en UTC con zona explícita; sin datos personales del paciente).
- Solo inserción (append-only), garantizado por la base: triggers que rechazan `UPDATE`, `DELETE` (por fila) y `TRUNCATE` (DD-25). Exigido por Ley 25.326 / 26.529.
- Índices: `(turno_id, id)` y `(usuario_id)`.

### Recordatorio
- `id` (uuid, PK), `turno_id` (FK `turno`, `ON DELETE RESTRICT`: un turno con recordatorios no se borra), `programado_para` (timestamptz, NOT NULL, **sin default**: lo calcula la aplicación con el reloj inyectado. Es el **próximo intento programado** (DD-29): al crear el recordatorio vale `inicio - REMINDER_LEAD_HOURS` y, tras un intento fallido que no agota los intentos, vale el momento de la falla más la espera del backoff; al pasar a `fallido` no cambia. Se pierde así el instante originalmente programado, que se reconstruye como `turno.inicio - REMINDER_LEAD_HOURS` si la configuración no cambió), `estado` (`varchar(20)`, default `pendiente`), `canal` (`varchar(20)`, NOT NULL), `intentos` (int, default 0), `creado_en` y `actualizado_en`.
- CHECKs (DD-21, DD-28, DD-29): `ck_recordatorio_estado_valido` (`estado IN ('pendiente','enviado','fallido','cancelado')`), `ck_recordatorio_canal_valido` (`canal IN ('mock')`; un canal real exige ampliar el CHECK con una migración), `ck_recordatorio_intentos_rango` (`intentos BETWEEN 0 AND 3`, backoff exponencial, agotados -> `fallido`, DD-19), `ck_recordatorio_intentos_segun_estado` (un `fallido` tiene exactamente 3 intentos y un `enviado` al menos 1) y `ck_recordatorio_pendiente_intentos` (`estado <> 'pendiente' OR intentos < 3`: un `pendiente` no agota los 3 intentos; migración `009`, DD-29).
- Índice único parcial `ux_recordatorio_turno_pendiente ON (turno_id) WHERE estado = 'pendiente'`: a lo sumo un recordatorio pendiente por turno (RN-NO-02); puede haber varios `cancelado`, `enviado` o `fallido`. Índices de apoyo: `ix_recordatorio_turno_id` (FK) e `ix_recordatorio_pendiente_programado_para` (parcial, para el re-encolado al iniciar el worker).
- Solo se crea si faltan 24 h o más para el turno (DD-13).
- Al cancelar el turno, el recordatorio pendiente pasa a `cancelado`; al reprogramar con cambio de inicio, el pendiente pasa a `cancelado` y se crea uno nuevo si corresponde (DD-28). Desde DD-29 también pasa a `cancelado` cuando el worker lo procesa con el turno ya iniciado (`inicio <= ahora`), conservando sus `intentos`: `cancelado` tiene entonces dos causas (turno cancelado o reprogramado, y turno ya iniciado). Los `enviado` y `fallido` no se modifican.

## Seed data inicial (todo ficticio)
- 1 usuario `recepcionista` y 2 usuarios `odontologo` (credenciales de desarrollo en `.env.example`/seed, no productivas).
- 2 profesionales, 2 sillones, 3-4 prestaciones (p. ej. Consulta 30 min sin sillón, Limpieza 45 min y Conservadora 60 min con sillón).
- Horarios de atención de ejemplo (lunes a viernes, mañana y tarde) y 3-5 pacientes ficticios.
