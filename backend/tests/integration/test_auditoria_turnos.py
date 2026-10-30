"""AuditorTurnos enchufado como observador de los casos de uso, contra PostgreSQL real.

Los registros se leen directo de la tabla (SQL), no por la API ni por el repositorio, para
verificar lo que de verdad quedó persistido. Reloj fijo; datos ficticios.
"""

from datetime import UTC, datetime, timedelta, timezone
from typing import Any
from uuid import UUID, uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.application.auditoria_turnos import AuditorTurnos
from app.application.cancelar_turno import CancelarTurno
from app.application.crear_turno import CrearTurno, SolicitudTurno
from app.application.reprogramar_turno import ReprogramarTurno, SolicitudReprogramacion
from app.domain.turnos import SolapamientoError, TurnoInvalidoError, TurnoNoModificableError
from app.infrastructure.db.models import Usuario
from app.infrastructure.db.repositorio_auditoria import RepositorioAuditoria
from app.infrastructure.db.repositorio_turnos import RepositorioTurnos
from tests.integration.factories import Catalogo, crear_catalogo

AHORA = datetime(2026, 10, 7, 12, 0, tzinfo=UTC)  # 09:00 hora local
BUENOS_AIRES = timezone(timedelta(hours=-3))
INICIO = datetime(2026, 10, 8, 10, 0, tzinfo=BUENOS_AIRES)  # 13:00Z
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


@pytest.fixture
def catalogo(db_session: Session) -> Catalogo:
    return crear_catalogo(db_session)


@pytest.fixture
def otra_recepcionista(db_session: Session) -> Usuario:
    usuario = Usuario(
        email="otra.recepcion@example.com", password_hash="hash-ficticio", rol="recepcionista"
    )
    db_session.add(usuario)
    db_session.flush()
    return usuario


def _auditor(session: Session, usuario_id: UUID, ahora: datetime = AHORA) -> AuditorTurnos:
    return AuditorTurnos(RepositorioAuditoria(session), usuario_id, lambda: ahora)


def _crear(
    session: Session,
    usuario: Usuario,
    c: Catalogo,
    *,
    inicio: datetime = INICIO,
    ahora: datetime = AHORA,
) -> UUID:
    caso = CrearTurno(
        RepositorioTurnos(session),
        lambda: ahora,
        observadores=[_auditor(session, usuario.id, ahora).al_crear],
    )
    creado = caso.ejecutar(
        SolicitudTurno(
            profesional_id=c.profesionales[0].id,
            paciente_id=c.pacientes[0].id,
            prestacion_id=c.limpieza.id,
            sillon_id=c.sillones[0].id,
            inicio=inicio,
        ),
        creado_por=usuario.id,
    )
    return creado.id


def _registros(session: Session, turno_id: UUID | None = None) -> list[dict[str, Any]]:
    """Filas de turno_auditoria por orden de inserción, leídas directo de la base."""
    filtro = "" if turno_id is None else "WHERE turno_id = :turno_id"
    filas = session.execute(
        text(
            "SELECT id, turno_id, usuario_id, accion, valores_previos, valores_nuevos, "
            f"ocurrido_en FROM turno_auditoria {filtro} ORDER BY id"
        ),
        {} if turno_id is None else {"turno_id": turno_id},
    ).mappings()
    return [dict(fila) for fila in filas]


# --- 6.1 alta auditada ---------------------------------------------------------------------


def test_crear_turno_con_auditor_deja_un_registro_crear_con_autor_instante_y_valores(
    db_session: Session, catalogo: Catalogo, recepcionista: Usuario
) -> None:
    turno_id = _crear(db_session, recepcionista, catalogo)

    (registro,) = _registros(db_session)

    assert registro["turno_id"] == turno_id
    assert registro["accion"] == "crear"
    assert registro["usuario_id"] == recepcionista.id
    assert registro["ocurrido_en"] == datetime(2026, 10, 7, 12, 0, tzinfo=UTC)
    assert registro["valores_previos"] is None
    assert registro["valores_nuevos"] == {
        "profesional_id": str(catalogo.profesionales[0].id),
        "paciente_id": str(catalogo.pacientes[0].id),
        "prestacion_id": str(catalogo.limpieza.id),
        "sillon_id": str(catalogo.sillones[0].id),
        "inicio": "2026-10-08T13:00:00+00:00",
        "fin": "2026-10-08T13:45:00+00:00",
        "duracion_min": 45,
        "estado": "programado",
        "motivo_cancelacion": None,
    }


def test_crear_turno_con_duracion_ajustada_y_sin_sillon_registra_sillon_nulo_y_duracion_20(
    db_session: Session, catalogo: Catalogo, recepcionista: Usuario
) -> None:
    caso = CrearTurno(
        RepositorioTurnos(db_session),
        lambda: AHORA,
        observadores=[_auditor(db_session, recepcionista.id).al_crear],
    )

    caso.ejecutar(
        SolicitudTurno(
            profesional_id=catalogo.profesionales[0].id,
            paciente_id=catalogo.pacientes[0].id,
            prestacion_id=catalogo.consulta.id,
            sillon_id=None,
            inicio=datetime(2026, 10, 8, 11, 0, tzinfo=BUENOS_AIRES),
            duracion_min=20,
        ),
        creado_por=recepcionista.id,
    )

    (registro,) = _registros(db_session)
    nuevos = registro["valores_nuevos"]
    assert nuevos["sillon_id"] is None
    assert nuevos["duracion_min"] == 20
    assert nuevos["inicio"] == "2026-10-08T14:00:00+00:00"
    assert nuevos["fin"] == "2026-10-08T14:20:00+00:00"
    assert nuevos["prestacion_id"] == str(catalogo.consulta.id)


def test_ocurrido_en_sale_del_reloj_inyectado_del_auditor_y_se_guarda_en_utc(
    db_session: Session, catalogo: Catalogo, recepcionista: Usuario
) -> None:
    ahora_local = datetime(2026, 10, 7, 9, 30, tzinfo=BUENOS_AIRES)

    _crear(db_session, recepcionista, catalogo, ahora=ahora_local)

    (registro,) = _registros(db_session)
    assert registro["ocurrido_en"] == datetime(2026, 10, 7, 12, 30, tzinfo=UTC)
    assert registro["ocurrido_en"].utcoffset() == timedelta(0)


# --- 6.2 reprogramación auditada -----------------------------------------------------------


def _reprogramar(
    session: Session,
    usuario: Usuario,
    turno_id: UUID,
    solicitud: SolicitudReprogramacion,
    ahora: datetime = AHORA,
) -> None:
    ReprogramarTurno(
        RepositorioTurnos(session),
        lambda: ahora,
        observadores=[_auditor(session, usuario.id, ahora).al_reprogramar],
    ).ejecutar(turno_id, solicitud)


def test_reprogramar_registra_valores_previos_y_nuevos_con_el_horario_anterior_y_el_nuevo(
    db_session: Session,
    catalogo: Catalogo,
    recepcionista: Usuario,
    otra_recepcionista: Usuario,
) -> None:
    turno_id = _crear(db_session, recepcionista, catalogo)
    ahora = datetime(2026, 10, 7, 9, 30, tzinfo=BUENOS_AIRES)

    _reprogramar(
        db_session,
        otra_recepcionista,
        turno_id,
        SolicitudReprogramacion(inicio=datetime(2026, 10, 8, 15, 0, tzinfo=BUENOS_AIRES)),
        ahora,
    )

    crear, reprogramar = _registros(db_session, turno_id)
    assert crear["accion"] == "crear"
    assert crear["usuario_id"] == recepcionista.id
    assert reprogramar["accion"] == "reprogramar"
    assert reprogramar["usuario_id"] == otra_recepcionista.id
    assert reprogramar["ocurrido_en"] == datetime(2026, 10, 7, 12, 30, tzinfo=UTC)
    previos, nuevos = reprogramar["valores_previos"], reprogramar["valores_nuevos"]
    assert (previos["inicio"], previos["fin"]) == (
        "2026-10-08T13:00:00+00:00",
        "2026-10-08T13:45:00+00:00",
    )
    assert (nuevos["inicio"], nuevos["fin"]) == (
        "2026-10-08T18:00:00+00:00",
        "2026-10-08T18:45:00+00:00",
    )
    resto = CLAVES - {"inicio", "fin"}
    assert {k: previos[k] for k in resto} == {k: nuevos[k] for k in resto}


def test_reprogramar_con_cambio_de_profesional_y_sillon_los_registra_en_previos_y_nuevos(
    db_session: Session, catalogo: Catalogo, recepcionista: Usuario
) -> None:
    turno_id = _crear(db_session, recepcionista, catalogo)

    _reprogramar(
        db_session,
        recepcionista,
        turno_id,
        SolicitudReprogramacion(
            profesional_id=catalogo.profesionales[1].id, sillon_id=catalogo.sillones[1].id
        ),
    )

    reprogramar = _registros(db_session, turno_id)[1]
    previos, nuevos = reprogramar["valores_previos"], reprogramar["valores_nuevos"]
    assert previos["profesional_id"] == str(catalogo.profesionales[0].id)
    assert previos["sillon_id"] == str(catalogo.sillones[0].id)
    assert nuevos["profesional_id"] == str(catalogo.profesionales[1].id)
    assert nuevos["sillon_id"] == str(catalogo.sillones[1].id)
    assert (previos["inicio"], previos["fin"]) == (nuevos["inicio"], nuevos["fin"])


def test_dos_reprogramaciones_encadenan_previos_con_los_nuevos_de_la_anterior(
    db_session: Session, catalogo: Catalogo, recepcionista: Usuario
) -> None:
    turno_id = _crear(db_session, recepcionista, catalogo)
    for hora in (15, 16):
        _reprogramar(
            db_session,
            recepcionista,
            turno_id,
            SolicitudReprogramacion(inicio=datetime(2026, 10, 8, hora, 0, tzinfo=BUENOS_AIRES)),
        )

    registros = _registros(db_session, turno_id)

    assert [r["accion"] for r in registros] == ["crear", "reprogramar", "reprogramar"]
    primera, segunda = registros[1], registros[2]
    assert segunda["valores_previos"] == primera["valores_nuevos"]
    assert primera["valores_previos"] == registros[0]["valores_nuevos"]
    assert segunda["valores_nuevos"]["inicio"] == "2026-10-08T19:00:00+00:00"


def test_reprogramar_sin_cambio_efectivo_igual_registra_con_previos_iguales_a_nuevos(
    db_session: Session, catalogo: Catalogo, recepcionista: Usuario
) -> None:
    turno_id = _crear(db_session, recepcionista, catalogo)

    _reprogramar(db_session, recepcionista, turno_id, SolicitudReprogramacion(inicio=INICIO))

    crear, reprogramar = _registros(db_session, turno_id)
    assert crear["accion"] == "crear"
    assert reprogramar["accion"] == "reprogramar"
    assert reprogramar["valores_previos"] == reprogramar["valores_nuevos"]
    assert reprogramar["valores_nuevos"] == crear["valores_nuevos"]


# --- 6.3 cancelación auditada --------------------------------------------------------------


def _cancelar(
    session: Session,
    usuario: Usuario,
    turno_id: UUID,
    motivo: str | None,
    ahora: datetime = AHORA,
) -> None:
    CancelarTurno(
        RepositorioTurnos(session),
        lambda: ahora,
        observadores=[_auditor(session, usuario.id, ahora).al_cancelar],
    ).ejecutar(turno_id, motivo)


def test_cancelar_registra_previos_programado_sin_motivo_y_nuevos_cancelado_con_motivo_normalizado(
    db_session: Session,
    catalogo: Catalogo,
    recepcionista: Usuario,
    otra_recepcionista: Usuario,
) -> None:
    turno_id = _crear(db_session, recepcionista, catalogo)
    ahora = datetime(2026, 10, 7, 10, 0, tzinfo=BUENOS_AIRES)

    _cancelar(db_session, otra_recepcionista, turno_id, "  El paciente avisó que no viene  ", ahora)

    cancelar = _registros(db_session, turno_id)[1]
    assert cancelar["accion"] == "cancelar"
    assert cancelar["usuario_id"] == otra_recepcionista.id
    assert cancelar["ocurrido_en"] == datetime(2026, 10, 7, 13, 0, tzinfo=UTC)
    previos, nuevos = cancelar["valores_previos"], cancelar["valores_nuevos"]
    assert (previos["estado"], previos["motivo_cancelacion"]) == ("programado", None)
    assert (nuevos["estado"], nuevos["motivo_cancelacion"]) == (
        "cancelado",
        "El paciente avisó que no viene",
    )
    resto = CLAVES - {"estado", "motivo_cancelacion"}
    assert {k: previos[k] for k in resto} == {k: nuevos[k] for k in resto}


@pytest.mark.parametrize("motivo", [None, "   "])
def test_cancelar_sin_motivo_deja_motivo_nulo_en_previos_y_en_nuevos(
    db_session: Session, catalogo: Catalogo, recepcionista: Usuario, motivo: str | None
) -> None:
    turno_id = _crear(db_session, recepcionista, catalogo)

    _cancelar(db_session, recepcionista, turno_id, motivo)

    cancelar = _registros(db_session, turno_id)[1]
    assert cancelar["valores_previos"]["motivo_cancelacion"] is None
    assert cancelar["valores_nuevos"]["motivo_cancelacion"] is None
    assert cancelar["valores_nuevos"]["estado"] == "cancelado"


def test_los_registros_de_la_cancelacion_cumplen_las_claves_exactas_y_los_instantes_en_utc(
    db_session: Session, catalogo: Catalogo, recepcionista: Usuario
) -> None:
    turno_id = _crear(db_session, recepcionista, catalogo)
    _cancelar(db_session, recepcionista, turno_id, "Motivo")

    crear, cancelar = _registros(db_session, turno_id)

    assert set(crear["valores_nuevos"]) == CLAVES
    assert set(cancelar["valores_previos"]) == CLAVES
    assert set(cancelar["valores_nuevos"]) == CLAVES
    assert crear["valores_nuevos"]["inicio"] == "2026-10-08T13:00:00+00:00"
    assert crear["valores_nuevos"]["fin"] == "2026-10-08T13:45:00+00:00"
    assert cancelar["valores_nuevos"]["inicio"] == "2026-10-08T13:00:00+00:00"
    assert cancelar["valores_nuevos"]["fin"] == "2026-10-08T13:45:00+00:00"


# --- 6.4 rollback conjunto con falla real de la base ---------------------------------------
# El auditor se construye con un usuario inexistente: la FK de turno_auditoria.usuario_id
# rechaza el registro (falla real de PostgreSQL, sin mocks) y todo el cambio debe revertirse.


def _total(session: Session, tabla: str) -> int:
    return session.execute(text(f"SELECT count(*) FROM {tabla}")).scalar_one()


def _fila_turno(session: Session, turno_id: UUID) -> Any:
    session.expire_all()
    return session.execute(
        text("SELECT inicio, fin, estado, motivo_cancelacion FROM turno WHERE id = :id"),
        {"id": turno_id},
    ).one()


def test_falla_del_auditor_en_el_alta_no_deja_turno_ni_registro(
    db_session: Session, catalogo: Catalogo
) -> None:
    auditor_roto = _auditor(db_session, uuid4())
    caso = CrearTurno(
        RepositorioTurnos(db_session), lambda: AHORA, observadores=[auditor_roto.al_crear]
    )

    with pytest.raises(IntegrityError) as excinfo:
        caso.ejecutar(
            SolicitudTurno(
                profesional_id=catalogo.profesionales[0].id,
                paciente_id=catalogo.pacientes[0].id,
                prestacion_id=catalogo.limpieza.id,
                sillon_id=catalogo.sillones[0].id,
                inicio=INICIO,
            )
        )

    assert excinfo.value.orig.diag.constraint_name == "fk_turno_auditoria_usuario_id_usuario"
    assert _total(db_session, "turno") == 0
    assert _total(db_session, "turno_auditoria") == 0


def test_falla_del_auditor_en_la_reprogramacion_conserva_el_horario_y_los_registros(
    db_session: Session, catalogo: Catalogo, recepcionista: Usuario
) -> None:
    turno_id = _crear(db_session, recepcionista, catalogo)
    antes = _fila_turno(db_session, turno_id)
    caso = ReprogramarTurno(
        RepositorioTurnos(db_session),
        lambda: AHORA,
        observadores=[_auditor(db_session, uuid4()).al_reprogramar],
    )

    with pytest.raises(IntegrityError):
        caso.ejecutar(
            turno_id,
            SolicitudReprogramacion(inicio=datetime(2026, 10, 8, 15, 0, tzinfo=BUENOS_AIRES)),
        )

    despues = _fila_turno(db_session, turno_id)
    assert (despues.inicio, despues.fin) == (antes.inicio, antes.fin)
    assert despues.inicio == datetime(2026, 10, 8, 13, 0, tzinfo=UTC)
    assert [r["accion"] for r in _registros(db_session, turno_id)] == ["crear"]


def test_falla_del_auditor_en_la_cancelacion_deja_el_turno_programado_y_su_horario_ocupado(
    db_session: Session, catalogo: Catalogo, recepcionista: Usuario
) -> None:
    turno_id = _crear(db_session, recepcionista, catalogo)
    caso = CancelarTurno(
        RepositorioTurnos(db_session),
        lambda: AHORA,
        observadores=[_auditor(db_session, uuid4()).al_cancelar],
    )

    with pytest.raises(IntegrityError):
        caso.ejecutar(turno_id, "Motivo")

    fila = _fila_turno(db_session, turno_id)
    assert (fila.estado, fila.motivo_cancelacion) == ("programado", None)
    assert [r["accion"] for r in _registros(db_session, turno_id)] == ["crear"]
    # el horario sigue ocupado: un alta solapada del mismo profesional es rechazada
    with pytest.raises(SolapamientoError):
        CrearTurno(RepositorioTurnos(db_session), lambda: AHORA).ejecutar(
            SolicitudTurno(
                profesional_id=catalogo.profesionales[0].id,
                paciente_id=catalogo.pacientes[1].id,
                prestacion_id=catalogo.limpieza.id,
                sillon_id=catalogo.sillones[1].id,
                inicio=INICIO + timedelta(minutes=15),
            )
        )


# --- 6.5 rechazos no auditados a nivel de caso de uso --------------------------------------


def test_alta_en_conflicto_no_cambia_la_cantidad_de_registros(
    db_session: Session, catalogo: Catalogo, recepcionista: Usuario
) -> None:
    _crear(db_session, recepcionista, catalogo)
    antes = _total(db_session, "turno_auditoria")

    with pytest.raises(SolapamientoError):
        _crear(db_session, recepcionista, catalogo, inicio=INICIO + timedelta(minutes=30))

    assert _total(db_session, "turno_auditoria") == antes == 1


def test_reprogramacion_con_duracion_7_no_cambia_la_cantidad_de_registros(
    db_session: Session, catalogo: Catalogo, recepcionista: Usuario
) -> None:
    turno_id = _crear(db_session, recepcionista, catalogo)

    with pytest.raises(TurnoInvalidoError):
        _reprogramar(db_session, recepcionista, turno_id, SolicitudReprogramacion(duracion_min=7))

    assert [r["accion"] for r in _registros(db_session, turno_id)] == ["crear"]


def test_segunda_cancelacion_no_cambia_la_cantidad_de_registros(
    db_session: Session, catalogo: Catalogo, recepcionista: Usuario
) -> None:
    turno_id = _crear(db_session, recepcionista, catalogo)
    _cancelar(db_session, recepcionista, turno_id, None)

    with pytest.raises(TurnoNoModificableError) as excinfo:
        _cancelar(db_session, recepcionista, turno_id, "Otra vez")

    assert excinfo.value.codigo == "turno_ya_cancelado"
    assert [r["accion"] for r in _registros(db_session, turno_id)] == ["crear", "cancelar"]
