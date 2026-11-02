# Proposal

## Why

El recordatorio previo al turno es una de las promesas del MVP (D.4, `01_vision_y_objetivos.md`): "todo turno activo genera un recordatorio previo" (RN-NO-01), que cancelar lo cancela y reprogramar lo reprograma (RN-NO-02). Hoy el sistema crea, reprograma y cancela turnos (C-03..C-05), con autor y auditoría (C-06, C-07), pero no genera ningún recordatorio: `NOTIFICATION_ADAPTER` existe en la configuración y Redis está en `docker-compose.yml`, y ninguno de los dos se usa. Con C-01, C-04 y C-05 archivados, los tres casos de uso ya exponen los observadores transaccionales donde la auditoría de C-07 se enchufó, y el recordatorio se enchufa igual. Las decisiones de producto que hacían falta ya están tomadas: 24 h de anticipación y nada si falta menos (DD-13), y 3 intentos con backoff exponencial antes de `fallido`, sin reintento manual (DD-19).

## What Changes

- **Nueva tabla `recordatorio`** (migración `006`): `id`, `turno_id`, `programado_para` (`timestamptz`, UTC), `estado` (`pendiente` | `enviado` | `fallido` | `cancelado`), `canal` (`mock`) e `intentos` (0 a 3). La integridad vive en la base: `estado` y `canal` como `varchar` + CHECK (criterio de DD-21), coherencia entre `estado` e `intentos`, FK a `turno` que impide borrarlo y **a lo sumo un recordatorio `pendiente` por turno** (índice único parcial).
- **Programación en la misma transacción que el turno**: al crear un turno con 24 h o más de anticipación (`REMINDER_LEAD_HOURS`, configurable) se inserta un recordatorio `pendiente` con `programado_para = inicio - 24 h`. Con menos de 24 h no se programa nada (RN-NO-03, DD-13). Cancelar el turno cancela su recordatorio pendiente. Reprogramarlo con otro inicio cancela el pendiente y programa uno nuevo si al nuevo inicio le faltan 24 h o más (RN-NO-02). Si el recordatorio falla, el cambio del turno (y su auditoría) se revierte. Una operación rechazada no toca recordatorios.
- **Cola Redis**: después del commit, el id del recordatorio se publica en una cola con fecha de vencimiento (sorted set). La base es la fuente de verdad: si Redis no responde, la operación sobre el turno igual se confirma y el recordatorio queda `pendiente` en la base hasta que el worker lo re-encola.
- **Worker de recordatorios** (nuevo servicio `worker` en Docker Compose): al arrancar re-encola los `pendiente` de la base; después toma los vencidos, verifica bajo bloqueo que el recordatorio siga `pendiente` y el turno siga `programado`, e invoca el puerto `NotificationSender`. Si el envío sale bien, el recordatorio pasa a `enviado`. Si falla, se reintenta con backoff exponencial hasta completar 3 intentos y después queda `fallido`, sin reintento manual (RN-NO-05, DD-19).
- **Puerto `NotificationSender` (dominio) y adaptador `MockSender`**: el mock registra el envío (en memoria y en el log), sin mensajería real. `NOTIFICATION_ADAPTER=mock` es el único valor válido.
- **Contenido sin datos clínicos** (RN-NO-04): el mensaje lleva solo fecha y hora del turno en `America/Argentina/Buenos_Aires` y el nombre del consultorio. Nunca la prestación, el profesional, el nombre del paciente ni el motivo de una cancelación.
- **Configuración**: nuevas variables `REMINDER_LEAD_HOURS` (entero > 0, por defecto `24`) y `CONSULTORIO_NOMBRE` (no vacío). `NOTIFICATION_ADAPTER` pasa a validarse. Todas se agregan a `.env.example`.

## Non-goals

- Mensajería real (WhatsApp Business API, email, SMS): solo puerto + mock (backlog de `CHANGES.md`).
- Reintento manual de un recordatorio `fallido` (DD-19) y envío inmediato cuando faltan menos de 24 h (descartado en DD-13).
- Endpoint de consulta del estado de los recordatorios: la matriz de `03_actores_y_roles.md` lo menciona, pero el scope de C-12 en `CHANGES.md` no lo incluye (ver preguntas abiertas en `design.md`).
- Auditar recordatorios: RN-CU-01 audita cambios de turno. El recordatorio no es un turno y lo cambia el sistema, no un usuario.
- Reportar Redis o el worker en `GET /health`.
- Horarios de atención (C-10), bloqueos (C-11), agenda (C-13), gestión de recursos (C-08), pacientes (C-09) y frontend (C-14..C-16).

## Capabilities

### New Capabilities
- `recordatorios`: ciclo de vida del recordatorio previo al turno. Cubre la programación atómica con el alta, la cancelación y la reprogramación del turno según la anticipación configurada; la integridad en la base; la cola Redis y su re-encolado al arrancar; el worker que verifica el turno y envía por el puerto de notificación (adaptador mock); los reintentos acotados con estado `fallido`; el contenido sin datos clínicos; y el servicio `worker` en Docker Compose.

### Modified Capabilities
- `app-configuration`: se leen `REMINDER_LEAD_HOURS` y `CONSULTORIO_NOMBRE`. `REMINDER_LEAD_HOURS`, `NOTIFICATION_ADAPTER` y `CONSULTORIO_NOMBRE` se validan al cargar la configuración, y `.env.example` declara las tres variables más `TEST_REDIS_URL`.

<!-- `agenda-turnos` no cambia: los contratos HTTP de crear, reprogramar y cancelar (códigos, cuerpos, estados) quedan iguales. El efecto nuevo (programar, cancelar o reprogramar el recordatorio de forma atómica) lo especifica `recordatorios`, con el mismo criterio que usó C-07 para la auditoría. -->

## Impact

- **Código nuevo**: `backend/app/domain/recordatorios.py` (estados, cálculo de `programado_para`, backoff, puerto `ColaRecordatorios`), `backend/app/domain/notificaciones.py` (puerto `NotificationSender`, `MensajeRecordatorio` y armado del contenido), `backend/app/infrastructure/db/models/recordatorio.py`, `backend/app/infrastructure/db/repositorio_recordatorios.py`, `backend/app/application/recordatorios.py` (programador que se registra como observador, procesamiento de un recordatorio vencido, re-encolado), `backend/app/infrastructure/queue/cola_redis.py`, `backend/app/infrastructure/notifications/mock_sender.py`, `backend/app/worker.py` (proceso `python -m app.worker`) y `backend/alembic/versions/006_recordatorio.py`.
- **Código modificado**: `backend/app/api/turnos.py` (las fábricas registran el programador como observador y las rutas publican en la cola después del commit), `backend/app/config.py`, `backend/app/infrastructure/db/models/__init__.py`, `backend/pyproject.toml` (dependencia `redis`; `pyyaml` en dev para el test de Compose), `docker-compose.yml` (servicio `worker` y variables nuevas) y `.env.example`.
- **API**: ningún endpoint nuevo. `POST /turnos`, `PATCH /turnos/{id}/reprogramar` y `POST /turnos/{id}/cancelar` mantienen su contrato.
- **Base de datos**: migración `006` (tabla, CHECKs, FK, índice único parcial e índices, con `downgrade`). C-08 (Matías) también puede tomar `006`: quien mergea segundo renumera su revisión y verifica que `alembic heads` muestre una sola cabeza.
- **Tests**: unitarios de dominio (programación, backoff, contenido), de migración y restricciones contra PostgreSQL real, de contrato de la cola contra Redis real (`TEST_REDIS_URL`) y contra la cola en memoria que usan los demás tests, de caso de uso (atomicidad, worker, reintentos, re-encolado) y de API. Además se actualiza el `head` esperado en `test_migrations.py` y la fixture `client` sobreescribe la cola con la de memoria.
- **KB**: nueva decisión DD-26 con las decisiones de este change, `04_modelo_de_datos.md` §Recordatorio, `08_arquitectura_propuesta.md` (variables `CONSULTORIO_NOMBRE` y `TEST_REDIS_URL`, servicio `worker`) y la redacción de RN-NO-05 alineada a "3 intentos en total".
- **Governance**: ALTO (worker, cola y datos de contacto del paciente). Antes del Apply, el usuario revisa y aprueba las decisiones marcadas **[A confirmar]** en `design.md`.
