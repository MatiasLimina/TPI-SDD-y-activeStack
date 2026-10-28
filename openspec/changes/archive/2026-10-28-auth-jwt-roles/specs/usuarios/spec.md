# Spec Delta

## Purpose

Definir a los usuarios del sistema (recepcionista y odontólogo), las garantías de integridad que la base asegura sobre ellos y el comando de línea de comandos con el que se dan de alta y se desactivan, sin UI ni endpoint (DD-16).

## ADDED Requirements

### Requirement: Usuario del sistema
Un usuario SHALL tener `id` (uuid), `email`, hash de contraseña, `rol`, `profesional_id` opcional, `activo` (verdadero al crearse) y marcas de tiempo `timestamptz` en UTC. La base MUST garantizar: email único y guardado en minúsculas sin espacios, rol `recepcionista` u `odontologo`, `profesional_id` informado si y solo si el rol es `odontologo` y referido a un profesional existente, y a lo sumo un usuario activo por profesional (DD-24).

#### Scenario: Usuario válido persistido
- **WHEN** cuando se inserta un usuario `odontologo` con email `ana.ficticia@example.com`, un hash de contraseña y el `profesional_id` de un profesional existente
- **THEN** entonces la fila queda con `activo = true` y `creado_en` en UTC

#### Scenario: Rol inválido rechazado por la base
- **WHEN** cuando se inserta directamente un usuario con `rol = 'administrador'`
- **THEN** entonces la base rechaza la inserción con una violación de CHECK

#### Scenario: Vínculo con profesional incoherente rechazado por la base
- **WHEN** cuando se inserta directamente un `odontologo` sin `profesional_id`, o una `recepcionista` con `profesional_id`
- **THEN** entonces la base rechaza ambas inserciones con una violación de CHECK

#### Scenario: Email duplicado rechazado por la base
- **GIVEN** dado un usuario con email `recepcion@example.com`, activo o inactivo
- **WHEN** cuando se inserta directamente otro usuario con el mismo email
- **THEN** entonces la base rechaza la inserción con una violación de unicidad

#### Scenario: Email no normalizado rechazado por la base
- **WHEN** cuando se inserta directamente un usuario con email `Recepcion@Example.com`
- **THEN** entonces la base rechaza la inserción con una violación de CHECK

#### Scenario: Segundo usuario activo del mismo profesional
- **GIVEN** dado un `odontologo` activo vinculado al profesional A
- **WHEN** cuando se inserta otro `odontologo` activo vinculado al profesional A
- **THEN** entonces la base rechaza la inserción con una violación de unicidad; si el primero estuviera inactivo, la inserción se acepta

### Requirement: Contraseñas guardadas solo como hash
La contraseña de un usuario MUST guardarse únicamente como hash argon2id con sal aleatoria; MUST NOT guardarse ni mostrarse en claro. Al iniciar sesión con éxito, si el hash fue generado con parámetros distintos de los vigentes, el sistema MUST reemplazarlo por uno nuevo con los parámetros vigentes (DD-24).

#### Scenario: Hash argon2id
- **WHEN** cuando se da de alta un usuario con una contraseña ficticia
- **THEN** entonces el hash guardado empieza con `$argon2id$`, no contiene la contraseña y verifica contra ella

#### Scenario: Misma contraseña, hashes distintos
- **WHEN** cuando se dan de alta dos usuarios con la misma contraseña
- **THEN** entonces sus hashes guardados son distintos

#### Scenario: Hash con parámetros desactualizados
- **GIVEN** dado un usuario activo cuyo hash fue generado con parámetros de argon2 distintos de los vigentes
- **WHEN** cuando inicia sesión con su contraseña correcta
- **THEN** entonces la respuesta es `200`, el hash guardado cambia, sigue verificando contra la misma contraseña y usa los parámetros vigentes

### Requirement: Alta de usuario por línea de comandos
El sistema SHALL ofrecer `python -m app.cli usuarios alta --email <email> --rol <rol> [--profesional-id <uuid>]`. La contraseña MUST tomarse de la variable de entorno `USUARIO_PASSWORD` si está definida y no es vacía o, si no está definida, pedirse por consola sin eco y dos veces; definida y vacía es un alta inválida (DD-24). Un alta válida crea el usuario activo con el email normalizado, termina con código de salida `0` y no muestra la contraseña ni el hash.

#### Scenario: Alta de una recepcionista
- **GIVEN** dado `USUARIO_PASSWORD` definida con una contraseña ficticia no vacía
- **WHEN** cuando se ejecuta `usuarios alta --email recepcion2@example.com --rol recepcionista`
- **THEN** entonces el código de salida es `0`, existe un usuario activo `recepcionista` con ese email y sin profesional, y la salida no contiene la contraseña

#### Scenario: Alta de un odontólogo
- **GIVEN** dado un profesional activo B sin usuario activo y `USUARIO_PASSWORD` definida y no vacía
- **WHEN** cuando se ejecuta `usuarios alta --email bruno.ficticio@example.com --rol odontologo --profesional-id <id de B>`
- **THEN** entonces el código de salida es `0` y existe un usuario activo `odontologo` vinculado a B que puede iniciar sesión con esa contraseña

#### Scenario: Contraseña por consola
- **GIVEN** dado que `USUARIO_PASSWORD` no está definida
- **WHEN** cuando se ejecuta el alta y se ingresa la misma contraseña ficticia en los dos pedidos
- **THEN** entonces el código de salida es `0` y el usuario puede iniciar sesión con esa contraseña

#### Scenario: Email normalizado en el alta
- **WHEN** cuando se ejecuta el alta con `--email " Recepcion3@Example.com "`
- **THEN** entonces el usuario queda guardado con el email `recepcion3@example.com`

### Requirement: Rechazo de un alta inválida
El alta MUST terminar con código de salida distinto de `0`, un mensaje que indique la causa y sin crear ningún usuario si: el email ya existe (activo o inactivo) o no tiene la forma `algo@algo`; el rol no es `recepcionista` ni `odontologo`; falta `--profesional-id` para un odontólogo o se informa para una recepcionista; el profesional no existe, está inactivo o ya tiene un usuario activo; `USUARIO_PASSWORD` está definida pero vacía; la contraseña ingresada por consola es vacía o sus dos ingresos no coinciden (DD-16, DD-24).

#### Scenario: Email ya registrado
- **GIVEN** dado un usuario inactivo con email `ana.ficticia@example.com`
- **WHEN** cuando se ejecuta el alta con ese mismo email
- **THEN** entonces el código de salida es distinto de `0`, el mensaje indica que el email ya existe y el usuario existente sigue inactivo

#### Scenario: Email sin forma válida
- **WHEN** cuando se ejecuta `usuarios alta --email sin-arroba --rol recepcionista`
- **THEN** entonces el código de salida es distinto de `0` y no se crea ningún usuario

#### Scenario: Odontólogo sin profesional
- **WHEN** cuando se ejecuta `usuarios alta --email x@example.com --rol odontologo` sin `--profesional-id`
- **THEN** entonces el código de salida es distinto de `0` y no se crea ningún usuario

#### Scenario: Recepcionista con profesional
- **WHEN** cuando se ejecuta el alta con `--rol recepcionista` y `--profesional-id` de un profesional existente
- **THEN** entonces el código de salida es distinto de `0` y no se crea ningún usuario

#### Scenario: Profesional inexistente o inactivo
- **WHEN** cuando se ejecuta el alta de un odontólogo con un `--profesional-id` que no existe, o con el de un profesional inactivo
- **THEN** entonces el código de salida es distinto de `0` y no se crea ningún usuario en ninguno de los dos casos

#### Scenario: Profesional con usuario activo
- **GIVEN** dado un profesional activo A que ya tiene un usuario `odontologo` activo
- **WHEN** cuando se ejecuta el alta de otro odontólogo con `--email otro.ficticio@example.com --rol odontologo --profesional-id <id de A>`
- **THEN** entonces el código de salida es distinto de `0`, no se crea ningún usuario nuevo y el usuario existente sigue activo

#### Scenario: Rol inválido
- **WHEN** cuando se ejecuta el alta con `--rol administrador`
- **THEN** entonces el código de salida es distinto de `0` y no se crea ningún usuario

#### Scenario: Contraseña vacía o confirmación distinta
- **GIVEN** dado que `USUARIO_PASSWORD` no está definida
- **WHEN** cuando se ejecuta el alta ingresando una contraseña vacía, o dos contraseñas distintas
- **THEN** entonces el código de salida es distinto de `0` y no se crea ningún usuario en ninguno de los dos casos

#### Scenario: USUARIO_PASSWORD definida y vacía
- **GIVEN** dado `USUARIO_PASSWORD` definida con el valor `""`
- **WHEN** cuando se ejecuta `usuarios alta --email recepcion4@example.com --rol recepcionista`
- **THEN** entonces el código de salida es distinto de `0`, no se crea ningún usuario y no se pide la contraseña por consola

### Requirement: Contraseña nunca como argumento
El comando MUST NOT aceptar la contraseña como argumento de línea de comandos, para que no quede en el historial del shell ni en la lista de procesos.

#### Scenario: Opción de contraseña rechazada
- **WHEN** cuando se ejecuta `usuarios alta --email x@example.com --rol recepcionista --password secreto-ficticio`
- **THEN** entonces el código de salida es distinto de `0` y no se crea ningún usuario

#### Scenario: Salida sin secretos
- **WHEN** cuando un alta falla o termina bien
- **THEN** entonces ni la salida estándar ni la de error contienen la contraseña ni el hash

### Requirement: Desactivación de usuario por línea de comandos
El sistema SHALL ofrecer `python -m app.cli usuarios desactivar --email <email>`, que pone `activo = false` sin borrar la fila (DD-16). Desactivar un usuario ya inactivo MUST terminar con código `0` sin cambios. Un email inexistente MUST terminar con código distinto de `0`. No existe reactivación: el email de un usuario inactivo no se puede volver a dar de alta (limitación del MVP registrada en DD-24 y en el backlog de `CHANGES.md`).

#### Scenario: Usuario desactivado
- **GIVEN** dado un usuario activo con email `ana.ficticia@example.com`
- **WHEN** cuando se ejecuta `usuarios desactivar --email ana.ficticia@example.com`
- **THEN** entonces el código de salida es `0`, la fila sigue existiendo con `activo = false` y el usuario ya no puede iniciar sesión

#### Scenario: Desactivar dos veces
- **GIVEN** dado un usuario ya inactivo
- **WHEN** cuando se ejecuta `usuarios desactivar` con su email
- **THEN** entonces el código de salida es `0` y el usuario sigue inactivo

#### Scenario: Email inexistente
- **WHEN** cuando se ejecuta `usuarios desactivar --email nadie@example.com`
- **THEN** entonces el código de salida es distinto de `0` y el mensaje indica que el usuario no existe

#### Scenario: Turnos del usuario desactivado conservan su autor
- **GIVEN** dado un turno creado por una recepcionista
- **WHEN** cuando la recepcionista se desactiva
- **THEN** entonces el turno conserva `creado_por` con el id de la recepcionista
