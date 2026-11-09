# Arquitectura Propuesta

## Patrones aplicados

| Patrón | Dónde se usa | Por qué |
|--------|--------------|---------|
| Capas / hexagonal liviana | Backend (domain, application, infrastructure) | Aislar reglas de agenda de FastAPI y SQLAlchemy |
| Puerto y adaptador | `NotificationSender` + `MockSender` | WhatsApp Business API queda como adaptador futuro sin tocar el dominio |
| Repositorio | Acceso a turnos, recursos | Testear reglas sin BD |
| Unidad de trabajo / transacción | Crear/reprogramar/cancelar + auditoría + recordatorio | Atomicidad |
| Cola de trabajo | Redis + worker (servicio `worker` de Compose, sin `JWT_SECRET`) | Recordatorios asincrónicos |
| Restricción de integridad en BD | `EXCLUDE USING gist` | Garantía real de no superposición (RN-AG-09) |

## Concurrencia y no superposición (riesgo técnico)
Dos reservas simultáneas pueden pasar ambas la validación en aplicación (condición de carrera "comprobar y luego insertar"). Mitigación obligatoria a nivel de BD:

1. **Principal:** restricción de exclusión de PostgreSQL con `btree_gist` y `tstzrange(inicio, fin, '[)')`, una por profesional, otra por sillón y otra por paciente (RN-AG-14), parciales sobre `estado <> 'cancelado'` (ver DDL en 04). La BD rechaza el segundo INSERT/UPDATE con `exclusion_violation` (SQLSTATE `23P01`), que la API traduce a 409.
2. **Alternativa/complemento:** bloqueo pesimista (`SELECT ... FOR UPDATE` sobre la fila del profesional/sillón, o `pg_advisory_xact_lock` por recurso) dentro de la transacción antes de validar.
3. La validación en aplicación (horario, bloqueo, solape) se mantiene solo para dar mensajes claros, no como garantía. En particular, el pre-chequeo de solape lista **todos** los recursos en conflicto (profesional, sillón, paciente) en el 409; si una carrera lo esquiva, `23P01` se traduce a 409 indicando el recurso deducido de `constraint_name` (DD-21).
4. Pruebas: test de concurrencia que lance N inserciones simultáneas del mismo horario y verifique exactamente 1 éxito.

Nota: las restricciones de exclusión no cubren horario de atención ni bloqueos; esas reglas se validan en aplicación dentro de la misma transacción, con un lock por profesional que serializa las escrituras de franjas y bloqueos con el alta y la reprogramación de turnos (DD-27 k, DD-30), sin triggers: la **Suposición** "o con triggers" quedó resuelta en DD-30. La garantía es de la aplicación, no de la base: un `INSERT` por SQL directo puede violarla ("trigger + lock" como defensa en profundidad está en el backlog de `CHANGES.md`). **Contrato del lock (DD-30)**: quien cree un turno, o lo mueva en el tiempo o de profesional, lee el profesional destino con `FOR SHARE` antes de validar; quien escriba un bloqueo toma `FOR NO KEY UPDATE` sobre el profesional antes de consultar los turnos.

## Estructura de directorios

```
proyecto/
├── docker-compose.yml          # servicios: db, redis, api, worker (python -m app.worker)
├── .env.example
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── worker.py          # proceso del worker de recordatorios (python -m app.worker)
│   │   ├── domain/            # entidades, reglas (intervalos, solapes), puertos
│   │   ├── application/       # casos de uso (crear/reprogramar/cancelar turno)
│   │   ├── infrastructure/
│   │   │   ├── db/            # modelos SQLAlchemy, repositorios, migraciones (lineales NNN_nombre.py, con downgrade; DD-17)
│   │   │   ├── notifications/ # MockSender (futuro WhatsAppSender)
│   │   │   └── queue/         # ColaRedis (sorted set de recordatorios con vencimiento)
│   │   ├── api/               # routers FastAPI, schemas, dependencias de auth
│   │   └── cli/               # comando de alta y desactivación de usuarios (DD-16, C-06)
│   └── tests/
├── frontend/
│   └── src/
│       ├── features/          # sesion (claims, guardas, ProveedorSesion; DD-33), agenda, turnos, pacientes, configuración
│       ├── shared/            # api (cliente HTTP y ErrorApi), layout
│       ├── pages/
│       └── test/              # setup y fábricas de fixtures ficticios
├── knowledge-base/
└── openspec/
```

## Seguridad
- **Autenticación:** JWT firmado (secreto por entorno), expiración corta; hash de contraseñas con bcrypt/argon2.
- **Autorización:** RBAC por dependencia de FastAPI (`recepcionista`, `odontologo`); el odontólogo filtrado por su `profesional_id`.
- **Auditoría:** tabla append-only de cambios de turnos (Ley 25.326 / 26.529).
- **Validación de input:** Pydantic en la API; constraints CHECK y de exclusión en BD.
- **Datos:** solo ficticios en repo/seed/tests/capturas; sin datos clínicos en el MVP; recordatorios sin datos clínicos.
- **Secretos:** nunca en el repo; `.env` ignorado, `.env.example` versionado.
- **Transporte:** HTTPS en despliegue; CORS restringido.
- **Tiempo:** persistencia en UTC (`timestamptz`), presentación en `America/Argentina/Buenos_Aires`.

## Variables de entorno

| Variable | Descripción | Ejemplo | Sensible |
|----------|-------------|---------|----------|
| `DATABASE_URL` | Conexión PostgreSQL | `postgresql+psycopg://user:pass@db:5432/turnos` | Sí |
| `REDIS_URL` | Conexión Redis | `redis://redis:6379/0` | No |
| `JWT_SECRET` | Clave de firma | `change-me` (placeholder) | Sí |
| `JWT_EXPIRE_MINUTES` | Vigencia del token | `60` | No |
| `REMINDER_LEAD_HOURS` | Anticipación del recordatorio en horas (DD-13); si el turno se crea con menos, no hay recordatorio | `24` | No |
| `APP_TIMEZONE` | Zona de presentación | `America/Argentina/Buenos_Aires` | No |
| `NOTIFICATION_ADAPTER` | Adaptador activo; el único valor válido hoy es `mock` (un adaptador real exige ampliar el valor y la migración del canal) | `mock` | No |
| `CONSULTORIO_NOMBRE` | Nombre del consultorio que se informa en el recordatorio (RN-NO-04); no puede estar vacío | `Consultorio Odontológico Ejemplo` | No |
| `CORS_ORIGINS` | Orígenes permitidos: lista separada por comas, con espacios opcionales; vacía no permite ningún origen y `*` es inválido (la API no arranca; DD-33 b) | `http://localhost:5173` | No |
| `VITE_API_URL` | URL de la API que usa el navegador (variable pública del frontend; nunca un secreto, y dentro de Compose es `http://localhost:8000`, no `http://api:8000`; DD-33 b) | `http://localhost:8000` | No |
| `TEST_REDIS_URL` | Redis de los tests (solo contrato de la cola); usa una base distinta de `REDIS_URL` para no vaciar la cola de desarrollo | `redis://localhost:6379/15` | No |
