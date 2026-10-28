# Spec Delta

## MODIFIED Requirements

### Requirement: Contenido del seed de desarrollo
El seed SHALL cargar exactamente 2 profesionales, 2 sillones, 4 prestaciones y 4 pacientes. Las prestaciones MUST incluir al menos una que no requiere sillón y al menos una que sí lo requiere. El seed SHALL cargar además 1 usuario `recepcionista` y 2 usuarios `odontologo`, cada odontólogo vinculado a uno de los dos profesionales del seed, todos activos. Cada usuario se siembra solo si su variable de contraseña de desarrollo (`SEED_RECEPCIONISTA_PASSWORD`, `SEED_ODONTOLOGO_1_PASSWORD`, `SEED_ODONTOLOGO_2_PASSWORD`) está definida y no vacía (DD-24).

#### Scenario: Seed sobre base vacía
- **WHEN** se ejecuta el seed sobre una base migrada y sin datos de catálogo
- **THEN** existen 2 profesionales, 2 sillones, 4 prestaciones y 4 pacientes, todos activos

#### Scenario: Prestaciones del seed
- **WHEN** se ejecuta el seed
- **THEN** existen "Consulta" (30 min, sin sillón), "Control" (20 min, sin sillón), "Limpieza" (45 min, con sillón) y "Conservadora" (60 min, con sillón)

#### Scenario: Usuarios del seed
- **GIVEN** dado que las tres variables `SEED_*_PASSWORD` están definidas con contraseñas ficticias
- **WHEN** se ejecuta el seed sobre una base migrada y sin usuarios
- **THEN** existen 1 usuario activo `recepcionista` sin profesional y 2 usuarios activos `odontologo`, uno vinculado a cada profesional del seed, y cada uno puede iniciar sesión con la contraseña de su variable

#### Scenario: Variable de contraseña ausente
- **GIVEN** dado que `SEED_ODONTOLOGO_2_PASSWORD` no está definida y las otras dos sí
- **WHEN** se ejecuta el seed
- **THEN** existen la recepcionista y el primer odontólogo, no existe el segundo odontólogo, y el catálogo se carga completo sin error

#### Scenario: Variable de contraseña vacía
- **GIVEN** dado que `SEED_ODONTOLOGO_2_PASSWORD` está definida como cadena vacía y las otras dos tienen contraseñas ficticias
- **WHEN** se ejecuta el seed
- **THEN** no se crea el segundo odontólogo, existen la recepcionista y el primer odontólogo, y el catálogo se carga completo sin error

#### Scenario: Sin ninguna variable de contraseña
- **GIVEN** dado que ninguna variable `SEED_*_PASSWORD` está definida
- **WHEN** se ejecuta el seed
- **THEN** no se crea ningún usuario y el catálogo se carga completo sin error

### Requirement: Seed idempotente
Ejecutar el seed más de una vez MUST dejar la base en el mismo estado que una única ejecución, sin duplicar filas ni fallar.

#### Scenario: Doble ejecución
- **WHEN** se ejecuta el seed dos veces seguidas
- **THEN** la segunda ejecución termina sin error y las cantidades por tabla son las mismas que tras la primera

#### Scenario: Identificadores estables
- **WHEN** se ejecuta el seed dos veces
- **THEN** cada registro sembrado conserva el mismo identificador en ambas ejecuciones

#### Scenario: Datos preexistentes no se pisan
- **WHEN** un registro sembrado fue modificado (por ejemplo, un sillón marcado inactivo) y se vuelve a ejecutar el seed
- **THEN** el seed no revierte la modificación ni falla

#### Scenario: Usuario sembrado desactivado no se reactiva
- **GIVEN** dado que un usuario del seed fue desactivado y que su variable de contraseña ahora tiene otro valor
- **WHEN** se vuelve a ejecutar el seed
- **THEN** el usuario sigue inactivo y su hash de contraseña no cambia

### Requirement: Solo datos ficticios
El seed MUST contener únicamente datos ficticios (RN-CU-02). Las únicas credenciales que maneja MUST ser contraseñas de desarrollo leídas del entorno al ejecutarse (RN-CU-03): MUST NOT figurar en el código del seed y MUST guardarse solo como hash. Los emails de pacientes y de usuarios MUST usar el dominio reservado `example.com`.

#### Scenario: Emails reservados
- **WHEN** se ejecuta el seed
- **THEN** todo paciente con email informado y todo usuario tienen un email terminado en `@example.com`

#### Scenario: Contraseñas fuera del código del seed
- **WHEN** se inspecciona el código fuente del seed
- **THEN** no contiene ninguno de los valores de `SEED_*_PASSWORD` de `.env.example` ni ningún hash de contraseña

#### Scenario: Contraseña sembrada guardada como hash
- **GIVEN** dado `SEED_RECEPCIONISTA_PASSWORD` definida con una contraseña ficticia
- **WHEN** se ejecuta el seed
- **THEN** el hash guardado de la recepcionista es distinto de esa contraseña y no la contiene
