# Spec Delta

## MODIFIED Requirements

### Requirement: Contenido del seed de desarrollo
El seed SHALL cargar exactamente 2 profesionales, 2 sillones, 4 prestaciones y 4 pacientes. Las prestaciones MUST incluir al menos una que no requiere sillón y al menos una que sí lo requiere. El seed SHALL cargar además 1 usuario `recepcionista` y 2 usuarios `odontologo`, cada odontólogo vinculado a uno de los dos profesionales del seed, todos activos. Cada usuario se siembra solo si su variable de contraseña de desarrollo (`SEED_RECEPCIONISTA_PASSWORD`, `SEED_ODONTOLOGO_1_PASSWORD`, `SEED_ODONTOLOGO_2_PASSWORD`) está definida y no vacía (DD-24). El seed SHALL cargar también el horario de atención de ejemplo de cada profesional: de lunes a viernes (`dia_semana` 0 a 4), una franja de 09:00 a 13:00 y otra de 14:00 a 18:00, hora local (20 franjas en total). Al re-ejecutarse, el seed MUST NOT modificar ni borrar franjas existentes, aunque hayan sido editadas a mano: solo inserta las franjas sembradas que falten, y omite sin error una franja faltante que se superpondría con otra existente del mismo profesional y día (mismo criterio que "Datos preexistentes no se pisan" de "Seed idempotente"; DD-27).

#### Scenario: Seed sobre base vacía
- **WHEN** se ejecuta el seed sobre una base migrada y sin datos de catálogo
- **THEN** existen 2 profesionales, 2 sillones, 4 prestaciones y 4 pacientes, todos activos

#### Scenario: Prestaciones del seed
- **WHEN** se ejecuta el seed
- **THEN** existen "Consulta" (30 min, sin sillón), "Control" (20 min, sin sillón), "Limpieza" (45 min, con sillón) y "Conservadora" (60 min, con sillón)

#### Scenario: Horario de atención del seed
- **WHEN** se ejecuta el seed sobre una base migrada y sin franjas
- **THEN** cada uno de los 2 profesionales tiene exactamente 10 franjas: para cada `dia_semana` de 0 a 4, una de 09:00 a 13:00 y otra de 14:00 a 18:00, y no tiene franjas el sábado ni el domingo

#### Scenario: Franjas editadas a mano no se pisan
- **GIVEN** dado el seed ejecutado, la franja del lunes de 09:00 a 13:00 del primer profesional editada a 09:00-12:00 y su franja del martes de 14:00 a 18:00 borrada
- **WHEN** se vuelve a ejecutar el seed
- **THEN** termina sin error, la franja del lunes sigue de 09:00 a 12:00 con el mismo `id`, la del martes de 14:00 a 18:00 existe otra vez con su `id` fijo, y el profesional tiene 10 franjas

#### Scenario: Franja sembrada faltante que choca con una cargada a mano
- **GIVEN** dado el seed ejecutado, la franja del martes de 14:00 a 18:00 del primer profesional borrada y una franja del martes de 15:00 a 19:00 creada a mano para él
- **WHEN** se vuelve a ejecutar el seed
- **THEN** termina sin error y el martes ese profesional tiene solo las franjas de 09:00 a 13:00 y de 15:00 a 19:00

#### Scenario: Turno agendable con el seed
- **GIVEN** dado el seed ejecutado, una recepcionista autenticada y que el reloj marca 2026-10-07 09:00 hora local
- **WHEN** cuando crea un turno de "Consulta" para el primer profesional del seed el jueves 2026-10-08 a las 10:00 hora local
- **THEN** entonces la respuesta es `201`

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
