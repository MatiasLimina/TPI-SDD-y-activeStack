"""Atomicidad del recordatorio con el cambio del turno, con fallas reales de PostgreSQL.

Un programador con `canal="sms"` viola `ck_recordatorio_canal_valido`: es una falla real de la
base (sin mocks) que debe revertir el turno y su auditoría.
"""

from datetime import datetime, timedelta
from uuid import UUID

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.application.auditoria_turnos import AuditorTurnos
from app.application.cancelar_turno import CancelarTurno
from app.application.crear_turno import CrearTurno
from app.application.recordatorios import ProgramadorRecordatorios
from app.application.reprogramar_turno import ReprogramarTurno, SolicitudReprogramacion
from app.domain.turnos import SolapamientoError, TurnoInvalidoError, TurnoNoModificableError
from app.infrastructure.db.models import Usuario
from app.infrastructure.db.repositorio_auditoria import RepositorioAuditoria
from app.infrastructure.db.repositorio_recordatorios import RepositorioRecordatorios
from app.infrastructure.db.repositorio_turnos import RepositorioTurnos
from tests.integration.factories import Catalogo, crear_catalogo
from tests.integration.helpers_recordatorios import (
    BUENOS_AIRES,
    INICIO_TURNO,
    PROGRAMADO_PARA,
    caso_cancelar,
    caso_crear,
    caso_reprogramar,
    contar_recordatorios,
    programador,
    recordatorios_de,
    solicitud,
)

AHORA_LOCAL = datetime(2026, 10, 7, 9, 0, tzinfo=BUENOS_AIRES)
NUEVO_INICIO = datetime(2026, 10, 12, 15, 0, tzinfo=BUENOS_AIRES)


@pytest.fixture
def catalogo(db_session: Session) -> Catalogo:
    return crear_catalogo(db_session)


@pytest.fixture
def fijo(db_session: Session, catalogo: Catalogo, recepcionista: Usuario) -> None:
    """Fija catálogo y usuario en la transacción externa: un rollback no los deshace."""
    db_session.commit()


def _programador_roto(session: Session) -> ProgramadorRecordatorios:
    return ProgramadorRecordatorios(
        RepositorioRecordatorios(session), lambda: AHORA_LOCAL, timedelta(hours=24), canal="sms"
    )


def _auditor(session: Session, usuario: Usuario) -> AuditorTurnos:
    return AuditorTurnos(RepositorioAuditoria(session), usuario.id, lambda: AHORA_LOCAL)


def _total(session: Session, tabla: str) -> int:
    return int(session.execute(text(f"SELECT count(*) FROM {tabla}")).scalar_one())


def _fila_turno(session: Session, turno_id: UUID) -> object:
    session.expire_all()
    return session.execute(
        text("SELECT inicio, fin, estado FROM turno WHERE id = :id"), {"id": turno_id}
    ).one()


@pytest.mark.usefixtures("fijo")
def test_falla_del_recordatorio_en_el_alta_no_deja_turno_auditoria_ni_recordatorio(
    db_session: Session, catalogo: Catalogo, recepcionista: Usuario
) -> None:
    caso = CrearTurno(
        RepositorioTurnos(db_session),
        lambda: AHORA_LOCAL,
        observadores=[
            _auditor(db_session, recepcionista).al_crear,
            _programador_roto(db_session).al_crear,
        ],
    )

    with pytest.raises(IntegrityError) as excinfo:
        caso.ejecutar(solicitud(catalogo, datetime(2026, 10, 9, 9, 0, tzinfo=BUENOS_AIRES)))

    assert excinfo.value.orig.diag.constraint_name == "ck_recordatorio_canal_valido"
    assert _total(db_session, "turno") == 0
    assert _total(db_session, "turno_auditoria") == 0
    assert contar_recordatorios(db_session) == 0


@pytest.mark.usefixtures("fijo")
def test_falla_del_recordatorio_en_la_reprogramacion_conserva_turno_y_recordatorio_original(
    db_session: Session, catalogo: Catalogo, recepcionista: Usuario
) -> None:
    creado = caso_crear(db_session, programador(db_session, AHORA_LOCAL), AHORA_LOCAL).ejecutar(
        solicitud(catalogo)
    )
    (original,) = recordatorios_de(db_session, creado.id)
    caso = ReprogramarTurno(
        RepositorioTurnos(db_session),
        lambda: AHORA_LOCAL,
        observadores=[
            _auditor(db_session, recepcionista).al_reprogramar,
            _programador_roto(db_session).al_reprogramar,
        ],
    )

    with pytest.raises(IntegrityError):
        caso.ejecutar(creado.id, SolicitudReprogramacion(inicio=NUEVO_INICIO))

    assert _fila_turno(db_session, creado.id).inicio == INICIO_TURNO  # type: ignore[attr-defined]
    (despues,) = recordatorios_de(db_session, creado.id)
    assert despues["id"] == original["id"]
    assert despues["estado"] == "pendiente"
    assert despues["programado_para"] == PROGRAMADO_PARA
    assert _total(db_session, "turno_auditoria") == 0


@pytest.mark.usefixtures("fijo")
def test_alta_en_conflicto_no_toca_los_recordatorios(
    db_session: Session, catalogo: Catalogo
) -> None:
    creado = caso_crear(db_session, programador(db_session, AHORA_LOCAL), AHORA_LOCAL).ejecutar(
        solicitud(catalogo)
    )
    (original,) = recordatorios_de(db_session, creado.id)
    antes = contar_recordatorios(db_session)

    with pytest.raises(SolapamientoError):
        caso_crear(db_session, programador(db_session, AHORA_LOCAL), AHORA_LOCAL).ejecutar(
            solicitud(catalogo, INICIO_TURNO + timedelta(minutes=30), paciente=1)
        )

    assert contar_recordatorios(db_session) == antes
    assert recordatorios_de(db_session, creado.id) == [original]


@pytest.mark.usefixtures("fijo")
def test_reprogramacion_con_duracion_7_no_toca_los_recordatorios(
    db_session: Session, catalogo: Catalogo
) -> None:
    creado = caso_crear(db_session, programador(db_session, AHORA_LOCAL), AHORA_LOCAL).ejecutar(
        solicitud(catalogo)
    )
    (original,) = recordatorios_de(db_session, creado.id)

    with pytest.raises(TurnoInvalidoError):
        caso_reprogramar(db_session, programador(db_session, AHORA_LOCAL), AHORA_LOCAL).ejecutar(
            creado.id, SolicitudReprogramacion(duracion_min=7)
        )

    assert recordatorios_de(db_session, creado.id) == [original]


@pytest.mark.usefixtures("fijo")
def test_segunda_cancelacion_no_modifica_ni_agrega_recordatorios(
    db_session: Session, catalogo: Catalogo
) -> None:
    creado = caso_crear(db_session, programador(db_session, AHORA_LOCAL), AHORA_LOCAL).ejecutar(
        solicitud(catalogo)
    )
    cancelar: CancelarTurno = caso_cancelar(
        db_session, programador(db_session, AHORA_LOCAL), AHORA_LOCAL
    )
    cancelar.ejecutar(creado.id, None)
    (tras_cancelar,) = recordatorios_de(db_session, creado.id)

    with pytest.raises(TurnoNoModificableError) as excinfo:
        cancelar.ejecutar(creado.id, "Otra vez")

    assert excinfo.value.codigo == "turno_ya_cancelado"
    assert tras_cancelar["estado"] == "cancelado"
    assert recordatorios_de(db_session, creado.id) == [tras_cancelar]
