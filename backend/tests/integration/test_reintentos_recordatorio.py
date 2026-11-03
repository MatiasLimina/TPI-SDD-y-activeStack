"""Reintentos con backoff exponencial y estado fallido (emisor que falla, PostgreSQL real)."""

from datetime import UTC, datetime

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from tests.fakes import ColaEnMemoria, EmisorQueFalla
from tests.integration.factories import Catalogo, crear_catalogo
from tests.integration.helpers_recordatorios import (
    PROGRAMADO_PARA,
    armar_worker,
    crear_sin_programar,
    insertar_recordatorio,
    recordatorios_de,
)

T1 = datetime(2026, 10, 8, 13, 1, tzinfo=UTC)
T3 = datetime(2026, 10, 8, 13, 3, tzinfo=UTC)


@pytest.fixture
def catalogo(db_session: Session) -> Catalogo:
    return crear_catalogo(db_session)


def _pendiente_encolado(
    session: Session, catalogo: Catalogo, cola: ColaEnMemoria, *, intentos: int = 0
) -> tuple[object, object]:
    turno = crear_sin_programar(session, catalogo)
    recordatorio_id = insertar_recordatorio(session, turno.id, intentos=intentos)
    cola.encolar(recordatorio_id, PROGRAMADO_PARA)
    return turno, recordatorio_id


def test_primer_intento_fallido_deja_pendiente_con_un_intento_y_reencola_a_1_minuto(
    db_session: Session, catalogo: Catalogo
) -> None:
    cola, emisor = ColaEnMemoria(), EmisorQueFalla(fallas=10)
    turno, recordatorio_id = _pendiente_encolado(db_session, catalogo, cola)

    armar_worker(db_session, cola, emisor).ciclo(PROGRAMADO_PARA)

    (fila,) = recordatorios_de(db_session, turno.id)
    assert (fila["estado"], fila["intentos"]) == ("pendiente", 1)
    assert cola.elementos == {recordatorio_id: T1}
    assert emisor.invocaciones == 1


def test_segundo_intento_fallido_reencola_a_2_minutos(
    db_session: Session, catalogo: Catalogo
) -> None:
    cola, emisor = ColaEnMemoria(), EmisorQueFalla(fallas=10)
    turno, recordatorio_id = _pendiente_encolado(db_session, catalogo, cola)
    worker = armar_worker(db_session, cola, emisor)
    worker.ciclo(PROGRAMADO_PARA)

    worker.ciclo(T1)

    (fila,) = recordatorios_de(db_session, turno.id)
    assert (fila["estado"], fila["intentos"]) == ("pendiente", 2)
    assert cola.elementos == {recordatorio_id: T3}


def test_tercer_intento_fallido_deja_fallido_sin_reencolar_con_tres_invocaciones(
    db_session: Session, catalogo: Catalogo
) -> None:
    cola, emisor = ColaEnMemoria(), EmisorQueFalla(fallas=10)
    turno, _ = _pendiente_encolado(db_session, catalogo, cola)
    worker = armar_worker(db_session, cola, emisor)
    worker.ciclo(PROGRAMADO_PARA)
    worker.ciclo(T1)

    worker.ciclo(T3)

    (fila,) = recordatorios_de(db_session, turno.id)
    assert (fila["estado"], fila["intentos"]) == ("fallido", 3)
    assert cola.elementos == {}
    assert emisor.invocaciones == 3
    assert worker.ciclo(datetime(2026, 10, 9, 13, 0, tzinfo=UTC)) == 0
    assert emisor.invocaciones == 3


def test_falla_y_despues_exito_deja_enviado_con_dos_intentos(
    db_session: Session, catalogo: Catalogo
) -> None:
    cola, emisor = ColaEnMemoria(), EmisorQueFalla(fallas=1)
    turno, _ = _pendiente_encolado(db_session, catalogo, cola)
    worker = armar_worker(db_session, cola, emisor)

    worker.ciclo(PROGRAMADO_PARA)
    worker.ciclo(T1)

    (fila,) = recordatorios_de(db_session, turno.id)
    assert (fila["estado"], fila["intentos"]) == ("enviado", 2)
    assert cola.elementos == {}
    assert len(emisor.enviados) == 1


def test_el_reintento_no_se_entrega_antes_de_su_vencimiento(
    db_session: Session, catalogo: Catalogo
) -> None:
    cola, emisor = ColaEnMemoria(), EmisorQueFalla(fallas=1)
    turno, _ = _pendiente_encolado(db_session, catalogo, cola)
    worker = armar_worker(db_session, cola, emisor)
    worker.ciclo(PROGRAMADO_PARA)

    procesados = worker.ciclo(datetime(2026, 10, 8, 13, 0, 59, tzinfo=UTC))

    assert procesados == 0
    assert emisor.invocaciones == 1
    (fila,) = recordatorios_de(db_session, turno.id)
    assert (fila["estado"], fila["intentos"]) == ("pendiente", 1)


def test_un_error_que_no_viene_del_emisor_se_propaga_y_deja_el_recordatorio_intacto(
    db_session: Session, catalogo: Catalogo
) -> None:
    cola = ColaEnMemoria()
    # Un pendiente con 3 intentos es un dato anómalo: sumarle otro viola el CHECK de la base
    turno, recordatorio_id = _pendiente_encolado(db_session, catalogo, cola, intentos=3)
    db_session.commit()
    worker = armar_worker(db_session, cola, EmisorQueFalla(fallas=10))

    with pytest.raises(IntegrityError) as excinfo:
        worker.ciclo(PROGRAMADO_PARA)

    assert excinfo.value.orig.diag.constraint_name == "ck_recordatorio_intentos_rango"  # type: ignore[union-attr]
    (fila,) = recordatorios_de(db_session, turno.id)
    assert (fila["id"], fila["estado"], fila["intentos"]) == (recordatorio_id, "pendiente", 3)


def test_un_fallo_del_emisor_no_impide_procesar_el_resto_del_ciclo(
    db_session: Session, catalogo: Catalogo
) -> None:
    cola = ColaEnMemoria()
    turno_a, _ = _pendiente_encolado(db_session, catalogo, cola)
    otro = crear_sin_programar(
        db_session,
        catalogo,
        datetime(2026, 10, 9, 15, 0, tzinfo=UTC),
        paciente=1,
    )
    otro_id = insertar_recordatorio(db_session, otro.id)
    cola.encolar(otro_id, PROGRAMADO_PARA.replace(minute=1))
    emisor = EmisorQueFalla(fallas=1)

    armar_worker(db_session, cola, emisor).ciclo(PROGRAMADO_PARA.replace(minute=5))

    (fila_a,) = recordatorios_de(db_session, turno_a.id)
    (fila_otro,) = recordatorios_de(db_session, otro.id)
    assert (fila_a["estado"], fila_a["intentos"]) == ("pendiente", 1)
    assert (fila_otro["estado"], fila_otro["intentos"]) == ("enviado", 1)
