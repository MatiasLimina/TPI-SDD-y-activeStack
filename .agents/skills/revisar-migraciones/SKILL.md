---
name: revisar-migraciones
description: Revisa en las ramas remotas del repo de turnos odontológicos que las migraciones de Alembic (backend/alembic/versions, revisiones numéricas escritas a mano como "008" con down_revision "007") estén bien numeradas respecto de main - detecta números ya usados en main, saltos, cadenas rotas, varias cabezas y dos ramas que reclaman el mismo número. Usala antes de abrir o mergear un PR que trae una migración, al crear una migración nueva, después de que se mergee otro change con migración, o cuando se pregunte por "alembic heads", "renumerar", "qué número de migración me toca" o el estado de las migraciones entre ramas. Solo reporta - no renumera ni commitea.
---

# Revisar migraciones entre ramas

En este proyecto las revisiones de Alembic son **números correlativos escritos a mano** (`008` con
`down_revision = "007"`), no hashes. Si dos ramas crean el mismo número, git no ve conflicto (los
archivos tienen nombres distintos), pero al mergear la segunda quedan **dos cabezas** y
`alembic upgrade head` falla. La regla del equipo (`docs/equipo/reparto-de-tareas.md`, sección
"Migraciones de Alembic") es: cada migración toma el siguiente número libre de `main`, y **el que mergea
segundo renumera la suya**.

Esta skill detecta el problema antes del merge. **Solo reporta**: renumerar toca código de un change y
lo hace su responsable, en su rama, con su commit.

## Entradas

- Nada obligatorio. Por defecto revisa todas las ramas de `origin` contra `origin/main`.
- Opcional: una o más ramas puntuales (`feat/c-11-bloqueos`), si el usuario pregunta por un PR concreto.
- **Solo ve lo que está pusheado.** Una migración que existe solo en la copia local no aparece: si el
  usuario acaba de crear una, pedirle que pushee la rama antes de correr la revisión.

## Procedimiento

1. Correr el script desde la raíz del repo (hace `git fetch --prune` y lee las ramas sin checkout):

   ```bash
   python .agents/skills/revisar-migraciones/scripts/revisar_migraciones.py
   ```

   Variantes: `--rama feat/c-11-bloqueos` (repetible) para revisar solo esas ramas; `--sin-fetch` si no
   hay red; `--base`, `--remoto` y `--dir` si cambia la estructura.

2. Leer el informe. Códigos de salida: `0` numeración correcta, `1` hay algo para corregir, `2` error de
   uso o de git (rama inexistente, sin red, remoto mal escrito): en ese caso no hay informe, solo el error.

3. Explicarle al usuario el resultado empezando por lo que bloquea un merge, y para cada problema decir
   **quién** lo corrige y **cómo**, usando la tabla de abajo. El responsable de cada rama sale del campo
   **Responsable** de `CHANGES.md`.

4. No editar migraciones ni commitear. Si el usuario pide corregir, eso es otro paso, en la rama del change.

## Cómo leer el informe

| Hallazgo | Qué significa | Corrección |
|----------|---------------|------------|
| ✅ OK | La migración sigue a la cabeza de `main` (o a otra migración nueva de la misma rama) | Nada |
| ❌ RENUMERAR | El número ya está ocupado en `main` (otra rama mergeó antes) | En la rama: renombrar el archivo y cambiar `revision` al siguiente libre y `down_revision` a la cabeza de `main`. Rebasear o mergear `main` primero |
| ❌ RENUMERAR ("va encima de…") | Su padre es otra migración de la rama que hay que renumerar | Renumerar toda la cadena de la rama, en orden |
| ❌ CADENA ROTA | Salta números o `down_revision` no apunta a la anterior | Ajustar `down_revision` para que la cadena sea contigua |
| ❌ MODIFICA MAIN | La rama trae un archivo de migración de `main` con otro contenido | No editar migraciones ya mergeadas: revertir el cambio y crear una migración nueva. Si la rama solo está desactualizada, traer `main` |
| Choque entre ramas (informativo) | Dos ramas abiertas agregan el mismo número | Ninguna está mal todavía y no cambia el código de salida. La que mergee **segunda** renumera. Avisar a ambos responsables |
| Integridad: revisión repetida | Dos archivos declaran el mismo número (típico al traer `main` sin renumerar) | RENUMERAR el archivo que no es de `main` |
| Integridad: varias cabezas | Dentro de una rama hay dos migraciones sin hijo | Igual que RENUMERAR; verificar después con `alembic heads` (una sola cabeza) |
| Integridad: no se puede leer | Error de sintaxis, `revision` no numérica o migración de merge | Corregir el archivo; en este proyecto no se usan migraciones de merge, se renumera |
| Sin migraciones propias (atrasada) | La rama no trae migraciones y está detrás de `main` | Informativo. Si después agrega una, debe partir de la cabeza actual de `main` |

Una rama que ya fue mergeada aparece como "sin migraciones propias": no es un error.

## Verificación después de renumerar

Con la rama corregida y la base levantada (`docker compose up -d db`):

```bash
cd backend && alembic heads && alembic upgrade head
```

`alembic heads` debe mostrar **una sola** revisión. Volver a correr esta skill para confirmar que el
informe da ✅.
