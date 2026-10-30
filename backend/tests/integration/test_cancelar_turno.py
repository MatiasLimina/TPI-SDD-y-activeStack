"""Caso de uso CancelarTurno contra PostgreSQL real, con reloj fijo inyectado."""

from collections.abc import Sequence
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.application.cancelar_turno import CancelarTurno, ObservadorCancelacion
from app.application.crear_turno import CrearTurno, SolicitudTurno
from app.domain.turnos import TurnoInexistenteError, TurnoNoModificableError, TurnoRegistrado
from app.infrastructure.db.models import Turno
from app.infrastructure.db.repositorio_turnos import RepositorioTurnos
from tests.integration.factories import Catalogo, crear_catalogo

AHORA = datetime(2026, 10, 7, 12, 0, tzinfo=UTC)  # 09:00 hora local
INICIO = datetime(2026, 10, 8, 13, 0, tzinfo=UTC)  # 10:00 hora local del día siguiente


@pytest.fixture
def catalogo(db_session: Session) -> Catalogo:
    return crear_catalogo(db_session)


def _crear(db_session: Session, c: Catalogo, *, reloj: datetime = AHORA) -> Turno:
    """Crea un turno con el caso de uso de alta usando `reloj` como instante actual."""
    creado = CrearTurno(RepositorioTurnos(db_session), reloj=lambda: reloj).ejecutar(
        SolicitudTurno(
            profesional_id=c.profesionales[0].id,
            paciente_id=c.pacientes[0].id,
            prestacion_id=c.limpieza.id,
            sillon_id=c.sillones[0].id,
            inicio=INICIO,
        )
    )
    turno = db_session.get(Turno, creado.id)
    assert turno is not None
    return turno


def _cancelar(
    db_session: Session,
    ahora: datetime = AHORA,
    observadores: Sequence[ObservadorCancelacion] = (),
) -> CancelarTurno:
    return CancelarTurno(
        RepositorioTurnos(db_session), reloj=lambda: ahora, observadores=observadores
    )


# --- 4.1 cancelación válida --------------------------------------------------------------


@pytest.mark.parametrize(
    ("motivo", "esperado"),
    [("  Viaje imprevisto  ", "Viaje imprevisto"), (None, None), ("   ", None)],
)
def test_cancelar_turno_futuro_devuelve_registrado_cancelado_y_persiste(
    db_session: Session, catalogo: Catalogo, motivo: str | None, esperado: str | None
) -> None:
    turno_id = _crear(db_session, catalogo).id

    resultado = _cancelar(db_session).ejecutar(turno_id, motivo)

    assert isinstance(resultado, TurnoRegistrado)
    assert resultado.estado == "cancelado"
    assert resultado.motivo_cancelacion == esperado
    db_session.expire_all()
    persistido = db_session.get(Turno, turno_id)
    assert persistido is not None
    assert (persistido.estado, persistido.motivo_cancelacion) == ("cancelado", esperado)


# --- 4.2 errores -------------------------------------------------------------------------


def test_cancelar_turno_inexistente_lanza_turno_inexistente(db_session: Session) -> None:
    inexistente = uuid4()

    with pytest.raises(TurnoInexistenteError) as info:
        _cancelar(db_session).ejecutar(inexistente, None)

    assert info.value.turno_id == inexistente


def test_cancelar_dos_veces_lanza_ya_cancelado_sin_cambiar_el_motivo(
    db_session: Session, catalogo: Catalogo
) -> None:
    turno_id = _crear(db_session, catalogo).id
    _cancelar(db_session).ejecutar(turno_id, "Viaje imprevisto")

    with pytest.raises(TurnoNoModificableError) as info:
        _cancelar(db_session).ejecutar(turno_id, "Otro motivo")

    assert info.value.codigo == "turno_ya_cancelado"
    db_session.expire_all()
    persistido = db_session.get(Turno, turno_id)
    assert persistido is not None
    assert persistido.motivo_cancelacion == "Viaje imprevisto"


@pytest.mark.parametrize(
    "ahora",
    [INICIO, INICIO + timedelta(minutes=20), INICIO + timedelta(days=1)],
    ids=["limite-exacto", "en-curso", "pasado"],
)
def test_cancelar_turno_iniciado_lanza_ya_iniciado_y_sigue_programado(
    db_session: Session, catalogo: Catalogo, ahora: datetime
) -> None:
    turno_id = _crear(db_session, catalogo).id

    with pytest.raises(TurnoNoModificableError) as info:
        _cancelar(db_session, ahora).ejecutar(turno_id, "Tarde")

    assert info.value.codigo == "turno_ya_iniciado"
    db_session.expire_all()
    persistido = db_session.get(Turno, turno_id)
    assert persistido is not None
    assert (persistido.estado, persistido.motivo_cancelacion) == ("programado", None)


# --- 4.3 puntos de extensión -------------------------------------------------------------


def test_observador_recibe_anterior_y_nuevo_antes_del_commit(
    db_session: Session, catalogo: Catalogo
) -> None:
    turno_id = _crear(db_session, catalogo).id
    recibidos: list[tuple[TurnoRegistrado, TurnoRegistrado]] = []
    repo = RepositorioTurnos(db_session)
    commits: list[int] = []
    commit_original = repo.commit
    repo.commit = lambda: (commits.append(len(recibidos)), commit_original())[1]  # type: ignore[method-assign]
    caso = CancelarTurno(
        repo, reloj=lambda: AHORA, observadores=[lambda a, n: recibidos.append((a, n))]
    )

    resultado = caso.ejecutar(turno_id, "  Motivo  ")

    assert len(recibidos) == 1
    anterior, nuevo = recibidos[0]
    assert nuevo == resultado
    assert (anterior.estado, anterior.motivo_cancelacion) == ("programado", None)
    assert (nuevo.estado, nuevo.motivo_cancelacion) == ("cancelado", "Motivo")
    assert anterior.id == nuevo.id == turno_id
    assert (anterior.inicio, anterior.fin) == (nuevo.inicio, nuevo.fin)
    assert commits == [1]  # el observador ya había corrido cuando se hizo el commit


def test_observador_sin_motivo_recibe_motivo_nulo_en_anterior_y_nuevo(
    db_session: Session, catalogo: Catalogo
) -> None:
    turno_id = _crear(db_session, catalogo).id
    recibidos: list[tuple[TurnoRegistrado, TurnoRegistrado]] = []

    _cancelar(db_session, observadores=[lambda a, n: recibidos.append((a, n))]).ejecutar(
        turno_id, "   "
    )

    anterior, nuevo = recibidos[0]
    assert anterior.motivo_cancelacion is None
    assert (nuevo.estado, nuevo.motivo_cancelacion) == ("cancelado", None)


def test_observador_que_falla_hace_rollback_y_el_turno_sigue_programado(
    db_session: Session, catalogo: Catalogo
) -> None:
    turno_id = _crear(db_session, catalogo).id

    def falla(_anterior: TurnoRegistrado, _nuevo: TurnoRegistrado) -> None:
        raise RuntimeError("fallo del observador")

    with pytest.raises(RuntimeError, match="fallo del observador"):
        _cancelar(db_session, observadores=[falla]).ejecutar(turno_id, "Motivo")

    estado = db_session.scalar(select(Turno.estado).where(Turno.id == turno_id))
    assert estado == "programado"


def test_sin_observadores_la_cancelacion_funciona(db_session: Session, catalogo: Catalogo) -> None:
    turno_id = _crear(db_session, catalogo).id

    resultado = _cancelar(db_session).ejecutar(turno_id, None)

    assert resultado.estado == "cancelado"
