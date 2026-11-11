## ADDED Requirements

### Requirement: Foco del selector de paciente
Al elegir un paciente, el foco MUST pasar a `Cambiar paciente`, y al elegir `Cambiar paciente` MUST volver al campo `Buscar paciente`, para que quien usa el teclado no lo pierda cuando desaparece el control enfocado. Al mostrarse por primera vez, el selector MUST NOT tomar el foco. El selector sigue siendo un campo con una lista de botones, sin navegación por flechas (D8 de C-15, DD-34).

#### Scenario: Foco tras elegir un paciente
- **GIVEN** dada una búsqueda con el resultado "Imaginaria, Carla" y el foco en ese resultado
- **WHEN** cuando se lo elige
- **THEN** entonces el foco queda en `Cambiar paciente` y no en el cuerpo de la página

#### Scenario: Foco tras cambiar de paciente
- **GIVEN** dado un selector con la paciente "Imaginaria, Carla" elegida
- **WHEN** cuando se elige `Cambiar paciente`
- **THEN** entonces el foco queda en el campo `Buscar paciente`

#### Scenario: Sin foco al mostrarse
- **WHEN** cuando se muestra el selector de paciente
- **THEN** entonces el campo `Buscar paciente` no tiene el foco

### Requirement: Esc en un campo de búsqueda
Con el foco en un campo de búsqueda dentro de un diálogo, `Esc` MUST cerrar el diálogo con una sola pulsación, y la acción nativa del campo (borrar su texto) MUST NOT ejecutarse antes. En los demás campos el diálogo MUST NOT intervenir: `Esc` sigue el comportamiento del navegador. Las demás teclas en el campo de búsqueda MUST NOT cerrar el diálogo (D6 de C-15, DD-34). La conducta en un navegador real es verificación manual.

#### Scenario: Esc en el campo de búsqueda
- **GIVEN** dado un diálogo abierto con el foco en un campo de búsqueda que contiene `per`
- **WHEN** cuando se presiona `Esc` una vez
- **THEN** entonces el diálogo se cierra una sola vez y la acción nativa de la tecla se cancela

#### Scenario: Esc en un campo de texto común
- **GIVEN** dado un diálogo abierto con el foco en un campo de texto que no es de búsqueda
- **WHEN** cuando se presiona `Esc`
- **THEN** entonces el diálogo no cancela el evento ni llama a `close()`; el comportamiento queda en manos del navegador

#### Scenario: Otra tecla en el campo de búsqueda
- **GIVEN** dado un diálogo abierto con el foco en un campo de búsqueda
- **WHEN** cuando se presiona la tecla `a`
- **THEN** entonces el diálogo sigue abierto

## MODIFIED Requirements

### Requirement: Reglas de agenda rechazadas por la API
Los `422` de negocio MUST mostrarse en español, en su campo (`duracion_invalida`, `inicio_no_alineado`, `inicio_en_pasado`, `sillon_requerido`) o como error general (`fuera_de_horario`, `turno_en_bloqueo`, `sillon_no_corresponde`). Con `sillon_requerido`, el campo `Sillón` MUST mostrarse aunque el catálogo no lo pida, solo para la prestación del envío rechazado (en el alta, la elegida; en la reprogramación, la del turno): con otra prestación que no lo requiere MUST ocultarse y el alta MUST NOT enviar `sillon_id`, y al volver a la rechazada MUST mostrarse otra vez. Otro error de sillón, como `referencia_invalida`, MUST marcar el campo sin forzarlo. `sillon_requerido` y `sillon_no_corresponde` MUST releer los catálogos (D7) y `turno_en_bloqueo`, la agenda (D13). Un `codigo` desconocido MUST mostrar el `mensaje` del error.

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

#### Scenario: Sillón forzado solo para la prestación rechazada
- **GIVEN** dado un alta con la prestación "Control", que según el catálogo no requiere sillón, rechazada con `422` `sillon_requerido`, y el campo `Sillón` visible
- **WHEN** cuando se elige otra prestación que no requiere sillón
- **THEN** entonces el campo `Sillón` no se muestra

#### Scenario: Vuelta a la prestación rechazada
- **GIVEN** dado un alta con la prestación "Control" rechazada con `422` `sillon_requerido`
- **WHEN** cuando se elige otra prestación y después otra vez "Control"
- **THEN** entonces el campo `Sillón` se muestra

#### Scenario: Otro error de sillón no fuerza el campo
- **GIVEN** dado un alta con una prestación que requiere sillón, rechazada con `422` `referencia_invalida` sobre el sillón, y el campo `Sillón` con `El sillón está inactivo.`
- **WHEN** cuando se elige una prestación que no requiere sillón y se envía otra vez
- **THEN** entonces el campo `Sillón` no se muestra y el `POST /turnos` no incluye `sillon_id`

#### Scenario: Sillón requerido al reprogramar
- **GIVEN** dado un formulario de reprogramación cuya prestación, según el catálogo, no requiere sillón, y una respuesta `422` con código `sillon_requerido`
- **WHEN** cuando se recibe la respuesta
- **THEN** entonces el campo `Sillón` se muestra con `Esta prestación requiere un sillón.`
