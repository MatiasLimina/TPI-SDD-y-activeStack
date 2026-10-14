# Design

## Context

Ver `proposal.md` (Why, Non-goals) y `specs/agenda-turnos/spec.md` (requisitos). Estado actual del código relevante (C-03 y C-04 archivados):

- `backend/app/application/crear_turno.py`: define `Reloj`, `ValidadorTurno`, `ObservadorTurno` y `SolicitudTurno`. `CrearTurno.ejecutar` contiene **en línea** toda la secuencia de validación: `cargar_referencias` (422 referencia) → `to_utc` → `duracion_efectiva` → `validar_duracion_y_grilla` → `validar_inicio_futuro` → `validar_sillon` → arma `TurnoPropuesto` → `validadores[]` → `buscar_conflictos` (409 con todos los recursos) → `insertar` → observadores → `commit`.
- `backend/app/application/cancelar_turno.py`: `CancelarTurno` con `obtener_para_actualizar` (`FOR UPDATE` + `populate_existing`), `validar_cancelable` con `rollback()` para liberar el bloqueo si falla, `marcar_cancelado`, observadores y `commit`.
- `backend/app/domain/turnos.py`: errores `TurnoInvalidoError` (422), `ReferenciaInvalidaError` (422), `SolapamientoError` (409), `TurnoInexistenteError` (404) y `TurnoNoCancelableError(codigo, mensaje)` (409); `TurnoRegistrado` (estado persistido); `validar_cancelable(estado, inicio, ahora)` informa `turno_ya_cancelado` antes que `turno_ya_iniciado`.
- `backend/app/infrastructure/db/repositorio_turnos.py`: `buscar_conflictos(intervalo, *, profesional_id, sillon_id, paciente_id)` filtra `estado != 'cancelado'` y no puede excluir un turno; `insertar` corre el `flush` en un SAVEPOINT y traduce `23P01` a `SolapamientoError` vía `constraint_name` (`RECURSO_POR_CONSTRAINT`).
- `backend/app/api/turnos.py`: `TurnoIn` (sin `extra="forbid"`: los campos desconocidos se ignoran), `TurnoOut.desde_registrado`, `get_reloj`, `registrar_manejadores` con cuerpo `{"detail": {"codigo", ...}}`.
- Migración `003`: las tres `ExcludeConstraint` (`turno_sin_solape_profesional|sillon|paciente`) son inmediatas (no `DEFERRABLE`) y parciales sobre `estado <> 'cancelado'`. Un `UPDATE` de la misma fila no choca con su propia versión anterior (PostgreSQL ignora la tupla que la misma transacción está reemplazando), así que **no hace falta migración**.
- Tests que usan los nombres de C-04: `tests/unit/test_dominio_turnos.py`, `tests/integration/test_cancelar_turno.py`, `tests/integration/test_concurrencia_cancelar.py` y el manejador en `app/api/turnos.py`. Fixtures de concurrencia en `tests/integration/conftest.py` (`motor_concurrente`, `catalogo_commiteado`).

## Goals / Non-Goals

**Goals:**
- RN-AG-08 "exactamente la misma validación" garantizada **por construcción**: una sola secuencia de validación que ejecutan el alta y la reprogramación, de modo que una regla nueva (C-10, C-11) aplique a ambas sin tocar los casos de uso.
- Una sola regla de "turno modificable" (estado antes que tiempo) para cancelar y reprogramar, con los mismos códigos `409`.
- Reprogramar atómico sobre la misma fila: ante cualquier fallo el turno original queda intacto.
- Refactors de C-03 y C-04 sin cambio de comportamiento, protegidos por sus tests existentes.

**Non-Goals:**
- Observadores o validadores concretos (auditoría C-07, recordatorio C-12, horarios C-10, bloqueos C-11): solo los puntos de extensión.
- Cambiar el contrato de `POST /turnos` o de `POST /turnos/{id}/cancelar`.
- Bloqueo optimista o columna de versión.

## Decisions

### 1. Capas y módulos
- `app/application/validacion_turno.py` (nuevo): `Reloj`, `ValidadorTurno` y `SolicitudTurno` se **mueven** aquí junto con la función compartida (sección 3). `crear_turno.py` los reimporta para que `from app.application.crear_turno import Reloj, SolicitudTurno` siga funcionando (lo usan `cancelar_turno.py`, `api/turnos.py` y varios tests). Moverlos evita el import circular `crear_turno` ↔ `validacion_turno`.
- `app/application/reprogramar_turno.py` (nuevo): `SolicitudReprogramacion`, el centinela `OMITIDO`, la función pura `aplicar_cambios(actual, solicitud) -> SolicitudTurno`, el tipo `ObservadorReprogramacion` y el caso de uso `ReprogramarTurno`.
- `app/domain/turnos.py`: `TurnoNoModificableError`, `validar_modificable`, `CampoNoEditableError` y `validar_campos_editables` (secciones 2 y 5).
- `app/infrastructure/db/repositorio_turnos.py`: `excluir_id` en `buscar_conflictos` y nuevo `actualizar(turno_id, propuesto) -> TurnoRegistrado`.
- `app/api/turnos.py`: `ReprogramacionIn`, ruta `PATCH /{turno_id}/reprogramar`, dependencia `get_reprogramar_turno` y manejador de `CampoNoEditableError`.

### 2. Regla de turno modificable (refactor de C-04, D4)
`TurnoNoCancelableError` y `validar_cancelable` se generalizan a `TurnoNoModificableError(codigo, mensaje)` y `validar_modificable(estado, inicio, ahora)`, con la misma lógica y los mismos códigos (`turno_ya_cancelado` antes que `turno_ya_iniciado`, `inicio <= ahora` → iniciado) y mensajes neutros respecto de la operación. `CancelarTurno` y `ReprogramarTurno` la usan; el manejador `409` es uno solo.
- **Refactor en dos pasos** para no perder la red de seguridad: (1) se introducen los nombres nuevos y se dejan `TurnoNoCancelableError = TurnoNoModificableError` y `validar_cancelable = validar_modificable` como alias, con los tests de C-04 **sin tocar** en verde; (2) se migran las referencias (imports e `isinstance`, sin cambiar ninguna aserción de código ni de estado HTTP) y se borran los alias.
- **Alternativas descartadas**: un `TurnoNoReprogramableError` paralelo (duplica la regla y su orden; los códigos ya son los mismos por DD-23c); reusar `TurnoNoCancelableError` desde reprogramar (nombre engañoso en el dominio).
- **Decisión revisable por el usuario**: es el default propuesto en explore. Si se prefiere no tocar C-04, la alternativa es que `ReprogramarTurno` llame a `validar_cancelable` tal cual; el comportamiento observable es idéntico y solo cambian el grupo de tareas 2 y los nombres.

### 3. Validación compartida (refactor de C-03, D5)
```python
def validar_solicitud_turno(
    repositorio: RepositorioTurnos,
    solicitud: SolicitudTurno,
    *,
    ahora: datetime,
    validadores: Sequence[ValidadorTurno] = (),
    excluir_id: UUID | None = None,
) -> TurnoPropuesto
```
Contiene exactamente la secuencia que hoy está en línea en `CrearTurno.ejecutar`, en el mismo orden (referencias → duración y grilla → inicio futuro → sillón → validadores → pre-chequeo de solape con `excluir_id`), y devuelve el `TurnoPropuesto` listo para persistir. `CrearTurno` la llama con `excluir_id=None` y luego inserta; `ReprogramarTurno` la llama con `excluir_id=turno.id` y luego actualiza. El orden fija que todo `422` precede al `409` también al reprogramar.
- **Por qué una función y no una clase**: no tiene estado propio; recibe `ahora` ya resuelto (el caso de uso llama al reloj una vez) y los validadores como datos. Se testea a través de los dos casos de uso, que son su interfaz pública.
- **Alternativas descartadas**: copiar la secuencia en `ReprogramarTurno` (dos copias que divergen con C-10/C-11 y rompen RN-AG-08 en silencio); que `ReprogramarTurno` herede de `CrearTurno` o lo invoque (el alta inserta, la reprogramación actualiza; acoplaría el flujo de persistencia).
- **Consecuencia aceptada de RN-AG-08**: la reprogramación revalida **todas** las referencias, incluidos paciente y prestación que no cambian. Si el paciente o la prestación fueron desactivados después del alta, reprogramar responde `422 referencia_invalida`; para el MVP es lo correcto (no se mueve un turno de un recurso dado de baja).

### 4. Pre-chequeo excluyendo al propio turno
`buscar_conflictos(..., excluir_id: UUID | None = None)` agrega `Turno.id != excluir_id` al `WHERE` cuando se informa. Al ser la misma consulta para los tres recursos, la exclusión cubre también el chequeo por paciente (RN-AG-14). En la base, el `UPDATE` de la misma fila tampoco se auto-conflictúa (ver Context), así que moverse dentro del propio intervalo anterior es válido en ambas capas.

### 5. PATCH parcial y campos no editables (D1, D3)
- **API**: `ReprogramacionIn` declara `inicio: AwareDatetime | None`, `profesional_id: UUID | None`, `sillon_id: UUID | None`, `duracion_min: int | None` y `paciente_id`/`prestacion_id` como `JsonValue` opcionales, todos con default `None`. "Omitido" vs "nulo explícito" se distingue con `model_fields_set`. Un `model_validator(mode="after")` rechaza con el `422` nativo de Pydantic un nulo explícito en `inicio`, `profesional_id` o `duracion_min` (no tienen valor "vacío" con sentido). **No** se usa `extra="forbid"`: se necesita el formato de dominio para `campo_no_editable` y los demás campos desconocidos se ignoran, igual que en `TurnoIn`.
- **Aplicación**: la ruta arma `SolicitudReprogramacion` con cada campo editable en su valor o en el centinela `OMITIDO` (enum de un miembro, tipado como `T | Omitido`), más `campos_no_editables: tuple[str, ...]` con los nombres presentes en `model_fields_set`. El tipo de `paciente_id`/`prestacion_id` es permisivo a propósito: lo que dispara el error es la **presencia** del campo, no su valor (un UUID inválido también responde `campo_no_editable`, con el mismo mensaje útil).
- **Dominio**: `validar_campos_editables(campos)` lanza `CampoNoEditableError(campos)` con los campos en orden fijo (`paciente_id`, `prestacion_id`) y el mensaje "El paciente y la prestación de un turno no se pueden modificar al reprogramar. Para cambiarlos, cancelá este turno y creá uno nuevo." (dirigido a la recepcionista; el paciente no es usuario del sistema). Manejador: `422 {"detail": {"codigo": "campo_no_editable", "campos": [...], "mensaje": ...}}`.
- **Fusión**: `aplicar_cambios(actual: TurnoRegistrado, solicitud) -> SolicitudTurno` es pura: cada campo `OMITIDO` toma el valor actual (incluida `duracion_min`, que por lo tanto **nunca** llega como `None` a `duracion_efectiva` y no vuelve a la de la prestación); `sillon_id=None` explícito queda `None` y lo resuelve `validar_sillon` (`sillon_requerido` o válido). Paciente y prestación salen siempre del turno actual.
- **Body vacío** `{}`: la fusión reproduce el turno actual; se revalida y, si pasa, responde `200` sin cambios (SQLAlchemy no emite `UPDATE` si no cambió ningún atributo). Alternativa descartada: `422 sin_cambios` (regla nueva sin respaldo en la KB).

### 6. Orden del caso de uso `ReprogramarTurno.ejecutar(turno_id, solicitud)`
1. `validar_campos_editables(solicitud.campos_no_editables)` → `422 campo_no_editable`. Va primero, antes de tomar el bloqueo, porque es un defecto del request independiente del turno (igual que la validación de formato de Pydantic, que FastAPI aplica antes de cualquier búsqueda). Por eso un turno cancelado o inexistente con `paciente_id` responde `422`.
2. `repositorio.obtener_para_actualizar(turno_id)` (`FOR UPDATE`) → `None`: `TurnoInexistenteError` (404).
3. Desde aquí, todo dentro de `try/except` que hace `rollback()` y relanza (libera el bloqueo y deja el turno intacto):
   1. `ahora = to_utc(reloj())`; `validar_modificable(turno.estado, turno.inicio, ahora)` → `409 turno_ya_cancelado | turno_ya_iniciado`. El estado y el inicio **actual** se evalúan antes que cualquier dato nuevo (DD-23c/d).
   2. `aplicar_cambios(turno, solicitud)`.
   3. `validar_solicitud_turno(..., ahora=ahora, validadores=..., excluir_id=turno.id)` → `422` o `409 solapamiento`.
   4. `repositorio.actualizar(turno.id, propuesto)` → `409 solapamiento` si la base rechaza (carrera).
   5. Observadores `(anterior, nuevo)`.
4. `commit()` y devolver el `TurnoRegistrado` nuevo.

### 7. Persistencia: `actualizar` con SAVEPOINT
`actualizar(turno_id, propuesto)` toma la entidad ya bloqueada, asigna `profesional_id`, `sillon_id`, `inicio`, `fin` (UTC) y `duracion_min`, y hace el `flush` dentro de `begin_nested()`. Una `IntegrityError` con SQLSTATE `23P01` se traduce a `SolapamientoError({recurso})` con el mismo `_recurso_en_conflicto` que usa `insertar` (se extrae un helper `_flush_traduciendo_exclusion` común a ambos). Si el SAVEPOINT se revierte, la entidad en memoria se refresca o se descarta con el `rollback()` exterior del caso de uso, así que nada queda persistido. `actualizado_en` lo pone el `onupdate=now()` del mixin. Paciente, prestación, `estado`, `creado_por` y `creado_en` no se tocan.
- **Alternativa descartada**: `UPDATE ... WHERE id = :id RETURNING` en SQL directo (saltea el ORM y la traducción ya probada de `insertar`, sin ganancia).

### 8. Concurrencia
- **Mismo turno** (reprogramar vs cancelar, o dos reprogramaciones): ambos casos de uso entran por `obtener_para_actualizar`, así que se serializan por el bloqueo de fila; el segundo relee el estado ya commiteado (`populate_existing`) y aplica la regla de modificable sobre él. Cancelar primero → la reprogramación ve `cancelado` → `409 turno_ya_cancelado`. Reprogramar primero → la cancelación ve el turno movido y futuro → lo cancela en su nuevo intervalo.
- **Turnos distintos hacia el mismo hueco**: cada uno bloquea solo su fila, así que no se serializan entre sí; los dos pueden pasar el pre-chequeo y la garantía la da la exclusión de la base sobre el `UPDATE` (el segundo espera el commit del primero y recibe `23P01` → `409`). Es exactamente el escenario de RN-AG-09 aplicado a la reprogramación.
- **Orden de bloqueos**: una operación bloquea una sola fila de `turno` y después solo escribe esa fila, así que no hay ciclos de bloqueo de filas entre operaciones de este change.

### 9. Contrato HTTP
| Situación | HTTP | Cuerpo |
|---|---|---|
| Reprogramado | 200 | `TurnoOut` (mismo `id`, `estado = "programado"`, `motivo_cancelacion` nulo) |
| `paciente_id` o `prestacion_id` presentes | 422 | `{"detail": {"codigo": "campo_no_editable", "campos": [...], "mensaje"}}` |
| `id` no UUID, `inicio` sin zona, nulo en campo obligatorio, tipos inválidos | 422 | Validación nativa de FastAPI/Pydantic |
| `TurnoInexistenteError` | 404 | `{"detail": {"codigo": "turno_inexistente", "mensaje"}}` |
| `TurnoNoModificableError` | 409 | `{"detail": {"codigo": "turno_ya_cancelado" \| "turno_ya_iniciado", "mensaje"}}` |
| `TurnoInvalidoError`, `ReferenciaInvalidaError` | 422 | Mismos cuerpos que en `POST /turnos` |
| `SolapamientoError` (pre-chequeo o base) | 409 | `{"detail": {"codigo": "solapamiento", "recursos": [...]}}` |

- **`PATCH /turnos/{id}/reprogramar`** y no `PATCH /turnos/{id}`: así lo fijan CHANGES.md, el Flujo 3 y DD-23; deja explícito que es una operación de dominio con reglas propias y no una edición libre.
- **`200` con el turno**: igual que la cancelación; la recepción ve el resultado sin otra consulta.

### 10. Puntos de extensión
`ReprogramarTurno(repositorio, reloj, validadores: Sequence[ValidadorTurno] = (), observadores: Sequence[ObservadorReprogramacion] = ())` con `ObservadorReprogramacion = Callable[[TurnoRegistrado, TurnoRegistrado], None]` (anterior, nuevo): C-07 necesita los valores previos y nuevos para la auditoría `reprogramar`, y C-12 el nuevo inicio para reprogramar el recordatorio. Los observadores corren antes del `commit` (como en C-03 y C-04); si uno falla → `rollback()` y el turno queda intacto. Los validadores son los mismos `ValidadorTurno` del alta y entran por la validación compartida: la composición en `api/turnos.py` pasará la misma lista a `CrearTurno` y a `ReprogramarTurno` cuando C-10/C-11 los registren (hoy ambas listas están vacías).

### 11. Tiempo
Reloj inyectado como en C-03/C-04 (`get_reloj`, sobreescrito en tests). Se lee **una vez** por ejecución y el mismo `ahora` alimenta `validar_modificable` y `validar_inicio_futuro`. Asimetría consciente heredada: el inicio actual `== ahora` cuenta como iniciado (`409`), mientras que un nuevo inicio `== ahora` es aceptado por `validar_inicio_futuro` (RN-AG-12 solo rechaza lo anterior). Para turnos "iniciados/pasados" los tests crean con un reloj y reprograman con otro posterior, o insertan la fila directamente.

### 12. Tests de concurrencia
Con `motor_concurrente` y `catalogo_commiteado`, limpieza en `finally`:
- **Turnos distintos al mismo hueco**: N=5 turnos commiteados del mismo profesional en horarios distintos (sillones y pacientes distintos para que el único recurso compartido sea el profesional), N hilos con `threading.Barrier`, cada uno con su `Session` y su `ReprogramarTurno` al mismo inicio. Se espera 1 éxito, N-1 `SolapamientoError` con recurso `profesional`, un solo turno activo en el hueco y los N-1 perdedores con su `inicio`/`fin` original. Correrlo 3 veces seguidas para verificar estabilidad.
- **Reprogramar vs cancelar el mismo turno, en ambos órdenes y de forma determinista**: la primera operación recibe un observador que, ya con la fila bloqueada, señala un `threading.Event` y espera otro; mientras espera se lanza la segunda operación en otro hilo y se verifica que no terminó (está bloqueada en el `FOR UPDATE`); luego se libera la primera. Se usan los observadores existentes (`CancelarTurno` y `ReprogramarTurno` los aceptan), sin agregar ganchos de test al código de producción. Orden "cancelar primero" → reprogramar recibe `TurnoNoModificableError("turno_ya_cancelado")` y el turno queda `cancelado` en su intervalo original; orden "reprogramar primero" → ambos tienen éxito y el turno queda `cancelado` en el intervalo nuevo.

## Risks / Trade-offs

- [El refactor de C-03 cambia el código del alta, el camino más usado] → se hace primero, sin funcionalidad nueva, con `test_crear_turno.py`, `test_api_turnos.py` y `test_concurrencia_turnos.py` como red de seguridad; ninguna aserción de esos tests cambia.
- [Renombrar `TurnoNoCancelableError` toca tests de C-04] → dos pasos con alias (sección 2): primero verde con los tests intactos, después solo cambios de nombre en imports, sin tocar aserciones.
- [Revalidar todas las referencias puede impedir mover un turno cuyo paciente o prestación se desactivó] → es lo que pide RN-AG-08; la salida es cancelar y crear otro. Documentado en sección 3.
- [`FOR UPDATE` + observadores dentro de la transacción alargan el bloqueo] → transacción corta (una lectura, un pre-chequeo, un `UPDATE`); igual que C-04.
- [Dos reprogramaciones cruzadas de turnos distintos podrían esperar una a la otra en la verificación de exclusión] → cada transacción bloquea una sola fila y la espera en la exclusión es sobre la transacción del otro; si PostgreSQL detectara un deadlock (`40P01`), la respuesta sería `500`. Es improbable con un único bloqueo de fila por operación; se acepta para el MVP y el test de concurrencia de turnos distintos lo vigila.
- [El endpoint queda sin autenticación hasta C-06] → igual que los otros endpoints de turnos.

## Migration Plan

Sin cambios de esquema: no hay migración nueva ni rollback de BD. El despliegue es solo código; revertir el change elimina la ruta y devuelve la validación a `CrearTurno` sin afectar datos. `test_modelos_vs_migracion.py` debe seguir verde sin cambios.
