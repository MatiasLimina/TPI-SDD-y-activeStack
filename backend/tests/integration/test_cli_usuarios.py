"""CLI `python -m app.cli usuarios`: alta y desactivación sobre PostgreSQL real.

La contraseña llega por `USUARIO_PASSWORD` o por un `pedir` falso (nunca por argumento) y no debe
aparecer, ni ella ni su hash, en ninguna salida.
"""

import os
import subprocess
import sys
from collections.abc import Sequence
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import func, select
from sqlalchemy.exc import DataError
from sqlalchemy.orm import Session

from app.application.autenticacion import IniciarSesion
from app.cli import main
from app.domain.usuarios import CredencialesInvalidasError
from app.infrastructure.db.models import Profesional, Turno, Usuario
from app.infrastructure.db.repositorio_usuarios import RepositorioUsuarios
from app.infrastructure.security.contrasenas import Hasher
from app.infrastructure.security.tokens import EmisorTokens
from tests.conftest import BACKEND_DIR
from tests.integration.factories import crear_catalogo

PASSWORD = "clave-ficticia-cli-0001"
ENTORNO = {"USUARIO_PASSWORD": PASSWORD}


class PedirFalso:
    """Reemplaza a `getpass`: devuelve las respuestas en orden y registra cuántas veces se usó."""

    def __init__(self, *respuestas: str) -> None:
        self._respuestas = list(respuestas)
        self.llamadas = 0

    def __call__(self, prompt: str = "") -> str:
        self.llamadas += 1
        assert self._respuestas, "el CLI pidió más respuestas de las previstas"
        return self._respuestas.pop(0)


def _ejecutar(
    db_session: Session,
    hasher: Hasher,
    argv: Sequence[str],
    *,
    entorno: dict[str, str] | None = None,
    pedir: PedirFalso | None = None,
) -> int:
    return main(
        list(argv),
        sesion=db_session,
        hasher=hasher,
        entorno=ENTORNO if entorno is None else entorno,
        pedir=pedir if pedir is not None else PedirFalso(),
    )


def _alta(*args: str) -> list[str]:
    return ["usuarios", "alta", *args]


def _desactivar(email: str) -> list[str]:
    return ["usuarios", "desactivar", "--email", email]


def _cantidad_usuarios(session: Session) -> int:
    return session.scalar(select(func.count()).select_from(Usuario)) or 0


def _sin_secretos(capsys: pytest.CaptureFixture[str], *secretos: str) -> str:
    """Devuelve stderr tras comprobar que ni las contraseñas ni ningún hash salieron."""
    salida = capsys.readouterr()
    for texto in (salida.out, salida.err):
        for secreto in (PASSWORD, *secretos):
            assert secreto not in texto
        assert "$argon2" not in texto
    return salida.err


def _profesional(session: Session, *, activo: bool = True) -> Profesional:
    profesional = Profesional(nombre="Carla", apellido="Ficticia", activo=activo)
    session.add(profesional)
    session.flush()
    return profesional


def _usuario_existente(
    session: Session,
    hasher: Hasher,
    *,
    email: str = "existente@example.com",
    activo: bool = True,
    profesional: Profesional | None = None,
) -> Usuario:
    usuario = Usuario(
        email=email,
        password_hash=hasher.hash("clave-ficticia-previa"),
        rol="odontologo" if profesional else "recepcionista",
        profesional_id=profesional.id if profesional else None,
        activo=activo,
    )
    session.add(usuario)
    session.flush()
    return usuario


def _iniciar_sesion(
    session: Session, hasher: Hasher, emisor: EmisorTokens, email: str, password: str
) -> str:
    return IniciarSesion(RepositorioUsuarios(session), hasher, emisor).ejecutar(email, password)


# --- 8.1 Alta exitosa ---------------------------------------------------------------------------


def test_alta_de_recepcionista_crea_usuario_activo_sin_profesional(
    db_session: Session, hasher_test: Hasher, capsys: pytest.CaptureFixture[str]
) -> None:
    codigo = _ejecutar(
        db_session,
        hasher_test,
        _alta("--email", "recepcion2@example.com", "--rol", "recepcionista"),
    )

    assert codigo == 0
    usuario = RepositorioUsuarios(db_session).por_email("recepcion2@example.com")
    assert usuario is not None
    assert (usuario.rol, usuario.activo, usuario.profesional_id) == ("recepcionista", True, None)
    assert usuario.password_hash != PASSWORD
    _sin_secretos(capsys, usuario.password_hash)


def test_alta_de_odontologo_con_profesional_activo_permite_iniciar_sesion(
    db_session: Session, hasher_test: Hasher, emisor_test: EmisorTokens
) -> None:
    profesional = _profesional(db_session)

    codigo = _ejecutar(
        db_session,
        hasher_test,
        _alta(
            *("--email", "odonto2@example.com", "--rol", "odontologo"),
            *("--profesional-id", str(profesional.id)),
        ),
    )

    assert codigo == 0
    usuario = RepositorioUsuarios(db_session).por_email("odonto2@example.com")
    assert usuario is not None
    assert (usuario.rol, usuario.profesional_id) == ("odontologo", profesional.id)
    assert _iniciar_sesion(db_session, hasher_test, emisor_test, "odonto2@example.com", PASSWORD)


def test_alta_guarda_el_email_normalizado(db_session: Session, hasher_test: Hasher) -> None:
    codigo = _ejecutar(
        db_session,
        hasher_test,
        _alta("--email", " Recepcion3@Example.com ", "--rol", "recepcionista"),
    )

    assert codigo == 0
    assert RepositorioUsuarios(db_session).por_email("recepcion3@example.com") is not None


def test_alta_sin_variable_pide_la_contrasena_dos_veces(
    db_session: Session,
    hasher_test: Hasher,
    emisor_test: EmisorTokens,
    capsys: pytest.CaptureFixture[str],
) -> None:
    pedir = PedirFalso("clave-ficticia-prompt", "clave-ficticia-prompt")

    codigo = _ejecutar(
        db_session,
        hasher_test,
        _alta("--email", "prompt@example.com", "--rol", "recepcionista"),
        entorno={},
        pedir=pedir,
    )

    assert codigo == 0
    assert pedir.llamadas == 2
    assert _iniciar_sesion(
        db_session, hasher_test, emisor_test, "prompt@example.com", "clave-ficticia-prompt"
    )
    _sin_secretos(capsys, "clave-ficticia-prompt")


# --- 8.2 Rechazos del alta ----------------------------------------------------------------------


@pytest.mark.parametrize(
    "argumentos",
    [
        pytest.param(("--email", "sin-arroba", "--rol", "recepcionista"), id="email-sin-arroba"),
        pytest.param(
            ("--email", "con espacio@example.com", "--rol", "recepcionista"), id="email-con-espacio"
        ),
        pytest.param(
            ("--email", "odonto@example.com", "--rol", "odontologo"),
            id="odontologo-sin-profesional",
        ),
        pytest.param(
            (
                *("--email", "recep@example.com", "--rol", "recepcionista"),
                *("--profesional-id", str(uuid4())),
            ),
            id="recepcionista-con-profesional",
        ),
        pytest.param(
            (
                *("--email", "odonto@example.com", "--rol", "odontologo"),
                *("--profesional-id", str(uuid4())),
            ),
            id="profesional-inexistente",
        ),
    ],
)
def test_alta_con_datos_invalidos_devuelve_1_y_no_crea_usuario(
    db_session: Session,
    hasher_test: Hasher,
    capsys: pytest.CaptureFixture[str],
    argumentos: tuple[str, ...],
) -> None:
    antes = _cantidad_usuarios(db_session)

    codigo = _ejecutar(db_session, hasher_test, _alta(*argumentos))

    assert codigo == 1
    assert _sin_secretos(capsys).strip() != ""
    assert _cantidad_usuarios(db_session) == antes


def test_alta_con_email_de_usuario_inactivo_es_rechazada_y_sigue_inactivo(
    db_session: Session, hasher_test: Hasher, capsys: pytest.CaptureFixture[str]
) -> None:
    previo = _usuario_existente(db_session, hasher_test, activo=False)
    antes = _cantidad_usuarios(db_session)

    codigo = _ejecutar(
        db_session,
        hasher_test,
        _alta("--email", "Existente@example.com", "--rol", "recepcionista"),
    )

    assert codigo == 1
    assert "registrado" in _sin_secretos(capsys)
    assert _cantidad_usuarios(db_session) == antes
    assert previo.activo is False


def test_alta_con_profesional_inactivo_es_rechazada(
    db_session: Session, hasher_test: Hasher, capsys: pytest.CaptureFixture[str]
) -> None:
    profesional = _profesional(db_session, activo=False)
    antes = _cantidad_usuarios(db_session)

    codigo = _ejecutar(
        db_session,
        hasher_test,
        _alta(
            *("--email", "odonto@example.com", "--rol", "odontologo"),
            *("--profesional-id", str(profesional.id)),
        ),
    )

    assert codigo == 1
    assert "inactivo" in _sin_secretos(capsys)
    assert _cantidad_usuarios(db_session) == antes


def test_alta_con_profesional_que_ya_tiene_usuario_activo_es_rechazada(
    db_session: Session, hasher_test: Hasher, capsys: pytest.CaptureFixture[str]
) -> None:
    profesional = _profesional(db_session)
    existente = _usuario_existente(db_session, hasher_test, profesional=profesional)
    antes = _cantidad_usuarios(db_session)

    codigo = _ejecutar(
        db_session,
        hasher_test,
        _alta(
            *("--email", "otro@example.com", "--rol", "odontologo"),
            *("--profesional-id", str(profesional.id)),
        ),
    )

    assert codigo == 1
    assert "usuario activo" in _sin_secretos(capsys)
    assert _cantidad_usuarios(db_session) == antes
    assert existente.activo is True


def test_alta_con_variable_definida_pero_vacia_se_rechaza_sin_pedir_nada(
    db_session: Session, hasher_test: Hasher, capsys: pytest.CaptureFixture[str]
) -> None:
    pedir = PedirFalso(PASSWORD, PASSWORD)
    antes = _cantidad_usuarios(db_session)

    codigo = _ejecutar(
        db_session,
        hasher_test,
        _alta("--email", "vacia@example.com", "--rol", "recepcionista"),
        entorno={"USUARIO_PASSWORD": ""},
        pedir=pedir,
    )

    assert codigo == 1
    assert pedir.llamadas == 0
    assert "USUARIO_PASSWORD" in _sin_secretos(capsys)
    assert _cantidad_usuarios(db_session) == antes


@pytest.mark.parametrize(
    "respuestas",
    [
        pytest.param(("", ""), id="contrasena-vacia"),
        pytest.param(("clave-ficticia-uno", "clave-ficticia-dos"), id="confirmacion-distinta"),
    ],
)
def test_alta_con_contrasena_invalida_por_consola_se_rechaza(
    db_session: Session,
    hasher_test: Hasher,
    capsys: pytest.CaptureFixture[str],
    respuestas: tuple[str, str],
) -> None:
    antes = _cantidad_usuarios(db_session)

    codigo = _ejecutar(
        db_session,
        hasher_test,
        _alta("--email", "consola@example.com", "--rol", "recepcionista"),
        entorno={},
        pedir=PedirFalso(*respuestas),
    )

    assert codigo == 1
    assert _sin_secretos(capsys, *(r for r in respuestas if r)).strip() != ""
    assert _cantidad_usuarios(db_session) == antes


def test_alta_ante_integrity_error_inesperada_devuelve_1_sin_traceback_ni_hash(
    db_session: Session,
    hasher_test: Hasher,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Sin normalizar, un email con mayúsculas llega a la base y viola el CHECK de email normalizado.
    monkeypatch.setattr("app.cli.usuarios.normalizar_email", lambda email: email)
    antes = _cantidad_usuarios(db_session)

    codigo = _ejecutar(
        db_session,
        hasher_test,
        _alta("--email", "Mayusculas@Example.com", "--rol", "recepcionista"),
    )

    assert codigo == 1
    err = _sin_secretos(capsys)
    assert "Traceback" not in err
    assert "email_normalizado" in err
    assert _cantidad_usuarios(db_session) == antes


def _email_de_largo(largo: int) -> str:
    dominio = "@example.com"
    return "a" * (largo - len(dominio)) + dominio


def test_alta_con_email_mas_largo_que_la_columna_devuelve_1_sin_traceback_ni_hash(
    db_session: Session, hasher_test: Hasher, capsys: pytest.CaptureFixture[str]
) -> None:
    antes = _cantidad_usuarios(db_session)

    codigo = _ejecutar(
        db_session, hasher_test, _alta("--email", _email_de_largo(255), "--rol", "recepcionista")
    )

    assert codigo == 1
    err = _sin_secretos(capsys)
    assert err.strip() != ""
    assert "Traceback" not in err
    assert "password_hash" not in err
    assert _cantidad_usuarios(db_session) == antes


def test_alta_con_email_de_exactamente_254_caracteres_se_crea(
    db_session: Session, hasher_test: Hasher, capsys: pytest.CaptureFixture[str]
) -> None:
    email = _email_de_largo(254)

    codigo = _ejecutar(db_session, hasher_test, _alta("--email", email, "--rol", "recepcionista"))

    assert codigo == 0
    assert RepositorioUsuarios(db_session).por_email(email) is not None
    _sin_secretos(capsys)


def test_alta_ante_error_de_base_al_confirmar_devuelve_1_sin_traceback_ni_hash(
    db_session: Session,
    hasher_test: Hasher,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def commit_roto() -> None:
        raise DataError(
            "INSERT ... [parameters: {'password_hash': '$argon2id$x'}]", {}, Exception()
        )

    monkeypatch.setattr(db_session, "commit", commit_roto)
    antes = _cantidad_usuarios(db_session)

    codigo = _ejecutar(
        db_session, hasher_test, _alta("--email", "commit@example.com", "--rol", "recepcionista")
    )

    assert codigo == 1
    err = _sin_secretos(capsys)
    assert "Traceback" not in err
    assert "password_hash" not in err
    assert _cantidad_usuarios(db_session) == antes


@pytest.mark.parametrize(
    "argumentos",
    [
        pytest.param(("--email", "a@example.com", "--rol", "administrador"), id="rol-desconocido"),
        pytest.param(
            (
                *("--email", "a@example.com", "--rol", "recepcionista"),
                *("--password", "secreto-ficticio"),
            ),
            id="password-como-argumento",
        ),
        pytest.param(
            (
                *("--email", "a@example.com", "--rol", "recepcionista"),
                "--password=secreto-ficticio",
            ),
            id="password-con-igual",
        ),
        pytest.param(("--email", "a@example.com"), id="falta-rol"),
        pytest.param(
            (
                *("--email", "a@example.com", "--rol", "odontologo"),
                *("--profesional-id", "no-es-uuid"),
            ),
            id="profesional-id-no-uuid",
        ),
    ],
)
def test_alta_con_uso_invalido_devuelve_2_de_argparse_sin_filtrar_el_valor(
    db_session: Session,
    hasher_test: Hasher,
    capsys: pytest.CaptureFixture[str],
    argumentos: tuple[str, ...],
) -> None:
    antes = _cantidad_usuarios(db_session)

    codigo = _ejecutar(db_session, hasher_test, _alta(*argumentos))

    assert codigo == 2
    _sin_secretos(capsys, "secreto-ficticio")
    assert _cantidad_usuarios(db_session) == antes


@pytest.mark.parametrize("argv", [[], ["usuarios"]], ids=["sin-comando", "sin-accion"])
def test_sin_comando_o_sin_accion_devuelve_2(
    db_session: Session, hasher_test: Hasher, argv: list[str]
) -> None:
    assert _ejecutar(db_session, hasher_test, argv) == 2


# --- 8.3 Desactivar -----------------------------------------------------------------------------


def test_desactivar_marca_inactivo_conserva_la_fila_e_impide_el_login(
    db_session: Session,
    hasher_test: Hasher,
    emisor_test: EmisorTokens,
    capsys: pytest.CaptureFixture[str],
) -> None:
    usuario = _usuario_existente(db_session, hasher_test)

    codigo = _ejecutar(db_session, hasher_test, _desactivar(" Existente@Example.com "))

    assert codigo == 0
    fila = RepositorioUsuarios(db_session).por_email("existente@example.com")
    assert fila is not None and fila.id == usuario.id
    assert fila.activo is False
    with pytest.raises(CredencialesInvalidasError):
        _iniciar_sesion(
            db_session, hasher_test, emisor_test, "existente@example.com", "clave-ficticia-previa"
        )
    _sin_secretos(capsys)


def test_desactivar_dos_veces_es_idempotente(
    db_session: Session, hasher_test: Hasher, capsys: pytest.CaptureFixture[str]
) -> None:
    usuario = _usuario_existente(db_session, hasher_test)
    assert _ejecutar(db_session, hasher_test, _desactivar(usuario.email)) == 0
    hash_antes = usuario.password_hash

    codigo = _ejecutar(db_session, hasher_test, _desactivar(usuario.email))

    assert codigo == 0
    assert (usuario.activo, usuario.password_hash) == (False, hash_antes)
    _sin_secretos(capsys)


def test_desactivar_email_inexistente_devuelve_1_con_mensaje(
    db_session: Session, hasher_test: Hasher, capsys: pytest.CaptureFixture[str]
) -> None:
    codigo = _ejecutar(db_session, hasher_test, _desactivar("nadie@example.com"))

    assert codigo == 1
    assert "nadie@example.com" in _sin_secretos(capsys)


def test_desactivar_conserva_el_autor_de_los_turnos(
    db_session: Session, hasher_test: Hasher
) -> None:
    autor = _usuario_existente(db_session, hasher_test)
    catalogo = crear_catalogo(db_session)
    inicio = datetime(2026, 10, 8, 13, 0, tzinfo=UTC)
    turno = Turno(
        profesional_id=catalogo.profesionales[0].id,
        paciente_id=catalogo.pacientes[0].id,
        prestacion_id=catalogo.consulta.id,
        inicio=inicio,
        fin=inicio + timedelta(minutes=30),
        duracion_min=30,
        creado_por=autor.id,
    )
    db_session.add(turno)
    db_session.flush()

    codigo = _ejecutar(db_session, hasher_test, _desactivar(autor.email))

    assert codigo == 0
    db_session.refresh(turno)
    assert autor.activo is False
    assert turno.creado_por == autor.id


# --- 8.4 Smoke ----------------------------------------------------------------------------------


def test_ayuda_de_usuarios_lista_alta_y_desactivar_sin_base_ni_configuracion() -> None:
    sin_configuracion = {
        k: v
        for k, v in os.environ.items()
        if k not in {"DATABASE_URL", "TEST_DATABASE_URL", "JWT_SECRET", "USUARIO_PASSWORD"}
    }

    resultado = subprocess.run(
        [sys.executable, "-m", "app.cli", "usuarios", "--help"],
        cwd=BACKEND_DIR,
        env=sin_configuracion,
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )

    assert resultado.returncode == 0, resultado.stderr
    assert "alta" in resultado.stdout
    assert "desactivar" in resultado.stdout
