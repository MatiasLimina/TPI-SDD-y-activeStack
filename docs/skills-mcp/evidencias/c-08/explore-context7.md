# Evidencia — Context7 en la preparación de C-08

Fecha: 2026-11-02 · Cliente: Claude Code (Windows 11), durante el `/opsx:propose` de C-08 `gestion-recursos-consultorio` · Servidor: `context7` del `.mcp.json` del proyecto

Las preguntas son genéricas: no llevan código, datos ni secretos del proyecto (límite de `CLAUDE.md`). Para cada una se registra la biblioteca, un resumen del resultado y la decisión de `design.md` que respalda. Los fragmentos se resumen; las fuentes están enlazadas.

## 1. Pydantic — restricciones numéricas de un entero

- **Resolución**: `resolve-library-id("Pydantic")` → `/websites/pydantic_dev_validation` (documentación oficial, reputación High, versiones 1.10 y 2.12).
- **Pregunta** (`query-docs`): restricciones `gt`, `le` y `multiple_of` para enteros, qué tipo de error de validación producen y si un `float` se acepta para un campo `int`.
- **Resultado (resumen)**: `Field(multiple_of=5)` produce un error de tipo `multiple_of` y `Field(le=10)` uno `less_than_equal`, con `type`, `loc`, `msg`, `input` y `ctx` en la lista de errores. Un campo `int` acepta `10.0` (lo convierte en `10`) y rechaza `10.2` con `int_from_float`. Fuentes: <https://pydantic.dev/docs/validation/latest/errors/validation_errors>, <https://pydantic.dev/docs/validation/latest/get-started/migration>.
- **Decisión que respalda**: `design.md` D2 y §2. La duración de la prestación **no** se valida con `Field(gt=0, multiple_of=5, le=480)`: el `422` tendría la forma de lista por defecto de FastAPI con tipos `multiple_of`/`less_than_equal`, distinta del `{"detail": {"codigo": "duracion_invalida"}}` que ya devuelven los turnos, y la regla quedaría en dos lugares. Se valida en el dominio con una sola función compartida. El caso `45.0` aceptado y `45.5` rechazado pasa a ser un test (tarea 6.2).

## 2. Alembic — CHECK en una migración con convención de nombres

- **Resolución**: `resolve-library-id("Alembic")` → `/websites/alembic_sqlalchemy` (documentación oficial, reputación High).
- **Pregunta** (`query-docs`): `op.create_check_constraint` y `op.drop_constraint(type_="check")` en `upgrade`/`downgrade`, y cómo se aplica la convención de nombres con `op.f()`.
- **Resultado (resumen)**: `op.create_check_constraint(nombre, tabla, condición)` acepta la condición como texto o expresión. Si la convención usa `%(constraint_name)s`, un nombre pasado como texto simple **se vuelve a pasar por la convención** (por ejemplo `some_check_const` → `ck_t1_some_check_const`); `op.f("...")` marca el nombre como ya convertido y lo deja fijo, tanto al crear como al borrar. Fuentes: <https://alembic.sqlalchemy.org/en/latest/naming.html>, <https://alembic.sqlalchemy.org/en/latest/ops.html>.
- **Decisión que respalda**: `design.md` D3 y §3. La migración `006` crea y borra `ck_prestacion_duracion_min_multiplo_5` y `ck_prestacion_duracion_min_maxima` con `op.f()` y el nombre completo, igual que `002..005`; sin `op.f()` la convención de `base.py` (`ck_%(table_name)s_%(constraint_name)s`) duplicaría el prefijo.

## 3. FastAPI — actualización parcial con `PATCH`

- **Resolución**: `resolve-library-id("FastAPI")` → `/websites/fastapi_tiangolo` (documentación oficial, reputación High).
- **Pregunta** (`query-docs`): `PATCH` parcial con `model_dump(exclude_unset=True)` y `model_copy(update=...)`, y cómo se distingue un `null` explícito de un campo omitido.
- **Resultado (resumen)**: el tutorial oficial usa `model_dump(exclude_unset=True)` para quedarse solo con los campos enviados y aplicarlos sobre el valor guardado. Las notas de la versión 0.151.0 (2026-10-20) agregan que los parámetros `Body` sueltos distinguen ahora `null` explícito de valor omitido: un tipo no anulable rechaza `null` aunque tenga default. Fuentes: <https://fastapi.tiangolo.com/tutorial/body-updates/>, <https://fastapi.tiangolo.com/release-notes/>.
- **Decisión que respalda**: `design.md` D4 y §2. La edición toma solo los campos de `model_fields_set` (lo mismo que `exclude_unset=True`) y un `model_validator` rechaza `null` en los campos obligatorios, como ya hace `ReprogramacionIn`. El cambio de la 0.151.0 afecta a parámetros `Body` sueltos, no a los modelos: igual queda como riesgo y la tarea 1.2 verifica la versión instalada.

## 4. SQLAlchemy — lectura con lock compartido

- **Resolución**: `resolve-library-id("SQLAlchemy")` → `/websites/sqlalchemy_en_20_orm` (documentación oficial de la 2.0, reputación High).
- **Pregunta** (`query-docs`): parámetros `with_for_update` (lock compartido) y `populate_existing` de `Session.get`.
- **Resultado (resumen)**: `Session.get(entidad, id, populate_existing=..., with_for_update=...)`; `with_for_update` acepta `True` o un diccionario con los mismos flags que `Query.with_for_update()` (por ejemplo `read=True`, que en PostgreSQL emite `FOR SHARE`); `populate_existing=True` emite siempre el `SELECT` y refresca el objeto aunque ya esté en el identity map. Fuente: <https://docs.sqlalchemy.org/en/20/orm/session_api.html>.
- **Decisión que respalda**: `design.md` D10 y §4. `cargar_referencias` lee profesional, paciente, prestación y sillón con `with_for_update={"read": True}, populate_existing=True`: el alta espera a una desactivación en curso y relee la fila confirmada, lo que hace cumplir el requisito "Desactivación simultánea con un alta o una reprogramación de turno" (tarea 8.4).

## Lo que Context7 no decide

Las cuatro respuestas fijan **cómo** usar cada biblioteca; ninguna decide reglas del dominio. Los códigos `409 recurso_duplicado`, la desactivación idempotente, la ausencia de reactivación y qué pasa con los turnos futuros de un recurso desactivado salen de la KB o de las decisiones D5, D6, D7, D9, D11 y D12 de `design.md`, confirmadas por el usuario el 2026-11-02 (se registran como DD-26).
