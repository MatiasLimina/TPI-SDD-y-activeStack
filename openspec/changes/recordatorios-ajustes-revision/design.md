# Design

## Context

Motivación y alcance: ver `proposal.md`. Requisitos: delta spec `specs/recordatorios/spec.md`. Este change ajusta lo que C-12 (`recordatorios-mock-redis`, archivado en `openspec/changes/archive/2026-11-02-recordatorios-mock-redis/`) dejó implementado en la misma rama. Las decisiones de C-12 (D1..D16, registradas en DD-28) siguen vigentes salvo donde este design las cambia explícitamente.

Estado actual del código que se toca:

- `app/application/recordatorios.py`:
  - `ProcesarRecordatorio.procesar(recordatorio_id, ahora)` bloquea con `bloquear_para_envio` (turno `FOR SHARE` y después recordatorio `FOR UPDATE`), descarta si no está `pendiente`, cancela si el turno no está `programado` y envía. No mira `inicio` (hallazgo 1).
  - Ante una falla del emisor calcula el reintento con el `ahora` recibido, que es el del inicio del ciclo (hallazgo 3), y lo encola después del commit. En la base solo cambia `intentos`: el vencimiento del reintento vive únicamente en Redis (hallazgo 2).
  - `WorkerRecordatorios.ciclo(ahora)` toma hasta 100 vencidos y los procesa en orden. Si uno lanza, el resto ya salió de Redis y no vuelve hasta el próximo `iniciar()` (hallazgo 5).
- `app/infrastructure/db/repositorio_recordatorios.py`: `registrar_fallo` hace `intentos + 1` y pasa a `fallido` al llegar a `MAX_INTENTOS`. El CHECK `ck_recordatorio_intentos_segun_estado` de la migración `008` no impide un `pendiente` con 3 intentos (hallazgo 4).
- `app/infrastructure/queue/cola_redis.py`: `tomar_vencidos` hace `ZRANGEBYSCORE` y un `ZREM` por id: 1 + N viajes (hallazgo 7).
- `app/infrastructure/notifications/mock_sender.py`: `MockSender.enviados` crece sin límite durante toda la vida del worker (hallazgo 6). El commit `cc627a3` ya sacó `paciente_id` del log.
- `app/worker.py`: `correr(worker, reloj=..., ...)` llama `worker.ciclo(reloj())`.
- `docker-compose.yml`: `worker` depende de `redis` (`service_started`) y `api` no (hallazgo 8).
- Tests: `tests/fakes.py` tiene `ColaEnMemoria`, `ColaQueFalla` y `EmisorQueFalla`. 29 llamadas a `ciclo(ahora)` en los tests de integración. `helpers_recordatorios.armar_worker` arma el worker sobre la sesión de test. `test_migrations.py` espera `head == "008"`.
- Criterio de "iniciado" ya vigente en el dominio: `validar_modificable` usa `inicio <= ahora` → `turno_ya_iniciado` (RN-AG-13, DD-23).

## Goals / Non-Goals

**Goals:**
- Cerrar los 8 hallazgos con el menor cambio posible sobre lo implementado, sin tocar los contratos HTTP ni la programación en los casos de uso de turnos.
- Una sola fuente de tiempo en el worker: un reloj inyectado, determinístico en los tests y sin `sleep`.
- La base sigue siendo la fuente de verdad. Con este change, también del próximo intento.

**Non-Goals:**
- Reconciliación periódica mientras el worker corre, persistencia de Redis (`appendonly`) y entrega "exactamente una vez" (siguen como limitaciones de DD-28).
- El endpoint de lectura del estado de los recordatorios (sigue como pregunta abierta).
- Cambiar el backoff (1 y 2 min) o el tope de 3 intentos.

## Decisions

Governance ALTO. Las decisiones marcadas **[A confirmar]** son reglas nuevas: no se implementan hasta que el usuario las apruebe y, una vez aprobadas, se registran como **DD-29** en `knowledge-base/09_decisiones_y_supuestos.md` (tarea 9.1). D5..D8 son decisiones de implementación sin regla de dominio nueva.

| Id | Decisión | Hallazgo | Fuente |
|---|---|---|---|
| D1 | Turno ya iniciado (`inicio <= ahora`) → no se envía y el recordatorio queda `cancelado`, con sus `intentos` | 1 | RN-AG-13, DD-23 (criterio de "iniciado"); el estado final es **[A confirmar]** |
| D2 | `programado_para` = próximo intento programado; `registrar_fallo` lo persiste con el reloj del momento de la falla | 2, 3 | DD-19, DD-28 (d); cambio de significado **[A confirmar]** |
| D3 | Migración `009`: CHECK nuevo `estado <> 'pendiente' OR intentos < 3` | 4 | DD-21, DD-28 (a); **[A confirmar]** |
| D4 | Error a mitad de lote → devolver a la cola, best-effort, lo tomado y no procesado, y relanzar | 5 | DD-28 (crash-only, D11 de C-12); **[A confirmar]** |
| D5 | Reloj único inyectado en el worker; `ciclo()` y `procesar(id)` sin `ahora` | 1, 3 | Patrón de reloj inyectado del proyecto |
| D6 | `MockSender` sin estado: solo log; los tests usan `EmisorQueRegistra` | 6 | DD-04, D13 de C-12 |
| D7 | `tomar_vencidos` con un script Lua (un viaje, atómico) | 7 | D7 de C-12 (sorted set) |
| D8 | `api` depende de `redis` con `service_started` en Compose | 8 | 08 (infraestructura) |

### D1. Sin envío para turnos ya iniciados **[A confirmar]**

- En `ProcesarRecordatorio.procesar`, después de bloquear y con este orden: (1) inexistente o no `pendiente` → descartado; (2) turno no `programado` → `marcar_cancelado` (igual que hoy); (3) **nuevo**: `inicio <= reloj()` → `marcar_cancelado`, sin envío y sin re-encolar; (4) envío. El estado se mira antes que la hora, igual que `validar_modificable` (DD-23).
- El `ahora` del chequeo es el reloj leído **con el recordatorio bloqueado**, no el del inicio del ciclo (D5).
- `marcar_cancelado` no toca `intentos`: un reintento descartado queda `cancelado` con 1 o 2 intentos. El CHECK `ck_recordatorio_intentos_segun_estado` no restringe `cancelado`, y D3 tampoco. Así que no hace falta cambiar ninguna restricción (verificado en `008_recordatorio.py`).
- Se registra un `logger.info` con el id del recordatorio y el motivo ("turno ya iniciado"), sin datos del paciente.
- **Opción recomendada**: estado final `cancelado`, sin cambio de esquema para el estado.
- **Alternativa**: un estado nuevo (por ejemplo `vencido`) que distinga "descartado por tardío" de "cancelado porque se canceló el turno". Como este change ya agrega la migración `009`, ampliar `ck_recordatorio_estado_valido` costaría poco. Pero cambia `EstadoRecordatorio`, el requisito "Integridad del recordatorio en la base", la entidad de `04`, la redacción de RN-NO-02 y la futura lectura del estado (pregunta abierta). Se descarta para el MVP porque hoy nadie lee esa diferencia. Si el endpoint de lectura la necesita, se agrega en ese change.
- Alternativa descartada: enviar igual (lo que hace C-12). Un recordatorio de un turno que ya empezó no le sirve al paciente y puede confundirlo.

### D2. Backoff persistido en `programado_para` **[A confirmar]**

- **Nuevo significado**: `programado_para` es el **próximo intento programado**. Al crear el recordatorio vale `inicio - REMINDER_LEAD_HOURS` (sin cambios en `ProgramadorRecordatorios`). Tras un intento fallido que no agota los intentos vale `momento_de_la_falla + espera_reintento(intentos)`.
- `ProcesarRecordatorio`: ante una excepción del emisor lee `momento_falla = self._reloj()` **en ese instante** (hallazgo 3) y calcula `intentos_nuevos = recordatorio.intentos + 1`, con `intentos` leído bajo `FOR UPDATE`, así que es exacto. Si `intentos_nuevos < MAX_INTENTOS`, `proximo = momento_falla + espera_reintento(intentos_nuevos)`; si no, `proximo = None`.
- `RepositorioRecordatorios.registrar_fallo(recordatorio_id, proximo_intento: datetime | None)`: en el mismo `UPDATE ... RETURNING` suma un intento, pasa a `fallido` si llega a `MAX_INTENTOS` y, si `proximo_intento` no es `None`, asigna `programado_para = to_utc(proximo_intento)`. Al llegar a `fallido`, `programado_para` no cambia (spec "Tercer intento fallido").
- Después del commit se encola con el mismo `proximo`. Si ese encolado falla, el próximo vencimiento ya está en la base: `iniciar()` lo recupera con la espera correcta (escenario "El reinicio conserva la espera del reintento").
- `ReencolarPendientes` no cambia: ya encola con `programado_para`. Cambia lo que significa.
- `cancelar_pendiente`, `marcar_enviado` y `marcar_cancelado` no tocan `programado_para`.
- **Opción recomendada**: reusar `programado_para`, sin columna nueva.
- **Alternativas**: (a) columna nueva `proximo_intento_en` (DD-28 la había descartado porque el vencimiento vivía en la cola). Conserva el `programado_para` original como dato histórico, pero agrega una columna, un índice parcial nuevo para el re-encolado y dos fuentes de "cuándo mirar" que pueden divergir. (b) Aceptar el adelanto al reiniciar, que es el statu quo de DD-28 y deja abierta la pregunta.
- Consecuencia: se pierde en la fila el instante originalmente programado para un recordatorio con reintentos. Se puede reconstruir como `turno.inicio - REMINDER_LEAD_HOURS` si la configuración no cambió. Hoy nadie lo lee. Se documenta en `04` (tarea 9.2).

### D3. CHECK `pendiente` con menos de 3 intentos (migración `009`) **[A confirmar]**

- `backend/alembic/versions/009_recordatorio_pendiente_intentos.py`, `revision = "009"`, `down_revision = "008"`:
  - `upgrade`: `op.create_check_constraint(op.f("ck_recordatorio_pendiente_intentos"), "recordatorio", "estado <> 'pendiente' OR intentos < 3")`.
  - `downgrade`: `op.drop_constraint(op.f("ck_recordatorio_pendiente_intentos"), "recordatorio", type_="check")`.
- El modelo `Recordatorio` declara la misma `CheckConstraint`, con la convención de nombres de `base.py`, igual que los CHECKs de `008`, para que `test_modelos_vs_migracion.py` siga sin diferencias.
- **Opción recomendada**: una restricción **nueva y separada**. El `downgrade` es trivial y el nombre del CHECK dice qué hueco cierra.
- **Alternativa**: reemplazar `ck_recordatorio_intentos_segun_estado` por la versión extendida (`... AND (estado <> 'pendiente' OR intentos < 3)`). Queda una sola regla de coherencia, pero el `upgrade` y el `downgrade` tienen que borrar y recrear el CHECK con dos textos distintos.
- Datos existentes: el código nunca deja un `pendiente` con 3 intentos (`registrar_fallo` pasa a `fallido` en el mismo `UPDATE`). Si existiera uno, el `upgrade` falla de forma explícita en lugar de corregir datos en silencio. Es aceptable porque el MVP no está en producción.
- **Numeración**: si otra rama mergea antes a `main` una migración `009`, el que mergea segundo renumera esta (archivo, `revision`, `down_revision`, el `head` de `test_migrations.py` y el nombre de su test de migración) para que `alembic heads` muestre una sola cabeza (regla del equipo).

### D4. Devolución a la cola de lo tomado y no procesado **[A confirmar]**

- `WorkerRecordatorios.ciclo()`:
  ```
  ahora = reloj(); vencidos = cola.tomar_vencidos(ahora, limite)
  for i, id in enumerate(vencidos):
      try: procesador.procesar(id)
      except Exception:
          self._devolver(vencidos[i + 1:], ahora)   # best-effort
          raise                                     # crash-only, sin cambios
  ```
- `_devolver` encola cada id con vencimiento `ahora` (el momento en que se tomaron: todos vencían a esa hora o antes, así que siguen vencidos y salen primero al reiniciar). Si una devolución falla, deja de intentar, registra un `logger.warning` con la cantidad no devuelta y el tipo de error (sin ids de pacientes ni contenido) y **no** reemplaza la excepción original.
- El recordatorio en el que ocurrió el error **no** se devuelve. Si el error fue de la base, la transacción se revirtió y sigue `pendiente`. Si fue el encolado del reintento, la base ya tiene su próximo intento (D2). En los dos casos `iniciar()` lo recupera con el vencimiento correcto. Devolverlo con `ahora` adelantaría su reintento.
- No se cambia el puerto `ColaRecordatorios`: `tomar_vencidos` sigue devolviendo solo ids. Por eso el vencimiento devuelto es `ahora` y no el original. Al reiniciar, `iniciar()` lo pisa con `programado_para` de la base (`ZADD` reemplaza el score), así que la diferencia dura como mucho hasta el reinicio.
- D4 complementa a `iniciar()`, que con D2 ya recupera todo lo `pendiente` con su vencimiento correcto. Su valor es que lo no procesado no desaparece de Redis en un entorno sin reinicio automático, y que vuelve a estar disponible enseguida si el error fue transitorio.
- **Opción recomendada**: devolver best-effort y relanzar.
- **Alternativas**: (a) no devolver nada y depender solo del re-encolado al reiniciar. Es más simple y, con D2 y `restart: unless-stopped`, no pierde recordatorios. (b) `tomar_vencidos` devuelve `(id, vence)` para devolver con el vencimiento original. Cambia el contrato del puerto y de la suite de contrato por una diferencia que `iniciar()` ya corrige. (c) Atrapar el error por elemento y seguir con el lote. Se descarta porque rompe el diseño crash-only de DD-28 (un error de la base se repetiría en cada elemento).

### D5. Reloj único en el worker

- `ProcesarRecordatorio(sesiones, cola, sender, consultorio, zona, reloj)` y `WorkerRecordatorios(cola, procesador, reencolar, reloj, limite=...)`. `procesar(recordatorio_id)` y `ciclo()` ya no reciben `ahora`: el ciclo lee `reloj()` para tomar los vencidos, el procesador lo lee con el recordatorio bloqueado (D1) y otra vez al fallar el envío (D2).
- `app/worker.py`: `construir_worker(config, reloj=lambda: datetime.now(UTC))` pasa el reloj a ambos, y `correr(worker, *, detenido, pausa_s, max_ciclos)` llama `worker.ciclo()`. El protocolo `_Ciclable` y los dobles de `tests/unit/test_worker.py` se ajustan.
- Tests: `tests/fakes.py` agrega `RelojManual` (`ahora`, `ajustar(instante)`, `avanzar(delta)`, invocable). `armar_worker` recibe el reloj. Las 29 llamadas `ciclo(T)` pasan a `reloj.ajustar(T); worker.ciclo()`, con un helper `ciclo_a(worker, reloj, T)` para que el cambio sea mecánico. El escenario "La espera se cuenta desde el momento de la falla" usa un emisor de test que avanza el `RelojManual` 40 s antes de fallar con R2.
- Alternativa descartada: conservar `ciclo(ahora)` e inyectar además un reloj solo para el momento de la falla. Serían dos fuentes de tiempo en el mismo proceso, y el chequeo de D1 quedaría con el `ahora` del inicio del ciclo.

### D6. `MockSender` sin estado

- `MockSender.enviar` solo emite el `logger.info` actual (id del recordatorio y texto, sin `paciente_id`). Se elimina `enviados`.
- `tests/fakes.py`: `EmisorQueRegistra` (lista `enviados` e `invocaciones`). `EmisorQueFalla(fallas=n)` pasa a extenderlo. Los tests que hoy inspeccionan `MockSender().enviados` (procesar, descartes, re-encolado y concurrencia, donde `SenderQueEsperaAlOtro` hereda hoy de `MockSender`) usan `EmisorQueRegistra`.
- Escenario "Envíos repetidos no acumulan estado en el adaptador mock": se compara `vars(sender)` antes y después de 1000 envíos (igualdad, no solo el tipo). Escenario "El adaptador mock registra el envío": `caplog` muestra un registro `INFO` con el id del recordatorio y el texto. Que no guarde el mensaje en memoria lo cubre la igualdad de `vars` del escenario anterior.
- Alternativas descartadas: un `deque(maxlen=n)` (sigue siendo estado que nadie de producción lee) o vaciar la lista periódicamente (agrega lógica a un mock).

### D7. `tomar_vencidos` en un solo viaje (script Lua)

- `ColaRedis.__init__` registra el script con `cliente.register_script(...)`, que no hace ningún viaje al construirse:
  ```lua
  local ids = redis.call('ZRANGEBYSCORE', KEYS[1], '-inf', ARGV[1], 'LIMIT', 0, ARGV[2])
  if #ids > 0 then redis.call('ZREM', KEYS[1], unpack(ids)) end
  return ids
  ```
  `tomar_vencidos` lo invoca una vez (`EVALSHA`, con caída automática a `EVAL` de redis-py). Redis ejecuta el script de forma atómica, así que cada id se entrega a un solo consumidor sin depender del valor de retorno de `ZREM`. El orden es el del score. `limite` es como mucho 100, lejos del límite de `unpack`.
- **Verificación**: la suite de contrato (`test_contrato_cola_recordatorios.py`), sin cambios en sus aserciones, más el escenario nuevo "Consumidores simultáneos no comparten elementos" (dos hilos con una barrera sobre 50 vencidos). Corre contra `ColaRedis` y contra `ColaEnMemoria`, que suma un `threading.Lock` para cumplir el mismo contrato. **No** se agrega un test que cuente viajes a Redis: tendría que espiar internos de redis-py (`execute_command`, pipelines) y quedaría acoplado a la implementación. "Un viaje" queda como nota de implementación verificable leyendo el código.
- Alternativas descartadas: `MULTI`/`EXEC` (dentro de la transacción no se puede usar el resultado de `ZRANGEBYSCORE` para el `ZREM`; con `WATCH` hay reintentos bajo contención); `ZREMRANGEBYSCORE` (no tiene `LIMIT`, así que borraría vencidos que no se devuelven); `ZPOPMIN` (saca también los no vencidos y obliga a devolverlos).

### D8. La API depende de Redis en Compose

- `api.depends_on` suma `redis: {condition: service_started}`, sin cambiar `db: {condition: service_healthy}`. `tests/unit/test_docker_compose.py` suma el escenario "La API espera a Redis".
- La API sigue respondiendo si Redis cae después de arrancar (spec "Cola no disponible al crear"). `depends_on` solo ordena el arranque.
- Alternativa descartada: un `healthcheck` de Redis con `service_healthy`. El `worker` usa `service_started` y el encolado ya es best-effort. Agregar un healthcheck es un cambio de infraestructura que ningún hallazgo pide.

## Risks / Trade-offs

- [D1 con el estado `cancelado` mezcla dos motivos: turno cancelado y turno ya iniciado] → Hoy nadie lee la diferencia. El log de D1 la deja trazable. Si la lectura del estado (pregunta abierta) la necesita, se agrega un estado con una migración en ese change.
- [D2 cambia el significado de una columna existente] → Queda escrito en `04` §Recordatorio, en DD-29 y en el requisito "Re-encolado de pendientes al iniciar el worker". `ProgramadorRecordatorios` y la cancelación no cambian. Los escenarios existentes sobre `programado_para` al crear, cancelar y reprogramar siguen valiendo.
- [D5 cambia firmas usadas por 29 llamadas en los tests] → Refactor mecánico en una tarea propia, con la suite en verde antes y después (tarea 2.1), antes de cualquier cambio de comportamiento.
- [D4 devuelve con vencimiento `ahora`, no con el original] → Todos ya estaban vencidos. `iniciar()` restituye el vencimiento de la base al reiniciar.
- [Migración `009` en conflicto con otra rama] → Renumerar según D3. El test de `head` falla si hay dos cabezas.
- [El script Lua depende de que Redis permita scripting (no lo deshabilita la imagen `redis:7`)] → La suite de contrato corre contra `redis:7` real (`TEST_REDIS_URL`), así que una configuración que lo bloquee falla en los tests y no en producción.
- [La garantía sigue siendo "al menos una vez"] → Sin cambios respecto de DD-28.

## Migration Plan

1. Detener el `worker` (opcional: con el código nuevo, un `pendiente` con reintentos se reprograma bien al iniciar).
2. `alembic upgrade head` aplica `009` (solo el CHECK; sin cambios de datos).
3. Desplegar `api` y `worker` con el código nuevo. Al iniciar, el worker re-encola los pendientes con su `programado_para`.
4. Rollback: `alembic downgrade 008` borra el CHECK y se vuelve al código de C-12. Los `programado_para` ya actualizados por D2 son instantes válidos, y el código anterior los trata como vencimientos normales: a lo sumo un reintento se adelanta, como pasaba antes.

## Open Questions

Ninguna que cambie los specs, el enfoque o las tareas. Las decisiones D1..D4 esperan la aprobación del usuario (governance ALTO). Si alguna se aprueba con su alternativa, se ajustan el spec y las tareas con `/opsx:update` antes del Apply.
