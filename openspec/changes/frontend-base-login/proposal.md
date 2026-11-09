# Proposal

## Why

El backend del MVP está completo para las pantallas que vienen (C-06 autenticación, C-13 agenda), pero no existe ningún frontend: `frontend/` no está en el repo y ni la recepcionista ni el odontólogo pueden usar el sistema (US-010, Flujo 1). C-15 y C-16 construyen las pantallas reales y necesitan antes una base común: proyecto, cliente HTTP con JWT, sesión, guardas por rol y layout.

## What Changes

- **Proyecto `frontend/`** con Vite + React + TypeScript estricto y la estructura `src/features/`, `src/shared/` y `src/pages/` de `08_arquitectura_propuesta.md`, con TDD (Vitest + React Testing Library) y verificación de lint, formato y tipos equivalente a `ruff`.
- **Cliente HTTP** que adjunta el token en cada request (Flujo 1) y unifica las formas de error reales de la API: `{"detail": {"codigo", ...}}`, la lista de `422` de FastAPI, el `detail` de texto y los fallos de red.
- **Página de login** contra `POST /auth/login` y **sesión en el navegador**: el login solo devuelve `access_token` y `token_type`, y no hay ningún endpoint de usuario actual, así que la SPA lee `rol`, `profesional_id` y `exp` de los claims del JWT, solo para decidir qué mostrar (la autorización sigue en el backend, `03_actores_y_roles.md`).
- **Vencimiento de la sesión y `401`**: al llegar `exp`, o ante un `401 no_autenticado` (DD-24), se cierra la sesión y se vuelve al login con un aviso. No hay `POST /auth/refresh` en el backend.
- **Guardas de ruta y layout**: rutas protegidas por sesión y por rol, pantalla de "sin permiso", redirección por rol tras el login y layout con navegación y cierre de sesión. `/agenda` y `/configuracion` son **placeholders**: las pantallas reales son de C-15 y C-16.
- **Servicio `frontend` en Docker Compose**, en el puerto `5173`, que coincide con el valor por defecto de `CORS_ORIGINS`.
- **Cambio de backend (único, a confirmar)**: `CORS_ORIGINS` existe en `config.py` y en `docker-compose.yml`, pero **`main.py` no instala ningún middleware de CORS**, así que hoy la variable no tiene efecto y un navegador en `:5173` no puede leer las respuestas de `:8000`. La recomendación es instalar el middleware: ya está en el alcance de C-14 en `CHANGES.md` y lo pide `08` ("CORS restringido"). La alternativa sin tocar el backend es un proxy de Vite (design D2). **Sin migración**: la cabeza de Alembic sigue en `010`.
- **Node**: se resuelve el "a confirmar en C-14" de DD-17 (design D9).
- **Limpieza pendiente**: la cabecera de DD-32 pasa de "pendiente de revisión de Nico" a "aprobada por Nico" (PR #14 aprobado el 2026-11-09).

Las decisiones que no fija la KB están marcadas **[A confirmar]** en `design.md`, con una opción recomendada. Las tres que más condicionan el resto son cómo conoce el rol la SPA (D1), el CORS (D2) y dónde se guarda el token (D3). El usuario las aprueba antes de `/opsx:apply`.

## Non-goals

- Pantallas reales de agenda, turnos y formularios (C-15) y de configuración, pacientes, bloqueos y auditoría (C-16). Tampoco la presentación de horarios en `America/Argentina/Buenos_Aires`, que llega con C-15.
- Endpoints nuevos en la API: `POST /auth/refresh`, usuario actual (`/auth/me`), cierre de sesión en el servidor o revocación de tokens. Tampoco el token en cookie `httpOnly`.
- Tests de punta a punta contra el backend real y CI: el repo no tiene CI y el alcance no los pide.
- Gestor de estado global, kit de componentes, librería de formularios y librería de JWT.
- Imagen de producción del frontend y servidor con HTTPS.
- Cambios de base de datos.

## Capabilities

### New Capabilities
- `frontend-base`: proyecto del frontend, verificación de tipos, lint y formato, y su servicio en Docker Compose.
- `frontend-cliente-http`: comunicación de la SPA con la API: URL base, token en cada request y normalización de errores.
- `frontend-sesion`: login, datos y conservación de la sesión, vencimiento, guardas por sesión y por rol, redirección por rol y layout.

### Modified Capabilities
- `app-configuration`: `CORS_ORIGINS` pasa a tener efecto real: la API acepta pedidos de navegador solo desde esos orígenes (design D2, [A confirmar]).

## Impact

- **Código nuevo**: `frontend/` completo, con su `Dockerfile` y `package-lock.json`.
- **Backend (a confirmar, D2)**: `backend/app/main.py` y `backend/app/config.py`, con tests. Sin endpoints nuevos ni migración.
- **Infraestructura**: servicio `frontend` en `docker-compose.yml`; `backend/tests/unit/test_docker_compose.py` suma sus verificaciones.
- **Variables de entorno**: `VITE_API_URL` (opcional, no sensible). `.env.example` no se puede leer desde el agente: la tarea indica qué línea agregar.
- **Repo y documentación**: `.gitignore` (`dist/`, `coverage/`), `README.md`, `CLAUDE.md` y `AGENTS.md` (byte-idénticos), `knowledge-base/02`, `07`, `08`, `09` (DD-33 y DD-32) y `10`.
- **Dependencias**: las de `frontend/package.json`, con versiones fijadas en `design.md`.
- **Requisito local**: Node (versión de D9) para correr el frontend fuera de Docker.
