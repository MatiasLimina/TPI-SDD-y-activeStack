# Resumen del explore — `crear-turno-sin-solapamientos` (C-03)

> Sesión de explore del 2026-10-07. Nota de nombre: el usuario escribió `crear-turno-sin-solapamiento` (singular); se usó el nombre del roadmap, `crear-turno-sin-solapamientos` (plural), para mantener la trazabilidad con `CHANGES.md`.

## 1. Contexto

- **Change**: C-03 `crear-turno-sin-solapamientos`, elegido para el ciclo OPSX (US-004 parcial). Governance: MEDIO.
- **Dependencias**: C-01 (`foundation-scaffolding-test-harness`) y C-02 (`catalogo-minimo-modelos-seed`), ambos archivados.
- **Lo que ya existe en el código**:
  - Extensión `btree_gist` instalada por la migración `001`, lista para las restricciones de exclusión.
  - Catálogo (`profesional`, `sillon`, `prestacion` con `duracion_min` y `requiere_sillon`, `paciente`) en la migración `002`, con seed ficticio.
  - `backend/app/domain/time.py`: `to_utc`, `to_local`, `NaiveDatetimeError`, `DEFAULT_TIMEZONE`.
  - Fixtures de test contra PostgreSQL real (`backend/tests/conftest.py`: `engine` con `alembic upgrade head`, `db_session` revertida por test, `client`, `scratch_url`).
  - `backend/app/application/` vacío: este change crea el primer caso de uso.

## 2. Flujo del caso de uso

```
POST /turnos {profesional, paciente, prestacion, sillon?, inicio, duracion_min?}
      |
      v
+--------------------------- caso de uso CrearTurno ---------------------------+
|  1. cargar recursos -----> inexistente o inactivo -> 422                     |
|  2. dominio puro:                                                            |
|       duracion = req.duracion_min ?? prestacion.duracion_min                 |
|       %5, <=480, inicio alineado a 5 min (hora AR) ---- falla -> 422         |
|       inicio < ahora (reloj inyectado) ---------------- falla -> 422         |
|       requiere_sillon && !sillon ---------------------- falla -> 422         |
|       !requiere_sillon && sillon ---------------------- falla -> 422         |
|       fin = inicio + duracion                                                |
|  3. [hook] validadores extra (C-10 horario, C-11 bloqueos) -- vacios         |
|  4. pre-chequeo de solape (profesional, sillon, paciente) -> 409 con lista   |
|  5. INSERT -----> 23P01 exclusion_violation --> 409 {recurso}                |
|  6. [hook] observadores (C-07 auditoria, C-12 recordatorio) -- vacios        |
+------------------------------------------------------------------------------+
                                 |
                                 v
     garantia real: EXCLUDE USING gist (profesional) + (sillon) + (paciente)
```

## 3. Decisiones tomadas

| # | Decisión | Consecuencia | Referencia |
|---|----------|--------------|------------|
| D1 | No se permite solape por **paciente**, aunque sea con otro profesional | Tercera restricción de exclusión `turno_sin_solape_paciente`; turnos contiguos del mismo paciente siguen siendo válidos | RN-AG-14, DD-20 |
| D2 | `sillon_id` enviado con una prestación que no requiere sillón -> `422` | No se ignora ni se guarda el sillón sobrante; el turno sin sillón no participa del solape por sillón | RN-AG-10, DD-21 (a) |
| D3 | `409` = pre-chequeo en la aplicación que lista **todos** los recursos en conflicto + restricción en BD como garantía | Ante carreras, `23P01` se traduce a `409` con el recurso deducido de `constraint_name` | Excepciones globales de 05, DD-21 (b) |
| D4 | Referencia inexistente en el body -> `422` (igual que inactiva) | `404` queda solo para recursos del path | DD-21 (c) |
| D5 | `estado` como `varchar` + `CHECK ('programado','cancelado')` | Agregar estados futuros es cambiar un CHECK, sin `ALTER TYPE` | DD-21 (d) |

## 4. Alternativas descartadas

- **Permitir el solape de paciente**: riesgo de doble reserva del mismo paciente en el mismo horario, que la recepción no detectaría a simple vista.
- **Ignorar o guardar el sillón sobrante**: oculta un error de carga y deja datos incoherentes (un turno que "ocupa" un sillón que la prestación no usa).
- **409 solo desde la BD**: la restricción dispara una sola vez e informa un único recurso (el primero que choca); la recepción no sabe todo lo que tiene que cambiar.
- **404 para referencias del body**: confunde "el endpoint/recurso del path no existe" con "el pedido trae datos inválidos".
- **Enum nativo de PostgreSQL**: agregar valores exige `ALTER TYPE` y migraciones más costosas.

## 5. Pendientes para el design (y cómo se resolvieron)

- **Reloj inyectable (RN-AG-12)**: resuelto como `Reloj = Callable[[], datetime]` (instante UTC con zona) inyectado en `CrearTurno` y provisto en la API por la dependencia `get_reloj()`, que los tests sobreescriben con un reloj fijo. Se descartó `freezegun` (parchea `datetime` global, frágil con hilos del test de concurrencia) y leer `datetime.now()` dentro del dominio.
- **Hooks**: resueltos como dos listas inyectadas en el constructor del caso de uso, vacías por defecto: `validadores` (`Callable[[TurnoPropuesto], None]`, corren tras las reglas de dominio y antes del pre-chequeo; los usarán C-10 y C-11) y `observadores` (`Callable[[TurnoCreado], None]`, corren tras el `INSERT` y antes del `commit` para que la auditoría de C-07 sea atómica). Sin bus de eventos ni framework.

Detalle completo en `design.md`.

## 6. Fuera de alcance

- Autenticación (`creado_por` queda nulo; llega en C-06).
- Auditoría (C-07).
- Recordatorio (C-12).
- Horario de atención (RN-AG-05, C-10).
- Bloqueos de agenda (RN-AG-06, C-11).
- Reprogramar turno (C-05).
- Cancelar turno (C-04).
