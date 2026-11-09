# Tasks

> Governance BAJO, pero con datos personales: las decisiones de `design.md` que no surgen de la KB (D1, D2, D3, D5, D6, D7, D8, D11, D13, D14, D15, D16, D17 y D18) fueron aprobadas por el usuario el 2026-11-09. Estas tareas asumen esas opciones; si alguna cambia, primero `/opsx:update`.
>
> TDD estricto: en cada tarea RED (test que falla, verificado ejecutándolo) → GREEN (mínimo código) → triangular → refactor con tests en verde. Unit tests de dominio sin BD; todo test de persistencia contra PostgreSQL real en contenedor (nunca SQLite ni mocks de la base). Solo datos ficticios. Skills: `fastapi-python`, `python-testing-patterns`, `tdd`.
>
> **Sin migración** (design D9): ninguna tarea toca `backend/alembic/versions/`.

## 1. Preparación

- [x] 1.1 Safety net: correr `pytest` completo contra la BD de test y registrar el baseline en verde; si algo falla, frenar y reportarlo como falla preexistente
- [x] 1.2 Aprobación previa al Apply: el usuario aprobó las decisiones de `design.md` el 2026-11-09 (se registran como DD-31 en 11.1), y los hallazgos H1 a H11 de `revisar-escenarios registro-pacientes` se resolvieron con `/opsx:update` ese mismo día; no quedan BLOQUEANTE ni MAYOR abiertos

## 2. Dominio de pacientes (sin BD)

- [x] 2.1 RED→GREEN: `tests/unit/test_dominio_pacientes.py` — `terminos_busqueda` separa por espacios, pliega mayúsculas, acentos y `ñ` con la tabla única (D6), normaliza a NFC y devuelve lista vacía para `None`, `""` y solo espacios; verificar con `pytest tests/unit/test_dominio_pacientes.py`
- [x] 2.2 RED→GREEN: `email_valido` (D16) acepta `carla@example.com` y rechaza sin `@`, con dos `@`, con espacios internos, `@example.com` y `carla@`; verificar con el mismo archivo de tests
- [x] 2.3 RED→GREEN: `PacienteAjenoError` con su mensaje y `TipoRecurso.PACIENTE = "paciente"`; verificar con los tests de dominio y `pytest tests/unit` en verde

## 3. Repositorio de pacientes

- [x] 3.1 RED→GREEN: `tests/integration/test_repositorio_pacientes.py` — `RepositorioPacientes.buscar` con `DEFINICION_PACIENTE`: orden apellido, nombre e `id`, inactivos incluidos, coincidencia parcial por cada campo, AND entre términos y plegado en ambos sentidos (D5, D6, D7); verificar con ese archivo en verde
- [x] 3.2 RED→GREEN: `buscar` escapa `%`, `_` y `\`, y aplica `limite` y `desplazamiento` después del orden, con páginas sin repetidos ante apellido y nombre iguales (D5, D8); verificar con el mismo archivo
- [x] 3.3 RED→GREEN: `tiene_turno_de(paciente_id, profesional_id)` — verdadero con un turno propio `programado` o cancelado, también pasado; falso con turnos solo de otro profesional, sin turnos o con un id inexistente (D3, D4); verificar con el mismo archivo

## 4. Alta y validaciones

- [x] 4.1 RED→GREEN: `tests/integration/test_api_pacientes.py` — `POST /pacientes` y registro del router en `create_app` (requisito "Alta de paciente"), con el conjunto exacto de claves; hacer públicas las bases `Entrada` y `Cambios` de `recursos.py`; verificar con ese archivo y los tests de recursos en verde
- [x] 4.2 RED→GREEN: requisito "Campos mínimos y textos normalizados": obligatorios, solo espacios, largo excedido y máximo aceptado en los cinco textos, recorte, email en blanco a nulo, documento y teléfono sin formato, y `U+0000` con `422` en cada texto, en alta y en edición (D15); verificar con el mismo archivo
- [x] 4.3 RED→GREEN: requisito "Formato mínimo del email" en alta y edición, incluido el email repetido entre pacientes (D16); verificar con el mismo archivo

## 5. Documento único

- [x] 5.1 RED→GREEN: requisito "Documento único" en alta, en edición y con un paciente desactivado: `409 recurso_duplicado` con `campo = "documento"` por el nombre `uq_paciente_documento` (D10); verificar con `test_api_pacientes.py`
- [x] 5.2 RED→GREEN: `tests/integration/test_concurrencia_pacientes.py` — escenario "Altas simultáneas con el mismo documento", con `motor_concurrente` y una primera transacción sin confirmar; el segundo responde `409`, no `500`, de forma determinista; verificar corriendo el archivo varias veces

## 6. Edición

- [x] 6.1 RED→GREEN: requisito "Edición parcial de un paciente": campo único, corrección del documento con turno intacto (con el reloj fijado (`get_reloj` reemplazado, como en `test_api_desactivacion_recursos.py`)), quitar email, nulos en obligatorios, texto en blanco, body vacío, campo desconocido, paciente desactivado y `404` (D11); verificar con `test_api_pacientes.py`
- [x] 6.2 RED→GREEN: requisito "Estado de actividad del paciente no editable" en `POST` y `PATCH`; verificar con el mismo archivo

## 7. Listado, búsqueda y paginación

- [x] 7.1 RED→GREEN: `tests/integration/test_api_consulta_pacientes.py` — requisito "Listado de pacientes" para la recepcionista; verificar con ese archivo
- [x] 7.2 RED→GREEN: requisito "Búsqueda de pacientes", los 13 escenarios, incluidos comodines, `q` en blanco, 100 y 101 caracteres y `%00` con `422` (D5, D6); verificar con el mismo archivo
- [x] 7.3 RED→GREEN: requisito "Paginación del listado de pacientes": default, páginas, búsqueda paginada, máximo y fuera de rango (D8); verificar con el mismo archivo

## 8. Detalle y permisos

- [x] 8.1 RED→GREEN: requisito "Detalle de un paciente para la recepcionista": completo, desactivado, `404` y `422`; verificar con `test_api_consulta_pacientes.py`
- [x] 8.2 RED→GREEN: `tests/integration/test_api_rbac_pacientes.py` — requisito "Lectura mínima del odontólogo", afirmando el conjunto exacto de claves `id`, `nombre` y `apellido` en los tres escenarios (D1, D3); verificar con ese archivo
- [x] 8.3 RED→GREEN: requisito "Paciente ajeno para el odontólogo", con cuerpos idénticos para ajeno e inexistente, `422` y `401` (D4); verificar con el mismo archivo
- [x] 8.4 RED→GREEN: requisitos "Escritura de pacientes reservada a la recepcionista" y "Listado y búsqueda reservados a la recepcionista", con rol antes que la validación del contenido del body, los parámetros y la existencia (D2); verificar con el mismo archivo

## 9. Desactivación

- [x] 9.1 RED→GREEN: `tests/integration/test_api_desactivacion_pacientes.py` — requisito "Desactivación lógica de un paciente"; verificar con ese archivo
- [x] 9.2 RED→GREEN: requisito "Un paciente desactivado no admite turnos nuevos": alta y reprogramación con `422 referencia_invalida`, con el reloj fijado (`get_reloj` reemplazado, como en `test_api_desactivacion_recursos.py`), sin tocar el código de turnos; verificar con el mismo archivo
- [x] 9.3 RED→GREEN: requisito "Un paciente desactivado conserva sus turnos y recordatorios": turno intacto sin filas de auditoría nuevas (D19) y cancelación, con el reloj fijado (`get_reloj` reemplazado, como en `test_api_desactivacion_recursos.py`), y recordatorio enviado por el worker real con el `RelojManual` y `ciclo_a` de `helpers_recordatorios` (D13); verificar con el mismo archivo
- [x] 9.4 RED→GREEN: en `test_concurrencia_pacientes.py`, los tres escenarios de "Desactivación de paciente simultánea con un alta o una reprogramación de turno" (D12), con reloj fijo y deterministas por orden de llegada, como `test_concurrencia_desactivacion.py`; verificar corriendo el archivo varias veces

## 10. Protección de datos personales

- [ ] 10.1 RED→GREEN: `tests/integration/test_api_privacidad_pacientes.py` — requisito "Errores sin datos personales": manejador de `RequestValidationError` limitado a `/pacientes` y `/pacientes/{id}` (D17), incluidos `PATCH` y el identificador mal formado, con `POST /sillones` conservando `input`; verificar con ese archivo y `pytest tests/integration/test_api_sillones.py`
- [ ] 10.2 RED→GREEN: `tests/unit/test_filtro_log_acceso.py` — requisito "Log de acceso sin el texto buscado": unidad del filtro: recorta la query de `/pacientes` en un `LogRecord` con la forma de `uvicorn.access`, y no toca otras rutas ni falla ante registros con otra forma (D18); verificar con ese archivo
- [ ] 10.3 RED→GREEN: un test con `with TestClient(create_app())` comprueba que el `lifespan` instala el filtro en `uvicorn.access` una sola vez; verificar con ese test
- [ ] 10.4 RED→GREEN: `tests/integration/test_log_acceso_uvicorn.py` — los dos escenarios de "Log de acceso sin el texto buscado": levanta `uvicorn app.main:app` en un subproceso (mismos argumentos que el `CMD` del `Dockerfile`, salvo host `127.0.0.1` y un puerto libre, con `PYTHONUNBUFFERED=1`), envía los pedidos sin token con `httpx` y lee su salida; afirma que la línea de acceso existe y no contiene "FIC-0101", y que `/bloqueos` conserva la query. Falla si `uvicorn` cambia el formato de `record.args` (D18, Risks). Sin dependencias nuevas; verificar con ese archivo

## 11. KB, documentación y cierre

- [ ] 11.1 Registrar **DD-31** en `knowledge-base/09_decisiones_y_supuestos.md` con el estilo de DD-26/DD-27, tal como se aprobó el 2026-11-09, con los literales (a) a (o) de la tabla de `design.md`, incluidos D17 como decisión aprobada y el código `paciente_ajeno`, con alternativas descartadas y consecuencias (D14 con la limitación corregida y D15, explícitas); verificar que el texto coincide con `design.md`
- [ ] 11.2 Actualizar la KB: fila Pacientes de `02_descripcion_general.md`, fila Pacientes de la matriz de `03_actores_y_roles.md` (sin **Suposición**), `06` si cambia US-009 y "Preguntas resueltas" de `10_preguntas_abiertas.md`; sumar "Reactivación de pacientes" al backlog de `CHANGES.md`, fuera de alcance según D14; verificar que no quedan menciones contradictorias con `grep -n "Pacientes" knowledge-base/0[23]*.md`
- [ ] 11.3 RED→GREEN: test sobre `/openapi.json` que afirma el conjunto exacto de rutas de `/pacientes` con sus métodos, sin `PUT` ni `DELETE`, y las descripciones de `q`, `limite` y `desplazamiento`; verificar con ese test
- [ ] 11.4 Verificar que no se tocó el aviso de `CLAUDE.md` y `AGENTS.md` y que siguen idénticos con `cmp CLAUDE.md AGENTS.md`; si se editó uno, editar el otro
- [ ] 11.5 Verificar que no hay migración nueva: `git diff --stat main... -- backend/alembic/versions` vacío y `alembic heads` en `010`
- [ ] 11.6 Verificación integral: `ruff format --check` y `ruff check` sin errores, `pytest` completo en verde (baseline de 1.1 más los nuevos) y `openspec validate registro-pacientes --strict` sin errores
- [ ] 11.7 Checkpoint FINAL_DIFF: consultar al agente `advisor` sobre `git diff main...` antes de declarar el Apply terminado; un veredicto BLOCK frena hasta la confirmación del usuario

## Workflow follow-up

- `revisar-escenarios registro-pacientes` ya corrió y sus hallazgos se corrigieron con `/opsx:update` el 2026-11-09 (H12 no se aplicó).
- Archivar el change en la rama `feat/c-09-registro-pacientes` antes del merge (`/opsx:archive registro-pacientes`), confirmar que `openspec validate registro-pacientes --type spec --strict` pasa sobre el spec archivado, marcar `[x]` C-09 en `CHANGES.md` y abrir el PR para la revisión de Matías. En la descripción del PR, recordarle que se espera que la agenda de C-13 lleve el nombre del paciente en su propia respuesta y que C-13 debe definirla (design, "Nota de coordinación con C-13"); no es un requisito de C-09.
