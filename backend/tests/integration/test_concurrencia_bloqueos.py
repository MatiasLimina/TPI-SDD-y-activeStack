"""Bloqueo vs alta o reprogramación de turno (D13), cada operación en su propia conexión.

Un escenario determinista por orden de llegada: la primera transacción queda abierta sin
confirmar, la segunda corre en un hilo, `_esperar_bloqueo` confirma que quedó esperando el lock
y recién entonces se deja confirmar a la primera. Sin el `FOR NO KEY UPDATE` de `CrearBloqueo`
la segunda operación no espera y estos tests fallan.
"""

import threading
import time
from collections.abc import Callable, Iterator
from datetime import UTC, datetime, timedelta, timezone
from typing import Any
from uuid import UUID

import pytest
from sqlalchemy import Engine, select, text
from sqlalchemy.orm import Session, sessionmaker

from app.application.bloqueos_agenda import CrearBloqueo, SolicitudBloqueo, ValidadorBloqueos
from app.application.crear_turno import CrearTurno, SolicitudTurno
from app.application.reprogramar_turno import ReprogramarTurno, SolicitudReprogramacion
from app.domain.bloqueos import BloqueoConTurnosError, TurnoAfectado
from app.domain.turnos import TurnoCreado, TurnoInvalidoError, TurnoPropuesto
from app.domain.usuarios import Rol, UsuarioAutenticado
from app.infrastructure.db.models import Bloqueo, Turno, Usuario
from app.infrastructure.db.repositorio_bloqueos import RepositorioBloqueos
from app.infrastructure.db.repositorio_turnos import RepositorioTurnos
from tests.integration.factories import Catalogo

AHORA = datetime(2026, 10, 7, 12, 0, tzinfo=UTC)  # 2026-10-07 09:00 hora local
BUENOS_AIRES = timezone(timedelta(hours=-3))
ESPERA_S = 15


def _h(hora: int, minuto: int = 0) -> datetime:
    """Instante del jueves 2026-10-08 a esa hora local."""
    return datetime(2026, 10, 8, hora, minuto, tzinfo=BUENOS_AIRES)


def _esperar_bloqueo(motor: Engine, consulta_bloqueada: str) -> None:
    """Espera a que otra conexión esté bloqueada esperando un lock en una consulta como esta."""
    limite = time.monotonic() + ESPERA_S
    consulta = text(
        "SELECT count(*) FROM pg_stat_activity WHERE datname = current_database() "
        "AND wait_event_type = 'Lock' AND query ILIKE :patron"
    )
    while time.monotonic() < limite:
        with motor.connect() as conexion:
            if conexion.execute(consulta, {"patron": f"%{consulta_bloqueada}%"}).scalar_one():
                return
        time.sleep(0.05)
    raise AssertionError(
        f"ninguna conexión quedó bloqueada en una consulta con {consulta_bloqueada}"
    )


_HILOS: list[threading.Thread] = []


class Hilo:
    """Una operación en su propio hilo: guarda el resultado o la excepción y avisa al terminar."""

    def __init__(self, operacion: Callable[[], Any]) -> None:
        self.resultado: Any = None
        self.terminada = threading.Event()
        self._operacion = operacion
        self._hilo = threading.Thread(target=self._correr)
        _HILOS.append(self._hilo)
        self._hilo.start()

    def _correr(self) -> None:
        try:
            self.resultado = self._operacion()
        except Exception as error:
            self.resultado = error
        finally:
            self.terminada.set()

    def esperar(self) -> Any:
        self._hilo.join(timeout=30)
        assert self.terminada.is_set(), "la operación no terminó"
        return self.resultado


class Pausa:
    """Detiene una operación en un punto y la deja seguir cuando el test lo decide."""

    def __init__(self) -> None:
        self.detenida = threading.Event()
        self._seguir = threading.Event()

    def detener(self) -> None:
        self.detenida.set()
        assert self._seguir.wait(timeout=ESPERA_S), "nadie liberó la operación detenida"

    def liberar(self) -> None:
        self._seguir.set()

    def esperar_detenida(self) -> None:
        assert self.detenida.wait(timeout=ESPERA_S), "la operación no llegó al punto de pausa"


class RepositorioBloqueosPausado(RepositorioBloqueos):
    """Detiene el alta justo antes del commit: el bloqueo está insertado y el lock tomado."""

    def __init__(self, session: Session, pausa: Pausa) -> None:
        super().__init__(session)
        self._pausa = pausa

    def commit(self) -> None:
        self._pausa.detener()
        super().commit()


@pytest.fixture
def fabrica(motor_concurrente: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=motor_concurrente, expire_on_commit=False)


@pytest.fixture
def operador(recepcionista_commiteada: Usuario) -> UsuarioAutenticado:
    return UsuarioAutenticado(
        id=recepcionista_commiteada.id, rol=Rol.RECEPCIONISTA, profesional_id=None
    )


@pytest.fixture
def pausas() -> Iterator[list[Pausa]]:
    """Libera las pausas y espera a los hilos al terminar, también si el test falla.

    Se desarma antes que los fixtures de datos: ningún hilo escribe después de que se borren.
    """
    creadas: list[Pausa] = []
    yield creadas
    for pausa in creadas:
        pausa.liberar()
    while _HILOS:
        _HILOS.pop().join(timeout=30)


def _pausa(pausas: list[Pausa]) -> Pausa:
    pausa = Pausa()
    pausas.append(pausa)
    return pausa


def _solicitud_turno(catalogo: Catalogo, profesional_id: UUID, inicio: datetime) -> SolicitudTurno:
    return SolicitudTurno(
        profesional_id=profesional_id,
        paciente_id=catalogo.pacientes[0].id,
        prestacion_id=catalogo.limpieza.id,
        sillon_id=catalogo.sillones[0].id,
        inicio=inicio,
    )


def _turno_confirmado(
    fabrica: sessionmaker[Session], catalogo: Catalogo, profesional_id: UUID, inicio: datetime
) -> TurnoCreado:
    with fabrica() as sesion:
        return CrearTurno(RepositorioTurnos(sesion), reloj=lambda: AHORA).ejecutar(
            _solicitud_turno(catalogo, profesional_id, inicio)
        )


def _alta_de_turno(
    fabrica: sessionmaker[Session],
    catalogo: Catalogo,
    profesional_id: UUID,
    inicio: datetime,
    *,
    pausa: Pausa | None = None,
) -> Callable[[], TurnoCreado]:
    """Alta con el validador de bloqueos; `pausa` la detiene tras validar y antes del INSERT."""

    def operacion() -> TurnoCreado:
        with fabrica() as sesion:
            validadores: list[Callable[[TurnoPropuesto], None]] = [
                ValidadorBloqueos(RepositorioBloqueos(sesion))
            ]
            if pausa is not None:
                validadores.append(lambda _: pausa.detener())
            return CrearTurno(
                RepositorioTurnos(sesion), reloj=lambda: AHORA, validadores=validadores
            ).ejecutar(_solicitud_turno(catalogo, profesional_id, inicio))

    return operacion


def _reprogramacion(
    fabrica: sessionmaker[Session],
    turno_id: UUID,
    cambios: SolicitudReprogramacion,
    *,
    pausa: Pausa | None = None,
) -> Callable[[], Any]:
    def operacion() -> Any:
        with fabrica() as sesion:
            validadores: list[Callable[[TurnoPropuesto], None]] = [
                ValidadorBloqueos(RepositorioBloqueos(sesion))
            ]
            if pausa is not None:
                validadores.append(lambda _: pausa.detener())
            return ReprogramarTurno(
                RepositorioTurnos(sesion), reloj=lambda: AHORA, validadores=validadores
            ).ejecutar(turno_id, cambios)

    return operacion


def _alta_de_bloqueo(
    fabrica: sessionmaker[Session],
    operador: UsuarioAutenticado,
    profesional_id: UUID,
    inicio: datetime,
    fin: datetime,
    *,
    pausa: Pausa | None = None,
) -> Callable[[], Bloqueo]:
    """`CrearBloqueo` real; con `pausa` queda detenido justo antes del commit, lock tomado."""

    def operacion() -> Bloqueo:
        with fabrica() as sesion:
            repositorio = (
                RepositorioBloqueos(sesion)
                if pausa is None
                else RepositorioBloqueosPausado(sesion, pausa)
            )
            return CrearBloqueo(repositorio).ejecutar(
                operador, SolicitudBloqueo(profesional_id, inicio, fin, "Congreso")
            )

    return operacion


def _turnos(motor: Engine, profesional_id: UUID) -> list[Turno]:
    with Session(motor) as sesion:
        return list(
            sesion.scalars(
                select(Turno).where(Turno.profesional_id == profesional_id).order_by(Turno.inicio)
            )
        )


def _bloqueos(motor: Engine, profesional_id: UUID) -> list[Bloqueo]:
    with Session(motor) as sesion:
        return list(sesion.scalars(select(Bloqueo).where(Bloqueo.profesional_id == profesional_id)))


def _turnos_activos_dentro_de_un_bloqueo(motor: Engine, profesional_id: UUID) -> int:
    """La invariante de RN-HB-03: nunca hay un turno activo pisando un bloqueo del profesional."""
    consulta = text(
        "SELECT count(*) FROM turno t JOIN bloqueo b ON b.profesional_id = t.profesional_id "
        "WHERE t.profesional_id = :id AND t.estado <> 'cancelado' "
        "AND tstzrange(t.inicio, t.fin, '[)') && tstzrange(b.inicio, b.fin, '[)')"
    )
    with motor.connect() as conexion:
        return int(conexion.execute(consulta, {"id": profesional_id}).scalar_one())


def test_alta_de_turno_espera_a_un_bloqueo_en_curso_y_responde_turno_en_bloqueo(
    motor_concurrente: Engine,
    fabrica: sessionmaker[Session],
    catalogo_commiteado: Catalogo,
    operador: UsuarioAutenticado,
    pausas: list[Pausa],
) -> None:
    a = catalogo_commiteado.profesionales[0].id
    pausa_bloqueo = _pausa(pausas)
    bloqueo = Hilo(_alta_de_bloqueo(fabrica, operador, a, _h(10), _h(12), pausa=pausa_bloqueo))
    pausa_bloqueo.esperar_detenida()

    alta = Hilo(_alta_de_turno(fabrica, catalogo_commiteado, a, _h(10, 30)))
    _esperar_bloqueo(motor_concurrente, "FOR SHARE")
    assert not alta.terminada.is_set()
    pausa_bloqueo.liberar()
    error = alta.esperar()
    bloqueo.esperar()

    assert isinstance(error, TurnoInvalidoError), error
    assert error.codigo == "turno_en_bloqueo"
    assert _turnos(motor_concurrente, a) == []
    assert len(_bloqueos(motor_concurrente, a)) == 1
    assert _turnos_activos_dentro_de_un_bloqueo(motor_concurrente, a) == 0


def test_bloqueo_espera_a_un_alta_de_turno_en_curso_y_responde_bloqueo_con_turnos(
    motor_concurrente: Engine,
    fabrica: sessionmaker[Session],
    catalogo_commiteado: Catalogo,
    operador: UsuarioAutenticado,
    pausas: list[Pausa],
) -> None:
    a = catalogo_commiteado.profesionales[0].id
    pausa_alta = _pausa(pausas)
    alta = Hilo(_alta_de_turno(fabrica, catalogo_commiteado, a, _h(10, 30), pausa=pausa_alta))
    pausa_alta.esperar_detenida()  # referencias validadas (FOR SHARE tomado), sin INSERT todavía

    bloqueo = Hilo(_alta_de_bloqueo(fabrica, operador, a, _h(10), _h(12)))
    _esperar_bloqueo(motor_concurrente, "FOR NO KEY UPDATE")
    assert not bloqueo.terminada.is_set()
    pausa_alta.liberar()
    creado = alta.esperar()
    error = bloqueo.esperar()

    assert isinstance(creado, TurnoCreado), creado
    assert isinstance(error, BloqueoConTurnosError), error
    assert error.turnos == (TurnoAfectado(creado.id, _h(10, 30), _h(11, 15)),)
    assert [t.id for t in _turnos(motor_concurrente, a)] == [creado.id]
    assert _bloqueos(motor_concurrente, a) == []
    assert _turnos_activos_dentro_de_un_bloqueo(motor_concurrente, a) == 0


def test_reprogramacion_espera_a_un_bloqueo_en_curso_y_responde_turno_en_bloqueo(
    motor_concurrente: Engine,
    fabrica: sessionmaker[Session],
    catalogo_commiteado: Catalogo,
    operador: UsuarioAutenticado,
    pausas: list[Pausa],
) -> None:
    a = catalogo_commiteado.profesionales[0].id
    t1 = _turno_confirmado(fabrica, catalogo_commiteado, a, _h(15))
    pausa_bloqueo = _pausa(pausas)
    bloqueo = Hilo(_alta_de_bloqueo(fabrica, operador, a, _h(10), _h(12), pausa=pausa_bloqueo))
    pausa_bloqueo.esperar_detenida()

    cambio = Hilo(_reprogramacion(fabrica, t1.id, SolicitudReprogramacion(inicio=_h(10, 30))))
    _esperar_bloqueo(motor_concurrente, "FOR SHARE")
    assert not cambio.terminada.is_set()
    pausa_bloqueo.liberar()
    error = cambio.esperar()
    bloqueo.esperar()

    assert isinstance(error, TurnoInvalidoError), error
    assert error.codigo == "turno_en_bloqueo"
    [turno] = _turnos(motor_concurrente, a)
    assert (turno.inicio, turno.fin) == (_h(15), _h(15, 45))
    assert len(_bloqueos(motor_concurrente, a)) == 1
    assert _turnos_activos_dentro_de_un_bloqueo(motor_concurrente, a) == 0


def test_bloqueo_espera_a_una_reprogramacion_en_curso_y_responde_bloqueo_con_turnos(
    motor_concurrente: Engine,
    fabrica: sessionmaker[Session],
    catalogo_commiteado: Catalogo,
    operador: UsuarioAutenticado,
    pausas: list[Pausa],
) -> None:
    a = catalogo_commiteado.profesionales[0].id
    t1 = _turno_confirmado(fabrica, catalogo_commiteado, a, _h(15))
    pausa_cambio = _pausa(pausas)
    cambio = Hilo(
        _reprogramacion(
            fabrica, t1.id, SolicitudReprogramacion(inicio=_h(10, 30)), pausa=pausa_cambio
        )
    )
    pausa_cambio.esperar_detenida()  # referencias validadas, sin UPDATE todavía

    bloqueo = Hilo(_alta_de_bloqueo(fabrica, operador, a, _h(10), _h(12)))
    _esperar_bloqueo(motor_concurrente, "FOR NO KEY UPDATE")
    assert not bloqueo.terminada.is_set()
    pausa_cambio.liberar()
    reprogramado = cambio.esperar()
    error = bloqueo.esperar()

    assert not isinstance(reprogramado, Exception), reprogramado
    assert isinstance(error, BloqueoConTurnosError), error
    assert error.turnos == (TurnoAfectado(t1.id, _h(10, 30), _h(11, 15)),)
    [turno] = _turnos(motor_concurrente, a)
    assert (turno.inicio, turno.fin) == (_h(10, 30), _h(11, 15))
    assert _bloqueos(motor_concurrente, a) == []
    assert _turnos_activos_dentro_de_un_bloqueo(motor_concurrente, a) == 0


def test_reprogramacion_hacia_otro_profesional_espera_al_bloqueo_del_destino(
    motor_concurrente: Engine,
    fabrica: sessionmaker[Session],
    catalogo_commiteado: Catalogo,
    operador: UsuarioAutenticado,
    pausas: list[Pausa],
) -> None:
    a, b = (p.id for p in catalogo_commiteado.profesionales)
    t2 = _turno_confirmado(fabrica, catalogo_commiteado, b, _h(10, 30))
    pausa_bloqueo = _pausa(pausas)
    bloqueo = Hilo(_alta_de_bloqueo(fabrica, operador, a, _h(10), _h(12), pausa=pausa_bloqueo))
    pausa_bloqueo.esperar_detenida()

    cambio = Hilo(_reprogramacion(fabrica, t2.id, SolicitudReprogramacion(profesional_id=a)))
    _esperar_bloqueo(motor_concurrente, "FOR SHARE")
    assert not cambio.terminada.is_set()
    pausa_bloqueo.liberar()
    error = cambio.esperar()
    bloqueo.esperar()

    assert isinstance(error, TurnoInvalidoError), error
    assert error.codigo == "turno_en_bloqueo"
    [turno] = _turnos(motor_concurrente, b)
    assert (turno.id, turno.inicio, turno.fin) == (t2.id, _h(10, 30), _h(11, 15))
    assert _turnos(motor_concurrente, a) == []
    assert len(_bloqueos(motor_concurrente, a)) == 1
    assert _turnos_activos_dentro_de_un_bloqueo(motor_concurrente, a) == 0
