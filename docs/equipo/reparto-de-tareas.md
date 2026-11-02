# Reparto de tareas del equipo

> **Versión 2 — vigente desde el 2026-11-02.** Para avanzar lo más posible esta semana, los changes pendientes se reparten **solo entre Matías y Nico**. Lauti queda fuera del reparto por ahora y no tiene changes asignados.
> La versión anterior (tres integrantes, con Lauti en los changes BAJO y la documentación) está en el historial de git: commit `c3506a2`.
> La asignación por change también figura en el campo **Responsable** de cada change en [CHANGES.md](../../CHANGES.md).

---

## 1. Integrantes

| Integrante | GitHub | Herramientas de IA | Perfil en el reparto |
|------------|--------|--------------------|----------------------|
| **Matías** Limina | `MatiasLimina` | Claude Pro (Claude Code) | Dueño del repo e integrador. Camino crítico del backend: recursos, horarios, agenda; y la última pantalla del frontend |
| **Nico** (Monjelardi Nicolás Lionel) | `nicolasmonjelardi` | Claude Pro (Claude Code) | Recordatorios, bloqueos, pacientes y el frontend de login y agenda |
| Lauti (Lautaro Agustín Agüero) | `LautaroAguero01` | Herramientas gratuitas | Sin changes asignados en esta versión |

Los dos tienen Claude Pro, así que cada uno hace el ciclo OPSX completo de sus changes (explore, propose, `revisar-escenarios`, apply, archive). Ya no hace falta la figura del padrino.

---

## 2. Estado de partida

- **C-01 a C-06**: archivados y en `main`.
- **C-07** `auditoria-turnos`: implementado y archivado en la rama `feat/c-07-auditoria-turnos`, con el PR #3 abierto. **Es lo primero que se mergea**: trae la migración `005`, y C-08 necesita partir de ella (ver §6).
- **C-08 a C-16**: pendientes.

> **Ojo con el TP de Skills + MCP.** `docs/skills-mcp/plan-preparacion-c08.md` eligió C-08 como el change que se deja "listo para Apply" sin implementar. Con esta versión C-08 **sí se implementa** esta semana. Antes de empezar el Apply, guardá lo que pida el TP (los artefactos del Propose y la revisión de escenarios) y ajustá ese plan, porque varios de sus pasos los tenía asignados Lauti.

---

## 3. Asignación por change

| Change | Gov. | Responsable | Revisa el PR | Ola |
|--------|------|-------------|--------------|-----|
| C-07 `auditoria-turnos` | CRITICO | Matías (hecho, falta merge) | Nico | 1 |
| C-08 `gestion-recursos-consultorio` | BAJO | **Matías** | Nico | 1 |
| C-12 `recordatorios-mock-redis` | ALTO | **Nico** | Matías | 1 |
| C-10 `horarios-atencion` | MEDIO | **Matías** | Nico | 2 |
| C-11 `bloqueos-agenda` | MEDIO | **Nico** | Matías | 2 |
| C-13 `agenda-diaria-semanal` | MEDIO | **Matías** | Nico | 3 |
| C-09 `registro-pacientes` | BAJO | **Nico** | Matías | 3 |
| C-14 `frontend-base-login` | BAJO | **Nico** | Matías | 4 |
| C-15 `frontend-agenda-turnos` | MEDIO | **Nico** | Matías | 5 |
| C-16 `frontend-configuracion-pacientes-bloqueos` | BAJO | **Matías** | Nico | 6 |

**Carga**: Matías 4 changes pendientes (C-08, C-10, C-13, C-16) más el merge de C-07 y la integración. Nico 5 (C-09, C-11, C-12, C-14, C-15).

### Por qué este reparto

1. **El camino crítico va sin cortes.** C-08 → C-10 → C-13 lo hace una sola persona (Matías), así no hay esperas entre changes encadenados. Nico se suma al camino crítico solo con C-11, que arranca en paralelo con C-10 apenas C-08 está en `main`.
2. **C-12 no espera a nadie.** Depende de C-01, C-04 y C-05, que ya están. Es el change más largo de Nico (cola Redis, worker, reintentos), por eso arranca en la ola 1, mientras Matías hace C-08.
3. **C-09 es relleno útil.** No está en el camino crítico; solo lo necesita C-15. Nico lo hace en la ola 3, mientras Matías hace C-13.
4. **El frontend lo arranca uno solo.** C-14 y C-15 los hace Nico, en secuencia: el cliente HTTP, el login y la agenda quedan con un único criterio. C-16 (pantallas de configuración) lo hace Matías, que construyó C-08, C-10 y los endpoints que esas pantallas consumen.
5. **Revisión cruzada.** Cada uno revisa los PR del otro. C-07 (CRITICO) y C-12 (ALTO) se revisan línea por línea, igual que en C-14 el cliente JWT y las guardas por rol, y en C-16 la vista de auditoría.

---

## 4. Calendario por olas

Una ola termina cuando sus changes están mergeados en `main` y archivados. Lo que no tenga dependencias pendientes puede adelantarse.

```
OLA 1 (ahora)
  Matías → merge de C-07 (PR #3) → C-08 gestion-recursos-consultorio
  Nico   → revisa PR #3 → C-12 recordatorios-mock-redis

OLA 2 (C-08 ✓)
  Matías → C-10 horarios-atencion
  Nico   → C-11 bloqueos-agenda        (si C-12 no terminó, lo cierra antes o en paralelo)

OLA 3 (C-10 ✓ y C-11 ✓)
  Matías → C-13 agenda-diaria-semanal
  Nico   → C-09 registro-pacientes

OLA 4 (backend MVP completo: C-07, C-09, C-12, C-13 ✓)
  Nico   → C-14 frontend-base-login
  Matías → verificación de punta a punta del backend; Propose de C-16

OLA 5 (C-14 ✓)
  Nico   → C-15 frontend-agenda-turnos
  Matías → revisión; find-skill para React si hace falta

OLA 6 (C-15 ✓)
  Matías → C-16 frontend-configuracion-pacientes-bloqueos
  Nico   → revisión final
```

> El Propose de C-16 se adelanta a la ola 4, antes de que C-15 esté terminado. OPSX lo permite, pero si la API o los componentes de C-15 cambian al mergear, Matías ajusta C-16 con `/opsx:update` antes de empezar el Apply.

**Meta realista para esta semana**: olas 1 a 3, o sea C-07, C-08, C-10, C-11, C-12, C-13 y C-09 en `main`. Eso deja el backend del MVP completo.

---

## 5. Puntos de conflicto en el código

- **Casos de uso de turnos** (crear, reprogramar, cancelar): los tocan C-07, C-10, C-11 y C-12 por los puntos de extensión de C-03. En la ola 1 se cruzan C-07 y C-12; en la ola 2, C-10 y C-11, que agregan validaciones al mismo flujo. Avísense al mergear: el segundo rebasa sobre el primero y vuelve a correr toda la suite.
- **`CHANGES.md`**: cada uno toca solo el `Estado` de su change, al archivarlo en su rama.
- **`AGENTS.md` y `CLAUDE.md`** tienen que quedar idénticos. Si alguien modifica uno, cambia los dos en el mismo commit.

---

## 6. Reglas de colaboración

### Git y GitHub

- **Nadie commitea en `main`.** Cada change va en su rama y entra por PR: `feat/c-08-gestion-recursos-consultorio`.
- **El otro integrante aprueba el PR** antes del merge.
- **El archive va en la rama, antes del merge**, como en C-06 y C-07, junto con el `Estado [x]` en `CHANGES.md`.
- **Merge commit, no squash.** El historial tiene que mostrar el proceso (un commit por etapa o tarea, regla del proyecto).
- **Conventional Commits con el scope del change**: `feat(c-08): ...`, `test(c-08): ...`.
- **Antes de abrir el PR**, actualizá tu rama con `main` y volvé a correr toda la suite.

### Migraciones de Alembic

Las revisiones son números correlativos escritos a mano (`005` con `down_revision = "004"`). Si dos ramas crean el mismo número, al mergear la segunda quedan dos cabezas y `alembic upgrade head` falla.

- C-07 ya usa `005`. **Mergealo antes de crear la migración de C-08**, que toma el siguiente número libre (`006` si C-12 no mergeó la suya antes).
- En adelante, creá tu migración con el siguiente número libre de `main`. **El que mergea segundo renumera la suya** (`revision` y `down_revision`) y verifica que `alembic heads` muestre una sola cabeza.
- Changes con migración propia que quedan: C-08 (CHECK de duración), C-10, C-11 y C-12.

### Memoria del proyecto (engram)

Las decisiones que el otro tiene que conocer van al `design.md` del change o a la KB (`09_decisiones_y_supuestos.md`), no solo a engram. Engram es local de cada máquina.

---

## 7. Pendientes de configuración (Matías)

- [ ] Que `nicolasmonjelardi` tenga acceso de escritura al repositorio en GitHub.
- [ ] Proteger `main`: PR obligatorio con una aprobación.
- [ ] Cada integrante copia `.env.example` a `.env` en su máquina; los secretos nunca se comparten por el repo.
