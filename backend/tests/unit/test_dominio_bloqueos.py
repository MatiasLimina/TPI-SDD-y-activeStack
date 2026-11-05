"""Reglas de dominio de los bloqueos de agenda (RN-HB-02, RN-HB-03), sin base de datos."""

import ast
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID, uuid4

import pytest

from app.domain import bloqueos
from app.domain.bloqueos import (
    BloqueoInvalidoError,
    ProfesionalRequeridoError,
    resolver_profesional,
    validar_bloqueo,
)
from app.domain.horarios import ProfesionalAjenoError
from app.domain.usuarios import Rol, UsuarioAutenticado

MENSAJE = "el bloqueo debe tener fin posterior a inicio y un motivo no vacío"
MENSAJE_AJENO = "Solo podés operar sobre tus propios bloqueos"


def _utc(dia: int, hora: int, minuto: int = 0) -> datetime:
    return datetime(2026, 10, dia, hora, minuto, tzinfo=UTC)


def test_el_dominio_de_bloqueos_no_importa_sqlalchemy_ni_fastapi() -> None:
    arbol = ast.parse(Path(bloqueos.__file__).read_text(encoding="utf-8"))
    importados = {
        (nodo.module or "") if isinstance(nodo, ast.ImportFrom) else alias.name
        for nodo in ast.walk(arbol)
        if isinstance(nodo, ast.Import | ast.ImportFrom)
        for alias in (nodo.names if isinstance(nodo, ast.Import) else [None])
    }

    assert not any(m.split(".")[0] in {"sqlalchemy", "fastapi"} for m in importados)


def test_validar_bloqueo_acepta_una_franja_de_dos_horas_y_devuelve_el_motivo() -> None:
    motivo = validar_bloqueo(_utc(8, 13), _utc(8, 15), "Congreso")

    assert motivo == "Congreso"


def test_validar_bloqueo_devuelve_el_motivo_sin_espacios_en_los_extremos() -> None:
    assert validar_bloqueo(_utc(8, 13), _utc(8, 15), "  Congreso  ") == "Congreso"


def test_validar_bloqueo_conserva_los_espacios_internos_del_motivo() -> None:
    assert validar_bloqueo(_utc(8, 13), _utc(8, 15), " Congreso  anual ") == "Congreso  anual"


def test_validar_bloqueo_acepta_un_intervalo_de_varios_dias() -> None:
    motivo = validar_bloqueo(_utc(12, 3), _utc(17, 3), "Vacaciones")

    assert motivo == "Vacaciones"


@pytest.mark.parametrize(
    ("inicio", "fin", "motivo"),
    [
        (_utc(8, 13), _utc(8, 13), "Congreso"),  # fin igual al inicio
        (_utc(8, 15), _utc(8, 13), "Congreso"),  # fin anterior al inicio
        (_utc(8, 13), _utc(8, 15), ""),
        (_utc(8, 13), _utc(8, 15), "   "),
        (_utc(8, 13), _utc(8, 15), " \t\n "),
    ],
)
def test_validar_bloqueo_rechaza_intervalo_no_positivo_o_motivo_en_blanco(
    inicio: datetime, fin: datetime, motivo: str
) -> None:
    with pytest.raises(BloqueoInvalidoError) as excinfo:
        validar_bloqueo(inicio, fin, motivo)

    assert excinfo.value.mensaje == MENSAJE


def _odontologo(profesional_id: UUID) -> UsuarioAutenticado:
    return UsuarioAutenticado(id=uuid4(), rol=Rol.ODONTOLOGO, profesional_id=profesional_id)


def _recepcionista() -> UsuarioAutenticado:
    return UsuarioAutenticado(id=uuid4(), rol=Rol.RECEPCIONISTA, profesional_id=None)


def test_resolver_profesional_del_odontologo_sin_id_usa_el_suyo() -> None:
    propio = uuid4()

    assert resolver_profesional(_odontologo(propio), None) == propio


def test_resolver_profesional_del_odontologo_con_su_id_usa_el_suyo() -> None:
    propio = uuid4()

    assert resolver_profesional(_odontologo(propio), propio) == propio


@pytest.mark.parametrize("ajeno", [uuid4(), uuid4()])
def test_resolver_profesional_del_odontologo_con_otro_id_lanza_profesional_ajeno(
    ajeno: UUID,
) -> None:
    with pytest.raises(ProfesionalAjenoError) as excinfo:
        resolver_profesional(_odontologo(uuid4()), ajeno)

    assert str(excinfo.value) == MENSAJE_AJENO
    assert excinfo.value.mensaje == MENSAJE_AJENO


def test_resolver_profesional_de_la_recepcionista_con_id_usa_ese_id() -> None:
    elegido = uuid4()

    assert resolver_profesional(_recepcionista(), elegido) == elegido


def test_resolver_profesional_de_la_recepcionista_sin_id_lanza_profesional_requerido() -> None:
    with pytest.raises(ProfesionalRequeridoError) as excinfo:
        resolver_profesional(_recepcionista(), None)

    assert excinfo.value.codigo == "profesional_requerido"
    assert excinfo.value.mensaje == "indicá el profesional del bloqueo"


def test_profesional_ajeno_por_defecto_conserva_el_mensaje_del_horario() -> None:
    assert ProfesionalAjenoError().mensaje == "Solo podés consultar tu propio horario"
