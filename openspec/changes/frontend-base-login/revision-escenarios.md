# Revisión de escenarios — frontend-base-login (C-14)

- Fecha: 2026-11-09
- Specs revisados: `openspec/changes/frontend-base-login/specs/{frontend-base,frontend-cliente-http,frontend-sesion,app-configuration}/spec.md` (24 requirements, 71 escenarios), con `proposal.md`, `design.md` y `tasks.md`
- Reglas aplicables: RN-AU-01, RN-AU-03, RN-CU-02, RN-CU-03, DD-05, DD-16, DD-17, DD-21 (forma del `409`), DD-24, DD-31 n, DD-32 d, Flujo 1, US-010, `03_actores_y_roles.md` (RBAC, "nunca solo en la UI"), `08_arquitectura_propuesta.md` §Estructura y §Seguridad, spec `autenticacion`, spec `app-configuration`, scope de C-14 en `CHANGES.md`
- No aplican a este change: RN-AU-02 (agenda del odontólogo, C-15 sobre el backend ya entregado) y RN-CU-04 (C-14 no presenta horarios, design D19)
- Veredicto: **CORREGIR ANTES DE APPLY** (0 BLOQUEANTE, 4 MAYOR, 11 MENOR, 3 SUGERENCIA). La tarea 1.3 exige no dejar ningún MAYOR abierto.

## Cobertura

| Requirement | Escenarios | Esperado | Error de negocio | Borde | Reglas cubiertas |
|-------------|-----------:|:--------:|:----------------:|:-----:|------------------|
| Proyecto del frontend | 3 | 3 | 0 | 0 | 08 §Estructura |
| Verificación antes de dar una tarea por terminada | 3 | 1 | 2 | 0 | Regla dura de `ruff` (equivalente) |
| Servicio frontend en Docker Compose | 3 | 3 | 0 | 0 | Scope C-14 |
| Sin secretos en el frontend | 1 | 1 | 0 | 0 | RN-CU-03 |
| URL base de la API | 3 | 2 | 0 | 1 | D2 |
| Token en cada request | 3 | 2 | 0 | 1 | Flujo 1 |
| Respuesta exitosa | 2 | 1 | 0 | 1 | `DELETE` con `204` |
| Error de negocio de la API | 2 | 0 | 1 | 1 | DD-24, DD-21 |
| Error de validación de la API | 2 | 0 | 2 | 0 | DD-31 n |
| Otras fallas | 3 | 0 | 1 | 2 | D15 |
| Formulario de inicio de sesión | 3 | 1 | 1 | 1 | DD-24 c, d |
| Redirección por rol tras el login | 2 | 2 | 0 | 0 | Scope C-14, D7 |
| Login rechazado | 3 | 0 | 2 | 1 | DD-24 a |
| Datos de la sesión tomados del token | 5 | 2 | 1 | 2 | Flujo 1, RN-AU-01, DD-05, D1 |
| Conservación de la sesión en la pestaña | 4 | 2 | 1 | 1 | D3 |
| Fin de la sesión por vencimiento | 4 | 1 | 1 | 2 | DD-24 b, D4 |
| Un 403 de la API no cierra la sesión | 1 | 0 | 1 | 0 | DD-24 b |
| Cierre de sesión | 2 | 1 | 0 | 1 | D8 |
| Guarda de autenticación | 3 | 1 | 1 | 1 | `03` Rutas públicas |
| Usuario con sesión en rutas de entrada | 2 | 2 | 0 | 0 | D6 |
| Guarda por rol | 4 | 3 | 1 | 0 | RN-AU-03, `03` RBAC, D5 |
| Layout de la aplicación | 4 | 3 | 0 | 1 | Scope C-14, límite con C-15 y C-16 |
| Ruta inexistente | 2 | 2 | 0 | 0 | Sin decisión registrada (H15) |
| Orígenes CORS restringidos | 7 | 3 | 2 | 2 | 08 §Seguridad, DD-24, D2 |
| **Total** | **71** | **36** | **17** | **18** | |

El conteo de 24 requirements y 71 escenarios coincide con el spec (`grep` por archivo). `openspec validate frontend-base-login --strict` pasa. Como este change es de frontend, "error de negocio" incluye los rechazos de la API y las prohibiciones de las guardas.

Reglas del scope sin escenario: ninguna queda sin cubrir por completo. `CORS_ORIGINS` (scope de C-14) está cubierta solo en parte: ver H2.

C1 a C9: C1 (tres tipos), C3 (scope: nada de C-15 ni C-16, los placeholders no piden datos) y C8 (solo datos ficticios, sin secretos) están bien. C4 está bien: `401` y `403` respetan DD-24. Los códigos y cuerpos de `rol_insuficiente`, `credenciales_invalidas`, `no_autenticado`, `solapamiento` con `recursos`, `{"detail": "Not Found"}` y el `204` de los `DELETE` coinciden con `backend/app/api/`. Los hallazgos vienen de C2, C5, C6, C7 y C9.

## Hallazgos

### H1 — El requirement cierra la sesión ante un `401` de "cualquier pedido", pero D4 y la tarea 6.6 no · MAYOR
- **Dónde**: `frontend-sesion`, requirement "Fin de la sesión por vencimiento" (falta escenario); `tasks.md` 6.6
- **Problema**: el requirement dice "ante una respuesta `401 no_autenticado` en cualquier pedido". D4 lo limita a "solo si el token del pedido sigue siendo el de la sesión actual", y la tarea 6.6 prueba justamente la excepción. Tal como está, esa tarea contradice el spec y su comportamiento no tiene escenario. El caso del cierre manual con un pedido en curso, que D4 también menciona, no aparece ni en el spec ni en las tareas.
- **Fuente**: design D4; `CLAUDE.md` §Proceso ("NUNCA implementar en Apply algo que no esté en el spec aprobado"); controles C2 y C9
- **Sugerencia**: limitar el requirement a los pedidos hechos con el token vigente y agregar:
  - GIVEN un pedido enviado con el token A, y después una sesión nueva con el token B / WHEN ese pedido responde `401 no_autenticado` / THEN el token B sigue guardado, la ruta no cambia y no se ve el aviso de sesión vencida.
  - GIVEN un pedido en curso y un cierre de sesión manual / WHEN ese pedido responde `401 no_autenticado` / THEN se sigue en `/login` sin el aviso de sesión vencida.

### H2 — CORS: el preflight del propio login, los métodos y las credenciales no tienen escenario · MAYOR
- **Dónde**: `app-configuration`, requirement "Orígenes CORS restringidos" (falta); `tasks.md` 2.2
- **Problema**: el requirement fija `GET`, `POST`, `PATCH`, `DELETE`, los encabezados `Authorization` y `Content-Type` y "sin credenciales", pero los escenarios solo ejercitan `GET` con `Authorization`. `POST /auth/login` con JSON dispara un preflight con `Content-Type`: si esa configuración falla, todos los escenarios pasan y el login no funciona en el navegador. El origen no permitido sí está cubierto, en preflight y en request simple.
- **Fuente**: `CHANGES.md` C-14 (`CORS_ORIGINS`); `08_arquitectura_propuesta.md` §Seguridad ("CORS restringido"); design D2. Comportamiento comprobado con `CORSMiddleware` (Starlette 1.10.0) en una app descartable
- **Sugerencia**:
  - GIVEN `CORS_ORIGINS` igual a `http://localhost:5173` / WHEN `OPTIONS /auth/login` con ese `Origin`, `Access-Control-Request-Method: POST` y `Access-Control-Request-Headers: content-type` / THEN `200`, con `Access-Control-Allow-Origin` y permitiendo `Content-Type`.
  - Igual para `PATCH` y `DELETE` (parametrizado).
  - WHEN preflight con `Access-Control-Request-Method: PUT`, y otro con `Access-Control-Request-Headers: x-otro` / THEN `400`. Hay que afirmar el estado: en estos dos casos la respuesta **sí** incluye `Access-Control-Allow-Origin`.
  - THEN de los escenarios del origen permitido: no incluye `Access-Control-Allow-Credentials`.

### H3 — Un `422` con `detail` objeto no tiene escenario · MAYOR
- **Dónde**: `frontend-cliente-http`, requirements "Error de negocio de la API" y "Error de validación de la API" (falta)
- **Problema**: la API devuelve `422` con dos formas: la lista de FastAPI y `{"detail": {"codigo", ...}}`. El segundo es el caso de `rango_invalido` y `referencia_invalida`, entre otros, y varios llevan campos extra. Los escenarios de `422` solo usan la lista, así que un cliente que decida por `status === 422` en lugar de por la forma de `detail` pasa todos los tests y falla con el rango de la agenda de C-15.
- **Fuente**: DD-32 d (`422` con `{"detail": {"codigo": "rango_invalido", "mensaje": ...}}`); `backend/app/api/turnos.py:373-397`; `backend/app/api/recursos.py:273-284`
- **Sugerencia**: GIVEN una respuesta `422` con `{"detail": {"codigo": "rango_invalido", "mensaje": "Rango inválido"}}` / WHEN se completa el pedido / THEN el error tiene `codigo` `rango_invalido`, ese `mensaje` y ninguna entrada de error por campo.

### H4 — La regla del "último tramo de `loc`" no define dos formas que la API devuelve · MAYOR
- **Dónde**: `frontend-cliente-http`, requirement "Error de validación de la API" (falta)
- **Problema**: el campo es "el último tramo de `loc`, sin el origen". Con `loc: ["body"]` no queda ningún campo, y con `loc: ["body", 5]` queda un número (la posición del JSON). Ambas formas son reales: la primera sale de los `model_validator` de `ReprogramacionIn`, `FranjaCambios` y los recursos, con `msg` igual a `Value error, inicio no admite null`, y de un body ausente. Apply tendría que inventar la respuesta.
- **Fuente**: `backend/app/api/turnos.py:169-174`, `backend/app/api/horarios.py:58-63`, `backend/app/api/recursos.py:109`; respuestas comprobadas con la `ReprogramacionIn` real
- **Sugerencia**: decidir el comportamiento y sumar el escenario (ver Preguntas abiertas, P1).

### H5 — El ciclo de vida del temporizador está sin cubrir · MENOR
- **Dónde**: `frontend-sesion`, requirements "Fin de la sesión por vencimiento" y "Cierre de sesión"; design D4
- **Problema**: faltan tres casos. Un cierre manual debe cancelar el temporizador: si no, al llegar el `exp` viejo aparece el aviso en `/login`, o se cierra una sesión nueva. El temporizador debe programarse tanto tras el login como al arrancar con un token vigente. Y D4 prevé no programarlo si la demora supera `2^31 - 1` ms, lo que contradice el "al llegar el `exp`" del requirement y no tiene escenario ni tarea. Es alcanzable: `JWT_EXPIRE_MINUTES` solo exige ser mayor que cero.
- **Fuente**: design D4 y D8; requirement "Cierre de sesión" ("sin aviso de sesión vencida"); DD-24 f
- **Sugerencia**: GIVEN un usuario que cerró la sesión con un token que vencía en un minuto / WHEN pasa un minuto / THEN sigue en `/login` sin el aviso. Sumar el arranque con token vigente que vence en un minuto, y escenario o nota para la demora excesiva.

### H6 — Casos del requirement de claims sin escenario · MENOR
- **Dónde**: `frontend-sesion`, requirements "Datos de la sesión tomados del token" y "Conservación de la sesión en la pestaña"
- **Problema**: "ya vencido" no tiene escenario de login, y es justo el riesgo de reloj adelantado que acepta el design (la tarea 5.1 solo prueba la función pura). Al arrancar, tampoco está definido si un token legible con `rol` desconocido o sin `exp` es "que no se pueda interpretar" (sin aviso). La función de claims debe distinguir vencido de inválido, porque el arranque los trata distinto, pero el requirement los agrupa.
- **Fuente**: design §Risks ("Reloj del cliente adelantado") y D4; control C7
- **Sugerencia**: GIVEN una respuesta `200` con un token cuyo `exp` ya pasó / WHEN se envía el formulario / THEN mensaje genérico, sigue en `/login`, sin token guardado y sin aviso de sesión vencida. Precisar que al arrancar "no interpretable" incluye `rol` desconocido y falta de `exp`.

### H7 — El claim desactualizado no se nombra en ningún escenario · MENOR
- **Dónde**: `frontend-sesion`, requirements "Un 403 de la API no cierra la sesión" y "Fin de la sesión por vencimiento"
- **Problema**: los caminos existen, pero implícitos. Usuario desactivado: el escenario "La API rechaza el token" lo cubre sin nombrarlo. Rol distinto en la base: "Rol insuficiente" da el resultado correcto. Nada documenta que la guarda y el layout pueden mostrar un rol viejo hasta el `exp`, que es el trade-off de D1. Además, como los placeholders no llaman a la API, en C-14 ningún pedido autenticado puede detectar la situación: aparece recién con C-15.
- **Fuente**: DD-24 b ("el rol que vale es el de la base"); spec `autenticacion`, escenario "Rol del token distinto del rol en la base"; design D1
- **Sugerencia**: GIVEN una sesión cuyo token dice `recepcionista` y un rol `odontologo` en la base / WHEN un pedido responde `403 rol_insuficiente` / THEN el token sigue guardado y el pedido falla con ese `codigo`. Registrar el límite en DD-33.

### H8 — Reloj sin fijar y `exp` sin unidad en el GIVEN · MENOR
- **Dónde**: `frontend-sesion`, escenarios de claims, "Recarga con token vigente", "Arranque con token vencido" y los de vencimiento
- **Problema**: "`exp` futuro", "vigente" y "vencido" dependen del ahora y ningún GIVEN fija el reloj. La tarea 6.5 usa temporizadores falsos, de ahí la severidad; 5.1 y 6.4 no lo aclaran. `exp` está en segundos y `Date.now()` en milisegundos, y "ese vencimiento" no fija ningún valor que atrape esa confusión. `exp` exactamente igual al reloj tampoco está definido al arrancar.
- **Fuente**: controles C5 y C6; spec `autenticacion` ("Token recién vencido")
- **Sugerencia**: GIVEN el reloj en `2026-11-09T12:00:00Z` y un token con `exp` `1794225600` / WHEN la aplicación arranca / THEN la sesión se trata como vencida (o vigente: decidir el borde). Agregar fake timers a 5.1 y 6.4.

### H9 — Los textos que los escenarios afirman no están fijados · MENOR
- **Dónde**: `frontend-sesion` y `frontend-cliente-http`: "aviso de sesión vencida" (7 escenarios, 4 de ellos por su ausencia), "mensaje de falta de conexión", "mensaje genérico"
- **Problema**: el texto del aviso solo está en D4 (`Tu sesión venció. Iniciá sesión de nuevo.`). Una afirmación de ausencia con un texto distinto del real pasa siempre, y es la que garantiza que un login fallido no se confunda con un vencimiento.
- **Fuente**: control C5; design D4
- **Sugerencia**: fijar en el requirement el texto del aviso y el de falta de conexión.

### H10 — "Nunca MUST mostrar el texto crudo del servidor" es ambiguo y choca con conservar `msg` · MENOR
- **Dónde**: `frontend-cliente-http`, requirement "Otras fallas"; requirement "Error de validación de la API"
- **Problema**: "Nunca MUST" no es una forma normativa válida (debería ser MUST NOT). El alcance tampoco queda claro: el `mensaje` de la API también es texto del servidor, y el error por campo conserva `msg` crudo en inglés (`Field required`, `Value error, ...`). D15 distingue "framework" de "API", pero el spec no. La regla tampoco es verificable en el cliente: mostrar es tarea de las pantallas de C-15 y C-16.
- **Fuente**: control C7; design D15
- **Sugerencia**: acotarla a `mensaje`: "el `mensaje` del error MUST NOT ser el `detail` de texto ni el cuerpo de la respuesta", y aclarar que `msg` por campo se conserva sin garantía de que sea apto para mostrar.

### H11 — MUST de `frontend-base` sin escenario · MENOR
- **Dónde**: `frontend-base`, requirements "Proyecto del frontend", "Verificación antes de dar una tarea por terminada" y "Sin secretos en el frontend"
- **Problema**: no hay escenario para la versión de Node declarada (`engines`, D9), para el archivo de bloqueo versionado, ni para que `lint` y `test` fallen ante un problema. "Sin secretos" cubre solo la clave `environment`: no mira `env_file` ni el código del navegador, que el requirement también nombra.
- **Fuente**: control C2; RN-CU-03; DD-17
- **Sugerencia**: WHEN se lee `frontend/package.json` / THEN `engines.node` es `^24.15.0`. Sumar `lint` con un error y que el servicio no declare `env_file`.

### H12 — `CORS_ORIGINS` vacío o `*`, y un "valor por defecto" que depende del `.env` · MENOR
- **Dónde**: `app-configuration`, requirement "Orígenes CORS restringidos", escenario "Valor por defecto"; `tasks.md` 2.1 y 2.2
- **Problema**: la tarea 2.1 prueba `""` sin escenario. D2 acepta `*` sin validarlo, aunque la KB pide CORS restringido y el spec principal exige fallar ante un valor inválido. Además, `create_app()` llama a `ConfiguracionCors()` sin forma de pasar `_env_file=None`, que es como `test_config.py` aísla sus tests: con `monkeypatch.delenv` solamente, el escenario depende del `.env` de cada desarrollador.
- **Fuente**: `backend/tests/unit/test_config.py:23-28`; spec `app-configuration` ("Fallo explícito"); 08 §Seguridad; design §Risks
- **Sugerencia**: probar el valor por defecto sobre `ConfiguracionCors(_env_file=None)`, o inyectar los orígenes en `create_app`. Para `""` y `*`, ver P2.

### H13 — La verificación de la tarea 8.3 no verifica nada · MENOR
- **Dónde**: `tasks.md` 8.3
- **Problema**: `test_env_example.py` recorre `Settings.model_fields` y una lista fija, y `VITE_API_URL` no está en ninguna. La verificación pasa con la línea o sin ella, y el spec `app-configuration` pide listar todas las variables.
- **Fuente**: `backend/tests/unit/test_env_example.py:21-38`; spec `app-configuration` ("Plantilla de entorno"); control C9
- **Sugerencia**: agregar `VITE_API_URL` a `test_env_example_declares_infrastructure_variables` con su RED. El test sí se puede escribir, aunque el agente no pueda editar `.env.example`.

### H14 — D7 cita de más a US-008, y la redirección por rol no distingue roles · MENOR
- **Dónde**: `design.md` D7; `frontend-sesion`, requirement "Redirección por rol tras el login"
- **Problema**: D7 dice que US-008 hace de la agenda "la pantalla principal de ambos roles". US-008 solo dice que ambos quieren ver su agenda, y la misma D7 admite que la KB no define una pantalla de inicio. El scope pide tests de "redirección por rol", pero con un único destino el escenario pasa igual con un redireccionamiento fijo. "MUST definirse en un único lugar" tampoco tiene forma de verificarse en un escenario.
- **Fuente**: `06_funcionalidades.md` US-008; `CHANGES.md` C-14; control C5
- **Sugerencia**: corregir la cita y dejarlo como decisión nueva en DD-33. Es válido, pero conviene decir que los escenarios distinguen por el layout y no por el destino.

### H15 — Decisiones que no llegan a DD-33 · MENOR
- **Dónde**: `tasks.md` 9.2 y 9.3; `frontend-sesion`, requirement "Ruta inexistente"
- **Problema**: la lista de la tarea 9.2 omite D6 (usuario con sesión en `/login`) y D11, aunque la tarea 1.2 pide aprobar D1-D11. La página de "no encontrada" es un comportamiento sin fila en la tabla de decisiones. La tarea 9.3 agrega `VITE_API_URL` a la tabla de `08`, pero no el formato de lista por comas de `CORS_ORIGINS`.
- **Fuente**: `tasks.md` 1.2; design §Decisions; `08_arquitectura_propuesta.md` §Variables de entorno
- **Sugerencia**: completar la lista de 9.2 y sumar el formato de `CORS_ORIGINS` a 9.3.

### H16 — Un solo código de `403` · SUGERENCIA
- **Dónde**: `frontend-sesion`, requirement "Un 403 de la API no cierra la sesión"
- **Problema**: D5 nombra `rol_insuficiente`, `profesional_ajeno` y `paciente_ajeno`, y el escenario solo ejercita el primero. El TDD del proyecto pide triangular cada comportamiento.
- **Fuente**: design D5; `backend/app/api/horarios.py:163`; `backend/app/api/pacientes.py:264`
- **Sugerencia**: parametrizar con los tres códigos.

### H17 — Detalles menores de cliente y tareas · SUGERENCIA
- **Dónde**: `frontend-cliente-http`, escenario "Parámetro de la consulta"; `tasks.md` 5.1
- **Problema**: el `msg` de ejemplo no es el real para ese `type` (la API dice `Input should be a valid date or datetime, input is too short`); no cambia el resultado. La tarea 5.1 prueba base64url con `-` y `_` sin escenario: es razonable como setup. El caso "respuesta de error JSON sin `detail`" (por ejemplo `503` de `/health`) no está contemplado; hoy la SPA no llama a esa ruta.
- **Fuente**: comprobación con FastAPI 0.162.0; control C9; `backend/app/api/health.py:22`
- **Sugerencia**: ajustar el ejemplo y decidir si un cuerpo JSON sin `detail` cae en "Otras fallas".

### H18 — `/configuracion` y las pantallas de C-16 · SUGERENCIA
- **Dónde**: `design.md` D7; `frontend-sesion`, requirement "Guarda por rol"
- **Problema**: la restricción es coherente con RN-AU-03, y `/configuracion` es solo un placeholder, sin invadir C-16. Pero la matriz de `03` da `R` al odontólogo sobre profesionales, sillones y prestaciones, y `R (propios)` sobre horarios. Si C-16 quisiera mostrarle esas vistas de lectura, no podrían vivir bajo esa ruta. D7 solo aclara el caso de los bloqueos.
- **Fuente**: `03_actores_y_roles.md` §RBAC; RN-AU-03; `CHANGES.md` C-16 ("permisos por rol")
- **Sugerencia**: confirmarlo con Matías, responsable de C-16 (ver P3).

## Preguntas abiertas

- **P1 (H4)**: ¿cómo se representa un `422` no atado a un campo (`loc` igual a `["body"]`, o `["body", <posición>]`)? Opciones: (a) error por campo con `campo` nulo; (b) sin entrada por campo, solo el `mensaje` genérico; (c) tomar el nombre del campo del `msg`, frágil porque depende de un texto.
- **P2 (H12)**: ¿`CORS_ORIGINS` vacío o `*` son configuración inválida (la app no arranca, como otras variables) o se aceptan? Opciones: (a) rechazar `*` y aceptar vacío como "ningún origen"; (b) aceptar ambos, como propone D2, y documentarlo.
- **P3 (H18)**: ¿el odontólogo tendrá en C-16 vistas de lectura del catálogo y de sus horarios? Si es así, ¿con qué ruta?

### Decisiones [A confirmar]: sustento en la KB

Las que introducen una regla nueva no contradicen la KB, pero tampoco salen de ella: hasta la aprobación de la tarea 1.2 son preguntas abiertas de hecho, y después van a DD-33 y a la tabla de resueltas de `10_preguntas_abiertas.md` (tareas 9.2 y 9.3).

| Decisión | Evaluación | Fundamento |
|----------|------------|------------|
| D1 Rol por claims, sin verificar firma | **Con sustento** | Flujo 1 y spec `autenticacion` fijan los claims. Confirmado en `tokens.py:44-51`: `rol` es `StrEnum` y sale como texto limpio, `profesional_id` es nulo para la recepcionista y `exp` son segundos. `03`: la autorización es del backend. El riesgo de rol viejo es real solo por SQL directo: el CLI únicamente da altas y desactiva (DD-16, `cli/usuarios.py`). Ver H7 |
| D2 `CORSMiddleware` | **Con sustento** en lo principal | `CHANGES.md` C-14 nombra `CORS_ORIGINS`; `08` pide "CORS restringido"; hoy `main.py` no lo instala. Consistente con el spec principal, que ya lista la variable, y con `create_app()`. El formato por comas y la lista de métodos son decisiones nuevas. Ver H2 y H12 |
| D3 `sessionStorage` | **Regla nueva** | `08` §Seguridad y el resto de la KB no dicen nada sobre dónde se guarda el token (búsqueda sin resultados). No hay conflicto |
| D4 Temporizador y `401` | **Mixta** | `no_autenticado` y su separación de `credenciales_invalidas` salen de DD-24 y están bien cubiertas por el escenario "Credenciales inválidas". El temporizador, el aviso y no volver a la ruta pedida son nuevos. Ver H1 y H5 |
| D5 Pantalla sin permiso | **Mixta** | Que un `403` no cierre la sesión sale de DD-24 b. La pantalla en el lugar es una regla nueva de UX |
| D6 `/login` con sesión | **Regla nueva** | La KB no lo menciona. Bajo impacto |
| D7 Inicio por rol | **Mixta** | `/configuracion` restringida sale de RN-AU-03. `/agenda` como inicio de ambos es nueva. Ver H14 y H18 |
| D8 Cierre de sesión | **Regla nueva** | La KB no lo menciona. Que sea local es forzoso: no hay revocación |
| D9 Node 24 | **Con sustento** | DD-17 lo deja "a confirmar en C-14". Cambia el valor (22 por 24) y `^24.15.0` es más estricto que un mínimo, así que DD-17 debe actualizarse (tarea 9.2) |
| D10 Vite en Docker | **Mixta** | El servicio sale de `CHANGES.md` y `02`. Usar el servidor de desarrollo es nuevo, sin conflicto: el MVP no define despliegue |
| D11 `fetch` falso | **Decisión técnica nueva** | La regla dura de no mockear aplica a la persistencia, no a la red del navegador |

## Fuera de esta revisión

- `.env.example` y `.env*` no se leyeron: el contenido de la plantilla no se verificó.
- El calendario de Node y las versiones y `engines` de npm de `design.md` no se reverificaron en línea (Node local: `24.19.0`, coincide).
- Las comprobaciones de `CORSMiddleware` y de las formas de `422` se hicieron con una app descartable y el `.venv` del proyecto (FastAPI 0.162.0, Starlette 1.10.0), no con el stack completo. No se dejó código en el repo.
- Lo ya conocido y excluido: el texto desactualizado de la tarea 9.4 sobre la fila "Frontend" de `CLAUDE.md`, y las fallas previas de `openspec validate --specs --strict` en otros cuatro specs.
