# Tasks

> Governance ALTO: el usuario aprobó el 2026-11-04 las decisiones D1, D2, D3 y D4 de `design.md`, las cuatro con la opción recomendada. Se registran como DD-29 en la tarea 10.1. Si más adelante alguna cambia, primero `/opsx:update` (spec, design y tareas).
>
> Change de seguimiento de C-12, en la rama `feat/c-12-recordatorios-mock-redis` (PR #8). Roadmap id: C-12. No se agrega un bloque nuevo en `CHANGES.md`: solo una línea de seguimiento en el bloque `[C-12]` (tarea 10.3).
>
> TDD estricto: en cada tarea RED (un test que falla, verificado al ejecutarlo) → GREEN (el mínimo código) → triangular → refactor con los tests en verde. Todo test de persistencia corre contra PostgreSQL real. Redis real solo en la suite de contrato de la cola (`TEST_REDIS_URL`). Reloj inyectado (`RelojManual`), sin `sleep` reales y con datos ficticios. No leer `.env*`. Nombres `test_<unidad>_<escenario>_<esperado>`. Cada grupo cierra con `ruff format` + `ruff check` sin errores, type hints completos y `pytest` completo en verde. Un commit Conventional Commits con scope `c-12` por grupo.

## 1. Preparación

- [x] 1.1 Safety net: con PostgreSQL y Redis de test levantados, correr `pytest` completo y registrar el baseline (cantidad de tests en verde). Si algo falla, frenar y reportarlo como falla preexistente. Verificar con `alembic heads` que la única cabeza es `008`

## 2. Reloj único en el worker (D5, refactor sin cambio de comportamiento)

- [x] 2.1 RED→GREEN: en `tests/fakes.py`, agregar `RelojManual` (invocable; `ajustar(instante)` y `avanzar(delta)`) y `EmisorQueRegistra` (`enviados`, `invocaciones`), y hacer que `EmisorQueFalla` lo extienda. Cubrirlos en `tests/unit/test_fakes.py`: el reloj devuelve lo ajustado y avanza; el emisor registra en orden. Verificar en verde
- [x] 2.2 Refactor: `ProcesarRecordatorio` recibe `reloj` y `procesar(recordatorio_id)` deja de recibir `ahora`. Por ahora el reloj se usa donde hoy se usa `ahora`. `WorkerRecordatorios` recibe `reloj` y `ciclo()` deja de recibir `ahora`. `app/worker.py`: `construir_worker(config, reloj=...)` y `correr(worker, *, detenido, pausa_s, max_ciclos)` llama `worker.ciclo()`. Ajustar `_Ciclable`, `tests/unit/test_worker.py`, `helpers_recordatorios.armar_worker` (recibe el reloj; helper `ciclo_a(worker, reloj, instante)`) y las 29 llamadas `ciclo(ahora)` de los tests de integración, sin cambiar ninguna aserción. Verificar con `pytest` completo igual al baseline de 1.1

## 3. `MockSender` sin estado (D6)

- [x] 3.1 Refactor de tests: los tests que inspeccionan `MockSender().enviados` (`test_procesar_recordatorio.py`, `test_procesar_recordatorio_descartes.py`, `test_reencolar_pendientes.py` y `test_concurrencia_recordatorios.py`, donde `SenderQueEsperaAlOtro` pasa a heredar de `EmisorQueRegistra`) usan `EmisorQueRegistra`. Verificar con `pytest` completo en verde y sin cambiar aserciones
- [x] 3.2 RED→GREEN: en `tests/unit/test_mock_sender.py`, escenario "Envíos repetidos no acumulan estado en el adaptador mock" (`vars(sender)` igual antes y después de 1000 envíos) y escenario "El adaptador mock registra el envío" redactado de nuevo (`caplog` con un `INFO` que tiene el id del recordatorio y el texto, sin el id del paciente). Quitar `enviados` de `MockSender` (design D6). Verificar en verde

## 4. CHECK de pendientes con menos de 3 intentos y migración `009` (D3)

- [x] 4.1 RED→GREEN: `tests/integration/test_migracion_009.py` (base scratch). Escenario "Restricción reversible": `upgrade head` crea `ck_recordatorio_pendiente_intentos`; `downgrade 008` la elimina y la base acepta un `pendiente` con `intentos` 3; un `upgrade` nuevo sobre una base sin ese dato la restaura y la base lo vuelve a rechazar. Ajustar `test_migrations.py` para esperar `"009"`. Si `test_migracion_008.py` afirma sobre `head` algo que `009` cambia, fijarlo a `"008"`. Escribir `backend/alembic/versions/009_recordatorio_pendiente_intentos.py` (`down_revision = "008"`, con `downgrade`). Verificar en verde y que `alembic heads` muestra solo `009`
- [x] 4.2 RED→GREEN: declarar la `CheckConstraint` en el modelo `Recordatorio` con la convención de nombres de `base.py`. Verificar que `test_modelos_vs_migracion.py` no detecta diferencias
- [x] 4.3 RED→GREEN: en `tests/integration/test_recordatorio_constraints.py`, sumar `pendiente` con `intentos` 3 al parametrizado de "Valores inválidos rechazados" y agregar el escenario "Un pendiente no llega a 3 intentos" (`UPDATE` de un `pendiente` con 2 intentos a 3 → CHECK; a 3 con `fallido` → aceptado), cada caso en un SAVEPOINT. Verificar en verde
- [x] 4.4 Actualizar `knowledge-base/04_modelo_de_datos.md` §Recordatorio con el CHECK `ck_recordatorio_pendiente_intentos` (DD-29) y verificar que coincide con la migración `009`

## 5. Backoff persistido en `programado_para` (D2, hallazgos 2 y 3)

- [x] 5.1 RED: en `tests/integration/test_reencolar_pendientes.py`, escenario "El reinicio conserva la espera del reintento", de punta a punta: un ciclo a 13:00Z con `EmisorQueFalla(fallas=1)` deja el recordatorio con `intentos` 1. Se simula el reinicio con una `ColaEnMemoria` nueva y vacía y `iniciar()`. Un ciclo a 13:00:30Z no invoca el puerto y uno a 13:01Z lo invoca una vez, y el recordatorio queda `enviado` con `intentos` 2. Ejecutarlo y confirmar que falla con el código actual (el reintento se adelanta a 13:00:30Z porque `programado_para` sigue en 13:00Z). Queda en rojo hasta 5.3
- [x] 5.2 RED→GREEN: en `tests/integration/test_repositorio_recordatorios.py`, `registrar_fallo(id, proximo_intento)` suma un intento y asigna `programado_para` en UTC cuando no llega a `fallido`; con el tercer intento pasa a `fallido` y deja `programado_para` sin cambios; con `proximo_intento=None` no lo toca. Implementar en el repositorio (design D2). Verificar en verde
- [x] 5.3 RED→GREEN: en `tests/integration/test_reintentos_recordatorio.py`, escenarios "Primer intento fallido" (`programado_para` 13:01Z en la base y en la cola), "Segundo intento fallido" (13:03Z) y "Tercer intento fallido" (`fallido`, `programado_para` 13:03Z, 3 invocaciones). `ProcesarRecordatorio` lee el reloj al fallar y pasa el próximo intento a `registrar_fallo`. Verificar en verde y que "Falla y después éxito" y "Un recordatorio fallido no se reintenta" siguen pasando
- [x] 5.4 RED→GREEN: escenario "La espera se cuenta desde el momento de la falla": R1 y R2 vencidos a 13:00Z, un emisor de test que envía R1 y, con R2, avanza el `RelojManual` a 13:00:40Z y falla. R2 queda `pendiente`, `intentos` 1 y `programado_para` 13:01:40Z en la base y en la cola. Verificar en verde
- [x] 5.5 Actualizar `knowledge-base/04_modelo_de_datos.md` §Recordatorio (`programado_para` = próximo intento programado; al crear vale `inicio - REMINDER_LEAD_HOURS`), `07_flujos_principales.md` Flujo 6 (el próximo intento se persiste y el reinicio respeta la espera) y la referencia de RN-NO-05 en `05_reglas_de_negocio.md` ("precisada en DD-28 y DD-29"). Verificar que el texto coincide con el spec

## 6. Sin envío para turnos ya iniciados (D1)

- [x] 6.1 RED→GREEN: en `tests/integration/test_procesar_recordatorio_descartes.py`, los escenarios del requisito "Sin envío para turnos ya iniciados": inicio igual al reloj → `cancelado` con `intentos` 0, sin invocación y fuera de la cola; reloj un minuto antes del inicio con un recordatorio atrasado → `enviado` con `intentos` 1; caída larga (`iniciar()` y ciclo a 2026-10-09T15:00Z) → `cancelado` con `intentos` 0; reintento con `intentos` 1 de un turno iniciado → `cancelado` con `intentos` 1. Implementar el chequeo después de los de estado, con el reloj leído bajo bloqueo y un `logger.info` sin datos del paciente (design D1). Verificar en verde y que los escenarios de "Sin envío para turnos cancelados ni recordatorios no pendientes" siguen pasando
- [x] 6.2 Actualizar `knowledge-base/07_flujos_principales.md` Flujo 6, paso 1 (verifica que el turno siga activo y no haya iniciado; si inició, el recordatorio queda `cancelado`) y, en `05_reglas_de_negocio.md`, RN-NO-01 con la marca "precisada en DD-29" (el recordatorio previo no se envía si el turno ya inició; queda `cancelado`). RN-NO-02 no se modifica: su texto trata de la cancelación y la reprogramación del turno y sigue siendo cierto. Verificar que el texto coincide con el spec
- [x] 6.3 Actualizar `knowledge-base/04_modelo_de_datos.md` §Recordatorio: el pendiente pasa a `cancelado` al cancelar el turno, al reprogramarlo con cambio de inicio y, desde DD-29, cuando el worker lo procesa con el turno ya iniciado (`inicio <= ahora`), conservando sus `intentos`. Verificar que el texto coincide con el requisito "Sin envío para turnos ya iniciados"

## 7. Devolución a la cola ante un error a mitad de lote (D4)

- [x] 7.1 RED→GREEN: en `tests/fakes.py`, un emisor que falla solo con ids dados y una cola en memoria que rechaza con `redis.exceptions.ConnectionError` el encolado de ids dados o todo encolado a partir de un momento. Cubrir los dos dobles en `tests/unit/test_fakes.py`. Verificar en verde
- [x] 7.2 RED→GREEN: en `tests/integration/test_procesar_recordatorio.py` (o un archivo nuevo `test_devolucion_cola.py`), escenario "Error a mitad de lote": el `ConnectionError` sale de `ciclo()`; R1 `enviado`; R2 `pendiente` con `intentos` 1 y `programado_para` 13:06Z y fuera de la cola; R3 `pendiente` y de vuelta en la cola con vencimiento 13:05Z. Implementar `_devolver` en `WorkerRecordatorios` (design D4). Verificar en verde
- [x] 7.3 RED→GREEN: escenario "La devolución también falla": la excepción propagada es la del reintento de R2 (no la de la devolución), hay un `warning` en `caplog` sin datos de pacientes, y después `iniciar()` con una cola disponible deja R2 con 13:06Z y R3 con 13:02Z. Verificar en verde y que `test_worker.py` "propaga errores inesperados" sigue pasando

## 8. Cola: tomar los vencidos en un solo viaje (D7)

- [x] 8.1 Red de seguridad: en `tests/integration/test_contrato_cola_recordatorios.py`, escenario "Consumidores simultáneos no comparten elementos" (50 vencidos, dos hilos con una barrera que piden hasta vaciar; la intersección es vacía y la unión son los 50), parametrizado sobre `ColaRedis` y `ColaEnMemoria` (que suma un `threading.Lock`). La implementación actual ya entrega a un solo consumidor, así que puede pasar sin cambios: se escribe antes del refactor para protegerlo. Verificar en verde contra las dos implementaciones
- [x] 8.2 Refactor: `ColaRedis.tomar_vencidos` con el script Lua registrado en el constructor (design D7). Verificar que toda la suite de contrato sigue en verde contra Redis real (`TEST_REDIS_URL`), sin cambiar sus aserciones, y que el docstring de `ColaRedis` describe el script

## 9. La API depende de Redis en Compose (D8)

- [x] 9.1 RED→GREEN: en `tests/unit/test_docker_compose.py`, escenario "La API espera a Redis" (`api.depends_on` con `db: service_healthy` y `redis: service_started`). Editar `docker-compose.yml`. Verificar en verde y, si Docker está disponible, que `docker compose config` no da errores
- [x] 9.2 Actualizar `knowledge-base/08_arquitectura_propuesta.md` si describe las dependencias de arranque de los servicios. Verificar que coincide con `docker-compose.yml`

## 10. Decisiones y documentación transversal

- [x] 10.1 Registrar **DD-29** en `knowledge-base/09_decisiones_y_supuestos.md` con D1..D4 tal como las aprobó el usuario el 2026-11-04 (las cuatro con la opción recomendada), con alternativas descartadas y consecuencias (el cambio de significado de `programado_para`). Anotar en DD-28 que DD-29 reemplaza dos cosas: la limitación aceptada "el re-encolado al reiniciar ignora el backoff restante" y la alternativa descartada "columna `proximo_intento_en`" (ahora se reusa `programado_para`). Verificar que todas las citas "a registrar en DD-29" del spec tienen fuente
- [x] 10.2 En `knowledge-base/10_preguntas_abiertas.md`, mover "Recordatorio procesado después del inicio del turno" y "Backoff perdido al reiniciar el worker" a una sección "Preguntas resueltas (2026-11-04)" con su resolución (DD-29), y actualizar el párrafo de conteo (queda una pregunta abierta: lectura del estado de los recordatorios). Verificar que la tabla de abiertas tiene una sola fila
- [x] 10.3 Quitar de `CHANGES.md` (backlog) la línea "Persistir el vencimiento del próximo reintento de un recordatorio en la base..." y agregar al bloque `[C-12]` la línea "Seguimiento: `recordatorios-ajustes-revision` (revisión del PR #8, DD-29)". Verificar con `grep` que no queda ninguna referencia a esa pregunta como pendiente y que el bloque `[C-12]` nombra el change de seguimiento
- [x] 10.4 Actualizar el aviso de preguntas abiertas de `CLAUDE.md` y `AGENTS.md` (una pregunta abierta no bloqueante, la lectura del estado de los recordatorios; el resto resuelto en DD-13..DD-29). Verificar con `cmp CLAUDE.md AGENTS.md` que siguen idénticos
- [x] 10.5 Revisar el README (sección de tests y de servicios) y actualizarlo solo si menciona algo que este change cambia (dependencias de `api` o `MockSender.enviados`). Verificar con `grep`

## 11. Verificación integral

- [ ] 11.1 `ruff format --check` y `ruff check` sin errores; `pytest` completo en verde (baseline de 1.1 más los tests nuevos) con PostgreSQL y Redis de test levantados; `alembic heads` con una sola cabeza `009`; `alembic upgrade head`, `downgrade 008` y `upgrade head` sin errores sobre una base scratch; `openspec validate recordatorios-ajustes-revision --strict` sin errores
- [ ] 11.2 Checkpoint FINAL_DIFF (lo hace el orquestador): consultar al agente `advisor` sobre `git diff` del change antes de dar el Apply por terminado. Un veredicto BLOCK frena hasta que el usuario confirme; CONCERNS se resuelven o se informan

## Workflow follow-up

- `revisar-escenarios recordatorios-ajustes-revision` ya corrió (sin BLOQUEANTE ni MAYOR). Sus hallazgos MENOR H1..H5 se resolvieron con `/opsx:update` el 2026-11-04.
- El usuario aprobó D1..D4 (governance ALTO) el 2026-11-04. El próximo paso es `/opsx:apply`.
- El archive (`/opsx:archive recordatorios-ajustes-revision`, que sincroniza el delta en `openspec/specs/recordatorios/spec.md`) se hace en esta misma rama, antes del merge del PR #8. Push solo a pedido del usuario.
