"""GET /turnos/{id}/auditoria de punta a punta: FastAPI + caso de uso + PostgreSQL real."""

import json
from datetime import UTC, datetime
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api.turnos import get_reloj
from app.infrastructure.db.models import Usuario
from app.infrastructure.security.contrasenas import Hasher
from app.infrastructure.security.tokens import EmisorTokens
from tests.integration.factories import Catalogo, crear_catalogo, crear_turno

AHORA = datetime(2026, 10, 7, 12, 0, tzinfo=UTC)  # 2026-10-07 09:00 hora local
INICIO_LOCAL = "2026-10-08T10:00:00-03:00"
DESCONOCIDO = "3f0c1c9e-5b7a-4d1e-9a52-8d2b6f0a7c11"
CLAVES = {
    "profesional_id",
    "paciente_id",
    "prestacion_id",
    "sillon_id",
    "inicio",
    "fin",
    "duracion_min",
    "estado",
    "motivo_cancelacion",
}


@pytest.fixture
def catalogo(db_session: Session) -> Catalogo:
    return crear_catalogo(db_session)


@pytest.fixture
def api(client: TestClient) -> TestClient:
    """Cliente autenticado como la recepcionista R de test, con el reloj fijo."""
    client.app.dependency_overrides[get_reloj] = lambda: lambda: AHORA  # type: ignore[attr-defined]
    return client


@pytest.fixture
def recepcionista_s(db_session: Session, hasher_test: Hasher) -> Usuario:
    usuario = Usuario(
        email="recepcion2@example.com",
        password_hash=hasher_test.hash("clave-ficticia-recepcion-2"),
        rol="recepcionista",
    )
    db_session.add(usuario)
    db_session.flush()
    return usuario


def _como(usuario: Usuario, emisor: EmisorTokens) -> dict[str, str]:
    return {"Authorization": f"Bearer {emisor.emitir(usuario)}"}


def _body(c: Catalogo, **cambios: Any) -> dict[str, Any]:
    body: dict[str, Any] = {
        "profesional_id": str(c.profesionales[0].id),
        "paciente_id": str(c.pacientes[0].id),
        "prestacion_id": str(c.limpieza.id),
        "sillon_id": str(c.sillones[0].id),
        "inicio": INICIO_LOCAL,
    }
    body.update(cambios)
    return body


def _crear(api: TestClient, c: Catalogo, **cambios: Any) -> str:
    respuesta = api.post("/turnos", json=_body(c, **cambios))
    assert respuesta.status_code == 201, respuesta.text
    return respuesta.json()["id"]


def _historial_completo(api: TestClient, c: Catalogo, s: Usuario, emisor: EmisorTokens) -> str:
    """R crea, S reprograma a las 15:00 y R cancela, con el reloj fijo."""
    turno_id = _crear(api, c)
    api.patch(
        f"/turnos/{turno_id}/reprogramar",
        json={"inicio": "2026-10-08T15:00:00-03:00"},
        headers=_como(s, emisor),
    ).raise_for_status()
    api.post(f"/turnos/{turno_id}/cancelar", json={"motivo": "Viaje"}).raise_for_status()
    return turno_id


def _total(session: Session) -> int:
    session.expire_all()
    return session.execute(text("SELECT count(*) FROM turno_auditoria")).scalar_one()


# --- 8.2 historial -----------------------------------------------------------------------


def test_historial_completo_en_orden_con_autores_e_instantes_en_hora_local(
    api: TestClient,
    catalogo: Catalogo,
    recepcionista: Usuario,
    recepcionista_s: Usuario,
    emisor_test: EmisorTokens,
) -> None:
    turno_id = _historial_completo(api, catalogo, recepcionista_s, emisor_test)

    respuesta = api.get(f"/turnos/{turno_id}/auditoria")

    assert respuesta.status_code == 200
    registros = respuesta.json()
    assert [r["accion"] for r in registros] == ["crear", "reprogramar", "cancelar"]
    assert [r["usuario_id"] for r in registros] == [
        str(recepcionista.id),
        str(recepcionista_s.id),
        str(recepcionista.id),
    ]
    assert {r["ocurrido_en"] for r in registros} == {"2026-10-07T09:00:00-03:00"}
    ids = [r["id"] for r in registros]
    assert all(isinstance(i, int) for i in ids)
    assert ids == sorted(ids)
    assert len(set(ids)) == 3


def test_crear_muestra_previos_nulos_e_instantes_de_las_instantaneas_en_hora_local(
    api: TestClient, catalogo: Catalogo
) -> None:
    turno_id = _crear(api, catalogo)

    (crear,) = api.get(f"/turnos/{turno_id}/auditoria").json()

    assert crear["valores_previos"] is None
    nuevos = crear["valores_nuevos"]
    assert set(nuevos) == CLAVES
    assert nuevos["inicio"] == "2026-10-08T10:00:00-03:00"
    assert nuevos["fin"] == "2026-10-08T10:45:00-03:00"
    assert nuevos["estado"] == "programado"
    assert nuevos["profesional_id"] == str(catalogo.profesionales[0].id)
    assert nuevos["sillon_id"] == str(catalogo.sillones[0].id)


def test_reprogramar_y_cancelar_muestran_previos_y_nuevos_con_instantes_en_hora_local(
    api: TestClient,
    catalogo: Catalogo,
    recepcionista_s: Usuario,
    emisor_test: EmisorTokens,
) -> None:
    turno_id = _historial_completo(api, catalogo, recepcionista_s, emisor_test)

    _, reprogramar, cancelar = api.get(f"/turnos/{turno_id}/auditoria").json()

    assert reprogramar["valores_previos"]["inicio"] == "2026-10-08T10:00:00-03:00"
    assert reprogramar["valores_nuevos"]["inicio"] == "2026-10-08T15:00:00-03:00"
    assert reprogramar["valores_nuevos"]["fin"] == "2026-10-08T15:45:00-03:00"
    assert cancelar["valores_previos"]["estado"] == "programado"
    assert cancelar["valores_nuevos"]["estado"] == "cancelado"
    assert cancelar["valores_nuevos"]["motivo_cancelacion"] == "Viaje"


def test_registros_con_el_mismo_ocurrido_en_salen_en_orden_de_insercion(
    api: TestClient, db_session: Session, catalogo: Catalogo, recepcionista: Usuario
) -> None:
    turno = crear_turno(db_session, catalogo)
    instantanea = json.dumps(
        {
            "profesional_id": str(catalogo.profesionales[0].id),
            "paciente_id": str(catalogo.pacientes[0].id),
            "prestacion_id": str(catalogo.limpieza.id),
            "sillon_id": None,
            "inicio": "2026-10-08T13:00:00+00:00",
            "fin": "2026-10-08T13:45:00+00:00",
            "duracion_min": 45,
            "estado": "programado",
            "motivo_cancelacion": None,
        }
    )
    # Insertados en un orden que no es el alfabético, todos con el mismo `ocurrido_en`
    for accion, previos in (
        ("crear", None),
        ("cancelar", instantanea),
        ("reprogramar", instantanea),
    ):
        db_session.execute(
            text(
                "INSERT INTO turno_auditoria (turno_id, usuario_id, accion, valores_previos, "
                "valores_nuevos, ocurrido_en) VALUES (:turno, :usuario, :accion, "
                "CAST(:previos AS jsonb), CAST(:nuevos AS jsonb), :ocurrido_en)"
            ),
            {
                "turno": turno.id,
                "usuario": recepcionista.id,
                "accion": accion,
                "previos": previos,
                "nuevos": instantanea,
                "ocurrido_en": AHORA,
            },
        )

    registros = api.get(f"/turnos/{turno.id}/auditoria").json()

    assert [r["accion"] for r in registros] == ["crear", "cancelar", "reprogramar"]
    assert {r["ocurrido_en"] for r in registros} == {"2026-10-07T09:00:00-03:00"}


def test_dos_consultas_iguales_devuelven_lo_mismo_y_no_agregan_registros(
    api: TestClient, db_session: Session, catalogo: Catalogo
) -> None:
    turno_id = _crear(api, catalogo)
    api.post(f"/turnos/{turno_id}/cancelar").raise_for_status()
    antes = _total(db_session)

    primera = api.get(f"/turnos/{turno_id}/auditoria")
    segunda = api.get(f"/turnos/{turno_id}/auditoria")

    assert primera.status_code == segunda.status_code == 200
    assert primera.json() == segunda.json()
    assert len(primera.json()) == 2
    assert _total(db_session) == antes


def test_solo_devuelve_los_registros_del_turno_pedido(api: TestClient, catalogo: Catalogo) -> None:
    t1 = _crear(api, catalogo)
    api.post(f"/turnos/{t1}/cancelar").raise_for_status()
    t2 = _crear(
        api,
        catalogo,
        profesional_id=str(catalogo.profesionales[1].id),
        paciente_id=str(catalogo.pacientes[1].id),
        sillon_id=str(catalogo.sillones[1].id),
    )

    de_t1 = api.get(f"/turnos/{t1}/auditoria").json()
    de_t2 = api.get(f"/turnos/{t2}/auditoria").json()

    assert [r["accion"] for r in de_t1] == ["crear", "cancelar"]
    assert [r["accion"] for r in de_t2] == ["crear"]


def test_turno_insertado_directo_sin_registros_responde_200_con_lista_vacia(
    api: TestClient, db_session: Session, catalogo: Catalogo
) -> None:
    turno = crear_turno(db_session, catalogo)

    respuesta = api.get(f"/turnos/{turno.id}/auditoria")

    assert respuesta.status_code == 200
    assert respuesta.json() == []


def test_turno_insertado_directo_y_luego_cancelado_por_api_tiene_un_unico_registro_cancelar(
    api: TestClient, db_session: Session, catalogo: Catalogo
) -> None:
    turno = crear_turno(db_session, catalogo)
    api.post(f"/turnos/{turno.id}/cancelar").raise_for_status()

    registros = api.get(f"/turnos/{turno.id}/auditoria").json()

    assert [r["accion"] for r in registros] == ["cancelar"]
    assert registros[0]["valores_previos"]["estado"] == "programado"


def test_turno_inexistente_responde_404_turno_inexistente(api: TestClient) -> None:
    respuesta = api.get(f"/turnos/{DESCONOCIDO}/auditoria")

    assert respuesta.status_code == 404
    assert respuesta.json()["detail"]["codigo"] == "turno_inexistente"


def test_identificador_con_formato_invalido_responde_422(api: TestClient) -> None:
    respuesta = api.get("/turnos/no-es-un-id/auditoria")

    assert respuesta.status_code == 422


# --- 8.3 acceso por rol --------------------------------------------------------------------

CUERPO_401 = {"detail": {"codigo": "no_autenticado", "mensaje": "No autenticado"}}
CUERPO_403 = {"detail": {"codigo": "rol_insuficiente", "mensaje": "Rol insuficiente"}}


def test_odontologo_de_su_propio_profesional_recibe_403_sin_registros_en_el_cuerpo(
    api: TestClient,
    db_session: Session,
    catalogo: Catalogo,
    odontologo: Usuario,
    emisor_test: EmisorTokens,
) -> None:
    turno_id = _crear(api, catalogo, profesional_id=str(odontologo.profesional_id))

    respuesta = api.get(f"/turnos/{turno_id}/auditoria", headers=_como(odontologo, emisor_test))

    assert respuesta.status_code == 403
    assert respuesta.json() == CUERPO_403


def test_sin_token_responde_401_con_www_authenticate_bearer(
    api: TestClient, cliente_anonimo: TestClient, catalogo: Catalogo
) -> None:
    turno_id = _crear(api, catalogo)

    respuesta = cliente_anonimo.get(f"/turnos/{turno_id}/auditoria")

    assert respuesta.status_code == 401
    assert respuesta.headers["WWW-Authenticate"] == "Bearer"
    assert respuesta.json() == CUERPO_401


def test_token_invalido_responde_401(cliente_anonimo: TestClient, catalogo: Catalogo) -> None:
    respuesta = cliente_anonimo.get(
        f"/turnos/{DESCONOCIDO}/auditoria", headers={"Authorization": "Bearer no-es-un-token"}
    )

    assert respuesta.status_code == 401
    assert respuesta.json() == CUERPO_401


def test_el_rol_se_evalua_antes_que_la_existencia_del_turno(
    api: TestClient, odontologo: Usuario, emisor_test: EmisorTokens
) -> None:
    respuesta = api.get(f"/turnos/{DESCONOCIDO}/auditoria", headers=_como(odontologo, emisor_test))

    assert respuesta.status_code == 403
    assert respuesta.json() == CUERPO_403


def test_la_autenticacion_se_evalua_antes_que_el_identificador(
    api: TestClient, cliente_anonimo: TestClient
) -> None:
    respuesta = cliente_anonimo.get("/turnos/no-es-un-id/auditoria")

    assert respuesta.status_code == 401


def test_el_rol_se_evalua_antes_que_el_identificador(
    api: TestClient, odontologo: Usuario, emisor_test: EmisorTokens
) -> None:
    respuesta = api.get("/turnos/no-es-un-id/auditoria", headers=_como(odontologo, emisor_test))

    assert respuesta.status_code == 403


@pytest.mark.parametrize("metodo", ["POST", "PUT", "PATCH", "DELETE"])
def test_metodos_de_escritura_sobre_la_ruta_responden_405_y_no_cambian_los_registros(
    api: TestClient, db_session: Session, catalogo: Catalogo, metodo: str
) -> None:
    turno_id = _crear(api, catalogo)
    api.post(f"/turnos/{turno_id}/cancelar").raise_for_status()
    antes = _total(db_session)

    respuesta = api.request(metodo, f"/turnos/{turno_id}/auditoria")

    assert respuesta.status_code == 405
    assert _total(db_session) == antes == 2
