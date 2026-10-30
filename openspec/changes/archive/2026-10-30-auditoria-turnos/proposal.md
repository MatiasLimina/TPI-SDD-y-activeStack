# Proposal

## Why

Desde C-06 cada alta, reprogramación y cancelación de turno la hace una recepcionista autenticada, pero el sistema solo guarda quién **creó** el turno (`creado_por`): una reprogramación pisa el horario anterior y una cancelación no deja rastro de quién la hizo ni cuándo. RN-CU-01 (Ley 25.326 y 26.529) exige auditar **todo** cambio de turno con usuario y momento en un registro append-only, y las excepciones globales de `05_reglas_de_negocio.md` exigen que cada operación sea atómica junto con su registro. US-011 pide además que la recepcionista pueda consultar ese historial. Con C-04, C-05 y C-06 archivados, los tres casos de uso y el usuario autenticado ya existen, y C-03/C-05 dejaron los observadores transaccionales donde se enchufa la auditoría.

## What Changes

- **Nueva tabla `turno_auditoria`** (migración `005`): `id`, `turno_id`, `usuario_id`, `accion` (`crear` | `reprogramar` | `cancelar`), `valores_previos` y `valores_nuevos` (`jsonb`), `ocurrido_en` (`timestamptz`, UTC). Integridad en la base: `accion` como `varchar` + CHECK (criterio de DD-21), coherencia entre la acción y la presencia de valores previos, claves foráneas a `turno` y `usuario` que impiden borrarlos.
- **Append-only garantizado por la base**: un trigger rechaza `UPDATE`, `DELETE` y `TRUNCATE` sobre `turno_auditoria`; la aplicación solo expone inserción y lectura.
- **Registro en la misma transacción** en crear, reprogramar y cancelar: una fila por operación exitosa, con el usuario autenticado, la acción, la instantánea del turno antes y después del cambio, y el instante del cambio. Si el registro falla, el cambio del turno se revierte (rollback conjunto). Una operación rechazada (`401`, `403`, `404`, `409`, `422`) no genera registro.
- **Nuevo endpoint `GET /turnos/{id}/auditoria`**: devuelve en orden cronológico los registros del turno, con los instantes presentados en `America/Argentina/Buenos_Aires`. Solo `recepcionista` (matriz de `03_actores_y_roles.md`); el odontólogo recibe `403 rol_insuficiente`. Turno inexistente → `404 turno_inexistente`; identificador mal formado → `422`.
- **Refactor menor protegido por los tests existentes**: el observador de cancelación pasa a recibir el turno anterior y el nuevo (igual que el de reprogramación), para que la auditoría registre el estado previo real en vez de deducirlo. No hay observadores registrados hoy, así que no cambia ningún comportamiento.

## Non-goals

- **Backfill**: los turnos creados antes de este change no reciben un registro `crear` retroactivo; su historial empieza con el primer cambio posterior.
- **Auditar lecturas** (incluida la consulta de auditoría) o intentos rechazados: RN-CU-01 audita cambios de turno.
- **Listado global** de auditoría con filtros (por fecha, usuario o profesional) y nombre o email del usuario en la respuesta: la consulta es por turno y devuelve `usuario_id` (ver preguntas abiertas en `design.md`).
- **Rol de base de datos de mínimo privilegio** (`REVOKE UPDATE, DELETE`): la aplicación se conecta hoy como dueña de las tablas, por lo que el trigger es la garantía efectiva; separar roles queda en el backlog.
- Horarios de atención (C-10), bloqueos (C-11), recordatorios (C-12), gestión de recursos (C-08), pacientes (C-09), agenda y lecturas de turnos (C-13) y frontend (C-14..C-16).

## Capabilities

### New Capabilities
- `auditoria-turnos`: registro append-only de los cambios de turnos (crear, reprogramar, cancelar) con usuario, acción, valores previos y nuevos e instante UTC; atomicidad del cambio con su registro; integridad e inmutabilidad garantizadas por la base; y consulta del historial de un turno, reservada a la recepcionista.

### Modified Capabilities
<!-- Ninguna: los contratos HTTP de crear, reprogramar y cancelar (códigos, cuerpos, estados) no cambian; el efecto nuevo —el registro atómico— lo especifica `auditoria-turnos`. -->

## Impact

- **Código nuevo**: `backend/app/domain/auditoria.py` (acciones e instantánea pura del turno), `backend/app/infrastructure/db/models/turno_auditoria.py`, `backend/app/infrastructure/db/repositorio_auditoria.py` (solo `registrar` y `listar_por_turno`), `backend/app/application/auditoria_turnos.py` (auditor que se registra como observador y caso de uso de consulta), `backend/app/api/auditoria.py` (ruta `GET /turnos/{id}/auditoria`), `backend/alembic/versions/005_turno_auditoria.py`.
- **Código modificado**: `backend/app/api/turnos.py` (las dependencias de los tres casos de uso registran el auditor con el usuario autenticado y el reloj), `backend/app/application/cancelar_turno.py` (firma del observador `(anterior, nuevo)`), `backend/app/infrastructure/db/models/__init__.py`, `backend/app/main.py` (router nuevo).
- **API**: nuevo `GET /turnos/{id}/auditoria`. `POST /turnos`, `PATCH /turnos/{id}/reprogramar` y `POST /turnos/{id}/cancelar` no cambian su contrato.
- **Base de datos**: migración `005` (tabla, índices, CHECK, FKs y trigger append-only, con `downgrade`). Si C-08 también agrega una `005`, quien mergea segundo renumera (regla del equipo).
- **Tests**: unitarios de la instantánea, de migración y de restricciones contra PostgreSQL real, de caso de uso (incluido el rollback conjunto) y de API; se actualiza la revisión `head` esperada en `test_migrations.py`.
- **KB**: registrar las decisiones de este change como DD-25 y alinear el endpoint de auditoría en `02_descripcion_general.md` (hoy dice `GET /auditoria/turnos`).
- **Governance**: CRITICO (auditoría y datos de salud). El Apply requiere aprobación humana explícita del plan.
