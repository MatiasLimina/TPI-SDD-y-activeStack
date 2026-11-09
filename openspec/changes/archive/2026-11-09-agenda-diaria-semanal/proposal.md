# Proposal

## Why

Hoy se pueden crear, reprogramar y cancelar turnos (C-03..C-05) y bloquear franjas (C-11), pero no hay forma de **ver** la agenda: no existe ninguna consulta de turnos por fecha, y `GET /bloqueos` (DD-30 k) no admite rango a propósito, porque los rangos se dejaron para este change. US-008 pide que la recepcionista vea la agenda diaria y semanal de todos los profesionales y sillones, y que el odontólogo vea solo la suya (RN-AU-02), con los horarios en `America/Argentina/Buenos_Aires` (RN-CU-04). Es el último change del backend MVP (GATE 7) y del camino crítico antes del frontend: C-14 y C-15 dependen de este contrato.

## What Changes

- **`GET /turnos?desde&hasta&profesional_id&sillon_id`** para ambos roles autenticados: `desde` y `hasta` son días del calendario local; la API convierte ese rango local a un intervalo de instantes en UTC, consulta y responde con los turnos y los bloqueos del rango (Flujo 7).
  - Un turno o bloqueo entra si **se superpone** con el rango (criterio `[)`, DD-03), así que un bloqueo de varios días aparece en cada día que cubre y un turno contiguo al borde no se cuela.
  - Filtros opcionales por profesional y por sillón, combinables. El de sillón aplica solo a los turnos: los bloqueos son por profesional (DD-30 d).
  - Cada turno incluye el `id`, `nombre` y `apellido` del paciente, los mismos campos que el odontólogo ya puede leer (DD-31 a), para que la agenda no necesite un pedido por paciente (nota de coordinación de C-09).
  - Rango inválido (`hasta` anterior a `desde` o más largo que una semana) → `422 rango_invalido`; parámetros faltantes o mal formados → `422` de validación.
- **Aislamiento del odontólogo** (RN-AU-02): ve solo los turnos y bloqueos de su profesional; si omite el filtro se usa el suyo, y otro profesional (exista o no) da `403 profesional_ajeno`, como en `GET /bloqueos` (DD-27 i, DD-30 k).
- **Sin migración**: los índices `(profesional_id, inicio)` y `(sillon_id, inicio)` de `turno` y `(profesional_id, inicio)` de `bloqueo` ya existen; la cabeza de Alembic sigue en `010`.
- El escenario de `service-health` que usaba `GET /turnos` como ejemplo de ruta inexistente pasa a usar otra ruta.

## Non-goals

- Escritura de turnos o bloqueos: `POST /turnos`, cancelar, reprogramar y `/bloqueos` no cambian.
- Consulta de disponibilidad o huecos libres (US-007, backlog de `CHANGES.md`), horarios de atención en la respuesta (tienen su propio `GET`, C-10) y vistas mensuales o de rango libre.
- Estado de los recordatorios (pregunta abierta de `10_preguntas_abiertas.md`): C-13 no lo agrega, sigue abierta.
- Auditoría (C-07 audita escrituras, una consulta no se audita) y frontend (C-14..C-16).
- Nombres de profesional, sillón y prestación embebidos: ambos roles ya los leen de los catálogos (matriz de `03`).

## Capabilities

### New Capabilities
- `consulta-agenda`: consulta de la agenda por rango de días locales con turnos y bloqueos que se superponen con el rango, filtros por profesional y sillón, aislamiento del odontólogo, conversión de zona horaria y contrato de errores.

### Modified Capabilities
- `service-health`: el escenario "Ruta inexistente" del requisito "Sin endpoints de negocio en la base" deja de usar `GET /turnos`, que pasa a existir.

## Impact

- **Código nuevo**: `backend/app/domain/agenda.py` (rango local → UTC y su validación, profesional según el rol), `backend/app/application/consulta_agenda.py` (caso de uso).
- **Código modificado**: `backend/app/api/turnos.py` (ruta `GET ""` con `UsuarioDeAmbosRoles`, schemas de salida de la agenda y manejador de `rango_invalido`), `backend/app/infrastructure/db/repositorio_turnos.py` (consulta por intervalo con el paciente) y `backend/app/infrastructure/db/repositorio_bloqueos.py` (consulta por intervalo). `backend/app/domain/horarios.py` solo si hace falta un mensaje propio para `profesional_ajeno`.
- **API**: 1 ruta nueva. Ningún contrato existente cambia.
- **Base de datos**: sin migración ni índices nuevos (ver `design.md`).
- **Tests existentes**: ninguno cambia; `test_health.py` ya no usa `/turnos`.
- **KB**: registrar las decisiones aprobadas como **DD-32** en `09_decisiones_y_supuestos.md`, alinear la fila Turnos de `02_descripcion_general.md` (nombres de los parámetros) y el Flujo 7 de `07_flujos_principales.md` si se aprueba responder en hora local (ver D7 de `design.md`), y marcar en `10_preguntas_abiertas.md` lo que se resuelva.
- **Governance**: MEDIO. Las decisiones de `design.md` que no fija la KB quedan **pendientes de aprobación del usuario** antes del Apply.
