# Design

## Context

Ver `proposal.md` y los delta specs `frontend-base`, `frontend-cliente-http`, `frontend-sesion` y `app-configuration`. Estado verificado en el código (`feat/c-14-frontend-base-login`, con C-13 mergeado):

- **`frontend/` no existe.** `docker-compose.yml` tiene `db`, `redis`, `api` y `worker`.
- **Login** (`backend/app/api/auth.py`, spec `autenticacion`): `POST /auth/login`, body JSON `{email, password}`. `200` devuelve **exactamente** `{"access_token", "token_type": "bearer"}`: ni rol ni profesional. `401 credenciales_invalidas` con cuerpo constante; `422` si falta un campo.
- **No hay endpoint de usuario actual** (`/auth/me`) **ni `POST /auth/refresh`**, aunque `02_descripcion_general.md` lo lista como **Suposición**.
- **Claims del JWT** (`infrastructure/security/tokens.py`): `sub` (UUID como texto), `rol`, `profesional_id` (nulo para la recepcionista), `exp` (segundos desde epoch). HS256 con `JWT_EXPIRE_MINUTES`, por defecto `60`. El backend relee rol y profesional de la base en cada request: los del token no autorizan nada.
- **CORS sin efecto**: `CORS_ORIGINS` está en `config.py:53` y `docker-compose.yml:35`, y `test_config.py` y `test_docker_compose.py` la mencionan, pero **`main.py` no instala `CORSMiddleware`**. Ninguna otra parte del código la lee. Es texto de configuración sin comportamiento.
- **Formas de error reales** (`backend/app/api/*.py`), más variadas que `{codigo, mensaje}`:
  - `{"detail": {"codigo", "mensaje"}}` (la mayoría).
  - `{"detail": {"codigo", ...extras}}` sin `mensaje`: `solapamiento` (`recursos`), `franja_superpuesta`, `recurso_duplicado` (`campo`), `recurso_inexistente` (`recurso`). Otros suman extras con mensaje, como `bloqueo_con_turnos` (`turnos`).
  - `{"detail": [{"type", "loc", "msg", ...}]}`: la lista de `422` (en `/pacientes` sin `input` ni `ctx`, DD-31 n).
  - `{"detail": "Not Found"}`: texto, en `404` y `405` del framework.
- **Rol en las respuestas**: `401 no_autenticado` y `403 rol_insuficiente` (DD-24). Las rutas de datos usan `/turnos`, `/pacientes`, etc., sin prefijo `/api`.
- **Entorno**: Node local `24.19.0`. `.gitignore` ya ignora `node_modules/` y `.env.*`, pero no `dist/`. Los archivos `.env*` no se pueden leer desde el agente.
- **Skill `vitest`** (`.agents/skills/vitest/`): documenta Vitest 5.1.0-beta.1. No hay skill de Vite, React ni React Router: la documentación sale de Context7.

## Goals / Non-Goals

**Goals:**
- C-15 y C-16 agregan pantallas sin tocar la sesión, el cliente HTTP ni las guardas: solo suman `<Route>` y carpetas en `features/`.
- Una sola interpretación de los errores de la API, probada contra las formas reales.
- El frontend no contiene ninguna decisión de seguridad que el backend no vuelva a verificar.

**Non-Goals:**
- Lo que lista `proposal.md`. Además, a nivel de diseño: sin capa de caché de datos, sin internacionalización y sin diseño visual más allá de un CSS mínimo propio.

## Decisions

La KB fija el stack (React + TypeScript + Vite), la estructura de carpetas (08), que el token va en cada request (Flujo 1), los códigos de error (DD-24), los dos roles y que la autorización real es del backend (03). **Lo demás no lo fija la KB.** D1 a D11 **fueron aprobadas por el usuario el 2026-11-09** con la opción de esta tabla, y se registran como **DD-33** (tarea 9.2); el literal de cada una figura en la columna Estado. Si alguna cambia, primero `/opsx:update` (spec, design y tareas).

| # | Decisión | Estado | Opción aprobada o adoptada |
|---|----------|--------|--------------------|
| D1 | Cómo conoce el rol la SPA | Aprobada 2026-11-09, DD-33 a | Leer los claims del JWT, sin verificar la firma, solo para la UI |
| D2 | CORS y URL de la API | Aprobada 2026-11-09, DD-33 b, **cambio de backend** | Instalar `CORSMiddleware` con `CORS_ORIGINS`; la SPA llama a `VITE_API_URL` |
| D3 | Dónde se guarda el token | Aprobada 2026-11-09, DD-33 c | `sessionStorage` |
| D4 | Vencimiento y `401` en plena sesión | Aprobada 2026-11-09, DD-33 d | Temporizador al `exp` más `401 no_autenticado`; sin volver a la ruta pedida |
| D5 | Falta de permiso | Aprobada 2026-11-09, DD-33 e | Pantalla en el lugar, sin cambiar la URL; un `403` de la API no cierra sesión |
| D6 | Usuario con sesión en `/login` | Aprobada 2026-11-09, DD-33 f | Redirigir a su inicio |
| D7 | Rutas e inicio por rol | Aprobada 2026-11-09, DD-33 g | `/agenda` para ambos; `/configuracion` solo recepcionista |
| D8 | Cierre de sesión manual | Aprobada 2026-11-09, DD-33 h | Botón en el layout; cierre solo local |
| D9 | Versión de Node | Aprobada 2026-11-09, DD-33 i | Node 24 LTS (`node:24-slim`, `engines: ^24.15.0`) |
| D10 | Servicio de Docker | Aprobada 2026-11-09, DD-33 j | Servidor de desarrollo de Vite, sin montar el código |
| D11 | Red en los tests | Aprobada 2026-11-09, DD-33 k | `fetch` reemplazado con `vi.stubGlobal`, sin MSW |
| D12 | Versiones de las herramientas | Decisión técnica | Tabla "Versiones"; TypeScript 6.0.3, no 7 |
| D13 | Librerías que no se agregan | Decisión técnica | Sin gestor de estado, kit de UI, axios ni librería de JWT |
| D14 | Organización de rutas | Decisión técnica | Modo declarativo con rutas de layout anidadas |
| D15 | Cliente HTTP | Decisión técnica | Fábrica sobre `fetch`; un único tipo de error |
| D16 | Lint y formato | Decisión técnica | ESLint + typescript-eslint + react-hooks, Prettier |
| D17 | Costuras de test | Decisión técnica | Función pura, cliente con `fetch` falso y `App` en `MemoryRouter` |
| D18 | Alcance de los tests | Decisión técnica | Sin tests contra el backend real ni CI |
| D19 | Zona horaria | KB, RN-CU-04 | C-14 no presenta fechas; es de C-15 |
| D20 | Ruta inexistente | Decisión técnica, DD-33 m | Pantalla de página no encontrada con enlace a `/`, con o sin sesión |

### D1 — Cómo conoce el rol la SPA

La API no lo informa por ningún otro medio. Opciones:

| Opción | A favor | En contra |
|--------|---------|-----------|
| **Leer los claims del JWT (aprobada)** | Sin cambios de backend. El Flujo 1 ya dice que el token lleva `rol` y `profesional_id` | El rol puede quedar viejo hasta el `exp`. La SPA depende de los nombres de los claims |
| `GET /auth/me` | Dato releído de la base; el contrato queda explícito | **Cambio de backend y ampliación del alcance**: endpoint, spec y tests. Un pedido más al arrancar y un estado de carga en las guardas |
| Agregar `rol` a la respuesta del login | Pequeño | **Cambio de backend** y contradice el spec `autenticacion` ("exactamente" dos claves). No resuelve la recarga |

Se decodifica el segundo segmento en base64url y se interpreta como JSON UTF-8, sin dependencia nueva. **No se verifica la firma**: el navegador no tiene ni debe tener `JWT_SECRET`, así que un usuario que altere su token solo cambia lo que ve su pantalla, y la API responde `401` o `403`. El riesgo de rol viejo es teórico en el MVP: no existe cambio de rol (DD-16), y un usuario desactivado recibe `401`. Si el rol de la base llegara a diferir, la guarda y el layout muestran el rol viejo hasta el `exp`, y la API responde `403` sin cerrar la sesión (escenario "Rol del token desactualizado"). Como los placeholders no llaman a la API, en C-14 ningún pedido autenticado puede detectarlo: se manifiesta recién desde C-15.

### D2 — CORS y URL de la API [cambio de backend]

**Este es el único cambio de backend del change.** No toca la base ni agrega endpoints, y la cabeza de Alembic sigue en `010`.

| Opción | A favor | En contra |
|--------|---------|-----------|
| **`CORSMiddleware` + `VITE_API_URL` (aprobada)** | `CHANGES.md` ya pone `CORS_ORIGINS` en C-14 y `08` pide "CORS restringido". El valor por defecto ya es `:5173`. Funciona igual dentro y fuera de Docker. No exige un proxy en un despliegue futuro | Toca `main.py` y `config.py` |
| Proxy de Vite (`/api` → API) | Sin tocar el backend y sin preflight | `CORS_ORIGINS` sigue sin efecto. El destino cambia entre host y Compose. Sin prefijo real, hay que reescribir la ruta. Producción necesitaría otro proxy, que hoy no existe |

Forma del cambio (API verificada en Context7, `/websites/fastapi_tiangolo`):

- `add_middleware(CORSMiddleware, allow_origins=..., allow_methods=["GET", "POST", "PATCH", "DELETE"], allow_headers=["Authorization", "Content-Type"])`. Son los cuatro verbos que usa la API. `allow_credentials` queda en `False`: el token viaja en un encabezado, no en una cookie.
- `CORS_ORIGINS` sigue siendo un `str` y se separa por comas, recortando espacios y descartando vacíos. Una lista vacía significa que ningún origen está permitido (P2).
- **`*` es configuración inválida** (P2, aprobada el 2026-11-09; `08` pide CORS restringido), solo o dentro de una lista. Sigue el patrón de `APP_TIMEZONE`: un `field_validator` en `ConfiguracionCors` lanza `ValueError` y la carga falla con un `ValidationError` que nombra `CORS_ORIGINS`.
- **Gotcha**: `main.py` ejecuta `create_app()` al importarse. Si llamara a `get_settings()`, importar la app exigiría `JWT_SECRET` y `DATABASE_URL`, cuando hoy la app se puede importar sin ellas. Se lee solo esa variable con una clase chica, `ConfiguracionCors(BaseSettings)`, de la que `Settings` hereda el campo y su validación, de modo que los tests actuales de `test_config.py` no cambian.
- **Dónde se dispara el rechazo de `*`**: por el mismo motivo, una excepción dentro de `create_app()` rompería `import app.main`, y con él la recolección de `pytest`, porque `conftest.py` importa ese módulo. Por eso `create_app()` captura el `ValidationError` e instala el middleware sin orígenes, y el `lifespan` vuelve a instanciar `ConfiguracionCors()` antes del `yield`, sin capturarlo: `uvicorn` corta con "Application startup failed" y no sirve ningún pedido (comprobado en una app descartable: código de salida `3`). Así se puede importar la app con cualquier valor, el arranque falla como pide "Fallo explícito" y `*` nunca llega al middleware, aunque el `lifespan` no corra.
- **Tests sin depender del `.env`**: `create_app()` no recibe `_env_file`, pero una variable definida con `monkeypatch.setenv` gana sobre el `.env`. El valor por defecto, que necesita la variable ausente, se prueba sobre `ConfiguracionCors(_env_file=None)`, como `test_config.py`.
- **Gotcha**: `VITE_API_URL` la usa el **navegador**, por lo que dentro de Compose debe ser `http://localhost:8000`, no `http://api:8000`.
- El origen debe coincidir exacto: abrir la SPA en `http://127.0.0.1:5173` falla por CORS con el valor por defecto. Se documenta en el README.

### D3 — Dónde se guarda el token

| Opción | XSS | Recarga (F5) | Otros |
|--------|-----|--------------|-------|
| **`sessionStorage` (aprobada)** | Un script inyectado lo puede leer | Conserva la sesión | Se borra al cerrar la pestaña. Cada pestaña nueva pide login |
| `localStorage` | Igual de legible, y sobrevive más tiempo | Conserva la sesión | Sobrevive al cierre del navegador, mala opción en una PC compartida de recepción con datos de salud (Ley 25.326) |
| Memoria (variable) | El más resistente: no queda en ningún almacenamiento | **Pierde la sesión** | Sin `/auth/refresh`, cada F5 obliga a iniciar sesión, inaceptable en un uso de todo el día |
| Cookie `httpOnly` | No legible desde JavaScript | Conserva la sesión | **Cambio de backend grande** (emisión, CSRF, credenciales en CORS). Mejor opción a futuro: queda fuera |

Ninguna opción legible desde JavaScript protege contra XSS. Mitigaciones del change: React escapa por defecto, se prohíbe `dangerouslySetInnerHTML`, el token nunca va en la URL ni en la consola, y se guarda solo el token (los claims se derivan). El impacto queda acotado por la vida corta del token (60 minutos).

### D4 — Vencimiento y `401`

- **Estados del token**: primero se evalúa la forma. Un valor ilegible, sin `exp` numérico o con `rol` desconocido es inválido, aunque su `exp` haya pasado; uno bien formado con `exp` (en segundos) menor o igual al reloj está vencido. La función de claims distingue vigente, vencido e inválido, porque el arranque los trata distinto.
- **Al arrancar**: si el token guardado está vencido, se descarta y `/login` avisa "Tu sesión venció. Iniciá sesión de nuevo." Si es inválido, se descarta sin aviso.
- **En el login**: vencido e inválido se rechazan igual, con el mensaje genérico, sin sesión y sin aviso.
- **En plena sesión**: un `setTimeout` hasta `exp` cierra la sesión con aviso. Se programa al crear la sesión (tras el login y al arrancar con un token vigente) y se cancela al cerrarla, para que un `exp` viejo no avise en `/login` ni cierre una sesión nueva. Las guardas quedan puras (hay sesión o no) y, cuando C-15 muestre datos de pacientes, no quedan en una pantalla desatendida después del vencimiento. Si la demora supera `2^31 - 1` ms (unos 24,8 días, alcanzable porque `JWT_EXPIRE_MINUTES` solo exige ser mayor que cero) no se programa, porque `setTimeout` se dispararía de inmediato; ahí alcanza el `401`. El requirement "Temporizador de vencimiento" deja explícita esa excepción.
- **`401 no_autenticado`**: el backend es la autoridad (usuario desactivado, reloj desfasado). Cierra la sesión con aviso solo si el token del pedido sigue siendo el de la sesión actual, para que un pedido en vuelo no cierre una sesión nueva ni avise después de un cierre manual. El cliente captura el token al enviar el pedido y se lo pasa a `alNoAutenticado`, que lo compara con el de la sesión.
- **`401 credenciales_invalidas`** del login no pasa por ese camino: la discriminación es por `codigo`.
- **Sin volver a la ruta pedida**: tras el login siempre se va al inicio del rol. Es menos código y evita validar una ruta contra el rol. C-15 lo puede sumar.
- **Alternativas**: solo reaccionar al `401` (un usuario sin actividad queda viendo la pantalla); renovación silenciosa (no hay endpoint).

### D5 — Falta de permiso

Una guarda por rol renderiza `PaginaSinPermiso` en el lugar, sin cambiar la URL ni cerrar sesión. Alternativa: redirigir a `/sin-permiso`, que pierde la URL pedida y agrega una ruta más. Un `403` de la API (`rol_insuficiente`, `profesional_ajeno`, `paciente_ajeno`) no cierra la sesión: se entrega como error normalizado y cada pantalla de C-15 y C-16 decide cómo mostrarlo.

### D6 — Usuario con sesión en `/login`

Redirige a su inicio, reemplazando la entrada del historial. Alternativa: mostrar el formulario, lo que permitiría pisar la sesión sin querer.

### D7 — Rutas e inicio por rol

La KB no define una pantalla de inicio. US-008 solo dice que ambos roles quieren ver su agenda, y DD-32 sirve a ambos con el mismo `GET /turnos`. Que **los dos entren a `/agenda`**, una sola pantalla que C-15 adapta según el rol, es una decisión nueva (DD-33 g).

| Opción | A favor | En contra |
|--------|---------|-----------|
| **`/agenda` para ambos (aprobada)** | Una ruta para un solo contrato de API | Hoy la "redirección por rol" no diferencia destinos; lo que varía por rol es el layout y la guarda |
| `/agenda` y `/mi-agenda` | El destino difiere por rol | Dos rutas para la misma pantalla y el mismo endpoint |

El destino por rol vive en un mapa (`RUTA_INICIAL_POR_ROL`), que permite diferenciar sin tocar el login: es una decisión de implementación, no un requirement. Como hoy el destino es el mismo, los escenarios de "redirección por rol" distinguen los roles por el layout (rol visible y enlace a la configuración), y no por el destino. `/configuracion` (RN-AU-03) es un placeholder restringido a la recepcionista, y es la ruta que prueba la guarda por rol. Los bloqueos (C-16) son de ambos roles, así que irán fuera de ese grupo.

**Nota de coordinación para Matías, responsable de C-16 (P3, respondida el 2026-11-09)**: C-14 no cambia, y `/configuracion` sigue siendo solo de la recepcionista. La matriz de `03` da lectura al odontólogo sobre el catálogo y sobre sus horarios: si C-16 necesita esas vistas, van en otra ruta.

### D8 — Cierre de sesión

La KB no lo menciona. Un botón en el layout: en una PC compartida, cerrar la pestaña no es obvio. Es local, y el token sigue siendo válido en el servidor hasta su `exp`, porque la API no revoca.

### D9 — Versión de Node

Se resuelve el "a confirmar en C-14" de DD-17, que pasa de Node 22 a Node 24 (tarea 9.2). Calendario oficial (`nodejs/Release`, `schedule.json`):

| Node | Estado al 2026-11-09 | Fin de soporte | Evaluación |
|------|----------------------|----------------|------------|
| 22 | Mantenimiento | 2027-04-30 | Cumple DD-17 tal como está escrita, pero le quedan menos de 6 meses y exige `>=22.22.2` por jsdom |
| **24 (aprobada)** | Mantenimiento (LTS) | 2028-04-30 | Es la instalada localmente (24.19.0); soportada por todas las herramientas |
| 26 | LTS activa desde 2026-10-28 | 2029-04-30 | Más soporte, pero obligaría a instalar otra versión y a diferir entre la máquina y la imagen, sin beneficio para el MVP |

`engines`: `"node": "^24.15.0"` (piso que pone jsdom 31; Vitest 5 excluye las impares 23 y 25). Imagen: `node:24-slim`, mismo criterio que `python:3.13-slim` del backend.

### D10 — Servicio de Docker

| Opción | A favor | En contra |
|--------|---------|-----------|
| **Servidor de desarrollo de Vite (aprobada)** | Un `Dockerfile` chico; `VITE_API_URL` se lee al arrancar; sirve la SPA con fallback de rutas | No es apto para producción |
| Build + nginx | Cercana a producción | Archivo de nginx con fallback, multi-stage, y `VITE_*` queda fija en el build. El MVP no tiene despliegue definido |
| `vite preview` | Sin nginx | Tampoco es para producción y compila sin aportar nada aquí |

Sin montar el código, igual que `api`: los cambios se ven con `--build`, y el desarrollo diario corre en el host con `npm run dev`. `depends_on: api` (`service_started`, porque `api` no tiene healthcheck) es solo de orden: quien habla con la API es el navegador. Un `frontend/.dockerignore` excluye `node_modules/` y `dist/`, porque los binarios instalados en Windows no sirven en la imagen Linux.

### D11 — Red en los tests

| Opción | A favor | En contra |
|--------|---------|-----------|
| **`vi.stubGlobal("fetch", ...)` con `Response` reales (aprobada)** | Sin dependencia nueva; es el borde del sistema y C-14 solo llama a un endpoint | Cada test arma la respuesta a mano |
| MSW 3 | Muy cómodo con muchos endpoints | Dependencia más; sobra hoy. Se reevalúa en C-15 |

### D12 — Versiones de las herramientas

Se fijan **exactas** (`npm install -E`) y `package-lock.json` se versiona. Solo versiones estables: `npm view` el 2026-11-09 para número, `engines` y `peerDependencies`; la documentación, en Context7.

| Paquete | Versión | Tipo | Notas |
|---------|---------|------|-------|
| `react`, `react-dom` | 19.3.1 | prod | Context7 `/react/react` indexa 19.3.1 |
| `react-router` | 8.5.1 | prod | Node `>=22.22.0`. v8 elimina `react-router-dom`: **no instalarlo** |
| `vite` | 8.3.7 | dev | Rolldown y Oxc reemplazan a esbuild y Rollup |
| `@vitejs/plugin-react` | 6.3.0 | dev | Exige Vite `^8` |
| `typescript` | **6.0.3** | dev | **No 7.0.2**: `typescript-eslint` 8.72.2 exige `<6.1.0` |
| `vitest` | 5.1.0 | dev | Estable, publicada el 2026-11-02 |
| `jsdom` | 31.0.0 | dev | Node `^22.22.2 \|\| ^24.15.0 \|\| >=26` |
| `@testing-library/react` | 16.3.3 | dev | Exige `@testing-library/dom` |
| `@testing-library/dom` | 10.4.2 | dev | |
| `@testing-library/jest-dom` | 7.0.1 | dev | Se importa `@testing-library/jest-dom/vitest` |
| `@testing-library/user-event` | 14.6.8 | dev | |
| `eslint` | 10.14.0 | dev | |
| `@eslint/js` | 10.0.1 | dev | |
| `typescript-eslint` | 8.72.2 | dev | |
| `eslint-plugin-react-hooks` | 7.1.1 | dev | |
| `prettier` | 3.9.10 | dev | |
| `@types/react`, `@types/react-dom` | 19.3.0 | dev | |

**Vitest estable y la skill**: la skill documenta 5.1.0-beta.1, y se fija la 5.1.0. Las notas de la 5.1.0 no separan lo que cambió desde la beta. De lo que listan, afectan a C-14 solo los temporizadores falsos, que ahora también cubren `node:timers`; el cambio del puerto por defecto de Browser Mode no aplica porque se usa jsdom. `--since-last-run` sigue experimental: no se depende de él y la verificación usa siempre `vitest run` completo. Ante una duda, vale la documentación de la 5.1.0 por sobre la skill.

**Vite 8**: la migración indica que `build.rollupOptions` y las opciones de `esbuild` pasan a `build.rolldownOptions` y `oxc`, con una capa de compatibilidad. C-14 no debería necesitar ninguna. Como no hay skill de Vite, **las tareas exigen consultar Context7 antes de escribir `vite.config.ts`**.

**Configuración de Vitest**: va en `vite.config.ts` con `defineConfig` de `vitest/config`, con `environment: "jsdom"`, `setupFiles`, `unstubGlobals: true`, `unstubEnvs: true` y `globals: true`. Lo último porque la limpieza automática de React Testing Library depende de un `afterEach` global. Fuera de Vitest, `server.port: 5173` con `strictPort: true`: otro puerto rompería el CORS sin aviso.

### D13 — Librerías que no se agregan

El estado de la sesión es un `Context` de React. Sin gestor de estado, kit de UI, librería de formularios, axios (`fetch` alcanza) ni librería de JWT (leer un segmento son pocas líneas, sin verificar firma). React Router sí, porque las guardas y el layout del alcance lo necesitan.

### D14 — Organización de rutas

Modo declarativo de React Router (`<Routes>`, `<Route>`, `<Outlet>`, `<Navigate replace>`), importado de `react-router`. `main.tsx` monta `BrowserRouter` y los tests `MemoryRouter`, con el mismo `App`.

```
frontend/src/
├── main.tsx                 # BrowserRouter + App
├── App.tsx                  # ProveedorSesion + árbol de rutas (único lugar donde se agregan rutas)
├── features/sesion/         # claims, almacenamiento, ProveedorSesion, guardas, mapa de inicio, formulario
├── shared/api/              # cliente HTTP y error normalizado
├── shared/layout/           # layout
├── pages/                   # login, agenda, configuración, sin permiso, no encontrada
└── test/                    # setup y fábricas de fixtures ficticios
```

```tsx
<Routes>
  <Route path="/" element={<RedireccionInicial />} />
  <Route element={<SoloSinSesion />}>
    <Route path="/login" element={<PaginaLogin />} />
  </Route>
  <Route element={<ConSesion />}>
    <Route element={<Layout />}>
      <Route path="/agenda" element={<PaginaAgenda />} />          {/* ambos roles */}
      <Route element={<ConRol roles={["recepcionista"]} />}>
        <Route path="/configuracion" element={<PaginaConfiguracion />} />
      </Route>
    </Route>
  </Route>
  <Route path="*" element={<PaginaNoEncontrada />} />
</Routes>
```

C-15 y C-16 reemplazan los placeholders y agregan `<Route>` en el grupo que corresponda. Sus features viven en `features/agenda/`, etc., y piden el cliente con `useClienteApi()`.

### D15 — Cliente HTTP

`crearClienteApi({ urlBase, obtenerToken, alNoAutenticado })`, sobre `fetch`. La inyección permite probarlo sin React. `ProveedorSesion` crea la instancia y la expone. Todo fallo es un único `ErrorApi` con `status`, `codigo` (`string | null`), `mensaje`, `errores` (por campo, en `422`) y `datos` (el resto de `detail`, para que C-15 lea `recursos` o `turnos`). `status` `0` significa falla de red. El token de cada pedido se captura al enviarlo y se entrega a `alNoAutenticado` (D4).

- **La forma de `detail` decide, no el `status`**: objeto con `codigo`, error de negocio, también en `422` (`rango_invalido`, `referencia_invalida`); lista, validación; texto, JSON sin `detail` o cuerpo no JSON, otras fallas.
- **`loc` (P1, aprobada el 2026-11-09, DD-33 l)**: cada entrada de `errores` es `{ campo: string | null, mensaje: string }`. `campo` es el último tramo de `loc` si es texto y no es el origen (`loc[0]`). Con `["body"]` o `["body", 5]` es nulo: C-15 y C-16 lo muestran como error general del formulario, no asociado a ningún campo.
- **Textos**: el `mensaje` de nivel superior viene de la API o es un texto propio en español (con voseo, como la API): `Ocurrió un error. Intentá de nuevo.`, `Revisá los datos ingresados.` y `No se pudo conectar con el servidor.`. Nunca es el `detail` de texto ni el cuerpo. El `mensaje` de cada entrada de `errores` conserva el `msg` de FastAPI, en inglés y sin garantía de que sea apto para mostrar; qué hacer con él lo decide cada pantalla.

### D16 — Lint y formato

Equivalente a `ruff check` y `ruff format`: ESLint con `@eslint/js`, `typescript-eslint` (`recommended`) y `react-hooks`, más Prettier con su configuración por defecto. Scripts: `dev`, `build` (`tsc -b && vite build`), `typecheck`, `lint`, `format`, `format:check`, `test` (`vitest run`), `test:watch`. Sin CI: el repo no tiene.

### D17 — Costuras de test (TDD estricto)

1. **Claims**: función pura, sin React.
2. **Cliente HTTP**: `crearClienteApi` con `fetch` falso y `Response` reales.
3. **Pantallas y guardas**: `App` entero dentro de `MemoryRouter`, con `fetch` falso, `sessionStorage` real de jsdom y `user-event`, afirmando lo que ve el usuario (roles y textos), no los componentes internos.

Los tokens se arman con un helper (`encabezado.payload.firma-ficticia`) y datos ficticios (`recepcion@example.com`, UUIDs inventados). El vencimiento se prueba con `vi.useFakeTimers`.

### D18 — Alcance de los tests

El alcance pide tests de login y de redirección por rol. **Los tests contra el backend real quedan fuera**, salvo el CORS, que se prueba en `pytest` contra la app real. La tarea final incluye una verificación manual del stack completo.

### D19 — Zona horaria

C-14 solo compara `exp` (epoch) con el reloj, sin presentar fechas. La regla de mostrar horarios en `America/Argentina/Buenos_Aires` es de C-15.

### D20 — Ruta inexistente

La KB no lo menciona. El comodín de rutas muestra `PaginaNoEncontrada` con un enlace a `/`, con o sin sesión, fuera de las guardas: `/` ya lleva a cada usuario a donde corresponde. Sin regla de dominio; se registra en DD-33 (tarea 9.2).

## Risks / Trade-offs

- [El token en `sessionStorage` es legible ante un XSS] → Sin `dangerouslySetInnerHTML`, token de vida corta y reevaluar la cookie `httpOnly` si el sistema se despliega.
- [El frontend depende de los nombres de los claims del JWT] → Un contrato fijado por el spec `autenticacion`. Un token inesperado se rechaza con un mensaje genérico (spec `frontend-sesion`).
- [Reloj del cliente adelantado más que `JWT_EXPIRE_MINUTES`] → El token parece vencido al recibirlo y el login muestra un error genérico en lugar de un bucle. Es poco probable en PCs con hora de red.
- [Una excepción no manejada devuelve `500` sin encabezados CORS, porque el manejador de Starlette queda por fuera del middleware] → El navegador lo ve como falla de red y muestra "no se pudo conectar". Aceptado: no ocurre en los errores de negocio, que sí llevan los encabezados (escenario del spec `app-configuration`).
- [`typescript` queda una versión mayor por detrás] → Lo impone `typescript-eslint`; se actualiza cuando lo soporte.
- [`CORS_ORIGINS` con `*` abriría la API a cualquier origen] → Es configuración inválida: la API no arranca (P2, D2). `.env.example` y el README muestran un origen concreto.
- [El servicio `frontend` no es apto para producción] → El MVP no define despliegue; se documenta en el README.

## Migration Plan

Sin migración de base: la cabeza de Alembic sigue en `010`. Variable nueva opcional: `VITE_API_URL`, con valor por defecto. Rollback: revertir la rama; el middleware de CORS no cambia ningún contrato de una llamada sin encabezado `Origin`.

## Open Questions

Ninguna que cambie specs o tareas: D1 a D11 están aprobadas y P1 a P3 de la revisión están respondidas. Quedan para más adelante, sin bloquear: MSW en C-15 y cookie `httpOnly` si se define un despliegue real.
