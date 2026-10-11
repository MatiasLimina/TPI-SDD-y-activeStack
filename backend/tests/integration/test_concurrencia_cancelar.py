"""Concurrencia: N cancelaciones simultáneas del mismo turno, cada una en su conexión."""

import threading
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import Engine, select
from sqlalchemy.orm import Session, sessionmaker

from app.application.cancelar_turno import CancelarTurno
from app.application.crear_turno import CrearTurno, SolicitudTurno
from app.domain.turnos import TurnoNoCancelableError, TurnoRegistrado
from app.infrastructure.db.models import Turno
from app.infrastructure.db.repositorio_turnos import RepositorioTurnos
from tests.integration.factories import Catalogo

AHORA = datetime(2026, 10, 7, 12, 0, tzinfo=UTC)
INICIO = datetime(2026, 10, 8, 13, 0, tzinfo=UTC)
HILOS = 5


def _crear_turno_commiteado(motor: Engine, catalogo: Catalogo) -> Any:
    with Session(motor) as sesion:
        return (
            CrearTurno(RepositorioTurnos(sesion), reloj=lambda: AHORA)
            .ejecutar(
                SolicitudTurno(
                    profesional_id=catalogo.profesionales[0].id,
                    paciente_id=catalogo.pacientes[0].id,
                    prestacion_id=catalogo.limpieza.id,
                    sillon_id=catalogo.sillones[0].id,
                    inicio=INICIO,
                )
            )
            .id
        )


def _cancelacion_concurrente(motor: Engine, turno_id: Any) -> list[Any]:
    fabrica = sessionmaker(bind=motor, expire_on_commit=False)
    barrera = threading.Barrier(HILOS)
    resultados: list[Any] = [None] * HILOS

    def trabajar(indice: int) -> None:
        with fabrica() as sesion:
            caso = CancelarTurno(RepositorioTurnos(sesion), reloj=lambda: AHORA)
            barrera.wait(timeout=10)
            try:
                resultados[indice] = caso.ejecutar(turno_id, f"motivo-{indice}")
            except Exception as error:  # se inspecciona en el hilo principal
                resultados[indice] = error

    hilos = [threading.Thread(target=trabajar, args=(i,)) for i in range(HILOS)]
    for hilo in hilos:
        hilo.start()
    for hilo in hilos:
        hilo.join(timeout=30)
    return resultados


def test_cancelaciones_simultaneas_del_mismo_turno_dejan_exactamente_un_exito(
    motor_concurrente: Engine, catalogo_commiteado: Catalogo
) -> None:
    turno_id = _crear_turno_commiteado(motor_concurrente, catalogo_commiteado)

    resultados = _cancelacion_concurrente(motor_concurrente, turno_id)

    exitos = [r for r in resultados if isinstance(r, TurnoRegistrado)]
    rechazos = [
        r
        for r in resultados
        if isinstance(r, TurnoNoCancelableError) and r.codigo == "turno_ya_cancelado"
    ]
    inesperados = [r for r in resultados if r is None or r not in exitos + rechazos]
    assert inesperados == []
    assert len(exitos) == 1
    assert len(rechazos) == HILOS - 1
    with Session(motor_concurrente) as sesion:
        estado, motivo = sesion.execute(
            select(Turno.estado, Turno.motivo_cancelacion).where(Turno.id == turno_id)
        ).one()
    assert estado == "cancelado"
    assert motivo == exitos[0].motivo_cancelacion
    assert motivo is not None and motivo.startswith("motivo-")
