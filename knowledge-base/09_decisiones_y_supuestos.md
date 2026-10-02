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
**Supuesto**: usuarios del sistema se crean por seed/CLI en el MVP; las fuentes no prevén gestión de usuarios. **Validar**: con el equipo.

### SU-07 — Un único consultorio por despliegue
**Supuesto**: monotenant, sin multisede (fuera de alcance).

### SU-08 — Argentina sin horario de verano
**Supuesto**: UTC-3 constante simplifica conversiones. **Validar**: usar zona IANA igualmente (`zoneinfo`) para no depender del supuesto.

### SU-09 — Stack complementario
**Supuesto**: Alembic para migraciones, psycopg como driver, pytest para tests. **Origen**: práctica estándar; no está en las fuentes.
