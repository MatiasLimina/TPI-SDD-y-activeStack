# Spec Delta

## Purpose

Permitir que la recepcionista registre, busque, edite y desactive lógicamente a los pacientes para asignarlos a turnos, y que el odontólogo lea solo los datos mínimos de los pacientes de sus turnos, sin exponer datos personales de más en errores ni logs.

## ADDED Requirements

### Requirement: Alta de paciente
El sistema SHALL exponer `POST /pacientes`, que recibe `nombre`, `apellido`, `documento`, `telefono` y `email` opcional, y responde `201` con `id`, `nombre`, `apellido`, `documento`, `telefono`, `email` y `activo`. Todo paciente nuevo MUST quedar activo (US-009).

#### Scenario: Paciente con email
- **GIVEN** dada una recepcionista autenticada
- **WHEN** cuando envía `POST /pacientes` con `{"nombre": "Carla", "apellido": "Imaginaria", "documento": "FIC-0101", "telefono": "+54 11 5555-0101", "email": "carla.imaginaria@example.com"}`
- **THEN** entonces la respuesta es `201` con un `id` nuevo, esos cinco valores y `activo = true`, y en la base existe el paciente activo con ese documento

#### Scenario: Paciente sin email
- **GIVEN** dada una recepcionista autenticada
- **WHEN** cuando envía `POST /pacientes` con `{"nombre": "Diego", "apellido": "Supuesto", "documento": "FIC-0102", "telefono": "+54 11 5555-0102"}`
- **THEN** entonces la respuesta es `201` con `email = null` y `activo = true`

#### Scenario: Respuesta sin datos clínicos
- **WHEN** cuando una recepcionista autenticada da de alta un paciente con un body válido
- **THEN** entonces las claves de la respuesta son exactamente `id`, `nombre`, `apellido`, `documento`, `telefono`, `email` y `activo`

### Requirement: Campos mínimos y textos normalizados
Los textos del body MUST guardarse sin espacios al principio ni al final. `nombre`, `apellido`, `documento` y `telefono` MUST ser obligatorios y no vacíos tras quitar esos espacios, y ningún texto MUST superar el largo de su columna (100, 100, 20, 30 y 254); si no, `422` sin persistir. Un `email` vacío o solo con espacios MUST quedar nulo. `documento` y `telefono` MUST NOT exigir un formato propio.

#### Scenario: Campo obligatorio faltante
- **WHEN** cuando una recepcionista autenticada envía `POST /pacientes` omitiendo, de a uno, `nombre`, `apellido`, `documento` o `telefono`
- **THEN** entonces cada respuesta es `422` y no se persiste ningún paciente

#### Scenario: Campo obligatorio solo con espacios
- **WHEN** cuando una recepcionista autenticada envía `POST /pacientes` con `"documento": "   "` y el resto válido
- **THEN** entonces la respuesta es `422` y no se persiste ningún paciente

#### Scenario: Texto más largo que su columna
- **WHEN** cuando una recepcionista autenticada envía `POST /pacientes` con un `documento` de 21 caracteres, o un `telefono` de 31, o un `nombre` de 101
- **THEN** entonces cada respuesta es `422`, no `500`, y no se persiste ningún paciente

#### Scenario: Texto con el largo máximo aceptado
- **WHEN** cuando una recepcionista autenticada envía `POST /pacientes` con un `documento` de 20 caracteres y un `telefono` de 30
- **THEN** entonces la respuesta es `201` con esos valores

#### Scenario: Espacios recortados
- **WHEN** cuando una recepcionista autenticada envía `POST /pacientes` con `"nombre": "  Elena  "`, `"documento": " FIC-0103 "` y el resto válido
- **THEN** entonces la respuesta es `201` con `nombre = "Elena"` y `documento = "FIC-0103"`

#### Scenario: Email en blanco guardado como nulo
- **WHEN** cuando una recepcionista autenticada envía `POST /pacientes` con `"email": "   "` y el resto válido
- **THEN** entonces la respuesta es `201` con `email = null`

#### Scenario: Documento y teléfono sin formato propio
- **WHEN** cuando una recepcionista autenticada envía `POST /pacientes` con `"documento": "30111222"` y `"telefono": "11 5555-0104"`, y otro alta con `"documento": "FIC-0104"` y `"telefono": "+54 (11) 5555 0105"`
- **THEN** entonces ambas respuestas son `201` y los valores quedan tal como se enviaron

#### Scenario: Carácter nulo rechazado
- **WHEN** cuando una recepcionista autenticada envía `POST /pacientes` con un `nombre` que contiene el carácter `U+0000`
- **THEN** entonces la respuesta es `422`, no `500`, y no se persiste ningún paciente

### Requirement: Formato mínimo del email
Un `email` informado MUST tener exactamente una `@`, con texto antes y después, y no contener espacios; si no, el alta o la edición MUST responder `422` sin persistir ni modificar nada. El email MUST guardarse como se envió, salvo los espacios extremos, y MUST NOT tener que ser único.

#### Scenario: Email sin arroba
- **WHEN** cuando una recepcionista autenticada envía `POST /pacientes` con `"email": "carla.example.com"` y el resto válido
- **THEN** entonces la respuesta es `422` y no se persiste ningún paciente

#### Scenario: Email con espacios internos o incompleto
- **WHEN** cuando una recepcionista autenticada envía `POST /pacientes` con `"email": "carla @example.com"`, o `"@example.com"`, o `"carla@"`, o `"carla@a@example.com"`
- **THEN** entonces cada respuesta es `422` y no se persiste ningún paciente

#### Scenario: Email repetido entre pacientes
- **GIVEN** dado un paciente con `email = "familia@example.com"`
- **WHEN** cuando una recepcionista autenticada da de alta a otro paciente, con otro documento y el mismo email
- **THEN** entonces la respuesta es `201` y ambos pacientes conservan ese email

#### Scenario: Edición con email inválido
- **GIVEN** dado un paciente con `email = "carla@example.com"`
- **WHEN** cuando una recepcionista autenticada envía `PATCH /pacientes/{id}` con `{"email": "no-es-un-email"}`
- **THEN** entonces la respuesta es `422` y en la base el paciente conserva `carla@example.com`

### Requirement: Documento único
El `documento` MUST ser único entre todos los pacientes, activos o no, comparado tras quitar los espacios extremos. Un alta o una edición que lo repita MUST responder `409` con `{"detail": {"codigo": "recurso_duplicado", "campo": "documento"}}` sin persistir ni modificar nada. Ante operaciones simultáneas, la restricción de la base MUST decidir y el perdedor MUST recibir ese mismo `409`.

#### Scenario: Alta con documento repetido
- **GIVEN** dado el paciente "Carla Imaginaria" con documento "FIC-0101"
- **WHEN** cuando una recepcionista autenticada envía `POST /pacientes` con `"documento": " FIC-0101 "` y otros datos válidos
- **THEN** entonces la respuesta es `409` con código `recurso_duplicado` y `campo = "documento"`, y sigue existiendo un solo paciente con ese documento

#### Scenario: Documento repetido al editar
- **GIVEN** dados los pacientes A con documento "FIC-0101" y B con documento "FIC-0102"
- **WHEN** cuando una recepcionista autenticada envía `PATCH /pacientes/{id de B}` con `{"documento": "FIC-0101"}`
- **THEN** entonces la respuesta es `409` con código `recurso_duplicado` y B conserva "FIC-0102"

#### Scenario: Documento de un paciente desactivado
- **GIVEN** dado un paciente desactivado con documento "FIC-0101"
- **WHEN** cuando una recepcionista autenticada envía `POST /pacientes` con `"documento": "FIC-0101"` y otros datos válidos
- **THEN** entonces la respuesta es `409` con código `recurso_duplicado` y no se persiste ningún paciente nuevo

#### Scenario: Altas simultáneas con el mismo documento
- **GIVEN** dada una transacción que insertó un paciente con documento "FIC-0101" y todavía no confirmó
- **WHEN** cuando en paralelo se envía `POST /pacientes` con ese documento y después se confirma la primera transacción
- **THEN** entonces el alta espera a la primera y responde `409` con código `recurso_duplicado` y `campo = "documento"`, no `500`, y existe un solo paciente con ese documento

### Requirement: Edición parcial de un paciente
El sistema SHALL exponer `PATCH /pacientes/{id}`, que responde `200` con el paciente. `nombre`, `apellido`, `documento`, `telefono` y `email` MUST poder editarse, también en un paciente desactivado. Un campo omitido MUST conservar su valor; un campo obligatorio con `null` MUST responder `422` sin modificar nada; `email` con `null` MUST quitarlo. Los campos desconocidos MUST ignorarse.

#### Scenario: Solo un campo modificado
- **GIVEN** dado el paciente "Carla Imaginaria" con teléfono "+54 11 5555-0101"
- **WHEN** cuando una recepcionista autenticada envía `PATCH /pacientes/{id}` con `{"telefono": "+54 11 5555-0199"}`
- **THEN** entonces la respuesta es `200` con el teléfono nuevo y el mismo `nombre`, `apellido`, `documento` y `email`

#### Scenario: Corrección del documento
- **GIVEN** dado un paciente con documento "FIC-0101" y un turno `programado` futuro
- **WHEN** cuando una recepcionista autenticada envía `PATCH /pacientes/{id}` con `{"documento": "FIC-0110"}`
- **THEN** entonces la respuesta es `200` con `documento = "FIC-0110"` y el turno sigue referenciando al mismo paciente, sin cambios

#### Scenario: Quitar el email
- **GIVEN** dado un paciente con email "carla@example.com"
- **WHEN** cuando una recepcionista autenticada envía `PATCH /pacientes/{id}` con `{"email": null}`
- **THEN** entonces la respuesta es `200` con `email = null`

#### Scenario: Nulo explícito en un campo obligatorio
- **GIVEN** dado un paciente con documento "FIC-0101"
- **WHEN** cuando una recepcionista autenticada envía `PATCH /pacientes/{id}` con `{"nombre": null}`, o `{"apellido": null}`, o `{"documento": null}`, o `{"telefono": null}`
- **THEN** entonces cada respuesta es `422` y el paciente no cambia

#### Scenario: Texto en blanco al editar
- **GIVEN** dado un paciente con teléfono "+54 11 5555-0101"
- **WHEN** cuando una recepcionista autenticada envía `PATCH /pacientes/{id}` con `{"telefono": "   "}`
- **THEN** entonces la respuesta es `422` y el paciente conserva su teléfono

#### Scenario: Body vacío
- **GIVEN** dado el paciente "Carla Imaginaria"
- **WHEN** cuando una recepcionista autenticada envía `PATCH /pacientes/{id}` con `{}`
- **THEN** entonces la respuesta es `200` y el paciente no cambia

#### Scenario: Campo desconocido ignorado
- **GIVEN** dado el paciente "Carla Imaginaria"
- **WHEN** cuando una recepcionista autenticada envía `PATCH /pacientes/{id}` con `{"obra_social": "Ficticia"}`
- **THEN** entonces la respuesta es `200`, sin ningún campo `obra_social`, y en la base el paciente no cambia

#### Scenario: Edición de un paciente desactivado
- **GIVEN** dado un paciente desactivado con teléfono "+54 11 5555-0101"
- **WHEN** cuando una recepcionista autenticada envía `PATCH /pacientes/{id}` con `{"telefono": "+54 11 5555-0199"}`
- **THEN** entonces la respuesta es `200` con el teléfono nuevo y `activo = false`

#### Scenario: Paciente a editar inexistente
- **WHEN** cuando una recepcionista autenticada envía `PATCH /pacientes/{id}` con un UUID que no corresponde a ningún paciente
- **THEN** entonces la respuesta es `404` con `{"detail": {"codigo": "recurso_inexistente", "recurso": "paciente"}}`

### Requirement: Estado de actividad del paciente no editable
`activo` MUST cambiar solo por el endpoint de desactivación. Si el body de un alta o de una edición lo incluye, con cualquier valor, el sistema MUST responder `422` con código `campo_no_editable` y `campos = ["activo"]`, sin persistir ni modificar nada (DD-26).

#### Scenario: Reactivación por edición rechazada
- **GIVEN** dado un paciente desactivado
- **WHEN** cuando una recepcionista autenticada envía `PATCH /pacientes/{id}` con `{"activo": true}`
- **THEN** entonces la respuesta es `422` con código `campo_no_editable` y `campos = ["activo"]`, y el paciente sigue inactivo

#### Scenario: Alta inactiva rechazada
- **WHEN** cuando una recepcionista autenticada envía `POST /pacientes` con un body válido y `"activo": false`
- **THEN** entonces la respuesta es `422` con código `campo_no_editable` y `campos = ["activo"]`, y no se persiste ningún paciente

### Requirement: Listado de pacientes
El sistema SHALL exponer `GET /pacientes`, que responde `200` con una lista de pacientes activos e inactivos, cada uno con `id`, `nombre`, `apellido`, `documento`, `telefono`, `email` y `activo`, ordenados por apellido, luego por nombre y luego por `id`.

#### Scenario: Listado con inactivos y en orden
- **GIVEN** dados los pacientes "Zoe Alfa" activo, "Ana Beta" desactivado y "Bruno Beta" activo
- **WHEN** cuando una recepcionista autenticada envía `GET /pacientes`
- **THEN** entonces la respuesta es `200` con "Zoe Alfa", "Ana Beta" (`activo = false`) y "Bruno Beta", en ese orden

#### Scenario: Sin pacientes registrados
- **GIVEN** dada una base sin pacientes
- **WHEN** cuando una recepcionista autenticada envía `GET /pacientes`
- **THEN** entonces la respuesta es `200` con una lista vacía

### Requirement: Búsqueda de pacientes
`GET /pacientes` MUST aceptar el parámetro opcional `q`, separado en términos por los espacios. Un paciente MUST aparecer si cada término es parte de su `nombre`, `apellido` o `documento`, sin distinguir mayúsculas ni acentos. `q` ausente o en blanco MUST listar sin filtrar; más de 100 caracteres o un carácter nulo MUST responder `422`. `%`, `_` y `\` MUST tomarse como texto literal.

#### Scenario: Coincidencia parcial por apellido
- **GIVEN** dados los pacientes "Carla Imaginaria" y "Diego Supuesto"
- **WHEN** cuando una recepcionista autenticada envía `GET /pacientes?q=magin`
- **THEN** entonces la respuesta es `200` con solo "Carla Imaginaria"

#### Scenario: Coincidencia parcial por nombre
- **GIVEN** dados los pacientes "Carla Imaginaria" y "Diego Supuesto"
- **WHEN** cuando una recepcionista autenticada envía `GET /pacientes?q=dieg`
- **THEN** entonces la respuesta es `200` con solo "Diego Supuesto"

#### Scenario: Coincidencia parcial por documento
- **GIVEN** dados los pacientes con documento "FIC-0101" y "FIC-0202"
- **WHEN** cuando una recepcionista autenticada envía `GET /pacientes?q=0202`
- **THEN** entonces la respuesta es `200` con solo el paciente de documento "FIC-0202"

#### Scenario: Sin distinguir mayúsculas
- **GIVEN** dado el paciente "Carla Imaginaria" con documento "FIC-0101"
- **WHEN** cuando una recepcionista autenticada envía `GET /pacientes?q=IMAGINARIA` y `GET /pacientes?q=fic-0101`
- **THEN** entonces ambas respuestas incluyen a "Carla Imaginaria"

#### Scenario: Sin distinguir acentos en ninguno de los dos sentidos
- **GIVEN** dados los pacientes "Lucía Pérez Ficticia" y "Tomás Nuñez Inventado"
- **WHEN** cuando una recepcionista autenticada envía `GET /pacientes?q=perez`, `GET /pacientes?q=PÉREZ` y `GET /pacientes?q=nunez`
- **THEN** entonces las dos primeras respuestas traen solo a "Lucía Pérez Ficticia" y la tercera solo a "Tomás Nuñez Inventado"

#### Scenario: Varios términos en campos distintos
- **GIVEN** dados los pacientes "Carla Imaginaria", "Carla Supuesta" y "Diego Imaginario"
- **WHEN** cuando una recepcionista autenticada envía `GET /pacientes?q=imag%20carla`
- **THEN** entonces la respuesta es `200` con solo "Carla Imaginaria"

#### Scenario: Sin coincidencias
- **WHEN** cuando una recepcionista autenticada envía `GET /pacientes?q=zzz-no-existe`
- **THEN** entonces la respuesta es `200` con una lista vacía

#### Scenario: Comodines tomados como texto
- **GIVEN** dados los pacientes con documento "FIC-0101" y "FIC_0102"
- **WHEN** cuando una recepcionista autenticada envía `GET /pacientes?q=%25`, `GET /pacientes?q=FIC_` y `GET /pacientes?q=%5C`
- **THEN** entonces la primera y la tercera respuesta son `200` con una lista vacía, y la segunda trae solo al paciente "FIC_0102"

#### Scenario: Paciente desactivado en la búsqueda
- **GIVEN** dado un paciente desactivado con documento "FIC-0101"
- **WHEN** cuando una recepcionista autenticada envía `GET /pacientes?q=FIC-0101`
- **THEN** entonces la respuesta es `200` e incluye a ese paciente con `activo = false`

#### Scenario: Búsqueda en blanco
- **GIVEN** dados dos pacientes
- **WHEN** cuando una recepcionista autenticada envía `GET /pacientes?q=%20%20`
- **THEN** entonces la respuesta es `200` con ambos pacientes

#### Scenario: Búsqueda demasiado larga
- **WHEN** cuando una recepcionista autenticada envía `GET /pacientes` con un `q` de 101 caracteres
- **THEN** entonces la respuesta es `422`

#### Scenario: Búsqueda con el largo máximo aceptado
- **WHEN** cuando una recepcionista autenticada envía `GET /pacientes` con un `q` de 100 caracteres
- **THEN** entonces la respuesta es `200`

#### Scenario: Búsqueda con carácter nulo
- **WHEN** cuando una recepcionista autenticada envía `GET /pacientes?q=a%00b`
- **THEN** entonces la respuesta es `422`, no `500`

### Requirement: Paginación del listado de pacientes
`GET /pacientes` MUST devolver como máximo `limite` pacientes, tras saltear `desplazamiento`, aplicados después del filtro y del orden. `limite` MUST valer `50` por defecto y estar entre `1` y `100`; `desplazamiento` MUST valer `0` por defecto y no ser negativo; si no, `422`.

#### Scenario: Límite por defecto
- **GIVEN** dados 51 pacientes
- **WHEN** cuando una recepcionista autenticada envía `GET /pacientes`
- **THEN** entonces la respuesta es `200` con los primeros 50 pacientes del orden

#### Scenario: Páginas sin repetidos
- **GIVEN** dados 5 pacientes con el mismo apellido y el mismo nombre
- **WHEN** cuando una recepcionista autenticada pide `limite=2` con `desplazamiento` 0, 2 y 4
- **THEN** entonces las tres respuestas traen 2, 2 y 1 pacientes, y entre todas aparecen los 5 una sola vez

#### Scenario: Paginación aplicada a la búsqueda
- **GIVEN** dados 3 pacientes de apellido "Imaginaria" y 2 de apellido "Supuesto"
- **WHEN** cuando una recepcionista autenticada envía `GET /pacientes?q=imaginaria&limite=2&desplazamiento=2`
- **THEN** entonces la respuesta es `200` con el tercer paciente de apellido "Imaginaria"

#### Scenario: Límite máximo aceptado
- **WHEN** cuando una recepcionista autenticada envía `GET /pacientes?limite=100`
- **THEN** entonces la respuesta es `200`

#### Scenario: Valores de paginación fuera de rango
- **WHEN** cuando una recepcionista autenticada envía `GET /pacientes` con `limite=0`, o `limite=101`, o `desplazamiento=-1`
- **THEN** entonces cada respuesta es `422`

### Requirement: Detalle de un paciente para la recepcionista
`GET /pacientes/{id}` MUST devolver a la recepcionista el paciente completo, activo o no, con `id`, `nombre`, `apellido`, `documento`, `telefono`, `email` y `activo`. Un paciente inexistente MUST responder `404` con `recurso_inexistente`; un identificador mal formado, `422`.

#### Scenario: Detalle completo
- **GIVEN** dado el paciente "Carla Imaginaria" con documento "FIC-0101"
- **WHEN** cuando una recepcionista autenticada envía `GET /pacientes/{id}`
- **THEN** entonces la respuesta es `200` con sus siete campos

#### Scenario: Detalle de un paciente desactivado
- **GIVEN** dado un paciente desactivado
- **WHEN** cuando una recepcionista autenticada envía `GET /pacientes/{id}`
- **THEN** entonces la respuesta es `200` con `activo = false`

#### Scenario: Detalle inexistente
- **WHEN** cuando una recepcionista autenticada envía `GET /pacientes/{id}` con un UUID que no corresponde a ningún paciente
- **THEN** entonces la respuesta es `404` con `{"detail": {"codigo": "recurso_inexistente", "recurso": "paciente"}}`

#### Scenario: Identificador mal formado
- **WHEN** cuando una recepcionista autenticada envía `GET /pacientes/no-es-un-id`
- **THEN** entonces la respuesta es `422`

### Requirement: Desactivación lógica de un paciente
El sistema SHALL exponer `POST /pacientes/{id}/desactivar`, que marca al paciente como inactivo sin borrarlo y responde `200` con el paciente. Desactivar uno ya inactivo MUST responder `200` sin cambios. Un paciente inexistente MUST responder `404` (DD-26).

#### Scenario: Paciente desactivado
- **GIVEN** dado un paciente activo
- **WHEN** cuando una recepcionista autenticada envía `POST /pacientes/{id}/desactivar`
- **THEN** entonces la respuesta es `200` con `activo = false`, y en la base la fila del paciente sigue existiendo con `activo = false` y con los mismos datos

#### Scenario: Desactivación repetida
- **GIVEN** dado un paciente ya desactivado
- **WHEN** cuando una recepcionista autenticada envía `POST /pacientes/{id}/desactivar`
- **THEN** entonces la respuesta es `200` con `activo = false` y el paciente no cambia

#### Scenario: Desactivar un paciente inexistente
- **WHEN** cuando una recepcionista autenticada envía `POST /pacientes/{id}/desactivar` con un UUID que no corresponde a ningún paciente
- **THEN** entonces la respuesta es `404` con `{"detail": {"codigo": "recurso_inexistente", "recurso": "paciente"}}`

### Requirement: Un paciente desactivado no admite turnos nuevos
Después de desactivar a un paciente, un alta de turno que lo referencie MUST responder `422` indicando la referencia inactiva, y reprogramar uno de sus turnos también MUST responder `422`, sin persistir ni modificar el turno (DD-21, DD-26).

#### Scenario: Alta con un paciente desactivado
- **GIVEN** dado un paciente desactivado con `POST /pacientes/{id}/desactivar`, y un profesional, un sillón y la prestación "Limpieza" activos en un horario futuro libre
- **WHEN** cuando una recepcionista autenticada envía `POST /turnos` con ese paciente
- **THEN** entonces la respuesta es `422` con `{"detail": {"codigo": "referencia_invalida", "referencia": "paciente", "motivo": "inactiva"}}` y no se persiste ningún turno

#### Scenario: Reprogramación del turno de un paciente desactivado
- **GIVEN** dado un turno `programado` futuro de un paciente que después fue desactivado
- **WHEN** cuando una recepcionista autenticada lo reprograma a otro horario libre
- **THEN** entonces la respuesta es `422` con código `referencia_invalida` y `referencia = "paciente"`, y el turno conserva su horario original

### Requirement: Un paciente desactivado conserva sus turnos y recordatorios
Desactivar a un paciente MUST NOT modificar, cancelar ni borrar sus turnos, pasados o futuros, ni sus recordatorios, y MUST NOT registrar auditoría de turnos. Un turno `programado` futuro MUST poder cancelarse igual, y su recordatorio pendiente MUST enviarse mientras el turno siga `programado` (DD-26).

#### Scenario: Turno futuro intacto
- **GIVEN** dado un turno `programado` futuro del paciente P con el profesional A de 10:00 a 10:45
- **WHEN** cuando una recepcionista autenticada desactiva al paciente P
- **THEN** entonces la respuesta es `200`, en la base el turno sigue `programado`, con el mismo paciente, profesional y horario, y no se agrega ninguna fila de auditoría de turnos

#### Scenario: Turno futuro cancelable
- **GIVEN** dado un turno `programado` futuro de un paciente desactivado
- **WHEN** cuando una recepcionista autenticada envía `POST /turnos/{id}/cancelar`
- **THEN** entonces la respuesta es `200` con `estado = cancelado`

#### Scenario: Recordatorio pendiente enviado igual
- **GIVEN** dado un turno `programado` futuro con su recordatorio `pendiente` y su paciente desactivado después de crearlo
- **WHEN** cuando llega el momento programado y el worker procesa el recordatorio
- **THEN** entonces el recordatorio sigue `pendiente` hasta ese momento y después queda `enviado`

### Requirement: Desactivación de paciente simultánea con un alta de turno
Una desactivación de paciente y un alta de turno simultáneas sobre el mismo paciente MUST quedar serializadas: la que toma al paciente primero hace esperar a la otra. Si confirma antes la desactivación, el alta MUST responder `422`; si confirma antes el alta, el turno se conserva. Nunca MUST confirmarse un turno con un paciente ya inactivo.

#### Scenario: Alta que espera a una desactivación en curso
- **GIVEN** dada una transacción que desactivó al paciente P y todavía no confirmó
- **WHEN** cuando en paralelo se crea un turno con el paciente P y después se confirma la desactivación
- **THEN** entonces el alta espera a la desactivación y responde `422` indicando la referencia `paciente`, y no se persiste ningún turno

#### Scenario: Desactivación que espera a un alta en curso
- **GIVEN** dada un alta de turno con el paciente P que ya validó sus referencias y todavía no confirmó
- **WHEN** cuando en paralelo se desactiva al paciente P y después se confirma el alta
- **THEN** entonces la desactivación no termina mientras el alta no confirma; al confirmarse el alta, la desactivación responde `200`, el turno queda persistido con el paciente P y el paciente P queda inactivo

### Requirement: Escritura de pacientes reservada a la recepcionista
Alta, edición y desactivación de pacientes MUST exigir un usuario autenticado con rol `recepcionista`. Un `odontologo` MUST recibir `403` con `{"detail": {"codigo": "rol_insuficiente", "mensaje": "Rol insuficiente"}}`. Autenticación y rol MUST evaluarse antes que el body y que la existencia del paciente; ante `401` o `403` nada cambia (DD-24).

#### Scenario: Odontólogo no puede escribir
- **GIVEN** dado un odontólogo autenticado y un paciente de uno de sus turnos
- **WHEN** cuando envía `POST /pacientes` con un body válido, `PATCH /pacientes/{id}` con un teléfono nuevo o `POST /pacientes/{id}/desactivar`
- **THEN** entonces cada respuesta es `403` con código `rol_insuficiente`, no se persiste ningún paciente y el existente no cambia

#### Scenario: Sin token en la escritura
- **WHEN** cuando se envía `POST /pacientes` con un body válido sin encabezado `Authorization`
- **THEN** entonces la respuesta es `401` con `WWW-Authenticate: Bearer` y `{"detail": {"codigo": "no_autenticado", "mensaje": "No autenticado"}}`, y no se persiste ningún paciente

#### Scenario: Rol evaluado antes que el body
- **GIVEN** dado un odontólogo autenticado
- **WHEN** cuando envía `POST /pacientes` con `{}`
- **THEN** entonces la respuesta es `403` con código `rol_insuficiente`, no `422`

#### Scenario: Rol evaluado antes que la existencia
- **GIVEN** dado un odontólogo autenticado
- **WHEN** cuando envía `POST /pacientes/{id}/desactivar` con un UUID que no corresponde a ningún paciente
- **THEN** entonces la respuesta es `403`, no `404`

### Requirement: Listado y búsqueda reservados a la recepcionista
`GET /pacientes` MUST exigir un usuario autenticado con rol `recepcionista`. Un `odontologo` MUST recibir `403 rol_insuficiente`, con o sin `q`, y la autenticación y el rol MUST evaluarse antes que los parámetros.

#### Scenario: Odontólogo no puede listar ni buscar
- **GIVEN** dado un odontólogo autenticado con pacientes en sus turnos
- **WHEN** cuando envía `GET /pacientes` y `GET /pacientes?q=imaginaria`
- **THEN** entonces ambas respuestas son `403` con código `rol_insuficiente` y ninguna incluye datos de pacientes

#### Scenario: Sin token en el listado
- **WHEN** cuando se envía `GET /pacientes` sin encabezado `Authorization`
- **THEN** entonces la respuesta es `401` con `WWW-Authenticate: Bearer`

#### Scenario: Rol evaluado antes que los parámetros
- **GIVEN** dado un odontólogo autenticado
- **WHEN** cuando envía `GET /pacientes?limite=0`
- **THEN** entonces la respuesta es `403`, no `422`

### Requirement: Lectura mínima del odontólogo
`GET /pacientes/{id}` MUST permitir a un `odontologo` leer a un paciente que tenga al menos un turno de su profesional, en cualquier estado y aunque el paciente esté desactivado. La respuesta MUST incluir exactamente `id`, `nombre` y `apellido`, y MUST NOT incluir `documento`, `telefono`, `email` ni `activo`.

#### Scenario: Paciente de un turno propio
- **GIVEN** dado un odontólogo autenticado y un turno `programado` de su profesional con el paciente "Carla Imaginaria"
- **WHEN** cuando envía `GET /pacientes/{id}`
- **THEN** entonces la respuesta es `200` y sus claves son exactamente `id`, `nombre` y `apellido`

#### Scenario: Paciente de un turno propio cancelado
- **GIVEN** dado un odontólogo autenticado y un paciente cuyo único turno con su profesional está cancelado
- **WHEN** cuando envía `GET /pacientes/{id}`
- **THEN** entonces la respuesta es `200` con solo `id`, `nombre` y `apellido`

#### Scenario: Paciente desactivado de un turno propio
- **GIVEN** dado un odontólogo autenticado y un paciente desactivado con un turno de su profesional
- **WHEN** cuando envía `GET /pacientes/{id}`
- **THEN** entonces la respuesta es `200` con solo `id`, `nombre` y `apellido`

### Requirement: Paciente ajeno para el odontólogo
Un `odontologo` que pida `GET /pacientes/{id}` de un paciente sin turnos de su profesional, exista o no, MUST recibir `403` con `{"detail": {"codigo": "paciente_ajeno", "mensaje": ...}}`, con el mismo cuerpo en ambos casos. Un identificador mal formado MUST responder `422`, y la falta de token, `401` antes que el path (DD-27).

#### Scenario: Paciente de otro profesional
- **GIVEN** dado un odontólogo autenticado y un paciente con turnos solo de otro profesional
- **WHEN** cuando envía `GET /pacientes/{id}`
- **THEN** entonces la respuesta es `403` con código `paciente_ajeno` y sin datos del paciente

#### Scenario: Paciente sin ningún turno
- **GIVEN** dado un odontólogo autenticado y un paciente sin turnos
- **WHEN** cuando envía `GET /pacientes/{id}`
- **THEN** entonces la respuesta es `403` con código `paciente_ajeno`

#### Scenario: Paciente inexistente indistinguible del ajeno
- **GIVEN** dado un odontólogo autenticado y un paciente con turnos solo de otro profesional
- **WHEN** cuando envía `GET /pacientes/{id}` con ese paciente y con un UUID que no corresponde a ningún paciente
- **THEN** entonces ambas respuestas son `403` y sus cuerpos son idénticos

#### Scenario: Identificador mal formado para el odontólogo
- **GIVEN** dado un odontólogo autenticado
- **WHEN** cuando envía `GET /pacientes/no-es-un-id`
- **THEN** entonces la respuesta es `422`

#### Scenario: Autenticación evaluada antes que el path
- **WHEN** cuando se envía `GET /pacientes/no-es-un-id` sin encabezado `Authorization`
- **THEN** entonces la respuesta es `401`, no `422`

### Requirement: Errores sin datos personales
Las respuestas de error de las rutas de `/pacientes` MUST NOT reproducir los valores enviados: un `422` de validación MUST indicar solo el campo y el motivo, y un `409` solo el campo en conflicto. Las rutas fuera de `/pacientes` MUST conservar su formato de `422`.

#### Scenario: Validación sin los datos enviados
- **WHEN** cuando una recepcionista autenticada envía `POST /pacientes` con `{"nombre": "Carla", "apellido": "Imaginaria", "documento": "FIC-0101"}`, sin `telefono`
- **THEN** entonces la respuesta es `422`, indica el campo `telefono` y su cuerpo no contiene "Carla", "Imaginaria" ni "FIC-0101"

#### Scenario: Valor inválido no reproducido
- **WHEN** cuando una recepcionista autenticada envía `POST /pacientes` con `"email": "no-es-un-email"` y el resto válido
- **THEN** entonces la respuesta es `422`, indica el campo `email` y su cuerpo no contiene "no-es-un-email"

#### Scenario: Búsqueda rechazada sin el texto enviado
- **WHEN** cuando una recepcionista autenticada envía `GET /pacientes` con un `q` de 101 caracteres
- **THEN** entonces la respuesta es `422` y su cuerpo no contiene ese texto

#### Scenario: Duplicado sin el documento
- **GIVEN** dado un paciente con documento "FIC-0101"
- **WHEN** cuando una recepcionista autenticada da de alta otro paciente con ese documento
- **THEN** entonces la respuesta es `409` y su cuerpo no contiene "FIC-0101" ni datos del paciente existente

#### Scenario: Otras rutas sin cambios
- **WHEN** cuando una recepcionista autenticada envía `POST /sillones` con `{}`
- **THEN** entonces la respuesta es `422` y conserva el formato por defecto de la API, incluido el dato `input`

### Requirement: Log de acceso sin el texto buscado
El log de acceso del servidor MUST registrar las rutas de `/pacientes` sin su query string, para que nombres y documentos buscados no queden en los logs. Las demás rutas MUST registrarse sin cambios.

#### Scenario: Búsqueda sin datos en el log
- **WHEN** cuando el servidor registra el acceso a `GET /pacientes?q=FIC-0101&limite=10`
- **THEN** entonces la línea del log contiene `/pacientes` y no contiene "FIC-0101"

#### Scenario: Otra ruta registrada completa
- **WHEN** cuando el servidor registra el acceso a `GET /bloqueos?profesional_id=00000000-0000-4000-8000-000000000101`
- **THEN** entonces la línea del log conserva la query string
