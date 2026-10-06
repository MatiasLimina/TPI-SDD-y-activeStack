# Spec Delta

## Purpose

Fija la política de tiempo del sistema (RN-CU-04): todo instante se persiste en UTC y se presenta en la zona configurada (`America/Argentina/Buenos_Aires`), rechazando fechas sin zona horaria.

## ADDED Requirements

### Requirement: Normalización a UTC para persistir
El sistema SHALL convertir todo datetime con zona horaria a su instante equivalente en UTC antes de persistirlo.

#### Scenario: Hora de Buenos Aires a UTC
- **WHEN** se normaliza `2026-10-06T10:00:00-03:00`
- **THEN** el resultado es `2026-10-06T13:00:00+00:00`

#### Scenario: Valor ya en UTC
- **WHEN** se normaliza `2026-10-06T13:00:00+00:00`
- **THEN** el resultado es el mismo instante con zona UTC

### Requirement: Presentación en zona local configurada
El sistema SHALL convertir un instante con zona a la zona de presentación configurada (por defecto `America/Argentina/Buenos_Aires`) conservando el mismo instante.

#### Scenario: UTC a Buenos Aires
- **WHEN** se convierte `2026-10-06T13:00:00+00:00` a la zona de presentación
- **THEN** el resultado es `2026-10-06T10:00:00-03:00`

#### Scenario: Cambio de día al convertir
- **WHEN** se convierte `2026-10-07T01:30:00+00:00` a la zona de presentación
- **THEN** el resultado es `2026-10-06T22:30:00-03:00`

### Requirement: Rechazo de datetimes sin zona horaria
El sistema MUST rechazar con un error explícito cualquier datetime sin zona horaria (naive) que se intente normalizar o convertir, en lugar de asumir una zona.

#### Scenario: Datetime naive al normalizar
- **WHEN** se normaliza `2026-10-06T10:00:00` sin zona
- **THEN** la operación falla con un error que indica que el datetime no tiene zona horaria

#### Scenario: Datetime naive al presentar
- **WHEN** se convierte `2026-10-06T13:00:00` sin zona a la zona de presentación
- **THEN** la operación falla con el mismo tipo de error
