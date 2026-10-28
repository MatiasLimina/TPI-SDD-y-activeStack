# Proposal

## Why

Hoy `POST /turnos`, `POST /turnos/{id}/cancelar` y `PATCH /turnos/{id}/reprogramar` están abiertos: cualquiera que alcance la API puede crear, mover o cancelar turnos de pacientes, y el turno no registra quién lo creó (`creado_por` queda vacío). Las leyes 25.326 y 26.529 exigen control de acceso por rol sobre datos de salud (RN-CU-01, `03_actores_y_roles.md`), y la auditoría de C-07 necesita un usuario autenticado al que atribuir cada cambio. US-010, RN-AU-01 y el Flujo 1 piden autenticación con JWT y dos roles; DD-16 fija que los usuarios se dan de alta por seed y por un comando CLI, sin UI ni endpoint.

## What Changes

- **Usuarios** (DD-16, DD-24, `04_modelo_de_datos.md` §Usuario): nueva tabla `usuario` (migración `004`) con email único normalizado, `password_hash` argon2 (nunca la contraseña en claro), `rol` restringido a `recepcionista | odontologo` por CHECK, `profesional_id` obligatorio si y solo si el rol es `odontologo`, y `activo`. La baja es `activo = false`, nunca borrado.
- **Comando CLI** `python -m app.cli usuarios alta|desactivar`: alta con email, rol y profesional (si odontólogo), contraseña pedida por prompt o tomada de una variable de entorno, **nunca** como argumento; desactivación idempotente; sin reactivación ni borrado.
- **`POST /auth/login`** (Flujo 1): body JSON `{email, password}`; si las credenciales son válidas y el usuario está activo responde `200` con `{"access_token", "token_type": "bearer"}`. Email desconocido, contraseña incorrecta y usuario inactivo responden **el mismo** `401` con el mismo cuerpo (DD-24), y el login hace el mismo trabajo de verificación de hash en los tres casos.
- **JWT** HS256 firmado con `JWT_SECRET`, con `sub` (id del usuario), `rol`, `profesional_id` y `exp` a `JWT_EXPIRE_MINUTES` (default 60). Se envía como `Authorization: Bearer`. Sin refresh token ni logout.
- **Autenticación de cada request protegido**: token ausente, mal formado, con firma inválida, vencido o sin los claims obligatorios → `401` con `WWW-Authenticate: Bearer`. El usuario se relee de la base en cada request: si fue desactivado después de emitido el token → `401`. El rol que vale es el de la base, no el del token.
- **RBAC** (RN-AU-01, matriz de `03_actores_y_roles.md`): crear, cancelar y reprogramar turnos quedan reservados al rol `recepcionista`; un `odontologo` autenticado recibe `403`. La autenticación y el permiso se evalúan antes que el body y que la existencia del turno. `GET /health` y `POST /auth/login` siguen públicos.
- **`creado_por`**: el alta de un turno registra al usuario autenticado; nunca se toma del body. Cancelar y reprogramar no lo cambian (quién hizo cada acción es C-07). La columna gana una FK a `usuario.id` (`ON DELETE RESTRICT`) e índice, y sigue nullable para las filas previas a este change.
- **Seed**: 1 recepcionista y 2 odontólogos ficticios vinculados a los dos profesionales del seed, con contraseñas de desarrollo leídas de variables `SEED_*_PASSWORD` (valores ficticios en `.env.example`); si falta una variable, ese usuario no se siembra. Idempotente y sin pisar cambios (un usuario desactivado sigue desactivado).
- **Dependencias**: `PyJWT` y `pwdlib[argon2]`; `fastapi` pasa a `>=0.122`.
- **BREAKING (contrato HTTP)**: los tres endpoints de turnos pasan a exigir token de recepcionista; un cliente sin token recibe `401`. `creado_por` en la respuesta de `POST /turnos` deja de ser `null`.

## Dependencias y alcance respecto de otros changes

C-06 depende de C-03 en CHANGES.md, pero **también modifica rutas entregadas por C-04 (`POST /turnos/{id}/cancelar`) y C-05 (`PATCH /turnos/{id}/reprogramar`)**, ambos ya archivados: CHANGES.md pide proteger "`POST /turnos`, cancelar y reprogramar (solo recepcionista)". Tocar esas rutas es parte del scope de C-06 y no una invasión: solo se les agrega la exigencia de autenticación y rol; sus reglas de negocio y códigos de error no cambian.

## Non-goals

- **Auditoría** de quién creó, canceló o reprogramó (C-07). Este change solo puebla `creado_por` en el alta.
- **Lectura de agenda** para el odontólogo ("R solo propios", RN-AU-02) y para la recepción: no hay endpoints de lectura hasta C-13; el filtrado por `profesional_id` llega con ellos.
- Gestión de recursos (C-08), pacientes (C-09), horarios y bloqueos (C-10, C-11), recordatorios (C-12), frontend y pantalla de login (C-14+).
- Endpoint o UI de usuarios, reactivación, cambio o recuperación de contraseña, refresh token, logout o revocación de tokens.
- **Rate limiting** del login y **registro de eventos de seguridad** (intentos fallidos): backlog, ver `design.md`.
- Validación de largo mínimo de `JWT_SECRET` al arrancar: excluida a conciencia (ver `design.md`).

## Capabilities

### New Capabilities
- `autenticacion`: inicio de sesión con email y contraseña, emisión y validación del JWT, respuesta `401` uniforme, relectura del usuario en cada request y rutas públicas.
- `usuarios`: usuario del sistema y su integridad en la base (email único, rol, vínculo con profesional, hash de contraseña, baja lógica) y el comando CLI de alta y desactivación.

### Modified Capabilities
- `agenda-turnos`: crear, cancelar y reprogramar exigen un usuario autenticado con rol `recepcionista` (`401`/`403`); `creado_por` pasa de "vacío" a "usuario autenticado" en el alta, con FK a `usuario`, y no cambia al cancelar ni al reprogramar.
- `datos-semilla`: el seed incorpora 3 usuarios ficticios con contraseñas de desarrollo tomadas del entorno; "Solo datos ficticios" deja de prohibir toda credencial y pasa a exigir que solo haya credenciales de desarrollo provenientes del entorno; la idempotencia cubre a los usuarios.
- `app-configuration`: `.env.example` lista las variables `SEED_*_PASSWORD` con valores ficticios de desarrollo; `JWT_EXPIRE_MINUTES` no positivo es configuración inválida.

## Impact

- **Código nuevo**: `backend/app/domain/usuarios.py` (rol, reglas de alta), `backend/app/application/autenticacion.py` (login, emisión y validación del token), `backend/app/application/usuarios.py` (alta y desactivación), `backend/app/infrastructure/db/models/usuario.py`, `backend/app/infrastructure/db/repositorio_usuarios.py`, `backend/app/infrastructure/security/` (hasher y JWT), `backend/app/api/auth.py` (`POST /auth/login`, dependencias `usuario_actual` y `requiere_rol`), `backend/app/cli/` (comando `usuarios`).
- **Código modificado**: `backend/app/api/turnos.py` (rutas protegidas, `creado_por` desde el usuario), `backend/app/application/crear_turno.py` y `repositorio_turnos.py` (autor del turno), `backend/app/infrastructure/db/models/turno.py` (FK de `creado_por`), `backend/app/infrastructure/db/seed.py` (usuarios), `backend/app/main.py` (router de auth y manejadores), `backend/app/config.py` (validación de `JWT_EXPIRE_MINUTES`).
- **Base de datos**: migración `004_usuario.py` (tabla `usuario`, CHECKs, índices, FK `turno.creado_por → usuario.id`), con `downgrade`.
- **Configuración**: `.env.example` con `SEED_RECEPCIONISTA_PASSWORD`, `SEED_ODONTOLOGO_1_PASSWORD`, `SEED_ODONTOLOGO_2_PASSWORD` (valores ficticios de desarrollo).
- **Dependencias**: `PyJWT`, `pwdlib[argon2]`, `fastapi>=0.122` en `backend/pyproject.toml`.
- **Tests**: los tests de API existentes (C-03..C-05) pasan a autenticarse con un fixture que crea una recepcionista real y emite un token real; sus aserciones de `creado_por is None` en la API pasan al id de esa usuaria. Tests nuevos de dominio, hasher, JWT, login, RBAC por endpoint, migración `004`, modelo vs. migración, CLI y seed, todos contra PostgreSQL real.
- **Changes posteriores**: C-07 atribuye la auditoría al usuario autenticado; C-08..C-13 reutilizan `requiere_rol`; C-14 consume `POST /auth/login`.
