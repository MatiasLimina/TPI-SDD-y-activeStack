# Proposal

## Why

La revisión del PR #16 (C-15, `frontend-agenda-turnos`, Nico) encontró comportamiento implementado **después** del archive de C-15 que no figura en los specs ni en el design: cuatro commits de corrección (`d114cda`, `fa2c754`, `81bc2eb` y `6b3fbdc`). Eso rompe la regla dura "NUNCA implementar en Apply algo que no esté en el spec aprobado". El usuario decidió **documentarlo, no revertirlo**: el código y sus tests ya existen. Además, dos frases del design archivado de C-15 quedaron falsas (subcolumnas de 90 px con scroll horizontal, de `bc3b31d`, y "Tab y Enter alcanzan" en el selector de paciente). Es un change de seguimiento de C-15, sin entrada propia en el roadmap. Governance BAJO.

## What Changes

- **Ancho de los carriles por grupo de superposición** (`d114cda`): un elemento sin superposiciones ocupa todo el ancho de su columna; los que se pisan, aunque sea de forma transitiva, se reparten el ancho en partes iguales según los carriles de **su** grupo, no los de la columna entera. Los carriles no tienen ancho mínimo propio (`bc3b31d`): el texto se recorta.
- **Foco del selector de paciente** (`fa2c754`): al elegir un resultado el foco pasa a `Cambiar paciente`, al cambiar de paciente vuelve al campo de búsqueda, y al montarse el selector no toma el foco.
- **`Esc` en un campo de búsqueda dentro de un diálogo** (`81bc2eb`): cierra el diálogo con una sola pulsación y evita el borrado nativo del texto; en los demás campos no interviene.
- **Sillón forzado solo para la prestación rechazada** (`6b3fbdc`): solo `sillon_requerido` muestra el campo `Sillón` cuando el catálogo no lo pide, y solo para la prestación del envío rechazado (en el alta, la elegida; al reprogramar, la del turno). Con otra prestación sin sillón el campo se oculta y el alta no envía `sillon_id`; al volver a la rechazada reaparece. Otros errores de sillón marcan el campo sin forzarlo. Precisa una frase del requirement "Reglas de agenda rechazadas por la API".
- Se registran las decisiones en `design.md` y se reemplazan explícitamente las dos frases del design archivado de C-15.
- **Sin comportamiento nuevo**: el Apply solo verifica que cada escenario tenga su test en verde y actualiza la documentación (DD-34, `CHANGES.md`).

## Capabilities

### New Capabilities
<!-- Ninguna -->

### Modified Capabilities
- `frontend-agenda`: requirement nuevo "Ancho de los elementos superpuestos".
- `frontend-turnos`: requirements nuevos "Foco del selector de paciente" y "Esc en un campo de búsqueda"; requirement modificado "Reglas de agenda rechazadas por la API" (alcance del sillón forzado).

## Impact

- Código ya existente, sin cambios previstos: `frontend/src/features/agenda/grilla.ts`, `GrillaAgenda.tsx`, `GrillaAgenda.module.css`, `frontend/src/features/pacientes/SelectorPaciente.tsx`, `frontend/src/shared/ui/Dialogo.tsx`, `frontend/src/features/turnos/useEnvioTurno.ts`, `FormularioNuevoTurno.tsx`, `FormularioReprogramar.tsx`, y sus tests.
- Documentación: `knowledge-base/09_decisiones_y_supuestos.md` (nota en DD-34) y `CHANGES.md` (seguimiento de C-15).
- Sin cambios de backend, migración ni dependencias.
- Fuera de alcance: `287e745`, que solo cambia tests.
