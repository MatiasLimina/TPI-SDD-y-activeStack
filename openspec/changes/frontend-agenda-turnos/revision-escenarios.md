# Revisión de escenarios — frontend-agenda-turnos (C-15)

> **Actualización**: los hallazgos H1 a H24 se resolvieron con `/opsx:update` el 2026-11-10. Respuestas aprobadas, todas con la opción (a): **P1**, solo cuentan los elementos visibles; sin ninguno, el mensaje de período vacío, y si solo hay cancelados, un texto propio que invita a mostrarlos; un profesional desactivado sin nada visible no tiene columna. **P2**, el odontólogo ve una sola columna, la de su profesional, aunque esté vacía. **P3**, la duración es obligatoria al reprogramar, con error propio y sin pedido. **P4**, un formulario intacto muestra `No hiciste cambios.` y no envía nada; `sillon_id: null` solo acompaña a otro cambio. **P5**, el valor rechazado sigue como opción marcada `(inactivo)` hasta que se cambie. **P6**, los carriles se calculan sobre las filas redondeadas a 5 minutos. **P7**, una `fecha` con año fuera de 1000 a 9998 es inválida y cae en el valor por defecto. **P8**, `noValidate`, con obligatorios propios y el resto a cargo de la API. Lo que esta revisión dejó sin verificar quedó comprobado: `AwareDatetime` rechaza un desfasaje con segundos con un `422` de validación sobre `inicio` (design D14).
>
> **Actualización 2**: los hallazgos H25 a H39 de la Revisión 2 se resolvieron con `/opsx:update` el 2026-11-10. Respuestas aprobadas, todas con la opción (a): **P9**, fecha, hora o sillón requerido vacíos al reprogramar muestran `Completá este campo.` sin pedido, antes de comparar. **P10**, el odontólogo de un profesional desactivado tiene una columna aunque esté vacía; la regla de desactivados vale para la recepcionista. **P11**, un valor rechazado que es el actual del turno sigue como opción mientras lo sea. **P12**, el filtro de profesional deja una columna solo al agrupar por profesional; al agrupar por sillón siguen los sillones; el filtro de sillón al agrupar por sillón deja ese sillón y `Bloqueos` si hay; un id inexistente no tiene columna. **P13**, un recurso ausente del catálogo tiene columna con el texto genérico, sin releer catálogos con `Actualizar`. **P14**, si falla la relectura de catálogos con el formulario abierto, este sigue abierto y el error se muestra como general. **P15**, el detalle se cierra al abrir un formulario; `Volver` o el éxito llevan a la agenda.

- Fecha: 2026-11-10
- Specs revisados: `specs/frontend-agenda/spec.md` (19 requirements, 58 escenarios), `specs/frontend-turnos/spec.md` (20, 63), `specs/frontend-sesion/spec.md` (1, 4). Total: 40 requirements, 125 escenarios.
- Reglas aplicables: US-004, US-005, US-006, US-008; RN-AG-03, 04, 07, 08, 10, 12, 13, 14; RN-AU-02; RN-CU-02, 04; DD-06, DD-14, DD-15, DD-21 (b, c), DD-22, DD-23, DD-25 (b, g), DD-26 (a, g y consecuencias), DD-27 (a), DD-30 (b, d, f), DD-31 (a, b, e, g, o), DD-32 (a-l), DD-33 (a, d, e, k, l); SU-07, SU-08.
- Contrato contrastado con: `backend/app/api/turnos.py`, `recursos.py`, `pacientes.py`, `backend/app/domain/turnos.py`, `application/validacion_turno.py`, `reprogramar_turno.py`, `repositorio_turnos.py`, `openspec/specs/{consulta-agenda,agenda-turnos,frontend-sesion,frontend-cliente-http}`, `frontend/src/shared/api/*`, `frontend/src/test/*`.
- Veredicto: **CORREGIR ANTES DE APPLY**
- Conteo: 1 BLOQUEANTE, 9 MAYOR, 12 MENOR, 2 SUGERENCIA.

El grueso del spec está bien anclado: los códigos de error, las formas de los cuerpos, los campos de `TurnoAgendaOut`, los parámetros de `GET /turnos`, el borde `inicio = reloj` y las fechas de los escenarios (lunes 2026-11-09, jueves 12, domingo 15) coinciden con el backend y el calendario. Los problemas son pocos en cantidad de texto a tocar: una frase que contradice DD-32 e, la grilla sin contrato y ocho casos que la KB o el propio diseño dejan sin resolver.

## Cobertura

E = esperado, N = error de negocio (una regla o la API rechaza), B = borde.

### frontend-agenda

| Requirement | Escenarios | E | N | B | Reglas cubiertas |
|-------------|-----------:|:-:|:-:|:-:|------------------|
| Pantalla de agenda | 3 | Sí | — | Sí | US-008, DD-32 a |
| Horarios en la zona del consultorio | 2 | Sí | — | Sí | RN-CU-04, DD-06, DD-32 g |
| Día actual del consultorio | 2 | — | — | Sí | RN-CU-04 |
| Vistas diaria y semanal | 4 | Sí | — | Sí | US-008, DD-32 d, DD-27 a |
| Navegación entre períodos | 3 | Sí | — | Sí | US-008 |
| La vista se conserva en la URL | 4 | Sí | — | Sí | DD-31 o, DD-32 l |
| Filtros por profesional y por sillón | 5 | Sí | — | Sí | US-008, DD-32 h, DD-26 g |
| Columnas de la vista diaria | 3 | Sí | — | Sí | DD-30 d, DD-26 g |
| Datos visibles de cada turno | 3 | Sí | — | Sí | DD-32 j, DD-08 |
| Nombres de los recursos | 2 | Sí | — | Sí | DD-26 g |
| Turnos cancelados | 3 | Sí | — | Sí | DD-32 f, RN-AG-07 |
| Elementos superpuestos en una columna | 3 | Sí | — | Sí | RN-AG-03, DD-30 b |
| Elementos que cruzan días | 3 | Sí | — | Sí | DD-32 e, DD-30 f |
| Bloqueos en la agenda | 1 | Sí | — | — | DD-30 |
| Agenda del odontólogo | 4 | Sí | Sí | Sí | RN-AU-02, DD-31 b, DD-32 i |
| Errores al cargar la agenda | 5 | — | Sí | Sí | DD-33 e, DD-32 i |
| Respuestas fuera de orden | 3 | — | — | Sí | D13 |
| Actualización manual | 2 | Sí | — | — | D13 |
| Accesibilidad de la agenda | 3 | Sí | — | — | D17 |

### frontend-turnos

| Requirement | Escenarios | E | N | B | Reglas cubiertas |
|-------------|-----------:|:-:|:-:|:-:|------------------|
| Operaciones solo para la recepcionista | 2 | Sí | Sí | — | RN-AU-02, matriz de 03 |
| Operaciones según el estado del turno | 3 | Sí | Sí | Sí | RN-AG-13, DD-14, DD-23 d |
| Formulario de nuevo turno | 3 | Sí | Sí | — | DD-21 c, US-004 |
| Sillón según la prestación | 2 | Sí | — | Sí | DD-09, RN-AG-10, DD-21 a |
| Duración por defecto y ajustable | 2 | Sí | — | — | RN-AG-04 |
| Inicio con zona horaria | 2 | Sí | — | Sí | RN-CU-04, DD-15; SU-08 sin discriminar (H10) |
| Alta exitosa | 2 | Sí | — | Sí | US-004 |
| Búsqueda de pacientes | 4 | Sí | — | Sí | DD-31 e |
| Resultados de la búsqueda de pacientes | 6 | Sí | Sí | Sí | DD-31 g, DD-21 c |
| Formulario de reprogramación | 3 | Sí | — | Sí | DD-23 b, DD-26 g |
| Reprogramación parcial | 6 | Sí | — | Sí | DD-23 a, DD-26 |
| Cancelación con confirmación | 4 | Sí | — | Sí | US-006, DD-14 |
| Conflicto por solapamiento | 3 | — | Sí | — | RN-AG-01, 02, 14, DD-21 b |
| Reglas de agenda rechazadas por la API | 5 | — | Sí | Sí | RN-AG-04, 05, 06, 10, 12 |
| Referencias inválidas | 2 | — | Sí | — | DD-21 c, DD-26 |
| Errores de validación por campo | 2 | — | Sí | Sí | DD-33 l, `frontend-cliente-http` |
| Turno que cambió mientras se editaba | 3 | — | Sí | — | DD-22, DD-23 c, d |
| Conservación de los datos ante un error | 2 | Sí | Sí | — | US-005 |
| Falta de permiso y fallas de red | 3 | — | Sí | Sí | DD-33 a, d, e |
| Accesibilidad de los formularios | 4 | Sí | — | — | D17 |

### frontend-sesion

| Requirement | Escenarios | E | N | B | Reglas cubiertas |
|-------------|-----------:|:-:|:-:|:-:|------------------|
| Layout de la aplicación (MODIFIED) | 4 | Sí | Sí | — | DD-33 g, RN-AU-03 |

C1 (mínimo de tres tipos) se cumple en el conjunto. C3 (scope): ningún escenario invade C-16 ni depende de algo inexistente; `GET /disponibilidad` no se usa y US-007 sigue en el backlog. C8: datos ficticios, sin secretos; el test de concurrencia de RN-AG-09 es del backend y ya existe.

Reglas del scope sin escenario: **SU-08** (el desfasaje IANA tiene una cláusula MUST, pero ningún escenario la distingue de un `-03:00` fijo: H10); **RN-AU-02 en las columnas del odontólogo** (H5); **DD-23 a en la duración vaciada** (H6).

## Hallazgos

### H1 — "El día local de su inicio" contradice DD-32 e · BLOQUEANTE
- **Dónde**: `frontend-agenda`, requirement "Horarios en la zona del consultorio", última oración.
- **Problema**: dice "Un turno MUST ubicarse en el día local de su `inicio` en esa zona". Leído como contrato, un turno de 23:30 a 00:30 va solo en el día de inicio, lo que contradice al requirement "Elementos que cruzan días" del mismo spec. La intención es otra: que el día sea el de Buenos Aires y no el de UTC o del navegador.
- **Fuente**: DD-32 e; `consulta-agenda`, escenario "Turno que cruza la medianoche local aparece en ambos días"; control C2.
- **Sugerencia**: reescribir como "Un turno MUST ubicarse en el o los días locales que abarca, calculados en esa zona y nunca en la del navegador". El cambio no toca los escenarios.

### H2 — La grilla de D1 no tiene contrato · MAYOR
- **Dónde**: `frontend-agenda`, falta un requirement. Afecta a D1 de `design.md` y a las tareas 4.2 y 10.1.
- **Problema**: ningún requirement exige eje horario, filas de 5 minutos ni que un elemento quede en la fila de su hora. Una lista ordenada pasa los 58 escenarios, y la regla dura prohíbe implementar en Apply lo que no está en el spec. Lo que jsdom sí no puede probar es la geometría; las filas salen de una función pura y sí se pueden afirmar. El scroll a las 08:00 solo se verifica a mano (tarea 10.2), y el spec debería decirlo.
- **Fuente**: `CLAUDE.md` §Reglas duras §Proceso; D1 y D15 de `design.md`; DD-15; controles C2 y C5.
- **Sugerencia**: requirement "Ubicación en la grilla", con escenarios sobre la función pura: GIVEN un turno de 10:00 a 10:45 hora de Buenos Aires, WHEN se calcula su ubicación, THEN ocupa 9 filas de 5 minutos desde la fila 120 (contando desde 0); un turno de 00:00 empieza en la primera fila; uno de 23:55 a 00:00 termina en la última. Declarar en el requirement que el scroll inicial y el ancho de carril son de verificación manual.

### H3 — Fin exacto a medianoche y borde de la semana · MAYOR
- **Dónde**: `frontend-agenda`, requirement "Elementos que cruzan días", falta. Tarea 4.2.
- **Problema**: en la vista semanal la API entrega completo un bloqueo del 2026-11-10 20:00 al 2026-11-11 00:00. Con `[)` no toca el día 11, pero ningún escenario lo dice y `segmentosPorDia` podría generar un segmento de 0 minutos. El otro borde es el fin de semana visible: un bloqueo del domingo 2026-11-15 22:00 al lunes 2026-11-16 02:00 debe verse solo en el domingo de esa semana y, en la siguiente, solo en el lunes, con los extremos reales en ambas.
- **Fuente**: RN-AG-03, DD-32 b, e; `consulta-agenda`, escenarios "Bloqueo que termina justo al empezar el día" y "Bloqueo que empieza justo al terminar el día".
- **Sugerencia**: dos escenarios sobre `segmentosPorDia`, con los valores de arriba: el primero THEN un solo segmento, en el día 10, hasta el final del día; el segundo THEN un segmento por semana visible e indicando `15/11 22:00` y `16/11 02:00`.

### H4 — Con cancelados ocultos, no está definido qué es un "elemento" · MAYOR
- **Dónde**: `frontend-agenda`, requirements "Pantalla de agenda", "Columnas de la vista diaria" y "Turnos cancelados". Consecuencia de D3.
- **Problema**: si la respuesta trae solo turnos `cancelado` y la casilla está apagada, el spec no dice si se ve `No hay turnos ni bloqueos en este período.` (falso: la API trajo turnos) o una grilla vacía sin explicación. Lo mismo con un profesional desactivado cuyo único turno está cancelado y oculto: ¿tiene columna? El resultado del test cambia según la lectura.
- **Fuente**: D3 de `design.md`; DD-32 f; control C7.
- **Sugerencia**: pregunta P1 más abajo. No se propone un escenario hasta decidirla.

### H5 — Columnas del odontólogo sin definir · MAYOR
- **Dónde**: `frontend-agenda`, requirements "Columnas de la vista diaria" y "Agenda del odontólogo".
- **Problema**: "Columnas de la vista diaria" habla solo de la recepcionista y ningún escenario fija qué columnas ve el odontólogo. `GET /profesionales` le responde a ambos roles, así que la implementación directa ("una columna por profesional activo") le mostraría columnas vacías de sus colegas, contra "solo su agenda". Tampoco está dicho qué se ve si no tiene turnos ese día.
- **Fuente**: RN-AU-02; US-008 ("El odontólogo solo ve sus turnos"); DD-32 i; D16.
- **Sugerencia**: pregunta P2. Escenario candidato, sujeto a esa respuesta: GIVEN una sesión de `odontologo` vinculada al profesional A y dos profesionales activos, WHEN ve la agenda diaria, THEN hay una sola columna, la de A, aunque no tenga elementos.

### H6 — Duración vaciada al reprogramar · MAYOR
- **Dónde**: `frontend-turnos`, requirements "Formulario de reprogramación" y "Reprogramación parcial", falta.
- **Problema**: el campo viene precargado y el spec no dice qué pasa si se lo vacía. En el alta, vacío significa "la de la prestación"; acá esa semántica no existe: lo omitido conserva el valor y `duracion_min: null` da `422` por el validador de `ReprogramacionIn`. Si D10 compara y manda `null`, el usuario ve `Revisá este campo.` o, según la implementación, un "sin cambios" engañoso.
- **Fuente**: DD-23 a ("para volver a la duración de la prestación hay que informarla"); `backend/app/api/turnos.py`, `_sin_nulos_en_campos_obligatorios`; D9 y D10.
- **Sugerencia**: pregunta P3. Escenario candidato: GIVEN el formulario de un turno de 45 minutos, WHEN se vacía la duración y se envía, THEN se ve un error en `Duración` y no se hace ningún `PATCH`.

### H7 — "Sin cambios" choca con el `sillon_id` nulo forzado · MAYOR
- **Dónde**: `frontend-turnos`, requirement "Reprogramación parcial", escenarios "Sin cambios" y "Prestación que dejó de requerir sillón".
- **Problema**: el requirement dice "Sin cambios, MUST informarlo sin hacer ningún pedido" y "Si la prestación ya no requiere sillón y el turno tiene uno, MUST enviar `sillon_id` nulo". Con el formulario intacto sobre ese turno, los dos MUST se contradicen. D10 inclina hacia un `PATCH` ("la comparación produce `sillon_id: null`"), pero el escenario solo cubre el caso en que además cambia la hora.
- **Fuente**: DD-23 a, DD-26 (consecuencias), D10; control C7.
- **Sugerencia**: pregunta P4.

### H8 — Error en un campo que no está en pantalla · MAYOR
- **Dónde**: `frontend-turnos`, requirement "Reglas de agenda rechazadas por la API". D7 y D12.
- **Problema**: el `requiere_sillon` del catálogo cargado puede estar viejo (DD-26 lo permite y C-16 lo edita). Si la API responde `sillon_requerido` con el campo oculto, D12 lo destina al campo `Sillón`, que no existe en la pantalla: el formulario no se envía y no se ve ningún error. Además D7 relee los catálogos solo ante `referencia_invalida`, así que reintentar da lo mismo. El caso simétrico es `sillon_no_corresponde`, que se muestra bien pero tampoco refresca el catálogo.
- **Fuente**: DD-26 (consecuencias); RN-AG-10; requirement "Conservación de los datos ante un error"; D7 y D12.
- **Sugerencia**: GIVEN un formulario con una prestación que según el catálogo no requiere sillón y una respuesta `422 sillon_requerido`, WHEN se recibe, THEN se piden otra vez los catálogos, el campo `Sillón` se muestra y contiene `Esta prestación requiere un sillón.`

### H9 — `referencia_invalida` contra "todos los datos cargados" · MAYOR
- **Dónde**: `frontend-turnos`, requirements "Referencias inválidas", "Conservación de los datos ante un error" y "Formulario de nuevo turno".
- **Problema**: tras `referencia_invalida` se releen los catálogos y el selector de alta ofrece solo activos: la opción elegida desaparece. A la vez, "todos los datos cargados" MUST seguir. Un `<select>` controlado con un valor sin opción queda en un estado indefinido, y el mensaje `El sillón está inactivo.` apuntaría a un campo vacío.
- **Fuente**: DD-21 c; escenario "Sillón inactivo"; requirement "Conservación de los datos ante un error".
- **Sugerencia**: pregunta P5.

### H10 — Ningún escenario distingue la zona IANA de un `-03:00` fijo · MAYOR
- **Dónde**: `frontend-turnos`, requirement "Inicio con zona horaria"; tarea 3.3.
- **Problema**: el único valor probado es `2026-11-12`, y un `-03:00` escrito a mano pasa el test. La tarea lo compensa con un `grep`, que no prueba comportamiento. El enfoque de D14 **sí es correcto para fechas históricas**, y eso da el test que falta: en Node 24 esa zona responde `GMT-02:00` para el 2008-01-15 y `GMT-03:00` para el 2009-03-16. Pero para fechas muy viejas devuelve desfasajes con segundos: `GMT-04:16:48` (1900) y `GMT-03:53:48` (1800). Una fecha así se puede tipear en un `type="date"`; el spec no dice qué hace la función. El camino válido solo manda fechas futuras (RN-AG-12), así que el daño se limita a no romper.
- **Fuente**: SU-08 ("usar zona IANA igualmente"); RN-CU-04; RN-AG-12; D14. Comprobado con `Intl` en Node 24.19.
- **Sugerencia**: escenario de función pura: GIVEN la fecha `2008-01-15` y la hora `10:00`, THEN el resultado es `2008-01-15T10:00:00-02:00`. Otro: GIVEN la fecha `1900-01-15`, WHEN se envía, THEN no hay una excepción sin controlar y el error de la API se muestra en `Hora`. No se comprobó qué responde Pydantic a un desfasaje con segundos.

### H11 — "Hora local" es ambigua en un spec de frontend · MENOR
- **Dónde**: `frontend-agenda`: "Agenda de la recepcionista", "Volver a hoy", "Fecha inválida", "Turno que cruza la medianoche", "Bloqueo de varios días", "Bloqueo que no respeta la grilla". `frontend-turnos`: "Turno ya iniciado", "Turno por iniciar", "Datos precargados", "Solo cambia la hora".
- **Problema**: en los specs de backend "hora local" solo puede ser Buenos Aires. Acá compite con la zona del navegador, y la suite corre en `Asia/Tokyo`. D15 y las fábricas lo resuelven en la práctica, por eso es MENOR.
- **Fuente**: control C6; RN-CU-04.
- **Sugerencia**: definir el término una vez en cada spec ("hora local = `America/Argentina/Buenos_Aires`, nunca la del navegador") o usar el desfasaje.

### H12 — Citas que atribuyen a la KB reglas nuevas · MENOR
- **Dónde**: "Turnos cancelados" cita DD-32 f para "MUST ocultarse por defecto"; "Formulario de nuevo turno" cita DD-21 c para "ordenados por nombre".
- **Problema**: DD-32 f solo sostiene que la API trae los cancelados, y DD-21 c, que un recurso inactivo se rechaza. Ocultar es D3, y el orden ya lo da la API (`repositorio_recursos.py`). Citarlas así presenta una decisión pendiente como si estuviera tomada.
- **Fuente**: control C2; DD-21 c; DD-32 f.
- **Sugerencia**: citar D3 y D9 (futura DD-34); agregar un escenario de orden o quitar la cláusula.

### H13 — ¿Los carriles usan el intervalo real o el redondeado? · MENOR
- **Dónde**: `frontend-agenda`, "Elementos superpuestos" y "Elementos que cruzan días". D1 y D4.
- **Problema**: dos bloqueos de 10:00 a 10:03 y de 10:03 a 10:05 son contiguos (`[)`), pero redondeados ocupan la misma fila. Con el criterio real compartirían carril y se taparían, contra "ninguno tape a otro".
- **Fuente**: DD-30 b, f; RN-AG-03.
- **Sugerencia**: pregunta P6.

### H14 — Casos de columnas y filtros sin escenario · MENOR
- **Dónde**: `frontend-agenda`, "Columnas de la vista diaria", "Filtros" y "La vista se conserva en la URL".
- **Problema**: faltan las columnas `Sin sillón` y `Bloqueos` cuando no hay nada que poner (D1 dice "cuando corresponda"; el requirement, no); un filtro por profesional inactivo sin elementos, donde "una sola columna" choca con "columna solo si tiene elementos"; un UUID bien formado que no existe (`200` vacío, DD-32 l) y el valor que muestra el selector; `columnas=sillon` en vista semanal o con sesión de odontólogo.
- **Fuente**: DD-30 d, DD-32 l, D1, D6, D16.
- **Sugerencia**: un escenario por caso, o dejar explícito en el requirement que se ignoran.

### H15 — Navegación y "hoy" a nivel de pantalla · MENOR
- **Dónde**: "Navegación entre períodos", "Vistas diaria y semanal", "Día actual del consultorio"; tarea 3.2.
- **Problema**: no hay escenario de `Hoy` en vista semanal, de pasar de semana a día ni de una semana que cruza mes o año (2026-12-28 a 2027-01-03). Los dos escenarios de "Día actual" afirman un `GET`, pero la tarea 3.2 prueba solo `hoyLocal`: ninguna tarea abre `/agenda` sin parámetros con el reloj de esos escenarios.
- **Fuente**: US-008, D2, control C9.
- **Sugerencia**: agregar los escenarios y sumar a 6.2 la verificación de pantalla.

### H16 — `fecha` en los extremos del calendario · MENOR
- **Dónde**: "La vista se conserva en la URL"; tarea 4.1.
- **Problema**: `fecha=9999-12-31` pasa la validación de formato y calendario, pero la API responde `422 rango_invalido`, que se muestra con su texto técnico y un `Reintentar` inútil. Además, `Date.UTC` interpreta los años de 0 a 99 como 1900 a 1999 (comprobado: `Date.UTC(50, 0, 15)` es 1950), de modo que `fecha=0050-01-15` calcula otro día.
- **Fuente**: `consulta-agenda`, escenario "Fin de rango no representable"; D14.
- **Sugerencia**: pregunta P7.

### H17 — Validación nativa contra "la API decide" · MENOR
- **Dónde**: `frontend-turnos`, "Formulario de nuevo turno" y "Reglas de agenda rechazadas"; D9.
- **Problema**: con `step=5`, `min` y `max` y sin `noValidate`, el navegador frena un `7`, y jsdom también al hacer clic en enviar: `duracion_invalida` e `inicio_no_alineado` no llegarían a la API, y `Elegí un paciente.` no aparecería si otro campo nativo falla antes. D9 dice lo contrario. El spec no define cuál rige.
- **Fuente**: D9; DD-15.
- **Sugerencia**: pregunta P8.

### H18 — Relecturas sin escenario · MENOR
- **Dónde**: "Conflicto por solapamiento", "Reglas de agenda rechazadas", "Respuestas fuera de orden", "Alta exitosa"; D13.
- **Problema**: D13 relee "tras un error que revela un cambio", pero el spec solo lo exige en `409 solapamiento` y turno obsoleto; `turno_en_bloqueo` también revela un cambio ajeno y queda indefinido. Falta el caso de una lectura vieja del mismo período que llega después de la relectura posterior a un alta (el turno recién creado desaparecería) y el de una relectura fallida tras un alta exitosa.
- **Fuente**: D13; requirement "Respuestas fuera de orden".
- **Sugerencia**: un escenario por caso en la tarea 5.2 o 9.2.

### H19 — Bloqueo sin profesional en la vista semanal · MENOR
- **Dónde**: `frontend-agenda`, "Bloqueos en la agenda".
- **Problema**: "cuando las columnas no lo indican" está escrito solo para turnos. En la semana sin filtro, un bloqueo no diría de quién es; D1 promete que "cada tarjeta" lo nombra.
- **Fuente**: D1; DD-30 d.
- **Sugerencia**: escenario análogo a "Semana con varios profesionales".

### H20 — Escenarios imprecisos o ausentes · MENOR
- **Dónde y problema**:
  - "Cambio hecho por otro usuario": "deja de verse como programado" no es un `assert`; con D3 el turno desaparece.
  - "Solo cambia la hora": el GIVEN no da la fecha que el THEN exige (2026-11-12).
  - "Cancelación con confirmación": exige mostrar paciente, día y hora, sin escenario ni formato.
  - "Conflicto por solapamiento": sin el texto de dos recursos (`... el profesional y el paciente.`). El orden lo fija `ORDEN_RECURSOS` del backend.
  - "Reprogramación parcial": sin escenario de solo sillón o solo duración.
  - "Accesibilidad de la agenda": sin escenario del nombre accesible de la columna ni formato del día.
  - "Búsqueda de pacientes": no dice qué `q` se envía con ` pe `.
- **Fuente**: control C5; D10, D11, D17.
- **Sugerencia**: completar los valores al tocar cada requirement.

### H21 — El reemplazo de `showModal` no prueba que sea modal · MENOR
- **Dónde**: "Accesibilidad de los formularios"; tarea 2.3; D6.
- **Problema**: confirmado que jsdom 31 no implementa `showModal`. Un reemplazo mínimo no vuelve inerte el fondo, así que "abrirse como diálogos modales" pasa aunque el componente use solo `open`. Tampoco hay escenario para `Esc` o el evento `close`: si el estado de React no se sincroniza, el diálogo no vuelve a abrir, y `Esc` puede descartar un formulario cargado.
- **Fuente**: D6, D15, D17; riesgo declarado en `design.md`.
- **Sugerencia**: que el reemplazo sea un espía y el escenario afirme que se llamó `showModal`; despachar `cancel` y `close` en un escenario de `Dialogo`; mantener foco y `Esc` real en la tarea 10.2.

### H22 — Escenarios cubiertos solo a nivel de requirement · MENOR
- **Dónde**: `tasks.md`: "Reprogramación exitosa" (9.4 no lo nombra) y "Diálogo con título".
- **Problema**: el control C9 pide una tarea por escenario. Se baja de MAYOR porque las tareas nombran el requirement y la 12.2 recorre todos los escenarios contra los tests.
- **Fuente**: control C9.
- **Sugerencia**: nombrarlos en 9.4 y 9.1.

### H23 — Dejar escrita la "última escritura gana" · SUGERENCIA
- **Dónde**: "Turno que cambió mientras se editaba"; D13.
- **Problema**: es consistente con DD-23 (no hay versión), con el `FOR UPDATE` de `obtener_para_actualizar` y con la auditoría (DD-25 b guarda la instantánea completa, así que la pisada queda trazada). Pero con envío parcial el resultado puede ser una mezcla que nadie vio (profesional de un usuario, hora del otro), y hoy eso solo figura en el diseño.
- **Fuente**: D10, D13, DD-23, DD-25 b.
- **Sugerencia**: escenario: GIVEN un formulario abierto y un cambio ajeno de profesional, WHEN se cambia solo la hora y la API responde `200`, THEN el `PATCH` lleva solo `inicio` y la relectura muestra el profesional ajeno. Registrar la mezcla en DD-34.

### H24 — Enter dentro del selector de paciente · SUGERENCIA
- **Dónde**: "Accesibilidad de los formularios", "Selector de paciente con teclado".
- **Problema**: el selector vive dentro de un `<form>`: Enter en el campo de búsqueda o en un `<button>` sin `type="button"` envía el formulario. El escenario solo afirma que queda elegido.
- **Fuente**: D8, D17.
- **Sugerencia**: agregar al THEN "y no se hizo ningún `POST /turnos`", y un caso de Enter en el campo.

## Revisión de las decisiones [A confirmar]

| Decisión | ¿Fundada en la KB? | Observación |
|----------|--------------------|-------------|
| D1 | Regla nueva de UI; solo las filas de 5 minutos se apoyan en DD-15 | No contradice nada, pero falta en el spec (H2) |
| D2 | Fundada: DD-27 a, DD-32 d y el escenario "Agenda semanal" de `consulta-agenda`. Abrir en la vista diaria es preferencia de UI | Sin observaciones |
| D3 | Regla nueva, compatible: ni DD-32 f ni US-008 exigen ver los cancelados | H4, H12. Costo a sopesar: el odontólogo no ve una cancelación sin activar la casilla |
| D5 | Técnica; alineada con DD-33 (sin kit de UI) | Sin observaciones |
| D6 | Técnica, y necesaria: no existe `GET /turnos/{id}` (verificado). DD-31 o respalda no poner pacientes en la URL | H21 |
| D7 | Técnica; DD-26 a confirma que los listados traen inactivos | H8, H9: la relectura debería ampliarse |
| D8 | Inactivo no elegible: fundada (DD-21 c, DD-31 g). 300 ms, mínimo de 2 y `limite=20`: parámetros nuevos de UI, sin conflicto con DD-31 e, que habla de la API | H24 |
| D9 | Duración por defecto: fundada (RN-AG-04). Fecha por defecto: UI | H17 |
| D10 | Envío parcial: fundado (DD-23 a). No enviar sin cambios: regla nueva, compatible con DD-25 g, que audita solo operaciones confirmadas | H6, H7 |
| D12 | Fundada en el contrato real; solo la redacción es nueva. Cubre todos los códigos alcanzables de los formularios: `campo_no_editable` no se produce y, si llegara, su `mensaje` ya está escrito para la recepcionista (DD-23 b) | H8. `rango_invalido` y `profesional_ajeno` son de la carga, fuera de este traductor (H16) |
| D13 | Regla nueva, consistente con DD-23 y con la auditoría de C-07 | H18, H23. Debe quedar en DD-34 como limitación aceptada |

## Preguntas abiertas

Ninguna tiene respuesta en la KB; las opciones son propuestas. La recomendada va primero.

- **P1 (H4)**: con cancelados ocultos, ¿qué cuenta como elemento? (a) Solo lo visible: sin elementos visibles se usa el mensaje vacío, y si solo hay cancelados, un texto propio que invite a activar la casilla; un profesional desactivado sin nada visible no tiene columna. (b) Todo lo que trae la API, con una grilla vacía.
- **P2 (H5)**: ¿qué columnas ve el odontólogo en la vista diaria? (a) Una sola, la de su profesional (claim `profesional_id`), aunque esté vacía. (b) Solo si tiene elementos.
- **P3 (H6)**: duración vaciada al reprogramar. (a) Campo obligatorio, con error propio y sin pedido. (b) Vacío significa volver a la de la prestación, enviando ese valor explícito (DD-23 a).
- **P4 (H7)**: formulario intacto sobre un turno con sillón sobrante. (a) `No hiciste cambios.` y sin pedido; el `sillon_id` nulo acompaña solo a otro cambio, como dice el escenario actual. (b) Enviar `{"sillon_id": null}`.
- **P5 (H9)**: valor rechazado tras `referencia_invalida`. (a) Mantenerlo como opción marcada `(inactivo)` hasta que se cambie, igual que al reprogramar. (b) Limpiar el campo y mostrar el error.
- **P6 (H13)**: carriles. (a) Sobre las filas redondeadas; la cláusula de contiguos se aplica a los intervalos alineados. (b) Sobre el intervalo real, aceptando el solape visual en ese caso raro.
- **P7 (H16)**: rango válido de `fecha`. (a) Tratar como inválidos los años fuera de un rango técnico (1000 a 9998), que caen en el valor por defecto. (b) No acotar y mostrar el error.
- **P8 (H17)**: validación del formulario. (a) `noValidate`, con obligatorios propios y el resto en la API, una sola vía de error, como pide D9. (b) Validación nativa, renunciando a mostrar esos `422`.

## Fuera de esta revisión

- No se corrió código del change: no existe todavía. Sí se comprobó `Intl` y `Date.UTC` en Node 24.19.
- No se verificó qué responde `AwareDatetime` a un desfasaje con segundos, porque no hay un entorno de Python del backend en la máquina.
- La geometría real de la grilla, el scroll inicial, el foco atrapado y `Esc` no se pueden probar en jsdom; quedan en la tarea 10.2, que hace el usuario.
- No son hallazgos: el comportamiento ya entregado del backend, las pantallas de C-16, la UI de recordatorios y de auditoría, y las fallas previas de `openspec validate --specs --strict` en otros cuatro specs.

## Revisión 2 — 2026-11-10

- Fecha: 2026-11-10, sobre `d99fc04` (después de `/opsx:update`).
- Specs revisados: `specs/frontend-agenda/spec.md` (20 requirements, 84 escenarios), `specs/frontend-turnos/spec.md` (20, 83), `specs/frontend-sesion/spec.md` (1, 4). Total: 41 requirements, 171 escenarios, contados con `grep`; 46 son nuevos respecto de la revisión 1.
- Reglas aplicables: las de la revisión 1, más DD-26 h, y las decisiones aprobadas D1 a D13 y P1 a P8, que se registran como DD-34 (tarea 11.1). No se reabre ninguna.
- Veredicto: **CORREGIR ANTES DE APPLY**
- Conteo: 0 BLOQUEANTE, 3 MAYOR, 11 MENOR, 1 SUGERENCIA.

Los 24 hallazgos anteriores se atendieron y el update no introdujo errores de cálculo: filas, carriles, fechas y días de la semana de los escenarios nuevos son correctos. Lo que queda son tres casos en los que una decisión aprobada no llegó entera a los escenarios: dos son justamente el cruce de P1 con el filtro y el orden de D10. Se corrigen con pocas líneas y sin decisiones de fondo, salvo las preguntas de abajo.

### Estado de H1 a H24

Comprobados uno por uno en los artefactos, no en la nota de actualización.

| Hallazgo | Estado | Evidencia |
|----------|--------|-----------|
| H1 | Resuelto | "Horarios en la zona del consultorio": "el o los días locales que abarca" |
| H2 | Resuelto | Requirement "Ubicación en la grilla", con 5 escenarios y lo manual declarado; tareas 4.2 y 4.3 |
| H3 | Resuelto | "Bloqueo que termina justo a la medianoche" y "Bloqueo que cruza el fin de la semana visible" |
| H4 | **Parcial** | "Solo hay turnos cancelados ocultos" y "Profesional desactivado con solo cancelados ocultos" lo resuelven sin filtro; con filtro, ver H25 |
| H5 | Resuelto | "Una sola columna aunque esté vacía"; queda un caso derivado (H28) |
| H6 | Resuelto | "Duración vaciada" con `Ingresá la duración.`; el mismo vacío en hora y fecha es H27 |
| H7 | Resuelto | "Sin cambios con un sillón sobrante" y "solo junto con otro cambio" |
| H8 | Resuelto | "Sillón requerido con el catálogo desactualizado" y el simétrico |
| H9 | Resuelto | "Sillón inactivo" y "Cambiar el valor rechazado"; casos derivados en H29 y H30 |
| H10 | Resuelto | Tres escenarios de desfasaje. Recomprobado: `Intl` en Node da `GMT-02:00` en 2008-01-15, `GMT-03:00` en 2009-03-16 y `GMT-04:16:48` en 1900 |
| H11 | Resuelto | "Hora local" definida en cada spec |
| H12 | Resuelto | Citas a D3, D9 y DD-34; la cláusula de orden se quitó |
| H13 | Resuelto | "Contiguos que comparten una fila redondeada" |
| H14 | **Parcial** | Columnas especiales, id inexistente y `columnas=sillon` resueltos; el filtro por inactivo sin elementos es H25 |
| H15 | Resuelto | Tres escenarios nuevos y verificación de pantalla en 6.2 |
| H16 | Resuelto | Años fuera de 1000 a 9998 en el requirement y tres escenarios |
| H17 | Resuelto | `noValidate` en ambos formularios y "Valores que decide la API" |
| H18 | Resuelto | "En un bloqueo", "Lectura vieja después de un alta", "Relectura fallida después del alta" |
| H19 | Resuelto | "Bloqueo en la semana sin filtro" |
| H20 | Resuelto | Los siete puntos, uno por uno |
| H21 | Resuelto | "Apertura modal", "Cierre con Esc", espías en 2.3 y tarea 2.4 |
| H22 | Resuelto | Nombrados en 9.4 y 9.1 |
| H23 | Resuelto | "Última escritura gana"; la mezcla queda en 11.1 |
| H24 | Resuelto | "Enter en el campo de búsqueda" y el THEN de "Selector de paciente con teclado" |

La afirmación que la revisión 1 dejó sin verificar también se comprobó: `AwareDatetime` (Pydantic 2.14.2 del `.venv`) rechaza `-04:16:48` y acepta `-04:16`, como dice D14.

### Controles específicos de esta pasada

- **Literales de D12**: coherentes en todos los lugares donde aparecen. `Completá este campo.` (`frontend-turnos` "Falta otro campo obligatorio"; D9, D12), `Ingresá la duración.` ("Duración vaciada"; D10, D12), `Solo hay turnos cancelados en este período. Activá Mostrar cancelados para verlos.` ("Solo hay turnos cancelados ocultos"; D3) y `Lunes 09/11` ("Semana de lunes a domingo", "Nombre de las columnas de la semana"; D17, tarea 6.6). También coinciden con D12 el resto de los textos afirmados en los escenarios. Lo que falta es dónde se aplican: H26, H27 y H31.
- **Tareas**: los 46 escenarios nuevos tienen tarea que los nombra o nombra su caso. Las dos observaciones de C9 están en H38.
- **Alcance**: nada invade C-16 ni depende de algo inexistente. No aparecen reglas fuera de la KB o de las decisiones aprobadas; `columnas=sillon` ignorado se deriva de D1 y D16.
- `openspec validate frontend-agenda-turnos --strict`: válido.

### Cobertura

E = esperado, N = error de negocio, B = borde.

#### frontend-agenda

| Requirement | Escenarios | E | N | B | Reglas cubiertas |
|-------------|-----------:|:-:|:-:|:-:|------------------|
| Pantalla de agenda | 4 | Sí | — | Sí | US-008, DD-32 a, D3, P1 |
| Horarios en la zona del consultorio | 2 | Sí | — | Sí | RN-CU-04, DD-06, DD-32 g |
| Día actual del consultorio | 2 | — | — | Sí | RN-CU-04 |
| Vistas diaria y semanal | 5 | Sí | — | Sí | US-008, DD-32 d, DD-27 a, D2 |
| Navegación entre períodos | 5 | Sí | — | Sí | US-008 |
| La vista se conserva en la URL | 7 | Sí | — | Sí | DD-31 o, DD-32 l, D6, P7 |
| Filtros por profesional y por sillón | 7 | Sí | — | Sí | US-008, DD-32 h, l, DD-26 g, P1 |
| Columnas de la vista diaria | 6 | Sí | — | Sí | DD-30 d, DD-26 g, D1, P1 |
| Datos visibles de cada turno | 3 | Sí | — | Sí | DD-32 j, DD-08 |
| Nombres de los recursos | 2 | Sí | — | Sí | DD-26 g |
| Turnos cancelados | 3 | Sí | — | Sí | D3, DD-32 f, RN-AG-07 |
| Ubicación en la grilla | 5 | Sí | — | Sí | D1, D4, DD-15, P6 |
| Elementos superpuestos en una columna | 4 | Sí | — | Sí | RN-AG-03, DD-30 b, f, P6 |
| Elementos que cruzan días | 5 | Sí | — | Sí | DD-32 b, e, DD-30 f, RN-AG-03 |
| Bloqueos en la agenda | 2 | Sí | — | — | DD-30, D1 |
| Agenda del odontólogo | 6 | Sí | Sí | Sí | RN-AU-02, DD-31 b, DD-32 i, P2 |
| Errores al cargar la agenda | 5 | — | Sí | Sí | DD-33 e, DD-32 i |
| Respuestas fuera de orden | 4 | — | — | Sí | D13 |
| Actualización manual | 2 | Sí | — | — | D13 |
| Accesibilidad de la agenda | 5 | Sí | — | — | D17 |

#### frontend-turnos

| Requirement | Escenarios | E | N | B | Reglas cubiertas |
|-------------|-----------:|:-:|:-:|:-:|------------------|
| Operaciones solo para la recepcionista | 2 | Sí | Sí | — | RN-AU-02, matriz de 03 |
| Operaciones según el estado del turno | 3 | Sí | Sí | Sí | RN-AG-13, DD-14, DD-23 d |
| Formulario de nuevo turno | 5 | Sí | Sí | Sí | D9, DD-21 c, US-004, P8 |
| Sillón según la prestación | 2 | Sí | — | Sí | DD-09, RN-AG-10, DD-21 a |
| Duración por defecto y ajustable | 2 | Sí | — | — | RN-AG-04 |
| Inicio con zona horaria | 5 | Sí | — | Sí | RN-CU-04, DD-15, SU-08, D14 |
| Alta exitosa | 3 | Sí | — | Sí | US-004, D13 |
| Búsqueda de pacientes | 5 | Sí | — | Sí | DD-31 e, D8 |
| Resultados de la búsqueda de pacientes | 6 | Sí | Sí | Sí | DD-31 g, DD-21 c |
| Formulario de reprogramación | 4 | Sí | Sí | Sí | DD-23 a, b, DD-26 g, P3 |
| Reprogramación parcial | 9 | Sí | — | Sí | DD-23 a, DD-26, P4 |
| Cancelación con confirmación | 5 | Sí | — | Sí | US-006, DD-14, D11 |
| Conflicto por solapamiento | 4 | — | Sí | — | RN-AG-01, 02, 14, DD-21 b |
| Reglas de agenda rechazadas por la API | 7 | — | Sí | Sí | RN-AG-04, 05, 06, 10, 12, D7, D13 |
| Referencias inválidas | 3 | — | Sí | Sí | DD-21 c, DD-26, P5 |
| Errores de validación por campo | 2 | — | Sí | Sí | DD-33 l, `frontend-cliente-http` |
| Turno que cambió mientras se editaba | 4 | — | Sí | Sí | DD-22, DD-23 c, d, D13 |
| Conservación de los datos ante un error | 2 | Sí | Sí | — | US-005 |
| Falta de permiso y fallas de red | 3 | — | Sí | Sí | DD-33 a, d, e |
| Accesibilidad de los formularios | 7 | Sí | — | Sí | D6, D17 |

#### frontend-sesion

| Requirement | Escenarios | E | N | B | Reglas cubiertas |
|-------------|-----------:|:-:|:-:|:-:|------------------|
| Layout de la aplicación (MODIFIED) | 4 | Sí | Sí | — | DD-33 g, RN-AU-03 |

C1 se cumple en el conjunto. Reglas del scope sin escenario: **el orden de D10** (H26). Las demás filas de la revisión 1 quedaron cubiertas.

### Hallazgos

Numeración continua respecto de la revisión 1. H25 a H27 y H29 salen de lo que agregó el update; el resto son casos que la revisión 1 no había visto.

#### H25 — El filtro por un profesional desactivado contradice P1 cuando solo tiene cancelados ocultos · MAYOR
- **Dónde**: `frontend-agenda`, requirement "Filtros por profesional y por sillón", escenario "Filtro por un profesional desactivado sin elementos". Tarea 6.3.
- **Problema**: el GIVEN dice "sin elementos **visibles** en el día" y el THEN exige `No hay turnos ni bloqueos en este período.`. Si ese profesional tiene un único turno `cancelado` y la casilla está apagada, el GIVEN se cumple; y para esa misma respuesta "Solo hay turnos cancelados ocultos" exige el otro texto y que **no** se vea ese. Los dos escenarios no pueden pasar a la vez, y el GIVEN tampoco dice que sea la vista diaria, donde "ninguna columna" tiene sentido.
- **Fuente**: P1; D3 ("Qué cuenta como elemento"); requirement "Pantalla de agenda"; controles C2 y C7.
- **Sugerencia**: GIVEN "la vista diaria, un profesional desactivado y una respuesta `{"turnos": [], "bloqueos": []}`". Agregar, sin regla nueva: GIVEN la vista diaria filtrada por un profesional desactivado cuyo único turno está `cancelado` y la casilla apagada, THEN no se ve ninguna columna y se ve `Solo hay turnos cancelados en este período. Activá Mostrar cancelados para verlos.`

#### H26 — El orden de D10 no está en el spec, y "Sin cambios" lo contradice · MAYOR
- **Dónde**: `frontend-turnos`, requirement "Reprogramación parcial", escenarios "Sin cambios" y "Prestación que pasó a requerir sillón"; falta un escenario. Tarea 9.4.
- **Problema**: D10 fija "primero los obligatorios y después la comparación". El requirement dice, sin excepción, "Sin cambios, MUST informarlo sin hacer ningún pedido", y el escenario "Sin cambios" tiene un GIVEN que incluye a un turno sin sillón cuya prestación ahora lo requiere: debería verse `No hiciste cambios.`, justo lo que D10 descarta. "Prestación que pasó a requerir sillón" termina al abrir el formulario, así que nada verifica el orden, y la tarea 9.4 tampoco lo menciona. Por la regla dura, Apply no puede implementar lo que no está en el spec.
- **Fuente**: D10 (Orden); `CLAUDE.md` §Reglas duras §Proceso; DD-26 (consecuencias); controles C2, C7 y C9.
- **Sugerencia**: agregar al requirement "los obligatorios se comprueban antes de comparar". Escenario: GIVEN un turno sin sillón cuya prestación ahora tiene `requiere_sillon` verdadero y el formulario sin modificar, WHEN se envía, THEN el campo `Sillón` muestra su error de obligatorio, no se ve `No hiciste cambios.` y no se hace ningún `PATCH`. El texto depende de P9. Sumarlo a 9.4.

#### H27 — Hora o fecha vaciadas al reprogramar · MAYOR
- **Dónde**: `frontend-turnos`, requirement "Formulario de reprogramación", falta. D10.
- **Problema**: el requirement solo hace obligatoria la duración. Con `noValidate` (P8) el navegador ya no frena un `Hora` o `Fecha` vacíos, y la comparación contra el turno ve un cambio: según la implementación, `aInstanteConDesfasaje` lanza, o sale un `PATCH` con un `inicio` inválido. Es el mismo problema de H6 en otros dos campos. D10 habla de "los obligatorios", en plural, y el spec no dice cuáles son.
- **Fuente**: P8, D10 (Orden), D14; requirement "Formulario de nuevo turno" ("Un campo obligatorio vacío MUST impedir el envío"), que aplica solo al alta; control C7.
- **Sugerencia**: pregunta P9.

#### H28 — Odontólogo de un profesional desactivado: P1 contra P2 · MENOR
- **Dónde**: `frontend-agenda`, requirements "Columnas de la vista diaria" y "Agenda del odontólogo". Tareas 4.3 y 6.5.
- **Problema**: desactivar un profesional no afecta a su usuario `odontologo`, que sigue entrando. Sin elementos, "Un recurso desactivado MUST tener columna solo si tiene elementos visibles" le quita la columna, y "una sola columna, la de su profesional, aunque esté vacía" se la da. La primera oración del requirement de columnas habla de la recepcionista, pero el resto no se limita a ella y la última regla menciona al odontólogo. Una función de columnas común (tarea 4.3) daría cero columnas.
- **Fuente**: DD-26 h; P1; P2; D3; D16.
- **Sugerencia**: pregunta P10.

#### H29 — Un valor rechazado que es el actual del turno · MENOR
- **Dónde**: `frontend-turnos`, requirements "Formulario de reprogramación" y "Referencias inválidas", escenarios "Profesional desactivado" y "Cambiar el valor rechazado".
- **Problema**: como `aplicar_cambios` fusiona lo omitido y `cargar_referencias` exige referencias activas, un `PATCH` que cambia solo la hora de un turno con profesional desactivado devuelve `referencia_invalida` sobre ese profesional. Al elegir otro, "Cambiar el valor rechazado" dice que la opción "deja de ofrecerse", y el otro requirement dice que el recurso actual "MUST seguir figurando".
- **Fuente**: P5; D7 ("más el valor actual al reprogramar"); DD-26 (consecuencias); `backend/app/application/reprogramar_turno.py`, `repositorio_turnos.py`.
- **Sugerencia**: pregunta P11.

#### H30 — Alcance de `(inactivo)` y un texto sin definir · MENOR
- **Dónde**: `frontend-turnos`, requirement "Referencias inválidas".
- **Problema**: "el valor rechazado MUST seguir como opción marcada `(inactivo)`" no contempla dos casos. Con `motivo` `inexistente` el recurso no está inactivo, y D9 dice que se usa el texto genérico. El paciente en el alta no es una opción de un selector. Además, el requirement pide indicar que el turno solo se puede cancelar con "paciente o prestación", pero D12 y el escenario solo dan el texto del paciente, y la tarea 7.1 afirma ambos.
- **Fuente**: P5; D9; D12; DD-26 (consecuencias); control C5.
- **Sugerencia**: un escenario con `motivo` `inexistente`; acotar la frase a los selectores; agregar a D12 y al spec el texto para `prestacion`.

#### H31 — "Es obligatorio" no se puede afirmar con `noValidate` · MENOR
- **Dónde**: `frontend-turnos`, escenarios "Prestación que requiere sillón" y "Prestación que pasó a requerir sillón".
- **Problema**: con P8, `required` no tiene efecto, y ningún escenario envía el formulario con el sillón vacío. "Falta otro campo obligatorio" solo prueba `Hora`. Un campo sin validación pasa los dos THEN si la prueba mira otra cosa.
- **Fuente**: P8; D9; control C5.
- **Sugerencia**: en el alta, GIVEN una prestación con `requiere_sillon` verdadero y el sillón sin elegir, WHEN se envía, THEN el campo `Sillón` muestra `Completá este campo.` y no se hace ningún `POST /turnos`.

#### H32 — Las columnas con filtro solo están en un escenario · MENOR
- **Dónde**: `frontend-agenda`, "Columnas de la vista diaria", escenarios "Filtrar por profesional" y "Filtro con un id que no existe".
- **Problema**: ningún requirement dice cómo un filtro reduce las columnas. "Se ve una sola columna" no fija la agrupación: agrupando por sillón, las columnas son sillones. Tampoco está definido filtrar por sillón agrupando por sillón (¿solo ese, o todos?), ni si un id inexistente tiene columna; el escenario afirma el texto, pero no eso.
- **Fuente**: D1, D6, DD-30 d, DD-32 l; control C7.
- **Sugerencia**: pregunta P12.

#### H33 — Un turno de un recurso ausente del catálogo no tiene columna · MENOR
- **Dónde**: `frontend-agenda`, "Nombres de los recursos" y "Columnas de la vista diaria". D7.
- **Problema**: el catálogo se carga al montar la página y `Actualizar` no lo relee. Un turno de un profesional dado de alta después no pertenece a ninguna columna diaria: es un elemento visible que no se ve, sin el mensaje de vacío, cuando el requirement dice "sin impedir ver la agenda". Agrupando por sillón pasa lo mismo.
- **Fuente**: requirement "Nombres de los recursos"; D1, D7; DD-26 a.
- **Sugerencia**: pregunta P13.

#### H34 — Relectura de catálogos fallida con el formulario abierto · MENOR
- **Dónde**: `frontend-agenda`, "Errores al cargar la agenda"; `frontend-turnos`, "Conservación de los datos ante un error".
- **Problema**: el update amplió las relecturas de catálogos a tres códigos, pero "Si falla la carga […] de los catálogos, la pantalla MUST mostrar el mensaje" no distingue la carga inicial de una relectura. Sin escenario, una implementación puede reemplazar la pantalla y perder el formulario.
- **Fuente**: D7; requirement "Conservación de los datos ante un error".
- **Sugerencia**: pregunta P14.

#### H35 — `inicio_no_alineado` sin escenario · MENOR
- **Dónde**: `frontend-turnos`, "Reglas de agenda rechazadas por la API".
- **Problema**: el requirement lo lista y "Valores que decide la API" envía justo `10:07`, pero ningún escenario afirma su respuesta. La tarea 7.1 cubre el traductor; la 9.3 no lo nombra.
- **Fuente**: P8; DD-15; D12.
- **Sugerencia**: GIVEN un formulario enviado y una respuesta `422` con código `inicio_no_alineado`, THEN el campo `Hora` muestra `El horario debe ser múltiplo de 5 minutos.`

#### H36 — El detalle queda indefinido bajo los formularios · MENOR
- **Dónde**: `frontend-turnos`, "Reprogramación exitosa", "Desistir" y "Turno creado"; `frontend-agenda`, "Detalle de un turno". D6.
- **Problema**: `Reprogramar` y `Cancelar turno` se abren desde el detalle, que también es un diálogo. Ningún escenario dice si sigue abierto. Si sigue, tras un éxito muestra datos viejos y las mismas acciones, y `queryByRole("dialog")` no da lo que afirma "el formulario se cierra".
- **Fuente**: D6; control C7.
- **Sugerencia**: pregunta P15.

#### H37 — Reglas de D7 y D9 que no llegaron al spec · MENOR
- **Dónde**: `frontend-turnos`, "Formulario de reprogramación" y "Formulario de nuevo turno".
- **Problema**: D7 dice que el formulario de reprogramación ofrece solo activos más el valor actual, pero solo está escrito para el alta. D9 dice que el profesional toma el del filtro, sin requirement; y si el filtro es un profesional desactivado, choca con "solo recursos activos".
- **Fuente**: D7, D9; `CLAUDE.md` §Reglas duras §Proceso.
- **Sugerencia**: agregar ambas al spec con su escenario, con el desactivado sin precargar, o quitar del diseño la del profesional.

#### H38 — Escenarios imprecisos · MENOR
- **Dónde y problema**:
  - "Detalle de un turno" (`frontend-agenda`) y "Turno cancelado" (`frontend-turnos`): con D3 un cancelado no se puede elegir sin activar la casilla, y el GIVEN no lo dice.
  - "Reenvío exitoso": "el error desaparece" no puede fallar, porque el formulario se cierra. La cláusula "Los errores previos MUST limpiarse al reenviar" no tiene escenario efectivo.
  - "Año anterior al admitido" usa `0050`, y el borde inferior (`1000-01-01` válida, `0999-12-31` inválida) no se prueba; un mínimo de 100 pasaría.
  - C9: los tres escenarios de años afirman un `GET`, y la tarea 4.1 prueba solo la función. "Sesión vencida al enviar" habla de un `POST /turnos`, y la tarea 9.5 está en el test de reprogramar, donde además hace falta `renderizarApp` para ver `/login`.
- **Fuente**: controles C5 y C9; D3; P7; DD-33 d.
- **Sugerencia**: completar los GIVEN; un escenario de reenvío que falla con otro error; el borde inferior; sumar los años a 6.2 y `POST` a 9.3.

#### H39 — Documentación del proposal sin tarea · SUGERENCIA
- **Dónde**: `proposal.md` (Impact) y tarea 11.2.
- **Problema**: el proposal anuncia cambios en `knowledge-base/06` (US-008) y ninguna tarea lo toca; 11.2 toca `08`, que el proposal no lista.
- **Fuente**: `proposal.md`; `tasks.md`.
- **Sugerencia**: alinear las dos listas.

### Preguntas abiertas

Ninguna tiene respuesta en la KB ni en las decisiones aprobadas. Las opciones son propuestas; la recomendada va primero.

- **P9 (H26, H27)**: obligatorios al reprogramar. (a) Fecha, hora, y sillón cuando se requiere, con `Completá este campo.` y sin pedido, antes de comparar, igual que en el alta. (b) Hora o fecha vacías conservan el valor del turno. Recomendada: (a), porque es lo que anticipa D10 y una sola vía de error.
- **P10 (H28)**: odontólogo de un profesional desactivado. (a) Una sola columna, aunque esté vacía: P2 es la regla específica, y conviene limitar la regla de desactivados a la recepcionista. (b) Sin columna, como P1. Recomendada: (a).
- **P11 (H29)**: valor rechazado que es el actual del turno. (a) Sigue como opción mientras sea el actual; "deja de ofrecerse" vale para los demás. (b) Deja de ofrecerse también. Recomendada: (a), porque coincide con D7.
- **P12 (H32)**: columnas con filtro. (a) El filtro de profesional deja una columna solo al agrupar por profesional; al agrupar por sillón, siguen los sillones; el filtro de sillón al agrupar por sillón deja ese sillón y `Bloqueos` si hay; un id inexistente, sin columna. (b) Las columnas no dependen de los filtros. Recomendada: (a).
- **P13 (H33)**: turno de un recurso ausente del catálogo. (a) Tiene columna, con el texto genérico, como un desactivado con elementos. (b) Releer los catálogos con `Actualizar`, además, para reducir el caso. Recomendada: (a), y (b) se puede sumar.
- **P14 (H34)**: relectura de catálogos fallida con el formulario abierto. (a) El formulario sigue abierto con sus datos y el error se muestra como general. (b) Error de pantalla con `Reintentar`. Recomendada: (a), por "Conservación de los datos".
- **P15 (H36)**: detalle al abrir un formulario. (a) Se cierra al abrir el formulario, y `Volver` o el éxito llevan a la agenda. (b) Sigue abierto y se actualiza. Recomendada: (a), porque evita diálogos apilados.

### Fuera de esta revisión

- No hay código del change: nada de esto se ejecutó. Solo se comprobaron `Intl`, los días de la semana, `AwareDatetime` y el camino de reprogramación del backend.
- No se reabrieron D1 a D13 ni P1 a P8.
- No son hallazgos: las fallas previas de `openspec validate --specs --strict` en otros cuatro specs, ni la cita a DD-34, que se crea en la tarea 11.1.
