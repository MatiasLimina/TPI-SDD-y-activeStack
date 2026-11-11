# Design

## Context

La motivación está en `proposal.md`. Lo que condiciona el enfoque:

- **Base de C-14 y C-15**: el frontend ya tiene sesión con guardas por rol (`ConSesion`, `ConRol`), un único cliente HTTP con `ErrorApi`, el diálogo nativo `shared/ui/Dialogo`, el componente `Campo` (etiqueta, error y ayuda asociados), la zona del consultorio (`shared/tiempo/zonaConsultorio`: `instanteALocal`, `hoyLocal`, `aInstanteConDesfasaje`, `cruzaDias`), los catálogos de la agenda (`useCatalogos` y `crearNombres`, con textos genéricos para ids desconocidos) y los helpers de test (`instalarApiFalsa`, `fabricas`, `renderizarApp`, `reloj`). La zona de los tests es `Asia/Tokyo` para detectar conversiones olvidadas.
- **`/configuracion` es provisoria** (`pages/PaginaConfiguracion.tsx`) y su guarda por rol ya existe. DD-33 g dejó dicho que las vistas del odontólogo van en otra ruta.
- **Contratos reales de la API, revisados en `backend/app/api/`**: recursos (DD-26), horarios anidados en el profesional (DD-27), pacientes (DD-31), bloqueos (DD-30) y auditoría (DD-25). Todos los endpoints que usa este change existen. **No hace falta ningún cambio de backend**.
- **Lo que la API no da y condiciona la UI**: no hay total en `GET /pacientes`, no hay rango en `GET /bloqueos`, no hay nombre del autor en la auditoría (solo `usuario_id`), no hay `GET /turnos/{id}`, no se puede reactivar y los bloqueos no se editan. Ninguno de estos faltantes bloquea el change. Cada uno se resuelve en una decisión (D7, D8, D10, D2).
- **Formas de error a traducir**: `recurso_duplicado` trae `campo` y no trae `mensaje`; `franja_superpuesta` tampoco trae `mensaje`; los demás traen mensajes pensados para desarrolladores. Igual que en C-15 (DD-34 j), se muestran solo textos propios por `codigo`.

## Goals / Non-Goals

**Goals:**
- Seis pantallas de gestión y un diálogo de historial que se comportan igual, porque comparten un patrón (D4) y no se copian de una a otra.
- Que lo que la UI ofrece a cada rol coincida con lo que la API le permite (matriz de `03`, DD-25 a, DD-30, DD-31 b).
- Un desglose de tareas TDD por pantalla, en el que cada scenario tenga su test con Vitest y React Testing Library.

**Non-Goals:**
- Cambios en `backend/`, dependencias nuevas o caché global de datos.
- Rediseñar la agenda: solo se suma `Ver historial` al detalle.
- Validar en el cliente las reglas de negocio que ya valida la API (D6).

## Decisions

Las decisiones D1, D2, D3, D7, D8 y D10 cambian lo que ve el usuario y la KB no las fija. Se presentaron con la opción recomendada y el usuario las aprobó el 2026-11-11 (tarea 1.2). D15, D17 y D18 responden a las preguntas abiertas de `revision-escenarios.md` (H5, H3 y H4) y el usuario también las decidió el 2026-11-11. Si alguna cambia, primero va `/opsx:update`. Las demás son técnicas o se derivan directamente de la KB.

### D1 — Un solo change con un patrón compartido **[Aprobada por el usuario el 2026-11-11]**

| Opción | A favor | En contra |
|--------|---------|-----------|
| **Un change, con `features/gestion/` compartido y una tarea por pantalla (recomendada)** | Es el scope de C-16 en `CHANGES.md`. El patrón se diseña una vez y se prueba a fondo en una pantalla (sillones, la más simple), y las demás lo reutilizan. Es el último change del roadmap y no bloquea a nadie | El PR es grande. Se mitiga con commits por grupo de tareas y con specs separados por pantalla |
| Partir en dos (configuración / pacientes, bloqueos y auditoría) | PRs más chicos | Hay que tocar `CHANGES.md` y hacer dos ciclos OPSX. El patrón compartido quedaría en el primero y el segundo dependería de él |

### D2 — Rutas **[Aprobada por el usuario el 2026-11-11]**

| Opción | A favor | En contra |
|--------|---------|-----------|
| **`/configuracion/{profesionales,sillones,prestaciones,horarios}` como subrutas bajo la guarda de recepcionista; `/pacientes` (recepcionista); `/bloqueos` (ambos roles); historial como diálogo de la agenda (recomendada)** | Cada sección se puede enlazar y sobrevive al F5. `/bloqueos` queda fuera de `/configuracion`, que DD-33 g reserva a la recepcionista. El historial no necesita `GET /turnos/{id}`, que no existe (DD-34 e) | Más rutas en `RutasApp` |
| Secciones como parámetro `?seccion=` de `/configuracion` | Una sola ruta | Mezcla en una página estados de pantallas distintas. Los parámetros de URL ya se usan para filtros (`profesional`) |
| Bloqueos dentro de la agenda | Se ven en contexto | Sin `GET /turnos/{id}` y con la grilla ya compleja, suma un formulario más a `/agenda`. El listado y el `409` con turnos afectados necesitan pantalla propia |
| Historial en una ruta `/turnos/:id/historial` | Enlazable | Sin `GET /turnos/{id}`, el encabezado del turno se podría reconstruir con el último registro, pero a costa de una pantalla más para algo que se consulta desde el detalle |

`/configuracion` usa un `index` con `<Navigate to="profesionales" replace />`. Una sección inexistente cae en la ruta `*` existente. `PaginaConfiguracion` pasa a ser el contenedor con el título y la navegación interna (`NavLink`) más un `<Outlet />`. El layout usa `NavLink` para marcar `aria-current="page"`.

### D3 — Qué ve el odontólogo **[Aprobada por el usuario el 2026-11-11]**

| Opción | A favor | En contra |
|--------|---------|-----------|
| **Solo `/bloqueos` (además de `/agenda`) (recomendada)** | Es lo único que la KB le da para operar (US-003, RN-HB-02). Las demás lecturas que la API le permite (catálogo y su horario) no tienen historia de usuario, y los nombres ya los ve en la agenda | No ve su horario de atención en la SPA |
| Sumar `Mi horario` (lectura de sus franjas) | Útil para elegir cuándo bloquear | Ninguna US lo pide. Suma ruta, guarda y tests. Puede ir al backlog |
| Sumar lectura del catálogo | Completa la matriz `R` de `03` | Sin valor para su trabajo; la matriz describe permisos de la API, no pantallas |

### D4 — Patrón compartido de gestión

`features/gestion/` aporta piezas chicas que cada pantalla compone. No es un generador de pantallas por configuración:

- `useListado(pedir)`: pide al montar y ante `recargar()`. Expone `{datos, cargando, error, recargar}` y descarta las respuestas viejas con un contador de cargas, como `useCatalogos` (spec `frontend-gestion`, "Respuestas fuera de orden").
- `DialogoFormulario`: `Dialogo` + `<form noValidate>` + botón de envío deshabilitado durante el envío + `Volver` + error general con rol `alert` + aviso `No hiciste cambios.` con rol `status`.
- `DialogoConfirmacion`: título, texto de consecuencia, botón de confirmación y `Volver`, con el error en el mismo diálogo.
- Funciones puras, que son lo que más se testea: `camposVacios(valores, obligatorios)`, `calcularCambios(actual, editado, opcionales)` (D5) e `interpretarErrorGestion(error, {campos, duplicado, codigos})` (D11).
- `PantallaGestion`: el esqueleto de título, botón `Nuevo …`, aviso, carga, error con `Reintentar`, mensaje de vacío y tabla. Cada pantalla le pasa sus columnas y sus acciones.

| Opción | A favor | En contra |
|--------|---------|-----------|
| **Piezas compartidas y pantallas que las componen (recomendada)** | Cada pantalla conserva sus particularidades (búsqueda paginada, franjas por día, `409` con turnos) sin forzar una abstracción. Las reglas comunes se prueban una sola vez como funciones puras | Algo de código parecido entre las tablas |
| Un `ABMGenerico` configurado por una tabla de campos | Menos código por pantalla | Los casos especiales lo llenan de opciones. Es difícil de leer y de testear por scenario |
| Copiar la primera pantalla en las demás | Rápido al principio | Seis copias que se desalinean, que es justo lo que pide evitar el scope |

### D5 — Edición parcial

`calcularCambios` compara cada campo, ya recortado, con el valor actual y devuelve solo los distintos. Un opcional vaciado (`matricula`, `email`) vale `null`. Los números se comparan como número y las horas de franja se normalizan a `HH:MM` antes de comparar (la API responde `HH:MM:SS`). Sin cambios, el formulario muestra `No hiciste cambios.` sin hacer ningún pedido, igual que la reprogramación (DD-34 i). Los obligatorios se comprueban antes de comparar (DD-34 P9). Se descartó mandar el objeto completo: cada campo enviado pisaría un cambio concurrente de otro usuario (última escritura gana, DD-34).

### D6 — Validación en el cliente

Los formularios tienen `noValidate` (DD-34 P8). El cliente solo comprueba los obligatorios vacíos o en blanco (`Completá este campo.`) y limita los largos con `maxLength`, con los mismos topes que las columnas de la API. La única excepción es que la duración de una prestación sea un entero (D15). Todo lo demás lo decide la API y se traduce por código: duración múltiplo de 5 y su rango, franja alineada, fin posterior al inicio, formato del email y duplicados. Se descartó duplicar esas reglas en TypeScript, porque se desalinearían de DD-15, DD-27 c y DD-31 m.

**`Requiere sillón` sin aviso** (H10 de la revisión): DD-26 advierte en sus consecuencias que cambiar `requiere_sillon` afecta la reprogramación de los turnos ya agendados de esa prestación. La KB no obliga a avisarlo en la pantalla y el MVP no lo hace: la casilla no lleva texto de ayuda. Si el equipo lo pide, es un texto de ayuda en `Campo`, sin cambio de contrato.

### D7 — Búsqueda y paginación de pacientes **[Aprobada por el usuario el 2026-11-11]**

- **Sin largo mínimo y con espera de 300 ms**: DD-31 e no fija mínimo y, a diferencia del selector de turnos (DD-34 g, mínimo 2), acá se busca por documento, donde un dígito ya filtra. Un texto vacío o en blanco lista sin filtrar.
- **Fuera de la URL**: el texto buscado y la página viven en el estado de la pantalla. Así nombres y documentos no quedan en el historial del navegador ni en la barra de direcciones, en la línea de DD-31 o. El costo es que un F5 vuelve a la primera página sin búsqueda.
- **20 por página con `limite=21`**: la API no da total (DD-31 h). Pedir uno de más dice si hay página siguiente sin hacer un pedido vacío. Se muestra `Página N` sin "de M".

| Alternativa descartada | Por qué |
|------------------------|---------|
| Búsqueda en `?q=` | Deja datos personales en el historial |
| `Siguiente` habilitado con 20 resultados | Lleva a una página vacía cuando el total es múltiplo de 20 |
| Mínimo de 2 caracteres, como el selector | Impide buscar un documento por un dígito sin razón de la KB |

### D8 — Bloqueos **[Aprobada por el usuario el 2026-11-11]**

- **Terminados ocultos por defecto** (`fin <= reloj`), con la casilla `Mostrar bloqueos terminados` y sin pedido nuevo. `GET /bloqueos` trae todo el historial (DD-30 k), y lo útil es lo vigente y lo próximo. La alternativa de mostrar todo deja lo relevante al final, porque el orden es por `inicio`.
- **Formulario con fecha y hora separadas** (`<input type="date">` y `<input type="time" step="60">`), con fechas por defecto en el día actual del consultorio (`hoyLocal`) y cualquier minuto (DD-30 f). `inicio` y `fin` se arman con `aInstanteConDesfasaje`, que calcula el desfasaje por zona IANA. No se usa `datetime-local`, porque su valor depende de la zona del navegador.
- **El `409 bloqueo_con_turnos`** lista los turnos de la respuesta con su horario local y un enlace `Ver en la agenda` a `/agenda?fecha=…&profesional=…` (sin `profesional` para el odontólogo, que no lo necesita). No se buscan nombres de pacientes: la respuesta no los trae, a propósito (DD-30 i).
- **Sin restricción de pasado** en el cliente: la API admite bloqueos pasados (DD-30 e). Qué ve el usuario después de crear uno ya terminado lo fija D18.
- **Títulos**: `Bloqueos` para la recepcionista, igual que su enlace del layout, y `Mis bloqueos` para el odontólogo.
- El filtro de la recepcionista va en el parámetro `profesional` de la URL, como en la agenda. Al odontólogo nunca se le envía `profesional_id`.

### D9 — Horarios

El profesional elegido va en el parámetro `profesional` de la URL. No hay preselección, para no pedir franjas que nadie miró y para que el estado inicial sea explícito. Un id mal formado o ausente del catálogo se ignora, en la línea de DD-34 P12. Las franjas se agrupan en los siete días (`0 = Lunes … 6 = Domingo`, DD-27 a), y un día vacío muestra `Sin atención`. Las horas de la API (`HH:MM:SS`, hora local sin zona) se muestran como `HH:MM` **sin pasar por `Date`**, para que la zona de la suite (`Asia/Tokyo`) no las altere. Los `<input type="time">` de `Desde` y `Hasta` usan `step="300"` como ayuda (tiene su scenario, que solo comprueba el atributo), y la API sigue decidiendo (`franja_invalida`). Las acciones de cada franja se nombran igual: `Editar lunes 09:00 a 13:00` y `Borrar lunes 09:00 a 13:00`, con el día en minúscula; el diálogo de edición se titula `Editar franja`. Sin profesional elegido, `Nueva franja` se ve deshabilitado (D17).

### D10 — Autor de un registro de auditoría **[Aprobada por el usuario el 2026-11-11]**

La API expone solo `usuario_id` (DD-25 f, que descartó exponer nombre o email por minimización) y no hay endpoint de usuarios (DD-16).

| Opción | A favor | En contra |
|--------|---------|-----------|
| **`Vos` si `usuario_id` coincide con el claim `sub` de la sesión, `Otro usuario` si no (recomendada)** | Sin cambio de backend. Responde lo más común ("¿lo hice yo?"). `sub` ya viene en el token (spec `autenticacion`) y se lee igual que `rol`, sin verificar la firma y solo para mostrar | No distingue entre otros usuarios. Se suma la lectura de `sub` a `frontend-sesion`, como dato opcional que no cambia qué token es válido |
| Mostrar el `usuario_id` | Distingue usuarios | Un UUID no le dice nada a la recepción |
| Omitir el autor | Lo más simple | US-011 pide "quién" |
| Agregar un endpoint de usuarios o el nombre en la respuesta | Resuelve el "quién" | Cambio de backend que contradice DD-25 f. Queda en el backlog como limitación |

**`sub` que no es UUID** (H11 de la revisión): se acepta cualquier texto tal cual, sin comprobar el formato. El spec `autenticacion` exige un UUID y la API rechaza con `401` un token que no lo cumpla, así que en la práctica no llega. Si llegara, el texto nunca coincide con un `usuario_id` y el autor se ve como `Otro usuario`: el único efecto posible es de presentación. Validar el formato en el cliente agregaría una regla sin valor para el usuario.

### D11 — Textos propios por código

`interpretarErrorGestion` recibe el `ErrorApi`, el mapa de campos de la API a campos del formulario y los textos de la pantalla. Comunes: `validacion` → `Revisá este campo.` o `Revisá los datos ingresados.`; `403` → `No tenés permiso para esta operación.`; `404 recurso_inexistente` → `Este registro ya no existe.`, con el envío deshabilitado y relectura; red o sin `codigo` → `mensaje` del error. Por pantalla:

| Código | Destino | Texto |
|--------|---------|-------|
| `recurso_duplicado` (`campo` `matricula`, `nombre` o `documento`) | Campo indicado | `Ya existe un profesional con esa matrícula.` / `Ya existe un sillón con ese nombre.` / `Ya existe una prestación con ese nombre.` / `Ya existe un paciente con ese documento, activo o desactivado.` |
| `duracion_invalida` | `Duración (minutos)` | `La duración debe ser múltiplo de 5, de 5 a 480 minutos.` (el mismo texto que en turnos) |
| `franja_invalida` | General | `La franja debe terminar después de empezar, el mismo día, y en horas múltiplo de 5 minutos.` |
| `franja_superpuesta` | General | `Se superpone con otra franja de ese día.` |
| `bloqueo_invalido` | General | `El bloqueo debe terminar después de empezar y tener un motivo.` |
| `profesional_requerido` | `Profesional` | `Completá este campo.` |
| `referencia_invalida` (profesional) | `Profesional` | `El profesional ya no existe.` + relectura del catálogo |
| `bloqueo_con_turnos` | General + lista | `Hay turnos activos en ese intervalo: reprogramalos o cancelalos antes de bloquear.` |

Para la carga de listados, un `403` dice `No tenés permiso para ver esta información.` Un `401 no_autenticado`, al cargar o al escribir, no lo traduce la pantalla: lo resuelve la sesión (cierre con aviso de sesión vencida, spec `frontend-sesion`).

`profesional_requerido` y `403 profesional_ajeno` al crear un bloqueo no deberían ocurrir: la pantalla siempre manda el profesional de la recepcionista y nunca manda uno para el odontólogo. Se traducen igual por defensa (por ejemplo, ante un rol desactualizado en el token) y tienen su scenario.

### D12 — Datos y relectura

Cada pantalla tiene su `useListado` y no hay caché global (DD-34 k y D7 de C-15). Tras una escritura exitosa se relee el listado. Si esa relectura falla, el aviso de éxito queda visible junto al error de carga con `Reintentar`: la escritura ya se hizo y no se repite. `/bloqueos` y la sección de horarios piden `GET /profesionales` para nombres y selectores. El historial usa los catálogos que la agenda ya tiene cargados (`crearNombres`), así que no hace pedidos nuevos para resolver nombres. Una desactivación hecha en `/configuracion` se ve en la agenda al volver a entrar, porque la agenda relee sus catálogos al montarse.

### D13 — Reubicación de piezas existentes

`features/turnos/Campo.tsx` pasa a `shared/ui/Campo.tsx`, y `comoErrorApi` (`features/agenda/errores.ts`) pasa a `shared/api/`, porque los van a usar cinco features. Es un refactor sin cambio de comportamiento, con la suite en verde antes y después. `zonaConsultorio` suma `fechaCompleta` (`DD/MM/AAAA`) para bloqueos e historial. Los tipos de pacientes (`features/pacientes/tipos.ts`) suman la ficha completa (`telefono`, `email`); `Profesional` suma `matricula` en un tipo de `features/recursos/`, compatible con el de la agenda.

### D14 — Estrategia de tests

- **Unitarios** (funciones puras): `calcularCambios`, `camposVacios`, `interpretarErrorGestion`, agrupación de franjas por día, diferencias de la auditoría (`cambiosDeReprogramacion`), `fechaCompleta` y el armado del cuerpo del bloqueo.
- **Componentes y pantallas**: con `renderizarApp` (rutas y sesión reales), `instalarApiFalsa` (respuestas por `"METODO /ruta"` y `pendiente` para el desorden), el reloj fijo y la zona `Asia/Tokyo`. Cada requirement del patrón compartido se prueba a fondo en la pantalla de sillones. En las demás pantallas se prueba lo propio y un caso de humo del patrón.
- `apiFalsa` suma por defecto `GET /bloqueos` → `[]`. `fabricas` suma ficha de paciente, franja, registros de auditoría y profesional con matrícula, todo ficticio.

### D15 — Duración de la prestación como entero **[Decidida por el usuario el 2026-11-11]**

`Duración (minutos)` es un `<input type="text" inputMode="numeric">`. Con `type="number"` el navegador (y jsdom) entrega un valor vacío ante `abc`, que se confundiría con `Completá este campo.`. Antes de enviar, un valor que sin espacios en los extremos no sea un entero (solo dígitos, con un `-` opcional) marca el campo con `Ingresá minutos enteros.` y no se envía, en el alta y en la edición. El texto lleva punto final, como los demás mensajes de campo. El rango (5 a 480) y el múltiplo de 5 siguen en la API (`duracion_invalida`), así que un `-5` o un `32` se envían.

| Opción | A favor | En contra |
|--------|---------|-----------|
| **Rechazar en el cliente lo que no es entero (elegida)** | El usuario ve un error claro en el campo. El cliente no redondea, así que no decide una regla de dominio en silencio | Una regla de formato más en el cliente (excepción a D6) |
| Enviar el valor tal cual | Coherente con D6 | La API responde un `422` genérico (`Revisá este campo.`), menos claro |
| Redondear o truncar | Nunca falla | El cliente cambia en silencio lo que cargó el usuario (DD-15) |

### D16 — Nombres accesibles que distinguen las filas

Las acciones de cada fila nombran el registro con un dato que lo distinga (H1 de la revisión), porque los tests buscan por rol y nombre y un lector de pantalla tampoco distingue dos botones iguales:

- **Pacientes**: `Editar Imaginaria, Carla (00000104)` y `Desactivar Imaginaria, Carla (00000104)`. El nombre puede repetirse; el documento es único (DD-31 i).
- **Bloqueos**: `Borrar bloqueo de Ficticia, Ana del 12/11/2026 15:00 al 12/11/2026 16:00`, en ambos roles, con un solo formato. Con `Todos`, dos profesionales pueden tener el mismo inicio, y DD-30 b permite que un mismo profesional tenga bloqueos superpuestos.
- **Profesionales, sillones y prestaciones**: el nombre alcanza. Sillones y prestaciones tienen nombre único (DD-26 e). Dos profesionales homónimos son posibles, pero improbables en un consultorio de 1 a 5 profesionales; se acepta.

Límite aceptado: dos bloqueos del mismo profesional con exactamente el mismo intervalo compartirían el nombre. La API lo permite, pero no tiene sentido cargarlo dos veces; si un test lo necesitara, busca dentro de la fila.

### D17 — `Nueva franja` sin profesional elegido **[Decidida por el usuario el 2026-11-11]**

El botón se ve siempre, pero sin profesional elegido (también con un parámetro mal formado o desconocido) está deshabilitado, con `aria-describedby` al texto `Elegí un profesional para ver o cargar su horario.`, que reemplaza al anterior `Elegí un profesional para ver su horario.`. Se descartó ocultarlo, porque el usuario no descubriría que puede cargar franjas, y se descartó habilitarlo, porque el alta necesita el `{id}` del path.

### D18 — Bloqueo creado que ya terminó **[Decidida por el usuario el 2026-11-11]**

Si el `fin` del bloqueo que devuelve el `201` es menor o igual al reloj y `Mostrar bloqueos terminados` está desmarcada, el aviso es `Bloqueo creado. Está oculto porque ya terminó.` y la casilla no cambia. Con la casilla marcada, el bloqueo se ve en la relectura y el aviso es el normal, `Bloqueo creado.`. Se descartaron dejarlo sin explicación (el usuario cree que no se guardó) y marcar la casilla sola (cambia un filtro que el usuario no tocó).

### D19 — Rótulo del período en la agenda **[Aprobada por el usuario el 2026-11-11; extensión de alcance]**

En la comprobación manual (tarea 11.2) se vio que la vista diaria no dice qué día muestra, y una recepcionista que creía estar en hoy no notó que su turno quedó en mañana. Es una brecha de C-15 (el spec `frontend-agenda` no pedía un rótulo; las columnas de la semana solo traen `Lunes 09/11`). El usuario aprobó resolverla dentro de C-16, con un requirement ADDED en el delta de `frontend-agenda`.

- **Formato**: día `Jueves 12/11/2026`; semana `Semana del 09/11 al 15/11/2026`, y si cruza de año `Semana del 28/12/2026 al 03/01/2027`. Se arma con la tabla propia de nombres de día (D14 de C-15) y `fechaCompleta`, `diaYMes`, `lunesDeLaSemana` y `sumarDias` de `zonaConsultorio`, así que no depende de ICU ni de la zona del navegador.
- **Accesibilidad**: `<p aria-live="polite" aria-atomic="true">` en `BarraAgenda`, junto a los botones de `Período`. Se descartó un encabezado, porque no anuncia los cambios, y `role="status"`, porque las pantallas usan ese rol para `Cargando…` y avisos y un test por rol encontraría dos. `aria-live` polite, sin rol, anuncia el período nuevo sin interrumpir, y es coherente con "Accesibilidad de la agenda" (controles etiquetados, columnas con nombre).
- **Función pura**: `rotuloPeriodo(vista)` en `features/agenda/vistaAgenda.ts`, con tests unitarios; la barra solo la muestra.

No hay cambio de backend ni de la URL.

### D20 — La agenda sigue al turno guardado **[Aprobada por el usuario el 2026-11-11; extensión de alcance]**

En la comprobación manual, un turno creado para mañana desde la vista de hoy desaparecía de la pantalla: la agenda releía el período en curso y el turno quedaba fuera. Es una brecha de C-15 ("Alta exitosa" dice releer el período en curso).

- **Regla**: tras un `201` del alta, o un `200` de la reprogramación, se toma el día del turno en `America/Argentina/Buenos_Aires` (`instanteALocal`). Si cae dentro de `aRango(vista)` (el día, o la semana de lunes a domingo), se relee como hasta ahora; si cae fuera, se navega con `aParametros({ ...vista, fecha })`, que conserva vista, filtros y agrupación. El cambio de rango dispara la lectura del período nuevo, así que no se llama además a `recargar` (evita un pedido doble). El aviso de confirmación no cambia.
- **Reprogramación**: el formulario informa el `inicio` nuevo (el enviado si cambió la fecha o la hora; si no, el del turno, que ya estaba visible).
- **Una semana que contiene la fecha conserva la vista**: no hay navegación.
- **Contrato**: "Alta exitosa" pasa a MODIFIED en un delta de `frontend-turnos`, con todos sus scenarios y nombres; la reprogramación es un requirement ADDED.
- **Descartado**: dejar la agenda donde estaba y solo avisar (el usuario cree que no se guardó), y navegar siempre (perdería la posición en el caso común).

### D21 — Encabezados de columna fijos **[Aprobada por el usuario el 2026-11-11; extensión de alcance]**

Al abrir la grilla se desplaza a las 08:00 y el usuario veía turnos sin saber de quién era cada columna. Los `h2` ya tenían `position: sticky; top: 0`, pero no funcionaba: el contenedor es `display: flex` con `max-height: 70vh`, las secciones se estiraban solo hasta esa altura y un elemento fijo no puede salirse de la caja de su padre, así que el encabezado se iba con el scroll pasados los 70vh. Es el mismo problema que ya se había resuelto para el eje de horas con `align-self: flex-start`.

- **Arreglo**: `align-self: flex-start` en `.columna`, de modo que cada sección mide lo que sus 288 filas, y el encabezado queda fijo en todo el recorrido. El eje de horas y la cabecera del eje siguen alineados porque comparten `--alto-cabecera`.
- **Sin requirement**: jsdom no calcula el layout, así que ningún test automático lo comprueba sin ser una tautología. Se registra aquí, en la tarea 11.1 y en la verificación manual de la 11.2.

## Risks / Trade-offs

- **[Última escritura gana en las ediciones]**: no hay versión ni `ETag` de los recursos. → El `PATCH` parcial (D5) reduce el pisado a los campos que se tocaron. Es la misma limitación aceptada en DD-34.
- **[`GET /bloqueos` crece sin límite]**: trae todo el historial sin rango. → Se ocultan los terminados en el cliente (D8). Para el volumen de un consultorio alcanza; un rango en la API sería un change de backend.
- **[Paginación sin total]**: no se puede mostrar "página N de M". → `limite=21` evita las páginas vacías (D7).
- **[`sub` sin verificar]**: un token alterado podría mostrar `Vos` en registros ajenos. → Solo afecta la presentación en la propia pestaña. La API sigue autorizando con la base (DD-33 a).
- **[Tamaño del PR]**: seis pantallas más el historial. → Tareas agrupadas por pantalla, commits por grupo y el patrón probado primero en sillones (D1).
- **[Tests de C-14 y C-15 que asumen `/configuracion` sin pedidos]**: van a fallar. → Tarea 2.5 los adapta antes de tocar pantallas.
- **[Nombre de un scenario MODIFIED]**: en el delta de `frontend-sesion`, el scenario "Pantallas provisorias sin pedidos" conserva su nombre aunque ahora comprueba lo contrario (que ninguna ruta es provisoria). `openspec validate --strict` exige que un requirement MODIFIED mantenga los nombres de los scenarios del spec vigente, y renombrarlo lo hace fallar. El THEN aclara el sentido nuevo.

## Migration Plan

Sin migración de datos ni de base. Es solo frontend: se despliega con el servicio `frontend` de Compose como hasta ahora. Para volver atrás alcanza con revertir el merge, porque no hay cambios de contrato con la API.

## Open Questions

- **Nombre del autor en la auditoría**: se registra en el backlog de `CHANGES.md` como limitación de DD-25 f (D10). No cambia este change.
- **Lectura del estado de los recordatorios**: sigue abierta en `10_preguntas_abiertas.md` y queda fuera de C-16.
