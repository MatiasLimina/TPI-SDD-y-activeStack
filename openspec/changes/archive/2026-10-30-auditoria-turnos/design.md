# Design

## Context

Ver `proposal.md` (Why, Non-goals) y el delta spec `auditoria-turnos`. Estado actual del código relevante (C-01..C-06 archivados):

- **Casos de uso** (`backend/app/application/`): `CrearTurno`, `ReprogramarTurno` y `CancelarTurno` reciben `observadores` opcionales que corren **dentro de la misma transacción, antes del commit**; si un observador lanza, el caso de uso hace `rollback()` y relanza. Firmas actuales: `ObservadorTurno = Callable[[TurnoCreado], None]`, `ObservadorReprogramacion = Callable[[TurnoRegistrado, TurnoRegistrado], None]` (anterior, nuevo) y `ObservadorCancelacion = Callable[[TurnoRegistrado], None]` (solo el turno ya cancelado). Hoy no hay ningún observador registrado.
- `ReprogramarTurno` y `CancelarTurno` leen el turno con `obtener_para_actualizar` (`SELECT ... FOR UPDATE`): las operaciones sobre un mismo turno ya están serializadas. `CrearTurno.ejecutar(..., creado_por=...)` recibe el autor; cancelar y reprogramar **no** reciben al usuario.
- **API** (`backend/app/api/turnos.py`): `RecepcionistaAutenticada = Annotated[UsuarioAutenticado, Depends(requiere_rol(Rol.RECEPCIONISTA))]` definido una vez a nivel de módulo; las fábricas `get_crear_turno`, `get_cancelar_turno`, `get_reprogramar_turno` arman el caso de uso con `get_session` y `get_reloj` (los tests sobreescriben `get_reloj` con un reloj fijo). Errores con cuerpo `{"detail": {"codigo", ...}}`; `TurnoInexistenteError` → `404 turno_inexistente` ya tiene manejador.
- **Modelo**: tablas con `id uuid` (`CatalogoMixin`) y convención de nombres de `base.py` (`ix_%(column_0_label)s`, `ck_%(table_name)s_%(constraint_name)s`, `fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s`). `turno.creado_por` es nullable con FK `RESTRICT` a `usuario` (C-06). Migraciones `001..004`, lineales y numeradas a mano (DD-17).
- **Tests**: `db_session` corre dentro de una transacción externa que siempre se revierte (`join_transaction_mode="create_savepoint"`); el `rollback()` de un caso de uso revierte solo el savepoint. Los tests de concurrencia (`motor_concurrente`, `catalogo_commiteado`) commitean de verdad y limpian con `DELETE FROM turno`; construyen los casos de uso **sin observadores**. `test_migrations.py` afirma `head == "004"`; `test_modelos_vs_migracion.py` compara `Base.metadata` con la base migrada.

## Goals / Non-Goals

**Goals:**
- Auditoría enchufada por los puntos de extensión de C-03/C-05, sin tocar la lógica de validación ni los contratos HTTP de los tres casos de uso.
- Inmutabilidad garantizada por la base (trigger), no solo por la ausencia de métodos en el repositorio.
- Atomicidad por construcción: la fila de auditoría se escribe en la sesión y la transacción del cambio, con `flush` inmediato para que un error aparezca antes del commit.
- Orden del historial determinístico aun con reloj fijo en los tests.
- Suite existente en verde durante todo el change.

**Non-Goals:**
- Hacer la auditoría obligatoria a nivel de caso de uso (ver decisión 4 y Risks).
- Test de concurrencia específico de auditoría (ver Risks).
- Rol de base de datos de mínimo privilegio, auditoría de lecturas, backfill, listado global (ver `proposal.md`).

## Decisions

Las decisiones marcadas **[A confirmar]** no las fija la KB; se proponen acá y, una vez aprobadas por el usuario, se registran como **DD-25** en `knowledge-base/09_decisiones_y_supuestos.md` (tarea del grupo 9). Governance CRITICO: nada de esto se implementa sin esa aprobación.

| Id | Decisión | Fuente |
|---|---|---|
| D1 | Endpoint `GET /turnos/{id}/auditoria`, no `GET /auditoria/turnos` | `CHANGES.md` §C-07 y US-011 (consulta por turno); contradice `02_descripcion_general.md` → **[A confirmar]** alinear 02 |
| D2 | Instantánea completa y fija del turno en ambos lados; `valores_previos` nulo en `crear` | **[A confirmar]** (la KB solo dice "valores previos/nuevos") |
| D3 | `id bigint GENERATED ALWAYS AS IDENTITY`; orden del historial por `id` | **[A confirmar]** (se aparta del `id uuid` del resto del modelo) |
| D4 | Auditor como observador armado por request en la capa API | Puntos de extensión de C-03 (`CHANGES.md`, nota de paralelismo) |
| D5 | `ocurrido_en` = reloj inyectado del sistema, sin `DEFAULT now()` | **[A confirmar]** |
| D6 | Trigger que rechaza `UPDATE`, `DELETE` y `TRUNCATE` | `CHANGES.md` ("opcionalmente trigger"); `TRUNCATE` **[A confirmar]** |
| D7 | Odontólogo → `403`; orden `401` → `403` → `422` (id) → `404` | Matriz de `03` ("Auditoría de turnos: —"), DD-21, DD-24 y precedente de `agenda-turnos` |
| D8 | Respuesta con `usuario_id`, sin nombre ni email del usuario | **[A confirmar]** (minimización de datos; no hay endpoint de usuarios) |
| D9 | Observador de cancelación con firma `(anterior, nuevo)` | Refactor interno |
| D10 | Una reprogramación `PATCH` sin cambio efectivo (DD-23a) igual genera un registro, con `valores_previos` = `valores_nuevos` | Decisión del usuario (Matías, 2026-10-30), opción (a); se registra en DD-25. La auditoría refleja cada operación exitosa, no solo los cambios de valores |

### 1. Capas y módulos
- `app/domain/auditoria.py` (puro): `AccionAuditoria` (`StrEnum`: `crear`, `reprogramar`, `cancelar`); `instantanea_turno(turno: TurnoCreado | TurnoRegistrado) -> dict[str, JsonValue]` con las nueve claves fijas (UUIDs como texto, `inicio`/`fin` vía `to_utc(...).isoformat()`, `motivo_cancelacion` nulo para `TurnoCreado`); `RegistroAuditoria` (dataclass de lectura: `id`, `turno_id`, `usuario_id`, `accion`, `valores_previos`, `valores_nuevos`, `ocurrido_en`).
- `app/infrastructure/db/models/turno_auditoria.py`: modelo `TurnoAuditoria` (no usa `CatalogoMixin`: no tiene `actualizado_en`, porque no se actualiza).
- `app/infrastructure/db/repositorio_auditoria.py`: `RepositorioAuditoria(session)` con **solo** `registrar(turno_id, usuario_id, accion, previos, nuevos, ocurrido_en) -> None` (`add` + `flush`) y `listar_por_turno(turno_id) -> list[RegistroAuditoria]` (`ORDER BY id`). Sin `commit`/`rollback`: la transacción es del caso de uso.
- `app/infrastructure/db/repositorio_turnos.py`: nuevo `existe(turno_id) -> bool` para distinguir "sin registros" de "turno inexistente".
- `app/application/auditoria_turnos.py`: `AuditorTurnos(repositorio, usuario_id, reloj)` con `al_crear(creado)`, `al_reprogramar(anterior, nuevo)` y `al_cancelar(anterior, nuevo)` (métodos ligados que se pasan como observadores); `ConsultarAuditoriaTurno(repo_turnos, repo_auditoria).ejecutar(turno_id)` que lanza `TurnoInexistenteError` si el turno no existe.
- `app/api/auditoria.py`: router con `GET /turnos/{turno_id}/auditoria`, schemas `InstantaneaTurnoOut` y `RegistroAuditoriaOut`, registrado en `main.py`. Reusa `RecepcionistaAutenticada` y el manejador `404` existente.

### 2. Modelo y migración `005_turno_auditoria.py`
```
turno_auditoria
  id               bigint GENERATED ALWAYS AS IDENTITY  PK (pk_turno_auditoria)
  turno_id         uuid        NOT NULL  FK turno(id)   ON DELETE RESTRICT
  usuario_id       uuid        NOT NULL  FK usuario(id) ON DELETE RESTRICT
  accion           varchar(20) NOT NULL  CHECK (accion IN ('crear','reprogramar','cancelar'))
  valores_previos  jsonb       NULL
  valores_nuevos   jsonb       NOT NULL
  ocurrido_en      timestamptz NOT NULL                 -- sin DEFAULT (D5)
  CHECK ((accion = 'crear') = (valores_previos IS NULL))   -- ck_turno_auditoria_previos_segun_accion
  INDEX ix_turno_auditoria_turno_id   (turno_id, id)     -- FK + consulta ordenada
  INDEX ix_turno_auditoria_usuario_id (usuario_id)       -- índice de FK
```
- `accion` como `varchar` + CHECK, mismo criterio que `turno.estado` (DD-21) y `usuario.rol` (DD-24).
- `usuario_id NOT NULL`: desde C-06 las tres operaciones exigen recepcionista autenticada, así que todo registro tiene autor. `creado_por` del turno sigue nullable (no se toca).
- FKs `RESTRICT`: un turno auditado no se borra (coherente con DD-08) y un usuario autor no se borra (DD-16, baja lógica).
- **Append-only (D6)**: función `turno_auditoria_inmutable()` en PL/pgSQL que hace `RAISE EXCEPTION 'turno_auditoria es append-only'`, con dos triggers: `BEFORE UPDATE OR DELETE ... FOR EACH ROW` y `BEFORE TRUNCATE ... FOR EACH STATEMENT`. `downgrade` borra triggers, función, índices y tabla (`DROP TABLE` no dispara triggers).
- **Numeración**: `revision = "005"`, `down_revision = "004"`. C-08 corre en paralelo y puede crear otra `005`: **quien mergea segundo renumera** su revisión (y su test de `head`) para que `alembic heads` muestre una sola cabeza (regla del equipo en `CLAUDE.md`).
- Alternativas descartadas: `id uuid` + `ORDER BY ocurrido_en` (con reloj fijo todos los registros empatan y el orden queda indefinido; `uuid7` recién llega en Python 3.14); solo "sin métodos de escritura" en el repositorio (no protege de SQL directo, y el dominio es CRITICO); `REVOKE UPDATE, DELETE` (la aplicación se conecta como dueña de la tabla, así que no tendría efecto).

### 3. Instantánea (D2)
- Misma forma en `valores_previos` y `valores_nuevos`: `profesional_id`, `paciente_id`, `prestacion_id`, `sillon_id`, `inicio`, `fin`, `duracion_min`, `estado`, `motivo_cancelacion`. `creado_por` no se incluye: el autor de cada operación es el `usuario_id` del registro.
- Instantánea completa en vez de "solo los campos que cambiaron": la comparación es trivial para quien lee, la forma no depende de la acción y el esquema de respuesta se tipa con un único modelo. El costo (repetir campos iguales) es despreciable en el volumen de un consultorio chico.
- `crear` → `valores_previos = NULL` (no había estado anterior); la base lo garantiza con el CHECK de coherencia.
- Persistencia en UTC (`isoformat()` con `+00:00`); la API convierte `inicio`/`fin` a `America/Argentina/Buenos_Aires` al responder, igual que `TurnoOut` (regla dura de datetimes).
- Sin datos personales del paciente: solo su `id` (RN-CU-01, minimización).

### 4. Enchufe en los casos de uso (D4, D9)
- Las fábricas de `api/turnos.py` pasan a depender de `RecepcionistaAutenticada` y construyen `AuditorTurnos(RepositorioAuditoria(session), usuario.id, reloj)`, que se registra como observador: `CrearTurno(..., observadores=[auditor.al_crear])`, etc. La misma `session` del request hace que el registro viva en la transacción del cambio.
- FastAPI cachea la dependencia por request: como la ruta y la fábrica usan **el mismo** alias `RecepcionistaAutenticada`, el usuario se resuelve una sola vez. Sin usuario autenticado no se puede ni siquiera construir el caso de uso.
- **D9**: `ObservadorCancelacion` pasa a `(anterior, nuevo)`, igual que reprogramación; `CancelarTurno` ya tiene el turno leído con `FOR UPDATE`. Así la instantánea previa es la real y no una deducción ("si se canceló, antes estaba programado"). No hay observadores registrados, así que el cambio de firma no rompe nada; C-12 (recordatorios) lo usará igual.
- `ocurrido_en` (D5) sale del mismo `reloj` inyectado que usan las validaciones: es testeable con reloj fijo y coincide con el "ahora" con el que se decidió el cambio. Se descarta `DEFAULT now()` porque en PostgreSQL `now()` es el inicio de la transacción (y en los tests, de la transacción externa), y porque una columna con default permitiría omitir el instante sin que nadie lo note.
- **D10**: el auditor registra en `al_reprogramar` siempre que el caso de uso confirma la operación, incluso si el `PATCH` no cambia ningún valor (DD-23a): previos y nuevos salen iguales. No se agrega lógica de comparación ni excepción.
- Rechazos (`401/403/404/409/422`): los errores se lanzan antes de llegar a los observadores o hacen rollback, así que no queda registro sin código adicional.
- Alternativas descartadas: pasar `usuario_id` a `ejecutar` de los tres casos de uso y cambiar las firmas de todos los observadores (toca más superficie y mezcla el "quién" con la lógica del turno); auditor como parámetro obligatorio del constructor (obliga a reescribir los tests de C-03..C-05 y los de concurrencia, que hoy limpian con `DELETE FROM turno`, ver Risks).

### 5. Atomicidad y rollback conjunto
- `registrar` hace `flush` dentro del observador: una violación de FK, CHECK o NOT NULL salta ahí, el caso de uso hace `rollback()` y relanza (comportamiento existente). En `CrearTurno` el `INSERT` del turno ya está flusheado en su SAVEPOINT, por lo que la FK `turno_id` se satisface.
- Para el test de rollback conjunto se usa una falla **real** de la base: el auditor se construye con un `usuario_id` inexistente y la FK rechaza el registro. Se verifica que el turno no se creó / conserva su horario / sigue programado. No se mockea la base.
- Locks: la FK toma `FOR KEY SHARE` sobre la fila del usuario y del turno; es compatible con otros `KEY SHARE` y con los `UPDATE` que no tocan claves (desactivar usuario, rehash del login), así que no agrega esperas ni riesgo de deadlock nuevo. El turno ya está bloqueado `FOR UPDATE` por la propia transacción en reprogramar y cancelar.

### 6. Endpoint de consulta (D1, D7, D8)
- `GET /turnos/{turno_id}/auditoria` → `200` con `list[RegistroAuditoriaOut]` (`id`, `accion`, `usuario_id`, `ocurrido_en`, `valores_previos: InstantaneaTurnoOut | None`, `valores_nuevos: InstantaneaTurnoOut`), orden por `id`.
- Orden de evaluación: autenticación (`401 no_autenticado`) y rol (`403 rol_insuficiente`) en la dependencia, antes que la validación del path (`422`) y la existencia (`404 turno_inexistente`), mismo criterio que el requisito "Operaciones sobre turnos reservadas a la recepcionista".
- Turno existente sin registros → `200 []` (turnos previos a C-07, sin backfill).
- Métodos de escritura sobre la ruta → `405` (no se declaran).

## Risks / Trade-offs

- [La auditoría es opcional a nivel de caso de uso: un caso de uso armado sin el auditor no audita] → Las tres fábricas de la API, único camino de entrada, la registran siempre, y los tests de API verifican un registro por acción. Si en el futuro aparece otro punto de entrada (CLI, worker), debe registrar el auditor; queda anotado en el docstring de los observadores.
- [Un superusuario o el dueño de la tabla puede deshabilitar el trigger (`ALTER TABLE ... DISABLE TRIGGER`)] → Limitación aceptada del MVP: la aplicación se conecta como dueña. Separar un rol de aplicación sin privilegios de DDL queda en el backlog (`CHANGES.md`).
- [Los fixtures de concurrencia limpian con `DELETE FROM turno`; si un test commiteado generara auditoría, la FK `RESTRICT` y el trigger impedirían limpiar] → Esos tests construyen los casos de uso sin auditor y siguen igual. Por eso no se agrega un test de concurrencia de auditoría: la serialización ya está probada (C-04, C-05) y el registro vive en la misma transacción. Si más adelante hiciera falta, la limpieza tendría que usar una base scratch descartable.
- [Bloquear `TRUNCATE` impide vaciar la tabla en mantenimiento o en una base de desarrollo] → Para reiniciar una base de desarrollo se usa `alembic downgrade`/`DROP` (no disparan el trigger). Si el usuario prefiere no bloquear `TRUNCATE`, se quita ese trigger y su escenario.
- [`id bigint` rompe la uniformidad de ids `uuid`] → Solo en esta tabla, que es un log interno; el `id` del registro no se usa como referencia desde otra tabla.
- [`compare_metadata` puede reportar diferencias por la columna `Identity`] → El modelo declara `Identity(always=True)` igual que la migración; `test_modelos_vs_migracion.py` lo verifica.
- [Conflicto de numeración con C-08] → Regla de renumerar del equipo; el test de `head` falla si quedan dos cabezas.

## Migration Plan

1. `alembic upgrade head` aplica `005` (tabla vacía, sin backfill). Los turnos existentes no se tocan.
2. Rollback: `alembic downgrade 004` borra triggers, función y tabla. Se pierde el historial de auditoría registrado, por lo que en un entorno real solo se haría antes de tener datos productivos.

## Open Questions

Ninguna. La pregunta sobre reprogramaciones sin cambio efectivo quedó resuelta como D10. D1, D2, D3, D5, D6 (alcance de `TRUNCATE`) y D8 ya fueron aprobadas por el usuario. Si cambia alguna, se ajustan el spec y las tareas con `/opsx:update` antes de implementar.
