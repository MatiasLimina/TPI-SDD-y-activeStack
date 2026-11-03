# Design

## Context

Ver `proposal.md` (Why, Non-goals) y los delta specs `recordatorios` y `app-configuration`. Estado actual del código relevante (C-01..C-07 archivados):

- **Casos de uso** (`backend/app/application/`): `CrearTurno`, `ReprogramarTurno` y `CancelarTurno` aceptan `observadores` que corren **dentro de la transacción, antes del commit**. Si uno lanza, el caso de uso hace `rollback()` y relanza. Firmas: `ObservadorTurno = Callable[[TurnoCreado], None]`, y `ObservadorReprogramacion` y `ObservadorCancelacion = Callable[[TurnoRegistrado, TurnoRegistrado], None]` (anterior, nuevo; C-07 unificó la de cancelación). `ReprogramarTurno` y `CancelarTurno` leen el turno con `obtener_para_actualizar` (`SELECT ... FOR UPDATE`).
- **API** (`backend/app/api/turnos.py`): las fábricas `get_crear_turno`, `get_cancelar_turno` y `get_reprogramar_turno` arman el caso de uso con `get_session`, `get_reloj` (sobreescrito en tests con un reloj fijo) y `RecepcionistaAutenticada`, y registran `AuditorTurnos` como observador (C-07). Las rutas son `def` sincrónicas (corren en el threadpool).
- **Configuración** (`backend/app/config.py`): `Settings` con `DATABASE_URL` y `JWT_SECRET` obligatorias, `NOTIFICATION_ADAPTER: str = "mock"` sin validar y `REDIS_URL` con valor por defecto. `get_engine()` (`session.py`) construye el engine desde `get_settings()`, así que cualquier proceso que lo use necesita `JWT_SECRET`. `tests/unit/test_env_example.py` exige que cada campo de `Settings` figure en `.env.example`. No se pudo leer `.env.example` al proponer (permiso denegado): el Apply lo inspecciona antes de editarlo.
- **Infraestructura**: `docker-compose.yml` tiene `db`, `redis` (`redis:7`, sin persistencia configurada) y `api`. No hay servicio `worker` y `redis` (redis-py) no está en `pyproject.toml`. La imagen (`backend/Dockerfile`) instala el paquete `app` y no las migraciones.
- **Modelo**: `CatalogoMixin` (`id uuid` con `gen_random_uuid()`, `creado_en`, `actualizado_en`) y la convención de nombres de `base.py`. Migraciones lineales `001..007` numeradas a mano (DD-17). `turno` no se borra nunca (DD-08).
- **Tests**: `db_session` corre dentro de una transacción externa que siempre se revierte (`join_transaction_mode="create_savepoint"`). Los fixtures de concurrencia (`motor_concurrente`, `catalogo_commiteado`) commitean de verdad y limpian con `DELETE FROM turno`, y arman los casos de uso **sin observadores**. `test_migrations.py` afirma `head == "008"`.

## Goals / Non-Goals

**Goals:**
- Recordatorio enchufado por los mismos puntos de extensión que la auditoría, sin tocar la validación ni los contratos HTTP de los casos de uso.
- La base es la única fuente de verdad del estado del recordatorio. Redis solo dice cuándo mirar, y perderlo no pierde recordatorios.
- Worker determinístico y testeable: reloj inyectado, cola y emisor detrás de puertos, un ciclo de procesamiento invocable desde los tests sin bucles infinitos.
- Sin envío doble en condiciones normales y sin envío para turnos cancelados, verificado en la base bajo bloqueo.
- Suite existente en verde durante todo el change.

**Non-Goals:**
- Entrega "exactamente una vez" ante una caída del worker entre el envío y el commit (ver Risks: la garantía es "al menos una vez").
- Reconciliación periódica mientras el worker corre: el re-encolado ocurre al iniciar (scope de `CHANGES.md`); ver Risks.
- Endpoint de lectura de recordatorios, auditoría de recordatorios y salud de Redis/worker (ver `proposal.md`).

## Decisions

Las decisiones marcadas **[A confirmar]** no las fija la KB. Se proponen acá y, cuando el usuario las aprueba, se registran como **DD-28** en `knowledge-base/09_decisiones_y_supuestos.md` (tarea 11.1), junto con D16, que no es una regla de dominio sino la validación de las variables nuevas con el criterio de DD-24 (f), y se registra para que la cita del spec `app-configuration` tenga fuente. Governance ALTO: no se implementa nada antes de esa aprobación.

| Id | Decisión | Fuente |
|---|---|---|
| D1 | Capability nueva `recordatorios`; `agenda-turnos` no cambia | Criterio de C-07 (el efecto lateral se especifica aparte) |
| D2 | Tabla `recordatorio` con CHECKs de estado, canal, intentos y coherencia, más índice único parcial "un `pendiente` por turno" | 04 §Recordatorio, DD-21 (varchar + CHECK); unicidad y coherencia **[A confirmar]** |
| D3 | Se programa sii `inicio - REMINDER_LEAD_HOURS >= ahora` (24 h exactas sí programan); `ahora` = reloj inyectado | RN-NO-03, DD-13 ("menos de 24 h" no programa) |
| D4 | Programador como observador armado por request, en la misma transacción | Puntos de extensión de C-03; 08 (unidad de trabajo turno + auditoría + recordatorio) |
| D5 | Reprogramar: si cambia `inicio`, cancela el `pendiente` y crea uno nuevo si corresponde; si `inicio` no cambia, no toca nada. Consecuencia explícita: si el recordatorio anterior ya estaba `enviado` (o `fallido`), el turno reprogramado recibe un **segundo** recordatorio, para la fecha nueva | RN-NO-02; RN-NO-01 ("todo turno activo genera un recordatorio previo"); la forma (fila nueva vs. editar) **[A confirmar]** |
| D6 | Encolado **después** del commit y best-effort; la base es la fuente de verdad; cancelar no toca Redis | Flujo 6 (errores, Suposición de la KB); **[A confirmar]** |
| D7 | Cola = sorted set de Redis (miembro = id, score = vencimiento en epoch UTC), detrás del puerto `ColaRecordatorios` | 08 (cola de trabajo Redis + worker) |
| D8 | Worker: bloqueo `turno FOR SHARE` → `recordatorio FOR UPDATE`, re-verificación de estados, envío y actualización en una transacción | Flujo 6 ("verifica que el turno siga activo") |
| D9 | Backoff: 1 min antes del 2.º intento y 2 min antes del 3.º (base 1 min, factor 2), constante en código | DD-19 (exponencial); valores **[A confirmar]** |
| D10 | "3 intentos" = 3 intentos en total (el 1.º más 2 reintentos) | DD-19, 04 ("máximo 3"); la redacción de RN-NO-05 ("se reintenta hasta 3 veces") y la de US-012 ("se reintenta 3 veces") se alinean **[A confirmar]** |
| D11 | Re-encolado al iniciar; un error inesperado termina el proceso y Compose lo reinicia (crash-only) | `CHANGES.md` §C-12, Flujo 6 |
| D12 | Contenido: texto fijo con fecha `dd/mm/aaaa`, hora `HH:MM` en `APP_TIMEZONE` y `CONSULTORIO_NOMBRE`; destinatario = `paciente_id` | RN-NO-04; `CONSULTORIO_NOMBRE` y el texto **[A confirmar]** |
| D13 | `MockSender` registra en memoria y en el log; `NOTIFICATION_ADAPTER` acepta solo `mock` | `CHANGES.md` §C-12, DD-04 |
| D14 | Configuración del worker separada (`ConfiguracionWorker`), sin `JWT_SECRET`; `Settings` la extiende | Mínimo privilegio (08 §Seguridad) **[A confirmar]** |
| D15 | Redis real solo para el contrato del adaptador (`TEST_REDIS_URL`); el resto de los tests usa la cola en memoria, que pasa el mismo contrato | Reglas duras (PostgreSQL real para persistencia; Redis no es la base) |
| D16 | Validación de las variables nuevas: `REMINDER_LEAD_HOURS` entero mayor que cero (`0`, un negativo o un valor no numérico son inválidos y la aplicación no arranca) y `CONSULTORIO_NOMBRE` no vacío ni formado solo por espacios | Mismo criterio que DD-24 (f) para `JWT_EXPIRE_MINUTES`; RN-CU-03. Se registra en DD-28 junto con las decisiones aprobadas |

### 1. Capas y módulos
- `app/domain/recordatorios.py` (puro): `EstadoRecordatorio` (`StrEnum`: `pendiente`, `enviado`, `fallido`, `cancelado`), `MAX_INTENTOS = 3`, `calcular_programacion(inicio, ahora, anticipacion) -> datetime | None` (D3, en UTC), `espera_reintento(intentos_hechos: int) -> timedelta` (D9) y el puerto `ColaRecordatorios(Protocol)`: `encolar(recordatorio_id: UUID, vence: datetime) -> None` y `tomar_vencidos(ahora: datetime, limite: int) -> list[UUID]`.
- `app/domain/notificaciones.py` (puro): `MensajeRecordatorio` (dataclass congelada: `recordatorio_id`, `paciente_id`, `texto`), `armar_mensaje(recordatorio_id, paciente_id, inicio, consultorio, zona) -> MensajeRecordatorio` (D12) y el puerto `NotificationSender(Protocol)` con `enviar(mensaje: MensajeRecordatorio) -> None`, que lanza una excepción si el envío falla.
- `app/infrastructure/db/models/recordatorio.py` y `app/infrastructure/db/repositorio_recordatorios.py`: `crear_pendiente`, `cancelar_pendiente(turno_id)`, `bloquear_para_envio(recordatorio_id)`, `marcar_enviado`, `registrar_fallo`, `marcar_cancelado` y `listar_pendientes`. Ninguno hace `commit` salvo los métodos de transacción explícitos (`commit`/`rollback`) que usa el procesador del worker. Dentro de un caso de uso de turnos, la transacción es del caso de uso.
- `app/application/recordatorios.py`: `ProgramadorRecordatorios` (observador, D4–D6), `ProcesarRecordatorio` (un recordatorio vencido, D8–D10), `ReencolarPendientes` (D11) y `WorkerRecordatorios` (`iniciar()` re-encola; `ciclo(ahora) -> int` toma los vencidos y los procesa).
- `app/infrastructure/queue/cola_redis.py`: `ColaRedis(cliente, clave="recordatorios:programados")` (D7).
- `app/infrastructure/notifications/mock_sender.py`: `MockSender` y `crear_sender(adaptador) -> NotificationSender` (D13).
- `app/worker.py`: `python -m app.worker` arma la configuración, el engine propio, la cola, el emisor y el reloj del sistema; llama `iniciar()` y después repite `ciclo()` con una pausa de 5 s cuando no hay vencidos, hasta recibir `SIGTERM`/`SIGINT`.

### 2. Modelo y migración `008_recordatorio.py` (D2)
```
recordatorio
  id               uuid        PK  DEFAULT gen_random_uuid()       (CatalogoMixin)
  turno_id         uuid        NOT NULL  FK turno(id) ON DELETE RESTRICT
  programado_para  timestamptz NOT NULL
  estado           varchar(20) NOT NULL  DEFAULT 'pendiente'
                   CHECK (estado IN ('pendiente','enviado','fallido','cancelado'))
  canal            varchar(20) NOT NULL  CHECK (canal IN ('mock'))
  intentos         integer     NOT NULL  DEFAULT 0  CHECK (intentos BETWEEN 0 AND 3)
  creado_en, actualizado_en  timestamptz  DEFAULT now()            (CatalogoMixin)
  CHECK ((estado <> 'fallido' OR intentos = 3) AND (estado <> 'enviado' OR intentos >= 1))
                                                -- ck_recordatorio_intentos_segun_estado
  UNIQUE INDEX ux_recordatorio_turno_pendiente ON (turno_id) WHERE estado = 'pendiente'
  INDEX ix_recordatorio_turno_id (turno_id)                        -- índice de FK
  INDEX ix_recordatorio_pendiente_programado_para (programado_para) WHERE estado = 'pendiente'
```
- `estado` y `canal` como `varchar` + CHECK, mismo criterio que `turno.estado` (DD-21). `canal` existe para el adaptador futuro: agregarlo requiere una migración que amplíe el CHECK, lo cual es deliberado.
- El índice único parcial es la garantía de RN-NO-02 ante errores de programación o carreras: dos programaciones del mismo turno se serializan igual por el `FOR UPDATE` del turno en reprogramar y cancelar, y en el alta el turno es nuevo.
- `programado_para` no tiene `DEFAULT`: siempre lo calcula la aplicación con el reloj inyectado. `creado_en`/`actualizado_en` usan `now()` como el resto del catálogo, porque son metadatos y no reglas.
- **Numeración**: `revision = "008"`, `down_revision = "007"`. Se propuso como `006` (sobre `005`); al integrar `main` con C-08 (`006`) y C-10 (`007`) se renumeró a `008`, junto con el `head` de `test_migrations.py` y el nombre de su test, y `alembic heads` muestra una sola cabeza.
- Alternativas descartadas: `enum` nativo (migraciones más costosas, DD-21); sin coherencia `estado`/`intentos` (un `fallido` con 1 intento sería un dato imposible que nadie detecta); columna `proximo_intento_en` (ver D11: el vencimiento del reintento vive en la cola y se aproxima al reiniciar).

### 3. Programación en los casos de uso (D3, D4, D5)
- `ProgramadorRecordatorios(repositorio, reloj, anticipacion: timedelta, canal="mock")` expone `al_crear(creado)`, `al_reprogramar(anterior, nuevo)` y `al_cancelar(anterior, nuevo)`, que se pasan como observadores **después** del auditor (`observadores=[auditor.al_crear, programador.al_crear]`). Comparte la `session` del request: el recordatorio vive en la transacción del turno y de su auditoría.
- `al_crear`: si `calcular_programacion(creado.inicio, ahora, anticipacion)` devuelve un instante, `crear_pendiente` (`add` + `flush`, para que una violación salte antes del commit) y lo anota para publicar.
- `al_cancelar`: `cancelar_pendiente(turno_id)` = `UPDATE recordatorio SET estado='cancelado' WHERE turno_id=:t AND estado='pendiente'`. Nada que publicar: el worker descarta el id al verlo `cancelado` (D6).
- `al_reprogramar`: si `anterior.inicio == nuevo.inicio`, no hace nada (D5). Si no, `cancelar_pendiente` y después la misma regla que el alta con `nuevo.inicio`. Se crea una fila nueva en lugar de editar la existente porque un recordatorio `enviado` o `fallido` es terminal, y así hay un solo camino para todos los casos (con o sin pendiente previo, ya enviado). El historial queda en las filas `cancelado`.
- Consecuencia de D5, a aprobar a conciencia: un turno cuyo recordatorio ya está `enviado` (o quedó `fallido`) y se reprograma con la anticipación suficiente recibe un **segundo** recordatorio, para la fecha nueva; el anterior queda intacto. Se apoya en RN-NO-01 (todo turno activo genera un recordatorio previo) y DD-28 lo dice explícitamente (tarea 11.1).
- El cálculo de D3 usa el mismo `ahora` del reloj inyectado que la validación del turno, así que es determinístico en los tests.
- Alternativas descartadas: editar `programado_para` del pendiente existente (no cubre el caso "ya enviado" y obliga a dos caminos); recalcular también cuando `inicio` no cambia (crea filas `cancelado` sin motivo y re-encola sin necesidad); programar desde un trigger de la base (la regla de 24 h y el reloj inyectado quedarían fuera del dominio).

### 4. Encolado post-commit (D6)
- El programador acumula `(recordatorio_id, programado_para)` de los pendientes que creó. La ruta llama `programador.publicar(cola)` **después** de que `caso.ejecutar(...)` volvió, es decir, con el commit ya hecho. Si `ejecutar` lanza, no se llega a publicar.
- Para eso las fábricas exponen el programador: `get_programador` (dependencia por request, cacheada por FastAPI) se inyecta en la fábrica del caso de uso y en la ruta, que lo recibe como parámetro. La cola llega por la dependencia `get_cola_recordatorios`, que los tests sobreescriben con la cola en memoria.
- `publicar` atrapa cualquier excepción de la cola, la registra con `logger.warning` (con el id del recordatorio y sin datos del paciente) y no la propaga: el turno ya está confirmado y el recordatorio sigue `pendiente` en la base, que el worker re-encola al iniciar (D11).
- Alternativas descartadas: encolar dentro del observador, antes del commit (si después la transacción se revierte, queda en Redis un id que no existe; si Redis falla, el alta falla sin necesidad); el evento `after_commit` de SQLAlchemy (con `join_transaction_mode="create_savepoint"` de los tests no se dispara igual que en producción, y es implícito); outbox con polling de la base sin Redis (el scope exige cola Redis).

### 5. Cola Redis (D7)
- `encolar` = `ZADD clave {id: vence_epoch}`: idempotente por miembro y reemplaza el score, lo que cumple "re-encolar reemplaza el vencimiento" sin duplicar.
- `tomar_vencidos(ahora, limite)` = `ZRANGEBYSCORE clave -inf ahora_epoch LIMIT 0 limite` y, por cada id, `ZREM`. Solo se devuelve el id si `ZREM` devolvió `1`. Así, aun con varios workers, cada elemento se entrega a un solo consumidor, sin Lua ni `WATCH`. El orden es el del score.
- Cliente `redis.Redis.from_url(REDIS_URL, decode_responses=True, socket_connect_timeout=2, socket_timeout=2)`: los timeouts acotan la espera de `publicar` en la API cuando Redis está caído.
- La clave es un parámetro del constructor: los tests de contrato usan una clave única por test sobre la base `TEST_REDIS_URL` y la borran al final.
- Alternativas descartadas: `LIST` + `BRPOP` (no tiene vencimiento: habría que encolar recién a las T-24 h, con un scheduler más); Redis Streams con grupos de consumidores (más robusto para entregas pendientes, pero agrega estado de grupo y ACK que el MVP no necesita, porque la base ya es la fuente de verdad); RQ/Celery (otra dependencia y otro modelo de reintentos que se superpone con DD-19).

### 6. Procesamiento de un recordatorio vencido (D8, D9, D10)
`ProcesarRecordatorio.procesar(recordatorio_id, ahora)`, en una transacción:
1. Lee `turno_id` del recordatorio. Si no existe → `descartado`.
2. `SELECT turno ... FOR SHARE` y después `SELECT recordatorio ... FOR UPDATE`. Es el mismo orden (turno → recordatorio) que cancelar y reprogramar, que bloquean el turno `FOR UPDATE` y después actualizan el recordatorio: no hay ciclo de espera ni deadlock. Mientras el worker envía, una cancelación del mismo turno espera a que termine.
3. Si el recordatorio no está `pendiente` → `descartado` (commit sin cambios). Si el turno no está `programado` → `marcar_cancelado` → `cancelado`, sin envío.
4. `armar_mensaje(...)` con `paciente_id` e `inicio` del turno, `CONSULTORIO_NOMBRE` y `APP_TIMEZONE`, y `sender.enviar(mensaje)`.
5. Éxito → `marcar_enviado` (`estado='enviado'`, `intentos+1`) → `enviado`. Excepción del emisor → `registrar_fallo` (`intentos+1`; si llega a 3, `estado='fallido'`) → `fallido`, o bien `reintento` con vencimiento `ahora + espera_reintento(intentos)`.
6. Commit. Después del commit, si el resultado es `reintento`, `cola.encolar(id, vence)`.
- Solo se tratan como intento fallido las excepciones del emisor. Un error de base o de Redis se propaga: el ciclo no lo atrapa, el proceso termina con código distinto de 0 y Compose lo reinicia (`restart: unless-stopped`). Al reiniciar, D11 recupera los pendientes (diseño crash-only, sin estados intermedios que manejar).
- **Backoff (D9)**: `espera_reintento(1) = 1 min` y `espera_reintento(2) = 2 min`. Con 24 h de anticipación, los tres intentos terminan en ~3 min. Es una constante de dominio, no una variable de entorno: la KB no pide configurarla y los tests la verifican con el reloj fijo.
- **Tres intentos en total (D10)**: DD-19 dice "3 intentos" y 04 dice "máximo 3". La frase de RN-NO-05 "se reintenta hasta 3 veces" admite leer 1 + 3. US-012 ("el envío fallido se reintenta 3 veces") tiene la misma ambigüedad. Se toma la lectura de DD-19, consistente con el CHECK `intentos BETWEEN 0 AND 3`, y se alinea la redacción de RN-NO-05 y del criterio de US-012 en la KB.
- Alternativas descartadas: verificar sin bloqueo (una cancelación concurrente podría confirmarse entre la lectura y el envío sin que nadie lo note); bloquear solo el recordatorio (el turno podría cancelarse mientras se envía); reintentar dentro del mismo ciclo con `sleep` (bloquea al worker y no sobrevive a un reinicio).

### 7. Re-encolado al iniciar (D11)
- `ReencolarPendientes.ejecutar()` = `listar_pendientes()` (usa el índice parcial) y `cola.encolar(id, programado_para)` por cada uno. Es idempotente por `ZADD`.
- Un pendiente con `intentos > 0` se re-encola con su `programado_para`, que ya pasó, así que se reintenta enseguida en lugar de esperar el resto de su backoff. Es una aproximación aceptada: pasa solo al reiniciar y nunca supera los 3 intentos, porque el contador vive en la base.

### 8. Contenido del mensaje (D12)
- Texto fijo: `Recordatorio: tiene un turno el {dd/mm/aaaa} a las {HH:MM} en {CONSULTORIO_NOMBRE}.`, con fecha y hora de `to_local(inicio, APP_TIMEZONE)`.
- `MensajeRecordatorio` no tiene campos para prestación, profesional ni datos personales: RN-NO-04 queda garantizada por construcción (el tipo no permite cargarlos), no solo por un test.
- Destinatario: el `paciente_id`. Un adaptador real (fuera de alcance) resolvería el contacto del paciente por ese id dentro de su propio límite.
- `CONSULTORIO_NOMBRE` **[A confirmar]**: RN-NO-04 exige "consultorio" en el contenido, pero la KB no tiene ninguna entidad ni variable con ese dato. El sistema es monotenant (SU-07), así que una variable de entorno por despliegue es la fuente natural. El valor por defecto es `Consultorio odontológico`, para no romper entornos existentes.

### 9. Adaptador mock y configuración (D13, D14)
- `MockSender.enviar` agrega el mensaje a `self.enviados` y emite un `logger.info` "recordatorio enviado (mock)" con `recordatorio_id`, `paciente_id` y el texto, que no tiene datos clínicos. No hace I/O de red. `crear_sender("mock")` devuelve un `MockSender`.
- `ConfiguracionWorker(BaseSettings)`: `DATABASE_URL`, `REDIS_URL`, `APP_TIMEZONE`, `NOTIFICATION_ADAPTER: Literal["mock"]`, `REMINDER_LEAD_HOURS: int = Field(24, gt=0)` y `CONSULTORIO_NOMBRE` (validador: `strip()` no vacío), según D16. `Settings(ConfiguracionWorker)` agrega `JWT_SECRET`, `JWT_EXPIRE_MINUTES` y `CORS_ORIGINS`. La API sigue usando `Settings`; el worker usa `ConfiguracionWorker` y construye su propio engine (`create_engine(DATABASE_URL, pool_pre_ping=True, hide_parameters=True)`), porque `get_engine()` carga `Settings` y exigiría `JWT_SECRET`.
- Alternativa descartada: pasar `JWT_SECRET` al worker para reutilizar `Settings` (expone un secreto a un proceso que no lo usa).

### 10. Estrategia de tests (D15)
- **PostgreSQL real** para toda persistencia (regla dura): migración, restricciones, repositorio, programador, procesador y re-encolado.
- **Cola**: una suite de contrato parametrizada (`tests/integration/test_contrato_cola_recordatorios.py`) corre contra `ColaRedis` sobre Redis real (`TEST_REDIS_URL`, base 15, clave única por test) y contra `ColaEnMemoria` (`tests/fakes.py`). Así el fake que usan los demás tests queda verificado contra el comportamiento real. Sin `TEST_REDIS_URL`, la suite falla con un mensaje que indica cómo levantar Redis, igual que la base. Para "cola no disponible" se usa `ColaQueFalla`, que lanza `redis.exceptions.ConnectionError`.
- **Emisor**: `MockSender` real en los tests del camino feliz. Para las fallas, `EmisorQueFalla(fallas=n)`, un doble del puerto en el límite externo (permitido por `python-testing-patterns`).
- **Reloj**: fijo en todos los tests. El worker recibe `ahora` explícito en `ciclo(ahora)`.
- **API**: la fixture `client` sobreescribe `get_cola_recordatorios` con una `ColaEnMemoria` expuesta como fixture `cola`. Así los tests de C-03..C-07 no dependen de Redis y los nuevos pueden inspeccionar lo encolado.
- **Concurrencia**: un test con `motor_concurrente` ejecuta dos `ProcesarRecordatorio.procesar` simultáneos sobre el mismo recordatorio commiteado y verifica un único envío. La limpieza de `catalogo_commiteado` pasa a borrar primero los recordatorios de sus turnos (la FK `RESTRICT` impediría borrar los turnos; `recordatorio` no es append-only).
- **Compose**: `tests/unit/test_docker_compose.py` parsea `docker-compose.yml` con PyYAML (dependencia `dev`).

## Risks / Trade-offs

- [Entrega "al menos una vez": si el worker cae después de `enviar` y antes del commit, al reiniciar el recordatorio sigue `pendiente` y se envía de nuevo] → Ventana mínima con el mock. Un adaptador real debería aceptar una clave de idempotencia (el `recordatorio_id`); queda anotado en el docstring del puerto.
- [El envío ocurre con el turno bloqueado `FOR SHARE`: un adaptador real lento haría esperar a una cancelación o reprogramación de ese turno] → Con el mock es instantáneo. Para un adaptador real, timeout del emisor y, si hiciera falta, separar el envío de la transacción (fuera de alcance).
- [Redis pierde datos (reinicio sin persistencia) mientras el worker sigue vivo: los pendientes no se re-encolan hasta el próximo reinicio del worker] → El cliente pierde la conexión y el `ciclo` falla, así que el proceso termina y Compose lo reinicia, lo que dispara el re-encolado. Si Redis vuelve antes de que el worker lo note, el hueco persiste. Mitigación posible fuera de alcance: `--appendonly yes` en Redis o una reconciliación periódica.
- [Redis caído durante un alta: `publicar` espera hasta `socket_connect_timeout` (2 s) antes de responder] → Latencia acotada y solo con Redis caído. El turno se confirma igual (spec "Cola no disponible al crear").
- [La programación es opcional a nivel de caso de uso, igual que la auditoría: un caso de uso armado sin el programador no programa] → Las tres fábricas de la API, único punto de entrada, lo registran siempre, y los tests de API lo verifican. Queda anotado en el docstring de los observadores.
- [Re-encolar al reiniciar ignora el backoff restante de un pendiente con intentos] → Ver D11. El tope de 3 intentos se mantiene porque vive en la base.
- [Conflicto de numeración con C-08 y C-10] → Se resolvió renumerando a `008` (regla del equipo). El test de `head` falla si hay dos cabezas.
- [El texto y la variable `CONSULTORIO_NOMBRE` pueden no coincidir con lo que el usuario espera] → Marcados **[A confirmar]**. Si cambian, se ajustan el spec y las tareas con `/opsx:update` antes del Apply.

## Migration Plan

1. `alembic upgrade head` aplica `008` (tabla vacía). **Sin backfill**: los turnos que ya existen no reciben recordatorio. Es coherente con el alcance (el MVP todavía no está en producción), y si hiciera falta sería un script aparte.
2. Se agregan `REMINDER_LEAD_HOURS`, `NOTIFICATION_ADAPTER` y `CONSULTORIO_NOMBRE` al entorno (todas tienen valor por defecto, así que un `.env` viejo sigue funcionando) y `TEST_REDIS_URL` para correr los tests.
3. `docker compose up -d worker` levanta el worker, que re-encola los pendientes al iniciar.
4. Rollback: detener `worker` y `alembic downgrade 007` (borra la tabla y los índices). Se pierde el historial de recordatorios. Las claves de Redis huérfanas se borran con `DEL recordatorios:programados`.

## Open Questions

Ninguna de estas preguntas cambia los specs, el enfoque ni las tareas de este change. Se registran para decidir en otro change si hace falta:

1. **Lectura del estado de los recordatorios**: la matriz de `03_actores_y_roles.md` da `R` a la recepcionista y `R propios` al odontólogo sobre "Recordatorios (estado)", pero ningún change de `CHANGES.md` incluye ese endpoint (C-12 no lo lista y C-13 solo consulta turnos). ¿Se agrega a C-13, a un change nuevo o al backlog?
2. **Recordatorio procesado después del inicio del turno** (por ejemplo, con Redis y el worker caídos durante más de 24 h): la KB solo pide verificar que el turno "siga activo" (`programado`), así que este change lo envía igual. ¿Debería descartarse (y con qué estado) si el turno ya empezó? Hoy no existe un estado para eso y agregarlo sería una regla nueva.
