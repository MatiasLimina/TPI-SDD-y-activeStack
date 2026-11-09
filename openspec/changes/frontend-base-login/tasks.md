# Tasks

> Governance BAJO según `CHANGES.md`, pero el change maneja el token de sesión: las filas **[A confirmar]** de `design.md` (D1-D11) las aprueba el usuario **antes** del Apply. Estas tareas asumen la opción recomendada; si alguna cambia, primero `/opsx:update` (spec, design y tareas) y recién después el Apply.
>
> TDD estricto: en cada tarea RED (test que falla, verificado ejecutándolo) → GREEN (mínimo código) → triangular → refactor con tests en verde. Solo datos ficticios en tests, fixtures y ejemplos (`recepcion@example.com`, UUIDs inventados, firma `firma-ficticia`). Skills a cargar: `tdd` y `vitest` en el frontend (la skill documenta 5.1.0-beta.1 y el proyecto fija la 5.1.0, ver D12); `fastapi-python` y `python-testing-patterns` en el grupo 2. React Router y React Testing Library se consultan en Context7.
>
> **Sin migración**: ninguna tarea toca `backend/alembic/versions/` y la cabeza sigue en `010`.

## 1. Preparación

- [ ] 1.1 Safety net: correr `pytest` completo en `backend/` y `ruff check` más `ruff format --check`, y registrar el baseline en verde; si algo falla, frenar y reportarlo como falla preexistente
- [ ] 1.2 Aprobación previa al Apply: el usuario aprueba o cambia D1-D11 de `design.md`; registrar la fecha y la opción aprobada de cada una; verificar que la tabla de Decisions no tiene ninguna fila **[A confirmar]**
- [ ] 1.3 Correr `revisar-escenarios frontend-base-login` y resolver con `/opsx:update` todo hallazgo BLOQUEANTE o MAYOR; verificar que `openspec/changes/frontend-base-login/revision-escenarios.md` no deja ninguno abierto y que `openspec validate frontend-base-login --strict` pasa

## 2. CORS en la API (D2; cambio de backend, a omitir solo si D2 se aprueba con la alternativa)

- [ ] 2.1 RED→GREEN: `tests/unit/test_config.py` — `ConfiguracionCors` separa `CORS_ORIGINS` por comas, recorta espacios y descarta vacíos (`"http://localhost:5173, http://consultorio.example.com"` da dos orígenes; `""` da ninguno; sin variable da `["http://localhost:5173"]`), y carga sin `JWT_SECRET` ni `DATABASE_URL`; `Settings` sigue teniendo el campo; verificar con `pytest tests/unit/test_config.py`
- [ ] 2.2 RED→GREEN: `tests/integration/test_cors.py`, con `create_app()` real y `CORS_ORIGINS` por `monkeypatch` — preflight de `OPTIONS /turnos` desde origen permitido con `Authorization`, preflight desde otro origen sin `Access-Control-Allow-Origin`, varios orígenes con espacios y valor por defecto (requirement "Orígenes CORS restringidos"); instalar `CORSMiddleware` en `create_app` con los métodos y encabezados de D2, leyendo solo `ConfiguracionCors` y no `get_settings()`; verificar con `pytest tests/integration/test_cors.py`
- [ ] 2.3 RED→GREEN: en el mismo archivo — `GET /turnos` sin token con origen permitido da `401 no_autenticado` con `Access-Control-Allow-Origin`, con otro origen da `401` sin ese encabezado, y `GET /health` sin `Origin` no lo incluye; verificar con el mismo archivo, `pytest` completo y `ruff check` más `ruff format --check`

## 3. Scaffolding del frontend (D9, D12, D16)

- [ ] 3.1 Crear `frontend/package.json` con `engines.node` `^24.15.0` y las dependencias exactas de la tabla de D12 (sin `react-router-dom`), más las carpetas `src/features/`, `src/shared/` y `src/pages/`; generar y versionar `package-lock.json`; verificar con `npm ci` y con `npm ls vitest typescript react-router`, que muestran las versiones fijadas
- [ ] 3.2 **Consultar Context7 antes de escribir `vite.config.ts`** (`/vitejs/vite/v8.3.5`: configuración, `@vitejs/plugin-react` y cambios del bundler) y `/vitest-dev/vitest` (entorno jsdom y `setupFiles`); escribir `vite.config.ts` (D12: `port` 5173, `strictPort`, sección `test`), `index.html`, `tsconfig` en modo `strict` con `types` explícitos, y `src/test/setup.ts` con `@testing-library/jest-dom/vitest`; verificar con `npm run typecheck` y dejar registrado en el reporte qué se consultó
- [ ] 3.3 RED→GREEN: primer test en `src/App.test.tsx`: `App` dentro de `MemoryRouter` renderiza sin errores en jsdom, afirmando un texto visible (se confirma el RED antes de crear `App.tsx`), y `main.tsx` monta `BrowserRouter`; verificar con `npm test` y `npm run build`, que genera `dist/`
- [ ] 3.4 Configurar ESLint flat con `@eslint/js`, `typescript-eslint` y `react-hooks`, Prettier con `.prettierignore`, y los scripts de D16; verificar que `npm run lint` y `npm run format:check` pasan, y que un error de tipos y un archivo mal formateado de prueba hacen fallar `typecheck` y `format:check` (requirement "Verificación antes de dar una tarea por terminada"), descartando esos archivos después
- [ ] 3.5 Agregar `dist/` y `coverage/` a `.gitignore`; verificar con `git status` que `frontend/node_modules/` y `frontend/dist/` no aparecen

## 4. Cliente HTTP (D15)

- [ ] 4.1 RED→GREEN: `src/shared/api/cliente.test.ts` — URL con `VITE_API_URL`, sin configurar y con barra final; `Authorization: Bearer` con sesión y sin encabezado sin sesión; el token nunca en la URL (requirements "URL base de la API" y "Token en cada request"); verificar con `npm test -- cliente`
- [ ] 4.2 RED→GREEN: mismo archivo — `200` entrega el JSON y `204` resuelve sin valor; ante un `500` la consola no recibe el token; verificar con `npm test -- cliente`
- [ ] 4.3 RED→GREEN: mismo archivo — `ErrorApi` para `{"detail": {"codigo", "mensaje"}}` (`rol_insuficiente`) y sin `mensaje` conservando extras (`solapamiento` con `recursos`); verificar con `npm test -- cliente`
- [ ] 4.4 RED→GREEN: mismo archivo — lista de `422`: campo del body y parámetro de consulta; `detail` de texto, cuerpo no JSON y falla de red con `status` `0`; verificar con `npm test -- cliente`, `npm run lint` y `npm run typecheck`

## 5. Datos de la sesión (D1)

- [ ] 5.1 RED→GREEN: `src/features/sesion/claims.test.ts` — con el helper de tokens ficticios de `src/test/`: claims de recepcionista (`profesional_id` nulo) y de odontólogo; un valor que no es JWT, sin `exp` numérico, ya vencido o con `rol` desconocido se rechazan; base64url con `-` y `_` se decodifica; verificar con `npm test -- claims`

## 6. Login y sesión (D3, D4, D6, D8, D17)

- [ ] 6.1 RED→GREEN: `src/pages/PaginaLogin.test.tsx` (costura `App` en `MemoryRouter`, `fetch` falso) — el envío hace un único `POST /auth/login` con body JSON `{email, password}` sin alterar los valores; campos vacíos no hacen pedidos; con un pedido en curso el botón está deshabilitado y no hay un segundo pedido; verificar con `npm test -- PaginaLogin`
- [ ] 6.2 RED→GREEN: mismo archivo — login exitoso de recepcionista y de odontólogo lleva a `/agenda` y guarda el token en `sessionStorage`, con `localStorage` vacío (D7, `RUTA_INICIAL_POR_ROL`); verificar con `npm test -- PaginaLogin`
- [ ] 6.3 RED→GREEN: mismo archivo — `401 credenciales_invalidas` muestra el mensaje, sigue en `/login`, sin token ni aviso de sesión vencida; sin conexión muestra su mensaje; reintento exitoso limpia el error; token ilegible, de rol desconocido o sin `exp` en una respuesta `200` da error genérico; verificar con `npm test -- PaginaLogin`
- [ ] 6.4 RED→GREEN: `src/features/sesion/sesion.test.tsx` — arranque con token vigente conserva la sesión; con token vencido lo elimina y avisa; con token ilegible lo elimina sin avisar; verificar con `npm test -- sesion`
- [ ] 6.5 RED→GREEN: mismo archivo, con `vi.useFakeTimers` — a los 59 segundos sigue la sesión y al minuto se cierra con aviso; el aviso desaparece tras iniciar sesión y cerrarla; verificar con `npm test -- sesion`
- [ ] 6.6 RED→GREEN: mismo archivo — `401 no_autenticado` en un pedido cierra la sesión con aviso; un `403 rol_insuficiente` no la cierra ni cambia la ruta; un `401` de un pedido hecho con un token anterior no cierra la sesión actual (D4); verificar con `npm test -- sesion`

## 7. Guardas, rutas y layout (D5, D6, D7, D8, D14)

- [ ] 7.1 RED→GREEN: `src/features/sesion/guardas.test.tsx` — sin sesión, `/agenda`, `/configuracion` y `/` llevan a `/login`; con sesión, `/login` y `/` llevan a `/agenda`; verificar con `npm test -- guardas`
- [ ] 7.2 RED→GREEN: mismo archivo — `/configuracion`: recepcionista ve el contenido; odontólogo ve la falta de permiso con la URL intacta y el token guardado, y su enlace lleva a `/agenda`; odontólogo ve `/agenda`; verificar con `npm test -- guardas`
- [ ] 7.3 RED→GREEN: `src/shared/layout/Layout.test.tsx` — rol `Recepcionista` con enlace a configuración, rol `Odontólogo` sin él; `/login` sin navegación; `/agenda` y `/configuracion` no hacen pedidos a la API; cerrar sesión elimina el token, lleva a `/login` sin aviso, y volver a `/agenda` muestra `/login`; verificar con `npm test -- Layout`
- [ ] 7.4 RED→GREEN: `/no-existe` muestra la página no encontrada con y sin sesión, y su enlace a `/` lleva al inicio del rol; verificar con `npm test -- guardas`, y con `grep` que `dangerouslySetInnerHTML` no aparece en `frontend/src/`

## 8. Docker y puesta en marcha (D10)

- [ ] 8.1 RED→GREEN: `backend/tests/unit/test_docker_compose.py` — servicio `frontend` con `build: ./frontend`, `5173:5173`, dependencia de `api`, `VITE_API_URL` por defecto `http://localhost:8000` y sin `JWT_SECRET`, `DATABASE_URL` ni `REDIS_URL`; agregar el servicio, `frontend/Dockerfile` (`node:24-slim`, `npm ci`, servidor de desarrollo en `0.0.0.0`) y `frontend/.dockerignore`; verificar con `pytest tests/unit/test_docker_compose.py` y `docker compose config`
- [ ] 8.2 Verificar que `docker compose up --build frontend` deja `http://localhost:5173/` respondiendo `200` con el HTML de la aplicación
- [ ] 8.3 Agregar a `.env.example` la línea `VITE_API_URL=http://localhost:8000`, con un comentario que aclare que es pública y la usa el navegador; **el agente no puede leer ni editar `.env*`, así que esta tarea la hace el usuario o se le indica la línea exacta**; verificar con `pytest tests/unit/test_env_example.py`
- [ ] 8.4 Agregar al `README.md` una sección de cómo correr el frontend (Node 24, `npm ci`, `npm run dev`, `npm test` y la verificación completa; `docker compose up --build`; `VITE_API_URL`; usar `http://localhost:5173` y no `127.0.0.1` por el CORS; el servicio no es apto para producción) y agregar `frontend/` a "Estructura"; verificar ejecutando los comandos documentados

## 9. Documentación del proyecto

- [ ] 9.1 Actualizar la cabecera de DD-32 en `knowledge-base/09_decisiones_y_supuestos.md`: de "pendiente de revisión de Nico" a "aprobada por Nico" (PR #14 aprobado el 2026-11-09, compromiso de la revisión con Matías); verificar con `grep` que la frase "pendiente de revisión" ya no aparece en DD-32
- [ ] 9.2 Registrar en `knowledge-base/09_decisiones_y_supuestos.md` la **DD-33** con las decisiones aprobadas en 1.2 (rol por claims, CORS, `sessionStorage`, vencimiento y `401`, falta de permiso, rutas e inicio por rol, cierre de sesión, Node, Docker) y actualizar DD-17 para que remita a DD-33; verificar que no queda "a confirmar en C-14" en `knowledge-base/`
- [ ] 9.3 Actualizar la KB: `02` (versión de Node y `POST /auth/refresh` no implementado, DD-33), `07` Flujo 1 (la SPA lee el rol de los claims y cierra la sesión ante `no_autenticado`), `08` (árbol con `frontend` y `features/sesion`, y `VITE_API_URL` en la tabla de variables) y `10` (preguntas resueltas de C-14); verificar que los enlaces a DD-33 existen
- [ ] 9.4 Actualizar `CLAUDE.md` y `AGENTS.md` por igual: fila "Tests" con Vitest + React Testing Library, versiones mínimas con Node 24 (DD-33) y fila "Frontend" de la tabla de skills, hoy desactualizada, con `vitest` y `tdd`; verificar con `cmp CLAUDE.md AGENTS.md` que son byte-idénticos

## 10. Verificación final

- [ ] 10.1 Correr en `frontend/` `npm run typecheck`, `npm run lint`, `npm run format:check`, `npm test` y `npm run build`, y en `backend/` `pytest` completo más `ruff check` y `ruff format --check`; todo en verde y sin cambios en `backend/alembic/versions/` (verificar con `git diff --stat main -- backend/alembic/versions/`)
- [ ] 10.2 Verificación manual del stack con `docker compose up --build`: el preflight con `curl -i -X OPTIONS http://localhost:8000/turnos -H "Origin: http://localhost:5173" -H "Access-Control-Request-Method: GET" -H "Access-Control-Request-Headers: authorization"` devuelve `200` con `Access-Control-Allow-Origin`; el login en el navegador con un usuario del seed llega a `/agenda` (las contraseñas ficticias están en `.env`, que el agente no lee: este paso lo hace el usuario)

## Workflow follow-up

- Abrir el PR con revisión de Matías; correr `revisar-migraciones` no aplica porque no hay migración.
- `/opsx:archive frontend-base-login` en la rama del change, antes del merge, y marcar `[x]` en `CHANGES.md`.
