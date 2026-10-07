# Design

## Context

Ver `proposal.md` (Why) y `specs/agenda-turnos/spec.md` (requisitos). Estado actual del código relevante:

- `backend/alembic/versions/001_enable_btree_gist.py` ya instala `btree_gist`; `002_catalogo_minimo.py` crea `profesional`, `sillon`, `prestacion` (`duracion_min`, `requiere_sillon`, `activa`) y `paciente`, con PK `uuid` (`gen_random_uuid()`) y el flag de actividad (`activo` / `activa` en prestación).
- `backend/app/infrastructure/db/base.py` define una convención de nombres (`ck_%(table_name)s_%(constraint_name)s`, `fk_...`, `ix_...`); los modelos usan `CatalogoMixin` (id + timestamps con default en BD).
- `backend/app/domain/time.py` expone `to_utc`, `to_local`, `NaiveDatetimeError` y `DEFAULT_TIMEZONE`.
- `backend/app/application/` está vacío; `app/main.py` solo registra `/health`; la sesión es SQLAlchemy 2 síncrona (psycopg 3) vía `get_session`.
- Tests: `conftest.py` aplica `alembic upgrade head` sobre PostgreSQL real; `db_session` envuelve cada test en una transacción revertida y `client` sobreescribe `get_session`. `tests/integration/test_modelos_vs_migracion.py` exige que `compare_metadata` no encuentre diferencias entre modelos y migraciones.

## Goals / Non-Goals

**Goals:**
- Reglas de turno en dominio puro, testeables sin BD ni reloj real.
- Un único caso de uso `CrearTurno` con puntos de extensión estables para C-04/05/07/10/11/12.
- Garantía de no solape en PostgreSQL y traducción determinista de sus errores a HTTP.
- Test de concurrencia reproducible contra PostgreSQL real.

**Non-Goals:**
- Bloqueos pesimistas o advisory locks (la restricción de exclusión alcanza como garantía).
- Implementar validadores u observadores concretos, ni un framework de eventos.
- Endpoints de lectura (`GET /turnos`, disponibilidad): llegan con la agenda (C-13).

## Decisions

### 1. Capas y módulos
- `app/domain/turnos.py`: tipos inmutables (`Intervalo`, `Recurso` = `profesional | sillon | paciente`), `solapan(a, b)` semiabierto, `duracion_efectiva(...)`, `validar_duracion_y_grilla(...)`, `validar_sillon(...)`, `validar_inicio_futuro(inicio, ahora)` y la jerarquía de errores de dominio. Sin SQLAlchemy ni FastAPI.
- `app/application/crear_turno.py`: caso de uso `CrearTurno` y los tipos de los puntos de extensión.
- `app/infrastructure/db/models/turno.py` (ORM) y `app/infrastructure/db/repositorio_turnos.py` (carga de referencias, pre-chequeo, insert, traducción de `23P01`).
- `app/api/turnos.py`: router, schemas Pydantic y manejadores de error; se registra en `create_app()`.
- **Alternativa descartada**: poner las reglas en el router o en el modelo ORM; impide los unit tests sin BD que pide CHANGES.md y que C-05 reutilice las mismas validaciones.

### 2. Orden del caso de uso
1. Cargar profesional, paciente, prestación y sillón (si viene) → inexistente o inactivo: `ReferenciaInvalidaError(referencia, motivo)`.
2. Dominio: duración efectiva (`req.duracion_min ?? prestacion.duracion_min`), `> 0`, `% 5 == 0`, `<= 480`, inicio alineado a 5 min en hora local (vía `to_local`), inicio `>= ahora`, sillón requerido/sobrante; `fin = inicio + duración`.
3. Validadores extra (hook, vacío en C-03).
4. Pre-chequeo de solape → `SolapamientoError(recursos)` con **todos** los recursos.
5. `INSERT` + `flush`; `23P01` → `SolapamientoError({recurso deducido})`.
6. Observadores (hook, vacío en C-03), dentro de la misma transacción; luego `commit`.

Todo `422` se evalúa antes de cualquier `409` (requisito "Conflicto 409 con todos los recursos"). Cada etapa corta en el primer error (guard clauses).

### 3. Reloj inyectable (RN-AG-12)
`Reloj = Callable[[], datetime]` que devuelve un instante con zona en UTC. `CrearTurno` lo recibe por constructor; la API lo provee con la dependencia `get_reloj()` (por defecto `lambda: datetime.now(UTC)`) y los tests la sobreescriben con `app.dependency_overrides` o pasan un reloj fijo al caso de uso.
- **Por qué**: el dominio recibe `ahora` como argumento (función pura) y los tests fijan el tiempo sin parchear globales.
- **Alternativas descartadas**: `freezegun` (dependencia nueva, parchea `datetime` global y es frágil con psycopg y threads del test de concurrencia); leer `datetime.now()` dentro del dominio (no testeable); recibir `ahora` en el request (inseguro).
- Los tests usan fechas fijas futuras respecto del reloj fijo, así no dependen del día en que corren.

### 4. Puntos de extensión como dos listas inyectadas
```python
ValidadorTurno = Callable[[TurnoPropuesto], None]   # lanza un error de dominio (p. ej. 422)
ObservadorTurno = Callable[[TurnoCreado], None]     # efecto lateral en la misma transacción
CrearTurno(repositorio, reloj, validadores: Sequence[ValidadorTurno] = (), observadores: Sequence[ObservadorTurno] = ())
```
- Validadores corren después de las reglas de dominio y antes del pre-chequeo (C-10 horario, C-11 bloqueos). Observadores corren después del `INSERT` y antes del `commit`, para que la auditoría de C-07 sea atómica con el alta (Excepciones globales). Los que necesiten BD reciben sus dependencias al construirse (closures), no por la firma.
- `TurnoPropuesto` y `TurnoCreado` son dataclasses inmutables de dominio.
- **Alternativas descartadas**: bus de eventos o señales (framework sin consumidores todavía), eventos de SQLAlchemy (acoplan dominio a ORM y esconden el orden), herencia/template method (cada change tendría que subclasear).
- En C-03 se cubre con un test de aplicación: un validador que falla corta el alta y un observador recibe el turno creado (ambos son dobles triviales del puerto, no de la BD).

### 5. Contrato de errores
| Error de dominio | HTTP | Cuerpo (`detail`) |
|---|---|---|
| `TurnoInvalidoError(codigo, mensaje)` (`duracion_invalida`, `inicio_no_alineado`, `inicio_en_pasado`, `sillon_requerido`, `sillon_no_corresponde`) | 422 | `{"codigo", "mensaje"}` |
| `ReferenciaInvalidaError(referencia, motivo)` (`inexistente` / `inactiva`) | 422 | `{"codigo": "referencia_invalida", "referencia", "motivo"}` |
| `SolapamientoError(recursos)` | 409 | `{"codigo": "solapamiento", "recursos": [...]}` en orden fijo `profesional, sillon, paciente` |

Los manejadores se registran con `app.add_exception_handler`. El inicio sin zona usa `AwareDatetime` de Pydantic (422 nativo de FastAPI). `duracion_min` se declara `int | None` sin restricciones en el schema: el rango lo valida el dominio, para que la regla viva en un solo lugar.

### 6. Pre-chequeo en una sola consulta
```sql
SELECT profesional_id, sillon_id, paciente_id FROM turno
WHERE estado <> 'cancelado'
  AND tstzrange(inicio, fin, '[)') && tstzrange(:inicio, :fin, '[)')
  AND (profesional_id = :p OR sillon_id = :s OR paciente_id = :pa)
```
El repositorio devuelve las filas y el caso de uso arma el conjunto de recursos. Usa los mismos índices GiST de las restricciones. **Alternativa descartada**: tres consultas (más viajes, misma información).

### 7. Traducción de `23P01`
Se captura `sqlalchemy.exc.IntegrityError`; si `orig.sqlstate == "23P01"`, `orig.diag.constraint_name` se mapea con un diccionario `{"turno_sin_solape_profesional": "profesional", "turno_sin_solape_sillon": "sillon", "turno_sin_solape_paciente": "paciente"}`; cualquier otra violación se relanza. Se hace `rollback` de la sesión antes de propagar.

### 8. Modelo y migración `003`
- Tabla `turno`: `id uuid` (`gen_random_uuid()`), FKs `profesional_id`, `paciente_id`, `prestacion_id` (NOT NULL) y `sillon_id` (NULL) con `ON DELETE RESTRICT`, `inicio`/`fin` `timestamptz`, `duracion_min int`, `estado varchar(20) DEFAULT 'programado'`, `motivo_cancelacion varchar(255) NULL`, `creado_por uuid NULL` (sin FK hasta que exista `usuario` en C-06), `creado_en`/`actualizado_en`.
- CHECKs con la convención del proyecto: `ck_turno_estado_valido` y `ck_turno_fin_mayor` (los nombres de la KB sin prefijo se adaptan a la convención ya usada en 002). Las tres exclusiones conservan el nombre exacto `turno_sin_solape_{profesional,sillon,paciente}` porque el mapeo de `23P01` depende de él; la de sillón agrega `sillon_id IS NOT NULL` al `WHERE`.
- Índices `ix_turno_profesional_id_inicio` e `ix_turno_sillon_id_inicio`; paciente queda cubierto por su GiST (KB 04).
- El modelo ORM declara las mismas restricciones (`ExcludeConstraint` con `postgresql_where`) para que `compare_metadata` no reporte diferencias.
- `estado` como `varchar` + CHECK (DD-21): agregar estados futuros es un `ALTER ... CHECK`, sin `ALTER TYPE`.

### 9. Tiempo
La API recibe `AwareDatetime`; el caso de uso normaliza con `to_utc`, valida alineación con `to_local` y persiste UTC. La respuesta serializa `inicio`/`fin` con `to_local` (offset `-03:00`).

### 10. Test de concurrencia
`db_session` revierte todo en una transacción externa, así que la concurrencia necesita conexiones propias con commit real: una fixture crea catálogo ficticio único y commitea, lanza N=10 hilos con `threading.Barrier`, cada uno con su `Session` llamando a `CrearTurno`, y al final borra los turnos y el catálogo creados. Se espera exactamente 1 éxito y N-1 `SolapamientoError`. La carrera "que esquiva el pre-chequeo" se cubre con un repositorio real cuyo pre-chequeo se fuerza a vacío (solo se sustituye esa consulta; el `INSERT` y la exclusión corren en PostgreSQL).

## Risks / Trade-offs

- [`compare_metadata` podría reportar los índices GiST de las exclusiones o no comparar `ExcludeConstraint`] → declarar las exclusiones en el modelo; si Alembic igual las reporta, filtrarlas con `include_object` documentando el motivo, y cubrirlas con tests de restricción explícitos.
- [Pre-chequeo y alta no son atómicos (READ COMMITTED)] → aceptado: la BD es la garantía; en carrera el 409 informa un solo recurso (DD-21).
- [Test de concurrencia con datos commiteados puede dejar basura si falla] → limpieza en `finally` de la fixture e identificadores únicos por ejecución.
- [Observadores dentro de la transacción alargan el lock] → aceptado para C-07; el encolado en Redis de C-12 deberá ocurrir post-commit (decisión de ese change).
- [`creado_por` sin FK] → C-06 agrega la FK a `usuario` en su propia migración.

## Migration Plan

`alembic upgrade head` aplica `003` (tabla, FKs, CHECKs, exclusiones, índices). Rollback: `alembic downgrade 002` elimina la tabla `turno` (y con ella sus restricciones e índices). No hay datos previos que migrar. El test de migraciones existente (upgrade/downgrade en base scratch) debe seguir verde.
