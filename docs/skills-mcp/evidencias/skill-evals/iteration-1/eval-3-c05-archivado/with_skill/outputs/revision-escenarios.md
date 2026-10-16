# Revisión de escenarios — reprogramar-turno (C-05)

- Fecha: 2026-10-16
- Specs revisados: `openspec/changes/archive/2026-10-14-reprogramar-turno/specs/agenda-turnos/spec.md` (delta, 10 requirements, 41 escenarios). Contexto leído: `proposal.md`, `design.md`, `tasks.md` del mismo archivo, bloque `[C-05]` de `CHANGES.md`, `knowledge-base/05` (RN-AG-01..14, RN-CU), `07` §Flujo 3, `09` (DD-15, DD-21, DD-22, DD-23), `10_preguntas_abiertas.md` y `openspec/specs/agenda-turnos/spec.md` (spec principal, ya sincronizado).
- Reglas aplicables: RN-AG-01, 02, 03, 04, 07, 08, 09, 10, 12, 13 (por simetría con cancelar), 14; DD-15, DD-18, DD-21, DD-22, DD-23; RN-CU-02, RN-CU-04.
- Nota de contexto: el change ya está archivado e implementado. La revisión es retroactiva; el veredicto se formula como si fuera antes de Apply.
- Veredicto: CORREGIR ANTES DE APPLY (sin bloqueantes; 3 MAYOR, todos de casos de borde y determinismo, ninguno contradice la KB)

## Cobertura

Clasificación: E = esperado, N = error de negocio (una RN/DD rechaza), B = borde (límite exacto de una regla).

| Requirement | Escenarios | E | N | B | Reglas cubiertas |
|-------------|-----------:|:-:|:-:|:-:|------------------|
| Reprogramación de un turno programado | 2 | 2 | 0 | 0 | RN-AG-08, DD-23 |
| Reprogramación parcial | 7 | 4 | 2 | 1 | DD-23a, RN-AG-10, DD-21 |
| Paciente y prestación no editables | 5 | 1 | 4 | 0 | DD-23b |
| Misma validación que el alta | 7 | 0 | 6 | 1 | RN-AG-08, RN-AG-04, DD-15, RN-AG-12, RN-AG-10, DD-21 |
| Sin solape, excluyendo al propio turno | 7 | 2 | 3 | 2 | RN-AG-01, 02, 03, 07, 08, 14 |
| Reprogramable solo antes del inicio | 4 | 0 | 3 | 2* | DD-23d |
| Turno cancelado no reprogramable | 3 | 0 | 3 | 0 | DD-23c, DD-22 |
| Turno inexistente | 2 | 0 | 2 | 0 | DD-21 |
| Reprogramaciones simultáneas al mismo horario | 2 | 0 | 2 | 0 | RN-AG-09, DD-18 |
| Reprogramación y cancelación simultáneas | 2 | 0 | 2 | 0 | RN-AG-08, DD-22 |

\* "un minuto antes" cuenta a la vez como esperado y borde.

Cumple el mínimo de C1 (hay esperado, error de negocio y borde, en el conjunto y en los requirements centrales). Sin bloqueantes de C3: ningún escenario cubre auditoría (C-07), recordatorio (C-12), autenticación (C-06), horarios (C-10) ni bloqueos (C-11), y los "Non-goals" de `proposal.md` coinciden con `CHANGES.md` (líneas de C-10 y C-11 asignan RN-AG-05/06 a esos changes).

Reglas del scope sin escenario: ninguna de las listadas en el scope de C-05. Hay reglas parcialmente cubiertas (ver H1, H2, H5, H6).

## Hallazgos

### H1 — Faltan los bordes de duración al reprogramar (480, 485, 0) · MAYOR
- **Dónde**: spec.md, requirement "Misma validación que el alta al reprogramar", escenario "Duración inválida" (falta el resto).
- **Problema**: el único caso de duración es `42` (no múltiplo de 5). El requirement dice "duración y grilla de 5 minutos" pero no hay escenario para 480 aceptada, 485 rechazada ni 0 rechazada, que son los límites que la KB define. Tampoco hay escenario de inicio con segundos o microsegundos (parte de DD-15).
- **Fuente**: RN-AG-04, DD-15 (múltiplo de 5, máximo 480, inicio alineado a 5 min); `references/bordes-por-dominio.md` §Agenda; CHANGES.md C-05 ("misma validación de duración y grilla").
- **Sugerencia**: agregar dos escenarios. (a) GIVEN turno `programado` futuro de 10:00 a 10:45, WHEN `duracion_min = 480`, THEN `200` y `fin` a las 18:00; WHEN `duracion_min = 485` o `0`, THEN `422` y el turno sigue de 10:00 a 10:45. (b) WHEN `inicio` 15:00:30-03:00, THEN `422` y el turno no cambia. Mitigante: la validación compartida (design §3) y los tests de C-03 cubren los límites del alta; igual el spec de C-05 no los fija.

### H2 — Borde "nuevo inicio exactamente ahora" sin escenario y con asimetría documentada solo en el design · MAYOR
- **Dónde**: spec.md, requirements "Misma validación que el alta" y "Reprogramable solo antes del inicio"; escenario "Nuevo inicio en el pasado" usa 08:55 con reloj 09:00 (cinco minutos antes, no el límite).
- **Problema**: RN-AG-12 rechaza inicios "anteriores" al momento actual, por lo que un nuevo inicio igual a `ahora` se acepta; en cambio un inicio actual igual a `ahora` cuenta como iniciado (`409 turno_ya_iniciado`). Esa asimetría está en `design.md` §11 pero ningún escenario fija el borde del lado de `422`. Apply puede implementar `<=` o `<` sin que el spec lo contradiga.
- **Fuente**: RN-AG-12; DD-23d; `design.md` §11; `references/bordes-por-dominio.md` ("Inicio en el pasado o exactamente ahora").
- **Sugerencia**: GIVEN reloj 2026-10-07 09:00 y turno `programado` de 2026-10-08 10:00, WHEN `inicio` 2026-10-07T09:00-03:00 (alineado a 5 min), THEN `200`; y con 08:55 el `422` ya existente. Si el equipo prefiere rechazar el "ahora" exacto, es decisión que debe quedar en la KB (ver Preguntas abiertas), no en el design.

### H3 — Escenarios que dependen de "ahora" sin reloj fijo e instantes sin fecha ni zona · MAYOR
- **Dónde**: spec.md, la mayoría de los GIVEN con "turno `programado` futuro de 10:00 a 10:45" (p. ej. "Cambio de profesional y de sillón", "Duración inválida", "Hueco ocupado...", "Solaparse consigo mismo", "Turno cancelado", "Turno pasado", "Turno cancelado y pasado"). Excepciones con reloj fijo: "Turno movido a un hueco libre", "Nuevo inicio en el pasado" y los tres escenarios del requirement "Reprogramable solo antes del inicio".
- **Problema**: "futuro" y "ya pasó según el reloj" sin fijar el reloj hacen el test dependiente de la hora real; además las horas "10:00 a 10:45" no traen fecha ni offset `-03:00`/`Z`.
- **Fuente**: C6 (`references/controles.md`); RN-CU-04, DD-06.
- **Sugerencia**: agregar una cláusula común (por ejemplo en el requirement o en un GIVEN de fondo) "el reloj marca 2026-10-07 09:00 hora local (-03:00) y los turnos son del 2026-10-08". Mitigante: `tasks.md` (6.1, 7.x, encabezado) exige reloj inyectado fijo, así que el riesgo es de redacción del spec, no de la implementación.

### H4 — Varios escenarios de rechazo no dicen que el turno queda intacto · MENOR
- **Dónde**: spec.md, escenarios "Paciente y prestación rechazados juntos", "Mismo paciente informado igualmente rechazado", "Campo no editable sobre un turno cancelado", "Sillón destino inexistente", "Reprogramación inválida y en conflicto", "409 que lista varios recursos", "Turno cancelado y pasado", "Turno cancelado con datos inválidos".
- **Problema**: el THEN solo da el status y el código; no afirma qué queda persistido. Los requirements sí lo exigen en general ("el turno MUST quedar intacto"), por eso baja a MENOR (C5 pone MAYOR por defecto en escrituras).
- **Fuente**: C5; RN-AG-08 ("si falla, el original no cambia"); `tasks.md` 6.4 y 7.x ya piden releer la fila.
- **Sugerencia**: agregar "y el turno sigue de 10:00 a 10:45 con su profesional y sillón" en cada uno.

### H5 — `sillon_id` nulo sin escenario del caso válido · MENOR
- **Dónde**: spec.md, requirement "Reprogramación parcial" (oración "`sillon_id` nulo quita el sillón del turno resultante").
- **Problema**: la regla tiene escenario solo en su rama de error (`{"sillon_id": null}` con "Limpieza" → `422`). No hay escenario de que, en una prestación que no requiere sillón, el nulo explícito sea válido, ni de que `sillon_id` omitido conserve el sillón actual.
- **Fuente**: DD-23a; RN-AG-10; `design.md` §5 (`sillon_id=None` queda `None`).
- **Sugerencia**: GIVEN turno "Consulta" sin sillón, WHEN `{"sillon_id": null}` o `{}`, THEN `200` y sigue sin sillón; y un caso con turno con sillón 1 y `{"inicio": ...}` que conserva el sillón (ya parcial en "Solo un nuevo inicio"). Mitigante: `tasks.md` 4.3 lo cubre a nivel unitario.

### H6 — Solape aislado por sillón no tiene escenario; contigüidad solo por profesional y sillón · MENOR
- **Dónde**: spec.md, requirement "Sin solape al reprogramar".
- **Problema**: hay escenarios para solape solo por profesional, solo por paciente y por los tres a la vez, pero no para solape solo por sillón (profesional y paciente distintos), regla RN-AG-02 independiente. Tampoco hay escenario de que, al reprogramar, un turno sin sillón no participe del chequeo por sillón. Los dos tests de concurrencia ejercitan solo la exclusión por profesional.
- **Fuente**: RN-AG-02; RN-AG-14; RN-AG-09 (tres restricciones en BD); requirement de C-03 "Sin solape por sillón".
- **Sugerencia**: GIVEN otro turno activo en sillón 1 con otro profesional y otro paciente de 15:00 a 15:45, WHEN se reprograma el turno del profesional A (sillón 2) a las 15:15 informando `sillon_id` = sillón 1, THEN `409` indicando solo `sillon`.

### H7 — Orden entre 422 de formato y 409 de turno cancelado no definido para nulos explícitos · MENOR
- **Dónde**: spec.md, requirements "Reprogramación parcial" y "Turno cancelado no reprogramable".
- **Problema**: este último dice que el estado se evalúa antes que las validaciones del turno resultante (escenario con `duracion_min = 42` → `409`). Pero `{"inicio": null}` sobre un turno cancelado lo resuelve Pydantic con `422` antes de entrar al caso de uso (`design.md` §5 y §9). El spec no dice cuál gana, y la redacción de "Turno cancelado no reprogramable" permitiría leer `409`.
- **Fuente**: DD-23c ("estado antes que hora"); `design.md` §5/§6; requirements citados.
- **Sugerencia**: acotar el requirement ("antes que las validaciones de dominio del turno resultante; los errores de formato del body, incluido el nulo explícito, se evalúan antes") y agregar un escenario que fije el resultado.

### H8 — Redacción: escenarios sin GIVEN, WHEN con alternativas, N sin valor · MENOR
- **Dónde**: spec.md. "Inicio sin zona horaria", "Sillón destino inexistente" y "Turno inexistente"/"Identificador con formato inválido" no tienen GIVEN (en los dos primeros hace falta: qué turno se reprograma); "Nulo explícito en un campo obligatorio" junta tres requests en un solo WHEN ("o"); "Turnos distintos movidos a la vez" usa "N" sin valor (el design dice 5). Todos los pasos repiten la palabra ("**GIVEN** dado", "**WHEN** cuando", "**THEN** entonces").
- **Problema**: los casos con "o" ocultan qué campo falló si el test pasa a medias; el N abierto no es verificable tal cual.
- **Fuente**: C5, C7.
- **Sugerencia**: dividir el escenario de nulos en tres (o marcarlo explícitamente como parametrizado), fijar N = 5 y agregar GIVEN a los dos primeros.

### H9 — Referencias no editables desactivadas: consecuencia no escrita en el spec · SUGERENCIA
- **Dónde**: `design.md` §3 ("Consecuencia aceptada de RN-AG-08") vs. spec.md (sin escenario).
- **Problema**: como se revalidan todas las referencias, un turno cuyo paciente o prestación se desactivó después del alta no se puede reprogramar (`422` referencia inválida). La KB no lo dice y no hay escenario; el único escenario relacionado, "Body sin campos editables", fija "cuyas referencias siguen activas", lo que sugiere que el caso contrario existe pero queda sin cubrir.
- **Fuente**: RN-AG-08 ("exactamente la misma validación"), DD-21; `design.md` §3.
- **Sugerencia**: ver Preguntas abiertas (Q2). Si el equipo confirma el comportamiento, agregar el escenario.

### H10 — Tareas sin escenario que las respalde · SUGERENCIA
- **Dónde**: `tasks.md` 6.6 (observadores y validadores inyectables, rollback si un observador falla), 5.1 (`actualizado_en`), 1.1 y grupos 2-3 (refactors).
- **Problema**: no corresponden a ningún escenario del spec. Los refactores y el setup son legítimos; los puntos de extensión (6.6) definen comportamiento observable (qué recibe el observador, rollback ante falla) que el spec no contrata, y la regla dura "no implementar en Apply algo que no esté en el spec aprobado" lo hace discutible.
- **Fuente**: C9; reglas duras del proyecto; `proposal.md` (Non-goals y Impact).
- **Sugerencia**: o un requirement breve de puntos de extensión con un escenario, o dejarlo documentado en el design como detalle interno no contractual.

## Resumen por severidad

| Severidad | Cantidad | Hallazgos |
|-----------|---------:|-----------|
| BLOQUEANTE | 0 | |
| MAYOR | 3 | H1, H2, H3 |
| MENOR | 5 | H4, H5, H6, H7, H8 |
| SUGERENCIA | 2 | H9, H10 |

## Preguntas abiertas

- Q1 (candidata a `10_preguntas_abiertas.md`): al reprogramar, ¿un nuevo inicio igual al instante actual se acepta (RN-AG-12 dice "anterior") o se rechaza? Hoy: se acepta (design §11), sin respaldo explícito en la KB.
- Q2: si el paciente o la prestación de un turno futuro se desactivó, ¿debe poder reprogramarse el turno? Hoy: no (`422`, por revalidar todo según RN-AG-08).
- Q3: un body con nulo explícito en `inicio`/`profesional_id`/`duracion_min` sobre un turno `cancelado`, ¿responde `422` (formato) o `409 turno_ya_cancelado`? Hoy: `422` por orden de capas, no contratado en DD-23.

## Fuera de esta revisión

- No se ejecutó `openspec status`: el change está archivado (no figura en `openspec list`).
- No se revisó el código ni los tests implementados; solo el spec, el design y las tareas. Los mitigantes citados de `tasks.md` son lo que las tareas dicen, no lo que los tests hacen.
- No se verificaron literalmente los cuerpos de DD-15, DD-21 y DD-23 de `09_decisiones_y_supuestos.md` (líneas largas omitidas por la herramienta de lectura); se contrastó con `proposal.md`, `design.md`, el Flujo 3 de `07`, las resoluciones de `10_preguntas_abiertas.md` y el spec principal sincronizado, que los citan de forma consistente.
- Horarios de atención y bloqueos (RN-AG-05/06): correctamente fuera de alcance (C-10, C-11); no se marcan como faltantes.
