# Revisión de escenarios — cliente-http-ajustes-revision (C-14, change de seguimiento)

- Fecha: 2026-11-10
- Specs revisados: `openspec/changes/cliente-http-ajustes-revision/specs/frontend-cliente-http/spec.md` (delta MODIFIED), contrastado con `openspec/specs/frontend-cliente-http/spec.md`
- Artefactos leídos: `proposal.md`, `design.md`, `tasks.md`, bloque `[C-14]` de `CHANGES.md`, DD-33 (a y la URL de la API), `docker-compose.yml` (`${VITE_API_URL:-...}`)
- Scope: dos desvíos de la revisión del PR #15. Sin bloque propio en `CHANGES.md` (lo declara el proposal)
- Reglas aplicables: DD-33 (cliente HTTP, `VITE_API_URL`, `no_autenticado` cierra la sesión), requirements "URL base de la API" y "Otras fallas" del spec principal
- `openspec validate cliente-http-ajustes-revision --strict`: válido
- Veredicto: **LISTO PARA APPLY**. Sin hallazgos BLOQUEANTE ni MAYOR.

## Cobertura

| Requirement | Escenarios | Esperado | Error de negocio | Borde | Reglas cubiertas |
|-------------|-----------:|:--------:|:----------------:|:-----:|------------------|
| URL base de la API | 4 | URL configurada, Sin configuración, Base con barra final | n/a | Variable vacía | DD-33 (URL de la API), Compose `:-` |
| Otras fallas | 7 | Detail de texto, JSON sin detail | Cuerpo que no es JSON, Éxito con cuerpo que no es JSON | Falla de red, Conexión cortada (2xx), Conexión cortada en un error | Requirement "Otras fallas", DD-33 (401 `no_autenticado`) |

Reglas del scope sin escenario: ninguna. Los escenarios existentes se copiaron sin cambios (verificado contra el spec principal).

## Hallazgos

### H1 — Variable de solo espacios sin regla · SUGERENCIA
- **Dónde**: requirement "URL base de la API", falta
- **Problema**: `VITE_API_URL=" "` no está cubierta. Compose tampoco la trata (`:-` solo mira vacía o indefinida), así que no hay desvío contra el que corregir.
- **Fuente**: `docker-compose.yml` (`${VITE_API_URL:-http://localhost:8000}`); el pedido del change es no agregar reglas más allá del desvío.
- **Sugerencia**: no agregar escenario. Si el equipo la quiere, sería una pregunta abierta.

### H2 — El escenario del 401 mezcla dos expectativas · SUGERENCIA
- **Dónde**: requirement "Otras fallas", escenario "Conexión cortada al leer el cuerpo de un error"
- **Problema**: verifica `status` `0` y que la sesión siga abierta. Es verificable (un test con `alNoAutenticado` espiado) y la segunda parte es la consecuencia que importa de DD-33, así que se deja junta.
- **Fuente**: DD-33 (solo un `401` con `codigo` `no_autenticado` cierra la sesión).

## Preguntas abiertas
Ninguna.

## Fuera de esta revisión
El texto del requirement "Otras fallas" no cambia (ya cubría el corte sin restringirlo a `2xx`); se copia entero porque el validador exige el requirement completo en un MODIFIED.
