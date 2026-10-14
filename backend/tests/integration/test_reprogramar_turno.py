"""Caso de uso ReprogramarTurno contra PostgreSQL real, con reloj fijo inyectado."""

from collections.abc import Sequence
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.application.crear_turno import CrearTurno, SolicitudTurno
from app.application.reprogramar_turno import (
    ObservadorReprogramacion,
    ReprogramarTurno,
    SolicitudReprogramacion,
)
from app.application.validacion_turno import ValidadorTurno
from app.domain.turnos import (
    CampoNoEditableError,
    ReferenciaInvalidaError,
    SolapamientoError,
    TurnoInexistenteError,
    TurnoInvalidoError,
    TurnoNoModificableError,
    TurnoPropuesto,
    TurnoRegistrado,
)
from app.infrastructure.db.models import Turno
from app.infrastructure.db.repositorio_turnos import RepositorioTurnos
from tests.integration.factories import Catalogo, crear_catalogo

AHORA = datetime(2026, 10, 7, 12, 0, tzinfo=UTC)  # 09:00 hora local
INICIO = datetime(2026, 10, 8, 13, 0, tzinfo=UTC)  # 10:00 hora local del día siguiente
OTRO_DIA = INICIO + timedelta(days=1)
LIMPIEZA = timedelta(minutes=45)


@pytest.fixture
def catalogo(db_session: Session) -> Catalogo:
    return crear_catalogo(db_session)


def _crear(
    session: Session,
    c: Catalogo,
    *,
    prof: int = 0,
    sillon: int | None = 0,
    pac: int = 0,
    inicio: datetime = INICIO,
    duracion: int | None = None,
    consulta: bool = False,
) -> UUID:
    """Crea un turno con el caso de uso de alta (reloj AHORA) y devuelve su id."""
    prestacion = c.consulta if consulta else c.limpieza
    creado = CrearTurno(RepositorioTurnos(session), reloj=lambda: AHORA).ejecutar(
        SolicitudTurno(
            profesional_id=c.profesionales[prof].id,
            paciente_id=c.pacientes[pac].id,
            prestacion_id=prestacion.id,
            sillon_id=None if sillon is None else c.sillones[sillon].id,
            inicio=inicio,
            duracion_min=duracion,
        )
    )
    return creado.id


def _caso(
    session: Session,
    ahora: datetime = AHORA,
    validadores: Sequence[ValidadorTurno] = (),
    observadores: Sequence[ObservadorReprogramacion] = (),
) -> ReprogramarTurno:
    return ReprogramarTurno(
        RepositorioTurnos(session),
        reloj=lambda: ahora,
        validadores=validadores,
        observadores=observadores,
    )


def _fila(session: Session, turno_id: UUID) -> Turno:
    session.expire_all()
    fila = session.get(Turno, turno_id)
    assert fila is not None
    return fila


def _horario(session: Session, turno_id: UUID) -> tuple[datetime, datetime, str]:
    fila = _fila(session, turno_id)
    return fila.inicio, fila.fin, fila.estado


def _cantidad(session: Session) -> int:
    return session.scalar(select(func.count()).select_from(Turno)) or 0


def _cancelar_en_la_base(session: Session, turno_id: UUID) -> None:
    _fila(session, turno_id).estado = "cancelado"
    session.commit()


def _intacto(session: Session, turno_id: UUID) -> None:
    assert _horario(session, turno_id) == (INICIO, INICIO + LIMPIEZA, "programado")


# --- 6.1 reprogramación válida -------------------------------------------------------------


def test_reprogramar_a_un_hueco_libre_conserva_el_id_y_persiste(
    db_session: Session, catalogo: Catalogo
) -> None:
    turno_id = _crear(db_session, catalogo)
    nuevo_inicio = INICIO + timedelta(hours=5)

    resultado = _caso(db_session).ejecutar(turno_id, SolicitudReprogramacion(inicio=nuevo_inicio))

    assert isinstance(resultado, TurnoRegistrado)
    assert resultado.id == turno_id
    assert (resultado.inicio, resultado.fin) == (nuevo_inicio, nuevo_inicio + LIMPIEZA)
    assert resultado.estado == "programado"
    assert _horario(db_session, turno_id) == (nuevo_inicio, nuevo_inicio + LIMPIEZA, "programado")
    assert _cantidad(db_session) == 1


def test_reprogramar_cambiando_profesional_y_sillon(
    db_session: Session, catalogo: Catalogo
) -> None:
    turno_id = _crear(db_session, catalogo)

    resultado = _caso(db_session).ejecutar(
        turno_id,
        SolicitudReprogramacion(
            profesional_id=catalogo.profesionales[1].id, sillon_id=catalogo.sillones[1].id
        ),
    )

    assert resultado.profesional_id == catalogo.profesionales[1].id
    assert resultado.sillon_id == catalogo.sillones[1].id
    fila = _fila(db_session, turno_id)
    assert (fila.profesional_id, fila.sillon_id) == (
        catalogo.profesionales[1].id,
        catalogo.sillones[1].id,
    )
    assert fila.paciente_id == catalogo.pacientes[0].id


# --- 6.2 parcialidad -----------------------------------------------------------------------


def test_reprogramar_solo_inicio_conserva_la_duracion_ajustada(
    db_session: Session, catalogo: Catalogo
) -> None:
    turno_id = _crear(db_session, catalogo, duracion=60)  # prestación de 45, ajustada a 60
    nuevo_inicio = INICIO + timedelta(hours=3)

    resultado = _caso(db_session).ejecutar(turno_id, SolicitudReprogramacion(inicio=nuevo_inicio))

    assert resultado.duracion_min == 60
    assert resultado.fin == nuevo_inicio + timedelta(minutes=60)


def test_reprogramar_solo_duracion_conserva_el_inicio(
    db_session: Session, catalogo: Catalogo
) -> None:
    turno_id = _crear(db_session, catalogo)

    resultado = _caso(db_session).ejecutar(turno_id, SolicitudReprogramacion(duracion_min=90))

    assert resultado.inicio == INICIO
    assert (resultado.duracion_min, resultado.fin) == (90, INICIO + timedelta(minutes=90))


def test_reprogramar_sin_cambios_responde_con_el_mismo_turno(
    db_session: Session, catalogo: Catalogo
) -> None:
    turno_id = _crear(db_session, catalogo, duracion=60)

    resultado = _caso(db_session).ejecutar(turno_id, SolicitudReprogramacion())

    assert (resultado.inicio, resultado.fin) == (INICIO, INICIO + timedelta(minutes=60))
    assert resultado.duracion_min == 60
    assert _cantidad(db_session) == 1


def test_sillon_nulo_en_prestacion_que_requiere_sillon_es_sillon_requerido(
    db_session: Session, catalogo: Catalogo
) -> None:
    turno_id = _crear(db_session, catalogo)

    with pytest.raises(TurnoInvalidoError) as info:
        _caso(db_session).ejecutar(turno_id, SolicitudReprogramacion(sillon_id=None))

    assert info.value.codigo == "sillon_requerido"
    _intacto(db_session, turno_id)


def test_sillon_en_prestacion_sin_sillon_es_sillon_no_corresponde(
    db_session: Session, catalogo: Catalogo
) -> None:
    turno_id = _crear(db_session, catalogo, sillon=None, consulta=True)

    with pytest.raises(TurnoInvalidoError) as info:
        _caso(db_session).ejecutar(
            turno_id, SolicitudReprogramacion(sillon_id=catalogo.sillones[0].id)
        )

    assert info.value.codigo == "sillon_no_corresponde"


# --- 6.3 errores y orden -------------------------------------------------------------------


@pytest.mark.parametrize(
    ("pedidos", "esperados"),
    [
        (("paciente_id",), ("paciente_id",)),
        (("prestacion_id", "paciente_id"), ("paciente_id", "prestacion_id")),
    ],
)
def test_campos_no_editables_fallan_antes_de_leer_el_turno(
    db_session: Session,
    catalogo: Catalogo,
    pedidos: tuple[str, ...],
    esperados: tuple[str, ...],
) -> None:
    turno_id = _crear(db_session, catalogo)
    solicitud = SolicitudReprogramacion(campos_no_editables=pedidos)

    with pytest.raises(CampoNoEditableError) as info:
        _caso(db_session).ejecutar(turno_id, solicitud)
    with pytest.raises(CampoNoEditableError):
        _caso(db_session).ejecutar(uuid4(), solicitud)  # ni siquiera busca el turno

    assert info.value.campos == esperados
    _intacto(db_session, turno_id)


def test_campos_no_editables_sobre_un_turno_cancelado_siguen_siendo_error_de_campo(
    db_session: Session, catalogo: Catalogo
) -> None:
    turno_id = _crear(db_session, catalogo)
    _cancelar_en_la_base(db_session, turno_id)

    with pytest.raises(CampoNoEditableError):
        _caso(db_session).ejecutar(
            turno_id, SolicitudReprogramacion(campos_no_editables=("paciente_id",))
        )


def test_turno_inexistente_lanza_turno_inexistente(db_session: Session) -> None:
    inexistente = uuid4()

    with pytest.raises(TurnoInexistenteError) as info:
        _caso(db_session).ejecutar(inexistente, SolicitudReprogramacion())

    assert info.value.turno_id == inexistente


@pytest.mark.parametrize(
    "cambios",
    [
        SolicitudReprogramacion(inicio=OTRO_DIA),
        SolicitudReprogramacion(duracion_min=42),  # duración inválida
        SolicitudReprogramacion(inicio=AHORA - timedelta(days=1)),  # inicio en el pasado
    ],
    ids=["valido", "duracion-invalida", "inicio-pasado"],
)
def test_turno_cancelado_informa_ya_cancelado_antes_que_cualquier_validacion(
    db_session: Session, catalogo: Catalogo, cambios: SolicitudReprogramacion
) -> None:
    turno_id = _crear(db_session, catalogo)
    _cancelar_en_la_base(db_session, turno_id)

    with pytest.raises(TurnoNoModificableError) as info:
        _caso(db_session).ejecutar(turno_id, cambios)

    assert info.value.codigo == "turno_ya_cancelado"
    assert _horario(db_session, turno_id) == (INICIO, INICIO + LIMPIEZA, "cancelado")


@pytest.mark.parametrize(
    "ahora",
    [INICIO, INICIO + timedelta(minutes=20), INICIO + timedelta(days=1)],
    ids=["limite-exacto", "en-curso", "pasado"],
)
def test_turno_iniciado_es_ya_iniciado_aunque_el_nuevo_inicio_sea_futuro(
    db_session: Session, catalogo: Catalogo, ahora: datetime
) -> None:
    turno_id = _crear(db_session, catalogo)

    with pytest.raises(TurnoNoModificableError) as info:
        _caso(db_session, ahora).ejecutar(
            turno_id, SolicitudReprogramacion(inicio=ahora + timedelta(days=3))
        )

    assert info.value.codigo == "turno_ya_iniciado"
    _intacto(db_session, turno_id)


def test_un_minuto_antes_del_inicio_todavia_se_puede_reprogramar(
    db_session: Session, catalogo: Catalogo
) -> None:
    turno_id = _crear(db_session, catalogo)

    resultado = _caso(db_session, INICIO - timedelta(minutes=1)).ejecutar(
        turno_id, SolicitudReprogramacion(inicio=OTRO_DIA)
    )

    assert resultado.inicio == OTRO_DIA


# --- 6.4 misma validación que el alta, con el original intacto -----------------------------


@pytest.mark.parametrize(
    ("cambios", "codigo"),
    [
        (SolicitudReprogramacion(duracion_min=42), "duracion_invalida"),
        (SolicitudReprogramacion(inicio=INICIO + timedelta(minutes=7)), "inicio_no_alineado"),
        (SolicitudReprogramacion(inicio=AHORA - timedelta(hours=1)), "inicio_en_pasado"),
    ],
    ids=["duracion-42", "inicio-10-07", "inicio-pasado"],
)
def test_reprogramar_aplica_la_validacion_del_alta_y_deja_el_turno_intacto(
    db_session: Session, catalogo: Catalogo, cambios: SolicitudReprogramacion, codigo: str
) -> None:
    turno_id = _crear(db_session, catalogo)

    with pytest.raises(TurnoInvalidoError) as info:
        _caso(db_session).ejecutar(turno_id, cambios)

    assert info.value.codigo == codigo
    _intacto(db_session, turno_id)


def test_profesional_inactivo_es_referencia_invalida_y_deja_el_turno_intacto(
    db_session: Session, catalogo: Catalogo
) -> None:
    turno_id = _crear(db_session, catalogo)
    catalogo.profesionales[1].activo = False
    db_session.commit()

    with pytest.raises(ReferenciaInvalidaError) as info:
        _caso(db_session).ejecutar(
            turno_id, SolicitudReprogramacion(profesional_id=catalogo.profesionales[1].id)
        )

    assert (info.value.referencia, info.value.motivo) == ("profesional", "inactiva")
    _intacto(db_session, turno_id)
    assert _fila(db_session, turno_id).profesional_id == catalogo.profesionales[0].id


def test_sillon_inexistente_es_referencia_invalida_y_deja_el_turno_intacto(
    db_session: Session, catalogo: Catalogo
) -> None:
    turno_id = _crear(db_session, catalogo)

    with pytest.raises(ReferenciaInvalidaError) as info:
        _caso(db_session).ejecutar(turno_id, SolicitudReprogramacion(sillon_id=uuid4()))

    assert (info.value.referencia, info.value.motivo) == ("sillon", "inexistente")
    _intacto(db_session, turno_id)


def test_hueco_ocupado_lanza_solapamiento_con_todos_los_recursos_y_deja_el_original(
    db_session: Session, catalogo: Catalogo
) -> None:
    lejano = INICIO + timedelta(hours=4)
    turno_id = _crear(db_session, catalogo, inicio=lejano)
    _crear(db_session, catalogo)  # ocupa INICIO con el mismo profesional, sillón y paciente

    with pytest.raises(SolapamientoError) as info:
        _caso(db_session).ejecutar(turno_id, SolicitudReprogramacion(inicio=INICIO))

    assert info.value.recursos == ("profesional", "sillon", "paciente")
    assert _horario(db_session, turno_id) == (lejano, lejano + LIMPIEZA, "programado")


def test_invalido_y_en_conflicto_responde_el_error_de_dominio_no_el_solape(
    db_session: Session, catalogo: Catalogo
) -> None:
    turno_id = _crear(db_session, catalogo, inicio=INICIO + timedelta(hours=4))
    _crear(db_session, catalogo)

    with pytest.raises(TurnoInvalidoError) as info:
        _caso(db_session).ejecutar(
            turno_id, SolicitudReprogramacion(inicio=INICIO, duracion_min=42)
        )

    assert info.value.codigo == "duracion_invalida"


# --- 6.5 exclusión del propio turno --------------------------------------------------------


def test_moverse_dentro_del_propio_intervalo_es_valido(
    db_session: Session, catalogo: Catalogo
) -> None:
    turno_id = _crear(db_session, catalogo)  # 10:00-10:45

    resultado = _caso(db_session).ejecutar(
        turno_id, SolicitudReprogramacion(inicio=INICIO + timedelta(minutes=15))
    )

    assert resultado.inicio == INICIO + timedelta(minutes=15)
    assert resultado.fin == INICIO + timedelta(minutes=60)


def test_extender_la_duracion_sobre_el_propio_intervalo_es_valido(
    db_session: Session, catalogo: Catalogo
) -> None:
    turno_id = _crear(db_session, catalogo)

    resultado = _caso(db_session).ejecutar(turno_id, SolicitudReprogramacion(duracion_min=90))

    assert resultado.fin == INICIO + timedelta(minutes=90)


def test_solape_con_otro_turno_del_mismo_paciente_es_solape_de_paciente(
    db_session: Session, catalogo: Catalogo
) -> None:
    turno_id = _crear(db_session, catalogo, inicio=INICIO + timedelta(hours=4))
    # Otro turno del mismo paciente con otro profesional y sillón
    _crear(db_session, catalogo, prof=1, sillon=1, pac=0)

    with pytest.raises(SolapamientoError) as info:
        _caso(db_session).ejecutar(turno_id, SolicitudReprogramacion(inicio=INICIO))

    assert info.value.recursos == ("paciente",)


def test_horario_contiguo_a_otro_turno_es_valido(db_session: Session, catalogo: Catalogo) -> None:
    turno_id = _crear(db_session, catalogo, inicio=INICIO + timedelta(hours=4))
    _crear(db_session, catalogo)  # 10:00-10:45

    resultado = _caso(db_session).ejecutar(
        turno_id, SolicitudReprogramacion(inicio=INICIO + LIMPIEZA)
    )

    assert resultado.inicio == INICIO + LIMPIEZA


def test_destino_ocupado_solo_por_un_turno_cancelado_es_valido(
    db_session: Session, catalogo: Catalogo
) -> None:
    turno_id = _crear(db_session, catalogo, inicio=INICIO + timedelta(hours=4))
    ocupante = _crear(db_session, catalogo)
    _cancelar_en_la_base(db_session, ocupante)

    resultado = _caso(db_session).ejecutar(turno_id, SolicitudReprogramacion(inicio=INICIO))

    assert resultado.inicio == INICIO


def test_carrera_que_esquiva_el_prechequeo_termina_en_solapamiento_y_deja_el_original(
    db_session: Session, catalogo: Catalogo
) -> None:
    lejano = INICIO + timedelta(hours=4)
    turno_id = _crear(db_session, catalogo, inicio=lejano, sillon=1, pac=1)
    _crear(db_session, catalogo)  # ocupa INICIO con el mismo profesional, otro sillón y paciente
    repositorio = RepositorioTurnos(db_session)
    # solo se sustituye la consulta del pre-chequeo; el UPDATE y la exclusión son reales
    repositorio.buscar_conflictos = lambda *a, **k: set()  # type: ignore[method-assign]
    caso = ReprogramarTurno(repositorio, reloj=lambda: AHORA)

    with pytest.raises(SolapamientoError) as info:
        caso.ejecutar(turno_id, SolicitudReprogramacion(inicio=INICIO))

    assert info.value.recursos == ("profesional",)
    # sin rollback manual: lo hace el propio caso de uso
    assert _horario(db_session, turno_id) == (lejano, lejano + LIMPIEZA, "programado")
    assert _fila(db_session, turno_id).sillon_id == catalogo.sillones[1].id


# --- 6.6 puntos de extensión ---------------------------------------------------------------


def test_observador_recibe_anterior_y_nuevo_antes_del_commit(
    db_session: Session, catalogo: Catalogo
) -> None:
    turno_id = _crear(db_session, catalogo)
    recibidos: list[tuple[TurnoRegistrado, TurnoRegistrado]] = []
    repo = RepositorioTurnos(db_session)
    commits: list[int] = []
    commit_original = repo.commit
    repo.commit = lambda: (commits.append(len(recibidos)), commit_original())[1]  # type: ignore[method-assign]
    caso = ReprogramarTurno(
        repo, reloj=lambda: AHORA, observadores=[lambda a, n: recibidos.append((a, n))]
    )
    nuevo_inicio = INICIO + timedelta(hours=2)

    resultado = caso.ejecutar(turno_id, SolicitudReprogramacion(inicio=nuevo_inicio))

    anterior, nuevo = recibidos[0]
    assert anterior.inicio == INICIO
    assert nuevo.inicio == nuevo_inicio
    assert nuevo == resultado
    assert commits == [1]  # el observador ya había corrido cuando se hizo el commit


def test_observador_que_falla_hace_rollback_y_el_turno_queda_intacto(
    db_session: Session, catalogo: Catalogo
) -> None:
    turno_id = _crear(db_session, catalogo)

    def falla(_anterior: TurnoRegistrado, _nuevo: TurnoRegistrado) -> None:
        raise RuntimeError("fallo del observador")

    with pytest.raises(RuntimeError, match="fallo del observador"):
        _caso(db_session, observadores=[falla]).ejecutar(
            turno_id, SolicitudReprogramacion(inicio=OTRO_DIA)
        )

    _intacto(db_session, turno_id)


def test_validador_recibe_el_turno_propuesto_fusionado_y_su_error_corta(
    db_session: Session, catalogo: Catalogo
) -> None:
    turno_id = _crear(db_session, catalogo, duracion=60)
    vistos: list[TurnoPropuesto] = []

    def rechaza(propuesto: TurnoPropuesto) -> None:
        vistos.append(propuesto)
        raise TurnoInvalidoError("regla_externa", "rechazado")

    with pytest.raises(TurnoInvalidoError) as info:
        _caso(db_session, validadores=[rechaza]).ejecutar(
            turno_id, SolicitudReprogramacion(inicio=OTRO_DIA)
        )

    assert info.value.codigo == "regla_externa"
    assert (vistos[0].inicio, vistos[0].duracion_min) == (OTRO_DIA, 60)
    assert vistos[0].paciente_id == catalogo.pacientes[0].id
    assert _fila(db_session, turno_id).inicio == INICIO


def test_con_listas_vacias_por_defecto_la_reprogramacion_funciona(
    db_session: Session, catalogo: Catalogo
) -> None:
    turno_id = _crear(db_session, catalogo)

    resultado = _caso(db_session).ejecutar(turno_id, SolicitudReprogramacion(inicio=OTRO_DIA))

    assert resultado.inicio == OTRO_DIA
