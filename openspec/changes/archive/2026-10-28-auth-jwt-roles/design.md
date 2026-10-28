# Design

## Context

Ver `proposal.md` (Why, Non-goals) y los delta specs `autenticacion`, `usuarios`, `agenda-turnos`, `datos-semilla` y `app-configuration`. Estado actual del código relevante (C-01..C-05 archivados):

- `backend/app/config.py`: `Settings` (pydantic-settings, lee `.env` de la raíz) ya declara `JWT_SECRET` (obligatoria) y `JWT_EXPIRE_MINUTES: int = 60`, sin validar el rango. `tests/unit/test_env_example.py` exige que todo campo de `Settings` figure en `.env.example` y que `JWT_SECRET` sea `change-me`.
- `backend/app/api/turnos.py`: tres rutas sin autenticación; las dependencias `get_crear_turno`, `get_cancelar_turno`, `get_reprogramar_turno` arman el caso de uso con `get_session` y `get_reloj`. `TurnoOut` ya expone `creado_por`. Errores de dominio con cuerpo `{"detail": {"codigo", ...}}` vía `registrar_manejadores`.
- `backend/app/application/crear_turno.py`: `CrearTurno.ejecutar(solicitud)`; `SolicitudTurno` se construye con `SolicitudTurno(**datos.model_dump())` y también lo produce la fusión de la reprogramación. `RepositorioTurnos.insertar(propuesto)` no setea `creado_por`; `TurnoCreado.desde_propuesto` tampoco lo copia.
- `backend/app/infrastructure/db/models/turno.py`: `creado_por` uuid nullable **sin FK** (comentario "hasta que exista `usuario` (C-06)"). Convención de nombres en `base.py` (`ck_%(table)s_%(name)s`, `fk_%(table)s_%(col)s_%(referred)s`, `ix_...`, `uq_...`).
- `backend/app/infrastructure/db/seed.py`: uuids fijos `...0101`/`...0102` (profesionales) e `insert ... on_conflict_do_nothing()`; `main()` hace commit. Los tests del seed (`test_seed.py`) vacían el catálogo con `DELETE` dentro de la transacción de test; `test_seed_main.py` corre `main()` dos veces sobre la base scratch.
- Migraciones lineales `001..003` (DD-17). `test_migrations.py` afirma que `head` es `"003"`; `test_migracion_003.py` sube a `head` y compara el conjunto **exacto** de FKs de `turno`; `test_modelos_vs_migracion.py` compara `Base.metadata` contra la base migrada con `compare_metadata`.
- Tests: `client` (en `tests/conftest.py`) es un `TestClient` sin credenciales con `get_session` sobreescrito por la `db_session` transaccional; lo usan `test_api_turnos.py`, `test_api_cancelar_turno.py`, `test_api_reprogramar_turno.py` y `test_health.py`. Baseline: 388 tests.
- No existe `backend/app/cli/` (previsto en `08_arquitectura_propuesta.md`). Dependencias actuales: `fastapi>=0.115`, sin librería de JWT ni de hashing.

**Registro en la KB**: las decisiones D1..D15 se acordaron con el usuario el 2026-10-28. Las seis que la KB no fijaba —contrato de errores (`credenciales_invalidas`, `no_autenticado`, `rol_insuficiente`, con `401` uniforme y hash ficticio anti-timing), email normalizado con CHECK, a lo sumo un usuario activo por profesional, `JWT_EXPIRE_MINUTES <= 0` como configuración inválida, rehash en el login y contrato del CLI— quedaron registradas en **DD-24** (`knowledge-base/09_decisiones_y_supuestos.md`), junto con `04` §Usuario y `07` §Flujo 1; ya no están pendientes de registro.

## Goals / Non-Goals

**Goals:**
- Una sola dependencia de autenticación (`usuario_actual`) y una fábrica genérica `requiere_rol(*roles)` que reusen C-07..C-13 sin tocarlas.
- Autorización resuelta contra la base en cada request: desactivar un usuario corta su acceso de inmediato, sin lista de revocación.
- Respuesta de login indistinguible entre los tres rechazos, con el mismo trabajo de hashing.
- Integridad de usuarios garantizada por la base (CHECK, UNIQUE, FK), igual que en el resto del modelo.
- Suite existente en verde durante todo el change: el fixture de autenticación se introduce primero.

**Non-Goals:**
- Rate limiting del login y registro de eventos de seguridad (backlog; ver Risks).
- Validación del largo de `JWT_SECRET` al arrancar (D5, excluida a conciencia; ver decisión 4).
- Política de complejidad o largo mínimo de contraseña más allá de "no vacía" (backlog; ver Risks).
- Revocación de tokens individuales, refresh, logout, cambio de contraseña.
- Filtrado por `profesional_id` del odontólogo (llega con los endpoints de lectura, C-13).

## Decisions

Mapa de los ids `D-n` citados en este documento (acordados con el usuario el 2026-10-28; los que la KB fijaba o no se citan acá no figuran). Origen en `knowledge-base/09_decisiones_y_supuestos.md` §DD-24 (letras a–j):

| Id | Significado | Registro |
|---|---|---|
| D1 | Usuario inactivo responde el mismo `401` que credenciales inválidas | DD-24 (a) |
| D2 | Login con body JSON, sin form-data | DD-24 (c) |
| D4 | `fastapi>=0.122` (esquemas de seguridad responden `401`) | Solo este design (Context7); no figura en DD-24 |
| D5 | Sin validar el largo de `JWT_SECRET` al arrancar | DD-24 (Fuera de alcance) |
| D11 | Fixture de autenticación antes de proteger rutas | Solo este design y `tasks.md` (grupo 4) |
| D12 | Rate limiting y eventos de seguridad en backlog | DD-24 (Fuera de alcance) y `CHANGES.md` |
| D13 | Hash ficticio anti-timing en el login | DD-24 (a) |
| D14 | El claim `rol` es informativo; el rol vale el de la base | DD-24 (b) |
| D15 | Sin reloj inyectado en los tokens | Solo este design (decisión 4) |

### 1. Capas y módulos
- `app/domain/usuarios.py`: `Rol` (`StrEnum`: `recepcionista`, `odontologo`), `UsuarioAutenticado` (dataclass: `id`, `rol`, `profesional_id`), `normalizar_email` (strip + lower), `validar_forma_email` (además rechaza espacios internos y caracteres de control, porque `strip`/`lower` de Python y `btrim`/`lower` de PostgreSQL pueden discrepar con ellos y el CHECK dejaría pasar o rechazaría distinto), reglas puras del alta (`validar_alta(rol, profesional_id)`) y errores: `CredencialesInvalidasError` (401), `NoAutenticadoError` (401), `RolInsuficienteError` (403), `AltaUsuarioInvalidaError(codigo, mensaje)` y `UsuarioInexistenteError` (CLI). Sin SQLAlchemy ni FastAPI.
- `app/infrastructure/security/contrasenas.py`: `Hasher` (envoltorio de `pwdlib.PasswordHash` con `hash`, `verify_and_update` y `verificar_dummy`), `get_hasher()` (`lru_cache`, `PasswordHash.recommended()`).
- `app/infrastructure/security/tokens.py`: `EmisorTokens(secreto, minutos)` con `emitir(usuario) -> str` y `decodificar(token) -> ClaimsToken`; `TokenInvalidoError`.
- `app/infrastructure/db/models/usuario.py` + `repositorio_usuarios.py` (`por_email`, `por_id`, `insertar`, `desactivar`, `actualizar_hash`, `profesional_activo`, `profesional_con_usuario_activo`).
- `app/application/autenticacion.py`: `IniciarSesion(repo, hasher, emisor)` y `AutenticarToken(repo, emisor)`.
- `app/application/usuarios.py`: `DarDeAltaUsuario(repo, hasher)` y `DesactivarUsuario(repo)`.
- `app/api/auth.py`: router `/auth`, `LoginIn`, `TokenOut`, dependencias `get_hasher`, `get_emisor_tokens`, `usuario_actual`, `requiere_rol`, y `registrar_manejadores_auth`.
- `app/cli/__main__.py` + `app/cli/usuarios.py`: `argparse` con subcomando `usuarios {alta,desactivar}`.

### 2. Modelo y migración `004_usuario.py`
Tabla `usuario` (`CatalogoMixin` para `id`/`creado_en`/`actualizado_en`, todos con default en la BD):

| Columna | Tipo | Restricción |
|---|---|---|
| `email` | `varchar(254)` | `NOT NULL`, `uq_usuario_email`, `ck_usuario_email_normalizado`: `email = lower(btrim(email)) AND email <> ''` |
| `password_hash` | `varchar(255)` | `NOT NULL` |
| `rol` | `varchar(20)` | `NOT NULL`, `ck_usuario_rol_valido`: `rol IN ('recepcionista','odontologo')` |
| `profesional_id` | `uuid` | nullable, `fk_usuario_profesional_id_profesional` `ON DELETE RESTRICT`; `ck_usuario_profesional_segun_rol`: `(rol = 'odontologo') = (profesional_id IS NOT NULL)` |
| `activo` | `boolean` | `NOT NULL DEFAULT true` |

Índices: `ix_usuario_profesional_id` (toda FK indexada) y `uq_usuario_profesional_activo` único parcial `ON (profesional_id) WHERE activo`.
En `turno`: FK `fk_turno_creado_por_usuario` (`ON DELETE RESTRICT`) e índice `ix_turno_creado_por`; la columna sigue nullable.
- **`rol` como `varchar` + CHECK** y no enum nativo: misma razón que DD-21 para `estado` (agregar un valor no exige `ALTER TYPE`).
- **Email normalizado en la base**: la aplicación normaliza en el login y en el alta, y el CHECK garantiza que una inserción directa (seed, SQL manual) no cree `Ana@x` y `ana@x` como usuarios distintos. **Alternativa descartada**: `citext` o índice único sobre `lower(email)` (extensión nueva u operación de comparación implícita; con el valor ya normalizado alcanza un `UNIQUE` simple).
- **Un usuario activo por profesional** (ERD `Usuario 1---0..1 Profesional` de `04_modelo_de_datos.md`): parcial sobre `activo` porque la baja es lógica y no hay reactivación; sin el filtro, un profesional cuyo usuario se desactivó no podría tener otro nunca.
- **`ON DELETE RESTRICT`** en `creado_por`: el usuario nunca se borra (DD-16) y C-07 lo referenciará en la auditoría.
- `downgrade`: borra índice y FK de `turno`, y después la tabla `usuario`.

### 3. Hash de contraseñas (`pwdlib[argon2]`)
- Producción: `PasswordHash.recommended()` (argon2id con los parámetros por defecto de `argon2-cffi`).
- `verify_and_update(password, hash)` devuelve `(valido, hash_nuevo | None)`; si el login es válido y hay `hash_nuevo` (parámetros cambiados), se persiste con `actualizar_hash` en la misma transacción del login.
- **Anti-timing (D13)**: el `Hasher` calcula una vez, perezosamente, un `DUMMY_HASH` con **sus propios** parámetros (`hash` de un valor fijo no secreto) y `verificar_dummy(password)` lo verifica y descarta el resultado. Calcularlo con la misma instancia garantiza que el costo sea el mismo que el de un hash real. Un hash guardado con formato desconocido (`UnknownHashError`) se trata como contraseña incorrecta.
- **Tests**: argon2 con parámetros de producción tarda decenas de ms por operación y la suite crea usuarios en cientos de tests. Los tests sobreescriben `get_hasher` con `PasswordHash((Argon2Hasher(time_cost=1, memory_cost=8, parallelism=1),))`: sigue siendo argon2id y el mismo código de producción, con costo mínimo. Un test unitario aparte verifica que `get_hasher()` por defecto produce hashes `$argon2id$` con los parámetros recomendados.
- **Alternativas descartadas**: `passlib` (sin mantenimiento, roto con bcrypt ≥4.1 y Python 3.13) y bcrypt (trunca a 72 bytes; la KB admite ambos, argon2 es el recomendado por OWASP y por la skill `auth-implementation-patterns`).

### 4. Token JWT (`PyJWT`)
- `emitir`: `jwt.encode({"sub": str(usuario.id), "rol": usuario.rol, "profesional_id": str | None, "exp": ahora + JWT_EXPIRE_MINUTES}, secreto, algorithm="HS256")`, con `ahora = datetime.now(UTC)`. Sin reloj inyectado (D15): los tests de vencimiento firman a mano tokens con un `exp` explícito y claramente separado del instante del request (una hora antes; y para el borde, 60 s antes → rechazado y 60 s después → aceptado), así que no dependen de la precisión del reloj. Los tests de emisión acotan `exp` entre los instantes medidos antes y después de emitir, con una tolerancia de 5 s.
- `decodificar`: `jwt.decode(token, secreto, algorithms=["HS256"], options={"require": ["exp", "sub"]})`. Lista de algoritmos fija: un token `alg: none` o `HS512` levanta `InvalidAlgorithmError`. Cualquier `jwt.InvalidTokenError` (firma, vencido, `MissingRequiredClaimError`, `DecodeError`) y un `sub` que no parsea como UUID se traducen a `TokenInvalidoError`.
- **`sub` como texto**: la especificación JWT lo define como string y PyJWT reciente lo valida; un UUID crudo no se serializa.
- **El claim `rol` es informativo** (D14): sirve al frontend (C-14), pero la autorización usa el usuario releído (decisión 5).
- **HS256 fijo y sin validar el largo de `JWT_SECRET` (D5)**: PyJWT solo emite `InsecureKeyLengthWarning` con claves HMAC de menos de 32 bytes, salvo que se pase `enforce_minimum_key_length=True`. El usuario excluyó la validación al arrancar; `change-me` sigue siendo placeholder en `.env.example` y en desarrollo se verá la advertencia. Riesgo registrado para el despliegue (ver Risks).
- **Alternativas descartadas**: `python-jose` (sin mantenimiento); RS256 (un solo servicio emite y valida; agrega gestión de claves sin beneficio en el MVP).

### 5. Dependencias FastAPI: `usuario_actual` y `requiere_rol`
```python
_bearer = HTTPBearer(auto_error=False)

def usuario_actual(
    credenciales: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
    session: Annotated[Session, Depends(get_session)],
    emisor: Annotated[EmisorTokens, Depends(get_emisor_tokens)],
) -> UsuarioAutenticado: ...

def requiere_rol(*roles: Rol) -> Callable[..., UsuarioAutenticado]: ...
```
- `AutenticarToken`: sin credenciales → `NoAutenticadoError`; `decodificar` → `TokenInvalidoError` → `NoAutenticadoError`; `repo.por_id(sub)` → `None` o `activo = false` → `NoAutenticadoError`; devuelve `UsuarioAutenticado` con `rol` y `profesional_id` **de la base**.
- `requiere_rol(Rol.RECEPCIONISTA)` depende de `usuario_actual` y lanza `RolInsuficienteError` si el rol no está en `roles`.
- **`auto_error=False`**: `HTTPBearer` devuelve `None` tanto sin encabezado como con un esquema distinto de `Bearer`, y el `401` lo arma nuestro manejador con el mismo cuerpo (`no_autenticado`) y `WWW-Authenticate: Bearer` para todos los casos de token. Con `auto_error=True` el cuerpo sería el genérico de FastAPI (`{"detail": "Not authenticated"}`), distinto del de token vencido. Igual se fija `fastapi>=0.122` (D4): desde esa versión los esquemas de seguridad responden `401` y no `403` ante credenciales ausentes, así que cualquier ruta futura que use `auto_error=True` queda coherente con este contrato.
- **Misma sesión que el caso de uso**: FastAPI cachea `get_session` por request, así que `usuario_actual` y el caso de uso comparten la sesión (y en tests, la `db_session` transaccional).
- **Orden de evaluación**: FastAPI resuelve las sub-dependencias antes de validar path y body, por lo que `401`/`403` preceden al `422` de Pydantic y a cualquier búsqueda del turno (`404`/`409`). Excepción heredada del framework: un body que **no es JSON** falla al parsearse antes de las dependencias y responde `422`; los escenarios usan JSON bien formado.
- **Rutas**: `POST /turnos` declara `usuario: Annotated[UsuarioAutenticado, Depends(requiere_rol(Rol.RECEPCIONISTA))]` como **primer** parámetro y pasa `usuario.id` al caso de uso; cancelar y reprogramar lo declaran igual (o en `dependencies=[...]`). `GET /health` y `POST /auth/login` no dependen de `usuario_actual`, así que un `Authorization` inválido en ellas se ignora.
- **Alternativas descartadas**: middleware global de autenticación con lista de rutas públicas (rompe el `404` de rutas inexistentes, es implícito y no da el usuario tipado a la ruta); confiar en el claim `rol` sin releer (un usuario desactivado seguiría operando hasta el vencimiento).

### 6. Login (`POST /auth/login`)
`LoginIn(email: str, password: str)` (JSON, D2; sin `OAuth2PasswordRequestForm` ni `python-multipart`; sin `EmailStr` para no sumar `email-validator` y porque un email mal formado debe dar el mismo `401`). `IniciarSesion.ejecutar(email, password)`:
1. `usuario = repo.por_email(normalizar_email(email))`.
2. Si `usuario is None`: `hasher.verificar_dummy(password)` y `CredencialesInvalidasError`.
3. `valido, nuevo = hasher.verify_and_update(password, usuario.password_hash)` (también si está inactivo: mismo trabajo).
4. Si `not valido or not usuario.activo`: `CredencialesInvalidasError`.
5. Si `nuevo`: `repo.actualizar_hash(usuario.id, nuevo)` y `commit()`.
6. `TokenOut(access_token=emisor.emitir(usuario), token_type="bearer")`.

Exactamente una verificación de hash por intento en los tres caminos de rechazo (el escenario lo comprueba con un hasher espía inyectado). El tiempo en sí no se testea.

### 7. `creado_por` desde el usuario autenticado
`CrearTurno.ejecutar(solicitud, *, creado_por: UUID | None = None)` → `repositorio.insertar(propuesto, *, creado_por=...)` → `Turno(creado_por=...)` y `TurnoCreado.desde_propuesto(..., creado_por=...)`, de modo que los observadores (C-07) ya lo reciben. La ruta pasa siempre `usuario.id`; `TurnoIn` no declara `creado_por`, y como los campos desconocidos se ignoran, un `creado_por` en el body no llega a ningún lado. Cancelar y reprogramar no lo tocan: `marcar_cancelado` y `actualizar` del repositorio no asignan `creado_por` (ya hoy es así) y los escenarios "no cambia el autor" lo fijan.
- **Default `None` en el caso de uso**: los tests de dominio, repositorio y caso de uso de C-03..C-05 (que afirman `creado_por is None`) siguen válidos sin crear usuarios; la obligatoriedad vive en la ruta, que no puede ejecutarse sin `requiere_rol`.
- **Alternativa descartada**: agregar `creado_por` a `SolicitudTurno` (la solicitud se arma con `**datos.model_dump()` y en la fusión de la reprogramación; mezclar el autor con los datos del request invita a que algún día venga del body).

### 8. Comando CLI (`python -m app.cli usuarios ...`)
- `argparse` con `usuarios alta --email --rol {recepcionista,odontologo} [--profesional-id UUID]` y `usuarios desactivar --email`. No existe opción de contraseña: `argparse` rechaza `--password` como argumento desconocido (código `2`).
- Contraseña (DD-24): `USUARIO_PASSWORD` si está definida y no vacía (uso no interactivo); definida y vacía → error de dominio (código `1`) sin caer al prompt, porque en un script indica una configuración rota; no definida → `getpass` dos veces (sin eco). Vacía por consola o confirmación distinta → error.
- `main(argv=None, *, sesion=None, hasher=None, entorno=os.environ, pedir=getpass.getpass) -> int`: los tests lo invocan en proceso con la `db_session` transaccional, el hasher barato, un `entorno` dict y un `pedir` falso; `__main__` usa la sesión real (`get_engine`) y `sys.exit(main())`.
- Códigos de salida: `0` éxito (incluida la desactivación idempotente), `1` error de dominio (`AltaUsuarioInvalidaError`, `UsuarioInexistenteError`) con el mensaje en `stderr`, `2` uso inválido (`argparse`). Nunca se imprime la contraseña ni el hash.
- Validaciones del alta en orden: forma del email → rol/profesional (`validar_alta`, puro) → profesional existe y activo → profesional sin usuario activo → email no registrado (activo o inactivo) → contraseña. La base es la red final: una `IntegrityError` de unicidad por carrera se traduce al mismo error de email o de profesional, y **cualquier otra** `IntegrityError` (p. ej. el CHECK de email normalizado ante una discrepancia Python/PostgreSQL) se traduce a código `1` con un mensaje claro en `stderr`, sin traceback.
- **Alternativas descartadas**: `typer`/`click` (dependencia nueva para dos subcomandos); contraseña por argumento (queda en el historial y en `ps`).

### 9. Seed de usuarios
- `USUARIOS` con uuids fijos `...0501` (recepcionista `recepcion@example.com`), `...0502` (`ana.ficticia@example.com`, profesional `...0101`) y `...0503` (`bruno.inventado@example.com`, profesional `...0102`), sin contraseñas en el código.
- `SeedSettings(BaseSettings)` en `seed.py`, con el mismo `env_file` y `extra="ignore"` (el `.env` raíz trae variables ajenas como `DATABASE_URL`), lee `SEED_RECEPCIONISTA_PASSWORD`, `SEED_ODONTOLOGO_1_PASSWORD`, `SEED_ODONTOLOGO_2_PASSWORD` (opcionales). No se agregan a `Settings` de la app: la API en ejecución no necesita esas contraseñas. Como lee el `.env` real, los tests no pueden aislarse con `monkeypatch.delenv`: construyen `SeedSettings(_env_file=None, ...)` (o inyectan la instancia a `main`) para ver solo lo que el test define.
- `seed_usuarios(session, contrasenas, hasher)` inserta después del catálogo (FK a profesional) con `on_conflict_do_nothing()` sin target, que cubre id, email y el único parcial por profesional: no pisa un usuario desactivado ni su hash. Una variable ausente o vacía omite ese usuario.
- `.env.example`: `SEED_RECEPCIONISTA_PASSWORD=dev-recepcion-ficticia`, `SEED_ODONTOLOGO_1_PASSWORD=dev-odontologo1-ficticia`, `SEED_ODONTOLOGO_2_PASSWORD=dev-odontologo2-ficticia`.

### 10. Configuración
`JWT_EXPIRE_MINUTES: int = Field(default=60, gt=0)` (DD-24): `0`, negativo o no numérico (`abc`, validación de entero de Pydantic) falla al cargar con un error que nombra la variable; sin definir vale `60` (escenario ya archivado en `app-configuration`). `get_emisor_tokens()` construye `EmisorTokens(get_settings().JWT_SECRET, get_settings().JWT_EXPIRE_MINUTES)`.

### 11. Contrato HTTP
| Situación | HTTP | Cuerpo / encabezados |
|---|---|---|
| Login válido | 200 | `{"access_token": "<jwt>", "token_type": "bearer"}` |
| Login: email desconocido, contraseña incorrecta o usuario inactivo | 401 | `{"detail": {"codigo": "credenciales_invalidas", "mensaje": "Credenciales inválidas"}}` + `WWW-Authenticate: Bearer` |
| Login: falta `email` o `password`, tipos inválidos | 422 | Validación nativa de FastAPI/Pydantic |
| Ruta protegida sin token, esquema no Bearer, token mal formado, firma o algoritmo inválidos, vencido, sin `sub`/`exp`, `sub` no UUID, usuario inexistente o inactivo | 401 | `{"detail": {"codigo": "no_autenticado", "mensaje": "No autenticado"}}` + `WWW-Authenticate: Bearer` |
| Usuario autenticado sin el rol requerido | 403 | `{"detail": {"codigo": "rol_insuficiente", "mensaje": "Rol insuficiente"}}` |
| Recepcionista autenticada | — | Contratos de C-03..C-05 sin cambios; `creado_por` del alta = id del usuario |

Contrato registrado en DD-24. Los tres mensajes (`401` x2 y `403`) son constantes, así que los cuerpos de cada familia son idénticos byte a byte. Un único código para todos los problemas de token: el cliente reacciona igual (volver al login) y no se informa por qué falló la validación.

### 12. Tests y fixtures
- **Primero el fixture** (D11): `tests/conftest.py` agrega `hasher_test` (argon2 barato), `emisor_test` (`EmisorTokens` con un secreto de test ficticio de ≥ 32 bytes y 60 min), `recepcionista` (usuario real creado en la `db_session` con el código de producción) y `token_de(usuario)`. `client` sobreescribe `get_hasher` y `get_emisor_tokens` y fija `Authorization: Bearer <token de la recepcionista>` por defecto; `cliente_anonimo` es el mismo cliente sin encabezado. Así `test_api_turnos.py`, `test_api_cancelar_turno.py` y `test_api_reprogramar_turno.py` corren sin cambios salvo las aserciones `creado_por is None` de la API, que pasan a `== str(recepcionista.id)`.
- Los tests de concurrencia usan los casos de uso directamente (sin API) y no necesitan usuarios; `catalogo_commiteado` no cambia.
- Migración: `test_migracion_004.py` (columnas, CHECKs, únicos, índices, FK de `turno.creado_por`, `downgrade` a `003` y re-`upgrade`); `test_migrations.py` pasa a esperar `"004"`; `test_migracion_003.py` sube a `"003"` en lugar de `head` para seguir afirmando el conjunto exacto de FKs de esa revisión; `test_modelos_vs_migracion.py` incorpora `Usuario`.
- `test_seed.py`: `base_vacia` borra también `usuario` antes que `profesional` (FK); `test_seed_main.py` no depende del `.env` local: construye `SeedSettings(_env_file=None, ...)` con solo los valores del test (o inyecta la instancia) y usa el hasher barato.

## Consulta a Context7

Documentación consultada (Context7, consultas genéricas sin código ni datos del proyecto) y cómo se usó:

| Fuente | Hallazgo | Uso en este change |
|---|---|---|
| FastAPI, tutorial de seguridad OAuth2/JWT | El ejemplo responde `400 Inactive user` cuando el usuario está inactivo | **Prevalece la KB/D1**: `401` idéntico a credenciales inválidas, para no revelar que la cuenta existe |
| FastAPI, release notes 0.122 | Los esquemas de seguridad pasan a responder `401` (antes `403`) ante credenciales ausentes o mal formadas | Se fija `fastapi>=0.122` (D4); con `auto_error=False` el contrato no depende de la versión, pero queda coherente |
| FastAPI, tutorial OAuth2/JWT | Patrón `DUMMY_HASH`: verificar contra un hash ficticio cuando el usuario no existe | Decisión 3 (anti-timing, D13), con el dummy calculado por la misma instancia del hasher |
| FastAPI, tutorial | Usa `OAuth2PasswordRequestForm` (form-data, requiere `python-multipart`) | **Descartado por D2**: body JSON con Pydantic |
| PyJWT | `options={"require": [...]}` levanta `MissingRequiredClaimError`; `algorithms` es obligatorio al decodificar | Decisión 4: `require: ["exp", "sub"]`, `algorithms=["HS256"]` |
| PyJWT | Claves HMAC < 256 bits solo emiten `InsecureKeyLengthWarning`, salvo `enforce_minimum_key_length=True` | Registrado como riesgo; sin validación al arrancar (D5) |
| pwdlib | `PasswordHash.recommended()` usa argon2; `verify(password, hash)`; `verify_and_update` devuelve `(valido, hash_nuevo \| None)` y re-hashea también si cambian los parámetros | Decisión 3 (rehash en el login); `Argon2Hasher(time_cost, memory_cost, parallelism)` para el hasher barato de tests |

Ante cualquier diferencia entre la documentación y la KB prevalece la KB; la única encontrada es la del `400` por usuario inactivo.

## Risks / Trade-offs

- [Sin rate limiting, el login admite fuerza bruta] → argon2 encarece cada intento y no hay forma de enumerar emails; rate limiting y registro de intentos fallidos quedan en backlog (D12) para antes de un despliegue real.
- [`JWT_SECRET` corto o el placeholder `change-me` en un despliegue] → PyJWT solo advierte; no se valida al arrancar por decisión del usuario (D5). Mitigación documental: `.env.example` y la guía de despliegue deben indicar un secreto aleatorio de ≥ 32 bytes. Backlog: `enforce_minimum_key_length` o validación en `Settings`.
- [`LoginIn.password` sin largo máximo: cada request cuesta un hash argon2 sin rate limiting] → anotado como backlog junto con el rate limiting (D12); no se agrega requisito al spec.
- [El `422` nativo de FastAPI devuelve en `input` el cuerpo recibido, incluida la contraseña, cuando el login llega incompleto] → solo vuelve al propio cliente y no se registra en logs; decisión del usuario en apply (2026-10-28): backlog, porque ocultarlo exige un manejador global de validación que afecta a todos los endpoints.
- [Un body con JSON sintácticamente inválido y sin token responde `422` (`json_invalid`) en lugar de `401`] → FastAPI parsea el body antes de resolver las dependencias; los escenarios usan JSON bien formado; aceptado, backlog junto con el manejador global de validación.
- [`Hasher.hash_dummy` se calcula la primera vez que se usa] → el primer login con un email inexistente tras arrancar paga un hash extra, una sola vez; decisión del usuario en apply (2026-10-28): se deja así, sin calentarlo en el `lifespan`.
- [Sin revocación de tokens] → la relectura del usuario en cada request corta el acceso al desactivarlo; un token robado de un usuario activo vale hasta su `exp` (60 min por defecto).
- [Una consulta extra por request protegido] → lectura por PK, despreciable para 1-5 profesionales.
- [Contraseñas débiles por CLI] → solo se exige no vacía; una política de largo mínimo es una regla nueva sin respaldo en la KB y queda como pregunta para el backlog.
- [Los tests de API pasan a depender del fixture de autenticación] → se introduce en el primer grupo de tareas con la suite completa en verde antes de proteger cualquier ruta.
- [argon2 lento en la suite] → hasher barato inyectado; un solo test usa los parámetros recomendados.
- [Odontólogo de un profesional desactivado puede iniciar sesión] → no tiene ningún endpoint habilitado en C-06; la regla se revisa con los endpoints de lectura (C-13).
- [El primer usuario en un entorno nuevo] → sin seed ni CLI nadie puede crear turnos; el Migration Plan exige crear la primera recepcionista antes de usar la API.
- [Sin reactivación: el email de un usuario desactivado queda tomado] → un usuario dado de baja por error no puede recuperar su cuenta ni volver a darse de alta con el mismo email; limitación aceptada del MVP (DD-24), con la reactivación registrada en el backlog de `CHANGES.md`.
- [Carrera entre dos altas por CLI del mismo email o del mismo profesional] → ambas pasan el pre-chequeo y la segunda choca contra `uq_usuario_email` o `uq_usuario_profesional_activo`; la base garantiza que no haya duplicados y el CLI traduce la `IntegrityError` al mismo error de dominio (decisión 8). No tiene escenario propio en este change: riesgo conocido, aceptable para un comando que se usa a mano y de a uno.

## Migration Plan

1. `alembic upgrade head` aplica `004`: crea `usuario` y agrega FK e índice a `turno.creado_por`. Los turnos existentes conservan `creado_por = NULL`, que la FK admite.
2. Desarrollo: copiar las variables `SEED_*_PASSWORD` de `.env.example` a `.env` y correr el seed. Otro entorno: `python -m app.cli usuarios alta --rol recepcionista ...` para la primera recepcionista.
3. Desplegar la API: desde ese momento los tres endpoints de turnos exigen token de recepcionista.
4. Rollback: revertir el código y `alembic downgrade 003` (borra índice, FK y la tabla `usuario`; los `creado_por` ya poblados quedan como uuids sin FK, igual que antes de C-06). Los usuarios se pierden; es aceptable porque se recrean por seed o CLI.
