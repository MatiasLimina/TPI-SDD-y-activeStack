# Tasks

> Governance BAJO. Change de seguimiento de C-15 (revisión del PR #16), en la rama `feat/c-15-frontend-agenda-turnos`. **Sin código de producción nuevo**: el comportamiento ya existe (`d114cda`, `fa2c754`, `81bc2eb`, `6b3fbdc`, y `bc3b31d` para el ancho mínimo). Cada tarea confirma que un escenario tiene su test en verde; si alguno no lo tuviera, se escribe el test (debe pasar sin tocar producción) y, si falla, se vuelve a Propose. Correr desde `frontend/`. No leer `.env*`.

## 1. Ancho de los elementos superpuestos (`frontend-agenda`)

- [x] 1.1 Safety net: correr `npx vitest run` y anotar la cantidad de tests en verde (los 7 archivos de este change suman 170 al 2026-11-10).
- [x] 1.2 Confirmar en verde `grilla.test.ts` › `asignarCarriles` para "Elemento aislado en una columna con superposiciones" (`un elemento aislado ocupa un grupo de un carril…`), "Cadena de superposiciones" (`en una cadena A-B-C…`), y "Tres elementos simultáneos" y "Tramos contiguos" (`tres elementos simultáneos forman un grupo de tres carriles; dos tramos contiguos son grupos separados`).
- [x] 1.3 Confirmar en verde `GrillaAgenda.test.tsx` › `GrillaAgenda: ancho por grupo de superposición` para "Ancho completo para el aislado y mitades para los superpuestos" (`el elemento aislado ocupa todo el ancho…`), "Grupos de distinto tamaño en la misma columna" (`con grupos de dos y tres carriles, la rejilla se divide en seis…`, por los `grid-column` de cada elemento) y "Carriles sin ancho mínimo" (el mismo test, por su `expect` de `gridTemplateColumns` igual a `repeat(6, minmax(0px, 1fr))`). Que el texto se recorte es manual (1.4).
- [x] 1.4 Verificación manual en el navegador: en la vista diaria, un turno aislado ocupa toda la columna y dos superpuestos, una mitad cada uno; en la semanal, las siete columnas miden lo mismo y el texto se recorta con puntos suspensivos. Hecho el 2026-11-10 con datos del seed: en la diaria, los dos turnos de las 10:00 (uno cancelado) miden 597 px cada uno y el aislado de las 15:00, 1195 px; en la semanal, las siete columnas miden 164 px y el texto usa `text-overflow: ellipsis`.

## 2. Foco del selector de paciente (`frontend-turnos`)

- [x] 2.1 Confirmar en verde `SelectorPaciente.test.tsx` › `Resultados de la búsqueda de pacientes` para "Foco tras elegir un paciente" (`tras elegir un paciente con Enter, el foco pasa a Cambiar paciente…`), "Foco tras cambiar de paciente" (`tras Cambiar paciente, el foco pasa al campo de búsqueda`) y "Sin foco al mostrarse" (`al montar el selector no roba el foco`).

## 3. `Esc` en un campo de búsqueda (`frontend-turnos`)

- [x] 3.1 Confirmar en verde `shared/ui/Dialogo.test.tsx` › `Esc dentro de un campo de búsqueda` para "Esc en el campo de búsqueda" (`cierra el diálogo con una sola pulsación…`), "Esc en un campo de texto común" (`en un campo de texto común no interviene…`) y "Otra tecla en el campo de búsqueda" (`otras teclas en el campo de búsqueda no lo cierran`).
- [x] 3.2 Verificación manual en Chrome: con texto en `Buscar paciente` dentro de `Nuevo turno`, un solo `Esc` cierra el diálogo, y `Nuevo turno` vuelve a abrirse. Hecho el 2026-11-10 en Chrome 152: con `car` escrito, un `Esc` cerró el diálogo y `Nuevo turno` volvió a abrirlo con el buscador vacío.

## 4. Sillón forzado solo para la prestación rechazada (`frontend-turnos`)

- [x] 4.1 Confirmar en verde `FormularioNuevoTurno.test.tsx` › `Formulario de nuevo turno: sillón tras un rechazo de la API` para "Otro error de sillón no fuerza el campo" (`tras un sillón rechazado, cambiar a una prestación sin sillón lo oculta y el POST no incluye sillon_id`), "Sillón forzado solo para la prestación rechazada" (`tras sillon_requerido, otra prestación sin sillón no muestra el campo`) y "Vuelta a la prestación rechazada" (`tras sillon_requerido, el campo sigue visible al volver a la prestación rechazada`).
- [x] 4.2 Confirmar en verde `useEnvioTurno.test.ts` › `useEnvioTurno: sillón forzado` (`sillon_requerido fuerza el sillón solo para la prestación del envío rechazado`, `un sillón inexistente marca el campo pero no lo fuerza`), que respalda la regla del requirement a nivel del hook.
- [x] 4.3 Confirmar en verde `FormularioReprogramar.test.tsx` › `Formulario de reprogramación: sillón tras un rechazo de la API` para "Sillón requerido al reprogramar" (`sillon_requerido con el catálogo desactualizado muestra el campo Sillón`), y que los escenarios existentes del requirement siguen en verde.

## 5. Documentación y cierre

- [x] 5.1 Agregar a DD-34 (`knowledge-base/09_decisiones_y_supuestos.md`) una nota (m) con A1 a A4 y A6 de `design.md` (ancho por grupo de superposición sin mínimo por carril, columnas de igual ancho con mínimo de `7rem`, foco del selector, `Esc` en un campo de búsqueda, sillón forzado solo para la prestación rechazada), con origen en este change; verificar que nombra `frontend-agenda-ajustes-revision`.
- [x] 5.2 Agregar a C-15 en `CHANGES.md` la línea `Seguimiento: frontend-agenda-ajustes-revision (revisión del PR #16)`, como en C-12; verificar con `grep`.
- [x] 5.3 `npm run typecheck`, `npm run lint`, `npm run format:check`, `npx vitest run` y `npm run build` limpios, sin diff en `frontend/src` de producción, y `openspec validate frontend-agenda-ajustes-revision --strict` sin errores.
