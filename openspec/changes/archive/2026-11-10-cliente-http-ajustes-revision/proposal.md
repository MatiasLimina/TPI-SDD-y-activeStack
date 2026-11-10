# Proposal

## Why

La revisión del PR #15 (C-14, `frontend-base-login`, Matías) dejó dos desvíos menores del cliente HTTP (`frontend/src/shared/api/cliente.ts`). Se resuelven en este change chico, sobre la rama de C-15, antes de que el cliente se use en las pantallas de la agenda. Es un change de seguimiento de C-14: no agrega una entrada al roadmap ni un bloque en `CHANGES.md`. Governance BAJO.

## What Changes

- **`VITE_API_URL` vacía** (hueco del spec): con `VITE_API_URL=` el cliente usa la cadena vacía y arma URLs relativas. El requirement "URL base de la API" solo contempla la variable "no definida". Se enmienda para que una variable vacía valga como no definida, igual que el `${VITE_API_URL:-...}` de `docker-compose.yml`, y se corrige el código (`||` en vez de `??`). Una variable de solo espacios no se contempla.
- **Corte de conexión al leer el cuerpo de un error** (defecto de código): "Otras fallas" ya exige `status` `0` ante un corte al leer el cuerpo, sin restringirlo a `2xx`, pero `interpretarError` traga la falla de lectura y devuelve un error genérico con el `status` original. Se corrige leyendo el cuerpo como texto, para distinguir una falla de lectura (`status` `0`) de un cuerpo no JSON (se conserva el `status`). El texto del requirement no cambia; se agrega un escenario.

## Capabilities

### Modified Capabilities
- `frontend-cliente-http`: "URL base de la API" (variable vacía) y "Otras fallas" (escenario nuevo de corte en un no `2xx`).

## Impact

- `frontend/src/shared/api/cliente.ts` y `cliente.test.ts`. Sin cambios de backend, migración ni dependencias.
- Un `401` cuyo cuerpo se corta pasa a `status` `0` y `codigo` nulo, así que no cierra la sesión (no se leyó `no_autenticado`).
- Fuera de alcance: el resto de las sugerencias de la revisión (tests literales de Compose, construcción repetida de `Sesion`, puertos repetidos, import de `pages/` en `guardas.tsx`).
