# Tasks

> Governance MEDIO: las decisiones D1-D4, D6-D9 y D11 de `design.md` fueron **aprobadas por el usuario el 2026-11-09** con la opción recomendada. Estas tareas la asumen; si alguna cambia, primero `/opsx:update` (spec, design y tareas) y recién después el Apply.
>
> TDD estricto: en cada tarea RED (test que falla, verificado ejecutándolo) → GREEN (mínimo código) → triangular → refactor con tests en verde. Unit tests de dominio sin BD; todo test de persistencia contra PostgreSQL real en contenedor (nunca SQLite ni mocks de la base). Solo datos ficticios (nombres como "Carla Imaginaria", documentos y teléfonos inventados). Skills: `fastapi-python`, `python-testing-patterns`, `tdd`, `supabase-postgres-best-practices` (consulta por rango).
>
> En los tests de repositorio y de API, los turnos y bloqueos del escenario se insertan directamente con el ORM en la sesión de test (la consulta no depende de los validadores de alta), con `inicio` y `fin` con zona. Los fixtures que borran usuarios deben borrar antes sus bloqueos (FK `creado_por`, DD-30 n).
>
> **Sin migración** (design D14): ninguna tarea toca `backend/alembic/versions/`.

## 1. Preparación

- [x] 1.1 Safety net: correr `pytest` completo contra la BD de test y registrar el baseline en verde; si algo falla, frenar y reportarlo como falla preexistente
- [x] 1.2 Aprobación previa al Apply: el usuario aprueba o cambia D1-D4, D6-D9 y D11 de `design.md` (D7 corrige texto de la KB); registrar en `design.md` la fecha y la opción aprobada de cada una; verificar que la tabla de Decisions no tiene ninguna fila **Pendiente**
- [x] 1.3 Correr `revisar-escenarios agenda-diaria-semanal` y resolver con `/opsx:update` todo hallazgo BLOQUEANTE o MAYOR; verificar que `openspec/changes/agenda-diaria-semanal/revision-escenarios.md` no deja ninguno abierto y que `openspec validate agenda-diaria-semanal --strict` pasa

## 2. Dominio de la agenda (sin BD)

- [x] 2.1 RED→GREEN: `tests/unit/test_dominio_agenda.py` — la conversión del rango devuelve el `Intervalo` UTC `[desde 00:00 local, hasta + 1 día 00:00 local)`: `2026-10-08`/`2026-10-08` da `[2026-10-08T03:00Z, 2026-10-09T03:00Z)` y `2026-10-05`/`2026-10-11` da `[2026-10-05T03:00Z, 2026-10-12T03:00Z)`, calculado con `zoneinfo` (D2, requisito "Rango local convertido a instantes UTC"); verificar con `pytest tests/unit/test_dominio_agenda.py`
- [x] 2.2 RED→GREEN: `RangoInvalidoError` (`codigo = "rango_invalido"`) para `hasta < desde` y para 8 días; se aceptan 1 y 7 días (D4, requisito "Rango válido de hasta una semana"); verificar con el mismo archivo
- [x] 2.3 RED→GREEN: profesional según el rol (D10): el odontólogo sin filtro o con el suyo obtiene su `profesional_id`, con otro obtiene `ProfesionalAjenoError` con el mensaje "Solo podés consultar tu propia agenda"; la recepcionista obtiene el filtro tal cual o `None`; verificar con el mismo archivo y `pytest tests/unit` en verde
- [x] 2.4 RED→GREEN: `hasta = date.max` (`9999-12-31`) da `RangoInvalidoError` y no `OverflowError`; un rango válido en `9999-12-30` se acepta (D4, escenario "Fin de rango no representable"); verificar con `pytest tests/unit/test_dominio_agenda.py`

## 3. Consultas por intervalo en los repositorios

- [x] 3.1 RED→GREEN: `tests/integration/test_repositorio_agenda.py` — `RepositorioTurnos.listar_en(intervalo, profesional_id, sillon_id)` con criterio `[)`: excluye los contiguos a ambos bordes, incluye el que cruza un borde con su intervalo real, incluye programados y cancelados, devuelve el `nombre` y `apellido` del paciente (también desactivado) y ordena por `inicio` e `id` (D5, D6, D11, D12); verificar con ese archivo en verde
- [x] 3.2 RED→GREEN: filtros de `listar_en` de turnos: por profesional, por sillón (excluye los turnos sin sillón), combinados, e ids inexistentes con lista vacía (D9, D13); verificar con el mismo archivo
- [x] 3.3 RED→GREEN: `RepositorioBloqueos.listar_en(intervalo, profesional_id)` con criterio `[)`: bloqueo de varios días, bordes, superpuestos del mismo profesional sin fusionar, filtro por profesional y orden `inicio, id` (D5, D12); verificar con el mismo archivo y con `tests/integration/test_repositorio_bloqueos.py` sin cambios en verde

## 4. Caso de uso

- [x] 4.1 RED→GREEN: `tests/unit/test_consulta_agenda.py` con repositorios falsos nuevos en `tests/fakes.py` (hoy solo tiene colas, relojes y emisores), que registran los argumentos recibidos — `ConsultarAgenda.ejecutar` pasa el intervalo UTC y los filtros a ambos repositorios, el `sillon_id` solo al de turnos (D9), y devuelve las dos listas; verificar con ese archivo
- [x] 4.2 RED→GREEN: orden de evaluación (D16): un odontólogo con profesional ajeno y rango invertido obtiene `ProfesionalAjenoError` y no se consulta ningún repositorio; un rango inválido tampoco consulta; verificar con el mismo archivo

## 5. Ruta `GET /turnos`

- [x] 5.1 RED→GREEN: `tests/integration/test_api_agenda.py` — requisito "Consulta de la agenda por rango de días": ruta `GET ""` en `api/turnos.py` con `UsuarioDeAmbosRoles`, respuesta con claves exactas `turnos` y `bloqueos` (D1), día vacío, y `422` por fecha faltante, mal formada o inexistente; las rutas de escritura siguen exigiendo `recepcionista`; verificar con ese archivo y `tests/integration/test_api_rbac_turnos.py` en verde
- [x] 5.2 RED→GREEN: requisito "Rango válido de hasta una semana" de punta a punta: agenda semanal, rango invertido y de 8 días con `422` y código `rango_invalido` (manejador en `registrar_manejadores`); verificar con el mismo archivo
- [x] 5.3 RED→GREEN: requisitos "Rango local convertido a instantes UTC" e "Inclusión por superposición con el rango": los tres escenarios de zona horaria (22:30 local, 00:00 local, 02:00Z-02:59Z) y los cuatro de bordes y bloqueos de varios días; verificar con el mismo archivo
- [x] 5.4 RED→GREEN: requisitos "Filtro por profesional" y "Filtro por sillón" para la recepcionista, incluidos el profesional desactivado, los ids inexistentes y los mal formados (D8, D9, D13); verificar con el mismo archivo
- [x] 5.5 RED→GREEN: requisitos "Turnos en cualquier estado y fecha", "Datos de cada turno de la agenda" y "Datos de cada bloqueo de la agenda": cancelado y programado en el mismo horario, día pasado con reloj fijo, claves exactas, hora local `-03:00` (D7), `paciente` con solo `id`, `nombre` y `apellido` y sin documento, teléfono ni email en el cuerpo, turno sin sillón y paciente desactivado; verificar con el mismo archivo
- [x] 5.6 RED→GREEN: requisito "Orden de la agenda" entre profesionales y con el mismo inicio; verificar con el mismo archivo
- [x] 5.7 RED→GREEN: test sobre `/openapi.json`: `/turnos` expone exactamente `get` y `post`, y `desde`, `hasta`, `profesional_id` y `sillon_id` tienen descripción (formato de fecha local incluido, aislamiento del odontólogo en `profesional_id`); verificar con ese test
- [x] 5.8 RED→GREEN: `GET /turnos?desde=9999-12-25&hasta=9999-12-31` da `422` con código `rango_invalido` y no `500` (escenario "Fin de rango no representable"); verificar con `pytest tests/integration/test_api_agenda.py`

## 6. Aislamiento del odontólogo y autenticación

- [x] 6.1 RED→GREEN: `tests/integration/test_api_rbac_agenda.py` — requisito "El odontólogo solo consulta su agenda": sin filtro, con el suyo, con otro y con un UUID inexistente (`403 profesional_ajeno`, cuerpos idénticos), sillón compartido, y `403` antes que el rango inválido (RN-AU-02, D10); verificar con ese archivo
- [x] 6.2 RED→GREEN: requisito "Agenda accesible solo con autenticación": sin token, con parámetros inválidos sin token (`401`, no `422`) y con token vencido, con `WWW-Authenticate: Bearer` y código `no_autenticado`; verificar con el mismo archivo

## 7. `service-health`

- [x] 7.1 Verificar que `backend/tests/integration/test_health.py` ya no usa `/turnos` como ruta inexistente y que su parametrización incluye `/consultorios` (escenario modificado del delta `service-health`); correr `pytest tests/integration/test_health.py` en verde

## 8. KB, documentación y cierre

- [x] 8.1 Registrar **DD-32** en `knowledge-base/09_decisiones_y_supuestos.md` con el estilo de DD-30/DD-31, con las decisiones aprobadas en 1.2 (D1-D4, D6-D11 y el código `rango_invalido`), alternativas descartadas y consecuencias; verificar que cada literal coincide con la tabla de `design.md`
- [x] 8.2 Actualizar la KB: fila Turnos de `02_descripcion_general.md` (parámetros `desde`, `hasta`, `profesional_id`, `sillon_id` y roles), Flujo 7 de `07_flujos_principales.md` y el scope de C-13 en `CHANGES.md` según D7, US-008 de `06` si cambia algún criterio, y "Preguntas resueltas" de `10_preguntas_abiertas.md` (la pregunta de los recordatorios sigue abierta); verificar con `grep -n "en UTC" knowledge-base/07_flujos_principales.md CHANGES.md` que no queda una contradicción con D7
- [x] 8.3 Verificar que `CLAUDE.md` y `AGENTS.md` siguen idénticos con `cmp CLAUDE.md AGENTS.md`; si se editó uno, editar el otro
- [x] 8.4 Verificar que no hay migración nueva: `git diff --stat main... -- backend/alembic/versions` vacío y `alembic heads` en `010`
- [x] 8.5 Verificación integral: `ruff format --check` y `ruff check` sin errores, `pytest` completo en verde (baseline de 1.1 más los nuevos) y `openspec validate agenda-diaria-semanal --strict` sin errores
- [x] 8.6 Checkpoint FINAL_DIFF: consultar al agente `advisor` sobre `git diff main...` antes de declarar el Apply terminado; un veredicto BLOCK frena hasta la confirmación del usuario. FINAL_DIFF advisor: CONCERNS atendidas (overflow 9999-12-31, rango DD en CLAUDE/AGENTS, tipos, docstring)

## Workflow follow-up

- Archivar el change en la rama `feat/c-13-agenda-diaria-semanal` antes del merge (`/opsx:archive agenda-diaria-semanal`), confirmar que `openspec validate consulta-agenda --type spec --strict` pasa sobre el spec nuevo, marcar `[x]` C-13 en `CHANGES.md` y abrir el PR para la revisión de Nico. En la descripción del PR, avisar a C-14/C-15 la forma de la respuesta (D1), la zona de los instantes (D7) y el paciente embebido (D11).
