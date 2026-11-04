"""Integridad de recordatorio garantizada por PostgreSQL (escritura directa, sin la app)."""

import uuid
from datetime import UTC, datetime
from typing import Any

import pytest
from sqlalchemy import delete, insert, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.infrastructure.db.models import Recordatorio, Turno
from tests.integration.factories import crear_catalogo, crear_turno

CHECK = "23514"
NOT_NULL = "23502"
FK = "23503"
UNICIDAD = "23505"
PROGRAMADO_PARA = datetime(2026, 10, 7, 13, 0, tzinfo=UTC)


@pytest.fixture
def turno(db_session: Session) -> Turno:
    return crear_turno(db_session, crear_catalogo(db_session))


def _fila(turno: Turno, **campos: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "turno_id": turno.id,
        "programado_para": PROGRAMADO_PARA,
        "estado": "pendiente",
        "canal": "mock",
        "intentos": 0,
    }
    return base | campos


def _insertar(session: Session, fila: dict[str, Any]) -> None:
    with session.begin_nested():
        session.execute(insert(Recordatorio).values(**fila))


def _rechazo(session: Session, fila: dict[str, Any]) -> IntegrityError:
    with pytest.raises(IntegrityError) as excinfo:
        _insertar(session, fila)
    return excinfo.value


def test_insercion_directa_valida_es_aceptada(db_session: Session, turno: Turno) -> None:
    _insertar(db_session, _fila(turno))

    guardado = db_session.execute(select(Recordatorio)).scalar_one()
    assert guardado.turno_id == turno.id
    assert guardado.estado == "pendiente"
    assert guardado.canal == "mock"
    assert guardado.intentos == 0
    assert guardado.programado_para == PROGRAMADO_PARA


def test_estado_e_intentos_omitidos_toman_los_defaults(db_session: Session, turno: Turno) -> None:
    fila = _fila(turno)
    del fila["estado"], fila["intentos"]

    _insertar(db_session, fila)

    guardado = db_session.execute(select(Recordatorio)).scalar_one()
    assert (guardado.estado, guardado.intentos) == ("pendiente", 0)


@pytest.mark.parametrize(
    ("campos", "constraint"),
    [
        ({"estado": "borrador"}, "ck_recordatorio_estado_valido"),
        ({"estado": "PENDIENTE"}, "ck_recordatorio_estado_valido"),
        ({"canal": "whatsapp"}, "ck_recordatorio_canal_valido"),
        ({"intentos": 4}, "ck_recordatorio_intentos_rango"),
        ({"intentos": -1}, "ck_recordatorio_intentos_rango"),
        ({"estado": "fallido", "intentos": 2}, "ck_recordatorio_intentos_segun_estado"),
        ({"estado": "fallido", "intentos": 0}, "ck_recordatorio_intentos_segun_estado"),
        ({"estado": "enviado", "intentos": 0}, "ck_recordatorio_intentos_segun_estado"),
        ({"estado": "pendiente", "intentos": 3}, "ck_recordatorio_pendiente_intentos"),
    ],
    ids=[
        "estado-borrador",
        "estado-mayusculas",
        "canal-whatsapp",
        "intentos-4",
        "intentos-menos-1",
        "fallido-con-2",
        "fallido-con-0",
        "enviado-con-0",
        "pendiente-con-3",
    ],
)
def test_check_rechaza_valores_invalidos_e_incoherentes(
    db_session: Session, turno: Turno, campos: dict[str, Any], constraint: str
) -> None:
    error = _rechazo(db_session, _fila(turno, **campos))

    assert error.orig.sqlstate == CHECK
    assert error.orig.diag.constraint_name == constraint


@pytest.mark.parametrize(
    "campos",
    [
        {"estado": "fallido", "intentos": 3},
        {"estado": "enviado", "intentos": 1},
        {"estado": "enviado", "intentos": 3},
        {"estado": "cancelado", "intentos": 0},
        {"estado": "pendiente", "intentos": 2},
    ],
    ids=["fallido-3", "enviado-1", "enviado-3", "cancelado-0", "pendiente-2"],
)
def test_check_acepta_combinaciones_coherentes_de_estado_e_intentos(
    db_session: Session, turno: Turno, campos: dict[str, Any]
) -> None:
    _insertar(db_session, _fila(turno, **campos))

    assert db_session.execute(select(Recordatorio.estado)).scalar_one() == campos["estado"]


@pytest.mark.parametrize("columna", ["programado_para", "canal", "turno_id"])
def test_columnas_obligatorias_nulas_son_rechazadas_por_not_null(
    db_session: Session, turno: Turno, columna: str
) -> None:
    error = _rechazo(db_session, _fila(turno, **{columna: None}))

    assert error.orig.sqlstate == NOT_NULL
    assert error.orig.diag.column_name == columna


def test_programado_para_omitido_es_rechazado_porque_no_tiene_default(
    db_session: Session, turno: Turno
) -> None:
    fila = _fila(turno)
    del fila["programado_para"]

    error = _rechazo(db_session, fila)

    assert error.orig.sqlstate == NOT_NULL
    assert error.orig.diag.column_name == "programado_para"


def test_turno_inexistente_es_rechazado_por_fk(db_session: Session, turno: Turno) -> None:
    error = _rechazo(db_session, _fila(turno, turno_id=uuid.uuid4()))

    assert error.orig.sqlstate == FK
    assert error.orig.diag.constraint_name == "fk_recordatorio_turno_id_turno"


def test_borrar_un_turno_con_recordatorio_es_rechazado_por_fk(
    db_session: Session, turno: Turno
) -> None:
    _insertar(db_session, _fila(turno))

    with pytest.raises(IntegrityError) as excinfo:
        with db_session.begin_nested():
            db_session.execute(delete(Turno).where(Turno.id == turno.id))

    assert excinfo.value.orig.sqlstate == FK
    assert excinfo.value.orig.diag.constraint_name == "fk_recordatorio_turno_id_turno"


def test_segundo_pendiente_para_el_mismo_turno_es_rechazado_por_unicidad(
    db_session: Session, turno: Turno
) -> None:
    _insertar(db_session, _fila(turno))

    error = _rechazo(db_session, _fila(turno))

    assert error.orig.sqlstate == UNICIDAD
    assert error.orig.diag.constraint_name == "ux_recordatorio_turno_pendiente"


def test_pendientes_de_turnos_distintos_son_aceptados(db_session: Session, turno: Turno) -> None:
    otro = crear_turno(db_session, crear_catalogo(db_session), desplazamiento_min=120)
    _insertar(db_session, _fila(turno))

    _insertar(db_session, _fila(otro))

    assert len(db_session.execute(select(Recordatorio)).scalars().all()) == 2


def test_historicos_mas_un_pendiente_son_aceptados(db_session: Session, turno: Turno) -> None:
    _insertar(db_session, _fila(turno, estado="cancelado"))
    _insertar(db_session, _fila(turno, estado="cancelado"))
    _insertar(db_session, _fila(turno, estado="enviado", intentos=1))
    _insertar(db_session, _fila(turno, estado="fallido", intentos=3))

    _insertar(db_session, _fila(turno))

    estados = db_session.execute(select(Recordatorio.estado)).scalars().all()
    assert sorted(estados) == ["cancelado", "cancelado", "enviado", "fallido", "pendiente"]


def test_pasar_un_pendiente_a_cancelado_libera_el_lugar_para_otro_pendiente(
    db_session: Session, turno: Turno
) -> None:
    _insertar(db_session, _fila(turno))
    db_session.execute(
        update(Recordatorio).where(Recordatorio.turno_id == turno.id).values(estado="cancelado")
    )

    _insertar(db_session, _fila(turno))

    estados = db_session.execute(select(Recordatorio.estado)).scalars().all()
    assert sorted(estados) == ["cancelado", "pendiente"]


def _actualizar(session: Session, turno: Turno, **valores: Any) -> None:
    with session.begin_nested():
        session.execute(
            update(Recordatorio).where(Recordatorio.turno_id == turno.id).values(**valores)
        )


def test_un_pendiente_no_llega_a_3_intentos_sin_cambiar_de_estado(
    db_session: Session, turno: Turno
) -> None:
    _insertar(db_session, _fila(turno, intentos=2))

    with pytest.raises(IntegrityError) as excinfo:
        _actualizar(db_session, turno, intentos=3)

    assert excinfo.value.orig.sqlstate == CHECK
    assert excinfo.value.orig.diag.constraint_name == "ck_recordatorio_pendiente_intentos"
    assert db_session.execute(select(Recordatorio.intentos)).scalar_one() == 2


def test_un_pendiente_con_2_intentos_pasa_a_3_si_pasa_a_fallido(
    db_session: Session, turno: Turno
) -> None:
    _insertar(db_session, _fila(turno, intentos=2))

    _actualizar(db_session, turno, intentos=3, estado="fallido")

    fila = db_session.execute(select(Recordatorio.estado, Recordatorio.intentos)).one()
    assert tuple(fila) == ("fallido", 3)
