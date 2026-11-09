# Spec Delta

## Purpose

Define el proyecto del frontend, la verificación mínima que debe pasar antes de dar una tarea por terminada y cómo se levanta junto con el resto del sistema en Docker Compose.

## ADDED Requirements

### Requirement: Proyecto del frontend
El repositorio SHALL incluir en `frontend/` una aplicación web en TypeScript con verificación estricta de tipos, organizada en `src/features/`, `src/shared/` y `src/pages/` (`08_arquitectura_propuesta.md`). El proyecto MUST declarar la versión de Node requerida y MUST instalarse de forma reproducible desde un archivo de bloqueo versionado.

#### Scenario: Compilación de producción
- **GIVEN** dado el proyecto `frontend/` con sus dependencias instaladas desde el archivo de bloqueo
- **WHEN** cuando se ejecuta `npm run build`
- **THEN** entonces el comando termina con código `0` y genera `frontend/dist/`

#### Scenario: Estructura de carpetas
- **WHEN** cuando se inspecciona `frontend/src/`
- **THEN** entonces existen `features/`, `shared/` y `pages/`

#### Scenario: Artefactos fuera del repositorio
- **GIVEN** dado el proyecto instalado y compilado
- **WHEN** cuando se ejecuta `git status`
- **THEN** entonces `frontend/node_modules/` y `frontend/dist/` no aparecen como archivos por agregar

#### Scenario: Versión de Node declarada
- **WHEN** cuando se lee `frontend/package.json`
- **THEN** entonces `engines.node` es `^24.15.0`

#### Scenario: Instalación reproducible
- **GIVEN** dado el repositorio con `frontend/package-lock.json` versionado
- **WHEN** cuando se ejecuta `npm ci` en `frontend/`
- **THEN** entonces el comando termina con código `0`

### Requirement: Verificación antes de dar una tarea por terminada
El proyecto SHALL ofrecer los scripts `typecheck`, `lint`, `format:check` y `test`, equivalentes a `ruff` y `pytest` en el backend. Cada uno MUST terminar con código distinto de `0` si encuentra un problema, y todos MUST estar en verde antes de dar una tarea por terminada.

#### Scenario: Código correcto
- **GIVEN** dado el proyecto sin errores
- **WHEN** cuando se ejecutan `npm run typecheck`, `npm run lint`, `npm run format:check` y `npm test`
- **THEN** entonces los cuatro terminan con código `0`

#### Scenario: Error de tipos
- **GIVEN** dado un archivo de `src/` que asigna un texto a una variable declarada `number`
- **WHEN** cuando se ejecuta `npm run typecheck`
- **THEN** entonces el comando termina con código distinto de `0`

#### Scenario: Error de lint
- **GIVEN** dado un archivo de `src/` que declara una variable y no la usa
- **WHEN** cuando se ejecuta `npm run lint`
- **THEN** entonces el comando termina con código distinto de `0`

#### Scenario: Test que falla
- **GIVEN** dado un test que afirma un valor distinto del obtenido
- **WHEN** cuando se ejecuta `npm test`
- **THEN** entonces el comando termina con código distinto de `0`

#### Scenario: Archivo mal formateado
- **GIVEN** dado un archivo de `src/` que no respeta el formato del proyecto
- **WHEN** cuando se ejecuta `npm run format:check`
- **THEN** entonces el comando termina con código distinto de `0`

### Requirement: Servicio frontend en Docker Compose
`docker-compose.yml` SHALL declarar un servicio `frontend` construido desde `./frontend`, publicado en el puerto `5173` y que arranca después de `api`. Su URL de la API MUST ser configurable por `VITE_API_URL` y MUST valer por defecto una dirección alcanzable desde el navegador (`http://localhost:8000`).

#### Scenario: Servicio declarado
- **WHEN** cuando se lee `docker-compose.yml`
- **THEN** entonces el servicio `frontend` tiene `build: ./frontend`, publica `5173:5173` y depende de `api`

#### Scenario: URL de la API por defecto
- **WHEN** cuando se lee el entorno del servicio `frontend`
- **THEN** entonces `VITE_API_URL` toma por defecto `http://localhost:8000` y no apunta al nombre interno `api`

#### Scenario: La aplicación responde
- **WHEN** cuando se ejecuta `docker compose up --build frontend` y se pide `http://localhost:5173/`
- **THEN** entonces la respuesta es `200` y entrega el HTML de la aplicación

### Requirement: Sin secretos en el frontend
El servicio `frontend` y el código del navegador MUST NOT recibir `JWT_SECRET` ni ninguna otra credencial del backend (RN-CU-03), porque toda variable expuesta al navegador es pública.

#### Scenario: Entorno del servicio
- **WHEN** cuando se lee el entorno del servicio `frontend` en `docker-compose.yml`
- **THEN** entonces no contiene `JWT_SECRET`, `DATABASE_URL` ni `REDIS_URL`

#### Scenario: Servicio sin archivo de entorno
- **WHEN** cuando se lee el servicio `frontend` en `docker-compose.yml`
- **THEN** entonces no declara `env_file`

#### Scenario: Código del navegador
- **GIVEN** dado el proyecto compilado con `npm run build`
- **WHEN** cuando se buscan `JWT_SECRET`, `DATABASE_URL` y `REDIS_URL` en `frontend/src/` y en `frontend/dist/`
- **THEN** entonces ninguno aparece
