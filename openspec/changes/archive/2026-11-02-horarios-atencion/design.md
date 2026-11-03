# Design

## Context

Ver `proposal.md` (Why, Non-goals) y los delta specs `horarios-atencion`, `agenda-turnos` y `datos-semilla`. Estado actual del código (C-01..C-08 archivados):

- **Validación compartida de turnos** (`app/application/validacion_turno.py`): `validar_solicitud_turno` aplica, en orden fijo, referencias (`cargar_referencias`, con `FOR SHARE` sobre profesional, paciente, prestación y sillón desde C-08), duración y grilla, inicio futuro, coherencia del sillón, **los `validadores` inyectados** (`ValidadorTurno = Callable[[TurnoPropuesto], None]`) y el pre-chequeo de solape. `CrearTurno` y `ReprogramarTurno` reciben `validadores` en el constructor, pero `get_crear_turno` y `get_reprogramar_turno` (`app/api/turnos.py`) hoy no pasan ninguno. Es el punto de extensión que C-03 dejó para RN-AG-05/06.
- **Errores de turno**: `TurnoInvalidoError(codigo, mensaje)` ya se traduce a `422 {"detail": {"codigo", "mensaje"}}` (códigos actuales `duracion_invalida`, `inicio_en_pasado`, `sillon_requerido`, …). `TurnoPropuesto` trae `inicio`/`fin` en UTC.
- **Tiempo**: `app/domain/time.py` (`to_utc`, `to_local` con `zoneinfo`, `DEFAULT_TIMEZONE = "America/Argentina/Buenos_Aires"`); la grilla de 5 minutos del inicio ya se evalúa en hora local con esa zona (DD-15). `app/domain/grilla.py` tiene `GRILLA_MIN = 5`.
- **Catálogo** (C-08): `app/api/recursos.py` con routers `/profesionales`, `/sillones`, `/prestaciones`; `RecursoInexistenteError(TipoRecurso)` → `404 recurso_inexistente`; `RecursoInvalidoError(codigo, mensaje)` → `422`; alias `RecepcionistaAutenticada` y `UsuarioDeAmbosRoles` en `app/api/auth.py`; `UsuarioAutenticado` trae `rol` y `profesional_id` (releídos de la base). Patrón de `PATCH` con `model_fields_set` y rechazo de `null` en obligatorios.
- **Base**: migraciones `001..006`, lineales y numeradas a mano; `btree_gist` habilitada en `001`; exclusiones de `turno` declaradas en el modelo con `ExcludeConstraint` y una expresión `text(...)`; `CatalogoMixin` (`id uuid gen_random_uuid()`, `creado_en`, `actualizado_en`). Profesionales nunca se borran (DD-26).
- **Tests**: `crear_catalogo(session)` (dos profesionales, dos sillones, dos pacientes, Limpieza y Consulta) lo usan 19 módulos de integración; `catalogo_commiteado` limpia con `DELETE` de turnos y catálogo; el fixture `odontologo` crea su propio profesional "Olga". Los turnos de los tests caen mayormente entre 09:00 y 19:00 hora local (también hay instantes `T00:00Z` = 21:00 local).

## Goals / Non-Goals

**Goals:**
- RN-AG-05 enchufada por el punto de extensión de C-03, sin cambiar el orden ni el código de las validaciones existentes, y dejando el lugar de C-11 (bloqueos) inmediatamente después.
- La regla "cabe en una franja" como función pura de dominio, con la conversión de zona hecha con `zoneinfo` (no un offset fijo; SU-08).
- La base como última garantía de la forma de la franja y de la no superposición (mismo criterio que DD-02/DD-15).
- La suite existente en verde durante todo el change: los tests que crean turnos por API no deben empezar a fallar por falta de horario.

**Non-Goals:**
- Endpoint de disponibilidad o huecos libres (C-13).
- Configurar la zona horaria por profesional o por consultorio (monotenant, SU-07).
- Auditoría de cambios de horario.

## Decisions

D1, D3, D5, D6, D7, D8, D9, D10 y D11 **no las fija la KB**: se propusieron con una recomendación y el usuario **confirmó la recomendada** de cada una (2026-11-02). D17 y D18 surgieron de la revisión de escenarios (`revision-escenarios.md`, preguntas abiertas 1 y 2) y también las decidió el usuario. Todas se registran como **DD-27** en `knowledge-base/09_decisiones_y_supuestos.md` (tarea 9.1), igual que DD-26 en C-08.

| Id | Decisión | Fuente / estado |
|---|---|---|
| D1 | `dia_semana`: **0 = lunes … 6 = domingo** (convención de `date.weekday()` de Python) | **Confirmada.** La KB solo dice "0-6" |
| D2 | `hora_inicio`/`hora_fin` como `time without time zone` en hora local; la API acepta `"HH:MM"` o `"HH:MM:SS"` y responde `"HH:MM:SS"` | `04_modelo_de_datos.md` §HorarioAtencion ("hora local"); RN-CU-04 |
| D3 | Horas de la franja alineadas a 5 minutos y sin zona horaria → si no, `422 franja_invalida` (con CHECK en la base) | **Confirmada.** Extiende la grilla de DD-15 a la franja |
| D4 | `hora_fin > hora_inicio`, sin cruzar la medianoche → `422 franja_invalida` + CHECK | `04` (`hora_fin > hora_inicio`); US-002 |
| D5 | Franjas superpuestas del mismo profesional y día → `409 franja_superpuesta`, con restricción de exclusión en la base; contiguas permitidas (`[)`) | **Confirmada.** La KB no lo dice |
| D6 | Un turno debe caber en **una** franja: si cruza dos franjas contiguas (09-13 y 13-17, turno 12:30-13:30) se rechaza | **Confirmada.** Lectura literal de RN-AG-05 y del test "intervalo que cruza dos franjas" de `CHANGES.md` |
| D7 | Profesional sin franjas (o sin franjas ese día) → todo turno `422 fuera_de_horario` | **Confirmada.** Lectura estricta de RN-AG-05 |
| D8 | Editar o borrar una franja **se permite** aunque deje turnos fuera de horario: los turnos no cambian, se pueden cancelar, y al reprogramarlos rige el horario vigente | **Confirmada.** Análogo a DD-26 g (desactivar con turnos futuros) |
| D9 | Rutas anidadas `GET`/`POST /profesionales/{id}/horarios`, `PATCH`/`DELETE /profesionales/{id}/horarios/{horario_id}`; `DELETE` es **borrado físico** (`204`) | **Confirmada.** KB: "CRUD por profesional" (`02`) |
| D10 | Odontólogo: lee solo las franjas de su profesional; sobre otro → `403 profesional_ajeno` (antes de verificar existencia) | **Confirmada** (código y `403`). Matriz de `03`: "R (propios)" |
| D11 | Se permiten franjas para un profesional desactivado (alta, edición, borrado y lectura) | **Confirmada.** La KB no lo dice |
| D12 | Las escrituras de franjas toman `FOR NO KEY UPDATE` sobre la fila del profesional | Diseño (§4) |
| D13 | El turno se lleva a hora local (no las franjas a UTC) y se compara como `datetime` local | RN-CU-04, SU-08 (§3) |
| D14 | RN-AG-05 como `ValidadorTurno` inyectado, `422 fuera_de_horario` vía `TurnoInvalidoError` | Punto de extensión de C-03; `05` §Excepciones globales; Flujo 2 de `07` |
| D15 | Seed: ambos profesionales, lunes a viernes 09:00-13:00 y 14:00-18:00, con `id` fijos | `CHANGES.md` §C-10 ("L-V mañana y tarde"); las horas exactas son una elección menor |
| D16 | `crear_catalogo` siembra por defecto una franja amplia (todos los días, 00:00-23:55) para sus profesionales; `con_horario=False` para los tests de C-10 | Diseño de tests (§6) |
| D17 | Odontólogo + `GET /profesionales/<id mal formado>/horarios` → `422` (la validación del path de FastAPI precede al chequeo de `profesional_ajeno`, como en C-08) | **Decidida por el usuario** (revisión, pregunta 1) |
| D18 | Re-ejecutar el seed no modifica ni borra franjas existentes (aunque estén editadas a mano): solo inserta las sembradas que falten, y omite sin error una faltante que se superpondría con otra existente | **Decidida por el usuario** (revisión, pregunta 2); mismo criterio que "Datos preexistentes no se pisan" |

### D1 — `dia_semana` 0 = lunes
- **Recomendada**: 0 = lunes … 6 = domingo. Coincide con `date.weekday()`, que es donde se evalúa la regla (en Python, no en SQL), y con la semana laboral argentina (lunes primero). Se documenta en el OpenAPI (descripción del campo) y en `04`.
- **Alternativa**: 0 = domingo (`EXTRACT(DOW)` de PostgreSQL y `Date.getDay()` de JavaScript, que usará el frontend de C-14). Descartada porque la regla vive en Python; el frontend traduce una sola vez.
- **Alternativa**: ISO 1-7 (`isoweekday()`). Contradice el rango 0-6 de la KB.

### D3 — Grilla de 5 minutos en la franja
- **Recomendada**: exigir minutos múltiplo de 5 y segundos/fracciones en 0, y rechazar horas con zona (`"09:00-03:00"`). Como todo turno empieza en la grilla y dura múltiplos de 5 (DD-15), un borde fuera de la grilla solo desperdicia minutos; y una hora con zona contradice "hora local". CHECK en la base con `mod(extract(epoch FROM hora_x)::int, 300) = 0` (sin `%`, por el marcador del driver, igual que la `006`).
- **Alternativa**: aceptar cualquier minuto (sin regla nueva). Descartada por coherencia con DD-15, pero no rompe nada si el usuario la prefiere.

### D5 — Superposición de franjas
- **Recomendada**: `409 franja_superpuesta` (es un conflicto con un estado existente, mismo criterio que el `409` de solapes) con pre-chequeo en la aplicación y `EXCLUDE USING gist (profesional_id WITH =, dia_semana WITH =, tsrange(DATE '2000-01-03' + hora_inicio, DATE '2000-01-03' + hora_fin, '[)') WITH &&)`. `date + time` da `timestamp` sin zona (inmutable), así que la expresión es indexable; la fecha es arbitraria. Contiguas permitidas por el `[)`.
- **Alternativa**: permitir superposición (la validación del turno igual funciona, pero el listado queda confuso y "cabe en una franja" pierde sentido). **Alternativa**: `422` (es un conflicto con datos existentes, no un body inválido; `409` es el código del proyecto para eso, DD-26 e).
- **Alternativa técnica**: un tipo de rango propio `timerange` (`CREATE TYPE … AS RANGE (subtype = time)`, documentado en PostgreSQL §8.17.8, Context7). Descartada: suma un tipo a la base y a SQLAlchemy sin beneficio frente a la expresión.

### D6 — Turno que cruza franjas contiguas
- **Recomendada**: rechazo literal (`fuera_de_horario`): RN-AG-05 dice "caber en **una** franja" y `CHANGES.md` pide el test "intervalo que cruza dos franjas rechazado". Si la recepción quiere atención continua, carga una sola franja (09:00-17:00). Consecuencia: se documenta en el OpenAPI y en DD-27.
- **Alternativa**: unir franjas contiguas al validar (12:30-13:30 válido con 09-13 y 13-17). Más amigable, pero contradice la letra de RN-AG-05.
- **Alternativa**: rechazar franjas contiguas al crearlas (`409`), para que no exista la trampa. Agrega una regla más fuerte que la KB.

### D7 — Profesional sin franjas
- **Recomendada**: sin franja que contenga el turno → `422 fuera_de_horario`, también si el profesional no tiene ninguna. Es la lectura estricta de RN-AG-05 y de US-002 ("no se dan turnos fuera de horario"). Consecuencia: el seed trae franjas (D15) y los tests existentes también (D16); un profesional recién dado de alta no admite turnos hasta que la recepción cargue su horario.
- **Alternativa**: "sin horario configurado = sin restricción". Más compatible, pero un olvido de configuración deja la agenda abierta las 24 h, que es justo lo que RN-AG-05 quiere evitar.
- **Alternativa**: mismo `422` con un código propio (`sin_horario_configurado`). Posible si el usuario quiere distinguirlo en la UI; no cambia el diseño.

### D8 — Cambios de horario con turnos existentes
- **Recomendada**: permitir; los turnos quedan como están (mismo criterio que DD-26 g y D11 de C-08). RN-HB-03 (rechazo `409` con turnos afectados) está escrita para **bloqueos**, no para horarios, y extenderla sería inventar. Consecuencia ya especificada: reprogramar uno de esos turnos, aunque sea solo para cambiar el sillón, da `422 fuera_de_horario` (RN-AG-08), igual que hoy pasa con una prestación desactivada (DD-26).
- **Alternativa**: `409` con la lista de turnos que quedarían fuera (como RN-HB-03). Más seguro para la recepción, pero exige consultar turnos futuros en cada escritura de franja y, con D12, serializar contra altas de turno; si se elige, se agrega un requisito y tareas.
- **Alternativa**: permitir y avisar en la respuesta (lista informativa). Agrega contrato sin consumidor en el MVP.

### D9 — Rutas y borrado
- **Recomendada**: rutas anidadas bajo el profesional (como pide `CHANGES.md`) y `DELETE` físico con `204`: ninguna tabla referencia a `horario_atencion` y la franja no tiene historial que conservar (los turnos guardan su propio intervalo). Sin `GET` de detalle de una franja (el listado por profesional alcanza: ≤ 14 filas típicas).
- **Alternativa**: desactivación lógica (`POST …/desactivar`, como DD-26). Suma un estado que la validación debería filtrar, sin necesidad.
- **Alternativa**: `PUT` reemplazando el horario semanal completo. Más simple para un formulario, pero distinto del resto de la API.

### D10 — Lectura del odontólogo
- **Recomendada**: `403` con `{"codigo": "profesional_ajeno", "mensaje": "Solo podés consultar tu propio horario"}`, evaluado antes que la existencia del profesional (no revela qué ids existen). La matriz de `03` dice "R (propios)", a diferencia del catálogo (DD-26 a / D14 de C-08), donde el odontólogo lee todo.
- **Alternativa**: `404` para ocultar la existencia (más opaco, pero confunde con "no existe").
- **Alternativa**: lectura total para ambos roles, como el catálogo (contradice la matriz).
- **Coordinación**: C-11 (Nico) resuelve el "solo lo propio" del odontólogo **forzando** `profesional_id` desde el token en `POST /bloqueos`; en lectura conviene que use el mismo `403 profesional_ajeno`.

### D11 — Profesional desactivado
- **Recomendada**: permitir leer y escribir sus franjas. No hay reactivación (DD-26 d) y sus turnos nuevos ya se rechazan por `referencia_invalida`, así que las franjas no tienen efecto; rechazarlas agregaría una regla sin respaldo en la KB.
- **Alternativa**: `422` al escribir franjas de un profesional inactivo.

### D17 — Identificador mal formado en la lectura del odontólogo
- **Decidida**: `422`. El chequeo de `profesional_ajeno` compara el `profesional_id` del path, ya parseado como `UUID`, con el del token, así que vive en el endpoint (o en una dependencia que recibe el path tipado); FastAPI valida el path antes de ejecutar el cuerpo del endpoint y responde `422`. Es el mismo comportamiento que las rutas de C-08 y no revela nada (un texto que no es UUID no identifica a ningún profesional). Sin token sigue siendo `401` (la dependencia de autenticación corre antes que la validación del path).
- **Alternativa descartada**: `403 profesional_ajeno` también con id mal formado. Exigiría tomar el path como `str` y parsearlo a mano, distinto del resto de la API.

### D18 — Seed ante franjas editadas a mano
- **Decidida**: las franjas sembradas tienen `id` fijos y se insertan con `ON CONFLICT DO NOTHING` **sin target**, como el resto de `seed.py`: una franja que ya existe (con su `id`) no se toca aunque se haya editado; una que falta (borrada a mano) se inserta otra vez; y si la faltante chocara con la exclusión `horario_atencion_sin_superposicion` (porque se cargó a mano otra franja en su lugar), `DO NOTHING` sin target también cubre las violaciones de exclusión y la omite sin error. Requisito MODIFIED "Contenido del seed de desarrollo" de `datos-semilla`.
- **Alternativa descartada**: reponer el horario de ejemplo completo (pisar ediciones). Contradice "Datos preexistentes no se pisan".

### 1. Capas y módulos
- `app/domain/horarios.py` (nuevo, puro): `Franja` (`dia_semana: int`, `hora_inicio: time`, `hora_fin: time`), `HorarioInvalidoError(codigo, mensaje)` (o reutilizar `RecursoInvalidoError` con código `franja_invalida`; ver tareas), `FranjaSuperpuestaError` (409), `validar_franja(franja)` (D3/D4, `dia_semana` 0-6), `se_superponen(a, b)` y `cabe_en_horario(inicio_utc, fin_utc, franjas, tz) -> bool` (§3). `MENSAJE_FUERA_DE_HORARIO`. Sin SQLAlchemy ni FastAPI.
- `app/infrastructure/db/models/horario_atencion.py` (nuevo): `HorarioAtencion(CatalogoMixin, Base)`, tabla `horario_atencion`: `profesional_id` (FK `profesional.id` `ON DELETE CASCADE`), `dia_semana smallint`, `hora_inicio time`, `hora_fin time`, CHECKs `ck_horario_atencion_dia_semana_valido` (`dia_semana BETWEEN 0 AND 6`), `ck_horario_atencion_hora_fin_mayor` (`hora_fin > hora_inicio`), `ck_horario_atencion_grilla` (ambas horas en múltiplos de 300 s) y `ExcludeConstraint` `horario_atencion_sin_superposicion` (D5). `CASCADE` porque la franja es parte del profesional (y simplifica la limpieza de `catalogo_commiteado`); en la app los profesionales nunca se borran.
- `app/infrastructure/db/repositorio_horarios.py` (nuevo): `bloquear_profesional(id)` (`SELECT … FOR NO KEY UPDATE`, devuelve `None` si no existe), `listar(profesional_id)` (orden `dia_semana, hora_inicio`), `franjas_del_dia(profesional_id, dia_semana) -> list[Franja]`, `obtener(profesional_id, horario_id)`, `superpuestas(profesional_id, franja, excluir_id)`, `agregar`, `eliminar`, `guardar` (`flush` que traduce `23P01` de `horario_atencion_sin_superposicion` a `FranjaSuperpuestaError`), `commit`/`rollback`.
- `app/application/horarios_atencion.py` (nuevo): casos de uso `ConsultarHorarios`, `CrearFranja`, `EditarFranja`, `BorrarFranja` (commit al final, rollback ante error, como C-08) y `ValidadorHorario(repositorio, tz)`: `__call__(propuesto: TurnoPropuesto) -> None` que obtiene el día local del inicio, lee `franjas_del_dia` y lanza `TurnoInvalidoError("fuera_de_horario", MENSAJE_FUERA_DE_HORARIO)` si `cabe_en_horario` es falso.
- `app/api/horarios.py` (nuevo): router `/profesionales/{profesional_id}/horarios`, schemas `FranjaIn`, `FranjaCambios` (`model_fields_set`, `null` → `422`), `FranjaOut`; manejadores de `FranjaSuperpuestaError` (`409`) y `ProfesionalAjenoError` (`403`). Registrado en `main.py`.
- `app/api/turnos.py`: `get_crear_turno` y `get_reprogramar_turno` pasan `validadores=[ValidadorHorario(RepositorioHorarios(session))]` (misma sesión del request). C-11 agrega su validador de bloqueos **después** en la misma lista.
- `app/domain/recursos.py`: `TipoRecurso.HORARIO = "horario"` para reutilizar `RecursoInexistenteError` → `404 {"codigo": "recurso_inexistente", "recurso": "horario"}`.

### 2. API y orden de evaluación
- Orden en escrituras: `401` → `403 rol_insuficiente` (dependencia `RecepcionistaAutenticada`) → `422` de schema/path (Pydantic) → `404` profesional (al tomar el lock) → `404` horario (`obtener` filtra por `profesional_id`, así una franja de otro profesional es `404`) → `422 franja_invalida` (sobre la franja resultante, tras fusionar el `PATCH`) → `409 franja_superpuesta`. Igual que C-08: un body inválido sobre un path inexistente da `422`, no `404`.
- Lectura: dependencia `UsuarioDeAmbosRoles` (`401`) → `422` de path mal formado (D17) → si el rol es `odontologo` y `profesional_id != usuario.profesional_id` → `403 profesional_ajeno` antes de buscar el profesional → `404` profesional.
- `PATCH` que cambia `dia_semana`: la superposición se evalúa sobre la franja resultante, o sea contra las franjas del día nuevo (excluyendo a la propia).
- `dia_semana: int` y horas `time` sin rangos en Pydantic: la regla vive en el dominio (`franja_invalida`), una sola fuente, como `duracion_min` en C-08. Un tipo inválido (`"nueve"`, `dia_semana: "lunes"`) da el `422` por defecto de FastAPI.
- `DELETE` responde `Response(status_code=204)` sin cuerpo.

### 3. Regla "cabe en una franja" (D13)
```
local_inicio = to_local(inicio_utc, tz); local_fin = to_local(fin_utc, tz)
dia = local_inicio.weekday()
cabe ⇔ ∃ f ∈ franjas(dia):
        datetime.combine(local_inicio.date(), f.hora_inicio, tz) <= local_inicio
    and local_fin <= datetime.combine(local_inicio.date(), f.hora_fin, tz)
```
- Comparar `datetime` locales (no `time`) hace que un turno que pasa la medianoche nunca quepa (su fin es del día siguiente) y que el fin igual al cierre sea válido (`<=`, intervalo `[)`).
- Se convierte el turno a local en vez de las franjas a UTC (equivalentes con offset fijo, pero con `zoneinfo` esto sigue siendo correcto si Argentina volviera a tener horario de verano: la franja es hora de reloj de pared). Zona: `DEFAULT_TIMEZONE`, la misma que usa la grilla del inicio (DD-15). En un cambio de hora hipotético, una hora local inexistente o ambigua se resuelve con `fold=0`; se acepta como límite (SU-08).

### 4. Concurrencia (D12)
- Toda escritura de franjas empieza con `SELECT id FROM profesional WHERE id = :id FOR NO KEY UPDATE`: serializa las escrituras de franjas del mismo profesional (el pre-chequeo de superposición queda consistente y se evitan deadlocks entre dos `INSERT` que verifican la exclusión a la vez) y, como `FOR NO KEY UPDATE` choca con el `FOR SHARE` que `cargar_referencias` toma sobre el profesional del turno, un alta o reprogramación de turno y un cambio de horario del mismo profesional también quedan en serie. Con D8 esa serialización no es imprescindible (validar contra el horario anterior equivale a crear el turno justo antes del cambio), pero da una semántica limpia sin costo y es la base si el usuario elige la alternativa `409` de D8.
- La exclusión en la base sigue como garantía ante escrituras directas; su `23P01` se traduce a `409 franja_superpuesta`.

### 5. Migración `007_horario_atencion.py`
- `upgrade`: `create_table("horario_atencion", …)` con los CHECKs y la exclusión de §1 (nombres con `op.f()`), `downgrade`: `drop_table`. El índice GiST de la exclusión tiene `profesional_id` como primera columna, así que cubre las búsquedas por FK (regla `schema-foreign-key-indexes`); no hace falta un btree aparte.
- `test_migrations.py` pasa a esperar `"007"`; `test_modelos_vs_migracion.py` debe seguir sin diferencias (la exclusión se declara igual en el modelo y en la migración, como `turno`).

### 6. Tests existentes (D16)
- Con D7, todo `POST /turnos` y `PATCH …/reprogramar` por API sin franjas da `422`. `crear_catalogo(session, *, con_horario: bool = True)` agrega para cada uno de sus dos profesionales siete franjas `00:00-23:55` (una por día): cubre todos los instantes que usan los tests actuales (09:00-21:00 locales) y deja explícito en las pruebas de C-10 (`con_horario=False`) qué franjas existen. Lo mismo para el profesional del fixture `odontologo` solo si algún test de turnos lo usa como profesional del turno (verificar en la tarea 1.1).
- Los tests de casos de uso que construyen `CrearTurno`/`ReprogramarTurno` sin `validadores` no cambian.
- `catalogo_commiteado` no necesita cambios gracias al `CASCADE`.

## Risks / Trade-offs

- [Los tests de API existentes empiezan a dar `422`] → D16 (franja amplia por defecto en la fábrica) y safety net completo antes y después de enchufar el validador (tareas 1.1 y 6.4).
- [Turnos que terminan entre 23:55 y 24:00 imposibles] → límite aceptado del modelo `time` sin "24:00" (D4); los consultorios no atienden a medianoche.
- [Conflicto de merge con C-11 en `api/turnos.py`, `factories.py` y la numeración de la migración] → el validador de horario va primero en `validadores`; quien mergea segundo reordena/renumera (regla del equipo); avisar a Nico al abrir el PR.
- [La recepción carga franjas contiguas esperando atención continua y se encuentra con `fuera_de_horario` (D6)] → documentarlo en la descripción del OpenAPI; si molesta, la alternativa "unir contiguas" es un cambio local en `cabe_en_horario`.
- [Profesional nuevo sin horario no admite turnos (D7)] → mensaje claro en `fuera_de_horario`; el frontend (C-14) puede mostrar "cargá el horario".
- [`date + time` en la exclusión] → verificado en la tarea 3.1 por el test de migración (la expresión debe ser inmutable para indexarse; si PostgreSQL la rechaza, se usa el tipo `timerange` de la alternativa de D5).

## Migration Plan

1. `alembic upgrade head` aplica `007` (tabla nueva, sin tocar datos existentes).
2. Ejecutar el seed (idempotente) para cargar las franjas de ejemplo.
3. **En una base con datos reales**, antes de desplegar el validador hay que cargar los horarios de cada profesional activo, o todo turno nuevo dará `422` (D7). En el MVP solo hay bases de desarrollo y test.
4. Rollback: `alembic downgrade 006` borra la tabla; el validador debe quitarse junto con el código (si no, toda alta da `422`).

## Open Questions

- Ninguna: D1, D3, D5-D11 están confirmadas y las preguntas abiertas de la revisión de escenarios se resolvieron como D17 y D18. Los textos exactos de los mensajes (`fuera_de_horario`, `profesional_ajeno`) quedan como están en los specs salvo pedido del usuario.
