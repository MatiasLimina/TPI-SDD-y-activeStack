"""Recordatorios: programación en los casos de uso de turnos y procesamiento en el worker.

El `ProgramadorRecordatorios` se enchufa como observador, igual que el auditor de C-07: corre
dentro de la transacción del cambio y antes del commit, así que si registrar el recordatorio
falla el caso de uso revierte el cambio. La programación es opcional a nivel de caso de uso:
todo punto de entrada que modifique turnos (la API) debe registrar al programador.
"""

import logging
from collections.abc import Callable
from contextlib import AbstractContextManager
from datetime import datetime, timedelta
from enum import StrEnum
from uuid import UUID

from sqlalchemy.orm import Session

from app.application.validacion_turno import Reloj
from app.domain.notificaciones import NotificationSender, armar_mensaje
from app.domain.recordatorios import (
    ColaRecordatorios,
    EstadoRecordatorio,
    calcular_programacion,
)
from app.domain.time import to_utc
from app.domain.turnos import TurnoCreado, TurnoRegistrado
from app.infrastructure.db.repositorio_recordatorios import RepositorioRecordatorios

logger = logging.getLogger(__name__)


class ProgramadorRecordatorios:
    """Crea, cancela y reprograma el recordatorio de un turno junto con el cambio del turno.

    Comparte la sesión del request: el recordatorio vive en la misma transacción que el turno y
    su auditoría. Los recordatorios nuevos quedan anotados en `por_publicar` y se encolan con
    `publicar` recién después del commit (D6).
    """

    def __init__(
        self,
        repositorio: RepositorioRecordatorios,
        reloj: Reloj,
        anticipacion: timedelta,
        canal: str = "mock",
    ) -> None:
        self._repositorio = repositorio
        self._reloj = reloj
        self._anticipacion = anticipacion
        self._canal = canal
        self.por_publicar: list[tuple[UUID, datetime]] = []

    def al_crear(self, creado: TurnoCreado) -> None:
        self._programar(creado.id, creado.inicio)

    def al_reprogramar(self, anterior: TurnoRegistrado, nuevo: TurnoRegistrado) -> None:
        """Si cambia el inicio, cancela el pendiente y crea uno nuevo si corresponde (D5).

        Un recordatorio `enviado` o `fallido` es terminal y no se toca: el turno recibe además
        uno nuevo para la fecha nueva. Si el inicio no cambia, no se toca nada.
        """
        if anterior.inicio == nuevo.inicio:
            return
        self._repositorio.cancelar_pendiente(nuevo.id)
        self._programar(nuevo.id, nuevo.inicio)

    def al_cancelar(self, anterior: TurnoRegistrado, nuevo: TurnoRegistrado) -> None:
        """Cancela el recordatorio pendiente; no hay nada que publicar (el worker lo descarta)."""
        self._repositorio.cancelar_pendiente(nuevo.id)

    def publicar(self, cola: ColaRecordatorios) -> None:
        """Encola los recordatorios creados; llamar solo después del commit.

        Si la cola no responde no se propaga el error: el turno ya está confirmado y el
        recordatorio sigue `pendiente` en la base, que el worker re-encola al iniciar (D11).
        """
        pendientes, self.por_publicar = self.por_publicar, []
        for recordatorio_id, programado_para in pendientes:
            try:
                cola.encolar(recordatorio_id, programado_para)
            except Exception as error:
                logger.warning(
                    "no se pudo encolar el recordatorio %s (%s)",
                    recordatorio_id,
                    type(error).__name__,
                )

    def _programar(self, turno_id: UUID, inicio: datetime) -> None:
        programado_para = calcular_programacion(
            to_utc(inicio), to_utc(self._reloj()), self._anticipacion
        )
        if programado_para is None:
            return
        recordatorio_id = self._repositorio.crear_pendiente(turno_id, programado_para, self._canal)
        self.por_publicar.append((recordatorio_id, programado_para))


SesionesFactory = Callable[[], AbstractContextManager[Session]]
"""Abre una sesión por unidad de trabajo (en el worker, `sessionmaker(...)`)."""

LIMITE_POR_CICLO = 100


class ResultadoProcesamiento(StrEnum):
    DESCARTADO = "descartado"
    CANCELADO = "cancelado"
    ENVIADO = "enviado"


class ProcesarRecordatorio:
    """Procesa un recordatorio vencido en una transacción (D8)."""

    def __init__(
        self,
        sesiones: SesionesFactory,
        cola: ColaRecordatorios,
        sender: NotificationSender,
        consultorio: str,
        zona: str,
    ) -> None:
        self._sesiones = sesiones
        self._cola = cola
        self._sender = sender
        self._consultorio = consultorio
        self._zona = zona

    def procesar(self, recordatorio_id: UUID, ahora: datetime) -> ResultadoProcesamiento:
        with self._sesiones() as session:
            repositorio = RepositorioRecordatorios(session)
            try:
                para_envio = repositorio.bloquear_para_envio(recordatorio_id)
                if (
                    para_envio is None
                    or para_envio.recordatorio.estado is not EstadoRecordatorio.PENDIENTE
                ):
                    repositorio.commit()
                    return ResultadoProcesamiento.DESCARTADO
                if para_envio.turno_estado != "programado":
                    repositorio.marcar_cancelado(recordatorio_id)
                    repositorio.commit()
                    return ResultadoProcesamiento.CANCELADO
                mensaje = armar_mensaje(
                    recordatorio_id,
                    para_envio.paciente_id,
                    para_envio.inicio,
                    self._consultorio,
                    self._zona,
                )
                self._sender.enviar(mensaje)
                repositorio.marcar_enviado(recordatorio_id)
                repositorio.commit()
            except Exception:
                repositorio.rollback()
                raise
        return ResultadoProcesamiento.ENVIADO


class ReencolarPendientes:
    """Vuelve a encolar todos los recordatorios `pendiente` de la base (D11, idempotente)."""

    def __init__(self, sesiones: SesionesFactory, cola: ColaRecordatorios) -> None:
        self._sesiones = sesiones
        self._cola = cola

    def ejecutar(self) -> int:
        with self._sesiones() as session:
            pendientes = RepositorioRecordatorios(session).listar_pendientes()
        for pendiente in pendientes:
            self._cola.encolar(pendiente.id, pendiente.programado_para)
        return len(pendientes)


class WorkerRecordatorios:
    """`iniciar()` re-encola; `ciclo(ahora)` toma los vencidos y los procesa."""

    def __init__(
        self,
        cola: ColaRecordatorios,
        procesador: ProcesarRecordatorio,
        reencolar: ReencolarPendientes,
        limite: int = LIMITE_POR_CICLO,
    ) -> None:
        self._cola = cola
        self._procesador = procesador
        self._reencolar = reencolar
        self._limite = limite

    def iniciar(self) -> int:
        return self._reencolar.ejecutar()

    def ciclo(self, ahora: datetime) -> int:
        """Procesa los recordatorios vencidos a `ahora`; devuelve cuántos tomó de la cola."""
        vencidos = self._cola.tomar_vencidos(ahora, self._limite)
        for recordatorio_id in vencidos:
            self._procesador.procesar(recordatorio_id, ahora)
        return len(vencidos)
