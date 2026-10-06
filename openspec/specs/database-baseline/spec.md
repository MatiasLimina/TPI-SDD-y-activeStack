# database-baseline Specification

## Purpose

Establece el esquema base versionado de PostgreSQL mediante migraciones reproducibles, incluyendo la extensión `btree_gist` que necesitan las restricciones de exclusión anti-solapamiento.

## Requirements

### Requirement: Migraciones versionadas reproducibles
El sistema SHALL gestionar el esquema de la base de datos únicamente mediante migraciones versionadas que se puedan aplicar sobre una base vacía hasta la última versión y revertir.

#### Scenario: Aplicar migraciones sobre base vacía
- **WHEN** se ejecuta la actualización de migraciones hasta la última versión sobre una base PostgreSQL vacía
- **THEN** el proceso termina sin errores y la base queda registrada en la revisión `001`

#### Scenario: Reaplicar es idempotente
- **WHEN** se ejecuta la actualización de migraciones sobre una base que ya está en la última revisión
- **THEN** el proceso termina sin errores y sin cambios

### Requirement: Extensión btree_gist instalada
La migración inicial `001` MUST instalar la extensión `btree_gist` de PostgreSQL, y su reversión MUST eliminarla.

#### Scenario: btree_gist presente tras migrar
- **WHEN** la base está en la revisión `001`
- **THEN** la consulta a `pg_extension` devuelve una fila con `extname = 'btree_gist'`

#### Scenario: Reversión de la migración inicial
- **WHEN** se revierte la base desde `001` a la base vacía
- **THEN** `btree_gist` ya no figura en `pg_extension`

### Requirement: Tests de persistencia contra PostgreSQL real
Los tests que tocan persistencia MUST ejecutarse contra una base PostgreSQL real dedicada a tests, separada de la base de desarrollo; MUST NOT usarse SQLite ni mocks de la base. Cada test MUST quedar aislado: sus escrituras no persisten para el test siguiente.

#### Scenario: Aislamiento entre tests
- **WHEN** un test inserta filas o crea objetos dentro de su sesión
- **THEN** el test siguiente no ve esos cambios

#### Scenario: Conexión a la base de test
- **WHEN** se ejecuta la suite de integración con la base de test levantada
- **THEN** una consulta `SELECT 1` por la sesión de test devuelve `1` y el servidor reporta ser PostgreSQL
