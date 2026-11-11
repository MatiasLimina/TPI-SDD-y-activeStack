# Design

## Context

Ver `proposal.md` y los delta specs `frontend-agenda` y `frontend-turnos`. El código ya existe en `feat/c-15-frontend-agenda-turnos` y sus tests pasan (`grilla.test.ts`, `GrillaAgenda.test.tsx`, `SelectorPaciente.test.tsx`, `Dialogo.test.tsx`, `useEnvioTurno.test.ts`, `FormularioNuevoTurno.test.tsx` y `FormularioReprogramar.test.tsx`, 2026-11-10). Este design registra decisiones que se tomaron en la verificación manual de C-15 y no llegaron a su design archivado (`openspec/changes/archive/2026-11-10-frontend-agenda-turnos/design.md`).

Estado observado en el código:

- `asignarCarriles` (`features/agenda/grilla.ts`) devuelve, además de `carril`, `carrilesGrupo`: los carriles del grupo de superposición del elemento. Un grupo se cierra cuando un tramo visible empieza en la fila en que termina todo lo anterior o después (`fila >= finDelGrupo`), así que el criterio es `[)` y la unión es transitiva. `carriles` de la columna pasa a ser el máximo de los grupos, el mismo valor de antes.
- `GrillaAgenda.tsx` divide cada columna en el mínimo común múltiplo de los `carrilesGrupo` de sus elementos, con `repeat(n, minmax(0, 1fr))`, y cada elemento ocupa `n / carrilesGrupo` divisiones desde `carril × ancho + 1`.
- `GrillaAgenda.module.css` (desde `bc3b31d`, antes del archive): `.columna` con `flex: 1 1 0` y `min-width: 7rem`; `.item` con `min-width: 0`. El `.contenedor` tiene `overflow: auto`.
- `SelectorPaciente.tsx` mueve el foco con un efecto sobre "hay paciente elegido", solo si lo pidió una acción del usuario (`conservarFoco`).
- `Dialogo.tsx` escucha `keydown` en fase de captura y, ante `Escape` sobre un `<input type="search">`, hace `preventDefault()` y `close()`.
- `useEnvioTurno.ts` guarda `sillonForzadoPara`, la prestación del envío rechazado con `sillon_requerido`, y expone `sillonForzado(prestacionId)`. El alta lo consulta con la prestación elegida y la reprogramación con `turno.prestacion_id`, que ahora pasa en los elegidos del envío (antes, `""`). El alta incluye `sillon_id` solo si el campo se muestra.

## Goals / Non-Goals

**Goals:**
- Que specs y design describan exactamente lo que hace el código, con un test por escenario.
- Dejar sin efecto, de forma explícita, las dos frases falsas del design archivado de C-15.

**Non-Goals:**
- Cambiar código de producción. Si un escenario no tiene test, se agrega el test, no comportamiento.
- Combobox ARIA, navegación por flechas en el selector o en la grilla (siguen fuera, D8 y D17 de C-15).
- `287e745`, que solo cambia tests.

## Decisions

### A1 — Ancho por grupo de superposición, no por columna (`d114cda`)

Con un ancho por columna, un solo par de turnos superpuestos a las 10:00 partía en dos **todos** los turnos del día de esa columna, incluso los aislados, y el texto de una línea quedaba recortado sin motivo.

| Opción | A favor | En contra |
|--------|---------|-----------|
| **Ancho por grupo de superposición transitiva (elegida)** | Un turno aislado usa todo el ancho; el reparto solo afecta a quienes se pisan. Sale de la misma pasada de `asignarCarriles` | La rejilla de la columna necesita divisiones comunes (MCM) cuando conviven grupos de distinto tamaño |
| Ancho por columna (C-15 archivado) | Una rejilla de N carriles, simple | Penaliza a todos los elementos por un solapamiento puntual |
| Ancho por solapamiento directo (sin transitividad) | Cada elemento lo más ancho posible | En una cadena A-B-C, A y C tendrían anchos distintos al de B y podrían taparse; exige un algoritmo de expansión más complejo |

El grupo es transitivo porque el carril de cada elemento se asigna dentro del grupo: en una cadena A-B-C, C reusa el carril de A y los tres necesitan la misma división. El MCM (por ejemplo, 6 para grupos de 2 y 3) da divisiones enteras para todos los grupos con una sola `grid-template-columns`. No cambia la regla de superposición de C-15 (tramo visible de al menos 3 filas, `[)`): solo el ancho.

### A2 — Carriles sin mínimo de 90 px (`bc3b31d`)

El texto de una línea hacía crecer cada columna hasta su turno más largo: en la semana las columnas quedaban desparejas, con scroll horizontal y el segundo carril cortado. Se eligió columnas de igual ancho (`flex: 1 1 0`) con un mínimo de `7rem` por **columna**, y carriles con `minmax(0, 1fr)` y `min-width: 0` en el elemento, que recorta su texto con puntos suspensivos (requirement "Datos visibles de cada turno" de C-15). La alternativa de mantener 90 px por carril reproducía el problema con 3 o más carriles. El scroll horizontal queda solo para cuando las columnas no entran a `7rem`.

### A3 — Foco del selector de paciente (`fa2c754`)

Al elegir, el botón del resultado se desmonta y el navegador deja el foco en `<body>`: quien usa el teclado tiene que volver a recorrer el diálogo desde el principio. Al cambiar de paciente pasa lo mismo con `Cambiar paciente`. Se mueve el foco al control que reemplaza al que desapareció (`Cambiar paciente` o el campo), y solo cuando el cambio de modo lo provocó el usuario, para no robar el foco al abrir el formulario (el `showModal` decide el foco inicial). Es el manejo de foco mínimo para no perderlo, no un combobox: sin flechas ni `aria-activedescendant`.

### A4 — `Esc` en un campo de búsqueda (`81bc2eb`)

En Chrome, el primer `Esc` sobre un `<input type="search">` borra el texto y recién el segundo cierra el `<dialog>`. El selector de paciente es un campo de búsqueda, así que cerrar `Nuevo turno` o `Reprogramar` exigía dos pulsaciones. Se captura el `keydown` en el diálogo, solo para `Escape` sobre `type="search"`, se cancela la acción nativa y se llama a `close()`, que dispara `close` y mantiene la sincronización de D6 de C-15. La alternativa de cambiar el campo a `type="text"` perdía la semántica de búsqueda y el botón de borrado nativo; la de interceptar `Esc` en cualquier campo cambiaba sin necesidad la conducta nativa de controles que no tienen el problema: por eso un campo de texto común no se toca.

### A5 — Frases del design archivado de C-15 que quedan sin efecto

Este design **reemplaza** (supersede) en `openspec/changes/archive/2026-11-10-frontend-agenda-turnos/design.md`:

- **D1**, viñeta "Una columna con N carriles define N subcolumnas de al menos 90 px, y la grilla se desplaza en horizontal si no entra." → vale A1 y A2: cada grupo reparte el ancho de la columna entre sus carriles, sin mínimo por carril; las columnas miden lo mismo, con un mínimo de `7rem`, y la grilla se desplaza en horizontal solo si no entran.
- **D8**, fila "Forma", "Tab y Enter alcanzan para el alcance; un combobox suma manejo de foco y flechas" → vale A3: sigue sin combobox ni flechas, pero el selector conserva el foco al elegir y al cambiar de paciente.
- **D12**, fila `sillon_requerido`, "Sillón, que se muestra aunque el catálogo no lo pida" → vale A6: solo para la prestación del envío rechazado.
- **Risks**, "[Vista semanal angosta con muchos profesionales] → Subcolumnas de 90 px, scroll horizontal y filtro" → columnas de al menos `7rem`, carriles sin mínimo con texto recortado, scroll horizontal y filtro.

El archivo archivado no se edita: es el registro de lo aprobado en su momento. La referencia cruzada queda en este design y en DD-34 (tarea 5.1).

### A6 — Sillón forzado por prestación (`6b3fbdc`)

Antes, cualquier error con destino `Sillón` (también `referencia_invalida` sobre el sillón) encendía una marca global: tras un rechazo, cambiar a una prestación sin sillón seguía mostrando el campo y el alta enviaba `sillon_id`, que la API rechaza con `sillon_no_corresponde`. Solo `sillon_requerido` revela que el catálogo está desactualizado (la API exige sillón para una prestación que el catálogo dice que no lo usa), y lo revela **para esa prestación**: por eso la marca se guarda con su id.

| Opción | A favor | En contra |
|--------|---------|-----------|
| **Marca por prestación, solo con `sillon_requerido` (elegida)** | El campo sigue a la prestación elegida; no se envía un sillón que no corresponde | Una sola prestación forzada a la vez: un segundo `sillon_requerido` con otra reemplaza a la primera |
| Marca global con cualquier error de sillón (C-15 archivado) | Simple | Muestra el campo y envía `sillon_id` con prestaciones que no lo usan |
| Limpiar la marca al cambiar de prestación | Sin estado por id | Al volver a la prestación rechazada el campo desaparece, aunque la API ya dijo que lo necesita |

La relectura de catálogos de D7 sigue igual; si el catálogo releído ya marca `requiere_sillon`, la marca deja de importar.

## Risks / Trade-offs

- [Muchos carriles en una columna angosta: elementos muy finos con el texto casi oculto] → El detalle del turno muestra todo; el filtro por profesional reduce los carriles en la vista semanal.
- [Grupos de tamaños coprimos (por ejemplo, 3, 4 y 5 carriles) dan muchas divisiones (60)] → Solo afecta a la rejilla CSS, no al dibujo; con 1 a 5 profesionales y 1 a 4 sillones es improbable.
- [jsdom no aplica CSS ni el comportamiento nativo de `Esc` en `type="search"`] → Los tests afirman la ubicación (`grid-column`), la plantilla de la rejilla y la cancelación del evento; el ancho en píxeles y el `Esc` real en Chrome son verificación manual (tareas 1.4 y 3.2).
- [El nombre del test "tras elegir un paciente con Enter" dispara un clic, no la tecla] → En un `<button>` el Enter del navegador produce el clic; jsdom no lo simula. Se acepta.

## Migration Plan

Sin migración ni cambio de backend. Rollback: revertir los commits de documentación de este change.

## Open Questions

Ninguna: `6b3fbdc` se incorporó al alcance (A6) con la aprobación del usuario.
