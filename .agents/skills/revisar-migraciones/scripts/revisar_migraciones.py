"""Revisa la numeración de las migraciones de Alembic en las ramas remotas.

Lee todo desde git (ls-tree / show), sin hacer checkout ni tocar el working copy.
Códigos de salida: 0 numeración correcta, 1 hay algo para corregir, 2 error de uso o de git.

Uso:
    python revisar_migraciones.py [--sin-fetch] [--remoto origin] [--base main]
                                  [--dir backend/alembic/versions] [--rama feat/c-12-...]
"""

from __future__ import annotations

import argparse
import ast
import subprocess
import sys
from dataclasses import dataclass
from enum import StrEnum

ANCHO = 3  # las revisiones se escriben como "008"


class Estado(StrEnum):
    OK = "OK"
    RENUMERAR = "RENUMERAR"
    CADENA_ROTA = "CADENA ROTA"
    MODIFICA_MAIN = "MODIFICA MAIN"


class ErrorDeUso(Exception):
    """Error que se informa con un mensaje y código de salida 2."""


@dataclass(frozen=True)
class Migracion:
    archivo: str
    revision: str
    down_revision: str | None
    blob: str

    @property
    def numero(self) -> int:
        return int(self.revision)


@dataclass
class Lectura:
    """Migraciones de una rama, más lo que no se pudo leer o está repetido."""

    migraciones: list[Migracion]
    problemas: list[str]

    def por_revision(self) -> dict[str, Migracion]:
        return {m.revision: m for m in self.migraciones}


def git(*args: str) -> str:
    resultado = subprocess.run(
        ["git", *args], capture_output=True, text=True, encoding="utf-8", check=False
    )
    if resultado.returncode != 0:
        raise ErrorDeUso(f"`git {' '.join(args)}` falló: {resultado.stderr.strip()}")
    return resultado.stdout


def leer_asignaciones(codigo: str) -> dict[str, ast.expr | None]:
    """Devuelve los nodos asignados a `revision` y `down_revision` en el módulo."""
    valores: dict[str, ast.expr | None] = {}
    for nodo in ast.parse(codigo).body:
        if isinstance(nodo, ast.AnnAssign) and isinstance(nodo.target, ast.Name):
            nombre, valor = nodo.target.id, nodo.value
        elif (
            isinstance(nodo, ast.Assign)
            and len(nodo.targets) == 1
            and isinstance(nodo.targets[0], ast.Name)
        ):
            nombre, valor = nodo.targets[0].id, nodo.value
        else:
            continue
        if nombre in ("revision", "down_revision"):
            valores[nombre] = valor
    return valores


def es_numerica(valor: object) -> bool:
    return isinstance(valor, str) and valor.isdigit()


def leer_migracion(archivo: str, codigo: str, blob: str) -> Migracion | str:
    """Devuelve la migración, o un texto con el problema si no se puede usar."""
    try:
        nodos = leer_asignaciones(codigo)
    except SyntaxError as error:
        return f"`{archivo}` no se puede parsear (línea {error.lineno})."
    nodo_rev, nodo_down = nodos.get("revision"), nodos.get("down_revision")
    revision = nodo_rev.value if isinstance(nodo_rev, ast.Constant) else None
    if not es_numerica(revision):
        return f"`{archivo}` no declara una `revision` numérica literal."
    if isinstance(nodo_down, ast.Tuple | ast.List):
        return (
            f"`{archivo}` es una migración de merge (varios `down_revision`): "
            "en este proyecto se renumera en lugar de mergear cabezas."
        )
    down = nodo_down.value if isinstance(nodo_down, ast.Constant) else None
    if down is not None and not es_numerica(down):
        return f"`{archivo}` tiene un `down_revision` no numérico (`{down}`)."
    return Migracion(archivo, revision, down, blob)


def leer_rama(ref: str, directorio: str) -> Lectura:
    salida = git("ls-tree", ref, f"{directorio.rstrip('/')}/")
    lectura = Lectura([], [])
    for linea in salida.splitlines():
        meta, ruta = linea.split("\t", 1)
        blob = meta.split()[2]
        archivo = ruta.rsplit("/", 1)[-1]
        if not archivo.endswith(".py") or archivo.startswith("__"):
            continue
        resultado = leer_migracion(archivo, git("show", f"{ref}:{ruta}"), blob)
        if isinstance(resultado, str):
            lectura.problemas.append(resultado)
        else:
            lectura.migraciones.append(resultado)
    return lectura


def cabezas(migraciones: list[Migracion]) -> list[str]:
    apuntadas = {m.down_revision for m in migraciones}
    return sorted({m.revision for m in migraciones} - apuntadas)


def problemas_de_integridad(lectura: Lectura) -> list[str]:
    """Chequeos que valen para cualquier rama, incluida la base."""
    problemas = list(lectura.problemas)
    vistas: dict[str, str] = {}
    revisiones = {m.revision for m in lectura.migraciones}
    for m in sorted(lectura.migraciones, key=lambda m: (m.revision, m.archivo)):
        if m.revision in vistas:
            problemas.append(
                f"`{m.revision}` está declarada en `{vistas[m.revision]}` y en `{m.archivo}`: "
                "Alembic no arranca con revisiones repetidas."
            )
        vistas.setdefault(m.revision, m.archivo)
        if not m.archivo.startswith(f"{m.revision}_"):
            problemas.append(
                f'`{m.archivo}` declara `revision = "{m.revision}"`: '
                "el nombre del archivo no coincide."
            )
        if m.down_revision is not None and m.down_revision not in revisiones:
            problemas.append(
                f'`{m.archivo}` apunta a `down_revision = "{m.down_revision}"`, '
                "que no existe en la rama."
            )
    heads = cabezas(lectura.migraciones)
    if len(heads) > 1:
        problemas.append(
            f"Hay {len(heads)} cabezas ({', '.join(heads)}): `alembic upgrade head` va a fallar."
        )
    return problemas


def formatear(numero: int) -> str:
    return str(numero).zfill(ANCHO)


def clasificar(
    mig: Migracion, head_main: int, previas: dict[int, Estado]
) -> tuple[Estado, str]:
    """Decide si una migración nueva de la rama está bien numerada respecto de main.

    - mig: una migración que la rama agrega y que no está en main.
    - head_main: número de la cabeza de main (por ejemplo 7 si main llega a 007).
    - previas: estado de las migraciones nuevas de la misma rama ya clasificadas
      (se clasifican en orden ascendente).
    """
    libre, cabeza = formatear(head_main + 1), formatear(head_main)
    if mig.numero <= head_main:
        return (
            Estado.RENUMERAR,
            f"`{mig.revision}` ya existe en main: pasar a `{libre}` sobre `{cabeza}`",
        )
    abajo = int(mig.down_revision) if mig.down_revision is not None else None
    if abajo is not None and abajo in previas:
        if previas[abajo] is not Estado.OK:
            return (
                Estado.RENUMERAR,
                f"va encima de `{formatear(abajo)}`, que también hay que renumerar",
            )
        if abajo == mig.numero - 1:
            return (
                Estado.OK,
                f"sigue a `{formatear(abajo)}`, otra migración nueva de la rama",
            )
    elif mig.numero == head_main + 1 and abajo == head_main:
        return Estado.OK, f"sigue a la cabeza de main (`{cabeza}`)"
    return Estado.CADENA_ROTA, (
        f"`{mig.revision}` apunta a `{mig.down_revision}`; se esperaba `{libre}` sobre `{cabeza}`"
    )


def ramas_remotas(remoto: str, base: str) -> list[str]:
    salida = git("for-each-ref", "--format=%(refname:short)", f"refs/remotes/{remoto}")
    excluidas = {remoto, f"{remoto}/HEAD", f"{remoto}/{base}"}
    return sorted(r for r in salida.split() if r not in excluidas)


def revisar(args: argparse.Namespace) -> int:
    if not args.sin_fetch:
        git("fetch", "--prune", args.remoto)

    ref_base = f"{args.remoto}/{args.base}"
    if (
        ref_base
        not in git(
            "for-each-ref", "--format=%(refname:short)", f"refs/remotes/{args.remoto}"
        ).split()
    ):
        raise ErrorDeUso(f"No existe la rama base `{ref_base}`.")
    ramas = ramas_remotas(args.remoto, args.base)
    if args.rama:
        pedidas = [f"{args.remoto}/{r}" for r in args.rama]
        faltan = [r for r in pedidas if r not in ramas]
        if faltan:
            raise ErrorDeUso(
                f"No existen en el remoto: {', '.join(faltan)}. ¿La rama está pusheada?"
            )
        ramas = pedidas

    lectura_base = leer_rama(ref_base, args.dir)
    base = lectura_base.por_revision()
    heads_base = cabezas(lectura_base.migraciones)
    hay_problemas = False

    print(f"# Revisión de migraciones Alembic\n\nBase: `{ref_base}`\n")
    problemas_base = problemas_de_integridad(lectura_base)
    if problemas_base:
        hay_problemas = True
        print("## ⚠️ La base tiene problemas\n")
        print("\n".join(f"- {p}" for p in problemas_base) + "\n")
    if not base:
        print(f"La base no tiene migraciones en `{args.dir}`.\n")
    head_main = int(heads_base[-1]) if heads_base else 0
    cabeza, libre = formatear(head_main), formatear(head_main + 1)
    print(f"Cabeza de `{args.base}`: **{cabeza}** — próxima libre: **{libre}**\n")

    reclamos: dict[str, list[str]] = {}  # número -> ramas que lo agregan
    filas: list[str] = []
    detalles: list[str] = []

    for rama in ramas:
        lectura = leer_rama(rama, args.dir)
        problemas = problemas_de_integridad(lectura)
        if problemas:
            hay_problemas = True
            detalles.append(f"### `{rama}`\n" + "\n".join(f"- {p}" for p in problemas))
        if not lectura.migraciones:
            filas.append(f"| `{rama}` | — | — | sin migraciones |")
            continue

        iguales_a_main = [
            m
            for m in lectura.migraciones
            if m.revision in base
            and base[m.revision].blob == m.blob
            and base[m.revision].archivo == m.archivo
        ]
        editadas = [
            m
            for m in lectura.migraciones
            if m not in iguales_a_main
            and m.revision in base
            and base[m.revision].archivo == m.archivo
        ]
        nuevas = sorted(
            (
                m
                for m in lectura.migraciones
                if m not in iguales_a_main and m not in editadas
            ),
            key=lambda m: (m.numero, m.archivo),
        )

        for m in editadas:
            hay_problemas = True
            motivo = (
                "distinta de la versión de main: no editar migraciones ya mergeadas "
                "(crear una nueva) o actualizar la rama desde main"
            )
            filas.append(
                f"| `{rama}` | `{m.archivo}` | ❌ {Estado.MODIFICA_MAIN} | {motivo} |"
            )

        if not nuevas and not editadas:
            atraso = head_main - int(cabezas(lectura.migraciones)[-1])
            nota = "sin migraciones propias" + (
                f" (atrasada {atraso} respecto de la base)" if atraso > 0 else ""
            )
            filas.append(f"| `{rama}` | — | — | {nota} |")

        previas: dict[int, Estado] = {}
        for m in nuevas:
            reclamos.setdefault(m.revision, []).append(rama)
            estado, motivo = clasificar(m, head_main, previas)
            previas[m.numero] = estado
            hay_problemas |= estado is not Estado.OK
            icono = "✅" if estado is Estado.OK else "❌"
            filas.append(f"| `{rama}` | `{m.archivo}` | {icono} {estado} | {motivo} |")

    print("## Ramas\n\n| Rama | Migración | Estado | Motivo |\n|---|---|---|---|")
    print("\n".join(filas) + "\n")

    choques = {r: rs for r, rs in reclamos.items() if len(set(rs)) > 1}
    if choques:
        print("## Choques entre ramas (informativo)\n")
        for revision, rs in sorted(choques.items()):
            nombres = ", ".join(f"`{r}`" for r in sorted(set(rs)))
            print(
                f"- `{revision}` lo agregan {nombres}: la que mergee segunda renumera."
            )
        print()

    if detalles:
        print("## Integridad por rama\n\n" + "\n\n".join(detalles) + "\n")

    veredicto = (
        "hay que corregir antes de mergear."
        if hay_problemas
        else "numeración correcta."
    )
    print(f"**Veredicto:** {veredicto}")
    return 1 if hay_problemas else 0


def main() -> int:
    for flujo in (sys.stdout, sys.stderr):
        if hasattr(flujo, "reconfigure"):
            flujo.reconfigure(encoding="utf-8")

    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--remoto", default="origin")
    parser.add_argument("--base", default="main")
    parser.add_argument("--dir", default="backend/alembic/versions")
    parser.add_argument(
        "--rama", action="append", help="Revisar solo estas ramas (sin el remoto)"
    )
    parser.add_argument(
        "--sin-fetch", action="store_true", help="No correr git fetch --prune"
    )
    args = parser.parse_args()

    try:
        return revisar(args)
    except ErrorDeUso as error:
        print(f"Error: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
