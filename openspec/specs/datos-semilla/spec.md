# datos-semilla Specification

## Purpose
Proveer un conjunto de datos de desarrollo ficticio e idempotente que deje el sistema listo para agendar turnos sin cargar el catálogo a mano ni usar datos reales.

## Requirements

### Requirement: Contenido del seed de desarrollo
El seed SHALL cargar exactamente 2 profesionales, 2 sillones, 4 prestaciones y 4 pacientes. Las prestaciones MUST incluir al menos una que no requiere sillón y al menos una que sí lo requiere.

#### Scenario: Seed sobre base vacía
- **WHEN** se ejecuta el seed sobre una base migrada y sin datos de catálogo
- **THEN** existen 2 profesionales, 2 sillones, 4 prestaciones y 4 pacientes, todos activos

#### Scenario: Prestaciones del seed
- **WHEN** se ejecuta el seed
- **THEN** existen "Consulta" (30 min, sin sillón), "Control" (20 min, sin sillón), "Limpieza" (45 min, con sillón) y "Conservadora" (60 min, con sillón)

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

### Requirement: Solo datos ficticios
El seed MUST contener únicamente datos ficticios (RN-CU-02) y ninguna credencial. Los emails de pacientes MUST usar el dominio reservado `example.com`.

#### Scenario: Emails reservados
- **WHEN** se ejecuta el seed
- **THEN** todo paciente con email informado tiene un email terminado en `@example.com`
