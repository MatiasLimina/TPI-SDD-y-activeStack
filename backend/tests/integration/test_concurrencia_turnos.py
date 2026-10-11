"""Concurrencia (DD-18): N altas simultáneas, cada una en su conexión, contra PostgreSQL real."""

import threading
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import Engine, func, select
from sqlalchemy.orm import Session, sessionmaker

from app.application.crear_turno import CrearTurno, SolicitudTurno
from app.domain.turnos import SolapamientoError, TurnoCreado
from app.infrastructure.db.models import Turno
from app.infrastructure.db.repositorio_turnos import RepositorioTurnos
from tests.integration.factories import Catalogo

AHORA = datetime(2026, 10, 7, 12, 0, tzinfo=UTC)
INICIO = datetime(2026, 10, 8, 13, 0, tzinfo=UTC)
HILOS = 10


def _alta_concurrente(motor: Engine, catalogo: Catalogo) -> list[Any]:
    fabrica = sessionmaker(bind=motor, expire_on_commit=False)
    barrera = threading.Barrier(HILOS)
    resultados: list[Any] = [None] * HILOS

    def trabajar(indice: int) -> None:
        with fabrica() as sesion:
            caso = CrearTurno(RepositorioTurnos(sesion), reloj=lambda: AHORA)
            solicitud = SolicitudTurno(
                profesional_id=catalogo.profesionales[0].id,
                paciente_id=catalogo.pacientes[indice % 2].id,
                prestacion_id=catalogo.limpieza.id,
                sillon_id=catalogo.sillones[0].id,
                inicio=INICIO,
            )
            barrera.wait(timeout=10)
            try:
                resultados[indice] = caso.ejecutar(solicitud)
            except Exception as error:  # se inspecciona en el hilo principal
                resultados[indice] = error

    hilos = [threading.Thread(target=trabajar, args=(i,)) for i in range(HILOS)]
    for hilo in hilos:
        hilo.start()
    for hilo in hilos:
        hilo.join(timeout=30)
    return resultados


def test_altas_simultaneas_del_mismo_horario_dejan_exactamente_un_turno(
    motor_concurrente: Engine, catalogo_commiteado: Catalogo
) -> None:
    resultados = _alta_concurrente(motor_concurrente, catalogo_commiteado)

    exitos = [r for r in resultados if isinstance(r, TurnoCreado)]
    conflictos = [r for r in resultados if isinstance(r, SolapamientoError)]
    inesperados = [r for r in resultados if r is not None and r not in exitos + conflictos]
    assert inesperados == []
    assert len(exitos) == 1
    assert len(conflictos) == HILOS - 1
    with Session(motor_concurrente) as sesion:
        activos = sesion.scalar(
            select(func.count())
            .select_from(Turno)
            .where(
                Turno.profesional_id == catalogo_commiteado.profesionales[0].id,
                Turno.estado != "cancelado",
            )
        )
    assert activos == 1
