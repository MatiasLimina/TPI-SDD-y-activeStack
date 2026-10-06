# Arquitectura Propuesta

## Patrones aplicados

| Patrón | Dónde se usa | Por qué |
|--------|--------------|---------|
| Capas / hexagonal liviana | Backend (domain, application, infrastructure) | Aislar reglas de agenda de FastAPI y SQLAlchemy |
| Puerto y adaptador | `NotificationSender` + `MockSender` | WhatsApp Business API queda como adaptador futuro sin tocar el dominio |
| Repositorio | Acceso a turnos, recursos | Testear reglas sin BD |
| Unidad de trabajo / transacción | Crear/reprogramar/cancelar + auditoría + recordatorio | Atomicidad |
| Cola de trabajo | Redis + worker | Recordatorios asincrónicos |
| Restricción de integridad en BD | `EXCLUDE USING gist` | Garantía real de no superposición (RN-AG-09) |

## Concurrencia y no superposición (riesgo técnico)
Dos reservas simultáneas pueden pasar ambas la validación en aplicación (condición de carrera "comprobar y luego insertar"). Mitigación obligatoria a nivel de BD:

1. **Principal:** restricción de exclusión de PostgreSQL con `btree_gist` y `tstzrange(inicio, fin, '[)')`, una por profesional y otra por sillón, parciales sobre `estado <> 'cancelado'` (ver DDL en 04). La BD rechaza el segundo INSERT/UPDATE con `exclusion_violation` (SQLSTATE `23P01`), que la API traduce a 409.
2. **Alternativa/complemento:** bloqueo pesimista (`SELECT ... FOR UPDATE` sobre la fila del profesional/sillón, o `pg_advisory_xact_lock` por recurso) dentro de la transacción antes de validar.
3. La validación en aplicación (horario, bloqueo, solape) se mantiene solo para dar mensajes claros, no como garantía.
4. Pruebas: test de concurrencia que lance N inserciones simultáneas del mismo horario y verifique exactamente 1 éxito.

Nota: las restricciones de exclusión no cubren horario de atención ni bloqueos; esas reglas se validan en aplicación dentro de la misma transacción (o con triggers, **Suposición** a decidir).

## Estructura de directorios

```
proyecto/
├── docker-compose.yml
├── .env.example
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── domain/            # entidades, reglas (intervalos, solapes), puertos
│   │   ├── application/       # casos de uso (crear/reprogramar/cancelar turno)
│   │   ├── infrastructure/
│   │   │   ├── db/            # modelos SQLAlchemy, repositorios, migraciones (lineales NNN_nombre.py, con downgrade; DD-17)
│   │   │   ├── notifications/ # MockSender (futuro WhatsAppSender)
│   │   │   └── queue/         # cliente Redis, worker
│   │   ├── api/               # routers FastAPI, schemas, dependencias de auth
│   │   └── cli/               # comando de alta y desactivación de usuarios (DD-16, C-06)
│   └── tests/
├── frontend/
│   └── src/
│       ├── features/          # agenda, turnos, pacientes, configuración
│       ├── shared/
│       └── pages/
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
| `NOTIFICATION_ADAPTER` | Adaptador activo | `mock` | No |
| `CORS_ORIGINS` | Orígenes permitidos | `http://localhost:5173` | No |
