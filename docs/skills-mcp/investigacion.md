# Ficha de investigación — skill propia y MCP

Proyecto: Turnos y Agenda para Consultorios Odontológicos · Fecha: 2026-10-16 · Cliente: Claude Code (Windows 11)

## 1. Necesidad detectada y change elegido

**Change**: `C-06` `auth-jwt-roles` (CHANGES.md, governance CRÍTICO). Depende solo de C-03, ya archivado,
así que puede prepararse sin funcionalidades inexistentes. Además, está en el camino crítico.

- **Tarea repetible (skill)**: en C-03, C-04 y C-05 los escenarios se revisaron a mano contra la KB, y los
  errores típicos se repitieron: códigos HTTP incoherentes, bordes `[)` sin escenario, reloj sin fijar y
  escenarios que invadían otros changes. Con TDD estricto, cada error del spec pasa directo a los tests. En
  C-06 el riesgo crece: `401` frente a `403`, la expiración del token y el usuario desactivado son bordes
  fáciles de omitir.
- **Acceso a información (MCP)**: la KB dice "JWT firmado" y "bcrypt/argon2", pero no fija la librería ni su
  API. Decidirlo de memoria arriesga APIs viejas (por ejemplo `python-jose`, que dejó de usarse en el tutorial
  oficial de FastAPI).
- **Cómo ayudan al mismo change**: el MCP fundamenta `design.md` (librería, validación de `exp` y de
  `algorithms`) y la skill controla que `specs/` cubra las RN-AU, DD-05, DD-16, el scope de C-06 y los bordes de auth
  antes de Apply.

## 2. Skill creadora y diseño de la skill propia

| Ítem | Dato |
|---|---|
| Skill creadora | `skill-creator`, de Anthropic: <https://github.com/anthropics/skills/tree/main/skills/skill-creator> (Apache 2.0) |
| Compatibilidad | Claude Code (formato `SKILL.md` con frontmatter `name` + `description`) |
| Instalación | `npx skills add anthropics/skills --skill skill-creator` (sin `-g`, convención del repo). Alternativa: `/plugin marketplace add anthropics/skills` |
| Comprobación | aparece en la lista de skills de una sesión nueva; `skills-lock.json` fija origen y hash |
| Uso | intención → entrevista → `SKILL.md` → casos de prueba en `evals/evals.json` → corrida y calificación → ajuste |

**Skill propia: `revisar-escenarios`**
- **Propósito**: revisar los escenarios GIVEN/WHEN/THEN de los delta specs de un change contra las RN/DD/SU de
  `knowledge-base/` y el scope de `CHANGES.md`.
- **Cuándo se activa**: después de `/opsx:propose` u `/opsx:update` y antes de `/opsx:apply`, o cuando se pide
  "revisar/validar/chequear" los specs.
- **Entradas**: nombre del change. Lee los specs, proposal/design/tasks, su bloque de CHANGES.md y la KB
  ("Leer antes", más 05, 09 y 10).
- **Procedimiento**: lista de reglas aplicables → inventario de escenarios (esperado, error de negocio, borde)
  → controles C1–C9 → hallazgos con severidad y fuente.
- **Resultado**: `openspec/changes/<change>/revision-escenarios.md`, con veredicto, cobertura, hallazgos y
  preguntas abiertas. Solo reporta: corregir es tarea de `/opsx:update`.
- **Criterios de revisión**: todo BLOQUEANTE o MAYOR cita una regla existente; no se inventan reglas de dominio
  (pasan a preguntas abiertas); no se piden como faltantes cosas de otro change.
- **Ubicación**: `.agents/skills/revisar-escenarios/` (versionada). Claude Code la encuentra mediante una
  *junction* en `.claude/skills/`.

## 3. Comparación de servidores MCP

| Criterio | **Context7** (Upstash) — elegido | **Semgrep MCP** |
|---|---|---|
| Propósito | Documentación actualizada y versionada de librerías | Escaneo estático de seguridad del código |
| Herramientas | `resolve-library-id`, `query-docs` | `semgrep_scan`, `security_check`, `semgrep_scan_with_custom_rule`, `get_abstract_syntax_tree` y otras |
| Compatibilidad | Claude Code, remoto HTTP o local stdio | Claude Code, local stdio |
| Instalación | `.mcp.json` con `https://mcp.context7.com/mcp`; no requiere Node | Python + `uvx semgrep-mcp`. El repo `semgrep/mcp` está **archivado** (oct-2025) y el servidor se mudó al binario `semgrep` |
| Credenciales | Ninguna; API key gratuita opcional (`Authorization: Bearer`) | Ninguna para el escaneo; token solo para las herramientas de la plataforma |
| Permisos | Envía solo el texto de la consulta a un servicio externo | Lee el código local |
| Costo | Gratis, con límite de requests sin clave | Gratis (núcleo MIT) |
| Aporte a C-06 | Alto **en la preparación**: fundamenta el design | Alto en Apply/verificación; casi nulo en la preparación (todavía no hay código de auth) |

**Elección: Context7**. El TP prepara el change sin implementarlo, y en esa etapa lo que hace falta es
documentación para decidir, no código para escanear. Además es el más reproducible en Windows (sin
instalación local). Semgrep queda como candidato para la verificación de C-06 en Apply. También se descartó
**Postgres MCP Pro** (crystaldba): el esquema de `usuario` todavía no existe, y el servidor maneja una cadena
de conexión con credenciales.

## 4. Pasos de instalación y configuración

1. Versionar `.mcp.json` en la raíz, ámbito *project*, sin secretos.
2. Abrir Claude Code en la raíz y aprobar `context7` (si se rechazó: `claude mcp reset-project-choices`).
3. Comprobar con `curl https://mcp.context7.com/ping`, que debe responder `{"status":"ok","message":"pong"}`, y con `claude mcp list`,
   que debe mostrar `✔ Connected`.
4. Ejecutar una herramienta: `resolve-library-id` con `PyJWT`, que debe devolver `/jpadilla/pyjwt`.
5. (Opcional) Usar la API key solo en ámbito *local*: `claude mcp add --scope local … --header "Authorization: Bearer <clave>"`.

**Límites para datos de prueba**: solo lectura de documentación pública. En `query` se envían únicamente
preguntas genéricas sobre la librería: nunca datos de pacientes (ni siquiera los ficticios), secretos,
`.env` ni código del repo. Ante un conflicto con la KB, prevalece la KB.

## 5. Archivos de la fundación que se prevé actualizar

| Archivo | Cambio |
|---|---|
| `.agents/skills/skill-creator/`, `skills-lock.json` | instalar la skill creadora con origen fijado |
| `.agents/skills/revisar-escenarios/` | nueva skill propia (`SKILL.md`, `references/`, `evals/`) |
| `.atl/skill-registry.md` | fila y compact rules de `revisar-escenarios`; nota de que el MCP no es una skill |
| `AGENTS.md` y `CLAUDE.md` (copias idénticas) | rol "Revisión de specs", sección de la skill propia, sección de integraciones MCP y paso 5 del flujo |
| `README.md` → `docs/skills-mcp/mcp.md` | instalación reproducible de la skill y del MCP, con la solución de un problema |
| `docs/fundacion/skills-seleccionadas.md` | ampliación del 2026-10-16, sin re-ejecutar etapas |
| `knowledge-base/` | **sin cambios**: la KB describe el dominio y el stack del producto, no las herramientas del agente |

## 6. Fuentes (consultadas el 2026-10-16)

- anthropics/skills, README y `skill-creator/SKILL.md`: <https://github.com/anthropics/skills>
- Context7, repositorio: <https://github.com/upstash/context7>; clientes: <https://context7.com/docs/resources/all-clients>
- Claude Code, MCP (ámbitos, `.mcp.json`, expansión de variables): <https://code.claude.com/docs/en/mcp>
- Semgrep MCP (archivado): <https://github.com/semgrep/mcp>; documentación: <https://semgrep.dev/docs/mcp>
- Postgres MCP Pro: <https://github.com/crystaldba/postgres-mcp>
- FastAPI, OAuth2 con JWT: <https://fastapi.tiangolo.com/tutorial/security/oauth2-jwt> (vía Context7)
- PyJWT, uso: <https://github.com/jpadilla/pyjwt/blob/master/docs/usage.rst> (vía Context7)

**Pendientes (no verificados)**:
- `docs.semgrep.dev/mcp` respondió HTTP 405 y no se pudieron confirmar sus pasos actuales para Claude Code.
- Context7 no publica el límite de requests sin clave.
- La alerta de Socket que `npx skills add` mostró para `skill-creator` no se revisó en detalle (Gen: Safe,
  Snyk: Low Risk).
