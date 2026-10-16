---
name: revisar-escenarios
description: Revisa los escenarios GIVEN/WHEN/THEN de los specs de un change OpenSpec del sistema de turnos odontológicos contra la base de conocimiento (reglas RN-xx, decisiones DD-xx, supuestos SU-xx) y el scope del change en CHANGES.md. Detecta reglas ambiguas, casos de borde faltantes, escenarios que invaden otros changes, códigos HTTP incoherentes y specs que no cumplen el mínimo (esperado, error de negocio, borde). Usala siempre que haya que revisar, auditar, validar o "chequear" los specs, escenarios o criterios de aceptación de un change (por ejemplo C-06), después de un /opsx:propose o /opsx:update y antes de /opsx:apply, aunque el usuario no diga "escenarios". Solo reporta: no edita specs.
---

# Revisar escenarios de un change

Un escenario mal escrito se convierte en un test mal escrito: con TDD estricto, el spec es el contrato que
Apply implementa sin preguntar. Esta skill es la revisión que se hace **antes** de implementar, cuando
corregir es barato (volver a Propose) y no caro (rehacer código y tests).

La skill **solo reporta**. Las correcciones las decide el equipo y se hacen con `/opsx:update` o volviendo
a Propose, porque las reglas duras del proyecto prohíben que Apply implemente algo que no esté en el spec
aprobado. Si se edita el spec desde acá, se pierde esa trazabilidad.

## Entradas

1. **Nombre del change** (por ejemplo `auth-jwt-roles`), o el ID del roadmap (`C-06`). Si no se da, correr
   `openspec list --json` y preguntar cuál.
2. Los archivos que la skill lee por su cuenta:
   - `openspec/changes/<change>/specs/**/spec.md` — los escenarios a revisar (delta specs).
   - `openspec/changes/<change>/proposal.md`, `design.md` y `tasks.md` si existen.
   - La entrada del change en `CHANGES.md` (scope, dependencias, governance, "Leer antes").
   - Los archivos de `knowledge-base/` listados en "Leer antes", más siempre
     `05_reglas_de_negocio.md`, `09_decisiones_y_supuestos.md` y `10_preguntas_abiertas.md`.
   - `openspec/specs/*/spec.md` de las capacidades que el change modifica (para detectar contradicciones
     con lo ya archivado, por ejemplo con "Excepciones globales").

Si el change todavía no tiene specs, decirlo y terminar: no hay nada que revisar y no corresponde
inventar escenarios.

## Procedimiento

1. **Ubicar el change.** `openspec status --change "<change>" --json` para saber qué artefactos existen.
   Buscar el bloque `### [C-NN] \`<change>\`` en `CHANGES.md` y anotar scope, dependencias y qué cosas
   llegan en otros changes.
2. **Armar la lista de reglas aplicables.** De los "Leer antes" y del scope, listar cada RN-xx, DD-xx y
   SU-xx que el change debe cumplir. Esta lista es la vara contra la que se mide el spec; sin ella la
   revisión se vuelve opinión.
3. **Inventariar escenarios.** Por cada requirement, listar sus escenarios y clasificar cada uno como
   *esperado*, *error de negocio* o *borde*. Anotar qué reglas cubre cada uno.
4. **Aplicar los controles** de `references/controles.md` en orden (C1 a C9). Leer también
   `references/bordes-por-dominio.md` y usar la sección del dominio del change (agenda, auth, notificaciones,
   etc.) como lista de casos de borde a buscar.
5. **Clasificar cada hallazgo** con una severidad (ver abajo) y una **fuente**: la regla, decisión, línea
   de `CHANGES.md` o sección de la KB que lo justifica. Un hallazgo sin fuente es una opinión: o se busca la
   fuente, o se lo marca como `SUGERENCIA`.
6. **No inventar dominio.** Si detectás que falta una decisión (la KB no dice qué pasa), el hallazgo es
   "pregunta abierta para `10_preguntas_abiertas.md`", no un escenario con la respuesta que te parece
   razonable. Podés proponer opciones, pero marcadas como opciones.
7. **Escribir el informe** en `openspec/changes/<change>/revision-escenarios.md` con la plantilla de abajo
   y mostrar en el chat el resumen (veredicto + conteo por severidad + los hallazgos BLOQUEANTE).

Si el archivo ya existe (una revisión anterior), no lo pises: agregá una sección `## Revisión N — <fecha>`
al final, así queda el antes y el después.

## Severidades

| Severidad | Cuándo | Efecto |
|-----------|--------|--------|
| `BLOQUEANTE` | Contradice una RN/DD, falta uno de los tres tipos mínimos de escenario, un escenario no es verificable, o el spec implementa algo de otro change | No pasar a Apply hasta corregir |
| `MAYOR` | Falta un caso de borde que la KB define, código HTTP incoherente con las excepciones globales, regla del scope sin escenario | Corregir antes de Apply salvo decisión explícita del equipo |
| `MENOR` | Redacción ambigua, valores no concretos, GIVEN incompleto que no cambia el resultado | Corregir si se toca el spec |
| `SUGERENCIA` | Mejora sin fuente en la KB, o pregunta abierta | El equipo decide |

## Plantilla del informe

```markdown
# Revisión de escenarios — <change> (<C-NN>)

- Fecha: <AAAA-MM-DD>
- Specs revisados: <rutas>
- Reglas aplicables: <RN-.., DD-.., SU-..>
- Veredicto: LISTO PARA APPLY | CORREGIR ANTES DE APPLY

## Cobertura

| Requirement | Escenarios | Esperado | Error de negocio | Borde | Reglas cubiertas |
|-------------|-----------:|:--------:|:----------------:|:-----:|------------------|

Reglas del scope sin escenario: <lista o "ninguna">

## Hallazgos

### H1 — <título corto> · <SEVERIDAD>
- **Dónde**: <archivo>, requirement "<nombre>", escenario "<nombre>" (o "falta")
- **Problema**: <qué está mal o qué falta, en una o dos oraciones>
- **Fuente**: <RN-xx / DD-xx / CHANGES.md C-NN / archivo de la KB §sección>
- **Sugerencia**: <escenario GIVEN/WHEN/THEN propuesto, o la pregunta a resolver>

## Preguntas abiertas
<decisiones que la KB no toma; candidatas a 10_preguntas_abiertas.md>

## Fuera de esta revisión
<lo que no se pudo verificar y por qué>
```

## Cómo revisar el resultado de esta skill

Antes de aceptar el informe, el equipo controla:

- Cada hallazgo `BLOQUEANTE` o `MAYOR` cita una fuente que existe y dice lo que el hallazgo afirma
  (abrir la regla y leerla).
- Ningún escenario sugerido introduce una regla que no esté en la KB; si la introduce, debe estar en
  "Preguntas abiertas".
- La tabla de cobertura coincide con el spec (contar escenarios a mano en un requirement al azar).
- No se marcó como faltante algo que el scope de `CHANGES.md` asigna a otro change.
