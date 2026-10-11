# Design

## Context

Ver `proposal.md` (Why) y `specs/agenda-turnos/spec.md` (requisitos). Estado actual del código relevante (C-03 archivado):

- `backend/app/infrastructure/db/models/turno.py` y `backend/alembic/versions/003_turno.py` ya tienen `estado varchar(20)` con `ck_turno_estado_valido` (`programado|cancelado`), `motivo_cancelacion varchar(255) NULL`, `actualizado_en` con `onupdate=now()` (vía `CatalogoMixin`) y las tres exclusiones `turno_sin_solape_*` parciales sobre `estado <> 'cancelado'`. **No hace falta migración.**
- `backend/app/infrastructure/db/repositorio_turnos.py`: `RepositorioTurnos(session)` con `cargar_referencias`, `buscar_conflictos` (ya filtra `Turno.estado != "cancelado"`), `insertar` (SAVEPOINT + traducción de `23P01`), `commit` y `rollback`.
- `backend/app/application/crear_turno.py`: define `Reloj = Callable[[], datetime]` y el patrón caso de uso + repositorio + observadores que corren antes del `commit`, con `rollback()` si un observador falla.
- `backend/app/domain/turnos.py`: errores `TurnoError` → `TurnoInvalidoError` (422), `ReferenciaInvalidaError` (422), `SolapamientoError` (409); dataclasses inmutables `TurnoPropuesto`, `TurnoCreado`. Funciones puras que reciben `ahora` como argumento (`validar_inicio_futuro`).
- `backend/app/api/turnos.py`: router `/turnos`, `TurnoOut.desde_dominio` (instantes con `to_local`), dependencia `get_reloj()` que los tests sobreescriben con `dependency_overrides`, y `registrar_manejadores(app)` con un `exception_handler` por error de dominio y cuerpo `{"detail": {"codigo", ...}}`.
- Tests: `db_session` envuelve cada test en una transacción revertida (modo savepoint) y `client` sobreescribe `get_session`; `tests/integration/test_concurrencia_turnos.py` ya resuelve datos commiteados en conexiones propias con limpieza en `finally`; `tests/integration/factories.py::crear_catalogo` arma catálogo ficticio.

## Goals / Non-Goals

**Goals:**
- Regla de cancelabilidad en dominio puro, testeable con un `ahora` fijo y sin BD.
- Un caso de uso `CancelarTurno` simétrico a `CrearTurno` (mismo reloj, mismo patrón de observadores) para que C-07 y C-12 se enchufen sin tocar su cuerpo.
- Serializar cancelaciones concurrentes del mismo turno sin depender de la ventana entre leer y escribir.
- Reutilizar los mismos contratos de error y de respuesta de C-03.

**Non-Goals:**
- Endpoint de lectura de un turno o listado (C-13).
- Deshacer una cancelación ("descancelar"): no está en US-006; volver a reservar es crear un turno nuevo.
- Implementar observadores concretos (auditoría C-07, recordatorio C-12).
- Cambiar el esquema de BD o el comportamiento de `POST /turnos`.

## Decisions

### 1. Capas y módulos
- `app/domain/turnos.py` (se extiende):
  - `TurnoRegistrado`: dataclass inmutable con el estado persistido del turno (los campos de `TurnoCreado` + `estado` + `motivo_cancelacion`). Es lo que devuelve el repositorio al leer y al cancelar y lo que reciben los observadores de cancelación.
  - `TurnoInexistenteError(turno_id)` → 404 y `TurnoNoCancelableError(codigo, mensaje)` → 409, ambos bajo `TurnoError`.
  - `validar_cancelable(estado, inicio, ahora)` pura y `normalizar_motivo(motivo) -> str | None` (strip; vacío → `None`).
- `app/application/cancelar_turno.py`: caso de uso `CancelarTurno` y el tipo `ObservadorCancelacion = Callable[[TurnoRegistrado], None]`.
- `app/infrastructure/db/repositorio_turnos.py` (se extiende): `obtener_para_actualizar(turno_id) -> TurnoRegistrado | None` y `marcar_cancelado(turno_id, motivo) -> TurnoRegistrado`.
- `app/api/turnos.py` (se extiende): ruta, `CancelacionIn`, campo `motivo_cancelacion` en `TurnoOut`, dependencia `get_cancelar_turno` y dos manejadores nuevos.
- **Alternativa descartada**: reutilizar `TurnoCreado` agregándole `motivo_cancelacion`. El nombre describe un evento (alta) y no el estado del turno; C-05 también va a necesitar leer el turno persistido, así que conviene un tipo propio.
- `Reloj` se importa desde `app.application.crear_turno` (sin mover el tipo, para no tocar C-03 sin necesidad).

### 2. Orden del caso de uso
1. `normalizar_motivo` (puro).
2. `repositorio.obtener_para_actualizar(id)` → `None`: `TurnoInexistenteError` (404).
3. `validar_cancelable(turno.estado, turno.inicio, to_utc(reloj()))` → `TurnoNoCancelableError` (409).
4. `repositorio.marcar_cancelado(id, motivo)` (UPDATE + `flush`).
5. Observadores (vacíos en C-04), dentro de la misma transacción; si uno falla → `rollback()` y se relanza (el turno sigue `programado`).
6. `commit()` y devolver el `TurnoRegistrado` cancelado.

El largo del motivo (>255 → 422) lo valida Pydantic en el borde, antes de entrar al caso de uso, porque es una restricción de formato del request y coincide con la columna `varchar(255)`.

### 3. Regla de cancelabilidad y orden de los 409
```python
def validar_cancelable(estado: str, inicio: datetime, ahora: datetime) -> None:
    if estado == "cancelado":  -> TurnoNoCancelableError("turno_ya_cancelado", ...)
    if inicio <= ahora:        -> TurnoNoCancelableError("turno_ya_iniciado", ...)
```
- **Límite exacto (`inicio == ahora`)**: se considera iniciado → `409`. RN-AG-13 dice "hasta su inicio"; en el instante del inicio el turno ya está en curso. Es una asimetría consciente con el alta, donde `validar_inicio_futuro` acepta `inicio == ahora` (RN-AG-12 solo rechaza lo "anterior"). Con la grilla de 5 minutos y un reloj a nivel microsegundo el caso es prácticamente teórico, pero queda fijado por un test.
- **Cancelado y pasado**: se informa `turno_ya_cancelado`. El estado es el hecho más relevante para la recepción ("ya lo cancelaste") y hace el resultado determinista sin depender del reloj.
- **Ya cancelado → 409, no idempotente** (DD-22; resuelve el "409/idempotente" que dejaba abierto el Flujo 4): un `200` silencioso escondería que otra persona ya canceló (y con otro motivo) y, cuando lleguen C-07/C-12, duplicaría auditoría o reintentaría cancelar un recordatorio. El 409 no modifica el motivo original.

### 4. Bloqueo de fila para cancelaciones concurrentes
`obtener_para_actualizar` hace `SELECT ... FROM turno WHERE id = :id FOR UPDATE` (`select(Turno).where(...).with_for_update()`). Con READ COMMITTED, el segundo pedido espera a que el primero haga `commit`, relee la fila ya `cancelado` y responde `409 turno_ya_cancelado`.
- **Por qué**: sin bloqueo, dos pedidos leen `programado`, ambos pasan la validación y ambos responden `200` (el último motivo pisa al primero y, con C-07, habría dos registros de auditoría). La exclusión de BD no ayuda aquí: cancelar no crea solape.
- **Alternativas descartadas**: `UPDATE ... WHERE id = :id AND estado = 'programado' AND inicio > :ahora RETURNING ...` (atómico, pero ante 0 filas hace falta otra consulta para distinguir 404 / ya cancelado / ya iniciado, y saca la regla del dominio puro); bloqueo optimista con columna de versión (requiere migración y no aporta para una sola transición de estado); advisory locks (más infraestructura para el mismo efecto).
- C-05 (reprogramar) reutiliza `obtener_para_actualizar`, con lo que cancelar y reprogramar el mismo turno a la vez también quedan serializados.

### 5. Persistencia de la cancelación
`marcar_cancelado` asigna `estado = "cancelado"` y `motivo_cancelacion` sobre la entidad ya bloqueada y hace `flush`; `actualizado_en` lo actualiza el `onupdate=now()` del mixin. No usa SAVEPOINT: la única restricción que podría dispararse es el CHECK de estado, imposible con un valor fijo válido. El cambio a `cancelado` saca la fila del `WHERE` de las tres exclusiones parciales, por lo que el horario queda libre para la verificación previa (`buscar_conflictos`) y para la base en la misma transacción.

### 6. Contrato HTTP
| Situación | HTTP | Cuerpo |
|---|---|---|
| Cancelado | 200 | `TurnoOut` con `estado = "cancelado"` y `motivo_cancelacion` |
| `TurnoInexistenteError` | 404 | `{"detail": {"codigo": "turno_inexistente", "mensaje"}}` |
| `TurnoNoCancelableError` | 409 | `{"detail": {"codigo": "turno_ya_cancelado" \| "turno_ya_iniciado", "mensaje"}}` |
| `id` no UUID, motivo > 255, body malformado | 422 | Validación nativa de FastAPI/Pydantic |

- **200 con el turno y no 204**: la recepción ve el estado final y el motivo guardado sin otra consulta (todavía no hay `GET /turnos/{id}`); es coherente con `POST /turnos` que devuelve el turno.
- **`POST /turnos/{id}/cancelar` y no `DELETE`**: así lo fija CHANGES.md/Flujo 4, y semánticamente la fila no se borra.
- **Body opcional**: el parámetro se declara `datos: CancelacionIn | None = None`; sin body equivale a sin motivo. `CancelacionIn.motivo: str | None = Field(default=None, max_length=255)`. Se valida el largo antes del strip; un motivo de 256 caracteres con espacios en los extremos se rechaza igual (regla simple y predecible).
- **`motivo_cancelacion` en `TurnoOut`**: se agrega como `str | None` (nulo en `POST /turnos`). Es un campo adicional compatible; `TurnoOut` gana un constructor `desde_registrado` además de `desde_dominio`.
- Los manejadores siguen el patrón `registrar_manejadores` de C-03.

### 7. Puntos de extensión
`CancelarTurno(repositorio, reloj, observadores: Sequence[ObservadorCancelacion] = ())`. Los observadores corren tras el `UPDATE` y antes del `commit`, igual que en `CrearTurno`: la auditoría `cancelar` de C-07 queda atómica con la cancelación. La cancelación del recordatorio de C-12 decidirá en su change si opera post-commit (como se anticipó en el design de C-03 para el encolado en Redis). No se agregan validadores previos: no hay reglas futuras planificadas que bloqueen una cancelación.

### 8. Tiempo
El reloj se inyecta igual que en C-03 (`get_reloj`, sobreescrito en tests con un instante fijo). La comparación `inicio <= ahora` se hace entre instantes con zona en UTC (`to_utc`); la respuesta serializa con `to_local` (`-03:00`). Los tests construyen turnos futuros respecto del reloj fijo y, para "iniciado/pasado", insertan el turno directamente o crean con un reloj y cancelan con otro posterior, ya que `POST /turnos` no permite crear en el pasado.

### 9. Test de concurrencia
Mismo enfoque que `test_concurrencia_turnos.py`: catálogo y un turno ficticio commiteados en conexión propia; N=5 hilos sincronizados con `threading.Barrier`, cada uno con su `Session` y su `CancelarTurno` con motivo distinto; se espera exactamente 1 éxito, N-1 `TurnoNoCancelableError("turno_ya_cancelado")`, y en la base el motivo del hilo exitoso; limpieza en `finally`.

## Risks / Trade-offs

- [`FOR UPDATE` alarga la espera de un segundo pedido concurrente] → la transacción de cancelar es corta (una lectura y un UPDATE); aceptado.
- [Observadores futuros dentro de la transacción mantienen el lock de fila] → aceptado como en C-03; C-12 evaluará post-commit.
- [`inicio == ahora` → 409 difiere del alta (acepta `inicio == ahora`)] → documentado aquí y en el spec; cubierto por test de límite.
- [No idempotencia: un reintento de red tras un 200 perdido recibe 409] → el 409 lleva `codigo = turno_ya_cancelado`, que el cliente puede tratar como éxito; aceptado para el MVP.
- [El endpoint queda sin autenticación hasta C-06] → igual que `POST /turnos`; C-06 lo protegerá por rol (recepcionista).

## Migration Plan

Sin cambios de esquema: no hay migración nueva ni rollback de BD. El despliegue es solo código; revertir el change elimina la ruta sin afectar datos (los turnos cancelados ya eran válidos para el esquema de `003`). `test_modelos_vs_migracion.py` debe seguir verde sin cambios.
