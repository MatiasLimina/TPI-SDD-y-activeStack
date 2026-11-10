## ADDED Requirements

### Requirement: Operaciones solo para la recepcionista
Crear, reprogramar y cancelar SHALL ofrecerse únicamente a `recepcionista` (`03_actores_y_roles.md`, RN-AU-02). Al `odontologo` MUST NOT mostrársele ningún control de esas operaciones. La autorización real sigue siendo de la API.

#### Scenario: Recepcionista
- **GIVEN** dada una sesión de `recepcionista` y un turno `programado` futuro
- **WHEN** cuando abre el detalle del turno
- **THEN** entonces se ven `Nuevo turno` en la agenda, y `Reprogramar` y `Cancelar turno` en el detalle

#### Scenario: Odontólogo
- **GIVEN** dada una sesión de `odontologo` y un turno `programado` futuro de su profesional
- **WHEN** cuando abre el detalle del turno
- **THEN** entonces no se ven `Nuevo turno`, `Reprogramar` ni `Cancelar turno`

### Requirement: Operaciones según el estado del turno
`Reprogramar` y `Cancelar turno` MUST ofrecerse solo para un turno `programado` cuyo `inicio` sea posterior al reloj (RN-AG-13, DD-23). Esta condición solo decide qué se muestra: la API sigue siendo la autoridad. Al elegir una, el detalle MUST cerrarse, y `Volver` o el éxito MUST llevar a la agenda (D6, DD-34).

#### Scenario: Turno cancelado
- **GIVEN** dada una recepcionista, un turno `cancelado` futuro y la casilla `Mostrar cancelados` activa
- **WHEN** cuando abre su detalle
- **THEN** entonces no se ven `Reprogramar` ni `Cancelar turno`

#### Scenario: Turno ya iniciado
- **GIVEN** dado el reloj en 2026-11-09 09:00 hora local y un turno `programado` con `inicio` a las 09:00 de ese día
- **WHEN** cuando la recepcionista abre su detalle
- **THEN** entonces no se ven `Reprogramar` ni `Cancelar turno`

#### Scenario: Turno por iniciar
- **GIVEN** dado el reloj en 2026-11-09 09:00 hora local y un turno `programado` con `inicio` a las 09:05 de ese día
- **WHEN** cuando la recepcionista abre su detalle
- **THEN** entonces se ven `Reprogramar` y `Cancelar turno`

#### Scenario: El detalle se cierra al abrir una operación
- **GIVEN** dada una recepcionista con el detalle abierto de un turno `programado` futuro
- **WHEN** cuando elige `Reprogramar`
- **THEN** entonces hay un solo diálogo abierto, el de la reprogramación

### Requirement: Formulario de nuevo turno
`Nuevo turno` SHALL abrir un formulario con profesional, paciente, prestación, sillón cuando corresponda, fecha, hora y duración opcional. Los selectores MUST ofrecer solo recursos activos (D9, DD-34; la API rechaza los inactivos, DD-21 c). La fecha MUST tomar por defecto la de la agenda y el profesional, el del filtro si está activo. Un campo obligatorio vacío MUST impedir el envío con un error propio. El formulario MUST usar `noValidate`: lo demás lo decide la API (D9, DD-34).

#### Scenario: Solo recursos activos
- **GIVEN** dados un profesional activo y uno desactivado, y la agenda filtrada por el desactivado
- **WHEN** cuando la recepcionista abre `Nuevo turno`
- **THEN** entonces el selector de profesional ofrece solo el activo y no tiene ninguno elegido

#### Scenario: Profesional del filtro
- **GIVEN** dada la agenda filtrada por un profesional activo
- **WHEN** cuando la recepcionista abre `Nuevo turno`
- **THEN** entonces el selector de profesional tiene elegido a ese profesional

#### Scenario: Fecha por defecto
- **GIVEN** dada la agenda en la fecha 2026-11-12
- **WHEN** cuando la recepcionista abre `Nuevo turno`
- **THEN** entonces el campo fecha vale `2026-11-12` y la hora está vacía

#### Scenario: Falta el paciente
- **GIVEN** dado un formulario con todo cargado menos el paciente
- **WHEN** cuando se envía
- **THEN** entonces se ve `Elegí un paciente.` y no se hace ningún `POST /turnos`

#### Scenario: Falta otro campo obligatorio
- **GIVEN** dado un formulario con todo cargado menos la hora
- **WHEN** cuando se envía
- **THEN** entonces el campo `Hora` muestra `Completá este campo.` y no se hace ningún `POST /turnos`

#### Scenario: Valores que decide la API
- **GIVEN** dado un formulario completo con fecha `2026-11-12`, hora `10:07` y duración `7`
- **WHEN** cuando se envía
- **THEN** entonces se hace el `POST /turnos`, con `inicio` igual a `2026-11-12T10:07:00-03:00` y `duracion_min` igual a `7`

### Requirement: Sillón según la prestación
El campo sillón MUST mostrarse y ser obligatorio solo si la prestación elegida tiene `requiere_sillon` verdadero (DD-09, RN-AG-10). Si no lo requiere, el pedido MUST NOT incluir `sillon_id`, aunque antes se hubiera elegido uno.

#### Scenario: Prestación que requiere sillón
- **GIVEN** dado un formulario completo con una prestación con `requiere_sillon` verdadero y el sillón sin elegir
- **WHEN** cuando se envía
- **THEN** entonces el campo `Sillón` se muestra con `Completá este campo.` y no se hace ningún `POST /turnos`

#### Scenario: Prestación que no requiere sillón
- **GIVEN** dado un formulario con un sillón elegido
- **WHEN** cuando se cambia a una prestación con `requiere_sillon` falso y se envía
- **THEN** entonces el campo `Sillón` no se muestra y el cuerpo del `POST /turnos` no incluye `sillon_id`

### Requirement: Duración por defecto y ajustable
El campo duración MUST ser opcional al crear e informar la duración de la prestación elegida como valor por defecto. Vacío, el pedido MUST NOT incluir `duracion_min`, y la API usa la de la prestación (RN-AG-04). Con un valor, MUST enviarlo.

#### Scenario: Duración de la prestación
- **GIVEN** dada la prestación "Limpieza" de 45 minutos elegida y la duración vacía
- **WHEN** cuando se envía el formulario
- **THEN** entonces se informa `Por defecto: 45 min` y el cuerpo no incluye `duracion_min`

#### Scenario: Duración ajustada
- **GIVEN** dada la prestación "Limpieza" de 45 minutos y la duración cargada en `60`
- **WHEN** cuando se envía el formulario
- **THEN** entonces el cuerpo incluye `duracion_min` igual a `60`

### Requirement: Inicio con zona horaria
La fecha y la hora ingresadas MUST interpretarse en `America/Argentina/Buenos_Aires` (en este spec, "hora local"; nunca la del navegador) y enviarse como instante con desfasaje explícito (RN-CU-04). El desfasaje MUST obtenerse de la zona IANA, no fijarse en el código (SU-08), y su cálculo MUST NOT lanzar una excepción aunque tenga segundos. El campo hora MUST ofrecer pasos de 5 minutos (DD-15).

#### Scenario: Navegador en otra zona horaria
- **GIVEN** dado un navegador en `Asia/Tokyo` y un formulario con fecha `2026-11-12` y hora `10:00`
- **WHEN** cuando se envía
- **THEN** entonces el cuerpo incluye `inicio` igual a `2026-11-12T10:00:00-03:00`

#### Scenario: Pasos de cinco minutos
- **WHEN** cuando se abre el formulario
- **THEN** entonces el campo `Hora` es de tipo hora con un paso de 300 segundos

#### Scenario: Fecha con otro desfasaje histórico
- **GIVEN** dada la fecha `2008-01-15` y la hora `10:00`
- **WHEN** cuando se calcula el instante
- **THEN** entonces el resultado es `2008-01-15T10:00:00-02:00`

#### Scenario: Fecha con el desfasaje actual
- **GIVEN** dada la fecha `2009-03-16` y la hora `10:00`
- **WHEN** cuando se calcula el instante
- **THEN** entonces el resultado es `2009-03-16T10:00:00-03:00`

#### Scenario: Fecha con desfasaje con segundos
- **GIVEN** dado un formulario con fecha `1900-01-15` y hora `10:00`, cuyo desfasaje en esa zona tiene segundos
- **WHEN** cuando se envía y la API responde `422` con `errores` para el campo `inicio`
- **THEN** entonces no hay una excepción sin controlar y el campo `Hora` muestra `Revisá este campo.`

### Requirement: Alta exitosa
Un envío válido MUST hacer un único `POST /turnos`. Ante un `201`, MUST cerrar el formulario, releer la agenda del período en curso y confirmar con el día y la hora del turno. Con un pedido en curso, MUST NOT enviarse otro.

#### Scenario: Turno creado
- **GIVEN** dado un formulario completo con paciente, profesional, prestación, sillón, fecha `2026-11-12` y hora `10:00`
- **WHEN** cuando se envía y la API responde `201`
- **THEN** entonces el formulario se cierra, se hace un `GET /turnos` nuevo y se ve `Turno creado para el 12/11 a las 10:00.`

#### Scenario: Doble envío
- **GIVEN** dado un `POST /turnos` sin responder
- **WHEN** cuando se intenta enviar otra vez
- **THEN** entonces el botón de envío está deshabilitado y hubo un solo `POST /turnos`

#### Scenario: Relectura fallida después del alta
- **GIVEN** dado un formulario completo y una agenda con datos en pantalla
- **WHEN** cuando se envía, la API responde `201` y el `GET /turnos` posterior falla por red
- **THEN** entonces el formulario se cierra, se ve la confirmación del turno creado y se ve `No se pudo conectar con el servidor.` junto con los datos anteriores

### Requirement: Búsqueda de pacientes
El selector de paciente SHALL buscar con `GET /pacientes` usando `q` y `limite=20`, 300 ms después de la última tecla y con al menos 2 caracteres sin contar espacios extremos; con menos MUST NOT pedir. MUST limitar la entrada a 100 caracteres (DD-31 e). El texto buscado MUST NOT figurar en la URL de la SPA.

#### Scenario: Búsqueda con espera
- **GIVEN** dado el selector de paciente abierto
- **WHEN** cuando se escribe `per` y pasan 300 ms sin escribir
- **THEN** entonces se hace un único `GET /pacientes` con `q=per` y `limite=20`

#### Scenario: Antes de la espera
- **GIVEN** dado el selector de paciente abierto
- **WHEN** cuando se escribe `per` y pasaron 299 ms
- **THEN** entonces no se hizo ningún pedido

#### Scenario: Texto demasiado corto
- **WHEN** cuando se escribe ` p ` y pasan 300 ms
- **THEN** entonces no se hace ningún pedido y se ve `Escribí al menos 2 caracteres.`

#### Scenario: Espacios extremos
- **WHEN** cuando se escribe ` pe ` y pasan 300 ms
- **THEN** entonces se hace un único `GET /pacientes` con `q=pe`

#### Scenario: Caracteres especiales
- **WHEN** cuando se escribe `Pérez & Cía` y pasan 300 ms
- **THEN** entonces el pedido codifica `q` en la URL de la API y la ruta de la SPA no contiene ese texto

### Requirement: Resultados de la búsqueda de pacientes
El selector MUST mostrar apellido, nombre y documento de cada resultado, en el orden de la API. Un paciente inactivo MUST verse identificado y no poder elegirse, porque la API lo rechaza (DD-21 c, DD-31 g). Sin resultados MUST informarlo, y con 20 resultados MUST sugerir refinar la búsqueda. Solo MUST mostrarse la respuesta de la última búsqueda.

#### Scenario: Elegir un paciente
- **GIVEN** dada una búsqueda con el resultado "Imaginaria, Carla", documento `00000104`
- **WHEN** cuando se lo elige
- **THEN** entonces el selector muestra a esa paciente y la acción `Cambiar paciente`, y el `POST /turnos` lleva su `paciente_id`

#### Scenario: Paciente inactivo
- **GIVEN** dada una búsqueda con un resultado con `activo` falso
- **WHEN** cuando se muestran los resultados
- **THEN** entonces se ve identificado como `Inactivo` y no se puede elegir

#### Scenario: Sin resultados
- **GIVEN** dada una respuesta `[]`
- **WHEN** cuando se muestran los resultados
- **THEN** entonces se ve `No se encontraron pacientes.`

#### Scenario: Muchos resultados
- **GIVEN** dada una respuesta con 20 pacientes
- **WHEN** cuando se muestran los resultados
- **THEN** entonces se ve `Hay más resultados: refiná la búsqueda.`

#### Scenario: Búsquedas fuera de orden
- **GIVEN** dada una búsqueda `per` sin responder y una posterior `pere` ya respondida
- **WHEN** cuando llega la respuesta de `per`
- **THEN** entonces se siguen viendo los resultados de `pere`

#### Scenario: Error de la búsqueda
- **GIVEN** dado que `GET /pacientes` falla por red
- **WHEN** cuando se muestran los resultados
- **THEN** entonces se ve `No se pudo conectar con el servidor.` y los demás datos del formulario se conservan

### Requirement: Formulario de reprogramación
`Reprogramar` SHALL abrir un formulario precargado con profesional, sillón cuando corresponda, fecha, hora y duración. Paciente y prestación MUST verse como texto, con la indicación de cancelar y crear otro turno, y MUST NOT enviarse (DD-23 b). Los selectores MUST ofrecer los recursos activos más el valor actual (D7). MUST usar `noValidate`: fecha, hora o sillón requerido vacíos MUST mostrar `Completá este campo.` y la duración vacía, `Ingresá la duración.`, sin pedido (D10, DD-34).

#### Scenario: Datos precargados
- **GIVEN** dado un turno `programado` del 2026-11-12 de 10:00 a 10:45 hora local
- **WHEN** cuando la recepcionista elige `Reprogramar`
- **THEN** entonces se ven fecha `2026-11-12`, hora `10:00` y duración `45`

#### Scenario: Paciente y prestación no editables
- **WHEN** cuando se abre el formulario de reprogramación
- **THEN** entonces paciente y prestación se ven como texto, sin controles editables, junto con `Para cambiarlos, cancelá este turno y creá uno nuevo.`

#### Scenario: Profesional desactivado
- **GIVEN** dado un turno cuyo profesional "Ana Ficticia" fue desactivado y otro profesional desactivado "Luis Inventado"
- **WHEN** cuando se abre el formulario de reprogramación
- **THEN** entonces el selector muestra `Ficticia, Ana (inactivo)` y no ofrece a `Inventado, Luis`

#### Scenario: Duración vaciada
- **GIVEN** dado el formulario de un turno de 45 minutos
- **WHEN** cuando se vacía la duración y se envía
- **THEN** entonces el campo `Duración` muestra `Ingresá la duración.` y no se hace ningún `PATCH`

#### Scenario: Hora y fecha vaciadas
- **GIVEN** dado el formulario de un turno
- **WHEN** cuando se vacían la hora y la fecha y se envía
- **THEN** entonces los campos `Hora` y `Fecha` muestran `Completá este campo.` y no se hace ningún `PATCH`

### Requirement: Reprogramación parcial
El `PATCH /turnos/{id}/reprogramar` MUST incluir solo los campos que cambiaron respecto del turno, porque lo omitido se conserva (DD-23 a), y MUST NOT incluir `paciente_id` ni `prestacion_id`. Los obligatorios MUST comprobarse antes de comparar. Sin cambios, MUST informarlo sin hacer ningún pedido. Si la prestación ya no requiere sillón y el turno tiene uno, MUST enviar `sillon_id` nulo solo junto con otro cambio (D10, DD-34).

#### Scenario: Solo cambia la hora
- **GIVEN** dado el formulario de un turno del 2026-11-12 a las 10:00 hora local con duración 45
- **WHEN** cuando se cambia la hora a `15:00` y se envía
- **THEN** entonces el cuerpo del `PATCH` es exactamente `{"inicio": "2026-11-12T15:00:00-03:00"}`

#### Scenario: Solo cambia el profesional
- **GIVEN** dado el formulario de un turno
- **WHEN** cuando se elige otro profesional y se envía
- **THEN** entonces el cuerpo del `PATCH` es exactamente `{"profesional_id": <id elegido>}`

#### Scenario: Solo cambia el sillón
- **GIVEN** dado el formulario de un turno con sillón
- **WHEN** cuando se elige otro sillón y se envía
- **THEN** entonces el cuerpo del `PATCH` es exactamente `{"sillon_id": <id elegido>}`

#### Scenario: Solo cambia la duración
- **GIVEN** dado el formulario de un turno de 45 minutos
- **WHEN** cuando se cambia la duración a `60` y se envía
- **THEN** entonces el cuerpo del `PATCH` es exactamente `{"duracion_min": 60}`

#### Scenario: Sin cambios
- **GIVEN** dado el formulario sin modificar de un turno con sus campos obligatorios completos
- **WHEN** cuando se envía
- **THEN** entonces se ve `No hiciste cambios.` y no se hace ningún `PATCH`

#### Scenario: Sin cambios con un sillón sobrante
- **GIVEN** dado un turno con sillón cuya prestación ahora tiene `requiere_sillon` falso (DD-26) y el formulario sin modificar
- **WHEN** cuando se envía
- **THEN** entonces se ve `No hiciste cambios.` y no se hace ningún `PATCH`

#### Scenario: Prestación que dejó de requerir sillón
- **GIVEN** dado un turno con sillón cuya prestación ahora tiene `requiere_sillon` falso (DD-26)
- **WHEN** cuando se cambia la hora y se envía
- **THEN** entonces el cuerpo del `PATCH` incluye `sillon_id` nulo y el nuevo `inicio`

#### Scenario: Prestación que pasó a requerir sillón
- **GIVEN** dado un turno sin sillón cuya prestación ahora tiene `requiere_sillon` verdadero (DD-26) y el formulario sin modificar
- **WHEN** cuando se envía
- **THEN** entonces el campo `Sillón` se muestra vacío con `Completá este campo.`, no se ve `No hiciste cambios.` y no se hace ningún `PATCH`

#### Scenario: Reprogramación exitosa
- **GIVEN** dado un formulario abierto desde el detalle, con un cambio válido
- **WHEN** cuando se envía y la API responde `200`
- **THEN** entonces no queda ningún diálogo abierto, se hace un `GET /turnos` nuevo y se ve `Turno reprogramado.`

### Requirement: Cancelación con confirmación
`Cancelar turno` SHALL pedir confirmación, mostrando paciente, día y hora, y un motivo opcional de hasta 255 caracteres. Solo al confirmar MUST hacerse `POST /turnos/{id}/cancelar`, con el motivo si no está en blanco y sin cuerpo si lo está. MUST poder desistirse sin hacer pedidos.

#### Scenario: Cancelar con motivo
- **GIVEN** dado el diálogo de cancelación de un turno y el motivo `Viaje`
- **WHEN** cuando se confirma y la API responde `200`
- **THEN** entonces el cuerpo es `{"motivo": "Viaje"}`, se hace un `GET /turnos` nuevo y se ve `Turno cancelado.`

#### Scenario: Cancelar sin motivo
- **GIVEN** dado el diálogo de cancelación con el motivo en blanco
- **WHEN** cuando se confirma
- **THEN** entonces el `POST /turnos/{id}/cancelar` se hace sin cuerpo

#### Scenario: Desistir
- **GIVEN** dado el diálogo de cancelación abierto desde el detalle
- **WHEN** cuando se elige `Volver`
- **THEN** entonces no queda ningún diálogo abierto y no se hace ningún pedido

#### Scenario: Motivo limitado
- **WHEN** cuando se abre el diálogo de cancelación
- **THEN** entonces el campo `Motivo` admite como máximo 255 caracteres

#### Scenario: Datos del turno en la confirmación
- **GIVEN** dado un turno de "Carla Imaginaria" el 2026-11-12 a las 10:00 hora local
- **WHEN** cuando se elige `Cancelar turno`
- **THEN** entonces el diálogo muestra `Imaginaria, Carla`, `12/11` y `10:00`

### Requirement: Conflicto por solapamiento
Un `409 solapamiento` MUST mostrarse como error del formulario, nombrando todos los recursos de `recursos` (DD-21 b), y MUST releer la agenda para que el conflicto quede visible.

#### Scenario: Un recurso en conflicto
- **GIVEN** dado un formulario enviado y una respuesta `409` con `{"detail": {"codigo": "solapamiento", "recursos": ["profesional"]}}`
- **WHEN** cuando se recibe la respuesta
- **THEN** entonces se ve `Ese horario ya está ocupado para el profesional.`

#### Scenario: Dos recursos en conflicto
- **GIVEN** dado un formulario enviado y una respuesta `409` con `recursos` `["profesional", "paciente"]`
- **WHEN** cuando se recibe la respuesta
- **THEN** entonces se ve `Ese horario ya está ocupado para el profesional y el paciente.`

#### Scenario: Todos los recursos en conflicto
- **GIVEN** dado un formulario enviado y una respuesta `409` con `recursos` `["profesional", "sillon", "paciente"]`
- **WHEN** cuando se recibe la respuesta
- **THEN** entonces se ve `Ese horario ya está ocupado para el profesional, el sillón y el paciente.`

#### Scenario: Relectura ante el conflicto
- **GIVEN** dado un formulario enviado
- **WHEN** cuando la API responde `409 solapamiento`
- **THEN** entonces el formulario sigue abierto y se hace un `GET /turnos` nuevo

### Requirement: Reglas de agenda rechazadas por la API
Los `422` de negocio MUST mostrarse en español, en su campo (`duracion_invalida`, `inicio_no_alineado`, `inicio_en_pasado`, `sillon_requerido`) o como error general (`fuera_de_horario`, `turno_en_bloqueo`, `sillon_no_corresponde`). Con `sillon_requerido`, el campo `Sillón` MUST mostrarse aunque el catálogo no lo pida. Ambos códigos de sillón MUST releer los catálogos (D7) y `turno_en_bloqueo`, la agenda (D13). Un `codigo` desconocido MUST mostrar el `mensaje` del error.

#### Scenario: Fuera de horario
- **GIVEN** dado un formulario enviado y una respuesta `422` con código `fuera_de_horario`
- **WHEN** cuando se recibe la respuesta
- **THEN** entonces se ve `El turno queda fuera del horario de atención del profesional.` como error general

#### Scenario: En un bloqueo
- **GIVEN** dado un formulario enviado y una respuesta `422` con código `turno_en_bloqueo`
- **WHEN** cuando se recibe la respuesta
- **THEN** entonces se ve `El turno se superpone con un bloqueo de la agenda del profesional.` como error general, el formulario sigue abierto y se hace un `GET /turnos` nuevo

#### Scenario: Inicio en el pasado
- **GIVEN** dado un formulario enviado y una respuesta `422` con código `inicio_en_pasado`
- **WHEN** cuando se recibe la respuesta
- **THEN** entonces el campo `Hora` muestra `El inicio no puede estar en el pasado.`

#### Scenario: Inicio no alineado
- **GIVEN** dado un formulario enviado y una respuesta `422` con código `inicio_no_alineado`
- **WHEN** cuando se recibe la respuesta
- **THEN** entonces el campo `Hora` muestra `El horario debe ser múltiplo de 5 minutos.`

#### Scenario: Duración inválida
- **GIVEN** dado un formulario enviado y una respuesta `422` con código `duracion_invalida`
- **WHEN** cuando se recibe la respuesta
- **THEN** entonces el campo `Duración` muestra `La duración debe ser múltiplo de 5, de 5 a 480 minutos.`

#### Scenario: Código desconocido
- **GIVEN** dado un formulario enviado y una respuesta `422` con `{"detail": {"codigo": "otro_codigo", "mensaje": "Mensaje de la API"}}`
- **WHEN** cuando se recibe la respuesta
- **THEN** entonces se ve `Mensaje de la API` como error general

#### Scenario: Sillón requerido con el catálogo desactualizado
- **GIVEN** dado un formulario con una prestación que según el catálogo no requiere sillón y una respuesta `422` con código `sillon_requerido`
- **WHEN** cuando se recibe la respuesta
- **THEN** entonces se piden otra vez los catálogos y el campo `Sillón` se muestra con `Esta prestación requiere un sillón.`

#### Scenario: Sillón que no corresponde con el catálogo desactualizado
- **GIVEN** dado un formulario con un sillón elegido y una respuesta `422` con código `sillon_no_corresponde`
- **WHEN** cuando se recibe la respuesta
- **THEN** entonces se ve `Esta prestación no usa sillón.` como error general y se piden otra vez los catálogos

### Requirement: Referencias inválidas
Un `422 referencia_invalida` MUST indicar el recurso según `referencia` y `motivo`, en su campo si existe y, si no, como error general (DD-21 c), y releer los catálogos. Salvo el paciente, el valor rechazado MUST seguir como opción hasta cambiarlo, marcado `(inactivo)` o, si no existe, con el texto genérico; el actual del turno, mientras lo sea (D9, DD-34). Al reprogramar con paciente o prestación inactivos, MUST indicar que el turno solo se puede cancelar (DD-26).

#### Scenario: Sillón inactivo
- **GIVEN** dado un formulario enviado con el sillón "Sillón 1" y una respuesta `422` con `{"detail": {"codigo": "referencia_invalida", "referencia": "sillon", "motivo": "inactiva"}}`
- **WHEN** cuando se recibe la respuesta
- **THEN** entonces el campo `Sillón` muestra `El sillón está inactivo.`, se piden otra vez los catálogos y sigue elegida la opción `Sillón 1 (inactivo)`

#### Scenario: Cambiar el valor rechazado
- **GIVEN** dado un formulario de `Nuevo turno` con la opción `Sillón 1 (inactivo)` tras un rechazo
- **WHEN** cuando se elige otro sillón activo
- **THEN** entonces la opción `Sillón 1 (inactivo)` deja de ofrecerse

#### Scenario: Valor rechazado que es el actual del turno
- **GIVEN** dado un formulario de reprogramación de un turno cuyo profesional "Ana Ficticia" fue desactivado y un rechazo `referencia_invalida` sobre ese profesional
- **WHEN** cuando se elige otro profesional activo
- **THEN** entonces la opción `Ficticia, Ana (inactivo)` se sigue ofreciendo

#### Scenario: Valor rechazado inexistente
- **GIVEN** dado un formulario enviado, una respuesta `422` con `referencia` `profesional` y `motivo` `inexistente`, y un catálogo releído que ya no incluye a ese profesional
- **WHEN** cuando se recibe la respuesta
- **THEN** entonces el campo `Profesional` muestra `El profesional no existe.` y sigue elegida la opción `Profesional no disponible`, sin `(inactivo)`

#### Scenario: Paciente inactivo al reprogramar
- **GIVEN** dado un formulario de reprogramación y una respuesta `422` con `referencia` `paciente` y `motivo` `inactiva`
- **WHEN** cuando se recibe la respuesta
- **THEN** entonces se ve `El paciente está inactivo: este turno no se puede reprogramar, pero sí cancelar.`

#### Scenario: Prestación inactiva al reprogramar
- **GIVEN** dado un formulario de reprogramación y una respuesta `422` con `referencia` `prestacion` y `motivo` `inactiva`
- **WHEN** cuando se recibe la respuesta
- **THEN** entonces se ve `La prestación está inactiva: este turno no se puede reprogramar, pero sí cancelar.`

### Requirement: Errores de validación por campo
Un `422` de validación MUST marcar cada campo identificado por `campo` y mapear `inicio` al campo hora. MUST mostrar textos propios en español y MUST NOT mostrar el `msg` de la API, que no es apto para mostrar (spec `frontend-cliente-http`). Un error con `campo` nulo o desconocido MUST mostrarse como error general.

#### Scenario: Error en un campo
- **GIVEN** dado un formulario enviado y un `422` con `errores` para el campo `duracion_min` y mensaje `Input should be a valid integer`
- **WHEN** cuando se recibe la respuesta
- **THEN** entonces el campo `Duración` muestra `Revisá este campo.` y no se ve `Input should be a valid integer`

#### Scenario: Error sin campo
- **GIVEN** dado un formulario enviado y un `422` con una entrada de `campo` nulo
- **WHEN** cuando se recibe la respuesta
- **THEN** entonces se ve `Revisá los datos ingresados.` como error general

### Requirement: Turno que cambió mientras se editaba
Un `409 turno_ya_cancelado`, un `409 turno_ya_iniciado` o un `404 turno_inexistente` MUST explicar que el turno ya no admite la operación, deshabilitar el envío, dejar solo la opción de cerrar y releer la agenda (DD-22, DD-23). MUST NOT reintentarse. Otro cambio ajeno no se detecta: rige la última escritura gana (D13, DD-34).

#### Scenario: Turno cancelado por otro usuario
- **GIVEN** dado un formulario de reprogramación y una respuesta `409` con código `turno_ya_cancelado`
- **WHEN** cuando se recibe la respuesta
- **THEN** entonces se ve `Este turno ya fue cancelado.`, el envío está deshabilitado y se hace un `GET /turnos` nuevo

#### Scenario: Turno ya iniciado
- **GIVEN** dado el diálogo de cancelación y una respuesta `409` con código `turno_ya_iniciado`
- **WHEN** cuando se recibe la respuesta
- **THEN** entonces se ve `Este turno ya inició: no se puede modificar.` y el envío está deshabilitado

#### Scenario: Turno inexistente
- **GIVEN** dado un formulario de reprogramación y una respuesta `404` con código `turno_inexistente`
- **WHEN** cuando se recibe la respuesta
- **THEN** entonces se ve `Este turno ya no existe.` y el envío está deshabilitado

#### Scenario: Última escritura gana
- **GIVEN** dado un formulario de reprogramación abierto y un cambio de profesional hecho por otro usuario
- **WHEN** cuando se cambia solo la hora, se envía y la API responde `200`
- **THEN** entonces el `PATCH` lleva solo `inicio` y la relectura muestra el profesional que cargó el otro usuario

### Requirement: Conservación de los datos ante un error
Ante cualquier error de envío, el formulario MUST seguir abierto con todos los datos cargados, y MUST permitir corregirlos y volver a enviar, salvo en un turno que cambió. Los errores previos MUST limpiarse al reenviar. Si falla la relectura de catálogos que sigue a un error, el formulario MUST seguir abierto y mostrar ese error como general (D7, DD-34).

#### Scenario: Datos conservados tras un conflicto
- **GIVEN** dado un formulario completo con paciente elegido y una respuesta `409 solapamiento`
- **WHEN** cuando se recibe la respuesta
- **THEN** entonces paciente, profesional, prestación, sillón, fecha, hora y duración siguen cargados

#### Scenario: Reenvío exitoso
- **GIVEN** dado un formulario con un error de conflicto en pantalla
- **WHEN** cuando se cambia la hora, se reenvía y la API responde `201`
- **THEN** entonces hubo un segundo `POST /turnos` y el formulario se cierra

#### Scenario: Reenvío con otro error
- **GIVEN** dado un formulario con `Ese horario ya está ocupado para el profesional.` en pantalla
- **WHEN** cuando se cambia la hora, se reenvía y la API responde `422` con código `fuera_de_horario`
- **THEN** entonces se ve `El turno queda fuera del horario de atención del profesional.` y ya no se ve el error anterior

#### Scenario: Relectura de catálogos fallida con el formulario abierto
- **GIVEN** dado un formulario enviado, una respuesta `422 referencia_invalida` sobre el sillón y un `GET /sillones` posterior que falla por red
- **WHEN** cuando se recibe el error de la relectura
- **THEN** entonces el formulario sigue abierto con sus datos, `No se pudo conectar con el servidor.` se ve como error general y no se ve la acción `Reintentar`

### Requirement: Falta de permiso y fallas de red
Un `403` MUST mostrar `No tenés permiso para esta operación.` sin cerrar la sesión (DD-33 a, e). Una falla de red o un error sin `codigo` MUST mostrar el `mensaje` del error. Ambos MUST conservar el formulario abierto. Un `401 no_autenticado` lo resuelve la sesión (DD-33 d).

#### Scenario: Rol desactualizado
- **GIVEN** dada una sesión con rol `recepcionista` en el token y un `POST /turnos` que responde `403` con código `rol_insuficiente`
- **WHEN** cuando se recibe la respuesta
- **THEN** entonces se ve `No tenés permiso para esta operación.`, el token sigue guardado y el formulario sigue abierto

#### Scenario: Sin conexión
- **GIVEN** dado un `POST /turnos` que falla por red
- **WHEN** cuando se recibe el error
- **THEN** entonces se ve `No se pudo conectar con el servidor.` y los datos siguen cargados

#### Scenario: Sesión vencida al enviar
- **GIVEN** dado un `POST /turnos` que responde `401 no_autenticado` con el token vigente
- **WHEN** cuando se recibe la respuesta
- **THEN** entonces se muestra `/login` con el aviso de sesión vencida

### Requirement: Accesibilidad de los formularios
Los formularios MUST abrirse como diálogos modales (`showModal`), con título y campos etiquetados, y MUST poder completarse y enviarse con el teclado. Un error de campo MUST asociarse a su control y marcarlo como inválido; un error general MUST anunciarse como alerta. Cerrar con `Esc` MUST dejar el diálogo listo para abrirse otra vez.

#### Scenario: Error asociado a su campo
- **GIVEN** dado un error del servidor en el campo `Duración`
- **WHEN** cuando se muestra
- **THEN** entonces el control tiene `aria-invalid` verdadero y su descripción accesible es el mensaje de error

#### Scenario: Error general
- **GIVEN** dado un `409 solapamiento`
- **WHEN** cuando se muestra el error
- **THEN** entonces está en un elemento con rol `alert`

#### Scenario: Selector de paciente con teclado
- **GIVEN** dado un selector de paciente con resultados
- **WHEN** cuando se llega con Tab a un resultado y se presiona Enter
- **THEN** entonces queda elegido ese paciente y no se hizo ningún `POST /turnos`

#### Scenario: Enter en el campo de búsqueda
- **GIVEN** dado un formulario con el campo de búsqueda de paciente enfocado
- **WHEN** cuando se presiona Enter
- **THEN** entonces no se hizo ningún `POST /turnos`

#### Scenario: Diálogo con título
- **WHEN** cuando se abre `Nuevo turno`
- **THEN** entonces hay un diálogo cuyo nombre accesible es `Nuevo turno`

#### Scenario: Apertura modal
- **WHEN** cuando se abre `Nuevo turno`
- **THEN** entonces el diálogo se abrió con `showModal`

#### Scenario: Cierre con Esc
- **GIVEN** dado un diálogo abierto
- **WHEN** cuando el diálogo recibe los eventos `cancel` y `close` y se elige otra vez la acción que lo abre
- **THEN** entonces el diálogo vuelve a abrirse
