# Visión y Objetivos

> Fuentes: `docs/discovery/discovery.md` (decisiones de producto, prevalece) e `docs/discovery/informe-discovery.md` (mercado, 17 sistemas; secciones C y D.4).

## Propósito del sistema
Sistema web de **turnos y agenda para consultorios odontológicos chicos de Argentina** (1 a 5 profesionales, 1 a 4 sillones/boxes). Reemplaza la agenda en papel, planillas o WhatsApp manual, que genera **turnos superpuestos** entre profesionales y sillones y **ausentismo** de pacientes que no avisan.

**Posicionamiento frente al mercado (Discovery C.3 / C.4).** El mercado argentino ya ofrece como estándar agenda multiprofesional, recordatorios por WhatsApp, odontograma y presupuestos (C.1), por lo que eso no diferencia. El **vacío detectado** es el *núcleo de agenda*: la **duración por prestación** y la **gestión de sillones** figuran como "No evidenciado" en casi todos los productos argentinos relevados (DentalTec, DentalCore, Bilog, Odonthia, ClinIA, Dentalink, etc.), incluso en los tutoriales oficiales de Bilog; solo Simples Dental (Brasil, control de sillas), DentalBox (boxes), Órbita/ClinIA (vista por sillón) y SMILE (duraciones 30/45/60 min, sin solapamientos) lo muestran parcialmente. Este MVP ataca ese vacío: una agenda odontológica **bien resuelta y demostrable** (prestaciones con duración, sillones como recurso, bloqueos y prevención de solapamientos).

Competidores prioritarios para demo (D.1): DentalTec, Bilog, DentalCore, Odonthia, Dentalink. Referencia de UX de agenda (D.2): Simples Dental, SMILE, Doctoralia Pro. Líder en lo evidenciado: DentalCore (4,35), aunque su puntaje refleja "mejor documentado" más que "mejor probado".

## Objetivos por actor

| Actor | Objetivo principal | Objetivos secundarios |
|-------|--------------------|-----------------------|
| Recepcionista | Dar, reprogramar y cancelar turnos de todos los profesionales sin dobles reservas | Configurar profesionales, sillones, prestaciones y horarios; registrar pacientes básicos |
| Odontólogo | Ver su agenda diaria/semanal | Bloquear franjas propias para no recibir turnos cuando no atiende |
| Sistema | Garantizar no superposición por profesional y por sillón | Generar recordatorio previo al turno (reducir ausentismo); auditar cambios de turnos |

## Alcance MVP v0.1 (decisión D.4, 2026-10-01)
El MVP "imprescindible" del informe (D.3) se **recortó** al núcleo de agenda por ser el vacío real del mercado y lo alcanzable en el trabajo:
- Agenda diaria y semanal multiprofesional y multisillón.
- Prestaciones con duración por defecto (ajustable por la recepcionista al crear el turno).
- Crear, reprogramar y cancelar turnos sin solapamientos por profesional ni por sillón, con intervalos semiabiertos `[inicio, fin)`.
- Horarios de atención por profesional y bloqueos de agenda.
- Registro básico de pacientes (solo datos ficticios).
- Autenticación JWT con dos roles (recepcionista, odontólogo) y registro de auditoría de cambios en turnos.
- Recordatorio previo al turno mediante un puerto de notificación con adaptador mock y cola Redis.

## Fuera de alcance
Pasan a *diferenciador* o *etapas posteriores* (D.3 y recortes D.4); **no** se implementan en el MVP:
- Enlace público de reserva y autogestión del paciente (cancelar/reprogramar). Nota: no es un vacío del mercado; Bilog ya lo evidencia vía agenda online web (QR/enlace), por lo que es un estándar emergente.
- Integración real con WhatsApp Business API (queda detrás del puerto de notificación; riesgo de dependencia/costo).
- Lista de espera con oferta automática del hueco liberado (Simples Dental, DentalCore, Bilog).
- Sobreturnos controlados (Bilog los evidencia; en el MVP no se permiten, ver pregunta abierta).
- Seña por Mercado Pago asociada al turno (solo DentalCore tiene Mercado Pago).
- Ficha clínica, anamnesis y odontograma.
- Presupuestos de tratamiento y caja.
- Facturación electrónica ARCA y obras sociales/prepagas.
- Panel de ausentismo y ocupación de sillones.
- Multisede.
- Rol administrador separado y portal/autogestión del paciente.
- Periodontograma, imágenes, consentimientos y firma digital, asistente IA, API pública, app móvil nativa, interoperabilidad HL7 FHIR.

## Métricas de éxito
- 0 turnos superpuestos (por profesional y por sillón) aun bajo reservas concurrentes (verificable con tests de concurrencia).
- Cobertura de las reglas RN-AG-01..RN-AG-10 por escenarios de prueba.
- Recordatorio generado y encolado para todo turno activo dentro de la ventana configurada.
- **Hipótesis sin probar:** que los recordatorios reduzcan el ausentismo; las cifras de proveedores (p. ej. "40 % menos de ausentismo") son afirmaciones comerciales y no se toman como evidencia.
