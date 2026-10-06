# Proposal

## Why

C-03 (`crear-turno-sin-solapamientos`) necesita referenciar profesionales, sillones, prestaciones y pacientes, pero esas entidades todavía no existen y sus CRUDs llegan recién en C-08/C-09. Este change crea el catálogo mínimo persistente (modelos + migración 002) y lo carga con un seed ficticio e idempotente, para que el núcleo de agenda pueda construirse sin depender de auth ni de pantallas de configuración. Es governance **ALTO**: son los modelos core que referencia todo lo demás, por eso las decisiones de tablas y columnas quedan explícitas abajo para revisión humana.

## What Changes

- Cuatro tablas nuevas en PostgreSQL vía migración Alembic **002** (encadenada a la 001 de C-01, que crea `btree_gist`):

  | Tabla | Columnas | Constraints |
  |-------|----------|-------------|
  | `profesional` | `id` uuid PK, `nombre` varchar(100) NOT NULL, `apellido` varchar(100) NOT NULL, `matricula` varchar(30) NULL, `activo` bool NOT NULL default `true`, `creado_en`, `actualizado_en` | `UNIQUE (matricula)` (admite varios NULL) |
  | `sillon` | `id` uuid PK, `nombre` varchar(50) NOT NULL, `activo` bool NOT NULL default `true`, `creado_en`, `actualizado_en` | `UNIQUE (nombre)` |
  | `prestacion` | `id` uuid PK, `nombre` varchar(100) NOT NULL, `duracion_min` integer NOT NULL, `requiere_sillon` bool NOT NULL default `true`, `activa` bool NOT NULL default `true`, `creado_en`, `actualizado_en` | `UNIQUE (nombre)`, `CHECK (duracion_min > 0)` |
  | `paciente` | `id` uuid PK, `nombre` varchar(100) NOT NULL, `apellido` varchar(100) NOT NULL, `documento` varchar(20) NOT NULL, `telefono` varchar(30) NOT NULL, `email` varchar(254) NULL, `activo` bool NOT NULL default `true`, `creado_en`, `actualizado_en` | `UNIQUE (documento)` |

  - `id`: `uuid` con `DEFAULT gen_random_uuid()` (coherente con `Usuario.id` uuid de la KB).
  - `creado_en` / `actualizado_en`: `timestamptz NOT NULL DEFAULT now()` (UTC, regla dura).
  - Los defaults (`activo`, `requiere_sillon`) viven en la BD (`server_default`), no solo en el ORM.
  - Nombres de tabla en singular y minúscula, alineados con el DDL de `turno` de la KB.
- Modelos SQLAlchemy 2.0 (`Mapped`/`mapped_column`) para `Profesional`, `Sillon`, `Prestacion` y `Paciente`.
- Script de seed de desarrollo, **solo con datos ficticios** e **idempotente** (re-ejecutarlo no duplica ni falla):
  - 2 profesionales, 2 sillones ("Sillón 1", "Sillón 2").
  - 4 prestaciones: Consulta 30 min (sin sillón), Control 20 min (sin sillón), Limpieza 45 min (con sillón), Conservadora 60 min (con sillón).
  - 4 pacientes con emails del dominio reservado `example.com`.
- Tests de integración contra PostgreSQL real: idempotencia del seed y constraints de BD (duración ≤ 0 rechazada, unicidad, defaults).

Fuera de alcance (diferido): usuarios y roles (C-06), CRUD/endpoints de configuración y pacientes (C-08, C-09), horarios de atención (C-10), bloqueos (C-11), turnos (C-03). Sin endpoints nuevos.

## Capabilities

### New Capabilities
- `catalogo-consultorio`: persistencia e integridad de los recursos del consultorio (profesionales, sillones, prestaciones) y de los pacientes: atributos obligatorios, unicidades, duración positiva, defaults y estado activo/inactivo.
- `datos-semilla`: carga de datos de desarrollo ficticios, idempotente, que deja el sistema listo para agendar turnos.

### Modified Capabilities
<!-- Ninguna: no existen specs previas en openspec/specs/. -->

## Impact

- **Código nuevo**: `backend/app/infrastructure/db/models/` (cuatro modelos), `backend/app/infrastructure/db/seed.py`, migración `backend/alembic/versions/002_*.py`, tests en `backend/tests/integration/`.
- **Dependencias**: ninguna nueva; usa SQLAlchemy 2, Alembic, psycopg y pytest de C-01. Requiere PostgreSQL ≥ 13 (`gen_random_uuid()` nativo).
- **Downstream**: C-03 agrega FKs desde `turno` hacia estas cuatro tablas; C-06 enlaza `usuario.profesional_id`; C-08/C-09 exponen CRUD sobre estos modelos.
- **Datos**: ningún dato real (RN-CU-02 / DD-07); el seed no contiene credenciales.
