"""Reprogramar el turno reprograma su recordatorio (caso de uso + programador, PostgreSQL)."""

from datetime import UTC, datetime

import pytest
from sqlalchemy.orm import Session

from app.application.reprogramar_turno import SolicitudReprogramacion
from app.domain.recordatorios import EstadoRecordatorio
from tests.integration.factories import Catalogo, crear_catalogo
from tests.integration.helpers_recordatorios import (
    BUENOS_AIRES,
    PROGRAMADO_PARA,
    caso_crear,
    caso_reprogramar,
    crear_sin_programar,
    insertar_recordatorio,
    programador,
    recordatorios_de,
    solicitud,
)

AHORA_LOCAL = datetime(2026, 10, 7, 9, 0, tzinfo=BUENOS_AIRES)
NUEVO_INICIO = datetime(2026, 10, 12, 15, 0, tzinfo=BUENOS_AIRES)
NUEVO_PROGRAMADO = datetime(2026, 10, 11, 18, 0, tzinfo=UTC)


@pytest.fixture
def catalogo(db_session: Session) -> Catalogo:
    return crear_catalogo(db_session)


def _crear_con_recordatorio(session: Session, catalogo: Catalogo) -> tuple[object, object]:
    creado = caso_crear(session, programador(session, AHORA_LOCAL), AHORA_LOCAL).ejecutar(
        solicitud(catalogo)
    )
    (recordatorio,) = recordatorios_de(session, creado.id)
    return creado, recordatorio["id"]


def test_nuevo_inicio_con_24h_o_mas_cancela_el_anterior_y_crea_uno_nuevo(
    db_session: Session, catalogo: Catalogo
) -> None:
    creado, anterior_id = _crear_con_recordatorio(db_session, catalogo)
    prog = programador(db_session, AHORA_LOCAL)

    caso_reprogramar(db_session, prog, AHORA_LOCAL).ejecutar(
        creado.id, SolicitudReprogramacion(inicio=NUEVO_INICIO)
    )

    filas = recordatorios_de(db_session, creado.id)
    assert [f["estado"] for f in filas] == ["cancelado", "pendiente"]
    anterior, nuevo = filas
    assert anterior["id"] == anterior_id
    assert anterior["programado_para"] == PROGRAMADO_PARA
    assert nuevo["id"] != anterior_id
    assert nuevo["programado_para"] == NUEVO_PROGRAMADO
    assert nuevo["intentos"] == 0
    assert prog.por_publicar == [(nuevo["id"], NUEVO_PROGRAMADO)]


def test_nuevo_inicio_con_menos_de_24h_cancela_el_anterior_y_no_crea_otro(
    db_session: Session, catalogo: Catalogo
) -> None:
    creado, _ = _crear_con_recordatorio(db_session, catalogo)
    prog = programador(db_session, AHORA_LOCAL)

    caso_reprogramar(db_session, prog, AHORA_LOCAL).ejecutar(
        creado.id,
        SolicitudReprogramacion(inicio=datetime(2026, 10, 7, 15, 0, tzinfo=BUENOS_AIRES)),
    )

    (fila,) = recordatorios_de(db_session, creado.id)
    assert fila["estado"] == "cancelado"
    assert prog.por_publicar == []


def test_turno_sin_recordatorio_reprogramado_con_24h_o_mas_pasa_a_tener_uno(
    db_session: Session, catalogo: Catalogo
) -> None:
    creado = caso_crear(db_session, programador(db_session, AHORA_LOCAL), AHORA_LOCAL).ejecutar(
        solicitud(catalogo, datetime(2026, 10, 7, 15, 0, tzinfo=BUENOS_AIRES))
    )
    assert recordatorios_de(db_session, creado.id) == []

    caso_reprogramar(db_session, programador(db_session, AHORA_LOCAL), AHORA_LOCAL).ejecutar(
        creado.id,
        SolicitudReprogramacion(inicio=datetime(2026, 10, 9, 10, 0, tzinfo=BUENOS_AIRES)),
    )

    (fila,) = recordatorios_de(db_session, creado.id)
    assert fila["estado"] == "pendiente"
    assert fila["programado_para"] == PROGRAMADO_PARA


def test_reprogramar_sin_cambio_de_inicio_conserva_el_mismo_recordatorio(
    db_session: Session, catalogo: Catalogo
) -> None:
    creado, anterior_id = _crear_con_recordatorio(db_session, catalogo)
    prog = programador(db_session, AHORA_LOCAL)

    caso_reprogramar(db_session, prog, AHORA_LOCAL).ejecutar(
        creado.id, SolicitudReprogramacion(sillon_id=catalogo.sillones[1].id)
    )

    (fila,) = recordatorios_de(db_session, creado.id)
    assert fila["id"] == anterior_id
    assert fila["estado"] == "pendiente"
    assert fila["programado_para"] == PROGRAMADO_PARA
    assert prog.por_publicar == []


def test_reprogramar_con_el_mismo_inicio_explicito_tampoco_toca_el_recordatorio(
    db_session: Session, catalogo: Catalogo
) -> None:
    creado, anterior_id = _crear_con_recordatorio(db_session, catalogo)

    caso_reprogramar(db_session, programador(db_session, AHORA_LOCAL), AHORA_LOCAL).ejecutar(
        creado.id, SolicitudReprogramacion(inicio=creado.inicio)
    )

    (fila,) = recordatorios_de(db_session, creado.id)
    assert (fila["id"], fila["estado"]) == (anterior_id, "pendiente")


@pytest.mark.parametrize(
    ("estado", "intentos"),
    [(EstadoRecordatorio.ENVIADO, 1), (EstadoRecordatorio.FALLIDO, 3)],
)
def test_recordatorio_enviado_o_fallido_queda_intacto_y_se_crea_un_segundo_pendiente(
    db_session: Session, catalogo: Catalogo, estado: EstadoRecordatorio, intentos: int
) -> None:
    creado = crear_sin_programar(db_session, catalogo, ahora=AHORA_LOCAL)
    anterior_id = insertar_recordatorio(db_session, creado.id, estado=estado, intentos=intentos)
    ahora = datetime(2026, 10, 8, 11, 0, tzinfo=BUENOS_AIRES)
    prog = programador(db_session, ahora)

    caso_reprogramar(db_session, prog, ahora).ejecutar(
        creado.id,
        SolicitudReprogramacion(inicio=datetime(2026, 10, 12, 10, 0, tzinfo=BUENOS_AIRES)),
    )

    anterior, nuevo = recordatorios_de(db_session, creado.id)
    assert (anterior["id"], anterior["estado"], anterior["intentos"]) == (
        anterior_id,
        estado.value,
        intentos,
    )
    assert nuevo["estado"] == "pendiente"
    assert nuevo["intentos"] == 0
    assert nuevo["programado_para"] == datetime(2026, 10, 11, 13, 0, tzinfo=UTC)
    assert prog.por_publicar == [(nuevo["id"], nuevo["programado_para"])]
