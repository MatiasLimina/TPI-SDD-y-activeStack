"""Integridad de turno_auditoria garantizada por PostgreSQL (escritura directa, sin la app)."""

import uuid
from datetime import UTC, datetime
from typing import Any

import pytest
from sqlalchemy import delete, insert, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.infrastructure.db.models import Turno, TurnoAuditoria, Usuario
from tests.integration.factories import crear_catalogo, crear_turno

CHECK = "23514"
NOT_NULL = "23502"
FK = "23503"
OCURRIDO_EN = datetime(2026, 10, 7, 12, 0, tzinfo=UTC)
INSTANTANEA = {
    "estado": "programado",
    "duracion_min": 45,
    "motivo_cancelacion": None,
}


@pytest.fixture
def turno(db_session: Session) -> Turno:
    return crear_turno(db_session, crear_catalogo(db_session))


def _fila(turno: Turno, usuario: Usuario, **campos: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "turno_id": turno.id,
        "usuario_id": usuario.id,
        "accion": "cancelar",
        "valores_previos": INSTANTANEA,
        "valores_nuevos": INSTANTANEA | {"estado": "cancelado"},
        "ocurrido_en": OCURRIDO_EN,
    }
    return base | campos


def _insertar(session: Session, fila: dict[str, Any]) -> None:
    with session.begin_nested():
        session.execute(insert(TurnoAuditoria).values(**fila))


def _rechazo(session: Session, fila: dict[str, Any]) -> IntegrityError:
    with pytest.raises(IntegrityError) as excinfo:
        _insertar(session, fila)
    return excinfo.value


def test_insercion_directa_valida_de_un_cancelar_es_aceptada(
    db_session: Session, turno: Turno, recepcionista: Usuario
) -> None:
    _insertar(db_session, _fila(turno, recepcionista))

    guardado = db_session.execute(select(TurnoAuditoria)).scalar_one()
    assert guardado.turno_id == turno.id
    assert guardado.usuario_id == recepcionista.id
    assert guardado.accion == "cancelar"
    assert guardado.ocurrido_en == OCURRIDO_EN
    assert guardado.valores_nuevos["estado"] == "cancelado"


def test_insercion_valida_de_un_crear_con_valores_previos_nulos_es_aceptada(
    db_session: Session, turno: Turno, recepcionista: Usuario
) -> None:
    _insertar(db_session, _fila(turno, recepcionista, accion="crear", valores_previos=None))

    guardado = db_session.execute(select(TurnoAuditoria)).scalar_one()
    assert guardado.accion == "crear"
    assert guardado.valores_previos is None


@pytest.mark.parametrize(
    ("campos", "constraint"),
    [
        ({"accion": "borrar"}, "ck_turno_auditoria_accion_valida"),
        ({"accion": "CREAR", "valores_previos": None}, "ck_turno_auditoria_accion_valida"),
        ({"accion": "crear"}, "ck_turno_auditoria_previos_segun_accion"),
        (
            {"accion": "reprogramar", "valores_previos": None},
            "ck_turno_auditoria_previos_segun_accion",
        ),
        (
            {"accion": "cancelar", "valores_previos": None},
            "ck_turno_auditoria_previos_segun_accion",
        ),
    ],
    ids=[
        "accion-borrar",
        "accion-mayusculas",
        "crear-con-previos",
        "reprogramar-sin-previos",
        "cancelar-sin-previos",
    ],
)
def test_check_rechaza_acciones_invalidas_y_previos_incoherentes(
    db_session: Session,
    turno: Turno,
    recepcionista: Usuario,
    campos: dict[str, Any],
    constraint: str,
) -> None:
    error = _rechazo(db_session, _fila(turno, recepcionista, **campos))

    assert error.orig.sqlstate == CHECK
    assert error.orig.diag.constraint_name == constraint


@pytest.mark.parametrize("columna", ["valores_nuevos", "ocurrido_en"])
def test_valores_nuevos_y_ocurrido_en_nulos_son_rechazados_por_not_null(
    db_session: Session, turno: Turno, recepcionista: Usuario, columna: str
) -> None:
    error = _rechazo(db_session, _fila(turno, recepcionista, **{columna: None}))

    assert error.orig.sqlstate == NOT_NULL
    assert error.orig.diag.column_name == columna


def test_ocurrido_en_omitido_es_rechazado_porque_no_tiene_default(
    db_session: Session, turno: Turno, recepcionista: Usuario
) -> None:
    fila = _fila(turno, recepcionista)
    del fila["ocurrido_en"]

    error = _rechazo(db_session, fila)

    assert error.orig.sqlstate == NOT_NULL
    assert error.orig.diag.column_name == "ocurrido_en"


@pytest.mark.parametrize(
    ("columna", "constraint"),
    [
        ("turno_id", "fk_turno_auditoria_turno_id_turno"),
        ("usuario_id", "fk_turno_auditoria_usuario_id_usuario"),
    ],
)
def test_turno_o_usuario_inexistentes_son_rechazados_por_fk(
    db_session: Session, turno: Turno, recepcionista: Usuario, columna: str, constraint: str
) -> None:
    error = _rechazo(db_session, _fila(turno, recepcionista, **{columna: uuid.uuid4()}))

    assert error.orig.sqlstate == FK
    assert error.orig.diag.constraint_name == constraint


def test_borrar_un_turno_auditado_es_rechazado_por_fk(
    db_session: Session, turno: Turno, recepcionista: Usuario
) -> None:
    _insertar(db_session, _fila(turno, recepcionista))

    with pytest.raises(IntegrityError) as excinfo:
        with db_session.begin_nested():
            db_session.execute(delete(Turno).where(Turno.id == turno.id))

    assert excinfo.value.orig.sqlstate == FK
    assert excinfo.value.orig.diag.constraint_name == "fk_turno_auditoria_turno_id_turno"


def test_borrar_un_usuario_autor_de_registros_es_rechazado_por_fk(
    db_session: Session, turno: Turno, recepcionista: Usuario
) -> None:
    _insertar(db_session, _fila(turno, recepcionista))

    with pytest.raises(IntegrityError) as excinfo:
        with db_session.begin_nested():
            db_session.execute(delete(Usuario).where(Usuario.id == recepcionista.id))

    assert excinfo.value.orig.sqlstate == FK
    assert excinfo.value.orig.diag.constraint_name == "fk_turno_auditoria_usuario_id_usuario"


def test_borrar_un_turno_sin_registros_de_auditoria_es_aceptado(
    db_session: Session, turno: Turno
) -> None:
    with db_session.begin_nested():
        db_session.execute(delete(Turno).where(Turno.id == turno.id))

    assert db_session.get(Turno, turno.id) is None
