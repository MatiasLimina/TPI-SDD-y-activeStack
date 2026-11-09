"""API de pacientes (lectura de la recepcionista): listado, búsqueda, paginación y detalle."""

from itertools import count
from typing import Any
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.infrastructure.db.models import Paciente

CLAVES_PACIENTE = {"id", "nombre", "apellido", "documento", "telefono", "email", "activo"}
_numero = count(1)


def _paciente(
    session: Session,
    nombre: str,
    apellido: str,
    documento: str | None = None,
    *,
    activo: bool = True,
    email: str | None = None,
) -> Paciente:
    paciente = Paciente(
        nombre=nombre,
        apellido=apellido,
        documento=documento or f"FIC-{next(_numero):05d}",
        telefono="+54 11 5555-0101",
        email=email,
        activo=activo,
    )
    session.add(paciente)
    session.flush()
    return paciente


def _nombres(respuesta: Any) -> list[str]:
    assert respuesta.status_code == 200, respuesta.text
    return [f"{p['nombre']} {p['apellido']}" for p in respuesta.json()]


# --- Listado de pacientes -----------------------------------------------------------------


def test_get_pacientes_lista_activos_e_inactivos_ordenados_por_apellido_y_nombre(
    client: TestClient, db_session: Session
) -> None:
    _paciente(db_session, "Zoe", "Alfa")
    _paciente(db_session, "Ana", "Beta", activo=False)
    _paciente(db_session, "Bruno", "Beta")

    respuesta = client.get("/pacientes")

    assert _nombres(respuesta) == ["Zoe Alfa", "Ana Beta", "Bruno Beta"]
    assert [p["activo"] for p in respuesta.json()] == [True, False, True]


def test_get_pacientes_cada_item_trae_exactamente_las_siete_claves(
    client: TestClient, db_session: Session
) -> None:
    creado = _paciente(db_session, "Carla", "Imaginaria", "FIC-0101", email="carla@example.com")

    (item,) = client.get("/pacientes").json()

    assert set(item) == CLAVES_PACIENTE
    assert item == {
        "id": str(creado.id),
        "nombre": "Carla",
        "apellido": "Imaginaria",
        "documento": "FIC-0101",
        "telefono": "+54 11 5555-0101",
        "email": "carla@example.com",
        "activo": True,
    }


def test_get_pacientes_sin_pacientes_responde_lista_vacia(client: TestClient) -> None:
    respuesta = client.get("/pacientes")

    assert respuesta.status_code == 200
    assert respuesta.json() == []


# --- Búsqueda de pacientes ----------------------------------------------------------------


@pytest.fixture
def agenda_de_pacientes(db_session: Session) -> None:
    _paciente(db_session, "Carla", "Imaginaria", "FIC-0101")
    _paciente(db_session, "Diego", "Supuesto", "FIC-0202")


@pytest.mark.parametrize(
    ("q", "esperado"),
    [
        ("magin", ["Carla Imaginaria"]),
        ("dieg", ["Diego Supuesto"]),
        ("0202", ["Diego Supuesto"]),
    ],
    ids=["apellido", "nombre", "documento"],
)
def test_get_pacientes_con_q_coincide_por_parte_de_apellido_nombre_o_documento(
    client: TestClient, agenda_de_pacientes: None, q: str, esperado: list[str]
) -> None:
    assert _nombres(client.get("/pacientes", params={"q": q})) == esperado


def test_get_pacientes_con_q_no_distingue_mayusculas(
    client: TestClient, agenda_de_pacientes: None
) -> None:
    assert _nombres(client.get("/pacientes", params={"q": "IMAGINARIA"})) == ["Carla Imaginaria"]
    assert _nombres(client.get("/pacientes", params={"q": "fic-0101"})) == ["Carla Imaginaria"]


def test_get_pacientes_con_q_no_distingue_acentos_en_ningun_sentido(
    client: TestClient, db_session: Session
) -> None:
    _paciente(db_session, "Lucía", "Pérez Ficticia")
    _paciente(db_session, "Tomás", "Nuñez Inventado")

    assert _nombres(client.get("/pacientes", params={"q": "perez"})) == ["Lucía Pérez Ficticia"]
    assert _nombres(client.get("/pacientes", params={"q": "PÉREZ"})) == ["Lucía Pérez Ficticia"]
    assert _nombres(client.get("/pacientes", params={"q": "nunez"})) == ["Tomás Nuñez Inventado"]


def test_get_pacientes_con_varios_terminos_exige_todos_en_cualquier_orden(
    client: TestClient, db_session: Session
) -> None:
    _paciente(db_session, "Carla", "Imaginaria")
    _paciente(db_session, "Carla", "Supuesta")
    _paciente(db_session, "Diego", "Imaginario")

    assert _nombres(client.get("/pacientes?q=imag%20carla")) == ["Carla Imaginaria"]
    assert _nombres(client.get("/pacientes?q=carla%20imag")) == ["Carla Imaginaria"]


def test_get_pacientes_sin_coincidencias_responde_lista_vacia(
    client: TestClient, agenda_de_pacientes: None
) -> None:
    respuesta = client.get("/pacientes?q=zzz-no-existe")

    assert respuesta.status_code == 200
    assert respuesta.json() == []


def test_get_pacientes_toma_los_comodines_como_texto(
    client: TestClient, db_session: Session
) -> None:
    _paciente(db_session, "Uno", "Guion", "FIC-0101")
    _paciente(db_session, "Dos", "Bajo", "FIC_0102")

    assert _nombres(client.get("/pacientes?q=%25")) == []
    assert _nombres(client.get("/pacientes?q=FIC_")) == ["Dos Bajo"]
    assert _nombres(client.get("/pacientes?q=%5C")) == []


def test_get_pacientes_con_q_incluye_a_un_desactivado_con_activo_falso(
    client: TestClient, db_session: Session
) -> None:
    _paciente(db_session, "Carla", "Imaginaria", "FIC-0101", activo=False)

    respuesta = client.get("/pacientes?q=FIC-0101")

    assert _nombres(respuesta) == ["Carla Imaginaria"]
    assert respuesta.json()[0]["activo"] is False


@pytest.mark.parametrize("q", ["%20%20", "", "%09"], ids=["espacios", "vacio", "tab"])
def test_get_pacientes_con_q_en_blanco_lista_sin_filtrar(
    client: TestClient, db_session: Session, q: str
) -> None:
    _paciente(db_session, "Carla", "Imaginaria")
    _paciente(db_session, "Diego", "Supuesto")

    assert _nombres(client.get(f"/pacientes?q={q}")) == ["Carla Imaginaria", "Diego Supuesto"]


def test_get_pacientes_con_q_de_101_caracteres_responde_422(client: TestClient) -> None:
    respuesta = client.get("/pacientes", params={"q": "a" * 101})

    assert respuesta.status_code == 422


def test_get_pacientes_con_q_de_100_caracteres_responde_200(client: TestClient) -> None:
    respuesta = client.get("/pacientes", params={"q": "a" * 100})

    assert respuesta.status_code == 200


def test_get_pacientes_con_q_con_caracter_nulo_responde_422_no_500(client: TestClient) -> None:
    respuesta = client.get("/pacientes?q=a%00b")

    assert respuesta.status_code == 422


# --- Paginación del listado de pacientes --------------------------------------------------


def test_get_pacientes_por_defecto_devuelve_los_primeros_50_del_orden(
    client: TestClient, db_session: Session
) -> None:
    for n in range(51):
        _paciente(db_session, f"Nombre{n:02d}", "Apellido")

    respuesta = client.get("/pacientes")

    assert _nombres(respuesta) == [f"Nombre{n:02d} Apellido" for n in range(50)]


def test_get_pacientes_pagina_sin_repetidos_con_apellido_y_nombre_iguales(
    client: TestClient, db_session: Session
) -> None:
    creados = {str(_paciente(db_session, "Igual", "Igual").id) for _ in range(5)}

    paginas = [
        client.get("/pacientes", params={"limite": 2, "desplazamiento": desplazamiento}).json()
        for desplazamiento in (0, 2, 4)
    ]

    assert [len(pagina) for pagina in paginas] == [2, 2, 1]
    vistos = [p["id"] for pagina in paginas for p in pagina]
    assert len(vistos) == 5
    assert set(vistos) == creados


def test_get_pacientes_con_q_y_paginacion_recorta_el_resultado_filtrado(
    client: TestClient, db_session: Session
) -> None:
    for n in range(3):
        _paciente(db_session, f"Nombre{n}", "Imaginaria")
    for n in range(2):
        _paciente(db_session, f"Otro{n}", "Supuesto")

    respuesta = client.get("/pacientes?q=imaginaria&limite=2&desplazamiento=2")

    assert _nombres(respuesta) == ["Nombre2 Imaginaria"]


def test_get_pacientes_con_limite_maximo_de_100_responde_200(client: TestClient) -> None:
    assert client.get("/pacientes?limite=100").status_code == 200


def test_get_pacientes_con_limite_100_devuelve_hasta_100(
    client: TestClient, db_session: Session
) -> None:
    for n in range(101):
        _paciente(db_session, f"Nombre{n:03d}", "Apellido")

    assert len(client.get("/pacientes?limite=100").json()) == 100


@pytest.mark.parametrize(
    "consulta",
    [
        "limite=0",
        "limite=101",
        "desplazamiento=-1",
        "desplazamiento=9223372036854775808",
        "limite=abc",
    ],
)
def test_get_pacientes_con_paginacion_fuera_de_rango_responde_422(
    client: TestClient, consulta: str
) -> None:
    assert client.get(f"/pacientes?{consulta}").status_code == 422


def test_get_pacientes_con_el_mayor_desplazamiento_admitido_responde_lista_vacia(
    client: TestClient, db_session: Session
) -> None:
    _paciente(db_session, "Carla", "Imaginaria")

    respuesta = client.get("/pacientes?desplazamiento=9223372036854775807")

    assert (respuesta.status_code, respuesta.json()) == (200, [])


def test_get_pacientes_con_desplazamiento_mayor_al_total_responde_lista_vacia(
    client: TestClient, db_session: Session
) -> None:
    _paciente(db_session, "Carla", "Imaginaria")

    respuesta = client.get("/pacientes?desplazamiento=10")

    assert respuesta.status_code == 200
    assert respuesta.json() == []


# --- Detalle de un paciente para la recepcionista -------------------------------------------


def test_get_paciente_devuelve_el_detalle_completo(client: TestClient, db_session: Session) -> None:
    creado = _paciente(db_session, "Carla", "Imaginaria", "FIC-0101", email="carla@example.com")

    respuesta = client.get(f"/pacientes/{creado.id}")

    assert respuesta.status_code == 200
    assert respuesta.json() == {
        "id": str(creado.id),
        "nombre": "Carla",
        "apellido": "Imaginaria",
        "documento": "FIC-0101",
        "telefono": "+54 11 5555-0101",
        "email": "carla@example.com",
        "activo": True,
    }


def test_get_paciente_desactivado_responde_200_con_activo_falso(
    client: TestClient, db_session: Session
) -> None:
    creado = _paciente(db_session, "Carla", "Imaginaria", activo=False)

    respuesta = client.get(f"/pacientes/{creado.id}")

    assert respuesta.status_code == 200
    assert respuesta.json()["activo"] is False
    assert set(respuesta.json()) == CLAVES_PACIENTE


def test_get_paciente_inexistente_responde_404(client: TestClient) -> None:
    respuesta = client.get(f"/pacientes/{uuid4()}")

    assert respuesta.status_code == 404
    assert respuesta.json() == {"detail": {"codigo": "recurso_inexistente", "recurso": "paciente"}}


def test_get_paciente_con_id_mal_formado_responde_422(client: TestClient) -> None:
    assert client.get("/pacientes/no-es-un-id").status_code == 422
