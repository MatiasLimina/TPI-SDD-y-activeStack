# Spec Delta

## Purpose

Garantizar que los recursos del consultorio (profesionales, sillones, prestaciones) y los pacientes se persistan con integridad asegurada por la base de datos, como base para la agenda de turnos.

## ADDED Requirements

### Requirement: Prestación con duración positiva
El sistema SHALL persistir cada prestación con un nombre y una duración por defecto en minutos estrictamente mayor que cero. La base de datos MUST rechazar cualquier prestación con duración cero o negativa, aun cuando la escritura no pase por la validación de la aplicación.

#### Scenario: Duración positiva aceptada
- **WHEN** se inserta la prestación "Limpieza" con duración de 45 minutos
- **THEN** la prestación queda persistida con `duracion_min = 45`

#### Scenario: Duración cero rechazada por la base
- **WHEN** se inserta una prestación con `duracion_min = 0`
- **THEN** la base de datos rechaza la inserción con una violación de CHECK y no se persiste ninguna fila

#### Scenario: Duración negativa rechazada por la base
- **WHEN** se inserta una prestación con `duracion_min = -15`
- **THEN** la base de datos rechaza la inserción con una violación de CHECK

### Requirement: Prestación indica si requiere sillón
Cada prestación SHALL indicar si requiere sillón (RN-AG-10). Si no se especifica, la base de datos MUST asumir que sí lo requiere.

#### Scenario: Default requiere sillón
- **WHEN** se inserta una prestación sin indicar `requiere_sillon`
- **THEN** la prestación queda persistida con `requiere_sillon = true`

#### Scenario: Prestación sin sillón
- **WHEN** se inserta la prestación "Consulta" con `requiere_sillon = false`
- **THEN** la prestación queda persistida con `requiere_sillon = false`

### Requirement: Recursos y pacientes activos por defecto
Profesionales, sillones, prestaciones y pacientes SHALL tener un indicador de actividad que la base de datos MUST inicializar en activo cuando no se especifica. La baja es lógica (inactivo), no un borrado.

#### Scenario: Alta sin indicar actividad
- **WHEN** se inserta un profesional, un sillón, una prestación o un paciente sin indicar su estado de actividad
- **THEN** el registro queda persistido como activo

### Requirement: Unicidad de identificadores naturales
La base de datos MUST impedir duplicados de: nombre de sillón, nombre de prestación, documento de paciente y matrícula de profesional cuando está informada. Varios profesionales MAY no tener matrícula.

#### Scenario: Sillón con nombre duplicado
- **WHEN** ya existe "Sillón 1" y se inserta otro sillón llamado "Sillón 1"
- **THEN** la base de datos rechaza la inserción con una violación de unicidad

#### Scenario: Paciente con documento duplicado
- **WHEN** ya existe un paciente con un documento dado y se inserta otro con el mismo documento
- **THEN** la base de datos rechaza la inserción con una violación de unicidad

#### Scenario: Profesionales sin matrícula
- **WHEN** se insertan dos profesionales sin matrícula
- **THEN** ambos quedan persistidos

### Requirement: Atributos obligatorios
La base de datos MUST rechazar profesionales sin nombre o apellido, sillones sin nombre, prestaciones sin nombre o duración, y pacientes sin nombre, apellido, documento o teléfono. El email del paciente SHALL ser opcional.

#### Scenario: Paciente sin documento
- **WHEN** se inserta un paciente sin documento
- **THEN** la base de datos rechaza la inserción con una violación de NOT NULL

#### Scenario: Paciente sin email
- **WHEN** se inserta un paciente con nombre, apellido, documento y teléfono pero sin email
- **THEN** el paciente queda persistido con email nulo

### Requirement: Marcas de tiempo en UTC
Cada registro del catálogo SHALL registrar su momento de creación y de última actualización como instantes con zona horaria, completados por la base de datos cuando no se informan.

#### Scenario: Marca de creación automática
- **WHEN** se inserta un sillón sin informar marcas de tiempo
- **THEN** `creado_en` y `actualizado_en` quedan completados con un instante con zona horaria (`timestamptz`)
