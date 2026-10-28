"""Caso de uso IniciarSesion con repositorio real (PostgreSQL), hasher barato y emisor de test."""

from datetime import UTC, datetime, timedelta

import jwt
import pytest
from pwdlib import PasswordHash
from pwdlib.hashers.argon2 import Argon2Hasher
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.application.autenticacion import IniciarSesion
from app.domain.usuarios import CredencialesInvalidasError
from app.infrastructure.db.models import Profesional, Usuario
from app.infrastructure.db.repositorio_usuarios import RepositorioUsuarios
from app.infrastructure.security.contrasenas import Hasher
from app.infrastructure.security.tokens import EmisorTokens
from tests.conftest import CONTRASENA_RECEPCIONISTA, SECRETO_TEST

CONTRASENA_ODONTOLOGO = "clave-ficticia-odontologo"


class _Argon2Espia(Argon2Hasher):
    """Argon2id barato que cuenta las verificaciones reales (el trabajo caro, no la fachada)."""

    def __init__(self) -> None:
        super().__init__(time_cost=1, memory_cost=8, parallelism=1)
        self.verificaciones = 0

    def verify(self, password: str | bytes, hash: str | bytes) -> bool:
        self.verificaciones += 1
        return super().verify(password, hash)


def _caso(session: Session, hasher: Hasher, emisor: EmisorTokens) -> IniciarSesion:
    return IniciarSesion(RepositorioUsuarios(session), hasher, emisor)


def _claims(token: str) -> dict[str, object]:
    return jwt.decode(token, SECRETO_TEST, algorithms=["HS256"])


@pytest.fixture
def odontologo(db_session: Session, hasher_test: Hasher) -> Usuario:
    profesional = Profesional(nombre="Ana", apellido="Ficticia")
    db_session.add(profesional)
    db_session.flush()
    usuario = Usuario(
        email="ana.ficticia@example.com",
        password_hash=hasher_test.hash(CONTRASENA_ODONTOLOGO),
        rol="odontologo",
        profesional_id=profesional.id,
    )
    db_session.add(usuario)
    db_session.flush()
    return usuario


def test_recepcionista_activa_obtiene_token_con_los_claims_de_la_decision_4(
    db_session: Session, hasher_test: Hasher, emisor_test: EmisorTokens, recepcionista: Usuario
) -> None:
    caso = _caso(db_session, hasher_test, emisor_test)
    t0 = datetime.now(UTC)

    token = caso.ejecutar("recepcion@example.com", CONTRASENA_RECEPCIONISTA)

    t1 = datetime.now(UTC)
    claims = _claims(token)
    assert claims["sub"] == str(recepcionista.id)
    assert claims["rol"] == "recepcionista"
    assert claims["profesional_id"] is None
    exp = datetime.fromtimestamp(int(str(claims["exp"])), UTC)
    tolerancia = timedelta(seconds=5)
    assert t0 + timedelta(minutes=60) - tolerancia <= exp <= t1 + timedelta(minutes=60) + tolerancia


def test_odontologo_obtiene_su_rol_y_su_profesional(
    db_session: Session, hasher_test: Hasher, emisor_test: EmisorTokens, odontologo: Usuario
) -> None:
    caso = _caso(db_session, hasher_test, emisor_test)

    claims = _claims(caso.ejecutar("ana.ficticia@example.com", CONTRASENA_ODONTOLOGO))

    assert claims["sub"] == str(odontologo.id)
    assert claims["rol"] == "odontologo"
    assert claims["profesional_id"] == str(odontologo.profesional_id)


@pytest.mark.parametrize(
    "email",
    ["  Recepcion@Example.COM ", "RECEPCION@EXAMPLE.COM", "\trecepcion@example.com\n"],
)
def test_el_email_se_normaliza_antes_de_buscar_al_usuario(
    db_session: Session,
    hasher_test: Hasher,
    emisor_test: EmisorTokens,
    recepcionista: Usuario,
    email: str,
) -> None:
    caso = _caso(db_session, hasher_test, emisor_test)

    claims = _claims(caso.ejecutar(email, CONTRASENA_RECEPCIONISTA))

    assert claims["sub"] == str(recepcionista.id)


def test_cada_usuario_recibe_su_propio_token(
    db_session: Session,
    hasher_test: Hasher,
    emisor_test: EmisorTokens,
    recepcionista: Usuario,
    odontologo: Usuario,
) -> None:
    caso = _caso(db_session, hasher_test, emisor_test)

    sub_recepcion = _claims(caso.ejecutar("recepcion@example.com", CONTRASENA_RECEPCIONISTA))["sub"]
    sub_odontologo = _claims(caso.ejecutar("ana.ficticia@example.com", CONTRASENA_ODONTOLOGO))[
        "sub"
    ]

    assert sub_recepcion == str(recepcionista.id)
    assert sub_odontologo == str(odontologo.id)
    assert sub_recepcion != sub_odontologo


def test_un_login_valido_no_modifica_los_usuarios(
    db_session: Session, hasher_test: Hasher, emisor_test: EmisorTokens, recepcionista: Usuario
) -> None:
    hash_antes = recepcionista.password_hash

    _caso(db_session, hasher_test, emisor_test).ejecutar(
        "recepcion@example.com", CONTRASENA_RECEPCIONISTA
    )

    db_session.expire_all()
    assert db_session.scalars(select(Usuario.password_hash)).all() == [hash_antes]


@pytest.fixture
def argon2_espia() -> _Argon2Espia:
    return _Argon2Espia()


@pytest.fixture
def hasher_espia(argon2_espia: _Argon2Espia) -> Hasher:
    return Hasher(PasswordHash((argon2_espia,)))


@pytest.fixture
def usuarios_para_rechazo(db_session: Session, hasher_espia: Hasher) -> None:
    """Un activo (A) y un inactivo (B), con contraseñas conocidas, hasheados con el espía."""
    db_session.add_all(
        [
            Usuario(
                email="activo@example.com",
                password_hash=hasher_espia.hash("clave-ficticia-a"),
                rol="recepcionista",
            ),
            Usuario(
                email="inactivo@example.com",
                password_hash=hasher_espia.hash("clave-ficticia-b"),
                rol="recepcionista",
                activo=False,
            ),
        ]
    )
    db_session.flush()


RECHAZOS = [
    pytest.param("activo@example.com", "contrasena-incorrecta", id="contrasena-incorrecta"),
    pytest.param("inactivo@example.com", "clave-ficticia-b", id="inactivo-con-su-contrasena"),
    pytest.param("nadie@example.com", "clave-ficticia-a", id="email-inexistente"),
]


@pytest.mark.parametrize(("email", "password"), RECHAZOS)
def test_los_tres_rechazos_lanzan_credenciales_invalidas_tras_una_sola_verificacion(
    db_session: Session,
    hasher_espia: Hasher,
    argon2_espia: _Argon2Espia,
    emisor_test: EmisorTokens,
    usuarios_para_rechazo: None,
    email: str,
    password: str,
) -> None:
    caso = _caso(db_session, hasher_espia, emisor_test)
    antes = argon2_espia.verificaciones

    with pytest.raises(CredencialesInvalidasError):
        caso.ejecutar(email, password)

    assert argon2_espia.verificaciones - antes == 1


def test_contrasena_vacia_se_rechaza_tras_una_sola_verificacion(
    db_session: Session,
    hasher_espia: Hasher,
    argon2_espia: _Argon2Espia,
    emisor_test: EmisorTokens,
    usuarios_para_rechazo: None,
) -> None:
    caso = _caso(db_session, hasher_espia, emisor_test)
    antes = argon2_espia.verificaciones

    with pytest.raises(CredencialesInvalidasError):
        caso.ejecutar("activo@example.com", "")

    assert argon2_espia.verificaciones - antes == 1


def test_el_dummy_no_se_usa_cuando_el_email_existe(
    db_session: Session,
    hasher_espia: Hasher,
    argon2_espia: _Argon2Espia,
    emisor_test: EmisorTokens,
    usuarios_para_rechazo: None,
) -> None:
    """Un login válido también hace una sola verificación (la del hash del usuario)."""
    caso = _caso(db_session, hasher_espia, emisor_test)
    antes = argon2_espia.verificaciones

    caso.ejecutar("activo@example.com", "clave-ficticia-a")

    assert argon2_espia.verificaciones - antes == 1


def test_el_email_inexistente_se_normaliza_y_sigue_siendo_un_rechazo(
    db_session: Session,
    hasher_espia: Hasher,
    emisor_test: EmisorTokens,
    usuarios_para_rechazo: None,
) -> None:
    caso = _caso(db_session, hasher_espia, emisor_test)

    with pytest.raises(CredencialesInvalidasError):
        caso.ejecutar("  NADIE@Example.com ", "clave-ficticia-a")


def test_el_rechazo_no_modifica_a_ningun_usuario(
    db_session: Session,
    hasher_espia: Hasher,
    emisor_test: EmisorTokens,
    usuarios_para_rechazo: None,
) -> None:
    hashes_antes = set(db_session.scalars(select(Usuario.password_hash)))
    caso = _caso(db_session, hasher_espia, emisor_test)

    for email, password in (
        ("activo@example.com", "mal"),
        ("inactivo@example.com", "clave-ficticia-b"),
    ):
        with pytest.raises(CredencialesInvalidasError):
            caso.ejecutar(email, password)

    db_session.expire_all()
    assert set(db_session.scalars(select(Usuario.password_hash))) == hashes_antes


@pytest.fixture
def usuario_con_hash_viejo(db_session: Session) -> Usuario:
    """Usuario con un hash generado con otros parámetros (time_cost=2) que los del hasher."""
    hasher_viejo = Hasher(PasswordHash((Argon2Hasher(time_cost=2, memory_cost=8, parallelism=1),)))
    usuario = Usuario(
        email="antiguo@example.com",
        password_hash=hasher_viejo.hash("clave-ficticia-antigua"),
        rol="recepcionista",
    )
    db_session.add(usuario)
    db_session.flush()
    return usuario


def _hash_guardado(session: Session, usuario: Usuario) -> str:
    session.expire_all()
    return session.scalars(select(Usuario.password_hash).where(Usuario.id == usuario.id)).one()


def test_login_valido_con_hash_viejo_lo_actualiza_en_la_base(
    db_session: Session,
    hasher_test: Hasher,
    emisor_test: EmisorTokens,
    usuario_con_hash_viejo: Usuario,
) -> None:
    hash_viejo = usuario_con_hash_viejo.password_hash
    caso = _caso(db_session, hasher_test, emisor_test)

    caso.ejecutar("antiguo@example.com", "clave-ficticia-antigua")

    hash_nuevo = _hash_guardado(db_session, usuario_con_hash_viejo)
    assert hash_nuevo != hash_viejo
    assert "t=1" in hash_nuevo
    assert hasher_test.verify_and_update("clave-ficticia-antigua", hash_nuevo) == (True, None)


def test_un_segundo_login_no_vuelve_a_cambiar_el_hash(
    db_session: Session,
    hasher_test: Hasher,
    emisor_test: EmisorTokens,
    usuario_con_hash_viejo: Usuario,
) -> None:
    caso = _caso(db_session, hasher_test, emisor_test)
    caso.ejecutar("antiguo@example.com", "clave-ficticia-antigua")
    hash_tras_el_primero = _hash_guardado(db_session, usuario_con_hash_viejo)

    caso.ejecutar("antiguo@example.com", "clave-ficticia-antigua")

    assert _hash_guardado(db_session, usuario_con_hash_viejo) == hash_tras_el_primero


def test_con_contrasena_incorrecta_el_hash_viejo_no_cambia(
    db_session: Session,
    hasher_test: Hasher,
    emisor_test: EmisorTokens,
    usuario_con_hash_viejo: Usuario,
) -> None:
    hash_viejo = usuario_con_hash_viejo.password_hash
    caso = _caso(db_session, hasher_test, emisor_test)

    with pytest.raises(CredencialesInvalidasError):
        caso.ejecutar("antiguo@example.com", "contrasena-incorrecta")

    assert _hash_guardado(db_session, usuario_con_hash_viejo) == hash_viejo


def test_un_usuario_inactivo_con_hash_viejo_y_contrasena_correcta_no_se_rehashea(
    db_session: Session,
    hasher_test: Hasher,
    emisor_test: EmisorTokens,
    usuario_con_hash_viejo: Usuario,
) -> None:
    usuario_con_hash_viejo.activo = False
    db_session.flush()
    hash_viejo = usuario_con_hash_viejo.password_hash
    caso = _caso(db_session, hasher_test, emisor_test)

    with pytest.raises(CredencialesInvalidasError):
        caso.ejecutar("antiguo@example.com", "clave-ficticia-antigua")

    assert _hash_guardado(db_session, usuario_con_hash_viejo) == hash_viejo
