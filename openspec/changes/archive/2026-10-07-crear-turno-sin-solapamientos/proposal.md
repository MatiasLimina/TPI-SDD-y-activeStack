# Proposal

## Why

El vacío detectado en el Discovery es que las agendas de consultorios chicos no impiden la doble reserva de un profesional, de un sillón o de un paciente cuando las prestaciones tienen duraciones propias. Con el catálogo y el seed ya disponibles (C-01, C-02), este change entrega el núcleo del producto: crear un turno con la garantía de no superposición asegurada por PostgreSQL, no solo por la aplicación (RN-AG-09). Es el change elegido para el ciclo OPSX y la base sobre la que se enchufan cancelar, reprogramar, horarios, bloqueos, auditoría y recordatorios.

## What Changes

- Nueva entidad `Turno` (modelo SQLAlchemy + migración `003`) con `profesional_id`, `sillon_id` (nullable), `paciente_id`, `prestacion_id`, `inicio`, `fin`, `duracion_min`, `estado` (`varchar` + CHECK `programado|cancelado`, DD-21), `motivo_cancelacion` y `creado_por` nullables, y marcas de tiempo.
- Restricciones en BD: `turno_fin_mayor`, `turno_estado_valido` y tres restricciones de exclusión `EXCLUDE USING gist ... tstzrange(inicio, fin, '[)')` parciales sobre `estado <> 'cancelado'`: por profesional, por sillón y por paciente (RN-AG-01/02/09/14, DD-20).
- Reglas de dominio puras (sin BD): duración efectiva (por defecto la de la prestación, ajustable), cálculo de `fin`, validación de grilla de 5 min y tope de 480 min (DD-15), inicio en el pasado (RN-AG-12), coherencia sillón/prestación (RN-AG-10, DD-21) y solape semiabierto (RN-AG-03).
- Caso de uso `CrearTurno` en `application/` con pre-chequeo de solape que reúne **todos** los recursos en conflicto, traducción de `23P01` a 409 ante carreras, reloj inyectable y dos puntos de extensión vacíos (validadores previos y observadores posteriores).
- Endpoint `POST /turnos` -> `201`; `409` por solape con la lista de recursos en conflicto; `422` por referencia inexistente o inactiva en el body, sillón faltante o sobrante, duración/grilla inválida e inicio en el pasado (DD-21).
- Tests de dominio (unitarios), de persistencia e integración contra PostgreSQL real, y un test de concurrencia (N inserciones simultáneas -> exactamente 1 éxito, DD-18).
- Fuera de alcance: autenticación (`creado_por` queda nulo hasta C-06), auditoría (C-07), recordatorio (C-12), horario de atención (RN-AG-05, C-10), bloqueos (RN-AG-06, C-11), reprogramar (C-05) y cancelar (C-04).

## Capabilities

### New Capabilities
- `agenda-turnos`: creación de turnos de la agenda del consultorio con duración por prestación, coherencia de sillón y garantía de no superposición por profesional, sillón y paciente (aplicación + base de datos), con su contrato de errores HTTP.

### Modified Capabilities
<!-- Ninguna: el catálogo, la línea base de BD y la política de tiempo no cambian sus requisitos; este change los reutiliza. -->

## Impact

- **Código nuevo**: `backend/app/domain/` (reglas de turno y solape), `backend/app/application/` (caso de uso `CrearTurno`), `backend/app/infrastructure/db/models/turno.py` y repositorio, `backend/alembic/versions/003_turno.py`, `backend/app/api/turnos.py` (router y schemas); registro del router en `app/main.py`.
- **Reutiliza**: `app/domain/time.py` (`to_utc`, `to_local`, `NaiveDatetimeError`), la extensión `btree_gist` de la migración 001 y el catálogo de la 002.
- **API**: nuevo `POST /turnos` sin autenticación (C-06 lo protegerá por rol).
- **Base de datos**: nueva tabla `turno` con FKs al catálogo y tres índices GiST de exclusión.
- **Tests**: fixtures nuevas para turnos y un test de concurrencia que necesita conexiones propias con commit real (fuera de la transacción revertida de `db_session`).
- **Changes posteriores**: C-04, C-05, C-07, C-10, C-11 y C-12 se enchufan en los puntos de extensión que define este change.
