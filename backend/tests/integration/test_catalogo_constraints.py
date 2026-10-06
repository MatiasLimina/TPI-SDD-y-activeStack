"""Integridad del catalogo garantizada por PostgreSQL (escribe directo, sin validacion de app)."""

from collections.abc import Callable

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.infrastructure.db.base import Base
from app.infrastructure.db.models import Paciente, Prestacion, Profesional, Sillon


def _insert_rechazado(session: Session, entidad: Base) -> IntegrityError:
    """Intenta persistir `entidad` en un savepoint y devuelve el IntegrityError esperado."""
    with pytest.raises(IntegrityError) as excinfo:
        with session.begin_nested():
            session.add(entidad)
            session.flush()
    return excinfo.value


def _paciente(**campos: str | None) -> Paciente:
    base: dict[str, str | None] = {
        "nombre": "Paula",
        "apellido": "Ficticia",
        "documento": "FIC-1000",
        "telefono": "+54 11 5555-0001",
    }
    return Paciente(**(base | campos))


# --- 3.1 duracion positiva ---------------------------------------------------------------


@pytest.mark.parametrize("duracion", [1, 45, 600])
def test_prestacion_with_positive_duration_is_persisted(db_session: Session, duracion: int) -> None:
    prestacion = Prestacion(nombre="Limpieza", duracion_min=duracion)

    db_session.add(prestacion)
    db_session.flush()
    db_session.refresh(prestacion)

    assert prestacion.duracion_min == duracion


@pytest.mark.parametrize("duracion", [0, -15])
def test_prestacion_with_non_positive_duration_is_rejected_by_check(
    db_session: Session, duracion: int
) -> None:
    error = _insert_rechazado(db_session, Prestacion(nombre="Invalida", duracion_min=duracion))

    assert "ck_prestacion_duracion_min_positiva" in str(error.orig)
    assert db_session.execute(text("SELECT count(*) FROM prestacion")).scalar_one() == 0


# --- 3.2 requiere_sillon -----------------------------------------------------------------


def test_prestacion_without_requiere_sillon_defaults_to_true(db_session: Session) -> None:
    prestacion = Prestacion(nombre="Limpieza", duracion_min=45)

    db_session.add(prestacion)
    db_session.flush()
    db_session.refresh(prestacion)

    assert prestacion.requiere_sillon is True


def test_prestacion_with_requiere_sillon_false_is_persisted(db_session: Session) -> None:
    prestacion = Prestacion(nombre="Consulta", duracion_min=30, requiere_sillon=False)

    db_session.add(prestacion)
    db_session.flush()
    db_session.refresh(prestacion)

    assert prestacion.requiere_sillon is False


# --- 3.3 actividad por defecto -----------------------------------------------------------


@pytest.mark.parametrize(
    ("fabrica", "columna"),
    [
        (lambda: Profesional(nombre="Ana", apellido="Ficticia"), "activo"),
        (lambda: Sillon(nombre="Sillon X"), "activo"),
        (lambda: Prestacion(nombre="Algo", duracion_min=10), "activa"),
        (lambda: _paciente(), "activo"),
    ],
    ids=["profesional", "sillon", "prestacion", "paciente"],
)
def test_record_without_activity_flag_is_active_by_default(
    db_session: Session, fabrica: Callable[[], Base], columna: str
) -> None:
    registro = fabrica()

    db_session.add(registro)
    db_session.flush()
    db_session.refresh(registro)

    assert getattr(registro, columna) is True


# --- 3.4 unicidad ------------------------------------------------------------------------


def test_sillon_with_duplicate_name_is_rejected(db_session: Session) -> None:
    db_session.add(Sillon(nombre="Sillon 1"))
    db_session.flush()

    error = _insert_rechazado(db_session, Sillon(nombre="Sillon 1"))

    assert "uq_sillon_nombre" in str(error.orig)


def test_prestacion_with_duplicate_name_is_rejected(db_session: Session) -> None:
    db_session.add(Prestacion(nombre="Limpieza", duracion_min=45))
    db_session.flush()

    error = _insert_rechazado(db_session, Prestacion(nombre="Limpieza", duracion_min=30))

    assert "uq_prestacion_nombre" in str(error.orig)


def test_paciente_with_duplicate_documento_is_rejected(db_session: Session) -> None:
    db_session.add(_paciente(documento="FIC-2000"))
    db_session.flush()

    error = _insert_rechazado(db_session, _paciente(documento="FIC-2000", nombre="Otro"))

    assert "uq_paciente_documento" in str(error.orig)


def test_profesional_with_duplicate_matricula_is_rejected(db_session: Session) -> None:
    db_session.add(Profesional(nombre="Ana", apellido="Ficticia", matricula="MP-FIC-9"))
    db_session.flush()

    error = _insert_rechazado(
        db_session, Profesional(nombre="Bruno", apellido="Inventado", matricula="MP-FIC-9")
    )

    assert "uq_profesional_matricula" in str(error.orig)


def test_two_profesionales_without_matricula_are_both_persisted(db_session: Session) -> None:
    db_session.add_all(
        [
            Profesional(nombre="Ana", apellido="Ficticia"),
            Profesional(nombre="Bruno", apellido="Inventado"),
        ]
    )
    db_session.flush()

    total = db_session.execute(
        text("SELECT count(*) FROM profesional WHERE matricula IS NULL")
    ).scalar_one()

    assert total == 2


# --- 3.5 obligatoriedad ------------------------------------------------------------------


@pytest.mark.parametrize("campo", ["documento", "telefono", "nombre", "apellido"])
def test_paciente_without_required_field_is_rejected_by_not_null(
    db_session: Session, campo: str
) -> None:
    error = _insert_rechazado(db_session, _paciente(**{campo: None}))

    assert "null value" in str(error.orig)
    assert campo in str(error.orig)


def test_paciente_without_email_is_persisted_with_null_email(db_session: Session) -> None:
    paciente = _paciente(documento="FIC-3000")

    db_session.add(paciente)
    db_session.flush()
    db_session.refresh(paciente)

    assert paciente.email is None


@pytest.mark.parametrize(
    ("fabrica", "columna"),
    [
        (lambda: Profesional(nombre=None, apellido="Ficticia"), "nombre"),
        (lambda: Profesional(nombre="Ana", apellido=None), "apellido"),
        (lambda: Sillon(nombre=None), "nombre"),
        (lambda: Prestacion(nombre=None, duracion_min=30), "nombre"),
        (lambda: Prestacion(nombre="Sin duracion", duracion_min=None), "duracion_min"),
    ],
    ids=[
        "profesional-sin-nombre",
        "profesional-sin-apellido",
        "sillon-sin-nombre",
        "prestacion-sin-nombre",
        "prestacion-sin-duracion",
    ],
)
def test_other_required_fields_are_rejected_by_not_null(
    db_session: Session, fabrica: Callable[[], Base], columna: str
) -> None:
    error = _insert_rechazado(db_session, fabrica())

    assert "null value" in str(error.orig)
    assert columna in str(error.orig)


# --- 3.6 marcas de tiempo ----------------------------------------------------------------


def test_sillon_without_timestamps_gets_timezone_aware_values_from_db(
    db_session: Session,
) -> None:
    sillon = Sillon(nombre="Sillon T")

    db_session.add(sillon)
    db_session.flush()
    db_session.refresh(sillon)

    assert sillon.creado_en.tzinfo is not None
    assert sillon.actualizado_en.tzinfo is not None
    assert sillon.creado_en.utcoffset() is not None


@pytest.mark.parametrize("tabla", ["profesional", "sillon", "prestacion", "paciente"])
def test_timestamp_columns_are_timestamptz(db_session: Session, tabla: str) -> None:
    filas = db_session.execute(
        text(
            "SELECT column_name, data_type FROM information_schema.columns "
            "WHERE table_name = :t AND column_name IN ('creado_en', 'actualizado_en')"
        ),
        {"t": tabla},
    ).all()

    assert {nombre: tipo for nombre, tipo in filas} == {
        "creado_en": "timestamp with time zone",
        "actualizado_en": "timestamp with time zone",
    }
