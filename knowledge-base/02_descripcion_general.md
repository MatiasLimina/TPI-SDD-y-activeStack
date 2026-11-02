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

Versiones mínimas (DD-17): Python ≥ 3.13, PostgreSQL 16, Node 22 LTS (a confirmar en C-14). Migraciones Alembic lineales, numeradas `NNN_nombre.py`, con `downgrade`.

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
| Auth | `POST /auth/login`, `POST /auth/refresh` (**Suposición**) |
| Profesionales | CRUD (recepcionista); `GET` (ambos roles) |
| Sillones | CRUD (recepcionista) |
| Prestaciones | CRUD con duración por defecto (recepcionista) |
| Horarios de atención | CRUD por profesional |
| Bloqueos | `POST/DELETE` (recepcionista cualquiera; odontólogo propios) |
| Pacientes | CRUD básico (datos ficticios) |
| Turnos | `GET /turnos?desde&hasta&profesional&sillon`, `POST /turnos`, `PATCH /turnos/{id}/reprogramar`, `POST /turnos/{id}/cancelar` |
| Disponibilidad | `GET /disponibilidad?profesional&prestacion&fecha` |
| Auditoría | `GET /turnos/{id}/auditoria` (solo lectura, recepcionista; DD-25) |

Conflicto de solapamiento -> `409 Conflict`; fuera de horario o dentro de bloqueo -> `422`.
