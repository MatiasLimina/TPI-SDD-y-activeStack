# Revisión de escenarios — cancelar-turno (C-04)

- Fecha: 2026-10-16
- Specs revisados: `.agents/skills/revisar-escenarios/evals/files/c04-sin-borde/spec.md` (tratado como delta spec de `agenda-turnos`; no se leyó el change archivado)
- Reglas aplicables: RN-AG-07, RN-AG-13, RN-CU-01 (no se borra), DD-14, DD-22, DD-21 (404 para recursos del path), DD-06 / RN-CU-04 (zona horaria), DD-08 (conservar cancelados), DD-18 / RN-AG-09 (concurrencia, solo en lo que toca solapes)
- Veredicto: CORREGIR ANTES DE APPLY

## Cobertura

| Requirement | Escenarios | Esperado | Error de negocio | Borde | Reglas cubiertas |
|-------------|-----------:|:--------:|:----------------:|:-----:|------------------|
| Cancelación de un turno | 2 | 1 (futuro -> 200) | 0 (el 404 es recurso inexistente, no regla RN/DD) | 0 | RN-AG-07 solo en el estado final; DD-21 (404) |

Reglas del scope sin escenario (según `CHANGES.md` C-04):
- RN-AG-13 / DD-14: cancelar turno iniciado o pasado -> 409; cancelar hasta el inicio.
- DD-22: cancelar turno ya cancelado -> 409 sin modificar el turno.
- RN-AG-07: el horario se puede reservar de inmediato; el cancelado no cuenta para solapes.
- Motivo opcional y `motivo_cancelacion` (scope C-04, US-006).
- "No se borra" (DD-08, RN-AG-07).

Fuera de alcance correctamente ausentes (no se piden): auditoría (C-07), cancelar recordatorio (C-12), autenticación (C-06).

## Hallazgos

### H1 — Falta el escenario de error de negocio (turno iniciado o pasado) · BLOQUEANTE
- **Dónde**: spec.md, requirement "Cancelación de un turno", escenario "falta"
- **Problema**: el único rechazo del spec es el 404 (recurso inexistente). Ninguna regla RN/DD rechaza la operación, así que falta el tipo mínimo "error de negocio" (C1). Además RN-AG-13 queda sin ejercitar.
- **Fuente**: CHANGES.md C-04 ("Cancelar un turno ya iniciado o pasado -> 409"; test "turno iniciado -> 409"); RN-AG-13; DD-14; US-006 criterio 4; controles C1
- **Sugerencia**:
  - GIVEN un turno programado para 2026-10-12 10:00-03:00 y el reloj en 2026-10-12 10:30-03:00 hora local
  - WHEN `POST /turnos/{id}/cancelar`
  - THEN `409` y el turno sigue `programado`, sin `motivo_cancelacion`

### H2 — Falta el escenario de borde de la regla temporal · BLOQUEANTE
- **Dónde**: spec.md, requirement "Cancelación de un turno", escenario "falta"
- **Problema**: el escenario feliz cancela con un día de anticipación, lejos del límite. No hay borde (C1). La regla "se cancela hasta el inicio" necesita el límite exacto con reloj fijo (C6).
- **Fuente**: RN-AG-13 ("hasta su inicio"); DD-14 (sin política de cancelación tardía: cancelar justo antes del inicio es válido); controles C1, C6
- **Sugerencia**:
  - Borde válido: GIVEN reloj 2026-10-12 09:59-03:00 y turno de 10:00-03:00; WHEN cancelar; THEN `200` y `estado = cancelado`.
  - Borde inválido: GIVEN reloj exactamente 2026-10-12 10:00-03:00 y el mismo turno; WHEN cancelar; THEN `409` y el turno no cambia.
  - Nota: que "inicio == ahora" sea rechazo es una interpretación de "ya iniciado". La KB no lo fija textualmente; ver Preguntas abiertas.

### H3 — Turno ya cancelado sin escenario (DD-22) · MAYOR
- **Dónde**: spec.md, falta
- **Problema**: la regla del scope "cancelar un turno ya cancelado -> 409, sin modificar el turno" no tiene escenario. DD-22 también fija que el estado se evalúa antes que la hora y que el motivo original se conserva.
- **Fuente**: DD-22; CHANGES.md C-04; 07_flujos_principales.md Flujo 4 (Errores)
- **Sugerencia**:
  - GIVEN un turno futuro ya cancelado con motivo "Viaje imprevisto"; WHEN se cancela de nuevo con motivo "Otro motivo"; THEN `409` y `motivo_cancelacion` sigue siendo "Viaje imprevisto".
  - GIVEN un turno cancelado cuyo inicio ya pasó; WHEN se cancela; THEN `409` indicando turno ya cancelado (el estado gana a la hora).

### H4 — Liberación inmediata del horario sin escenario (RN-AG-07) · MAYOR
- **Dónde**: spec.md, requirement "Cancelación de un turno"
- **Problema**: el requirement dice que el turno "deja de contar para los solapamientos", pero ningún escenario lo verifica. Es el propósito de US-006 y el test central del scope.
- **Fuente**: RN-AG-07; CHANGES.md C-04 (tests: "cancelar libera el horario y permite crear otro turno en el mismo intervalo; el cancelado no cuenta para solapes"); US-006 criterio 2
- **Sugerencia**:
  - GIVEN un turno del profesional A, sillón 1, paciente P de 10:00 a 10:45; WHEN se cancela y luego se crea otro con los mismos recursos y horario; THEN cancelar da `200`, crear da `201` y en la base hay una fila `cancelado` y una `programado`.
  - Contraste: sin cancelar, crear el segundo da `409`.

### H5 — Motivo opcional y `motivo_cancelacion` sin escenarios · MAYOR
- **Dónde**: spec.md, requirement "Cancelación de un turno"; el requirement ni menciona el motivo
- **Problema**: el scope incluye "motivo opcional" y `motivo_cancelacion`. No hay escenario con motivo ni sin body, y el requirement no dice cómo se persiste ni qué devuelve la respuesta.
- **Fuente**: CHANGES.md C-04; Flujo 4 paso 1 ("con motivo opcional"); controles C2
- **Sugerencia**:
  - GIVEN un turno futuro; WHEN se cancela con `{"motivo": "El paciente avisó que está con fiebre"}`; THEN `200` y `motivo_cancelacion` con ese texto, también en la base.
  - GIVEN un turno futuro; WHEN se cancela sin body; THEN `200` y `motivo_cancelacion` nulo.
  - Normalización de espacios y largo máximo: ver Preguntas abiertas. No darlos por reglas.

### H6 — El escenario feliz no prueba "no se borra" · MENOR
- **Dónde**: spec.md, escenario "Cancelar un turno futuro"
- **Problema**: el THEN verifica `200` y `estado`, pero no que la fila siga existiendo con sus datos originales (inicio, fin, profesional, sillón, paciente). La regla es "no se borra".
- **Fuente**: DD-08; RN-AG-07; CHANGES.md C-04 ("no se borra"); controles C5
- **Sugerencia**: agregar al THEN "y en la base la fila sigue existiendo con `estado = 'cancelado'` y los mismos inicio, fin, profesional, sillón, paciente y prestación". Indicar también `inicio`/`fin` en `-03:00` en la respuesta (DD-06).

### H7 — Requirement sin citas de reglas y 404 con GIVEN vacío · MENOR
- **Dónde**: spec.md, requirement "Cancelación de un turno" y escenario "Turno inexistente"
- **Problema**:
  - El requirement cita solo RN-AG-07; omite RN-AG-13, DD-14 y DD-22, que definen el comportamiento.
  - Solo describe el caso del turno `programado` y no dice qué pasa con los demás estados.
  - El escenario 404 no tiene GIVEN y no dice que no se persiste nada.
  - Los prefijos "dado / cuando / entonces" repiten a GIVEN/WHEN/THEN (redacción).
- **Fuente**: controles C2 (citas), C5, C7; DD-21 (404 para recursos del path)
- **Sugerencia**: citar las reglas, enunciar el requirement para todos los estados, y en el 404 agregar GIVEN "no existe ningún turno con ese id" y THEN "`404` y ningún turno cambia".

### H8 — Concurrencia de cancelaciones · SUGERENCIA
- **Dónde**: spec.md, falta
- **Problema**: C-04 modifica el estado que habilita la reserva del horario (índice parcial sobre `estado <> 'cancelado'`). No hay escenario ni tarea de concurrencia. El scope de C-04 no pide tests de concurrencia, y DD-18/RN-AG-09 los exigen para los solapes. El equipo debe decidir si la doble cancelación simultánea o la carrera "cancelar + crear en el mismo hueco" entra en C-04.
- **Fuente**: DD-18; RN-AG-09; CHANGES.md C-04 (scope sin test de concurrencia)
- **Sugerencia**: si entra, N cancelaciones simultáneas del mismo turno -> exactamente una `200` y el resto `409` (DD-22), contra PostgreSQL real.

### H9 — Identificador mal formado · SUGERENCIA
- **Dónde**: spec.md, escenario "Turno inexistente"
- **Problema**: solo se cubre un id numérico inexistente. La KB no dice qué responde la API ante un id con formato inválido (`/turnos/abc/cancelar`).
- **Fuente**: DD-21 (404 solo para recursos del path); sin decisión sobre formato inválido
- **Sugerencia**: pregunta abierta, no escenario.

## Preguntas abiertas
1. En el instante exacto del inicio (reloj == `inicio`), ¿se puede cancelar? RN-AG-13 dice "hasta su inicio" y "ya iniciado o pasado -> 409". Conviene que DD-14/RN-AG-13 fijen `ahora < inicio` o `ahora <= inicio` para que el borde sea testeable.
2. Motivo: ¿se recortan los espacios, se normaliza el vacío a nulo y hay largo máximo? La KB solo dice "motivo opcional".
3. Id con formato inválido en el path: ¿`404` o `422`?
4. ¿Entran los tests de concurrencia de cancelación en C-04 o en otro change?

## Fuera de esta revisión
- `tasks.md`, `proposal.md` y `design.md` del change: no se proporcionaron, así que no se aplicó C9.
- No se leyó el change archivado, por indicación. Las "Excepciones globales" de `openspec/specs/agenda-turnos/spec.md` se usaron solo como contrato de códigos HTTP (409 / 422 / 404).
- La existencia de las columnas `motivo_cancelacion` y `estado` en el modelo (C-02) no se verificó contra `04_modelo_de_datos.md`.
