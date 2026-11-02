# Proposal

## Why

Hoy un turno se puede dar a cualquier hora de cualquier día: el sistema valida solapes, duración, grilla y referencias, pero no sabe cuándo atiende cada profesional. RN-AG-05 exige que el intervalo completo `[inicio, fin)` de un turno quepa en una franja del horario de atención del profesional, y RN-HB-01 y US-002 piden que la recepcionista configure esas franjas por profesional y día de la semana, con varias franjas por día (mañana y tarde). Con C-08 archivado ya existen la gestión de profesionales y los alias de rol, y C-03 y C-05 dejaron un punto de extensión (`validadores`) en la validación compartida de alta y reprogramación para sumar esta regla sin tocar su orden. C-10 está en el camino crítico: C-13 (consulta de agenda) y el frontend dependen de que la agenda respete el horario.

## What Changes

- **Modelo `HorarioAtencion`** (`profesional_id`, `dia_semana` 0-6, `hora_inicio`, `hora_fin`, hora local `America/Argentina/Buenos_Aires`) y migración `007` con CHECK de día, de `hora_fin > hora_inicio` y de grilla de 5 minutos, y una restricción de exclusión que impide franjas superpuestas del mismo profesional en el mismo día.
- **API de franjas** anidada en el profesional: `GET /profesionales/{id}/horarios`, `POST /profesionales/{id}/horarios`, `PATCH /profesionales/{id}/horarios/{horario_id}` y `DELETE /profesionales/{id}/horarios/{horario_id}`.
  - Alta → `201`; edición parcial (lo omitido se conserva, `null` → `422`); borrado físico → `204`.
  - Franja inválida (día fuera de 0-6, `hora_fin <= hora_inicio`, hora fuera de la grilla de 5 minutos o con zona horaria) → `422 franja_invalida`; franja superpuesta con otra del mismo profesional y día → `409 franja_superpuesta`; profesional o franja del path inexistente → `404 recurso_inexistente`.
  - Escritura solo `recepcionista` (RN-HB-01, RN-AU-03); lectura de la recepcionista sobre cualquier profesional y del `odontologo` solo sobre su propio profesional (matriz de `03_actores_y_roles.md`); `401`/`403` evaluados antes que el body y que la existencia del path.
- **Validación RN-AG-05 en alta y reprogramación de turnos**: el turno, convertido a hora local, MUST caber completo en una franja del profesional para el día de la semana local de su inicio; si no → `422 fuera_de_horario`. Se evalúa después de las validaciones actuales que dan `422` y antes del pre-chequeo de solape (`409`). Un profesional sin franjas no admite turnos.
- **Cambiar o borrar una franja no toca los turnos existentes**: siguen vigentes y se pueden cancelar; reprogramarlos aplica el horario vigente (RN-AG-08).
- **Seed de desarrollo**: cada profesional del seed atiende de lunes a viernes de 09:00 a 13:00 y de 14:00 a 18:00; re-ejecutarlo no pisa franjas editadas a mano, solo inserta las que falten.

## Non-goals

- Bloqueos de agenda y RN-AG-06 (C-11, Nico; usa el mismo punto de extensión, después del validador de horario), recordatorios (C-12), consulta de agenda y huecos libres (C-13), frontend (C-14..C-16).
- Franjas que crucen la medianoche, excepciones por fecha (feriados, vacaciones: se modelan como bloqueos en C-11) y horarios por sillón.
- Auditar los cambios de horario (RN-CU-01 audita turnos).
- Advertir o rechazar cambios de horario que dejan turnos fuera de franja (ver D8 de `design.md`).

## Capabilities

### New Capabilities
- `horarios-atencion`: franjas de atención por profesional y día de la semana; alta, consulta, edición parcial y borrado; validaciones de la franja y de superposición con garantía en la base; acceso por rol (escritura de la recepcionista, lectura propia del odontólogo); efecto de los cambios de horario sobre los turnos existentes.

### Modified Capabilities
- `agenda-turnos`: se agrega (ADDED) el requisito "Turno dentro del horario de atención" (RN-AG-05) para el alta y la reprogramación, y se modifica (MODIFIED) "Misma validación que el alta al reprogramar" para incluir el horario entre las validaciones que dan `422` antes del solape.
- `datos-semilla`: se modifica (MODIFIED) "Contenido del seed de desarrollo" para sembrar las franjas de ejemplo de los dos profesionales.

## Impact

- **Código nuevo**: `backend/app/domain/horarios.py` (franja, reglas puras de validación y `cabe_en_horario`), `backend/app/application/horarios_atencion.py` (casos de uso y validador de turno), `backend/app/infrastructure/db/models/horario_atencion.py`, `backend/app/infrastructure/db/repositorio_horarios.py`, `backend/app/api/horarios.py`, `backend/alembic/versions/007_horario_atencion.py`.
- **Código modificado**: `backend/app/api/turnos.py` (`get_crear_turno` y `get_reprogramar_turno` inyectan el validador de horario por el punto de extensión `validadores`), `backend/app/domain/recursos.py` (`TipoRecurso.HORARIO`), `backend/app/infrastructure/db/models/__init__.py`, `backend/app/infrastructure/db/seed.py`, `backend/app/main.py`.
- **API**: 4 rutas nuevas. El contrato de `POST /turnos` y `PATCH /turnos/{id}/reprogramar` suma el `422 fuera_de_horario`.
- **Base de datos**: migración `007` (tabla `horario_atencion`, CHECKs, exclusión con `btree_gist`, ya habilitada en `001`) con `downgrade`. Si C-09 (Nico) mergea antes otra `007`, quien mergea segundo renumera (regla del equipo).
- **Tests existentes**: las pruebas de API que crean o reprograman turnos pasan a necesitar una franja; la fábrica `crear_catalogo` siembra por defecto una franja amplia para sus profesionales (D16 de `design.md`). Coordinar con C-11, que toca la misma fábrica y las mismas fábricas de casos de uso de `api/turnos.py`.
- **KB**: registrar las decisiones aprobadas como **DD-27** en `09_decisiones_y_supuestos.md` y precisar la entidad `HorarioAtencion` de `04_modelo_de_datos.md` (convención de `dia_semana`, grilla, sin superposición).
- **Governance**: MEDIO (regla de negocio del núcleo de agenda). Las decisiones D1, D3, D5, D6, D7, D8, D9, D10 y D11 de `design.md` no las fija la KB: el usuario las confirmó (2026-11-02), igual que D17 y D18 (surgidas de la revisión de escenarios); se registran como DD-27.
