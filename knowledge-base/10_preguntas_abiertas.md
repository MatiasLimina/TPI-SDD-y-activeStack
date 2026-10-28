# Preguntas Abiertas

## Inconsistencias detectadas

### IN-01 — MVP del informe (D.3) vs MVP final (D.4)
**D.3 dice**: imprescindible incluye reserva online por enlace, recordatorio y confirmación por WhatsApp, odontograma, presupuesto, caja, roles administrador/profesional/recepción y exportación de datos.
**D.4 / discovery.md dicen**: solo núcleo de agenda, 2 roles, recordatorio con adaptador mock.
**Impacto**: si se toma D.3 el alcance se infla. **Resolución adoptada**: prevalece D.4 / `discovery.md` (esta KB lo sigue).

### IN-02 — Autogestión del paciente: "vacío" vs "estándar emergente"
**Análisis automatizado inicial**: la daba como ausente en todo el mercado. **Verificación manual (§7)**: Bilog la evidencia (agenda online con cancelar/reprogramar). **Impacto**: no puede venderse como diferencial. **Resolución**: queda fuera del MVP como etapa posterior, no como vacío.

### IN-03 — Roles
**D.3**: administrador, profesional y recepción. **Discovery**: solo recepcionista (que además configura) y odontólogo. **Resolución**: 2 roles.

### IN-04 — Estado de verificación de fuentes
El resumen de §7 del informe decía "siete fuentes comprobadas" mientras la tabla registraba nueve. **Resolución (2026-10-01)**: corregido en el informe; son nueve fuentes, seis coincidentes y tres con errores del agente (Doctoralia Pro, SMILE, Bilog). Se conserva como antecedente de trazabilidad.

## Preguntas abiertas (priorizadas)

Ninguna abierta al 2026-10-07. Las ocho preguntas pendientes se resolvieron (ver "Preguntas resueltas (2026-10-06)" más abajo) y las cinco surgidas al explorar C-03 también (ver "Preguntas resueltas (2026-10-07)").

## Datos de competidores "No evidenciado" (de la investigación)

| Prioridad | Tema | Detalle |
|-----------|------|---------|
| Media | Duración por prestación y sillones en competidores | "No evidenciado" en casi todos (incluidos los tutoriales de Bilog); a contrastar en demos (D.1) |
| Baja | Precios en pesos (ARS) | DentalTec, Bilog, ClinIA, Órbita y Dentalink no publican; el resto publica en USD (excepto Doctoralia Pro, ARS 25.000/35.000/55.000) |
| Baja | Alcance real de la integración ARCA | Evidenciada en DentalCore, DentalTec (con obras sociales) y ClinIA (AFIP/PUCO); alcance no comprobado |
| Media | WhatsApp por API oficial vs sesión QR | SMILE y Dentiqa dicen API oficial; DentalCore usa QR; el resto no evidenciado. Relevante para el adaptador futuro |
| Baja | Doctoralia Pro: período de facturación del plan | Cobro anual con tarjeta según la página; Capterra habla de EUR 69 por usuario por mes; período real no concluyente |
| Baja | Centros de ayuda no verificados | Solo se revisaron 9 fuentes (incl. YouTube de DentalTec y Bilog); centros de ayuda detallados pendientes |
| Baja | Seña vía Mercado Pago ligada al turno | No evidenciada en ningún sistema; solo DentalCore tiene Mercado Pago |
| Baja | Evidencia de cumplimiento Ley 25.326 / 26.529 en competidores | Solo declaraciones, sin certificaciones |

## Incertidumbres de [DISCOVERY] (state.kb.discovery)
- [DISCOVERY] `system_type` se infirmó como `web_app` (SPA + API REST); no figura en las fuentes de forma explícita. **Confirmado** por el equipo (2026-10-06).
- [DISCOVERY] `scale` se infirmó como `team` (1-5 profesionales, un consultorio por despliegue) a partir de `usuarios` y del segmento objetivo. **Confirmado** por el equipo (2026-10-06): monotenant, sin multitenant (SU-07).
- [DISCOVERY] `domain`: `dental_scheduling` (dato de Discovery; sin discrepancia).
- Sin discrepancias entre `discovery` del estado y `docs/discovery/discovery.md`.

## Preguntas resueltas (2026-10-02)

| Pregunta | Resolución |
|---|---|
| ¿Se permiten **sobreturnos**? ¿Con qué límite y quién los autoriza? (hoy: no, RN-AG-11) | Resuelta: no en el MVP (DD-10, RN-AG-11) |
| ¿Un turno puede **no requerir sillón** (p. ej. consulta)? Hoy sillón obligatorio (RN-AG-10, SU-04); el DDL ya tolera `sillon_id` nulo | Resuelta: depende de la prestación (DD-09, RN-AG-10) |
| ¿Crear un bloqueo sobre turnos existentes se rechaza o los afecta? (RN-HB-03) | Resuelta: se rechaza con 409 (DD-12, RN-HB-03) |
| ¿Se permiten turnos en el pasado o retroactivos (carga de lo ya atendido)? (RN-AG-12) | Resuelta: no (DD-11, RN-AG-12) |

## Preguntas resueltas (2026-10-06)

| Pregunta | Resolución |
|---|---|
| ¿Con cuánta **anticipación** se envía el recordatorio (24 h, 48 h)? | Resuelta: 24 h antes; si el turno se crea con menos de 24 h no se programa recordatorio (DD-13, RN-NO-03) |
| ¿**Anticipación mínima para cancelar** y tratamiento de la cancelación tardía? | Resuelta: sin política de cancelación tardía; se cancela hasta el inicio del turno, iniciado o pasado -> 409 (DD-14, RN-AG-13) |
| ¿Duración mínima/máxima o múltiplos (granularidad de la grilla)? | Resuelta: múltiplo de 5 min, máximo 480 min, inicio alineado a 5 min; violación -> 422 (DD-15, RN-AG-04) |
| ¿Quién crea/da de baja usuarios (seed/CLI vs UI)? (SU-06) | Resuelta: seed más comando CLI de alta y desactivación; sin UI ni endpoint; baja = `activo = false` (DD-16) |
| Versiones mínimas del stack y política de migraciones | Resuelta: Python ≥ 3.13, PostgreSQL 16, Node 22 LTS; migraciones Alembic lineales con `downgrade` (DD-17) |
| ¿Cómo se realizan los tests de concurrencia en CI? | Resuelta: siempre contra PostgreSQL real en contenedor; si hay CI, service `postgres:16` (DD-18) |
| ¿Cuáles son los datos mínimos del paciente? | Resuelta con lo ya modelado: nombre, apellido, documento único, teléfono obligatorio, email opcional (ver 04, entidad Paciente); no requirió DD |
| ¿Reintentos y política de fallo del adaptador de notificación? | Resuelta: 3 intentos con backoff exponencial; agotados, `fallido`; sin reintento manual (DD-19, RN-NO-05) |

## Preguntas resueltas (2026-10-07)

| Pregunta | Resolución |
|---|---|
| ¿Un **paciente** puede tener dos turnos superpuestos con profesionales distintos? | Resuelta: no; sin solape por paciente, con tercera restricción de exclusión en BD (DD-20, RN-AG-14) |
| ¿Qué pasa si el request trae `sillon_id` y la prestación **no requiere sillón**? | Resuelta: 422; no se ignora ni se guarda (DD-21, RN-AG-10) |
| ¿Qué recurso informa el 409 por solape? | Resuelta: todos los recursos en conflicto (pre-chequeo en la aplicación) y, ante carreras, el deducido de `constraint_name` del `23P01` (DD-21) |
| ¿Un ID inexistente en el body (profesional, paciente, prestación, sillón) da 404 o 422? | Resuelta: 422, igual que un recurso inactivo; 404 solo para recursos del path (DD-21) |
| ¿Qué tipo tiene `Turno.estado`: enum nativo o texto? | Resuelta: `varchar` + `CHECK (estado IN ('programado','cancelado'))` (DD-21) |

## Preguntas resueltas (2026-10-11)

| Pregunta | Resolución |
|---|---|
| ¿Cancelar un turno **ya cancelado** da 409 o es idempotente? | Resuelta: 409 `turno_ya_cancelado`, sin modificar el turno ni su motivo (DD-22) |

## Preguntas resueltas (2026-10-14)

| Pregunta | Resolución |
|---|---|
| Al reprogramar, ¿un campo omitido conserva su valor o vuelve al default (duración de la prestación)? | Resuelta: conserva el valor actual, incluida la duración ajustada (DD-23) |
| ¿Se puede cambiar el paciente o la prestación al reprogramar? | Resuelta: no; 422 `campo_no_editable` con mensaje para la recepcionista (DD-23) |
| ¿Se puede reprogramar un turno cancelado o ya iniciado/pasado? | Resuelta: no; 409 `turno_ya_cancelado` / `turno_ya_iniciado`, estado antes que hora (DD-23) |

## Preguntas resueltas (2026-10-28)

| Pregunta | Resolución |
|---|---|
| ¿Qué responde el login ante email desconocido, contraseña incorrecta o usuario inactivo? | Resuelta: el mismo `401 credenciales_invalidas` en los tres casos, con verificación contra un hash ficticio cuando el email no existe (DD-24) |
| ¿Qué responde una ruta protegida ante token ausente, mal formado, inválido o vencido, o usuario desactivado? ¿Y sin el rol? | Resuelta: `401 no_autenticado` con `WWW-Authenticate: Bearer`; sin el rol, `403 rol_insuficiente` (DD-24) |
| ¿El email del usuario distingue mayúsculas? | Resuelta: no; se normaliza en el login y en el alta, y la base lo garantiza con CHECK + `UNIQUE` (DD-24) |
| ¿Un profesional puede tener más de un usuario activo? | Resuelta: no; índice único parcial por profesional sobre los activos (DD-24) |
| ¿`JWT_EXPIRE_MINUTES` en `0` o negativo es válido? | Resuelta: no; entero mayor que cero, default `60` (DD-24) |
| ¿Cómo recibe la contraseña el CLI de alta y qué pasa si `USUARIO_PASSWORD` está definida pero vacía? | Resuelta: de `USUARIO_PASSWORD` si está definida y no vacía, o por doble prompt sin eco; definida y vacía se rechaza sin crear el usuario (DD-24) |
| ¿Se puede reactivar un usuario desactivado o volver a dar de alta su email? | Resuelta: no en el MVP; limitación registrada en el backlog (DD-24) |
