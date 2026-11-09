# Descripción General

## Stack tecnológico (restricción del proyecto)

| Capa | Tecnologías | Notas |
|------|-------------|-------|
| Backend | Python + FastAPI | API REST, validación con Pydantic |
| ORM / migraciones | SQLAlchemy (+ Alembic, **Suposición**) | |
| Base de datos | PostgreSQL | Requiere extensión `btree_gist` para la restricción de exclusión |
| Cola / caché | Redis | Cola de recordatorios asincrónicos |
| Autenticación | JWT | 2 roles |
| Frontend | React + TypeScript + Vite | Agenda diaria/semanal |
| Infra | Docker / Docker Compose | api, db, redis, worker, frontend |

Versiones mínimas (DD-17): Python ≥ 3.13, PostgreSQL 16, Node 24 LTS (DD-17, confirmado en C-14 por DD-33 i). Migraciones Alembic lineales, numeradas `NNN_nombre.py`, con `downgrade`.

## Tipo de sistema
Aplicación web (SPA + API REST), monotenant (un consultorio por despliegue), escala de equipo: 1-5 profesionales, 1-4 sillones, pocos usuarios internos. Sin acceso público de pacientes en el MVP.

## Arquitectura general

```
 Navegador (React/TS/Vite)
        |  HTTPS + JWT
        v
 API FastAPI --> Servicios de dominio (agenda, turnos, disponibilidad)
   |   |                         |
   |   +- SQLAlchemy --> PostgreSQL (UTC; EXCLUDE USING gist)
   |
   +- publica recordatorio --> Redis (cola) --> Worker
                                                  |
                                       Puerto NotificationSender
                                                  |
                                   Adaptador MockSender (MVP)
                                   [futuro: WhatsApp Business API]
```

Decisiones de alto nivel: el dominio de agenda es el corazón; la no superposición se garantiza **en la base de datos** (ver 08 y 09); la notificación es un **puerto** para no depender de WhatsApp (acceso, aprobación y costo de la API); horarios en UTC y presentación en `America/Argentina/Buenos_Aires`.

## Integraciones externas

| Servicio | Propósito | Tipo | Estado MVP |
|----------|-----------|------|------------|
| Puerto de notificación + adaptador mock | Recordatorio previo al turno | Interfaz interna | Incluido |
| Redis | Cola de recordatorios | Cola | Incluido |
| WhatsApp Business API | Envío real | REST (adaptador futuro) | Fuera de alcance |
| Mercado Pago, ARCA, obras sociales | Seña, facturación, cobertura | — | Fuera de alcance |

No hay integraciones externas obligatorias en el MVP.

## API REST (resumen propuesto)

| Recurso | Endpoints principales |
|---------|-----------------------|
| Auth | `POST /auth/login`; `POST /auth/refresh` (**Suposición**) **no está implementado**: sin renovación, al vencer el token el frontend pide iniciar sesión de nuevo (DD-33 d) |
| Profesionales | `GET /profesionales[/{id}]` (ambos roles); `POST /profesionales`, `PATCH /profesionales/{id}`, `POST /profesionales/{id}/desactivar` (recepcionista; DD-26) |
| Sillones | `GET /sillones[/{id}]` (ambos roles); `POST /sillones`, `PATCH /sillones/{id}`, `POST /sillones/{id}/desactivar` (recepcionista; DD-26) |
| Prestaciones | `GET /prestaciones[/{id}]` (ambos roles); `POST /prestaciones` con duración por defecto, `PATCH /prestaciones/{id}`, `POST /prestaciones/{id}/desactivar` (recepcionista; DD-26) |
| Horarios de atención | `GET /profesionales/{id}/horarios` (recepcionista; el odontólogo, solo el propio); `POST /profesionales/{id}/horarios`, `PATCH` y `DELETE /profesionales/{id}/horarios/{horario_id}` (recepcionista; DD-27) |
| Bloqueos | `GET /bloqueos?profesional_id=` (recepcionista todos o el filtrado; odontólogo, solo los de su profesional); `POST /bloqueos` (el odontólogo puede omitir `profesional_id`); `DELETE /bloqueos/{id}` (recepcionista cualquiera; odontólogo, los de su profesional); sin `PATCH` (DD-30) |
| Pacientes | `GET /pacientes?q=&limite=&desplazamiento=` (listado y búsqueda, solo recepcionista); `GET /pacientes/{id}` (recepcionista: ficha completa; odontólogo: `id`, `nombre` y `apellido` de pacientes de sus turnos, `403 paciente_ajeno` en otro caso); `POST /pacientes`, `PATCH /pacientes/{id}`, `POST /pacientes/{id}/desactivar` (recepcionista; DD-31) |
| Turnos | `GET /turnos?desde&hasta&profesional_id&sillon_id` (agenda por rango de hasta 7 días locales `YYYY-MM-DD`, ambas incluidas; recepcionista y odontólogo, este último solo la suya; responde `{turnos, bloqueos}` con hora local; DD-32), `POST /turnos`, `PATCH /turnos/{id}/reprogramar`, `POST /turnos/{id}/cancelar` |
| Disponibilidad | `GET /disponibilidad?profesional&prestacion&fecha` |
| Auditoría | `GET /turnos/{id}/auditoria` (solo lectura, recepcionista; DD-25) |

Conflicto de solapamiento -> `409 Conflict`; fuera de horario o dentro de bloqueo -> `422`.
