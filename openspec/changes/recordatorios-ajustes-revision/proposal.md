# Proposal

## Why

La revisión del PR #8 (C-12, `recordatorios-mock-redis`, Matías) dejó 8 hallazgos sobre el worker de recordatorios, la cola Redis, el adaptador mock, la base y Compose. Dos de ellos ya figuran como preguntas abiertas en `10_preguntas_abiertas.md` ("Recordatorio procesado después del inicio del turno" y "Backoff perdido al reiniciar el worker"). El equipo decidió resolverlos en este change chico, sobre la misma rama y el mismo PR, antes del merge de C-12. Así C-12 no entra a `main` con huecos conocidos de integridad (un `pendiente` con 3 intentos que la base acepta), de comportamiento (un recordatorio enviado cuando el turno ya empezó y un backoff que se pierde al reiniciar) ni de recursos (el mock acumula en memoria todo lo que envía).

Es un change de seguimiento de C-12: no agrega una entrada nueva al roadmap ni un bloque nuevo en `CHANGES.md`.

## What Changes

**Reglas nuevas (decisión DD-29, a registrar en la KB en el Apply; governance ALTO, requieren aprobación):**
- **Sin envío para turnos ya iniciados** (hallazgo 1): el worker MUST NOT enviar el recordatorio si `turno.inicio <= ahora`, con el mismo criterio de "iniciado" que RN-AG-13 y DD-23 (`inicio <= ahora`). Lo descarta y el recordatorio queda `cancelado`. Cubre también los recordatorios re-encolados después de una caída larga.
- **Backoff persistido en la base** (hallazgos 2 y 3): al registrar un intento fallido que no agota los intentos, `programado_para` pasa a ser el instante del próximo intento: el momento de la falla, leído del reloj en ese instante y no al inicio del ciclo, más la espera de DD-19/DD-28. Así el re-encolado al iniciar respeta el backoff. **`programado_para` cambia de significado**: deja de ser "inicio − anticipación" y pasa a ser "próximo intento programado", que al crear el recordatorio vale inicio − anticipación.
- **CHECK que cierra el hueco `pendiente` con 3 intentos** (hallazgo 4): una migración `009` agrega la restricción `estado <> 'pendiente' OR intentos < 3`, reversible.
- **Devolución a la cola ante un error a mitad de lote** (hallazgo 5): antes de terminar el proceso (sigue siendo crash-only), el worker devuelve a la cola, best-effort, los ids que tomó y no llegó a procesar, y relanza el error.

**Sin regla nueva (ajustes de implementación con redacción de escenarios):**
- **`MockSender` sin estado acumulado** (hallazgo 6): el mock solo registra en el log. Los tests que necesitan inspeccionar lo enviado usan un emisor de test que registra (`tests/fakes.py`).
- **Tomar los vencidos en un solo viaje a Redis** (hallazgo 7): un script Lua reemplaza el `ZREM` por id y conserva la entrega a un solo consumidor.
- **La API depende de Redis en Compose** (hallazgo 8): el servicio `api` declara `depends_on: redis: condition: service_started`, como el `worker`.

**Documentación (en el Apply):** DD-29 en `09`; las dos preguntas abiertas pasan a resueltas en `10`; `04` §Recordatorio (significado de `programado_para` y CHECK nuevo); `05` (RN-NO-05 y la referencia a DD-29 por el descarte de turnos iniciados); `07` Flujo 6; `08` (Compose); se quita del backlog de `CHANGES.md` la línea "Persistir el vencimiento del próximo reintento..."; y se actualiza el aviso de preguntas abiertas en `CLAUDE.md` y `AGENTS.md`, que deben quedar idénticos.

## Capabilities

### New Capabilities

Ninguna.

### Modified Capabilities

- `recordatorios`: se modifican los requisitos "Envío del recordatorio vencido por el worker" (el envío exige un turno no iniciado y el mock no acumula estado), "Reintentos con backoff exponencial y estado fallido" (el próximo vencimiento se persiste en `programado_para`, con el reloj del momento de la falla), "Re-encolado de pendientes al iniciar el worker" (el reinicio conserva el backoff), "Integridad del recordatorio en la base" (`pendiente` con 3 intentos rechazado) y "Cola de recordatorios con vencimiento" (consumidores simultáneos). Se agregan los requisitos "Sin envío para turnos ya iniciados", "Devolución a la cola de lo tomado y no procesado" y "La API depende de Redis en Compose" (va aparte de "Worker desplegado como servicio", que no cambia, porque ese requisito trata del servicio `worker`).

`app-configuration` no cambia: no hay variables nuevas.

## Impact

- **Código**: `backend/app/application/recordatorios.py` (`ProcesarRecordatorio`, `WorkerRecordatorios`: reloj inyectado, chequeo de turno iniciado, devolución a la cola), `backend/app/infrastructure/db/repositorio_recordatorios.py` (`registrar_fallo` persiste el próximo vencimiento), `backend/app/infrastructure/db/models/recordatorio.py` (CHECK nuevo), `backend/app/infrastructure/queue/cola_redis.py` (script Lua), `backend/app/infrastructure/notifications/mock_sender.py` (sin lista), `backend/app/worker.py` (reloj hacia el worker) y `docker-compose.yml`.
- **Base**: migración nueva `backend/alembic/versions/009_recordatorio_pendiente_intentos.py` (`down_revision = "008"`). Si otra rama mergea antes una `009`, se renumera según la regla del equipo.
- **Tests**: `tests/fakes.py` (reloj manual, emisor que registra, dobles de falla de la cola) y los tests de recordatorios, de migración, de contrato de la cola, del worker y de Compose. Las firmas de `ciclo` y `procesar` cambian (ver design), así que se ajustan sus llamadas en los tests existentes.
- **API HTTP**: sin cambios de contrato.
- **Dependencias**: ninguna nueva (los scripts Lua vienen con redis-py).
- **KB y documentación**: `04`, `05`, `07`, `08`, `09`, `10`, `CHANGES.md` (backlog), `CLAUDE.md` y `AGENTS.md`.
- **Fuera de alcance**: el endpoint de lectura del estado de los recordatorios (sigue como pregunta abierta), la reconciliación periódica mientras el worker corre, la persistencia de Redis y la entrega "exactamente una vez".
