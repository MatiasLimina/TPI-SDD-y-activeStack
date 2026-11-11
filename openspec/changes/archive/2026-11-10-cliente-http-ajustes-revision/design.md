# Design

## Context

Ver `proposal.md` y el delta `specs/frontend-cliente-http/spec.md`. Se toca solo `frontend/src/shared/api/cliente.ts`.

## Decisions

- **D1. `||` para la URL base.** `urlBaseDesdeEntorno()` devuelve `configurada || URL_BASE_POR_DEFECTO`. Reproduce el `:-` de Compose (indefinida o vacía). No se agrega `trim()`: una variable de solo espacios no está en el spec.
- **D2. Un solo lector de texto.** Se extrae `leerTexto(respuesta)`, que lanza `ErrorApi` con `status` `0` ante un corte, y la usan `leerCuerpoJson` e `interpretarError`. Este último hace `JSON.parse` del texto y, si falla, trata el cuerpo como `null` (conserva `status` y mensaje genérico, como hoy).
- **D3. Efecto sobre `alNoAutenticado`.** `interpretarError` pasa a poder lanzar. En `pedir` se llama antes del chequeo del `401`, así que un corte lanza `status` `0` sin llegar a `alNoAutenticado`: la sesión no se cierra. Se cubre con un test.

## Risks

Ninguno de dominio: es una corrección interna del cliente, sin cambio de contrato con la API.
