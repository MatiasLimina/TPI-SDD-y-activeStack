# Spec Delta

## MODIFIED Requirements

### Requirement: Sin endpoints de negocio en la base
El sistema SHALL NOT exponer endpoints de negocio como parte de esta base; cualquier ruta no definida MUST responder `404 Not Found`.

#### Scenario: Ruta inexistente
- **WHEN** un cliente envía `GET /consultorios`
- **THEN** el sistema responde `404 Not Found`
