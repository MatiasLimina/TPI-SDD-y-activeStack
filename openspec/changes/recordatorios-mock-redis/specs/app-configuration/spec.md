# Spec Delta

## MODIFIED Requirements

### Requirement: Configuración leída de variables de entorno
El sistema SHALL leer su configuración desde variables de entorno (opcionalmente cargadas desde un archivo `.env` local): `DATABASE_URL`, `REDIS_URL`, `JWT_SECRET`, `JWT_EXPIRE_MINUTES`, `APP_TIMEZONE`, `NOTIFICATION_ADAPTER`, `CORS_ORIGINS`, `REMINDER_LEAD_HOURS` y `CONSULTORIO_NOMBRE`.

#### Scenario: Valores tomados del entorno
- **WHEN** la aplicación arranca con `DATABASE_URL` y `APP_TIMEZONE=America/Argentina/Buenos_Aires` definidos en el entorno
- **THEN** la configuración efectiva usa exactamente esos valores

#### Scenario: Valores por defecto no sensibles
- **WHEN** la aplicación arranca sin definir `APP_TIMEZONE` ni `JWT_EXPIRE_MINUTES`
- **THEN** la configuración usa `America/Argentina/Buenos_Aires` y `60` respectivamente

#### Scenario: Valores por defecto de los recordatorios
- **WHEN** la aplicación arranca sin definir `REMINDER_LEAD_HOURS`, `NOTIFICATION_ADAPTER` ni `CONSULTORIO_NOMBRE`
- **THEN** la configuración usa `24`, `mock` y `Consultorio odontológico` respectivamente

#### Scenario: Anticipación y consultorio tomados del entorno
- **WHEN** la aplicación arranca con `REMINDER_LEAD_HOURS=48` y `CONSULTORIO_NOMBRE=Consultorio Odontológico Ejemplo` en el entorno
- **THEN** la configuración efectiva usa `48` y `Consultorio Odontológico Ejemplo`

### Requirement: Fallo explícito ante configuración obligatoria faltante
El sistema MUST negarse a arrancar con un error que nombre la variable cuando falte una variable obligatoria sin valor por defecto (`DATABASE_URL`, `JWT_SECRET`) o cuando un valor sea inválido, en lugar de usar un valor implícito. `JWT_EXPIRE_MINUTES` MUST ser un entero mayor que cero; un valor no numérico también es inválido (DD-24 (f)). `REMINDER_LEAD_HOURS` MUST ser un entero mayor que cero, con el mismo criterio (design D16, a registrar en DD-28). `NOTIFICATION_ADAPTER` MUST valer `mock`, el único adaptador del MVP (DD-04; design D13), y `CONSULTORIO_NOMBRE` MUST NOT estar vacío ni ser solo espacios (design D16, a registrar en DD-28).

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

#### Scenario: Anticipación del recordatorio inválida
- **WHEN** se carga la configuración con `REMINDER_LEAD_HOURS=0`, con `REMINDER_LEAD_HOURS=-24` o con `REMINDER_LEAD_HOURS=un-dia`
- **THEN** la carga falla en los tres casos con un error de validación que menciona `REMINDER_LEAD_HOURS`

#### Scenario: Anticipación mínima aceptada
- **WHEN** se carga la configuración con `REMINDER_LEAD_HOURS=1`
- **THEN** la configuración efectiva usa `1`

#### Scenario: Adaptador de notificación desconocido
- **WHEN** se carga la configuración con `NOTIFICATION_ADAPTER=whatsapp`
- **THEN** la carga falla con un error de validación que menciona `NOTIFICATION_ADAPTER`

#### Scenario: Nombre del consultorio vacío
- **WHEN** se carga la configuración con `CONSULTORIO_NOMBRE` vacío o con `CONSULTORIO_NOMBRE` formado solo por espacios
- **THEN** la carga falla en ambos casos con un error de validación que menciona `CONSULTORIO_NOMBRE`

## ADDED Requirements

### Requirement: Variables de recordatorios en la plantilla de entorno
`.env.example` MUST declarar `REMINDER_LEAD_HOURS`, `NOTIFICATION_ADAPTER` y `CONSULTORIO_NOMBRE` con valores de ejemplo no sensibles, y `TEST_REDIS_URL`, la conexión al Redis de tests, apuntando a una base de Redis distinta de la de `REDIS_URL` para que los tests no vacíen la cola de desarrollo.

#### Scenario: Variables de recordatorios en la plantilla
- **WHEN** se inspecciona `.env.example`
- **THEN** declara `REMINDER_LEAD_HOURS=24`, `NOTIFICATION_ADAPTER=mock` y `CONSULTORIO_NOMBRE` con un nombre de consultorio ficticio

#### Scenario: Redis de tests separado del de desarrollo
- **WHEN** se inspecciona `.env.example`
- **THEN** declara `TEST_REDIS_URL` y su número de base de Redis es distinto del de `REDIS_URL`
