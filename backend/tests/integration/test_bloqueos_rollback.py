"""Casos de uso de bloqueos: un error con el lock tomado deshace la transacción (design §2)."""

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.orm import Session

from app.application.bloqueos_agenda import BorrarBloqueo, CrearBloqueo, SolicitudBloqueo
from app.domain.bloqueos import BloqueoConTurnosError, BloqueoInvalidoError
from app.domain.usuarios import Rol, UsuarioAutenticado
from app.infrastructure.db.models import Bloqueo, Turno, Usuario
from app.infrastructure.db.repositorio_bloqueos import RepositorioBloqueos
from tests.integration.factories import Catalogo, crear_catalogo

INICIO = datetime(2026, 10, 9, 13, 0, tzinfo=UTC)


@pytest.fixture
def catalogo(db_session: Session) -> Catalogo:
    return crear_catalogo(db_session)


def _espiar_rollback(repo: RepositorioBloqueos) -> list[int]:
    llamadas: list[int] = []
    original = repo.rollback
    repo.rollback = lambda: (llamadas.append(1), original())[1]  # type: ignore[method-assign]
    return llamadas


def _quien(usuario: Usuario) -> UsuarioAutenticado:
    return UsuarioAutenticado(id=usuario.id, rol=Rol.RECEPCIONISTA, profesional_id=None)


def test_alta_rechazada_por_turnos_activos_hace_rollback(
    db_session: Session, catalogo: Catalogo, recepcionista: Usuario
) -> None:
    db_session.add(
        Turno(
            profesional_id=catalogo.profesionales[0].id,
            sillon_id=catalogo.sillones[0].id,
            paciente_id=catalogo.pacientes[0].id,
            prestacion_id=catalogo.limpieza.id,
            inicio=INICIO,
            fin=INICIO + timedelta(minutes=45),
            duracion_min=45,
            estado="programado",
        )
    )
    db_session.flush()
    repo = RepositorioBloqueos(db_session)
    llamadas = _espiar_rollback(repo)
    solicitud = SolicitudBloqueo(
        profesional_id=catalogo.profesionales[0].id,
        inicio=INICIO,
        fin=INICIO + timedelta(hours=2),
        motivo="Congreso",
    )

    with pytest.raises(BloqueoConTurnosError):
        CrearBloqueo(repo).ejecutar(_quien(recepcionista), solicitud)

    assert llamadas == [1]


def test_alta_rechazada_por_forma_invalida_hace_rollback(
    db_session: Session, catalogo: Catalogo, recepcionista: Usuario
) -> None:
    repo = RepositorioBloqueos(db_session)
    llamadas = _espiar_rollback(repo)
    solicitud = SolicitudBloqueo(
        profesional_id=catalogo.profesionales[0].id,
        inicio=INICIO,
        fin=INICIO - timedelta(hours=1),
        motivo="Congreso",
    )

    with pytest.raises(BloqueoInvalidoError):
        CrearBloqueo(repo).ejecutar(_quien(recepcionista), solicitud)

    assert llamadas == [1]


def test_borrado_que_falla_con_el_lock_tomado_hace_rollback(
    db_session: Session, catalogo: Catalogo, recepcionista: Usuario
) -> None:
    bloqueo = Bloqueo(
        profesional_id=catalogo.profesionales[0].id,
        inicio=INICIO,
        fin=INICIO + timedelta(hours=1),
        motivo="Congreso",
        creado_por=recepcionista.id,
    )
    db_session.add(bloqueo)
    db_session.flush()
    repo = RepositorioBloqueos(db_session)
    llamadas = _espiar_rollback(repo)

    def _falla(_: Bloqueo) -> None:
        raise RuntimeError("falla de la base")

    repo.eliminar = _falla  # type: ignore[method-assign]

    with pytest.raises(RuntimeError):
        BorrarBloqueo(repo).ejecutar(_quien(recepcionista), bloqueo.id)

    assert llamadas == [1]
