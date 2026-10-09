## 1. Portada

# Informe de Discovery: sistemas de gestión de turnos y agenda para consultorios odontológicos en Argentina

**Materia:** Metodología I, Tecnicatura Universitaria en Programación
**Integrante:** Matias Limina
**Fecha:** 2026-10-01

---

## 2. Resumen ejecutivo

**Qué se investigó.** Se relevaron 17 sistemas de gestión odontológica o de agenda sanitaria: 7 de origen argentino, 6 de otros países latinoamericanos con presencia o relevancia para Argentina, 1 plataforma de directorio médico con agenda (Doctoralia Pro) y referencias de Brasil y Estados Unidos (Simples Dental, Open Dental). Se consultaron páginas oficiales de cada proveedor y, de forma complementaria, un agregador de terceros (Capterra). Todas las consultas se realizaron el 2026-10-01 y cada hallazgo se clasificó como *Comprobado* (figura en la página oficial), *Afirmación comercial* (cifra o promesa del proveedor sin respaldo verificable) o *No evidenciado*.

**Hallazgos principales.**
- El mercado argentino ya ofrece, en varios productos, el paquete básico: agenda multiprofesional, recordatorios por WhatsApp, odontograma, presupuestos y caja. Eso es estándar y no diferencia.
- La integración local (ARCA, Mercado Pago, obras sociales y prepagas) está evidenciada en muy pocos productos: DentalCore (los tres), DentalTec (ARCA y obras sociales) y ClinIA (AFIP y cobertura vía PUCO). Mercado Pago aparece solo en DentalCore.
- El núcleo de agenda odontológica se evidencia de forma incompleta en casi todos: la **duración por prestación** y la **gestión de sillones** figuran como "No evidenciado" en la gran mayoría, incluso tras revisar videos oficiales. Sobreturnos, lista de espera y autogestión del paciente (cancelar y reprogramar) solo se demostraron en pocos productos: Bilog (en sus tutoriales oficiales), Simples Dental (Brasil) y DentalCore.
- Los precios en pesos casi no se publican; los sistemas con precio visible lo hacen en dólares (USD 19 a 249 por mes según el producto).
- Gran parte de la información comparativa de internet proviene de los propios proveedores (blogs de DentalCore, Odonthia y Turnito); se la tomó solo como pista, no como evidencia.
- Mejor puntuación ponderada (0 a 5): DentalCore 4,35; Dentiqa 3,55; ClinIA y Bilog 3,30 (empate); DentalBox 3,25. Bilog subió de 2,65 a 3,30 al incorporar como evidencia dos videos oficiales en la verificación manual. DentalCore se beneficia de ser el sitio más detallado, por lo que su puntaje debe leerse como "mejor documentado", no como "mejor probado".

**MVP recomendado (síntesis).** Agenda con prestaciones de duración configurable, múltiples profesionales y sillones, prevención de solapamientos, cancelación y reprogramación; reserva online por enlace; recordatorios y confirmación por WhatsApp; ficha clínica con odontograma; presupuestos; caja básica con seña por Mercado Pago. Diferenciadores: lista de espera con relleno automático de huecos y reprogramación en un paso. Se difieren la facturación ARCA completa, la liquidación a obras sociales, el periodontograma, la IA conversacional y el multisede.

---

## 3. A. Tabla comparativa

Convenciones: **Comprobado (...)** = figura en la página oficial consultada; **Afirmación comercial** = promesa o cifra del proveedor sin evidencia verificable; **No evidenciado** = no figura en las fuentes consultadas (no se completa por deducción). Todas las fuentes se consultaron el **2026-10-01**. Las tablas A.1 a A.5 conservan el mismo orden de filas: ordenados por relevancia para Argentina (origen o presencia local, integraciones argentinas evidenciadas y especificidad odontológica).

### A.1 Identificación, segmento y modalidad

| # | Producto | Proveedor | País | URL oficial | Consulta | Segmento | Modalidad |
|---|----------|-----------|------|-------------|----------|----------|-----------|
| 1 | DentalTec | DentalTec (razón social no evidenciada) | Argentina | https://web.dentaltec.com.ar/ | 2026-10-01 | No evidenciado (se presenta como gestión odontológica) | Comprobado (100 % web/nube) |
| 2 | DentalCore | DentalCore (fundador Od. A. Di Tullio) | Argentina | https://dentalcore.app/ | 2026-10-01 | Comprobado (consultorios y clínicas, de individual a multisede) | Comprobado (SaaS en nube) |
| 3 | Bilog | Bilog (razón social no evidenciada) | Argentina | https://bilog.com.ar/ | 2026-10-01 | Comprobado (clínicas, consultorios individuales, universidades) | Comprobado (SaaS web y app móvil) |
| 4 | Odonthia | Odonthia (razón social no evidenciada) | Argentina | https://odonthia.com/ | 2026-10-01 | Comprobado (odontólogos) | Comprobado (web, sin instalación) |
| 5 | ClinIA (OdontoClinIA) | Emprinet | Argentina | https://www.clinia.com.ar/odontologia | 2026-10-01 | Comprobado (consultorios, clínicas pyme, centros municipales, hospitales públicos, cadenas) | Comprobado (SaaS web) |
| 6 | Órbita | Órbita Global | Argentina (La Plata) | https://hiorbita.com/ | 2026-10-01 | Comprobado (clínicas odontológicas y centros médicos) | Comprobado (nube + app iPhone) |
| 7 | OdontoApp | No evidenciado | Argentina | https://odontoapp.com.ar/ | 2026-10-01 | Comprobado (odontólogos y consultorios) | No evidenciado (se la describe como plataforma digital) |
| 8 | Dentalink | Healthatom | Chile (opera en Argentina) | https://www.softwaredentalink.com/?c=cl | 2026-10-01 | Comprobado (clínicas y consultorios) | Comprobado (nube) |
| 9 | Doctoralia Pro (agenda) | Docplanner Group | Polonia; sitio para Argentina | https://pro.doctoralia.com/ar/agenda-doctoralia-para-especialistas | 2026-10-01 | Comprobado (especialistas de la salud; no exclusivo odontología) | Comprobado (web y apps, Capterra) |
| 10 | Dentiqa | Violet Wave | No evidenciado (LatAm; Argentina listada) | https://dentiqa.app/ | 2026-10-01 | Comprobado (clínicas pequeñas a grandes y grupos) | Comprobado (nube, navegador) |
| 11 | DentalBox | AppLab Software LLC | No evidenciado (multipaís; Argentina listada) | https://www.dentalbox.app/ | 2026-10-01 | Comprobado (independientes a cadenas; centros radiológicos y estéticos) | Comprobado (100 % nube) |
| 12 | SMILE | SmileApp, LLC | No evidenciado (LatAm; Argentina incluida según verificación manual del 2026-10-01) | https://smiledental.app/ | 2026-10-01 | Comprobado (independientes y clínicas) | Comprobado (nube, Google Cloud) |
| 13 | Doctocliq | Doctocliq | Perú (opera en 20+ países) | https://www.doctocliq.com/ | 2026-10-01 | Comprobado (clínicas dentales, médicas, estéticas, kinesiología) | Comprobado (nube + apps iOS/Android) |
| 14 | Dentidesk | Dentidesk | Chile | https://www.dentidesk.com/ | 2026-10-01 | Comprobado (clínicas dentales) | Comprobado (nube) |
| 15 | Mi Agenda Dental | Mi Agenda Dental | México | https://miagendadental.com/ | 2026-10-01 | Comprobado (clínicas e independientes) | Comprobado (nube) |
| 16 | Simples Dental | Simples Dental | Brasil | https://www.simplesdental.com/ | 2026-10-01 | Comprobado (dentistas; redes y franquicias bajo consulta) | Comprobado (nube + apps) |
| 17 | Open Dental | Open Dental Software | Estados Unidos | https://www.opendental.com/ | 2026-10-01 | Comprobado (consultorios de cualquier tamaño) | Comprobado (instalación local) |

### A.2 Gestión de agenda y turnos digitales

| # | Producto | Profesionales y sillones/boxes | Duración, bloqueos, sobreturnos, solapamientos | Reserva online y canales | Confirmación, cancelación, reprogramación, lista de espera |
|---|----------|--------------------------------|-----------------------------------------------|--------------------------|------------------------------------------------------------|
| 1 | DentalTec | Comprobado (multiprofesional, intervalos configurables). Sillones: No evidenciado | Duración por prestación: No evidenciado. Bloqueos: No evidenciado. Sobreturnos: No evidenciado. Solapamientos: No evidenciado | No evidenciado (reserva online) | Comprobado (confirmación por WhatsApp). Cancelación, reprogramación y lista de espera: No evidenciado |
| 2 | DentalCore | Comprobado (agenda multi-doctor). Sillones: No evidenciado | Comprobado (detección de conflictos, según lectura "implícita"; verificar). Duración y bloqueos: No evidenciado. Sobreturnos: No evidenciado (el "autorrelleno de huecos" es otra función) | Comprobado (portal de pacientes 24/7; WhatsApp por QR) | Comprobado (confirmación automática; autorrelleno de huecos al cancelar). Reprogramación y lista de espera: No evidenciado |
| 3 | Bilog | Comprobado (multiprofesional; consultorios; vista diaria y semanal (video oficial, verificación manual)). Sillones/boxes: No evidenciado | Comprobado (sobreturnos como tipo de turno; horarios por profesional; botón "primer día disponible" (video oficial, verificación manual)). Duración por prestación, bloqueos y prevención de solapamientos: No evidenciado | Comprobado (agenda online por enlace y QR imprimible; ventana configurable de días; franjas habilitadas para pacientes nuevos o recurrentes; carga de obra social y plan; verificación por código de 6 dígitos al email; opción de reserva con IA, no probada (video oficial, verificación manual)) | Comprobado (recordatorios WhatsApp y SMS; cancelación y reprogramación por el paciente desde la agenda online; límite de turnos por paciente; lista de espera que ofrece el turno liberado; confirmación de turnos como servicio adicional; registro de presentes y ausentes (video oficial, verificación manual)) |
| 4 | Odonthia | Comprobado (equipo y profesionales). Sillones: No evidenciado | No evidenciado | Comprobado (reserva online) | Comprobado (recordatorios WhatsApp). Resto: No evidenciado |
| 5 | ClinIA | Comprobado (vista por profesional, especialidad y sillón) | Duración, bloqueos, sobreturnos, solapamientos: No evidenciado | Comprobado (agenda online 24/7; asistente IA por WhatsApp) | Comprobado (confirmación por WhatsApp). Resto: No evidenciado |
| 6 | Órbita | Comprobado (agenda por sillón; multiprofesional) | No evidenciado | Comprobado (reserva por WhatsApp y QR; asistente 24/7) | Comprobado (confirmaciones y recontacto de ausentes). Resto: No evidenciado |
| 7 | OdontoApp | No evidenciado | No evidenciado | No evidenciado | No evidenciado |
| 8 | Dentalink | Comprobado (multiprofesional). Sillones: No evidenciado | No evidenciado | Comprobado (el paciente agenda sus propias citas) | Comprobado (confirmaciones por WhatsApp). Resto: No evidenciado |
| 9 | Doctoralia Pro | Multiprofesional: No evidenciado. Comprobado (varias direcciones) | Comprobado (duración de citas elegible; bloqueos). Sobreturnos y solapamientos: No evidenciado | Comprobado (24/7 desde perfil, web, Google My Business y redes) | Comprobado (confirmaciones por WhatsApp). Resto: No evidenciado |
| 10 | Dentiqa | Comprobado (multi-dentista). Sillones: No evidenciado | Comprobado (bloqueos por profesional; "sin riesgo de doble reserva"). Duración y sobreturnos: No evidenciado | Comprobado (chatbot por WhatsApp 24/7) | Recordatorios 24 h y 2 h: Comprobado. Reprogramación y lista de espera: No evidenciado |
| 11 | DentalBox | Comprobado (multiprofesional; múltiples boxes) | No evidenciado | Comprobado (página pública con boxes y horarios) | Comprobado (confirmación por correo y WhatsApp). Resto: No evidenciado |
| 12 | SMILE | Comprobado (agenda por consultorio; multiusuario) | Comprobado (duraciones de 30, 45 y 60 min; no permite solapamientos; búsqueda de huecos). Bloqueos y sobreturnos: No evidenciado | Comprobado (chatbot por WhatsApp que agenda) | Comprobado (confirmaciones y recalls). Reprogramación y lista de espera: No evidenciado |
| 13 | Doctocliq | Comprobado (multiprofesional). Sillones: No evidenciado | No evidenciado | Comprobado (enlace de agendamiento; asistente IA) | Comprobado (recordatorios). Resto: No evidenciado |
| 14 | Dentidesk | No evidenciado en la página leída (filtro por dentista y sucursal según resultado de búsqueda) | No evidenciado | Comprobado (botón de agendamiento online para la web) | Comprobado (estados de cita personalizables; recordatorios por correo). Resto: No evidenciado |
| 15 | Mi Agenda Dental | Comprobado (multiprofesional; unidades configurables según plan) | Comprobado (candados anti doble cita). Duración y sobreturnos: No evidenciado | No evidenciado | Comprobado (confirmación por WhatsApp). Resto: No evidenciado |
| 16 | Simples Dental | Comprobado (varios dentistas; control de cadeiras) | Comprobado (bloqueos; prevención de duplicidad). Duración por prestación: No evidenciado. Sobreturnos: No evidenciado (existe "gestión de encaje") | Comprobado (enlace con horarios en tiempo real) | Comprobado (confirmación por WhatsApp, con costo adicional; lista de espera). Reprogramación: No evidenciado |
| 17 | Open Dental | No evidenciado | No evidenciado | Comprobado (Web Sched) | Comprobado (mensajería automatizada). Resto: No evidenciado |

### A.3 Automatización y gestión odontológica

| # | Producto | Recordatorios, ausentes, recupero, campañas | Ficha, odontograma, periodontograma | Imágenes, presupuestos y planes de tratamiento |
|---|----------|--------------------------------------------|-------------------------------------|-----------------------------------------------|
| 1 | DentalTec | Comprobado (recordatorios por WhatsApp). Afirmación comercial (40 % menos de ausentismo). Ausentes y campañas: No evidenciado | Comprobado (odontograma interactivo). Periodontograma: No evidenciado | Imágenes: No evidenciado. Presupuestos: No evidenciado |
| 2 | DentalCore | Comprobado (9 automatizaciones WhatsApp, recall) | Comprobado (odontograma con voz; periodontograma comparativo; consentimientos) | Imágenes: No evidenciado. Comprobado (presupuestos versionados) |
| 3 | Bilog | Comprobado (WhatsApp y SMS; registro de ausencias; pacientes marcados para recitar; SMS automático de cumpleaños con respuestas en el sistema (video oficial, verificación manual)). Campañas masivas: No evidenciado | Comprobado (odontograma en ficha; historia clínica diaria; prestaciones por estado (video oficial, verificación manual)). Periodontograma: No evidenciado | Comprobado (imágenes pre y post tratamiento; presupuestos con estadística de aceptados y rechazados (video oficial, verificación manual)) |
| 4 | Odonthia | Comprobado (WhatsApp). Resto: No evidenciado | Comprobado (odontograma FDI con temporales; periodontograma) | Imágenes: No evidenciado. Comprobado (presupuestos y planes) |
| 5 | ClinIA | Comprobado (recordatorios por WhatsApp). Resto: No evidenciado | Comprobado (odontograma 3D). Periodontograma: No evidenciado | Imágenes: No evidenciado. Comprobado (presupuestos por pieza, procedimiento y materiales) |
| 6 | Órbita | Comprobado (recontacto de ausentes). Afirmación comercial (806 turnos agendados por IA en 30 días) | Comprobado (odontograma y periodontograma) | Imágenes: No evidenciado. Comprobado (presupuestos) |
| 7 | OdontoApp | Comprobado (recordatorios automáticos) | Comprobado (odontograma). Periodontograma: No evidenciado | No evidenciado |
| 8 | Dentalink | Comprobado (recordatorios automáticos) | Comprobado (odontograma y periodontograma) | Imágenes: No evidenciado. Comprobado (presupuestos) |
| 9 | Doctoralia Pro | Comprobado (recordatorios y confirmaciones por WhatsApp) | Comprobado (episodios clínicos, no odontológicos). Odontograma: No evidenciado | No evidenciado |
| 10 | Dentiqa | Comprobado (campañas, reactivación, post tratamiento) | Comprobado (odontograma versionado; periodontograma BOP/NIC; firma digital) | Comprobado (galería de radiografías y fotos; plan con presupuesto) |
| 11 | DentalBox | Comprobado (confirmación por correo y WhatsApp). Campañas: No evidenciado | Comprobado (odontograma). Periodontograma: No evidenciado | Imágenes: No evidenciado. Comprobado (presupuestos en PDF) |
| 12 | SMILE | Comprobado (recalls a 6 meses; seguimiento por WhatsApp) | Comprobado (odontograma FDI de 32 piezas). Periodontograma: No evidenciado (solo mención en pie de página) | Imágenes: No evidenciado. Presupuestos: No evidenciado |
| 13 | Doctocliq | Comprobado (recordatorios; CRM y campañas) | Comprobado (odontograma, periodontograma, consentimientos) | Imágenes: Comprobado según plan (almacenamiento en plan avanzado). Comprobado (presupuestos) |
| 14 | Dentidesk | Comprobado (recordatorios por correo). WhatsApp: No evidenciado | Comprobado (odontograma; periodontograma) | Imágenes: No evidenciado. Comprobado (presupuestos con plantillas) |
| 15 | Mi Agenda Dental | Comprobado (recordatorios 24 h y 6 h; alertas post visita) | Comprobado (odontograma FDI; periodontograma) | Imágenes: No evidenciado. Comprobado (presupuestos con avance clínico y de pago) |
| 16 | Simples Dental | Comprobado (confirmaciones y automatización; CRM según plan) | Comprobado (odontograma; prescripciones digitales) | Comprobado (almacenamiento ilimitado de imágenes en plan Pro; presupuestos) |
| 17 | Open Dental | Comprobado (mensajería de texto automatizada) | Comprobado (gráfico dental) | No evidenciado |

### A.4 Administración e integraciones

| # | Producto | Caja, cobros, facturación, Mercado Pago | Obras sociales y prepagas | Integraciones (WhatsApp, Google Calendar, ARCA, API pública, firma, marketing) |
|---|----------|----------------------------------------|---------------------------|---------------------------------------------------------------------------------|
| 1 | DentalTec | Comprobado (facturación automática con ARCA; liquidación a prestadores). Caja y Mercado Pago: No evidenciado | Comprobado (más de 15 obras sociales). Afirmación comercial (validación en tiempo real, 64 % menos de débitos) | Comprobado (ARCA; WhatsApp, mecanismo No evidenciado). API pública y Google Calendar: No evidenciado |
| 2 | DentalCore | Comprobado (caja diaria; Mercado Pago con QR; facturas B y C con CAE) | Comprobado (más de 20 precargadas; presentación por lotes PDF/CSV) | Comprobado (WhatsApp por sesión QR, no API oficial; Mercado Pago; ARCA; HL7 FHIR). Google Calendar y API pública: No evidenciado |
| 3 | Bilog | Comprobado (caja, cobros, factura electrónica; cuenta corriente y saldos deudores; liquidación de profesionales; módulo de administración con caja auditada por sucursal y por usuario (video oficial, verificación manual)). Mercado Pago: No evidenciado | Comprobado (liquidación a obras sociales y módulo de auditoría de prestaciones por obra social (video oficial, verificación manual)) | WhatsApp: Comprobado (recordatorios). ARCA, Google Calendar, API: No evidenciado |
| 4 | Odonthia | Comprobado (caja y reportes). Facturación y Mercado Pago: No evidenciado | No evidenciado (el dato de obra social figura solo en la ficha del paciente) | Comprobado (sincronización de calendario; WhatsApp). ARCA y API: No evidenciado |
| 5 | ClinIA | Comprobado (facturación electrónica con AFIP). Caja y Mercado Pago: No evidenciado | Comprobado (cobertura vía API PUCO) | Comprobado (AFIP, PUCO, RENAPER, HL7 FHIR, WhatsApp). Recetario electrónico: Comprobado |
| 6 | Órbita | Comprobado (caja y cobros). Facturación y Mercado Pago: No evidenciado | Comprobado | Comprobado (WhatsApp; integraciones listadas con Dentalink, Bilog y Benty, alcance No evidenciado) |
| 7 | OdontoApp | No evidenciado | No evidenciado | No evidenciado |
| 8 | Dentalink | Comprobado (caja, cobros, pagos online y en cuotas). Mercado Pago: No evidenciado | No evidenciado | WhatsApp: Comprobado. API: No evidenciado |
| 9 | Doctoralia Pro | No evidenciado (la fuente de terceros Capterra menciona facturación) | No evidenciado | Comprobado (Google My Business). WhatsApp: Comprobado (recordatorios) |
| 10 | Dentiqa | Comprobado (facturación por profesional, texto genérico). Caja y Mercado Pago: No evidenciado | No evidenciado | Comprobado (API oficial de WhatsApp Business; importación CSV; firma digital). ARCA: No evidenciado |
| 11 | DentalBox | Comprobado (caja y cobros; facturación electrónica solo Chile y México). Mercado Pago: No evidenciado | Comprobado (convenios y seguros, no específico argentino) | Comprobado (WhatsApp, correo, pedidos a laboratorio). ARCA: No evidenciado |
| 12 | SMILE | Comprobado (saldos por paciente y recordatorios de pago). Facturación local y Mercado Pago: No evidenciado | No evidenciado | Comprobado (API oficial de WhatsApp Business) |
| 13 | Doctocliq | Comprobado (caja, comisiones; facturación electrónica en Perú, México, Ecuador y Colombia, no Argentina) | No evidenciado | Comprobado (Google Calendar; WhatsApp). ARCA: No evidenciado |
| 14 | Dentidesk | Comprobado (facturación, pagos y convenios). Mercado Pago: No evidenciado | Comprobado (módulo de convenios, sin detalle argentino) | Comprobado (Google Forms). WhatsApp: No evidenciado |
| 15 | Mi Agenda Dental | Comprobado (caja por método, comisiones, CFDI mexicano). Mercado Pago: No evidenciado | No evidenciado | Comprobado (Google Calendar bidireccional; WhatsApp). ARCA: No evidenciado |
| 16 | Simples Dental | Comprobado (nota fiscal brasileña, comisiones, flujo de caja, máquina de tarjeta integrada, según plan) | No evidenciado | Comprobado (WhatsApp con costo aparte). Google Calendar y ARCA: No evidenciado |
| 17 | Open Dental | Comprobado (seguros y clearinghouses de EE. UU.) | No aplica a Argentina (No evidenciado) | No evidenciado |

### A.5 Operación, seguridad, modelo comercial y adopción

Los precios corresponden al valor publicado el **2026-10-01** en la moneda indicada.

| # | Producto | Sucursales, roles, exportación, soporte | Seguridad y cumplimiento (Argentina) | Precio y prueba | Adopción y reseñas |
|---|----------|-----------------------------------------|--------------------------------------|-----------------|--------------------|
| 1 | DentalTec | Comprobado (10 tipos de rol; exportación PDF y Excel; auditoría). Sucursales: No evidenciado | Afirmación comercial (100 % de trazabilidad; JWT, bcrypt). Ley 25.326 y 26.529: No evidenciado | Precio: No evidenciado. Comprobado (demo gratuita) | Afirmación comercial (2.000 profesionales). Reseñas verificables: No evidenciado |
| 2 | DentalCore | Comprobado (roles personalizables; exportación FHIR, CSV y PDF). Sucursales: No evidenciado | Afirmación comercial (controles ISO/IEC 27001; Ley 25.326; cifrado AES-256-GCM de claves fiscales; base por clínica). Comprobado (12 plantillas de consentimiento) | Comprobado (USD 50 por mes con 2 usuarios; USD 10 por usuario adicional hasta 20 usuarios, USD 230 por mes; garantía de devolución de 14 días) | Clientes y reseñas: No evidenciado |
| 3 | Bilog | Comprobado (sucursales, por la caja por sucursal; capacitación con serie oficial de tutoriales (video oficial, verificación manual)). Roles detallados y exportación: No evidenciado | Afirmación comercial (seguridad como prioridad, sin certificaciones) | Precio: No evidenciado (la comparativa de Odonthia, competidor, habla de plan gratuito: no verificado). Comprobado: versiones con módulos adicionales (administración, auditoría) y recordatorios como servicio aparte; demo a pedido (video oficial) | Afirmación comercial (+1.500 clínicas, +5.000 usuarios); testimonios publicados por el proveedor |
| 4 | Odonthia | Comprobado (roles; exportación; backup en nube) | Afirmación comercial (cumplimiento declarado de Ley 26.529 y Ley 25.326) | Comprobado (gratis para funciones centrales sin tarjeta; IA y mensajería desde USD 26 por mes) | Afirmación comercial (2.694 clínicas registradas) |
| 5 | ClinIA | Roles, exportación y sucursales: No evidenciado (se menciona "cadenas" como segmento) | Afirmación comercial (adecuación a la ley de historia clínica digital; ReNaPDiS n.º 248 solo farmacia) | Precio: No evidenciado. Comprobado (demo gratuita) | Clientes y reseñas: No evidenciado |
| 6 | Órbita | Roles, exportación y sucursales: No evidenciado | No evidenciado | Precio y prueba: No evidenciado (a consultar) | Afirmación comercial (9+ testimonios; 145.000 mensajes y 806 turnos por IA en 30 días) |
| 7 | OdontoApp | No evidenciado | No evidenciado | No evidenciado | Afirmación comercial (más de 10 odontólogos) |
| 8 | Dentalink | Comprobado (roles; más de 50 reportes en Excel). Sucursales: No evidenciado | Comprobado (publica contrato de tratamiento de datos y política de seguridad). Adecuación a la ley argentina: No evidenciado | Precio y prueba: No evidenciado | Afirmación comercial (15.000+ clientes; 12 millones de pacientes) |
| 9 | Doctoralia Pro | Comprobado (varias direcciones). Roles y exportación: No evidenciado | Comprobado (almacenamiento AWS; declara GDPR). Ley argentina: No evidenciado | Comprobado (cobro anual con tarjeta; Starter ARS 25.000, Plus ARS 35.000, VIP ARS 55.000; página web profesional +ARS 4.000 por mes; corregido en la verificación manual). Terceros (Capterra): EUR 69 por usuario por mes y EUR 129 por mes; sin prueba gratuita | Terceros: 4,7/5 sobre 415 reseñas (Capterra); directorio con 110.000 profesionales según un resultado de búsqueda sin verificar |
| 10 | Dentiqa | Comprobado (roles dueño, admin, dentista y recepción; multiclínica en Enterprise; auditoría). Exportación: No evidenciado | Comprobado (AES-256 de tokens; HTTPS; backups; logs de auditoría; declarados). Ley argentina: No evidenciado | Comprobado (USD 89, 149 y 249 por mes; mensual sin contrato). Prueba: No evidenciado (demo) | Clientes: No evidenciado |
| 11 | DentalBox | Comprobado (roles; exportación a Excel). Sucursales: No evidenciado | Afirmación comercial (AES-256, backup diario, GDPR/HIPAA/LGPD). Ley argentina: No evidenciado | Comprobado (USD 21, 33, 50 y 75 por mes; prueba de 7 días) | Clientes y reseñas: No evidenciado |
| 12 | SMILE | Comprobado (roles; exportación a Excel; sucursal adicional USD 15 por mes; auditoría de acciones) | Afirmación comercial (cifrado, backup automático, "nivel bancario"). Ley argentina: No evidenciado | Comprobado (USD 19; clínica USD 23 más módulos de USD 5; IA y WhatsApp USD 15; prueba de 30 días) | Un solo testimonio; cantidad de clientes: No evidenciado |
| 13 | Doctocliq | Comprobado (roles). Exportación y sucursales: No evidenciado | No evidenciado (enlaces a términos de Perú y México) | Comprobado (plan gratuito hasta 30 pacientes por mes; prueba de 7 días). Precios de planes pagos: No evidenciado | Afirmación comercial (4.000+ médicos; "+30 % de ingresos") |
| 14 | Dentidesk | Comprobado (usuarios y permisos). Exportación: No evidenciado | No evidenciado | Precio y prueba: No evidenciado | No evidenciado |
| 15 | Mi Agenda Dental | Comprobado (roles; exportación CSV; auditoría inmutable declarada) | Normativa mexicana declarada (NOM-013/024, LFPDPPP); la argentina: No evidenciado | Comprobado (MXN 99 a 899 por mes con IVA según plan; Empresarial MXN 2.500; prueba de 30 días) | Afirmación comercial (en uso real en 2 clínicas) |
| 16 | Simples Dental | Roles y exportación: No evidenciado. Redes y franquicias: a consultar | No evidenciado | Comprobado (BRL 149,90, 249,90 y 349,90 por mes de lista, con descuento vigente 137,41, 229,08 y 320,74; prueba de 7 días; confirmaciones WhatsApp con cargo aparte) | Afirmación comercial (más de 100 mil dentistas; 9,6/10 en Reclame Aqui; 4,8 en iOS y 4,2 en Android) |
| 17 | Open Dental | No evidenciado | No evidenciado | Prueba: Comprobado. Precio: No evidenciado | No evidenciado |

---

## 4. B. Matriz de puntuación

Pesos: Turnos y automatización 25 %; Funcionalidad clínica 20 %; Integraciones locales y WhatsApp 15 %; Administración, cobros y facturación 15 %; Experiencia del paciente 10 %; Seguridad, exportación y trazabilidad 10 %; Precio y facilidad de adopción 5 %. Puntaje de cada criterio de 0 a 5; total = suma ponderada (máximo 5,00).

| Rank | Producto | Turnos y autom. (25 %) | Clínica (20 %) | Integr. locales y WhatsApp (15 %) | Admin., cobros y fact. (15 %) | Exp. del paciente (10 %) | Seguridad, export. y traz. (10 %) | Precio y adopción (5 %) | **Total ponderado** |
|------|----------|------|------|------|------|------|------|------|-----------|
| 1 | DentalCore | 4 | 4 | 5 | 5 | 4 | 5 | 3 | **4,35** |
| 2 | Dentiqa | 4 | 5 | 3 | 2 | 4 | 3 | 2 | **3,55** |
| 3 (empate) | ClinIA | 4 | 3 | 4 | 3 | 4 | 2 | 1 | **3,30** |
| 3 (empate) | Bilog | 4 | 4 | 2 | 4 | 4 | 2 | 0 | **3,30** |
| 5 | DentalBox | 4 | 3 | 2 | 3 | 3 | 4 | 4 | **3,25** |
| 6 | Simples Dental | 5 | 4 | 1 | 3 | 4 | 0 | 3 | **3,20** |
| 7 | SMILE | 4 | 2 | 3 | 2 | 4 | 4 | 4 | **3,15** |
| 8 (empate) | Odonthia | 3 | 4 | 2 | 2 | 3 | 3 | 5 | **3,00** |
| 8 (empate) | Mi Agenda Dental | 3 | 4 | 2 | 3 | 2 | 3 | 4 | **3,00** |
| 10 | Órbita | 4 | 4 | 2 | 3 | 4 | 0 | 0 | **2,95** |
| 11 (empate) | DentalTec | 3 | 2 | 4 | 4 | 1 | 4 | 1 | **2,90** |
| 11 (empate) | Dentalink | 3 | 4 | 2 | 3 | 3 | 3 | 0 | **2,90** |
| 11 (empate) | Doctocliq | 3 | 4 | 2 | 3 | 3 | 1 | 4 | **2,90** |
| 14 | Dentidesk | 2 | 4 | 1 | 3 | 2 | 1 | 0 | **2,20** |
| 15 | Doctoralia Pro | 3 | 1 | 2 | 1 | 5 | 1 | 2 | **2,10** |
| 16 | Open Dental | 2 | 2 | 0 | 1 | 2 | 0 | 1 | **1,30** |
| 17 | OdontoApp | 1 | 1 | 0 | 0 | 0 | 0 | 0 | **0,45** |

### Nota metodológica

- **Escala.** 0 = sin evidencia pública de ninguna capacidad del criterio; 1 = una capacidad aislada o solo mencionada; 2 = capacidades básicas comprobadas; 3 = cobertura razonable con vacíos relevantes; 4 = cobertura amplia comprobada; 5 = cobertura completa comprobada para el contexto argentino.
- **Tratamiento de "No evidenciado".** Lo no evidenciado no suma puntos: no se asumió que una función exista por ser habitual en el rubro. Un 0 significa "sin evidencia", no "el producto carece de la función". Esto penaliza a sitios poco detallados (OdontoApp, Órbita; Bilog también lo estaba hasta que sus videos oficiales aportaron evidencia y su puntaje pasó de 2,65 a 3,30) y beneficia a los que publican más información, en particular a DentalCore.
- **Afirmaciones comerciales.** Se puntuaron solo cuando describen una función concreta publicada por el proveedor (por ejemplo, "integración con ARCA"); las cifras de resultados ("40 % menos de ausentismo") no sumaron.
- **Criterio 5 (experiencia del paciente).** Se valoró reserva online autónoma, canales (WhatsApp, enlace, QR), asistente 24/7 y directorio; no se probó ninguna interfaz.
- **Criterio 7.** 5 = plan gratuito permanente con precio publicado; 3 a 4 = precio publicado con prueba o garantía; 1 a 2 = solo demo o precio alto o parcial; 0 = sin precio ni prueba evidenciados.
- **Sesgos y límites.** Las puntuaciones son juicio del analista sobre información de sitios oficiales, no resultado de uso real. Las extracciones se hicieron con una herramienta automatizada de lectura, por lo que pueden omitir contenido dinámico. Los sistemas extranjeros no son penalizados por no tener ARCA, pero sí no suman en el criterio 3 por no cubrir el contexto local.

---

## 5. C. Análisis competitivo

### C.1 Funcionalidades que ya son estándar de mercado

Aparecen comprobadas en la mayoría de los sistemas relevados y no alcanzan para diferenciar un producto nuevo:
- Agenda multiprofesional en la nube con acceso desde web y celular.
- Recordatorios y confirmaciones automáticas por WhatsApp (en 14 de 17 sistemas aparece algún recordatorio por WhatsApp o canal digital equivalente).
- Odontograma digital y presupuestos de tratamiento (en la mayoría de los productos odontológicos); el periodontograma está en aproximadamente la mitad.
- Caja o cobros básicos y reportes.
- Roles de usuario.
- Reserva online por enlace, QR o página pública (en cerca de dos tercios).

### C.2 Funcionalidades diferenciadoras reales

- **Integración fiscal y de cobros argentina combinada.** ARCA con CAE, Mercado Pago y obras sociales en un mismo flujo solo está evidenciada en DentalCore; ARCA con obras sociales en DentalTec; AFIP y PUCO en ClinIA.
- **WhatsApp por API oficial** frente a sesión por QR. SMILE y Dentiqa publican que usan la API oficial; DentalCore explicita que usa sesión por QR (menos robusta ante bloqueos y sin plantillas oficiales).
- **Asistente conversacional que agenda por WhatsApp** (ClinIA, Órbita, SMILE, Dentiqa, DentalCore con portal y automatizaciones). Hay cifras de desempeño (Órbita), pero son afirmaciones comerciales sin auditoría.
- **Lista de espera y relleno automático de huecos** (Simples Dental, DentalCore, Bilog): reduce el costo de las cancelaciones y es poco frecuente.
- **Interoperabilidad clínica** con HL7 FHIR, PUCO y RENAPER (ClinIA, DentalCore).
- **Validación de prácticas contra obra social antes de cargarlas** (DentalTec lo declara como exclusivo; no se pudo comprobar su alcance).
- **Entrada por voz y apoyo a la decisión clínica** (DentalCore); se trata de afirmaciones del proveedor sin evidencia externa.

### C.3 Vacíos frecuentes del mercado argentino

- **Núcleo de agenda poco documentado.** Duración variable por prestación y gestión de sillones figuran como "No evidenciado" en casi todos los productos argentinos, incluso en los tutoriales oficiales de Bilog; los sobreturnos sí aparecen en Bilog. Es posible que existan, pero no se demuestran públicamente, lo que ya es una debilidad de comunicación.
- **Autogestión del paciente.** Cancelación y reprogramación por el paciente solo se evidenciaron en Bilog, mediante su agenda online web con enlace y QR (video oficial); el análisis automatizado inicial la había dado como ausente en todo el mercado. Dentro de una conversación de WhatsApp no se evidenció en ningún sistema.
- **Precios opacos en pesos.** DentalTec, Bilog, ClinIA, Órbita y Dentalink no publican precios; los que sí publican lo hacen mayormente en USD, con exposición cambiaria para el consultorio (Doctoralia Pro es la excepción: publica en pesos, dato corregido en la verificación manual).
- **Mercado Pago poco presente** (solo DentalCore) y seña online para turnos no evidenciada.
- **Evidencia de seguridad débil.** Las referencias a las Leyes 25.326 y 26.529 son declaraciones sin certificaciones ni descripción de auditoría; solo algunos explicitan trazabilidad. Solo se evidencia exportación de datos en algunos productos (Odonthia, DentalCore, DentalTec, Dentalink, SMILE, DentalBox).
- **Evidencia de adopción poco verificable.** Las cifras de clientes son autodeclaradas y no hay reseñas verificables de productos argentinos en las fuentes consultadas (las únicas reseñas verificables halladas corresponden a Doctoralia Pro en Capterra y a Simples Dental según su propio sitio).
- **Dependencia de blogs interesados.** Las comparativas locales las publican los propios proveedores; falta una fuente independiente.

### C.4 Oportunidades de innovación para un nuevo sistema

- Agenda odontológica bien resuelta y demostrable: prestaciones con duración propia, sillones como recurso, bloqueos, sobreturnos controlados y prevención de solapamientos, con documentación pública clara (propia ventaja de comunicación).
- Ciclo completo de autogestión del paciente por WhatsApp (Bilog ya lo resuelve por web, no dentro del mensaje): reservar, confirmar, cancelar y reprogramar en un solo hilo, con lista de espera que ofrece automáticamente el hueco liberado.
- Seña o pago anticipado por Mercado Pago ligada al turno para reducir ausentismo (el vínculo turno-seña no se evidenció en los sistemas relevados).
- Precios publicados en pesos con actualización transparente y prueba gratuita real.
- Transparencia de seguridad: registro de auditoría visible, exportación completa en formatos abiertos, política de privacidad clara y adecuación documentada a las leyes 25.326 y 26.529.
- Métricas simples y accionables de ausentismo, ocupación de sillones y recupero de pacientes.
- Incorporación sencilla desde planillas o sistemas previos (Dentiqa publica migración desde Dentalink y Excel; es una barrera de adopción a reducir).

---

## 6. D. Recomendación final

### D.1 Cinco competidores prioritarios para analizar mediante demo

1. **DentalTec**: líder declarado local, con ARCA y más de 15 obras sociales; permite contrastar la agenda, la reserva online (no evidenciada) y la validación de prácticas.
2. **Bilog**: mayor base de clientes declarada en Argentina (+1.500); los videos oficiales ya muestran agenda online con autogestión, lista de espera y liquidación a obras sociales; en la demo falta verificar sillones, duración por prestación y prevención de solapamientos.
3. **DentalCore**: el más completo en lo evidenciado (ARCA, Mercado Pago, prepagas, FHIR); validar la solidez real de la agenda y de WhatsApp por QR.
4. **Odonthia**: plan gratuito permanente y odontograma FDI; es el competidor de entrada más agresivo en precio.
5. **Dentalink**: referencia regional con gran base declarada y presencia en Argentina; contrastar reserva online, caja y reportes.

Alternativas si se amplía el análisis: Dentiqa (WhatsApp API y campañas) y ClinIA (integraciones públicas).

### D.2 Tres productos de referencia para experiencia de usuario

1. **Simples Dental**: enlace de reserva con horarios en tiempo real, lista de espera y control de sillas; referencia para el flujo de agenda.
2. **SMILE**: chatbot que agenda por WhatsApp, planes simples y prueba de 30 días; referencia de simplicidad comercial.
3. **Doctoralia Pro**: experiencia de reserva del paciente y recordatorios; referencia de la perspectiva del paciente (no de la clínica odontológica).

### D.3 MVP sugerido

**Imprescindible (agenda y turnos como núcleo)**
- Agenda diaria y semanal con múltiples profesionales y múltiples sillones o boxes como recursos.
- Catálogo de prestaciones con duración propia; el turno reserva la duración correspondiente.
- Prevención de solapamientos por profesional y por sillón; bloqueos de agenda (vacaciones, franjas).
- Alta, cancelación y reprogramación de turnos (por la recepción) con historial.
- Reserva online por enlace público con horarios disponibles en tiempo real.
- Recordatorio y confirmación por WhatsApp.
- Ficha de paciente con odontograma digital y anamnesis simple.
- Presupuesto de tratamiento y caja básica.
- Roles (administrador, profesional, recepción), registro de auditoría y exportación de datos.

**Diferenciador (alcanzable en el MVP o primera iteración)**
- Cancelación y reprogramación por el paciente desde el mensaje de WhatsApp, con reglas de antelación.
- Lista de espera con oferta automática del hueco liberado.
- Sobreturnos controlados con límite configurable.
- Seña online por Mercado Pago asociada al turno.
- Panel de ausentismo y ocupación de sillones.
- Precios publicados en pesos y prueba gratuita.

**Etapas posteriores**
- Facturación electrónica ARCA integrada.
- Liquidación y validación con obras sociales y prepagas.
- Periodontograma, imágenes y radiografías, consentimientos y firma digital.
- Asistente conversacional con IA.
- Multisede, campañas de marketing y recupero masivo.
- API pública, integraciones con Google Calendar y estándares como HL7 FHIR.
- App móvil nativa.

### D.4 Ajuste de alcance del MVP (decisión del equipo, 2026-10-01)

Al revisar la sección D.3 durante la ronda de Discovery se decidió **Ajustar**:
el MVP "imprescindible" propuesto por el análisis era demasiado amplio para un
primer incremento (incluía ficha con odontograma, presupuestos, caja, enlace
público de reserva y WhatsApp real). Se recorta al núcleo de agenda, que es
además el vacío principal detectado en C.3.

**MVP final (imprescindible)**
- Agenda diaria y semanal con múltiples profesionales y múltiples sillones.
- Prestaciones con duración por defecto; el turno toma esa duración y la recepción puede ajustarla.
- Crear, reprogramar y cancelar turnos sin solapamientos por profesional ni por sillón (intervalos `[inicio, fin)`).
- Horarios de atención y bloqueos de agenda.
- Registro básico de pacientes (datos ficticios).
- Roles: recepcionista y odontólogo (autenticación JWT); registro de auditoría de cambios en turnos.
- Recordatorio previo al turno mediante una abstracción de envío con adaptador simulado.

**Pasan a diferenciador o etapas posteriores**: enlace público de reserva,
WhatsApp Business API real, ficha clínica y odontograma, presupuestos y caja,
además de todo lo ya listado en D.3 como diferenciador o etapa posterior.

Detalle de las decisiones de producto en `docs/discovery/discovery.md`.

---

## 7. Verificación de fuentes

Verificación realizada personalmente por el estudiante el 2026-10-01 sobre nueve fuentes (sitio oficial, página de precios, funcionalidades, marketplace de reseñas, página de producto y video oficial). Se eligieron las afirmaciones más propensas a estar desactualizadas o mal interpretadas (precios, WhatsApp, ARCA).

| # | Fuente (URL) | Tipo | Qué afirma el informe | Qué encontré | Corrección aplicada |
|---|--------------|------|-----------------------|--------------|---------------------|
| 1 | https://dentalcore.app/ | Sitio oficial | Facturación ARCA (Factura B/C con CAE), Mercado Pago con QR y WhatsApp por sesión QR (no API oficial) | Coincide con lo relevado por el agente. | Ninguna. |
| 2 | https://dentalcore.app/ (sección de precios) | Página de precios | USD 50 por mes con 2 usuarios y USD 10 por usuario adicional; otra fuente interesada habla de USD 69 a 139 | Coincide: USD 50 por mes con 2 usuarios y USD 10 por cada usuario adicional, hasta 20 usuarios (USD 230 por mes). Garantía de 14 días. | Se agrega el tope de 20 usuarios y el valor máximo (USD 230 por mes) en A.5 y en la nota de la fuente. La cifra de USD 69 a 139 de la comparativa de terceros queda descartada. |
| 3 | https://web.dentaltec.com.ar/funcionalidades | Sitio oficial / funcionalidades | Integración de facturación con ARCA y más de 15 obras sociales; no se evidenció reserva online ni precios | Coincide con lo relevado. No se encontraron tarifas publicadas; solo se ofrece una demo gratuita. | Ninguna. Se confirma "precios: No evidenciado". |
| 4 | https://www.simplesdental.com/planos-e-precos | Página de precios | BRL 149,90 / 249,90 / 349,90 por mes; confirmaciones por WhatsApp con cargo aparte (una lectura previa mostró R$ 139,90 / 199,90 / 279,90) | Precio de lista R$ 149,90 / 249,90 / 349,90 por mes, con descuento vigente R$ 137,41 / 229,08 / 320,74 por mes (Basic / Plus / Pro). | Se confirman los precios de lista y se descarta la lectura previa de R$ 139,90 / 199,90 / 279,90. Se agregan los precios con descuento. El descuento observado es de aproximadamente 8,3 %, no el 10 % que registró el agente; queda anotado en la fuente. |
| 5 | https://smiledental.app/ | Sitio oficial / video o demo oficial | API oficial de WhatsApp Business, chatbot que agenda y precios USD 19 / 23 / +15; que Argentina esté o no entre los países cubiertos | Coincide con lo relevado. Argentina sí aparece entre los países incluidos. | Se corrige el país en A.1 y en la nota de la fuente: Argentina incluida (verificación manual). |
| 6 | https://www.capterra.com/p/253301/Doctoralia-Pro/ | Marketplace / reseñas | 4,7/5 con 415 reseñas; Basic EUR 69 y Clinic EUR 129; sin prueba gratuita | Coincide con lo relevado por el agente. | Ninguna. |
| 7 | https://pro.doctoralia.com/ar/agenda-doctoralia-para-especialistas | Centro de ayuda / página del producto | Duración de citas elegible, bloqueos y recordatorios por WhatsApp; no se evidenció odontograma ni facturación | Coincide con lo relevado. Precios publicados en pesos: Starter ARS 25.000, Plus ARS 35.000, VIP ARS 55.000; página web profesional opcional por ARS 4.000 por mes adicionales. | Se corrige A.5: los importes en pesos sí están publicados en la página oficial (el agente los había marcado "No evidenciado"). |
| 8 | https://www.youtube.com/@grupodentaltec | Video oficial (canal de YouTube) | Agenda por sillón y reserva online de DentalTec: No evidenciado | El canal oficial publica sketches de salud dental dirigidos a niños; no hay videos de demostración ni tutoriales del software. | Ninguna sobre funcionalidades: se confirma que agenda por sillón y reserva online siguen "No evidenciado". Se registra que DentalTec no ofrece evidencia en video del producto. |
| 9 | https://www.youtube.com/@bilogsoluciones | Video oficial (canal de YouTube) | Agenda por consultorio, QR y liquidación a obras sociales de Bilog | Se transcribieron dos videos oficiales. "Agenda online": agenda online con enlace y QR, ventana de días configurable, franjas para pacientes nuevos o recurrentes, cancelación y reprogramación por el paciente, límite de turnos por paciente, obra social al reservar, verificación por email y turno marcado como online en la agenda. "Versión full": vista diaria y semanal, sobreturnos, lista de espera ante cancelaciones, confirmación de turnos (servicio adicional), presentes y ausentes, imágenes, presupuestos, cuenta corriente, liquidación de obras sociales y profesionales, caja por sucursal y por usuario, estadísticas. No se muestran sillones, duración por prestación ni prevención de solapamientos. | Se corrigen las filas de Bilog en A.2 a A.5, su puntaje en B (2,65 → 3,30, del puesto 13 al 3), C.2, C.3 (la autogestión del paciente no estaba ausente en todo el mercado, como afirmaba el agente), C.4 y D.1. Simples Dental sale del top 5. |

**Resumen de la verificación.** De nueve fuentes comprobadas, seis coincidieron con el informe y tres revelaron errores del agente: los precios en pesos de Doctoralia Pro (marcados "No evidenciado" cuando sí estaban publicados), el país de SMILE (Argentina sí figura) y la subestimación de Bilog, cuyos videos oficiales muestran autogestión del paciente, lista de espera y sobreturnos que el agente había dado como ausentes. Además se completaron datos que el agente omitió (tope de usuarios de DentalCore y precios con descuento de Simples Dental). Las correcciones no alteran los puntajes de la matriz B: SMILE no cambia de criterio y Doctoralia Pro mantiene 2 en el criterio 7 porque, aunque publica precios, no ofrece prueba gratuita según Capterra.

**Videos oficiales.** Se revisaron los canales de YouTube de DentalTec y Bilog. DentalTec solo publica contenido educativo infantil, sin demostraciones del producto, por lo que no aporta evidencia y sus "No evidenciado" se mantienen. Bilog tiene una serie oficial de tutoriales; dos de ellos ("Agenda online" y "Versión full") se transcribieron y contrastaron con el informe. Fue la corrección más importante de la verificación: el agente había dado la autogestión del paciente como inexistente en el mercado y había subestimado a Bilog por la poca información de su sitio web.

**Pendiente.** No se verificaron centros de ayuda.

---

## 8. Referencias completas

Todas consultadas el **2026-10-01**. Se distingue entre páginas leídas ("L") y páginas que solo se vieron en resultados de búsqueda ("B"). Las notas por sistema están en `docs/discovery/sources/`.

**Sitios oficiales y páginas de producto**
- DentalTec: https://web.dentaltec.com.ar/funcionalidades (L); https://web.dentaltec.com.ar/ (B)
- DentalCore: https://dentalcore.app/ (L); https://dentalcore.app/blog/mejor-software-dental-argentina (L, contenido promocional del proveedor)
- Bilog: https://bilog.com.ar/ (L); https://bilog.com.ar/precios (HTTP 404)
- Odonthia: https://odonthia.com/ (L); https://odonthia.com/precios (L, sin precios); https://odonthia.com/blog/mejores-software-odontologicos-argentina-2026 (L, contenido del propio proveedor)
- ClinIA: https://www.clinia.com.ar/odontologia (L)
- Órbita: https://hiorbita.com/ (L)
- OdontoApp: https://odontoapp.com.ar/ (L)
- Dentalink: https://www.softwaredentalink.com/?c=cl (L); https://www.dentalink.cl/ (redirección); https://www.dentalink.com/ (no resuelve)
- Doctoralia Pro: https://pro.doctoralia.com/ar/agenda-doctoralia-para-especialistas (L)
- Dentiqa: https://dentiqa.app/ (L)
- DentalBox: https://www.dentalbox.app/ (L)
- SMILE: https://smiledental.app/ (L)
- Doctocliq: https://www.doctocliq.com/ (L)
- Dentidesk: https://www.dentidesk.com/dentidesk/feature (L); https://www.dentidesk.com/ (B)
- Mi Agenda Dental: https://miagendadental.com/ (L)
- Simples Dental: https://www.simplesdental.com/planos-e-precos (L); https://www.simplesdental.com/agenda-online (L); https://www.simplesdental.com/ (B)
- Open Dental: https://www.opendental.com/ (L)

**Videos oficiales (verificación manual)**
- DentalTec: https://www.youtube.com/@grupodentaltec — consultado el 2026-10-01
- Bilog: https://www.youtube.com/@bilogsoluciones (videos "Agenda online" y "Versión full", transcriptos) — consultado el 2026-10-01

**Terceros, comparativas y marketplaces**
- Capterra, Doctoralia Pro: https://www.capterra.com/p/253301/Doctoralia-Pro/ (L)
- Turnito, comparativa (contenido de un proveedor): https://turnito.app/blog/los-mejores-software-de-turnos-para-odontologos-en-argentina-2026/ (HTTP 404 al leerla; solo vista en búsqueda)
- Nexup, Tus Programas, Medesk, Akeito y otros agregadores: vistos solo en resultados de búsqueda; no se utilizaron como evidencia.

**Limitaciones.** El análisis automatizado no consultó videos oficiales ni centros de ayuda; los canales oficiales de YouTube de DentalTec y Bilog se revisaron luego en la verificación manual (sección 7). No se consultaron centros de ayuda detallados, y no se contactó a ningún proveedor ni se crearon cuentas. Las extracciones de contenido se realizaron con una herramienta automatizada que resume la página; las discrepancias detectadas (precios de DentalCore y Simples Dental, cantidad de clientes de Simples Dental) se señalan en cada nota de fuente.
