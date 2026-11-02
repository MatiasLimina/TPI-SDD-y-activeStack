"""turno_auditoria es append-only: la base rechaza UPDATE, DELETE y TRUNCATE (ni la app puede)."""

from datetime import UTC, datetime
from typing import Any

import pytest
from sqlalchemy import delete, insert, select, text, update
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from app.infrastructure.db.models import TurnoAuditoria, Usuario
from tests.integration.factories import crear_catalogo, crear_turno

MENSAJE = "turno_auditoria es append-only"
OCURRIDO_EN = datetime(2026, 10, 7, 12, 0, tzinfo=UTC)
NUEVOS = {"estado": "cancelado", "motivo_cancelacion": None}


@pytest.fixture
def registro(db_session: Session, recepcionista: Usuario) -> TurnoAuditoria:
    """Un registro `cancelar` insertado directamente (la inserción sí está permitida)."""
    turno = crear_turno(db_session, crear_catalogo(db_session))
    with db_session.begin_nested():
        db_session.execute(
            insert(TurnoAuditoria).values(
                turno_id=turno.id,
                usuario_id=recepcionista.id,
                accion="cancelar",
                valores_previos={"estado": "programado", "motivo_cancelacion": None},
                valores_nuevos=NUEVOS,
                ocurrido_en=OCURRIDO_EN,
            )
        )
    return db_session.execute(select(TurnoAuditoria)).scalar_one()


@pytest.fixture
def otro_usuario(db_session: Session) -> Usuario:
    usuario = Usuario(
        email="otra.recepcion@example.com", password_hash="hash-ficticio", rol="recepcionista"
    )
    db_session.add(usuario)
    db_session.flush()
    return usuario


def _rechazada(session: Session, sentencia: Any) -> DBAPIError:
    with pytest.raises(DBAPIError) as excinfo:
        with session.begin_nested():
            session.execute(sentencia)
    return excinfo.value


def _fila_actual(session: Session, registro_id: int) -> tuple[Any, ...]:
    # Consulta SQL directa: evita que el identity map de la sesión devuelva valores en caché
    return tuple(
        session.execute(
            text("SELECT usuario_id, valores_nuevos, accion FROM turno_auditoria WHERE id = :id"),
            {"id": registro_id},
        ).one()
    )


def test_update_del_usuario_id_es_rechazado_y_el_registro_conserva_su_autor(
    db_session: Session, registro: TurnoAuditoria, otro_usuario: Usuario
) -> None:
    antes = _fila_actual(db_session, registro.id)

    error = _rechazada(
        db_session,
        update(TurnoAuditoria)
        .where(TurnoAuditoria.id == registro.id)
        .values(usuario_id=otro_usuario.id),
    )

    assert MENSAJE in str(error.orig)
    assert _fila_actual(db_session, registro.id) == antes


def test_update_de_valores_nuevos_es_rechazado_y_el_registro_conserva_sus_valores(
    db_session: Session, registro: TurnoAuditoria
) -> None:
    antes = _fila_actual(db_session, registro.id)

    error = _rechazada(
        db_session,
        update(TurnoAuditoria)
        .where(TurnoAuditoria.id == registro.id)
        .values(valores_nuevos={"estado": "programado"}),
    )

    assert MENSAJE in str(error.orig)
    assert _fila_actual(db_session, registro.id) == antes
    assert antes[1] == NUEVOS


def test_delete_de_la_fila_es_rechazado_y_el_registro_sigue_existiendo(
    db_session: Session, registro: TurnoAuditoria
) -> None:
    error = _rechazada(db_session, delete(TurnoAuditoria).where(TurnoAuditoria.id == registro.id))

    assert MENSAJE in str(error.orig)
    assert _fila_actual(db_session, registro.id)[2] == "cancelar"


def test_delete_sin_where_es_rechazado_aunque_afecte_a_toda_la_tabla(
    db_session: Session, registro: TurnoAuditoria
) -> None:
    error = _rechazada(db_session, delete(TurnoAuditoria))

    assert MENSAJE in str(error.orig)
    assert db_session.execute(text("SELECT count(*) FROM turno_auditoria")).scalar_one() == 1


def test_truncate_de_la_tabla_es_rechazado_y_los_registros_siguen_existiendo(
    db_session: Session, registro: TurnoAuditoria
) -> None:
    error = _rechazada(db_session, text("TRUNCATE turno_auditoria"))

    assert MENSAJE in str(error.orig)
    assert db_session.execute(text("SELECT count(*) FROM turno_auditoria")).scalar_one() == 1


def test_truncate_de_turno_en_cascada_tambien_es_rechazado(
    db_session: Session, registro: TurnoAuditoria
) -> None:
    """Vaciar `turno` con CASCADE arrastraría la auditoría: el trigger también lo frena."""
    error = _rechazada(db_session, text("TRUNCATE turno CASCADE"))

    assert MENSAJE in str(error.orig)
    assert db_session.execute(text("SELECT count(*) FROM turno_auditoria")).scalar_one() == 1
