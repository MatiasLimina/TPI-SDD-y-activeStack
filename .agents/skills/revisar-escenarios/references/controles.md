# Controles de revisión (C1 a C9)

Aplicalos en orden. Cada control dice qué buscar, por qué importa en este proyecto y qué severidad
corresponde por defecto (se puede subir o bajar con justificación).

## C1 — Mínimo de tres tipos de escenario
Cada change MUST tener, en el conjunto de sus specs, al menos un escenario **esperado**, uno de
**error de negocio** (una regla RN/DD rechaza la operación: 409, 422, 403…) y uno de **borde** (el límite
exacto de una regla: contiguo `[)`, 480 min, token que vence justo ahora).
- Un 422 por JSON mal formado es error de validación, no de negocio: no cuenta como tal.
- Severidad si falta alguno: `BLOQUEANTE`.

## C2 — Trazabilidad con la KB
- Cada RN/DD del scope y de "Leer antes" tiene al menos un escenario que la ejercite. Las que no, van en
  "Reglas del scope sin escenario". Severidad: `MAYOR`.
- Cada requirement que fija un comportamiento de dominio debería citar su regla (`RN-AG-04`, `DD-15`).
  Severidad si no cita: `MENOR`.
- Un escenario que **contradice** una RN/DD, una "Excepción global" de `05_reglas_de_negocio.md` o un
  escenario de un spec archivado (`openspec/specs/`): `BLOQUEANTE`.

## C3 — Scope del change
Comparar contra el bloque del change en `CHANGES.md` y contra los changes que llegan después.
- Escenarios que implementan algo asignado a otro change (por ejemplo, auditoría en C-06 cuando es C-07,
  horarios en C-05 cuando es C-10): `BLOQUEANTE`. Las reglas duras prohíben implementar fuera del spec y
  el roadmap asigna cada cosa a un único change.
- Escenarios que dependen de algo que todavía no existe (una tabla o endpoint de un change no
  implementado): `BLOQUEANTE`.
- Los ítems de "Fuera de alcance / backlog" de `CHANGES.md` no se piden como faltantes.

## C4 — Contrato HTTP coherente
Contrastar con la sección "Excepciones globales" de `knowledge-base/05_reglas_de_negocio.md` y con
DD-21/DD-22/DD-23:
- Solapamiento -> `409`; violación de horario/bloqueo/validación de dominio -> `422`; referencia
  inexistente en el **body** -> `422`; recurso inexistente en el **path** -> `404`.
- Auth (`07_flujos_principales.md` §Flujo 1 y scope de C-06): credenciales inválidas y token vencido ->
  `401`; rol insuficiente -> `403`. No son intercambiables. La KB **no** fija el código para request sin
  token, token malformado o usuario desactivado: si el spec los decide, debe citar una DD nueva del change;
  si no, van a "Preguntas abiertas" (ojo: según la versión, `HTTPBearer` de FastAPI respondió `403` sin header; verificarlo con Context7).
- Un código distinto del contrato sin una decisión DD que lo justifique: `MAYOR`.

## C5 — Verificabilidad
Un escenario es verificable si el THEN se puede chequear con un `assert`.
- THEN vago ("funciona correctamente", "se maneja el error", "responde rápido"): `BLOQUEANTE`.
- THEN sin estado observable: además del status code, decir qué queda (o no queda) persistido. Si una
  operación falla y el escenario no dice "no se persiste" / "el original queda intacto": `MAYOR` en
  operaciones de escritura.
- Valores concretos: fechas con zona horaria, duraciones con unidad, roles con su nombre exacto
  (`recepcionista`, `odontologo`). Faltantes: `MENOR`.

## C6 — Tiempo y zona horaria
Aplica a todo escenario con instantes (turnos, expiración de tokens, recordatorios).
- El GIVEN fija el reloj ("el reloj marca 2026-10-07 09:00 hora local") cuando el resultado depende de
  "ahora". Sin reloj fijo, el test es no determinista: `MAYOR`. Si `tasks.md` ya fija el reloj para esos
  tests, el riesgo es solo de redacción del spec: `MENOR`.
- Instantes con offset explícito (`-03:00` o `Z`); persistencia en UTC, presentación en
  `America/Argentina/Buenos_Aires` (RN-CU-04, DD-06).
- Bordes de intervalo `[inicio, fin)`: contiguo válido, un minuto de solape rechazado (RN-AG-03).

## C7 — Ambigüedad de redacción
- Requirement sin SHALL/MUST, o con "debería", "puede", "idealmente" en algo normativo: `MENOR`.
- Términos sin definir en la KB ("expiración corta", "usuario válido", "admin"): `MAYOR` si cambia el
  resultado del test. Proponer la pregunta abierta, no el valor.
- Roles o estados que no existen en la KB (por ejemplo un rol `admin`, prohibido por DD-05): `BLOQUEANTE`.

## C8 — Reglas duras del proyecto
- Datos de ejemplo ficticios (RN-CU-02): DNI, emails y teléfonos inventados. Nada que parezca real: `MAYOR`.
- Ningún secreto en escenarios ni en `.env.example` más allá de placeholders (RN-CU-03): `BLOQUEANTE`.
- Si el change toca solapamientos, hay un escenario o tarea de concurrencia contra PostgreSQL real
  (DD-18, RN-AG-09): `MAYOR` si falta.
- Recordatorios sin datos clínicos (RN-NO-04): `BLOQUEANTE` si un escenario muestra la prestación.

## C9 — Tareas de verificación (solo si existe `tasks.md`)
- Cada escenario tiene una tarea que dice cómo se verificará (qué test, qué capa). Escenarios sin tarea:
  `MAYOR`.
- Tareas que no corresponden a ningún escenario: señalarlas como `SUGERENCIA` (pueden ser setup legítimo).
