# Reparto de tareas del equipo

> Vigente desde el 2026-10-29, cuando se suman Nico y Lauti al proyecto.
> Cubre los changes pendientes (C-07 a C-16) y la documentación. C-01 a C-06 ya están archivados.
> La asignación por change también figura en el campo **Responsable** de cada change en [CHANGES.md](../../CHANGES.md).

---

## 1. Integrantes y herramientas

| Integrante | GitHub | Herramientas de IA | Perfil en el reparto |
|------------|--------|--------------------|----------------------|
| **Matías** Limina | `MatiasLimina` | Claude Pro (Claude Code: Opus/Sonnet, skills, engram, advisor) | Dueño del repo e integrador. Changes críticos del núcleo de turnos |
| **Nico** (Monjelardi Nicolás Lionel) | `nicolasmonjelardi` | Claude Pro (Claude Code) | Changes pesados de infraestructura y el frontend de agenda |
| **Lauti** (Lautaro Agustín Agüero) | `LautaroAguero01` | Solo gratuitas: OpenCode con modelos free, Gemini (lo que incluya su plan), GitHub Copilot Student | Implementación de changes de governance BAJO y documentación |

### Por qué este reparto

1. **El governance ya marca la frontera.** El CLAUDE.md global define que en dominios CRITICO el agente solo analiza y no escribe código sin aprobación humana explícita, que en ALTO propone y espera revisión antes de escribir, y que en BAJO tiene autonomía si los tests pasan. Los changes CRITICO/ALTO (C-07, C-12) y los MEDIO que tocan los casos de uso de turnos quedan para quienes tienen Claude Pro; los BAJO (C-08, C-09, C-14, C-16) son para Lauti.
   - **Excepción dentro de los BAJO**: C-14 incluye el cliente HTTP con JWT, el login y las guardas por rol, y C-16 la vista de auditoría. Son partes de auth y auditoría, que el governance global trata como CRITICO. El padrino las revisa línea por línea en el PR, y el `design.md` de esos changes las marca como tales.
2. **Lo caro de OPSX es el Propose.** La tabla de modelos asigna Opus con esfuerzo alto al Propose, porque un error de diseño es el más costoso. Por eso, en los changes de Lauti, el Propose lo hace su **padrino** (Matías o Nico) con Claude; Lauti hace el Apply, que es lo que más tokens consume pero sigue tareas ya escritas.
3. **Los changes de Lauti son módulos nuevos.** C-08 y C-09 agregan routers y modelos propios, sin tocar los casos de uso de turnos. Así se reducen los conflictos de merge con lo que hacen Matías y Nico en paralelo.
4. **C-08 está en el camino crítico** (C-10 y C-11 dependen de él). Es un CRUD simple, por eso es el primero de Lauti: mientras lo implementa, Matías y Nico avanzan con C-07 y C-12, que no dependen de C-08.

---

## 2. Asignación por change

| Change | Gov. | Responsable (Apply) | Propose y revisión | Ola |
|--------|------|---------------------|--------------------|-----|
| C-07 `auditoria-turnos` | CRITICO | Matías | Matías; revisa Nico | 1 |
| C-12 `recordatorios-mock-redis` | ALTO | Nico | Nico; revisa Matías | 1 |
| C-08 `gestion-recursos-consultorio` | BAJO | Lauti | Padrino: Matías | 1 |
| C-10 `horarios-atencion` | MEDIO | Matías | Matías; revisa Nico | 2 |
| C-11 `bloqueos-agenda` | MEDIO | Nico | Nico; revisa Matías | 2 |
| C-09 `registro-pacientes` | BAJO | Lauti | Padrino: Matías | 2 |
| C-13 `agenda-diaria-semanal` | MEDIO | Matías | Matías; revisa Nico | 3 |
| C-14 `frontend-base-login` | BAJO | Lauti | Padrino: Nico | 4 |
| C-15 `frontend-agenda-turnos` | MEDIO | Nico | Nico; revisa Matías | 5 |
| C-16 `frontend-configuracion-pacientes-bloqueos` | BAJO | Lauti | Padrino: Nico | 6 |

**Carga resultante**: Matías 3 changes (1 CRITICO, 2 MEDIO) + padrino de 2 + integración; Nico 3 changes (1 ALTO, 2 MEDIO) + padrino de 2; Lauti 4 changes BAJO + documentación.

### Tareas de documentación (Lauti)

| ID | Tarea | Cuándo | Entregable |
|----|-------|--------|------------|
| D-1 | **Guía de puesta en marcha con herramientas gratuitas**: levantar Docker, correr `pytest`, usar los comandos `/opsx-*` de OpenCode. Lauti la escribe mientras hace su primer setup, que es la mejor prueba de que funciona | Ola 1 | `docs/equipo/onboarding.md` |
| D-2 | **Referencia de la API**: endpoints, roles que pueden usarlos, códigos de error (401/403/404/409/422) y ejemplos con datos ficticios, a partir del OpenAPI de FastAPI (`/docs`) | Ola 3, y se actualiza con cada change que agrega endpoints | `docs/api/endpoints.md` |
| D-3 | **Mantenimiento del README**: sección "Cómo correr" y "Estado del proyecto" al cerrar cada ola | Al cierre de cada ola | `README.md` |
| D-4 | **Checklist de cierre por change** (como `docs/opsx/checklist-c03.md`): escenarios del spec ↔ test que los cubre, para los changes de Lauti | Al archivar C-08, C-09, C-14, C-16 | `docs/opsx/checklist-c08.md`, etc. |

> La documentación también cuenta como entregable de la consigna. Cualquier dato de ejemplo (pacientes, DNI, teléfonos) debe ser ficticio: es regla dura del proyecto.

---

## 3. Calendario por olas

Una ola termina cuando todos sus changes están mergeados en `main` y archivados. Lo que no tiene dependencias pendientes puede adelantarse.

```
OLA 1 (ya: C-06 ✓)
  Matías  → C-07 auditoria-turnos            (+ Propose de C-08 al arrancar la ola)
  Nico    → C-12 recordatorios-mock-redis
  Lauti   → setup + D-1 onboarding → Apply de C-08

OLA 2 (C-08 ✓)
  Matías  → C-10 horarios-atencion           (+ Propose de C-09)
  Nico    → C-11 bloqueos-agenda
  Lauti   → Apply de C-09

OLA 3 (C-10 ✓ y C-11 ✓)
  Matías  → C-13 agenda-diaria-semanal
  Nico    → explora el frontend (find-skill para React, Propose de C-14)
  Lauti   → D-2 referencia de la API

OLA 4 (backend MVP completo: C-07, C-09, C-12, C-13 ✓)
  Lauti   → Apply de C-14
  Nico    → Propose de C-15
  Matías  → verificación de punta a punta del backend

OLA 5 (C-14 ✓)
  Nico    → C-15 frontend-agenda-turnos      (+ Propose de C-16)
  Lauti   → D-3 / D-4 pendientes

OLA 6 (C-15 ✓)
  Lauti   → Apply de C-16
  Matías y Nico → revisión final y preparación de la entrega
```

---

## 4. Flujo de trabajo para los changes de Lauti

Como no tiene Claude, el ciclo OPSX se reparte entre él y su padrino:

```
Padrino (Claude Pro)                       Lauti (herramientas gratuitas)
────────────────────                       ──────────────────────────────
1. /opsx:propose C-NN                 ──►
2. revisar-escenarios C-NN
   (si hay BLOQUEANTE/MAYOR → /opsx:update)
3. Commit de los artefactos y push    ──►  4. Rama del change, /opsx-apply en OpenCode
                                           5. TDD estricto, un commit por tarea
                                           6. PR a main
7. /code-review + advisor (FINAL_DIFF) ◄──
8. Pide cambios                       ──►  9. Correcciones y /opsx-archive
                                              en la misma rama (incluye el
                                              Estado [x] en CHANGES.md)
10. Aprueba y mergea                  ◄──
```

> El archive va **en la rama, antes del merge**, como se hizo con C-06. Si se archiva después, el commit del archive caería directo en `main`.
>
> `/code-review` es una skill de Claude Code que puede no estar en todas las instalaciones. Si no la tenés, usá `/review` o pedile a Claude que revise el diff del PR.

### Reglas para el Apply con modelos gratuitos

- **Una tarea de `tasks.md` por vez.** Los modelos gratuitos pierden el hilo con contextos largos: pedile al agente que implemente solo la tarea N, corré los tests y commiteá antes de pasar a la siguiente.
- **El agente tiene que leer las skills a mano.** Las skills viven en `.agents/skills/<skill>/SKILL.md`. Si la herramienta no las carga sola, indicale que lea `tdd`, `python-testing-patterns` y `fastapi-python` antes de empezar.
- **`AGENTS.md` es el punto de entrada.** OpenCode lo lee automáticamente. En Copilot (modo agente de VS Code) activá la lectura de `AGENTS.md`; en Gemini CLI, configurá `AGENTS.md` como archivo de contexto o pasáselo en el primer mensaje.
- **Vos corrés los tests, no el modelo.** Ejecutá `pytest` vos mismo y verificá RED antes de GREEN. Un test que pasa sin haber fallado primero no prueba nada.
- **Si el spec no alcanza, no se inventa.** Si una tarea pide algo que no está en el spec o contradice la KB, frená y avisale al padrino para hacer `/opsx:update`. Es regla dura: nada se implementa en Apply sin estar en el spec aprobado.
- **Uso sugerido de cada herramienta**:
  - **OpenCode (modelos free)**: el Apply, con los comandos `/opsx-apply` y `/opsx-archive` que ya están en `.opencode/commands/`.
  - **Copilot Student**: completado de código y tests en el editor, y modo agente para tareas chicas.
  - **Gemini**: leer y resumir la KB (contexto largo) y redactar la documentación D-1 a D-4.

---

## 5. Reglas de colaboración (para los tres)

### Git y GitHub

- **Nadie commitea en `main`.** Cada change va en su rama y entra por PR:
  - `feat/c-08-gestion-recursos-consultorio`
  - `docs/d-1-onboarding`
- **Al menos una aprobación de alguien con Claude Pro** antes de mergear. Los changes CRITICO o ALTO los revisa el otro integrante con Pro.
- **Merge commit, no squash.** El historial tiene que mostrar el proceso (un commit por etapa o tarea, regla del proyecto), y el squash lo borra.
- **Conventional Commits con el scope del change**: `feat(c-08): ...`, `test(c-08): ...`, `docs(c-08): ...`.
- **Antes de abrir el PR, actualizá tu rama con `main`** y volvé a correr toda la suite.

### Migraciones de Alembic (punto de conflicto seguro)

Las revisiones son números correlativos escritos a mano (`004` con `down_revision = "003"`). Si dos ramas crean `005` en paralelo, al mergear la segunda quedan dos cabezas y `alembic upgrade head` falla.

- Creá tu migración con el **siguiente número libre de `main`** en ese momento.
- **El que mergea segundo renumera la suya**: cambia `revision` y `down_revision` para que apunte a la última de `main`, y verifica que `alembic heads` muestre **una sola** cabeza.
- Changes con migración propia: C-07, C-08 (CHECK de duración), C-10, C-11 y C-12.

### Puntos de conflicto en el código

- **Casos de uso de turnos** (crear, reprogramar, cancelar): los tocan C-07, C-10, C-11 y C-12 a través de los puntos de extensión de C-03. En las olas 1 y 2 Matías y Nico trabajan ahí en paralelo: avísense cuando mergean, y el segundo rebasa sobre el primero.
- **`CHANGES.md`**: solo se toca el `Estado` del change propio, al archivarlo en su rama.
- **Propose adelantado**: C-14 se propone mientras C-13 está en curso, y C-16 mientras se hace C-15. OPSX lo permite, pero si la API de C-13 o C-15 cambia al mergear, el padrino ajusta el change con `/opsx:update` antes de que Lauti arranque el Apply.
- **`AGENTS.md` y `CLAUDE.md`** deben quedar idénticos. Si alguien los modifica, cambia los dos en el mismo commit.

### Memoria del proyecto (engram)

Matías y Nico guardan decisiones en engram como indica el CLAUDE.md global. Lo que tenga que conocer todo el equipo (decisiones de diseño, gotchas) va además en el `design.md` del change o en la KB (`09_decisiones_y_supuestos.md`), porque Lauti puede no tener engram.

---

## 6. Pendientes de configuración (Matías)

- [ ] Invitar a `nicolasmonjelardi` y `LautaroAguero01` como colaboradores del repositorio en GitHub.
- [ ] Proteger `main`: PR obligatorio con una aprobación.
- [ ] Cada integrante copia `.env.example` a `.env` en su máquina; los secretos nunca se comparten por el repo.
