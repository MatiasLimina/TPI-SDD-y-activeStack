# Revisión de escenarios — agenda-diaria-semanal (C-13)

- Fecha: 2026-11-09
- Specs revisados: `specs/consulta-agenda/spec.md` (nuevo, 12 requirements), `specs/service-health/spec.md` (MODIFIED)
- Reglas aplicables: RN-AU-01, RN-AU-02, RN-CU-04, RN-AG-03 (DD-03), RN-AG-07 (DD-08), SU-08, DD-24 b, DD-26 g, DD-27 i, DD-30 b/d/k, DD-31 a/c
- Decisiones del usuario (D1-D4, D6-D11) aprobadas como recomendadas; D7 (instantes en `-03:00`) es una desviación deliberada de "UTC" en CHANGES.md C-13 y Flujo 7, a registrar como DD-32: no es hallazgo contra el spec.
- Veredicto: LISTO PARA APPLY (sin BLOQUEANTE ni MAYOR; 4 MENOR y 3 SUGERENCIA)

## Cobertura

| Requirement | Escenarios | Esperado | Error de negocio | Borde | Reglas cubiertas |
|-------------|-----------:|:--------:|:----------------:|:-----:|------------------|
| Consulta por rango de días | 4 | 2 | 2 (422 validación) | 1 (día vacío) | US-008, Flujo 7 |
| Rango local a UTC | 3 | 3 | - | 3 | RN-CU-04, SU-08 |
| Inclusión por superposición | 4 | 1 | - | 4 | DD-03 |
| Rango válido hasta una semana | 3 | 1 | 2 | 1 (7 días) | US-008, D4 |
| Filtro por profesional | 5 | 2 | 1 | 2 | DD-26 g, DD-30 k |
| Filtro por sillón | 4 | 2 | - | 2 | DD-30 d |
| Turnos en cualquier estado y fecha | 2 | 2 | - | 1 | DD-08 |
| Datos de cada turno | 3 | 1 | - | 2 | RN-CU-04, DD-31 a/c |
| Datos de cada bloqueo | 2 | 1 | - | 1 | DD-30 b/k |
| Orden | 2 | 1 | - | 1 | DD-30 k |
| Odontólogo solo su agenda | 5 | 2 | 3 (403) | 2 | RN-AU-02, DD-27 i |
| Autenticación | 3 | 1 | 2 (401) | 1 | RN-AU-01, DD-24 b |
| service-health (MODIFIED) | 1 | - | 1 | - | - |

Reglas del scope sin escenario: ninguna. C1 cumplido (esperado, error de negocio y borde presentes).

## Hallazgos

### H1 — Inclusión por superposición solo probada con bloqueos · MENOR
- **Dónde**: requirement "Inclusión por superposición con el rango"; escenarios (falta turnos)
- **Problema**: el requirement dice "turno o bloqueo", pero los 4 escenarios usan bloqueos; un turno que cruza el borde (23:30-00:30) o contiguo no tiene escenario en el spec (sí lo cubre la tarea 3.1 a nivel repositorio).
- **Fuente**: DD-03; C2/C9 de la skill.
- **Sugerencia**: agregar un escenario de turno que cruza la medianoche local (aparece completo en ambos días) y uno contiguo excluido.

### H2 — Offset en las aserciones de instantes · MENOR
- **Dónde**: escenarios con `inicio 2026-10-08T10:00:00-03:00`
- **Problema**: no dice si se compara el string literal o el instante; una serialización `+00:00` equivalente fallaría o no según el test.
- **Fuente**: C5/C6; D7.
- **Sugerencia**: redactar "instante igual a ... con desfasaje `-03:00`" y fijar en design el formato ISO exacto.

### H3 — Odontólogo con `sillon_id` y bloqueos · MENOR
- **Dónde**: requirement "El odontólogo solo consulta su agenda"
- **Problema**: el escenario del sillón compartido no verifica `bloqueos` (deben ser solo los de A y no filtrarse por sillón, D9).
- **Fuente**: DD-30 d; D9.
- **Sugerencia**: agregar un bloqueo de A y de B al GIVEN y exigir solo el de A.

### H4 — MODIFIED de service-health cambia una ruta por otra · MENOR
- **Dónde**: `specs/service-health/spec.md`
- **Problema**: el escenario archivado `GET /turnos` -> 404 ya era falso desde C-03 (hoy da 405); verificar que el header del requirement coincide exacto con el archivado (coincide: "Sin endpoints de negocio en la base").
- **Fuente**: `openspec/specs/service-health/spec.md`.
- **Sugerencia**: sin cambio al spec; confirmar con `openspec validate --strict`.

### H5 — Tarea 5.7 (OpenAPI) sin escenario · SUGERENCIA
- **Problema**: tarea de verificación sin escenario; es setup legítimo (C9).

### H6 — `design.md` y `tasks.md` aún dicen "Pendiente" · SUGERENCIA
- **Problema**: la tabla de Decisions conserva D1-D4, D6-D9, D11 como Pendiente y el encabezado de tasks pide aprobación; la tarea 1.2 exige registrar fecha y opción aprobada antes del Apply.
- **Sugerencia**: `/opsx:update` para marcarlas aprobadas (2026-11-09) y quitar el aviso.

### H7 — Odontólogo con `profesional_id` mal formado · SUGERENCIA
- **Problema**: FastAPI valida el query antes del handler, por lo que un odontólogo con `profesional_id=no-es-un-id` recibe `422`, no `403`; el spec ya lo dice implícitamente ("mal formado MUST dar 422") pero el precedente "403 antes que 422" solo se prueba con rango invertido.

## Preguntas abiertas
Ninguna nueva. El usuario odontólogo siempre tiene profesional (alta por CLI lo exige), por lo que no hay caso de odontólogo sin vínculo.

## Fuera de esta revisión
Código y tests aún inexistentes (no se contrastó con `backend/`); la redacción de DD-32 (tarea 8.1).
