# Revisión de escenarios — horarios-atencion (C-10)

- Fecha: 2026-11-02
- Specs revisados: `specs/horarios-atencion/spec.md`, `specs/agenda-turnos/spec.md` (ADDED + MODIFIED), `specs/datos-semilla/spec.md` (MODIFIED); contrastados con `proposal.md`, `design.md`, `tasks.md`, `CHANGES.md` §C-10, la KB (05, 04, 03, 06, 09) y los specs archivados `agenda-turnos` y `datos-semilla`.
- Reglas aplicables: RN-HB-01, RN-AG-05, RN-AG-08, RN-AG-03, RN-CU-04, RN-AU-03, DD-15, DD-21 (contrato 422/409/404), DD-26 (criterio para recursos desactivados), matriz de `03_actores_y_roles.md` ("R (propios)"), SU-08. Las decisiones D1, D3, D5-D11 de `design.md` están confirmadas por el usuario con DD-27 pendiente (tarea 9.1); se citan como "design D-n (confirmed, DD-27 pending)".
- Veredicto: LISTO PARA APPLY (0 BLOQUEANTE, 0 MAYOR, 7 MENOR, 2 SUGERENCIA)

## Cobertura

| Requirement | Escenarios | Esperado | Error de negocio | Borde | Reglas cubiertas |
|-------------|-----------:|:--------:|:----------------:|:-----:|------------------|
| Alta de una franja de atención | 4 | 3 | 1 (404) | 0 | RN-HB-01, D9, D11 |
| Validación de la franja | 6 | 0 | 6 (422) | 4 | D3, D4 |
| Franjas superpuestas | 4 | 1 | 2 (409) | 2 | D5 |
| Garantía en la base de datos | 3 | 0 | 3 | 2 | D3-D5 |
| Consulta de franjas | 4 | 3 | 1 (404/422) | 0 | D9, D11 |
| Edición parcial | 6 | 2 | 4 | 1 | D5 |
| Borrado | 2 | 1 | 1 | 0 | D9 |
| Cambios de horario no alteran turnos | 2 | 2 | 0 | 0 | D8 |
| Escritura reservada a recepcionista | 3 | 0 | 3 (401/403) | 0 | RN-HB-01, RN-AU-03 |
| Lectura según rol | 3 | 1 | 2 (403/401) | 0 | matriz 03, D10 |
| Turno dentro del horario (agenda, ADDED) | 15 | 4 | 8 | 7 | RN-AG-05, RN-CU-04, D6, D7, D13 |
| Misma validación al reprogramar (MODIFIED) | 11 (7 previos + 4 nuevos) | 0 | 11 | 1 | RN-AG-08, RN-AG-05 |
| Contenido del seed (MODIFIED) | 8 (6 previos + 2 nuevos) | 5 | 0 | 0 | D15, CHANGES.md C-10 |

Reglas del scope sin escenario: ninguna. RN-AG-06 (bloqueos) queda fuera por pertenecer a C-11.

Controles: C1 cumple (hay esperado, error de negocio y borde). C3 sin invasión de C-11, C-12, C-07 ni C-13. C4 coherente con "Excepciones globales" (horario -> 422) y DD-21 (path -> 404, 409 por conflicto). C8 sin datos reales; la concurrencia contra PostgreSQL está en el spec (altas simultáneas) y en la tarea 5.4. Los MODIFIED conservan todos los escenarios de los specs archivados (7 de reprogramar, 6 del seed). Los 15 escenarios del ADDED coinciden con la tarea 6.3 y las fechas son coherentes (2026-10-08 es jueves, `dia_semana = 3`; 15:30Z = 12:30 local; 01:00Z del 10-09 = jueves 22:00 local).

## Hallazgos

### H1 — Edición de `dia_semana` sin escenario · MENOR
- **Dónde**: `horarios-atencion/spec.md`, requirement "Edición parcial de una franja" (falta)
- **Problema**: el requirement dice que `PATCH` puede modificar `dia_semana`, pero ningún escenario lo ejercita. Mover una franja a otro día con la superposición evaluada en el día nuevo es un camino distinto.
- **Fuente**: design D5 (confirmed, DD-27 pending); US-002.
- **Sugerencia**: GIVEN A con lunes 09:00-13:00 y martes 10:00-12:00; WHEN `PATCH` de la del lunes con `{"dia_semana": 1}`; THEN `409 franja_superpuesta` y ambas siguen igual. Y el caso positivo hacia un martes libre -> `200`.

### H2 — Orden de evaluación con id mal formado no cubierto en todos los casos · MENOR
- **Dónde**: requirements "Lectura de franjas según el rol" y "Escritura reservada a la recepcionista"
- **Problema**: se fija que `GET` sin token con id mal formado da `401`, y que el odontólogo recibe `403` antes que `404`. No se dice qué pasa con un odontólogo y `GET /profesionales/no-es-un-id/horarios` (el chequeo de `profesional_ajeno` necesita el id ya parseado, probablemente `422`). Tampoco hay escenarios de `PATCH` y `DELETE` sin token (solo `POST`).
- **Fuente**: design §2 (orden de evaluación); C4.
- **Sugerencia**: decidir y escribir el resultado (ver Preguntas abiertas 1). Agregar `PATCH`/`DELETE` sin token -> `401` a un escenario existente.

### H3 — Faltan 404 de `PATCH`/`DELETE` por profesional inexistente y de `PATCH` por franja inexistente · MENOR
- **Dónde**: requirements "Edición parcial" y "Borrado de una franja"
- **Problema**: el texto promete `404` con `recurso = "profesional"` en `DELETE` y `404` ante franja inexistente en `PATCH`, pero los escenarios solo cubren `DELETE` de franja inexistente y `PATCH` de franja ajena. (La tarea 5.7 sí menciona `DELETE` con profesional inexistente.)
- **Fuente**: design D9, DD-21 (404 para recursos del path).
- **Sugerencia**: sumar `DELETE` con profesional inexistente (`recurso = "profesional"`) y `PATCH` con UUID de franja desconocido (`recurso = "horario"`).

### H4 — Reloj no fijado en el GIVEN de casi todos los escenarios de turno · MENOR
- **Dónde**: `agenda-turnos/spec.md`, escenarios del ADDED (salvo el primero) y los nuevos del MODIFIED
- **Problema**: usan fechas absolutas (2026-10-08) pero solo el primero fija el reloj; sin reloj el resultado dependería de `inicio_en_pasado`. El encabezado de `tasks.md` y la tarea 6.3 ya fijan el reloj en 2026-10-07 09:00, así que el riesgo es de redacción.
- **Fuente**: C6; tasks.md encabezado y 6.3.
- **Sugerencia**: una cláusula única en el requirement ("los escenarios asumen el reloj en 2026-10-07 09:00 hora local").

### H5 — Orden de `fuera_de_horario` frente a las demás validaciones 422 probado solo con `duracion_invalida` · MENOR
- **Dónde**: `agenda-turnos/spec.md`, escenario "Validaciones previas antes que el horario"
- **Problema**: el diseño ubica el validador después de duración, inicio futuro y coherencia de sillón, pero el spec solo prueba el primero. Un turno en el pasado y fuera de horario, o con `sillon_requerido`, podría devolver el código equivocado sin romper ningún test.
- **Fuente**: design §Contexto (orden fijo de `validar_solicitud_turno`), D14; RN-AG-08.
- **Sugerencia**: ampliar el escenario con `inicio_en_pasado` o `sillon_requerido`, o aclarar que basta una muestra.

### H6 — Falta un escenario positivo de reprogramación dentro del horario · MENOR
- **Dónde**: `agenda-turnos/spec.md`, MODIFIED "Misma validación que el alta al reprogramar"
- **Problema**: los 4 escenarios nuevos son todos rechazos; ninguno muestra una reprogramación válida que cabe justo (terminando al cierre de la franja).
- **Fuente**: RN-AG-05, RN-AG-08; C6 (borde `[)` también al reprogramar).
- **Sugerencia**: GIVEN franja jueves 09-13 y turno programado de A de 45 min; WHEN se reprograma a las 12:15 del mismo jueves; THEN `200` y `fin` 13:00.

### H7 — Requirements sin cita de regla · MENOR
- **Dónde**: `horarios-atencion/spec.md`, requirements "Validación de la franja", "Franjas superpuestas", "Garantía en la base", "Consulta", "Edición" y "Borrado". `agenda-turnos` sí cita RN-AG-05 y RN-CU-04.
- **Problema**: solo "Alta" y los de rol citan regla; D3/D5/D10 aún no tienen DD.
- **Fuente**: C2.
- **Sugerencia**: citar "RN-HB-01, DD-27" cuando DD-27 exista (tarea 9.1), sin inventar numeración antes.

### H8 — Escenarios archivados que crean turnos asumen implícitamente una franja · SUGERENCIA
- **Dónde**: specs archivados `agenda-turnos`, `auditoria-turnos`, `autenticacion` (GIVEN sin horario)
- **Problema**: con D7 (confirmed, DD-27 pending) todo `POST /turnos` sin franja da `422`. El delta no lo declara y se resuelve solo en tests (D16); tras archivar, los specs principales parecerían contradictorios.
- **Fuente**: design D7, D16; C2.
- **Sugerencia**: nota en el ADDED requirement: los escenarios de turnos de otros requisitos asumen que el profesional tiene una franja que cubre el turno. No es BLOQUEANTE: el comportamiento nuevo es el que pide RN-AG-05.

### H9 — La tarea 8.1 (OpenAPI) no corresponde a un escenario · SUGERENCIA
- **Dónde**: `tasks.md` 8.1
- **Problema**: C9, tarea sin escenario; es documentación legítima (D1, D6).
- **Sugerencia**: dejarla como está.

## Preguntas abiertas
1. ¿Odontólogo + `GET /profesionales/<id mal formado>/horarios` responde `422` o `403 profesional_ajeno`? (H2; candidata a la DD-27).
2. Seed ante franjas editadas a mano: no se especifica si el seed las repone o las respeta. Los requirements "Seed idempotente" y "Datos preexistentes no se pisan" lo cubren por analogía; confirmar en la tarea 7.1.

## Fuera de esta revisión
- No se verificó que Pydantic parsee `"09:00-03:00"` como `time` con `tzinfo` ni que `date + time` sea indexable en la exclusión GiST (lo cubren la tarea 3.1 y Risks).
- Bloqueos (RN-AG-06), recordatorios, auditoría de horarios y frontend: fuera del scope de C-10.

## Seguimiento (`/opsx:update`, 2026-11-02)

Hallazgos atendidos con aprobación del usuario:
- **H1**: escenarios "Mover una franja a un día donde se superpone" (`409`) y "Mover una franja a un día libre" (`200`); el requirement aclara que la superposición se evalúa en el día nuevo.
- **H2**: "Sin token en la escritura" cubre `POST`, `PATCH` y `DELETE` (`401` cada uno).
- **H3**: escenarios "Editar una franja o un profesional inexistente" (`404 horario` / `404 profesional`) y "Borrar sobre un profesional inexistente" (`404 profesional`); tareas 5.6 y 5.7 alineadas.
- **H4**: el requirement ADDED de `agenda-turnos` fija el reloj de los escenarios en 2026-10-07 09:00 local.
- **H6**: escenario "Reprogramación que termina justo al cierre de la franja" (`200`, `fin` 13:00); tarea 6.4.
- **H7**: los requirements de `horarios-atencion` citan "RN-HB-01, DD-27" (o "RN-AG-08, DD-27").
- **H8**: el requirement ADDED de `agenda-turnos` declara que los escenarios de turnos de otros requisitos asumen una franja que cubre el turno.
- **Pregunta abierta 1** → design D17: odontólogo con id mal formado en `GET …/horarios` → `422`; escenario "Odontólogo con identificador mal formado"; tarea 5.8.
- **Pregunta abierta 2** → design D18: el seed no pisa franjas editadas a mano y solo inserta las faltantes (omitiendo sin error la que chocaría con otra); escenarios "Franjas editadas a mano no se pisan" y "Franja sembrada faltante que choca con una cargada a mano"; tarea 7.1.
- D17 y D18 se suman a la lista de DD-27 (tarea 9.1).

Sin cambios: **H5** (una muestra del orden alcanza) y **H9** (8.1 queda como documentación). `openspec validate horarios-atencion --strict`: válido.
