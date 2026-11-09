"""Consultas de agenda por intervalo `[)` contra PostgreSQL real (turnos y bloqueos)."""

from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest
from sqlalchemy.orm import Session

from app.domain.turnos import Intervalo
from app.infrastructure.db.models import Bloqueo, Turno, Usuario
from app.infrastructure.db.repositorio_bloqueos import RepositorioBloqueos
from app.infrastructure.db.repositorio_turnos import RepositorioTurnos
from tests.integration.factories import Catalogo, crear_catalogo


def _h(dia: int, hora: int, minuto: int = 0) -> datetime:
    """Instante UTC de octubre de 2026 (10:00 local es 13:00Z)."""
    return datetime(2026, 10, dia, hora, minuto, tzinfo=UTC)


# El dia 8 local: [03:00Z del 8, 03:00Z del 9)
DIA_8 = Intervalo(_h(8, 3), _h(9, 3))


@pytest.fixture
def catalogo(db_session: Session) -> Catalogo:
    return crear_catalogo(db_session)


@pytest.fixture
def repo_turnos(db_session: Session) -> RepositorioTurnos:
    return RepositorioTurnos(db_session)


@pytest.fixture
def repo_bloqueos(db_session: Session) -> RepositorioBloqueos:
    return RepositorioBloqueos(db_session)


def _turno(
    db_session: Session,
    catalogo: Catalogo,
    inicio: datetime,
    *,
    minutos: int = 45,
    profesional: int = 0,
    sillon: int | None = 0,
    paciente: int = 0,
    estado: str = "programado",
) -> Turno:
    turno = Turno(
        profesional_id=catalogo.profesionales[profesional].id,
        sillon_id=None if sillon is None else catalogo.sillones[sillon].id,
        paciente_id=catalogo.pacientes[paciente].id,
        prestacion_id=catalogo.limpieza.id,
        inicio=inicio,
        fin=inicio + timedelta(minutes=minutos),
        duracion_min=minutos,
        estado=estado,
        motivo_cancelacion="Viaje" if estado == "cancelado" else None,
    )
    db_session.add(turno)
    db_session.flush()
    return turno


def _bloqueo(
    db_session: Session,
    profesional_id: UUID,
    autor: Usuario,
    inicio: datetime,
    fin: datetime,
) -> Bloqueo:
    bloqueo = Bloqueo(
        profesional_id=profesional_id,
        inicio=inicio,
        fin=fin,
        motivo="Congreso",
        creado_por=autor.id,
    )
    db_session.add(bloqueo)
    db_session.flush()
    return bloqueo


# --- 3.1 turnos: criterio [), estados, paciente y orden ---------------------------------------


def test_turnos_contiguos_a_los_bordes_quedan_fuera_y_el_que_cruza_un_borde_entra_completo(
    db_session: Session, repo_turnos: RepositorioTurnos, catalogo: Catalogo
) -> None:
    otro = {"profesional": 1, "sillon": 1, "paciente": 1}  # evita las exclusiones entre turnos
    termina_en_el_inicio = _turno(db_session, catalogo, _h(8, 2, 15), **otro)
    empieza_en_el_fin = _turno(db_session, catalogo, _h(9, 3), **otro)
    cruza_el_inicio = _turno(db_session, catalogo, _h(8, 2, 45))  # 02:45Z a 03:30Z
    cruza_el_fin = _turno(db_session, catalogo, _h(9, 2, 45))  # 02:45Z a 03:30Z
    dentro = _turno(db_session, catalogo, _h(8, 13), **otro)

    encontrados = repo_turnos.listar_en(DIA_8)

    ids = [t.id for t in encontrados]
    assert ids == [cruza_el_inicio.id, dentro.id, cruza_el_fin.id]
    assert termina_en_el_inicio.id not in ids
    assert empieza_en_el_fin.id not in ids
    assert (encontrados[0].inicio, encontrados[0].fin) == (_h(8, 2, 45), _h(8, 3, 30))
    assert (encontrados[2].inicio, encontrados[2].fin) == (_h(9, 2, 45), _h(9, 3, 30))


def test_incluye_cancelados_y_programados_con_nombre_del_paciente_aun_desactivado(
    db_session: Session, repo_turnos: RepositorioTurnos, catalogo: Catalogo
) -> None:
    cancelado = _turno(db_session, catalogo, _h(8, 13), estado="cancelado")
    programado = _turno(db_session, catalogo, _h(8, 13))
    catalogo.pacientes[0].activo = False
    db_session.flush()

    encontrados = repo_turnos.listar_en(DIA_8)

    assert {t.id: t.estado for t in encontrados} == {
        cancelado.id: "cancelado",
        programado.id: "programado",
    }
    paciente = catalogo.pacientes[0]
    assert {(t.paciente_id, t.paciente_nombre, t.paciente_apellido) for t in encontrados} == {
        (paciente.id, paciente.nombre, paciente.apellido)
    }
    por_id = {t.id: t for t in encontrados}
    assert por_id[cancelado.id].motivo_cancelacion == "Viaje"
    assert por_id[programado.id].motivo_cancelacion is None


def test_ordena_por_inicio_y_despues_por_id(
    db_session: Session, repo_turnos: RepositorioTurnos, catalogo: Catalogo
) -> None:
    tarde = _turno(db_session, catalogo, _h(8, 15), sillon=1, paciente=1)
    a = _turno(db_session, catalogo, _h(8, 13))
    b = _turno(db_session, catalogo, _h(8, 13), profesional=1, sillon=1, paciente=1)

    ids = [t.id for t in repo_turnos.listar_en(DIA_8)]

    assert ids == [*sorted([a.id, b.id]), tarde.id]


# --- 3.2 turnos: filtros ----------------------------------------------------------------------


def test_filtra_por_profesional_por_sillon_y_combinados(
    db_session: Session, repo_turnos: RepositorioTurnos, catalogo: Catalogo
) -> None:
    a, b = catalogo.profesionales
    s1, s2 = catalogo.sillones
    a_s1 = _turno(db_session, catalogo, _h(8, 13), profesional=0, sillon=0)
    b_s1 = _turno(db_session, catalogo, _h(8, 14), profesional=1, sillon=0, paciente=1)
    a_s2 = _turno(db_session, catalogo, _h(8, 15), profesional=0, sillon=1)
    a_sin = _turno(db_session, catalogo, _h(8, 16), profesional=0, sillon=None)

    def ids(profesional: UUID | None, sillon: UUID | None) -> list[UUID]:
        return [t.id for t in repo_turnos.listar_en(DIA_8, profesional, sillon)]

    assert ids(a.id, None) == [a_s1.id, a_s2.id, a_sin.id]
    assert ids(b.id, None) == [b_s1.id]
    assert ids(None, s1.id) == [a_s1.id, b_s1.id]  # el turno sin sillon queda fuera
    assert ids(None, s2.id) == [a_s2.id]
    assert ids(a.id, s1.id) == [a_s1.id]
    assert ids(None, None) == [a_s1.id, b_s1.id, a_s2.id, a_sin.id]


def test_ids_inexistentes_dan_lista_vacia(
    db_session: Session, repo_turnos: RepositorioTurnos, catalogo: Catalogo
) -> None:
    _turno(db_session, catalogo, _h(8, 13))

    assert repo_turnos.listar_en(DIA_8, profesional_id=uuid4()) == []
    assert repo_turnos.listar_en(DIA_8, sillon_id=uuid4()) == []


# --- 3.3 bloqueos -----------------------------------------------------------------------------


def test_bloqueos_en_aplica_el_criterio_semiabierto_y_conserva_el_intervalo_real(
    db_session: Session,
    repo_bloqueos: RepositorioBloqueos,
    catalogo: Catalogo,
    recepcionista: Usuario,
) -> None:
    a = catalogo.profesionales[0]
    varios_dias = _bloqueo(db_session, a.id, recepcionista, _h(5, 11), _h(10, 23))
    termina_justo = _bloqueo(db_session, a.id, recepcionista, _h(7, 23), _h(8, 3))
    empieza_justo = _bloqueo(db_session, a.id, recepcionista, _h(9, 3), _h(9, 11))
    cruza = _bloqueo(db_session, a.id, recepcionista, _h(8, 1), _h(8, 4))

    encontrados = repo_bloqueos.listar_en(DIA_8)

    assert [b.id for b in encontrados] == [varios_dias.id, cruza.id]
    assert (encontrados[0].inicio, encontrados[0].fin) == (_h(5, 11), _h(10, 23))
    assert termina_justo.id not in {b.id for b in encontrados}
    assert empieza_justo.id not in {b.id for b in encontrados}


def test_bloqueos_superpuestos_no_se_fusionan_y_se_filtran_por_profesional_y_orden(
    db_session: Session,
    repo_bloqueos: RepositorioBloqueos,
    catalogo: Catalogo,
    recepcionista: Usuario,
) -> None:
    a, b = catalogo.profesionales
    tarde_a = _bloqueo(db_session, a.id, recepcionista, _h(8, 18), _h(8, 19))
    uno_a = _bloqueo(db_session, a.id, recepcionista, _h(8, 13), _h(8, 15))
    dos_a = _bloqueo(db_session, a.id, recepcionista, _h(8, 14), _h(8, 16))
    de_b = _bloqueo(db_session, b.id, recepcionista, _h(8, 12), _h(8, 13))

    def ids(profesional: UUID | None) -> list[UUID]:
        return [x.id for x in repo_bloqueos.listar_en(DIA_8, profesional)]

    assert ids(a.id) == [uno_a.id, dos_a.id, tarde_a.id]
    assert ids(b.id) == [de_b.id]
    assert ids(None) == [de_b.id, uno_a.id, dos_a.id, tarde_a.id]
    assert ids(uuid4()) == []
