# Spec Delta

## ADDED Requirements

### Requirement: Duración de la prestación en la grilla de 5 minutos
La base de datos MUST rechazar por sí misma una prestación cuya `duracion_min` no sea múltiplo de 5 o sea mayor que 480, tanto al insertarla como al actualizarla, aun cuando la escritura no pase por la aplicación (DD-15, RN-AG-04). El rechazo de una duración cero o negativa sigue a cargo del requisito "Prestación con duración positiva", que no cambia.

#### Scenario: Duración máxima aceptada
- **WHEN** cuando se inserta directamente en la base la prestación "Rehabilitación ficticia" con `duracion_min = 480`
- **THEN** entonces la prestación queda persistida con `duracion_min = 480`

#### Scenario: Duración mínima de la grilla aceptada
- **WHEN** cuando se inserta directamente en la base una prestación con `duracion_min = 5`
- **THEN** entonces la prestación queda persistida con `duracion_min = 5`

#### Scenario: Duración mayor a 480 rechazada por la base
- **WHEN** cuando se inserta directamente en la base una prestación con `duracion_min = 485`
- **THEN** entonces la base rechaza la inserción con una violación de CHECK y no se persiste ninguna fila

#### Scenario: Duración fuera de la grilla rechazada por la base
- **WHEN** cuando se inserta directamente en la base una prestación con `duracion_min = 7`
- **THEN** entonces la base rechaza la inserción con una violación de CHECK

#### Scenario: Actualización directa fuera de la grilla rechazada
- **GIVEN** dada la prestación "Limpieza" persistida con `duracion_min = 45`
- **WHEN** cuando se actualiza directamente en la base su `duracion_min` a 42
- **THEN** entonces la base rechaza la actualización con una violación de CHECK y la prestación sigue con `duracion_min = 45`
