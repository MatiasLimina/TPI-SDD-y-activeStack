# Proposal

## Why

El backend de configuración, pacientes, bloqueos y auditoría está completo (C-07, C-08, C-09, C-10, C-11) y C-15 dejó la agenda y los turnos en la SPA, pero la recepcionista todavía no puede dar de alta un profesional, cargar un horario, registrar un paciente ni ver quién modificó un turno sin usar la API a mano, y el odontólogo no puede bloquear su agenda (US-001, US-002, US-003, US-009, US-011). `/configuracion` sigue siendo la pantalla provisoria de C-14. Este change es el último del roadmap y cierra el MVP del lado del frontend. **Responsable**: Matías. **Revisa**: Nico. **Governance**: BAJO.

## What Changes

- **Configuración del consultorio** (solo recepcionista, RN-AU-03): `/configuracion` deja de ser provisoria y se divide en secciones de profesionales, sillones, prestaciones y horarios de atención. Cada recurso tiene listado con activos e inactivos, alta, edición parcial y desactivación con confirmación, sin reactivación (DD-26). Los horarios se gestionan por profesional, agrupados por día de la semana (DD-27).
- **Pacientes** (solo recepcionista, DD-31 b): pantalla `/pacientes` con búsqueda paginada, alta, edición y desactivación. El texto buscado no va a la URL.
- **Bloqueos de agenda** (ambos roles, RN-HB-02, RN-AU-02): pantalla `/bloqueos` con listado, alta y borrado. La recepcionista opera sobre cualquier profesional; el odontólogo, solo sobre el suyo y sin elegir profesional. El `409 bloqueo_con_turnos` muestra los turnos afectados con un enlace a la agenda (RN-HB-03).
- **Historial de un turno** (solo recepcionista, DD-25): desde el detalle del turno en la agenda, un diálogo con los registros de `GET /turnos/{id}/auditoria`: acción, instante en hora local, autor y qué cambió.
- **Patrón compartido de gestión**: listados con carga, error y `Reintentar`; formularios en diálogo con `noValidate`, errores por campo y conservación de lo cargado; confirmación antes de desactivar o borrar; relectura tras cada escritura; textos propios por `codigo`. Las seis pantallas lo reutilizan para comportarse igual.
- **Navegación por rol**: el layout suma `Pacientes` y `Bloqueos` para la recepcionista, y `Bloqueos` para el odontólogo. `/pacientes` y `/configuracion/*` se protegen con la guarda por rol de C-14.
- **Rótulo del período en la agenda** (brecha de C-15 hallada en la comprobación manual, aprobada por el usuario el 2026-11-11, D19): la barra de la agenda muestra el día (`Jueves 12/11/2026`) o la semana (`Semana del 09/11 al 15/11/2026`) en hora del consultorio, y se actualiza al navegar.
- **La agenda sigue al turno guardado** (brecha de C-15, D20): si el turno creado o reprogramado cae fuera del período visible, la agenda navega a su día en lugar de releer un período donde no está.
- **Encabezados de columna fijos** (brecha de C-15, D21): el encabezado de cada columna queda arriba al desplazar la grilla.
- **Navegación con estilo**: los enlaces del layout se ven separados y el de la página actual se distingue (presentación pura, tarea 11.1).
- **Sesión**: la SPA lee también el claim `sub` (id del usuario), solo para mostrar `Vos` como autor en el historial. No cambia qué token es válido.

Las decisiones que la KB no fija figuran en `design.md` con sus alternativas. El usuario aprobó D1, D2, D3, D7, D8 y D10 el 2026-11-11 (tarea 1.2) y decidió el mismo día D15, D17 y D18, que surgieron de la revisión de escenarios, y D19, D20 y D21, halladas en la comprobación manual.

## Non-goals

- **Cambios de backend o de base de datos**: la API tiene todo lo que estas pantallas necesitan. La cabeza de Alembic no cambia.
- **Nombre del autor en la auditoría**: la API expone solo `usuario_id` (DD-25 f) y no hay endpoint de usuarios (DD-16). Se registra como limitación en el backlog.
- **Reactivar recursos o pacientes**: la API no lo permite (DD-26 d, DD-31 k).
- **Editar bloqueos**: la API no lo permite (DD-30 c). Para cambiar uno, se borra y se crea otro.
- **Vistas de solo lectura del catálogo y del horario para el odontólogo**: la API se las permite, pero ninguna historia de usuario las pide. La agenda ya muestra los nombres (design D3, aprobada el 2026-11-11).
- **Gestión de usuarios**: es por seed y CLI (DD-16).
- **Estado de los recordatorios**: sigue como pregunta abierta en `10_preguntas_abiertas.md`.
- **Bloqueos por sillón** (DD-30 d) y **auditoría de bloqueos o pacientes** (RN-CU-01 audita solo turnos).
- **Dependencias nuevas**: sin gestor de estado, kit de UI, librería de formularios ni librería de fechas.

## Capabilities

### New Capabilities
- `frontend-gestion`: comportamiento compartido de las pantallas de gestión. Cubre la carga de listados con error y reintento, las respuestas fuera de orden, los formularios en diálogo (obligatorios, errores por campo, conservación de datos, edición parcial), la confirmación de acciones destructivas, la relectura tras escribir y los `403`, `401` y fallas de red.
- `frontend-recursos`: secciones de profesionales, sillones y prestaciones dentro de `/configuracion`. Incluye los campos de cada recurso, los duplicados, la duración de la prestación, la desactivación y los inactivos.
- `frontend-horarios`: sección de horarios de atención. Cubre la elección del profesional, las franjas por día, el alta, la edición, el borrado y los errores `franja_invalida` y `franja_superpuesta`.
- `frontend-pacientes`: pantalla `/pacientes`. Cubre la búsqueda y la paginación, el alta, la edición, el documento duplicado, la desactivación y la privacidad del texto buscado.
- `frontend-bloqueos`: pantalla `/bloqueos` para ambos roles. Cubre el listado y el filtro, los bloqueos terminados, el alta con hora local, el `409` con turnos afectados y el borrado según el rol.
- `frontend-auditoria`: historial de un turno desde la agenda. Cubre el acceso solo para la recepcionista, la presentación de cada registro y los errores.

### Modified Capabilities
- `frontend-turnos`: "Alta exitosa" (MODIFIED, la agenda sigue al turno creado) y "Agenda sigue al turno reprogramado" (ADDED).
- `frontend-agenda`: se suma el requirement "Rótulo del período visible" (ADDED).
- `frontend-sesion`: "Layout de la aplicación" (`/configuracion` deja de ser provisoria y se suman los enlaces a pacientes y bloqueos), "Guarda por rol" (`/pacientes` también es exclusiva de la recepcionista) y "Datos de la sesión tomados del token" (se lee `sub` como dato opcional).

## Impact

- **Código nuevo**: `frontend/src/features/gestion/` (patrón compartido), `features/recursos/`, `features/horarios/`, `features/pacientes/` (pantalla, junto al `SelectorPaciente` existente), `features/bloqueos/`, `features/auditoria/`, y `pages/PaginaPacientes.tsx` y `pages/PaginaBloqueos.tsx`.
- **Código modificado**: `pages/PaginaConfiguracion.tsx` (deja de ser provisoria y pasa a tener subrutas), `App.tsx` (rutas), `shared/layout/Layout.tsx` (enlaces), `features/sesion/claims.ts` (`sub`), `features/agenda/DetalleTurno.tsx` y `pages/PaginaAgenda.tsx` (`Ver historial`), `features/agenda/BarraAgenda.tsx` y `vistaAgenda.ts` (rótulo del período, D19; encabezados fijos, D21), `features/turnos/` y `pages/PaginaAgenda.tsx` (navegar al turno guardado, D20), y `test/apiFalsa.ts` y `test/fabricas.ts` (respuestas y datos ficticios nuevos).
- **Tests de C-14 y C-15 a adaptar**: el scenario "Pantallas provisorias sin pedidos" conserva su nombre pero ahora comprueba que ninguna ruta es provisoria (design, Risks), y los tests que navegan a `/configuracion` ahora necesitan respuestas de la API falsa.
- **API consumida, sin cambios**: `GET`/`POST`/`PATCH` y `POST .../desactivar` de `/profesionales`, `/sillones`, `/prestaciones` y `/pacientes`; `GET`/`POST`/`PATCH`/`DELETE` de `/profesionales/{id}/horarios`; `GET`/`POST`/`DELETE` de `/bloqueos`; `GET /turnos/{id}/auditoria`.
- **Dependencias**: ninguna nueva.
- **Documentación**: `knowledge-base/09` (DD-35 con las decisiones aprobadas), `10` (preguntas resueltas), `08` (estructura de `features/`), `CHANGES.md` (C-16 completo y la limitación del autor en el backlog), y `CLAUDE.md` y `AGENTS.md`.
