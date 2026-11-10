# Proposal

## Why

El backend de la agenda y de los turnos está completo (C-03, C-04, C-05, C-07, C-09, C-11, C-12, C-13) y C-14 dejó la base del frontend, pero `/agenda` sigue siendo una pantalla provisoria: ni la recepcionista ni el odontólogo pueden usar el sistema para lo que existe (US-004, US-005, US-006, US-008). Este change construye esa pantalla sobre la sesión, el cliente HTTP y las guardas de C-14. **Responsable**: Nico. **Revisa**: Matías. **Governance**: MEDIO.

## What Changes

- **Agenda diaria y semanal** en `/agenda`, para ambos roles, filtrable por profesional y por sillón, con los horarios siempre en `America/Argentina/Buenos_Aires`, sea cual sea la zona del navegador (RN-CU-04). Consume `GET /turnos` (DD-32) y resuelve los nombres de profesionales, sillones y prestaciones con los catálogos.
- **Odontólogo**: ve solo la agenda de su profesional, de solo lectura, sin controles de crear, reprogramar ni cancelar (RN-AU-02).
- **Formularios de la recepcionista**: crear, reprogramar y cancelar un turno, con selector de paciente sobre `GET /pacientes?q=`, manejo de los `409` y `422` reales de la API y conservación de los datos cargados ante un error.
- **Presentación de los casos difíciles de la agenda**: turnos cancelados junto a programados en el mismo horario (DD-32 f), turnos que cruzan la medianoche y bloqueos de varios días (DD-32 e).
- **Refresco y concurrencia**: la agenda se relee después de cada escritura y las respuestas que llegan fuera de orden se descartan.
- **Spec modificado**: `/agenda` deja de ser una pantalla provisoria en `frontend-sesion`.
- **Primer CSS del frontend**: C-14 no tiene estilos y la grilla los necesita (design D5).

Las decisiones que la KB no fija figuran en `design.md` con sus trade-offs. El usuario las aprobó el 2026-11-10 con la opción recomendada, junto con las respuestas P1 a P15 de la revisión de escenarios (tarea 1.2); se registran como **DD-34**.

## Non-goals

- Pantallas de configuración, gestión de pacientes y gestión de bloqueos, y vista de auditoría de un turno: son de C-16. La agenda muestra los bloqueos, pero no los crea ni los borra.
- UI del estado de los recordatorios: la lectura sigue como pregunta abierta en `10_preguntas_abiertas.md` y ningún endpoint la expone.
- Consulta de huecos libres: `GET /disponibilidad` **no existe** en `backend/app` y US-007 está en el backlog de `CHANGES.md`. El formulario no la usa.
- Crear un turno haciendo clic en una celda vacía, arrastrar turnos y actualización automática por sondeo o WebSocket.
- Sombrear los horarios de atención en la grilla (`GET /profesionales/{id}/horarios`): las reglas de horario las informa la API con `422 fuera_de_horario`.
- Gestor de estado, kit de UI, librería de fechas, librería de formularios y MSW.
- Cambios en el backend y en la base de datos: la cabeza de Alembic sigue en `010`.

## Capabilities

### New Capabilities
- `frontend-agenda`: visualización de la agenda diaria y semanal, filtros, presentación horaria, turnos cancelados, turnos y bloqueos que cruzan días, vista del odontólogo, carga y respuestas fuera de orden.
- `frontend-turnos`: crear, reprogramar y cancelar turnos desde la SPA, selector de paciente, interpretación de los errores de la API y refresco posterior.

### Modified Capabilities
- `frontend-sesion`: el requirement "Layout de la aplicación" deja de exigir que `/agenda` sea una pantalla provisoria sin pedidos a la API; `/configuracion` lo sigue siendo hasta C-16.

## Impact

- **Código nuevo**: `frontend/src/features/agenda/`, `features/turnos/`, `features/pacientes/`, `shared/tiempo/`, `shared/ui/`, `shared/estilos/` y helpers en `frontend/src/test/`.
- **Código modificado**: `frontend/src/pages/PaginaAgenda.tsx`, `main.tsx` (hoja base), `vite.config.ts` (zona de los tests) y `test/setup.ts`. La sesión, el cliente HTTP y las guardas no cambian.
- **Tests de C-14**: los que renderizan `/agenda` y encolan respuestas de `fetch` deben adaptarse, porque la pantalla ahora hace pedidos al montarse (tarea 2.3).
- **API consumida, sin cambios**: `GET /turnos`, `POST /turnos`, `PATCH /turnos/{id}/reprogramar`, `POST /turnos/{id}/cancelar`, `GET /profesionales`, `GET /sillones`, `GET /prestaciones`, `GET /pacientes`.
- **Dependencias**: ninguna nueva.
- **Documentación**: `knowledge-base/09` (DD-34), `10`, `02` y `07` (`GET /disponibilidad` no implementado), `08` (`shared/tiempo`, `shared/ui`, `shared/estilos`), `CLAUDE.md`, `AGENTS.md` y `CHANGES.md`.
