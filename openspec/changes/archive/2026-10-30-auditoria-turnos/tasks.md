# Tasks

> Governance CRÍTICO: no empezar el Apply sin la aprobación explícita del usuario sobre las decisiones **[A confirmar]** de `design.md` (D1, D2, D3, D5, D6, D8); D10 (reprogramación sin cambio efectivo) ya la resolvió el usuario el 2026-10-30. Cada grupo se revisa antes de pasar al siguiente.
>
> TDD estricto: en cada tarea RED (test que falla, verificado ejecutándolo) → GREEN (mínimo código) → triangular → refactor con tests en verde. Unit tests de dominio sin BD; todo test de persistencia contra PostgreSQL real (nunca SQLite ni mocks de la base). Datos 100 % ficticios (emails `@example.com`, nombres inventados), instantes `timestamptz` en UTC y reloj fijo inyectado (`get_reloj` sobreescrito en API). Nombres `test_<unidad>_<escenario>_<esperado>`. Cerrar cada grupo con `ruff format` + `ruff check` sin errores, type hints completos y `pytest` completo en verde. Un commit Conventional Commits con scope `c-07` por grupo (solo si el usuario lo pide).

## 1. Preparación

- [x] 1.1 Safety net: correr `pytest` completo (C-01..C-06) contra la BD de test y registrar el baseline de tests en verde; si algo falla, frenar y reportarlo como falla preexistente

## 2. Instantánea del turno (dominio, sin BD)

- [x] 2.1 RED→GREEN: `tests/unit/test_dominio_auditoria.py` — `instantanea_turno` sobre un `TurnoCreado` con sillón devuelve exactamente las claves `profesional_id`, `paciente_id`, `prestacion_id`, `sillon_id`, `inicio`, `fin`, `duracion_min`, `estado`, `motivo_cancelacion`, con UUIDs como texto, `estado = "programado"` y `motivo_cancelacion = None`; triangular con un `TurnoRegistrado` cancelado sin sillón y con motivo; `inicio` informado con `-03:00` sale como el mismo instante en UTC (`+00:00`); el resultado es serializable con `json.dumps`; `AccionAuditoria` tiene exactamente `crear`, `reprogramar`, `cancelar`; verificar en verde y que `app/domain/auditoria.py` no importa SQLAlchemy ni FastAPI

## 3. Tabla `turno_auditoria`, migración `005` y garantías de la base

- [x] 3.1 RED→GREEN: `tests/integration/test_migracion_005.py` (base scratch) — `upgrade head` crea `turno_auditoria` con columnas `id, turno_id, usuario_id, accion, valores_previos, valores_nuevos, ocurrido_en` (`id` identity `ALWAYS`, `jsonb`, `timestamptz`, nulabilidad de design §2), CHECKs `ck_turno_auditoria_accion_valida` y `ck_turno_auditoria_previos_segun_accion`, FKs `turno_id → turno` y `usuario_id → usuario` ambas `RESTRICT`, índices `ix_turno_auditoria_turno_id (turno_id, id)` e `ix_turno_auditoria_usuario_id`, y los triggers append-only; `downgrade 004` elimina tabla, triggers y función y re-`upgrade` los restaura; ajustar `test_migrations.py` para esperar `"005"` y `test_migracion_004.py` para subir a `"004"` en lugar de `head` si compara conjuntos exactos; escribir `alembic/versions/005_turno_auditoria.py` con `downgrade`; verificar en verde
- [x] 3.2 RED→GREEN: modelo `app/infrastructure/db/models/turno_auditoria.py` (`Identity(always=True)`, registrado en `models/__init__.py`); agregar `TurnoAuditoria` a `test_modelos_vs_migracion.py` y verificar que `compare_metadata` no detecta diferencias
- [x] 3.3 RED→GREEN: `tests/integration/test_turno_auditoria_constraints.py` (requisito "Integridad del registro en la base") — inserción directa válida de un `cancelar` aceptada; `accion = 'borrar'` → CHECK; `crear` con previos no nulos → CHECK; `reprogramar` y `cancelar` con previos nulos → CHECK; `valores_nuevos` nulo y `ocurrido_en` nulo → NOT NULL; `turno_id` y `usuario_id` inexistentes → FK; borrar un turno auditado y un usuario autor → FK (parametrizar; cada caso en un SAVEPOINT de la `db_session`); verificar en verde
- [x] 3.4 RED→GREEN: `tests/integration/test_turno_auditoria_append_only.py` (requisito "Registro append-only garantizado por la base") — `UPDATE` de `usuario_id` y de `valores_nuevos`, `DELETE` de la fila y `TRUNCATE` de la tabla son rechazados por la base con el mensaje `turno_auditoria es append-only`, y el registro conserva sus valores tras el rollback del SAVEPOINT; verificar en verde y `pytest` completo (los fixtures de concurrencia siguen limpiando sin errores)

## 4. Repositorio de auditoría

- [x] 4.1 RED→GREEN: `tests/integration/test_repositorio_auditoria.py` — `RepositorioAuditoria.registrar` persiste la fila con `flush` (visible en la misma sesión sin commit) y `listar_por_turno` devuelve `RegistroAuditoria` en orden de inserción aun con `ocurrido_en` idénticos, con `ocurrido_en` en UTC; triangular: solo los registros del turno pedido y lista vacía para un turno sin registros; verificar que la clase no expone métodos de actualización, borrado, `commit` ni `rollback`
- [x] 4.2 RED→GREEN: en `tests/integration/test_repositorio_turnos.py`, `RepositorioTurnos.existe` devuelve `True` para un turno insertado y `False` para un UUID desconocido; verificar en verde

## 5. Observador de cancelación con turno anterior (refactor)

- [x] 5.1 Safety net: correr `test_cancelar_turno.py`, `test_api_cancelar_turno.py` y `test_concurrencia_cancelar.py` y registrar cuántos pasan
- [x] 5.2 RED→GREEN: en `tests/integration/test_cancelar_turno.py`, un observador espía registrado en `CancelarTurno` recibe `(anterior, nuevo)` con `anterior.estado = "programado"`, `anterior.motivo_cancelacion = None` y `nuevo.estado = "cancelado"` con el motivo normalizado; cambiar `ObservadorCancelacion` a `Callable[[TurnoRegistrado, TurnoRegistrado], None]`; verificar que los tests de 5.1 siguen en verde con el mismo número

## 6. Auditor en los casos de uso y rollback conjunto

- [x] 6.1 RED→GREEN: `tests/integration/test_auditoria_turnos.py` — `CrearTurno` con `observadores=[AuditorTurnos(RepositorioAuditoria(s), usuario.id, reloj_fijo).al_crear]` deja un registro `crear` con `usuario_id`, `ocurrido_en` = reloj fijo, previos nulos y `valores_nuevos` = instantánea del turno creado (escenarios "Alta auditada" y "Alta con duración ajustada y sin sillón"); además lee `valores_nuevos` directo de la fila persistida (no de la API) y verifica las claves exactas de la instantánea y que `inicio`/`fin` son el texto UTC con `+00:00` (escenarios "Campos de la instantánea" e "Instantes en UTC", con un `crear` y un `cancelar` concretos); verificar en verde
- [x] 6.2 RED→GREEN: `ReprogramarTurno` con `al_reprogramar` registra previos y nuevos con el horario anterior y el nuevo; cambio de profesional y sillón; dos reprogramaciones encadenan previos = nuevos anteriores y reprogramación sin cambio efectivo (mismos valores, DD-23a) que igual registra con previos = nuevos (escenarios del requisito "Registro de auditoría al reprogramar un turno"); verificar en verde
- [x] 6.3 RED→GREEN: `CancelarTurno` con `al_cancelar` registra previos `programado` sin motivo y nuevos `cancelado` con el motivo normalizado; sin motivo, nulo en ambos (escenarios del requisito "Registro de auditoría al cancelar un turno"); verificar en verde
- [x] 6.4 RED→GREEN: rollback conjunto con falla real de la base — auditor construido con un `usuario_id` inexistente: el alta falla y no queda ni turno ni registro; la reprogramación falla y el turno conserva su horario; la cancelación falla y el turno sigue `programado` sin motivo y su horario sigue ocupado (un alta solapada da `SolapamientoError`); verificar en verde
- [x] 6.5 RED→GREEN: rechazos no auditados a nivel de caso de uso — alta en conflicto (`SolapamientoError`), reprogramación con `duracion_min` 7 (`TurnoInvalidoError`) y segunda cancelación (`turno_ya_cancelado`) no cambian la cantidad de registros; verificar en verde

## 7. Enchufe en la API de turnos

- [x] 7.1 RED→GREEN: `tests/integration/test_api_auditoria_registro.py` — con `client` (recepcionista R) y reloj fijo: `POST /turnos`, `PATCH /turnos/{id}/reprogramar` y `POST /turnos/{id}/cancelar` exitosos dejan, cada uno, exactamente un registro con la acción, `usuario_id` de R y `ocurrido_en` del reloj; R crea, S reprograma y R cancela → autores R, S, R; body de alta con `usuario_id` y `creado_por` de S → registro con R; modificar `get_crear_turno`, `get_reprogramar_turno` y `get_cancelar_turno` para depender de `RecepcionistaAutenticada` y registrar el auditor; verificar en verde
- [x] 7.2 RED→GREEN: rechazos por API no auditados — alta `409`, reprogramación `422`, segunda cancelación `409 turno_ya_cancelado`, cancelación de un odontólogo `403`, cancelación sin token `401`, y cancelación y reprogramación de un UUID inexistente `404` no cambian la cantidad total de registros; verificar en verde y `pytest` completo (los tests de API de C-03..C-06 siguen sin cambios en sus aserciones)

## 8. Consulta `GET /turnos/{id}/auditoria`

- [x] 8.1 RED→GREEN: `tests/integration/test_consultar_auditoria.py` — `ConsultarAuditoriaTurno.ejecutar` devuelve los registros del turno en orden; turno existente sin registros → lista vacía; turno inexistente → `TurnoInexistenteError`; verificar en verde
- [x] 8.2 RED→GREEN: `tests/integration/test_api_auditoria_consulta.py` — router `app/api/auditoria.py` registrado en `create_app`: historial `crear`, `reprogramar`, `cancelar` en ese orden con autores R, S, R y `ocurrido_en` 2026-10-07T09:00-03:00 (reloj fijo); `valores_previos` nulo en `crear` e `inicio`/`fin` de las instantáneas en `-03:00`; cada elemento incluye `id`; dos registros con el mismo `ocurrido_en` salen en orden de inserción; dos consultas iguales y sin registros nuevos; solo los registros del turno pedido; turno insertado directo → `200 []`; turno insertado directo y luego cancelado por API → un único registro `cancelar`; UUID inexistente → `404` con `codigo = "turno_inexistente"`; `no-es-un-id` → `422`; verificar en verde
- [x] 8.3 RED→GREEN: acceso por rol en `test_api_auditoria_consulta.py` — odontólogo sobre un turno de su propio profesional → `403` con `{"detail": {"codigo": "rol_insuficiente", "mensaje": "Rol insuficiente"}}` sin registros en el cuerpo; sin token → `401` con `WWW-Authenticate: Bearer` y `no_autenticado`; odontólogo con UUID inexistente → `403`, no `404`; sin token y `no-es-un-id` → `401`, no `422`; `POST`, `PUT`, `PATCH` y `DELETE` sobre la ruta → `405` y los registros no cambian; verificar en verde

## 9. Documentación y cierre

- [x] 9.1 Registrar en `knowledge-base/09_decisiones_y_supuestos.md` la decisión **DD-25** (D1, D2, D3, D5, D6, D8 tal como las aprobó el usuario, más D10: una reprogramación sin cambio efectivo igual genera registro con previos = nuevos, decisión de Matías del 2026-10-30), actualizar `02_descripcion_general.md` (fila Auditoría → `GET /turnos/{id}/auditoria`), `04_modelo_de_datos.md` §TurnoAuditoria (id identity, CHECKs, FKs, trigger) y agregar al backlog de `CHANGES.md` "rol de base de datos de mínimo privilegio para la aplicación"; verificar que `CLAUDE.md`/`AGENTS.md` no quedan desalineados con lo cambiado
- [x] 9.2 Verificación integral: `ruff format --check` y `ruff check` sin errores, `pytest` completo en verde (baseline de 1.1 + nuevos) y `alembic heads` con una sola cabeza (si C-08 ya mergeó su `005`, renumerar esta revisión a `006` y su test de `head`); `openspec validate auditoria-turnos --strict` sin errores
- [x] 9.3 Checkpoint FINAL_DIFF: consultar al agente `advisor` sobre `git diff` antes de declarar el Apply terminado; un veredicto BLOCK frena hasta la confirmación del usuario

## Workflow follow-up

- Correr `revisar-escenarios auditoria-turnos` antes del Apply y, si hay hallazgos BLOQUEANTE o MAYOR, ajustar con `/opsx:update`.
- Abrir PR de `feat/c-07-auditoria-turnos` con revisión de Nico; `/opsx:archive auditoria-turnos` en la rama del change antes del merge y marcar `[x]` C-07 en `CHANGES.md`.
