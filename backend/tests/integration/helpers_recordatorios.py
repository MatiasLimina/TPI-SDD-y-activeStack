"""Ayudas de los tests de recordatorios: lectura directa de la tabla y armado de casos de uso."""

from datetime import UTC, datetime, timedelta, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.application.cancelar_turno import CancelarTurno
from app.application.crear_turno import CrearTurno, SolicitudTurno
from app.application.recordatorios import ProgramadorRecordatorios
from app.application.reprogramar_turno import ReprogramarTurno
from app.domain.recordatorios import EstadoRecordatorio
from app.domain.turnos import TurnoCreado
from app.infrastructure.db.repositorio_recordatorios import RepositorioRecordatorios
from app.infrastructure.db.repositorio_turnos import RepositorioTurnos
from tests.integration.factories import Catalogo

BUENOS_AIRES = timezone(timedelta(hours=-3))
AHORA = datetime(2026, 10, 7, 12, 0, tzinfo=UTC)  # 09:00 hora local
INICIO_TURNO = datetime(2026, 10, 9, 10, 0, tzinfo=BUENOS_AIRES)  # 13:00Z
PROGRAMADO_PARA = datetime(2026, 10, 8, 13, 0, tzinfo=UTC)  # INICIO_TURNO - 24 h


def recordatorios_de(session: Session, turno_id: UUID) -> list[dict[str, Any]]:
    """Filas de `recordatorio` del turno por fecha de creación, leídas directo con SQL."""
    filas = session.execute(
        text(
            "SELECT id, turno_id, programado_para, estado, canal, intentos FROM recordatorio "
            "WHERE turno_id = :turno_id ORDER BY creado_en, programado_para, id"
        ),
        {"turno_id": turno_id},
    ).mappings()
    return [dict(fila) for fila in filas]


def contar_recordatorios(session: Session) -> int:
    return int(session.execute(text("SELECT count(*) FROM recordatorio")).scalar_one())


def insertar_recordatorio(
    session: Session,
    turno_id: UUID,
    *,
    estado: EstadoRecordatorio = EstadoRecordatorio.PENDIENTE,
    intentos: int = 0,
    programado_para: datetime = PROGRAMADO_PARA,
) -> UUID:
    """Inserta un recordatorio directo (sin pasar por el programador)."""
    fila = session.execute(
        text(
            "INSERT INTO recordatorio (turno_id, programado_para, estado, canal, intentos) "
            "VALUES (:turno_id, :programado_para, :estado, 'mock', :intentos) RETURNING id"
        ),
        {
            "turno_id": turno_id,
            "programado_para": programado_para,
            "estado": estado.value,
            "intentos": intentos,
        },
    ).one()
    return fila.id


def programador(
    session: Session, ahora: datetime = AHORA, *, horas: int = 24
) -> ProgramadorRecordatorios:
    return ProgramadorRecordatorios(
        RepositorioRecordatorios(session), lambda: ahora, timedelta(hours=horas)
    )


def solicitud(catalogo: Catalogo, inicio: datetime = INICIO_TURNO, *, paciente: int = 0) -> Any:
    return SolicitudTurno(
        profesional_id=catalogo.profesionales[0].id,
        paciente_id=catalogo.pacientes[paciente].id,
        prestacion_id=catalogo.limpieza.id,
        sillon_id=catalogo.sillones[0].id,
        inicio=inicio,
    )


def caso_crear(
    session: Session, prog: ProgramadorRecordatorios, ahora: datetime = AHORA
) -> CrearTurno:
    return CrearTurno(RepositorioTurnos(session), lambda: ahora, observadores=[prog.al_crear])


def caso_cancelar(
    session: Session, prog: ProgramadorRecordatorios, ahora: datetime = AHORA
) -> CancelarTurno:
    return CancelarTurno(RepositorioTurnos(session), lambda: ahora, observadores=[prog.al_cancelar])


def caso_reprogramar(
    session: Session, prog: ProgramadorRecordatorios, ahora: datetime = AHORA
) -> ReprogramarTurno:
    return ReprogramarTurno(
        RepositorioTurnos(session), lambda: ahora, observadores=[prog.al_reprogramar]
    )


def crear_sin_programar(
    session: Session,
    catalogo: Catalogo,
    inicio: datetime = INICIO_TURNO,
    *,
    ahora: datetime = AHORA,
    paciente: int = 0,
) -> TurnoCreado:
    """Turno creado sin observadores: no tiene recordatorio hasta que el test lo inserte."""
    caso = CrearTurno(RepositorioTurnos(session), lambda: ahora)
    return caso.ejecutar(solicitud(catalogo, inicio, paciente=paciente))
