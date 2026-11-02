# Revisión de escenarios — recordatorios-mock-redis (C-12)

- Fecha: 2026-11-02
- Specs revisados: `openspec/changes/recordatorios-mock-redis/specs/recordatorios/spec.md` y `openspec/changes/recordatorios-mock-redis/specs/app-configuration/spec.md` (más `proposal.md`, `design.md`, `tasks.md` y los specs archivados `app-configuration` y `agenda-turnos`)
- Reglas aplicables: RN-NO-01, RN-NO-02, RN-NO-03, RN-NO-04, RN-NO-05, RN-CU-02, RN-CU-03, RN-CU-04, excepción global "operaciones atómicas junto con su registro de auditoría" (05) y unidad de trabajo turno + auditoría + recordatorio (08 §Patrones aplicados), Flujo 6 (incluida su sección de errores), 04 §Recordatorio, US-012, DD-04, DD-08, DD-13, DD-15, DD-19, DD-21, DD-22, DD-23, DD-24 (solo por la validación de configuración), DD-25 (atomicidad con la auditoría), SU-07, y el scope de C-12 en `CHANGES.md`.
- Decisiones **[A confirmar]** de `design.md` (D2, D5, D6, D9, D10, D12, D14): **pendientes de aprobación**. Se evalúan abajo, en una sección propia. Ninguna introduce en silencio una regla de dominio sin respaldo en la KB.
- Veredicto: **LISTO PARA APPLY**, con la condición de que el usuario apruebe las decisiones [A confirmar] (governance ALTO). Hay 0 BLOQUEANTE y 0 MAYOR. Los 9 MENOR se corrigen con `/opsx:update` si se toca el spec; conviene corregir H1 antes del Apply porque el arreglo es barato.

## Cobertura

### `recordatorios` (capability nueva)

| Requirement | Escenarios | Esperado | Error de negocio | Borde | Reglas cubiertas |
|-------------|-----------:|:--------:|:----------------:|:-----:|------------------|
| Programación al crear un turno | 4 | 1 | 1 (< 24 h no programa) | 2 (24 h exactas; anticipación de 48 h, con 47 h y 49 h) | RN-NO-01, RN-NO-03, DD-13, US-012 (configurable) |
| Cancelar cancela el pendiente | 3 | 1 | 0 | 2 (sin recordatorio; `enviado` intacto) | RN-NO-02 |
| Reprogramar reprograma | 5 | 1 | 1 (nuevo inicio < 24 h) | 3 (sin previo; inicio sin cambio; `enviado` previo) | RN-NO-02, RN-NO-03, DD-23 (reprogramación parcial) |
| Atomicidad con el turno | 3 | 0 | 3 (rollback del alta, rollback de la reprogramación, rechazos 409/422/409) | 0 | Excepción global de atomicidad, 08 (unidad de trabajo), DD-15, DD-21, DD-22 |
| Encolado post-commit | 4 | 2 | 1 (alta rechazada no encola) | 1 (cola caída) | Flujo 6 (errores), US-012 |
| Cola con vencimiento | 3 | 1 | 0 | 2 (entrega única; re-encolar reemplaza el vencimiento) | DD-04, 08 (cola de trabajo) |
| Envío por el worker | 3 | 2 | 0 | 1 (12:59Z, todavía no vence) | Flujo 6 pasos 1 y 2, DD-04 |
| Sin envío para cancelados o no pendientes | 5 | 0 | 2 (turno cancelado; recordatorio cancelado) | 3 (`enviado` re-encolado; procesamiento simultáneo; id inexistente) | Flujo 6 paso 1, RN-NO-02, scope C-12 |
| Reintentos y `fallido` | 5 | 2 (1.º y 2.º fallo) | 2 (3.º fallo → `fallido`; un `fallido` no se reintenta) | 1 (falla y después éxito) | RN-NO-05, DD-19, Flujo 6 paso 3 |
| Contenido sin datos clínicos | 3 | 1 | 1 (sin prestación ni datos personales) | 1 (cambio de día por la zona horaria) | RN-NO-04, RN-CU-02, RN-CU-04 |
| Re-encolado al iniciar | 3 | 1 | 0 | 2 (idempotencia; alta con la cola caída) | Flujo 6 (errores), scope C-12 |
| A lo sumo un pendiente por turno | 2 | 1 (históricos más un pendiente) | 1 (segundo pendiente) | 0 | RN-NO-02 (D2) |
| Integridad en la base | 3 | 1 (UTC) | 2 (CHECK/NOT NULL; FK) | 0 | 04 §Recordatorio, DD-08, DD-21, RN-CU-04 |
| Worker como servicio | 3 | 3 | 0 | 0 | DD-04, 08, D14 |
| **Subtotal** | **49** | | | | |

### `app-configuration` (MODIFIED + ADDED)

| Requirement | Escenarios | Esperado | Error de negocio | Borde | Reglas cubiertas |
|-------------|-----------:|:--------:|:----------------:|:-----:|------------------|
| Configuración leída de variables de entorno (MODIFIED) | 4 (2 previos + 2 nuevos) | 4 | 0 | 0 | RN-CU-03, US-012, DD-13 |
| Fallo explícito ante configuración faltante (MODIFIED) | 10 (6 previos + 4 nuevos) | 0 | 8 | 2 (`JWT_EXPIRE_MINUTES=1`, `REMINDER_LEAD_HOURS=1`) | DD-24 (f), D12, D13 |
| Variables de recordatorios en la plantilla (ADDED) | 2 | 2 | 0 | 0 | RN-CU-03 |
| **Subtotal** | **16** | | | | |

**Total: 65 escenarios.**

- **Reglas del scope sin escenario**: ninguna. Todos los ítems del scope y de los "Tests" de C-12 en `CHANGES.md` tienen escenario: encolado al crear, nada con menos de 24 h, ajuste al cancelar y al reprogramar, el worker invoca el puerto (mock), 3 reintentos y `fallido`, un turno cancelado no envía, y re-encolado al reiniciar.
- **C1**: se cumple. Hay escenarios esperados, de error de negocio y de borde.
- **C2, contra los specs archivados**: los bloques MODIFIED de `app-configuration` conservan textualmente los 2 escenarios previos de "Configuración leída…" y los 6 de "Fallo explícito…". El requirement "Plantilla de entorno versionada sin secretos" no se modifica y sigue coherente con el ADDED. No hay contradicciones con `agenda-turnos`: se mantienen los códigos `201`/`200`/`409 turno_ya_cancelado`/`422`, y la reprogramación parcial (DD-23a) se usa en "Reprogramación sin cambio de inicio".
- **C3**: nada pertenece a otro change. No aparecen horarios ni bloqueos (C-10, C-11), agenda (C-13), endpoints de lectura, frontend, mensajería real ni auditoría de recordatorios (descartada con fundamento en RN-CU-01). La migración `006` está coordinada con C-08 por la regla de renumerar.
- **C4**: el change no agrega endpoints ni códigos. La caída de la cola responde `201`, coherente con el Flujo 6 (errores).
- **C8**: los datos son ficticios ("Ana Prueba", "Ficticio Pérez", DNI "30111222", "Consultorio Odontológico Ejemplo") y no hay secretos. El change no toca solapamientos, y aun así trae un escenario de concurrencia del worker contra PostgreSQL real (tarea 9.4). RN-NO-04 se cumple: ningún escenario muestra la prestación.
- **C9**: cada escenario tiene su tarea (3.x, 4.3, 6.1, 7.x, 8.x, 9.x, 10.1, 2.x). Las tareas sin escenario son setup o documentación legítimos: 1.x, 2.4, 4.4, 9.7, 10.2, 11.x.

## Evaluación de las decisiones [A confirmar]

| Id | ¿Tiene respaldo en la KB? | ¿Introduce una regla de dominio nueva? | Observación |
|----|---------------------------|----------------------------------------|-------------|
| D2 (CHECKs, coherencia estado/intentos, único parcial) | Sí. Estados y canal en 04 §Recordatorio, varchar + CHECK en DD-21, "agotados → `fallido`" en DD-19 y "su recordatorio pendiente" (en singular) en RN-NO-02 | No. Son invariantes derivados | El CHECK `fallido ⇒ intentos = 3` impide en el futuro un `fallido` por otra causa (por ejemplo, un paciente sin contacto). Hoy la KB no lo contempla, así que es correcto. Mencionarlo en DD-26 |
| D5 (reprogramar actúa solo si cambia `inicio`; fila nueva) | Sí. RN-NO-02, y RN-NO-03 (`programado_para` depende solo del inicio) | No | Consecuencia a aprobar a conciencia: un turno con recordatorio ya `enviado` que se reprograma recibe un **segundo** recordatorio, para la fecha nueva. Se apoya en RN-NO-01 ("todo turno activo genera un recordatorio previo"). Conviene que DD-26 lo diga explícitamente |
| D6 (encolado post-commit, best-effort; cancelar no toca Redis) | Sí. Flujo 6, errores ("pendientes persisten en BD y se re-encolan al reiniciar", **Suposición**), y Flujo 6 paso 1 (el worker verifica el turno) | No | Tiene el mismo carácter de suposición que la KB. Ver S4 sobre el hueco cuando Redis pierde datos mientras el worker sigue vivo |
| D9 (backoff de 1 min y después 2 min) | En parte. DD-19 fija "exponencial" y no da valores | No es una regla de dominio: es un parámetro | El spec vuelve normativos los valores (13:01Z, 13:03Z), así que DD-26 tiene que registrarlos |
| D10 (3 intentos en total) | Sí. DD-19 ("3 intentos") y 04 ("máximo 3"). RN-NO-05 cita DD-19 como fuente | No | Ambigüedad de redacción en RN-NO-05 ("se reintenta hasta 3 veces") **y también en US-012** ("se reintenta 3 veces"), que admiten leer 1 + 3. Ver H3 |
| D12 (`CONSULTORIO_NOMBRE`, texto fijo, formato `dd/mm/aaaa HH:MM`) | RN-NO-04 exige el consultorio en el contenido. La KB no tiene ninguna fuente de ese dato. SU-07 (monotenant) justifica una variable por despliegue | No. Es configuración y redacción de producto, no una regla. Que el mensaje excluya al profesional y el nombre del paciente sale del "solo fecha, hora, consultorio" de RN-NO-04 | La aprobación tiene que cubrir el texto exacto y el valor por defecto "Consultorio odontológico". La tarea 2.4 actualiza la tabla de variables de 08 |
| D14 (`ConfiguracionWorker` sin `JWT_SECRET`) | Mínimo privilegio (08 §Seguridad), en línea con RN-CU-03 | No | Sin observaciones |

## Hallazgos

### H1 — Fechas de prueba en sábado, que dejarán de ser válidas con C-10 · MENOR
- **Dónde**: `recordatorios/spec.md`. En "Reprogramar el turno reprograma su recordatorio", los escenarios "Nuevo inicio con 24 h o más" (`2026-10-10T15:00-03:00`) y "Recordatorio ya enviado y nuevo inicio con 24 h o más" (`2026-10-10T10:00-03:00`). En "Atomicidad…", el escenario "Falla del recordatorio revierte la reprogramación". En "Encolado…", el escenario "Recordatorio nuevo encolado tras reprogramar". Las tareas 7.3, 7.4 y 8.2 repiten las mismas fechas.
- **Problema**: el 2026-10-10 es sábado. Cuando C-10 sume la validación de horario de atención a crear y reprogramar (RN-AG-05, que se aplica también al reprogramar por RN-AG-08), estos turnos se rechazarán con `422` y los tests de C-12 se romperán al integrar. Ningún spec archivado usa fines de semana.
- **Fuente**: `CHANGES.md` (nota: "C-04, C-05, C-07, C-10, C-11 y C-12 tocan los mismos casos de uso de turnos… coordinar el merge"), 04 §Seed data ("lunes a viernes, mañana y tarde"), RN-AG-05, RN-AG-08.
- **Sugerencia**: cambiar `2026-10-10` por un día hábil (por ejemplo, el lunes `2026-10-12`) y recalcular `programado_para`. Por ejemplo, `2026-10-12T15:00-03:00` da `2026-10-11T18:00Z`, y `2026-10-12T10:00-03:00` da `2026-10-11T13:00Z`. Mantener los horarios dentro de una franja típica de mañana o tarde.

### H2 — La validación de `REMINDER_LEAD_HOURS` cita DD-24, que no la cubre · MENOR
- **Dónde**: `app-configuration/spec.md`, requirement "Fallo explícito ante configuración obligatoria faltante".
- **Problema**: el texto dice que "`JWT_EXPIRE_MINUTES` y `REMINDER_LEAD_HOURS` MUST ser enteros mayores que cero… (DD-24)". DD-24 (f) habla solo de `JWT_EXPIRE_MINUTES`. Las reglas "`REMINDER_LEAD_HOURS` entero > 0" y "`CONSULTORIO_NOMBRE` no vacío" tampoco figuran como decisiones en la tabla D1..D15, ni en la lista que la tarea 11.1 registra como DD-26. No son reglas de dominio nuevas (son validación de configuración), pero la cita es incorrecta.
- **Fuente**: DD-24 (f), control C2.
- **Sugerencia**: citar DD-26 (o D12/D13) para las variables nuevas. Sumar a D12/D13 "entero > 0 y no numérico inválido, mismo criterio que DD-24 (f)" e incluirlo en la tarea 11.1.

### H3 — La alineación de "3 intentos en total" deja afuera US-012 · MENOR
- **Dónde**: `tasks.md`, tarea 11.1, y design D10.
- **Problema**: la tarea alinea la redacción de RN-NO-05, pero US-012 (06) dice "El envío fallido se reintenta 3 veces", que tiene la misma ambigüedad: leído 1 + 3, el puerto se invocaría 4 veces y no 3 como en el escenario "Tercer intento fallido". El spec sigue a DD-19 y es correcto. El hallazgo es de coherencia de la KB.
- **Fuente**: DD-19, 04 §Recordatorio, 05 RN-NO-05, 06 §US-012.
- **Sugerencia**: que la tarea 11.1 alinee también el criterio de US-012 ("3 intentos en total, el primero más 2 reintentos"), una vez aprobada D10.

### H4 — Relojes sin fijar en varios GIVEN · MENOR
- **Dónde**: `recordatorios/spec.md`, escenarios "Cancelación con recordatorio pendiente", "Cancelación de un turno sin recordatorio", "Recordatorio ya enviado no se modifica al cancelar", "Reprogramación sin cambio de inicio", "Falla del recordatorio revierte el alta" (dice "48 h de anticipación" sin reloj), "Falla del recordatorio revierte la reprogramación", "Operaciones rechazadas no tocan recordatorios" y "Alta rechazada no encola".
- **Problema**: el resultado depende de "ahora" (RN-AG-12, RN-AG-13, RN-NO-03), pero el GIVEN no fija el reloj. El preámbulo de `tasks.md` fija el reloj inyectado, así que el riesgo es solo de redacción.
- **Fuente**: control C6.
- **Sugerencia**: agregar "y que el reloj marca 2026-10-07 09:00 hora local" (o el instante que corresponda) a esos GIVEN.

### H5 — THEN sin resultado observable concreto · MENOR
- **Dónde**: `recordatorios/spec.md`. Escenarios "Falla del recordatorio revierte el alta" y "Falla del recordatorio revierte la reprogramación" ("falla"). "Nuevo inicio con menos de 24 h" y "Turno sin recordatorio reprogramado con 24 h o más" (sin código de respuesta). "Operaciones rechazadas no tocan recordatorios" ("el estado de los existentes es el que dejó la última operación exitosa").
- **Problema**: "falla" no dice qué se observa. La tarea 7.4 lo prueba a nivel de caso de uso, con un error de integridad, pero el spec no lo aclara. A dos reprogramaciones les falta el `200`. El THEN del escenario combinado es indirecto: se puede verificar, pero obliga a reconstruir el estado esperado.
- **Fuente**: control C5.
- **Sugerencia**: "a nivel de caso de uso se lanza el error de integridad de la base; no se define respuesta HTTP". Agregar "la respuesta es `200`" donde falta. Concretar el escenario combinado: "después del `409` y del `422` el recordatorio sigue `pendiente` con el mismo id; después de la segunda cancelación sigue `cancelado`, y el total de recordatorios del turno no cambia".

### H6 — Requirements sin cita de su regla · MENOR
- **Dónde**: `recordatorios/spec.md`, requirements "Atomicidad del recordatorio con el cambio del turno", "Encolado después de confirmar el cambio", "Cola de recordatorios con vencimiento", "Sin envío para turnos cancelados ni recordatorios no pendientes", "A lo sumo un recordatorio pendiente por turno", "Integridad del recordatorio en la base" y "Worker desplegado como servicio".
- **Problema**: fijan comportamiento de dominio o de integridad sin citar de dónde sale.
- **Fuente**: control C2.
- **Sugerencia**: citar, en el orden de la lista, 05 §Excepciones globales + 08 (unidad de trabajo); Flujo 6 (errores); DD-04 + 08 (cola de trabajo); Flujo 6 paso 1 + RN-NO-02; RN-NO-02 + DD-26 (D2); 04 §Recordatorio + DD-08 + DD-21; DD-04 + DD-26 (D14).

### H7 — "Cola caída" y "rechazada no publica" se prueban solo en el alta · MENOR
- **Dónde**: `recordatorios/spec.md`, requirement "Encolado después de confirmar el cambio".
- **Problema**: el requirement abarca toda "operación sobre el turno", pero la reprogramación también publica (tarea 8.2) y no tiene escenario de cola caída (debería responder `200` y dejar el nuevo `pendiente` en la base) ni de reprogramación rechazada sin publicar.
- **Fuente**: Flujo 6 (errores), texto del propio requirement.
- **Sugerencia**: agregar "Cola no disponible al reprogramar" (`200`, el anterior `cancelado` y el nuevo `pendiente` en la base) y extender "Alta rechazada no encola" a una reprogramación con `409`.

### H8 — Reprogramar con recordatorio `fallido` sin escenario · MENOR
- **Dónde**: `recordatorios/spec.md`, requirement "Reprogramar el turno reprograma su recordatorio".
- **Problema**: el requirement dice que los recordatorios `enviado` o `fallido` MUST NOT modificarse, pero solo hay escenario para `enviado`.
- **Fuente**: texto del requirement, RN-NO-05 (`fallido` es terminal y no se reintenta a mano).
- **Sugerencia**: agregar o parametrizar: "turno con recordatorio `fallido` (`intentos` 3) reprogramado con 24 h o más → el `fallido` sigue igual y se crea un `pendiente` nuevo".

### H9 — Borde "un minuto menos que la anticipación" no ejercitado · MENOR
- **Dónde**: `recordatorios/spec.md`, requirement "Programación del recordatorio al crear un turno", escenario "Alta con menos de 24 h de anticipación" (usa 23 h 55 min).
- **Problema**: el borde de 24 h exactas está cubierto, pero el caso "por debajo" queda a 5 minutos del umbral. La grilla de 5 minutos (DD-15) restringe el inicio, no el reloj: con el reloj en 09:01 se llega a 23 h 59 min.
- **Fuente**: RN-NO-03, DD-13 (lista de bordes de notificaciones de la skill).
- **Sugerencia**: reloj en 2026-10-07 09:01 hora local e inicio 2026-10-08T09:00-03:00 (23 h 59 min) → sin recordatorio. También se puede sumar el caso de 24 h exactas a la reprogramación.

## Sugerencias

- **S1. Carrera entre la cancelación y el worker**: D8 la resuelve con `FOR SHARE` sobre el turno y `FOR UPDATE` sobre el recordatorio, pero ningún test la ejercita. Un test con `motor_concurrente` y una barrera, que cancele mientras el worker procesa, verificaría que el resultado sea "enviado y después cancelado" o "cancelado y no enviado", y nunca otro.
- **S2. "Un vencido se entrega una sola vez"** se prueba con dos consumidores secuenciales. El requirement dice "a un solo consumidor". Una variante concurrente en el contrato de `ColaRedis` (dos hilos con `tomar_vencidos`) probaría la semántica de `ZREM`.
- **S3. Recordatorio cancelado por una reprogramación que seguía en la cola**: es la misma mecánica que "Recordatorio cancelado que seguía en la cola" (que prueba la cancelación). Se puede parametrizar con la reprogramación.
- **S4. Redis pierde datos con el worker vivo**: el design lo acepta como riesgo (re-encolado solo al reiniciar, coherente con la Suposición del Flujo 6). Si se quiere cerrar el hueco, la reconciliación periódica o `--appendonly yes` quedan como candidatos al backlog de `CHANGES.md`. No es exigible en C-12.

## Preguntas abiertas

Coinciden con las del design. Las dos son legítimas y no bloquean C-12 (la tarea 11.1 las suma a `10_preguntas_abiertas.md`):

1. **Lectura del estado de los recordatorios**. La matriz de `03_actores_y_roles.md` da `R` a la recepcionista y `R propios` al odontólogo, pero ningún change ni el backlog de `CHANGES.md` lo asignan. Pedirlo en C-12 sería ampliar el scope (control C3). Opciones: (a) sumarlo al scope de C-13 (agenda, que ya filtra por `profesional_id`); (b) un change nuevo; (c) mandarlo al backlog y anotar en 03 que la matriz anticipa algo que el MVP no expone. Es una decisión de roadmap, no de este spec.
2. **Recordatorio procesado después del inicio del turno** (Redis y el worker caídos más de 24 h, o un re-encolado tardío). La KB solo exige que el turno "siga activo". Opciones: (a) enviarlo igual (lo que hace hoy el spec, sin regla nueva); (b) descartarlo pasándolo a `cancelado` si `ahora >= turno.inicio` (sería una regla nueva, que requiere una DD); (c) un estado nuevo, por ejemplo `vencido` (regla y migración nuevas). Mientras no se decida, (a) es lo único que respalda la KB.

## Fuera de esta revisión

- `.env.example` no se leyó: el design avisa que la lectura se denegó al proponer. Que los valores sean placeholders se verificará en la tarea 2.3.
- No se verificó el código existente (firmas de los observadores, fixtures `client`, `catalogo_commiteado`, `test_migrations.py`). Se tomó lo que describe `design.md` §Context.
- No se corrieron tests ni `openspec validate` (el orquestador informa que `--strict` pasa).
- Las decisiones [A confirmar] se evaluaron solo por su respaldo en la KB. Aprobarlas es una decisión del usuario (governance ALTO).
