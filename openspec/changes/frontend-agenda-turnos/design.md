# Design

## Context

Ver `proposal.md` y los delta specs `frontend-agenda`, `frontend-turnos` y `frontend-sesion`. Estado verificado en el código (`feat/c-15-frontend-agenda-turnos`, desde `main` con C-14 y `cliente-http-ajustes-revision`):

**Contrato real de la API** (`backend/app/api/turnos.py`, `recursos.py`, `pacientes.py`, `bloqueos.py`):

- `GET /turnos?desde&hasta&profesional_id&sillon_id` (ambos roles) responde `{turnos, bloqueos}`. `TurnoAgendaOut`: `id`, `profesional_id`, `paciente {id, nombre, apellido}`, `prestacion_id`, `sillon_id` (nulo posible), `inicio`, `fin` (`-03:00`), `duracion_min`, `estado`, `creado_por`, `motivo_cancelacion`. `BloqueoOut`: `id`, `profesional_id`, `inicio`, `fin`, `motivo`, `creado_por`. Sin paginación y con cancelados incluidos.
- **No existe `GET /turnos/{id}`.** El router de turnos solo tiene la agenda, `POST`, cancelar y reprogramar: un formulario no puede recargar un turno por id, y esto condiciona D6.
- **`GET /disponibilidad` no existe en `backend/app`**, aunque figura en `knowledge-base/02_descripcion_general.md` (fila API) y en `07` (Flujos 2 y 5). US-007 está en el backlog de `CHANGES.md`. Es una inconsistencia de la KB (tarea 11.2).
- `POST /turnos`, `PATCH /turnos/{id}/reprogramar` y `POST /turnos/{id}/cancelar` usan `RecepcionistaAutenticada`. `TurnoIn.inicio` y `ReprogramacionIn.inicio` son `AwareDatetime`: un datetime sin zona da `422`.
- `GET /profesionales`, `/sillones` y `/prestaciones` usan `UsuarioDeAmbosRoles`, sin paginación e **incluyen inactivos** (`activo`; en la prestación, `activa`). `PrestacionOut` trae `duracion_min` y `requiere_sillon`.
- `GET /pacientes?q&limite&desplazamiento` usa `RecepcionistaAutenticada` y devuelve la lista con `activo` (DD-31 b, e, g, h).

**Errores reales** (formas verificadas en los manejadores):

| Status | `codigo` | Forma | Origen |
|--------|----------|-------|--------|
| 409 | `solapamiento` | `{codigo, recursos: ["profesional"\|"sillon"\|"paciente"]}`, **sin `mensaje`** | Alta y reprogramación |
| 409 | `turno_ya_cancelado`, `turno_ya_iniciado` | `{codigo, mensaje}` | Cancelar y reprogramar |
| 404 | `turno_inexistente` | `{codigo, mensaje}` | Cancelar y reprogramar |
| 422 | `duracion_invalida`, `inicio_no_alineado`, `inicio_en_pasado`, `sillon_requerido`, `sillon_no_corresponde`, `fuera_de_horario`, `turno_en_bloqueo` | `{codigo, mensaje}`, con texto técnico | Alta y reprogramación |
| 422 | `referencia_invalida` | `{codigo, referencia: "profesional"\|"paciente"\|"prestacion"\|"sillon", motivo: "inexistente"\|"inactiva"}`, **sin `mensaje`** | Alta y reprogramación |
| 422 | `campo_no_editable` | `{codigo, campos, mensaje}` | Reprogramar (el formulario nunca lo provoca) |
| 422 | `rango_invalido` | `{codigo, mensaje}` | Agenda |
| 422 | (validación) | lista `{loc, msg}`; `ErrorApi` con `codigo` `validacion` y `errores[].campo` | Todas |

**Frontend de C-14**: `useClienteApi().pedir(metodo, ruta, cuerpo?)` lanza un único `ErrorApi` (`status`, `codigo`, `mensaje`, `errores`, `datos`); `useSesion().sesion.claims` trae `rol` y `profesionalId`; `/agenda` es un placeholder con `<h1>Agenda</h1>`; **no hay CSS**; `renderizarApp`, `instalarFetchFalso`, `respuestaJson`, `pedidoHecho`, `usarRelojFijo` (2026-11-09T12:00Z, las 09:00 en Buenos Aires, un lunes).

**Comprobado en esta máquina**: la zona del sistema es `America/Buenos_Aires`, así que un test sin zona forzada pasaría aunque el código usara la hora local. `test.env.TZ` en la configuración de Vitest 5.1 (pool `forks`) cambia la zona efectiva en Windows. `Temporal` no existe en Node 24. `Intl` con `timeZoneName: "longOffset"` devuelve `GMT-03:00`. `es-AR` formatea `lun 9-11`, un texto que depende de la versión de ICU. **jsdom 31 no implementa `HTMLDialogElement.showModal`.** En Node 24.19, `longOffset` da `GMT-02:00` para el 2008-01-15, `GMT-03:00` para el 2009-03-16 y un desfasaje con segundos para toda fecha anterior a mayo de 1920 (`GMT-04:16:48` en 1900). `AwareDatetime` (Pydantic 2.14 del `.venv`) rechaza un desfasaje con segundos: da un `422` de validación con `loc` `["body", "inicio"]`, y acepta `-04:16`. `useSearchParams` existe en React Router 8.5 en modo declarativo (Context7).

## Goals / Non-Goals

**Goals:**
- Extender C-14 sin rediseñarlo: `RutasApp`, la sesión, el cliente HTTP y las guardas no cambian.
- Una sola fuente de presentación horaria, reutilizable por C-16.
- Un único traductor de errores de turno, probado contra las formas reales.

**Non-Goals:**
- Lo que lista `proposal.md`. Además: sin capa de caché de datos, sin diseño responsive para teléfonos (el uso es de recepción, en PC) y sin internacionalización.

## Decisions

La KB fija los roles y permisos (03, DD-31 b, DD-32 i), la zona (RN-CU-04), la grilla de 5 minutos (DD-15), los campos editables (DD-23), que las respuestas traen cancelados y al paciente embebido (DD-32 f, j), y `fetch` falso en tests (DD-33 k, D15 de este documento). **Las decisiones marcadas como aprobadas no las fija la KB: el usuario las aprobó el 2026-11-10 con la opción recomendada** (tarea 1.2), junto con las respuestas P1 a P15 de `revision-escenarios.md`, y se registran como **DD-34**. Si alguna cambia, primero `/opsx:update`.

| # | Decisión | Estado | Opción |
|---|----------|--------|--------------------|
| D1 | Forma de la grilla | **Aprobada por el usuario (2026-11-10)** | Eje de 24 h con scroll inicial a las 08:00. Día: una columna por profesional o por sillón. Semana: una columna por día |
| D2 | Semana y período inicial | **Aprobada por el usuario (2026-11-10)** | Lunes a domingo; por defecto, vista diaria de hoy |
| D3 | Turnos cancelados | **Aprobada por el usuario (2026-11-10)** | Ocultos por defecto, con casilla `Mostrar cancelados`; solo cuenta lo visible |
| D4 | Superposición y cruce de días | Técnica, DD-32 e; carriles sobre filas aprobado el 2026-11-10 | Carriles paralelos sobre las filas redondeadas y recorte por día local |
| D5 | CSS | **Aprobada por el usuario (2026-11-10)** | CSS Modules más una hoja base, sin kit de UI |
| D6 | Rutas y formularios | **Aprobada por el usuario (2026-11-10)** | `/agenda` con estado en la URL y diálogos nativos, sin rutas nuevas |
| D7 | Catálogos | **Aprobada por el usuario (2026-11-10)** | Un hook por página, sin caché global; se releen ante `referencia_invalida`, `sillon_requerido` y `sillon_no_corresponde` |
| D8 | Selector de paciente | **Aprobada por el usuario (2026-11-10)** | 300 ms, mínimo 2 caracteres, `limite=20`, inactivos visibles sin poder elegirse |
| D9 | Formulario de alta | **Aprobada por el usuario (2026-11-10)** | Duración vacía usa la de la prestación; fecha por defecto la de la agenda; `noValidate` |
| D10 | Reprogramación | **Aprobada por el usuario (2026-11-10)** | `PATCH` solo con lo que cambió; sin cambios no hay pedido; duración obligatoria |
| D11 | Cancelación | KB, DD-14 y DD-22 | Diálogo de confirmación con motivo opcional |
| D12 | Errores y textos | **Aprobada por el usuario (2026-11-10)** | Un traductor por `codigo`, con la tabla de D12 |
| D13 | Refresco y concurrencia | **Aprobada por el usuario (2026-11-10)** | Relectura tras cada escritura, botón `Actualizar`, sin sondeo |
| D14 | Tiempo | KB más técnica | `Intl` con zona explícita y aritmética de calendario pura, sin librería |
| D15 | Tests | KB, DD-33 k, más técnica | `fetch` falso enrutado, `TZ` forzada y sin MSW |
| D16 | Roles en la UI | KB | Tabla de D16 |
| D17 | Accesibilidad | Técnica | Etiquetas, teclado, `<dialog>` y errores asociados |
| D18 | Organización del código | Técnica, 08 | `features/agenda`, `turnos`, `pacientes`; `shared/tiempo`, `ui`, `estilos` |
| D19 | Fuera de la UI | KB | Sin recordatorios, auditoría ni disponibilidad |

### D1 — Forma de la grilla **[Aprobada por el usuario el 2026-11-10]**

| Opción | A favor | En contra |
|--------|---------|-----------|
| **Eje de 24 h en CSS Grid, con filas de 5 minutos y scroll inicial a las 08:00 (recomendada)** | Ningún elemento queda fuera de la vista. No hace falta calcular una ventana horaria. La posición sale de una función pura | Una columna mide 1728 px (6 px por fila): hay que desplazarse. El scroll inicial no se puede probar en jsdom |
| Ventana variable (08:00 a 20:00, ampliada según los elementos) | Sin scroll en el día típico | Lógica extra, y un bloqueo de varios días obliga a decidir qué extremos amplían la ventana o queda oculto |
| Lista por día, sin eje horario | La más simple | No muestra los huecos ni la duración de un vistazo, que es el diferencial del producto (DD-01) |

- **Vista diaria**: una columna por profesional (activos, más desactivados con elementos visibles en el período). La recepcionista puede cambiar a una columna por sillón (`columnas=sillon`), con `Sin sillón` y `Bloqueos` solo si tienen elementos visibles, porque un bloqueo no pertenece a un sillón (DD-30 d). `columnas=sillon` se ignora en la vista semanal y con rol `odontologo`. El odontólogo tiene siempre una sola columna (D16), también si su profesional está desactivado (P10): la regla de los desactivados vale solo para la recepcionista.
- **Filtros y columnas (P12)**: al agrupar por profesional, el filtro de profesional deja a lo sumo su columna; al agrupar por sillón, siguen los sillones, y el filtro de sillón deja ese sillón y `Bloqueos` si tiene elementos visibles. Un id de filtro ausente del catálogo no genera una columna por sí mismo. Si llega un elemento de un recurso ausente del catálogo, ese elemento sí tiene columna (P13, D7).
- **Vista semanal**: siete columnas, una por día, sin agrupar. El pedido "por profesional y por sillón" se cubre con los filtros, y cada tarjeta, turno o bloqueo, nombra al profesional (y el turno, al sillón) cuando la columna no lo dice. Con 7 días × 5 profesionales, una matriz tendría 35 columnas.
- Cada fila son 5 minutos (288 por día): `grid-row` sale de los minutos del día. Los bloqueos pueden no estar alineados (DD-30 f), así que el inicio se redondea hacia abajo y el fin hacia arriba solo para ubicarlos; el texto muestra la hora real. El contrato de filas, recorte y carriles está en el requirement "Ubicación en la grilla", sobre funciones puras; la geometría y el scroll inicial se verifican a mano (tarea 10.2).
- Una columna con N carriles define N subcolumnas de al menos 90 px, y la grilla se desplaza en horizontal si no entra.
- **Fuera de alcance**: crear un turno al hacer clic en una celda vacía; se usa el botón `Nuevo turno`.

### D2 — Semana y período inicial **[Aprobada por el usuario el 2026-11-10]**

**Recomendado: lunes a domingo**, coherente con `dia_semana` 0 = lunes (DD-27 a) y con el escenario "Agenda semanal" del spec `consulta-agenda` (lunes 2026-10-05 a domingo 2026-10-11). La alternativa domingo a sábado no tiene respaldo en la KB. Por defecto se muestra la vista diaria de hoy, porque la recepción trabaja sobre el día; la alternativa de abrir en la semana muestra más de lo que se usa. El rango se pide con `desde = lunes` y `hasta = domingo` (7 días, el máximo de DD-32 d). "Hoy" se calcula en Buenos Aires (D14).

### D3 — Turnos cancelados **[Aprobada por el usuario el 2026-11-10]**

| Opción | A favor | En contra |
|--------|---------|-----------|
| **Ocultos por defecto, con casilla (recomendada)** | Un horario liberado se ve libre (RN-AG-07), que es para lo que se mira la grilla. El filtrado es local: `GET /turnos` siempre los trae (DD-32 f) y la casilla no hace pedidos | Quien no active la casilla no se entera de una cancelación en la grilla |
| Visibles por defecto, atenuados | El historial del día está a la vista | Un horario libre parece ocupado y la grilla se llena de carriles |

Es una decisión de UI: DD-32 f solo sostiene que la API trae los cancelados. Visibles, llevan el texto `Cancelado`, tachado y borde punteado (no solo color) y van en su propio carril. La casilla se guarda en la URL (`cancelados=1`).

**Qué cuenta como elemento (P1)**: solo lo visible. Sin elementos visibles se usa el mensaje de período vacío; si la respuesta trae solo cancelados ocultos, `Solo hay turnos cancelados en este período. Activá Mostrar cancelados para verlos.`; para la recepcionista, un profesional desactivado sin nada visible no tiene columna, tampoco si se lo filtra.

### D4 — Superposición y cruce de días

Dos funciones puras en `features/agenda/grilla.ts`:

- `segmentosPorDia(elemento, dias)`: un segmento por cada día local visible que toca, con minutos recortados a `[0, 1440]` y la indicación de si continúa antes o después. Cubre el turno que cruza la medianoche (DD-32 e) y el bloqueo de varios días. Con `[)`, un fin exacto a las 00:00 no genera un segmento de 0 minutos en el día siguiente.
- `asignarCarriles(segmentos)`: por orden de inicio, cada segmento toma el primer carril libre, con criterio `[)` (RN-AG-03) **sobre las filas ya redondeadas (P6)**, para que dos bloqueos contiguos que comparten una fila no se tapen. Cubre cancelado junto a programado, bloqueos superpuestos (DD-30 b) y varios profesionales en un día de la semana.

### D5 — CSS **[Aprobada por el usuario el 2026-11-10]**

| Opción | A favor | En contra |
|--------|---------|-----------|
| **CSS Modules (incluido en Vite) más `shared/estilos/base.css` con variables y reset (recomendada)** | Sin dependencias. Estilos con alcance por componente. C-16 reutiliza las variables | Se escribe el CSS a mano |
| Tailwind | Rápido y consistente | Dependencia y configuración nuevas para unas pocas pantallas |
| Kit de UI (MUI, etc.) | Componentes listos | Dependencia pesada; **DD-33 descartó sumar kit de UI** y no resuelve la grilla, que es lo difícil |
| CSS global sin módulos | Lo más simple | Colisiones de nombres con C-16, que trabaja en paralelo |

### D6 — Rutas y formularios **[Aprobada por el usuario el 2026-11-10]**

| Opción | A favor | En contra |
|--------|---------|-----------|
| **`/agenda` con estado en parámetros de URL y formularios en diálogos (recomendada)** | No toca `RutasApp`. La vista sobrevive al F5 y al botón atrás. El formulario tiene el turno en memoria | Un formulario abierto no es un enlace compartible |
| Rutas `/agenda/turnos/nuevo` y `/agenda/turnos/:id/reprogramar` | URL propia por formulario | **Sin `GET /turnos/{id}`** un F5 no puede recuperar el turno: exigiría un cambio de backend o rastrear el turno en la agenda |

Parámetros: `vista` (`dia`, `semana`), `fecha`, `profesional`, `sillon`, `columnas`, `cancelados`. Se validan con una función pura: `fecha` por formato, calendario real y **año de 1000 a 9998 (P7)**, porque `Date.UTC` interpreta los años 0 a 99 como 19xx y `9999-12-31` da `422 rango_invalido`; ids por forma de UUID (uno mal formado daría `422`), y un valor inválido se ignora. Un UUID bien formado que no existe da `200` vacío (DD-32 l) y el selector lo muestra con el texto genérico (`Profesional no disponible`). Cada cambio hace una navegación nueva. Ningún dato de paciente va en la URL (DD-31 o).

**Diálogos**: `<dialog>` nativo con `showModal()`, que da foco atrapado, `Esc` y `::backdrop` sin dependencias. jsdom no lo implementa, así que `src/test/setup.ts` agrega un reemplazo de `showModal` y `close` que además es espía, para afirmar que se abrió como modal y no solo con `open`. `Dialogo` sincroniza su estado con los eventos `cancel` y `close`, para que un `Esc` no impida volver a abrirlo. El detalle del turno es un diálogo para ambos roles, con acciones solo para la recepcionista. **Sin diálogos apilados (P15)**: el detalle se cierra al abrir `Reprogramar` o `Cancelar turno`, y `Volver` o el éxito llevan a la agenda, no al detalle.

### D7 — Catálogos **[Aprobada por el usuario el 2026-11-10]**

`TurnoAgendaOut` solo trae ids. `useCatalogos()` hace los tres `GET` en paralelo al montar la página, los guarda en estado y expone mapas por id más `recargar()`.

| Opción | A favor | En contra |
|--------|---------|-----------|
| **Hook en la página, sin caché global (recomendada)** | Sin gestor de estado (DD-33). Datos frescos cada vez que se entra a `/agenda`, que además refleja los cambios hechos en C-16 | Tres pedidos por cada entrada a la pantalla |
| Contexto global con caché | Un solo pedido por sesión | Hay que invalidarlo cuando C-16 cambia un recurso, y no se pidió |
| Hacer `GET /{recurso}/{id}` por cada id | Datos exactos | Decenas de pedidos por vista |

Los mapas incluyen inactivos, porque hay turnos históricos que los referencian. Los filtros muestran todos, con la marca `(inactivo)`; los formularios, solo los activos, más el valor actual al reprogramar. Se releen ante `referencia_invalida`, `sillon_requerido` y `sillon_no_corresponde`, porque los tres revelan un catálogo desactualizado (DD-26); `Actualizar` no los relee. Un id desconocido se ve con un texto genérico y, si la agrupación es por ese recurso, tiene columna (P13), para que el turno no desaparezca. Si falla una relectura con el formulario abierto, el formulario sigue abierto y el error se muestra como general (P14); la pantalla de error con `Reintentar` queda para la carga inicial.

### D8 — Selector de paciente **[Aprobada por el usuario el 2026-11-10]**

La KB fija que `GET /pacientes` es solo de la recepcionista, que `q` busca por subcadena sin mínimo ni acentos (DD-31 e, f) y que los inactivos aparecen (DD-31 g). **No fija** el comportamiento del selector:

| Punto | Recomendado | Alternativa | Trade-off |
|-------|-------------|-------------|-----------|
| Espera | 300 ms | Sin espera | Un pedido por tecla |
| Mínimo | 2 caracteres | Sin mínimo | Con 1, listas largas y poco útiles; se busca por recorte de espacios |
| Límite | `limite=20`, con aviso de refinar | Paginar con `desplazamiento` | La búsqueda por documento o apellido basta; paginar suma UI |
| Inactivos | Visibles, marcados y **no elegibles** | Ocultarlos | La API los rechaza (`referencia_invalida`); verlos explica por qué no se puede y evita creer que no existe |
| Forma | Campo de búsqueda más lista de botones, con anuncio de resultados | Combobox ARIA completo | Tab y Enter alcanzan para el alcance; un combobox suma manejo de foco y flechas |

El documento se muestra solo aquí, para distinguir homónimos: la recepcionista ya lo lee (DD-31). Las búsquedas fuera de orden se descartan con el mismo mecanismo que la agenda.

### D9 — Formulario de alta **[Aprobada por el usuario el 2026-11-10]**

Campos: profesional, paciente, prestación, sillón (según `requiere_sillon`), fecha (`date`), hora (`time`, `step=300`) y duración (`number`, `step=5`, `min=5`, `max=480`).

- **Duración vacía usa la de la prestación** y se omite del pedido, con la leyenda `Por defecto: 45 min`. La alternativa de precargarla enviaría siempre un valor y dejaría de distinguir un ajuste real.
- **Fecha por defecto**: la de la agenda en curso. **Hora**: vacía, para obligar a elegirla. **Profesional**: el del filtro, si hay uno y está activo; un filtro por un desactivado no precarga nada.
- **Selectores**: solo recursos activos, en el orden en que los entrega la API (D7). Tras un `referencia_invalida`, el valor rechazado sigue como opción hasta que se cambie (P5): marcado `(inactivo)` con su nombre del catálogo o, si ya no figura (`inexistente`), con el texto genérico y sin la marca. Si es el valor actual del turno, sigue ofreciéndose mientras lo sea (P11). No aplica al paciente, que no es una opción de una lista.
- **Validación (P8)**: el formulario usa `noValidate`. Los obligatorios se comprueban con errores propios (`Elegí un paciente.`, `Completá este campo.`), y DD-15, RN-AG-12, horario y bloqueos **no se validan por adelantado**: `step`, `min` y `max` solo guían al usuario, y la API decide con errores ya traducidos (D12). Hay una sola vía de error y no se duplican reglas de dominio en el cliente.

Tras un alta exitosa la agenda **no** salta a la fecha del turno: se confirma con día y hora. La alternativa de saltar haría perder el contexto de quien carga varios turnos.

### D10 — Reprogramación **[Aprobada por el usuario el 2026-11-10]**

| Opción | A favor | En contra |
|--------|---------|-----------|
| **Enviar solo lo que cambió; sin cambios, no hay pedido (recomendada)** | Usa el `PATCH` parcial de DD-23 a. No pisa campos que otro usuario haya cambiado. Evita un registro de auditoría vacío (DD-25 g) | Hay que comparar contra el turno original |
| Enviar siempre todos los campos | Más simple | Puede pisar cambios ajenos y audita operaciones sin efecto |

Paciente y prestación se muestran como texto (DD-23 b). Si el catálogo cambió `requiere_sillon` después de crear el turno (consecuencia de DD-26), el selector sigue a la prestación: el `sillon_id: null` acompaña a otro cambio cuando ya no corresponde, y el campo aparece vacío y obligatorio cuando ahora se requiere.

- **Duración vaciada (P3)**: obligatoria, con `Ingresá la duración.` y sin pedido, porque acá vacío no significa "la de la prestación" y `duracion_min: null` da `422` (DD-23 a).
- **Formulario intacto con sillón sobrante (P4)**: `No hiciste cambios.` y sin pedido; el `sillon_id` nulo por sí solo no cuenta como cambio.
- **Orden (P9)**: primero los obligatorios y después la comparación. Fecha, hora y sillón requerido vacíos muestran `Completá este campo.` sin pedido, y la duración, `Ingresá la duración.`. Un turno sin sillón cuya prestación ahora lo requiere pide el sillón antes de evaluar si hubo cambios.
- **Selectores**: los recursos activos más el valor actual del turno (D7).
- Como en el alta, el formulario usa `noValidate` (P8).

### D11 — Cancelación

Diálogo con paciente, día y hora, motivo opcional (`maxLength=255`, como `CancelacionIn`) y `Volver`. Motivo en blanco: pedido sin cuerpo, que la API acepta (spec `agenda-turnos`).

### D12 — Errores y textos **[Aprobada por el usuario el 2026-11-10]**

Una función pura `interpretarErrorTurno(error, operacion)` devuelve `{general, porCampo, turnoObsoleto, releerCatalogos, releerAgenda}`.

| `codigo` | Destino | Texto |
|----------|---------|-------|
| `solapamiento` | General, relee la agenda | `Ese horario ya está ocupado para el profesional, el sillón y el paciente.` (solo los de `recursos`, en ese orden, el de `ORDEN_RECURSOS`: con dos, `... para el profesional y el paciente.`) |
| `fuera_de_horario` | General | `El turno queda fuera del horario de atención del profesional.` |
| `turno_en_bloqueo` | General, relee la agenda | `El turno se superpone con un bloqueo de la agenda del profesional.` |
| `inicio_en_pasado` | Hora | `El inicio no puede estar en el pasado.` |
| `inicio_no_alineado` | Hora | `El horario debe ser múltiplo de 5 minutos.` |
| `duracion_invalida` | Duración | `La duración debe ser múltiplo de 5, de 5 a 480 minutos.` |
| `sillon_requerido` | Sillón, que se muestra aunque el catálogo no lo pida; relee catálogos | `Esta prestación requiere un sillón.` |
| `sillon_no_corresponde` | General, relee catálogos | `Esta prestación no usa sillón.` |
| `referencia_invalida` | Su campo, o general; relee catálogos | `El sillón está inactivo.` / `El profesional no existe.` / `La prestación está inactiva.` … |
| `referencia_invalida` en reprogramar, de `paciente` o `prestacion` | General | `El paciente está inactivo: este turno no se puede reprogramar, pero sí cancelar.` / `La prestación está inactiva: este turno no se puede reprogramar, pero sí cancelar.` (DD-26) |
| `turno_ya_cancelado` | General, obsoleto, relee la agenda | `Este turno ya fue cancelado.` |
| `turno_ya_iniciado` | General, obsoleto, relee la agenda | `Este turno ya inició: no se puede modificar.` |
| `turno_inexistente` | General, obsoleto, relee la agenda | `Este turno ya no existe.` |
| `validacion` | Campo: `Revisá este campo.`; sin campo: general | `Revisá los datos ingresados.`; `inicio` se mapea a Hora; `msg` no se muestra |
| `rol_insuficiente` | General | `No tenés permiso para esta operación.` |
| otro código, sin código o `status` 0 | General | `error.mensaje` |

Se traduce por `codigo` porque `solapamiento` y `referencia_invalida` no traen `mensaje`, y los demás están escritos para desarrolladores. Los datos del formulario viven en estado controlado y no se limpian ante un error. Los textos de obligatorios (`Completá este campo.`, `Ingresá la duración.`) no salen de este traductor, porque no hay pedido.

### D13 — Refresco y concurrencia **[Aprobada por el usuario el 2026-11-10]**

| Opción | A favor | En contra |
|--------|---------|-----------|
| **Relectura tras cada escritura y tras un error que revela un cambio (`solapamiento`, `turno_en_bloqueo` y turno obsoleto), más botón `Actualizar` (recomendada)** | Una sola fuente de verdad. Sin procesos en segundo plano | Lo que cambió otro usuario no aparece hasta actualizar |
| Sondeo cada N segundos | Agenda viva | Más carga, más casos de carrera con un formulario abierto; nadie lo pidió |
| WebSocket o SSE | Tiempo real | Cambio de backend |

**Respuestas fuera de orden**: el efecto de carga marca su pedido como no vigente al limpiarse, y solo uno vigente escribe el estado. Los datos se guardan junto con su clave (rango y filtros) y solo se muestran si coincide con la clave actual, así que `cargando` se deriva sin mezclar períodos. `Actualizar` y las relecturas posteriores a una escritura mantienen la misma clave y conservan los datos a la vista, pero invalidan el pedido en curso: una lectura vieja del mismo período que llega después no pisa el turno recién creado. Si la relectura posterior a un alta falla, el alta sigue confirmada y el error se muestra junto con los datos anteriores. No se agrega `AbortController` al cliente de C-14: descartar basta y no lo modifica.

**Otro usuario cambió el turno**: no hay `ETag` ni versión. `turno_ya_cancelado`, `turno_ya_iniciado` y `turno_inexistente` se detectan por la API. Otro cambio de horario no se detecta: la reprogramación es **última escritura gana**, y la mitiga solo parcialmente el envío parcial de D10: el resultado puede mezclar el profesional de un usuario con la hora de otro, y la auditoría deja trazada la instantánea (DD-25 b). Resolverlo requiere un cambio de backend y queda como limitación aceptada, a registrar en DD-34.

### D14 — Tiempo

`shared/tiempo/zonaConsultorio.ts`, sin librería:

- **Instante a local**: `Intl.DateTimeFormat("en-CA", { timeZone, hourCycle: "h23", ... }).formatToParts`, que da fecha y hora estables. `hourCycle: "h23"` evita `24:00`.
- **Calendario**: las fechas son texto `YYYY-MM-DD`, y sumar días o hallar el lunes se hace con `Date.UTC` y getters UTC, independientes de la zona. Los nombres de días son una tabla propia, porque la salida de `es-AR` depende de ICU.
- **Local a instante**: `aInstanteConDesfasaje(fecha, hora)` obtiene el desfasaje de la zona IANA con `timeZoneName: "longOffset"` (en dos pasadas), no con un `-03:00` fijo, por SU-08. Es poco código a cambio de no depender del supuesto, y los tests lo distinguen con `2008-01-15` (`-02:00`) y `2009-03-16` (`-03:00`). El análisis del desfasaje acepta segundos y no lanza: antes de mayo de 1920 devuelve, por ejemplo, `1900-01-15T10:00:00-04:16:48`, que la API rechaza con un `422` de validación sobre `inicio` (se ve `Revisá este campo.` en `Hora`). Esa fecha se puede tipear en el formulario, porque P7 solo acota el parámetro `fecha` de la URL; el daño se limita a la redacción, ya que una fecha pasada se rechazaría igual por `inicio_en_pasado` (RN-AG-12), así que no se recorta el desfasaje.
- La zona es una constante del frontend. `APP_TIMEZONE` del backend no se expone; el sistema es monotenant (SU-07).

Alternativas: `date-fns-tz` o `Luxon` (dependencia para cuatro funciones) y `Temporal` (no disponible en Node 24).

### D15 — Tests

- **`showModal`**: el reemplazo de `setup.ts` es un espía (D6).
- **`fetch` falso, sin MSW** (DD-33 k). La reevaluación no lo justifica: con pedidos en paralelo solo hace falta responder por método y ruta, no interceptar la red. Se agrega `src/test/apiFalsa.ts` sobre `instalarFetchFalso`, con respuestas por `"GET /turnos"` y pedidos pendientes para los casos fuera de orden, y catálogos y agenda vacíos por defecto.
- **Zona**: `test.env.TZ = "Asia/Tokyo"` en `vite.config.ts`, para **toda** la suite: cualquier uso accidental de la zona local falla. Un test de control afirma que la zona efectiva es `Asia/Tokyo` y que el turno de las 22:30 da `getHours() === 10`, para que el mecanismo no quede en falso silencioso.
- **Reloj**: `usarRelojFijo()`. Los bordes de 299 y 300 ms del selector usan fake timers **sin** `shouldAdvanceTime`.
- **Capas**: funciones puras (`zonaConsultorio`, `grilla`, parámetros de URL, `interpretarErrorTurno`); pantalla completa con `renderizarApp("/agenda?...")`. jsdom no calcula el layout: la posición se prueba en las funciones puras.
- **Tests de C-14**: los que renderizan `/agenda` con respuestas encoladas se adaptan. `sesion.test.tsx` depende del orden de `mockResolvedValueOnce`, y la pantalla ahora consume respuestas al montarse.

### D16 — Roles en la UI (KB)

| | Recepcionista | Odontólogo |
|---|---|---|
| Agenda | Todos los profesionales | La suya, sin enviar `profesional_id` (DD-32 i) |
| Filtro de profesional, agrupar por sillón | Sí | No |
| Columnas de la vista diaria | Por profesional o por sillón | Una sola, la de su profesional (claim `profesional_id`), aunque esté vacía (P2) o él esté desactivado (P10) |
| Filtro de sillón, vistas, cancelados | Sí | Sí |
| Detalle del turno | Con acciones | Solo lectura |
| `Nuevo turno`, reprogramar, cancelar | Sí | No se renderizan |
| `GET /pacientes` | Sí | Nunca (DD-31 b) |

El rol sale de los claims y solo decide qué se muestra (DD-33 a).

### D17 — Accesibilidad

Etiquetas en todos los controles; columnas como `<section aria-label>` con `<ol>` en orden cronológico, con el recurso (`Ficticia, Ana`) o el día (`Lunes 09/11`) como nombre; turnos como `<button>`; `<dialog>` con `aria-labelledby`; errores de campo con `aria-invalid` y `aria-describedby`; error general con `role="alert"`; confirmaciones y resultados con `role="status"`. Sin navegación por flechas en la grilla: excede el alcance.

### D18 — Organización del código

```
frontend/src/
├── pages/PaginaAgenda.tsx          # compone agenda, detalle y formularios
├── features/agenda/                # tipos, api, parámetros de URL, grilla, useAgenda, useCatalogos, componentes
├── features/turnos/                # api, erroresTurno, FormularioNuevoTurno, FormularioReprogramar, DialogoCancelar
├── features/pacientes/             # SelectorPaciente y su api (C-16 puede reutilizarlos)
├── shared/tiempo/zonaConsultorio.ts
├── shared/ui/Dialogo.tsx
├── shared/estilos/base.css
└── test/apiFalsa.ts, fabricas.ts
```

### D19 — Fuera de la UI (KB)

- **Recordatorios**: la lectura de su estado sigue abierta en `10_preguntas_abiertas.md` y no tiene endpoint.
- **Auditoría**: C-16 la implementa.
- **Disponibilidad**: el endpoint no existe (Context). El formulario informa los conflictos por los errores de la API.

## Risks / Trade-offs

- [Reprogramar es última escritura gana, y el envío parcial puede dejar una mezcla que nadie vio] → Envío parcial (D10), relectura y auditoría de la instantánea (DD-25 b). Sin versión del turno no hay solución en el frontend.
- [Reloj del cliente incorrecto: "hoy" y las acciones visibles se equivocan] → Son solo presentación: la API rechaza con `409` o `422` y el formulario lo explica.
- [Un `500` no controlado llega sin encabezados CORS y se ve como falla de red] → Limitación ya aceptada en DD-33.
- [Rol del token desactualizado] → `403` se muestra en el formulario, sin cerrar la sesión (DD-33 a).
- [Una columna muy alta] → Scroll inicial a las 08:00 y `Actualizar` conserva la posición.
- [El reemplazo de `showModal` en tests no prueba foco ni `Esc` real] → El espía afirma la apertura modal y `Dialogo` se prueba con eventos `cancel` y `close`; foco atrapado y `Esc` real, verificación manual (tarea 10.2).
- [Vista semanal angosta con muchos profesionales] → Subcolumnas de 90 px, scroll horizontal y filtro.
- [`react-hooks` 7 marca `setState` síncrono dentro de un efecto] → `cargando` se deriva de la clave (D13), sin escribir estado al iniciar el efecto.
- [C-16 trabaja en paralelo y reutiliza piezas] → Avisar a Matías en el PR sobre `shared/tiempo`, `shared/ui/Dialogo`, `base.css` y `SelectorPaciente`.

## Migration Plan

Sin migración de datos ni cambios de backend: la cabeza de Alembic sigue en `010`. Se despliega con el servicio `frontend` existente. Rollback: revertir el PR.

## Open Questions

- Lectura del estado de los recordatorios: sigue abierta en `10_preguntas_abiertas.md`; no afecta a este change.
- Si en el futuro se quisiera detectar ediciones concurrentes, habría que agregar versión o `ETag` al turno (backlog, no bloquea).
