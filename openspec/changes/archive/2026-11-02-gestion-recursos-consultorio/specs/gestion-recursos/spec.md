# Spec Delta

## Purpose

Permitir que la recepcionista dé de alta, edite y desactive lógicamente los profesionales, sillones y prestaciones del consultorio, y que ambos roles los consulten, con validaciones coherentes con la agenda y sin que una desactivación afecte los turnos ya existentes.

## ADDED Requirements

### Requirement: Alta de profesional
El sistema SHALL exponer `POST /profesionales`, que recibe `nombre`, `apellido` y `matricula` opcional, y responde `201` con `id`, `nombre`, `apellido`, `matricula` y `activo`. Todo profesional nuevo MUST quedar activo.

#### Scenario: Profesional con matrícula
- **GIVEN** dada una recepcionista autenticada
- **WHEN** cuando envía `POST /profesionales` con `{"nombre": "Ana", "apellido": "Ficticia", "matricula": "MN-0001"}`
- **THEN** entonces la respuesta es `201` con un `id` nuevo, esos tres valores y `activo = true`, y en la base existe el profesional activo con esa matrícula

#### Scenario: Profesional sin matrícula
- **GIVEN** dada una recepcionista autenticada
- **WHEN** cuando envía `POST /profesionales` con `{"nombre": "Bruno", "apellido": "Inventado"}`
- **THEN** entonces la respuesta es `201` con `matricula = null` y `activo = true`

### Requirement: Alta de sillón
El sistema SHALL exponer `POST /sillones`, que recibe `nombre` y responde `201` con `id`, `nombre` y `activo`. Todo sillón nuevo MUST quedar activo.

#### Scenario: Sillón creado
- **GIVEN** dada una recepcionista autenticada
- **WHEN** cuando envía `POST /sillones` con `{"nombre": "Sillón 3"}`
- **THEN** entonces la respuesta es `201` con un `id` nuevo, `nombre = "Sillón 3"` y `activo = true`

### Requirement: Alta de prestación con duración por defecto
El sistema SHALL exponer `POST /prestaciones`, que recibe `nombre`, `duracion_min` y `requiere_sillon` opcional, y responde `201` con `id`, `nombre`, `duracion_min`, `requiere_sillon` y `activa`. Si no se informa `requiere_sillon`, MUST valer `true` (RN-AG-10). Toda prestación nueva MUST quedar activa.

#### Scenario: Prestación que requiere sillón por defecto
- **GIVEN** dada una recepcionista autenticada
- **WHEN** cuando envía `POST /prestaciones` con `{"nombre": "Endodoncia ficticia", "duracion_min": 90}`
- **THEN** entonces la respuesta es `201` con `duracion_min = 90`, `requiere_sillon = true` y `activa = true`

#### Scenario: Prestación sin sillón
- **GIVEN** dada una recepcionista autenticada
- **WHEN** cuando envía `POST /prestaciones` con `{"nombre": "Control", "duracion_min": 15, "requiere_sillon": false}`
- **THEN** entonces la respuesta es `201` con `requiere_sillon = false`

### Requirement: Duración de la prestación validada por la API
Al dar de alta o editar una prestación, `duracion_min` MUST ser mayor que cero, múltiplo de 5 y no mayor a 480 (DD-15, RN-AG-04). Una violación MUST responder `422` con `{"detail": {"codigo": "duracion_invalida", "mensaje": ...}}`, el mismo código que usan los turnos, sin persistir ni modificar la prestación.

#### Scenario: Duración cero rechazada
- **WHEN** cuando una recepcionista autenticada envía `POST /prestaciones` con `duracion_min = 0`
- **THEN** entonces la respuesta es `422` con código `duracion_invalida` y no se persiste ninguna prestación

#### Scenario: Duración mínima de la grilla aceptada
- **WHEN** cuando una recepcionista autenticada envía `POST /prestaciones` con `duracion_min = 5`
- **THEN** entonces la respuesta es `201` con `duracion_min = 5`

#### Scenario: Duración máxima aceptada
- **WHEN** cuando una recepcionista autenticada envía `POST /prestaciones` con `duracion_min = 480`
- **THEN** entonces la respuesta es `201` con `duracion_min = 480`

#### Scenario: Duración mayor a 480 rechazada
- **WHEN** cuando una recepcionista autenticada envía `POST /prestaciones` con `duracion_min = 485`
- **THEN** entonces la respuesta es `422` con código `duracion_invalida` y no se persiste ninguna prestación

#### Scenario: Duración fuera de la grilla rechazada
- **WHEN** cuando una recepcionista autenticada envía `POST /prestaciones` con `duracion_min = 7`
- **THEN** entonces la respuesta es `422` con código `duracion_invalida` y no se persiste ninguna prestación

#### Scenario: Edición con duración inválida rechazada
- **GIVEN** dada la prestación "Limpieza" con `duracion_min = 45`
- **WHEN** cuando una recepcionista autenticada envía `PATCH /prestaciones/{id}` con `{"duracion_min": 485}`
- **THEN** entonces la respuesta es `422` con código `duracion_invalida` y en la base la prestación sigue con `duracion_min = 45`

### Requirement: Atributos obligatorios y textos normalizados
Los textos del body MUST guardarse sin espacios al principio ni al final. `nombre` (los tres recursos) y `apellido` (profesional) MUST ser obligatorios y no vacíos tras quitar esos espacios, y no superar el largo de su columna; si no, `422` sin persistir. Una `matricula` vacía o solo con espacios MUST quedar nula (DD-26).

#### Scenario: Nombre solo con espacios rechazado
- **WHEN** cuando una recepcionista autenticada envía `POST /sillones` con `{"nombre": "   "}`
- **THEN** entonces la respuesta es `422` y no se persiste ningún sillón

#### Scenario: Campo obligatorio faltante
- **WHEN** cuando una recepcionista autenticada envía `POST /profesionales` con `{"nombre": "Ana"}`, sin `apellido`
- **THEN** entonces la respuesta es `422` y no se persiste ningún profesional

#### Scenario: Nombre más largo que su columna rechazado
- **WHEN** cuando una recepcionista autenticada envía `POST /sillones` con un `nombre` de 51 caracteres (la columna admite 50)
- **THEN** entonces la respuesta es `422`, no `500`, y no se persiste ningún sillón

#### Scenario: Espacios recortados
- **WHEN** cuando una recepcionista autenticada envía `POST /prestaciones` con `{"nombre": "  Blanqueamiento ficticio  ", "duracion_min": 60}`
- **THEN** entonces la respuesta es `201` con `nombre = "Blanqueamiento ficticio"`

#### Scenario: Matrícula vacía guardada como nula
- **GIVEN** dado un profesional ya registrado sin matrícula
- **WHEN** cuando una recepcionista autenticada envía `POST /profesionales` con `{"nombre": "Carla", "apellido": "Supuesta", "matricula": "  "}`
- **THEN** entonces la respuesta es `201` con `matricula = null` y ambos profesionales quedan persistidos sin matrícula

### Requirement: Identificadores naturales duplicados
El nombre de un sillón, el nombre de una prestación y la matrícula de un profesional MUST ser únicos, comparados tras quitar los espacios iniciales y finales. Un alta o una edición que repita uno de ellos MUST responder `409` con `{"detail": {"codigo": "recurso_duplicado", "campo": ...}}` sin persistir ni modificar nada (DD-26).

#### Scenario: Sillón con nombre repetido
- **GIVEN** dado el sillón "Sillón 1" ya registrado
- **WHEN** cuando una recepcionista autenticada envía `POST /sillones` con `{"nombre": " Sillón 1 "}`
- **THEN** entonces la respuesta es `409` con código `recurso_duplicado` y `campo = "nombre"`, y sigue existiendo un solo "Sillón 1"

#### Scenario: Matrícula repetida al editar
- **GIVEN** dados los profesionales A con matrícula "MN-0001" y B con matrícula "MN-0002"
- **WHEN** cuando una recepcionista autenticada envía `PATCH /profesionales/{id de B}` con `{"matricula": "MN-0001"}`
- **THEN** entonces la respuesta es `409` con código `recurso_duplicado` y `campo = "matricula"`, y B conserva "MN-0002"

#### Scenario: Prestación con nombre repetido
- **GIVEN** dada la prestación "Limpieza" ya registrada
- **WHEN** cuando una recepcionista autenticada envía `POST /prestaciones` con `{"nombre": "Limpieza", "duracion_min": 30}`
- **THEN** entonces la respuesta es `409` con código `recurso_duplicado` y `campo = "nombre"`, y sigue existiendo una sola prestación "Limpieza" con su duración original

### Requirement: Edición parcial de un recurso
El sistema SHALL exponer `PATCH /profesionales/{id}`, `PATCH /sillones/{id}` y `PATCH /prestaciones/{id}`, que responden `200` con el recurso. Un campo omitido MUST conservar su valor; un campo obligatorio informado con `null` MUST responder `422` sin modificar nada; `matricula` con `null` MUST quitar la matrícula. Los campos desconocidos MUST ignorarse.

#### Scenario: Solo un campo modificado
- **GIVEN** dado el profesional "Ana Ficticia" con matrícula "MN-0001"
- **WHEN** cuando una recepcionista autenticada envía `PATCH /profesionales/{id}` con `{"apellido": "Ficticia Segunda"}`
- **THEN** entonces la respuesta es `200` con `nombre = "Ana"`, `apellido = "Ficticia Segunda"` y `matricula = "MN-0001"`

#### Scenario: Cambio de requiere_sillon
- **GIVEN** dada la prestación "Control" con `requiere_sillon = false`
- **WHEN** cuando una recepcionista autenticada envía `PATCH /prestaciones/{id}` con `{"requiere_sillon": true}`
- **THEN** entonces la respuesta es `200` con `requiere_sillon = true` y la misma `duracion_min`

#### Scenario: Body vacío
- **GIVEN** dado el sillón "Sillón 2"
- **WHEN** cuando una recepcionista autenticada envía `PATCH /sillones/{id}` con `{}`
- **THEN** entonces la respuesta es `200` y el sillón sigue llamándose "Sillón 2"

#### Scenario: Campo desconocido ignorado
- **GIVEN** dado el sillón "Sillón 2"
- **WHEN** cuando una recepcionista autenticada envía `PATCH /sillones/{id}` con `{"color": "azul"}`
- **THEN** entonces la respuesta es `200` con `nombre = "Sillón 2"` y sin ningún campo `color`, y en la base el sillón no cambia

#### Scenario: Nulo explícito en un campo obligatorio
- **GIVEN** dada la prestación "Limpieza" con `duracion_min = 45`
- **WHEN** cuando una recepcionista autenticada envía `PATCH /prestaciones/{id}` con `{"nombre": null}`, o `{"duracion_min": null}`, o `{"requiere_sillon": null}`
- **THEN** entonces la respuesta es `422` y la prestación no cambia

#### Scenario: Quitar la matrícula
- **GIVEN** dado un profesional con matrícula "MN-0001"
- **WHEN** cuando una recepcionista autenticada envía `PATCH /profesionales/{id}` con `{"matricula": null}`
- **THEN** entonces la respuesta es `200` con `matricula = null`

#### Scenario: Recurso a editar inexistente
- **WHEN** cuando una recepcionista autenticada envía `PATCH /sillones/{id}` con un UUID que no corresponde a ningún sillón
- **THEN** entonces la respuesta es `404` con `{"detail": {"codigo": "recurso_inexistente", "recurso": "sillon"}}`

### Requirement: Estado de actividad no editable
El estado de actividad (`activo` en profesional y sillón, `activa` en prestación) MUST cambiar solo por el endpoint de desactivación. Si el body de un alta o de una edición lo incluye, con cualquier valor, el sistema MUST responder `422` con código `campo_no_editable` y la lista de campos rechazados, sin persistir ni modificar nada (DD-26).

#### Scenario: Reactivación por edición rechazada
- **GIVEN** dado un sillón desactivado
- **WHEN** cuando una recepcionista autenticada envía `PATCH /sillones/{id}` con `{"activo": true}`
- **THEN** entonces la respuesta es `422` con código `campo_no_editable` y `campos = ["activo"]`, y el sillón sigue inactivo

#### Scenario: Alta inactiva rechazada
- **WHEN** cuando una recepcionista autenticada envía `POST /prestaciones` con `{"nombre": "Consulta de urgencia", "duracion_min": 30, "activa": false}`
- **THEN** entonces la respuesta es `422` con código `campo_no_editable` y `campos = ["activa"]`, y no se persiste ninguna prestación

### Requirement: Consulta de recursos
El sistema SHALL exponer `GET /profesionales`, `GET /sillones` y `GET /prestaciones`, que devuelven todos los recursos, activos e inactivos, con su estado de actividad: profesionales ordenados por apellido y nombre, sillones y prestaciones por nombre. `GET /{recurso}/{id}` MUST devolver uno; inexistente → `404`; identificador mal formado → `422`.

#### Scenario: Listado con inactivos y en orden
- **GIVEN** dados los sillones "Sillón 2" activo y "Sillón 1" desactivado
- **WHEN** cuando una recepcionista autenticada envía `GET /sillones`
- **THEN** entonces la respuesta es `200` con "Sillón 1" (`activo = false`) seguido de "Sillón 2" (`activo = true`)

#### Scenario: Profesionales por apellido
- **GIVEN** dados los profesionales "Zoe Alfa" y "Ana Beta"
- **WHEN** cuando se envía `GET /profesionales` autenticado
- **THEN** entonces "Zoe Alfa" aparece antes que "Ana Beta"

#### Scenario: Detalle de una prestación
- **GIVEN** dada la prestación "Consulta" de 30 minutos sin sillón
- **WHEN** cuando se envía `GET /prestaciones/{id}` autenticado
- **THEN** entonces la respuesta es `200` con `nombre = "Consulta"`, `duracion_min = 30`, `requiere_sillon = false` y `activa = true`

#### Scenario: Detalle inexistente
- **WHEN** cuando se envía `GET /profesionales/{id}` autenticado con un UUID que no corresponde a ningún profesional
- **THEN** entonces la respuesta es `404` con `{"detail": {"codigo": "recurso_inexistente", "recurso": "profesional"}}`

#### Scenario: Identificador mal formado
- **WHEN** cuando se envía `GET /prestaciones/no-es-un-id` autenticado
- **THEN** entonces la respuesta es `422`

### Requirement: Desactivación lógica de un recurso
El sistema SHALL exponer `POST /profesionales/{id}/desactivar`, `POST /sillones/{id}/desactivar` y `POST /prestaciones/{id}/desactivar`, que marcan el recurso como inactivo sin borrarlo y responden `200` con el recurso. Desactivar un recurso ya inactivo MUST responder `200` sin cambios. Un recurso inexistente MUST responder `404`. Desactivar un profesional MUST NOT modificar al usuario `odontologo` vinculado (DD-26).

#### Scenario: Sillón desactivado
- **GIVEN** dado el sillón "Sillón 1" activo
- **WHEN** cuando una recepcionista autenticada envía `POST /sillones/{id}/desactivar`
- **THEN** entonces la respuesta es `200` con `activo = false`, y en la base la fila del sillón sigue existiendo con `activo = false`

#### Scenario: Desactivación repetida
- **GIVEN** dada una prestación ya desactivada
- **WHEN** cuando una recepcionista autenticada envía `POST /prestaciones/{id}/desactivar`
- **THEN** entonces la respuesta es `200` con `activa = false` y la prestación no cambia

#### Scenario: Desactivar un recurso inexistente
- **WHEN** cuando una recepcionista autenticada envía `POST /profesionales/{id}/desactivar` con un UUID que no corresponde a ningún profesional
- **THEN** entonces la respuesta es `404` con `{"detail": {"codigo": "recurso_inexistente", "recurso": "profesional"}}`

#### Scenario: Usuario del profesional desactivado intacto
- **GIVEN** dado un odontólogo activo vinculado al profesional A
- **WHEN** cuando una recepcionista autenticada envía `POST /profesionales/{id de A}/desactivar`
- **THEN** entonces la respuesta es `200` y en la base el usuario del odontólogo sigue activo y vinculado al profesional A

#### Scenario: Recurso desactivado sigue consultable
- **GIVEN** dado un profesional desactivado
- **WHEN** cuando se envía `GET /profesionales/{id}` autenticado
- **THEN** entonces la respuesta es `200` con `activo = false`

### Requirement: Un recurso desactivado no admite turnos nuevos
Después de desactivar un profesional, un sillón o una prestación, un alta de turno o una reprogramación que lo referencie MUST responder `422` indicando la referencia inactiva, sin persistir ni modificar el turno (US-001, requisito "Referencias del body existentes y activas" de `agenda-turnos`).

#### Scenario: Alta con un sillón desactivado
- **GIVEN** dado el sillón 1 desactivado con `POST /sillones/{id}/desactivar`, un profesional, un paciente y la prestación "Limpieza" activos, y un horario futuro libre
- **WHEN** cuando una recepcionista autenticada envía `POST /turnos` con el sillón 1
- **THEN** entonces la respuesta es `422` con `{"detail": {"codigo": "referencia_invalida", "referencia": "sillon", "motivo": "inactiva"}}` y no se persiste ningún turno

#### Scenario: Alta con una prestación desactivada
- **GIVEN** dada la prestación "Limpieza" desactivada con `POST /prestaciones/{id}/desactivar`
- **WHEN** cuando una recepcionista autenticada envía `POST /turnos` con esa prestación y referencias activas para el resto
- **THEN** entonces la respuesta es `422` indicando la referencia `prestacion` con motivo `inactiva`, y no se persiste ningún turno

#### Scenario: Reprogramación hacia un profesional desactivado
- **GIVEN** dado un turno `programado` futuro del profesional A y el profesional B desactivado con `POST /profesionales/{id}/desactivar`
- **WHEN** cuando una recepcionista autenticada lo reprograma informando `profesional_id` de B
- **THEN** entonces la respuesta es `422` indicando la referencia `profesional` y el turno sigue con el profesional A

### Requirement: Un recurso desactivado conserva sus turnos
Desactivar un recurso MUST NOT modificar, cancelar ni borrar los turnos que lo referencian, sean pasados o futuros: conservan su referencia, su estado y su horario, y un turno `programado` futuro MUST poder cancelarse igual (US-001, DD-08, DD-26).

#### Scenario: Turno futuro intacto tras desactivar su profesional
- **GIVEN** dado un turno `programado` futuro del profesional A en el sillón 1 de 10:00 a 10:45
- **WHEN** cuando una recepcionista autenticada desactiva al profesional A
- **THEN** entonces la respuesta es `200` y en la base el turno sigue `programado`, con el profesional A, el sillón 1 y el horario de 10:00 a 10:45

#### Scenario: Cancelación de un turno cuyo sillón fue desactivado
- **GIVEN** dado un turno `programado` futuro en el sillón 1 y el sillón 1 desactivado
- **WHEN** cuando una recepcionista autenticada envía `POST /turnos/{id}/cancelar`
- **THEN** entonces la respuesta es `200` con `estado = cancelado`

#### Scenario: Turno cancelado intacto tras desactivar su prestación
- **GIVEN** dado un turno cancelado de la prestación "Limpieza" con su motivo
- **WHEN** cuando una recepcionista autenticada desactiva la prestación "Limpieza"
- **THEN** entonces el turno sigue cancelado, con la misma prestación y el mismo motivo

### Requirement: Editar una prestación no altera los turnos existentes
Cambiar la `duracion_min` o el `requiere_sillon` de una prestación MUST NOT modificar la duración, el horario ni el sillón de los turnos ya registrados con ella; la nueva duración MUST aplicarse solo como valor por defecto de los turnos que se creen después (RN-AG-04).

#### Scenario: Nueva duración por defecto
- **GIVEN** dado un turno futuro de la prestación "Limpieza" (45 min) de 10:00 a 10:45
- **WHEN** cuando una recepcionista autenticada cambia la `duracion_min` de "Limpieza" a 60 y luego crea otro turno de "Limpieza" a las 15:00 sin informar duración
- **THEN** entonces el primer turno sigue de 10:00 a 10:45 con `duracion_min = 45`, y el nuevo queda de 15:00 a 16:00 con `duracion_min = 60`

### Requirement: Desactivación simultánea con un alta o una reprogramación de turno
Una desactivación y un alta o reprogramación de turno simultáneas sobre el mismo recurso MUST quedar serializadas: la que toma el recurso primero hace esperar a la otra. Si confirma antes el turno, conserva el recurso; si confirma antes la desactivación, el alta o la reprogramación MUST responder `422`. Nunca MUST quedar un turno con una referencia ya inactiva al confirmarse.

#### Scenario: Alta que espera a una desactivación en curso
- **GIVEN** dada una transacción que desactivó el sillón 1 y todavía no confirmó
- **WHEN** cuando en paralelo se crea un turno con el sillón 1 y después se confirma la desactivación
- **THEN** entonces el alta espera a la desactivación y responde `422` indicando la referencia `sillon`, y no se persiste ningún turno

#### Scenario: Desactivación que espera a un alta en curso
- **GIVEN** dada un alta de turno con el sillón 1 que ya validó sus referencias y todavía no confirmó
- **WHEN** cuando en paralelo se desactiva el sillón 1 y después se confirma el alta
- **THEN** entonces la desactivación no termina mientras el alta no confirma (queda esperando el lock de la fila del sillón 1); al confirmarse el alta, la desactivación responde `200`, el turno queda persistido con el sillón 1 y el sillón 1 queda inactivo

#### Scenario: Reprogramación que espera a una desactivación en curso
- **GIVEN** dado un turno `programado` futuro en el sillón 2 y una transacción que desactivó el sillón 1 y todavía no confirmó
- **WHEN** cuando en paralelo se reprograma ese turno informando `sillon_id` del sillón 1 y después se confirma la desactivación
- **THEN** entonces la reprogramación espera a la desactivación y responde `422` indicando la referencia `sillon`, y el turno sigue en el sillón 2 con su horario original

### Requirement: Escritura de recursos reservada a la recepcionista
Alta, edición y desactivación de profesionales, sillones y prestaciones MUST exigir un usuario autenticado con rol `recepcionista` (RN-AU-03, DD-05, DD-24). Un `odontologo` MUST recibir `403` con `{"detail": {"codigo": "rol_insuficiente", "mensaje": "Rol insuficiente"}}`. Autenticación y rol MUST evaluarse antes que el body y que la existencia del recurso; ante `401` o `403` nada cambia.

#### Scenario: Odontólogo no puede dar de alta
- **GIVEN** dado un odontólogo autenticado
- **WHEN** cuando envía `POST /profesionales`, `POST /sillones` o `POST /prestaciones` con un body válido
- **THEN** entonces cada respuesta es `403` con código `rol_insuficiente` y no se persiste ningún recurso

#### Scenario: Odontólogo no puede editar ni desactivar
- **GIVEN** dado un odontólogo autenticado y el profesional vinculado a su usuario
- **WHEN** cuando envía `PATCH /profesionales/{id}` con un nuevo apellido, o `POST /profesionales/{id}/desactivar`, sobre su propio profesional
- **THEN** entonces ambas respuestas son `403` y el profesional no cambia y sigue activo

#### Scenario: Sin token en la escritura
- **WHEN** cuando se envía `POST /sillones` con un body válido sin encabezado `Authorization`
- **THEN** entonces la respuesta es `401` con `WWW-Authenticate: Bearer` y `{"detail": {"codigo": "no_autenticado", "mensaje": "No autenticado"}}`, y no se persiste ningún sillón

#### Scenario: Rol evaluado antes que el body
- **GIVEN** dado un odontólogo autenticado
- **WHEN** cuando envía `POST /sillones` con `{}` (sin `nombre`, un body que el schema rechaza), o `POST /prestaciones` con `{"nombre": "Control", "duracion_min": 7}` (que rechaza el dominio)
- **THEN** entonces cada respuesta es `403` con código `rol_insuficiente`, no `422`, y no se persiste ningún sillón ni ninguna prestación

#### Scenario: Rol evaluado antes que la existencia del recurso
- **GIVEN** dado un odontólogo autenticado
- **WHEN** cuando envía `POST /sillones/{id}/desactivar` con un UUID que no corresponde a ningún sillón
- **THEN** entonces la respuesta es `403`, no `404`

### Requirement: Lectura de recursos para ambos roles
Las consultas de profesionales, sillones y prestaciones MUST exigir un usuario autenticado, y MUST permitirse tanto a la `recepcionista` como al `odontologo`, que ve todos los recursos y no solo los propios (matriz de `03_actores_y_roles.md`, US-001). Sin token MUST responderse `401` antes que validar el path.

#### Scenario: Odontólogo lee el catálogo completo
- **GIVEN** dados dos profesionales, uno de ellos vinculado al usuario del odontólogo, y un odontólogo autenticado
- **WHEN** cuando envía `GET /profesionales`, `GET /sillones` y `GET /prestaciones`
- **THEN** entonces las tres respuestas son `200` y el listado de profesionales incluye a ambos

#### Scenario: Sin token en la lectura
- **WHEN** cuando se envía `GET /prestaciones` sin encabezado `Authorization`
- **THEN** entonces la respuesta es `401` con `WWW-Authenticate: Bearer`

#### Scenario: Autenticación evaluada antes que el path
- **WHEN** cuando se envía `GET /sillones/no-es-un-id` sin encabezado `Authorization`
- **THEN** entonces la respuesta es `401`, no `422`
