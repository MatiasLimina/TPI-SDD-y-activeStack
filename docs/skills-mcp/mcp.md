# MCP del proyecto: Context7

Context7 (Upstash) es un servidor MCP que entrega documentación actualizada y versionada de librerías.
En este proyecto se usa para contrastar las decisiones de stack de cada change con la documentación
oficial, en lugar de depender de lo que el modelo recuerda. Es una **integración**, no una skill: no trae
procedimiento propio, expone herramientas que el agente invoca.

- Repositorio: <https://github.com/upstash/context7> (MIT; el backend de la API es privado).
- Documentación de clientes: <https://context7.com/docs/resources/all-clients>.
- Configuración de Claude Code: <https://code.claude.com/docs/en/mcp>.

## Herramientas que usamos

| Herramienta | Entrada | Para qué |
|---|---|---|
| `resolve-library-id` | `libraryName`, `query` | Obtener el ID de Context7 de una librería (por ejemplo `/jpadilla/pyjwt`) |
| `query-docs` | `libraryId`, `query` | Traer fragmentos de documentación y ejemplos para una pregunta concreta |

## Requisitos

- Claude Code (CLI o app de escritorio). Probado en Windows 11, Claude Code de octubre de 2026.
- Salida HTTPS a `mcp.context7.com`. No requiere Node, Docker ni cuenta.
- Variables de entorno: **ninguna**. Opcionalmente, una API key gratuita de
  <https://context7.com/dashboard> (empieza con `ctx7sk`) da un límite de requests más alto; se configura
  fuera del repo (paso 3). **No va en el repo.**

## Configuración (reproducible)

El repo versiona [`.mcp.json`](../../.mcp.json) en la raíz (ámbito *project* de Claude Code). No contiene secretos:

```json
{
  "mcpServers": {
    "context7": {
      "type": "http",
      "url": "https://mcp.context7.com/mcp"
    }
  }
}
```

Pasos para otro integrante:

1. Clonar el repo y abrir Claude Code en la raíz.
2. Aprobar el servidor `context7` cuando Claude Code pregunte por los servidores de `.mcp.json` (es un
   control de seguridad del cliente). Si se rechazó por error: `claude mcp reset-project-choices`.
3. (Opcional) Usar la API key **sin versionarla**: exportarla en la shell como `CONTEXT7_API_KEY` y agregar el servidor en ámbito *local*, que se guarda
   en `~/.claude.json` y no en el repo:

   ```bash
   claude mcp add --scope local --transport http --header "Authorization: Bearer $CONTEXT7_API_KEY" context7 https://mcp.context7.com/mcp
   ```

Se eligió el servidor remoto y no el local (`npx -y @upstash/context7-mcp`) porque no requiere Node y evita,
en Windows, envolver `npx` en `cmd /c`.

## Comprobar la conexión y ejecutar una herramienta

```bash
curl https://mcp.context7.com/ping
```

Responde `{"status":"ok","message":"pong"}`.

```bash
claude mcp list
```

Debe mostrar `context7 … ✔ Connected`. Dentro de una sesión, `/mcp` muestra el mismo estado.

Prueba de una herramienta real desde la sesión: pedirle al agente *"usá Context7 para resolver el ID de
PyJWT"*. Debe invocar `resolve-library-id` y devolver `/jpadilla/pyjwt`. Evidencia de las invocaciones
hechas para C-06: [evidencias/mcp-context7.md](evidencias/mcp-context7.md).

## Problema de instalación encontrado

**Síntoma**: `claude mcp list` advierte *"Server context7 is defined in multiple scopes with different
endpoints: user (npx …), project (https://mcp.context7.com/mcp)"*.

**Causa**: Active Stack ya había instalado Context7 en ámbito *user* (stdio con `npx`, en `~/.claude.json`),
y el proyecto agrega el mismo nombre en ámbito *project*. Claude Code usa una sola definición por nombre y
avisa porque los endpoints difieren (y las credenciales OAuth se guardan por endpoint).

**Solución**: dejar una sola definición. Para que todos usen la del repo, quitar la global con
`claude mcp remove context7 -s user` y volver a correr `claude mcp list`. Si se prefiere conservar la
global para otros proyectos, el aviso no impide el uso: ambas apuntan al mismo servicio.

## Límites de uso

- **Solo lectura de documentación pública.** Context7 no accede al repo, a la base de datos ni a `.env`.
- **Lo que se envía**: el parámetro `query` sale a un servicio externo. Nunca incluir datos de pacientes
  (aunque sean ficticios), secretos, contenido de `.env` ni código del proyecto: solo preguntas genéricas
  sobre la librería ("cómo valida PyJWT el claim exp").
- **No es fuente de verdad del dominio.** La documentación la aporta la comunidad y puede no coincidir con
  la KB. Ante un conflicto o un vacío (por ejemplo, el `400 Inactive user` del tutorial de FastAPI: la KB
  solo dice que un usuario desactivado "no inicia sesión", `CHANGES.md` C-06, y no fija el código), prevalecen `knowledge-base/` y las reglas duras; la diferencia se registra en el design.
- **Costo**: gratis, con límite de requests sin clave. Si se agota, conseguir la clave gratuita.
