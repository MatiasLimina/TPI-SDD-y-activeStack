# Revisión de escenarios — auditoria-turnos (C-07)

- Fecha: 2026-10-30
- Specs revisados: `openspec/changes/auditoria-turnos/specs/auditoria-turnos/spec.md` (más `proposal.md`, `design.md`, `tasks.md` y los specs archivados `agenda-turnos` y `autenticacion`)
- Reglas aplicables: RN-CU-01, RN-CU-02, RN-CU-04, RN-AU-01 (matriz de `03`), excepción global "operaciones atómicas junto con su registro de auditoría", DD-06, DD-08, DD-16, DD-21, DD-22, DD-23, DD-24, scope de C-07 en `CHANGES.md`. Decisiones D1, D2, D3, D5, D6 y D8 aprobadas por el usuario (se registran como DD-25 en la tarea 9.1; no se marcan como hallazgo).
- Veredicto: LISTO PARA APPLY (0 BLOQUEANTE, 0 MAYOR; los MENOR se corrigen si se toca el spec)

## Cobertura

| Requirement | Escenarios | Esperado | Error de negocio | Borde | Reglas cubiertas |
|-------------|-----------:|:--------:|:----------------:|:-----:|------------------|
| Registro al crear | 2 | 1 | 0 | 1 (sillón nulo, duración ajustada) | RN-CU-01, US-011 |
| Registro al reprogramar | 3 | 2 | 0 | 1 (encadenamiento previos = nuevos) | RN-CU-01 |
| Registro al cancelar | 2 | 1 | 0 | 1 (sin motivo) | RN-CU-01, DD-22 |
| Instantánea | 2 | 1 | 0 | 1 (UTC) | RN-CU-01, RN-CU-04 |
| Autor e instante | 2 | 2 | 0 | 0 | RN-CU-01 (usuario y momento) |
| Rechazada no genera registro | 4 | 0 | 4 (409, 422, 409 DD-22, 403) | 0 | excepción global, DD-21/22/24 |
| Atomicidad | 3 | 0 | 3 (rollback conjunto) | 0 | excepción global de atomicidad |
| Append-only | 5 | 1 (insert aceptado) | 4 | 0 | RN-CU-01 |
| Integridad en la base | 7 | 0 | 7 | 0 | DD-08, DD-16 |
| Consulta del historial | 4 | 4 | 0 | 0 | US-011, RN-CU-04 |
| Sin registros / inexistente / id inválido | 4 | 2 | 2 (404, 422) | 0 | DD-21 |
| Consulta reservada a la recepcionista | 4 | 0 | 4 (403, 401, orden 403>404, 401>422) | 0 | RN-CU-01, DD-24, matriz de 03 |
| **Total** | **42** | | | | |

Reglas del scope sin escenario: ninguna. C1 cumplido (esperado, error de negocio y borde presentes). C3: nada pertenece a otro change (C-10, C-11, C-12, C-08, C-09, C-13 no aparecen). C4: 401/403/404/409/422 coherentes con DD-21/22/24 y con `agenda-turnos` y `autenticacion` archivados. Sin contradicciones con specs archivados. C8: datos ficticios, sin secretos; sin solapamientos nuevos, así que la concurrencia no es exigible (design lo justifica).

## Hallazgos

### H1 — Rechazos 401 y 404 de las escrituras sin escenario · MENOR
- **Dónde**: spec, requirement "Una operación rechazada no genera registro", escenarios (faltan)
- **Problema**: el requirement enumera `401`, `403`, `404`, `409`, `422`, pero los escenarios solo ejercitan 409, 422, 409 `turno_ya_cancelado` y 403. No hay escenario para `401` (sin token en una escritura) ni `404` (cancelar o reprogramar un turno inexistente). La tarea 7.2 tampoco los lista.
- **Fuente**: excepción global de atomicidad (05 §Excepciones globales), DD-21 y DD-24.
- **Sugerencia**: agregar un escenario "Escritura sin token o sobre turno inexistente no auditada" (`POST /turnos/{id}/cancelar` sin token -> `401`; con UUID inexistente -> `404`; el total de registros no cambia), o acotar la lista del requirement a lo que se prueba.

### H2 — Relojes no fijados en varios GIVEN · MENOR
- **Dónde**: spec, escenarios "Alta con duración ajustada y sin sillón", "Cada operación registra a quien la hizo", "Autor informado en el body ignorado", "Cambio de profesional y sillón auditado", "Dos reprogramaciones generan dos registros", "Cancelación sin motivo auditada"
- **Problema**: dependen de que el inicio sea futuro (RN-AG-12, RN-AG-13) pero el GIVEN no fija el reloj. Como `tasks.md` (preámbulo y 6.x/7.1) fija el reloj inyectado, el riesgo es solo de redacción.
- **Fuente**: control C6.
- **Sugerencia**: agregar "y que el reloj marca 2026-10-07 09:00 hora local" a esos GIVEN.

### H3 — "La operación falla" sin resultado observable concreto · MENOR
- **Dónde**: spec, requirement "Atomicidad del cambio con su registro", los tres escenarios
- **Problema**: el THEN dice "la operación falla" sin precisar qué se observa (excepción de integridad en el caso de uso; qué respondería la API). El GIVEN usa un autor inexistente, algo que por API no puede ocurrir (el usuario se relee de la base). El test es ejecutable a nivel de caso de uso (tarea 6.4), pero el spec no lo dice.
- **Fuente**: control C5, design §5.
- **Sugerencia**: aclarar "a nivel de caso de uso, se lanza un error de integridad de la base" y que no se define respuesta HTTP para ese caso.

### H4 — `id` del registro ausente del contrato de respuesta · MENOR
- **Dónde**: spec, requirement "Consulta del historial de auditoría de un turno"
- **Problema**: el spec lista `accion`, `usuario_id`, `ocurrido_en`, `valores_previos` y `valores_nuevos`; design §6 y la tarea 8.2 devuelven además `id` (D3). Incoherencia menor entre artefactos.
- **Fuente**: design §6 (D3 aprobada).
- **Sugerencia**: agregar `id` a la lista del requirement o quitarlo del schema.

### H5 — Escenarios de lectura de la base sin tarea explícita · MENOR
- **Dónde**: scenarios "Campos de la instantánea" e "Instantes en UTC"
- **Problema**: leen el JSON persistido (no el de la API). La tarea 2.1 cubre la función pura, pero ninguna tarea 6.x dice que se lee `valores_nuevos` directo de la base y se comparan las claves exactas y el offset `+00:00`. Además el GIVEN de "Campos de la instantánea" ("cualquier registro") no es concreto.
- **Fuente**: control C9, C5.
- **Sugerencia**: sumar a 6.1 la aserción sobre la fila persistida (claves exactas, `+00:00`) y acotar el GIVEN a un registro `crear` y uno `cancelar` concretos.

## Sugerencias

- S1: tarea 9.1 registra DD-25 y la corrección de `02` (`GET /auditoria/turnos` -> `GET /turnos/{id}/auditoria`) y del backlog: correcto, mantenerlo. Agregar también que `04_modelo_de_datos.md` §TurnoAuditoria queda alineada (ya está en 9.1).
- S2: sin escenario para `POST` sobre `/turnos/{id}/auditoria` (el escenario 405 solo prueba PUT, PATCH y DELETE); agregarlo si se quiere cerrar el borde.
- S3: la tarea 8.2 cubre el borde "dos registros con el mismo `ocurrido_en` salen en orden de inserción"; el spec lo exige solo implícitamente ("en el orden en que ocurrieron"). Considerar una frase explícita en el requirement.

## Preguntas abiertas

- Una reprogramación `PATCH` que no cambia ningún valor (mismos `inicio`, profesional, sillón y duración, DD-23a) es "exitosa": hoy el spec manda un registro con previos = nuevos. La KB no dice si debe auditarse. Opciones: (a) registrar igual (consistente con el spec actual); (b) no registrar y responder sin cambios. Decisión del equipo, candidata a `10_preguntas_abiertas.md` o a DD-25.

## Fuera de esta revisión

- No se ejecutó código ni la migración; no se verificó que los nombres de constraints del design coincidan con la convención de `base.py` ni que `compare_metadata` no reporte diferencias por `Identity`.
- Las decisiones D1, D2, D3, D5, D6 y D8 se tomaron como aprobadas por el usuario.

---

## Revisión 2 — 2026-10-30

- Contexto: segunda pasada tras `/opsx:update` que atendió H1-H5, S2 y S3 de la Revisión 1 y sumó D10 (aprobada por el usuario: una reprogramación `PATCH` sin cambio efectivo igual genera registro con previos = nuevos).
- Specs revisados: `specs/auditoria-turnos/spec.md`, `design.md`, `tasks.md`, `proposal.md`.
- Reglas aplicables: las de la Revisión 1, más DD-23a (reprogramación sin cambio efectivo). D1, D2, D3, D5, D6, D8 y D10 aprobadas por el usuario (DD-25 en la tarea 9.1); no se marcan por ausencia en la KB.
- Veredicto: **LISTO PARA APPLY** (0 BLOQUEANTE, 0 MAYOR, 2 MENOR, 0 SUGERENCIA nuevas)

### Cobertura actualizada

| Requirement | Escenarios | Cambio vs. Revisión 1 |
|-------------|-----------:|-----------------------|
| Registro al crear | 2 | igual |
| Registro al reprogramar | 4 | +1 ("Reprogramación sin cambio efectivo auditada", D10) |
| Registro al cancelar | 2 | igual |
| Instantánea | 2 | igual (GIVEN concretado) |
| Autor e instante | 2 | igual |
| Rechazada no genera registro | 6 | +2 (401 y 404 nuevos; el resto ya estaba) |
| Atomicidad | 3 | igual (THEN concreto) |
| Append-only | 5 | igual (el 405 ahora incluye POST) |
| Integridad en la base | 7 | igual |
| Consulta del historial | 4 | igual (`id` en el contrato) |
| Sin registros / inexistente / id inválido | 4 | igual |
| Consulta reservada a la recepcionista | 4 | igual |
| **Total** | **45** | +3 |

Reglas del scope sin escenario: ninguna. Tipos mínimos (esperado, error de negocio, borde) presentes. Nada de otros changes (C-08..C-13). D10 es coherente entre spec (requirement + escenario), design (D10, Open Questions), tasks (preámbulo, 6.2, 9.1) y con el código actual: `ReprogramarTurno` invoca a los observadores incondicionalmente, así que el no-op ya genera registro sin tocar la lógica de validación.

### Estado de los hallazgos de la Revisión 1

| Id | Estado | Verificación |
|----|--------|--------------|
| H1 (401/404 en escrituras) | RESUELTO | Escenarios "Escritura sin token no auditada" y "Escritura sobre turno inexistente no auditada"; tarea 7.2 los lista |
| H2 (relojes no fijados) | RESUELTO en lo señalado; resto en M1 | Los GIVEN citados ahora fijan el reloj |
| H3 ("la operación falla") | RESUELTO | Requirement y THEN dicen "error de integridad de la base" a nivel de caso de uso, sin respuesta HTTP; tareas 6.4 y 6.5 alineadas |
| H4 (`id` en la respuesta) | RESUELTO | `id` figura en el requirement de consulta y en 8.2 |
| H5 (lectura directa de la base) | RESUELTO | Tarea 6.1 lee la fila persistida; GIVEN concreto (un `crear` y un `cancelar`) |
| S2 (POST sobre la ruta) | RESUELTO | El escenario de 405 incluye POST |
| S3 (orden por mismo `ocurrido_en`) | RESUELTO | Frase explícita en el requirement; cubierto en 8.2 |
| Pregunta abierta (PATCH sin cambio) | RESUELTA | D10 + escenario + tarea 6.2 + 9.1 |

## Hallazgos nuevos

### M1 — Alta en conflicto y escenarios de instantánea sin reloj fijado · MENOR
- **Dónde**: spec, escenarios "Alta en conflicto no auditada", "Campos de la instantánea", "Instantes en UTC", "Instantes presentados en hora local"
- **Problema**: crean turnos (inicio en 2026-10-08) sin fijar el reloj en el GIVEN; dependen de RN-AG-12/13. El riesgo es solo de redacción: `tasks.md` fija el reloj inyectado.
- **Fuente**: control C6; RN-AG-12, RN-AG-13.
- **Sugerencia**: agregar "y que el reloj marca 2026-10-07 09:00 hora local" a esos GIVEN.

### M2 — Frase suelta en la tarea 6.5 · MENOR
- **Dónde**: `tasks.md` 6.5, última oración ("en 6.4 la falla se observa como error de integridad...")
- **Problema**: describe a 6.4 dentro de 6.5; ya está dicho en 6.4 y en el spec. Redacción confusa, sin efecto en el resultado.
- **Fuente**: coherencia entre artefactos.
- **Sugerencia**: borrar la oración de 6.5.

## Preguntas abiertas

Ninguna nueva.

## Fuera de esta revisión

- No se ejecutó código ni la migración (igual que en la Revisión 1).
