# Revisión de escenarios — auth-jwt-roles (C-06)

- Fecha: 2026-10-28
- Specs revisados: `specs/autenticacion/spec.md`, `specs/usuarios/spec.md`, `specs/agenda-turnos/spec.md`, `specs/datos-semilla/spec.md`, `specs/app-configuration/spec.md` (89 escenarios), contrastados con `proposal.md`, `design.md`, `tasks.md`, `CHANGES.md` §C-06, KB (03, 04, 05, 07, 08, 09, 10) y `openspec/specs/agenda-turnos`.
- Reglas aplicables: RN-AU-01 (JWT, 2 roles), RN-AU-02/03 (fuera de scope: lectura y configuración llegan con C-08/C-13), RN-CU-01 (acceso por rol; la auditoría es C-07), RN-CU-02 (datos ficticios), RN-CU-03 (sin secretos), RN-CU-04 (UTC); DD-05 (sin admin), DD-16 (alta por seed/CLI, baja lógica), Flujo 1 (401/403/401), matriz de `03_actores_y_roles.md` (turnos C/U/D solo recepcionista), `08` §Seguridad (argon2, RBAC por dependencia).
- Veredicto: CORREGIR ANTES DE APPLY (0 BLOQUEANTE, 3 MAYOR, 4 MENOR, 2 SUGERENCIA; los tres MAYOR son de registro/redacción y el equipo ya aceptó las decisiones de fondo)

## Cobertura

| Requirement | Escenarios | Esperado | Error de negocio | Borde | Reglas cubiertas |
|-------------|-----------:|:--------:|:----------------:|:-----:|------------------|
| autenticacion: Inicio de sesión con credenciales válidas | 4 | 2 | 0 (el 422 es validación, no cuenta) | 1 (email con mayúsculas/espacios) | RN-AU-01, Flujo 1 |
| autenticacion: Rechazo uniforme de credenciales | 5 | 0 | 4 | 1 (contraseña vacía) | Flujo 1 (401) |
| autenticacion: Contenido y vigencia del token | 3 | 3 | 0 | 0 | Flujo 1 (claims, expiración) |
| autenticacion: Token ausente o mal formado | 3 | 0 | 3 | 0 | Flujo 1 (401) |
| autenticacion: Token inválido o vencido | 4 | 0 | 3 | 1 (sin `exp`/`sub`) | Flujo 1 (token vencido 401) |
| autenticacion: Usuario vigente en cada request | 3 | 0 | 3 | 0 | RN-AU-01, DD-16 |
| autenticacion: Rutas públicas | 4 | 3 | 0 | 1 (404 sin token) | `03` §Rutas públicas |
| usuarios: Usuario del sistema | 6 | 1 | 4 | 1 (2.º activo por profesional) | DD-05, DD-16, `04` §Usuario |
| usuarios: Contraseñas solo como hash | 3 | 2 | 0 | 1 (hash desactualizado) | `08` §Seguridad |
| usuarios: Alta por CLI | 4 | 3 | 0 | 1 (email normalizado) | DD-16 |
| usuarios: Rechazo de un alta inválida | 6 | 0 | 6 | 0 | DD-05, DD-16 |
| usuarios: Contraseña nunca como argumento | 2 | 0 | 2 | 0 | RN-CU-03 |
| usuarios: Desactivación por CLI | 4 | 1 | 2 | 1 (idempotente) | DD-16 |
| agenda-turnos: Creación (MODIFIED) | 3 | 1 | 1 | 1 (body con `creado_por` ajeno) | RN-CU-01, RN-CU-04 |
| agenda-turnos: Cancelación (MODIFIED) | 2 | 1 | 0 | 1 (cancelar no cambia autor) | DD-08 |
| agenda-turnos: Reprogramación (MODIFIED) | 3 | 2 | 0 | 1 (reprogramar no cambia autor) | DD-23 |
| agenda-turnos: Operaciones reservadas a la recepcionista | 6 | 0 | 4 | 2 (403 antes de 404/422) | RN-AU-01, matriz `03` |
| agenda-turnos: Autor referenciado en la base | 3 | 0 | 2 | 1 (`creado_por` nulo) | DD-16 |
| datos-semilla: Contenido (MODIFIED) | 5 | 3 | 0 | 2 (variable ausente / ninguna) | DD-16, SU-06 |
| datos-semilla: Seed idempotente (MODIFIED) | 4 | 3 | 0 | 1 (desactivado no se reactiva) | DD-16 |
| datos-semilla: Solo datos ficticios (MODIFIED) | 3 | 3 | 0 | 0 | RN-CU-02, RN-CU-03 |
| app-configuration: Fallo ante config faltante (MODIFIED) | 5 | 0 | 4 | 1 (`JWT_EXPIRE_MINUTES=1`) | RN-CU-03 |
| app-configuration: Plantilla de entorno (MODIFIED) | 4 | 4 | 0 | 0 | RN-CU-03 |

Las columnas de tipo son una clasificación aproximada (un escenario cuenta una sola vez); los totales por requirement coinciden con el spec (89 escenarios). Los tres tipos mínimos (C1) están cubiertos en el conjunto del change. Los MODIFIED conservan todos los escenarios de los requirements archivados (verificado contra `openspec/specs/agenda-turnos`); `creado_por` pasa de "vacío" a autor sin contradecir ningún escenario archivado.

Reglas del scope sin escenario: ninguna (RN-AU-01, Flujo 1, DD-16, seed de 1+2 usuarios, `creado_por`, CLI de alta/desactivación y "desactivado no inicia sesión" tienen escenario). No hay invasión de scope: C-04/C-05 se tocan solo para proteger las rutas, como pide `CHANGES.md` §C-06; auditoría (C-07) y lectura por profesional (C-13) quedan fuera.

## Hallazgos

### H1 — Seis decisiones nuevas sin registro DD en la KB · MAYOR
- **Dónde**: `autenticacion` (todos los `401 no_autenticado`, `credenciales_invalidas`, `403 rol_insuficiente`, "Usuario vigente en cada request", "Hash con parámetros desactualizados"), `usuarios` ("Usuario del sistema": email normalizado y único activo por profesional; "Alta por CLI": `USUARIO_PASSWORD`/doble prompt), `app-configuration` ("Vigencia del token no positiva").
- **Problema**: la KB solo fija credenciales inválidas 401, token vencido 401 y rol insuficiente 403. Los escenarios deciden además: token ausente/mal formado/usuario inactivo → 401 `no_autenticado`; códigos `credenciales_invalidas`/`no_autenticado`/`rol_insuficiente`; email normalizado con CHECK; a lo sumo un usuario activo por profesional (índice parcial); `JWT_EXPIRE_MINUTES <= 0` inválido; rehash en el login; contrato del CLI. `04_modelo_de_datos.md` §Usuario solo dice "email (unique)". El usuario las aceptó el 2026-10-28, pero no están en `09_decisiones_y_supuestos.md`.
- **Fuente**: `controles.md` C4 y C2; `07_flujos_principales.md` §Flujo 1; `04` §Usuario; `09` (DD-16 es la última decisión relevante).
- **Sugerencia**: registrar un DD-24 (o varios) antes de Apply con estas seis decisiones, y actualizar `04` §Usuario (email normalizado, índice parcial) y `07` §Flujo 1 (401 para token ausente/usuario inactivo). Sin cambios en los specs.

### H2 — Requirement "Rechazo de un alta inválida" enumera causas sin escenario · MAYOR
- **Dónde**: `usuarios/spec.md`, requirement "Rechazo de un alta inválida".
- **Problema**: el texto exige rechazo cuando el email "no tiene la forma `algo@algo`" y cuando el profesional "ya tiene un usuario activo", pero ningún escenario del requirement las ejercita (los escenarios cubren email repetido, odontólogo sin profesional, recepcionista con profesional, profesional inexistente/inactivo, rol inválido, contraseña vacía/distinta). `tasks.md` 8.2 sí las prueba: hoy son tests sin escenario que los respalde.
- **Fuente**: `controles.md` C2/C9; DD-16; consistencia con el índice parcial de H1.
- **Sugerencia**: agregar (a) "Email sin forma válida": `--email sin-arroba` → código distinto de `0`, sin usuario creado; (b) "Profesional con usuario activo": alta de un odontólogo para el profesional A que ya tiene uno activo → código distinto de `0`, sin usuario nuevo.

### H3 — Alta por CLI con `USUARIO_PASSWORD` definida pero vacía: resultado no definido · MAYOR
- **Dónde**: `usuarios/spec.md`, requirements "Alta de usuario por línea de comandos" y "Rechazo de un alta inválida", escenario "Contraseña vacía o confirmación distinta".
- **Problema**: el requirement dice "variable `USUARIO_PASSWORD` si está definida"; el escenario de contraseña vacía exige GIVEN "no definida" (solo prompt). Una variable definida y vacía puede leerse como "usar el prompt" o como "rechazar"; `tasks.md` 8.2 asume rechazo ("por entorno y por consola"). El resultado del test cambia según la lectura.
- **Fuente**: `controles.md` C7 (término sin definir que cambia el resultado); DD-16.
- **Sugerencia**: precisar en el requirement "definida y no vacía", o agregar el escenario "`USUARIO_PASSWORD` definida y vacía → código distinto de `0`, sin usuario" (opción a decidir por el equipo: rechazar vs. caer al prompt).

### H4 — Sin escenario de `sub` que no es UUID · MENOR
- **Dónde**: `autenticacion/spec.md`, "Token inválido o vencido" / "Usuario vigente en cada request".
- **Problema**: `tasks.md` 2.3 prueba `sub` no UUID, pero los escenarios solo usan `sub` ausente o UUID inexistente.
- **Fuente**: `controles.md` C9; `bordes-por-dominio.md` (auth).
- **Sugerencia**: sumar `sub = "abc"` al escenario "Token sin claim obligatorio" o a "Sub que no corresponde a ningún usuario" (→ 401 `no_autenticado`).

### H5 — Cuerpo "idéntico" con `mensaje` sin valor concreto · MENOR
- **Dónde**: "Rechazo uniforme de credenciales" y "Token ausente o mal formado" (`"mensaje": ...`).
- **Problema**: la igualdad de los tres rechazos depende del texto del mensaje, que no está fijado; el test compara cuerpos completos.
- **Fuente**: `controles.md` C5.
- **Sugerencia**: fijar el texto (p. ej. "Credenciales inválidas") o aclarar que `mensaje` es constante e idéntico entre casos.

### H6 — Tolerancia "pocos segundos" y reloj sin fijar en la vigencia del token · MENOR
- **Dónde**: "Contenido y vigencia del token" ("Claims de la recepcionista", "Vigencia configurable") y "Token vencido".
- **Problema**: "pocos segundos" no es un número; "exp posterior a la emisión" y "una hora anterior" no fijan el reloj. `tasks.md` 2.2 usa tolerancia de segundos sin cifra.
- **Fuente**: `controles.md` C5/C6 (bajado a MENOR porque `tasks.md` ya inyecta el emisor).
- **Sugerencia**: "tolerancia de 5 segundos" y reloj fijo/inyectado en el GIVEN.

### H7 — Faltan bordes del vencimiento y de configuración · MENOR
- **Dónde**: "Token inválido o vencido"; "Vigencia del token no positiva"; "Contenido y vigencia".
- **Problema**: no hay escenario de token que vence exactamente en el instante de uso, ni de `JWT_EXPIRE_MINUTES` no entero (`abc`), ni del default `60` (KB `08` §Variables de entorno).
- **Fuente**: `bordes-por-dominio.md` (auth); `08` §Variables; `app-configuration` ("entero mayor que cero").
- **Sugerencia**: agregar un escenario con reloj inyectado en `exp` y otro con `JWT_EXPIRE_MINUTES=abc` → falla mencionando la variable; el default `60` queda como sugerencia.

### H8 — Email de usuario inactivo no reutilizable: callejón operativo · SUGERENCIA
- **Dónde**: "Desactivación por CLI" ("No existe reactivación...") y "Email ya registrado".
- **Problema**: un usuario desactivado no puede recuperar su cuenta ni volver a darse de alta con el mismo email; la KB no dice cómo se resuelve (DD-16 solo define baja lógica). Aceptable para el MVP pero conviene registrarlo.
- **Fuente**: DD-16, `10_preguntas_abiertas.md`.
- **Sugerencia**: anotarlo como limitación en el DD de H1 o como pregunta abierta.

### H9 — Carrera en el alta CLI no especificada · SUGERENCIA
- **Dónde**: "Rechazo de un alta inválida".
- **Problema**: dos altas simultáneas del mismo email o profesional pasarían el pre-chequeo y chocarían contra el índice; no hay escenario de cómo termina el CLI (código distinto de `0`, sin traza).
- **Fuente**: DD-18 por analogía (la BD es la fuente de verdad).
- **Sugerencia**: decidir si se cubre con un escenario o se deja a la base.

## Preguntas abiertas
- ¿Se registra como DD-24 el bloque de seis decisiones de H1? (el usuario ya las aceptó; falta el registro).
- ¿Variable `USUARIO_PASSWORD` vacía: rechazar o pedir por consola? (H3).
- ¿Hay camino de reactivación o re-alta de un email desactivado en un change posterior? (H8).

## Fuera de esta revisión
- Orden efectivo de evaluación 401/403 antes de 422 en FastAPI y comportamiento de `HTTPBearer(auto_error=False)`: depende de la implementación y se verifica en Apply (`tasks.md` 7.1/7.4); el design ya lo contrastó con Context7.
- Código y migraciones: no existen aún.
