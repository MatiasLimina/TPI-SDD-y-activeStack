"""Acceso a datos de los recordatorios.

No hace `commit` ni `rollback` salvo los métodos explícitos que usa el procesador del worker:
dentro de un caso de uso de turnos, la transacción es del caso de uso.
"""

from datetime import datetime
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.domain.recordatorios import EstadoRecordatorio, RecordatorioRegistrado
from app.domain.time import to_utc
from app.infrastructure.db.models import Recordatorio


class RepositorioRecordatorios:
    def __init__(self, session: Session) -> None:
        self._session = session

    def crear_pendiente(self, turno_id: UUID, programado_para: datetime, canal: str) -> UUID:
        """Agrega un recordatorio `pendiente` y hace `flush`: una violación salta antes del commit.

        `programado_para` se persiste en UTC (RN-CU-04).
        """
        recordatorio = Recordatorio(
            turno_id=turno_id,
            programado_para=to_utc(programado_para),
            estado=EstadoRecordatorio.PENDIENTE.value,
            canal=canal,
            intentos=0,
        )
        self._session.add(recordatorio)
        self._session.flush()
        return recordatorio.id

    def cancelar_pendiente(self, turno_id: UUID) -> bool:
        """Pasa a `cancelado` el recordatorio `pendiente` del turno; `True` si había uno.

        No toca `programado_para` ni `intentos`, ni los recordatorios en otro estado.
        """
        resultado = self._session.execute(
            update(Recordatorio)
            .where(
                Recordatorio.turno_id == turno_id,
                Recordatorio.estado == EstadoRecordatorio.PENDIENTE.value,
            )
            .values(estado=EstadoRecordatorio.CANCELADO.value)
            .execution_options(synchronize_session="fetch")
        )
        return resultado.rowcount > 0

    def listar_pendientes(self) -> list[RecordatorioRegistrado]:
        """Recordatorios `pendiente` por `programado_para` (usa el índice parcial)."""
        filas = self._session.scalars(
            select(Recordatorio)
            .where(Recordatorio.estado == EstadoRecordatorio.PENDIENTE.value)
            .order_by(Recordatorio.programado_para, Recordatorio.id)
            .execution_options(populate_existing=True)
        )
        return [_a_registrado(fila) for fila in filas]


def _a_registrado(fila: Recordatorio) -> RecordatorioRegistrado:
    return RecordatorioRegistrado(
        id=fila.id,
        turno_id=fila.turno_id,
        programado_para=to_utc(fila.programado_para),
        estado=EstadoRecordatorio(fila.estado),
        canal=fila.canal,
        intentos=fila.intentos,
    )
