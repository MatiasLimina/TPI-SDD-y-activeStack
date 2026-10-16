# Revisión de escenarios — auth-jwt-roles (C-06)

- Fecha: 2026-10-16
- Specs revisados: `.agents/skills/revisar-escenarios/evals/files/c06-con-defectos/spec.md` (tratado como delta spec; el change no tiene carpeta en `openspec/changes/`, no hay proposal/design/tasks)
- Reglas aplicables: RN-AU-01, RN-AU-03, RN-CU-02, RN-CU-03, RN-CU-04, DD-05, DD-16 (SU-06 resuelta por DD-16); `07_flujos_principales.md` §Flujo 1; `08_arquitectura_propuesta.md` §Seguridad; scope de C-06 en `CHANGES.md`
- Veredicto: CORREGIR ANTES DE APPLY

## Cobertura

| Requirement | Escenarios | Esperado | Error de negocio | Borde | Reglas cubiertas |
|-------------|-----------:|:--------:|:----------------:|:-----:|------------------|
| Inicio de sesión | 3 | 1 (Login válido) | 1 (Usuario desactivado, código incorrecto) | 0 (el de expiración no es verificable) | RN-AU-01 (parcial), DD-16 (parcial) |
| Protección de endpoints de turnos | 2 | 0 | 1 (Odontólogo, código incorrecto) | 0 | RN-AU-01 (parcial); un escenario invade C-07 |

Total: 5 escenarios. Ningún requirement cita su regla.

Reglas del scope sin escenario: credenciales inválidas (email inexistente y contraseña incorrecta); token vencido (existe solo como escenario vago); sin token / token alterado -> 401; protección de cancelar y reprogramar; recepcionista permitida en `POST /turnos`; `creado_por` poblado; email único; `odontologo` sin `profesional_id`; hash bcrypt/argon2; CLI de alta y desactivación (DD-16); `JWT_SECRET`/`JWT_EXPIRE_MINUTES` por entorno.

## Hallazgos

### H1 — Escenario de auditoría pertenece a C-07 · BLOQUEANTE
- **Dónde**: spec.md, requirement "Protección de endpoints de turnos", escenario "Se registra la auditoría del alta"
- **Problema**: pide insertar una fila en `turno_auditoria`. La tabla y el registro de auditoría los crea C-07, que depende de C-06. En C-06 la tabla no existe, y el escenario haría que Apply implemente algo de otro change.
- **Fuente**: `CHANGES.md` C-07 (`TurnoAuditoria`, registro en crear/reprogramar/cancelar); C-06 solo pide que `creado_por` pase a poblarse; reglas duras ("NUNCA implementar en Apply algo fuera del spec"); control C3.
- **Sugerencia**: eliminarlo y reemplazarlo por: GIVEN una recepcionista autenticada con `sub` = X; WHEN `POST /turnos` válido; THEN `201` y el turno persistido tiene `creado_por` = X.

### H2 — Odontólogo sin permiso responde 401 en vez de 403 · BLOQUEANTE
- **Dónde**: spec.md, escenario "Odontólogo no puede crear turnos"
- **Problema**: un usuario autenticado con rol insuficiente recibe `403`; `401` es para token ausente, inválido o vencido. El escenario contradice el contrato y produciría un test que fija el código equivocado.
- **Fuente**: `07_flujos_principales.md` §Flujo 1 ("rol insuficiente -> 403"); scope de C-06 en `CHANGES.md`; controles C2 y C4.
- **Sugerencia**: THEN la respuesta es `403` y no se crea ningún turno (la cuenta de turnos no cambia).

### H3 — "Token con expiración" no es verificable · BLOQUEANTE
- **Dónde**: spec.md, escenario "Token con expiración"
- **Problema**: no tiene GIVEN, no fija el reloj, no dice contra qué endpoint se presenta el token y el THEN ("maneja el token correctamente") no se puede afirmar con un `assert`. Tampoco indica el código esperado.
- **Fuente**: `07_flujos_principales.md` §Flujo 1 ("token vencido -> 401"); `CHANGES.md` C-06 (expiración por `JWT_EXPIRE_MINUTES`); controles C5 y C6.
- **Sugerencia**: GIVEN reloj fijo en 2026-10-07T09:00:00-03:00, `JWT_EXPIRE_MINUTES = 60` y un token emitido a esa hora; WHEN a las 10:00:01-03:00 se presenta en `POST /turnos`; THEN `401`. Agregar el borde: a las 09:59:59 sigue válido. El instante exacto de vencimiento (`exp` igual a ahora) es una pregunta abierta.

### H4 — Falta el escenario de borde (mínimo C1) · BLOQUEANTE
- **Dónde**: spec.md completo (falta)
- **Problema**: ningún escenario ejercita el límite exacto de una regla. Hay esperado (1) y error de negocio (2, ambos con defectos), pero cero bordes verificables.
- **Fuente**: control C1; `bordes-por-dominio.md` §Autenticación.
- **Sugerencia**: bordes candidatos: token válido 1 segundo antes de vencer vs 1 segundo después (con reloj fijo); token con firma alterada -> `401`; token con `alg: none` -> `401`; `odontologo` sin `profesional_id` rechazado en el alta.

### H5 — Usuario desactivado responde `400 Inactive user` · MAYOR
- **Dónde**: spec.md, escenario "Usuario desactivado"
- **Problema**: el código `400` y el mensaje en inglés no salen de la KB. El contrato de C-06 solo define 401 (credenciales inválidas/token vencido) y 403 (rol insuficiente). Además no dice que no se emite token, y el GIVEN no identifica al usuario.
- **Fuente**: `CHANGES.md` C-06 ("un usuario desactivado no inicia sesión"); DD-16; `07_flujos_principales.md` §Flujo 1; control C4.
- **Sugerencia**: opciones (decide el equipo): `401` (igual que credenciales inválidas) o `403`. El THEN debe decir además que la respuesta no contiene `access_token`. El código elegido va como decisión DD nueva (ver preguntas abiertas).

### H6 — Faltan los escenarios de autenticación fallida · MAYOR
- **Dónde**: requirement "Inicio de sesión" (falta)
- **Problema**: sin escenario para contraseña incorrecta, email inexistente, request sin `Authorization`, token malformado o con firma alterada.
- **Fuente**: `CHANGES.md` C-06 ("credenciales inválidas 401"; tests "login válido/inválido"); Flujo 1; `bordes-por-dominio.md`.
- **Sugerencia**: un escenario por caso, todos `401`; el de "sin header" sobre un endpoint protegido debe dar `401`, no `403`.

### H7 — Faltan permitido/prohibido por rol en cancelar y reprogramar, y `creado_por` · MAYOR
- **Dónde**: requirement "Protección de endpoints de turnos" (falta)
- **Problema**: el requirement nombra cancelar y reprogramar pero solo hay un escenario (odontólogo en `POST /turnos`). No hay escenario "permitido" de la recepcionista ni de `creado_por`.
- **Fuente**: `CHANGES.md` C-06 ("se protegen `POST /turnos`, cancelar y reprogramar (solo recepcionista); `creado_por` pasa a poblarse"; tests "acceso por rol a cada endpoint existente, `creado_por` registrado"); `03_actores_y_roles.md`.
- **Sugerencia**: par permitido (recepcionista -> 2xx) / prohibido (odontólogo -> `403`, recurso sin cambios) por cada uno de los tres endpoints, más el escenario de `creado_por` de H1.

### H8 — Faltan escenarios de usuarios, CLI y seguridad de credenciales · MAYOR
- **Dónde**: spec.md (falta un requirement de gestión de usuarios y de seguridad)
- **Problema**: el scope incluye modelo `Usuario`, CLI de alta/desactivación, hash y secretos por entorno, y nada de eso tiene escenario.
- **Fuente**: `CHANGES.md` C-06 (scope y tests); DD-16; `08_arquitectura_propuesta.md` §Seguridad; RN-CU-03.
- **Sugerencia**: escenarios: CLI de alta con email duplicado rechazado; `odontologo` sin `profesional_id` rechazado; la contraseña persistida es hash (no coincide con el texto plano); CLI de desactivación pone `activo = false` sin borrar la fila y luego el login falla; `.env.example` solo con placeholders.

### H9 — El rechazo no dice qué queda persistido · MAYOR
- **Dónde**: spec.md, escenario "Odontólogo no puede crear turnos"
- **Problema**: es una operación de escritura rechazada y el THEN no afirma que no se crea el turno.
- **Fuente**: control C5.
- **Sugerencia**: agregar "y no se persiste ningún turno nuevo".

### H10 — Redacción normativa débil · MENOR
- **Dónde**: requirement "Protección de endpoints de turnos"
- **Problema**: usa "deberían requerir"; debe ser SHALL/MUST. Ningún requirement cita reglas (RN-AU-01, DD-16).
- **Fuente**: controles C2 y C7.
- **Sugerencia**: "El sistema SHALL requerir rol `recepcionista` en `POST /turnos`, cancelar y reprogramar (RN-AU-01)."

### H11 — Valores no concretos en los GIVEN · MENOR
- **Dónde**: "Login válido de recepcionista", "Usuario desactivado", "Odontólogo no puede crear turnos"
- **Problema**: "contraseña de desarrollo" sin valor/origen (seed), usuario desactivado sin identificar, odontólogo sin email ni `profesional_id`; la redacción repite "dada/cuando/entonces" tras las palabras clave. El email `.test` ficticio está bien (RN-CU-02).
- **Fuente**: control C5 (valores concretos).
- **Sugerencia**: referenciar los usuarios del seed por email ficticio, rol y `profesional_id`; la contraseña por la variable del seed/`.env.example`, sin escribir secretos.

### H12 — Decisiones que la KB no toma · SUGERENCIA
- Ver "Preguntas abiertas".

## Preguntas abiertas
1. Código de respuesta para usuario desactivado en login (401 vs 403) y mensaje (H5).
2. ¿Email inexistente y contraseña incorrecta deben devolver exactamente la misma respuesta (evitar enumeración de usuarios)? Opciones: misma respuesta / respuestas distintas.
3. Token emitido antes de la desactivación del usuario: ¿sigue válido hasta vencer o se rechaza? (DD-16 no lo define.)
4. Token que vence exactamente en el instante del request: ¿válido o vencido? (borde de H3/H4).
5. Valor de "expiración corta": la KB deja `JWT_EXPIRE_MINUTES` por entorno (ejemplo `60` en `08_arquitectura_propuesta.md`); confirmar el default.

## Fuera de esta revisión
- No existe `proposal.md`, `design.md` ni `tasks.md`: no se aplicó C9.
- Los specs archivados en `openspec/specs/` no tienen una sección "Excepciones globales" para auth; el contrato HTTP se contrastó con la KB y `CHANGES.md`.
- No se corrió `openspec status` (el change no existe en el CLI).
- RN-AU-02 (agenda propia del odontólogo, C-13) y la auditoría (C-07) quedan fuera de C-06 y no se piden.
