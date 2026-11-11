# Revisión de escenarios — frontend-agenda-ajustes-revision (seguimiento de C-15)

- Fecha: 2026-11-10
- Specs revisados: `specs/frontend-agenda/spec.md`, `specs/frontend-turnos/spec.md` (más `proposal.md`, `design.md`, `tasks.md`)
- Alcance de referencia: C-15 `frontend-agenda-turnos` en `CHANGES.md` (change de seguimiento, sin entrada propia). Specs principales contrastados: `openspec/specs/frontend-agenda`, `openspec/specs/frontend-turnos`.
- Reglas aplicables: RN-AG-03 (`[)`), RN-AG-04 (5 min), DD-34 (frontend de agenda y turnos; la nota (m) sigue a (l)), DD-30/DD-32 (bloqueos, cruce de días) y los códigos 422 de las excepciones globales (`sillon_requerido`, `sillon_no_corresponde`, `referencia_invalida`). Ninguna regla de dominio nueva.
- Veredicto: LISTO PARA APPLY

## Cobertura

| Requirement | Escenarios | Esperado | Error de negocio | Borde | Reglas cubiertas |
|-------------|-----------:|:--------:|:----------------:|:-----:|------------------|
| Ancho de los elementos superpuestos (agenda) | 7 | 3 | n/a (layout) | 4 (cadena, 3 simultáneos, contiguos `[)`, MCM) | D4, DD-34, RN-AG-03 |
| Foco del selector de paciente | 3 | 2 | n/a | 1 (sin foco al montar) | D8, DD-34 |
| Esc en un campo de búsqueda | 3 | 1 | n/a | 2 (campo común, otra tecla) | D6 de C-15 |
| Reglas de agenda rechazadas (MODIFIED) | 13 (9 previos + 4 nuevos) | sí | sí (422) | sí | RN-AG-04, DD-34, códigos 422 |

Reglas del scope sin escenario: ninguna. Los tres tipos mínimos (C1) se cumplen en el conjunto: error de negocio en el requirement modificado (422), borde en el ancho (contiguos) y en el sillón (vuelta a la prestación rechazada).

Verificaciones hechas: el requirement MODIFIED conserva todos los escenarios del spec principal (9) y suma 4; los 17 tests nombrados en `tasks.md` existen por texto en `frontend/src`; los mensajes citados (`El sillón está inactivo.`) existen en el spec principal; no hay contradicción con "Carriles según las filas ocupadas" (0, 1, 0) ni con "Turnos contiguos" del spec principal; DD-34 llega a (l), así que la nota (m) de la tarea 5.1 es correcta; no hay cambios de backend ni reglas de otros changes (auth, auditoría, horarios, bloqueos). Datos ficticios (RN-CU-02): "Imaginaria, Carla". Sin reloj ni zona horaria en juego (C6 no aplica, salvo horas locales explícitas).

## Hallazgos

Sin BLOQUEANTE ni MAYOR.

### H1 — "Ambos códigos de sillón" queda ambiguo · MENOR
- **Dónde**: `specs/frontend-turnos/spec.md`, requirement MODIFIED "Reglas de agenda rechazadas por la API", frase "Ambos códigos de sillón MUST releer los catálogos"
- **Problema**: la frase nueva sobre `referencia_invalida` introduce un tercer código de sillón antes de "Ambos códigos de sillón", y no se sabe si "ambos" lo incluye. El escenario "Otro error de sillón no fuerza el campo" no exige releer catálogos, aunque el spec principal ("Referencias inválidas") sí lo hace.
- **Fuente**: C7 (ambigüedad); `openspec/specs/frontend-turnos/spec.md` §Referencias inválidas.
- **Sugerencia**: escribir "`sillon_requerido` y `sillon_no_corresponde` MUST releer los catálogos (D7)".

### H2 — El escenario "Carriles sin ancho mínimo" no tiene un test que lo ejercite tal cual · MENOR
- **Dónde**: `specs/frontend-agenda/spec.md` escenario "Carriles sin ancho mínimo" y `tasks.md` 1.3
- **Problema**: el GIVEN es un grupo de 3 elementos, pero la tarea 1.3 lo mapea al test `con grupos de dos y tres carriles` (`repeat(6, minmax(0px, 1fr))`). El THEN ("entra en el ancho de la columna", "el texto se recorta") no se puede afirmar con un `assert` en jsdom.
- **Fuente**: C5 (verificabilidad), C9.
- **Sugerencia**: reformular el THEN a lo afirmable ("las divisiones se definen con `minmax(0, 1fr)`, sin mínimo en píxeles") y acotar la tarea 1.3 para que diga que cubre ese THEN con el test de grupos 2 y 3, o agregar un test con un grupo de 3.

### H3 — "Esc en un campo de texto común": THEN contradictorio · MENOR
- **Dónde**: `specs/frontend-turnos/spec.md`, escenario "Esc en un campo de texto común"
- **Problema**: dice que el diálogo no "se cierra por su cuenta" y a la vez que lo resuelve el navegador (que cierra un `<dialog>` con `Esc`). Lo que el test afirma es que no se cancela el evento ni se llama a `close()` desde el componente.
- **Fuente**: C5.
- **Sugerencia**: "entonces el diálogo no cancela el evento ni llama a `close()`; el comportamiento queda en manos del navegador".

### H4 — Foco y `Esc` sin cita de decisión · MENOR
- **Dónde**: requirements "Foco del selector de paciente" y "Esc en un campo de búsqueda"
- **Problema**: el de foco cita solo D8 (de C-15) y el de `Esc` no cita nada. Los de agenda citan D4 y DD-34.
- **Fuente**: C2 (trazabilidad).
- **Sugerencia**: citar DD-34 (nota (m) de la tarea 5.1) y D6/D8 de C-15.

## Sugerencias (sin fuente en la KB; decide el equipo)

- **S1**: el design (A6) reconoce que un segundo `sillon_requerido` con otra prestación reemplaza al primero, y no hay escenario. Si se quiere fijar, agregar uno; si no, dejarlo como límite aceptado.
- **S2**: no hay escenario para un selector que se monta con un paciente ya elegido (por ejemplo, al reabrir el formulario): el foco no debería moverse. El design lo dice ("solo si lo pidió una acción del usuario") pero el spec solo cubre el montaje sin paciente.
- **S3**: la tarea 1.2 mezcla cuatro escenarios en tres nombres de test, y 4.1 y 4.3 verifican "los escenarios existentes siguen en verde" sin listarlos; aceptable por ser un change sin código.

## Preguntas abiertas

Ninguna nueva para `10_preguntas_abiertas.md`: los escenarios describen comportamiento de interfaz ya implementado y no fijan reglas de dominio.

## Fuera de esta revisión

- Ancho real en píxeles y `Esc` en Chrome (manuales, tareas 1.4 y 3.2).
- No se ejecutaron los tests; se verificó solo que los nombres existen.
