"""Garantía de no solape en PostgreSQL: escritura directa, sin pasar por la aplicación."""

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.infrastructure.db.models import Paciente, Prestacion, Profesional, Sillon, Turno

BASE = datetime(2026, 10, 8, 13, 0, tzinfo=UTC)  # 10:00 hora local


@dataclass
class Catalogo:
    profesionales: list[Profesional]
    sillones: list[Sillon]
    pacientes: list[Paciente]
    prestacion: Prestacion


@pytest.fixture
def catalogo(db_session: Session) -> Catalogo:
    profesionales = [Profesional(nombre=n, apellido="Ficticio") for n in ("Ana", "Beto")]
    sillones = [Sillon(nombre=f"Sillon {i}") for i in (1, 2)]
    pacientes = [
        Paciente(
            nombre=n, apellido="Ficticia", documento=f"FIC-{i}", telefono="+54 11 5555-000" + str(i)
        )
        for i, n in enumerate(("Paula", "Quique"), start=1)
    ]
    prestacion = Prestacion(nombre="Limpieza", duracion_min=45)
    db_session.add_all([*profesionales, *sillones, *pacientes, prestacion])
    db_session.flush()
    return Catalogo(profesionales, sillones, pacientes, prestacion)


def _turno(
    c: Catalogo,
    *,
    prof: int = 0,
    sillon: int | None = 0,
    pac: int = 0,
    desde: int = 0,
    minutos: int = 45,
    estado: str = "programado",
    fin: datetime | None = None,
) -> Turno:
    inicio = BASE + timedelta(minutes=desde)
    return Turno(
        profesional_id=c.profesionales[prof].id,
        sillon_id=None if sillon is None else c.sillones[sillon].id,
        paciente_id=c.pacientes[pac].id,
        prestacion_id=c.prestacion.id,
        inicio=inicio,
        fin=fin or inicio + timedelta(minutes=minutos),
        duracion_min=minutos,
        estado=estado,
    )


def _insertar(session: Session, turno: Turno) -> None:
    with session.begin_nested():
        session.add(turno)
        session.flush()


def _rechazo(session: Session, turno: Turno) -> IntegrityError:
    with pytest.raises(IntegrityError) as excinfo:
        _insertar(session, turno)
    return excinfo.value


@pytest.mark.parametrize(
    ("variacion", "constraint"),
    [
        ({"sillon": 1, "pac": 1}, "turno_sin_solape_profesional"),
        ({"prof": 1, "pac": 1}, "turno_sin_solape_sillon"),
        ({"prof": 1, "sillon": 1}, "turno_sin_solape_paciente"),
    ],
)
def test_superposicion_es_rechazada_por_la_exclusion_correspondiente(
    db_session: Session, catalogo: Catalogo, variacion: dict[str, int], constraint: str
) -> None:
    _insertar(db_session, _turno(catalogo))

    error = _rechazo(db_session, _turno(catalogo, desde=30, minutos=30, **variacion))

    assert error.orig.sqlstate == "23P01"
    assert error.orig.diag.constraint_name == constraint


def test_turnos_contiguos_son_aceptados(db_session: Session, catalogo: Catalogo) -> None:
    _insertar(db_session, _turno(catalogo))

    _insertar(db_session, _turno(catalogo, desde=45))  # mismo prof, sillón y paciente


def test_dos_turnos_sin_sillon_en_el_mismo_horario_no_chocan_por_sillon(
    db_session: Session, catalogo: Catalogo
) -> None:
    _insertar(db_session, _turno(catalogo, sillon=None))

    _insertar(db_session, _turno(catalogo, prof=1, sillon=None, pac=1))


def test_turno_cancelado_no_bloquea_el_horario(db_session: Session, catalogo: Catalogo) -> None:
    _insertar(db_session, _turno(catalogo, estado="cancelado"))

    _insertar(db_session, _turno(catalogo))


def test_estado_fuera_de_programado_o_cancelado_es_rechazado(
    db_session: Session, catalogo: Catalogo
) -> None:
    error = _rechazo(db_session, _turno(catalogo, estado="reprogramado"))

    assert error.orig.sqlstate == "23514"
    assert "ck_turno_estado_valido" in str(error.orig)


@pytest.mark.parametrize("delta", [0, -15])
def test_fin_no_posterior_al_inicio_es_rechazado(
    db_session: Session, catalogo: Catalogo, delta: int
) -> None:
    error = _rechazo(db_session, _turno(catalogo, fin=BASE + timedelta(minutes=delta)))

    assert error.orig.sqlstate == "23514"
    assert "ck_turno_fin_mayor" in str(error.orig)
