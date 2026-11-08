# Design

## Context

Ver `proposal.md` y el delta spec `registro-pacientes`. Estado actual verificado en el código (`main` con C-11):

- **Modelo**: `Paciente` existe desde C-02 (migración `002`): `nombre` 100, `apellido` 100, `documento` 20 con `uq_paciente_documento`, `telefono` 30, `email` 254 nullable, `activo` con default `true`, más `CatalogoMixin`. El seed usa documentos como `FIC-0001` y teléfonos como `+54 11 5555-0001`; `recordatorios` usa un DNI ficticio `30111222`.
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
- Unificar documentos con formatos distintos (`30.111.222` y `30111222`).
- Nombre del paciente embebido en la respuesta de turnos: si hace falta, lo decide C-13.

## Decisions

Las marcadas **[A confirmar]** no surgen de la KB. Como son datos personales, **requieren aprobación del usuario antes del Apply**. Los specs y las tareas están escritos con la opción recomendada; si se elige otra, corregirlos con `/opsx:update`. Al aprobarse se registran como **DD-31** (tarea 11.1).

| # | Decisión | Estado | Opción recomendada |
|---|----------|--------|--------------------|
| D1 | Campos de la lectura mínima | **[A confirmar]** | `id`, `nombre`, `apellido` |
| D2 | Rutas del odontólogo | **[A confirmar]** | Solo `GET /pacientes/{id}` |
| D3 | Qué es "paciente de sus turnos" | **[A confirmar]** | Un turno de su profesional, en cualquier estado |
| D4 | Paciente ajeno o inexistente | Precedente DD-27 i | `403 paciente_ajeno`, igual en ambos casos |
| D5 | Parámetro de búsqueda | **[A confirmar]** | `q` único, parcial, varios términos con AND |
| D6 | Mayúsculas y acentos | **[A confirmar]** | Ambos ignorados, con `translate` y `lower` |
| D7 | Inactivos en listado y búsqueda | **[A confirmar]** | Aparecen, con `activo` (DD-26 a) |
| D8 | Orden y paginación | **[A confirmar]** | `limite` 50 (máx. 100) y `desplazamiento`; lista simple |
| D9 | Índice y migración | Decisión técnica | Ninguno: **este change no tiene migración** |
| D10 | Documento duplicado | Precedente DD-26 e | `409 recurso_duplicado` por nombre de constraint |
| D11 | `PATCH` y documento editable | **[A confirmar]** el documento | Editable; lo demás, DD-26 j |
| D12 | Desactivación | Precedente DD-26 c, g | `POST /{id}/desactivar`, idempotente; turnos intactos |
| D13 | Recordatorios de un paciente desactivado | **[A confirmar]** | Se envían si el turno sigue `programado` |
| D14 | Reactivación | **[A confirmar]** | Fuera de alcance; va al backlog |
| D15 | Documento y teléfono | **[A confirmar]** | Solo recorte y largo, sin formato |
| D16 | Formato del email | **[A confirmar]** | Chequeo mínimo, sin dependencia nueva |
| D17 | Errores sin datos personales | Regla del proyecto | `422` de `/pacientes` sin `input` ni `ctx` |
| D18 | Búsqueda fuera del log de acceso | **[A confirmar]** | Filtro que quita la query de `/pacientes` |
| D19 | Auditoría | KB, RN-CU-01 | No se auditan pacientes |

### D1 — Campos de la lectura mínima **[A confirmar]**
La KB dice "R (pacientes de sus turnos, **Suposición**)" y `CHANGES.md` "lectura mínima", sin enumerar campos. **Recomendado**: `id`, `nombre` y `apellido`: identifica a quien atiende, que es para lo que el odontólogo necesita leer (RN-AU-02: ve su agenda). Dos schemas de salida, `PacienteOut` y `PacienteResumenOut`. **Alternativas**: sumar `telefono`, útil para avisar un imprevisto, pero contactar pacientes es tarea de recepción y es un dato de contacto más; ficha completa, contradice "mínima".

### D2 — Rutas del odontólogo **[A confirmar]**
**Recomendado**: solo `GET /pacientes/{id}`; `GET /pacientes` da `403 rol_insuficiente`. US-009 pide buscar a la recepcionista, y el id ya llega en cada turno de su agenda. **Alternativa**: `GET /pacientes` filtrado a sus pacientes, que evita N pedidos al armar la agenda pero suma una consulta sobre datos personales que la KB no pide; si C-13 o C-15 lo necesitan, se agrega con su change.

### D3 — Qué es "paciente de sus turnos" **[A confirmar]**
**Recomendado**: tener al menos un turno con su `profesional_id`, en cualquier estado, pasado o futuro. Es la lectura literal de la matriz, y coherente con "Turnos: R solo propios". **Alternativa**: excluir cancelados, más restrictiva, pero un turno cancelado que el odontólogo sí ve en su agenda quedaría sin nombre. El estado de actividad del paciente no influye: sus turnos se conservan (DD-26 g).

### D4 — Paciente ajeno o inexistente
`403` con `{"detail": {"codigo": "paciente_ajeno", "mensaje": "Solo podés consultar pacientes de tus turnos"}}`, evaluado antes que la existencia, como `profesional_ajeno` (DD-27 i). Así un odontólogo no puede averiguar si un id corresponde a un paciente. Se consulta `EXISTS` sobre `turno` por `paciente_id` y `profesional_id`; si da verdadero, la FK garantiza que el paciente existe. Se descartó `404` por el mismo motivo que en DD-27.

### D5 — Parámetro de búsqueda **[A confirmar]**
**Recomendado**: un solo `q`. Se separa por espacios; cada término debe ser subcadena de `nombre`, `apellido` o `documento` (AND entre términos, OR entre campos). Encaja con el selector de paciente de C-15 y resuelve "Carla Imaginaria" en cualquier orden. `%`, `_` y `\` se escapan. Sin largo mínimo: el límite de D8 acota el resultado. Máximo 100 caracteres. **Alternativa**: tres parámetros `nombre`, `apellido`, `documento`, más literal respecto de `CHANGES.md`, pero obliga a la UI a saber qué escribió la persona.

### D6 — Mayúsculas y acentos **[A confirmar]**
**Recomendado**: ignorar ambos, también en `ñ`, para que "perez" encuentre "Pérez" y "nunez" encuentre "Nuñez". En SQL, `lower(translate(col, <acentuadas>, <sin acento>))`, y una **única tabla** de caracteres en `app/domain/pacientes.py` aplicada también en Python a cada término. `translate` va primero y cubre mayúsculas acentuadas, de modo que no depende del locale de la base; `q` se normaliza a NFC. **Alternativas**: extensión `unaccent`, que exige migración y `CREATE EXTENSION`; `ILIKE` a secas, que no encuentra "Pérez" con "perez", el error más común al tipear apellidos.

### D7 — Inactivos en listado y búsqueda **[A confirmar]**
**Recomendado**: aparecen, con `activo`, como DD-26 a. Es necesario para explicar un `409` por documento de un paciente dado de baja, y la UI puede deshabilitar su selección. **Alternativa**: filtrar por defecto y sumar `incluir_inactivos=true`, que limpia el selector a cambio de un parámetro más.

### D8 — Orden y paginación **[A confirmar]**
Orden por `apellido`, `nombre`, `id` (como profesionales; el `id` da páginas estables). **Recomendado**: `limite` (default 50, entre 1 y 100) y `desplazamiento` (default 0), respuesta como lista simple, igual que el resto de la API. C-08 no paginó porque un catálogo es chico; los pacientes crecen sin tope. **Alternativas**: sobre con `total` (cuenta en cada pedido; ninguna regla lo pide); solo `limite` (no permite recorrer el padrón).

### D9 — Índice y migración: **este change no tiene migración**
La tabla y `uq_paciente_documento` existen, y una subcadena no usa un btree. Un consultorio de 1 a 5 profesionales tiene del orden de miles de pacientes: un recorrido secuencial con `LIMIT` es aceptable. Las validaciones nuevas son de la API; C-08 tampoco agregó `CHECK` para textos vacíos. La cabeza sigue en `010` y **no se toma la `011`**. Si el volumen real lo pidiera, un GIN con `pg_trgm` sobre la expresión de D6 es un change aislado. Se descartó agregarlo ahora por sumar extensión e índice sin una medición que lo justifique.

### D10 — Documento duplicado
`409 recurso_duplicado` con `campo = "documento"` (DD-26 e). `DEFINICION_PACIENTE.unicas = {"uq_paciente_documento": "documento"}`: `RepositorioRecursos.guardar` traduce el `IntegrityError` por SQLSTATE `23505` y nombre de constraint dentro de un SAVEPOINT. No hay pre-chequeo: la base decide también en la carrera, y un solo camino de código cubre ambos casos.

### D11 — `PATCH` y documento editable **[A confirmar] el documento**
Semántica DD-26 j: lo omitido se conserva, `null` en un obligatorio da `422`, `email: null` lo quita, los campos desconocidos se ignoran y `activo` da `campo_no_editable`. **Recomendado**: `documento` editable, porque corregir un error de tipeo es el caso real y turnos, recordatorios y auditoría referencian al paciente por `id`. **Alternativa**: inmutable; corregir un error de tipeo obligaría a dar de baja al paciente y cargarlo de nuevo con otro `id`, separándolo de sus turnos. También se permite editar a un desactivado, como en C-08.

### D12 — Desactivación
`POST /pacientes/{id}/desactivar`, idempotente (DD-26 c). Los turnos no cambian y se pueden cancelar; no se pueden reprogramar, consecuencia ya escrita en DD-26. La serialización con el alta ya existe: `FOR UPDATE` de `obtener_para_actualizar` contra `FOR SHARE` de `_activa`; se cubre con test porque es otra ruta sobre la misma garantía.

### D13 — Recordatorios de un paciente desactivado **[A confirmar]**
**Recomendado**: no tocar nada. El worker no mira `Paciente.activo`, y el turno sigue `programado`: mientras exista, el paciente debe recibir el aviso. Si no va a venir, la recepcionista cancela el turno y RN-NO-02 cancela el recordatorio. **Alternativas**: no enviarlo, que deja un turno vivo sin aviso; cancelar los turnos en cascada, que contradice DD-26 g.

### D14 — Reactivación **[A confirmar]**
**Recomendado**: fuera de alcance, como DD-26 d, y sumada al backlog: `CHANGES.md` solo pide desactivación. **Limitación que hay que aceptar**: es más seria que en C-08, porque si un paciente dado de baja vuelve, su documento sigue tomado y no se lo puede volver a registrar ni reactivar por API; haría falta tocar la base. **Alternativa**: `POST /pacientes/{id}/reactivar`, un endpoint chico y simétrico (idempotente, solo recepcionista, 3 o 4 escenarios), que evita el callejón sin salida pero amplía el alcance definido en `CHANGES.md`.

### D15 — Documento y teléfono **[A confirmar]**
**Recomendado**: recortar espacios extremos y validar largo (1 a 20 y 1 a 30); sin formato. La KB no define ninguno y los datos existentes tienen formatos distintos. **Limitación**: `30.111.222` y `30111222` cuentan como documentos distintos. **Alternativa**: quitar puntos y unificar mayúsculas antes de guardar, que detecta más duplicados pero es una regla que la KB no tiene y altera el dato cargado.

### D16 — Formato del email **[A confirmar]**
**Recomendado**: exactamente una `@`, texto a ambos lados y sin espacios; se guarda como vino y no es único (una familia puede compartirlo). Atrapa errores de tipeo sin dependencia nueva. **Alternativas**: `EmailStr`, que suma `email-validator` y rechaza algunos dominios reservados de ejemplo; solo largo, que deja pasar cualquier texto.

### D17 — Errores sin datos personales
Un manejador de `RequestValidationError` deja solo `type`, `loc` y `msg` cuando la ruta es `/pacientes` o empieza por `/pacientes/`, y delega en el manejador por defecto de FastAPI en cualquier otra, para no alterar contratos ya entregados. Los mensajes de los validadores propios no incluyen el valor. Los `409` llevan solo `campo`. El código nuevo no loguea datos de pacientes.

### D18 — Búsqueda fuera del log de acceso **[A confirmar]**
`q` lleva nombres y documentos en la URL, y `uvicorn` registra la query string. **Recomendado**: un `logging.Filter` sobre `uvicorn.access` que recorta la query de las rutas de `/pacientes` (conserva método, ruta y status), instalado en el `lifespan` para que corra después de la configuración de logging de `uvicorn`, y sin duplicarse. **Alternativas**: `POST /pacientes/buscar` con body, que evita la URL en todo el camino, incluidos proxies futuros, pero se aparta del `GET` de `CHANGES.md` y de lo idempotente; `--no-access-log`, que pierde el log de toda la API.

### D19 — Auditoría
RN-CU-01 y la matriz auditan solo cambios de turno. No se auditan altas, ediciones ni desactivaciones de pacientes, y desactivar no genera filas de auditoría porque no cambia ningún turno.

### Capas y módulos

- `app/domain/pacientes.py`: tabla de plegado, `terminos_busqueda`, `email_valido` y `PacienteAjenoError`. `TipoRecurso` suma `PACIENTE`.
- `app/infrastructure/db/repositorio_pacientes.py`: `DEFINICION_PACIENTE` y `RepositorioPacientes(RepositorioRecursos[Paciente])`, que agrega `buscar(terminos, limite, desplazamiento)` y `tiene_turno_de(paciente_id, profesional_id)`.
- `app/application/gestion_pacientes.py`: `ConsultarPaciente`, que decide según el rol. Alta, edición y desactivación reutilizan los casos de uso genéricos de C-08.
- `app/api/pacientes.py`: schemas, router y `registrar_manejadores_pacientes`. `_Entrada` y `_Cambios` de `recursos.py` pasan a ser públicas, sin cambios de comportamiento.
- `response_model` del detalle: `PacienteOut | PacienteResumenOut`, con `PacienteOut` primero. La respuesta se valida como dict: un resumen no puede convertirse en ficha completa porque le faltan campos obligatorios; los tests afirman el conjunto exacto de claves.

### Orden de evaluación

`401` → `403 rol_insuficiente` → `422` de path, query o body → `422 campo_no_editable` → (odontólogo) `403 paciente_ajeno` → `404 recurso_inexistente` → `409 recurso_duplicado`. Es el orden de C-08, con `paciente_ajeno` en el lugar que tiene en DD-27 i.

## Risks / Trade-offs

- [Consulta sin índice si el padrón crece mucho] → Límite máximo por página y plan descrito en D9, sin cambiar el contrato.
- [Documento con otro formato pasa como distinto] → Aceptado en D15; la búsqueda parcial ayuda a detectarlo antes del alta.
- [Paciente dado de baja que vuelve queda sin salida por API] → D14 lo pone a decisión del usuario.
- [El filtro de log depende del formato de argumentos de `uvicorn.access`] → Si `record.args` no tiene la forma esperada, el filtro no lo toca; un test fija el formato de la versión instalada.
- [Otros intermediarios pueden registrar la URL, como un proxy en producción] → No existen en el despliegue del MVP; D18 lo deja como motivo de la alternativa `POST`.
- [Texto guardado en forma Unicode descompuesta no se pliega] → Solo con entradas atípicas; lo que queda sin plegar sigue encontrándose escrito igual.
- [El carácter `U+0000` hace fallar al driver con `500`] → Se rechaza con `422` en los textos y en `q` de `/pacientes`. Las rutas de C-08 mantienen ese comportamiento: está fuera de este change.

## Migration Plan

Sin migración de datos ni de esquema. Despliegue: nuevas rutas y filtro de log, sin pasos previos. Rollback: revertir el código; la base no cambia.

## Open Questions

Ninguna que pueda diferirse: lo que falta definir son las decisiones **[A confirmar]**, que se resuelven antes del Apply.
