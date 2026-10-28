"""Seed de desarrollo: contenido, idempotencia y datos ficticios (PostgreSQL real)."""

import inspect
import uuid
from pathlib import Path

import pytest
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from app.application.autenticacion import IniciarSesion
from app.config import REPO_ROOT
from app.infrastructure.db import seed as seed_module
from app.infrastructure.db.models import Paciente, Prestacion, Profesional, Sillon, Usuario
from app.infrastructure.db.repositorio_usuarios import RepositorioUsuarios
from app.infrastructure.db.seed import SILLONES, SeedSettings, seed_catalogo, seed_usuarios
from app.infrastructure.security.contrasenas import Hasher
from app.infrastructure.security.tokens import EmisorTokens
from tests.unit.test_env_example import parse_env

MODELOS = [Profesional, Sillon, Prestacion, Paciente]


def _contar(session: Session, modelo: type) -> int:
    return session.execute(select(func.count()).select_from(modelo)).scalar_one()


def _conteos(session: Session) -> dict[str, int]:
    return {modelo.__tablename__: _contar(session, modelo) for modelo in MODELOS}


@pytest.fixture
def base_vacia(db_session: Session) -> Session:
    """El catalogo y los usuarios deben estar vacios para medir cantidades exactas.

    Todo se revierte al final. `usuario` va antes que `profesional` por la FK.
    """
    for tabla in ("usuario", "paciente", "prestacion", "sillon", "profesional"):
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


# --- usuarios del seed (C-06, DD-24) -----------------------------------------------------

PROFESIONAL_1 = uuid.UUID("00000000-0000-4000-8000-000000000101")
PROFESIONAL_2 = uuid.UUID("00000000-0000-4000-8000-000000000102")
PASS_RECEPCION = "clave-seed-recepcion-ficticia"
PASS_ODONTO_1 = "clave-seed-odontologo1-ficticia"
PASS_ODONTO_2 = "clave-seed-odontologo2-ficticia"


def _contrasenas(
    recepcion: str | None = PASS_RECEPCION,
    odonto_1: str | None = PASS_ODONTO_1,
    odonto_2: str | None = PASS_ODONTO_2,
) -> SeedSettings:
    """Instancia aislada del `.env` local y del entorno: solo valen los valores del test."""
    return SeedSettings(
        _env_file=None,
        SEED_RECEPCIONISTA_PASSWORD=recepcion,
        SEED_ODONTOLOGO_1_PASSWORD=odonto_1,
        SEED_ODONTOLOGO_2_PASSWORD=odonto_2,
    )


def _sembrar(session: Session, hasher: Hasher, contrasenas: SeedSettings) -> None:
    seed_catalogo(session)
    seed_usuarios(session, contrasenas, hasher)
    session.flush()


def _usuarios(session: Session) -> dict[str, Usuario]:
    return {u.email: u for u in session.scalars(select(Usuario))}


def _login(session: Session, hasher: Hasher, emisor: EmisorTokens, email: str, clave: str) -> str:
    return IniciarSesion(RepositorioUsuarios(session), hasher, emisor).ejecutar(email, clave)


def test_seed_usuarios_creates_receptionist_and_two_dentists_linked_to_profesionales(
    base_vacia: Session, hasher_test: Hasher
) -> None:
    _sembrar(base_vacia, hasher_test, _contrasenas())

    usuarios = _usuarios(base_vacia)

    assert len(usuarios) == 3
    assert all(u.activo for u in usuarios.values())
    assert all(email.endswith("@example.com") for email in usuarios)
    por_rol = sorted((u.rol, u.profesional_id) for u in usuarios.values() if u.rol == "odontologo")
    assert por_rol == [("odontologo", PROFESIONAL_1), ("odontologo", PROFESIONAL_2)]
    recepcionistas = [u for u in usuarios.values() if u.rol == "recepcionista"]
    assert len(recepcionistas) == 1
    assert recepcionistas[0].profesional_id is None


def test_seed_usuarios_stores_hashes_not_passwords(
    base_vacia: Session, hasher_test: Hasher
) -> None:
    _sembrar(base_vacia, hasher_test, _contrasenas())

    claves = (PASS_RECEPCION, PASS_ODONTO_1, PASS_ODONTO_2)
    for usuario in _usuarios(base_vacia).values():
        assert usuario.password_hash not in claves
        assert all(clave not in usuario.password_hash for clave in claves)
    assert len({u.password_hash for u in _usuarios(base_vacia).values()}) == 3


def test_seed_usuarios_each_user_can_log_in_with_the_password_of_its_variable(
    base_vacia: Session, hasher_test: Hasher, emisor_test: EmisorTokens
) -> None:
    _sembrar(base_vacia, hasher_test, _contrasenas())
    usuarios = list(_usuarios(base_vacia).values())
    recepcionista = next(u for u in usuarios if u.rol == "recepcionista")
    odontologos = sorted(
        (u for u in usuarios if u.rol == "odontologo"), key=lambda u: u.profesional_id
    )

    for usuario, clave in (
        (recepcionista, PASS_RECEPCION),
        (odontologos[0], PASS_ODONTO_1),
        (odontologos[1], PASS_ODONTO_2),
    ):
        assert _login(base_vacia, hasher_test, emisor_test, usuario.email, clave)


@pytest.mark.parametrize(
    ("kwargs", "esperados"),
    [
        ({"odonto_2": None}, 2),
        ({"odonto_2": ""}, 2),
        ({"recepcion": None, "odonto_1": None, "odonto_2": None}, 0),
        ({"recepcion": "", "odonto_1": "", "odonto_2": ""}, 0),
    ],
)
def test_seed_usuarios_skips_users_without_password_and_still_loads_full_catalog(
    base_vacia: Session, hasher_test: Hasher, kwargs: dict[str, str | None], esperados: int
) -> None:
    _sembrar(base_vacia, hasher_test, _contrasenas(**kwargs))

    assert _contar(base_vacia, Usuario) == esperados
    assert _conteos(base_vacia) == {"profesional": 2, "sillon": 2, "prestacion": 4, "paciente": 4}


def test_seed_usuarios_without_second_dentist_password_keeps_the_other_two(
    base_vacia: Session, hasher_test: Hasher
) -> None:
    _sembrar(base_vacia, hasher_test, _contrasenas(odonto_2=None))

    profesionales = {u.profesional_id for u in _usuarios(base_vacia).values()}

    assert profesionales == {None, PROFESIONAL_1}


# --- idempotencia y secretos de los usuarios (9.3) ----------------------------------------

ENV_EXAMPLE = REPO_ROOT / ".env.example"
SEED_PY = Path(inspect.getsourcefile(seed_module) or "")


def _snapshot_usuarios(session: Session) -> list[tuple[uuid.UUID, str, str, bool]]:
    filas = session.execute(
        select(Usuario.id, Usuario.email, Usuario.password_hash, Usuario.activo).order_by(
            Usuario.email
        )
    )
    return [tuple(fila) for fila in filas]  # type: ignore[misc]


def test_seed_usuarios_twice_does_not_duplicate_and_keeps_ids_and_hashes(
    base_vacia: Session, hasher_test: Hasher
) -> None:
    _sembrar(base_vacia, hasher_test, _contrasenas())
    tras_primera = _snapshot_usuarios(base_vacia)

    _sembrar(base_vacia, hasher_test, _contrasenas())

    assert len(tras_primera) == 3
    assert _snapshot_usuarios(base_vacia) == tras_primera


def test_seed_usuarios_second_run_completes_users_missing_in_the_first(
    base_vacia: Session, hasher_test: Hasher
) -> None:
    _sembrar(base_vacia, hasher_test, _contrasenas(odonto_2=None))
    assert _contar(base_vacia, Usuario) == 2

    _sembrar(base_vacia, hasher_test, _contrasenas())

    assert _contar(base_vacia, Usuario) == 3


def test_seed_usuarios_does_not_reactivate_nor_rehash_a_deactivated_user(
    base_vacia: Session, hasher_test: Hasher
) -> None:
    _sembrar(base_vacia, hasher_test, _contrasenas())
    base_vacia.execute(
        text("UPDATE usuario SET activo = false WHERE email = 'ana.ficticia@example.com'")
    )
    antes = _snapshot_usuarios(base_vacia)

    _sembrar(base_vacia, hasher_test, _contrasenas(odonto_1="otra-clave-ficticia-distinta"))

    despues = {fila[1]: fila for fila in _snapshot_usuarios(base_vacia)}
    assert despues["ana.ficticia@example.com"][3] is False
    assert _snapshot_usuarios(base_vacia) == antes


def test_seed_source_does_not_contain_passwords_of_env_example_nor_hashes() -> None:
    codigo = SEED_PY.read_text(encoding="utf-8")
    valores = [
        valor
        for clave, valor in parse_env(ENV_EXAMPLE).items()
        if clave.startswith("SEED_") and clave.endswith("_PASSWORD")
    ]

    assert len(valores) == 3
    assert all(valor and valor not in codigo for valor in valores), "secreto en el codigo"
    assert "$argon2" not in codigo
