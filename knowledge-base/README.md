# Turnos y Agenda para Consultorios Odontológicos — Base de Conocimiento

Base de conocimiento generada (Mode A, ingest) a partir de `docs/discovery/` (checklist de Discovery aprobado, informe de mercado de 17 sistemas y notas por competidor) y del estado del orquestador. Ante conflicto, prevalece `discovery.md` y el ajuste de alcance D.4.

## Índice de Archivos

| Archivo | Contenido |
|---------|-----------|
| [01_vision_y_objetivos.md](01_vision_y_objetivos.md) | Propósito, vacío de mercado, objetivos, alcance MVP (D.4), fuera de alcance |
| [02_descripcion_general.md](02_descripcion_general.md) | Stack, arquitectura, integraciones, API |
| [03_actores_y_roles.md](03_actores_y_roles.md) | Actores, RBAC, rutas públicas |
| [04_modelo_de_datos.md](04_modelo_de_datos.md) | Entidades, ERD, constraints de exclusión, seed |
| [05_reglas_de_negocio.md](05_reglas_de_negocio.md) | Reglas de agenda (RN-AG, trazadas a RN1-RN6), horarios, notificaciones, cumplimiento |
| [06_funcionalidades.md](06_funcionalidades.md) | Épicas e historias de usuario del MVP |
| [07_flujos_principales.md](07_flujos_principales.md) | Auth, crear/reprogramar/cancelar turno, bloqueo, recordatorios |
| [08_arquitectura_propuesta.md](08_arquitectura_propuesta.md) | Patrones, concurrencia en BD, directorios, seguridad, env vars |
| [09_decisiones_y_supuestos.md](09_decisiones_y_supuestos.md) | Decisiones DD-xx y supuestos SU-xx |
| [10_preguntas_abiertas.md](10_preguntas_abiertas.md) | Inconsistencias, preguntas priorizadas, datos "No evidenciado" |

## Quick Start para Desarrolladores

1. Entender el dominio -> [01](01_vision_y_objetivos.md), [03](03_actores_y_roles.md)
2. Entender los datos -> [04](04_modelo_de_datos.md)
3. Entender las reglas -> [05](05_reglas_de_negocio.md)
4. Entender la arquitectura -> [02](02_descripcion_general.md), [08](08_arquitectura_propuesta.md)
5. Implementar -> [07](07_flujos_principales.md), [06](06_funcionalidades.md)
6. Antes de codificar -> [10](10_preguntas_abiertas.md)

## Resumen Ejecutivo

Sistema web (Python/FastAPI, PostgreSQL, Redis, React/TS) de agenda para consultorios odontológicos chicos de Argentina. El MVP se concentra en el vacío detectado en el mercado: agenda con prestaciones de duración configurable y sillones como recurso, con prevención de solapamientos por profesional y por sillón garantizada en la base de datos (intervalos `[inicio, fin)`). Dos roles (recepcionista, odontólogo), auditoría de turnos y recordatorio vía puerto de notificación con adaptador mock. Reserva online, WhatsApp real, ficha clínica, caja y ARCA quedan fuera de alcance.
