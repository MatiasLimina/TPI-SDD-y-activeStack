# Tasks

> TDD estricto: en cada tarea RED (test que falla, verificado ejecutándolo) → GREEN (mínimo código) → triangular → refactor con tests en verde. Unit tests de dominio sin BD; todo test de persistencia contra PostgreSQL real (nunca SQLite ni mocks de la base). Reloj siempre inyectado (fijo en tests). Cerrar cada tarea con `ruff format` + `ruff check` sin errores y type hints completos. Datos de test 100 % ficticios. Sin migración nueva. Un commit Conventional Commits por grupo (solo si el usuario lo pide).

## 1. Preparación

- [x] 1.1 Safety net: correr `pytest` completo (C-01..C-03) contra la BD de test y registrar el baseline de tests pasando; si algo falla, frenar y reportarlo como falla preexistente

## 2. Dominio de cancelación (`app/domain/turnos.py`, sin BD)

- [x] 2.1 RED→GREEN: `tests/unit/test_dominio_turnos.py` — `validar_cancelable(estado, inicio, ahora)`: `programado` con inicio 10:00 y ahora 09:59 aceptado; ahora 10:00 (límite exacto), 10:20 (en curso) y día siguiente (pasado) → `TurnoNoCancelableError(codigo="turno_ya_iniciado")`; verificar `pytest tests/unit/test_dominio_turnos.py -k cancelable` en verde
- [x] 2.2 RED→GREEN: triangular `validar_cancelable` con estado `cancelado` → `turno_ya_cancelado`, tanto con inicio futuro como con inicio pasado (el estado se informa antes que el tiempo); verificar en verde
- [x] 2.3 RED→GREEN: `normalizar_motivo` — `None` → `None`; `""` y `"   "` → `None`; `"  Viaje imprevisto  "` → `"Viaje imprevisto"`; verificar en verde
- [x] 2.4 Refactor: agregar `TurnoInexistenteError(turno_id)` y `TurnoNoCancelableError(codigo, mensaje)` bajo `TurnoError`, y el dataclass inmutable `TurnoRegistrado` (campos de `TurnoCreado` + `estado` + `motivo_cancelacion`); verificar que todo `tests/unit` sigue verde y que el módulo no importa SQLAlchemy ni FastAPI

## 3. Repositorio (`app/infrastructure/db/repositorio_turnos.py`)

- [x] 3.1 RED→GREEN: `tests/integration/test_repositorio_turnos.py` — `obtener_para_actualizar(id)` devuelve el `TurnoRegistrado` (estado, motivo, inicio/fin en UTC) de un turno existente y `None` para un UUID inexistente; la consulta usa `FOR UPDATE` (verificar con un turno bloqueado desde otra conexión que una segunda lectura con `nowait` falla, o inspeccionando el SQL compilado); verificar en verde
- [x] 3.2 RED→GREEN: `marcar_cancelado(id, motivo)` deja la fila con `estado='cancelado'` y el motivo (también con motivo `None`), sin borrarla, actualiza `actualizado_en`, y conserva profesional, sillón, paciente, prestación, inicio y fin; verificar en verde
- [x] 3.3 RED→GREEN: tras `marcar_cancelado` en la misma sesión, `buscar_conflictos` sobre el mismo intervalo y recursos devuelve vacío y un `insertar` del mismo horario y recursos no viola ninguna exclusión (RN-AG-07 a nivel de BD); verificar en verde

## 4. Caso de uso `CancelarTurno` (`app/application/cancelar_turno.py`)

- [x] 4.1 RED→GREEN: `tests/integration/test_cancelar_turno.py` — con reloj fijo, cancelar un turno futuro devuelve `TurnoRegistrado` con `estado="cancelado"` y motivo normalizado, y lo commitea; triangular sin motivo (`None`); verificar en verde
- [x] 4.2 RED→GREEN: id inexistente → `TurnoInexistenteError`; turno ya cancelado → `TurnoNoCancelableError("turno_ya_cancelado")` sin cambiar el motivo original; turno con inicio igual o anterior al reloj → `TurnoNoCancelableError("turno_ya_iniciado")` y sigue `programado` (insertar el turno directamente o crearlo con un reloj anterior); verificar en verde
- [x] 4.3 RED→GREEN: puntos de extensión — un observador inyectado recibe el `TurnoRegistrado` cancelado antes del commit; un observador que lanza error provoca rollback y el turno sigue `programado`; con la lista vacía (default) la cancelación funciona igual; verificar en verde

## 5. API `POST /turnos/{id}/cancelar` (`app/api/turnos.py`)

- [x] 5.1 RED→GREEN: `tests/integration/test_api_cancelar_turno.py` — con `get_reloj` sobreescrito, crear un turno vía `POST /turnos` y cancelarlo → `200` con `estado="cancelado"`, `inicio`/`fin` en `-03:00` y `motivo_cancelacion`; la fila sigue en la BD con `estado='cancelado'`; `POST /turnos` sigue respondiendo `201` con `motivo_cancelacion` nulo; verificar en verde
- [x] 5.2 RED→GREEN: motivo — sin body → `200` y motivo nulo; `{}` → nulo; `{"motivo": "   "}` → nulo; motivo con espacios en los extremos → guardado sin ellos; motivo de 256 caracteres → `422` y el turno sigue `programado`; verificar en verde
- [x] 5.3 RED→GREEN: errores — UUID inexistente → `404` con `detail.codigo="turno_inexistente"`; `id` no UUID → `422`; segunda cancelación → `409` con `detail.codigo="turno_ya_cancelado"` y motivo original intacto; verificar en verde
- [x] 5.4 RED→GREEN: cancelable solo antes del inicio — reloj 09:59 con inicio 10:00 → `200`; reloj 10:00 → `409 turno_ya_iniciado`; reloj 10:20 (en curso) → `409`; turno del día anterior → `409`; turno cancelado y pasado → `409 turno_ya_cancelado`; en cada `409` el turno no cambia (crear con un reloj y cancelar con otro posterior vía `dependency_overrides`); verificar en verde
- [x] 5.5 RED→GREEN: liberación del horario (RN-AG-07) — sin cancelar, el mismo horario y profesional da `409` (profesional); tras cancelar, `POST /turnos` con mismos profesional, sillón, paciente y horario → `201` y quedan dos filas (una `cancelado`, una `programado`); tras cancelar, otro paciente en 10:15–11:00 con el mismo profesional y sillón → `201`; verificar en verde

## 6. Concurrencia

- [x] 6.1 RED→GREEN: `tests/integration/test_concurrencia_cancelar.py` — reutilizar (extrayéndolas a un módulo compartido si hace falta, sin cambiar el comportamiento de `test_concurrencia_turnos.py`) las fixtures de motor propio y catálogo commiteado; con un turno futuro commiteado, N=5 hilos sincronizados con `threading.Barrier`, cada uno con su `Session` y `CancelarTurno` con motivo distinto: exactamente 1 éxito, N-1 `TurnoNoCancelableError("turno_ya_cancelado")`, y en la BD el motivo del hilo exitoso; limpieza en `finally`; correrlo 3 veces seguidas y verificar que es estable, y que `test_concurrencia_turnos.py` sigue verde

## 7. Cierre

- [x] 7.1 Verificar integración completa: `pytest` en verde (baseline de 1.1 + nuevos), `ruff format --check` y `ruff check` sin errores, `test_modelos_vs_migracion.py` verde sin migración nueva, y `openspec validate cancelar-turno --strict` sin errores
