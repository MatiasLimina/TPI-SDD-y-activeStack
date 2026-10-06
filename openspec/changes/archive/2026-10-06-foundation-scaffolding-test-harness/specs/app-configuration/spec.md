# Spec Delta

## Purpose

Define cómo la aplicación obtiene su configuración (conexiones, secretos, zona horaria) exclusivamente desde variables de entorno, sin secretos versionados (RN-CU-03).

## ADDED Requirements

### Requirement: Configuración leída de variables de entorno
El sistema SHALL leer su configuración desde variables de entorno (opcionalmente cargadas desde un archivo `.env` local): `DATABASE_URL`, `REDIS_URL`, `JWT_SECRET`, `JWT_EXPIRE_MINUTES`, `APP_TIMEZONE`, `NOTIFICATION_ADAPTER` y `CORS_ORIGINS`.

#### Scenario: Valores tomados del entorno
- **WHEN** la aplicación arranca con `DATABASE_URL` y `APP_TIMEZONE=America/Argentina/Buenos_Aires` definidos en el entorno
- **THEN** la configuración efectiva usa exactamente esos valores

#### Scenario: Valores por defecto no sensibles
- **WHEN** la aplicación arranca sin definir `APP_TIMEZONE` ni `JWT_EXPIRE_MINUTES`
- **THEN** la configuración usa `America/Argentina/Buenos_Aires` y `60` respectivamente

### Requirement: Fallo explícito ante configuración obligatoria faltante
El sistema MUST negarse a arrancar con un error que nombre la variable cuando falte una variable obligatoria sin valor por defecto (`DATABASE_URL`, `JWT_SECRET`) o cuando un valor sea inválido, en lugar de usar un valor implícito.

#### Scenario: Falta DATABASE_URL
- **WHEN** se carga la configuración sin `DATABASE_URL` en el entorno ni en `.env`
- **THEN** la carga falla con un error de validación que menciona `DATABASE_URL`

#### Scenario: Zona horaria inválida
- **WHEN** se carga la configuración con `APP_TIMEZONE=Mars/Olympus`
- **THEN** la carga falla con un error de validación que menciona `APP_TIMEZONE`

### Requirement: Plantilla de entorno versionada sin secretos
El repositorio SHALL incluir un `.env.example` versionado que liste todas las variables de configuración con valores de ejemplo no sensibles (placeholders), y el archivo `.env` MUST estar excluido del control de versiones.

#### Scenario: .env ignorado y .env.example versionado
- **WHEN** se consulta a git si `.env` y `.env.example` están ignorados
- **THEN** `.env` está ignorado y `.env.example` no lo está

#### Scenario: Placeholders en lugar de secretos
- **WHEN** se inspecciona `.env.example`
- **THEN** `JWT_SECRET` tiene un valor placeholder evidente (por ejemplo `change-me`) y no hay credenciales reales
