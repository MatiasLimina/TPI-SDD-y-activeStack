# Decisiones y Supuestos

## Decisiones documentadas

### DD-01 — MVP recortado al núcleo de agenda (D.4)
**Decisión**: el MVP cubre solo agenda multiprofesional/multisillón, prestaciones con duración, turnos sin solapamientos, horarios/bloqueos, pacientes básicos, 2 roles JWT y recordatorio mock.
**Contexto**: el MVP "imprescindible" de D.3 incluía odontograma, presupuestos, caja, enlace público y WhatsApp real: demasiado amplio para un primer incremento.
**Alternativas consideradas**: MVP completo de D.3; solo agenda sin recordatorios.
**Justificación**: la agenda (duración por prestación y sillones, "No evidenciado" en casi todos los competidores argentinos) es el vacío real del mercado (C.3) y es alcanzable en el trabajo.
**Trade-offs aceptados**: sin reserva online, odontograma ni cobros; se pierde paridad con estándares de mercado (C.1).

### DD-02 — Garantía de no superposición en la base de datos
**Decisión**: restricciones `EXCLUDE USING gist` con `tstzrange(inicio, fin, '[)')` por profesional y por sillón, parciales sobre turnos no cancelados.
**Contexto**: riesgo técnico de reservas concurrentes (Discovery §10).
**Alternativas consideradas**: solo validación en aplicación; bloqueo pesimista/advisory locks; serializable isolation.
**Justificación**: es declarativa, atómica e inevitable aun con múltiples instancias de la API. Locks quedan como complemento.
**Trade-offs aceptados**: dependencia de PostgreSQL y `btree_gist`; el mapeo del error `23P01` a 409; horario y bloqueos siguen validándose en aplicación.

### DD-03 — Intervalos semiabiertos `[inicio, fin)`
**Decisión**: RN3. **Justificación**: permite turnos contiguos sin falsos conflictos y coincide con `tstzrange '[)'` de PostgreSQL.

### DD-04 — Notificaciones detrás de un puerto con adaptador mock
**Decisión**: `NotificationSender` + `MockSender`; Redis como cola.
**Contexto**: WhatsApp Business API implica acceso, aprobación y costo (riesgo de dependencia); además DentalCore usa sesión QR (frágil) y SMILE/Dentiqa API oficial.
**Justificación**: desacopla el dominio y permite integrar WhatsApp luego sin reescribir.
**Trade-offs**: el MVP no envía mensajes reales, por lo que la hipótesis de reducción de ausentismo no se prueba.

### DD-05 — Dos roles, sin administrador
**Decisión**: la recepcionista también configura profesionales, sillones, prestaciones y horarios. **Justificación**: consultorios de 1-5 profesionales; simplicidad. **Trade-off**: sin separación de funciones admin/operación.

### DD-06 — UTC en almacenamiento, hora de Buenos Aires en presentación
**Decisión**: `timestamptz` UTC; conversión a `America/Argentina/Buenos_Aires` en la presentación.

### DD-07 — Datos ficticios y sin secretos en el repo
**Decisión**: seeds/tests/capturas solo con datos ficticios; `.env.example` versionado. **Justificación**: Ley 25.326 / 26.529 y buenas prácticas.

### DD-08 — Cancelación como estado, no borrado
**Decisión**: el turno cancelado se conserva con `estado = cancelado`. **Justificación**: auditoría y trazabilidad; la restricción parcial lo excluye del solape (RN-AG-07).

### DD-09 — Sillón según la prestación (decisión del equipo, 2026-10-02)
**Decisión**: cada prestación indica si requiere sillón (`requiere_sillon`). Las que lo requieren obligan a asignar uno; las que no (consulta, control) no ocupan sillón. **Alternativas descartadas**: sillón siempre obligatorio (las consultas bloquean sillones sin usarlos y, con menos sillones que profesionales, impiden tratamientos) y sillón siempre opcional (depende de la memoria de la recepcionista y permite olvidar el sillón en un tratamiento real). **Consecuencia**: la restricción de exclusión por sillón ya ignora `sillon_id` nulo; la obligatoriedad se valida en el dominio según la prestación.

### DD-10 — Sin sobreturnos en el MVP (decisión del equipo, 2026-10-02)
**Decisión**: todo solape se rechaza. **Motivo**: D.4 no los incluye; agregan reglas (límite, autorización) que no hacen al núcleo. Bilog los ofrece: quedan como extensión.

### DD-11 — Sin turnos en el pasado (decisión del equipo, 2026-10-02)
**Decisión**: no se crean ni reprograman turnos con inicio anterior a ahora. **Motivo**: el sistema agenda, no registra atenciones históricas.

### DD-12 — Un bloqueo no puede pisar turnos activos (decisión del equipo, 2026-10-02)
**Decisión**: se rechaza con 409 y se informan los turnos afectados. **Alternativas descartadas**: crear el bloqueo y marcar los turnos "a reprogramar" (agrega un estado nuevo) y cancelarlos automáticamente (riesgoso para el paciente si nadie le avisa).

### DD-13 — Recordatorio 24 h antes (decisión del equipo, 2026-10-06)
**Decisión**: el recordatorio se envía 24 h antes del turno (`REMINDER_LEAD_HOURS=24`). Si el turno se crea (o reprograma) con menos de 24 h de anticipación, **no** se programa recordatorio. **Alternativas descartadas**: 48 h (muchos turnos de un consultorio chico se dan con menos de 48 h y quedarían sin aviso) y enviar de inmediato cuando faltan menos de 24 h (el paciente acaba de reservar y suma una rama al worker). **Consecuencia**: RN-NO-03 y US-012 quedan cerrados; el worker no necesita lógica de envío inmediato.

### DD-14 — Sin política de cancelación tardía en el MVP (decisión del equipo, 2026-10-06)
**Decisión**: se puede cancelar hasta el inicio del turno; cancelar un turno ya iniciado o pasado se rechaza con 409. Cobros, marcas y penalidades quedan en el backlog. **Alternativas descartadas**: marca informativa `cancelacion_tardia` (no la consume nadie en el MVP, que no tiene reportes) y rechazo de cancelaciones con menos de N horas (contraproducente: si el paciente avisa, la recepcionista necesita liberar el horario; además genera turnos fantasma). **Consecuencia**: RN-AG-13.

### DD-15 — Duración y grilla de 5 minutos (decisión del equipo, 2026-10-06)
**Decisión**: la duración efectiva del turno debe ser múltiplo de 5 min y ≤ 480 min (además de > 0); el inicio debe estar alineado a 5 min (minutos % 5 == 0, segundos y microsegundos en 0, evaluado en hora local `America/Argentina/Buenos_Aires`). La violación se rechaza con 422. Aplica al crear (C-03), al reprogramar (C-05) y a `Prestacion.duracion_min` en el CRUD de catálogo (C-08, con CHECK en BD); el CHECK `> 0` de C-02 sigue vigente. **Alternativas descartadas**: grilla de 15 min (prestaciones de 20 o 40 min pierden capacidad, contra el diferencial de duración propia) y sin restricción (datos raros y sin tope ante errores de tipeo, como 600 por 60). **Consecuencia**: RN-AG-04 reescrita.

### DD-16 — Alta de usuarios por seed y CLI (decisión del equipo, 2026-10-06)
**Decisión**: los usuarios se crean por seed (usuarios ficticios) y por un comando CLI de alta y desactivación; sin UI ni endpoint. La baja es `activo = false`, nunca borrado, porque la auditoría referencia al usuario. **Alternativas descartadas**: solo seed (empuja credenciales al repo) y endpoint para la recepcionista (amplía el alcance en un dominio CRÍTICO y contradice DD-05, que no tiene rol administrador). **Consecuencia**: resuelve SU-06; el comando se implementa en C-06.

### DD-17 — Versiones mínimas y política de migraciones (decisión del equipo, 2026-10-06)
**Decisión**: Python ≥ 3.13 (ya en `backend/pyproject.toml`), PostgreSQL 16 (ya en `docker-compose.yml`) y Node 22 LTS (a confirmar en C-14). Migraciones Alembic lineales, numeradas `NNN_nombre.py`, una por change y siempre con `downgrade`.

### DD-18 — Tests de concurrencia contra PostgreSQL real (decisión del equipo, 2026-10-06)
**Decisión**: los tests de concurrencia corren siempre contra PostgreSQL real en contenedor (ya es regla dura del proyecto). Hoy no hay CI; si se agrega, levanta un service `postgres:16`.

### DD-19 — Reintentos del adaptador de notificación (decisión del equipo, 2026-10-06)
**Decisión**: 3 intentos con backoff exponencial; agotados, el recordatorio queda en `estado = fallido`. Sin reintento manual en el MVP. **Consecuencia**: precisa los "reintentos acotados" del Flujo 6.

### DD-20 — Sin solape por paciente (decisión del equipo, 2026-10-07)
**Decisión**: un paciente no puede tener dos turnos activos superpuestos, aunque sean con profesionales distintos; mismo criterio semiabierto `[inicio, fin)`, cancelados no cuentan y contiguo es válido. **Alternativas descartadas**: permitirlo (riesgo de doble reserva del mismo paciente en el mismo horario, que la recepción no detectaría a simple vista). **Consecuencia**: RN-AG-14 y una tercera restricción de exclusión `turno_sin_solape_paciente` en BD (se suma a DD-02).

### DD-21 — Contrato de errores al crear turno y `estado` como varchar + CHECK (decisión del equipo, 2026-10-07)
**Decisión**: (a) si la prestación no requiere sillón y el request trae `sillon_id` -> 422; (b) el 409 por solape lista **todos** los recursos en conflicto (profesional, sillón, paciente) mediante un pre-chequeo en la aplicación, y la restricción de BD (SQLSTATE `23P01`) queda como garantía ante carreras, con el recurso deducido de `constraint_name`; (c) una referencia inexistente en el body (profesional, paciente, prestación, sillón) -> 422, igual que un recurso inactivo, y 404 queda solo para recursos del path; (d) `Turno.estado` se persiste como `varchar` + `CHECK (estado IN ('programado','cancelado'))`. **Alternativas descartadas**: ignorar o guardar el sillón sobrante; 409 solo desde la BD (informa un único recurso, el primero que dispare); 404 para referencias del body; enum nativo de PostgreSQL (migraciones más costosas al agregar estados). **Consecuencia**: precisa RN-AG-10 y las excepciones globales de 05; afecta C-03 y, por reuso de las validaciones, C-05.

### DD-22 — Cancelar un turno ya cancelado -> 409, no idempotente (decisión del equipo, 2026-10-11)
**Decisión**: una segunda cancelación del mismo turno se rechaza con `409 turno_ya_cancelado` y no modifica el turno (el motivo original se conserva). Si el turno está cancelado y además es pasado, se informa `turno_ya_cancelado` (el estado se evalúa antes que la hora). **Alternativas descartadas**: cancelación idempotente con 200 (oculta a la recepcionista que el turno ya estaba cancelado y obliga a decidir si el nuevo motivo pisa al anterior, lo que ensucia la auditoría de C-07). **Consecuencia**: resuelve la ambigüedad "409/idempotente" del Flujo 4; afecta C-04.

### DD-23 — Contrato de reprogramar turno (decisión del equipo, 2026-10-14)
**Decisión**: (a) `PATCH /turnos/{id}/reprogramar` es parcial: los campos editables (`inicio`, `profesional_id`, `sillon_id`, `duracion_min`) que no vienen en el request conservan el valor actual del turno, incluida una duración ajustada; para volver a la duración de la prestación hay que informarla; (b) paciente y prestación no se pueden cambiar: si el request trae `paciente_id` o `prestacion_id` -> `422 campo_no_editable` con la lista de campos rechazados y un mensaje dirigido a la recepcionista (cancelar el turno y crear uno nuevo); (c) un turno cancelado no se reprograma -> `409 turno_ya_cancelado`; (d) un turno ya iniciado o pasado no se reprograma -> `409 turno_ya_iniciado`, aunque el nuevo inicio sea futuro; el estado se evalúa antes que la hora, igual que en DD-22. **Alternativas descartadas**: duración omitida vuelve a `Prestacion.duracion_min` (pierde en silencio un ajuste de la recepcionista); ignorar `paciente_id`/`prestacion_id` (mismo antipatrón que el sillón sobrante de DD-21: el cliente cree que cambió algo que no cambió); permitir mover un turno pasado a futuro (mezcla reprogramación con ausentismo, que el MVP no modela, y reescribe la agenda histórica). **Consecuencia**: precisa RN-AG-08 y RN-AG-12 y cierra los huecos de US-005 y el Flujo 3; afecta C-05 y reusa los códigos de C-04.

### DD-24 — Contrato de autenticación y usuarios (decisión del equipo, 2026-10-28)
**Decisión**: (a) `POST /auth/login` con email desconocido, contraseña incorrecta o usuario inactivo -> `401 credenciales_invalidas`, con el mismo estado, el mismo encabezado `WWW-Authenticate: Bearer` y exactamente el mismo cuerpo en los tres casos; cuando el email no existe se verifica la contraseña contra un hash ficticio (dummy) calculado con los mismos parámetros, para que el trabajo y el tiempo de respuesta no revelen qué emails están registrados; (b) en una ruta protegida, token ausente, con esquema distinto de `Bearer`, que no es un JWT, con firma o algoritmo inválidos, vencido, sin `sub` o `exp`, con `sub` que no es un UUID o de un usuario inexistente o desactivado después de emitido el token -> `401 no_autenticado` con `WWW-Authenticate: Bearer`; un usuario autenticado sin el rol requerido -> `403 rol_insuficiente`; el rol que vale es el de la base, que se relee en cada request; (c) el login recibe un body JSON `{email, password}`; (d) el email se normaliza (sin espacios al principio ni al final y en minúsculas) en el login y en el alta, y la base lo garantiza con `CHECK (email = lower(btrim(email)) AND email <> '')` más `UNIQUE`; (e) a lo sumo un usuario activo por profesional, garantizado por un índice único parcial `ON (profesional_id) WHERE activo`; `rol` se persiste como `varchar` + CHECK, mismo criterio que DD-21; (f) `JWT_EXPIRE_MINUTES` debe ser un entero mayor que cero: `0`, un negativo o un valor no numérico son configuración inválida y la aplicación no arranca; si no se define, vale `60`; (g) en un login válido, si el hash guardado fue generado con parámetros distintos de los vigentes, se reemplaza por uno nuevo (`verify_and_update`) en la misma transacción; (h) contrato del CLI `python -m app.cli usuarios alta|desactivar`: la contraseña se toma de `USUARIO_PASSWORD` si está definida y no vacía; definida y vacía se **rechaza** (código distinto de `0`, sin crear usuario); no definida, se pide dos veces por consola sin eco; nunca se acepta como argumento; códigos de salida `0` éxito (incluida la desactivación idempotente), `1` error de dominio con el mensaje en `stderr` y `2` uso inválido (`argparse`); el alta rechaza un profesional inexistente, inactivo o que ya tiene un usuario activo; (i) las contraseñas del seed se leen de `SEED_RECEPCIONISTA_PASSWORD`, `SEED_ODONTOLOGO_1_PASSWORD` y `SEED_ODONTOLOGO_2_PASSWORD` (valores ficticios de desarrollo en `.env.example`; una variable ausente o vacía omite ese usuario); (j) no hay reactivación: un usuario desactivado sigue inactivo y su email queda tomado. Es una limitación aceptada del MVP y queda en el backlog. **Fuera de alcance**: rate limiting del login, registro de eventos de seguridad (intentos fallidos) y validación del largo mínimo de `JWT_SECRET` al arrancar (backlog en `CHANGES.md`). **Alternativas descartadas**: `400` por usuario inactivo, como en el tutorial de FastAPI (revela que la cuenta existe); form-data `OAuth2PasswordRequestForm` (suma `python-multipart` sin beneficio); `citext` o índice único sobre `lower(email)` (con el valor ya normalizado alcanza un `UNIQUE` simple); `USUARIO_PASSWORD` vacía interpretada como "pedir por consola" (en un uso no interactivo enmascara un error de configuración). **Consecuencia**: precisa RN-AU-01, el Flujo 1, DD-16 y la entidad Usuario de 04; afecta C-06, y C-07..C-14 reusan los códigos y la dependencia de rol.

## Supuestos inferidos

### SU-01 — Los recordatorios reducen el ausentismo
**Supuesto**: el recordatorio previo reduce las ausencias. **Origen**: Discovery §10 (cifras de proveedores como DentalCore u Órbita son afirmaciones comerciales). **Riesgo si es falso**: el valor del recordatorio es menor al esperado. **Cómo validar**: medir ausentismo antes/después en piloto (fuera del MVP).

### SU-02 — Las fuentes de competidores pueden estar desactualizadas
**Supuesto**: los datos de competidores son orientativos. **Origen**: informe §7 y C.3 (blogs de proveedores interesados; 9 fuentes verificadas manualmente, centros de ayuda pendientes). **Riesgo**: conclusiones de mercado incorrectas. **Validar**: demos de los 5 competidores prioritarios (D.1).

### SU-03 — "No evidenciado" no equivale a "no existe"
**Supuesto**: duración por prestación y sillones pueden existir en competidores sin estar documentados; el diferencial es "demostrable" más que "exclusivo". **Origen**: nota metodológica (sección B). **Validar**: demos.

### SU-04 — Un turno requiere sillón
**Resuelto** por DD-09 (el sillón depende de la prestación).

### SU-05 — Sin sobreturnos
**Resuelto** por DD-10.

### SU-06 — Alta de usuarios fuera de la UI
**Resuelto** por DD-16.

### SU-07 — Un único consultorio por despliegue
**Supuesto**: monotenant, sin multisede (fuera de alcance).

### SU-08 — Argentina sin horario de verano
**Supuesto**: UTC-3 constante simplifica conversiones. **Validar**: usar zona IANA igualmente (`zoneinfo`) para no depender del supuesto.

### SU-09 — Stack complementario
**Supuesto**: Alembic para migraciones, psycopg como driver, pytest para tests. **Origen**: práctica estándar; no está en las fuentes.
