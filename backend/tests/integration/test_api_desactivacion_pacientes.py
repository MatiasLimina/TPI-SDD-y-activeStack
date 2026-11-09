"""Desactivar pacientes y su efecto en los turnos: app real, PostgreSQL real, reloj fijo."""

from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.turnos import get_reloj
from app.infrastructure.db.models import Paciente, Turno, TurnoAuditoria
from tests.fakes import ColaEnMemoria, EmisorQueRegistra, RelojManual
from tests.integration.factories import Catalogo, crear_catalogo
from tests.integration.helpers_recordatorios import armar_worker, ciclo_a, recordatorios_de

AHORA = datetime(2026, 10, 7, 12, 0, tzinfo=UTC)  # 2026-10-07 09:00 hora local
INICIO_LOCAL = "2026-10-08T10:00:00-03:00"
INICIO = datetime(2026, 10, 8, 13, 0, tzinfo=UTC)
CUERPO_404 = {"detail": {"codigo": "recurso_inexistente", "recurso": "paciente"}}
CUERPO_INACTIVA = {
    "detail": {"codigo": "referencia_invalida", "referencia": "paciente", "motivo": "inactiva"}
}


@pytest.fixture
def catalogo(db_session: Session) -> Catalogo:
    return crear_catalogo(db_session)


@pytest.fixture
def api(client: TestClient) -> TestClient:
    client.app.dependency_overrides[get_reloj] = lambda: lambda: AHORA  # type: ignore[attr-defined]
    return client


def _body_turno(c: Catalogo, **cambios: Any) -> dict[str, Any]:
    body: dict[str, Any] = {
        "profesional_id": str(c.profesionales[0].id),
        "paciente_id": str(c.pacientes[0].id),
        "prestacion_id": str(c.limpieza.id),
        "sillon_id": str(c.sillones[0].id),
        "inicio": INICIO_LOCAL,
    }
    body.update(cambios)
    return body


def _crear_turno(api: TestClient, c: Catalogo, **cambios: Any) -> str:
    respuesta = api.post("/turnos", json=_body_turno(c, **cambios))
    assert respuesta.status_code == 201, respuesta.text
    return respuesta.json()["id"]


def _desactivar(api: TestClient, paciente_id: UUID) -> None:
    respuesta = api.post(f"/pacientes/{paciente_id}/desactivar")
    assert respuesta.status_code == 200, respuesta.text


def _paciente(session: Session, paciente_id: UUID) -> Paciente:
    session.expire_all()
    return session.execute(select(Paciente).where(Paciente.id == paciente_id)).scalar_one()


def _turno(session: Session, turno_id: str) -> Turno:
    session.expire_all()
    return session.execute(select(Turno).where(Turno.id == UUID(turno_id))).scalar_one()


def _contar(session: Session, modelo: type) -> int:
    session.expire_all()
    return session.scalar(select(func.count()).select_from(modelo)) or 0


# --- Desactivación lógica de un paciente --------------------------------------------------


def test_desactivar_marca_al_paciente_inactivo_y_conserva_la_fila_y_sus_datos(
    api: TestClient, db_session: Session, catalogo: Catalogo
) -> None:
    paciente = catalogo.pacientes[0]
    antes = (paciente.nombre, paciente.apellido, paciente.documento, paciente.telefono)

    respuesta = api.post(f"/pacientes/{paciente.id}/desactivar")

    assert respuesta.status_code == 200
    assert respuesta.json()["activo"] is False
    assert respuesta.json()["id"] == str(paciente.id)
    assert set(respuesta.json()) == {
        "id",
        "nombre",
        "apellido",
        "documento",
        "telefono",
        "email",
        "activo",
    }
    guardado = _paciente(db_session, paciente.id)
    assert guardado.activo is False
    assert (guardado.nombre, guardado.apellido, guardado.documento, guardado.telefono) == antes


def test_desactivar_a_uno_no_toca_a_los_demas_pacientes(
    api: TestClient, db_session: Session, catalogo: Catalogo
) -> None:
    _desactivar(api, catalogo.pacientes[0].id)

    assert _paciente(db_session, catalogo.pacientes[1].id).activo is True


def test_desactivar_dos_veces_responde_200_y_no_cambia_nada(
    api: TestClient, db_session: Session, catalogo: Catalogo
) -> None:
    paciente = catalogo.pacientes[0]
    _desactivar(api, paciente.id)
    despues_de_la_primera = _paciente(db_session, paciente.id).actualizado_en

    respuesta = api.post(f"/pacientes/{paciente.id}/desactivar")

    assert respuesta.status_code == 200
    assert respuesta.json()["activo"] is False
    assert _paciente(db_session, paciente.id).actualizado_en == despues_de_la_primera


def test_desactivar_un_paciente_inexistente_responde_404(api: TestClient) -> None:
    respuesta = api.post(f"/pacientes/{uuid4()}/desactivar")

    assert respuesta.status_code == 404
    assert respuesta.json() == CUERPO_404


def test_desactivar_con_id_mal_formado_responde_422(api: TestClient) -> None:
    assert api.post("/pacientes/no-es-un-id/desactivar").status_code == 422


# --- Un paciente desactivado no admite turnos nuevos ----------------------------------------


def test_alta_de_turno_con_un_paciente_desactivado_responde_referencia_inactiva(
    api: TestClient, db_session: Session, catalogo: Catalogo
) -> None:
    _desactivar(api, catalogo.pacientes[0].id)

    respuesta = api.post("/turnos", json=_body_turno(catalogo))

    assert respuesta.status_code == 422
    assert respuesta.json() == CUERPO_INACTIVA
    assert _contar(db_session, Turno) == 0


def test_alta_de_turno_con_otro_paciente_activo_sigue_funcionando(
    api: TestClient, catalogo: Catalogo
) -> None:
    _desactivar(api, catalogo.pacientes[0].id)

    respuesta = api.post(
        "/turnos", json=_body_turno(catalogo, paciente_id=str(catalogo.pacientes[1].id))
    )

    assert respuesta.status_code == 201


def test_reprogramar_el_turno_de_un_paciente_desactivado_responde_referencia_inactiva(
    api: TestClient, db_session: Session, catalogo: Catalogo
) -> None:
    turno_id = _crear_turno(api, catalogo)
    _desactivar(api, catalogo.pacientes[0].id)

    respuesta = api.patch(
        f"/turnos/{turno_id}/reprogramar", json={"inicio": "2026-10-08T11:00:00-03:00"}
    )

    assert respuesta.status_code == 422
    detalle = respuesta.json()["detail"]
    assert (detalle["codigo"], detalle["referencia"]) == ("referencia_invalida", "paciente")
    assert _turno(db_session, turno_id).inicio == INICIO


# --- Un paciente desactivado conserva sus turnos y recordatorios -----------------------------


def test_desactivar_deja_intacto_el_turno_futuro_y_no_registra_auditoria(
    api: TestClient, db_session: Session, catalogo: Catalogo
) -> None:
    turno_id = _crear_turno(api, catalogo)
    auditorias_antes = _contar(db_session, TurnoAuditoria)

    respuesta = api.post(f"/pacientes/{catalogo.pacientes[0].id}/desactivar")

    assert respuesta.status_code == 200
    turno = _turno(db_session, turno_id)
    assert turno.estado == "programado"
    assert turno.paciente_id == catalogo.pacientes[0].id
    assert turno.profesional_id == catalogo.profesionales[0].id
    assert (turno.inicio, turno.fin) == (INICIO, INICIO + timedelta(minutes=45))
    assert _contar(db_session, TurnoAuditoria) == auditorias_antes


def test_desactivar_deja_intacto_un_turno_cancelado_y_uno_pasado(
    api: TestClient, db_session: Session, catalogo: Catalogo
) -> None:
    cancelado = _crear_turno(api, catalogo)
    api.post(f"/turnos/{cancelado}/cancelar", json={"motivo": "Viaje"})

    _desactivar(api, catalogo.pacientes[0].id)

    turno = _turno(db_session, cancelado)
    assert (turno.estado, turno.motivo_cancelacion) == ("cancelado", "Viaje")


def test_el_turno_futuro_de_un_paciente_desactivado_se_puede_cancelar(
    api: TestClient, catalogo: Catalogo
) -> None:
    turno_id = _crear_turno(api, catalogo)
    _desactivar(api, catalogo.pacientes[0].id)

    respuesta = api.post(f"/turnos/{turno_id}/cancelar")

    assert respuesta.status_code == 200
    assert respuesta.json()["estado"] == "cancelado"


def test_el_recordatorio_de_un_paciente_desactivado_sigue_pendiente_y_se_envia_a_su_hora(
    api: TestClient, db_session: Session, catalogo: Catalogo, cola: ColaEnMemoria
) -> None:
    turno_id = _crear_turno(api, catalogo)
    (recordatorio,) = recordatorios_de(db_session, UUID(turno_id))
    assert recordatorio["estado"] == "pendiente"
    programado_para = recordatorio["programado_para"]
    _desactivar(api, catalogo.pacientes[0].id)
    reloj, emisor = RelojManual(AHORA), EmisorQueRegistra()
    worker = armar_worker(db_session, cola, emisor, reloj)

    antes_de_la_hora = ciclo_a(worker, reloj, programado_para - timedelta(minutes=1))
    (sin_enviar,) = recordatorios_de(db_session, UUID(turno_id))
    a_la_hora = ciclo_a(worker, reloj, programado_para)
    (enviado,) = recordatorios_de(db_session, UUID(turno_id))

    assert (antes_de_la_hora, sin_enviar["estado"]) == (0, "pendiente")
    assert (a_la_hora, enviado["estado"]) == (1, "enviado")
    assert len(emisor.enviados) == 1


def test_desactivar_no_cambia_el_recordatorio_pendiente(
    api: TestClient, db_session: Session, catalogo: Catalogo
) -> None:
    turno_id = _crear_turno(api, catalogo)
    (antes,) = recordatorios_de(db_session, UUID(turno_id))

    _desactivar(api, catalogo.pacientes[0].id)

    (despues,) = recordatorios_de(db_session, UUID(turno_id))
    assert despues == antes
