# Revisión de escenarios — frontend-configuracion-pacientes-bloqueos (C-16)

- Fecha: 2026-11-11 (segunda revisión, después del `/opsx:update` que resolvió H1 a H11)
- Specs revisados: `specs/frontend-gestion`, `frontend-recursos`, `frontend-horarios`, `frontend-pacientes`, `frontend-bloqueos`, `frontend-auditoria` (ADDED) y `frontend-sesion` (MODIFIED), 155 escenarios. También `proposal.md`, `design.md` (D1-D18) y `tasks.md`. `openspec validate --strict` pasa.
- Reglas aplicables: RN-HB-01, RN-HB-02, RN-HB-03, RN-AU-02, RN-AU-03, RN-CU-01, RN-CU-02, RN-CU-04; DD-15, DD-25, DD-26, DD-27, DD-30, DD-31, DD-33, DD-34; US-001, US-002, US-003, US-009, US-011.
- Contexto: change solo de frontend. Los faltantes de backend (autor sin nombre, sin total en `GET /pacientes`, sin rango en `GET /bloqueos`, sin `GET /turnos/{id}`) están declarados fuera de alcance. El nombre del escenario "Pantallas provisorias sin pedidos" se conserva a propósito (el validador estricto lo exige) y no se vuelve a señalar. Los límites aceptados de D16 tampoco se reabren como defecto; solo se señala la redacción donde el spec los contradice.
- Veredicto: **LISTO PARA APPLY** (0 BLOQUEANTE, 0 MAYOR, 3 MENOR, 2 SUGERENCIA)

## Verificación de la primera revisión

| Hallazgo | Estado | Comprobación |
|----------|--------|--------------|
| H1 (MAYOR) | Corregido, con un resto en H12 | Bloqueos: el nombre lleva profesional, `Desde` y `Hasta`; el escenario "Bloqueos con el mismo inicio" tiene tres filas y tres nombres distintos. Pacientes: el nombre lleva el documento; el escenario "Pacientes homónimos" lo prueba. Profesionales homónimos quedan fuera por D16 |
| H2 | Corregido | La cláusula de la medianoche pasó a ser una explicación (DD-27 c, e), sin norma suelta |
| H3 | Corregido | `Nueva franja` visible y deshabilitado con descripción; dos escenarios lo prueban, incluso con parámetro inválido o desconocido |
| H4 | Corregido | Dos escenarios (casilla desmarcada y marcada) con los dos avisos; la casilla no cambia |
| H5 | Corregido | Regla cerrada (solo dígitos, `-` opcional, trim), alta y edición, escenarios `32.5` y `abc`; rango y múltiplo de 5 siguen en la API (DD-15) |
| H6 | Corregido | Escenarios de `profesional_requerido`, `403 profesional_ajeno` al crear y `409` en días distintos |
| H7 | Corregido | Tareas 6.1, 6.2 y 8.3 mencionan etiquetas, `maxLength` 100 y los `422` de `Nuevo paciente` |
| H8 | Corregido | Títulos, nombre accesible de `Editar` franja y `step=300` con escenario; restos de "a confirmar" quitados |
| H9 | Corregido | "Sesión vencida al cargar" y "Relectura fallida" |
| H10, H11 | Sin acción, coherente | Nota en D6 y cláusula del `sub` en el requirement |

## Cobertura

| Spec | Requirements | Escenarios | Esperado | Error de negocio | Borde | Reglas cubiertas |
|------|-------------:|-----------:|:--------:|:----------------:|:-----:|------------------|
| frontend-gestion | 15 | 36 | sí | sí (duplicado, 404, 403, 401) | sí (solo espacios, doble envío, fuera de orden, relectura fallida) | DD-26 d/g/j, DD-31 i, DD-33 d/e, DD-34 i/k/P8/P9/P15 |
| frontend-recursos | 7 | 18 | sí | sí (duplicados, `duracion_invalida`) | sí (decimales, no numérico, inactivo, sección inexistente) | US-001, DD-15, DD-26 b/d/e/g, RN-AU-03 |
| frontend-horarios | 6 | 18 | sí | sí (`franja_invalida`, `franja_superpuesta`, 404) | sí (sin profesional, id desconocido, zona del runner, sin horario) | US-002, DD-27 a/b/c/d/e/g/j, RN-HB-01 |
| frontend-pacientes | 7 | 20 | sí | sí (documento repetido) | sí (299/300 ms, 20 exactos, blanco, homónimos) | US-009, DD-31 e/h/i/k/l/m/o, RN-CU-02 |
| frontend-bloqueos | 8 | 27 | sí | sí (`bloqueo_invalido`, `referencia_invalida`, `profesional_requerido`, `409`, `403`) | sí (ya terminado, mismo inicio, días distintos, parámetro mal formado) | US-003, RN-HB-02, RN-HB-03, RN-AU-02, DD-30 a/b/c/e/f/g/h/i/k |
| frontend-auditoria | 7 | 18 | sí | sí (`404`, `403`) | sí (sin cambios, sin `sub`, vacío, fuera de catálogo) | US-011, DD-25 a/b/c/f/g, RN-CU-01 |
| frontend-sesion (delta) | 3 | 18 | sí | sí (rol no permitido) | sí (`sub` ausente o numérico, sección de configuración) | RN-AU-03, DD-31 b, RN-HB-02, DD-33 g |

Total 155 (los conteos coinciden con `grep` sobre los specs). Reglas del scope sin escenario: ninguna.

Controles: C1 cumplido en el change y en cada spec. C4: los códigos nuevos (`profesional_requerido`, `403 profesional_ajeno` al crear, `recurso_inexistente` con `recurso` `horario`) coinciden con DD-30 a/l y DD-27. C8: datos ficticios. Delta MODIFIED: los escenarios del spec vigente (Datos de la sesión, Guarda por rol, Layout) se conservan o se reemplazan sin perder ninguno.

## Hallazgos

### H12 — El requirement de accesibilidad exige distinguir toda fila, pero hay dos límites aceptados · MENOR
- **Dónde**: `frontend-gestion`, requirement "Accesibilidad de las pantallas de gestión" ("MUST tener un nombre accesible que... lo distinga de las demás filas"); escenarios de profesionales (`Editar Ficticia, Ana`, `Desactivar Ficticia, Ana`).
- **Problema**: la matrícula es opcional y única solo si existe (DD-26 e, f), así que dos profesionales homónimos sin matrícula tendrían nombres idénticos. D16 acepta ese límite y el de dos bloqueos del mismo profesional con el mismo intervalo, pero el requirement los contradice con un MUST sin excepción. Un test de Apply que lea el requirement al pie de la letra no puede cumplirlo.
- **Fuente**: DD-26 e/f; design D16 (límite aceptado); control C7.
- **Sugerencia**: agregar al requirement "salvo dos profesionales homónimos o dos bloqueos idénticos del mismo profesional, que la API admite y D16 acepta". No agrega escenarios.

### H13 — Reprogramación que cambia el sillón a `Sin sillón` o desde `Sin sillón` · MENOR
- **Dónde**: `frontend-auditoria`, requirement "Datos de una reprogramación".
- **Problema**: `Sin sillón` se define solo para la creación. Un cambio de `requiere_sillon` de la prestación (DD-26, Consecuencias) hace que reprogramar aplique la regla nueva, así que `sillon_id` puede pasar de un valor a nulo o al revés; el spec no dice cómo se ve el nulo en `antes → después`. La tarea de Apply tendría que decidirlo.
- **Fuente**: DD-26 (Consecuencias); DD-25 b (`sillon_id` nullable en las instantáneas).
- **Sugerencia**: escenario de borde: registro `reprogramar` con `sillon_id` previo "Sillón 1" y nuevo nulo, y THEN `Sillón: Sillón 1 → Sin sillón`. Reutiliza el texto ya definido.

### H14 — Formulario `Nuevo bloqueo`: profesionales inactivos y ausencia del selector del odontólogo · MENOR
- **Dónde**: `frontend-bloqueos`, requirements "Alta de un bloqueo" y "Bloqueos del odontólogo".
- **Problema**: el filtro dice que incluye los inactivos `(inactivo)` (DD-30 h), pero el selector `Profesional` del formulario no lo dice, y la ausencia del selector del odontólogo en el formulario (RN-AU-02) solo se comprueba de forma indirecta (el cuerpo no trae `profesional_id`); el escenario "Odontólogo sin filtro" verifica la pantalla, sin abrir el formulario.
- **Fuente**: DD-30 h (se permiten bloqueos de un profesional desactivado); RN-AU-02.
- **Sugerencia**: una cláusula en "Alta de un bloqueo" ("el selector del formulario ofrece los mismos profesionales que el filtro, inactivos incluidos") y sumar al escenario "Alta del odontólogo" "y el formulario no tiene el campo `Profesional`".

### H15 — Límite de `fin` igual al reloj en el aviso de D18 · SUGERENCIA
- **Dónde**: `frontend-bloqueos`, escenario "Bloqueo creado que ya terminó".
- **Problema**: el requirement usa "menor o igual", pero el escenario usa un `fin` claramente pasado. El borde `fin == reloj` ya lo prueba "Terminado oculto" para el listado; con el mismo predicado alcanza.
- **Fuente**: design D8, D18.
- **Sugerencia**: sin acción, o una nota en la tarea para reutilizar la misma función.

### H16 — `/configuracion/<inexistente>` para el odontólogo · SUGERENCIA
- **Dónde**: `frontend-sesion` "Guarda por rol" y `frontend-recursos` "Secciones de la configuración".
- **Problema**: una sección inexistente muestra "no encontrada" para la recepcionista; para el odontólogo no se dice si prima la falta de permiso o la ruta inexistente. No cambia nada de seguridad (ninguna muestra datos).
- **Fuente**: control C7.
- **Sugerencia**: decisión del equipo; si se quiere, un escenario.

## Preguntas abiertas

Ninguna nueva. H16 es la única decisión pendiente y no bloquea.

## Fuera de esta revisión

- Comportamiento visual (11.1, 11.2): se verifica a mano.
- Código existente de C-14 y C-15 (`apiFalsa`, `fabricas`, `DetalleTurno`): no se leyó. Los escenarios de auditoría suponen que el detalle de un turno cancelado no ofrece `Reprogramar` ni `Cancelar turno`; eso pertenece a C-15.
- Los faltantes de backend declarados fuera de alcance: no se evaluaron como hallazgos.
- No se verificaron los `maxLength` contra los modelos del backend en esta pasada (la primera revisión los dio por coincidentes).

## Primera revisión (2026-11-11)

Hallazgos H1 a H11 de la primera pasada (1 MAYOR, 6 MENOR, 4 SUGERENCIA; 141 escenarios) y cómo se resolvieron con `/opsx:update` (141 → 155 escenarios).


- Fecha: 2026-11-11, con `/opsx:update`. Las preguntas abiertas 1 a 3 las decidió el usuario ese día (design D15, D17 y D18). Escenarios: 141 → 155. `openspec validate frontend-configuracion-pacientes-bloqueos --strict` pasa.

| Hallazgo | Resolución |
|----------|------------|
| H1 (MAYOR) | Resuelto. Bloqueos: `Borrar bloqueo de Apellido, Nombre del DD/MM/AAAA HH:MM al DD/MM/AAAA HH:MM`, en ambos roles. Pacientes: `Editar`/`Desactivar Apellido, Nombre (documento)`. Escenarios nuevos "Bloqueos con el mismo inicio" (tres bloqueos, dos profesionales) y "Pacientes homónimos". El requirement "Accesibilidad" de `frontend-gestion` exige que el nombre distinga la fila. Design D16, con el límite aceptado de dos bloqueos idénticos del mismo profesional |
| H2 | Resuelto. Se quitó la cláusula de la medianoche de "Datos de una creación" y se explica por qué no ocurre (DD-27 c y e) |
| H3 | Resuelto por decisión del usuario: `Nueva franja` visible y deshabilitado, con la descripción `Elegí un profesional para ver o cargar su horario.` (texto que reemplaza al anterior). Escenario "Nueva franja sin profesional" y el de parámetro inválido lo comprueba. Design D17 |
| H4 | Resuelto por decisión del usuario: `Bloqueo creado. Está oculto porque ya terminó.` sin tocar la casilla; con la casilla marcada, `Bloqueo creado.` Dos escenarios. Design D18 |
| H5 | Resuelto por decisión del usuario: `Ingresá minutos enteros.` (con punto final, como los demás mensajes de campo) y sin pedido, en alta y edición; campo `type="text"` con `inputMode="numeric"`. Escenarios "Duración con decimales" y "Duración no numérica en la edición". Design D15 y excepción anotada en D6 y en "Campos obligatorios" |
| H6 | Resuelto. Escenarios "Profesional requerido por la API", "Odontólogo rechazado al crear" (`403 profesional_ajeno`, diálogo abierto, token intacto) y "Turnos afectados en días distintos". D11 aclara que los dos primeros son defensivos |
| H7 | Resuelto en `tasks.md`: 8.3 suma los `422` de `Nuevo paciente` sin el `msg`, 6.2 el `maxLength` 100 y 6.1 los campos etiquetados. También se reflejaron en tareas los escenarios nuevos (5.1, 5.2, 7.2, 7.3, 7.4, 9.3, 9.4, 9.5, 9.6). Sin tareas nuevas: 44 |
| H8 | Resuelto en parte. El escenario "Pantallas provisorias sin pedidos" **conserva el nombre**: `openspec validate --strict` rechaza un MODIFIED que omite un escenario del spec vigente (se probó el renombre y falló); queda explicado en design (Risks) y en la tarea 2.5. Se quitaron los "a confirmar" de `proposal.md` y `tasks.md`. Título `Bloqueos` para la recepcionista (escenario nuevo), acción `Editar lunes 09:00 a 13:00` con diálogo `Editar franja`, y escenario "Horas en pasos de 5 minutos" (`type="time"`, `step="300"`) |
| H9 | Resuelto. Escenarios "Sesión vencida al cargar" (`401 no_autenticado` al cargar: lo resuelve la sesión) y "Relectura fallida" (el aviso queda junto al error con `Reintentar`, sin reenviar) |
| H10 | Sin cambio de pantalla: nota en design D6. La KB no obliga a avisar el efecto de `requiere_sillon`; si se pide, es un texto de ayuda |
| H11 | Decidido: un `sub` textual se acepta tal cual, sin comprobar que sea UUID; solo puede mostrar `Otro usuario`. Cláusula en el requirement de `frontend-sesion`, nota en design D10 y en la tarea 2.4 |

Hallazgos abiertos: ninguno BLOQUEANTE ni MAYOR. Conviene volver a correr `revisar-escenarios` sobre los 14 escenarios nuevos antes del Apply (tarea 1.3).

## Resolución de la segunda revisión (2026-11-11)

Con `/opsx:update`. Escenarios: 155 → 157. `openspec validate frontend-configuracion-pacientes-bloqueos --strict` pasa. Tarea 1.3 marcada: las dos pasadas están hechas y el veredicto es LISTO PARA APPLY.

- **H12**: el requirement "Accesibilidad de las pantallas de gestión" de `frontend-gestion` nombra las dos excepciones de D16 (profesionales homónimos sin matrícula y bloqueos idénticos del mismo profesional), así que el MUST se puede cumplir. Sin escenarios nuevos.
- **H13**: "Datos de una reprogramación" de `frontend-auditoria` dice que un sillón nulo se ve como `Sin sillón`, con el escenario nuevo "Sillón quitado al reprogramar" (`Sillón: Sillón 1 → Sin sillón`). Tarea 10.1.
- **H14**: "Alta de un bloqueo" dice que `Profesional` ofrece los mismos profesionales que el filtro, inactivos incluidos y marcados `(inactivo)`. La API los admite: escenario "Profesional desactivado" de `bloqueos-agenda`, `201`. Escenario nuevo "Bloqueo de un profesional inactivo", y "Alta del odontólogo" comprueba que el formulario no tiene el campo `Profesional` (RN-AU-02). Tarea 9.4.
- **H15 y H16** (SUGERENCIA): sin cambios. H15 ya lo cubre el predicado compartido con "Terminado oculto", y H16 queda como decisión del equipo.
