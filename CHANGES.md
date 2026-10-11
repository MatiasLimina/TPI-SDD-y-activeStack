# CHANGES — Secuencia de Implementación

> Índice canónico de todos los changes del proyecto **Agenda de turnos para consultorios odontológicos (Argentina)**.
> Cada change es atómico: un agente puede implementarlo en una sesión (~4-6 horas; los marcados "pequeño" en menos).
> **Leer este archivo antes de ejecutar cualquier `/opsx:propose`.**
> Alcance: exclusivamente el MVP de la sección D.4 de `docs/discovery/informe-discovery.md`. Stack: Python + FastAPI + SQLAlchemy + PostgreSQL + Redis + JWT + Docker Compose; frontend React + TypeScript + Vite (al final).

---

## Change recomendado para el ciclo OPSX: `C-03` `crear-turno-sin-solapamientos`

- Es una única feature (no un módulo): un endpoint, una regla de dominio (intervalos `[inicio, fin)`) y una garantía en BD (`EXCLUDE USING gist`). Cubre RN-AG-01..04, 09, 10, 12, 14.
- Solo depende de C-01 (scaffolding + harness de tests) y C-02 (modelos mínimos + seed): está a 3 pasos de la raíz del grafo, sin auth ni CRUDs.
- Cada escenario (solape por profesional, por sillón, contiguo válido, sin sillón si la prestación no lo requiere, concurrencia con 1 éxito, inicio en el pasado) se traduce directo en un test automatizado, ideal para un ciclo explore → propose → apply → verify → archive.

**Change grabado para la defensa (video)**: `C-05` `reprogramar-turno`, con el ciclo OPSX completo desde cero (explore → propose → ajustar → apply → archive). C-03 se hizo antes, fuera de cámara, y es su base.

**Decisión de prerrequisitos**: auth/JWT y los CRUDs de configuración quedan FUERA de la ruta previa a C-03. En C-02 se cargan por seed profesionales, sillones, prestaciones y pacientes; `POST /turnos` nace sin autenticación (`creado_por` nullable) y C-06 le agrega la protección por rol y C-07 la auditoría. Las validaciones de horario de atención y bloqueos (RN-AG-05/06) se incorporan en C-10 y C-11; el recordatorio en C-12.

---

## Cómo usar este documento

1. Identificá el change a ejecutar y verificá que sus dependencias estén en `[x]`.
2. Leé los archivos de "Leer antes" de la KB (`knowledge-base/`).
3. Corré `/opsx:propose C-NN-nombre` (explorá antes con `/opsx:explore` si hace falta) y luego `/opsx:apply`.
4. Verificá los escenarios con tests automatizados y corré `/opsx:archive`.
5. Marcá el checkbox del Estado: `[ ]` pendiente → `[x]` completado.

---

## Árbol de dependencias

```
C-01 foundation-scaffolding-test-harness
 └── C-02 catalogo-minimo-modelos-seed
      └── C-03 crear-turno-sin-solapamientos          ★ RECOMENDADO PARA OPSX
           ├── C-04 cancelar-turno
           ├── C-05 reprogramar-turno
           └── C-06 auth-jwt-roles
                ├── C-07 auditoria-turnos            (también requiere C-04, C-05)
                ├── C-08 gestion-recursos-consultorio
                │    ├── C-10 horarios-atencion      (también C-03, C-05)
                │    └── C-11 bloqueos-agenda        (también C-04, C-05)
                ├── C-09 registro-pacientes
                └── C-13 agenda-diaria-semanal       (también C-03, C-11)
C-04, C-05 ──► C-12 recordatorios-mock-redis         (también C-01)
Backend completo ──► C-14 frontend-base-login
                      └── C-15 frontend-agenda-turnos
                           └── C-16 frontend-configuracion-pacientes-bloqueos
```

### Paralelismo por fase

```
GATE 0: C-01 ✓
  → C-02 catalogo-minimo-modelos-seed            [Agente A]   (único camino)

GATE 1: C-02 ✓
  → C-03 crear-turno-sin-solapamientos           [Agente A]   ★ OPSX

GATE 2: C-03 ✓                                    ← FORK
  → C-04 cancelar-turno                          [Agente A]
  → C-05 reprogramar-turno                       [Agente B]
  → C-06 auth-jwt-roles                          [Agente C]

GATE 3: C-06 ✓                                    ← FORK
  → C-08 gestion-recursos-consultorio            [Agente A]
  → C-09 registro-pacientes                      [Agente B]
  → C-07 auditoria-turnos                        [Agente C — si C-04 y C-05 ✓]

GATE 4: C-04 ✓ y C-05 ✓
  → C-12 recordatorios-mock-redis                [Agente B]

GATE 5: C-08 ✓                                    ← FORK
  → C-10 horarios-atencion                       [Agente A]
  → C-11 bloqueos-agenda                         [Agente B — si C-04, C-05 ✓]

GATE 6: C-10 ✓ y C-11 ✓
  → C-13 agenda-diaria-semanal                   [Agente A]

GATE 7: Backend MVP completo (C-07, C-09, C-12, C-13) ✓
  → C-14 frontend-base-login                     [Agente C]
  → C-15 frontend-agenda-turnos                  [Agente C]
  → C-16 frontend-configuracion-pacientes-bloqueos [Agente C]
```

> Nota: C-04, C-05, C-07, C-10, C-11 y C-12 tocan los mismos casos de uso de turnos; si corren en paralelo, coordinar el merge (los hooks de auditoría/recordatorio/validaciones se enchufan por puntos de extensión definidos en C-03).

### Camino crítico (12 changes — mínimo irreducible)

`C-01 → C-02 → C-03 → C-05 → C-06 → C-08 → C-10 → C-11 → C-13 → C-14 → C-15 → C-16`

C-04, C-07, C-09 y C-12 son obligatorios para el MVP pero cuelgan del camino crítico sin alargarlo.

### Plan óptimo con 3 agentes

| Paso | Agente A (Backend Core) | Agente B (Backend Aux) | Agente C (Seguridad / Frontend) |
|------|-------------------------|------------------------|---------------------------------|
| 1 | C-01 | — | — |
| 2 | C-02 | — | — |
| 3 | C-03 ★ | — | — |
| 4 | C-04 | C-05 | C-06 |
| 5 | C-08 | C-09 | C-07 |
| 6 | C-10 | C-11 | C-12 |
| 7 | C-13 | — | — |
| 8 | — | — | C-14 |
| 9 | — | — | C-15 |
| 10 | — | — | C-16 |

---

## FASE 0 — Fundaciones mínimas

### [C-01] `foundation-scaffolding-test-harness`
- **Estado**: `[x]` completado
- **Scope**:
  - Estructura `backend/app/{domain,application,infrastructure,api}` + `backend/tests/`, `pyproject.toml` (FastAPI, SQLAlchemy 2, Alembic, psycopg, pytest, httpx)
  - `docker-compose.yml` con `db` (PostgreSQL), `redis` y `api`; `.env.example` (DATABASE_URL, REDIS_URL, JWT_SECRET placeholder, APP_TIMEZONE, etc.); `.env` en `.gitignore`
  - `GET /health`; configuración por variables de entorno (Pydantic Settings)
  - Alembic inicializado + migración 001: `CREATE EXTENSION btree_gist`
  - Harness de tests: pytest con BD PostgreSQL de test (fixtures de sesión/transacción), test de humo de `/health` y de conexión a BD
  - Utilidad de tiempo: persistencia UTC, conversión a `America/Argentina/Buenos_Aires`
- **Dependencias**: ninguna
- **Governance**: BAJO
- **Leer antes**:
  - `knowledge-base/08_arquitectura_propuesta.md` §Estructura de directorios, §Variables de entorno
  - `knowledge-base/05_reglas_de_negocio.md` §RN-CU-02, RN-CU-03, RN-CU-04
  - `knowledge-base/01_vision_y_objetivos.md`

### [C-02] `catalogo-minimo-modelos-seed`
- **Estado**: `[x]` completado
- **Scope** (change pequeño; sin endpoints):
  - Modelos SQLAlchemy: `Profesional`, `Sillon`, `Prestacion` (`duracion_min > 0`, `requiere_sillon` default true), `Paciente`
  - Migración 002 con las cuatro tablas
  - Script de seed (todo ficticio): 2 profesionales, 2 sillones, 3-4 prestaciones (p. ej. Consulta 30 min sin sillón; Limpieza 45 min y Conservadora 60 min con sillón), 3-5 pacientes
  - Tests: el seed es idempotente y respeta los constraints (duración > 0)
  - Sin usuarios, horarios, bloqueos ni CRUD (diferidos a C-06, C-08, C-09, C-10, C-11)
- **Dependencias**: `C-01`
- **Governance**: ALTO (modelos core referenciados por todo lo demás; sin datos reales ni auth)
- **Leer antes**:
  - `knowledge-base/04_modelo_de_datos.md` §Profesional, §Sillon, §Prestacion, §Paciente, §Seed data inicial
  - `knowledge-base/05_reglas_de_negocio.md` §RN-AG-10, RN-CU-02
  - `knowledge-base/09_decisiones_y_supuestos.md`

---

## FASE 1 — Núcleo de agenda (turnos)

### [C-03] `crear-turno-sin-solapamientos`  ★ RECOMENDADO PARA EL CICLO OPSX
- **Estado**: `[x]` completado
- **Scope** (US-004 parcial; una sola feature):
  - Modelo `Turno` + migración 003: `profesional_id`, `sillon_id` NULLABLE, `paciente_id`, `prestacion_id`, `inicio`, `fin`, `duracion_min`, `estado` (`programado|cancelado`), `creado_por` NULLABLE (se completa en C-06), timestamps
  - Constraints en BD: `ck_turno_fin_mayor CHECK (fin > inicio)`, `ck_turno_estado_valido`, `turno_sin_solape_profesional`, `turno_sin_solape_sillon` y `turno_sin_solape_paciente` (`EXCLUDE USING gist ... tstzrange(inicio, fin, '[)')` parciales `estado <> 'cancelado'`) — RN-AG-09, RN-AG-14 (DD-20)
  - `estado` se persiste como `varchar` + `CHECK (estado IN ('programado','cancelado'))`, no enum nativo (DD-21)
  - Dominio puro: cálculo de `fin = inicio + duración efectiva` (por defecto `Prestacion.duracion_min`, ajustable; RN-AG-04) y regla de solape semiabierto (RN-AG-03)
  - Regla del sillón según la prestación: requerido si `requiere_sillon` (falta -> 422), no ocupa sillón si no lo requiere (RN-AG-10)
  - Validación de duración y grilla (DD-15): duración efectiva múltiplo de 5 min y ≤ 480 min, inicio alineado a 5 min en hora local -> 422 (RN-AG-04)
  - Rechazo de inicio en el pasado -> 422 (RN-AG-12); recursos inactivos -> 422; sin sobreturnos (RN-AG-11)
  - `POST /turnos` -> 201; solape (profesional, sillón o paciente) -> 409 que lista **todos** los recursos en conflicto (pre-chequeo en la aplicación) y, ante carreras, traducción de SQLSTATE `23P01` indicando el recurso deducido de `constraint_name` (DD-21)
  - `sillon_id` informado con una prestación que no requiere sillón -> 422; referencia inexistente en el body (profesional, paciente, prestación, sillón) -> 422, igual que un recurso inactivo (DD-21)
  - Puntos de extensión (hooks) en el caso de uso para auditoría, validaciones de horario/bloqueo y recordatorio, sin implementarlos
  - Tests (uno por escenario): solape por profesional; solape por sillón; contiguo (fin = inicio siguiente) aceptado; mismo horario en distinto profesional y distinto sillón aceptado; duración por defecto y ajustada; prestación sin sillón no genera conflicto de sillón; sillón faltante con prestación que lo requiere -> 422; solape por paciente con distinto profesional -> 409; mismo paciente en turnos contiguos aceptado; prestación sin sillón con `sillon_id` informado -> 422; ID inexistente en el body -> 422; 409 que lista varios recursos en conflicto; inicio pasado -> 422; duración no múltiplo de 5, mayor a 480 o inicio no alineado -> 422; concurrencia (N inserciones simultáneas del mismo horario, exactamente 1 éxito); unit tests del dominio sin BD
  - Fuera de este change: auth, auditoría, recordatorio, horario de atención, bloqueos, reprogramar, cancelar
- **Dependencias**: `C-02`
- **Governance**: MEDIO
- **Leer antes**:
  - `knowledge-base/05_reglas_de_negocio.md` §RN-AG-01..04, RN-AG-09..12, RN-AG-14, §Excepciones globales
  - `knowledge-base/04_modelo_de_datos.md` §Turno (DDL de constraints)
  - `knowledge-base/07_flujos_principales.md` §Flujo 2
  - `knowledge-base/08_arquitectura_propuesta.md` §Concurrencia y no superposición
  - `knowledge-base/06_funcionalidades.md` §US-004
  - `knowledge-base/09_decisiones_y_supuestos.md` §DD-20, §DD-21

### [C-04] `cancelar-turno`
- **Estado**: `[ ]` pendiente
- **Scope** (US-006 parcial):
  - `POST /turnos/{id}/cancelar` (motivo opcional): `estado = cancelado`, `motivo_cancelacion`; no se borra
  - El horario se puede reservar de inmediato (el índice parcial ignora cancelados; RN-AG-07)
  - Cancelar un turno ya cancelado -> 409 (Suposición documentada); inexistente -> 404
  - Cancelar un turno ya iniciado o pasado -> 409; se cancela hasta el inicio, sin política de cancelación tardía (RN-AG-13, DD-14)
  - Tests: cancelar libera el horario y permite crear otro turno en el mismo intervalo; el cancelado no cuenta para solapes; turno iniciado -> 409
  - Auditoría y recordatorio se enchufan en C-07 y C-12
- **Dependencias**: `C-03`
- **Governance**: MEDIO
- **Leer antes**:
  - `knowledge-base/05_reglas_de_negocio.md` §RN-AG-07
  - `knowledge-base/07_flujos_principales.md` §Flujo 4
  - `knowledge-base/06_funcionalidades.md` §US-006
  - `knowledge-base/09_decisiones_y_supuestos.md` §DD-14

### [C-05] `reprogramar-turno`
- **Estado**: `[ ]` pendiente
- **Scope** (US-005 parcial):
  - `PATCH /turnos/{id}/reprogramar` (inicio, profesional, sillón, duración): mismas validaciones que crear excluyendo al propio turno (RN-AG-08; la exclusión del propio turno aplica también al chequeo por paciente, RN-AG-14), mismo inicio-no-pasado (RN-AG-12) y misma validación de duración y grilla de 5 min (RN-AG-04, DD-15; 422)
  - UPDATE de la misma fila dentro de una transacción; si falla (409/422) el turno original queda intacto
  - Tests: duración inválida o inicio no alineado -> 422 con original intacto; reprogramar a hueco libre; a hueco ocupado -> 409 con original intacto; solaparse consigo mismo es válido; cambiar de profesional y de sillón; turno cancelado no reprogramable
  - Auditoría y recordatorio se enchufan en C-07 y C-12
- **Dependencias**: `C-03`
- **Governance**: MEDIO
- **Leer antes**:
  - `knowledge-base/05_reglas_de_negocio.md` §RN-AG-08
  - `knowledge-base/07_flujos_principales.md` §Flujo 3
  - `knowledge-base/06_funcionalidades.md` §US-005

---

## FASE 2 — Seguridad y cumplimiento

### [C-06] `auth-jwt-roles`
- **Estado**: `[ ]` pendiente
- **Scope** (US-010):
  - Modelo `Usuario` (email único, `password_hash` bcrypt/argon2, `rol` `recepcionista|odontologo`, `profesional_id` obligatorio si odontólogo, `activo`) + migración; seed de 1 recepcionista y 2 odontólogos (credenciales de desarrollo ficticias en `.env.example`/seed)
  - `POST /auth/login` -> JWT con `sub`, `rol`, `profesional_id`, expiración corta (`JWT_EXPIRE_MINUTES`); credenciales inválidas 401, token vencido 401, rol insuficiente 403
  - Dependencias FastAPI de RBAC; se protegen `POST /turnos`, cancelar y reprogramar (solo recepcionista); `creado_por` pasa a poblarse
  - Comando CLI de alta y desactivación de usuarios (sin UI ni endpoint; la baja es `activo = false`, nunca borrado; DD-16)
  - Tests: login válido/inválido, token expirado, acceso por rol a cada endpoint existente, `creado_por` registrado; CLI de alta y desactivación (un usuario desactivado no inicia sesión)
- **Dependencias**: `C-03`
- **Governance**: CRITICO
- **Leer antes**:
  - `knowledge-base/03_actores_y_roles.md`
  - `knowledge-base/05_reglas_de_negocio.md` §RN-AU-01..03
  - `knowledge-base/07_flujos_principales.md` §Flujo 1
  - `knowledge-base/08_arquitectura_propuesta.md` §Seguridad

### [C-07] `auditoria-turnos`
- **Estado**: `[ ]` pendiente
- **Scope** (US-011):
  - Modelo `TurnoAuditoria` append-only (`turno_id`, `usuario_id`, `accion` `crear|reprogramar|cancelar`, `valores_previos`/`valores_nuevos` jsonb, `ocurrido_en` UTC) + migración (sin UPDATE/DELETE desde la aplicación; opcionalmente trigger que lo impida)
  - Registro dentro de la misma transacción en crear, reprogramar y cancelar (si falla la auditoría, el cambio se revierte)
  - `GET /turnos/{id}/auditoria` (solo recepcionista)
  - Tests: una fila por acción con valores previos/nuevos; rollback conjunto; append-only; acceso por rol
- **Dependencias**: `C-06, C-04, C-05`
- **Governance**: CRITICO
- **Leer antes**:
  - `knowledge-base/05_reglas_de_negocio.md` §RN-CU-01
  - `knowledge-base/04_modelo_de_datos.md` §TurnoAuditoria
  - `knowledge-base/06_funcionalidades.md` §US-011

---

## FASE 3 — Configuración, pacientes, horarios y bloqueos

### [C-08] `gestion-recursos-consultorio`
- **Estado**: `[ ]` pendiente
- **Scope** (US-001):
  - CRUD de profesionales, sillones y prestaciones: `/profesionales`, `/sillones`, `/prestaciones` (alta, edición, desactivación lógica)
  - Validaciones: `duracion_min > 0`, múltiplo de 5 y ≤ 480 (con CHECK en BD; DD-15), `requiere_sillon`; recurso desactivado no admite turnos nuevos pero conserva historial
  - Escritura solo recepcionista; el odontólogo solo lee (RN-AU-03)
  - Tests: CRUD por rol, desactivación bloquea turnos nuevos (422) y conserva los existentes
- **Dependencias**: `C-06`
- **Governance**: BAJO
- **Leer antes**:
  - `knowledge-base/06_funcionalidades.md` §US-001
  - `knowledge-base/04_modelo_de_datos.md` §Profesional, §Sillon, §Prestacion
  - `knowledge-base/05_reglas_de_negocio.md` §RN-AU-03

### [C-09] `registro-pacientes`
- **Estado**: `[ ]` pendiente
- **Scope** (US-009):
  - `POST/GET/PATCH /pacientes` y búsqueda por nombre/apellido/documento (datos ficticios, sin ficha clínica ni odontograma)
  - Desactivación lógica; roles: recepcionista escribe; odontólogo lectura mínima
  - Tests: alta, búsqueda, validaciones de campos mínimos, permisos
- **Dependencias**: `C-06`
- **Governance**: BAJO
- **Leer antes**:
  - `knowledge-base/06_funcionalidades.md` §US-009
  - `knowledge-base/04_modelo_de_datos.md` §Paciente
  - `knowledge-base/05_reglas_de_negocio.md` §RN-CU-02

### [C-10] `horarios-atencion`
- **Estado**: `[ ]` pendiente
- **Scope** (US-002):
  - Modelo `HorarioAtencion` (`profesional_id`, `dia_semana` 0-6, `hora_inicio`, `hora_fin`, varias franjas por día) + migración
  - `/profesionales/{id}/horarios` CRUD (solo recepcionista); semilla de ejemplo L-V mañana y tarde
  - Validación RN-AG-05 integrada en crear (C-03) y reprogramar (C-05): el intervalo completo debe caber en una franja (hora local `America/Argentina/Buenos_Aires` convertida a UTC) -> 422
  - Tests: dentro/fuera de franja, borde exacto de fin, varias franjas, intervalo que cruza dos franjas rechazado
- **Dependencias**: `C-08, C-03, C-05`
- **Governance**: MEDIO
- **Leer antes**:
  - `knowledge-base/05_reglas_de_negocio.md` §RN-HB-01, RN-AG-05, RN-CU-04
  - `knowledge-base/04_modelo_de_datos.md` §HorarioAtencion
  - `knowledge-base/06_funcionalidades.md` §US-002

### [C-11] `bloqueos-agenda`
- **Estado**: `[ ]` pendiente
- **Scope** (US-003):
  - Modelo `Bloqueo` (`profesional_id`, `inicio`, `fin`, `motivo`, `creado_por`) + migración
  - `POST /bloqueos`, `GET`, `DELETE`; el odontólogo fuerza `profesional_id` del token y solo bloquea lo suyo; la recepcionista cualquiera (RN-HB-02, RN-AU-02)
  - Bloqueo sobre intervalo con turnos activos -> 409 con lista de turnos afectados (RN-HB-03)
  - Validación RN-AG-06 integrada en crear y reprogramar: solape con bloqueo -> 422; empezar justo al terminar el bloqueo es válido
  - Tests: permisos por rol, 409 con turnos afectados, turno vs bloqueo (solapa/contiguo)
- **Dependencias**: `C-08, C-04, C-05, C-06`
- **Governance**: MEDIO
- **Leer antes**:
  - `knowledge-base/05_reglas_de_negocio.md` §RN-HB-02, RN-HB-03, RN-AG-06
  - `knowledge-base/07_flujos_principales.md` §Flujo 5
  - `knowledge-base/06_funcionalidades.md` §US-003

---

## FASE 4 — Recordatorios y consulta de agenda

### [C-12] `recordatorios-mock-redis`
- **Estado**: `[ ]` pendiente
- **Scope** (US-012):
  - Puerto `NotificationSender` (dominio) + adaptador `MockSender` (registra el envío, sin mensajería real); `NOTIFICATION_ADAPTER=mock`
  - Modelo `Recordatorio` (`turno_id`, `programado_para`, `estado`, `canal=mock`, `intentos`) + migración
  - Se crea en la misma transacción que el turno; cancelar lo cancela y reprogramar lo reprograma (RN-NO-02)
  - Cola Redis + worker con reintentos acotados; verifica que el turno siga activo; re-encola pendientes de BD al reiniciar
  - Anticipación de 24 h (`REMINDER_LEAD_HOURS=24`); si el turno se crea o reprograma con menos de 24 h, no se programa recordatorio (RN-NO-03, DD-13); contenido sin datos clínicos (RN-NO-04)
  - Reintentos: 3 intentos con backoff exponencial; agotados, `estado = fallido`; sin reintento manual (RN-NO-05, DD-19)
  - Tests: encolado al crear, sin recordatorio con menos de 24 h, ajuste al cancelar/reprogramar, worker invoca el puerto (mock), 3 reintentos y `fallido`, turno cancelado no envía
- **Dependencias**: `C-04, C-05, C-01`
- **Governance**: ALTO
- **Leer antes**:
  - `knowledge-base/05_reglas_de_negocio.md` §RN-NO-01..04
  - `knowledge-base/07_flujos_principales.md` §Flujo 6
  - `knowledge-base/04_modelo_de_datos.md` §Recordatorio
  - `knowledge-base/08_arquitectura_propuesta.md` §Patrones aplicados
  - `knowledge-base/09_decisiones_y_supuestos.md` §DD-13, §DD-19

### [C-13] `agenda-diaria-semanal`
- **Estado**: `[ ]` pendiente
- **Scope** (US-008, backend):
  - `GET /turnos?desde&hasta&profesional&sillon` (rango local -> UTC, respuesta en UTC) para vistas diaria/semanal multiprofesional y multisillón; incluye bloqueos en la respuesta de agenda
  - El odontólogo queda filtrado a su `profesional_id` (RN-AU-02)
  - Tests: filtros, rangos diario/semanal, aislamiento del odontólogo, conversión de zona horaria
- **Dependencias**: `C-06, C-03, C-11`
- **Governance**: MEDIO
- **Leer antes**:
  - `knowledge-base/07_flujos_principales.md` §Flujo 7
  - `knowledge-base/06_funcionalidades.md` §US-008
  - `knowledge-base/05_reglas_de_negocio.md` §RN-AU-02, RN-CU-04

---

## FASE 5 — Frontend (React + TypeScript + Vite) — AL FINAL

> El backend MVP completo debe estar estable antes de empezar. No es requisito de la consigna.

### [C-14] `frontend-base-login`
- **Estado**: `[ ]` pendiente
- **Scope**:
  - Scaffolding Vite + React + TypeScript en `frontend/` (features/, shared/, pages/), cliente HTTP con JWT, `CORS_ORIGINS`
  - Página de login, guardas de ruta por rol, layout; servicio `frontend` en Docker Compose
  - Tests: login, redirección por rol
- **Dependencias**: `C-06, C-13`
- **Governance**: BAJO
- **Leer antes**:
  - `knowledge-base/08_arquitectura_propuesta.md` §Estructura de directorios, §Seguridad
  - `knowledge-base/03_actores_y_roles.md`
  - `knowledge-base/07_flujos_principales.md` §Flujo 1

### [C-15] `frontend-agenda-turnos`
- **Estado**: `[ ]` pendiente
- **Scope**:
  - Agenda diaria y semanal filtrable por profesional/sillón (horarios en `America/Argentina/Buenos_Aires`)
  - Formularios de crear, reprogramar y cancelar turno con manejo de 409/422 y selector de paciente
  - Tests de componentes de agenda y formulario de turno
- **Dependencias**: `C-14, C-12, C-07, C-09`
- **Governance**: MEDIO
- **Leer antes**:
  - `knowledge-base/06_funcionalidades.md` §Épica 2, §US-008
  - `knowledge-base/07_flujos_principales.md` §Flujos 2, 3, 4, 7
  - `knowledge-base/08_arquitectura_propuesta.md`

### [C-16] `frontend-configuracion-pacientes-bloqueos`
- **Estado**: `[ ]` pendiente
- **Scope**:
  - Pantallas de profesionales, sillones, prestaciones, horarios de atención, pacientes y bloqueos
  - Vista de auditoría de un turno (recepcionista)
  - Tests de formularios y permisos por rol
- **Dependencias**: `C-15, C-08, C-10, C-11`
- **Governance**: BAJO
- **Leer antes**:
  - `knowledge-base/06_funcionalidades.md` §Épicas 1, 4, 5
  - `knowledge-base/05_reglas_de_negocio.md` §RN-HB, RN-AU
  - `knowledge-base/08_arquitectura_propuesta.md` §Estructura de directorios

---

## Resumen

| ID | Change | Fase | Deps | Gov. |
|----|--------|------|------|------|
| C-01 | foundation-scaffolding-test-harness | 0 | — | BAJO |
| C-02 | catalogo-minimo-modelos-seed | 0 | C-01 | ALTO |
| C-03 | crear-turno-sin-solapamientos ★ | 1 | C-02 | MEDIO |
| C-04 | cancelar-turno | 1 | C-03 | MEDIO |
| C-05 | reprogramar-turno | 1 | C-03 | MEDIO |
| C-06 | auth-jwt-roles | 2 | C-03 | CRITICO |
| C-07 | auditoria-turnos | 2 | C-06, C-04, C-05 | CRITICO |
| C-08 | gestion-recursos-consultorio | 3 | C-06 | BAJO |
| C-09 | registro-pacientes | 3 | C-06 | BAJO |
| C-10 | horarios-atencion | 3 | C-08, C-03, C-05 | MEDIO |
| C-11 | bloqueos-agenda | 3 | C-08, C-04, C-05, C-06 | MEDIO |
| C-12 | recordatorios-mock-redis | 4 | C-04, C-05, C-01 | ALTO |
| C-13 | agenda-diaria-semanal | 4 | C-06, C-03, C-11 | MEDIO |
| C-14 | frontend-base-login | 5 | C-06, C-13 | BAJO |
| C-15 | frontend-agenda-turnos | 5 | C-14, C-12, C-07, C-09 | MEDIO |
| C-16 | frontend-configuracion-pacientes-bloqueos | 5 | C-15, C-08, C-10, C-11 | BAJO |

**Primer change a ejecutar en el ciclo OPSX**: `C-03` (requiere C-01 y C-02 previos). Arranque: `/opsx:propose C-03-crear-turno-sin-solapamientos`.

---

## Fuera de alcance / backlog (no son changes)

Diferido por el Discovery (ver `docs/discovery/informe-discovery.md` §D.3 y §D.4 "Ajuste de alcance del MVP"). **No implementar** en este roadmap:

- Enlace público de reserva y autogestión del paciente
- WhatsApp Business API real (solo puerto + adaptador mock en C-12)
- Lista de espera con oferta automática
- Sobreturnos (RN-AG-11: todo solape se rechaza)
- Seña / pagos con Mercado Pago
- Ficha clínica, anamnesis y odontograma
- Presupuestos y caja
- Facturación ARCA
- Obras sociales y prepagas
- Panel de ausentismo y ocupación de sillones (no-show dashboard)
- Multisede / multi-sucursal
- Política de cancelación tardía (decidido DD-14: sin política en el MVP)
- Consulta de disponibilidad / huecos libres (US-007): no figura en D.4, es una suposición de la KB y se acopla naturalmente con el enlace público de reserva diferido (D.3)
