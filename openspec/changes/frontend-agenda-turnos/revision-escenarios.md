# Revisión de escenarios — frontend-agenda-turnos (C-15)

> **Actualización**: los hallazgos H1 a H24 se resolvieron con `/opsx:update` el 2026-11-10. Respuestas aprobadas, todas con la opción (a): **P1**, solo cuentan los elementos visibles; sin ninguno, el mensaje de período vacío, y si solo hay cancelados, un texto propio que invita a mostrarlos; un profesional desactivado sin nada visible no tiene columna. **P2**, el odontólogo ve una sola columna, la de su profesional, aunque esté vacía. **P3**, la duración es obligatoria al reprogramar, con error propio y sin pedido. **P4**, un formulario intacto muestra `No hiciste cambios.` y no envía nada; `sillon_id: null` solo acompaña a otro cambio. **P5**, el valor rechazado sigue como opción marcada `(inactivo)` hasta que se cambie. **P6**, los carriles se calculan sobre las filas redondeadas a 5 minutos. **P7**, una `fecha` con año fuera de 1000 a 9998 es inválida y cae en el valor por defecto. **P8**, `noValidate`, con obligatorios propios y el resto a cargo de la API. Lo que esta revisión dejó sin verificar quedó comprobado: `AwareDatetime` rechaza un desfasaje con segundos con un `422` de validación sobre `inicio` (design D14).

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
