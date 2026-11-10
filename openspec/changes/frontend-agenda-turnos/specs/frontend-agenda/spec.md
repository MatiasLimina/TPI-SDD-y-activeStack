## ADDED Requirements

### Requirement: Pantalla de agenda
`/agenda` SHALL mostrar a ambos roles la agenda de un período, cargando con `GET /turnos` los turnos y bloqueos y con `GET /profesionales`, `GET /sillones` y `GET /prestaciones` los nombres de los catálogos (US-008, DD-32). Mientras carga MUST indicarlo. Un período sin elementos visibles MUST informarlo con un mensaje; si solo hay cancelados ocultos, con un texto propio que invite a mostrarlos (D3, DD-34).

#### Scenario: Agenda de la recepcionista
- **GIVEN** dada una sesión de `recepcionista` y un turno `programado` del profesional "Ana Ficticia" el 2026-11-09 de 10:00 a 10:45 hora local, con la paciente "Carla Imaginaria" y la prestación "Limpieza"
- **WHEN** cuando navega a `/agenda?fecha=2026-11-09`
- **THEN** entonces se hace `GET /turnos?desde=2026-11-09&hasta=2026-11-09` y se ve el turno con `10:00`, `Imaginaria, Carla` y `Limpieza` en la columna de `Ficticia, Ana`

#### Scenario: Carga en curso
- **GIVEN** dada una sesión activa y un pedido de agenda sin responder
- **WHEN** cuando se muestra `/agenda`
- **THEN** entonces se ve la indicación `Cargando agenda…`

#### Scenario: Día sin turnos
- **GIVEN** dada una respuesta `{"turnos": [], "bloqueos": []}`
- **WHEN** cuando se muestra la agenda
- **THEN** entonces se ve el mensaje `No hay turnos ni bloqueos en este período.`

#### Scenario: Solo hay turnos cancelados ocultos
- **GIVEN** dada una respuesta con un único turno `cancelado` y la casilla `Mostrar cancelados` apagada
- **WHEN** cuando se muestra la agenda
- **THEN** entonces se ve `Solo hay turnos cancelados en este período. Activá Mostrar cancelados para verlos.` y no se ve `No hay turnos ni bloqueos en este período.`

### Requirement: Horarios en la zona del consultorio
Toda fecha y hora de la agenda MUST mostrarse en `America/Argentina/Buenos_Aires`, sin importar la zona configurada en el navegador (RN-CU-04, DD-06). En este spec, "hora local" significa esa zona. Un turno MUST ubicarse en el o los días locales que abarca, calculados en esa zona y nunca en la del navegador.

#### Scenario: Navegador en otra zona horaria
- **GIVEN** dado un navegador configurado en `Asia/Tokyo` y un turno con `inicio` `2026-11-09T22:30:00-03:00`, que en esa zona es el 2026-11-10 a las 10:30
- **WHEN** cuando se muestra la agenda del 2026-11-09
- **THEN** entonces el turno se ve con `22:30` en el día 2026-11-09

#### Scenario: Formato de 24 horas a medianoche
- **GIVEN** dado un turno con `inicio` `2026-11-09T00:00:00-03:00`
- **WHEN** cuando se muestra la agenda del 2026-11-09
- **THEN** entonces el turno se ve con `00:00`, nunca `24:00`

### Requirement: Día actual del consultorio
El día actual MUST calcularse en `America/Argentina/Buenos_Aires` a partir del reloj, no en la zona del navegador.

#### Scenario: Ya es mañana en la zona del navegador
- **GIVEN** dado un navegador en `Asia/Tokyo` y el reloj en 2026-11-10T02:00:00Z, que es el 2026-11-09 a las 23:00 en Buenos Aires y el 2026-11-10 en Tokio
- **WHEN** cuando se navega a `/agenda` sin parámetros
- **THEN** entonces se hace `GET /turnos?desde=2026-11-09&hasta=2026-11-09`

#### Scenario: Ya es hoy en Buenos Aires
- **GIVEN** dado el reloj en 2026-11-10T03:00:00Z, que es el 2026-11-10 a las 00:00 en Buenos Aires
- **WHEN** cuando se navega a `/agenda` sin parámetros
- **THEN** entonces se hace `GET /turnos?desde=2026-11-10&hasta=2026-11-10`

### Requirement: Vistas diaria y semanal
La agenda SHALL ofrecer una vista diaria y una semanal (US-008). La semanal MUST abarcar de lunes a domingo la semana de la fecha en curso, con una columna por día. Sin indicación, MUST mostrarse la vista diaria del día actual.

#### Scenario: Semana de lunes a domingo
- **GIVEN** dada una sesión activa
- **WHEN** cuando se navega a `/agenda?vista=semana&fecha=2026-11-12`, un jueves
- **THEN** entonces se hace `GET /turnos?desde=2026-11-09&hasta=2026-11-15` y se ven siete columnas, de `Lunes 09/11` a `Domingo 15/11`

#### Scenario: Fecha que ya es lunes
- **WHEN** cuando se navega a `/agenda?vista=semana&fecha=2026-11-09`
- **THEN** entonces se hace `GET /turnos?desde=2026-11-09&hasta=2026-11-15`

#### Scenario: Fecha que es domingo
- **WHEN** cuando se navega a `/agenda?vista=semana&fecha=2026-11-15`
- **THEN** entonces se hace `GET /turnos?desde=2026-11-09&hasta=2026-11-15`

#### Scenario: Cambio de vista
- **GIVEN** dada la vista diaria del 2026-11-12
- **WHEN** cuando se elige la vista semanal
- **THEN** entonces se muestra la semana del 2026-11-09 al 2026-11-15

#### Scenario: De semana a día
- **GIVEN** dada la vista semanal con fecha 2026-11-12
- **WHEN** cuando se elige la vista diaria
- **THEN** entonces se hace `GET /turnos?desde=2026-11-12&hasta=2026-11-12`

### Requirement: Navegación entre períodos
La agenda SHALL permitir ir al período anterior, al siguiente y al día actual. El período es un día en la vista diaria y una semana en la semanal.

#### Scenario: Día siguiente
- **GIVEN** dada la vista diaria del 2026-11-30
- **WHEN** cuando se elige el período siguiente
- **THEN** entonces se hace `GET /turnos?desde=2026-12-01&hasta=2026-12-01`

#### Scenario: Semana anterior
- **GIVEN** dada la vista semanal del 2026-11-09 al 2026-11-15
- **WHEN** cuando se elige el período anterior
- **THEN** entonces se hace `GET /turnos?desde=2026-11-02&hasta=2026-11-08`

#### Scenario: Volver a hoy
- **GIVEN** dado el reloj en el 2026-11-09 hora local y la vista diaria del 2026-12-20
- **WHEN** cuando se elige ir a hoy
- **THEN** entonces se hace `GET /turnos?desde=2026-11-09&hasta=2026-11-09`

#### Scenario: Hoy en la vista semanal
- **GIVEN** dado el reloj en el 2026-11-09 hora local y la vista semanal del 2026-12-14 al 2026-12-20
- **WHEN** cuando se elige ir a hoy
- **THEN** entonces se hace `GET /turnos?desde=2026-11-09&hasta=2026-11-15`

#### Scenario: Semana que cruza el año
- **GIVEN** dada la vista semanal del 2026-12-21 al 2026-12-27
- **WHEN** cuando se elige el período siguiente
- **THEN** entonces se hace `GET /turnos?desde=2026-12-28&hasta=2027-01-03`

### Requirement: La vista se conserva en la URL
La vista, la fecha, los filtros, el modo de columnas y la casilla de cancelados MUST reflejarse en la URL de `/agenda`, de modo que recargar conserve la vista y volver atrás recupere la anterior. Un parámetro inválido MUST ignorarse y usar su valor por defecto; una `fecha` con año fuera de 1000 a 9998 es inválida (D6, DD-34). La URL MUST NOT contener datos de pacientes.

#### Scenario: Recargar conserva la vista
- **WHEN** cuando se abre `/agenda?vista=semana&fecha=2026-11-12&sillon=00000000-0000-4000-8000-0000000000c1`
- **THEN** entonces se hace `GET /turnos` con `desde=2026-11-09`, `hasta=2026-11-15` y `sillon_id` igual a ese id

#### Scenario: Volver atrás
- **GIVEN** dada la vista diaria del 2026-11-09 y una navegación al período siguiente
- **WHEN** cuando se vuelve atrás en el historial
- **THEN** entonces se muestra otra vez la vista del 2026-11-09

#### Scenario: Fecha inválida
- **GIVEN** dado el reloj en el 2026-11-09 hora local
- **WHEN** cuando se abre `/agenda?fecha=2026-02-30`
- **THEN** entonces se hace `GET /turnos?desde=2026-11-09&hasta=2026-11-09`

#### Scenario: Filtro mal formado
- **WHEN** cuando se abre `/agenda?fecha=2026-11-09&profesional=no-es-un-id`
- **THEN** entonces el pedido no incluye `profesional_id` y la agenda se muestra sin filtro

#### Scenario: Año posterior al admitido
- **GIVEN** dado el reloj en el 2026-11-09 hora local
- **WHEN** cuando se abre `/agenda?fecha=9999-12-31`
- **THEN** entonces se hace `GET /turnos?desde=2026-11-09&hasta=2026-11-09`

#### Scenario: Año anterior al admitido
- **GIVEN** dado el reloj en el 2026-11-09 hora local
- **WHEN** cuando se abre `/agenda?fecha=0050-01-15`
- **THEN** entonces se hace `GET /turnos?desde=2026-11-09&hasta=2026-11-09`

#### Scenario: Año en el borde admitido
- **WHEN** cuando se abre `/agenda?fecha=9998-12-31`
- **THEN** entonces se hace `GET /turnos?desde=9998-12-31&hasta=9998-12-31`

### Requirement: Filtros por profesional y por sillón
La agenda SHALL filtrarse por profesional y por sillón con los parámetros `profesional_id` y `sillon_id` de la API, combinables (US-008). Los selectores MUST incluir los recursos desactivados, identificados como inactivos, porque conservan su agenda (DD-32 l). Filtrar por sillón MUST seguir mostrando los bloqueos del profesional (DD-32 h).

#### Scenario: Filtrar por profesional
- **GIVEN** dada una recepcionista en la agenda del 2026-11-09
- **WHEN** cuando elige un profesional en el filtro
- **THEN** entonces se hace `GET /turnos` con `profesional_id` igual a ese id y se ve una sola columna

#### Scenario: Filtrar por sillón y profesional a la vez
- **GIVEN** dada una recepcionista en la agenda del 2026-11-09
- **WHEN** cuando elige un profesional y un sillón
- **THEN** entonces el último pedido incluye `profesional_id` y `sillon_id`

#### Scenario: Quitar el filtro
- **GIVEN** dada una agenda filtrada por sillón
- **WHEN** cuando se elige la opción `Todos los sillones`
- **THEN** entonces el pedido no incluye `sillon_id`

#### Scenario: Profesional desactivado en el filtro
- **GIVEN** dado un profesional desactivado "Luis Inventado"
- **WHEN** cuando se abre el filtro de profesional
- **THEN** entonces se ve la opción `Inventado, Luis (inactivo)`

#### Scenario: Bloqueo con filtro de sillón
- **GIVEN** dada una agenda filtrada por sillón cuya respuesta trae un bloqueo del profesional A
- **WHEN** cuando se muestra la agenda
- **THEN** entonces se ve el bloqueo

#### Scenario: Filtro por un profesional desactivado sin elementos
- **GIVEN** dado un profesional desactivado sin elementos visibles en el día
- **WHEN** cuando la recepcionista filtra por él
- **THEN** entonces no se ve ninguna columna y se ve `No hay turnos ni bloqueos en este período.`

#### Scenario: Filtro con un id que no existe
- **GIVEN** dado un id bien formado que no figura en el catálogo y una respuesta `200` vacía (DD-32 l)
- **WHEN** cuando se abre `/agenda?fecha=2026-11-09&profesional=00000000-0000-4000-8000-0000000000a9`
- **THEN** entonces el pedido incluye `profesional_id`, el filtro muestra `Profesional no disponible` y se ve `No hay turnos ni bloqueos en este período.`

### Requirement: Columnas de la vista diaria
La vista diaria de la recepcionista SHALL mostrar una columna por profesional o, si elige agrupar por sillón, una por sillón. Un recurso desactivado MUST tener columna solo si tiene elementos visibles. Agrupando por sillón, los turnos sin sillón MUST ir en `Sin sillón` y los bloqueos en `Bloqueos` (DD-30 d), columnas que MUST aparecer solo si tienen elementos visibles. `columnas=sillon` MUST ignorarse en la vista semanal y con rol `odontologo`.

#### Scenario: Una columna por profesional activo
- **GIVEN** dados dos profesionales activos y uno desactivado sin turnos en el día
- **WHEN** cuando la recepcionista ve la agenda diaria
- **THEN** entonces se ven dos columnas

#### Scenario: Profesional desactivado con turnos
- **GIVEN** dado un profesional desactivado con un turno en el día
- **WHEN** cuando la recepcionista ve la agenda diaria
- **THEN** entonces ese profesional tiene su columna

#### Scenario: Profesional desactivado con solo cancelados ocultos
- **GIVEN** dado un profesional desactivado cuyo único turno del día está `cancelado` y la casilla `Mostrar cancelados` apagada
- **WHEN** cuando la recepcionista ve la agenda diaria
- **THEN** entonces ese profesional no tiene columna

#### Scenario: Agrupar por sillón
- **GIVEN** dado un turno en el sillón "Sillón 1", un turno sin sillón y un bloqueo el 2026-11-09
- **WHEN** cuando la recepcionista agrupa la vista diaria por sillón
- **THEN** entonces cada turno se ve en la columna `Sillón 1` y en `Sin sillón`, y el bloqueo en `Bloqueos` con el nombre de su profesional

#### Scenario: Sin columnas especiales vacías
- **GIVEN** dados solo turnos con sillón el 2026-11-09
- **WHEN** cuando la recepcionista agrupa la vista diaria por sillón
- **THEN** entonces no se ven las columnas `Sin sillón` ni `Bloqueos`

#### Scenario: Agrupar por sillón no aplica a la semana
- **WHEN** cuando se abre `/agenda?vista=semana&fecha=2026-11-12&columnas=sillon`
- **THEN** entonces se ven siete columnas, una por día

### Requirement: Datos visibles de cada turno
Cada turno de la agenda MUST mostrar su horario, paciente (`apellido, nombre`) y prestación. MUST mostrar el profesional y el sillón cuando las columnas no lo indican. Al elegirlo, MUST abrirse un detalle con horario, paciente, prestación, profesional, sillón, estado y motivo de cancelación si existe. MUST NOT mostrar documento, teléfono ni email del paciente (DD-32 j).

#### Scenario: Semana con varios profesionales
- **GIVEN** dada la vista semanal sin filtro de profesional y un turno de "Ana Ficticia" en el sillón "Sillón 1"
- **WHEN** cuando se muestra la agenda
- **THEN** entonces el turno muestra `Ficticia, Ana` y `Sillón 1`

#### Scenario: Detalle de un turno
- **GIVEN** dado un turno `cancelado` con motivo "Viaje"
- **WHEN** cuando se lo elige en la agenda
- **THEN** entonces se abre un detalle que muestra el estado `Cancelado` y el motivo `Viaje`

#### Scenario: Turno sin sillón
- **GIVEN** dado un turno con `sillon_id` nulo
- **WHEN** cuando se abre su detalle
- **THEN** entonces el sillón se muestra como `Sin sillón`

### Requirement: Nombres de los recursos
Los ids de profesional, sillón y prestación MUST presentarse con su nombre, incluidos los de recursos desactivados. Un id que no figura en el catálogo cargado MUST mostrarse con un texto genérico, sin mostrar el id y sin impedir ver la agenda.

#### Scenario: Prestación desactivada
- **GIVEN** dado un turno cuya prestación "Control" fue desactivada
- **WHEN** cuando se muestra la agenda
- **THEN** entonces el turno muestra `Control`

#### Scenario: Id ausente del catálogo
- **GIVEN** dado un turno cuyo `prestacion_id` no está en el catálogo cargado
- **WHEN** cuando se muestra la agenda
- **THEN** entonces el turno se ve con el texto `Prestación no disponible` y no se ve el id

### Requirement: Turnos cancelados
Los turnos `cancelado` MUST ocultarse por defecto y mostrarse al activar `Mostrar cancelados` (D3, DD-34), sin un pedido nuevo, porque la API siempre los trae (DD-32 f). Visibles, MUST distinguirse con el texto `Cancelado` y no solo por color, y un cancelado y un programado del mismo horario MUST verse los dos, sin taparse.

#### Scenario: Oculto por defecto
- **GIVEN** dada una respuesta con un turno `programado` y uno `cancelado` el mismo día
- **WHEN** cuando se muestra la agenda
- **THEN** entonces se ve solo el programado

#### Scenario: Cancelado y programado en el mismo horario
- **GIVEN** dada una respuesta con un turno `cancelado` y uno `programado` de 10:00 a 10:45 del mismo profesional
- **WHEN** cuando se activa `Mostrar cancelados`
- **THEN** entonces se ven ambos, en carriles distintos, y solo el cancelado tiene el texto `Cancelado`; no se hizo ningún pedido adicional

#### Scenario: La casilla se conserva al recargar
- **WHEN** cuando se abre `/agenda?fecha=2026-11-09&cancelados=1`
- **THEN** entonces la casilla `Mostrar cancelados` está activa

### Requirement: Ubicación en la grilla
Cada día MUST presentarse con un eje de 24 horas de 288 filas de 5 minutos (D1, DD-34). La ubicación MUST calcularse con funciones puras sobre la hora local: inicio redondeado hacia abajo, fin hacia arriba y recorte a cada día. El texto MUST seguir mostrando la hora real. El desplazamiento inicial a las 08:00, la geometría y el ancho de los carriles son de verificación manual (tarea 10.2).

#### Scenario: Fila de un turno
- **GIVEN** dado un turno de 10:00 a 10:45 hora local
- **WHEN** cuando se calcula su ubicación
- **THEN** entonces ocupa 9 filas desde la fila 120, contando desde 0

#### Scenario: Primer tramo del día
- **GIVEN** dado un turno de 00:00 a 00:30 hora local
- **WHEN** cuando se calcula su ubicación
- **THEN** entonces ocupa 6 filas desde la fila 0

#### Scenario: Último tramo del día
- **GIVEN** dado un turno de 23:55 a 00:00 hora local
- **WHEN** cuando se calcula su ubicación
- **THEN** entonces ocupa una sola fila, la 287, que es la última

#### Scenario: Recorte por día
- **GIVEN** dado un turno del 2026-11-10 23:30 al 2026-11-11 00:30 hora local
- **WHEN** cuando se calculan sus segmentos por día
- **THEN** entonces el del día 10 ocupa 6 filas desde la fila 282 y el del día 11 ocupa 6 filas desde la fila 0

#### Scenario: Carriles según las filas ocupadas
- **GIVEN** dados en una columna segmentos de 10:00 a 10:30, de 10:15 a 10:45 y de 10:30 a 11:00
- **WHEN** cuando se asignan los carriles
- **THEN** entonces usan los carriles 0, 1 y 0

### Requirement: Elementos superpuestos en una columna
Los elementos que se superponen dentro de una columna MUST ubicarse en carriles paralelos, para que ninguno tape a otro. La superposición MUST evaluarse sobre las filas de 5 minutos ya redondeadas (D4, DD-34). Dos elementos cuyas filas son contiguas (`[inicio, fin)`, RN-AG-03) MUST NOT considerarse superpuestos.

#### Scenario: Varios profesionales en un mismo día de la semana
- **GIVEN** dada la vista semanal sin filtro y tres turnos de profesionales distintos de 10:00 a 11:00 el mismo día
- **WHEN** cuando se ubican en la columna del día
- **THEN** entonces ocupan tres carriles distintos

#### Scenario: Turnos contiguos
- **GIVEN** dados dos turnos del mismo profesional de 10:00 a 10:30 y de 10:30 a 11:00
- **WHEN** cuando se ubican en la columna
- **THEN** entonces ambos usan el mismo carril

#### Scenario: Bloqueos superpuestos
- **GIVEN** dados dos bloqueos superpuestos del mismo profesional (DD-30 b)
- **WHEN** cuando se ubican en la columna
- **THEN** entonces se ven los dos, en carriles distintos y sin fusionarse

#### Scenario: Contiguos que comparten una fila redondeada
- **GIVEN** dados dos bloqueos de 10:00 a 10:03 y de 10:03 a 10:05 hora local (DD-30 f)
- **WHEN** cuando se asignan los carriles
- **THEN** entonces ocupan carriles distintos, porque ambos usan la fila 120

### Requirement: Elementos que cruzan días
Un turno o bloqueo MUST verse en cada día local visible que abarca, recortado a ese día e indicando su `inicio` y `fin` reales con fecha, porque la API los entrega completos (DD-32 e).

#### Scenario: Turno que cruza la medianoche
- **GIVEN** dada la vista semanal y un turno del 2026-11-10 23:30 al 2026-11-11 00:30 hora local
- **WHEN** cuando se muestra la agenda
- **THEN** entonces se ve en el día 10 desde las 23:30 hasta el final del día y en el día 11 desde el inicio del día hasta las 00:30, indicando en ambos `10/11 23:30` y `11/11 00:30`

#### Scenario: Bloqueo de varios días en la vista diaria
- **GIVEN** dada la vista diaria del 2026-11-11 y un bloqueo del 2026-11-09 08:00 al 2026-11-13 20:00 hora local
- **WHEN** cuando se muestra la agenda
- **THEN** entonces el bloqueo ocupa todo el día 11 e indica `09/11 08:00` y `13/11 20:00`

#### Scenario: Bloqueo que no respeta la grilla
- **GIVEN** dado un bloqueo de 10:03 a 10:07 hora local (DD-30 f)
- **WHEN** cuando se muestra la agenda
- **THEN** entonces se ve con el texto `10:03` y `10:07`, y su ubicación ocupa 2 filas desde la fila 120

#### Scenario: Bloqueo que termina justo a la medianoche
- **GIVEN** dado un bloqueo del 2026-11-10 20:00 al 2026-11-11 00:00 hora local (RN-AG-03)
- **WHEN** cuando se calculan sus segmentos en la semana del 2026-11-09 al 2026-11-15
- **THEN** entonces hay un solo segmento, en el día 10, hasta el final del día

#### Scenario: Bloqueo que cruza el fin de la semana visible
- **GIVEN** dado un bloqueo del domingo 2026-11-15 22:00 al lunes 2026-11-16 02:00 hora local
- **WHEN** cuando se calculan sus segmentos en la semana del 2026-11-09 al 2026-11-15 y en la del 2026-11-16 al 2026-11-22
- **THEN** entonces en la primera hay un segmento solo en el domingo y en la segunda uno solo en el lunes, indicando en ambas `15/11 22:00` y `16/11 02:00`

### Requirement: Bloqueos en la agenda
Los bloqueos del período MUST mostrarse con su horario, su motivo y una identificación visible de que son bloqueos, distinta de un turno, y con su profesional cuando las columnas no lo indican. La agenda MUST NOT ofrecer crearlos ni borrarlos.

#### Scenario: Bloqueo visible
- **GIVEN** dado un bloqueo del profesional A de 15:00 a 16:00 con motivo "Congreso"
- **WHEN** cuando se muestra la agenda
- **THEN** entonces se ve en la columna de A con el texto `Bloqueo`, `15:00`, `16:00` y `Congreso`, sin acciones para modificarlo

#### Scenario: Bloqueo en la semana sin filtro
- **GIVEN** dada la vista semanal sin filtro de profesional y un bloqueo de "Ana Ficticia"
- **WHEN** cuando se muestra la agenda
- **THEN** entonces el bloqueo muestra `Ficticia, Ana`

### Requirement: Agenda del odontólogo
Con rol `odontologo`, la agenda SHALL ser de solo lectura y mostrar únicamente la agenda de su profesional (RN-AU-02). El pedido MUST omitir `profesional_id`, aunque la URL lo traiga, y la pantalla MUST NOT ofrecer filtro de profesional ni agrupar por sillón. La vista diaria MUST tener una sola columna, la de su profesional, aunque esté vacía (D16, DD-34). MUST NOT pedir `GET /pacientes` (DD-31 b).

#### Scenario: Odontólogo sin filtro de profesional
- **GIVEN** dada una sesión de `odontologo`
- **WHEN** cuando navega a `/agenda?fecha=2026-11-09`
- **THEN** entonces el pedido a `GET /turnos` no incluye `profesional_id` y no se ve el filtro de profesional ni la opción de agrupar por sillón

#### Scenario: Parámetro de profesional ignorado
- **GIVEN** dada una sesión de `odontologo`
- **WHEN** cuando abre `/agenda?fecha=2026-11-09&profesional=00000000-0000-4000-8000-0000000000a2`
- **THEN** entonces el pedido a `GET /turnos` no incluye `profesional_id`

#### Scenario: Filtro de sillón disponible
- **GIVEN** dada una sesión de `odontologo`
- **WHEN** cuando elige un sillón en el filtro
- **THEN** entonces el pedido a `GET /turnos` incluye `sillon_id` y no `profesional_id`

#### Scenario: Sin pedidos de pacientes
- **GIVEN** dada una sesión de `odontologo` y una agenda con turnos
- **WHEN** cuando se muestra la agenda y se abre el detalle de un turno
- **THEN** entonces no se hizo ningún pedido a `/pacientes` y se ve el nombre del paciente

#### Scenario: Una sola columna aunque esté vacía
- **GIVEN** dada una sesión de `odontologo` vinculada al profesional A, dos profesionales activos y una respuesta sin elementos
- **WHEN** cuando ve la agenda diaria
- **THEN** entonces hay una sola columna, la de A, y se ve `No hay turnos ni bloqueos en este período.`

#### Scenario: Agrupar por sillón ignorado
- **GIVEN** dada una sesión de `odontologo` vinculada al profesional A
- **WHEN** cuando abre `/agenda?fecha=2026-11-09&columnas=sillon`
- **THEN** entonces hay una sola columna, la de A

### Requirement: Errores al cargar la agenda
Si falla la carga de la agenda o de los catálogos, la pantalla MUST mostrar el mensaje del error, conservar la vista y ofrecer `Reintentar`. Un `403` MUST mostrarse sin cerrar la sesión (DD-33 e). Una recarga fallida del mismo período MUST conservar visibles los datos anteriores.

#### Scenario: Sin conexión
- **GIVEN** dado que el pedido de agenda falla por red
- **WHEN** cuando se muestra la agenda
- **THEN** entonces se ve `No se pudo conectar con el servidor.` y la acción `Reintentar`

#### Scenario: Reintentar con éxito
- **GIVEN** dado un error de carga en pantalla
- **WHEN** cuando se elige `Reintentar` y la API responde `200`
- **THEN** entonces se ve la agenda y desaparece el error

#### Scenario: Catálogos no disponibles
- **GIVEN** dado que `GET /sillones` responde `500`
- **WHEN** cuando se muestra la agenda
- **THEN** entonces se ve `Ocurrió un error. Intentá de nuevo.` y la acción `Reintentar`

#### Scenario: Agenda ajena
- **GIVEN** dada una sesión de `odontologo` y un `GET /turnos` que responde `403` con código `profesional_ajeno` y mensaje "Solo podés consultar tu propia agenda"
- **WHEN** cuando se muestra la agenda
- **THEN** entonces se ve ese mensaje, el token sigue guardado y la ruta no cambia

#### Scenario: Recarga fallida conserva los datos
- **GIVEN** dada una agenda con un turno en pantalla
- **WHEN** cuando se elige `Actualizar` y el pedido falla por red
- **THEN** entonces se sigue viendo el turno junto con el mensaje de error

### Requirement: Respuestas fuera de orden
La agenda MUST mostrar solo la respuesta del último pedido hecho. Una respuesta de un pedido anterior que llega después MUST descartarse, y los datos de otro período o filtro MUST NOT mostrarse como si fueran del actual.

#### Scenario: Navegación rápida
- **GIVEN** dada la agenda del 2026-11-09, un pedido sin responder para el 2026-11-10 y otro posterior para el 2026-11-11
- **WHEN** cuando responde primero el del día 11 y después el del día 10
- **THEN** entonces se ven los turnos del día 11 y no los del día 10

#### Scenario: Error de un pedido anterior
- **GIVEN** dado un pedido anterior sin responder y uno posterior ya respondido con éxito
- **WHEN** cuando el pedido anterior falla
- **THEN** entonces no se muestra ningún error

#### Scenario: Cambio de período sin mezclar datos
- **GIVEN** dada la agenda del 2026-11-09 con un turno en pantalla
- **WHEN** cuando se pide el día siguiente y la respuesta aún no llegó
- **THEN** entonces no se ve el turno del día 9 y se ve `Cargando agenda…`

#### Scenario: Lectura vieja después de un alta
- **GIVEN** dado un `GET /turnos` del período sin responder y un alta exitosa cuya relectura ya respondió con el turno creado
- **WHEN** cuando llega la respuesta de la lectura anterior, sin ese turno
- **THEN** entonces se sigue viendo el turno creado

### Requirement: Actualización manual
La agenda SHALL ofrecer una acción `Actualizar` que vuelve a pedir el período en curso, manteniendo a la vista los datos actuales hasta recibir la respuesta.

#### Scenario: Actualizar
- **GIVEN** dada una agenda con un turno en pantalla
- **WHEN** cuando se elige `Actualizar` y la respuesta aún no llegó
- **THEN** entonces se hizo un pedido nuevo del mismo período y el turno sigue visible

#### Scenario: Cambio hecho por otro usuario
- **GIVEN** dada una agenda con un turno en pantalla que otro usuario canceló
- **WHEN** cuando se elige `Actualizar`
- **THEN** entonces el turno no se ve en la agenda, porque los cancelados están ocultos

### Requirement: Accesibilidad de la agenda
Cada columna MUST tener un nombre accesible con su día o recurso y sus elementos MUST estar en orden cronológico en el documento. Los turnos MUST poder elegirse con el teclado. Los controles de vista, filtros y navegación MUST tener etiqueta.

#### Scenario: Turno elegible con el teclado
- **GIVEN** dada una agenda con un turno
- **WHEN** cuando se lleva el foco al turno y se presiona Enter
- **THEN** entonces se abre su detalle

#### Scenario: Orden cronológico
- **GIVEN** dados en una columna un turno a las 11:00 y otro a las 09:00
- **WHEN** cuando se lee la columna en orden del documento
- **THEN** entonces el de las 09:00 está antes que el de las 11:00

#### Scenario: Filtros etiquetados
- **WHEN** cuando la recepcionista busca los filtros por su etiqueta
- **THEN** entonces encuentra `Profesional`, `Sillón` y `Mostrar cancelados`

#### Scenario: Nombre de las columnas de la semana
- **GIVEN** dada la vista semanal del 2026-11-09 al 2026-11-15
- **WHEN** cuando se buscan las columnas por su nombre accesible
- **THEN** entonces se encuentran `Lunes 09/11` y `Domingo 15/11`

#### Scenario: Nombre de las columnas del día
- **GIVEN** dada la vista diaria con la columna de "Ana Ficticia"
- **WHEN** cuando se busca la columna por su nombre accesible
- **THEN** entonces se encuentra `Ficticia, Ana`
