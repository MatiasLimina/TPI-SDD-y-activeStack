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

| Prioridad | Pregunta | Bloquea | Decisor |
|-----------|----------|---------|---------|
| Alta | ¿Con cuánta **anticipación** se envía el recordatorio (24 h, 48 h)? Parametrizado en `REMINDER_LEAD_HOURS` | Worker de recordatorios | Producto |
| Alta | ¿**Anticipación mínima para cancelar** y tratamiento de la cancelación tardía (cobro, marca, bloqueo)? Hoy sin política | Flujo de cancelación | Producto |
| Media | ¿Duración mínima/máxima o múltiplos (granularidad de la grilla, p. ej. 15 min)? | Agenda UI y RN-AG-04 | Producto |
| Media | ¿Quién crea/da de baja usuarios (seed/CLI vs UI)? (SU-06) | Auth | Equipo técnico |
| Media | Versiones mínimas del stack (Python, PostgreSQL, Node) y política de migraciones | Setup | Equipo técnico |
| Media | ¿Cómo se realizan los tests de concurrencia en CI (PostgreSQL real vs mock)? | Calidad | Equipo técnico |
| Baja | ¿Cuáles son los datos mínimos del paciente (documento, teléfono, email)? | Modelo | Producto |
| Baja | ¿Reintentos y política de fallo del adaptador de notificación? | Worker | Equipo técnico |

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
- [DISCOVERY] `system_type` se infirmó como `web_app` (SPA + API REST); no figura en las fuentes de forma explícita. Confirmar.
- [DISCOVERY] `scale` se infirmó como `team` (1-5 profesionales, un consultorio por despliegue) a partir de `usuarios` y del segmento objetivo; confirmar que no habrá multitenant.
- [DISCOVERY] `domain`: `dental_scheduling` (dato de Discovery; sin discrepancia).
- Sin discrepancias entre `discovery` del estado y `docs/discovery/discovery.md`.

## Preguntas resueltas (2026-10-02)

| Pregunta | Resolución |
|---|---|
| ¿Se permiten **sobreturnos**? ¿Con qué límite y quién los autoriza? (hoy: no, RN-AG-11) | Resuelta: no en el MVP (DD-10, RN-AG-11) |
| ¿Un turno puede **no requerir sillón** (p. ej. consulta)? Hoy sillón obligatorio (RN-AG-10, SU-04); el DDL ya tolera `sillon_id` nulo | Resuelta: depende de la prestación (DD-09, RN-AG-10) |
| ¿Crear un bloqueo sobre turnos existentes se rechaza o los afecta? (RN-HB-03) | Resuelta: se rechaza con 409 (DD-12, RN-HB-03) |
| ¿Se permiten turnos en el pasado o retroactivos (carga de lo ya atendido)? (RN-AG-12) | Resuelta: no (DD-11, RN-AG-12) |
