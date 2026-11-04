"""Cancelar el turno cancela su recordatorio pendiente (caso de uso + programador, PostgreSQL)."""

from datetime import datetime

import pytest
from sqlalchemy.orm import Session

from app.domain.recordatorios import EstadoRecordatorio
from tests.integration.factories import Catalogo, crear_catalogo
from tests.integration.helpers_recordatorios import (
    BUENOS_AIRES,
    PROGRAMADO_PARA,
    caso_cancelar,
    caso_crear,
    contar_recordatorios,
    crear_sin_programar,
    insertar_recordatorio,
    programador,
    recordatorios_de,
    solicitud,
)

AHORA_LOCAL = datetime(2026, 10, 7, 9, 0, tzinfo=BUENOS_AIRES)


@pytest.fixture
def catalogo(db_session: Session) -> Catalogo:
    return crear_catalogo(db_session)


def test_cancelar_con_recordatorio_pendiente_lo_pasa_a_cancelado_sin_tocar_el_resto(
    db_session: Session, catalogo: Catalogo
) -> None:
    creado = caso_crear(db_session, programador(db_session, AHORA_LOCAL), AHORA_LOCAL).ejecutar(
        solicitud(catalogo)
    )
    (antes,) = recordatorios_de(db_session, creado.id)

    cancelado = caso_cancelar(
        db_session, programador(db_session, AHORA_LOCAL), AHORA_LOCAL
    ).ejecutar(creado.id, None)

    assert cancelado.estado == "cancelado"
    (despues,) = recordatorios_de(db_session, creado.id)
    assert despues["id"] == antes["id"]
    assert despues["estado"] == "cancelado"
    assert despues["programado_para"] == PROGRAMADO_PARA
    assert despues["intentos"] == 0


def test_cancelar_un_turno_sin_recordatorio_no_crea_ninguno(
    db_session: Session, catalogo: Catalogo
) -> None:
    inicio = datetime(2026, 10, 7, 15, 0, tzinfo=BUENOS_AIRES)  # 6 h después del reloj
    creado = caso_crear(db_session, programador(db_session, AHORA_LOCAL), AHORA_LOCAL).ejecutar(
        solicitud(catalogo, inicio)
    )
    assert recordatorios_de(db_session, creado.id) == []

    caso_cancelar(db_session, programador(db_session, AHORA_LOCAL), AHORA_LOCAL).ejecutar(
        creado.id, None
    )

    assert recordatorios_de(db_session, creado.id) == []


@pytest.mark.parametrize(
    ("estado", "intentos"),
    [
        (EstadoRecordatorio.ENVIADO, 1),
        (EstadoRecordatorio.FALLIDO, 3),
        (EstadoRecordatorio.CANCELADO, 0),
    ],
)
def test_cancelar_no_modifica_recordatorios_que_no_estan_pendientes(
    db_session: Session, catalogo: Catalogo, estado: EstadoRecordatorio, intentos: int
) -> None:
    creado = crear_sin_programar(db_session, catalogo, ahora=AHORA_LOCAL)
    insertar_recordatorio(db_session, creado.id, estado=estado, intentos=intentos)
    ahora = datetime(2026, 10, 8, 11, 0, tzinfo=BUENOS_AIRES)

    caso_cancelar(db_session, programador(db_session, ahora), ahora).ejecutar(creado.id, None)

    (fila,) = recordatorios_de(db_session, creado.id)
    assert (fila["estado"], fila["intentos"]) == (estado.value, intentos)
    assert contar_recordatorios(db_session) == 1
