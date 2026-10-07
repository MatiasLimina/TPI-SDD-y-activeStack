# Tasks

> TDD estricto: en cada tarea RED (test que falla, verificado ejecutándolo) → GREEN (mínimo código) → triangular → refactor con tests en verde. Unit tests de dominio sin BD; todo test de persistencia contra PostgreSQL real (nunca SQLite ni mocks de la base). Cerrar cada tarea con `ruff format` + `ruff check` sin errores y type hints completos. Datos de test 100 % ficticios. Un commit Conventional Commits por grupo (solo si el usuario lo pide).

## 1. Preparación

- [ ] 1.1 Safety net: correr `pytest` completo (C-01 + C-02) contra la BD de test y registrar el baseline de tests pasando; si algo falla, frenar y reportarlo como falla preexistente

## 2. Dominio puro de turnos (`app/domain/turnos.py`, sin BD)

- [ ] 2.1 RED→GREEN: `tests/unit/test_dominio_turnos.py` — `solapan` semiabierto: [10:00,10:45) vs [10:45,11:30) no solapa; vs [10:30,11:00) y vs [09:00,12:00) sí; simetría A/B; verificar `pytest tests/unit/test_dominio_turnos.py -k solapan` en verde
- [ ] 2.2 RED→GREEN: `duracion_efectiva` — sin duración informada toma la de la prestación (45), informada la reemplaza (60); y cálculo de `fin = inicio + duración` (10:00+45 → 10:45); verificar en verde
- [ ] 2.3 RED→GREEN: `validar_duracion_y_grilla` — rechaza 0, -5, 42 y 485 con `TurnoInvalidoError(codigo="duracion_invalida")`; acepta 5 y 480; rechaza inicio local 10:07 y 10:05:30 con `inicio_no_alineado`; acepta 10:05 local; triangular con un instante UTC cuya hora local está alineada (evaluación en `America/Argentina/Buenos_Aires` vía `to_local`); verificar en verde
- [ ] 2.4 RED→GREEN: `validar_inicio_futuro(inicio, ahora)` — 08:55 con ahora 09:00 → `inicio_en_pasado`; 09:05 aceptado; igual a `ahora` aceptado; verificar en verde
- [ ] 2.5 RED→GREEN: `validar_sillon` — requiere y falta → `sillon_requerido`; no requiere e informado → `sillon_no_corresponde`; requiere e informado, y no requiere sin informar → aceptados; verificar en verde
- [ ] 2.6 Refactor: jerarquía de errores (`TurnoInvalidoError`, `ReferenciaInvalidaError`, `SolapamientoError` con recursos en orden `profesional, sillon, paciente`) y tipos inmutables (`Intervalo`, `TurnoPropuesto`, `TurnoCreado`); verificar que todo `tests/unit` sigue verde y que el módulo no importa SQLAlchemy ni FastAPI

## 3. Modelo `Turno` y migración `003` (garantía en BD)

- [ ] 3.1 RED: `tests/integration/test_migracion_003.py` — tras `upgrade head` existe `turno` con sus columnas, FKs, `ck_turno_estado_valido`, `ck_turno_fin_mayor` y las exclusiones `turno_sin_solape_profesional|sillon|paciente`; `downgrade 002` la elimina (usar `scratch_url`); verificar que falla
- [ ] 3.2 GREEN: escribir `backend/alembic/versions/003_turno.py` (tabla, FKs `ON DELETE RESTRICT`, `estado varchar` default `programado`, `creado_por` y `motivo_cancelacion` nullables, CHECKs, `EXCLUDE USING gist (... tstzrange(inicio, fin, '[)') WITH &&) WHERE (estado <> 'cancelado' [AND sillon_id IS NOT NULL])`, índices `(profesional_id, inicio)` y `(sillon_id, inicio)`, downgrade); verificar que 3.1 pasa
- [ ] 3.3 Crear `app/infrastructure/db/models/turno.py` con `ExcludeConstraint` y CHECKs equivalentes, re-exportarlo en `models/__init__.py` y ampliar `test_modelos_vs_migracion.py` con `turno`; verificar que el autogenerate no detecta diferencias (si Alembic reporta los índices GiST, filtrarlos con `include_object` documentando el motivo)
- [ ] 3.4 RED→GREEN: `tests/integration/test_turno_constraints.py` — inserción directa superpuesta rechazada por cada exclusión (profesional, sillón, paciente) con SQLSTATE `23P01` y el `constraint_name` esperado; dos turnos sin sillón en el mismo horario no chocan por sillón; contiguos aceptados; un turno `cancelado` no bloquea; `estado='reprogramado'` y `fin = inicio` rechazados por CHECK (usar savepoints); verificar en verde

## 4. Repositorio de turnos (`app/infrastructure/db/repositorio_turnos.py`)

- [ ] 4.1 RED→GREEN: carga de referencias — devuelve profesional, paciente, prestación y sillón por id; un id inexistente → `ReferenciaInvalidaError(referencia, "inexistente")`; un recurso inactivo (incluida prestación `activa=false`) → `"inactiva"`; verificar en verde
- [ ] 4.2 RED→GREEN: pre-chequeo `buscar_conflictos(intervalo, profesional, sillon, paciente)` en una sola consulta — devuelve `{profesional}`, `{sillon}`, `{paciente}` o los tres según el turno existente; ignora cancelados y contiguos; sin sillón no consulta por sillón; verificar en verde
- [ ] 4.3 RED→GREEN: `insertar` persiste en UTC y traduce `IntegrityError` con `23P01` a `SolapamientoError({recurso})` según `constraint_name` (un caso por cada exclusión), haciendo rollback; otras violaciones se relanzan; verificar en verde

## 5. Caso de uso `CrearTurno` (`app/application/crear_turno.py`)

- [ ] 5.1 RED→GREEN: alta válida con reloj fijo inyectado → `TurnoCreado` con `estado=programado`, duración por defecto y `fin` calculado, `creado_por` nulo; triangular con duración ajustada; verificar en verde
- [ ] 5.2 RED→GREEN: orden de validaciones — referencia inválida y reglas de dominio (`inicio_en_pasado` con el reloj inyectado, sillón, duración) responden antes que el solape (un pedido inválido y en conflicto produce el error de validación, no `SolapamientoError`); verificar en verde
- [ ] 5.3 RED→GREEN: pre-chequeo — conflicto que involucra profesional, sillón y paciente a la vez produce `SolapamientoError` con los tres recursos; uno solo produce un recurso; verificar en verde
- [ ] 5.4 RED→GREEN: puntos de extensión — un validador inyectado que lanza error corta el alta (no se persiste nada); un observador inyectado recibe el `TurnoCreado` antes del commit; con listas vacías (default) el alta funciona igual; verificar en verde
- [ ] 5.5 RED→GREEN: carrera que esquiva el pre-chequeo — con el pre-chequeo forzado a vacío (solo esa consulta sustituida, `INSERT` real en PostgreSQL) y un turno existente en el mismo sillón, el alta termina en `SolapamientoError({sillon})`; verificar en verde

## 6. API `POST /turnos` (`app/api/turnos.py`)

- [ ] 6.1 RED→GREEN: `tests/integration/test_api_turnos.py` — `POST /turnos` válido → `201` con `estado`, `inicio`/`fin` en `-03:00`, `duracion_min` y `creado_por` nulo; en la BD `inicio` en UTC; dependencia `get_reloj` sobreescrita con reloj fijo; router registrado en `create_app()`; verificar en verde
- [ ] 6.2 RED→GREEN: `422` — inicio sin zona horaria; duración 42, 485 y 0; inicio 10:07 y 10:05:30; inicio en el pasado; sillón faltante; sillón sobrante con "Consulta"; cada caso sin persistir turno y con `detail.codigo` esperado; verificar en verde
- [ ] 6.3 RED→GREEN: `422` por referencias — profesional, paciente, prestación y sillón inexistentes (no `404`) y sillón/prestación inactivos, con `detail.referencia`; verificar en verde
- [ ] 6.4 RED→GREEN: `409` — solape por profesional, por sillón, por paciente con distinto profesional, y 409 que lista `["profesional","sillon","paciente"]`; verificar en verde
- [ ] 6.5 RED→GREEN: aceptados (`201`) — contiguos mismo profesional y sillón; mismo paciente contiguo; mismo horario con recursos distintos; prestación sin sillón no genera conflicto de sillón; turno cancelado preexistente no bloquea; duración 480 aceptada; verificar en verde

## 7. Concurrencia (DD-18)

- [ ] 7.1 RED→GREEN: `tests/integration/test_concurrencia_turnos.py` — fixture con catálogo ficticio commiteado en conexión propia; N=10 hilos sincronizados con `threading.Barrier`, cada uno con su `Session` llamando a `CrearTurno` para el mismo profesional, sillón y horario; exactamente 1 éxito, 9 `SolapamientoError`, y un solo turno activo en la BD; limpieza en `finally`; correrlo 3 veces seguidas y verificar que es estable

## 8. Cierre

- [ ] 8.1 Verificar integración completa: `pytest` en verde (baseline de 1.1 + nuevos), `ruff format --check` y `ruff check` sin errores, `alembic downgrade 002 && alembic upgrade head` sin error, y `openspec validate crear-turno-sin-solapamientos` sin errores
