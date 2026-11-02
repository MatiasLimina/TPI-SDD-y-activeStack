"""Escrituras de turnos por la API de punta a punta: cada operación exitosa deja su registro."""

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api.turnos import get_reloj
from app.infrastructure.db.models import Usuario
from app.infrastructure.security.contrasenas import Hasher
from app.infrastructure.security.tokens import EmisorTokens
from tests.integration.factories import Catalogo, crear_catalogo

AHORA = datetime(2026, 10, 7, 12, 0, tzinfo=UTC)  # 2026-10-07 09:00 hora local
INICIO_LOCAL = "2026-10-08T10:00:00-03:00"


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


def _crear(api: TestClient, c: Catalogo, **kwargs: Any) -> str:
    respuesta = api.post("/turnos", json=_body(c), **kwargs)
    assert respuesta.status_code == 201, respuesta.text
    return respuesta.json()["id"]


def _registros(session: Session, turno_id: str) -> list[Any]:
    session.expire_all()
    return list(
        session.execute(
            text(
                "SELECT accion, usuario_id, ocurrido_en, valores_previos, valores_nuevos "
                "FROM turno_auditoria WHERE turno_id = :id ORDER BY id"
            ),
            {"id": UUID(turno_id)},
        ).all()
    )


# --- 7.1 una operación exitosa, un registro -------------------------------------------------


def test_post_turnos_exitoso_deja_un_registro_crear_con_autor_e_instante_del_reloj(
    api: TestClient, db_session: Session, catalogo: Catalogo, recepcionista: Usuario
) -> None:
    turno_id = _crear(api, catalogo)

    (registro,) = _registros(db_session, turno_id)

    assert registro.accion == "crear"
    assert registro.usuario_id == recepcionista.id
    assert registro.ocurrido_en == AHORA
    assert registro.valores_previos is None
    assert registro.valores_nuevos["inicio"] == "2026-10-08T13:00:00+00:00"
    assert registro.valores_nuevos["estado"] == "programado"


def test_patch_reprogramar_exitoso_deja_un_registro_reprogramar_con_previos_y_nuevos(
    api: TestClient, db_session: Session, catalogo: Catalogo, recepcionista: Usuario
) -> None:
    turno_id = _crear(api, catalogo)

    respuesta = api.patch(
        f"/turnos/{turno_id}/reprogramar", json={"inicio": "2026-10-08T15:00:00-03:00"}
    )

    assert respuesta.status_code == 200
    crear, reprogramar = _registros(db_session, turno_id)
    assert (crear.accion, reprogramar.accion) == ("crear", "reprogramar")
    assert reprogramar.usuario_id == recepcionista.id
    assert reprogramar.ocurrido_en == AHORA
    assert reprogramar.valores_previos["inicio"] == "2026-10-08T13:00:00+00:00"
    assert reprogramar.valores_nuevos["inicio"] == "2026-10-08T18:00:00+00:00"


def test_post_cancelar_exitoso_deja_un_registro_cancelar_con_el_motivo_normalizado(
    api: TestClient, db_session: Session, catalogo: Catalogo, recepcionista: Usuario
) -> None:
    turno_id = _crear(api, catalogo)

    respuesta = api.post(f"/turnos/{turno_id}/cancelar", json={"motivo": "  Viaje imprevisto  "})

    assert respuesta.status_code == 200
    crear, cancelar = _registros(db_session, turno_id)
    assert (crear.accion, cancelar.accion) == ("crear", "cancelar")
    assert cancelar.usuario_id == recepcionista.id
    assert cancelar.ocurrido_en == AHORA
    assert cancelar.valores_previos["estado"] == "programado"
    assert cancelar.valores_nuevos["estado"] == "cancelado"
    assert cancelar.valores_nuevos["motivo_cancelacion"] == "Viaje imprevisto"


def test_cada_operacion_registra_a_su_autor_autenticado(
    api: TestClient,
    db_session: Session,
    catalogo: Catalogo,
    recepcionista: Usuario,
    recepcionista_s: Usuario,
    emisor_test: EmisorTokens,
) -> None:
    turno_id = _crear(api, catalogo)  # R
    api.patch(
        f"/turnos/{turno_id}/reprogramar",
        json={"inicio": "2026-10-08T15:00:00-03:00"},
        headers=_como(recepcionista_s, emisor_test),  # S
    ).raise_for_status()
    api.post(f"/turnos/{turno_id}/cancelar").raise_for_status()  # R

    registros = _registros(db_session, turno_id)

    assert [r.accion for r in registros] == ["crear", "reprogramar", "cancelar"]
    assert [r.usuario_id for r in registros] == [
        recepcionista.id,
        recepcionista_s.id,
        recepcionista.id,
    ]


def test_el_autor_informado_en_el_body_se_ignora_y_queda_el_usuario_autenticado(
    api: TestClient,
    db_session: Session,
    catalogo: Catalogo,
    recepcionista: Usuario,
    recepcionista_s: Usuario,
) -> None:
    cuerpo = _body(catalogo, usuario_id=str(recepcionista_s.id), creado_por=str(recepcionista_s.id))

    respuesta = api.post("/turnos", json=cuerpo)

    assert respuesta.status_code == 201
    (registro,) = _registros(db_session, respuesta.json()["id"])
    assert registro.usuario_id == recepcionista.id
    assert respuesta.json()["creado_por"] == str(recepcionista.id)


# --- 7.2 rechazos que no auditan ------------------------------------------------------------


def _total(session: Session) -> int:
    session.expire_all()
    return session.execute(text("SELECT count(*) FROM turno_auditoria")).scalar_one()


def test_alta_en_conflicto_409_no_cambia_la_cantidad_de_registros(
    api: TestClient, db_session: Session, catalogo: Catalogo
) -> None:
    _crear(api, catalogo)
    antes = _total(db_session)

    respuesta = api.post("/turnos", json=_body(catalogo, inicio="2026-10-08T10:30:00-03:00"))

    assert respuesta.status_code == 409
    assert _total(db_session) == antes == 1


def test_reprogramacion_invalida_422_no_cambia_la_cantidad_de_registros(
    api: TestClient, db_session: Session, catalogo: Catalogo
) -> None:
    turno_id = _crear(api, catalogo)

    respuesta = api.patch(f"/turnos/{turno_id}/reprogramar", json={"duracion_min": 7})

    assert respuesta.status_code == 422
    assert [r.accion for r in _registros(db_session, turno_id)] == ["crear"]


def test_segunda_cancelacion_409_no_agrega_registros(
    api: TestClient, db_session: Session, catalogo: Catalogo
) -> None:
    turno_id = _crear(api, catalogo)
    api.post(f"/turnos/{turno_id}/cancelar").raise_for_status()

    respuesta = api.post(f"/turnos/{turno_id}/cancelar")

    assert respuesta.status_code == 409
    assert respuesta.json()["detail"]["codigo"] == "turno_ya_cancelado"
    assert [r.accion for r in _registros(db_session, turno_id)] == ["crear", "cancelar"]


def test_cancelacion_de_un_odontologo_403_no_agrega_registros(
    api: TestClient,
    db_session: Session,
    catalogo: Catalogo,
    odontologo: Usuario,
    emisor_test: EmisorTokens,
) -> None:
    turno_id = _crear(api, catalogo)

    respuesta = api.post(f"/turnos/{turno_id}/cancelar", headers=_como(odontologo, emisor_test))

    assert respuesta.status_code == 403
    assert [r.accion for r in _registros(db_session, turno_id)] == ["crear"]


def test_reprogramacion_de_un_odontologo_403_no_agrega_registros(
    api: TestClient,
    db_session: Session,
    catalogo: Catalogo,
    odontologo: Usuario,
    emisor_test: EmisorTokens,
) -> None:
    turno_id = _crear(api, catalogo)

    respuesta = api.patch(
        f"/turnos/{turno_id}/reprogramar",
        json={"inicio": "2026-10-08T15:00:00-03:00"},
        headers=_como(odontologo, emisor_test),
    )

    assert respuesta.status_code == 403
    assert [r.accion for r in _registros(db_session, turno_id)] == ["crear"]


def test_cancelacion_sin_token_401_no_agrega_registros_y_el_turno_sigue_programado(
    api: TestClient, cliente_anonimo: TestClient, db_session: Session, catalogo: Catalogo
) -> None:
    turno_id = _crear(api, catalogo)

    respuesta = cliente_anonimo.post(f"/turnos/{turno_id}/cancelar")

    assert respuesta.status_code == 401
    assert respuesta.headers["WWW-Authenticate"] == "Bearer"
    assert [r.accion for r in _registros(db_session, turno_id)] == ["crear"]
    estado = db_session.execute(
        text("SELECT estado FROM turno WHERE id = :id"), {"id": UUID(turno_id)}
    ).scalar_one()
    assert estado == "programado"


def test_alta_sin_token_401_no_genera_registros(
    api: TestClient, cliente_anonimo: TestClient, db_session: Session, catalogo: Catalogo
) -> None:
    respuesta = cliente_anonimo.post("/turnos", json=_body(catalogo))

    assert respuesta.status_code == 401
    assert _total(db_session) == 0


def test_cancelar_y_reprogramar_un_turno_inexistente_404_no_cambian_los_registros(
    api: TestClient, db_session: Session, catalogo: Catalogo
) -> None:
    _crear(api, catalogo)
    antes = _total(db_session)
    desconocido = "3f0c1c9e-5b7a-4d1e-9a52-8d2b6f0a7c11"

    cancelar = api.post(f"/turnos/{desconocido}/cancelar")
    reprogramar = api.patch(
        f"/turnos/{desconocido}/reprogramar", json={"inicio": "2026-10-09T10:00:00-03:00"}
    )

    assert cancelar.status_code == reprogramar.status_code == 404
    assert cancelar.json()["detail"]["codigo"] == "turno_inexistente"
    assert reprogramar.json()["detail"]["codigo"] == "turno_inexistente"
    assert _total(db_session) == antes == 1
