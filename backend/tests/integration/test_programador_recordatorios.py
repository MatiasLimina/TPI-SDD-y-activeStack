"""ProgramadorRecordatorios como observador de los casos de uso, contra PostgreSQL real."""

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.domain.turnos import SolapamientoError, TurnoCreado
from tests.integration.factories import Catalogo, crear_catalogo
from tests.integration.helpers_recordatorios import (
    BUENOS_AIRES,
    INICIO_TURNO,
    PROGRAMADO_PARA,
    caso_crear,
    contar_recordatorios,
    programador,
    recordatorios_de,
    solicitud,
)

AHORA_LOCAL = datetime(2026, 10, 7, 9, 0, tzinfo=BUENOS_AIRES)


@pytest.fixture
def catalogo(db_session: Session) -> Catalogo:
    return crear_catalogo(db_session)


def _crear(
    session: Session,
    catalogo: Catalogo,
    ahora: datetime,
    inicio: datetime,
    *,
    horas: int = 24,
    paciente: int = 0,
) -> tuple[TurnoCreado, list[tuple[object, datetime]]]:
    prog = programador(session, ahora, horas=horas)
    caso = caso_crear(session, prog, ahora)
    creado = caso.ejecutar(solicitud(catalogo, inicio, paciente=paciente))
    return creado, list(prog.por_publicar)


def test_alta_con_mas_de_24h_crea_un_unico_recordatorio_pendiente_en_utc(
    db_session: Session, catalogo: Catalogo
) -> None:
    creado, _ = _crear(db_session, catalogo, AHORA_LOCAL, INICIO_TURNO)

    (recordatorio,) = recordatorios_de(db_session, creado.id)

    assert recordatorio["estado"] == "pendiente"
    assert recordatorio["canal"] == "mock"
    assert recordatorio["intentos"] == 0
    assert recordatorio["programado_para"] == PROGRAMADO_PARA


def test_alta_con_exactamente_24h_programa_para_ahora(
    db_session: Session, catalogo: Catalogo
) -> None:
    ahora = datetime(2026, 10, 7, 10, 0, tzinfo=BUENOS_AIRES)
    inicio = datetime(2026, 10, 8, 10, 0, tzinfo=BUENOS_AIRES)

    creado, _ = _crear(db_session, catalogo, ahora, inicio)

    (recordatorio,) = recordatorios_de(db_session, creado.id)
    assert recordatorio["estado"] == "pendiente"
    assert recordatorio["programado_para"] == datetime(2026, 10, 7, 13, 0, tzinfo=UTC)


def test_alta_con_menos_de_24h_confirma_el_turno_sin_recordatorio(
    db_session: Session, catalogo: Catalogo
) -> None:
    ahora = datetime(2026, 10, 7, 9, 1, tzinfo=BUENOS_AIRES)
    inicio = datetime(2026, 10, 8, 9, 0, tzinfo=BUENOS_AIRES)

    creado, por_publicar = _crear(db_session, catalogo, ahora, inicio)

    assert creado.estado == "programado"
    assert recordatorios_de(db_session, creado.id) == []
    assert por_publicar == []


@pytest.mark.parametrize(
    ("inicio_local", "paciente", "programado_utc"),
    [
        (datetime(2026, 10, 9, 9, 0, tzinfo=BUENOS_AIRES), 0, None),
        (
            datetime(2026, 10, 9, 11, 0, tzinfo=BUENOS_AIRES),
            1,
            datetime(2026, 10, 7, 14, 0, tzinfo=UTC),
        ),
        (
            datetime(2026, 10, 9, 10, 0, tzinfo=BUENOS_AIRES),
            0,
            datetime(2026, 10, 7, 13, 0, tzinfo=UTC),
        ),
    ],
    ids=["47h-sin-recordatorio", "49h-con-recordatorio", "48h-exactas-con-recordatorio"],
)
def test_alta_con_anticipacion_configurada_en_48h(
    db_session: Session,
    catalogo: Catalogo,
    inicio_local: datetime,
    paciente: int,
    programado_utc: datetime | None,
) -> None:
    ahora = datetime(2026, 10, 7, 10, 0, tzinfo=BUENOS_AIRES)

    creado, _ = _crear(db_session, catalogo, ahora, inicio_local, horas=48, paciente=paciente)

    filas = recordatorios_de(db_session, creado.id)
    if programado_utc is None:
        assert filas == []
    else:
        (recordatorio,) = filas
        assert recordatorio["estado"] == "pendiente"
        assert recordatorio["programado_para"] == programado_utc


def test_programador_anota_para_publicar_solo_los_pendientes_creados(
    db_session: Session, catalogo: Catalogo
) -> None:
    creado, por_publicar = _crear(db_session, catalogo, AHORA_LOCAL, INICIO_TURNO)

    (recordatorio,) = recordatorios_de(db_session, creado.id)
    assert por_publicar == [(recordatorio["id"], PROGRAMADO_PARA)]


def test_programado_para_se_lee_de_la_base_como_timestamptz_en_utc(
    db_session: Session, catalogo: Catalogo
) -> None:
    creado, _ = _crear(db_session, catalogo, AHORA_LOCAL, INICIO_TURNO)

    tipo, instante = db_session.execute(
        text(
            "SELECT pg_typeof(programado_para)::text, programado_para AT TIME ZONE 'UTC' "
            "FROM recordatorio WHERE turno_id = :id"
        ),
        {"id": creado.id},
    ).one()

    assert tipo == "timestamp with time zone"
    assert instante == PROGRAMADO_PARA.replace(tzinfo=None)


def test_alta_rechazada_no_crea_recordatorios_ni_anota_publicaciones(
    db_session: Session, catalogo: Catalogo
) -> None:
    _crear(db_session, catalogo, AHORA_LOCAL, INICIO_TURNO)
    antes = contar_recordatorios(db_session)
    prog = programador(db_session, AHORA_LOCAL)

    with pytest.raises(SolapamientoError):
        caso_crear(db_session, prog, AHORA_LOCAL).ejecutar(
            solicitud(catalogo, INICIO_TURNO + timedelta(minutes=30), paciente=1)
        )

    assert contar_recordatorios(db_session) == antes
    assert prog.por_publicar == []
