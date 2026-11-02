"""RBAC de las rutas de horarios: app real, PostgreSQL real, tokens reales."""

from datetime import time
from typing import Any
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.infrastructure.db.models import HorarioAtencion, Profesional, Usuario
from app.infrastructure.security.tokens import EmisorTokens

CUERPO_401 = {"detail": {"codigo": "no_autenticado", "mensaje": "No autenticado"}}
CUERPO_403 = {"detail": {"codigo": "rol_insuficiente", "mensaje": "Rol insuficiente"}}
CUERPO_AJENO = {
    "detail": {"codigo": "profesional_ajeno", "mensaje": "Solo podés consultar tu propio horario"}
}
VALIDO = {"dia_semana": 1, "hora_inicio": "09:00", "hora_fin": "13:00"}


@pytest.fixture
def anonimo(client: TestClient, cliente_anonimo: TestClient) -> TestClient:
    return cliente_anonimo


@pytest.fixture
def franja_propia(db_session: Session, odontologo: Usuario) -> HorarioAtencion:
    franja = HorarioAtencion(
        profesional_id=odontologo.profesional_id,
        dia_semana=0,
        hora_inicio=time(9, 0),
        hora_fin=time(13, 0),
    )
    db_session.add(franja)
    db_session.flush()
    return franja


@pytest.fixture
def otro_profesional(db_session: Session) -> Profesional:
    profesional = Profesional(nombre="Beto", apellido="Ficticio")
    db_session.add(profesional)
    db_session.flush()
    return profesional


def _bearer(usuario: Usuario, emisor: EmisorTokens) -> dict[str, str]:
    return {"Authorization": f"Bearer {emisor.emitir(usuario)}"}


def _franjas(session: Session) -> list[tuple[object, int, time, time]]:
    session.expire_all()
    consulta = select(
        HorarioAtencion.profesional_id,
        HorarioAtencion.dia_semana,
        HorarioAtencion.hora_inicio,
        HorarioAtencion.hora_fin,
    ).order_by(HorarioAtencion.dia_semana, HorarioAtencion.hora_inicio)
    return [tuple(f) for f in session.execute(consulta)]  # type: ignore[misc]


def _escrituras(
    odontologo: Usuario, franja: HorarioAtencion
) -> dict[str, tuple[str, str, dict[str, Any]]]:
    base = f"/profesionales/{odontologo.profesional_id}/horarios"
    return {
        "post": ("POST", base, VALIDO),
        "patch": ("PATCH", f"{base}/{franja.id}", {"hora_fin": "14:00"}),
        "delete": ("DELETE", f"{base}/{franja.id}", {}),
    }


@pytest.mark.parametrize("ruta", ["post", "patch", "delete"])
def test_escritura_de_un_odontologo_sobre_su_propio_profesional_responde_403(
    anonimo: TestClient,
    db_session: Session,
    odontologo: Usuario,
    emisor_test: EmisorTokens,
    franja_propia: HorarioAtencion,
    ruta: str,
) -> None:
    metodo, url, cuerpo = _escrituras(odontologo, franja_propia)[ruta]
    antes = _franjas(db_session)

    respuesta = anonimo.request(
        metodo, url, json=cuerpo or None, headers=_bearer(odontologo, emisor_test)
    )

    assert respuesta.status_code == 403
    assert respuesta.json() == CUERPO_403
    assert _franjas(db_session) == antes


@pytest.mark.parametrize("ruta", ["post", "patch", "delete"])
def test_escritura_sin_token_responde_401_y_la_base_no_cambia(
    anonimo: TestClient,
    db_session: Session,
    odontologo: Usuario,
    franja_propia: HorarioAtencion,
    ruta: str,
) -> None:
    metodo, url, cuerpo = _escrituras(odontologo, franja_propia)[ruta]
    antes = _franjas(db_session)

    respuesta = anonimo.request(metodo, url, json=cuerpo or None)

    assert respuesta.status_code == 401
    assert respuesta.json() == CUERPO_401
    assert respuesta.headers["WWW-Authenticate"] == "Bearer"
    assert _franjas(db_session) == antes


def test_odontologo_con_body_invalido_recibe_403_y_no_422(
    anonimo: TestClient, odontologo: Usuario, emisor_test: EmisorTokens
) -> None:
    respuesta = anonimo.post(
        f"/profesionales/{odontologo.profesional_id}/horarios",
        json={"dia_semana": 9},
        headers=_bearer(odontologo, emisor_test),
    )

    assert respuesta.status_code == 403


def test_odontologo_borrando_uuids_inexistentes_recibe_403_y_no_404(
    anonimo: TestClient, odontologo: Usuario, emisor_test: EmisorTokens
) -> None:
    respuesta = anonimo.delete(
        f"/profesionales/{uuid4()}/horarios/{uuid4()}", headers=_bearer(odontologo, emisor_test)
    )

    assert respuesta.status_code == 403


def test_odontologo_lee_su_propio_horario(
    anonimo: TestClient,
    odontologo: Usuario,
    emisor_test: EmisorTokens,
    franja_propia: HorarioAtencion,
) -> None:
    respuesta = anonimo.get(
        f"/profesionales/{odontologo.profesional_id}/horarios",
        headers=_bearer(odontologo, emisor_test),
    )

    assert respuesta.status_code == 200
    assert [f["id"] for f in respuesta.json()] == [str(franja_propia.id)]


def test_odontologo_no_lee_horarios_ajenos_ni_de_uuids_inexistentes(
    anonimo: TestClient,
    odontologo: Usuario,
    emisor_test: EmisorTokens,
    otro_profesional: Profesional,
) -> None:
    encabezados = _bearer(odontologo, emisor_test)

    ajeno = anonimo.get(f"/profesionales/{otro_profesional.id}/horarios", headers=encabezados)
    inexistente = anonimo.get(f"/profesionales/{uuid4()}/horarios", headers=encabezados)

    assert (ajeno.status_code, inexistente.status_code) == (403, 403)
    assert ajeno.json() == inexistente.json() == CUERPO_AJENO


def test_odontologo_con_id_mal_formado_recibe_422_y_no_403(
    anonimo: TestClient, odontologo: Usuario, emisor_test: EmisorTokens
) -> None:
    respuesta = anonimo.get(
        "/profesionales/no-es-un-id/horarios", headers=_bearer(odontologo, emisor_test)
    )

    assert respuesta.status_code == 422


def test_lectura_sin_token_con_id_mal_formado_recibe_401_y_no_422(anonimo: TestClient) -> None:
    respuesta = anonimo.get("/profesionales/no-es-un-id/horarios")

    assert respuesta.status_code == 401
    assert respuesta.headers["WWW-Authenticate"] == "Bearer"
    assert respuesta.json() == CUERPO_401


def test_la_recepcionista_lee_el_horario_de_cualquier_profesional(
    client: TestClient, otro_profesional: Profesional
) -> None:
    assert client.get(f"/profesionales/{otro_profesional.id}/horarios").status_code == 200
