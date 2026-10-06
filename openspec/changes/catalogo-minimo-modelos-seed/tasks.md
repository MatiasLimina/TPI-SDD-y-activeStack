# Tasks

> TDD estricto: en cada tarea el test va primero (RED), luego el mínimo código (GREEN) y refactor. Todos los tests corren contra PostgreSQL real (fixtures de C-01), marker `integration`. Cerrar cada tarea con `ruff format` + `ruff check` sin errores.

## 1. Preparación

- [x] 1.1 Verificar que C-01 está aplicado (`alembic upgrade head` llega a la 001 y `pytest -m integration` está verde) y registrar el baseline de tests pasando; anotar el revision id real de la 001 y la ubicación de `Base`/fixtures
- [x] 1.2 Asegurar `MetaData(naming_convention=...)` en la `Base` declarativa (reutilizar la de C-01 si existe) y verificar con un test que un constraint de prueba recibe nombre determinista o, si ya existe, que los tests de C-01 siguen verdes

## 2. Migración 002 y modelos ORM

- [x] 2.1 RED: `tests/integration/test_migracion_002.py` — tras `upgrade head` existen las tablas `profesional`, `sillon`, `prestacion`, `paciente` con sus columnas, y `downgrade` a 001 las elimina; verificar que falla
- [x] 2.2 GREEN: escribir `backend/alembic/versions/002_catalogo_minimo.py` (uuid PK `gen_random_uuid()`, NOT NULL, UNIQUE, CHECK `duracion_min > 0`, defaults en BD, `timestamptz` con `now()`) y verificar que 2.1 pasa
- [x] 2.3 Crear los modelos SQLAlchemy 2.0 en `backend/app/infrastructure/db/models/` (type hints completos, `server_default`, re-export en `__init__.py`, incluidos en `target_metadata`) y verificar con un test que el autogenerate de Alembic contra la BD migrada no detecta diferencias

## 3. Integridad del catálogo (spec `catalogo-consultorio`)

- [ ] 3.1 RED→GREEN: tests de duración — 45 aceptada; 0 y -15 rechazadas con `IntegrityError` del CHECK `ck_prestacion_duracion_min_positiva`; verificar `pytest tests/integration/test_catalogo_constraints.py -k duracion` en verde
- [ ] 3.2 RED→GREEN: tests de `requiere_sillon` — default `true` sin informar, `false` explícito persiste; verificar en verde
- [ ] 3.3 RED→GREEN: test de actividad por defecto en las cuatro tablas (insert sin `activo`/`activa` → `true`); verificar en verde
- [ ] 3.4 RED→GREEN: tests de unicidad — sillón duplicado y documento duplicado rechazados; dos profesionales sin matrícula aceptados (usar savepoints para los casos de error); verificar en verde
- [ ] 3.5 RED→GREEN: tests de obligatoriedad — paciente sin documento rechazado por NOT NULL; paciente sin email aceptado; verificar en verde
- [ ] 3.6 RED→GREEN: test de marcas de tiempo — `creado_en`/`actualizado_en` completados por la BD y con zona horaria (`tzinfo` no nulo); verificar en verde

## 4. Seed de desarrollo (spec `datos-semilla`)

- [ ] 4.1 RED: `tests/integration/test_seed.py` — seed sobre base vacía deja 2 profesionales, 2 sillones, 4 prestaciones, 4 pacientes, todos activos; verificar que falla por ausencia de `seed_catalogo`
- [ ] 4.2 GREEN: implementar `seed_catalogo(session: Session) -> None` en `backend/app/infrastructure/db/seed.py` con ids uuid fijos y `INSERT ... ON CONFLICT DO NOTHING`, datos 100 % ficticios; verificar que 4.1 pasa
- [ ] 4.3 RED→GREEN (triangular): test de las prestaciones sembradas (Consulta 30/sin sillón, Control 20/sin sillón, Limpieza 45/con sillón, Conservadora 60/con sillón); verificar en verde
- [ ] 4.4 RED→GREEN: tests de idempotencia — doble ejecución sin error y mismas cantidades; ids estables entre ejecuciones; un sillón sembrado marcado inactivo no se revierte al re-ejecutar; verificar en verde
- [ ] 4.5 RED→GREEN: test de datos ficticios — todo email de paciente sembrado termina en `@example.com`; revisar a mano que no haya datos reales ni credenciales en el módulo; verificar en verde
- [ ] 4.6 Agregar `main()` ejecutable (`python -m app.infrastructure.db.seed`, sesión desde Settings, commit) y verificar ejecutándolo dos veces contra la BD de desarrollo de Docker Compose sin error
- [ ] 4.7 Documentar en el README cómo correr el seed (después de `alembic upgrade head`) y verificar que el comando documentado funciona tal cual

## 5. Cierre

- [ ] 5.1 Verificar suite completa: `pytest` en verde (C-01 + C-02), `ruff format --check` y `ruff check` sin errores, y `openspec validate catalogo-minimo-modelos-seed` sin errores
