"""Integridad de usuario y de turno.creado_por garantizada por PostgreSQL (escritura directa)."""

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import delete, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.infrastructure.db.base import Base
from app.infrastructure.db.models import Paciente, Prestacion, Profesional, Sillon, Turno, Usuario

HASH_FICTICIO = "hash-ficticio-no-verificable"
CHECK = "23514"
UNICIDAD = "23505"
FK = "23503"


def _persistir(session: Session, entidad: Base) -> None:
    with session.begin_nested():
        session.add(entidad)
        session.flush()


def _rechazo(session: Session, entidad: Base) -> IntegrityError:
    with pytest.raises(IntegrityError) as excinfo:
        _persistir(session, entidad)
    return excinfo.value


def _usuario(**campos: object) -> Usuario:
    base: dict[str, object] = {
        "email": "recepcion@example.com",
        "password_hash": HASH_FICTICIO,
        "rol": "recepcionista",
    }
    return Usuario(**(base | campos))


@pytest.fixture
def profesionales(db_session: Session) -> list[Profesional]:
    lista = [Profesional(nombre=n, apellido="Ficticio") for n in ("Ana", "Bruno")]
    db_session.add_all(lista)
    db_session.flush()
    return lista


# --- Usuario válido ------------------------------------------------------------------------


def test_odontologo_valido_queda_activo_con_creado_en_timestamptz_en_el_instante_actual(
    db_session: Session, profesionales: list[Profesional]
) -> None:
    usuario = _usuario(
        email="ana.ficticia@example.com", rol="odontologo", profesional_id=profesionales[0].id
    )

    _persistir(db_session, usuario)
    db_session.refresh(usuario)

    assert usuario.activo is True
    assert usuario.creado_en.tzinfo is not None
    assert abs(usuario.creado_en.astimezone(UTC) - datetime.now(UTC)) < timedelta(seconds=30)
    tipo = db_session.execute(
        text(
            "SELECT data_type FROM information_schema.columns "
            "WHERE table_name = 'usuario' AND column_name = 'creado_en'"
        )
    ).scalar_one()
    assert tipo == "timestamp with time zone"


def test_recepcionista_valida_se_persiste_sin_profesional(db_session: Session) -> None:
    usuario = _usuario()

    _persistir(db_session, usuario)
    db_session.refresh(usuario)

    assert usuario.profesional_id is None
    assert usuario.activo is True


# --- Rol -----------------------------------------------------------------------------------


@pytest.mark.parametrize("rol", ["administrador", "Recepcionista", ""])
def test_rol_fuera_de_los_validos_es_rechazado_por_check(db_session: Session, rol: str) -> None:
    error = _rechazo(db_session, _usuario(rol=rol))

    assert error.orig.sqlstate == CHECK
    assert error.orig.diag.constraint_name == "ck_usuario_rol_valido"


# --- Vínculo con profesional según rol ----------------------------------------------------


def test_odontologo_sin_profesional_es_rechazado_por_check(db_session: Session) -> None:
    error = _rechazo(db_session, _usuario(rol="odontologo"))

    assert error.orig.sqlstate == CHECK
    assert error.orig.diag.constraint_name == "ck_usuario_profesional_segun_rol"


def test_recepcionista_con_profesional_es_rechazada_por_check(
    db_session: Session, profesionales: list[Profesional]
) -> None:
    error = _rechazo(db_session, _usuario(profesional_id=profesionales[0].id))

    assert error.orig.sqlstate == CHECK
    assert error.orig.diag.constraint_name == "ck_usuario_profesional_segun_rol"


def test_odontologo_con_profesional_inexistente_es_rechazado_por_fk(db_session: Session) -> None:
    error = _rechazo(db_session, _usuario(rol="odontologo", profesional_id=uuid.uuid4()))

    assert error.orig.sqlstate == FK
    assert error.orig.diag.constraint_name == "fk_usuario_profesional_id_profesional"


# --- Email ---------------------------------------------------------------------------------


@pytest.mark.parametrize("activo", [True, False])
def test_email_duplicado_es_rechazado_aunque_el_existente_este_inactivo(
    db_session: Session, activo: bool
) -> None:
    _persistir(db_session, _usuario(activo=activo))

    error = _rechazo(db_session, _usuario())

    assert error.orig.sqlstate == UNICIDAD
    assert error.orig.diag.constraint_name == "uq_usuario_email"


def test_emails_distintos_conviven(db_session: Session) -> None:
    _persistir(db_session, _usuario())

    _persistir(db_session, _usuario(email="recepcion2@example.com"))


@pytest.mark.parametrize(
    "email",
    ["Recepcion@Example.com", " recepcion@example.com", "recepcion@example.com ", ""],
)
def test_email_no_normalizado_o_vacio_es_rechazado_por_check(
    db_session: Session, email: str
) -> None:
    error = _rechazo(db_session, _usuario(email=email))

    assert error.orig.sqlstate == CHECK
    assert error.orig.diag.constraint_name == "ck_usuario_email_normalizado"


# --- Un usuario activo por profesional ----------------------------------------------------


def _odontologo(profesional: Profesional, email: str, *, activo: bool = True) -> Usuario:
    return _usuario(email=email, rol="odontologo", profesional_id=profesional.id, activo=activo)


def test_segundo_odontologo_activo_del_mismo_profesional_es_rechazado(
    db_session: Session, profesionales: list[Profesional]
) -> None:
    _persistir(db_session, _odontologo(profesionales[0], "ana1@example.com"))

    error = _rechazo(db_session, _odontologo(profesionales[0], "ana2@example.com"))

    assert error.orig.sqlstate == UNICIDAD
    assert error.orig.diag.constraint_name == "uq_usuario_profesional_activo"


def test_segundo_odontologo_se_acepta_si_el_primero_esta_inactivo(
    db_session: Session, profesionales: list[Profesional]
) -> None:
    _persistir(db_session, _odontologo(profesionales[0], "ana1@example.com", activo=False))

    _persistir(db_session, _odontologo(profesionales[0], "ana2@example.com"))


def test_odontologos_activos_de_profesionales_distintos_conviven(
    db_session: Session, profesionales: list[Profesional]
) -> None:
    _persistir(db_session, _odontologo(profesionales[0], "ana@example.com"))

    _persistir(db_session, _odontologo(profesionales[1], "bruno@example.com"))


def test_dos_odontologos_inactivos_del_mismo_profesional_conviven(
    db_session: Session, profesionales: list[Profesional]
) -> None:
    _persistir(db_session, _odontologo(profesionales[0], "ana1@example.com", activo=False))

    _persistir(db_session, _odontologo(profesionales[0], "ana2@example.com", activo=False))


# --- Autor del turno referenciado en la base ----------------------------------------------


def _turno(session: Session, **campos: object) -> Turno:
    """Turno con catálogo ficticio mínimo, para ejercitar solo la FK de creado_por."""
    profesional = Profesional(nombre="Carla", apellido="Ficticia")
    paciente = Paciente(
        nombre="Paula", apellido="Ficticia", documento="FIC-U-1", telefono="+54 11 5555-0001"
    )
    prestacion = Prestacion(nombre="Limpieza", duracion_min=45)
    sillon = Sillon(nombre="Sillon U")
    session.add_all([profesional, paciente, prestacion, sillon])
    session.flush()
    inicio = datetime(2026, 10, 8, 13, 0, tzinfo=UTC)
    base: dict[str, object] = {
        "profesional_id": profesional.id,
        "paciente_id": paciente.id,
        "prestacion_id": prestacion.id,
        "sillon_id": sillon.id,
        "inicio": inicio,
        "fin": inicio + timedelta(minutes=45),
        "duracion_min": 45,
    }
    return Turno(**(base | campos))


def test_turno_con_autor_existente_es_aceptado(db_session: Session) -> None:
    autor = _usuario()
    _persistir(db_session, autor)

    turno = _turno(db_session, creado_por=autor.id)
    _persistir(db_session, turno)

    assert turno.creado_por == autor.id


def test_turno_con_autor_inexistente_es_rechazado_por_fk(db_session: Session) -> None:
    error = _rechazo(db_session, _turno(db_session, creado_por=uuid.uuid4()))

    assert error.orig.sqlstate == FK
    assert error.orig.diag.constraint_name == "fk_turno_creado_por_usuario"


def test_borrar_un_usuario_con_turnos_es_rechazado_por_fk(db_session: Session) -> None:
    autor = _usuario()
    _persistir(db_session, autor)
    _persistir(db_session, _turno(db_session, creado_por=autor.id))

    with pytest.raises(IntegrityError) as excinfo:
        with db_session.begin_nested():
            db_session.execute(delete(Usuario).where(Usuario.id == autor.id))

    assert excinfo.value.orig.sqlstate == FK
    assert excinfo.value.orig.diag.constraint_name == "fk_turno_creado_por_usuario"


def test_borrar_un_usuario_sin_turnos_es_aceptado(db_session: Session) -> None:
    sin_turnos = _usuario(email="sin.turnos@example.com")
    _persistir(db_session, sin_turnos)

    with db_session.begin_nested():
        db_session.execute(delete(Usuario).where(Usuario.id == sin_turnos.id))

    assert db_session.get(Usuario, sin_turnos.id) is None


def test_turno_con_creado_por_nulo_es_aceptado(db_session: Session) -> None:
    turno = _turno(db_session, creado_por=None)

    _persistir(db_session, turno)

    assert turno.creado_por is None
