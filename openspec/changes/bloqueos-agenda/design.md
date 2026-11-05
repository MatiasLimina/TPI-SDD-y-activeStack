# Design

## Context

La motivación y el alcance están en `proposal.md` (Why, Non-goals); los contratos, en los delta specs `bloqueos-agenda` y `agenda-turnos`. Estado actual del código (C-01..C-08, C-10 y C-12 archivados):

- **Validación compartida de turnos** (`app/application/validacion_turno.py`): `validar_solicitud_turno` aplica, en orden fijo, referencias (`cargar_referencias`, que lee profesional, paciente, prestación y sillón con `FOR SHARE`), duración y grilla, inicio futuro, coherencia del sillón, los `validadores` inyectados y el pre-chequeo de solape. `app/api/turnos.py::_validadores` hoy devuelve `[ValidadorHorario(...)]`, y su docstring reserva el lugar siguiente para C-11 (DD-27 l).
- **Efectos laterales del turno**: `CrearTurno` inserta y recién después llama a los observadores `[auditor.al_crear, programador.al_crear]`. `ReprogramarTurno` bloquea el turno (`FOR UPDATE`), valida, actualiza y llama a `[auditor.al_reprogramar, programador.al_reprogramar]`. La ruta llama a `programador.publicar(cola)` después del commit. Un validador que lanza corta antes del `INSERT`/`UPDATE` y antes de los observadores, y la excepción sale de la ruta antes de `publicar`.
- **Errores**: `TurnoInvalidoError(codigo, mensaje)` → `422 {"codigo", "mensaje"}`; `ReferenciaInvalidaError(referencia, motivo)` → `422 referencia_invalida`; `RecursoInexistenteError(TipoRecurso)` → `404 recurso_inexistente`; `ProfesionalAjenoError` → `403 profesional_ajeno`, hoy sin argumentos y con el mensaje fijo del horario ("Solo podés consultar tu propio horario").
- **Auth** (C-06): `UsuarioAutenticado(id, rol, profesional_id)` releído de la base en cada request; alias `RecepcionistaAutenticada` y `UsuarioDeAmbosRoles`. No hay ningún endpoint que fuerce `profesional_id` desde el token en un body: C-10 solo lo compara en un path (`ConsultarHorarios`).
- **Concurrencia de C-10** (DD-27 k): las escrituras de franjas toman `FOR NO KEY UPDATE` sobre la fila del profesional (`RepositorioHorarios.bloquear_profesional`), que choca con el `FOR SHARE` de `cargar_referencias`.
- **Base**: migraciones `001..009` lineales y numeradas a mano; `btree_gist` en `001`; `main` en `009`. La exclusión `turno_sin_solape_profesional` indexa `(profesional_id, tstzrange(inicio, fin, '[)'))` con un GiST que sirve para buscar turnos activos de un profesional en un intervalo.
- **Tests**: `crear_catalogo(session, con_horario=True)` da franjas 00:00-23:55 todos los días; `catalogo_commiteado` y `motor_concurrente` para concurrencia (patrón de `test_concurrencia_horarios.py`); reloj fijo 2026-10-07 09:00 local.

## Goals / Non-Goals

**Goals:**
- RN-AG-06 enchufada como segundo `ValidadorTurno`, sin cambiar el orden ni el código de las validaciones existentes.
- RN-HB-03 sin carreras: entre un alta de bloqueo y un alta o reprogramación de turno del mismo profesional, nunca quedan los dos.
- La base como garantía de la forma del bloqueo (`fin > inicio`, motivo no vacío, autor obligatorio).
- Cero cambios en recordatorios y auditoría (C-12, C-07).

**Non-Goals:**
- Consultas por rango y agenda combinada de turnos y bloqueos (C-13 reutilizará el repositorio de este change).
- Garantía en la base contra un turno escrito por SQL directo dentro de un bloqueo (ver D13).

## Decisions

D1-D9 y D11-D13 no las fija la KB. El usuario las **aprobó el 2026-11-04** (governance MEDIO) con la opción recomendada, salvo **D12**, donde eligió que el odontólogo reciba `403` antes de la existencia del bloqueo, alineado con DD-27 (i). Los specs y las tareas están escritos con lo aprobado. Todas se registran como **DD-30** (tarea 9.1).

| Id | Decisión | Fuente / estado |
|---|---|---|
| D1 | `profesional_id` opcional en `POST /bloqueos`: el odontólogo lo omite (se usa el suyo) o informa el suyo; uno distinto → `403 profesional_ajeno`. La recepcionista debe informarlo → `422 profesional_requerido` | **Aprobada** (2026-11-04). Flujo 5 ("la API fuerza `profesional_id`"), RN-HB-02 |
| D2 | Bloqueos superpuestos del mismo profesional **permitidos**, sin restricción de exclusión | **Aprobada** (2026-11-04). La KB no lo dice |
| D3 | Sin edición: no hay `PATCH` ni `PUT`; para cambiar un bloqueo se borra y se crea otro | **Aprobada** (2026-11-04). `CHANGES.md` pide `POST`/`GET`/`DELETE`; la matriz de `03` dice "CRUD" para la recepcionista |
| D4 | Sin `sillon_id`: la **Suposición** de `04` (bloqueo por sillón) no se implementa y pasa al backlog | **Aprobada** (2026-11-04). `CHANGES.md` §C-11 no lista el campo |
| D5 | Sin restricción temporal: se pueden crear y borrar bloqueos pasados | **Aprobada** (2026-11-04). RN-AG-12 es de turnos |
| D6 | Sin grilla de 5 minutos para el bloqueo | **Aprobada** (2026-11-04). DD-15 y DD-27 c alinean turnos y franjas, no bloqueos |
| D7 | `motivo` obligatorio, sin espacios en los extremos, no vacío y de a lo sumo 255 caracteres medidos ya recortado; `fin > inicio`. Violación → `422 bloqueo_invalido` (el largo, por el `422` de Pydantic), con CHECKs en la base | **Aprobada** (2026-11-04), el largo incluido. RN-HB-02 ("con motivo"), `04` ("texto corto", `fin > inicio`) |
| D8 | Se permiten bloqueos de un profesional desactivado | **Aprobada** (2026-11-04). Análogo a DD-27 j |
| D9 | `409 bloqueo_con_turnos` con `turnos: [{id, inicio, fin}]` en hora local, ordenados por `inicio` (y `id`), sin datos del paciente | **Aprobada** (2026-11-04), los campos incluidos. RN-HB-03, DD-12 |
| D10 | RN-AG-06 como `ValidadorTurno` después del de horario: `422 turno_en_bloqueo` vía `TurnoInvalidoError`, sin exponer el bloqueo ni su motivo | DD-27 l, `02` ("dentro de bloqueo → 422"), Flujo 2 |
| D11 | `GET /bloqueos?profesional_id=` (opcional): la recepcionista ve todos o los filtrados (un inexistente da `[]`); el odontólogo, solo los suyos (otro → `403`). Sin `desde`/`hasta` ni `GET` de detalle | **Aprobada** (2026-11-04). `CHANGES.md` pide `GET`; los rangos son de C-13 |
| D12 | `DELETE /bloqueos/{id}` físico (`204`). "Propios" significa del profesional del odontólogo, no "creados por él". Para el odontólogo, `403` antes de la existencia: un bloqueo ajeno o inexistente → `403 profesional_ajeno`; para la recepcionista, inexistente → `404` | **Aprobada con cambio** (2026-11-04): `403` primero, como DD-27 i. Matriz de `03` ("CRD solo propios") |
| D13 | Concurrencia: toda escritura de bloqueos toma `FOR NO KEY UPDATE` sobre el profesional; los turnos ya lo leen con `FOR SHARE`. Sin trigger ni restricción entre tablas. Test de concurrencia obligatorio | **Aprobada** (2026-11-04). `08` §Concurrencia (alternativa 2), DD-27 k |
| D14 | Tabla `bloqueo` en la migración **`010`** (`down_revision = "009"`): CHECKs, FK a `profesional` `ON DELETE CASCADE`, `creado_por` `NOT NULL` con FK a `usuario` `RESTRICT`, índice `(profesional_id, inicio)` | Diseño. `04` §Bloqueo, DD-17 |
| D15 | `ProfesionalAjenoError(mensaje)` con el del horario por defecto; para bloqueos: "Solo podés operar sobre tus propios bloqueos" | Diseño. Reusa el código de DD-27 i |
| D16 | Sin auditoría de bloqueos y sin cambios en recordatorios | RN-CU-01 (audita turnos); RN-HB-03 (nunca hay turnos que mover) |

### D1 — Profesional del bloqueo según el rol
- **Elegida**: `profesional_id: UUID | None` en el body. Si el rol es `odontologo` y viene omitido, se usa `usuario.profesional_id`; si viene igual, también; si viene distinto, `403 profesional_ajeno` (evaluado antes que la existencia del profesional y que la forma del bloqueo, como en DD-27 i). Si el rol es `recepcionista` y viene omitido → `422 profesional_requerido`. Así se cumple el Flujo 5 ("la API fuerza") y nunca se ignora un dato del cliente en silencio (el antipatrón del sillón sobrante, DD-21).
- **Alternativa**: ignorar el `profesional_id` del odontólogo y usar siempre el del token. Es la lectura más literal de "fuerza", pero el cliente puede creer que bloqueó a otro profesional.
- **Alternativa**: `profesional_id` obligatorio para ambos roles (el odontólogo manda el suyo). Más simple de validar, pero contradice el "fuerza" del Flujo 5.

### D2 — Bloqueos superpuestos
- **Elegida**: permitirlos. La KB no tiene una regla que los prohíba y no rompen ninguna invariante: un turno se valida contra **cualquier** bloqueo del profesional. El caso real es que la recepción bloquee el día entero (feriado) y el odontólogo ya tenga un trámite de una hora; obligar a borrar uno para crear el otro pierde el motivo. Borrar uno deja vigente al otro.
- **Alternativa**: `409 bloqueo_superpuesto` con `EXCLUDE USING gist (profesional_id WITH =, tstzrange(inicio, fin, '[)') WITH &&)` (como `horario_atencion_sin_superposicion`, D5 de C-10). Da garantía en la base para ese caso, pero agrega una regla sin respaldo en la KB y un código nuevo.
- **Alternativa**: fusionar bloqueos superpuestos al crearlos. Pierde motivos y complica el borrado.

### D3 — Sin edición
- **Elegida**: no exponer `PATCH`. `CHANGES.md` y `02` listan `POST`/`DELETE` (más `GET` en `CHANGES.md`), y un `PATCH` obligaría a revalidar RN-HB-03 sobre el intervalo nuevo, con los mismos locks. Borrar y crear cubre el caso con dos requests. Consecuencia: la tarea de KB precisa la fila "Bloqueos de agenda" de la matriz de `03` como `CRD` para ambos roles (inconsistencia detectada: la matriz dice `CRUD (todos)`).
- **Alternativa**: `PATCH /bloqueos/{id}` parcial (con `409 bloqueo_con_turnos` sobre el intervalo resultante). Suma un requisito y unas 6 tareas.

### D4 — Bloqueo por sillón
- **Elegida**: fuera de alcance. Es una **Suposición** de `04` ("opcionalmente por sillón para mantenimiento") que el scope de C-11 no incluye. Para validarla habría que cruzar bloqueos con el sillón del turno y definir quién la crea. Se agrega al backlog de `CHANGES.md` y la entidad de `04` lo aclara.
- **Alternativa**: `sillon_id` nullable desde ahora, sin efecto en la validación. Agrega un campo que nadie consume.

### D5 — Bloqueos en el pasado
- **Elegida**: sin restricción. No hay regla en la KB y un bloqueo pasado no afecta a ningún turno nuevo (RN-AG-12 ya impide turnos en el pasado). Consecuencia aceptada: RN-HB-03 cuenta todos los turnos activos, también los que ya ocurrieron (el MVP no tiene estado "atendido"). Un bloqueo retroactivo sobre un turno pasado da `409`, y ese turno ya no se puede cancelar ni reprogramar (RN-AG-13, DD-23 d). Se documenta, no se agrega lógica y lo fija el escenario "Bloqueo retroactivo sobre un turno pasado".
- **Alternativa**: `422` si `fin <= ahora` (o si `inicio < ahora`). Es una regla nueva y obliga a inyectar el reloj en el alta.

### D6 — Grilla del bloqueo
- **Elegida**: no exigirla. Un bloqueo 10:03-10:07 bloquea igual los turnos 10:00-10:05 y 10:05-10:10 con el criterio `[)`; no hay capacidad que proteger ni regla en la KB. Lo fija el escenario "Bloqueo fuera de la grilla de 5 minutos".
- **Alternativa**: grilla de 5 minutos en hora local (como DD-15 y DD-27 c), con CHECK. Coherente con turnos y franjas, pero agrega una regla.

### D7 — Forma del bloqueo
- **Elegida**: un solo código de dominio `bloqueo_invalido` para `fin <= inicio` y para un motivo vacío tras quitar los espacios extremos (mismo criterio que `franja_invalida`), validado en el dominio (`app/domain/bloqueos.py`) y respaldado por `ck_bloqueo_fin_mayor` (`fin > inicio`) y `ck_bloqueo_motivo_no_vacio` (`btrim(motivo) <> ''`). `motivo varchar(255)`, el mismo largo que `motivo_cancelacion` del turno. El largo se mide sobre el texto ya recortado, que es lo que se guarda: `Annotated[str, StringConstraints(strip_whitespace=True, max_length=255)]`, como los nombres de `app/api/recursos.py` (C-08), da el `422` por defecto; sin `min_length`, para que el motivo vacío llegue al dominio y dé `bloqueo_invalido`. Así "  " + 255 letras se acepta y 256 letras se rechazan (escenario "Motivo de 255 caracteres"). Los datetimes con `AwareDatetime` (`422` sin zona, `datetime-handling`), y se guardan con `to_utc`.
- **Alternativa**: códigos separados (`intervalo_invalido`, `motivo_vacio`) o un largo menor (100). Cambia solo el contrato del error.

### D8 — Profesional desactivado
- **Elegida**: permitir, como las franjas (DD-27 j). Sus turnos nuevos ya se rechazan por `referencia_invalida` y no hay reactivación (DD-26 d), así que el bloqueo no tiene efecto. El repositorio busca el profesional sin filtrar por `activo`.
- **Alternativa**: `422 referencia_invalida` con `motivo = "inactiva"` (como los turnos).

### D9 — Cuerpo del `409`
- **Elegida**: `{"detail": {"codigo": "bloqueo_con_turnos", "mensaje": "...", "turnos": [{"id", "inicio", "fin"}]}}`, con instantes en hora local como `TurnoOut`. El `id` alcanza para que la recepción reprograme o cancele cada turno (US-003 pide "informa los turnos afectados"). No incluye paciente ni prestación: el odontólogo también puede recibir este `409` y la respuesta no necesita datos de salud. Sí ve los ids de sus propios turnos (matriz: "R solo propios").
- **Alternativa**: incluir `paciente_id`, `prestacion_id` y `sillon_id` (más cómodo para la UI de C-15, que igual puede pedir el detalle).

### D10 — Validador de bloqueos
- `ValidadorBloqueos(repositorio)`: `__call__(propuesto)` busca bloqueos del `propuesto.profesional_id` con `inicio < propuesto.fin AND fin > propuesto.inicio` (la consulta de solape `[)`, RN-AG-03) y, si hay alguno, lanza `TurnoInvalidoError("turno_en_bloqueo", MENSAJE_TURNO_EN_BLOQUEO)`. Va **después** de `ValidadorHorario` en `_validadores`, como dejó escrito DD-27 l. Consecuencias ya especificadas: fuera de horario y en bloqueo → `fuera_de_horario`; en bloqueo y en solape → `422`, no `409` (las validaciones de `422` van antes del solape, RN-AG-08).
- No expone el bloqueo (ni su `id` ni su motivo) en el `422`: el motivo puede ser personal del profesional y el cuerpo mantiene la forma `{codigo, mensaje}` de los demás `TurnoInvalidoError`. C-13 mostrará los bloqueos en la agenda.
- Al reprogramar, `excluir_id` no aplica: un bloqueo no es un turno. Por la invariante de RN-HB-03, un turno nunca está dentro de un bloqueo, así que reprogramar solo el sillón de un turno existente no puede dar `turno_en_bloqueo` (salvo un turno escrito por SQL directo, D13).

### D11 — Consulta
- **Elegida**: `GET /bloqueos` con `profesional_id: UUID | None = Query(None)`. La recepcionista sin filtro ve todos, y con filtro los de ese profesional (`[]` si no existe: es un filtro, no un recurso del path). El odontólogo sin filtro o con el suyo ve los suyos; con otro → `403 profesional_ajeno`, antes de buscar nada (no revela existencia, DD-27 i). Orden `inicio, id`. Incluye los pasados. Sin paginación (MVP, pocos bloqueos por profesional).
- **Alternativa**: `desde`/`hasta` desde ya. Se superpone con C-13 (`GET /turnos?desde&hasta` "incluye bloqueos"), que define la semántica de rangos locales.
- **Alternativa**: ruta anidada `GET /profesionales/{id}/bloqueos` (como horarios). `CHANGES.md` y `02` usan `/bloqueos`.

### D12 — Borrado
- **Elegida**: borrado físico (`204`), como las franjas (D9 de C-10): nada referencia a `bloqueo` y RN-CU-01 no lo audita. El odontólogo borra cualquier bloqueo de **su profesional**, aunque lo haya creado la recepción: la matriz habla de bloqueos "propios", y el bloqueo es de la agenda del profesional.
- **Orden (cambio del usuario, 2026-11-04)**: `422` de path → lectura del bloqueo → si el rol es `odontologo` y el bloqueo no existe o es de otro profesional, `403 profesional_ajeno` → si el rol es `recepcionista` y no existe, `404 recurso_inexistente` (`recurso = "bloqueo"`). El endpoint nunca le revela al odontólogo si un id existe, con el mismo criterio de DD-27 (i) (`403` antes de la existencia, "existente o no") y del `POST` de este change (D1). Leer el bloqueo sigue siendo necesario para decidir la propiedad, pero la respuesta no distingue los dos casos.
- **Alternativa descartada** (la recomendada original): `404` y después `403`. Revela al odontólogo qué ids existen, y se aparta de DD-27 (i).
- **Alternativa**: el odontólogo solo borra los que creó él (`creado_por`). Una vacación cargada por la recepción no la podría quitar el propio profesional.
- **Alternativa**: `404` también para el bloqueo ajeno (oculta su existencia). Distinto del `403` del resto del change.

### D13 — Concurrencia bloqueo ↔ turno
El conflicto cruza dos tablas (`bloqueo` y `turno`), así que **no hay restricción de exclusión** que lo garantice: una `EXCLUDE` compara filas de la misma tabla. Un trigger tampoco alcanza solo: en `READ COMMITTED` cada transacción no ve las filas no confirmadas de la otra, así que dos triggers "comprobar y luego insertar" tienen la misma carrera.
- **Elegida**: serializar por la fila del profesional, con la alternativa 2 de `08` §Concurrencia, que C-10 ya usa (DD-27 k):
  - `CrearBloqueo` y `BorrarBloqueo` empiezan con `SELECT … FROM profesional WHERE id = :id FOR NO KEY UPDATE`, que también sirve como verificación de existencia (`None` → `422 referencia_invalida` en el alta). Después consultan los turnos activos y el `INSERT` va en la misma transacción.
  - El alta y la reprogramación de turnos ya leen el profesional (el destino, al reprogramar) con `FOR SHARE` en `cargar_referencias`, **antes** de los validadores. `FOR SHARE` y `FOR NO KEY UPDATE` se excluyen.
  - Si el bloqueo toma el lock primero, el turno espera. Cuando el bloqueo confirma, la consulta del `ValidadorBloqueos` (sentencia nueva, snapshot nuevo en `READ COMMITTED`) lo ve → `422`. Si el turno toma el lock primero, el bloqueo espera, y su consulta de turnos ve el turno confirmado → `409`. Dos altas de turno siguen sin bloquearse entre sí (`FOR SHARE` es compartido).
  - Sin deadlocks: el bloqueo toma un solo lock de fila y lee turnos sin lock; la reprogramación toma `turno FOR UPDATE` y luego `profesional FOR SHARE`, y el bloqueo nunca pide el turno.
  - Un turno que se va de A a B mientras se bloquea A: la reprogramación no bloquea A. El bloqueo puede ver el turno todavía en A y responder `409` (conservador) o no verlo. Nunca queda un turno activo dentro del bloqueo.
- **Límite honesto**: la garantía es de la aplicación. Un `INSERT` por SQL directo en `turno` o en `bloqueo` puede violar RN-AG-06/RN-HB-03, a diferencia de los solapes entre turnos (RN-AG-09). Es la misma posición que `08` ("las restricciones de exclusión no cubren horario de atención ni bloqueos").
- **Alternativa**: `pg_advisory_xact_lock(hash(profesional_id))` en las cuatro operaciones. Equivale, pero obliga a tocar `CrearTurno`/`ReprogramarTurno`, que hoy ya serializan por la fila.
- **Alternativa**: triggers en `turno` y `bloqueo` que validen y además tomen el lock del profesional. Mueve RN-AG-06 a la base (errores menos claros, regla duplicada) por una ganancia que solo importa ante SQL directo.
- **Alternativa**: `SERIALIZABLE` en las cuatro operaciones. Exige reintentar ante `40001` en toda la API.
- **Contrato del lock (invariante, se registra en DD-30)**: la garantía de RN-HB-03 y RN-AG-06 depende de un protocolo que la base aplica pero que la aplicación tiene que pedir. Todo escritor de `turno` que pueda crear un turno o moverlo en el tiempo o de profesional MUST leer el profesional destino con `FOR SHARE` antes de validar; todo escritor de `bloqueo` MUST tomar `FOR NO KEY UPDATE` sobre el profesional antes de consultar los turnos. Un change futuro que agregue otra vía de escritura (C-13 o el backlog) hereda este contrato. D13 resuelve la **Suposición** abierta de `08` §Concurrencia ("o con triggers"): validación en aplicación con lock por profesional, sin triggers. "Trigger + lock" queda en el backlog como defensa en profundidad, junto al rol de base de datos de mínimo privilegio.
- Prueba (regla dura): `test_concurrencia_bloqueos.py` con `motor_concurrente`, con un escenario determinista por orden de llegada (patrón de `test_concurrencia_desactivacion.py`, DD-26 i): el turno espera al bloqueo y el bloqueo espera al turno, tanto para el alta como para la reprogramación, más la reprogramación de un turno de B hacia A mientras se bloquea A (el lock que cuenta es el del profesional destino). RED verificado sin el `FOR NO KEY UPDATE`, y estable en ≥ 5 corridas.

### D14 — Modelo y migración `010`
- `app/infrastructure/db/models/bloqueo.py`: `Bloqueo(Base)`, tabla `bloqueo`: `id uuid` (`gen_random_uuid()`), `profesional_id` (FK `profesional.id` `ON DELETE CASCADE`), `inicio`/`fin` `timestamptz NOT NULL`, `motivo varchar(255) NOT NULL`, `creado_por` (FK `usuario.id` `ON DELETE RESTRICT`, `NOT NULL`: a diferencia del turno, el bloqueo nace con autenticación), `creado_en timestamptz` (como el resto de las tablas; no es parte del contrato de la API). CHECKs `ck_bloqueo_fin_mayor` y `ck_bloqueo_motivo_no_vacio`. Índice `ix_bloqueo_profesional_id_inicio` btree `(profesional_id, inicio)`: cubre la FK (regla `schema-foreign-key-indexes`) y el listado ordenado. Para la consulta de solape `[)` alcanza a la escala del MVP; si se elige la alternativa de D2, el GiST de la exclusión lo reemplaza.
- `CASCADE` en el profesional, como `horario_atencion`: el bloqueo es parte de su agenda, la app nunca borra profesionales y simplifica `catalogo_commiteado`. `RESTRICT` en el autor: los usuarios no se borran (DD-16) y un fixture que borre un usuario con bloqueos debe borrarlos antes (tarea 3.3).
- `alembic/versions/010_bloqueo.py`: `revision = "010"`, `down_revision = "009"`; `downgrade` hace `drop_table`. `test_migrations.py` pasa a esperar `"010"`; `test_modelos_vs_migracion.py` sin diferencias.
- Numeración: `revisar-migraciones` (2026-11-04) dio `010` libre, sin otra rama que lo reclame. C-13 puede sumar una migración en paralelo; quien mergea segundo renumera (tarea 9.2).

### D15 — `profesional_ajeno` reutilizado
- `ProfesionalAjenoError.__init__(self, mensaje: str = MENSAJE_PROFESIONAL_AJENO)` y el manejador de `app/api/horarios.py` usa `error.mensaje`. Horarios no cambia (sus tests lo cubren); bloqueos lanza con `MENSAJE_BLOQUEO_AJENO = "Solo podés operar sobre tus propios bloqueos"`. Se puede mover el error a un módulo común (`app/domain/usuarios.py`) en el refactor si queda más claro; el código HTTP y el cuerpo no cambian.

### 1. Capas y módulos
- `app/domain/bloqueos.py` (puro): `validar_bloqueo(inicio, fin, motivo) -> str` (devuelve el motivo normalizado o lanza `BloqueoInvalidoError`), `BloqueoInvalidoError` (→ `422 bloqueo_invalido`), `ProfesionalRequeridoError` (→ `422 profesional_requerido`), `BloqueoConTurnosError(turnos: Sequence[TurnoAfectado])` (→ `409`), `TurnoAfectado(id, inicio, fin)`, `resolver_profesional(usuario, profesional_id) -> UUID` (D1) y mensajes. Reusa `Intervalo` de `app/domain/turnos.py`. Sin SQLAlchemy ni FastAPI.
- `app/infrastructure/db/repositorio_bloqueos.py`: `bloquear_profesional(id)` (misma consulta que en horarios; extraer un helper común en el refactor si conviene), `turnos_activos_en(profesional_id, intervalo) -> list[TurnoAfectado]` (`estado <> 'cancelado'`, solape `[)`, orden `inicio, id`), `bloqueos_en(profesional_id, intervalo) -> bool`, `listar(profesional_id | None)`, `obtener(id)`, `agregar`, `eliminar`, `commit`/`rollback`.
- `app/application/bloqueos_agenda.py`: `CrearBloqueo`, `ConsultarBloqueos`, `BorrarBloqueo` (commit al final; rollback ante cualquier error ocurrido con el lock del profesional tomado, como `CancelarTurno`; los rechazos previos al lock no escribieron nada y los deshace el cierre de la sesión del request) y `ValidadorBloqueos`.
- `app/api/bloqueos.py`: router `/bloqueos` (`UsuarioDeAmbosRoles` en las tres rutas), `BloqueoIn` (`profesional_id: UUID | None = None`, `inicio`/`fin: AwareDatetime`, `motivo: Annotated[str, StringConstraints(strip_whitespace=True, max_length=255)]`, D7), `BloqueoOut` (instantes con `to_local`, como `TurnoOut`) y manejadores de `BloqueoInvalidoError`, `ProfesionalRequeridoError` y `BloqueoConTurnosError`. `ReferenciaInvalidaError` y `RecursoInexistenteError` ya tienen manejador. Se registra en `main.py`.
- `app/api/turnos.py::_validadores` → `[ValidadorHorario(...), ValidadorBloqueos(RepositorioBloqueos(session))]`.

### 2. Orden de evaluación
- `POST /bloqueos`: `401` (dependencia) → `422` de schema (Pydantic: tipos, zona, largo) → `403 profesional_ajeno` / `422 profesional_requerido` (D1, sin tocar la base) → lock del profesional, `422 referencia_invalida` si no existe → `422 bloqueo_invalido` → `409 bloqueo_con_turnos` → `INSERT` y commit.
- `GET /bloqueos`: `401` → `422` de query → `403 profesional_ajeno` → `200`.
- `DELETE /bloqueos/{id}`: `401` → `422` de path → lectura del bloqueo → odontólogo con un bloqueo inexistente o de otro profesional: `403 profesional_ajeno` / recepcionista con un bloqueo inexistente: `404 recurso_inexistente` (D12) → lock del profesional → `DELETE` y commit.

### 3. Interacción con C-12 (recordatorios), verificada en el código
- Crear o borrar un bloqueo no escribe en `turno`, `recordatorio` ni `turno_auditoria`, y no usa la cola: la ruta de bloqueos no depende de `get_programador` ni de `get_cola_recordatorios`.
- Un turno rechazado por `ValidadorBloqueos` lanza dentro de `validar_solicitud_turno`, antes de `insertar`/`actualizar` y de los observadores (`auditor`, `programador`). `programador.publicar(cola)` no se ejecuta porque la excepción sale de `caso.ejecutar`. Al reprogramar, el `rollback` deja el turno y su recordatorio `pendiente` intactos.
- El worker (Flujo 6) no necesita mirar bloqueos: por RN-HB-03 un turno activo nunca queda dentro de uno.
- Lo cubren los escenarios "El rechazo no toca el turno ni su recordatorio", "Turno rechazado sin recordatorio" y "Reprogramación rechazada por un bloqueo conserva el recordatorio".

## Risks / Trade-offs

- [Un turno escrito por SQL directo puede quedar dentro de un bloqueo] → aceptado y documentado (D13, `08`). La API es el único escritor en el MVP; el backlog ya tiene el rol de base de datos de mínimo privilegio.
- [Conflicto de merge con C-13 en la numeración de la migración y en `api/turnos.py`] → tarea 9.2 (`revisar-migraciones` y renumeración por quien mergea segundo); el validador de bloqueos va siempre después del de horario.
- [Los fixtures que borran usuarios fallan por la FK `RESTRICT` de `creado_por`] → tarea 3.3 los ajusta antes de escribir tests de API.
- [La serialización por profesional suma espera entre un alta de bloqueo y las altas de turno del mismo profesional] → es una fila por profesional y operaciones de milisegundos; las altas de turno entre sí no se serializan.
- [Bloqueo retroactivo sobre turnos pasados imposible de resolver (D5)] → caso raro, aceptado por el usuario; se documenta en DD-30 y lo fija un escenario. Si molesta, contar solo turnos con `fin > ahora` sería una regla nueva (pregunta abierta, no de este change).
- [Un change futuro agrega otra vía de escritura de turnos o bloqueos sin respetar el contrato del lock (D13)] → el contrato queda en DD-30 como invariante para todo escritor futuro.

## Migration Plan

1. `alembic upgrade head` aplica `010` (tabla nueva, sin tocar datos).
2. Sin seed de bloqueos: el seed de desarrollo no cambia.
3. Rollback: `alembic downgrade 009` borra la tabla. El validador de bloqueos debe quitarse junto con el código (sin la tabla, toda alta de turno fallaría).

## Open Questions

- Ninguna. Las decisiones D1-D9 y D11-D13 quedaron aprobadas por el usuario el 2026-11-04 (D12 con `403` primero). No se agregan preguntas a `10_preguntas_abiertas.md`. Las inconsistencias de la KB que este change resuelve (matriz `CRUD` vs scope `POST`/`GET`/`DELETE`, la Suposición del bloqueo por sillón, la tabla de API de `02` sin `GET`, la Suposición "o con triggers" de `08` §Concurrencia) se registran en DD-30.
