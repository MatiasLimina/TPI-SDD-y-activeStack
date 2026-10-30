"""RepositorioAuditoria: persiste con flush y lista por turno en orden de inserción."""

from datetime import UTC, datetime, timedelta, timezone
from uuid import uuid4

import pytest
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.domain.auditoria import AccionAuditoria, RegistroAuditoria
from app.infrastructure.db.models import Turno, TurnoAuditoria, Usuario
from app.infrastructure.db.repositorio_auditoria import RepositorioAuditoria
from tests.integration.factories import Catalogo, crear_catalogo, crear_turno

OCURRIDO_EN = datetime(2026, 10, 7, 12, 0, tzinfo=UTC)
PREVIOS = {"estado": "programado", "motivo_cancelacion": None}
NUEVOS = {"estado": "cancelado", "motivo_cancelacion": "Aviso del paciente"}


@pytest.fixture
def catalogo(db_session: Session) -> Catalogo:
    return crear_catalogo(db_session)


@pytest.fixture
def turno(db_session: Session, catalogo: Catalogo) -> Turno:
    return crear_turno(db_session, catalogo)


def _total(session: Session) -> int:
    return session.execute(select(func.count()).select_from(TurnoAuditoria)).scalar_one()


def test_registrar_persiste_la_fila_con_flush_sin_commit(
    db_session: Session, turno: Turno, recepcionista: Usuario
) -> None:
    repo = RepositorioAuditoria(db_session)

    repo.registrar(
        turno.id, recepcionista.id, AccionAuditoria.CANCELAR, PREVIOS, NUEVOS, OCURRIDO_EN
    )

    assert not db_session.new  # ya se envió a la base: un error de integridad salta acá
    fila = db_session.execute(select(TurnoAuditoria)).scalar_one()
    assert fila.turno_id == turno.id
    assert fila.usuario_id == recepcionista.id
    assert fila.accion == "cancelar"
    assert fila.valores_previos == PREVIOS
    assert fila.valores_nuevos == NUEVOS
    assert fila.ocurrido_en == OCURRIDO_EN


def test_registrar_un_crear_guarda_valores_previos_como_null_de_sql(
    db_session: Session, turno: Turno, recepcionista: Usuario
) -> None:
    repo = RepositorioAuditoria(db_session)

    repo.registrar(turno.id, recepcionista.id, AccionAuditoria.CREAR, None, PREVIOS, OCURRIDO_EN)

    registro = repo.listar_por_turno(turno.id)[0]
    assert registro.valores_previos is None
    assert registro.accion is AccionAuditoria.CREAR


def test_registrar_con_un_usuario_inexistente_falla_en_el_flush_con_error_de_integridad(
    db_session: Session, turno: Turno
) -> None:
    repo = RepositorioAuditoria(db_session)

    with pytest.raises(IntegrityError):
        with db_session.begin_nested():
            repo.registrar(turno.id, uuid4(), AccionAuditoria.CREAR, None, NUEVOS, OCURRIDO_EN)

    assert _total(db_session) == 0


def test_listar_por_turno_devuelve_registros_de_dominio_en_orden_de_insercion_con_instantes_iguales(
    db_session: Session, turno: Turno, recepcionista: Usuario
) -> None:
    repo = RepositorioAuditoria(db_session)
    for accion, previos in (
        (AccionAuditoria.CREAR, None),
        (AccionAuditoria.REPROGRAMAR, PREVIOS),
        (AccionAuditoria.CANCELAR, PREVIOS),
    ):
        repo.registrar(turno.id, recepcionista.id, accion, previos, NUEVOS, OCURRIDO_EN)

    registros = repo.listar_por_turno(turno.id)

    assert [r.accion for r in registros] == ["crear", "reprogramar", "cancelar"]
    assert all(isinstance(r, RegistroAuditoria) for r in registros)
    ids = [r.id for r in registros]
    assert ids == sorted(ids)
    assert len(set(ids)) == 3
    assert all(r.turno_id == turno.id and r.usuario_id == recepcionista.id for r in registros)
    assert registros[0].valores_previos is None
    assert registros[1].valores_previos == PREVIOS
    assert registros[2].valores_nuevos == NUEVOS


def test_listar_por_turno_devuelve_ocurrido_en_en_utc_aunque_se_registre_con_otra_zona(
    db_session: Session, turno: Turno, recepcionista: Usuario
) -> None:
    repo = RepositorioAuditoria(db_session)
    en_buenos_aires = datetime(2026, 10, 7, 9, 0, tzinfo=timezone(timedelta(hours=-3)))

    repo.registrar(turno.id, recepcionista.id, AccionAuditoria.CREAR, None, NUEVOS, en_buenos_aires)

    registro = repo.listar_por_turno(turno.id)[0]
    assert registro.ocurrido_en == OCURRIDO_EN
    assert registro.ocurrido_en.utcoffset() == timedelta(0)


def test_listar_por_turno_devuelve_solo_los_registros_del_turno_pedido(
    db_session: Session, catalogo: Catalogo, turno: Turno, recepcionista: Usuario
) -> None:
    otro = crear_turno(db_session, catalogo, desplazamiento_min=120)
    repo = RepositorioAuditoria(db_session)
    repo.registrar(turno.id, recepcionista.id, AccionAuditoria.CREAR, None, NUEVOS, OCURRIDO_EN)
    repo.registrar(otro.id, recepcionista.id, AccionAuditoria.CREAR, None, NUEVOS, OCURRIDO_EN)
    repo.registrar(
        otro.id, recepcionista.id, AccionAuditoria.CANCELAR, PREVIOS, NUEVOS, OCURRIDO_EN
    )

    assert [r.accion for r in repo.listar_por_turno(turno.id)] == ["crear"]
    assert [r.accion for r in repo.listar_por_turno(otro.id)] == ["crear", "cancelar"]


def test_listar_por_turno_sin_registros_devuelve_lista_vacia(
    db_session: Session, turno: Turno
) -> None:
    assert RepositorioAuditoria(db_session).listar_por_turno(turno.id) == []
    assert RepositorioAuditoria(db_session).listar_por_turno(uuid4()) == []


def test_el_repositorio_solo_expone_registrar_y_listar_por_turno() -> None:
    publicos = {n for n in dir(RepositorioAuditoria) if not n.startswith("_")}

    assert publicos == {"registrar", "listar_por_turno"}
