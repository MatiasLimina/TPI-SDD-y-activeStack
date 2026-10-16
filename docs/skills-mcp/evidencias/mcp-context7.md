# Evidencia — uso real del MCP Context7

Fecha: 2026-10-16 · Cliente: Claude Code (app de escritorio, Windows 11) · Change: C-06 `auth-jwt-roles`

Para cada invocación se registra la solicitud, un resumen del resultado y qué aporta al change. Los
fragmentos de documentación se resumen; las fuentes originales están enlazadas.

## 1. Comprobación de conexión

| Comprobación | Resultado |
|---|---|
| `curl https://mcp.context7.com/ping` | `{"status":"ok","message":"pong"}`, HTTP 200 |
| `claude mcp list` (en la raíz del repo) | `context7 … ✔ Connected`, con aviso de que está definido en dos ámbitos (ver "Problema de instalación" en [../mcp.md](../mcp.md)) |
| `tools/call` directo por HTTP (JSON-RPC, sin cliente) a `resolve-library-id` con `libraryName: "PyJWT"` | Devuelve `/jpadilla/pyjwt`, reputación High, versión 2.15.1: el endpoint del `.mcp.json` del proyecto funciona por sí solo |

## 2. `resolve-library-id` — FastAPI

- **Solicitud**: `libraryName: "FastAPI"`, `query: "OAuth2 password flow with JWT tokens, password hashing, role-based dependencies"`.
- **Resultado**: `/websites/fastapi_tiangolo` (3457 snippets, reputación High, benchmark 85.29) más
  alternativas (`fastapi-users`, Deepwiki). Se elige la documentación oficial.

## 3. `query-docs` — FastAPI, tutorial OAuth2 + JWT

- **Solicitud**: `libraryId: /websites/fastapi_tiangolo`, `query: "OAuth2 with Password and JWT Bearer
  tokens: which JWT library and password hashing library does the tutorial recommend (PyJWT, pwdlib
  argon2), and how is an expired or invalid token handled"`.
- **Resultado (resumen)**: el tutorial oficial
  (<https://fastapi.tiangolo.com/tutorial/security/oauth2-jwt>) usa **PyJWT** (`jwt.decode(..., algorithms=[ALGORITHM])`)
  y **`pwdlib[argon2]`** (`PasswordHash.recommended()`); ante `InvalidTokenError` responde `401` con
  `WWW-Authenticate: Bearer`; cuando el usuario no existe verifica igual contra un hash señuelo
  (`DUMMY_HASH`) para que el tiempo de respuesta no revele qué emails existen; y responde `400 "Inactive user"`
  para usuarios desactivados.
- **Aporte a C-06**:
  - Fundamenta en `design.md` la elección PyJWT + pwdlib/argon2 (la KB admitía "bcrypt/argon2" sin decidir).
  - El `401` uniforme para email inexistente y contraseña incorrecta, con verificación de un hash señuelo,
    pasa a ser un escenario de borde y una pregunta para el equipo (la KB no lo fija).
  - **Sugerencia no adoptada sin decisión**: el tutorial responde `400` a un usuario inactivo. La KB no fija
    ese código: `CHANGES.md` C-06 solo dice que un usuario desactivado "no inicia sesión" y el Flujo 1
    (`07_flujos_principales.md`) usa 401/403 para los demás casos. Queda como pregunta abierta para el
    Propose de C-06 (y como caso de revisión crítica: la documentación oficial no decide el dominio).

## 4. `query-docs` — PyJWT, validación de expiración y algoritmos

- **Solicitud**: `libraryId: /jpadilla/pyjwt`, `query: "decode a token validating exp claim,
  ExpiredSignatureError vs InvalidTokenError, why algorithms parameter must be passed explicitly, leeway"`.
- **Resultado (resumen)**: `jwt.decode` verifica `exp` automáticamente y lanza `ExpiredSignatureError`;
  `leeway` acepta tokens vencidos dentro de un margen (por defecto 0); desde la 2.0 `algorithms` es
  obligatorio y un token cuyo `alg` no está en la lista se rechaza con `InvalidAlgorithmError` (protege contra
  `alg: none` y confusión de algoritmo); una clave corta para HMAC emite `InsecureKeyLengthWarning`.
  Fuente: <https://github.com/jpadilla/pyjwt/blob/master/docs/usage.rst>.
- **Aporte a C-06**:
  - Escenario de borde "token que vence en el instante del request" con reloj fijo y `leeway = 0`.
  - Escenario de error "token con `alg` no permitido o `none`" → `401`.
  - Hallazgo para el design: el placeholder `JWT_SECRET=change-me` de
    `08_arquitectura_propuesta.md` es más corto que lo que PyJWT recomienda para HS256; `.env.example`
    debería indicar cómo generar una clave de al menos 32 bytes (por ejemplo `openssl rand -hex 32`).
