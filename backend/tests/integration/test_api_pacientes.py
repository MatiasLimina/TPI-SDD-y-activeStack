"""API de pacientes (escritura) contra PostgreSQL real: alta, validaciones, edición y estado."""

from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.turnos import get_reloj
from app.infrastructure.db.models import Paciente, Turno
from tests.integration.factories import crear_catalogo

AHORA = datetime(2026, 10, 7, 12, 0, tzinfo=UTC)  # 2026-10-07 09:00 hora local

CLAVES_PACIENTE = {"id", "nombre", "apellido", "documento", "telefono", "email", "activo"}


def _body(**cambios: Any) -> dict[str, Any]:
    body: dict[str, Any] = {
        "nombre": "Carla",
        "apellido": "Imaginaria",
        "documento": "FIC-0101",
        "telefono": "+54 11 5555-0101",
        "email": "carla.imaginaria@example.com",
    }
    body.update(cambios)
    return body


def _cantidad(session: Session) -> int:
    session.expire_all()
    return session.scalar(select(func.count()).select_from(Paciente)) or 0


def _en_base(session: Session, paciente_id: str | UUID) -> Paciente:
    session.expire_all()
    return session.execute(
        select(Paciente).where(Paciente.id == UUID(str(paciente_id)))
    ).scalar_one()


def _crear(client: TestClient, **cambios: Any) -> dict[str, Any]:
    respuesta = client.post("/pacientes", json=_body(**cambios))
    assert respuesta.status_code == 201, respuesta.text
    return respuesta.json()


# --- Alta de paciente --------------------------------------------------------------------


def test_post_pacientes_con_email_crea_un_paciente_activo(
    client: TestClient, db_session: Session
) -> None:
    respuesta = client.post("/pacientes", json=_body())

    assert respuesta.status_code == 201
    cuerpo = respuesta.json()
    assert cuerpo["id"]
    assert {k: v for k, v in cuerpo.items() if k != "id"} == {
        "nombre": "Carla",
        "apellido": "Imaginaria",
        "documento": "FIC-0101",
        "telefono": "+54 11 5555-0101",
        "email": "carla.imaginaria@example.com",
        "activo": True,
    }
    guardado = _en_base(db_session, cuerpo["id"])
    assert (guardado.documento, guardado.activo) == ("FIC-0101", True)


def test_post_pacientes_sin_email_responde_email_nulo(client: TestClient) -> None:
    body = _body(nombre="Diego", apellido="Supuesto", documento="FIC-0102")
    del body["email"]

    respuesta = client.post("/pacientes", json=body)

    assert respuesta.status_code == 201
    assert respuesta.json()["email"] is None
    assert respuesta.json()["activo"] is True


def test_post_pacientes_responde_exactamente_las_siete_claves(client: TestClient) -> None:
    respuesta = client.post("/pacientes", json=_body())

    assert respuesta.status_code == 201
    assert set(respuesta.json()) == CLAVES_PACIENTE


def test_post_pacientes_dos_altas_generan_ids_distintos(client: TestClient) -> None:
    uno = _crear(client)
    otro = _crear(client, documento="FIC-0102")

    assert uno["id"] != otro["id"]


# --- Campos mínimos y textos normalizados -------------------------------------------------

TEXTOS = ["nombre", "apellido", "documento", "telefono", "email"]
LARGOS = {"nombre": 100, "apellido": 100, "documento": 20, "telefono": 30, "email": 254}


def _email_de(largo: int) -> str:
    """Email bien formado con exactamente `largo` caracteres."""
    return "a" * (largo - len("@example.com")) + "@example.com"


def _valor_de_largo(campo: str, largo: int) -> str:
    return _email_de(largo) if campo == "email" else "x" * largo


@pytest.mark.parametrize("campo", ["nombre", "apellido", "documento", "telefono"])
def test_post_pacientes_sin_un_campo_obligatorio_responde_422_y_no_persiste(
    client: TestClient, db_session: Session, campo: str
) -> None:
    body = _body()
    del body[campo]

    respuesta = client.post("/pacientes", json=body)

    assert respuesta.status_code == 422
    assert _cantidad(db_session) == 0


@pytest.mark.parametrize("campo", ["nombre", "apellido", "documento", "telefono"])
@pytest.mark.parametrize("valor", ["   ", ""])
def test_post_pacientes_con_un_obligatorio_en_blanco_responde_422(
    client: TestClient, db_session: Session, campo: str, valor: str
) -> None:
    respuesta = client.post("/pacientes", json=_body(**{campo: valor}))

    assert respuesta.status_code == 422
    assert _cantidad(db_session) == 0


@pytest.mark.parametrize("campo", TEXTOS)
def test_post_pacientes_con_un_texto_mas_largo_que_su_columna_responde_422_no_500(
    client: TestClient, db_session: Session, campo: str
) -> None:
    respuesta = client.post(
        "/pacientes", json=_body(**{campo: _valor_de_largo(campo, LARGOS[campo] + 1)})
    )

    assert respuesta.status_code == 422
    assert _cantidad(db_session) == 0


def test_post_pacientes_acepta_los_cinco_textos_con_su_largo_maximo(client: TestClient) -> None:
    textos = {campo: _valor_de_largo(campo, largo) for campo, largo in LARGOS.items()}

    respuesta = client.post("/pacientes", json=_body(**textos))

    assert respuesta.status_code == 201
    cuerpo = respuesta.json()
    assert {campo: cuerpo[campo] for campo in textos} == textos


def test_post_pacientes_recorta_los_espacios_extremos(client: TestClient) -> None:
    respuesta = client.post(
        "/pacientes",
        json=_body(
            nombre="  Elena  ",
            apellido="\tImaginaria ",
            documento=" FIC-0103 ",
            telefono="  +54 11 5555-0103 ",
            email="  elena@example.com ",
        ),
    )

    assert respuesta.status_code == 201
    cuerpo = respuesta.json()
    assert cuerpo["nombre"] == "Elena"
    assert cuerpo["apellido"] == "Imaginaria"
    assert cuerpo["documento"] == "FIC-0103"
    assert cuerpo["telefono"] == "+54 11 5555-0103"
    assert cuerpo["email"] == "elena@example.com"


def test_post_pacientes_no_recorta_los_espacios_internos(client: TestClient) -> None:
    respuesta = client.post("/pacientes", json=_body(nombre="Ana  María"))

    assert respuesta.json()["nombre"] == "Ana  María"


@pytest.mark.parametrize("email", ["   ", ""])
def test_post_pacientes_con_email_en_blanco_lo_guarda_como_nulo(
    client: TestClient, db_session: Session, email: str
) -> None:
    respuesta = client.post("/pacientes", json=_body(email=email))

    assert respuesta.status_code == 201
    assert respuesta.json()["email"] is None
    assert _en_base(db_session, respuesta.json()["id"]).email is None


def test_post_pacientes_con_email_nulo_explicito_lo_guarda_como_nulo(client: TestClient) -> None:
    respuesta = client.post("/pacientes", json=_body(email=None))

    assert respuesta.status_code == 201
    assert respuesta.json()["email"] is None


def test_post_pacientes_no_exige_formato_a_documento_ni_telefono(client: TestClient) -> None:
    numerico = client.post(
        "/pacientes", json=_body(documento="00000104", telefono="11 5555-0104", email=None)
    )
    con_prefijo = client.post(
        "/pacientes",
        json=_body(documento="FIC-0104", telefono="+54 (11) 5555 0105", email=None),
    )

    assert numerico.status_code == 201
    assert (numerico.json()["documento"], numerico.json()["telefono"]) == (
        "00000104",
        "11 5555-0104",
    )
    assert con_prefijo.status_code == 201
    assert (con_prefijo.json()["documento"], con_prefijo.json()["telefono"]) == (
        "FIC-0104",
        "+54 (11) 5555 0105",
    )


@pytest.mark.parametrize("campo", TEXTOS)
def test_post_pacientes_con_caracter_nulo_responde_422_no_500(
    client: TestClient, db_session: Session, campo: str
) -> None:
    valor = "a\x00b@example.com" if campo == "email" else "a\x00b"

    respuesta = client.post("/pacientes", json=_body(**{campo: valor}))

    assert respuesta.status_code == 422
    assert _cantidad(db_session) == 0


# --- Formato mínimo del email -------------------------------------------------------------


@pytest.mark.parametrize(
    "email",
    [
        "carla.example.com",
        "carla @example.com",
        "carla@exam ple.com",
        "@example.com",
        "carla@",
        "carla@a@example.com",
        "carla\t@example.com",
    ],
    ids=[
        "sin-arroba",
        "espacio-local",
        "espacio-dominio",
        "sin-local",
        "sin-dominio",
        "dos",
        "tab",
    ],
)
def test_post_pacientes_con_email_mal_formado_responde_422_y_no_persiste(
    client: TestClient, db_session: Session, email: str
) -> None:
    respuesta = client.post("/pacientes", json=_body(email=email))

    assert respuesta.status_code == 422
    assert _cantidad(db_session) == 0


def test_post_pacientes_guarda_el_email_como_se_envio_sin_cambiar_mayusculas(
    client: TestClient,
) -> None:
    respuesta = client.post("/pacientes", json=_body(email="Carla.Imaginaria@Example.COM"))

    assert respuesta.status_code == 201
    assert respuesta.json()["email"] == "Carla.Imaginaria@Example.COM"


def test_post_pacientes_admite_un_email_repetido_entre_pacientes(
    client: TestClient, db_session: Session
) -> None:
    uno = _crear(client, email="familia@example.com")
    otro = _crear(client, documento="FIC-0102", email="familia@example.com")

    assert uno["id"] != otro["id"]
    assert _en_base(db_session, uno["id"]).email == "familia@example.com"
    assert _en_base(db_session, otro["id"]).email == "familia@example.com"


# --- Documento único ----------------------------------------------------------------------

CUERPO_DUPLICADO = {"detail": {"codigo": "recurso_duplicado", "campo": "documento"}}


def _existente(
    session: Session, documento: str = "FIC-0101", *, activo: bool = True, nombre: str = "Carla"
) -> Paciente:
    paciente = Paciente(
        nombre=nombre,
        apellido="Imaginaria",
        documento=documento,
        telefono="+54 11 5555-0101",
        activo=activo,
    )
    session.add(paciente)
    session.flush()
    return paciente


def _con_documento(session: Session, documento: str) -> int:
    session.expire_all()
    return (
        session.scalar(
            select(func.count()).select_from(Paciente).where(Paciente.documento == documento)
        )
        or 0
    )


def test_post_pacientes_con_documento_repetido_responde_409_aunque_traiga_espacios(
    client: TestClient, db_session: Session
) -> None:
    _existente(db_session)

    respuesta = client.post("/pacientes", json=_body(documento=" FIC-0101 ", nombre="Otra"))

    assert respuesta.status_code == 409
    assert respuesta.json() == CUERPO_DUPLICADO
    assert _con_documento(db_session, "FIC-0101") == 1
    assert _cantidad(db_session) == 1


def test_post_pacientes_con_documento_de_un_desactivado_responde_409(
    client: TestClient, db_session: Session
) -> None:
    _existente(db_session, activo=False)

    respuesta = client.post("/pacientes", json=_body())

    assert respuesta.status_code == 409
    assert respuesta.json() == CUERPO_DUPLICADO
    assert _cantidad(db_session) == 1


def test_post_pacientes_tras_un_409_la_misma_sesion_sigue_aceptando_altas(
    client: TestClient, db_session: Session
) -> None:
    _existente(db_session)
    assert client.post("/pacientes", json=_body()).status_code == 409

    respuesta = client.post("/pacientes", json=_body(documento="FIC-0102"))

    assert respuesta.status_code == 201
    assert _cantidad(db_session) == 2


def test_post_pacientes_409_no_incluye_el_documento_ni_datos_del_existente(
    client: TestClient, db_session: Session
) -> None:
    _existente(db_session, nombre="Nombre-Del-Existente")

    respuesta = client.post("/pacientes", json=_body())

    assert respuesta.status_code == 409
    assert "FIC-0101" not in respuesta.text
    assert "Nombre-Del-Existente" not in respuesta.text


# --- Edición parcial de un paciente -------------------------------------------------------


def _estado(session: Session, paciente_id: UUID) -> dict[str, Any]:
    """Los campos del paciente, leídos de la base."""
    guardado = _en_base(session, paciente_id)
    return {
        "nombre": guardado.nombre,
        "apellido": guardado.apellido,
        "documento": guardado.documento,
        "telefono": guardado.telefono,
        "email": guardado.email,
        "activo": guardado.activo,
    }


def test_patch_pacientes_con_un_solo_campo_cambia_solo_ese(
    client: TestClient, db_session: Session
) -> None:
    paciente = _existente(db_session)
    paciente.email = "carla@example.com"
    db_session.flush()

    respuesta = client.patch(f"/pacientes/{paciente.id}", json={"telefono": "+54 11 5555-0199"})

    assert respuesta.status_code == 200
    assert respuesta.json() == {
        "id": str(paciente.id),
        "nombre": "Carla",
        "apellido": "Imaginaria",
        "documento": "FIC-0101",
        "telefono": "+54 11 5555-0199",
        "email": "carla@example.com",
        "activo": True,
    }
    assert _estado(db_session, paciente.id)["telefono"] == "+54 11 5555-0199"


def test_patch_pacientes_cambia_varios_campos_a_la_vez(
    client: TestClient, db_session: Session
) -> None:
    paciente = _existente(db_session)

    respuesta = client.patch(
        f"/pacientes/{paciente.id}",
        json={"nombre": "  Carlota ", "apellido": "Ficticia", "email": "carlota@example.com"},
    )

    assert respuesta.status_code == 200
    assert _estado(db_session, paciente.id) == {
        "nombre": "Carlota",
        "apellido": "Ficticia",
        "documento": "FIC-0101",
        "telefono": "+54 11 5555-0101",
        "email": "carlota@example.com",
        "activo": True,
    }


def test_patch_pacientes_corrige_el_documento_y_el_turno_sigue_con_el_mismo_paciente(
    client: TestClient, db_session: Session
) -> None:
    client.app.dependency_overrides[get_reloj] = lambda: lambda: AHORA  # type: ignore[attr-defined]
    catalogo = crear_catalogo(db_session)
    paciente = catalogo.pacientes[0]
    turno = client.post(
        "/turnos",
        json={
            "profesional_id": str(catalogo.profesionales[0].id),
            "paciente_id": str(paciente.id),
            "prestacion_id": str(catalogo.limpieza.id),
            "sillon_id": str(catalogo.sillones[0].id),
            "inicio": "2026-10-08T10:00:00-03:00",
        },
    )
    assert turno.status_code == 201, turno.text
    turno_id = UUID(turno.json()["id"])

    respuesta = client.patch(f"/pacientes/{paciente.id}", json={"documento": "FIC-0110"})

    assert respuesta.status_code == 200
    assert respuesta.json()["documento"] == "FIC-0110"
    db_session.expire_all()
    guardado = db_session.get(Turno, turno_id)
    assert guardado is not None
    assert (guardado.paciente_id, guardado.estado) == (paciente.id, "programado")


def test_patch_pacientes_con_email_nulo_lo_quita(client: TestClient, db_session: Session) -> None:
    paciente = _existente(db_session)
    paciente.email = "carla@example.com"
    db_session.flush()

    respuesta = client.patch(f"/pacientes/{paciente.id}", json={"email": None})

    assert respuesta.status_code == 200
    assert respuesta.json()["email"] is None
    assert _estado(db_session, paciente.id)["email"] is None


def test_patch_pacientes_con_email_en_blanco_lo_quita(
    client: TestClient, db_session: Session
) -> None:
    paciente = _existente(db_session)
    paciente.email = "carla@example.com"
    db_session.flush()

    respuesta = client.patch(f"/pacientes/{paciente.id}", json={"email": "   "})

    assert respuesta.status_code == 200
    assert respuesta.json()["email"] is None


@pytest.mark.parametrize("campo", ["nombre", "apellido", "documento", "telefono"])
def test_patch_pacientes_con_nulo_en_un_obligatorio_responde_422_y_no_cambia(
    client: TestClient, db_session: Session, campo: str
) -> None:
    paciente = _existente(db_session)
    antes = _estado(db_session, paciente.id)

    respuesta = client.patch(f"/pacientes/{paciente.id}", json={campo: None})

    assert respuesta.status_code == 422
    assert _estado(db_session, paciente.id) == antes


@pytest.mark.parametrize("campo", ["nombre", "apellido", "documento", "telefono"])
def test_patch_pacientes_con_un_obligatorio_en_blanco_responde_422_y_no_cambia(
    client: TestClient, db_session: Session, campo: str
) -> None:
    paciente = _existente(db_session)
    antes = _estado(db_session, paciente.id)

    respuesta = client.patch(f"/pacientes/{paciente.id}", json={campo: "   "})

    assert respuesta.status_code == 422
    assert _estado(db_session, paciente.id) == antes


def test_patch_pacientes_con_body_vacio_responde_200_sin_cambios(
    client: TestClient, db_session: Session
) -> None:
    paciente = _existente(db_session)
    antes = _estado(db_session, paciente.id)

    respuesta = client.patch(f"/pacientes/{paciente.id}", json={})

    assert respuesta.status_code == 200
    assert set(respuesta.json()) == CLAVES_PACIENTE
    assert _estado(db_session, paciente.id) == antes


def test_patch_pacientes_ignora_un_campo_desconocido(
    client: TestClient, db_session: Session
) -> None:
    paciente = _existente(db_session)
    antes = _estado(db_session, paciente.id)

    respuesta = client.patch(f"/pacientes/{paciente.id}", json={"obra_social": "Ficticia"})

    assert respuesta.status_code == 200
    assert "obra_social" not in respuesta.json()
    assert _estado(db_session, paciente.id) == antes


def test_patch_pacientes_edita_a_un_paciente_desactivado_sin_reactivarlo(
    client: TestClient, db_session: Session
) -> None:
    paciente = _existente(db_session, activo=False)

    respuesta = client.patch(f"/pacientes/{paciente.id}", json={"telefono": "+54 11 5555-0199"})

    assert respuesta.status_code == 200
    assert respuesta.json()["telefono"] == "+54 11 5555-0199"
    assert respuesta.json()["activo"] is False
    assert _estado(db_session, paciente.id)["activo"] is False


def test_patch_pacientes_inexistente_responde_404(client: TestClient) -> None:
    respuesta = client.patch(f"/pacientes/{uuid4()}", json={"telefono": "+54 11 5555-0199"})

    assert respuesta.status_code == 404
    assert respuesta.json() == {"detail": {"codigo": "recurso_inexistente", "recurso": "paciente"}}


def test_patch_pacientes_con_id_mal_formado_responde_422(client: TestClient) -> None:
    respuesta = client.patch("/pacientes/no-es-un-id", json={"telefono": "+54 11 5555-0199"})

    assert respuesta.status_code == 422


# --- La edición aplica las mismas validaciones que el alta (D15, D16) ----------------------


@pytest.mark.parametrize("campo", TEXTOS)
def test_patch_pacientes_con_caracter_nulo_responde_422_no_500_y_no_cambia(
    client: TestClient, db_session: Session, campo: str
) -> None:
    paciente = _existente(db_session)
    antes = _estado(db_session, paciente.id)
    valor = "a\x00b@example.com" if campo == "email" else "a\x00b"

    respuesta = client.patch(f"/pacientes/{paciente.id}", json={campo: valor})

    assert respuesta.status_code == 422
    assert _estado(db_session, paciente.id) == antes


@pytest.mark.parametrize("campo", TEXTOS)
def test_patch_pacientes_con_un_texto_mas_largo_que_su_columna_responde_422_no_500(
    client: TestClient, db_session: Session, campo: str
) -> None:
    paciente = _existente(db_session)
    antes = _estado(db_session, paciente.id)

    respuesta = client.patch(
        f"/pacientes/{paciente.id}", json={campo: _valor_de_largo(campo, LARGOS[campo] + 1)}
    )

    assert respuesta.status_code == 422
    assert _estado(db_session, paciente.id) == antes


@pytest.mark.parametrize("campo", TEXTOS)
def test_patch_pacientes_acepta_el_largo_maximo_en_cada_texto(
    client: TestClient, db_session: Session, campo: str
) -> None:
    paciente = _existente(db_session)
    valor = _valor_de_largo(campo, LARGOS[campo])

    respuesta = client.patch(f"/pacientes/{paciente.id}", json={campo: valor})

    assert respuesta.status_code == 200
    assert respuesta.json()[campo] == valor


def test_patch_pacientes_con_email_mal_formado_responde_422_y_conserva_el_email(
    client: TestClient, db_session: Session
) -> None:
    paciente = _existente(db_session)
    paciente.email = "carla@example.com"
    db_session.flush()

    respuesta = client.patch(f"/pacientes/{paciente.id}", json={"email": "no-es-un-email"})

    assert respuesta.status_code == 422
    assert _estado(db_session, paciente.id)["email"] == "carla@example.com"


def test_patch_pacientes_con_documento_repetido_responde_409_y_conserva_el_propio(
    client: TestClient, db_session: Session
) -> None:
    _existente(db_session, "FIC-0101")
    otro = _existente(db_session, "FIC-0102", nombre="Diego")

    respuesta = client.patch(f"/pacientes/{otro.id}", json={"documento": " FIC-0101 "})

    assert respuesta.status_code == 409
    assert respuesta.json() == CUERPO_DUPLICADO
    assert _estado(db_session, otro.id)["documento"] == "FIC-0102"


def test_patch_pacientes_con_el_propio_documento_no_es_un_duplicado(
    client: TestClient, db_session: Session
) -> None:
    paciente = _existente(db_session)

    respuesta = client.patch(f"/pacientes/{paciente.id}", json={"documento": "FIC-0101"})

    assert respuesta.status_code == 200


def test_patch_pacientes_tras_un_409_la_misma_sesion_sigue_editando(
    client: TestClient, db_session: Session
) -> None:
    _existente(db_session, "FIC-0101")
    otro = _existente(db_session, "FIC-0102", nombre="Diego")
    assert client.patch(f"/pacientes/{otro.id}", json={"documento": "FIC-0101"}).status_code == 409

    respuesta = client.patch(f"/pacientes/{otro.id}", json={"telefono": "+54 11 5555-0199"})

    assert respuesta.status_code == 200


# --- Estado de actividad no editable -------------------------------------------------------


@pytest.mark.parametrize("activo", [True, False])
def test_post_pacientes_con_activo_responde_campo_no_editable_y_no_persiste(
    client: TestClient, db_session: Session, activo: bool
) -> None:
    respuesta = client.post("/pacientes", json=_body(activo=activo))

    assert respuesta.status_code == 422
    detalle = respuesta.json()["detail"]
    assert detalle["codigo"] == "campo_no_editable"
    assert detalle["campos"] == ["activo"]
    assert _cantidad(db_session) == 0


def test_patch_pacientes_con_activo_true_no_reactiva_a_un_desactivado(
    client: TestClient, db_session: Session
) -> None:
    paciente = _existente(db_session, activo=False)

    respuesta = client.patch(f"/pacientes/{paciente.id}", json={"activo": True})

    assert respuesta.status_code == 422
    detalle = respuesta.json()["detail"]
    assert (detalle["codigo"], detalle["campos"]) == ("campo_no_editable", ["activo"])
    assert _estado(db_session, paciente.id)["activo"] is False


def test_patch_pacientes_con_activo_false_no_desactiva_y_no_aplica_el_resto(
    client: TestClient, db_session: Session
) -> None:
    paciente = _existente(db_session)
    antes = _estado(db_session, paciente.id)

    respuesta = client.patch(
        f"/pacientes/{paciente.id}", json={"activo": False, "telefono": "+54 11 5555-0199"}
    )

    assert respuesta.status_code == 422
    assert respuesta.json()["detail"]["codigo"] == "campo_no_editable"
    assert _estado(db_session, paciente.id) == antes


@pytest.mark.parametrize("activo", [None, "si", 1, [], {}])
def test_patch_pacientes_con_activo_de_cualquier_valor_responde_campo_no_editable(
    client: TestClient, db_session: Session, activo: object
) -> None:
    paciente = _existente(db_session)

    respuesta = client.patch(f"/pacientes/{paciente.id}", json={"activo": activo})

    assert respuesta.status_code == 422
    assert respuesta.json()["detail"]["codigo"] == "campo_no_editable"


def test_patch_pacientes_con_activo_se_evalua_antes_que_la_existencia(client: TestClient) -> None:
    respuesta = client.patch(f"/pacientes/{uuid4()}", json={"activo": True})

    assert respuesta.status_code == 422
    assert respuesta.json()["detail"]["codigo"] == "campo_no_editable"
