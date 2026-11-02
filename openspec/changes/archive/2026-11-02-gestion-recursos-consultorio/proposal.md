# Proposal

## Why

Hoy los profesionales, sillones y prestaciones solo existen por el seed de desarrollo (C-02): no hay forma de dar de alta un profesional nuevo, sacar de servicio un sillón ni corregir la duración de una prestación sin tocar la base a mano. US-001 pide que la recepcionista los gestione (alta, edición y desactivación lógica) para poder agendar, RN-AU-03 y la matriz de `03_actores_y_roles.md` reservan esa escritura a la recepcionista (el odontólogo solo lee), y DD-15 exige que `Prestacion.duracion_min` respete la misma grilla que los turnos (> 0, múltiplo de 5 y ≤ 480) **con CHECK en la base**, cosa que C-02 dejó pendiente para este change. Con C-06 archivado ya existen el usuario autenticado y la dependencia de rol, y C-08 está en el camino crítico: C-10 (horarios) y C-11 (bloqueos) dependen de él.

## What Changes

- **API de recursos** con el mismo contrato para los tres: `GET /profesionales`, `GET /profesionales/{id}`, `POST /profesionales`, `PATCH /profesionales/{id}` y `POST /profesionales/{id}/desactivar`; ídem `/sillones` y `/prestaciones`.
  - Alta → `201` con el recurso, siempre activo. Edición parcial (`PATCH`): lo omitido se conserva, `null` explícito en un campo obligatorio → `422`, `matricula` admite `null` para quitarla.
  - Desactivación lógica (`activo`/`activa = false`), nunca borrado; desactivar un recurso ya inactivo responde `200` sin cambios (idempotente).
  - Recurso del path inexistente → `404` (DD-21); identificador mal formado → `422`; nombre de sillón o prestación, o matrícula, repetidos → `409`.
- **Validación de la duración de la prestación** (DD-15, RN-AG-04): `duracion_min` > 0, múltiplo de 5 y ≤ 480 → si no, `422 duracion_invalida`, con la **misma** regla de dominio que ya usan crear y reprogramar turnos. `requiere_sillon` se informa en el alta (por defecto `true`, RN-AG-10) y se puede editar.
- **CHECK en la base** (migración `006`): `duracion_min % 5 = 0` y `duracion_min <= 480` sobre `prestacion`, además del `> 0` de C-02, que sigue vigente.
- **Acceso por rol** (RN-AU-03): escritura solo `recepcionista`; lectura `recepcionista` y `odontologo`; sin token → `401`; odontólogo que escribe → `403 rol_insuficiente`, evaluado antes que el body y que la existencia del recurso.
- **Un recurso desactivado no admite turnos nuevos pero conserva su historial**: `POST /turnos` y `PATCH /turnos/{id}/reprogramar` ya responden `422` ante una referencia inactiva (requisito "Referencias del body existentes y activas" de `agenda-turnos`); este change lo cubre de punta a punta a través del endpoint de desactivación, garantiza que los turnos existentes no se tocan (siguen en la base, se pueden consultar y cancelar) y cierra la carrera entre una desactivación y un alta o una reprogramación simultáneas.
- **El estado de actividad no se edita por `PATCH` ni se informa en el alta**: un body con `activo`/`activa` → `422 campo_no_editable` (mismo criterio que DD-23: no ignorar en silencio lo que el cliente cree que cambió). No hay reactivación en este change (D6 de `design.md`).

## Non-goals

- **Reactivar** un recurso desactivado, **borrado físico** y **listados filtrados o paginados** (los volúmenes son de 1-5 profesionales, 1-4 sillones y pocas prestaciones).
- **Auditar** los cambios del catálogo: RN-CU-01 audita cambios de turnos (C-07).
- **Bloquear o advertir** la desactivación de un recurso con turnos futuros, y cualquier efecto sobre el usuario `odontologo` vinculado a un profesional desactivado (D11 y D12 de `design.md`, confirmadas por el usuario el 2026-11-02: la desactivación se permite y el usuario no cambia).
- Horarios de atención (C-10), bloqueos (C-11), pacientes (C-09), lecturas de turnos y agenda (C-13), recordatorios (C-12) y frontend (C-14..C-16).
- Precios, cobertura u obras sociales de la prestación (fuera del MVP, `04_modelo_de_datos.md`).

## Capabilities

### New Capabilities
- `gestion-recursos`: API de alta, lectura, edición parcial y desactivación lógica de profesionales, sillones y prestaciones; validaciones de la duración por defecto y de los atributos; unicidad informada como `409`; acceso por rol (escritura de la recepcionista, lectura de ambos roles); y efecto de la desactivación sobre los turnos (bloquea los nuevos, conserva los existentes, sin carreras).

### Modified Capabilities
- `catalogo-consultorio`: se agrega (ADDED) el requisito de que la base rechace por sí misma una `duracion_min` que no sea múltiplo de 5 o que supere 480 (DD-15). El requisito "Prestación con duración positiva" no cambia.

`agenda-turnos` **no** se modifica: sus requisitos ya exigen referencias activas al crear y al reprogramar (`422`), y su contrato HTTP no cambia. La serialización frente a una desactivación simultánea es un detalle de implementación de esa misma regla y se especifica desde `gestion-recursos`.

## Impact

- **Código nuevo**: `backend/app/domain/grilla.py` (regla pura de la grilla de 5 minutos, `duracion_en_grilla`), `backend/app/domain/recursos.py` (errores y reglas puras del catálogo), `backend/app/application/gestion_recursos.py` (casos de uso), `backend/app/infrastructure/db/repositorio_recursos.py`, `backend/app/api/recursos.py` (tres routers), `backend/alembic/versions/006_prestacion_duracion_grilla.py`.
- **Código modificado**: `backend/app/domain/turnos.py` (`validar_duracion_y_grilla` pasa a usar `duracion_en_grilla` de `grilla.py`, compartida con el catálogo; refactor protegido por los tests de C-03/C-05), `backend/app/infrastructure/db/models/prestacion.py` (CHECKs nuevos), `backend/app/infrastructure/db/repositorio_turnos.py` (`cargar_referencias` toma `FOR SHARE` sobre las referencias), `backend/app/api/auth.py` (alias de dependencia por rol compartidos), `backend/app/api/turnos.py` y `backend/app/api/auditoria.py` (importan el alias desde `auth`), `backend/app/main.py` (routers y manejadores nuevos).
- **API**: 15 rutas nuevas (5 por recurso). Las rutas de turnos, auth y auditoría no cambian su contrato.
- **Base de datos**: migración `006` con dos CHECK sobre `prestacion` y `downgrade`. Si C-12 (Nico) mergea antes otra `006`, quien mergea segundo renumera su revisión (regla del equipo).
- **Tests**: unitarios de dominio, de migración y de CHECK contra PostgreSQL real, de repositorio, de API por recurso y por rol, de desactivación sobre turnos y de concurrencia de la desactivación con el alta y con la reprogramación; se actualiza el `head` esperado en `test_migrations.py`.
- **KB**: registrar las decisiones aprobadas de este change como **DD-26** y alinear la tabla de API de `02_descripcion_general.md` (hoy no dice que el odontólogo lee sillones y prestaciones, aunque la matriz de `03` y US-001 sí).
- **Governance**: BAJO (CRUD de catálogo). Las decisiones de `design.md` que la KB no fijaba (D5, D6, D7, D9, D11, D12) las confirmó el usuario el 2026-11-02.
