## ADDED Requirements

### Requirement: Rótulo del período visible
La agenda MUST mostrar, junto a los controles de navegación, un rótulo del período que se está viendo, en la zona `America/Argentina/Buenos_Aires` y no en la del navegador (D19). En la vista diaria MUST ser el nombre del día y la fecha completa, por ejemplo `Jueves 12/11/2026`. En la vista semanal MUST ser `Semana del DD/MM al DD/MM/AAAA` desde el lunes hasta el domingo; si la semana cruza de año, MUST llevar el año en ambas fechas, por ejemplo `Semana del 28/12/2026 al 03/01/2027`. El rótulo MUST actualizarse al usar `Período anterior`, `Período siguiente`, `Hoy`, al cambiar entre `Día` y `Semana` y al cambiar el parámetro `fecha` de la URL. El rótulo MUST ser una región `aria-live="polite"` para que un lector de pantalla anuncie el cambio de período.

#### Scenario: Rótulo de la vista diaria
- **GIVEN** dada la agenda en la vista diaria de la fecha 2026-11-12
- **WHEN** cuando se muestra la barra de la agenda
- **THEN** entonces se ve el texto `Jueves 12/11/2026`

#### Scenario: Rótulo de la vista semanal
- **GIVEN** dada la agenda en la vista semanal con la fecha 2026-11-12
- **WHEN** cuando se muestra la barra de la agenda
- **THEN** entonces se ve el texto `Semana del 09/11 al 15/11/2026`

#### Scenario: Semana que cruza de año
- **GIVEN** dada la agenda en la vista semanal con la fecha 2026-12-30
- **WHEN** cuando se muestra la barra de la agenda
- **THEN** entonces se ve el texto `Semana del 28/12/2026 al 03/01/2027`

#### Scenario: Rótulo tras navegar
- **GIVEN** dada la agenda en la vista diaria de la fecha 2026-11-12
- **WHEN** cuando se presiona `Período siguiente`
- **THEN** entonces se ve `Viernes 13/11/2026`, y al presionar `Hoy` se ve el rótulo del día actual del consultorio

#### Scenario: Rótulo tras cambiar de vista
- **GIVEN** dada la agenda en la vista diaria de la fecha 2026-11-12
- **WHEN** cuando se presiona `Semana`
- **THEN** entonces se ve `Semana del 09/11 al 15/11/2026`

#### Scenario: Rótulo con la fecha de la URL
- **GIVEN** dada la ruta `/agenda?vista=dia&fecha=2026-11-16`
- **WHEN** cuando se muestra la agenda
- **THEN** entonces se ve `Lunes 16/11/2026`

#### Scenario: Zona del consultorio
- **GIVEN** dado un navegador en `Asia/Tokyo` y el reloj en 2026-11-11T20:00:00-03:00, que en Tokio ya es el 12
- **WHEN** cuando se muestra la agenda sin parámetros
- **THEN** entonces el rótulo muestra `Miércoles 11/11/2026`, la fecha del consultorio

#### Scenario: Rótulo anunciado a los lectores de pantalla
- **WHEN** cuando se inspecciona el rótulo del período
- **THEN** entonces es una región con `aria-live="polite"`
