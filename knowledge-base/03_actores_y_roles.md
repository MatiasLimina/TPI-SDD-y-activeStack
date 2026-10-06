# Actores y Roles

## Actores del sistema

| Actor | Descripción | Cómo interactúa |
|-------|-------------|-----------------|
| Recepcionista / secretaria | Gestiona la agenda de todos los profesionales y la configuración del consultorio | Web autenticada (rol `recepcionista`) |
| Odontólogo | Profesional que atiende; ve su propia agenda | Web autenticada (rol `odontologo`) |
| Sistema (worker) | Genera y envía recordatorios | Proceso asincrónico (Redis + puerto de notificación) |
| Paciente | Receptor del recordatorio; **no** es usuario del sistema en el MVP | Recibe notificación (mock) |

Fuera del MVP: rol administrador separado y autogestión del paciente.

## RBAC — Matriz de permisos

C = crear, R = leer, U = actualizar, D = eliminar/cancelar.

| Recurso | recepcionista | odontologo |
|---------|---------------|------------|
| Profesionales | CRUD | R |
| Sillones | CRUD | R |
| Prestaciones | CRUD | R |
| Horarios de atención | CRUD (todos los profesionales) | R (propios) |
| Bloqueos de agenda | CRUD (todos) | CRD solo propios |
| Pacientes | CRU (baja lógica, **Suposición**) | R (pacientes de sus turnos, **Suposición**) |
| Turnos | C, R (todos), U (reprogramar), D (cancelar) | R solo propios |
| Recordatorios (estado) | R | R propios |
| Auditoría de turnos | R | — |
| Usuarios | Alta/baja (por seed y comando CLI en el MVP; DD-16) | — |

Control de acceso por rol exigido por Ley 25.326 / 26.529 (datos de salud). La autorización se verifica en el backend, nunca solo en la UI. Cada usuario `odontologo` se vincula a un `Profesional`.

## Rutas públicas
- `POST /auth/login`
- `GET /health` (healthcheck, sin datos)
- Ninguna ruta de datos es pública; el enlace público de reserva está fuera de alcance.
