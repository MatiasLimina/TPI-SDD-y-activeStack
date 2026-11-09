"""Caso de uso de la consulta de agenda con repositorios falsos (sin base de datos)."""

from datetime import UTC, date, datetime
from uuid import UUID, uuid4

import pytest

from app.application.consulta_agenda import ConsultarAgenda
from app.domain.agenda import RangoInvalidoError, TurnoDeAgenda
from app.domain.horarios import ProfesionalAjenoError
from app.domain.turnos import Intervalo
from app.domain.usuarios import Rol, UsuarioAutenticado
from app.infrastructure.db.models import Bloqueo
from tests.fakes import RepositorioBloqueosDeAgendaFalso, RepositorioTurnosDeAgendaFalso

PROPIO = uuid4()
DIA_8 = Intervalo(datetime(2026, 10, 8, 3, 0, tzinfo=UTC), datetime(2026, 10, 9, 3, 0, tzinfo=UTC))
SEMANA = Intervalo(
    datetime(2026, 10, 5, 3, 0, tzinfo=UTC), datetime(2026, 10, 12, 3, 0, tzinfo=UTC)
)


def _recepcionista() -> UsuarioAutenticado:
    return UsuarioAutenticado(id=uuid4(), rol=Rol.RECEPCIONISTA, profesional_id=None)


def _odontologo() -> UsuarioAutenticado:
    return UsuarioAutenticado(id=uuid4(), rol=Rol.ODONTOLOGO, profesional_id=PROPIO)


def _turno() -> TurnoDeAgenda:
    return TurnoDeAgenda(
        id=uuid4(),
        profesional_id=uuid4(),
        paciente_id=uuid4(),
        paciente_nombre="Carla",
        paciente_apellido="Imaginaria",
        prestacion_id=uuid4(),
        sillon_id=None,
        inicio=datetime(2026, 10, 8, 13, 0, tzinfo=UTC),
        fin=datetime(2026, 10, 8, 13, 45, tzinfo=UTC),
        duracion_min=45,
        estado="programado",
        creado_por=None,
        motivo_cancelacion=None,
    )


def _bloqueo() -> Bloqueo:
    return Bloqueo(
        id=uuid4(),
        profesional_id=uuid4(),
        inicio=datetime(2026, 10, 8, 18, 0, tzinfo=UTC),
        fin=datetime(2026, 10, 8, 19, 0, tzinfo=UTC),
        motivo="Congreso",
        creado_por=uuid4(),
    )


def _caso(
    turnos: list[TurnoDeAgenda] | None = None, bloqueos: list[Bloqueo] | None = None
) -> tuple[ConsultarAgenda, RepositorioTurnosDeAgendaFalso, RepositorioBloqueosDeAgendaFalso]:
    repo_turnos = RepositorioTurnosDeAgendaFalso(turnos)
    repo_bloqueos = RepositorioBloqueosDeAgendaFalso(bloqueos)
    return ConsultarAgenda(repo_turnos, repo_bloqueos), repo_turnos, repo_bloqueos


# --- 4.1 delegación ---------------------------------------------------------------------------


def test_pasa_el_intervalo_utc_y_los_filtros_y_devuelve_las_dos_listas() -> None:
    turno, bloqueo = _turno(), _bloqueo()
    caso, repo_turnos, repo_bloqueos = _caso([turno], [bloqueo])
    profesional, sillon = uuid4(), uuid4()

    agenda = caso.ejecutar(
        _recepcionista(), date(2026, 10, 8), date(2026, 10, 8), profesional, sillon
    )

    assert agenda.turnos == [turno]
    assert agenda.bloqueos == [bloqueo]
    assert repo_turnos.consultas == [(DIA_8, profesional, sillon)]
    # el sillon solo filtra turnos: los bloqueos siguen al profesional (D9)
    assert repo_bloqueos.consultas == [(DIA_8, profesional)]


def test_sin_filtros_consulta_todo_el_rango_semanal() -> None:
    caso, repo_turnos, repo_bloqueos = _caso()

    agenda = caso.ejecutar(_recepcionista(), date(2026, 10, 5), date(2026, 10, 11), None, None)

    assert agenda.turnos == []
    assert agenda.bloqueos == []
    assert repo_turnos.consultas == [(SEMANA, None, None)]
    assert repo_bloqueos.consultas == [(SEMANA, None)]


def test_el_odontologo_consulta_con_su_profesional_y_conserva_el_sillon() -> None:
    caso, repo_turnos, repo_bloqueos = _caso()
    sillon = uuid4()

    caso.ejecutar(_odontologo(), date(2026, 10, 8), date(2026, 10, 8), None, sillon)

    assert repo_turnos.consultas == [(DIA_8, PROPIO, sillon)]
    assert repo_bloqueos.consultas == [(DIA_8, PROPIO)]


# --- 4.2 orden de evaluación ------------------------------------------------------------------


@pytest.mark.parametrize("ajeno", [uuid4(), uuid4()])
def test_profesional_ajeno_antes_que_el_rango_invalido_y_sin_consultar(ajeno: UUID) -> None:
    caso, repo_turnos, repo_bloqueos = _caso()

    with pytest.raises(ProfesionalAjenoError):
        caso.ejecutar(_odontologo(), date(2026, 10, 9), date(2026, 10, 8), ajeno, None)

    assert repo_turnos.consultas == []
    assert repo_bloqueos.consultas == []


@pytest.mark.parametrize(
    ("desde", "hasta"),
    [(date(2026, 10, 9), date(2026, 10, 8)), (date(2026, 10, 5), date(2026, 10, 12))],
)
def test_rango_invalido_no_consulta_ningun_repositorio(desde: date, hasta: date) -> None:
    caso, repo_turnos, repo_bloqueos = _caso()

    with pytest.raises(RangoInvalidoError):
        caso.ejecutar(_recepcionista(), desde, hasta, None, None)

    assert repo_turnos.consultas == []
    assert repo_bloqueos.consultas == []
