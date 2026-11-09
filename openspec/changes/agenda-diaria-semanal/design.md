# Design

## Context

Ver `proposal.md` y el delta spec `consulta-agenda`. Estado actual verificado en el código (`main` en `502588a`, con C-09 y C-11 archivados):

- **No existe ningún `GET /turnos`**: `api/turnos.py` expone solo `POST /turnos`, `POST /turnos/{id}/cancelar` y `PATCH /turnos/{id}/reprogramar`, todas con `RecepcionistaAutenticada`. `GET /turnos/{id}/auditoria` vive en `api/auditoria.py` y no choca con `GET /turnos`.
- **Bloqueos**: `GET /bloqueos?profesional_id=` (DD-30 k) lista sin rango, por `inicio, id`; el odontólogo pasa por `resolver_profesional` (`domain/bloqueos.py`), que da `403 profesional_ajeno` antes de mirar la base. `RepositorioBloqueos.listar` y `bloqueos_en` ya usan el criterio `[)`. `BloqueoOut` (`api/bloqueos.py`) presenta `inicio` y `fin` con `to_local`.
- **Hora en las respuestas**: todas las respuestas existentes (`TurnoOut`, `BloqueoOut`, auditoría, `409 bloqueo_con_turnos`) presentan los instantes con `to_local` (`-03:00`), y el spec `agenda-turnos` lo exige. `CHANGES.md` y el Flujo 7 dicen "respuesta en UTC". Ver D7.
- **Tiempo**: `domain/time.py` tiene `to_utc` y `to_local` con `zoneinfo` y `DEFAULT_TIMEZONE = "America/Argentina/Buenos_Aires"`; `domain/turnos.py` tiene `Intervalo(inicio, fin)` semiabierto.
- **Pacientes**: `PacienteResumenOut` (`api/pacientes.py`) es `{id, nombre, apellido}`, lo que el odontólogo puede leer de los pacientes de sus turnos, en cualquier estado (DD-31 a, c). DD-31 deja pendiente que la agenda de C-13 lleve el nombre del paciente.
- **Índices**: `ix_turno_profesional_id_inicio`, `ix_turno_sillon_id_inicio` e `ix_bloqueo_profesional_id_inicio` existen. Las exclusiones GiST de `turno` son parciales (`estado <> 'cancelado'`). No hay CHECK de duración máxima en `turno` (DD-15 vive en la aplicación y en `prestacion`).
- **Roles**: `UsuarioDeAmbosRoles` (`api/auth.py`) ya existe; `usuario.profesional_id` no es nulo para el odontólogo (CHECK de `usuario`). El odontólogo lee profesionales, sillones y prestaciones (matriz de `03`).
- **`service-health`**: su escenario "Ruta inexistente" usa `GET /turnos`; `test_health.py` ya no lo usa (prueba `/agenda`, `/consultorios` y `/`).

## Goals / Non-Goals

**Goals:**
- Un único pedido por vista: la agenda diaria o semanal llega completa (turnos con el nombre del paciente y bloqueos), sin pedidos por paciente ni un segundo pedido a `/bloqueos`.
- El rango se piensa en días locales y la conversión a UTC vive en un solo lugar del dominio, probado con unit tests sin base.
- Mismo contrato de aislamiento que `GET /bloqueos`: el odontólogo no puede averiguar si existe otro profesional.

**Non-Goals:**
- Agrupar la respuesta por día, profesional o sillón: lo hace el frontend (C-15).
- Optimizar la consulta con índices nuevos o una cota inferior sobre `inicio` (ver Risks).
- Cambiar `GET /bloqueos`, que sigue sin rango (DD-30 k).

## Decisions

La KB fija el criterio `[)` (DD-03), el aislamiento del odontólogo (RN-AU-02), la presentación en hora local (RN-CU-04) y la forma de los errores de rol (DD-24, DD-27 i, DD-30 k). Lo demás **no lo fija la KB** y fue **aprobado por el usuario el 2026-11-09** (D1-D4, D6-D9 y D11) con la opción recomendada de esta tabla. Los requirements del delta spec están escritos con esa opción; si alguna cambia, corregirlos con `/opsx:update`. Al aprobarse se registran como **DD-32** (tarea 8.1).

| # | Decisión | Estado | Opción recomendada |
|---|----------|--------|--------------------|
| D1 | Forma de la respuesta | **Aprobada por el usuario (2026-11-09)** | Objeto `{turnos, bloqueos}`, dos listas planas |
| D2 | Tipo y semántica de `desde`/`hasta` | **Aprobada por el usuario (2026-11-09)** | Fechas `YYYY-MM-DD` locales, ambas incluidas |
| D3 | Parámetros obligatorios | **Aprobada por el usuario (2026-11-09)** | `desde` y `hasta` obligatorios, sin valor por defecto |
| D4 | Largo máximo del rango | **Aprobada por el usuario (2026-11-09)** | 7 días; más, o invertido, `422 rango_invalido` |
| D5 | Qué entra en el rango | KB, DD-03 | Superposición `[)`, con el intervalo real |
| D6 | Turnos cancelados | **Aprobada por el usuario (2026-11-09)** | Se incluyen, con `estado` y `motivo_cancelacion` |
| D7 | Zona de los instantes de la respuesta | **Aprobada por el usuario (2026-11-09)**, desvía de la KB | Hora local con desfasaje (`-03:00`), como el resto de la API |
| D8 | Nombre de los filtros | **Aprobada por el usuario (2026-11-09)** | `profesional_id` y `sillon_id` |
| D9 | Filtro de sillón y bloqueos | **Aprobada por el usuario (2026-11-09)** | El sillón filtra solo turnos; los bloqueos siguen al profesional |
| D10 | Odontólogo con otro profesional | Precedente DD-27 i, DD-30 k | `403 profesional_ajeno`, antes que el rango; mensaje propio |
| D11 | Datos del paciente en el turno | **Aprobada por el usuario (2026-11-09)** (nota de DD-31) | `paciente: {id, nombre, apellido}` embebido |
| D12 | Orden y paginación | Precedente DD-30 k | `inicio, id`; sin paginación (la acota D4) |
| D13 | Filtro con un id inexistente | Precedente DD-30 k | `200` con listas vacías |
| D14 | Migración e índices | Decisión técnica | Ninguno: **sin migración** |
| D15 | Lectura y concurrencia | Decisión técnica | Sin locks; `READ COMMITTED` |
| D16 | Ubicación de la ruta | Decisión técnica | `GET ""` en `api/turnos.py`, con `UsuarioDeAmbosRoles` |
| D17 | Auditoría | KB, RN-CU-01 | La consulta no se audita |

### D1 — Forma de la respuesta
`CHANGES.md` pide que `GET /turnos` "incluye bloqueos en la respuesta de agenda". **Recomendado**: un objeto con exactamente `turnos` y `bloqueos`, dos listas planas. Cada elemento conserva su forma (la de `TurnoOut` y la de `BloqueoOut`) y el frontend agrupa como necesite la vista. **Alternativas**: (a) una lista con elementos de tipo mixto y un discriminador `tipo` (obliga al cliente a separar y mezcla dos esquemas en uno); (b) agrupar por día o por profesional en el backend (acopla la API a una vista y duplica bloqueos de varios días); (c) solo turnos y que el frontend llame a `GET /bloqueos` (no tiene rango por DD-30 k: traería todos los bloqueos de la historia). Se descartó también devolver `desde` y `hasta` en el cuerpo: el cliente ya los conoce.

### D2 — `desde` y `hasta` como fechas locales, ambas incluidas
El Flujo 7 dice "la API convierte el rango local a UTC". **Recomendado**: fechas del calendario (`YYYY-MM-DD`), las dos incluidas: `desde=2026-10-08&hasta=2026-10-08` es el día 8 y `desde=2026-10-05&hasta=2026-10-11` es la semana. El intervalo de instantes es `[00:00 local de desde, 00:00 local de hasta + 1 día)`, semiabierto como todo intervalo del sistema (DD-03). Son días, no instantes, así que una fecha incluida es lo natural para quien arma la vista ("del lunes al domingo"). **Alternativas**: (a) `hasta` excluido (`desde=8&hasta=9` para un día): coherente con `[)` pero contraintuitivo para fechas y fuente típica de errores de un día; (b) datetimes con zona: el cliente tendría que calcular la medianoche local, que es justo lo que el Flujo 7 asigna a la API, y abre rangos que no empiezan a medianoche; (c) datetimes locales sin zona: los prohíbe la regla dura de `CLAUDE.md`.

### D3 — Parámetros obligatorios
**Recomendado**: `desde` y `hasta` obligatorios (`422` si falta alguno). Un valor por defecto ("hoy") depende del reloj del servidor y esconde errores del cliente. **Alternativa**: `desde` por defecto hoy y `hasta` igual a `desde`.

### D4 — Largo máximo del rango
US-008 pide vistas diaria y semanal, nada más. **Recomendado**: entre 1 y 7 días locales; `hasta < desde` o más de 7 días → `422` con `{"detail": {"codigo": "rango_invalido", "mensaje": ...}}`. Acota la respuesta sin paginación (D12). **Alternativas**: sin máximo (una consulta de un año trae miles de turnos sin paginar); 31 días (habilita una vista mensual que la KB no pide; ampliar el límite después no rompe a ningún cliente, achicarlo sí). Borde: `hasta = 9999-12-31` no tiene día siguiente representable (el fin `[)` desborda), así que también da `422 rango_invalido` y no `500`. El código `rango_invalido` es nuevo y sigue la forma `{codigo, mensaje}` de `franja_invalida` y `bloqueo_invalido`.

### D5 — Superposición `[)` con el intervalo real
Derivado de DD-03: entra lo que cumple `inicio < fin_del_rango AND fin > inicio_del_rango`, y se devuelve con su `inicio` y `fin` reales, sin recortarlo al rango. Así un bloqueo de vacaciones de lunes a viernes aparece en la vista del miércoles, y un bloqueo que termina justo a las 00:00 del día pedido no aparece. Es el mismo criterio de `bloqueos_en` y `turnos_activos_en` del repositorio de bloqueos. **Alternativa descartada**: "empieza dentro del rango", que pierde los bloqueos de varios días.

### D6 — Turnos cancelados
DD-08 conserva el turno cancelado como estado, y DD-31 c ya razonó que "un turno cancelado que el odontólogo sí ve en su agenda" debe poder mostrar el nombre del paciente. **Recomendado**: incluirlos con `estado` y `motivo_cancelacion`, y que la vista los atenúe o los oculte. **Alternativas**: (a) excluirlos siempre (más simple para la vista, pero la recepción pierde de vista que alguien canceló, y queda incoherente con DD-31 c); (b) excluirlos por defecto con `incluir_cancelados=true` opcional (suma un parámetro que la KB no pide). Consecuencia: un cancelado y un programado pueden ocupar el mismo horario en la respuesta, y el frontend tiene que saberlo.

### D7 — Zona de los instantes de la respuesta (conflicto en la KB)
`CHANGES.md` (C-13) y el Flujo 7 dicen "respuesta en UTC; el frontend presenta en Buenos Aires". RN-CU-04, DD-06, la regla dura de `CLAUDE.md` ("presentar en `America/Argentina/Buenos_Aires`") y **todas** las respuestas ya entregadas (`agenda-turnos`, `bloqueos-agenda`, `auditoria-turnos`) presentan en hora local con desfasaje (`2026-10-08T10:00:00-03:00`). **Recomendado**: hora local con desfasaje, como el resto de la API, y corregir el Flujo 7 y `CHANGES.md` al registrar DD-32. `inicio` y `fin` se serializan en ISO 8601 con desfasaje `-03:00` (ej. `2026-10-08T10:00:00-03:00`). Los tests de API existentes (`backend/tests/integration/test_api_auditoria_consulta.py`) comparan el string literal con `-03:00`, y los de esta ruta siguen esa convención: comparan el string literal, no instantes parseados. Es el mismo instante en ISO 8601 en ambos casos y cualquier cliente lo interpreta igual, pero que una sola ruta responda distinto de las demás obliga al frontend a dos formas. **Alternativa**: UTC (`Z`) solo en esta ruta, literal de `CHANGES.md`. Es una decisión del usuario porque contradice texto de la KB.

### D8 — Nombre de los filtros
`02_descripcion_general.md` y `CHANGES.md` escriben `profesional` y `sillon`; `GET /bloqueos` ya usa `profesional_id` (DD-30 k) y todos los bodies usan `*_id`. **Recomendado**: `profesional_id` y `sillon_id`, un solo valor cada uno (US-008: "filtrables por profesional y sillón"), y alinear la fila Turnos de `02`. **Alternativas**: los nombres literales de la KB; listas de varios profesionales (la KB no lo pide).

### D9 — El filtro de sillón no se aplica a los bloqueos
Los bloqueos son por profesional, sin sillón (DD-30 d). **Recomendado**: `sillon_id` filtra solo `turnos`; `bloqueos` sigue solo al filtro de profesional (y al rol). Una vista por sillón muestra igual cuándo cada profesional no atiende. **Alternativas**: (a) con `sillon_id`, `bloqueos` vacía (la vista por sillón pierde contexto y la regla depende de qué filtros vinieron); (b) los bloqueos de los profesionales que tienen turnos en ese sillón ese día (regla nueva, difícil de explicar). Consecuencia: con un sillón inexistente, `turnos` viene vacía y `bloqueos` no necesariamente.

### D10 — Odontólogo con otro profesional
Precedente directo de DD-27 i y DD-30 k: `403` con `{"detail": {"codigo": "profesional_ajeno", "mensaje": "Solo podés consultar tu propia agenda"}}` para otro profesional exista o no, evaluado antes que la validez del rango (como DD-30 a lo evalúa antes que la forma del bloqueo), sin tocar la base. Omitirlo o informar el suyo da su agenda. El mensaje es nuevo (`ProfesionalAjenoError(mensaje)` ya acepta uno por recurso, DD-30 o). El `sillon_id` del odontólogo restringe dentro de sus turnos: nunca ve un turno de otro profesional en un sillón compartido. **Alternativa descartada**: ignorar el `profesional_id` ajeno y devolver la propia agenda (oculta un error del cliente; DD-30 la descartó).

### D11 — Paciente embebido en el turno
DD-31 dejó a C-13 decidir cómo la agenda muestra el nombre del paciente. **Recomendado**: cada turno trae `paciente: {id, nombre, apellido}` (la forma de `PacienteResumenOut`), para ambos roles, en lugar de `paciente_id`. Son exactamente los campos que el odontólogo ya puede leer de los pacientes de sus turnos en cualquier estado (DD-31 a, c), así que no amplía su acceso; nunca documento, teléfono ni email. **Alternativas**: (a) solo `paciente_id` (la agenda de C-15 haría un `GET /pacientes/{id}` por turno); (b) `paciente_id` más `paciente_nombre` plano; (c) embeber también nombres de profesional, sillón y prestación (ambos roles los leen de los catálogos, que son pocos y cambian poco). El resto de los campos es el de `TurnoOut` (incluidos `creado_por` y `motivo_cancelacion`).

### D12 — Orden y paginación
`turnos` y `bloqueos` por `inicio` y después `id`, como `GET /bloqueos` y el `409 bloqueo_con_turnos`. Sin paginación: D4 acota a una semana, que para 1 a 5 profesionales son a lo sumo algunos cientos de turnos.

### D13 — Filtro con un id inexistente
Para la recepcionista, un `profesional_id` o `sillon_id` que no existe da `200` con lo que corresponda vacío, como `GET /bloqueos` (DD-30 k). Un id mal formado da el `422` de validación. Profesionales y sillones desactivados conservan su agenda (DD-26 g), así que el filtro no mira `activo`.

### D14 — Sin migración
Los índices `(profesional_id, inicio)` y `(sillon_id, inicio)` de `turno` y `(profesional_id, inicio)` de `bloqueo` sirven a `inicio < fin_del_rango` con el filtro de igualdad. La cabeza de Alembic sigue en `010`. Ver Risks sobre la cota inferior.

### D15 — Lectura sin locks
La consulta solo lee: no toma `FOR SHARE` ni `FOR UPDATE` y no entra en el contrato de lock de DD-30 m, que es para escritores. Turnos y bloqueos se leen en dos sentencias de la misma sesión en `READ COMMITTED`, así que entre ambas puede confirmarse otra escritura (por ejemplo, un turno cancelado y un bloqueo creado en su lugar) y la vista mezcla dos momentos separados por milisegundos. Para una vista de lectura que se refresca es aceptable y no justifica `REPEATABLE READ`.

### D16 — Capas y módulos
- `app/domain/agenda.py` (puro, sin base ni HTTP): `MAX_DIAS_AGENDA = 7`; `RangoInvalidoError` (`codigo = "rango_invalido"`); una función que valida `desde`/`hasta` y devuelve el `Intervalo` UTC (medianoche local con `datetime.combine(..., tzinfo=ZoneInfo(DEFAULT_TIMEZONE))` y `to_utc`, sin desfasaje fijo, SU-08); una función que resuelve el profesional según el rol (odontólogo: el suyo o `ProfesionalAjenoError`; recepcionista: el filtro tal cual, `None` = todos); y el dato de salida `TurnoDeAgenda` (los campos de `TurnoRegistrado` más el nombre y apellido del paciente).
- `app/application/consulta_agenda.py`: `ConsultarAgenda.ejecutar(usuario, desde, hasta, profesional_id, sillon_id)` resuelve primero el profesional (`403`), después el rango (`422`), y consulta los dos repositorios. Devuelve un objeto con las dos listas.
- `RepositorioTurnos.listar_en(intervalo, profesional_id, sillon_id)`: `SELECT` de `turno` con `JOIN paciente`, criterio `[)`, filtros opcionales, orden `inicio, id`. `RepositorioBloqueos.listar_en(intervalo, profesional_id)`: lo mismo sobre `bloqueo`.
- `api/turnos.py`: `GET ""` con `UsuarioDeAmbosRoles`, `desde: date` y `hasta: date` obligatorios y los dos filtros `UUID | None`, con descripciones en el OpenAPI; `AgendaOut`, `TurnoAgendaOut` (reusa `PacienteResumenOut`) y `BloqueoOut` importado de `api/bloqueos.py`; manejador de `RangoInvalidoError` en `registrar_manejadores`. Las rutas de escritura no cambian.
- Orden de evaluación: autenticación y rol (`401`) → validación de los parámetros (`422` de FastAPI) → profesional según el rol (`403`) → rango (`422 rango_invalido`) → consulta. FastAPI resuelve las dependencias antes de levantar los errores de los parámetros (ya probado en C-06 para path y body).

### D17 — Sin auditoría
RN-CU-01 audita cambios de turno. Una consulta no modifica nada y no se registra.

## Risks / Trade-offs

- [D7 contradice el texto de `CHANGES.md` y del Flujo 7] → se presenta como decisión del usuario; aprobada la recomendación, la tarea 8.2 corrige ambos textos para que la KB no quede con dos verdades.
- [La condición `fin > inicio_del_rango` no usa índice: con `inicio < fin_del_rango` el índice recorre toda la historia del profesional anterior al fin del rango] → aceptable para el volumen de un consultorio (miles de turnos por año). Una cota `inicio >= inicio_del_rango - 480 min` sería correcta solo si la base garantizara la duración máxima (hoy no hay CHECK en `turno`) y no sirve para bloqueos, que no tienen largo máximo. Si el volumen real lo pidiera, un índice GiST sobre `tstzrange(inicio, fin)` es un change aislado.
- [Un cancelado y un programado en el mismo horario (D6)] → escenario explícito en el spec; C-15 decide cómo mostrarlos.
- [`date` de Pydantic en modo laxo acepta más formas que `YYYY-MM-DD` (por ejemplo, un timestamp Unix de medianoche)] → no cambia el resultado (la fecha es la misma); el spec solo exige aceptar `YYYY-MM-DD` y rechazar fechas mal formadas o inexistentes. Si se quisiera el formato estricto, un patrón sobre el texto antes de parsear.
- [`datetime.combine` con medianoche en una zona con horario de verano puede caer en un hueco] → Argentina no lo usa hoy (SU-08); se usa `zoneinfo` igual, y un unit test fija la conversión de la medianoche local.
- [El orden por `id` (UUID) ante el mismo `inicio` no es cronológico de alta] → solo desempata y es estable; nadie depende de él.
- [Conflicto de merge con C-12/C-14 en `api/turnos.py`] → C-12 está archivado y C-14 no toca el backend; sin migración, no hay renumeración.

## Migration Plan

Sin migración. Despliegue: merge del PR (la ruta es aditiva y ningún contrato existente cambia). Rollback: revertir el merge; ningún dato depende de esta ruta.

## Open Questions

- Ninguna. Las decisiones D1-D4, D6-D9 y D11 fueron aprobadas por el usuario el 2026-11-09.
- La pregunta abierta de `10_preguntas_abiertas.md` sobre la lectura del estado de los recordatorios **no** se resuelve en C-13 (no figura en su scope) y sigue abierta para otro change o el backlog.
