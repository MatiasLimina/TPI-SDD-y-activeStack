from datetime import UTC, date, datetime
from uuid import UUID, uuid4

import pytest

from app.domain.agenda import (
    MAX_DIAS_AGENDA,
    RangoInvalidoError,
    rango_local_a_intervalo,
    resolver_profesional_agenda,
)
from app.domain.horarios import ProfesionalAjenoError
from app.domain.turnos import Intervalo
from app.domain.usuarios import Rol, UsuarioAutenticado


@pytest.mark.parametrize(
    ("desde", "hasta", "inicio", "fin"),
    [
        # un solo dia local
        (
            date(2026, 10, 8),
            date(2026, 10, 8),
            datetime(2026, 10, 8, 3, 0, tzinfo=UTC),
            datetime(2026, 10, 9, 3, 0, tzinfo=UTC),
        ),
        # semana completa (lunes a domingo)
        (
            date(2026, 10, 5),
            date(2026, 10, 11),
            datetime(2026, 10, 5, 3, 0, tzinfo=UTC),
            datetime(2026, 10, 12, 3, 0, tzinfo=UTC),
        ),
        # cruza el limite de mes: hasta + 1 dia cae en el mes siguiente
        (
            date(2026, 10, 30),
            date(2026, 10, 31),
            datetime(2026, 10, 30, 3, 0, tzinfo=UTC),
            datetime(2026, 11, 1, 3, 0, tzinfo=UTC),
        ),
    ],
)
def test_rango_local_a_intervalo_devuelve_instantes_utc_semiabiertos(
    desde: date, hasta: date, inicio: datetime, fin: datetime
) -> None:
    intervalo = rango_local_a_intervalo(desde, hasta)

    assert intervalo == Intervalo(inicio, fin)
    assert intervalo.inicio.tzinfo is UTC
    assert intervalo.fin.tzinfo is UTC


@pytest.mark.parametrize(
    ("desde", "hasta"),
    [
        (date(2026, 10, 9), date(2026, 10, 8)),  # invertido
        (date(2026, 10, 5), date(2026, 10, 12)),  # 8 dias
        (date(2026, 1, 1), date(2026, 12, 31)),  # un anio
        (date(9999, 12, 25), date.max),  # el dia siguiente a hasta no se puede representar
    ],
)
def test_rango_invalido_si_es_invertido_o_supera_una_semana(desde: date, hasta: date) -> None:
    with pytest.raises(RangoInvalidoError) as error:
        rango_local_a_intervalo(desde, hasta)

    assert error.value.codigo == "rango_invalido"
    assert error.value.mensaje


@pytest.mark.parametrize(
    ("desde", "hasta"),
    [
        (date(2026, 10, 8), date(2026, 10, 8)),  # 1 dia
        (date(2026, 10, 5), date(2026, 10, 11)),  # 7 dias
        (date(9999, 12, 30), date(9999, 12, 30)),  # ultimo dia con fin representable
    ],
)
def test_rango_de_uno_y_de_siete_dias_se_acepta(desde: date, hasta: date) -> None:
    intervalo = rango_local_a_intervalo(desde, hasta)

    assert intervalo.inicio < intervalo.fin
    assert (hasta - desde).days + 1 <= MAX_DIAS_AGENDA


MENSAJE_AJENO = "Solo podés consultar tu propia agenda"
PROPIO = uuid4()


def _odontologo() -> UsuarioAutenticado:
    return UsuarioAutenticado(id=uuid4(), rol=Rol.ODONTOLOGO, profesional_id=PROPIO)


def _recepcionista() -> UsuarioAutenticado:
    return UsuarioAutenticado(id=uuid4(), rol=Rol.RECEPCIONISTA, profesional_id=None)


@pytest.mark.parametrize("filtro", [None, PROPIO])
def test_el_odontologo_sin_filtro_o_con_el_suyo_obtiene_su_profesional(filtro: UUID | None) -> None:
    assert resolver_profesional_agenda(_odontologo(), filtro) == PROPIO


@pytest.mark.parametrize("filtro", [uuid4(), uuid4()])
def test_el_odontologo_con_otro_profesional_es_profesional_ajeno(filtro: UUID | None) -> None:
    with pytest.raises(ProfesionalAjenoError) as error:
        resolver_profesional_agenda(_odontologo(), filtro)

    assert error.value.mensaje == MENSAJE_AJENO


def test_la_recepcionista_conserva_el_filtro_tal_cual() -> None:
    otro = uuid4()

    assert resolver_profesional_agenda(_recepcionista(), otro) == otro
    assert resolver_profesional_agenda(_recepcionista(), None) is None
