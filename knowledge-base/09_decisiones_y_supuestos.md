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
