"""RBAC de las rutas de pacientes: app real, PostgreSQL real, tokens reales."""

from datetime import timedelta
from typing import Any
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.infrastructure.db.models import Paciente, Turno, Usuario
from app.infrastructure.security.tokens import EmisorTokens
from tests.integration.factories import INICIO_BASE, Catalogo, crear_catalogo

CUERPO_401 = {"detail": {"codigo": "no_autenticado", "mensaje": "No autenticado"}}
CUERPO_403 = {"detail": {"codigo": "rol_insuficiente", "mensaje": "Rol insuficiente"}}
CUERPO_AJENO = {
    "detail": {
        "codigo": "paciente_ajeno",
        "mensaje": "Solo podés consultar pacientes de tus turnos",
    }
}
CLAVES_RESUMEN = {"id", "nombre", "apellido"}
DATOS_RESERVADOS = ["FIC-0101", "+54 11 5555-0101", "carla.imaginaria@example.com"]


@pytest.fixture
def anonimo(client: TestClient, cliente_anonimo: TestClient) -> TestClient:
    return cliente_anonimo


@pytest.fixture
def catalogo(db_session: Session) -> Catalogo:
    return crear_catalogo(db_session)


@pytest.fixture
def carla(db_session: Session) -> Paciente:
    paciente = Paciente(
        nombre="Carla",
        apellido="Imaginaria",
        documento="FIC-0101",
        telefono="+54 11 5555-0101",
        email="carla.imaginaria@example.com",
    )
    db_session.add(paciente)
    db_session.flush()
    return paciente


def _bearer(usuario: Usuario, emisor: EmisorTokens) -> dict[str, str]:
    return {"Authorization": f"Bearer {emisor.emitir(usuario)}"}


def _turno(
    session: Session,
    catalogo: Catalogo,
    *,
    profesional_id: UUID | None,
    paciente: Paciente,
    estado: str = "programado",
    dias: int = 0,
) -> Turno:
    """Turno de consulta (sin sillón) del profesional con el paciente, insertado directo."""
    inicio = INICIO_BASE + timedelta(days=dias)
    turno = Turno(
        profesional_id=profesional_id,
        sillon_id=None,
        paciente_id=paciente.id,
        prestacion_id=catalogo.consulta.id,
        inicio=inicio,
        fin=inicio + timedelta(minutes=30),
        duracion_min=30,
        estado=estado,
    )
    session.add(turno)
    session.flush()
    return turno


def _snapshot(session: Session) -> list[tuple[Any, ...]]:
    session.expire_all()
    return sorted(
        (p.id, p.nombre, p.apellido, p.documento, p.telefono, p.email, p.activo)
        for p in session.scalars(select(Paciente))
    )


# --- Lectura mínima del odontólogo --------------------------------------------------------


def test_odontologo_lee_solo_id_nombre_y_apellido_de_un_paciente_de_un_turno_propio(
    anonimo: TestClient,
    db_session: Session,
    catalogo: Catalogo,
    odontologo: Usuario,
    emisor_test: EmisorTokens,
    carla: Paciente,
) -> None:
    _turno(db_session, catalogo, profesional_id=odontologo.profesional_id, paciente=carla)

    respuesta = anonimo.get(f"/pacientes/{carla.id}", headers=_bearer(odontologo, emisor_test))

    assert respuesta.status_code == 200
    assert respuesta.json() == {"id": str(carla.id), "nombre": "Carla", "apellido": "Imaginaria"}
    assert set(respuesta.json()) == CLAVES_RESUMEN
    for dato in DATOS_RESERVADOS:
        assert dato not in respuesta.text


def test_odontologo_lee_a_un_paciente_cuyo_unico_turno_propio_esta_cancelado(
    anonimo: TestClient,
    db_session: Session,
    catalogo: Catalogo,
    odontologo: Usuario,
    emisor_test: EmisorTokens,
    carla: Paciente,
) -> None:
    _turno(
        db_session,
        catalogo,
        profesional_id=odontologo.profesional_id,
        paciente=carla,
        estado="cancelado",
    )

    respuesta = anonimo.get(f"/pacientes/{carla.id}", headers=_bearer(odontologo, emisor_test))

    assert respuesta.status_code == 200
    assert set(respuesta.json()) == CLAVES_RESUMEN


def test_odontologo_lee_a_un_paciente_desactivado_de_un_turno_propio(
    anonimo: TestClient,
    db_session: Session,
    catalogo: Catalogo,
    odontologo: Usuario,
    emisor_test: EmisorTokens,
    carla: Paciente,
) -> None:
    _turno(db_session, catalogo, profesional_id=odontologo.profesional_id, paciente=carla)
    carla.activo = False
    db_session.flush()

    respuesta = anonimo.get(f"/pacientes/{carla.id}", headers=_bearer(odontologo, emisor_test))

    assert respuesta.status_code == 200
    assert set(respuesta.json()) == CLAVES_RESUMEN
    assert "activo" not in respuesta.json()


def test_odontologo_lee_a_un_paciente_con_un_turno_pasado_propio(
    anonimo: TestClient,
    db_session: Session,
    catalogo: Catalogo,
    odontologo: Usuario,
    emisor_test: EmisorTokens,
    carla: Paciente,
) -> None:
    _turno(
        db_session, catalogo, profesional_id=odontologo.profesional_id, paciente=carla, dias=-400
    )

    respuesta = anonimo.get(f"/pacientes/{carla.id}", headers=_bearer(odontologo, emisor_test))

    assert respuesta.status_code == 200


def test_la_recepcionista_sigue_leyendo_la_ficha_completa(
    client: TestClient, carla: Paciente
) -> None:
    respuesta = client.get(f"/pacientes/{carla.id}")

    assert respuesta.status_code == 200
    assert set(respuesta.json()) == {
        "id",
        "nombre",
        "apellido",
        "documento",
        "telefono",
        "email",
        "activo",
    }


# --- Paciente ajeno para el odontólogo ----------------------------------------------------


def test_odontologo_no_lee_a_un_paciente_con_turnos_solo_de_otro_profesional(
    anonimo: TestClient,
    db_session: Session,
    catalogo: Catalogo,
    odontologo: Usuario,
    emisor_test: EmisorTokens,
    carla: Paciente,
) -> None:
    _turno(db_session, catalogo, profesional_id=catalogo.profesionales[0].id, paciente=carla)

    respuesta = anonimo.get(f"/pacientes/{carla.id}", headers=_bearer(odontologo, emisor_test))

    assert respuesta.status_code == 403
    assert respuesta.json() == CUERPO_AJENO
    for dato in ["Carla", "Imaginaria", *DATOS_RESERVADOS]:
        assert dato not in respuesta.text


def test_odontologo_no_lee_a_un_paciente_sin_turnos(
    anonimo: TestClient, odontologo: Usuario, emisor_test: EmisorTokens, carla: Paciente
) -> None:
    respuesta = anonimo.get(f"/pacientes/{carla.id}", headers=_bearer(odontologo, emisor_test))

    assert respuesta.status_code == 403
    assert respuesta.json() == CUERPO_AJENO


def test_un_paciente_ajeno_y_uno_inexistente_dan_el_mismo_cuerpo_para_el_odontologo(
    anonimo: TestClient,
    db_session: Session,
    catalogo: Catalogo,
    odontologo: Usuario,
    emisor_test: EmisorTokens,
    carla: Paciente,
) -> None:
    _turno(db_session, catalogo, profesional_id=catalogo.profesionales[0].id, paciente=carla)
    cabeceras = _bearer(odontologo, emisor_test)

    ajeno = anonimo.get(f"/pacientes/{carla.id}", headers=cabeceras)
    inexistente = anonimo.get(f"/pacientes/{uuid4()}", headers=cabeceras)

    assert ajeno.status_code == inexistente.status_code == 403
    assert ajeno.content == inexistente.content
    assert ajeno.json() == CUERPO_AJENO


def test_odontologo_no_ve_turnos_de_su_profesional_con_otro_paciente(
    anonimo: TestClient,
    db_session: Session,
    catalogo: Catalogo,
    odontologo: Usuario,
    emisor_test: EmisorTokens,
    carla: Paciente,
) -> None:
    propio, ajeno = catalogo.pacientes
    _turno(db_session, catalogo, profesional_id=odontologo.profesional_id, paciente=propio)

    permitido = anonimo.get(f"/pacientes/{propio.id}", headers=_bearer(odontologo, emisor_test))
    negado = anonimo.get(f"/pacientes/{ajeno.id}", headers=_bearer(odontologo, emisor_test))

    assert permitido.status_code == 200
    assert negado.status_code == 403


def test_odontologo_con_id_mal_formado_responde_422(
    anonimo: TestClient, odontologo: Usuario, emisor_test: EmisorTokens
) -> None:
    respuesta = anonimo.get("/pacientes/no-es-un-id", headers=_bearer(odontologo, emisor_test))

    assert respuesta.status_code == 422


def test_sin_token_el_detalle_responde_401_antes_que_el_422_del_path(anonimo: TestClient) -> None:
    respuesta = anonimo.get("/pacientes/no-es-un-id")

    assert respuesta.status_code == 401
    assert respuesta.json() == CUERPO_401
    assert respuesta.headers["WWW-Authenticate"] == "Bearer"


# --- Escritura de pacientes reservada a la recepcionista -----------------------------------

BODY_VALIDO = {
    "nombre": "Nuevo",
    "apellido": "Ficticio",
    "documento": "FIC-9999",
    "telefono": "+54 11 5555-9999",
}


def _escrituras(paciente_id: object) -> dict[str, tuple[str, str, dict[str, Any] | None]]:
    return {
        "post": ("POST", "/pacientes", BODY_VALIDO),
        "patch": ("PATCH", f"/pacientes/{paciente_id}", {"telefono": "+54 11 5555-0199"}),
    }


@pytest.mark.parametrize("ruta", ["post", "patch"])
def test_escritura_de_un_odontologo_responde_403_y_la_base_no_cambia(
    anonimo: TestClient,
    db_session: Session,
    catalogo: Catalogo,
    odontologo: Usuario,
    emisor_test: EmisorTokens,
    carla: Paciente,
    ruta: str,
) -> None:
    _turno(db_session, catalogo, profesional_id=odontologo.profesional_id, paciente=carla)
    metodo, url, body = _escrituras(carla.id)[ruta]
    antes = _snapshot(db_session)

    respuesta = anonimo.request(metodo, url, json=body, headers=_bearer(odontologo, emisor_test))

    assert respuesta.status_code == 403
    assert respuesta.json() == CUERPO_403
    assert _snapshot(db_session) == antes


@pytest.mark.parametrize("ruta", ["post", "patch"])
def test_escritura_sin_token_responde_401_y_la_base_no_cambia(
    anonimo: TestClient, db_session: Session, carla: Paciente, ruta: str
) -> None:
    metodo, url, body = _escrituras(carla.id)[ruta]
    antes = _snapshot(db_session)

    respuesta = anonimo.request(metodo, url, json=body)

    assert respuesta.status_code == 401
    assert respuesta.json() == CUERPO_401
    assert respuesta.headers["WWW-Authenticate"] == "Bearer"
    assert _snapshot(db_session) == antes


def test_odontologo_con_body_vacio_recibe_403_y_no_422(
    anonimo: TestClient, db_session: Session, odontologo: Usuario, emisor_test: EmisorTokens
) -> None:
    respuesta = anonimo.post("/pacientes", json={}, headers=_bearer(odontologo, emisor_test))

    assert respuesta.status_code == 403
    assert respuesta.json() == CUERPO_403
    assert db_session.scalar(select(func.count()).select_from(Paciente)) == 0


def test_odontologo_con_activo_en_el_body_recibe_403_y_no_campo_no_editable(
    anonimo: TestClient, odontologo: Usuario, emisor_test: EmisorTokens, carla: Paciente
) -> None:
    respuesta = anonimo.patch(
        f"/pacientes/{carla.id}", json={"activo": True}, headers=_bearer(odontologo, emisor_test)
    )

    assert respuesta.status_code == 403


def test_odontologo_con_patch_a_un_paciente_inexistente_recibe_403_y_no_404(
    anonimo: TestClient, odontologo: Usuario, emisor_test: EmisorTokens
) -> None:
    respuesta = anonimo.patch(
        f"/pacientes/{uuid4()}",
        json={"telefono": "+54 11 5555-0199"},
        headers=_bearer(odontologo, emisor_test),
    )

    assert respuesta.status_code == 403


def test_la_recepcionista_si_puede_escribir_en_las_rutas_de_alta_y_edicion(
    client: TestClient, carla: Paciente
) -> None:
    peticiones = _escrituras(carla.id)

    codigos = {
        ruta: client.request(metodo, url, json=body).status_code
        for ruta, (metodo, url, body) in peticiones.items()
    }

    assert codigos == {"post": 201, "patch": 200}


# --- Listado y búsqueda reservados a la recepcionista --------------------------------------


@pytest.mark.parametrize("consulta", ["", "?q=imaginaria"], ids=["listado", "busqueda"])
def test_odontologo_no_lista_ni_busca_pacientes(
    anonimo: TestClient,
    db_session: Session,
    catalogo: Catalogo,
    odontologo: Usuario,
    emisor_test: EmisorTokens,
    carla: Paciente,
    consulta: str,
) -> None:
    _turno(db_session, catalogo, profesional_id=odontologo.profesional_id, paciente=carla)

    respuesta = anonimo.get(f"/pacientes{consulta}", headers=_bearer(odontologo, emisor_test))

    assert respuesta.status_code == 403
    assert respuesta.json() == CUERPO_403
    for dato in ["Carla", "Imaginaria", *DATOS_RESERVADOS]:
        assert dato not in respuesta.text


@pytest.mark.parametrize("consulta", ["", "?q=imaginaria"], ids=["listado", "busqueda"])
def test_listado_sin_token_responde_401(anonimo: TestClient, consulta: str) -> None:
    respuesta = anonimo.get(f"/pacientes{consulta}")

    assert respuesta.status_code == 401
    assert respuesta.json() == CUERPO_401
    assert respuesta.headers["WWW-Authenticate"] == "Bearer"


@pytest.mark.parametrize("consulta", ["?limite=0", "?limite=101", "?desplazamiento=-1"])
def test_rol_y_autenticacion_se_evaluan_antes_que_los_parametros(
    anonimo: TestClient, odontologo: Usuario, emisor_test: EmisorTokens, consulta: str
) -> None:
    como_odontologo = anonimo.get(f"/pacientes{consulta}", headers=_bearer(odontologo, emisor_test))
    sin_token = anonimo.get(f"/pacientes{consulta}")

    assert como_odontologo.status_code == 403
    assert sin_token.status_code == 401
