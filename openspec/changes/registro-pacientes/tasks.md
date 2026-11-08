# Tasks

> Governance BAJO, pero con datos personales: las decisiones **[A confirmar]** de `design.md` (D1, D2, D3, D5, D6, D7, D8, D11, D13, D14, D15, D16 y D18) deben estar aprobadas por el usuario antes de empezar. Estas tareas asumen las opciones recomendadas; si alguna cambia, primero `/opsx:update`.
>
> TDD estricto: en cada tarea RED (test que falla, verificado ejecutándolo) → GREEN (mínimo código) → triangular → refactor con tests en verde. Unit tests de dominio sin BD; todo test de persistencia contra PostgreSQL real en contenedor (nunca SQLite ni mocks de la base). Solo datos ficticios. Skills: `fastapi-python`, `python-testing-patterns`, `tdd`.
>
> **Sin migración** (design D9): ninguna tarea toca `backend/alembic/versions/`.

## 1. Preparación

- [ ] 1.1 Safety net: correr `pytest` completo contra la BD de test y registrar el baseline en verde; si algo falla, frenar y reportarlo como falla preexistente
- [ ] 1.2 Comprobar en `design.md` que ninguna decisión siga **[A confirmar]** sin aprobación y que `revisar-escenarios registro-pacientes` no tenga hallazgos BLOQUEANTE o MAYOR abiertos; si no, frenar

## 2. Dominio de pacientes (sin BD)

- [ ] 2.1 RED→GREEN: `tests/unit/test_dominio_pacientes.py` — `terminos_busqueda` separa por espacios, pliega mayúsculas, acentos y `ñ` con la tabla única (D6), normaliza a NFC y devuelve lista vacía para `None`, `""` y solo espacios; verificar con `pytest tests/unit/test_dominio_pacientes.py`
- [ ] 2.2 RED→GREEN: `email_valido` (D16) acepta `carla@example.com` y rechaza sin `@`, con dos `@`, con espacios internos, `@example.com` y `carla@`; verificar con el mismo archivo de tests
- [ ] 2.3 RED→GREEN: `PacienteAjenoError` con su mensaje y `TipoRecurso.PACIENTE = "paciente"`; verificar con los tests de dominio y `pytest tests/unit` en verde

## 3. Repositorio de pacientes

- [ ] 3.1 RED→GREEN: `tests/integration/test_repositorio_pacientes.py` — `RepositorioPacientes.buscar` con `DEFINICION_PACIENTE`: orden apellido, nombre e `id`, inactivos incluidos, coincidencia parcial por cada campo, AND entre términos y plegado en ambos sentidos (D5, D6, D7); verificar con ese archivo en verde
- [ ] 3.2 RED→GREEN: `buscar` escapa `%`, `_` y `\`, y aplica `limite` y `desplazamiento` después del orden, con páginas sin repetidos ante apellido y nombre iguales (D5, D8); verificar con el mismo archivo
- [ ] 3.3 RED→GREEN: `tiene_turno_de(paciente_id, profesional_id)` — verdadero con un turno propio `programado` o cancelado, también pasado; falso con turnos solo de otro profesional, sin turnos o con un id inexistente (D3, D4); verificar con el mismo archivo

## 4. Alta y validaciones

- [ ] 4.1 RED→GREEN: `tests/integration/test_api_pacientes.py` — `POST /pacientes` y registro del router en `create_app` (requisito "Alta de paciente"), con el conjunto exacto de claves; hacer públicas las bases `Entrada` y `Cambios` de `recursos.py`; verificar con ese archivo y los tests de recursos en verde
- [ ] 4.2 RED→GREEN: requisito "Campos mínimos y textos normalizados": obligatorios, solo espacios, largo excedido y máximo aceptado, recorte, email en blanco a nulo, documento y teléfono sin formato, y `U+0000` con `422` (D15); verificar con el mismo archivo
- [ ] 4.3 RED→GREEN: requisito "Formato mínimo del email" en alta y edición, incluido el email repetido entre pacientes (D16); verificar con el mismo archivo

## 5. Documento único

- [ ] 5.1 RED→GREEN: requisito "Documento único" en alta, en edición y con un paciente desactivado: `409 recurso_duplicado` con `campo = "documento"` por el nombre `uq_paciente_documento` (D10); verificar con `test_api_pacientes.py`
- [ ] 5.2 RED→GREEN: `tests/integration/test_concurrencia_pacientes.py` — escenario "Altas simultáneas con el mismo documento", con `motor_concurrente` y una primera transacción sin confirmar; el segundo responde `409`, no `500`, de forma determinista; verificar corriendo el archivo varias veces

## 6. Edición

- [ ] 6.1 RED→GREEN: requisito "Edición parcial de un paciente": campo único, corrección del documento con turno intacto, quitar email, nulos en obligatorios, texto en blanco, body vacío, campo desconocido, paciente desactivado y `404` (D11); verificar con `test_api_pacientes.py`
- [ ] 6.2 RED→GREEN: requisito "Estado de actividad del paciente no editable" en `POST` y `PATCH`; verificar con el mismo archivo

## 7. Listado, búsqueda y paginación

- [ ] 7.1 RED→GREEN: `tests/integration/test_api_consulta_pacientes.py` — requisito "Listado de pacientes" para la recepcionista; verificar con ese archivo
- [ ] 7.2 RED→GREEN: requisito "Búsqueda de pacientes", los 13 escenarios, incluidos comodines, `q` en blanco, 100 y 101 caracteres y `%00` con `422` (D5, D6); verificar con el mismo archivo
- [ ] 7.3 RED→GREEN: requisito "Paginación del listado de pacientes": default, páginas, búsqueda paginada, máximo y fuera de rango (D8); verificar con el mismo archivo

## 8. Detalle y permisos

- [ ] 8.1 RED→GREEN: requisito "Detalle de un paciente para la recepcionista": completo, desactivado, `404` y `422`; verificar con `test_api_consulta_pacientes.py`
- [ ] 8.2 RED→GREEN: `tests/integration/test_api_rbac_pacientes.py` — requisito "Lectura mínima del odontólogo", afirmando el conjunto exacto de claves `id`, `nombre` y `apellido` en los tres escenarios (D1, D3); verificar con ese archivo
- [ ] 8.3 RED→GREEN: requisito "Paciente ajeno para el odontólogo", con cuerpos idénticos para ajeno e inexistente, `422` y `401` (D4); verificar con el mismo archivo
- [ ] 8.4 RED→GREEN: requisitos "Escritura de pacientes reservada a la recepcionista" y "Listado y búsqueda reservados a la recepcionista", con rol antes que body, parámetros y existencia (D2); verificar con el mismo archivo

## 9. Desactivación

- [ ] 9.1 RED→GREEN: `tests/integration/test_api_desactivacion_pacientes.py` — requisito "Desactivación lógica de un paciente"; verificar con ese archivo
- [ ] 9.2 RED→GREEN: requisito "Un paciente desactivado no admite turnos nuevos": alta y reprogramación con `422 referencia_invalida`, sin tocar el código de turnos; verificar con el mismo archivo
- [ ] 9.3 RED→GREEN: requisito "Un paciente desactivado conserva sus turnos y recordatorios": turno intacto sin filas de auditoría nuevas (D19), cancelación, y recordatorio enviado por el worker real con `helpers_recordatorios` (D13); verificar con el mismo archivo
- [ ] 9.4 RED→GREEN: en `test_concurrencia_pacientes.py`, los dos escenarios de "Desactivación de paciente simultánea con un alta de turno" (D12), deterministas por orden de llegada; verificar corriendo el archivo varias veces

## 10. Protección de datos personales

- [ ] 10.1 RED→GREEN: `tests/integration/test_api_privacidad_pacientes.py` — requisito "Errores sin datos personales": manejador de `RequestValidationError` limitado a `/pacientes` (D17), con `POST /sillones` conservando `input`; verificar con ese archivo y `pytest tests/integration/test_api_sillones.py`
- [ ] 10.2 RED→GREEN: `tests/unit/test_filtro_log_acceso.py` — requisito "Log de acceso sin el texto buscado": el filtro recorta la query de `/pacientes` en un `LogRecord` con el formato de `uvicorn.access`, no toca otras rutas ni registros con otra forma (D18); verificar con ese archivo
- [ ] 10.3 RED→GREEN: un test con `with TestClient(create_app())` comprueba que el `lifespan` instala el filtro en `uvicorn.access` una sola vez; verificar además levantando `uvicorn` y revisando que un `GET /pacientes?q=FIC-0101` no deje "FIC-0101" en el log

## 11. KB, documentación y cierre

- [ ] 11.1 Registrar **DD-31** en `knowledge-base/09_decisiones_y_supuestos.md` con el estilo de DD-26/DD-27, tal como se aprobó, con alternativas descartadas y consecuencias (D14 y D15 explícitas); verificar que el texto coincide con `design.md`
- [ ] 11.2 Actualizar la KB: fila Pacientes de `02_descripcion_general.md`, fila Pacientes de la matriz de `03_actores_y_roles.md` (sin **Suposición**), `06` si cambia US-009 y "Preguntas resueltas" de `10_preguntas_abiertas.md`; sumar "Reactivación de pacientes" al backlog de `CHANGES.md`; verificar que no quedan menciones contradictorias con `grep -n "Pacientes" knowledge-base/0[23]*.md`
- [ ] 11.3 RED→GREEN: test sobre `/openapi.json` que afirma el conjunto exacto de rutas de `/pacientes` con sus métodos, sin `PUT` ni `DELETE`, y las descripciones de `q`, `limite` y `desplazamiento`; verificar con ese test
- [ ] 11.4 Verificar que no se tocó el aviso de `CLAUDE.md` y `AGENTS.md` y que siguen idénticos con `cmp CLAUDE.md AGENTS.md`; si se editó uno, editar el otro
- [ ] 11.5 Verificar que no hay migración nueva: `git diff --stat main... -- backend/alembic/versions` vacío y `alembic heads` en `010`
- [ ] 11.6 Verificación integral: `ruff format --check` y `ruff check` sin errores, `pytest` completo en verde (baseline de 1.1 más los nuevos) y `openspec validate registro-pacientes --strict` sin errores
- [ ] 11.7 Checkpoint FINAL_DIFF: consultar al agente `advisor` sobre `git diff main...` antes de declarar el Apply terminado; un veredicto BLOCK frena hasta la confirmación del usuario

## Workflow follow-up

- Correr `revisar-escenarios registro-pacientes` antes del Apply y corregir los hallazgos con `/opsx:update`.
- Archivar el change en la rama `feat/c-09-registro-pacientes` antes del merge (`/opsx:archive registro-pacientes`), confirmar que `openspec validate registro-pacientes --type spec --strict` pasa sobre el spec archivado, marcar `[x]` C-09 en `CHANGES.md` y abrir el PR para la revisión de Matías.
