# Delta for agenda-turnos

## ADDED Requirements

### Requirement: Cancelación de un turno
El sistema SHALL exponer `POST /turnos/{id}/cancelar`. Un turno programado MUST pasar a `estado = cancelado` y dejar de contar para los solapamientos (RN-AG-07).

#### Scenario: Cancelar un turno futuro
- **GIVEN** dado un turno programado para 2026-10-12 10:00-03:00 y que el reloj marca 2026-10-11 09:00 hora local
- **WHEN** cuando se envía `POST /turnos/{id}/cancelar`
- **THEN** entonces la respuesta es `200` y el turno queda con `estado = cancelado`

#### Scenario: Turno inexistente
- **WHEN** cuando se envía `POST /turnos/999999/cancelar`
- **THEN** entonces la respuesta es `404`
