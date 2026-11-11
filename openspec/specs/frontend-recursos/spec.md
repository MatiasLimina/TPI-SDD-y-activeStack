# frontend-recursos Specification

## Purpose
Secciones de `/configuracion` con las que la recepcionista gestiona profesionales, sillones y prestaciones desde la SPA (US-001, RN-AU-03), sobre el contrato de `gestion-recursos` (DD-26).

## Requirements

### Requirement: Secciones de la configuración
`/configuracion` SHALL reemplazar su entrada del historial por `/configuracion/profesionales`. Cada sección (`profesionales`, `sillones`, `prestaciones` y `horarios`) MUST tener su propia ruta y una navegación interna con los enlaces `Profesionales`, `Sillones`, `Prestaciones` y `Horarios`, con la sección actual marcada como página actual (design D2). Una sección inexistente MUST mostrar la página no encontrada.

#### Scenario: Entrada por /configuracion
- **GIVEN** dada una sesión de `recepcionista`
- **WHEN** cuando navega a `/configuracion`
- **THEN** entonces se muestra `/configuracion/profesionales`, reemplazando la entrada del historial, con el título `Configuración` y la sección de profesionales

#### Scenario: Cambio de sección
- **GIVEN** dada la sección de profesionales
- **WHEN** cuando la recepcionista elige `Prestaciones`
- **THEN** entonces se muestra `/configuracion/prestaciones`, el enlace `Prestaciones` tiene `aria-current="page"` y se hizo `GET /prestaciones`

#### Scenario: Sección inexistente
- **GIVEN** dada una sesión de `recepcionista`
- **WHEN** cuando navega a `/configuracion/usuarios`
- **THEN** entonces se ve la pantalla de página no encontrada

### Requirement: Listado de profesionales
La sección de profesionales SHALL listar todos los profesionales de `GET /profesionales`, activos e inactivos, en el orden de la API (apellido y nombre), con su nombre como `Apellido, Nombre`, su matrícula (`Sin matrícula` si es nula) y su estado.

#### Scenario: Profesionales con y sin matrícula
- **GIVEN** dada una respuesta de `GET /profesionales` con "Ana Ficticia" (matrícula "MN-0001", activa) y "Luis Inventado" (sin matrícula, inactivo)
- **WHEN** cuando se muestra la sección
- **THEN** entonces hay una fila `Ficticia, Ana` con `MN-0001` y otra `Inventado, Luis` con `Sin matrícula` e `Inactivo`, en ese orden

### Requirement: Alta y edición de un profesional
El formulario de profesional SHALL tener `Nombre` y `Apellido` obligatorios y `Matrícula` opcional, y enviar `POST /profesionales` o `PATCH /profesionales/{id}`. Una matrícula repetida (`409 recurso_duplicado`, `campo` `matricula`) MUST marcar el campo `Matrícula` con `Ya existe un profesional con esa matrícula.` (DD-26 e). El éxito MUST avisar `Profesional guardado.`

#### Scenario: Alta de profesional
- **GIVEN** dado el formulario `Nuevo profesional` con `Ana`, `Ficticia` y `MN-0001`
- **WHEN** cuando se envía y la API responde `201`
- **THEN** entonces el `POST /profesionales` tiene cuerpo `{"nombre": "Ana", "apellido": "Ficticia", "matricula": "MN-0001"}` y se ve `Profesional guardado.`

#### Scenario: Matrícula repetida
- **GIVEN** dado el formulario de edición de "Luis Inventado"
- **WHEN** cuando se carga la matrícula `MN-0001`, se envía y la API responde `409` con `{"detail": {"codigo": "recurso_duplicado", "campo": "matricula"}}`
- **THEN** entonces el campo `Matrícula` muestra `Ya existe un profesional con esa matrícula.` y el diálogo sigue abierto

### Requirement: Sillones
La sección de sillones SHALL listar los sillones de `GET /sillones` con su nombre y su estado, y su formulario MUST tener solo `Nombre`, obligatorio. Un nombre repetido (`409 recurso_duplicado`, `campo` `nombre`) MUST marcar `Nombre` con `Ya existe un sillón con ese nombre.` El éxito MUST avisar `Sillón guardado.`

#### Scenario: Alta de sillón
- **GIVEN** dado el formulario `Nuevo sillón` con `Sillón 3`
- **WHEN** cuando se envía y la API responde `201`
- **THEN** entonces el `POST /sillones` tiene cuerpo `{"nombre": "Sillón 3"}` y se ve `Sillón guardado.`

#### Scenario: Nombre de sillón repetido
- **GIVEN** dado el formulario `Nuevo sillón` con `Sillón 1`
- **WHEN** cuando se envía y la API responde `409` con `{"detail": {"codigo": "recurso_duplicado", "campo": "nombre"}}`
- **THEN** entonces el campo `Nombre` muestra `Ya existe un sillón con ese nombre.`

### Requirement: Listado de prestaciones
La sección de prestaciones SHALL listar las prestaciones de `GET /prestaciones` con su nombre, su duración por defecto como `N min`, si requiere sillón (`Sí` o `No`) y su estado.

#### Scenario: Prestaciones con y sin sillón
- **GIVEN** dada una respuesta de `GET /prestaciones` con "Control" (30 min, sin sillón) y "Limpieza" (45 min, con sillón)
- **WHEN** cuando se muestra la sección
- **THEN** entonces la fila de "Control" muestra `30 min` y `No`, y la de "Limpieza" `45 min` y `Sí`

### Requirement: Alta y edición de una prestación
El formulario de prestación SHALL tener `Nombre` y `Duración (minutos)` obligatorios y la casilla `Requiere sillón`, marcada por defecto en el alta (DD-09). La duración MUST enviarse como número entero: un valor que, sin espacios en los extremos, no sea un entero (solo dígitos, con un signo `-` opcional; por ejemplo `32.5`, `32,5` o `abc` no lo son) MUST marcar `Duración (minutos)` con `Ingresá minutos enteros.` sin hacer ningún pedido, igual en el alta y en la edición. El rango y el múltiplo de 5 los decide la API (design D6, D15). `422 duracion_invalida` MUST marcar `Duración (minutos)` con `La duración debe ser múltiplo de 5, de 5 a 480 minutos.` (DD-15, DD-26 b); un nombre repetido, `Ya existe una prestación con ese nombre.` El éxito MUST avisar `Prestación guardada.`

#### Scenario: Alta con los valores por defecto
- **GIVEN** dado el formulario `Nueva prestación` recién abierto
- **WHEN** cuando se observa la casilla `Requiere sillón`
- **THEN** entonces está marcada

#### Scenario: Alta de prestación sin sillón
- **GIVEN** dado el formulario `Nueva prestación` con `Control`, duración `30` y `Requiere sillón` desmarcada
- **WHEN** cuando se envía y la API responde `201`
- **THEN** entonces el `POST /prestaciones` tiene cuerpo `{"nombre": "Control", "duracion_min": 30, "requiere_sillon": false}` y se ve `Prestación guardada.`

#### Scenario: Duración inválida
- **GIVEN** dado el formulario de alta con `Control` y duración `32`
- **WHEN** cuando se envía y la API responde `422` con `{"detail": {"codigo": "duracion_invalida", "mensaje": "..."}}`
- **THEN** entonces el campo `Duración (minutos)` muestra `La duración debe ser múltiplo de 5, de 5 a 480 minutos.` y el diálogo sigue abierto

#### Scenario: Duración con decimales
- **GIVEN** dado el formulario `Nueva prestación` con `Control` y duración `32.5`
- **WHEN** cuando se envía
- **THEN** entonces `Duración (minutos)` muestra `Ingresá minutos enteros.` y no se hizo ningún `POST /prestaciones`

#### Scenario: Duración no numérica en la edición
- **GIVEN** dada la prestación "Control" en edición
- **WHEN** cuando se cambia la duración a `abc` y se envía
- **THEN** entonces `Duración (minutos)` muestra `Ingresá minutos enteros.` y no se hizo ningún `PATCH /prestaciones/{id}`

#### Scenario: Cambio de requiere sillón
- **GIVEN** dada la prestación "Control" sin sillón en edición
- **WHEN** cuando se marca `Requiere sillón` y se envía
- **THEN** entonces el `PATCH /prestaciones/{id}` tiene cuerpo `{"requiere_sillon": true}`

#### Scenario: Nombre de prestación repetido
- **GIVEN** dado el formulario de alta con `Limpieza` y duración `30`
- **WHEN** cuando se envía y la API responde `409` con `{"detail": {"codigo": "recurso_duplicado", "campo": "nombre"}}`
- **THEN** entonces el campo `Nombre` muestra `Ya existe una prestación con ese nombre.`

### Requirement: Desactivación de un recurso
La confirmación para desactivar un profesional, un sillón o una prestación SHALL explicar que no admitirá turnos nuevos, que los turnos ya agendados no cambian y se pueden cancelar, y que no se puede reactivar (DD-26 d, g). Al confirmar MUST enviar `POST /{recurso}/{id}/desactivar` y avisar `Profesional desactivado.`, `Sillón desactivado.` o `Prestación desactivada.`

#### Scenario: Texto de la confirmación
- **GIVEN** dado el profesional "Ana Ficticia" activo
- **WHEN** cuando la recepcionista elige `Desactivar Ficticia, Ana`
- **THEN** entonces el diálogo nombra `Ficticia, Ana` y dice `No va a admitir turnos nuevos. Los turnos ya agendados no cambian y se pueden cancelar. No se puede reactivar.`

#### Scenario: Prestación desactivada
- **GIVEN** dada la confirmación para desactivar la prestación "Control"
- **WHEN** cuando se confirma y la API responde `200` con `activa = false`
- **THEN** entonces se hizo `POST /prestaciones/{id}/desactivar`, se ve `Prestación desactivada.` y se volvió a pedir `GET /prestaciones`
