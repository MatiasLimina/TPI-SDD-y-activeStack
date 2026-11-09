# Design

## Context

Ver `proposal.md` y el delta spec `registro-pacientes`. Estado actual verificado en el código (`main` con C-11):

- **Modelo**: `Paciente` existe desde C-02 (migración `002`): `nombre` 100, `apellido` 100, `documento` 20 con `uq_paciente_documento`, `telefono` 30, `email` 254 nullable, `activo` con default `true`, más `CatalogoMixin`. El seed usa documentos como `FIC-0001` y teléfonos como `+54 11 5555-0001`; el spec de `recordatorios` usa un documento numérico ficticio.
- **Turnos**: `RepositorioTurnos._activa` ya lee al paciente con `FOR SHARE` y responde `422 referencia_invalida` (`inexistente` o `inactiva`); lo usan el alta y la reprogramación. La cancelación no carga referencias. La FK `turno.paciente_id` es `ON DELETE RESTRICT`.
- **Precedente C-08**: `RepositorioRecursos`, `CrearRecurso`, `EditarRecurso`, `DesactivarRecurso` y los manejadores globales de `RecursoInexistenteError`, `RecursoDuplicadoError` y `EstadoNoEditableError`. El factory `_router` no sirve tal cual: asume lectura idéntica para ambos roles y no tiene búsqueda.
- **Recordatorios (C-12)**: el worker lee `Turno.estado`, `paciente_id` e `inicio`; no consulta `Paciente.activo`.
- **Roles**: `usuario.profesional_id` no es nulo para el odontólogo (`ck_usuario_profesional_segun_rol`). `profesional_ajeno` (DD-27 i) responde `403` antes que la existencia.
- **Logs y errores**: el `CMD` del `Dockerfile` corre `uvicorn` con el log de acceso activo, que incluye la query string. El `422` por defecto de FastAPI incluye `input`, y cuando falta un campo, `input` es **el body entero**.

## Goals / Non-Goals

**Goals:**
- Contrato HTTP alineado con DD-26 y una sola implementación de los flujos de escritura.
- Mínimo privilegio real para el odontólogo: pocos campos, una sola ruta, sin revelar si un paciente existe.
- Ningún dato de paciente en errores ni logs nuevos, incluida la búsqueda en la URL.

**Non-Goals:**
- Búsqueda difusa, ranking por relevancia, conteo total o paginación por cursor.
- Unificar documentos con formatos distintos (`00.000.104` y `00000104`).
- Nombre del paciente embebido en la respuesta de turnos: C-09 no lo cambia (ver "Nota de coordinación con C-13").

## Decisions

Las decisiones que no surgen de la KB (D1, D2, D3, D5, D6, D7, D8, D11, D13, D14, D15, D16, D17 y D18) **fueron aprobadas por el usuario el 2026-11-09** con la opción de esta tabla, y se registran como **DD-31** (tarea 11.1). El literal de DD-31 de cada una figura en la columna Estado y es el que citan los requirements; D4 suma a DD-31 el código nuevo `paciente_ajeno`. Si alguna cambia, corregir los artefactos con `/opsx:update`.

| # | Decisión | Estado | Opción aprobada o adoptada |
|---|----------|--------|--------------------|
| D1 | Campos de la lectura mínima | Aprobada 2026-11-09, DD-31 a | `id`, `nombre`, `apellido` |
| D2 | Rutas del odontólogo | Aprobada 2026-11-09, DD-31 b | Solo `GET /pacientes/{id}` |
| D3 | Qué es "paciente de sus turnos" | Aprobada 2026-11-09, DD-31 c | Un turno de su profesional, en cualquier estado |
| D4 | Paciente ajeno o inexistente | Precedente DD-27 i, código en DD-31 d | `403 paciente_ajeno`, igual en ambos casos |
| D5 | Parámetro de búsqueda | Aprobada 2026-11-09, DD-31 e | `q` único, parcial, varios términos con AND |
| D6 | Mayúsculas y acentos | Aprobada 2026-11-09, DD-31 f | Ambos ignorados, con `translate` y `lower` |
| D7 | Inactivos en listado y búsqueda | Aprobada 2026-11-09, DD-31 g | Aparecen, con `activo` (DD-26 a) |
| D8 | Orden y paginación | Aprobada 2026-11-09, DD-31 h | `limite` 50 (máx. 100) y `desplazamiento`; lista simple |
| D9 | Índice y migración | Decisión técnica | Ninguno: **este change no tiene migración** |
| D10 | Documento duplicado | Precedente DD-26 e | `409 recurso_duplicado` por nombre de constraint |
| D11 | `PATCH` y documento editable | Aprobada 2026-11-09 (el documento), DD-31 i | Editable; lo demás, DD-26 j |
| D12 | Desactivación | Precedente DD-26 c, g | `POST /{id}/desactivar`, idempotente; turnos intactos |
| D13 | Recordatorios de un paciente desactivado | Aprobada 2026-11-09, DD-31 j | La desactivación no cambia su procesamiento (RN-NO-01, RN-NO-05, DD-29 a) |
| D14 | Reactivación | Aprobada 2026-11-09, DD-31 k | Fuera de alcance; va al backlog |
| D15 | Documento y teléfono | Aprobada 2026-11-09, DD-31 l | Solo recorte y largo, sin formato |
| D16 | Formato del email | Aprobada 2026-11-09, DD-31 m | Chequeo mínimo, sin dependencia nueva |
| D17 | Errores sin datos personales | Aprobada 2026-11-09, DD-31 n | `422` de `/pacientes` sin `input` ni `ctx` |
| D18 | Búsqueda fuera del log de acceso | Aprobada 2026-11-09, DD-31 o | Filtro que quita la query de `/pacientes` |
| D19 | Auditoría | KB, RN-CU-01 | No se auditan pacientes |

### D1 — Campos de la lectura mínima
La KB dice "R (pacientes de sus turnos, **Suposición**)" y `CHANGES.md` "lectura mínima", sin enumerar campos. **Aprobado**: `id`, `nombre` y `apellido`: identifica a quien atiende, que es para lo que el odontólogo necesita leer (RN-AU-02: ve su agenda). Dos schemas de salida, `PacienteOut` y `PacienteResumenOut`. **Alternativas**: sumar `telefono`, útil para avisar un imprevisto, pero contactar pacientes es tarea de recepción y es un dato de contacto más; ficha completa, contradice "mínima".

### D2 — Rutas del odontólogo
**Aprobado**: solo `GET /pacientes/{id}`; `GET /pacientes` da `403 rol_insuficiente`. US-009 pide buscar a la recepcionista, y el id ya llega en cada turno de su agenda. **Alternativa**: `GET /pacientes` filtrado a sus pacientes, que evita N pedidos al armar la agenda pero suma una consulta sobre datos personales que la KB no pide; si C-13 o C-15 lo necesitan, se agrega con su change (ver "Nota de coordinación con C-13").

### D3 — Qué es "paciente de sus turnos"
**Aprobado**: tener al menos un turno con su `profesional_id`, en cualquier estado, pasado o futuro. Es la lectura literal de la matriz, y coherente con "Turnos: R solo propios". **Alternativa**: excluir cancelados, más restrictiva, pero un turno cancelado que el odontólogo sí ve en su agenda quedaría sin nombre. El estado de actividad del paciente no influye: sus turnos se conservan (DD-26 g).

### D4 — Paciente ajeno o inexistente
`403` con `{"detail": {"codigo": "paciente_ajeno", "mensaje": "Solo podés consultar pacientes de tus turnos"}}`, evaluado antes que la existencia, como `profesional_ajeno` (DD-27 i). Así un odontólogo no puede averiguar si un id corresponde a un paciente. Se consulta `EXISTS` sobre `turno` por `paciente_id` y `profesional_id`; si da verdadero, la FK garantiza que el paciente existe. Se descartó `404` por el mismo motivo que en DD-27.

### D5 — Parámetro de búsqueda
**Aprobado**: un solo `q`. Se separa por espacios; cada término debe ser subcadena de `nombre`, `apellido` o `documento` (AND entre términos, OR entre campos). Encaja con el selector de paciente de C-15 y resuelve "Carla Imaginaria" en cualquier orden. `%`, `_` y `\` se escapan. Sin largo mínimo: el límite de D8 acota el resultado. Máximo 100 caracteres. **Alternativa**: tres parámetros `nombre`, `apellido`, `documento`, más literal respecto de `CHANGES.md`, pero obliga a la UI a saber qué escribió la persona.

### D6 — Mayúsculas y acentos
**Aprobado**: ignorar ambos, también en `ñ`, para que "perez" encuentre "Pérez" y "nunez" encuentre "Nuñez". En SQL, `lower(translate(col, <acentuadas>, <sin acento>))`, y una **única tabla** de caracteres en `app/domain/pacientes.py` aplicada también en Python a cada término. `translate` va primero y cubre mayúsculas acentuadas, de modo que no depende del locale de la base; `q` se normaliza a NFC. **Alternativas**: extensión `unaccent`, que exige migración y `CREATE EXTENSION`; `ILIKE` a secas, que no encuentra "Pérez" con "perez", el error más común al tipear apellidos.

### D7 — Inactivos en listado y búsqueda
**Aprobado**: aparecen, con `activo`, como DD-26 a. Es necesario para explicar un `409` por documento de un paciente dado de baja, y la UI puede deshabilitar su selección. **Alternativa**: filtrar por defecto y sumar `incluir_inactivos=true`, que limpia el selector a cambio de un parámetro más.

### D8 — Orden y paginación
Orden por `apellido`, `nombre`, `id` (como profesionales; el `id` da páginas estables). **Aprobado**: `limite` (default 50, entre 1 y 100) y `desplazamiento` (default 0), respuesta como lista simple, igual que el resto de la API. C-08 no paginó porque un catálogo es chico; los pacientes crecen sin tope. **Alternativas**: sobre con `total` (cuenta en cada pedido; ninguna regla lo pide); solo `limite` (no permite recorrer el padrón).

### D9 — Índice y migración: **este change no tiene migración**
La tabla y `uq_paciente_documento` existen, y una subcadena no usa un btree. Un consultorio de 1 a 5 profesionales tiene del orden de miles de pacientes: un recorrido secuencial con `LIMIT` es aceptable. Las validaciones nuevas son de la API; C-08 tampoco agregó `CHECK` para textos vacíos. La cabeza sigue en `010` y **no se toma la `011`**. Si el volumen real lo pidiera, un GIN con `pg_trgm` sobre la expresión de D6 es un change aislado. Se descartó agregarlo ahora por sumar extensión e índice sin una medición que lo justifique.

### D10 — Documento duplicado
`409 recurso_duplicado` con `campo = "documento"` (DD-26 e). `DEFINICION_PACIENTE.unicas = {"uq_paciente_documento": "documento"}`: `RepositorioRecursos.guardar` traduce el `IntegrityError` por SQLSTATE `23505` y nombre de constraint dentro de un SAVEPOINT. No hay pre-chequeo: la base decide también en la carrera, y un solo camino de código cubre ambos casos.

### D11 — `PATCH` y documento editable
Semántica DD-26 j: lo omitido se conserva, `null` en un obligatorio da `422`, `email: null` lo quita, los campos desconocidos se ignoran y `activo` da `campo_no_editable`. **Aprobado**: `documento` editable, porque corregir un error de tipeo es el caso real y turnos, recordatorios y auditoría referencian al paciente por `id`. **Alternativa**: inmutable; corregir un error de tipeo obligaría a dar de baja al paciente y cargarlo de nuevo con otro `id`, separándolo de sus turnos. También se permite editar a un desactivado, como en C-08, incluido su documento (ver D14).

### D12 — Desactivación
`POST /pacientes/{id}/desactivar`, idempotente (DD-26 c). Los turnos no cambian y se pueden cancelar; no se pueden reprogramar, consecuencia ya escrita en DD-26. La serialización con el alta ya existe: `FOR UPDATE` de `obtener_para_actualizar` contra `FOR SHARE` de `_activa`; se cubre con test porque es otra ruta sobre la misma garantía.

### D13 — Recordatorios de un paciente desactivado
**Aprobado**: no tocar nada. El worker no mira `Paciente.activo`, y la desactivación no cambia el procesamiento del recordatorio, que sigue sujeto a RN-NO-01, RN-NO-05 y DD-29 (a): no se envía si el turno ya inició (queda `cancelado`) y agotados los intentos queda `fallido`, como cualquier otro. Si el paciente no va a venir, la recepcionista cancela el turno y RN-NO-02 cancela el recordatorio. **Alternativas**: no enviarlo, que deja un turno vivo sin aviso; cancelar los turnos en cascada, que contradice DD-26 g.

### D14 — Reactivación
**Aprobado**: fuera de alcance, como DD-26 d y DD-24 j, y sumada al backlog de `CHANGES.md` (resuelve P1 de la revisión). **Limitación aceptada**: es más seria que en C-08. Si un paciente dado de baja vuelve, no se lo puede reactivar por API, y un alta con su documento da `409` mientras ese documento siga en la fila desactivada. El documento no se libera solo tocando la base: un `PATCH` de `documento` sobre el paciente desactivado (D11) también lo libera, y después se puede dar un alta nueva. Esa es la salida aceptada y no se prohíbe; su costo es un dato de reemplazo en la fila vieja, un `id` nuevo y el historial de turnos repartido entre dos filas. **Alternativas**: `POST /pacientes/{id}/reactivar`, un endpoint chico y simétrico (idempotente, solo recepcionista, 3 o 4 escenarios), que evita esa salida pero amplía el alcance definido en `CHANGES.md`; prohibir editar el documento de un desactivado, que dejaría como única salida tocar la base.

### D15 — Documento y teléfono
**Aprobado**: recortar espacios extremos y validar largo (1 a 20 y 1 a 30); sin formato. La KB no define ninguno y los datos existentes tienen formatos distintos. **Limitación**: `00.000.104` y `00000104` cuentan como documentos distintos. **Alternativa**: quitar puntos y unificar mayúsculas antes de guardar, que detecta más duplicados pero es una regla que la KB no tiene y altera el dato cargado.

### D16 — Formato del email
**Aprobado**: exactamente una `@`, texto a ambos lados y sin espacios; se guarda como vino y no es único (una familia puede compartirlo). Atrapa errores de tipeo sin dependencia nueva. **Alternativas**: `EmailStr`, que suma `email-validator` y rechaza algunos dominios reservados de ejemplo; solo largo, que deja pasar cualquier texto.

### D17 — Errores sin datos personales
No surge de la KB ni de las reglas duras de `CLAUDE.md`: es una decisión aprobada por el usuario el 2026-11-09, que se registra en DD-31 (n). Un manejador de `RequestValidationError` deja solo `type`, `loc` y `msg` cuando la ruta es `/pacientes` o empieza por `/pacientes/`, y delega en el manejador por defecto de FastAPI en cualquier otra, para no alterar contratos ya entregados. Los mensajes de los validadores propios no incluyen el valor, y el de un UUID inválido se reemplaza por uno fijo, porque el de pydantic cita el primer carácter recibido. Los `409` llevan solo `campo`. El código nuevo no loguea datos de pacientes.

### D18 — Búsqueda fuera del log de acceso
`q` lleva nombres y documentos en la URL, y `uvicorn` registra la query string. **Aprobado**: un `logging.Filter` sobre `uvicorn.access` que recorta la query de las rutas de `/pacientes` (conserva método, ruta y status), instalado en el `lifespan` para que corra después de la configuración de logging de `uvicorn`, y sin duplicarse. En `uvicorn` 0.54.0 (fuente revisada), `record.args` es `(client_addr, method, full_path, http_version, status_code)`. Lo que se comprueba es la salida de un `uvicorn` real en un subproceso (tarea 10.4), no solo un `LogRecord` armado por el test. **Alternativas**: `POST /pacientes/buscar` con body, que evita la URL en todo el camino, incluidos proxies futuros, pero se aparta del `GET` de `CHANGES.md` y de lo idempotente; `--no-access-log`, que pierde el log de toda la API.

### D19 — Auditoría
RN-CU-01 y la matriz auditan solo cambios de turno. No se auditan altas, ediciones ni desactivaciones de pacientes, y desactivar no genera filas de auditoría porque no cambia ningún turno.

### Capas y módulos

- `app/domain/pacientes.py`: tabla de plegado, `terminos_busqueda`, `email_valido` y `PacienteAjenoError`. `TipoRecurso` suma `PACIENTE`.
- `app/infrastructure/db/repositorio_pacientes.py`: `DEFINICION_PACIENTE` y `RepositorioPacientes(RepositorioRecursos[Paciente])`, que agrega `buscar(terminos, limite, desplazamiento)` y `tiene_turno_de(paciente_id, profesional_id)`.
- `app/application/gestion_pacientes.py`: `ConsultarPaciente`, que decide según el rol. Alta, edición y desactivación reutilizan los casos de uso genéricos de C-08.
- `app/api/pacientes.py`: schemas, router y `registrar_manejadores_pacientes`. `_Entrada` y `_Cambios` de `recursos.py` pasan a ser públicas, sin cambios de comportamiento.
- `response_model` del detalle: `PacienteOut | PacienteResumenOut`, con `PacienteOut` primero. La respuesta se valida como dict: un resumen no puede convertirse en ficha completa porque le faltan campos obligatorios; los tests afirman el conjunto exacto de claves.

### Orden de evaluación

`401` → `403 rol_insuficiente` → `422` de path, query o contenido del body → `422 campo_no_editable` → (odontólogo) `403 paciente_ajeno` → `404 recurso_inexistente` → `409 recurso_duplicado`. Es el orden de C-08, con `paciente_ajeno` en el lugar que tiene en DD-27 i.

Excepción: FastAPI parsea el JSON antes de resolver las dependencias, así que un body con JSON sintácticamente inválido responde `422` aunque falte el token o el rol no alcance. No se ejecuta el caso de uso ni se persiste nada, y ese `422` tampoco reproduce lo enviado (D17). Es el comportamiento que ya tienen las rutas de C-08; este change no lo modifica.

## Risks / Trade-offs

- [Consulta sin índice si el padrón crece mucho] → Límite máximo por página y plan descrito en D9, sin cambiar el contrato.
- [Documento con otro formato pasa como distinto] → Aceptado en D15; la búsqueda parcial ayuda a detectarlo antes del alta.
- [Paciente dado de baja que vuelve no se puede reactivar por API] → Aceptado en D14: `PATCH` del documento del desactivado y alta nueva, con `id` nuevo e historial repartido. La reactivación queda en el backlog.
- [El filtro de log depende del formato de argumentos de `uvicorn.access` y falla abierto: si `record.args` cambia, no toca el registro y la búsqueda vuelve al log] → `pyproject.toml` pide `uvicorn>=0.30`, sin tope. La tarea 10.4 levanta `uvicorn` real y lee su salida: si el formato cambia, "FIC-0101" aparece y el test falla. Riesgo residual: desplegar una versión de `uvicorn` con la que no se corrió `pytest`.
- [Otros intermediarios pueden registrar la URL, como un proxy en producción] → No existen en el despliegue del MVP; D18 lo deja como motivo de la alternativa `POST`.
- [Texto guardado en forma Unicode descompuesta no se pliega] → Solo con entradas atípicas; lo que queda sin plegar sigue encontrándose escrito igual.
- [El carácter `U+0000` hace fallar al driver con `500`] → Se rechaza con `422` en los textos, en alta y en edición, y en `q` de `/pacientes`. Las rutas de C-08 mantienen ese comportamiento: está fuera de este change.

## Migration Plan

Sin migración de datos ni de esquema. Despliegue: nuevas rutas y filtro de log, sin pasos previos. Rollback: revertir el código; la base no cambia.

## Open Questions

Ninguna. Las decisiones se aprobaron el 2026-11-09, y P1 de la revisión se resolvió con D14.

### Nota de coordinación con C-13

No es un requisito de C-09, que no cambia por esto (P2 de la revisión). `TurnoOut` trae solo `paciente_id` y el odontólogo lee de a un paciente (D1, D2). Se espera que la agenda de C-13 lleve el nombre del paciente en su propia respuesta, y eso debe definirlo C-13 (responsable: Matías); sin eso, la agenda de C-15 necesitaría un pedido por paciente. Se avisa en la descripción del PR.
