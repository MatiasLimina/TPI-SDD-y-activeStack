# Tasks

> Governance BAJO. Change de seguimiento de C-14 (PR #15), en la rama `feat/c-15-frontend-agenda-turnos`. TDD estricto: RED verificado, GREEN mínimo, triangular, refactor. Correr desde `frontend/`. No leer `.env*`.

## 1. Variable `VITE_API_URL` vacía

- [x] 1.1 Safety net: correr la suite del frontend (120 tests en verde).
- [x] 1.2 RED: test de `VITE_API_URL` vacía → `http://localhost:8000`; verificar que falla por la URL relativa.
- [x] 1.3 GREEN: `configurada || URL_BASE_POR_DEFECTO` en `urlBaseDesdeEntorno()`.

## 2. Corte al leer el cuerpo de un error

- [x] 2.1 RED: tests de un `500` y un `401` con cuerpo cortado → `status` `0`, y el `401` sin llamar a `alNoAutenticado`; verificar que fallan porque el error conserva el `status`.
- [x] 2.2 GREEN: extraer `leerTexto` (corte → `status` `0`) y usarlo en `leerCuerpoJson` e `interpretarError`.
- [x] 2.3 Triangular: un error con cuerpo no JSON conserva su `status` y el mensaje genérico (cubierto por los escenarios existentes).
- [x] 2.4 Refactor, y `typecheck`, `lint`, `format:check`, tests y `build` limpios.
