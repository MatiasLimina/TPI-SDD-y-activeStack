"""Subcomandos `usuarios alta` y `usuarios desactivar`.

La contraseña sale de `USUARIO_PASSWORD` (uso no interactivo) o de un prompt doble sin eco. No
existe opción de contraseña. Ni la contraseña ni su hash se imprimen ni van en ningún mensaje de
error: los errores de base se traducen mostrando solo el nombre de la restricción violada.
"""

import argparse
from collections.abc import Mapping
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy.exc import IntegrityError

from app.domain.usuarios import (
    AltaUsuarioInvalidaError,
    Rol,
    UsuarioInexistenteError,
    normalizar_email,
    validar_alta,
    validar_forma_email,
)
from app.infrastructure.db.models import Usuario
from app.infrastructure.db.repositorio_usuarios import RepositorioUsuarios

if TYPE_CHECKING:
    from app.cli import Contexto, Pedir

VARIABLE_PASSWORD = "USUARIO_PASSWORD"


def registrar(comandos: "argparse._SubParsersAction[argparse.ArgumentParser]") -> None:
    usuarios = comandos.add_parser("usuarios", help="Alta y baja de usuarios del sistema.")
    acciones = usuarios.add_subparsers(dest="accion", required=True, metavar="accion")

    alta_parser = acciones.add_parser("alta", help="Crea un usuario activo.")
    alta_parser.add_argument("--email", required=True)
    alta_parser.add_argument("--rol", required=True, choices=[r.value for r in Rol])
    alta_parser.add_argument("--profesional-id", type=UUID, default=None)
    alta_parser.set_defaults(ejecutar=alta)

    baja_parser = acciones.add_parser(
        "desactivar", help="Desactiva un usuario sin borrar la fila (idempotente)."
    )
    baja_parser.add_argument("--email", required=True)
    baja_parser.set_defaults(ejecutar=desactivar)


def _leer_password(entorno: Mapping[str, str], pedir: "Pedir") -> str:
    if VARIABLE_PASSWORD in entorno:
        valor = entorno[VARIABLE_PASSWORD]
        if not valor:
            raise AltaUsuarioInvalidaError(
                "password_vacia",
                f"{VARIABLE_PASSWORD} está definida pero vacía; defínela o quitá la variable "
                "para ingresarla por consola.",
            )
        return valor
    try:
        primera = pedir("Contraseña: ")
        if not primera:
            raise AltaUsuarioInvalidaError("password_vacia", "La contraseña no puede ser vacía.")
        segunda = pedir("Repetí la contraseña: ")
    except (EOFError, KeyboardInterrupt):
        raise AltaUsuarioInvalidaError(
            "password_no_leida", "No se pudo leer la contraseña."
        ) from None
    if primera != segunda:
        raise AltaUsuarioInvalidaError("password_distinta", "Las contraseñas no coinciden.")
    return primera


def _traducir(error: IntegrityError) -> AltaUsuarioInvalidaError:
    """Mensaje claro a partir del nombre de la restricción; nunca el texto de la excepción.

    El texto de una `IntegrityError` incluye los parámetros del INSERT, entre ellos el hash.
    """
    restriccion = getattr(getattr(error.orig, "diag", None), "constraint_name", None)
    if restriccion == "uq_usuario_email":
        return AltaUsuarioInvalidaError("email_duplicado", "Ese email ya está registrado.")
    if restriccion == "uq_usuario_profesional_activo":
        return AltaUsuarioInvalidaError(
            "profesional_con_usuario", "Ese profesional ya tiene un usuario activo."
        )
    detalle = f" (restricción {restriccion})" if restriccion else ""
    return AltaUsuarioInvalidaError(
        "no_guardado", f"No se pudo guardar el usuario: la base rechazó los datos{detalle}."
    )


def alta(args: argparse.Namespace, contexto: "Contexto") -> int:
    email = normalizar_email(args.email)
    validar_forma_email(email)
    validar_alta(args.rol, args.profesional_id)
    repositorio = RepositorioUsuarios(contexto.sesion)
    if args.profesional_id is not None:
        profesional = repositorio.profesional_por_id(args.profesional_id)
        if profesional is None:
            raise AltaUsuarioInvalidaError(
                "profesional_inexistente", "No existe un profesional con ese id."
            )
        if not profesional.activo:
            raise AltaUsuarioInvalidaError("profesional_inactivo", "El profesional está inactivo.")
        if repositorio.activo_de_profesional(args.profesional_id) is not None:
            raise AltaUsuarioInvalidaError(
                "profesional_con_usuario", "Ese profesional ya tiene un usuario activo."
            )
    if repositorio.por_email(email) is not None:
        raise AltaUsuarioInvalidaError("email_duplicado", "Ese email ya está registrado.")
    password_hash = contexto.hasher.hash(_leer_password(contexto.entorno, contexto.pedir))
    usuario = Usuario(
        email=email, password_hash=password_hash, rol=args.rol, profesional_id=args.profesional_id
    )
    try:
        # Savepoint: si la base rechaza el INSERT, solo se deshace esto y la sesión sigue usable.
        with contexto.sesion.begin_nested():
            repositorio.agregar(usuario)
    except IntegrityError as error:
        raise _traducir(error) from None
    contexto.sesion.commit()
    print(f"Usuario creado: {email} ({args.rol}).")
    return 0


def desactivar(args: argparse.Namespace, contexto: "Contexto") -> int:
    email = normalizar_email(args.email)
    usuario = RepositorioUsuarios(contexto.sesion).por_email(email)
    if usuario is None:
        raise UsuarioInexistenteError(f"No existe un usuario con el email {email}.")
    if not usuario.activo:
        print(f"El usuario {email} ya estaba inactivo.")
        return 0
    usuario.activo = False
    contexto.sesion.commit()
    print(f"Usuario desactivado: {email}.")
    return 0
