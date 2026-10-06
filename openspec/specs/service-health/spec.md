# service-health Specification

## Purpose

Permite a operadores, orquestadores de contenedores y tests de humo verificar que la API está en ejecución y puede comunicarse con su base de datos PostgreSQL.

## Requirements

### Requirement: Endpoint de salud disponible
El sistema SHALL exponer `GET /health` sin autenticación, respondiendo en JSON con el estado general de la API y el estado de la base de datos.

#### Scenario: API y base de datos operativas
- **WHEN** un cliente envía `GET /health` y la base de datos acepta conexiones
- **THEN** el sistema responde `200 OK`
- **AND** el cuerpo es `{"status": "ok", "database": "ok"}`

### Requirement: Salud degradada cuando la base no responde
El sistema MUST informar el fallo de conectividad con la base de datos en `GET /health` en lugar de reportar un estado sano, sin exponer detalles internos (cadena de conexión, credenciales ni traza).

#### Scenario: Base de datos inaccesible
- **WHEN** un cliente envía `GET /health` y la base de datos no acepta conexiones
- **THEN** el sistema responde `503 Service Unavailable`
- **AND** el cuerpo es `{"status": "degraded", "database": "unavailable"}`
- **AND** el cuerpo no contiene la URL de conexión ni credenciales

### Requirement: Sin endpoints de negocio en la base
El sistema SHALL NOT exponer endpoints de negocio como parte de esta base; cualquier ruta no definida MUST responder `404 Not Found`.

#### Scenario: Ruta inexistente
- **WHEN** un cliente envía `GET /turnos`
- **THEN** el sistema responde `404 Not Found`
