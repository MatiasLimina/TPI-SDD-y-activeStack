# app-configuration Specification

## Purpose

Define cómo la aplicación obtiene su configuración (conexiones, secretos, zona horaria) exclusivamente desde variables de entorno, sin secretos versionados (RN-CU-03).

## Requirements


### Requirement: Configuración leída de variables de entorno
El sistema SHALL leer su configuración desde variables de entorno (opcionalmente cargadas desde un archivo `.env` local): `DATABASE_URL`, `REDIS_URL`, `JWT_SECRET`, `JWT_EXPIRE_MINUTES`, `APP_TIMEZONE`, `NOTIFICATION_ADAPTER` y `CORS_ORIGINS`.

#### Scenario: Valores tomados del entorno
- **WHEN** la aplicación arranca con `DATABASE_URL` y `APP_TIMEZONE=America/Argentina/Buenos_Aires` definidos en el entorno
- **THEN** la configuración efectiva usa exactamente esos valores

#### Scenario: Valores por defecto no sensibles
- **WHEN** la aplicación arranca sin definir `APP_TIMEZONE` ni `JWT_EXPIRE_MINUTES`
- **THEN** la configuración usa `America/Argentina/Buenos_Aires` y `60` respectivamente

### Requirement: Fallo explícito ante configuración obligatoria faltante
El sistema MUST negarse a arrancar con un error que nombre la variable cuando falte una variable obligatoria sin valor por defecto (`DATABASE_URL`, `JWT_SECRET`) o cuando un valor sea inválido, en lugar de usar un valor implícito. `JWT_EXPIRE_MINUTES` MUST ser un entero mayor que cero; un valor no numérico también es inválido (DD-24).

#### Scenario: Falta DATABASE_URL
- **WHEN** se carga la configuración sin `DATABASE_URL` en el entorno ni en `.env`
- **THEN** la carga falla con un error de validación que menciona `DATABASE_URL`

#### Scenario: Zona horaria inválida
- **WHEN** se carga la configuración con `APP_TIMEZONE=Mars/Olympus`
- **THEN** la carga falla con un error de validación que menciona `APP_TIMEZONE`

#### Scenario: Falta JWT_SECRET
- **WHEN** se carga la configuración sin `JWT_SECRET` en el entorno ni en `.env`
- **THEN** la carga falla con un error de validación que menciona `JWT_SECRET`

#### Scenario: Vigencia del token no positiva
- **WHEN** se carga la configuración con `JWT_EXPIRE_MINUTES=0`, o con `JWT_EXPIRE_MINUTES=-5`
- **THEN** la carga falla en ambos casos con un error de validación que menciona `JWT_EXPIRE_MINUTES`

#### Scenario: Vigencia del token no numérica
- **WHEN** se carga la configuración con `JWT_EXPIRE_MINUTES=abc`
- **THEN** la carga falla con un error de validación que menciona `JWT_EXPIRE_MINUTES`

#### Scenario: Vigencia mínima aceptada
- **WHEN** se carga la configuración con `JWT_EXPIRE_MINUTES=1`
- **THEN** la configuración efectiva usa `1`

### Requirement: Plantilla de entorno versionada sin secretos
El repositorio SHALL incluir un `.env.example` versionado que liste todas las variables de configuración con valores de ejemplo no sensibles (placeholders), y el archivo `.env` MUST estar excluido del control de versiones. `.env.example` MUST listar también las contraseñas de desarrollo del seed (`SEED_RECEPCIONISTA_PASSWORD`, `SEED_ODONTOLOGO_1_PASSWORD`, `SEED_ODONTOLOGO_2_PASSWORD`) con valores ficticios, evidentes y no productivos.

#### Scenario: .env ignorado y .env.example versionado
- **WHEN** se consulta a git si `.env` y `.env.example` están ignorados
- **THEN** `.env` está ignorado y `.env.example` no lo está

#### Scenario: Placeholders en lugar de secretos
- **WHEN** se inspecciona `.env.example`
- **THEN** `JWT_SECRET` tiene un valor placeholder evidente (por ejemplo `change-me`) y no hay credenciales reales

#### Scenario: Contraseñas de desarrollo del seed
- **WHEN** se inspecciona `.env.example`
- **THEN** declara `SEED_RECEPCIONISTA_PASSWORD`, `SEED_ODONTOLOGO_1_PASSWORD` y `SEED_ODONTOLOGO_2_PASSWORD`, cada una con un valor no vacío que la identifica como contraseña ficticia de desarrollo

#### Scenario: Contraseña del comando CLI fuera de la plantilla
- **WHEN** se inspecciona `.env.example`
- **THEN** no declara `USUARIO_PASSWORD`, que solo se define al invocar el comando de alta
