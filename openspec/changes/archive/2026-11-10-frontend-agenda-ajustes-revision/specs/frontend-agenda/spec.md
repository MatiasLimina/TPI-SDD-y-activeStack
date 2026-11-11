## ADDED Requirements

### Requirement: Ancho de los elementos superpuestos
Cada elemento MUST ocupar el ancho de su columna dividido por los carriles de su grupo de superposición: los elementos cuyos tramos visibles se pisan, aunque sea de forma transitiva (D4, DD-34). Un elemento sin superposiciones MUST ocupar todo el ancho, aunque otros de la columna se superpongan. Tramos contiguos (`[)`, RN-AG-03) MUST NOT unir grupos. Un carril MUST NOT tener ancho mínimo propio: el texto se recorta. El ancho en píxeles es manual.

#### Scenario: Elemento aislado en una columna con superposiciones
- **GIVEN** dados en una columna turnos de 09:00 a 09:30, de 10:00 a 10:30, de 10:05 a 10:35 y de 12:00 a 12:30 hora local
- **WHEN** cuando se asignan los carriles
- **THEN** entonces los de 09:00 y de 12:00 forman cada uno un grupo de 1 carril, y los de 10:00 y de 10:05, un grupo de 2 carriles

#### Scenario: Ancho completo para el aislado y mitades para los superpuestos
- **GIVEN** dada una columna con un turno aislado y dos turnos que se superponen entre sí
- **WHEN** cuando se dibuja la columna
- **THEN** entonces el aislado ocupa todo el ancho de la columna y cada uno de los otros dos ocupa una mitad, uno al lado del otro

#### Scenario: Cadena de superposiciones
- **GIVEN** dados en una columna segmentos de 10:00 a 10:30, de 10:15 a 10:45 y de 10:30 a 11:00 hora local, donde el primero y el tercero no se superponen
- **WHEN** cuando se asignan los carriles
- **THEN** entonces los tres forman un mismo grupo de 2 carriles

#### Scenario: Tres elementos simultáneos
- **GIVEN** dados en una columna tres elementos de 10:00 a 11:00 hora local
- **WHEN** cuando se asignan los carriles
- **THEN** entonces forman un grupo de 3 carriles

#### Scenario: Tramos contiguos
- **GIVEN** dados en una columna turnos de 10:00 a 10:30 y de 10:30 a 11:00 hora local
- **WHEN** cuando se asignan los carriles
- **THEN** entonces cada uno forma su propio grupo de 1 carril y ocupa todo el ancho

#### Scenario: Grupos de distinto tamaño en la misma columna
- **GIVEN** dada una columna con un grupo de 2 elementos superpuestos y, más tarde, otro grupo de 3
- **WHEN** cuando se dibuja la columna
- **THEN** entonces cada elemento del primer grupo ocupa una mitad del ancho y cada uno del segundo, un tercio, sin taparse entre sí

#### Scenario: Carriles sin ancho mínimo
- **GIVEN** dada una columna con un grupo de 2 elementos superpuestos y otro de 3
- **WHEN** cuando se dibuja la columna
- **THEN** entonces las divisiones de la columna se definen con `minmax(0, 1fr)`, sin un mínimo en píxeles como los 90 px de C-15
