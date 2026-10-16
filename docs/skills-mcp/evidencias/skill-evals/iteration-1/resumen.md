# Evals de `revisar-escenarios` — iteración 1 (2026-10-16)

Modo liviano acordado con el equipo: 3 casos de [`evals/evals.json`](../../../../../.agents/skills/revisar-escenarios/evals/evals.json),
una corrida **con la skill** por caso (subagente Sonnet, sin baseline), calificación manual contra las
aserciones. La versión de la skill usada está en [`../iteration-0-skill-snapshot/`](../iteration-0-skill-snapshot/).

| Eval | Caso | Aserciones cumplidas | Veredicto de la skill | Tokens / tiempo |
|---|---|:---:|---|---|
| 1 | [C-06 con defectos sembrados](eval-1-c06-con-defectos/with_skill/outputs/revision-escenarios.md) | 6/6 | CORREGIR (4 BLOQ, 5 MAY, 2 MEN, 1 SUG) | 91 k / 84 s |
| 2 | [C-04 sin error de negocio ni borde](eval-2-c04-sin-borde/with_skill/outputs/revision-escenarios.md) | 4/4 | CORREGIR (2 BLOQ, 3 MAY, 2 MEN, 2 SUG) | 93 k / 66 s |
| 3 | [C-05 archivado (spec maduro)](eval-3-c05-archivado/with_skill/outputs/revision-escenarios.md) | 3/3 | CORREGIR (0 BLOQ, 3 MAY, 5 MEN, 2 SUG) | 129 k / 126 s |

## Calificación

- **Eval 1**: detectó los seis defectos sembrados: auditoría fuera de scope (C-07), `401` donde
  corresponde `403`, expiración no verificable, `400` sin fuente (derivado a pregunta abierta sin inventar
  regla), falta credenciales inválidas → `401`, veredicto correcto.
- **Eval 2**: detectó la falta de error de negocio y de borde (RN-AG-13/DD-14 → `409`) y el doble cancelado
  (DD-22 → `409`), y no objetó el `404` de path (coherente con DD-21).
- **Eval 3**: no pidió como faltantes horarios, bloqueos, auditoría ni recordatorios, ningún BLOQUEANTE y
  tabla de cobertura completa. **Pero** el `expected_output` esperaba "LISTO o solo MENOR" y la skill dio
  3 MAYOR. Revisión:
  - H1 (bordes de duración 480/485 al reprogramar) y H2 ("inicio exactamente ahora") tienen fuente
    (RN-AG-04, RN-AG-12) y son faltantes reales del spec, aunque la lógica se comparta con C-03.
  - H3 (reloj no fijado en el spec) es exagerado: `tasks.md` sí fija el reloj. **Ajuste**: el control C6
    baja a `MENOR` cuando `tasks.md` ya fija el reloj.

## Defectos de la skill detectados y corregidos

1. **Fuente equivocada de las "Excepciones globales"**: la skill las buscaba en `openspec/specs/*/spec.md`,
   pero viven en `knowledge-base/05_reglas_de_negocio.md` §Excepciones globales. Lo reportó el subagente de
   la eval 1 ("no encontré una sección Excepciones globales en los specs archivados") y se verificó con
   `grep`. Corregido en `SKILL.md` y en `references/controles.md` (C2 y C4).
2. **Severidad de C6 demasiado alta** cuando el reloj está fijado en `tasks.md` (eval 3). Corregido.

3. **Reglas de auth sin fuente** (revisión FINAL_DIFF del advisor, antes del commit): `controles.md` C4 y
   `bordes-por-dominio.md` daban como reglas `401` para request sin token, token malformado o `alg: none`,
   citaban DD-16 para "no inicia sesión" (está en el scope de C-06 de `CHANGES.md`, no en DD-16) y excluían
   "refresh tokens" como "fuera del MVP" sin que la KB lo diga. Se corrigió: ahora son convenciones a
   confirmar como DD de C-06 o preguntas abiertas. El mismo error estaba en `mcp.md` y en
   `evidencias/mcp-context7.md` (atribuían al Flujo 1 un `401` para el usuario inactivo).

## Limitaciones

- Sin baseline sin skill: no se mide cuánto aporta la skill frente al agente solo.
- Una corrida por caso: no se mide la varianza.
- Las aserciones se calificaron a mano, leyendo los informes.
