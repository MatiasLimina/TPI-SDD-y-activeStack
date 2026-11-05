# Proposal

## Why

Hoy la agenda solo sabe cuándo atiende cada profesional (C-10), pero no cuándo deja de atender en una fecha puntual: un congreso, un trámite o unas vacaciones no se pueden registrar, y la recepción puede darle turnos en esas horas. RN-HB-02, RN-AG-06 y US-003 piden bloquear franjas por profesional (la recepcionista cualquiera, el odontólogo solo las suyas, RN-AU-02), que ningún turno nuevo ni reprogramado caiga dentro de un bloqueo y, por RN-HB-03 y DD-12, que un bloqueo nunca pise turnos activos: se rechaza con `409` y la lista de los turnos afectados. Con C-04, C-05, C-06 y C-08 archivados, y con el validador de horario de C-10 ya enchufado en el punto de extensión `validadores`, la regla entra sin tocar el orden de las validaciones existentes. C-13 (consulta de agenda) depende de este change.

## What Changes

- **Modelo `Bloqueo`** (`profesional_id`, `inicio`, `fin` en `timestamptz` UTC, `motivo`, `creado_por`) y migración **`010`** (`down_revision = "009"`) con CHECK de `fin > inicio` y de motivo no vacío.
- **API de bloqueos** para ambos roles autenticados:
  - `POST /bloqueos` con `[inicio, fin)` y `motivo` → `201`. La recepcionista indica el `profesional_id`; para el odontólogo el profesional sale del token (Flujo 5) y uno distinto se rechaza con `403 profesional_ajeno`.
  - Bloqueo con turnos activos del mismo profesional en el intervalo → `409 bloqueo_con_turnos` con la lista de turnos afectados, sin persistir nada (RN-HB-03, DD-12). Un turno contiguo (que termina justo al empezar el bloqueo o empieza justo al terminar) no cuenta, y un turno cancelado tampoco.
  - Bloqueo inválido (`fin <= inicio`, motivo vacío) → `422 bloqueo_invalido`; datetime sin zona → `422`; profesional inexistente → `422 referencia_invalida`.
  - `GET /bloqueos` (la recepcionista ve todos o filtra por `profesional_id`; el odontólogo, solo los suyos) y `DELETE /bloqueos/{id}` (`204`; el odontólogo solo los suyos, y sobre uno ajeno o inexistente recibe `403 profesional_ajeno`, sin revelar si existe).
- **Validación RN-AG-06 en alta y reprogramación de turnos**: un turno que se superpone con un bloqueo de su profesional se rechaza con `422 turno_en_bloqueo`. Uno que empieza justo al terminar el bloqueo, o termina justo al empezar, es válido. Se evalúa después del horario de atención (C-10) y antes del pre-chequeo de solape (`409`).
- **Concurrencia**: un bloqueo y un turno simultáneos sobre el mismo intervalo del mismo profesional nunca quedan los dos persistidos. La garantía cruza dos tablas, así que no hay restricción de exclusión que la cubra; se serializa con un lock sobre la fila del profesional (ver `design.md` D13) y se prueba con un test de concurrencia.

## Non-goals

- Consulta de agenda con turnos y bloqueos por rango (`GET /turnos?desde&hasta…`, C-13), disponibilidad, recordatorios (C-12, sin cambios) y frontend (C-14..C-16).
- Bloqueos por sillón (la **Suposición** de `04_modelo_de_datos.md`, ver D4), edición de un bloqueo (D3) y bloqueos recurrentes.
- Auditar los bloqueos: RN-CU-01 audita cambios de turno; el bloqueo guarda `creado_por`.
- Cambiar, cancelar o marcar turnos al bloquear (DD-12 descarta las dos alternativas).

## Capabilities

### New Capabilities
- `bloqueos-agenda`: bloqueos de agenda por profesional con intervalo semiabierto y motivo; alta con rechazo `409` ante turnos activos; consulta y borrado; acceso por rol (la recepcionista sobre cualquier profesional, el odontólogo solo sobre el suyo); integridad en la base; serialización con el alta y la reprogramación de turnos.

### Modified Capabilities
- `agenda-turnos`: se agrega (ADDED) el requisito "Turno fuera de los bloqueos de agenda" (RN-AG-06) para el alta y la reprogramación, y se modifica (MODIFIED) "Misma validación que el alta al reprogramar" para incluir los bloqueos entre las validaciones que dan `422` antes del solape.

## Impact

- **Código nuevo**: `backend/app/domain/bloqueos.py`, `backend/app/application/bloqueos_agenda.py` (casos de uso y validador de turno), `backend/app/infrastructure/db/models/bloqueo.py`, `backend/app/infrastructure/db/repositorio_bloqueos.py`, `backend/app/api/bloqueos.py`, `backend/alembic/versions/010_bloqueo.py`.
- **Código modificado**: `backend/app/api/turnos.py` (`_validadores` suma el validador de bloqueos **después** del de horario), `backend/app/domain/horarios.py` (`ProfesionalAjenoError` con mensaje propio por recurso), `backend/app/domain/recursos.py` (`TipoRecurso.BLOQUEO`), `backend/app/infrastructure/db/models/__init__.py`, `backend/app/main.py`.
- **API**: 3 rutas nuevas. El contrato de `POST /turnos` y `PATCH /turnos/{id}/reprogramar` suma el `422 turno_en_bloqueo`.
- **Base de datos**: migración `010` (tabla `bloqueo`, CHECKs, FKs e índice) con `downgrade`. `main` está en `009`. Si C-13 (Matías) u otro change mergea antes una `010`, quien mergea segundo renumera (regla del equipo); hay una tarea para correr `revisar-migraciones` antes del PR.
- **Recordatorios (C-12)**: sin cambios. Crear un bloqueo no modifica turnos (se rechaza si hay activos). Un turno rechazado por RN-AG-06 corta antes del `INSERT`/`UPDATE`, así que no crea, cancela ni encola recordatorios. Lo cubren escenarios explícitos.
- **Tests existentes**: los fixtures que borran usuarios deben borrar antes sus bloqueos (FK `creado_por`). La fábrica `crear_catalogo` no cambia.
- **KB**: registrar las decisiones aprobadas como **DD-30** en `09_decisiones_y_supuestos.md`, precisar la entidad Bloqueo de `04`, la tabla de API de `02` y la fila "Bloqueos de agenda" de la matriz de `03` según D3.
- **Governance**: MEDIO. Las decisiones de `design.md` que no fija la KB (D1-D9, D11-D13) las aprobó el usuario el 2026-11-04, D12 con `403` antes de la existencia (como DD-27 i). Se registran como DD-30.
