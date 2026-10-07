"""POST /turnos de punta a punta: FastAPI + caso de uso + PostgreSQL real, con reloj fijo."""

from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from app.api.turnos import get_reloj
from app.infrastructure.db.models import Turno
from tests.integration.factories import Catalogo, crear_catalogo

AHORA = datetime(2026, 10, 7, 12, 0, tzinfo=UTC)  # 2026-10-07 09:00 hora local


@pytest.fixture
def catalogo(db_session: Session) -> Catalogo:
    return crear_catalogo(db_session)


@pytest.fixture
def api(client: TestClient) -> TestClient:
    client.app.dependency_overrides[get_reloj] = lambda: lambda: AHORA  # type: ignore[attr-defined]
    return client


def _hora(hora: int, minuto: int = 0, segundo: int = 0, dia: int = 8) -> str:
    return f"2026-10-{dia:02d}T{hora:02d}:{minuto:02d}:{segundo:02d}-03:00"


def _body(c: Catalogo, **cambios: Any) -> dict[str, Any]:
    body: dict[str, Any] = {
        "profesional_id": str(c.profesionales[0].id),
        "paciente_id": str(c.pacientes[0].id),
        "prestacion_id": str(c.limpieza.id),
        "sillon_id": str(c.sillones[0].id),
        "inicio": _hora(10),
    }
    body.update(cambios)
    return {k: v for k, v in body.items() if v is not ...}


def _cantidad_turnos(session: Session) -> int:
    return session.scalar(select(func.count()).select_from(Turno)) or 0


# --- 6.1 alta válida ---------------------------------------------------------------------


def test_post_turno_valido_responde_201_con_instantes_en_hora_local(
    api: TestClient, db_session: Session, catalogo: Catalogo
) -> None:
    respuesta = api.post("/turnos", json=_body(catalogo))

    assert respuesta.status_code == 201
    cuerpo = respuesta.json()
    assert cuerpo["estado"] == "programado"
    assert cuerpo["inicio"] == "2026-10-08T10:00:00-03:00"
    assert cuerpo["fin"] == "2026-10-08T10:45:00-03:00"
    assert cuerpo["duracion_min"] == 45
    assert cuerpo["creado_por"] is None
    assert cuerpo["sillon_id"] == str(catalogo.sillones[0].id)
    inicio_utc = db_session.execute(
        text("SELECT inicio AT TIME ZONE 'UTC' FROM turno WHERE id = :id"), {"id": cuerpo["id"]}
    ).scalar_one()
    assert inicio_utc == datetime(2026, 10, 8, 13, 0)


def test_post_turno_con_inicio_en_utc_se_presenta_en_hora_local(
    api: TestClient, catalogo: Catalogo
) -> None:
    respuesta = api.post("/turnos", json=_body(catalogo, inicio="2026-10-08T13:00:00Z"))

    assert respuesta.status_code == 201
    assert respuesta.json()["inicio"] == "2026-10-08T10:00:00-03:00"


def test_post_turno_con_duracion_ajustada(api: TestClient, catalogo: Catalogo) -> None:
    respuesta = api.post("/turnos", json=_body(catalogo, duracion_min=60))

    assert respuesta.status_code == 201
    assert (respuesta.json()["duracion_min"], respuesta.json()["fin"]) == (
        60,
        "2026-10-08T11:00:00-03:00",
    )


def test_router_de_turnos_esta_registrado_en_la_app(client: TestClient) -> None:
    rutas = client.get("/openapi.json").json()["paths"]

    assert "post" in rutas["/turnos"]


# --- 6.2 422 por reglas -------------------------------------------------------------------


def test_inicio_sin_zona_horaria_responde_422_sin_persistir(
    api: TestClient, db_session: Session, catalogo: Catalogo
) -> None:
    respuesta = api.post("/turnos", json=_body(catalogo, inicio="2026-10-08T10:00:00"))

    assert respuesta.status_code == 422
    assert _cantidad_turnos(db_session) == 0


@pytest.mark.parametrize(
    ("cambios", "codigo"),
    [
        ({"duracion_min": 42}, "duracion_invalida"),
        ({"duracion_min": 485}, "duracion_invalida"),
        ({"duracion_min": 0}, "duracion_invalida"),
        ({"duracion_min": -5}, "duracion_invalida"),
        ({"inicio": _hora(10, 7)}, "inicio_no_alineado"),
        ({"inicio": _hora(10, 5, 30)}, "inicio_no_alineado"),
        ({"inicio": _hora(8, 55, dia=7)}, "inicio_en_pasado"),
        ({"sillon_id": ...}, "sillon_requerido"),
    ],
)
def test_reglas_de_dominio_violadas_responden_422_con_codigo(
    api: TestClient,
    db_session: Session,
    catalogo: Catalogo,
    cambios: dict[str, Any],
    codigo: str,
) -> None:
    respuesta = api.post("/turnos", json=_body(catalogo, **cambios))

    assert respuesta.status_code == 422
    assert respuesta.json()["detail"]["codigo"] == codigo
    assert respuesta.json()["detail"]["mensaje"]
    assert _cantidad_turnos(db_session) == 0


def test_sillon_sobrante_con_prestacion_sin_sillon_responde_422(
    api: TestClient, db_session: Session, catalogo: Catalogo
) -> None:
    respuesta = api.post("/turnos", json=_body(catalogo, prestacion_id=str(catalogo.consulta.id)))

    assert respuesta.status_code == 422
    assert respuesta.json()["detail"]["codigo"] == "sillon_no_corresponde"
    assert _cantidad_turnos(db_session) == 0


# --- 6.3 422 por referencias ---------------------------------------------------------------


@pytest.mark.parametrize("referencia", ["profesional", "paciente", "prestacion", "sillon"])
def test_referencia_inexistente_responde_422_y_no_404(
    api: TestClient, catalogo: Catalogo, referencia: str
) -> None:
    respuesta = api.post("/turnos", json=_body(catalogo, **{f"{referencia}_id": str(uuid4())}))

    assert respuesta.status_code == 422
    assert respuesta.json()["detail"] == {
        "codigo": "referencia_invalida",
        "referencia": referencia,
        "motivo": "inexistente",
    }


def test_sillon_inactivo_responde_422_indicando_sillon(
    api: TestClient, db_session: Session, catalogo: Catalogo
) -> None:
    catalogo.sillones[0].activo = False
    db_session.flush()

    respuesta = api.post("/turnos", json=_body(catalogo))

    assert respuesta.status_code == 422
    assert respuesta.json()["detail"]["referencia"] == "sillon"
    assert respuesta.json()["detail"]["motivo"] == "inactiva"


def test_prestacion_inactiva_responde_422_indicando_prestacion(
    api: TestClient, db_session: Session, catalogo: Catalogo
) -> None:
    catalogo.limpieza.activa = False
    db_session.flush()

    respuesta = api.post("/turnos", json=_body(catalogo))

    assert respuesta.status_code == 422
    assert respuesta.json()["detail"]["referencia"] == "prestacion"
    assert respuesta.json()["detail"]["motivo"] == "inactiva"


# --- 6.4 409 -------------------------------------------------------------------------------


def _alta(api: TestClient, body: dict[str, Any]) -> None:
    assert api.post("/turnos", json=body).status_code == 201


def test_solape_por_profesional_responde_409(
    api: TestClient, db_session: Session, catalogo: Catalogo
) -> None:
    _alta(api, _body(catalogo))

    respuesta = api.post(
        "/turnos",
        json=_body(
            catalogo,
            inicio=_hora(10, 30),
            duracion_min=30,
            sillon_id=str(catalogo.sillones[1].id),
            paciente_id=str(catalogo.pacientes[1].id),
        ),
    )

    assert respuesta.status_code == 409
    assert respuesta.json()["detail"] == {"codigo": "solapamiento", "recursos": ["profesional"]}
    assert _cantidad_turnos(db_session) == 1


def test_solape_por_sillon_responde_409(api: TestClient, catalogo: Catalogo) -> None:
    _alta(api, _body(catalogo))

    respuesta = api.post(
        "/turnos",
        json=_body(
            catalogo,
            inicio=_hora(10, 15),
            duracion_min=30,
            profesional_id=str(catalogo.profesionales[1].id),
            paciente_id=str(catalogo.pacientes[1].id),
        ),
    )

    assert respuesta.status_code == 409
    assert respuesta.json()["detail"]["recursos"] == ["sillon"]


def test_solape_por_paciente_con_distinto_profesional_responde_409(
    api: TestClient, catalogo: Catalogo
) -> None:
    _alta(api, _body(catalogo))

    respuesta = api.post(
        "/turnos",
        json=_body(
            catalogo,
            inicio=_hora(10, 30),
            duracion_min=30,
            profesional_id=str(catalogo.profesionales[1].id),
            sillon_id=str(catalogo.sillones[1].id),
        ),
    )

    assert respuesta.status_code == 409
    assert respuesta.json()["detail"]["recursos"] == ["paciente"]


def test_409_lista_todos_los_recursos_en_orden_fijo(api: TestClient, catalogo: Catalogo) -> None:
    _alta(api, _body(catalogo))

    respuesta = api.post("/turnos", json=_body(catalogo, inicio=_hora(10, 15), duracion_min=45))

    assert respuesta.status_code == 409
    assert respuesta.json()["detail"]["recursos"] == ["profesional", "sillon", "paciente"]


def test_solicitud_invalida_y_en_conflicto_responde_422_no_409(
    api: TestClient, catalogo: Catalogo
) -> None:
    _alta(api, _body(catalogo))

    respuesta = api.post("/turnos", json=_body(catalogo, inicio=_hora(10, 15), duracion_min=42))

    assert respuesta.status_code == 422


# --- 6.5 aceptados --------------------------------------------------------------------------


def test_turnos_contiguos_del_mismo_profesional_y_sillon_se_aceptan(
    api: TestClient, catalogo: Catalogo
) -> None:
    _alta(api, _body(catalogo))

    respuesta = api.post(
        "/turnos",
        json=_body(
            catalogo,
            inicio=_hora(10, 45),
            duracion_min=45,
            paciente_id=str(catalogo.pacientes[1].id),
        ),
    )

    assert respuesta.status_code == 201


def test_mismo_paciente_en_turnos_contiguos_se_acepta(api: TestClient, catalogo: Catalogo) -> None:
    _alta(api, _body(catalogo))

    respuesta = api.post(
        "/turnos",
        json=_body(
            catalogo,
            inicio=_hora(10, 45),
            duracion_min=30,
            profesional_id=str(catalogo.profesionales[1].id),
            sillon_id=str(catalogo.sillones[1].id),
        ),
    )

    assert respuesta.status_code == 201


def test_mismo_horario_con_recursos_distintos_se_acepta(
    api: TestClient, catalogo: Catalogo
) -> None:
    _alta(api, _body(catalogo))

    respuesta = api.post(
        "/turnos",
        json=_body(
            catalogo,
            profesional_id=str(catalogo.profesionales[1].id),
            sillon_id=str(catalogo.sillones[1].id),
            paciente_id=str(catalogo.pacientes[1].id),
        ),
    )

    assert respuesta.status_code == 201


def test_prestacion_sin_sillon_no_genera_conflicto_de_sillon(
    api: TestClient, catalogo: Catalogo
) -> None:
    _alta(
        api,
        _body(catalogo, prestacion_id=str(catalogo.consulta.id), sillon_id=..., inicio=_hora(10)),
    )

    respuesta = api.post(
        "/turnos",
        json=_body(
            catalogo,
            profesional_id=str(catalogo.profesionales[1].id),
            paciente_id=str(catalogo.pacientes[1].id),
        ),
    )

    assert respuesta.status_code == 201


def test_turno_cancelado_preexistente_no_bloquea_el_horario(
    api: TestClient, db_session: Session, catalogo: Catalogo
) -> None:
    inicio = datetime(2026, 10, 8, 13, 0, tzinfo=UTC)
    db_session.add(
        Turno(
            profesional_id=catalogo.profesionales[0].id,
            sillon_id=catalogo.sillones[0].id,
            paciente_id=catalogo.pacientes[0].id,
            prestacion_id=catalogo.limpieza.id,
            inicio=inicio,
            fin=inicio + timedelta(minutes=45),
            duracion_min=45,
            estado="cancelado",
        )
    )
    db_session.flush()

    respuesta = api.post("/turnos", json=_body(catalogo))

    assert respuesta.status_code == 201


def test_duracion_de_480_minutos_se_acepta(api: TestClient, catalogo: Catalogo) -> None:
    respuesta = api.post("/turnos", json=_body(catalogo, inicio=_hora(8), duracion_min=480))

    assert respuesta.status_code == 201
    assert respuesta.json()["fin"] == "2026-10-08T16:00:00-03:00"
