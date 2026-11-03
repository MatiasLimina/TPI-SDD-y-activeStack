"""Recordatorios: programación en los casos de uso de turnos y procesamiento en el worker.

El `ProgramadorRecordatorios` se enchufa como observador, igual que el auditor de C-07: corre
dentro de la transacción del cambio y antes del commit, así que si registrar el recordatorio
falla el caso de uso revierte el cambio. La programación es opcional a nivel de caso de uso:
todo punto de entrada que modifique turnos (la API) debe registrar al programador.
"""

import logging
from datetime import datetime, timedelta
from uuid import UUID

from app.application.validacion_turno import Reloj
from app.domain.recordatorios import ColaRecordatorios, calcular_programacion
from app.domain.time import to_utc
from app.domain.turnos import TurnoCreado
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
