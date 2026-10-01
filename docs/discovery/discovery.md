# Discovery — Sistema de turnos y agenda para consultorios odontológicos

**Fecha**: 2026-10-01
**Fuentes investigadas**: 17 sistemas (ver `docs/discovery/informe-discovery.md` y `docs/discovery/sources/`)
**Consigna de investigación**: `docs/discovery/consigna-investigacion.md`

> Resultado estructurado de `discovery-research` (checklist de 11 puntos). El
> informe de mercado completo (secciones A-D) está en `informe-discovery.md`;
> este documento resume las decisiones de producto tomadas a partir de él.

## 1. Problema que resuelve

Los consultorios odontológicos chicos de Argentina (1 a 5 profesionales, 1 a 4
sillones) llevan la agenda en papel, planillas o WhatsApp manual. Eso genera
turnos superpuestos entre profesionales y sillones, y ausentismo de pacientes
que no avisan.

## 2. Usuarios / roles

- **Recepcionista / secretaria**: da, reprograma y cancela turnos de todos los
  profesionales. Además configura profesionales, sillones, prestaciones y
  horarios.
- **Odontólogo**: consulta su agenda y bloquea horarios propios.

Fuera del MVP: rol administrador separado y autogestión del paciente.

## 3. Casos de uso

1. Como recepcionista, quiero crear un turno con prestación, profesional y
   sillón sin solapamientos, para evitar dobles reservas.
2. Como recepcionista, quiero reprogramar un turno con la misma validación,
   para mantener la agenda consistente.
3. Como recepcionista, quiero cancelar un turno y liberar el horario, para que
   pueda reutilizarse.
4. Como odontólogo, quiero ver mi agenda diaria o semanal y bloquear franjas,
   para que no me asignen turnos cuando no atiendo.
5. Como sistema, quiero generar un recordatorio previo a cada turno, para
   reducir el ausentismo.

## 4. Competidores / soluciones existentes

Se relevaron 17 sistemas. Ranking completo, matriz ponderada y análisis en
`informe-discovery.md` (secciones A-C).

| Competidor | País | Puntaje ponderado | Nota |
|---|---|---|---|
| DentalCore | Argentina | 4,35 | El más completo en lo evidenciado (ARCA, Mercado Pago, FHIR); puntúa alto en parte porque es el mejor documentado. |
| Dentiqa | No evidenciado (LatAm) | 3,55 | Fuerte en clínica, WhatsApp por API oficial. |
| ClinIA | Argentina | 3,30 | Integraciones públicas (AFIP, PUCO, FHIR). |
| Bilog | Argentina | 3,30 | Mayor base declarada en Argentina. Sus videos oficiales muestran agenda online con autogestión del paciente, lista de espera, sobreturnos y liquidación a obras sociales (subió de 2,65 tras la verificación manual). |
| DentalBox | No evidenciado (multipaís) | 3,25 | Buena cobertura de agenda y seguridad. |

Competidores prioritarios para demo: DentalTec, Bilog, DentalCore, Odonthia,
Dentalink (sección D.1 del informe). Referencia de UX de agenda: Simples Dental
(3,20).

**Vacío principal detectado**: duración por prestación y gestión de sillones
figuran como "No evidenciado" en casi todos los productos argentinos, incluso
en los tutoriales oficiales de Bilog. La autogestión del paciente (cancelar y
reprogramar) sí existe en Bilog vía agenda online web, por lo que no es un
vacío del mercado sino un estándar emergente. El MVP ataca el primer vacío.

## 5. Funcionalidades necesarias (MVP)

- Agenda diaria y semanal con múltiples profesionales y múltiples sillones.
- Catálogo de prestaciones con duración por defecto.
- Crear, reprogramar y cancelar turnos sin solapamientos.
- Horarios de atención por profesional y bloqueos de agenda.
- Registro básico de pacientes (solo con datos ficticios en el repositorio).
- Autenticación JWT con dos roles (recepcionista, odontólogo).
- Recordatorio previo al turno mediante una abstracción de envío, con un
  adaptador simulado (mock).

## 6. Funcionalidades opcionales (etapas posteriores)

- Enlace público de reserva y autogestión del paciente (cancelar o
  reprogramar desde WhatsApp).
- Integración real con WhatsApp Business API.
- Lista de espera con oferta automática del hueco liberado.
- Sobreturnos controlados.
- Seña por Mercado Pago asociada al turno.
- Ficha clínica, anamnesis y odontograma.
- Presupuestos, caja, facturación ARCA y obras sociales/prepagas.
- Panel de ausentismo y ocupación de sillones.
- Multisede.

Decisión consciente: se recortó el MVP "imprescindible" del informe (que
incluía ficha con odontograma, presupuestos, caja y enlace de reserva) para
concentrarse en el núcleo de agenda, que es el vacío real del mercado y el
alcance alcanzable en el trabajo. Registrado en `informe-discovery.md`, D.4.

## 7. Reglas de negocio

- **RN1**: un profesional no puede tener dos turnos superpuestos.
- **RN2**: un sillón no puede tener dos turnos superpuestos.
- **RN3**: los intervalos son semiabiertos `[inicio, fin)`; un turno que
  empieza exactamente cuando termina otro es válido.
- **RN4**: la duración del turno es por defecto la de la prestación; la
  recepcionista puede ajustarla al crearlo.
- **RN5**: no se dan turnos fuera del horario de atención del profesional ni
  dentro de un bloqueo.
- **RN6**: un turno cancelado libera el horario y deja de contar para la
  validación de solapamientos.

## 8. Integraciones

- Recordatorios: puerto de notificación con adaptador mock en el MVP;
  WhatsApp Business API como adaptador futuro.
- Redis como cola para el procesamiento asincrónico de recordatorios.
- Sin integraciones externas obligatorias en el MVP.

## 9. Restricciones

- **Stack**: backend Python + FastAPI, SQLAlchemy, PostgreSQL, Redis, JWT,
  Docker / Docker Compose; frontend React + TypeScript + Vite.
- **Datos de salud** (Ley 25.326 de Protección de Datos Personales y Ley
  26.529 de Derechos del Paciente): control de acceso por rol y registro de
  auditoría de cambios en turnos.
- **Solo datos ficticios**: nunca datos reales de pacientes en el repositorio,
  ejemplos, tests ni capturas.
- **Sin secretos en el repositorio**: claves por variables de entorno, con
  `.env.example` versionado.
- **Zona horaria**: horarios persistidos en UTC y presentados en
  `America/Argentina/Buenos_Aires`.

## 10. Riesgos

- **Supuesto sin probar**: que los recordatorios reduzcan el ausentismo. Las
  cifras publicadas por proveedores son afirmaciones comerciales.
- **Riesgo de información**: precios y funcionalidades de competidores pueden
  estar desactualizados o mal citados; varios provienen de blogs de los
  propios proveedores. Mitigación: verificación personal de fuentes (sección
  7 del informe).
- **Riesgo técnico**: dos reservas concurrentes sobre el mismo horario. La
  prevención de solapamientos necesita una garantía a nivel de base de datos
  (restricción de exclusión o bloqueo), no solo validación en la aplicación.
- **Riesgo de dependencia**: acceso, aprobación y costo de WhatsApp Business
  API; por eso queda detrás de una abstracción.
- **Riesgo de alcance**: tendencia a crecer hacia un sistema clínico completo.

## 11. Preguntas abiertas

- ¿Se permiten sobreturnos? ¿Con qué límite y quién los autoriza?
- ¿Con cuánta anticipación se envía el recordatorio (24 h, 48 h)?
- ¿Hace falta una anticipación mínima para cancelar, y qué pasa con la
  cancelación tardía?
- ¿Un turno puede no requerir sillón (por ejemplo, una consulta)?
- Todo lo que el informe dejó como "No evidenciado": precios en pesos, alcance
  real de ARCA, WhatsApp por API oficial frente a sesión por QR, duración por
  prestación en competidores.
- Verificar centros de ayuda (ya se verificaron 9 fuentes, incluidos videos oficiales: ver sección 7 del informe).
