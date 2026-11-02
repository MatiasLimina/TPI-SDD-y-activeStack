"""Instantánea del turno para la auditoría: pura, sin base de datos ni FastAPI."""

import ast
import json
from datetime import UTC, datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4

import pytest

from app.domain.auditoria import AccionAuditoria, instantanea_turno
from app.domain.turnos import TurnoCreado, TurnoRegistrado

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
INICIO_UTC = datetime(2026, 10, 8, 13, 0, tzinfo=UTC)


def _creado() -> TurnoCreado:
    return TurnoCreado(
        id=uuid4(),
        profesional_id=uuid4(),
        paciente_id=uuid4(),
        prestacion_id=uuid4(),
        sillon_id=uuid4(),
        inicio=INICIO_UTC,
        fin=INICIO_UTC + timedelta(minutes=45),
        duracion_min=45,
        creado_por=uuid4(),
    )


def _cancelado_sin_sillon() -> TurnoRegistrado:
    return TurnoRegistrado(
        id=uuid4(),
        profesional_id=uuid4(),
        paciente_id=uuid4(),
        prestacion_id=uuid4(),
        sillon_id=None,
        inicio=INICIO_UTC,
        fin=INICIO_UTC + timedelta(minutes=20),
        duracion_min=20,
        estado="cancelado",
        motivo_cancelacion="El paciente avisó que no viene",
    )


def test_instantanea_turno_creado_tiene_exactamente_las_nueve_claves_fijas() -> None:
    turno = _creado()

    resultado = instantanea_turno(turno)

    assert set(resultado) == CLAVES
    assert resultado == {
        "profesional_id": str(turno.profesional_id),
        "paciente_id": str(turno.paciente_id),
        "prestacion_id": str(turno.prestacion_id),
        "sillon_id": str(turno.sillon_id),
        "inicio": "2026-10-08T13:00:00+00:00",
        "fin": "2026-10-08T13:45:00+00:00",
        "duracion_min": 45,
        "estado": "programado",
        "motivo_cancelacion": None,
    }


def test_instantanea_turno_registrado_cancelado_sin_sillon_lleva_nulo_y_motivo() -> None:
    turno = _cancelado_sin_sillon()

    resultado = instantanea_turno(turno)

    assert set(resultado) == CLAVES
    assert resultado["sillon_id"] is None
    assert resultado["estado"] == "cancelado"
    assert resultado["motivo_cancelacion"] == "El paciente avisó que no viene"
    assert resultado["duracion_min"] == 20
    assert resultado["fin"] == "2026-10-08T13:20:00+00:00"


def test_instantanea_no_incluye_el_id_del_turno_ni_el_autor() -> None:
    resultado = instantanea_turno(_creado())

    assert "id" not in resultado
    assert "creado_por" not in resultado


@pytest.mark.parametrize(
    ("zona", "inicio_local"),
    [
        (timezone(timedelta(hours=-3)), datetime(2026, 10, 8, 10, 0)),
        (timezone(timedelta(hours=5, minutes=30)), datetime(2026, 10, 8, 18, 30)),
    ],
)
def test_instantanea_convierte_instantes_con_zona_al_mismo_instante_en_utc(
    zona: timezone, inicio_local: datetime
) -> None:
    inicio = inicio_local.replace(tzinfo=zona)
    turno = TurnoRegistrado(
        **{
            **vars(_cancelado_sin_sillon()),
            "inicio": inicio,
            "fin": inicio + timedelta(minutes=20),
        }
    )

    resultado = instantanea_turno(turno)

    assert resultado["inicio"] == "2026-10-08T13:00:00+00:00"
    assert resultado["fin"] == "2026-10-08T13:20:00+00:00"


def test_instantanea_es_serializable_como_json_y_se_recupera_igual() -> None:
    for turno in (_creado(), _cancelado_sin_sillon()):
        resultado = instantanea_turno(turno)

        assert json.loads(json.dumps(resultado)) == resultado


def test_accion_auditoria_tiene_exactamente_crear_reprogramar_y_cancelar() -> None:
    assert {accion.value for accion in AccionAuditoria} == {"crear", "reprogramar", "cancelar"}
    assert AccionAuditoria.CREAR == "crear"
    assert AccionAuditoria.REPROGRAMAR == "reprogramar"
    assert AccionAuditoria.CANCELAR == "cancelar"


def test_el_dominio_de_auditoria_no_importa_sqlalchemy_ni_fastapi() -> None:
    ruta = Path(__file__).parents[2] / "app" / "domain" / "auditoria.py"
    importados: set[str] = set()
    for nodo in ast.walk(ast.parse(ruta.read_text("utf-8"))):
        if isinstance(nodo, ast.Import):
            importados.update(alias.name.split(".")[0] for alias in nodo.names)
        elif isinstance(nodo, ast.ImportFrom) and nodo.module and nodo.level == 0:
            importados.add(nodo.module.split(".")[0])

    assert "app" in importados  # el parseo detecta imports reales
    assert importados.isdisjoint({"sqlalchemy", "fastapi"})
