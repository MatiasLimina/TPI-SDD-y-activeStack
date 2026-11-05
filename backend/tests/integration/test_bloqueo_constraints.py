"""Garantía del bloqueo en PostgreSQL: escritura directa, sin pasar por la aplicación."""

from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.infrastructure.db.models import Bloqueo, Profesional, Usuario

SQLSTATE_CHECK = "23514"
SQLSTATE_NOT_NULL = "23502"
SQLSTATE_FK = "23503"

INICIO = datetime(2026, 10, 8, 13, 0, tzinfo=UTC)
FIN = datetime(2026, 10, 8, 15, 0, tzinfo=UTC)


@pytest.fixture
def profesional(db_session: Session) -> Profesional:
    profesional = Profesional(nombre="Ana", apellido="Ficticia")
    db_session.add(profesional)
    db_session.flush()
    return profesional


def _bloqueo(
    profesional_id: UUID,
    creado_por: UUID | None,
    *,
    inicio: datetime = INICIO,
    fin: datetime = FIN,
    motivo: str = "Congreso",
) -> Bloqueo:
    return Bloqueo(
        profesional_id=profesional_id,
        inicio=inicio,
        fin=fin,
        motivo=motivo,
        creado_por=creado_por,  # type: ignore[arg-type]  # None a propósito: lo rechaza la base
    )


def _rechazado(db_session: Session, bloqueo: Bloqueo) -> IntegrityError:
    with pytest.raises(IntegrityError) as excinfo, db_session.begin_nested():
        db_session.add(bloqueo)
        db_session.flush()
    return excinfo.value


def _contar(db_session: Session) -> int:
    return db_session.scalar(select(func.count()).select_from(Bloqueo)) or 0


def test_la_base_rechaza_un_bloqueo_con_fin_igual_al_inicio(
    db_session: Session, profesional: Profesional, recepcionista: Usuario
) -> None:
    error = _rechazado(db_session, _bloqueo(profesional.id, recepcionista.id, fin=INICIO))

    assert getattr(error.orig, "sqlstate", None) == SQLSTATE_CHECK
    assert error.orig.diag.constraint_name == "ck_bloqueo_fin_mayor"  # type: ignore[union-attr]


def test_la_base_rechaza_un_bloqueo_con_fin_anterior_al_inicio(
    db_session: Session, profesional: Profesional, recepcionista: Usuario
) -> None:
    error = _rechazado(
        db_session, _bloqueo(profesional.id, recepcionista.id, inicio=FIN, fin=INICIO)
    )

    assert error.orig.diag.constraint_name == "ck_bloqueo_fin_mayor"  # type: ignore[union-attr]


@pytest.mark.parametrize("motivo", ["", "   "])
def test_la_base_rechaza_un_motivo_vacio_o_solo_espacios(
    db_session: Session, profesional: Profesional, recepcionista: Usuario, motivo: str
) -> None:
    error = _rechazado(db_session, _bloqueo(profesional.id, recepcionista.id, motivo=motivo))

    assert getattr(error.orig, "sqlstate", None) == SQLSTATE_CHECK
    assert error.orig.diag.constraint_name == "ck_bloqueo_motivo_no_vacio"  # type: ignore[union-attr]


def test_la_base_rechaza_un_bloqueo_sin_autor(
    db_session: Session, profesional: Profesional
) -> None:
    error = _rechazado(db_session, _bloqueo(profesional.id, None))

    assert getattr(error.orig, "sqlstate", None) == SQLSTATE_NOT_NULL


def test_la_base_rechaza_un_profesional_inexistente(
    db_session: Session, recepcionista: Usuario
) -> None:
    error = _rechazado(db_session, _bloqueo(uuid4(), recepcionista.id))

    assert getattr(error.orig, "sqlstate", None) == SQLSTATE_FK
    assert error.orig.diag.constraint_name == "fk_bloqueo_profesional_id_profesional"  # type: ignore[union-attr]


def test_la_base_rechaza_un_autor_que_no_es_un_usuario(
    db_session: Session, profesional: Profesional
) -> None:
    error = _rechazado(db_session, _bloqueo(profesional.id, uuid4()))

    assert getattr(error.orig, "sqlstate", None) == SQLSTATE_FK
    assert error.orig.diag.constraint_name == "fk_bloqueo_creado_por_usuario"  # type: ignore[union-attr]


def test_la_base_acepta_un_bloqueo_valido_y_guarda_los_instantes_en_utc(
    db_session: Session, profesional: Profesional, recepcionista: Usuario
) -> None:
    db_session.add(_bloqueo(profesional.id, recepcionista.id))
    db_session.flush()

    guardado = db_session.scalars(select(Bloqueo)).one()
    db_session.refresh(guardado)

    assert (guardado.inicio, guardado.fin, guardado.motivo) == (INICIO, FIN, "Congreso")
    assert guardado.inicio.utcoffset() is not None
    assert guardado.creado_por == recepcionista.id


def test_borrar_el_profesional_borra_sus_bloqueos_y_no_los_de_otro(
    db_session: Session, profesional: Profesional, recepcionista: Usuario
) -> None:
    otro = Profesional(nombre="Beto", apellido="Ficticio")
    db_session.add(otro)
    db_session.flush()
    db_session.add_all(
        [
            _bloqueo(profesional.id, recepcionista.id),
            _bloqueo(
                profesional.id, recepcionista.id, inicio=FIN, fin=datetime(2026, 10, 9, tzinfo=UTC)
            ),
            _bloqueo(otro.id, recepcionista.id),
        ]
    )
    db_session.flush()

    db_session.delete(profesional)
    db_session.flush()

    restantes = db_session.scalars(select(Bloqueo)).all()
    assert [b.profesional_id for b in restantes] == [otro.id]
    assert _contar(db_session) == 1


def test_no_se_puede_borrar_el_usuario_autor_de_un_bloqueo(
    db_session: Session, profesional: Profesional, recepcionista: Usuario
) -> None:
    db_session.add(_bloqueo(profesional.id, recepcionista.id))
    db_session.flush()

    with pytest.raises(IntegrityError) as excinfo, db_session.begin_nested():
        db_session.delete(recepcionista)
        db_session.flush()

    assert getattr(excinfo.value.orig, "sqlstate", None) == SQLSTATE_FK
