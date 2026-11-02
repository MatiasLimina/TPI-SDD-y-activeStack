# Design

## Context

Ver `proposal.md` (Why, Non-goals) y los delta specs `gestion-recursos` y `catalogo-consultorio`. Estado actual del código (C-01..C-07 archivados):

- **Modelos** (`backend/app/infrastructure/db/models/`): `Profesional` (`nombre` 100, `apellido` 100, `matricula` 30 nullable y `UNIQUE`, `activo`), `Sillon` (`nombre` 50 `UNIQUE`, `activo`) y `Prestacion` (`nombre` 100 `UNIQUE`, `duracion_min` con `CHECK > 0`, `requiere_sillon` default `true`, **`activa`**). Todos con `CatalogoMixin` (`id uuid` con `gen_random_uuid()`, `creado_en`, `actualizado_en`). Convención de nombres en `base.py` (`uq_%(table_name)s_%(column_0_name)s`, `ck_%(table_name)s_%(constraint_name)s`). No existe ninguna ruta sobre estas tablas: solo las llena el seed.
- **Validación de turnos** (`app/domain/turnos.py`): `validar_duracion_y_grilla` valida a la vez la duración (`GRILLA_MIN = 5`, `DURACION_MAX_MIN = 480`) y la alineación del inicio, y lanza `TurnoInvalidoError("duracion_invalida", ...)`. `TurnoIn` no pone restricciones de rango en Pydantic a propósito: "una sola fuente de la regla".
- **Referencias activas**: `RepositorioTurnos.cargar_referencias` hace `session.get` de profesional, paciente, prestación y sillón, y lanza `ReferenciaInvalidaError(nombre, "inexistente" | "inactiva")` → `422 referencia_invalida`. Lo usan alta y reprogramación (vía `validacion_turno.py`); la cancelación no carga referencias. Hoy **no toma lock** sobre esas filas: el `INSERT` del turno toma `FOR KEY SHARE` por las FKs, que no choca con un `UPDATE ... SET activo = false` (`FOR NO KEY UPDATE`).
- **RBAC** (`app/api/auth.py`): `requiere_rol(*roles)` relee el rol de la base; `RecepcionistaAutenticada` está definido en `app/api/turnos.py` y lo importa `app/api/auditoria.py`. `401 no_autenticado` y `403 rol_insuficiente` con manejadores propios. FastAPI resuelve las dependencias antes que path y body (comentario en `crear_turno`).
- **Contrato de errores**: `{"detail": {"codigo": ..., ...}}` para errores de dominio; los errores de tipo de Pydantic usan el `422` por defecto de FastAPI (`{"detail": [...]}`), igual que hoy en turnos.
- **Migraciones**: `001..005`, lineales y numeradas a mano (DD-17). `test_migrations.py` afirma `head == "005"`. Seed de desarrollo: Consulta 30 min, Limpieza 45, Conservadora 60 (todas válidas para la grilla).
- **Tests**: `db_session` en transacción externa que se revierte; fixtures `recepcionista`, `odontologo` (con su profesional), `client`/`cliente_anonimo`, `token_de`; concurrencia con `motor_concurrente` y `catalogo_commiteado` (commitean de verdad y limpian con `DELETE`).

## Goals / Non-Goals

**Goals:**
- Una sola fuente para la regla de duración (DD-15), compartida por turnos y prestaciones, y la base como última garantía (CHECK).
- Tres recursos con el **mismo** contrato HTTP y una implementación sin triplicar lógica, pero con schemas explícitos por recurso (OpenAPI legible).
- La regla "desactivado no admite turnos nuevos" garantizada también bajo concurrencia, sin cambiar el contrato de `agenda-turnos`.
- Suite existente en verde durante todo el change; el refactor de la duración queda protegido por los tests de C-03/C-05.

**Non-Goals:**
- Paginación, filtros, búsqueda u ordenamientos configurables en los listados.
- Auditoría del catálogo y cambios en el usuario `odontologo` vinculado a un profesional (ver D11 y D12).
- Rol de base de datos de mínimo privilegio (ya está en el backlog).

## Decisions

D5, D6, D7, D9 (matrícula vacía), D11 y D12 no las fija la KB: se propusieron en este change y el usuario las confirmó tal cual el 2026-11-02. Se registran como **DD-26** en `knowledge-base/09_decisiones_y_supuestos.md` en la tarea 10.1, igual que DD-25 en C-07.

| Id | Decisión | Fuente |
|---|---|---|
| D1 | Rutas por recurso: `GET` (listado y detalle), `POST` (alta), `PATCH /{id}` (edición parcial), `POST /{id}/desactivar` | `CHANGES.md` §C-08, `02_descripcion_general.md`; acción explícita igual que `POST /turnos/{id}/cancelar` |
| D2 | Duración validada en el dominio con `422 duracion_invalida`, no con `Field(multiple_of=5, le=480)` de Pydantic | C-03 ("una sola fuente de la regla"); Context7 C7-1 |
| D3 | CHECK nuevos `ck_prestacion_duracion_min_multiplo_5` (`mod(duracion_min, 5) = 0`) y `ck_prestacion_duracion_min_maxima` (`duracion_min <= 480`); el `> 0` de C-02 sigue | DD-15; Context7 C7-2 |
| D4 | `PATCH` parcial con `model_fields_set`: omitido conserva, `null` en obligatorio → `422`, `matricula: null` quita | DD-23 (mismo criterio que reprogramar); Context7 C7-3 |
| D5 | Desactivar un recurso ya inactivo → `200` sin cambios (idempotente) | **Confirmada por el usuario (2026-11-02)** (análogo a la desactivación idempotente del CLI de usuarios, DD-24 h) |
| D6 | Sin reactivación: `activo`/`activa` en el body de alta o edición → `422 campo_no_editable` | **Confirmada por el usuario (2026-11-02)** (US-001 solo pide alta, edición y desactivación; DD-24 j tampoco reactiva usuarios; no ignorar en silencio, DD-23) |
| D7 | Duplicado de nombre de sillón, nombre de prestación o matrícula → `409 recurso_duplicado` con `campo` | **Confirmada por el usuario (2026-11-02)** (la KB fija la unicidad en la base pero no el código HTTP; `409` es el código de conflicto del proyecto) |
| D8 | Path inexistente → `404 recurso_inexistente` con `recurso`; id mal formado → `422` | DD-21 (`404` solo para recursos del path) |
| D9 | Textos sin espacios extremos; `nombre`/`apellido` no vacíos; `matricula` vacía → `null` | Atributos obligatorios de `catalogo-consultorio`; matrícula vacía como `null`: **Confirmada por el usuario (2026-11-02)** (dos `""` chocarían en el `UNIQUE`) |
| D10 | `cargar_referencias` lee las referencias con `FOR SHARE` | Requisito "Desactivación simultánea con un alta o una reprogramación de turno"; Context7 C7-4 |
| D11 | Desactivar un recurso con turnos futuros **se permite**: los turnos no cambian y se pueden cancelar | **Confirmada por el usuario (2026-11-02)** (US-001: "conserva su historial"; la KB no pide bloquear ni advertir, a diferencia de los bloqueos, DD-12) |
| D12 | Desactivar un profesional no toca a su usuario `odontologo` | **Confirmada por el usuario (2026-11-02)** (la KB no lo fija; DD-24 h solo impide dar de alta un usuario para un profesional inactivo) |
| D13 | Listados completos (activos e inactivos) con orden fijo: profesionales por `apellido, nombre, id`; sillones y prestaciones por `nombre` | Volúmenes de `02` (1-5 profesionales, 1-4 sillones); orden determinístico para los tests |
| D14 | Lectura para ambos roles, sin restringir al odontólogo a "lo propio" | Matriz de `03` (R en los tres recursos) y US-001; RN-AU-02 restringe la agenda, no el catálogo |

### 1. Capas y módulos
- `app/domain/grilla.py` (nuevo, puro): `GRILLA_MIN`, `DURACION_MAX_MIN`, `MENSAJE_DURACION_INVALIDA` y `duracion_en_grilla(duracion_min: int) -> bool`. `app/domain/turnos.py` la usa dentro de `validar_duracion_y_grilla` y re-exporta las constantes (los imports actuales no cambian).
- `app/domain/recursos.py` (nuevo, puro): `TipoRecurso` (`StrEnum`: `profesional`, `sillon`, `prestacion`); errores `RecursoInvalidoError(codigo, mensaje)` (422), `RecursoInexistenteError(tipo)` (404), `RecursoDuplicadoError(tipo, campo)` (409), `EstadoNoEditableError(campos)` (422 `campo_no_editable`); `validar_duracion_prestacion(duracion_min)` (lanza `duracion_invalida` con el mismo mensaje que turnos) y `normalizar_matricula(valor) -> str | None`.
- `app/infrastructure/db/repositorio_recursos.py` (nuevo): `RepositorioRecursos[M](session, definicion)` con `listar()`, `obtener(id)`, `obtener_para_actualizar(id)` (`with_for_update=True`), `agregar(entidad)` y `guardar()` (`flush` que traduce `IntegrityError` `23505` por `diag.constraint_name` → `RecursoDuplicadoError`), más `commit`/`rollback`. La `DefinicionRecurso` reúne modelo, `TipoRecurso`, nombre del flag (`activo`/`activa`), orden y el mapa `uq_sillon_nombre → nombre`, `uq_prestacion_nombre → nombre`, `uq_profesional_matricula → matricula`.
- `app/application/gestion_recursos.py` (nuevo): casos de uso `CrearRecurso`, `EditarRecurso`, `DesactivarRecurso`, `ConsultarRecursos`, genéricos sobre la definición, con una función de validación por recurso (solo la prestación valida duración). Cada escritura hace `commit` al final y `rollback` ante error, igual que los casos de uso de turnos.
- `app/api/recursos.py` (nuevo): tres `APIRouter` (`/profesionales`, `/sillones`, `/prestaciones`) armados por una función común, con schemas explícitos por recurso (`ProfesionalIn`, `ProfesionalCambios`, `ProfesionalOut`, etc.) y `registrar_manejadores_recursos(app)`. Registrados en `main.py`.
- `app/api/auth.py`: se mudan ahí los alias `RecepcionistaAutenticada` y nuevo `UsuarioDeAmbosRoles` (`requiere_rol(Rol.RECEPCIONISTA, Rol.ODONTOLOGO)`); `turnos.py` y `auditoria.py` los importan desde `auth`. Un alias por módulo, definido una sola vez, para que FastAPI cachee la dependencia por request.
- Alternativa descartada: un módulo y una clase de caso de uso por recurso (tres copias casi idénticas de alta, edición, desactivación y traducción de duplicados). Alternativa descartada: un router genérico `/{recurso}` (OpenAPI ilegible y schemas sin tipar).

### 2. Schemas y validación (D2, D4, D6, D9)
- Textos: `Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=N)]` con el largo de cada columna (100/100/50/100); `matricula`: `str | None` con un `BeforeValidator` que recorta y convierte `""` en `None`, `max_length=30`. Un texto vacío o demasiado largo da el `422` por defecto de FastAPI, como cualquier error de tipo; así ningún valor llega a la base para fallar como `500`.
- `duracion_min: int` sin restricciones en el schema; la regla vive en el dominio (D2). Pydantic en modo laxo acepta `45.0` como `45` y rechaza `45.5` (`int_from_float`, C7-1), igual que hoy en `TurnoIn`.
- Estado de actividad (D6): los schemas de alta y edición declaran `activo` (o `activa`) como `JsonValue = None` solo para detectar su presencia en `model_fields_set`, igual que `paciente_id`/`prestacion_id` en `ReprogramacionIn`; si está, `EstadoNoEditableError` → `422 {"codigo": "campo_no_editable", "campos": [...], "mensaje": "El estado de actividad no se edita: para dar de baja usá /desactivar"}`.
- `PATCH` (D4): un `model_validator(mode="after")` rechaza `null` en `nombre`, `apellido`, `duracion_min` y `requiere_sillon`; el caso de uso recibe solo los campos de `model_fields_set` (equivalente a `model_dump(exclude_unset=True)`, C7-3). Campos desconocidos: ignorados (`extra` por defecto), mismo criterio que reprogramar.
- **Orden de evaluación** en escrituras: `401` → `403` (dependencia) → `422` de path y de body (Pydantic, `campo_no_editable`, `duracion_invalida`: no necesitan leer la base) → `404` → `409` (al hacer `flush`). Así un body inválido sobre un id inexistente da `422`, sin leer la base.
- Alternativa descartada (D2): `Field(gt=0, multiple_of=5, le=480)`. Produce errores `greater_than`/`multiple_of`/`less_than_equal` en la lista por defecto de FastAPI, no el `duracion_invalida` que ya devuelven los turnos, y duplica la regla en dos lugares.

### 3. Migración `006_prestacion_duracion_grilla.py` (D3)
- `upgrade`: `op.create_check_constraint(op.f("ck_prestacion_duracion_min_multiplo_5"), "prestacion", "mod(duracion_min, 5) = 0")` y `op.create_check_constraint(op.f("ck_prestacion_duracion_min_maxima"), "prestacion", "duracion_min <= 480")`. `downgrade`: `op.drop_constraint(op.f(...), "prestacion", type_="check")` de ambos.
- `op.f()` con el nombre completo, como en `002..005`: con la convención `ck_%(table_name)s_%(constraint_name)s` un nombre sin `op.f()` se prefijaría otra vez (C7-2).
- `mod(...)` en vez de `%`: evita que el `%` del texto SQL se interprete como marcador de parámetro del driver al emitir el DDL.
- El modelo `Prestacion` declara los mismos `CheckConstraint(..., name="duracion_min_multiplo_5")` y `name="duracion_min_maxima"`. Como `compare_metadata` no compara CHECKs, `test_migracion_006.py` verifica en `pg_constraint` nombre y definición.
- Dos CHECK en vez de uno: el nombre de la restricción violada dice cuál de las dos reglas falló.
- `ADD CONSTRAINT ... CHECK` valida las filas existentes con un lock `ACCESS EXCLUSIVE` breve; la tabla tiene decenas de filas, así que no hace falta `NOT VALID` + `VALIDATE`.
- **Numeración**: `revision = "006"`, `down_revision = "005"`. C-12 (Nico) puede crear otra `006`: quien mergea segundo renumera su revisión y el test de `head` (tarea 10.2).

### 4. Desactivación y turnos (D5, D10, D11)
- `DesactivarRecurso`: `obtener_para_actualizar` (`SELECT ... FOR UPDATE`); si ya está inactivo, devuelve sin escribir (no cambia `actualizado_en`); si no, pone el flag en `false` y confirma.
- No se toca `turno`: la regla "no admite turnos nuevos" ya la aplica `cargar_referencias` en alta y reprogramación. La cancelación no carga referencias, así que un turno con un recurso inactivo se sigue cancelando (escenario de `gestion-recursos`).
- **Serialización (D10)**: `cargar_referencias` pasa a usar `session.get(modelo, id, with_for_update={"read": True}, populate_existing=True)` (`SELECT ... FOR SHARE`, C7-4). `FOR SHARE` choca con el `FOR NO KEY UPDATE` del `UPDATE` de la desactivación: si la desactivación está en curso, el alta espera y, en `READ COMMITTED`, relee la fila ya confirmada (`activo = false` → `422`); si el alta está en curso, la desactivación espera a que confirme. `populate_existing` evita que el identity map devuelva una versión vieja del objeto. Dos altas simultáneas toman `FOR SHARE` compatibles entre sí: no se serializan entre ellas más que hoy. La reprogramación pasa por el mismo `cargar_referencias`, así que queda serializada con la desactivación de la misma forma (escenario propio en `gestion-recursos`).
- **Test de la espera de la desactivación**: el alta se detiene después de `cargar_referencias` y antes del `INSERT` del turno. Después del `INSERT`, el `FOR KEY SHARE` de la FK ya choca con el `FOR UPDATE` de `obtener_para_actualizar` y la desactivación esperaría también sin `FOR SHARE`; antes del `INSERT`, la única fila bloqueada es la del `FOR SHARE`, así que el test falla sin el cambio (RED real).
- Locks: cada desactivación bloquea una sola fila; el alta bloquea sus referencias siempre en el mismo orden (profesional, paciente, prestación, sillón). No se forma un ciclo, así que no se agrega riesgo de deadlock. La reprogramación ya tiene el turno `FOR UPDATE` antes de cargar referencias, sin cambios en ese orden.
- Alternativa descartada: no serializar y aceptar la carrera (un turno creado milisegundos después de confirmada la baja contradice US-001). Alternativa descartada: `SERIALIZABLE` en el alta (reintentos y errores de serialización en todo el camino de C-03 por un caso raro).

### 5. Lectura y acceso (D13, D14)
- `GET` lista con `ORDER BY` fijo; detalle con `obtener`. Respuestas: profesional `{id, nombre, apellido, matricula, activo}`, sillón `{id, nombre, activo}`, prestación `{id, nombre, duracion_min, requiere_sillon, activa}`. Sin marcas de tiempo (no las pide la KB).
- Los nombres `activo`/`activa` siguen la KB (`04_modelo_de_datos.md`) y la columna real; no se unifican.
- Lecturas con `UsuarioDeAmbosRoles`; escrituras con `RecepcionistaAutenticada`. Métodos no declarados (`PUT`, `DELETE`) → `405` de FastAPI.

### 6. Consultas a Context7
Preguntas genéricas, sin código ni datos del proyecto. Detalle en `docs/skills-mcp/evidencias/c-08/explore-context7.md`.

| Id | Biblioteca | Pregunta (resumen) | Decisión que respalda |
|---|---|---|---|
| C7-1 | Pydantic (`/websites/pydantic_dev_validation`) | Restricciones `gt`/`le`/`multiple_of` para enteros, tipo de error que producen y conversión de `float` a `int` | D2 y §2: no usar `Field(multiple_of, le)`, porque cambiaría la forma del `422`; `45.0` se acepta y `45.5` se rechaza |
| C7-2 | Alembic (`/websites/alembic_sqlalchemy`) | `op.create_check_constraint`, `op.drop_constraint(type_="check")` y cómo aplica la convención de nombres con `op.f()` | D3 y §3: nombres completos con `op.f()` en `upgrade` y `downgrade` |
| C7-3 | FastAPI (`/websites/fastapi_tiangolo`) | `PATCH` parcial con `model_dump(exclude_unset=True)` y diferencia entre `null` explícito y campo omitido | D4 y §2: campos de `model_fields_set`, `null` validado aparte; la nota de la versión 0.151.0 obliga a verificar la versión instalada (ver Risks) |
| C7-4 | SQLAlchemy (`/websites/sqlalchemy_en_20_orm`) | `Session.get` con `with_for_update` (lectura compartida) y `populate_existing` | D10 y §4: `FOR SHARE` con relectura forzada en `cargar_referencias` |

## Risks / Trade-offs

- [`FOR SHARE` en `cargar_referencias` toca el camino crítico de C-03/C-05] → Cambio de una línea por referencia; los tests de concurrencia de alta y reprogramación (C-03..C-05) se corren en la tarea 8.1 como red de seguridad, más tres tests nuevos de concurrencia con la desactivación (alta que espera, desactivación que espera y reprogramación que espera).
- [Una `PATCH` de prestación también toma `FOR UPDATE` y hace esperar a las altas que la referencian] → Esperas de milisegundos en un consultorio chico; es el precio de que el alta vea siempre la prestación confirmada.
- [Desactivar una prestación o un paciente deja sus turnos futuros sin reprogramar posible: paciente y prestación no son editables (DD-23) y la validación de reprogramar exige referencias activas] → Comportamiento ya vigente de `agenda-turnos`; el turno se puede cancelar. Aceptado por el usuario al confirmar D11 (2026-11-02); queda registrado en DD-26.
- [Cambiar `requiere_sillon` de una prestación con turnos futuros hace que reprogramarlos aplique la regla nueva (puede dar `422 sillon_requerido` o `sillon_no_corresponde`)] → Comportamiento vigente de la reprogramación (valida contra la prestación actual); queda documentado y se registra en DD-26.
- [FastAPI 0.151.0 cambió cómo distingue `null` de omitido en parámetros `Body` sueltos (C7-3)] → El change usa modelos Pydantic y `model_fields_set`, que no dependen de ese cambio; igual, el test de `null` explícito de la tarea 6.5 lo cubre con la versión instalada.
- [Unicidad exacta: "Sillón 1" y "sillón 1" conviven] → Es lo que garantiza hoy el `UNIQUE` de C-02; normalizar mayúsculas o acentos sería una regla nueva sin respaldo en la KB.
- [Conflicto de numeración con C-12] → Regla de renumerar del equipo; `alembic heads` en la verificación final.

## Migration Plan

1. Antes de aplicar en una base con datos: `SELECT id, nombre, duracion_min FROM prestacion WHERE mod(duracion_min, 5) <> 0 OR duracion_min > 480;` debe devolver cero filas (el seed cumple). Si devuelve alguna, se corrige el dato antes; la migración falla en vez de dejar datos inválidos.
2. `alembic upgrade head` aplica `006` (solo agrega dos CHECK).
3. Rollback: `alembic downgrade 005` borra los dos CHECK; el código de la API sigue validando en el dominio.

## Open Questions

Ninguna. D5, D6, D7, D9 (matrícula vacía), D11 y D12 quedaron confirmadas por el usuario el 2026-11-02, tal como se propusieron, así que spec y tareas no cambian. Quedan para el backlog, sin afectar este change: reactivación de recursos (D6) y una advertencia en la UI al desactivar un recurso con turnos futuros (C-14..C-16).
