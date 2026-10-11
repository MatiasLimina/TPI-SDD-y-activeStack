# Guion del video de defensa

**Duración objetivo**: 11 minutos (rango permitido: 8 a 12).
**Formato**: 7 bloques grabados por separado y unidos al final en Clipchamp.
**Change del ciclo OPSX grabado**: `C-05` `reprogramar-turno`, hecho desde cero frente a cámara. (C-03 se hizo antes, fuera de cámara, y construyó la base sobre la que se apoya C-05.)

**Qué pide la consigna y dónde se cubre**:

| Pedido | Bloque |
|---|---|
| Qué hice | 1 (producto y MVP), 3 (change elegido) |
| Cómo lo hice | 2 (fundación), 3 (Explore, Propose y Ajustar), 4 (TDD), 6 (Engram) |
| Cómo funciona lo desarrollado | 4 (demo de la API andando, además de los tests) |
| Recorrer los archivos y carpetas y explicar para qué sirve cada uno | 2 (tabla de recorrido), 5 (lo que deja el archive) |
| Voz real y explicación con mis palabras | Todo el video (ver nota) |

> **Trabajo individual**: narro todo con mi voz real; no se usa voz sintética ni lectura de pantalla. El texto sugerido es solo un ayudamemoria: **no lo leas**, decilo con tus palabras y explicá el *porqué* de cada decisión. Lo que está entre `[corchetes]` se completa cuando ocurra (por ejemplo, qué corregiste en Propose).

---

## Antes de grabar (checklist)

- [ ] Docker Desktop levantado (para los tests y la demo).
- [ ] `openspec list` vacío y `git status` limpio: el ciclo arranca desde cero.
- [ ] Terminal con letra grande (Ctrl + rueda) y tema legible.
- [ ] Cerrar pestañas, notificaciones y **el archivo `.env`**; en el explorador, no abrirlo nunca: **no debe verse ninguna clave**.
- [ ] Solo datos ficticios de pacientes en pantalla (los del seed).
- [ ] Micrófono probado (grabá 10 segundos y escuchalos).
- [ ] Cámara encendida para los bloques 1 y 7.

## Qué se graba en vivo y qué no

| Bloque | Cuándo se graba |
|---|---|
| 1, 2 y 7 | En cualquier momento: muestran archivos que ya existen. |
| 3, 4, 5 y 6 | **Durante el chat de C-05.** Grabá esa sesión entera de corrido y después recortá. |
| Demo de la API (parte del bloque 4) | Después del Apply, con la API levantada. Puede ser un clip aparte. |

**Orden recomendado para la sesión de C-05**: arrancá a grabar **antes** de escribir el primer mensaje del chat nuevo. Así el bloque 6 (Engram) queda grabado sin esfuerzo, aunque en el video final vaya después del bloque 5.

---

## Guion de la sesión en vivo de C-05

**Regla de control**: después de cada paso, el agente se detiene y espera tu OK. No se commitea nada sin que lo pidas, y se hace un commit por etapa (`docs(c-05): propose reprogramar-turno`, `feat(c-05): …`, `test(c-05): …`, `chore(c-05): archive reprogramar-turno and sync specs`).

| # | Qué escribís | Qué tiene que pasar | Bloque |
|---|---|---|---|
| 1 | *Retomemos el proyecto. Recuperá el contexto de Engram y el estado de OpenSpec, y arranquemos con C-05 reprogramar-turno. Frená después de cada paso y esperá mi OK.* | Consulta Engram (`mem_context` / `mem_search`) y corre `openspec list`. Resume lo decidido en C-03 y lo que C-05 **no** lleva. | 6 |
| 2 | (Opcional) *¿Qué decidimos sobre el 409 en C-03?* | Responde con DD-21 (el 409 lista todos los recursos en conflicto) sin que se lo expliques. | 6 |
| 3 | `/opsx:explore reprogramar-turno` | Plantea las preguntas abiertas: ¿se puede cambiar la prestación? ¿Y el paciente? ¿Qué pasa con el sillón si cambia el profesional? **Las decidís en voz alta.** | 3 |
| 4 | `/opsx:propose reprogramar-turno` | Crea `proposal.md`, `design.md`, `specs/` y `tasks.md`. **Se frena.** | 3 |
| 5 | Revisás el spec con el checklist del bloque 3 | Encontrás algo real para corregir. | 3 |
| 6 | `/opsx:update reprogramar-turno` + qué corregir | Spec ajustado; mostrás el diff (`git diff`). Commit `docs(c-05): propose…`. | 3 |
| 7 | `/opsx:apply reprogramar-turno` | TDD estricto, un commit por tarea. | 4 |
| 8 | *Corré la suite completa* | `pytest` todo en verde, incluidos C-01..C-03. | 4 |
| 9 | Demo de la API (ver bloque 4) | Reprogramar funcionando de verdad, fuera de los tests. | 4 |
| 10 | `/opsx:archive reprogramar-turno` | Sincroniza el spec en `openspec/specs/agenda-turnos/`, mueve el change a `archive/` y marca C-05 `[x]` en `CHANGES.md`. | 5 |

---

## Bloque 1 — Qué hice: producto, Discovery y MVP (1:15)

**Toma**: cámara (0:15) → pantalla (1:00).

**Mostrar**:
1. `docs/discovery/informe-discovery.md` → Resumen ejecutivo.
2. Sección **B** (matriz de puntuación), con scroll lento.
3. Sección **D.4** (ajuste de alcance del MVP).
4. Sección **7** (verificación de fuentes): filas de Doctoralia, SMILE y Bilog.

**Texto sugerido**:

> Soy [nombre]. Hice un sistema de turnos y agenda para consultorios odontológicos chicos de Argentina.
>
> Empecé por el Discovery: el agente relevó 17 sistemas, con fuente y fecha de consulta para cada dato, y una matriz ponderada según los pesos de la consigna.
>
> El hallazgo principal es que casi ningún producto demuestra públicamente dos cosas básicas de una agenda odontológica: que cada prestación tenga su propia duración y que los sillones se manejen como un recurso. Ese es el vacío que ataca el MVP.
>
> El análisis proponía un MVP muy amplio, con odontograma, caja y WhatsApp. Usé **Ajustar** y lo recorté al núcleo de agenda: prestaciones con duración propia, sillones como recurso, turnos sin solapamientos por profesional, por sillón y por paciente, horarios, bloqueos y recordatorios simulados. Quedó registrado en la sección D.4.
>
> Después verifiqué nueve fuentes a mano y encontré tres errores del agente. El más importante: afirmaba que ningún sistema permitía al paciente cancelar o reprogramar su turno, pero en los videos oficiales de Bilog se ve que sí. Eso cambió el puntaje de Bilog del puesto 13 al 3.

---

## Bloque 2 — Cómo lo hice: recorrido del repositorio (2:00)

**Toma**: pantalla.

**Mostrar** el árbol del proyecto en el explorador y recorrer las carpetas **en este orden**, abriendo apenas cada una y diciendo para qué sirve:

| Carpeta / archivo | Para qué sirve (decilo con tus palabras) | Qué abrir |
|---|---|---|
| `docs/discovery/` | El origen de cada decisión de producto: investigación de mercado y checklist. | (ya se vio en el bloque 1) |
| `knowledge-base/` | La fuente de verdad del dominio: diez archivos canónicos que el agente lee antes de implementar. | `05_reglas_de_negocio.md` → trazabilidad, RN-AG-01..03 y **RN-AG-08** (reprogramar). `10_preguntas_abiertas.md` → "Preguntas resueltas". |
| `CHANGES.md` | El roadmap: los 16 changes, sus dependencias y el camino crítico. | Árbol de dependencias, C-03 en `[x]` y el bloque de **C-05**. |
| `AGENTS.md` / `CLAUDE.md` | Lo primero que lee cualquier agente: stack, skills y reglas duras. Son copias idénticas para que funcione con distintos agentes. | Sección "Reglas Duras". |
| `.atl/skill-registry.md` y `docs/fundacion/` | Qué skills se instalaron, cuáles carga cada rol y por qué. | Solo mostrar. |
| `openspec/` | El corazón de SDD: `specs/` es lo que el sistema hace hoy, `changes/` lo que está en curso y `changes/archive/` el historial de cada change cerrado. | `openspec/specs/` (lista de capacidades) y `changes/archive/`. |
| `backend/app/` | El código, en capas: `domain/` tiene las reglas puras sin base de datos, `application/` los casos de uso, `infrastructure/` la base y `api/` los endpoints. | Las cuatro carpetas. |
| `backend/alembic/versions/` | Las migraciones de la base: 001 activa `btree_gist`, 002 crea el catálogo y 003 crea los turnos con las restricciones de exclusión. | `003_turno.py` → las `EXCLUDE USING gist`. |
| `backend/tests/` | `unit/` testea el dominio sin base; `integration/` usa PostgreSQL real, porque las restricciones de exclusión solo existen ahí. | Solo mostrar. |
| `docker-compose.yml` | Levanta la base, Redis y la API con un solo comando. | Solo mostrar. |

Terminar con `git log --oneline` en la terminal.

**Texto sugerido** (entre carpeta y carpeta):

> La fundación la hice con `/active-orchestrator`, que pasa por siete etapas y en cada una me deja Continuar, Ajustar o Parar. Cada etapa dejó una de estas carpetas.
>
> En la knowledge-base también ajusté supuestos que el agente había inventado. Por ejemplo, había puesto el sillón como obligatorio en todo turno; lo cambié para que dependa de la prestación, porque una consulta no ocupa sillón.
>
> El roadmap tiene 16 changes, con el backend primero. Saqué la consulta de disponibilidad porque no estaba en el MVP. C-03 ya está hecho: construyó el alta de turnos y las restricciones de exclusión. Sobre eso voy a hacer en vivo **C-05, reprogramar turno**, que está en el camino crítico.
>
> En `AGENTS.md` quedaron diez reglas que revisé una por una. Por ejemplo, nunca usar datos reales de pacientes, y nunca confiar solo en la aplicación para evitar solapamientos: la base también tiene que impedirlos.
>
> El historial de commits muestra el proceso: un commit por etapa.

---

## Bloque 3 — El change elegido: Explore, Propose y Ajustar en C-05 (2:30) ★ el más importante

**Toma**: pantalla, grabada en vivo (pasos 3 a 6 de la sesión).

**Mostrar**:
1. `/opsx:explore reprogramar-turno` y las preguntas que plantea el agente.
2. `/opsx:propose reprogramar-turno`.
3. `openspec/changes/reprogramar-turno/` → para qué sirve cada archivo: `proposal.md` (qué y por qué), `design.md` (cómo), `specs/` (qué tiene que cumplirse) y `tasks.md` (los pasos).
4. `specs/` → escenarios **dado / cuando / entonces**: feliz, error de negocio y borde.
5. **El momento en que encontrás algo mal** y pedís el ajuste con `/opsx:update`.
6. El diff del spec corregido.

**Texto sugerido**:

> Elegí C-05, "reprogramar turno", porque está en el camino crítico, depende solo de C-03 y tiene reglas verificables: aplica las mismas validaciones que crear, pero excluyendo al propio turno.
>
> Antes de proponer usé Explore, porque la knowledge-base no dice si al reprogramar se puede cambiar la prestación o el paciente. Decidí que [tu decisión y por qué].
>
> El spec tiene [N] escenarios. El feliz: mover el turno a un hueco libre. El de error de negocio: moverlo a un hueco ocupado da 409 y el turno original queda intacto. El de borde: superponerse consigo mismo, por ejemplo correrlo 15 minutos, tiene que aceptarse.
>
> No lo aprobé a la primera. Encontré que [qué estaba mal]. Si hubiera apretado Continuar, [qué habría pasado en Apply]. Pedí Ajustar y quedó así: [mostrar el diff].

**Checklist de revisión** (para que el Ajustar sea real y no actuado). Hay trampas concretas en la KB:
- ¿Aparecen horarios de atención o bloqueos? RN-AG-08 dice "RN-AG-01..06", pero la 05 y la 06 llegan en **C-10 y C-11**. No corresponden a C-05.
- ¿Aparecen auditoría o recordatorio? US-005 y el Flujo 3 los piden, pero llegan en **C-07 y C-12**. En C-05 van, como mucho, como hooks sin implementar.
- ¿Aparece autenticación o rol? Tampoco: llega en **C-06**.
- ¿Están estos escenarios?
  - Solaparse consigo mismo es válido.
  - Un 409 o un 422 deja el turno original intacto.
  - Un turno cancelado no se puede reprogramar.
  - Un turno inexistente da 404.
  - El inicio en el pasado da 422.
  - Una duración que no es múltiplo de 5 o un inicio no alineado dan 422.
- ¿Se excluye el propio turno también en el chequeo **por paciente** (RN-AG-14)?
- Si cambia el profesional o la prestación, ¿se revalida la regla del sillón (RN-AG-10)?
- ¿Está el escenario de concurrencia: dos reprogramaciones al mismo hueco, exactamente una gana?

---

## Bloque 4 — Apply, Verify y cómo funciona (2:15)

**Toma**: pantalla, grabada en vivo (pasos 7 a 9).

### 4a. Tests (1:00)

**Mostrar**:
1. `tasks.md` con las tareas marcadas.
2. Un test abierto al lado del escenario del spec que cubre (por ejemplo, el del original intacto ante un 409).
3. La terminal corriendo la suite completa: **todo en verde**, incluidos los tests de C-01 a C-03.
4. El test de concurrencia de reprogramar pasando.

**Texto sugerido**:

> La implementación sigue el spec aprobado, sin decisiones improvisadas. Si algo no estaba en el spec, no se inventa: se vuelve a Propose.
>
> Se hizo con TDD estricto: primero el test en rojo, después el código mínimo. Cada escenario del spec tiene su test. Por ejemplo, este cubre [escenario].
>
> El solapamiento no se valida solo en la aplicación: la restricción de exclusión de PostgreSQL que hizo C-03 también protege la reprogramación, porque es un UPDATE de la misma fila. Este test lanza dos reprogramaciones al mismo hueco al mismo tiempo y verifica que exactamente una gane.
>
> La suite completa pasa: [N] tests en verde, y los de C-03 siguen pasando, así que no rompí nada de lo anterior.

### 4b. Demo: la API funcionando (1:15)

**Preparación (fuera de cámara)**: `docker compose up -d db api`, `alembic upgrade head` y el seed (`python -m app.infrastructure.db.seed`, ver `README.md`). Anotá los IDs de un profesional, un paciente y una prestación del seed. Usá fechas futuras con horas en múltiplos de 5 minutos.

**Mostrar** en el navegador `http://localhost:8000/docs` (Swagger, lo genera FastAPI solo):
1. `GET /health` → `{"status":"ok","database":"ok"}`.
2. `POST /turnos` → **201**: un turno de [paciente ficticio] a las 10:00.
3. `POST /turnos` de otro paciente con el mismo profesional a las 10:00 → **409**, y el cuerpo lista el recurso en conflicto.
4. `PATCH /turnos/{id}/reprogramar` del primer turno a las 11:00 → **200**.
5. `PATCH` del segundo turno a las 11:00 → **409**, y el original sigue intacto: [ruta o consulta que lo muestre según cómo quede el spec].

**Texto sugerido**:

> Para que se vea que funciona de verdad, y no solo en los tests, levanto la API con Docker. Swagger lo genera FastAPI a partir del código.
>
> Creo un turno: 201. Si intento otro con el mismo profesional en el mismo horario, el sistema lo rechaza con 409 y me dice qué recurso choca. Reprogramo el primero a las 11: funciona. Si quiero mover otro turno ahí, vuelve a dar 409, y el turno que intenté mover no cambió.

---

## Bloque 5 — Archive y estado final (0:45)

**Toma**: pantalla, grabada en vivo (paso 10).

**Mostrar**:
1. `/opsx:archive reprogramar-turno`.
2. La carpeta `openspec/changes/archive/AAAA-MM-DD-reprogramar-turno/`.
3. `openspec/specs/agenda-turnos/spec.md` con los requisitos de reprogramar agregados.
4. `openspec list` vacío.
5. `CHANGES.md` con C-05 en `[x]`.
6. `git log --oneline` con los commits `(c-05)`.

**Texto sugerido**:

> Con los tests en verde, archivé el change. Los requisitos de reprogramar se sumaron al spec vigente de agenda, que es la descripción de lo que el sistema hace hoy. El change quedó en `archive` con su propuesta, diseño, tareas y specs, para que se pueda rastrear por qué se hizo cada cosa. No quedan changes abiertos, y el historial muestra cada etapa en su propio commit.

---

## Bloque 6 — Engram (1:00)

**Toma**: pantalla. Es el **arranque del chat nuevo de C-05**, grabado en vivo (pasos 1 y 2).

**Mostrar**:
1. El primer mensaje del chat nuevo:
   > Retomemos el proyecto. Recuperá el contexto de Engram y el estado de OpenSpec, y arranquemos con C-05 reprogramar-turno. Frená después de cada paso y esperá mi OK.
2. El agente consultando Engram y respondiendo con decisiones de sesiones anteriores.
3. Opcional: una búsqueda puntual, por ejemplo "¿qué decidimos sobre el 409 en C-03?".

**Texto sugerido**:

> Engram es la memoria persistente del agente. Cada decisión importante quedó guardada: el recorte del MVP, los errores que encontré en la verificación, la decisión del sillón y cómo se cerró C-03.
>
> Abrí un chat nuevo, sin nada de contexto, y le pedí que recuperara lo anterior. Como ven, sabe que C-05 no lleva autenticación, ni horarios, ni bloqueos, y que reutiliza las restricciones de C-03, sin que yo se lo explique. Eso evita arrancar de cero en cada sesión.

---

## Bloque 7 — Conclusiones (1:00)

**Toma**: cámara.

**Texto sugerido** (con tus palabras; puede salir de la reflexión escrita):

> Lo que más me sirvió fue [etapa o artefacto].
>
> En C-05 el spec que propuso el agente [qué tenía de más o de menos]. Lo corregí antes de escribir una línea de código, y eso es lo que vale del ciclo: el error se detecta en un documento, no en producción.
>
> La diferencia entre implementar con un spec aprobado y pedir código con un prompt suelto es que [tu conclusión].
>
> Y lo que más me sorprendió es que el agente, cuando no encuentra un dato, tiende a completarlo. Por eso verificar fuentes y usar Ajustar no es opcional.

---

## Tiempos

| Bloque | Duración |
|---|---|
| 1. Qué hice: producto, Discovery y MVP | 1:15 |
| 2. Cómo lo hice: recorrido del repositorio | 2:00 |
| 3. Explore, Propose y Ajustar | 2:30 |
| 4. Apply, Verify y demo | 2:15 |
| 5. Archive y estado final | 0:45 |
| 6. Engram | 1:00 |
| 7. Conclusiones | 1:00 |
| **Total** | **10:45** |

Margen hasta 12:00: 1:15. Si te pasás, recortá primero los tiempos de espera del agente y después el bloque 1.

---

## Armado final en Clipchamp

1. Abrir Clipchamp → **Crear un video nuevo**.
2. Importar los clips (arrastrarlos a "Tus medios").
3. Arrastrarlos a la línea de tiempo en orden: 1 → 2 → 3 → 4 → 5 → 6 → 7. El clip de la sesión de C-05 se divide: el arranque (Engram) va como bloque 6, después del Archive.
4. Para recortar un clip largo: seleccionarlo y arrastrar sus bordes, o usar **Dividir** (tijera) en el punto de corte y borrar lo que sobra. Las esperas mientras el agente trabaja se cortan o se aceleran.
5. Revisar que el total quede entre 8 y 12 minutos (se ve abajo a la derecha).
6. **Exportar** → 1080p.

Si algún recorte se complica, anotá los minutos exactos ("del clip X, de 12:30 a 15:00") y se puede hacer con `ffmpeg`.
