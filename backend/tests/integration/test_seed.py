"""Seed de desarrollo: contenido, idempotencia y datos ficticios (PostgreSQL real)."""

import pytest
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from app.infrastructure.db.models import Paciente, Prestacion, Profesional, Sillon
from app.infrastructure.db.seed import SILLONES, seed_catalogo

MODELOS = [Profesional, Sillon, Prestacion, Paciente]


def _contar(session: Session, modelo: type) -> int:
    return session.execute(select(func.count()).select_from(modelo)).scalar_one()


def _conteos(session: Session) -> dict[str, int]:
    return {modelo.__tablename__: _contar(session, modelo) for modelo in MODELOS}


@pytest.fixture
def base_vacia(db_session: Session) -> Session:
    """El catalogo debe estar vacio para medir cantidades exactas (todo se revierte al final)."""
    for tabla in ("paciente", "prestacion", "sillon", "profesional"):
        db_session.execute(text(f"DELETE FROM {tabla}"))
    return db_session


# --- 4.1 contenido -----------------------------------------------------------------------


def test_seed_on_empty_database_loads_expected_counts_all_active(base_vacia: Session) -> None:
    seed_catalogo(base_vacia)

    assert _conteos(base_vacia) == {"profesional": 2, "sillon": 2, "prestacion": 4, "paciente": 4}
    inactivos = (
        base_vacia.scalar(select(func.count()).select_from(Profesional).where(~Profesional.activo))
        + base_vacia.scalar(select(func.count()).select_from(Sillon).where(~Sillon.activo))
        + base_vacia.scalar(select(func.count()).select_from(Prestacion).where(~Prestacion.activa))
        + base_vacia.scalar(select(func.count()).select_from(Paciente).where(~Paciente.activo))
    )
    assert inactivos == 0


# --- 4.3 prestaciones --------------------------------------------------------------------


@pytest.mark.parametrize(
    ("nombre", "duracion", "requiere_sillon"),
    [
        ("Consulta", 30, False),
        ("Control", 20, False),
        ("Limpieza", 45, True),
        ("Conservadora", 60, True),
    ],
)
def test_seed_loads_expected_prestacion(
    base_vacia: Session, nombre: str, duracion: int, requiere_sillon: bool
) -> None:
    seed_catalogo(base_vacia)

    prestacion = base_vacia.scalars(select(Prestacion).where(Prestacion.nombre == nombre)).one()

    assert prestacion.duracion_min == duracion
    assert prestacion.requiere_sillon is requiere_sillon


# --- 4.4 idempotencia --------------------------------------------------------------------


def test_seed_twice_does_not_fail_nor_duplicate_rows(base_vacia: Session) -> None:
    seed_catalogo(base_vacia)
    tras_primera = _conteos(base_vacia)

    seed_catalogo(base_vacia)

    assert _conteos(base_vacia) == tras_primera


def test_seed_twice_keeps_stable_ids(base_vacia: Session) -> None:
    seed_catalogo(base_vacia)
    ids_primera = {
        modelo.__tablename__: set(base_vacia.scalars(select(modelo.id))) for modelo in MODELOS
    }

    seed_catalogo(base_vacia)
    ids_segunda = {
        modelo.__tablename__: set(base_vacia.scalars(select(modelo.id))) for modelo in MODELOS
    }

    assert ids_segunda == ids_primera
    assert SILLONES[0]["id"] in ids_segunda["sillon"]


def test_seed_does_not_revert_manual_changes(base_vacia: Session) -> None:
    seed_catalogo(base_vacia)
    sillon_id = SILLONES[0]["id"]
    base_vacia.execute(text("UPDATE sillon SET activo = false WHERE id = :i"), {"i": sillon_id})

    seed_catalogo(base_vacia)

    assert (
        base_vacia.execute(
            text("SELECT activo FROM sillon WHERE id = :i"), {"i": sillon_id}
        ).scalar_one()
        is False
    )


def test_seed_respects_records_preexisting_with_natural_key_conflict(base_vacia: Session) -> None:
    base_vacia.add(Sillon(nombre=str(SILLONES[0]["nombre"])))
    base_vacia.flush()

    seed_catalogo(base_vacia)

    assert _contar(base_vacia, Sillon) == 2


# --- 4.5 datos ficticios -----------------------------------------------------------------


def test_seed_patient_emails_use_reserved_domain(base_vacia: Session) -> None:
    seed_catalogo(base_vacia)

    emails = [e for e in base_vacia.scalars(select(Paciente.email)) if e is not None]

    assert emails, "el seed debe incluir al menos un paciente con email"
    assert all(email.endswith("@example.com") for email in emails)


def test_seed_patient_documents_are_fictitious_non_numeric_prefixed(base_vacia: Session) -> None:
    seed_catalogo(base_vacia)

    documentos = list(base_vacia.scalars(select(Paciente.documento)))

    assert len(documentos) == 4
    assert all(documento.startswith("FIC-") for documento in documentos)
