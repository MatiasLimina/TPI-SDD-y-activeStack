from dataclasses import FrozenInstanceError
from datetime import UTC, datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4

import pytest

from app.domain.turnos import (
    CampoNoEditableError,
    Intervalo,
    ReferenciaInvalidaError,
    SolapamientoError,
    TurnoCreado,
    TurnoError,
    TurnoInvalidoError,
    TurnoNoModificableError,
    TurnoPropuesto,
    calcular_fin,
    duracion_efectiva,
    normalizar_motivo,
    solapan,
    validar_campos_editables,
    validar_duracion_y_grilla,
    validar_inicio_futuro,
    validar_modificable,
    validar_sillon,
)

BA = timezone(timedelta(hours=-3))


def _iv(h1: int, m1: int, h2: int, m2: int) -> Intervalo:
    return Intervalo(
        inicio=datetime(2026, 10, 8, h1, m1, tzinfo=BA),
        fin=datetime(2026, 10, 8, h2, m2, tzinfo=BA),
    )


BASE = _iv(10, 0, 10, 45)


@pytest.mark.parametrize(
    ("otro", "esperado"),
    [
        (_iv(10, 45, 11, 30), False),  # contiguo: semiabierto
        (_iv(10, 30, 11, 0), True),  # parcial
        (_iv(9, 0, 12, 0), True),  # contiene
        (_iv(11, 0, 11, 30), False),  # disjunto
        (_iv(9, 0, 10, 0), False),  # contiguo por izquierda
        (_iv(10, 0, 10, 45), True),  # idéntico
    ],
)
def test_solapan_es_semiabierto_y_simetrico(otro: Intervalo, esperado: bool) -> None:
    assert solapan(BASE, otro) is esperado
    assert solapan(otro, BASE) is esperado


def test_solapan_compara_instantes_en_distintas_zonas() -> None:
    en_utc = Intervalo(
        inicio=datetime(2026, 10, 8, 13, 30, tzinfo=UTC),
        fin=datetime(2026, 10, 8, 14, 0, tzinfo=UTC),
    )

    assert solapan(BASE, en_utc) is True


@pytest.mark.parametrize(
    ("de_prestacion", "informada", "esperada"),
    [(45, None, 45), (45, 60, 60), (30, None, 30), (45, 15, 15)],
)
def test_duracion_efectiva_usa_la_informada_o_la_de_la_prestacion(
    de_prestacion: int, informada: int | None, esperada: int
) -> None:
    assert duracion_efectiva(de_prestacion, informada) == esperada


@pytest.mark.parametrize(
    ("minutos", "fin_esperado"),
    [(45, (10, 45)), (60, (11, 0)), (480, (18, 0))],
)
def test_calcular_fin_suma_la_duracion_al_inicio(
    minutos: int, fin_esperado: tuple[int, int]
) -> None:
    inicio = datetime(2026, 10, 8, 10, 0, tzinfo=BA)

    assert calcular_fin(inicio, minutos) == datetime(2026, 10, 8, *fin_esperado, tzinfo=BA)


def _local(h: int, m: int, s: int = 0) -> datetime:
    return datetime(2026, 10, 8, h, m, s, tzinfo=BA)


@pytest.mark.parametrize("duracion", [0, -5, 42, 485])
def test_duracion_invalida_se_rechaza(duracion: int) -> None:
    with pytest.raises(TurnoInvalidoError) as excinfo:
        validar_duracion_y_grilla(_local(10, 0), duracion)

    assert excinfo.value.codigo == "duracion_invalida"


@pytest.mark.parametrize("duracion", [5, 45, 480])
def test_duracion_valida_se_acepta(duracion: int) -> None:
    validar_duracion_y_grilla(_local(10, 0), duracion)


@pytest.mark.parametrize("inicio", [_local(10, 7), _local(10, 5, 30)])
def test_inicio_no_alineado_se_rechaza(inicio: datetime) -> None:
    with pytest.raises(TurnoInvalidoError) as excinfo:
        validar_duracion_y_grilla(inicio, 45)

    assert excinfo.value.codigo == "inicio_no_alineado"


def test_inicio_con_microsegundos_se_rechaza() -> None:
    inicio = datetime(2026, 10, 8, 10, 5, 0, 1, tzinfo=BA)

    with pytest.raises(TurnoInvalidoError) as excinfo:
        validar_duracion_y_grilla(inicio, 45)

    assert excinfo.value.codigo == "inicio_no_alineado"


def test_inicio_alineado_en_hora_local_se_acepta() -> None:
    validar_duracion_y_grilla(_local(10, 5), 45)


def test_alineacion_se_evalua_en_hora_local_aunque_llegue_en_utc() -> None:
    validar_duracion_y_grilla(datetime(2026, 10, 8, 13, 5, tzinfo=UTC), 45)  # 10:05 local

    with pytest.raises(TurnoInvalidoError):
        validar_duracion_y_grilla(datetime(2026, 10, 8, 13, 7, tzinfo=UTC), 45)  # 10:07 local


def test_alineacion_en_zona_con_offset_de_media_hora_usa_hora_local_de_buenos_aires() -> None:
    # 10:05 en UTC-3 llega expresado como +05:30 (15:35 local de esa zona): sigue alineado
    india = timezone(timedelta(hours=5, minutes=30))

    validar_duracion_y_grilla(datetime(2026, 10, 8, 18, 35, tzinfo=india), 45)  # 13:05Z = 10:05 BA


AHORA = datetime(2026, 10, 7, 9, 0, tzinfo=BA)


def test_inicio_en_pasado_se_rechaza() -> None:
    with pytest.raises(TurnoInvalidoError) as excinfo:
        validar_inicio_futuro(datetime(2026, 10, 7, 8, 55, tzinfo=BA), AHORA)

    assert excinfo.value.codigo == "inicio_en_pasado"


@pytest.mark.parametrize(
    "inicio",
    [datetime(2026, 10, 7, 9, 5, tzinfo=BA), AHORA, datetime(2026, 10, 7, 12, 0, tzinfo=UTC)],
)
def test_inicio_igual_o_posterior_a_ahora_se_acepta(inicio: datetime) -> None:
    validar_inicio_futuro(inicio, AHORA)


def test_inicio_en_pasado_compara_instantes_entre_zonas() -> None:
    # 11:55Z = 08:55 local: pasado respecto de 09:00 local
    with pytest.raises(TurnoInvalidoError):
        validar_inicio_futuro(datetime(2026, 10, 7, 11, 55, tzinfo=UTC), AHORA)


def test_sillon_requerido_y_ausente_se_rechaza() -> None:
    with pytest.raises(TurnoInvalidoError) as excinfo:
        validar_sillon(requiere_sillon=True, sillon_informado=False)

    assert excinfo.value.codigo == "sillon_requerido"


def test_sillon_informado_cuando_no_corresponde_se_rechaza() -> None:
    with pytest.raises(TurnoInvalidoError) as excinfo:
        validar_sillon(requiere_sillon=False, sillon_informado=True)

    assert excinfo.value.codigo == "sillon_no_corresponde"


@pytest.mark.parametrize(("requiere", "informado"), [(True, True), (False, False)])
def test_sillon_coherente_se_acepta(requiere: bool, informado: bool) -> None:
    validar_sillon(requiere_sillon=requiere, sillon_informado=informado)


# --- 2.6 errores y tipos inmutables -------------------------------------------------------


def test_solapamiento_ordena_los_recursos_en_orden_fijo() -> None:
    error = SolapamientoError({"paciente", "profesional", "sillon"})

    assert error.recursos == ("profesional", "sillon", "paciente")


def test_solapamiento_con_un_solo_recurso() -> None:
    assert SolapamientoError({"sillon"}).recursos == ("sillon",)


def test_referencia_invalida_expone_referencia_y_motivo() -> None:
    error = ReferenciaInvalidaError("profesional", "inactiva")

    assert (error.referencia, error.motivo) == ("profesional", "inactiva")


@pytest.mark.parametrize(
    "error",
    [
        TurnoInvalidoError("duracion_invalida", "x"),
        ReferenciaInvalidaError("sillon", "inexistente"),
        SolapamientoError({"sillon"}),
    ],
)
def test_todos_los_errores_derivan_de_turno_error(error: Exception) -> None:
    assert isinstance(error, TurnoError)


def _propuesto() -> TurnoPropuesto:
    return TurnoPropuesto(
        profesional_id=uuid4(),
        paciente_id=uuid4(),
        prestacion_id=uuid4(),
        sillon_id=None,
        inicio=datetime(2026, 10, 8, 13, 0, tzinfo=UTC),
        fin=datetime(2026, 10, 8, 13, 45, tzinfo=UTC),
        duracion_min=45,
    )


def test_turno_propuesto_es_inmutable_y_expone_su_intervalo() -> None:
    propuesto = _propuesto()

    with pytest.raises(FrozenInstanceError):
        propuesto.duracion_min = 60  # type: ignore[misc]
    assert propuesto.intervalo == Intervalo(propuesto.inicio, propuesto.fin)


def test_turno_creado_es_inmutable_y_arranca_programado_sin_autor() -> None:
    creado = TurnoCreado.desde_propuesto(_propuesto(), id=uuid4())

    assert creado.estado == "programado"
    assert creado.creado_por is None
    with pytest.raises(FrozenInstanceError):
        creado.estado = "cancelado"  # type: ignore[misc]


def test_modulo_de_dominio_no_depende_de_sqlalchemy_ni_fastapi() -> None:
    codigo = (Path(__file__).parents[2] / "app" / "domain" / "turnos.py").read_text("utf-8")

    assert "sqlalchemy" not in codigo
    assert "fastapi" not in codigo


# --- C-04 cancelación ----------------------------------------------------------------------

INICIO_CANCELABLE = datetime(2026, 10, 7, 10, 0, tzinfo=BA)


def test_validar_modificable_acepta_programado_un_minuto_antes_del_inicio() -> None:
    validar_modificable("programado", INICIO_CANCELABLE, datetime(2026, 10, 7, 9, 59, tzinfo=BA))


@pytest.mark.parametrize(
    "ahora",
    [
        datetime(2026, 10, 7, 10, 0, tzinfo=BA),  # límite exacto
        datetime(2026, 10, 7, 10, 20, tzinfo=BA),  # en curso
        datetime(2026, 10, 8, 9, 0, tzinfo=BA),  # pasado (día siguiente)
    ],
)
def test_validar_modificable_rechaza_turno_iniciado_o_pasado(ahora: datetime) -> None:
    with pytest.raises(TurnoNoModificableError) as info:
        validar_modificable("programado", INICIO_CANCELABLE, ahora)

    assert info.value.codigo == "turno_ya_iniciado"


@pytest.mark.parametrize(
    "ahora",
    [
        datetime(2026, 10, 6, 9, 0, tzinfo=BA),  # inicio futuro
        datetime(2026, 10, 8, 9, 0, tzinfo=BA),  # inicio pasado: el estado se informa primero
    ],
)
def test_validar_modificable_informa_turno_ya_cancelado_antes_que_el_tiempo(
    ahora: datetime,
) -> None:
    with pytest.raises(TurnoNoModificableError) as info:
        validar_modificable("cancelado", INICIO_CANCELABLE, ahora)

    assert info.value.codigo == "turno_ya_cancelado"


@pytest.mark.parametrize(
    ("motivo", "esperado"),
    [
        (None, None),
        ("", None),
        ("   ", None),
        ("  Viaje imprevisto  ", "Viaje imprevisto"),
        ("Fiebre", "Fiebre"),
    ],
)
def test_normalizar_motivo_recorta_y_convierte_vacio_en_none(
    motivo: str | None, esperado: str | None
) -> None:
    assert normalizar_motivo(motivo) == esperado


# --- C-05 reprogramación: campos no editables ----------------------------------------------


def test_validar_campos_editables_sin_campos_no_falla() -> None:
    validar_campos_editables(())


@pytest.mark.parametrize(
    ("recibidos", "esperados"),
    [
        (("paciente_id",), ("paciente_id",)),
        (("prestacion_id",), ("prestacion_id",)),
        (("prestacion_id", "paciente_id"), ("paciente_id", "prestacion_id")),
    ],
)
def test_validar_campos_editables_lanza_con_los_campos_en_orden_fijo(
    recibidos: tuple[str, ...], esperados: tuple[str, ...]
) -> None:
    with pytest.raises(CampoNoEditableError) as info:
        validar_campos_editables(recibidos)

    assert info.value.campos == esperados


def test_campo_no_editable_indica_cancelar_y_crear_uno_nuevo() -> None:
    with pytest.raises(CampoNoEditableError) as info:
        validar_campos_editables(("paciente_id",))

    assert "cancel" in info.value.mensaje
    assert "nuevo" in info.value.mensaje
    assert isinstance(info.value, TurnoError)
