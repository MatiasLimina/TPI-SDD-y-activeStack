# Tasks

> Governance BAJO según `CHANGES.md`, pero el change maneja el token de sesión: D1-D11 de `design.md` fueron aprobadas por el usuario el 2026-11-09. Estas tareas asumen esas opciones; si alguna cambia, primero `/opsx:update` (spec, design y tareas) y recién después el Apply.
>
> TDD estricto: en cada tarea RED (test que falla, verificado ejecutándolo) → GREEN (mínimo código) → triangular → refactor con tests en verde. Solo datos ficticios en tests, fixtures y ejemplos (`recepcion@example.com`, UUIDs inventados, firma `firma-ficticia`). Skills a cargar: `tdd` y `vitest` en el frontend (la skill documenta 5.1.0-beta.1 y el proyecto fija la 5.1.0, ver D12); `fastapi-python` y `python-testing-patterns` en el grupo 2. React Router y React Testing Library se consultan en Context7.
>
> **Sin migración**: ninguna tarea toca `backend/alembic/versions/` y la cabeza sigue en `010`.

## 1. Preparación

- [x] 1.1 Safety net: correr `pytest` completo en `backend/` y `ruff check` más `ruff format --check`, y registrar el baseline en verde; si algo falla, frenar y reportarlo como falla preexistente
- [x] 1.2 Aprobación previa al Apply: el usuario aprobó D1-D11 de `design.md` el 2026-11-09 con la opción recomendada (se registran como DD-33 en 9.2) y respondió P1, P2 y P3 de la revisión; la tabla de Decisions ya no tiene ninguna fila pendiente de aprobación
- [x] 1.3 Correr `revisar-escenarios frontend-base-login` y resolver con `/opsx:update` todo hallazgo BLOQUEANTE o MAYOR; verificar que `openspec/changes/frontend-base-login/revision-escenarios.md` no deja ninguno abierto y que `openspec validate frontend-base-login --strict` pasa

## 2. CORS en la API (D2; cambio de backend)

- [x] 2.1 RED→GREEN: `tests/unit/test_config.py`, siempre con `ConfiguracionCors(_env_file=None)` para no depender del `.env` de cada desarrollador — separa `CORS_ORIGINS` por comas, recorta espacios y descarta vacíos (`"http://localhost:5173, http://consultorio.example.com"` da dos orígenes; `""` da ninguno; sin variable da `["http://localhost:5173"]`); `*` y `http://localhost:5173, *` fallan con un `ValidationError` que menciona `CORS_ORIGINS` (`field_validator`, igual que `APP_TIMEZONE`); carga sin `JWT_SECRET` ni `DATABASE_URL`; `Settings` sigue teniendo el campo y también rechaza `*`; verificar con `pytest tests/unit/test_config.py`
- [x] 2.2 RED→GREEN: `tests/integration/test_cors.py`, con `create_app()` real y `CORS_ORIGINS` por `monkeypatch.setenv`, que gana sobre el `.env` — preflights desde origen permitido: `OPTIONS /turnos` con `Authorization`, `OPTIONS /auth/login` con `POST` y `Content-Type`, `PATCH` y `DELETE`, todos `200` con `Access-Control-Allow-Origin` y sin `Access-Control-Allow-Credentials`; `PUT` y `x-otro` afirman el estado `400`, porque esas respuestas sí incluyen `Access-Control-Allow-Origin`; otro origen da `400` sin ese encabezado; varios orígenes con espacios y lista vacía (requirements "Orígenes CORS restringidos" y "Valor de CORS_ORIGINS"); instalar `CORSMiddleware` en `create_app` con los métodos y encabezados de D2, leyendo solo `ConfiguracionCors` y no `get_settings()`; verificar con `pytest tests/integration/test_cors.py`
- [x] 2.3 RED→GREEN: en el mismo archivo — `GET /turnos` sin token con origen permitido da `401 no_autenticado` con `Access-Control-Allow-Origin`, con otro origen da `401` sin ese encabezado, y `GET /health` sin `Origin` no lo incluye; verificar con el mismo archivo
- [x] 2.4 RED→GREEN: mismo archivo — con `CORS_ORIGINS` igual a `*` y a `http://localhost:5173, *`, `with TestClient(create_app())` lanza un `ValidationError` que menciona `CORS_ORIGINS` (validación en el `lifespan`, D2); `create_app()` sin arrancar no lanza y un preflight desde otro origen no recibe `Access-Control-Allow-Origin`; verificar con el mismo archivo, `pytest` completo y `ruff check` más `ruff format --check`

## 3. Scaffolding del frontend (D9, D12, D16)

- [x] 3.1 Crear `frontend/package.json` con `engines.node` `^24.15.0` y las dependencias exactas de la tabla de D12 (sin `react-router-dom`), más las carpetas `src/features/`, `src/shared/` y `src/pages/`; generar y versionar `package-lock.json`; verificar con `npm ci`, con `npm ls vitest typescript react-router`, que muestran las versiones fijadas, y con `git check-ignore frontend/package-lock.json`, que no lo ignora
- [x] 3.2 **Consultar Context7 antes de escribir `vite.config.ts`** (`/vitejs/vite/v8.3.5`: configuración, `@vitejs/plugin-react` y cambios del bundler) y `/vitest-dev/vitest` (entorno jsdom y `setupFiles`); escribir `vite.config.ts` (D12: `port` 5173, `strictPort`, sección `test`), `index.html`, `tsconfig` en modo `strict` con `types` explícitos, y `src/test/setup.ts` con `@testing-library/jest-dom/vitest`; verificar con `npm run typecheck` y dejar registrado en el reporte qué se consultó
- [x] 3.3 RED→GREEN: primer test en `src/App.test.tsx`: `App` dentro de `MemoryRouter` renderiza sin errores en jsdom, afirmando un texto visible (se confirma el RED antes de crear `App.tsx`), y `main.tsx` monta `BrowserRouter`; verificar con `npm test` y `npm run build`, que genera `dist/`
- [x] 3.4 Configurar ESLint flat con `@eslint/js`, `typescript-eslint` y `react-hooks`, Prettier con `.prettierignore`, y los scripts de D16; verificar que `npm run lint` y `npm run format:check` pasan, y que un error de tipos, una variable sin usar, un archivo mal formateado y un test que falla, todos de prueba, hacen fallar `typecheck`, `lint`, `format:check` y `test` (requirement "Verificación antes de dar una tarea por terminada"), descartando esos archivos después
- [x] 3.5 Agregar `dist/` y `coverage/` a `.gitignore`; verificar con `git status` que `frontend/node_modules/` y `frontend/dist/` no aparecen

## 4. Cliente HTTP (D15)

- [x] 4.1 RED→GREEN: `src/shared/api/cliente.test.ts` — URL con `VITE_API_URL`, sin configurar y con barra final; `Authorization: Bearer` con sesión y sin encabezado sin sesión; el token nunca en la URL (requirements "URL base de la API" y "Token en cada request"); verificar con `npm test -- cliente`
- [x] 4.2 RED→GREEN: mismo archivo — `200` entrega el JSON y `204` resuelve sin valor; ante un `500` la consola no recibe el token; verificar con `npm test -- cliente`
- [x] 4.3 RED→GREEN: mismo archivo — `ErrorApi` para `{"detail": {"codigo", "mensaje"}}` (`rol_insuficiente`) y sin `mensaje` conservando extras (`solapamiento` con `recursos`); `422` con `detail` objeto, con mensaje (`rango_invalido`) y sin él (`referencia_invalida`, con `referencia` y `motivo`), sin errores por campo: se decide por la forma de `detail`, no por el `status`; los tests afirman los textos literales del spec; verificar con `npm test -- cliente`
- [x] 4.4 RED→GREEN: mismo archivo — lista de `422`: campo del body y parámetro de consulta, conservando `msg`; `loc` `["body"]` y `["body", 5]` dan `campo` nulo, también mezclados con un error de campo (P1); `detail` de texto, JSON sin `detail` (`503`), cuerpo no JSON y falla de red con `status` `0`; el `mensaje` nunca es el `detail` de texto ni el cuerpo; verificar con `npm test -- cliente`, `npm run lint` y `npm run typecheck`

## 5. Datos de la sesión (D1)

- [x] 5.1 RED→GREEN: `src/features/sesion/claims.test.ts` — con el helper de tokens ficticios de `src/test/` y el reloj fijo (`vi.useFakeTimers`, `vi.setSystemTime("2026-11-09T12:00:00Z")`): claims de recepcionista (`profesional_id` nulo) y de odontólogo, con `exp` en segundos; distingue inválido (no es JWT, sin `exp` numérico, `rol` desconocido, aunque su `exp` haya pasado) de vencido (`exp` menor o igual al reloj, con el borde igual); base64url con `-` y `_` se decodifica; verificar con `npm test -- claims`

## 6. Login y sesión (D3, D4, D6, D8, D17)

- [x] 6.1 RED→GREEN: `src/pages/PaginaLogin.test.tsx` (costura `App` en `MemoryRouter`, `fetch` falso) — el envío hace un único `POST /auth/login` con body JSON `{email, password}` sin alterar los valores; campos vacíos no hacen pedidos; con un pedido en curso el botón está deshabilitado y no hay un segundo pedido; verificar con `npm test -- PaginaLogin`
- [x] 6.2 RED→GREEN: mismo archivo — login exitoso de recepcionista y de odontólogo lleva a `/agenda`, con el rol visible y el enlace a la configuración solo para la recepcionista (la redirección por rol se distingue por el layout), y guarda el token en `sessionStorage`, con `localStorage` vacío (D7, `RUTA_INICIAL_POR_ROL`); verificar con `npm test -- PaginaLogin`
- [x] 6.3 RED→GREEN: mismo archivo — `401 credenciales_invalidas` muestra el mensaje, sigue en `/login`, sin token ni aviso de sesión vencida; sin conexión muestra `No se pudo conectar con el servidor.`; reintento exitoso limpia el error; token ilegible, de rol desconocido, sin `exp` o ya vencido en una respuesta `200` muestra `Ocurrió un error. Intentá de nuevo.`, sin token ni aviso de sesión vencida; verificar con `npm test -- PaginaLogin`
- [x] 6.4 RED→GREEN: `src/features/sesion/sesion.test.tsx`, con el reloj fijo como en 5.1 — arranque con token vigente conserva la sesión; con token vencido o con `exp` igual al reloj lo elimina y avisa con `Tu sesión venció. Iniciá sesión de nuevo.`; con token ilegible, de `rol` desconocido o sin `exp` lo elimina sin avisar; verificar con `npm test -- sesion`
- [ ] 6.5 RED→GREEN: mismo archivo, con `vi.useFakeTimers` — a los 59 segundos sigue la sesión y al minuto se cierra con aviso; el temporizador se programa tras el login y al arrancar con token vigente; el cierre manual lo cancela (sin aviso al llegar el `exp` viejo) y una sesión nueva no lo hereda; con una demora mayor a `2^31 - 1` ms no se programa y la sesión sigue; el aviso desaparece tras iniciar sesión y cerrarla; verificar con `npm test -- sesion`
- [ ] 6.6 RED→GREEN: mismo archivo — `401 no_autenticado` en un pedido hecho con el token vigente cierra la sesión con aviso; un `403` con `rol_insuficiente` (también con el rol del token desactualizado), `profesional_ajeno` o `paciente_ajeno` no la cierra ni cambia la ruta; un `401` de un pedido hecho con un token anterior no cierra la sesión actual ni avisa, y uno que llega después de un cierre manual deja `/login` sin aviso (D4); verificar con `npm test -- sesion`

## 7. Guardas, rutas y layout (D5, D6, D7, D8, D14)

- [ ] 7.1 RED→GREEN: `src/features/sesion/guardas.test.tsx` — sin sesión, `/agenda`, `/configuracion` y `/` llevan a `/login`; con sesión, `/login` y `/` llevan a `/agenda`; verificar con `npm test -- guardas`
- [ ] 7.2 RED→GREEN: mismo archivo — `/configuracion`: recepcionista ve el contenido; odontólogo ve la falta de permiso con la URL intacta y el token guardado, y su enlace lleva a `/agenda`; odontólogo ve `/agenda`; verificar con `npm test -- guardas`
- [ ] 7.3 RED→GREEN: `src/shared/layout/Layout.test.tsx` — rol `Recepcionista` con enlace a configuración, rol `Odontólogo` sin él; `/login` sin navegación; `/agenda` y `/configuracion` no hacen pedidos a la API; cerrar sesión elimina el token, lleva a `/login` sin aviso, y volver a `/agenda` muestra `/login`; verificar con `npm test -- Layout`
- [ ] 7.4 RED→GREEN: `/no-existe` muestra la página no encontrada con y sin sesión, y su enlace a `/` lleva al inicio del rol; verificar con `npm test -- guardas`, y con `grep` que `dangerouslySetInnerHTML` no aparece en `frontend/src/`

## 8. Docker y puesta en marcha (D10)

- [ ] 8.1 RED→GREEN: `backend/tests/unit/test_docker_compose.py` — servicio `frontend` con `build: ./frontend`, `5173:5173`, dependencia de `api`, `VITE_API_URL` por defecto `http://localhost:8000` y sin `JWT_SECRET`, `DATABASE_URL`, `REDIS_URL` ni `env_file`; agregar el servicio, `frontend/Dockerfile` (`node:24-slim`, `npm ci`, servidor de desarrollo en `0.0.0.0`) y `frontend/.dockerignore`; verificar con `pytest tests/unit/test_docker_compose.py` y `docker compose config`
- [ ] 8.2 Verificar que `docker compose up --build frontend` deja `http://localhost:5173/` respondiendo `200` con el HTML de la aplicación
- [ ] 8.3 RED: agregar `VITE_API_URL` a la lista de `test_env_example_declares_infrastructure_variables` en `backend/tests/unit/test_env_example.py` y verificar con `pytest tests/unit/test_env_example.py` que falla, porque `.env.example` todavía no tiene la línea. GREEN: **el agente no puede leer ni editar `.env*`, así que frena y le pide al usuario que agregue a `.env.example`** estas dos líneas: `# Pública: la usa el navegador para llamar a la API` y `VITE_API_URL=http://localhost:8000`; verificar que el mismo comando pasa
- [ ] 8.4 Agregar al `README.md` una sección de cómo correr el frontend (Node 24, `npm ci`, `npm run dev`, `npm test` y la verificación completa; `docker compose up --build`; `VITE_API_URL`; usar `http://localhost:5173` y no `127.0.0.1` por el CORS; el servicio no es apto para producción) y agregar `frontend/` a "Estructura"; verificar ejecutando los comandos documentados

## 9. Documentación del proyecto

- [ ] 9.1 Actualizar la cabecera de DD-32 en `knowledge-base/09_decisiones_y_supuestos.md`: de "pendiente de revisión de Nico" a "aprobada por Nico" (PR #14 aprobado el 2026-11-09, compromiso de la revisión con Matías); verificar con `grep` que la frase "pendiente de revisión" ya no aparece en DD-32
- [ ] 9.2 Registrar en `knowledge-base/09_decisiones_y_supuestos.md` la **DD-33** con las decisiones aprobadas en 1.2: a rol por claims (con el límite del claim desactualizado, que se manifiesta desde C-15), b CORS (con `*` inválido y lista vacía), c `sessionStorage`, d vencimiento y `401`, e falta de permiso, f `/login` con sesión (D6), g rutas e inicio por rol, h cierre de sesión, i Node, j Docker, k `fetch` falso en los tests (D11), l `422` no atado a un campo (P1) y m página no encontrada (D20). Actualizar DD-17: pasa de Node 22 a Node 24 y remite a DD-33; verificar que no queda "a confirmar en C-14" en `knowledge-base/`
- [ ] 9.3 Actualizar la KB: `02` (versión de Node y `POST /auth/refresh` no implementado, DD-33), `07` Flujo 1 (la SPA lee el rol de los claims y cierra la sesión ante `no_autenticado`), `08` (árbol con `frontend` y `features/sesion`, `VITE_API_URL` en la tabla de variables y, en la fila de `CORS_ORIGINS`, el formato de lista separada por comas, que vacía no permite ningún origen y que `*` es inválido) y `10` (preguntas resueltas de C-14); verificar que los enlaces a DD-33 existen
- [ ] 9.4 Actualizar `CLAUDE.md` y `AGENTS.md` por igual: fila "Tests" con Vitest + React Testing Library y versiones mínimas con Node 24 (DD-33); verificar con `cmp CLAUDE.md AGENTS.md` que son byte-idénticos

## 10. Verificación final

- [ ] 10.1 Correr en `frontend/` `npm run typecheck`, `npm run lint`, `npm run format:check`, `npm test` y `npm run build`, y en `backend/` `pytest` completo más `ruff check` y `ruff format --check`; todo en verde, sin cambios en `backend/alembic/versions/` (verificar con `git diff --stat main -- backend/alembic/versions/`) y sin `JWT_SECRET`, `DATABASE_URL` ni `REDIS_URL` en `frontend/src/` ni en `frontend/dist/` (verificar con `grep -r`)
- [ ] 10.2 Verificación manual del stack con `docker compose up --build`: el preflight con `curl -i -X OPTIONS http://localhost:8000/turnos -H "Origin: http://localhost:5173" -H "Access-Control-Request-Method: GET" -H "Access-Control-Request-Headers: authorization"` devuelve `200` con `Access-Control-Allow-Origin`; el login en el navegador con un usuario del seed llega a `/agenda` (las contraseñas ficticias están en `.env`, que el agente no lee: este paso lo hace el usuario)

## Workflow follow-up

- Abrir el PR con revisión de Matías; correr `revisar-migraciones` no aplica porque no hay migración.
- En la descripción del PR, dejar la nota para Matías, responsable de C-16: `/configuracion` sigue siendo solo de la recepcionista; si C-16 necesita vistas de lectura para el odontólogo, van en otra ruta (design D7, P3).
- `/opsx:archive frontend-base-login` en la rama del change, antes del merge, y marcar `[x]` en `CHANGES.md`.
