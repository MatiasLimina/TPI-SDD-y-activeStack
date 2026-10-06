# Design

## Context

- Depende de C-01 (`foundation-scaffolding-test-harness`), que entrega: `backend/app/{domain,application,infrastructure,api}`, `backend/tests/{unit,integration}`, Alembic en `backend/alembic/` con la migración `001` (`btree_gist`), Pydantic Settings, fixtures de engine/sesión contra PostgreSQL real con rollback por test y el marker `integration`. Al momento de este propose el `design.md` de C-01 no existe todavía; si C-01 define nombres distintos (p. ej. ubicación de `Base` o de las fixtures), C-02 se adapta a ellos sin cambiar specs.
- El modelo de la KB (`04_modelo_de_datos.md`) define atributos pero no tipos, largos ni unicidades: esas decisiones se toman acá (governance ALTO → explícitas para revisión).
- Motivación y alcance: ver `proposal.md`. Comportamiento exigido: `specs/catalogo-consultorio/spec.md` y `specs/datos-semilla/spec.md`.

## Goals / Non-Goals

**Goals:**
- Esquema de las cuatro tablas con la integridad en la BD (CHECK, NOT NULL, UNIQUE, defaults), no solo en el ORM.
- Modelos ORM que reflejen exactamente la migración (sin autogenerate divergente).
- Seed reutilizable desde tests (función) y desde consola (módulo ejecutable).

**Non-Goals:**
- Repositorios, casos de uso o entidades de dominio puras para el catálogo (llegan con los CRUD de C-08/C-09 cuando haya comportamiento que testear).
- Relaciones ORM hacia `turno`, `usuario`, `horario_atencion` o `bloqueo` (se agregan en sus changes).
- Validación de formato de documento, teléfono o email (no hay regla de negocio todavía; `10_preguntas_abiertas.md` la deja como pregunta Baja).

## Decisions

### D1 — PK `uuid` con `gen_random_uuid()` en la BD
- **Elegido**: `id uuid PRIMARY KEY DEFAULT gen_random_uuid()` en las cuatro tablas.
- **Por qué**: la KB ya define `Usuario.id` como uuid; un mismo tipo de PK en todo el modelo simplifica FKs. Permite que el seed use ids fijos conocidos de antemano (ver D5) y no expone conteos en la futura API.
- **Alternativas**: `bigint GENERATED ALWAYS AS IDENTITY` (más compacto e índices más chicos, pero mezcla tipos con `usuario` y complica ids estables en el seed). El volumen esperado (consultorio chico) hace irrelevante la diferencia de tamaño.
- `gen_random_uuid()` es nativo desde PostgreSQL 13 (sin `pgcrypto`). El ORM no genera ids: usa `server_default`.

### D2 — Integridad declarada en la BD
- `CHECK (duracion_min > 0)` con nombre `ck_prestacion_duracion_min_positiva`.
- `UNIQUE` en `sillon.nombre`, `prestacion.nombre`, `paciente.documento`, `profesional.matricula` (UNIQUE estándar: varios `NULL` permitidos, que es lo deseado para matrícula opcional).
- `NOT NULL` + `server_default` para `activo`/`activa` (`true`) y `requiere_sillon` (`true`).
- **Por qué**: regla dura del proyecto (no confiar solo en la aplicación) y skill `supabase-postgres-best-practices` (schema-constraints). Los tests escriben con SQL/ORM directo y esperan `IntegrityError` de la BD.
- **Alternativa descartada**: validar solo con Pydantic/ORM → no protege escrituras directas ni el seed.
- No se agrega índice extra: los UNIQUE ya crean índice; no hay FKs en este change (C-03 indexará las FKs de `turno`).

### D3 — Tipos y nombres
- Tablas en singular y minúscula (`profesional`, `sillon`, `prestacion`, `paciente`), consistentes con el DDL de `turno` de la KB. Sin tildes en identificadores.
- Textos como `varchar(n)` con límites holgados (nombres 100, sillón 50, matrícula 30, documento 20, teléfono 30, email 254). `duracion_min` como `integer`.
- `creado_en` / `actualizado_en` como `timestamptz NOT NULL DEFAULT now()`; `actualizado_en` se refresca desde el ORM (`onupdate`). Sin trigger: no hay updates en este change y C-08/C-09 pueden revisarlo.
- Convención de nombres de constraints vía `MetaData(naming_convention=...)` (`pk_`, `uq_`, `ck_`, `fk_`, `ix_`) para que migraciones y ORM generen nombres deterministas. Si C-01 ya la define en `Base`, se reutiliza.

### D4 — Ubicación del código
- Modelos: `backend/app/infrastructure/db/models/{profesional,sillon,prestacion,paciente}.py`, re-exportados en `models/__init__.py` para que Alembic los vea en `target_metadata`.
- Migración: `backend/alembic/versions/002_catalogo_minimo.py`, `down_revision = "001"` (o el id real de la 001 de C-01). Escrita a mano y verificada contra los modelos; `downgrade` borra las cuatro tablas.
- Seed: `backend/app/infrastructure/db/seed.py` con `seed_catalogo(session: Session) -> None` (no hace commit; lo controla quien llama) y `main()` ejecutable con `python -m app.infrastructure.db.seed`, que abre sesión desde Settings y hace commit.

### D5 — Seed idempotente con ids fijos + `ON CONFLICT DO NOTHING`
- Cada registro sembrado tiene un `uuid` fijo literal definido en el módulo de seed.
- Inserción con `INSERT ... ON CONFLICT DO NOTHING` (dialecto PostgreSQL de SQLAlchemy, `postgresql.insert(...).on_conflict_do_nothing()`), sin target, para absorber conflictos tanto por `id` como por claves naturales.
- **Por qué**: re-ejecutar no duplica, no falla y no pisa cambios hechos en desarrollo (spec "Datos preexistentes no se pisan"). Ids estables permiten que tests y documentación referencien registros conocidos.
- **Alternativas**: `ON CONFLICT DO UPDATE` (re-sincroniza valores, pero revierte cambios manuales y obliga a elegir un único target de conflicto); "select-then-insert" (condición de carrera, más código); truncar y recargar (destructivo, rompería FKs desde `turno` en C-03).

### D6 — Datos ficticios del seed
- Profesionales: 2 (p. ej. "Ana Ficticia", "Bruno Inventado"), matrícula ficticia con prefijo `MP-FIC-`.
- Sillones: "Sillón 1", "Sillón 2".
- Prestaciones: Consulta 30 sin sillón; Control 20 sin sillón; Limpieza 45 con sillón; Conservadora 60 con sillón.
- Pacientes: 4, emails `@example.com` (dominio reservado RFC 2606), documentos con prefijo `FIC-` (no pueden coincidir con un DNI real, que es numérico), teléfonos de la forma `+54 11 5555-000N`.

### D7 — Estrategia de tests (TDD, PostgreSQL real)
- `backend/tests/integration/test_catalogo_constraints.py`: un test por escenario de `catalogo-consultorio` (insert directo + `pytest.raises(IntegrityError)` y verificación del nombre de constraint cuando aplica).
- `backend/tests/integration/test_seed.py`: escenarios de `datos-semilla` llamando `seed_catalogo(session)` una o dos veces dentro de la transacción con rollback de C-01.
- `backend/tests/integration/test_migracion_002.py`: `upgrade head` crea las cuatro tablas y `downgrade` a 001 las elimina (sobre la BD de test).
- Nombres `test_<unidad>_<escenario>_<esperado>`, AAA, marker `integration`.
- Para escenarios que esperan error dentro de la transacción compartida se usa `session.begin_nested()` (savepoint) para no invalidar la transacción del test.

## Risks / Trade-offs

- [La 001 de C-01 todavía no existe / su revision id difiere] → la tarea de migración toma el `down_revision` real al implementar; el test de migración lo detecta.
- [Drift entre modelos ORM y migración escrita a mano] → test que compara `alembic check`/autogenerate vacío tras `upgrade head` (o al menos que `Base.metadata` y la BD tengan las mismas columnas).
- [`ON CONFLICT DO NOTHING` sin target oculta conflictos inesperados] → aceptable para un seed de desarrollo; los tests verifican cantidades exactas tras la primera ejecución.
- [Unicidad de `nombre` sensible a mayúsculas ("sillón 1" vs "Sillón 1")] → aceptado en el MVP; se puede pasar a índice único sobre `lower(nombre)` en C-08 si aparece el problema.
- [Datos del seed usados en tests futuros] → los ids fijos se exponen como constantes para que C-03 los reutilice sin acoplarse a nombres.

## Migration Plan

- Deploy: `alembic upgrade head` (aplica 002 sobre 001) y luego, solo en desarrollo, `python -m app.infrastructure.db.seed`.
- Rollback: `alembic downgrade 001` elimina las cuatro tablas (sin datos productivos en riesgo en esta etapa).

## Open Questions

- ¿Hace falta un límite superior para `duracion_min` (p. ej. ≤ 480)? No cambia este change; podría agregarse como CHECK adicional cuando se definan los CRUD (C-08).
