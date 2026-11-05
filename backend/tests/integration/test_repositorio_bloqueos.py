"""RepositorioBloqueos contra PostgreSQL real: lock del profesional, solapes `[)` y consultas."""

from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest
from psycopg.errors import LockNotAvailable
from sqlalchemy import Engine, text
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from app.domain.bloqueos import TurnoAfectado
from app.domain.turnos import Intervalo
from app.infrastructure.db.models import Bloqueo, Turno, Usuario
from app.infrastructure.db.repositorio_bloqueos import RepositorioBloqueos
from tests.integration.factories import Catalogo, crear_catalogo


@pytest.fixture
def catalogo(db_session: Session) -> Catalogo:
    return crear_catalogo(db_session)


@pytest.fixture
def repo(db_session: Session) -> RepositorioBloqueos:
    return RepositorioBloqueos(db_session)


def _h(dia: int, hora: int, minuto: int = 0) -> datetime:
    """Instante UTC de octubre de 2026 (10:00 local es 13:00Z)."""
    return datetime(2026, 10, dia, hora, minuto, tzinfo=UTC)


def _turno(
    db_session: Session,
    catalogo: Catalogo,
    inicio: datetime,
    *,
    minutos: int = 45,
    profesional: int = 0,
    estado: str = "programado",
    paciente: int = 0,
    sillon: int = 0,
) -> Turno:
    turno = Turno(
        profesional_id=catalogo.profesionales[profesional].id,
        sillon_id=catalogo.sillones[sillon].id,
        paciente_id=catalogo.pacientes[paciente].id,
        prestacion_id=catalogo.limpieza.id,
        inicio=inicio,
        fin=inicio + timedelta(minutes=minutos),
        duracion_min=minutos,
        estado=estado,
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
    motivo: str = "Congreso",
) -> Bloqueo:
    bloqueo = Bloqueo(
        profesional_id=profesional_id, inicio=inicio, fin=fin, motivo=motivo, creado_por=autor.id
    )
    db_session.add(bloqueo)
    db_session.flush()
    return bloqueo


def test_bloquear_profesional_devuelve_none_para_un_uuid_desconocido(
    repo: RepositorioBloqueos,
) -> None:
    assert repo.bloquear_profesional(uuid4()) is None


def test_bloquear_profesional_devuelve_al_profesional_activo_o_desactivado(
    repo: RepositorioBloqueos, catalogo: Catalogo
) -> None:
    activo, desactivado = catalogo.profesionales
    desactivado.activo = False

    assert repo.bloquear_profesional(activo.id) is activo
    assert repo.bloquear_profesional(desactivado.id) is desactivado


def test_bloquear_profesional_choca_con_for_share_de_otra_conexion(
    motor_concurrente: Engine, catalogo_commiteado: Catalogo
) -> None:
    profesional = catalogo_commiteado.profesionales[0]
    with Session(motor_concurrente) as sesion:
        assert RepositorioBloqueos(sesion).bloquear_profesional(profesional.id) is not None

        # FOR SHARE es lo que toma `cargar_referencias` al crear o reprogramar un turno
        with pytest.raises(OperationalError) as excinfo, motor_concurrente.connect() as otra:
            otra.execute(
                text("SELECT id FROM profesional WHERE id = :id FOR SHARE NOWAIT"),
                {"id": profesional.id},
            )

        assert isinstance(excinfo.value.orig, LockNotAvailable)


def test_turnos_activos_en_devuelve_los_que_se_superponen_ordenados_por_inicio(
    db_session: Session, repo: RepositorioBloqueos, catalogo: Catalogo
) -> None:
    # Bloqueo 10:00-12:00 local = 13:00Z-15:00Z
    termina_dentro = _turno(db_session, catalogo, _h(8, 14, 30))  # 11:30-12:15 local
    empieza_antes = _turno(db_session, catalogo, _h(8, 12, 30))  # 09:30-10:15 local
    contenido = _turno(db_session, catalogo, _h(8, 13, 30))  # 10:30-11:15 local

    encontrados = repo.turnos_activos_en(
        catalogo.profesionales[0].id, Intervalo(_h(8, 13), _h(8, 15))
    )

    assert encontrados == [
        TurnoAfectado(empieza_antes.id, empieza_antes.inicio, empieza_antes.fin),
        TurnoAfectado(contenido.id, contenido.inicio, contenido.fin),
        TurnoAfectado(termina_dentro.id, termina_dentro.inicio, termina_dentro.fin),
    ]


def test_turnos_activos_en_excluye_cancelados_contiguos_y_de_otro_profesional(
    db_session: Session, repo: RepositorioBloqueos, catalogo: Catalogo
) -> None:
    _turno(db_session, catalogo, _h(8, 13, 30), estado="cancelado")
    _turno(db_session, catalogo, _h(8, 12, 15))  # 09:15-10:00 local: termina justo al empezar
    _turno(db_session, catalogo, _h(8, 15))  # 12:00-12:45 local: empieza justo al terminar
    _turno(db_session, catalogo, _h(8, 13, 30), profesional=1, paciente=1, sillon=1)

    encontrados = repo.turnos_activos_en(
        catalogo.profesionales[0].id, Intervalo(_h(8, 13), _h(8, 15))
    )

    assert encontrados == []


def test_bloqueos_en_es_verdadero_ante_un_solape_y_falso_ante_contiguo_u_otro_profesional(
    db_session: Session, repo: RepositorioBloqueos, catalogo: Catalogo, recepcionista: Usuario
) -> None:
    a, b = catalogo.profesionales
    _bloqueo(db_session, a.id, recepcionista, _h(8, 13), _h(8, 15))

    assert repo.bloqueos_en(a.id, Intervalo(_h(8, 14), _h(8, 16))) is True  # termina fuera
    assert repo.bloqueos_en(a.id, Intervalo(_h(8, 12), _h(8, 14))) is True  # empieza antes
    assert repo.bloqueos_en(a.id, Intervalo(_h(8, 13, 30), _h(8, 14))) is True  # contenido
    assert repo.bloqueos_en(a.id, Intervalo(_h(8, 12), _h(8, 16))) is True  # lo contiene
    assert repo.bloqueos_en(a.id, Intervalo(_h(8, 12), _h(8, 13))) is False  # contiguo antes
    assert repo.bloqueos_en(a.id, Intervalo(_h(8, 15), _h(8, 16))) is False  # contiguo después
    assert repo.bloqueos_en(b.id, Intervalo(_h(8, 13), _h(8, 15))) is False  # otro profesional


def test_listar_ordena_por_inicio_y_filtra_por_profesional(
    db_session: Session, repo: RepositorioBloqueos, catalogo: Catalogo, recepcionista: Usuario
) -> None:
    a, b = catalogo.profesionales
    de_a_dia_9 = _bloqueo(db_session, a.id, recepcionista, _h(9, 13), _h(9, 14))
    de_b = _bloqueo(db_session, b.id, recepcionista, _h(8, 18), _h(8, 19))
    de_a_dia_6 = _bloqueo(db_session, a.id, recepcionista, _h(6, 13), _h(6, 14))

    assert [x.id for x in repo.listar(None)] == [de_a_dia_6.id, de_b.id, de_a_dia_9.id]
    assert [x.id for x in repo.listar(a.id)] == [de_a_dia_6.id, de_a_dia_9.id]
    assert repo.listar(uuid4()) == []


def test_obtener_devuelve_el_bloqueo_o_none_si_el_id_es_desconocido(
    db_session: Session, repo: RepositorioBloqueos, catalogo: Catalogo, recepcionista: Usuario
) -> None:
    profesional = catalogo.profesionales[0]
    existente = _bloqueo(db_session, profesional.id, recepcionista, _h(8, 13), _h(8, 14))

    assert repo.obtener(existente.id) is existente
    assert repo.obtener(uuid4()) is None


def test_agregar_y_eliminar_persisten_y_quitan_el_bloqueo(
    db_session: Session, repo: RepositorioBloqueos, catalogo: Catalogo, recepcionista: Usuario
) -> None:
    profesional = catalogo.profesionales[0]
    nuevo = Bloqueo(
        profesional_id=profesional.id,
        inicio=_h(8, 13),
        fin=_h(8, 14),
        motivo="Trámite",
        creado_por=recepcionista.id,
    )

    repo.agregar(nuevo)

    assert [x.id for x in repo.listar(profesional.id)] == [nuevo.id]

    repo.eliminar(nuevo)

    assert repo.listar(profesional.id) == []
