# Revisión de escenarios — auth-jwt-roles (C-06) — segunda pasada

- Fecha: 2026-10-28
- Revisión anterior: `revision-escenarios-v1.md` (primera pasada, conservada como evidencia)
- Specs revisados: `specs/autenticacion/spec.md`, `specs/usuarios/spec.md`, `specs/agenda-turnos/spec.md`, `specs/datos-semilla/spec.md`, `specs/app-configuration/spec.md` (96 escenarios), contrastados con `proposal.md`, `design.md`, `tasks.md`, `CHANGES.md` §C-06 y backlog, KB (04, 07, 09 §DD-24, 10) y `openspec/specs/agenda-turnos`.
- Reglas aplicables: RN-AU-01, RN-CU-01..04, DD-05, DD-16, DD-24 (nuevo), SU-06, Flujo 1, matriz de `03_actores_y_roles.md`, `08` §Seguridad. Fuera de scope (no se exige): RN-AU-02/03 (C-08/C-13), auditoría (C-07).
- Veredicto: LISTO PARA APPLY (0 BLOQUEANTE, 0 MAYOR, 2 MENOR, 0 SUGERENCIA nuevas)

## Seguimiento de la revisión anterior

| Hallazgo v1 | Sev. | Estado | Evidencia |
|---|---|---|---|
| H1 Decisiones sin DD | MAYOR | Cerrado | `09` §DD-24 (a)-(j) cubre códigos, normalización de email, índice parcial por profesional, `JWT_EXPIRE_MINUTES`, rehash, contrato del CLI, seed y no reactivación; `04` §Usuario (índice parcial); `07` §Flujo 1 (errores); `10` filas 92-98. Los specs citan DD-24 en cada requirement afectado. |
| H2 Alta inválida sin escenarios | MAYOR | Cerrado | `usuarios`, "Rechazo de un alta inválida": "Email sin forma válida" y "Profesional con usuario activo" (9 escenarios, cubren cada causa enumerada). |
| H3 `USUARIO_PASSWORD` vacía | MAYOR | Cerrado | DD-24 (h) decide rechazar; requirement "Alta por CLI" dice "definida y no vacía"; escenario "USUARIO_PASSWORD definida y vacía" (exit != 0, sin prompt). |
| H4 `sub` no UUID | MENOR | Cerrado | `autenticacion`, "Token inválido o vencido", escenario "Sub que no es un UUID". |
| H5 `mensaje` sin valor | MENOR | Cerrado (parcial, ver N1) | Literales `"Credenciales inválidas"` y `"No autenticado"` en los requirements de login y token. |
| H6 "pocos segundos" | MENOR | Cerrado | "Contenido y vigencia": tolerancia de 5 s con ventana `t0`/`t1`; "Token recién vencido" / "a punto de vencer" con `exp` explícito (±60 s). |
| H7 Bordes de vencimiento/config | MENOR | Cerrado | `app-configuration`: "Vigencia del token no numérica" (`abc`) y "Vigencia mínima aceptada"; borde de `exp` reemplazado por ±60 s (coherente con D15, sin reloj JWT inyectado); default `60` ya cubierto en el spec archivado de app-configuration. |
| H8 Email de inactivo no reutilizable | SUGERENCIA | Aceptado como limitación | DD-24 (j); `CHANGES.md` backlog "Reactivación de usuarios"; `design.md` Risks; requirement "Desactivación" lo declara. |
| H9 Carrera en alta CLI | SUGERENCIA | Aceptado como riesgo conocido | `design.md` Risks ("Carrera entre dos altas..."), la base garantiza unicidad; sin escenario por decisión del equipo. |

## Cobertura

| Requirement | Escenarios | Esperado | Error de negocio | Borde | Reglas cubiertas |
|-------------|-----------:|:--------:|:----------------:|:-----:|------------------|
| autenticacion: Inicio de sesión válido | 4 | 2 | 0 (422 es validación) | 2 | RN-AU-01, DD-24(c)(d) |
| autenticacion: Rechazo uniforme | 5 | 0 | 4 | 1 | DD-24(a) |
| autenticacion: Contenido y vigencia | 3 | 3 | 0 | 0 | Flujo 1, DD-24(f) |
| autenticacion: Token ausente/mal formado | 3 | 0 | 3 | 0 | DD-24(b) |
| autenticacion: Token inválido o vencido | 7 | 1 | 4 | 2 | DD-24(b) |
| autenticacion: Usuario vigente | 3 | 0 | 3 | 0 | RN-AU-01, DD-24(b) |
| autenticacion: Rutas públicas | 4 | 3 | 0 | 1 | `03` §Rutas públicas |
| usuarios: Usuario del sistema | 6 | 1 | 4 | 1 | DD-05, DD-16, DD-24(d)(e) |
| usuarios: Hash | 3 | 2 | 0 | 1 | `08` §Seguridad, DD-24(g) |
| usuarios: Alta por CLI | 4 | 3 | 0 | 1 | DD-16, DD-24(h) |
| usuarios: Rechazo de alta inválida | 9 | 0 | 9 | 0 | DD-16, DD-24(h) |
| usuarios: Contraseña nunca como argumento | 2 | 0 | 2 | 0 | RN-CU-03 |
| usuarios: Desactivación | 4 | 1 | 2 | 1 | DD-16, DD-24(j) |
| agenda-turnos: Creación / Cancelación / Reprogramación (MODIFIED) | 3 / 2 / 3 | 4 | 1 | 3 | RN-CU-01, DD-08, DD-23 |
| agenda-turnos: Operaciones reservadas a recepcionista | 6 | 0 | 4 | 2 | RN-AU-01, DD-24(b) |
| agenda-turnos: Autor referenciado | 3 | 0 | 2 | 1 | DD-16 |
| datos-semilla: Contenido / Idempotente / Ficticios | 5 / 4 / 3 | 9 | 0 | 3 | DD-16, DD-24(i), RN-CU-02/03 |
| app-configuration: Config faltante / Plantilla | 6 / 4 | 4 | 5 | 1 | RN-CU-03, DD-24(f) |

Totales por spec verificados con conteo de `#### Scenario`: autenticacion 29, usuarios 28, agenda-turnos 17, datos-semilla 12, app-configuration 10 = 96. Los tres tipos mínimos (C1) están cubiertos. Los MODIFIED conservan los escenarios archivados; `creado_por` pasa de vacío a autor sin contradecir ninguno.

Reglas del scope sin escenario: ninguna. Sin invasión: C-04/C-05 se modifican solo para protegerlas, como pide `CHANGES.md` §C-06; auditoría, lectura por profesional, rate limiting y largo de `JWT_SECRET` quedan fuera y figuran en backlog.

## Hallazgos nuevos

### N1 — Mensaje de `rol_insuficiente` sin valor fijado · MENOR
- **Dónde**: `agenda-turnos`, requirement "Operaciones reservadas a la recepcionista" (`"mensaje": ...`).
- **Problema**: los 401 fijan el texto del mensaje; el 403 no. Los escenarios solo verifican `detail.codigo`, así que no bloquea.
- **Fuente**: `controles.md` C5; DD-24(b).
- **Sugerencia**: fijar un literal (p. ej. "Rol insuficiente") si se toca el spec.

### N2 — Seed con variable definida y vacía sin escenario · MENOR
- **Dónde**: `datos-semilla`, "Contenido del seed" (texto: "definida y no vacía"; DD-24(i): "ausente o vacía omite ese usuario").
- **Problema**: los escenarios cubren variable ausente y ninguna variable, pero no el valor vacío, que es el análogo exacto de H3 en el CLI.
- **Fuente**: `controles.md` C2/C9; DD-24(i).
- **Sugerencia**: agregar "Variable de contraseña vacía": `SEED_ODONTOLOGO_2_PASSWORD=""` → no se crea ese usuario y el catálogo se carga sin error.

## Preguntas abiertas
Ninguna nueva. Las de v1 quedaron resueltas en `10_preguntas_abiertas.md` (DD-24).

## Fuera de esta revisión
- Orden efectivo 401/403 antes de 422 y `HTTPBearer(auto_error=False)`: se verifica en Apply (`tasks.md` 7.1/7.4).
- Código y migraciones: aún no existen.
