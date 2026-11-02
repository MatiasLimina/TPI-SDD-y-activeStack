import ast
import dataclasses
from datetime import UTC, datetime
from pathlib import Path
from types import ModuleType
from uuid import UUID, uuid4

import pytest

import app.domain.notificaciones as notificaciones
import app.domain.recordatorios as recordatorios
from app.domain.notificaciones import MensajeRecordatorio, armar_mensaje

ZONA = "America/Argentina/Buenos_Aires"
CONSULTORIO = "Consultorio Odontológico Ejemplo"


def test_armar_mensaje_builds_exact_text_addressed_to_the_patient() -> None:
    recordatorio_id, paciente_id = uuid4(), uuid4()

    mensaje = armar_mensaje(
        recordatorio_id,
        paciente_id,
        datetime(2026, 10, 9, 13, 0, tzinfo=UTC),
        CONSULTORIO,
        ZONA,
    )

    assert mensaje.texto == (
        "Recordatorio: tiene un turno el 09/10/2026 a las 10:00 "
        "en Consultorio Odontológico Ejemplo."
    )
    assert mensaje.paciente_id == paciente_id
    assert mensaje.recordatorio_id == recordatorio_id


@pytest.mark.parametrize(
    ("inicio_utc", "fecha", "hora"),
    [
        (datetime(2026, 10, 10, 2, 0, tzinfo=UTC), "09/10/2026", "23:00"),
        (datetime(2026, 10, 9, 3, 5, tzinfo=UTC), "09/10/2026", "00:05"),
        (datetime(2026, 1, 1, 2, 59, tzinfo=UTC), "31/12/2025", "23:59"),
    ],
)
def test_armar_mensaje_presents_date_and_time_in_local_zone(
    inicio_utc: datetime, fecha: str, hora: str
) -> None:
    mensaje = armar_mensaje(uuid4(), uuid4(), inicio_utc, CONSULTORIO, ZONA)

    assert f"el {fecha} a las {hora} en" in mensaje.texto


def test_armar_mensaje_uses_the_given_consultorio_name() -> None:
    mensaje = armar_mensaje(
        uuid4(), uuid4(), datetime(2026, 10, 9, 13, 0, tzinfo=UTC), "Clínica Ficticia Norte", ZONA
    )

    assert mensaje.texto.endswith("en Clínica Ficticia Norte.")


def test_mensaje_recordatorio_has_exactly_the_non_clinical_fields() -> None:
    assert {c.name for c in dataclasses.fields(MensajeRecordatorio)} == {
        "recordatorio_id",
        "paciente_id",
        "texto",
    }
    mensaje = MensajeRecordatorio(UUID(int=1), UUID(int=2), "texto")
    with pytest.raises(dataclasses.FrozenInstanceError):
        mensaje.texto = "otro"  # type: ignore[misc]


def _raices_importadas(modulo: ModuleType) -> set[str]:
    arbol = ast.parse(Path(str(modulo.__file__)).read_text(encoding="utf-8"))
    raices: set[str] = set()
    for nodo in ast.walk(arbol):
        if isinstance(nodo, ast.Import):
            raices |= {alias.name.split(".")[0] for alias in nodo.names}
        elif isinstance(nodo, ast.ImportFrom) and nodo.module:
            raices.add(nodo.module.split(".")[0])
    return raices


@pytest.mark.parametrize("modulo", [notificaciones, recordatorios])
def test_domain_modules_do_not_import_infrastructure(modulo: ModuleType) -> None:
    assert not _raices_importadas(modulo) & {"sqlalchemy", "redis", "fastapi"}


def test_raices_importadas_detects_forbidden_imports(tmp_path: Path) -> None:
    falso = tmp_path / "falso.py"
    codigo = "import redis.asyncio" + chr(10) + "from sqlalchemy.orm import Session"
    falso.write_text(codigo, encoding="utf-8")
    modulo = ModuleType("falso")
    modulo.__file__ = str(falso)

    assert _raices_importadas(modulo) == {"redis", "sqlalchemy"}
