# Aplicación de la skill propia y del MCP en un change real

Proyecto: Turnos y Agenda para Consultorios Odontológicos · Fecha: 2026-10-28 · Change: `C-06` `auth-jwt-roles`

Este documento sigue a [investigacion.md](investigacion.md): allí se justificó qué skill y qué MCP se
instalaban; acá se registra cómo se usaron en el ciclo OPSX completo de C-06, con la evidencia de cada paso.

## 1. Contexto

C-06 es el change de autenticación (JWT, dos roles, usuarios por CLI y seed). Lo elegí en la ficha de
investigación (§1) por tres motivos: depende solo de C-03, está en el camino crítico y es de governance
CRÍTICO, así que un error en el spec se paga caro. Además, la KB dice "JWT firmado" y "bcrypt/argon2" pero no
fija librería ni API, que es justo el hueco que cubre un MCP de documentación.

Orden de trabajo del 2026-10-28:

1. `/opsx:explore` de C-06, con consultas a Context7.
2. `/opsx:propose`: 5 delta specs con 89 escenarios.
3. `revisar-escenarios`, primera pasada.
4. Decisiones mías sobre los hallazgos, DD-24 en la KB y `/opsx:update`.
5. `revisar-escenarios`, segunda pasada.
6. `/opsx:apply` con TDD estricto y revisión final del advisor.
7. `/opsx:archive`.

## 2. Uso del MCP Context7

**Cuándo**: en el explore y en el propose, antes de fijar en `design.md` cualquier API de terceros. Las
consultas las hizo un sub-agente de solo lectura. Para la conexión y la primera prueba del servidor ver
[evidencias/mcp-context7.md](evidencias/mcp-context7.md) (2026-10-16).

**Regla de privacidad**: todas las consultas fueron genéricas sobre la librería. No se envió código del
proyecto, secretos, `.env` ni datos de pacientes (límite fijado en [mcp.md](mcp.md)).

| Biblioteca (id) | Pregunta | Hallazgo |
|---|---|---|
| `pwdlib` → `/frankie567/pwdlib` | hash, verificación y hash señuelo con argon2 | Id confirmado (score 87,65) |
| `/frankie567/pwdlib` | `recommended`, `verify_and_update`, extras | argon2 viene con `pwdlib[argon2]`; `verify_and_update` devuelve `(valido, hash_nuevo \| None)` |
| `/websites/fastapi_tiangolo` | `OAuth2PasswordBearer` frente a `HTTPBearer`, form frente a JSON, 401 frente a 403 | Desde FastAPI 0.122 se responde 401 sin header (antes 403); el form OAuth2 exige `username`/`password` como form-data; patrón `DUMMY_HASH`; el tutorial devuelve 400 al usuario inactivo |
| `/jpadilla/pyjwt` | claims obligatorios y largo de clave HS256 | `options={"require": ["exp", "sub"]}` levanta `MissingRequiredClaimError`; HS256 pide clave de al menos 256 bits y solo avisa salvo `enforce_minimum_key_length=True` |

**Qué cambió en el diseño** (detalle en la sección "Consulta a Context7" de
[design.md](../../openspec/changes/archive/2026-10-28-auth-jwt-roles/design.md)):

| Decisión | Origen | Resultado |
|---|---|---|
| Usuario inactivo | El tutorial responde `400`. **Prevaleció la KB**: se mantiene `401` uniforme, igual al de credenciales inválidas, para no revelar que la cuenta existe (DD-24) | Documentación descartada |
| Códigos 401/403 | Dependen de la versión de FastAPI | Se fijó `fastapi>=0.122` y se agregó el escenario explícito "sin token → 401" |
| Validación del token | PyJWT `require` | Se adoptó `require: ["exp", "sub"]` y `algorithms=["HS256"]` fijo |
| Contraseñas | pwdlib `verify_and_update` | Re-hash en el login cuando cambian los parámetros |
| Email inexistente | patrón `DUMMY_HASH` | Se verifica igual contra un hash señuelo (anti-timing, DD-24) |
| Largo de `JWT_SECRET` | PyJWT solo advierte | **Decidí no validarlo al arrancar**; quedó como riesgo y backlog |

El caso del `400` es el ejemplo de la regla "ante conflicto prevalece la KB": la documentación oficial
resuelve un tutorial, no el dominio del producto. Otro punto con Context7: el tutorial usa form-data, pero
el diseño eligió body JSON con Pydantic (decisión D2) y lo dejó anotado como descartado.

## 3. Uso de la skill `revisar-escenarios`

**Cuándo**: entre el propose y el apply, como indica el paso 5 del flujo en `CLAUDE.md`. Solo reporta; las
correcciones pasan por `/opsx:update`, así que la decisión sigue siendo humana. Controles C1–C9 y formato
en [SKILL.md](../../.agents/skills/revisar-escenarios/SKILL.md).

### 3.1 Primera pasada

Informe: [revision-escenarios-v1.md](../../openspec/changes/archive/2026-10-28-auth-jwt-roles/revision-escenarios-v1.md).
Revisó 89 escenarios en 5 specs. Veredicto: **CORREGIR ANTES DE APPLY** (0 bloqueantes, 3 mayores,
4 menores, 2 sugerencias).

| Id | Sev. | Hallazgo | Mi decisión |
|---|---|---|---|
| H1 | MAYOR | Seis decisiones nuevas sin registro DD en la KB | Corregir (DD-24) |
| H2 | MAYOR | Causas del alta inválida por CLI sin escenario | Corregir |
| H3 | MAYOR | `USUARIO_PASSWORD` definida pero vacía: resultado no definido | Corregir: se rechaza |
| H4 | MENOR | Falta escenario de `sub` que no es UUID | Corregir |
| H5 | MENOR | Cuerpo "idéntico" con `mensaje` sin valor concreto | Corregir |
| H6 | MENOR | "Pocos segundos" de tolerancia, reloj sin fijar | Corregir |
| H7 | MENOR | Faltan bordes de vencimiento y de configuración | Corregir |
| H8 | SUGERENCIA | Email de un usuario inactivo no se puede reutilizar | Limitación aceptada, backlog "Reactivación de usuarios" |
| H9 | SUGERENCIA | Carrera entre dos altas por CLI | Riesgo conocido, la base garantiza la unicidad |

### 3.2 Correcciones

- Se creó **DD-24** (contrato de autenticación y usuarios) en `knowledge-base/09_decisiones_y_supuestos.md`, y
  se actualizaron `04`, `07`, `10` y `CHANGES.md`.
- Mientras registraba DD-24 apareció una contradicción en la propia KB: `rol` figuraba como "enum" en un
  lado y como `varchar` + CHECK en otro. Se resolvió al unificar el modelo de datos.
- `/opsx:update` llevó el change de 89 a 96 escenarios.

### 3.3 Segunda pasada

Informe: [revision-escenarios.md](../../openspec/changes/archive/2026-10-28-auth-jwt-roles/revision-escenarios.md),
con tabla de seguimiento. Veredicto: **LISTO PARA APPLY** (0 bloqueantes, 0 mayores, 2 menores nuevos).

| Hallazgo v1 | Estado |
|---|---|
| H1 a H7 | Cerrados, con evidencia en el spec o la KB (H5 cerrado en parte, ver N1) |
| H8 | Aceptado como limitación |
| H9 | Aceptado como riesgo conocido |

Los dos menores nuevos (N1: literal del mensaje de `rol_insuficiente` sin fijar; N2: variable `SEED_*`
definida y vacía sin escenario) aparecieron recién ahora porque DD-24 ya existía y permitió exigirlos. Se
corrigieron y el change quedó en **97 escenarios**.

## 4. Resultado medible

| Medida | Antes | Después |
|---|---|---|
| Escenarios | 89 (propose) | 96 (update) y 97 (tras la segunda pasada) |
| Hallazgos MAYOR | 3 | 0 |
| Hallazgos MENOR | 4 | 2, corregidos |
| Decisiones de diseño con registro en KB | 0 de 6 | DD-24 |
| Tests (`pytest`) | 388 de base | 632 (639 tras integrar una corrección de concurrencia ajena a C-06) |

Apply: 10 grupos de tareas con TDD estricto, `ruff` limpio y `openspec validate --strict` válido. Resumen en
[tasks.md](../../openspec/changes/archive/2026-10-28-auth-jwt-roles/tasks.md). La verificación manual contra
el stack de Docker confirmó los casos clave: login `200`, contraseña incorrecta `401`, sin token `401`, rol
insuficiente `403`, creación `201` con `creado_por` igual al `sub`, y token de un usuario desactivado `401`.

## 5. Qué no cubre cada herramienta

La skill revisa **escenarios contra la KB**, no el diseño técnico ni el código. Lo vimos en tres casos:

| Hallazgo | Quién lo encontró | Por qué la skill no lo veía |
|---|---|---|
| 5 problemas de diseño y tests (por ejemplo, tests del seed que dependían del `.env` local, y un problema de orden TDD en la tarea 4.1) | Advisor, revisor aparte, antes de Apply | No son escenarios ni reglas de la KB |
| Fuga del hash en un camino de error del CLI (error de base distinto de `IntegrityError`) | Advisor, revisión final del diff | Es código, no spec. Se corrigió con test RED → GREEN y frontera de 254/255 caracteres |
| Un byte NUL literal escrito en `tasks.md` durante el propose | Solo `git` | `validate`, la skill y el advisor leen texto y no lo detectaron |

Otros límites:

- Context7 informa, pero no decide: la diferencia con la KB (el `400`) la resolví yo.
- La skill es de solo reporte por diseño. Eso evitó que un agente cambiara el spec sin mi decisión, a costa
  de un paso manual más.
- Las pasadas no sustituyen a los tests: cada escenario se verifica con `pytest` en el Apply.

Se complementan así: Context7 fundamenta el diseño antes de escribir, la skill controla spec contra KB antes
de Apply, y el advisor revisa diseño y código. Cada una atrapó cosas que las otras no veían.

## 6. Archivos de la fundación

Comparación con lo previsto en [investigacion.md](investigacion.md) §5. Todos existen en el repo.

| Archivo | Estado |
|---|---|
| `.agents/skills/revisar-escenarios/` (`SKILL.md`, `references/`, `evals/`) | Creado según lo previsto; evals en [evidencias/skill-evals/](evidencias/skill-evals/) |
| `.agents/skills/skill-creator/`, `skills-lock.json` | Presentes, con origen fijado |
| `.claude/skills/revisar-escenarios` | Junction para que Claude Code la vea |
| `.atl/skill-registry.md` | Con la fila y las compact rules de la skill |
| `AGENTS.md` y `CLAUDE.md` | Rol "Revisión de specs", sección de la skill, sección de integraciones MCP y paso 5 del flujo |
| `.mcp.json` | Servidor `context7`, sin secretos |
| `docs/skills-mcp/` (`investigacion.md`, `mcp.md`, `evidencias/`, este archivo) | Documentación y evidencia |
| `docs/fundacion/skills-seleccionadas.md`, `README.md` | Ampliación del 2026-10-16 |
| `knowledge-base/09`, `04`, `07`, `10` y `CHANGES.md` | **Cambiaron** por DD-24. Difiere de lo previsto en §5, donde la KB no se tocaba: aquel supuesto valía para las herramientas, pero la revisión sí produjo decisiones de dominio |

## 7. Conclusión

Con un change real quedó a la vista qué aporta cada pieza. Context7 evitó decidir librerías de memoria y
dejó trazable en `design.md` dónde la documentación coincidió con la KB y dónde no. La skill encontró tres
problemas mayores antes de escribir una línea de código, y obligó a registrar DD-24. Ninguna reemplaza la
revisión humana ni la del código; sí acortaron el camino hasta un Apply con spec cerrado.
