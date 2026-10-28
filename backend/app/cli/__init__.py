"""Administración por línea de comandos: `python -m app.cli usuarios {alta,desactivar}`.

Códigos de salida: 0 éxito, 1 error de dominio (mensaje en stderr), 2 uso inválido (argparse).
La contraseña nunca viaja por argumento ni se imprime: ver `app.cli.usuarios`.
"""

import argparse
import getpass
import os
import sys
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import NoReturn

from sqlalchemy.orm import Session

from app.cli import usuarios
from app.domain.usuarios import AltaUsuarioInvalidaError, UsuarioInexistenteError
from app.infrastructure.security.contrasenas import Hasher, get_hasher

Pedir = Callable[[str], str]


@dataclass(frozen=True)
class Contexto:
    """Dependencias de un comando: se inyectan en los tests y se resuelven aquí en producción."""

    sesion: Session
    hasher: Hasher
    entorno: Mapping[str, str]
    pedir: Pedir


class ParserSeguro(argparse.ArgumentParser):
    """`argparse` que nunca repite el valor de una opción desconocida en sus mensajes.

    El mensaje por defecto (`unrecognized arguments: --password <valor>`) repetiría una contraseña
    pasada por error como argumento.
    """

    def parse_args(  # type: ignore[override]
        self, args: Sequence[str] | None = None, namespace: argparse.Namespace | None = None
    ) -> argparse.Namespace:
        parsed, sobrantes = self.parse_known_args(args, namespace)
        if sobrantes:
            opciones = sorted({s.split("=", 1)[0] for s in sobrantes if s.startswith("-")})
            detalle = ", ".join(opciones) if opciones else "argumento inesperado"
            self.error(f"opción no reconocida ({detalle}); la contraseña no se pasa por argumento")
        return parsed

    def error(self, message: str) -> NoReturn:
        self.print_usage(sys.stderr)
        self.exit(2, f"{self.prog}: error: {message}\n")


def _crear_parser() -> ParserSeguro:
    parser = ParserSeguro(prog="python -m app.cli", description="Administración del sistema.")
    comandos = parser.add_subparsers(dest="comando", required=True, metavar="comando")
    usuarios.registrar(comandos)
    return parser


def _codigo_de_salida(codigo: object) -> int:
    if codigo is None:
        return 0
    return codigo if isinstance(codigo, int) else 2


def _abrir_sesion() -> Session:
    # Import perezoso: pedir la ayuda o equivocarse de argumentos no necesita base ni .env.
    from app.infrastructure.db.session import get_engine

    return Session(get_engine(), expire_on_commit=False)


def main(
    argv: Sequence[str] | None = None,
    *,
    sesion: Session | None = None,
    hasher: Hasher | None = None,
    entorno: Mapping[str, str] | None = None,
    pedir: Pedir | None = None,
) -> int:
    """Ejecuta el comando y devuelve el código de salida; los parámetros son puntos de inyección."""
    try:
        args = _crear_parser().parse_args(argv)
    except SystemExit as salida:
        return _codigo_de_salida(salida.code)
    propia = sesion is None
    sesion_efectiva = _abrir_sesion() if sesion is None else sesion
    contexto = Contexto(
        sesion=sesion_efectiva,
        hasher=get_hasher() if hasher is None else hasher,
        entorno=os.environ if entorno is None else entorno,
        pedir=getpass.getpass if pedir is None else pedir,
    )
    ejecutar: Callable[[argparse.Namespace, Contexto], int] = args.ejecutar
    try:
        return ejecutar(args, contexto)
    except (AltaUsuarioInvalidaError, UsuarioInexistenteError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1
    finally:
        if propia:
            sesion_efectiva.close()


__all__ = ["main"]
