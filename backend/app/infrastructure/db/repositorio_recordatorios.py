"""Acceso a datos de los recordatorios.

No hace `commit` ni `rollback` salvo los métodos explícitos que usa el procesador del worker:
dentro de un caso de uso de turnos, la transacción es del caso de uso.
"""

from datetime import datetime
from uuid import UUID

from sqlalchemy import case, select, update
from sqlalchemy.orm import Session

from app.domain.recordatorios import (
    MAX_INTENTOS,
    EstadoRecordatorio,
    RecordatorioParaEnvio,
    RecordatorioRegistrado,
)
from app.domain.time import to_utc
from app.infrastructure.db.models import Recordatorio, Turno


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

    def bloquear_para_envio(self, recordatorio_id: UUID) -> RecordatorioParaEnvio | None:
        """Bloquea el turno `FOR SHARE` y después el recordatorio `FOR UPDATE` (D8).

        Es el mismo orden (turno, recordatorio) que siguen cancelar y reprogramar, que bloquean
        el turno `FOR UPDATE` y después tocan el recordatorio: no hay ciclo de espera. Devuelve
        `None` si el recordatorio no existe.
        """
        turno_id = self._session.scalar(
            select(Recordatorio.turno_id).where(Recordatorio.id == recordatorio_id)
        )
        if turno_id is None:
            return None
        turno = self._session.execute(
            select(Turno.estado, Turno.paciente_id, Turno.inicio)
            .where(Turno.id == turno_id)
            .with_for_update(read=True)
        ).one()
        fila = self._session.execute(
            select(Recordatorio)
            .where(Recordatorio.id == recordatorio_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        ).scalar_one()
        return RecordatorioParaEnvio(
            recordatorio=_a_registrado(fila),
            turno_estado=turno.estado,
            paciente_id=turno.paciente_id,
            inicio=to_utc(turno.inicio),
        )

    def marcar_enviado(self, recordatorio_id: UUID) -> None:
        """Suma un intento y pasa a `enviado`."""
        self._actualizar(
            recordatorio_id,
            estado=EstadoRecordatorio.ENVIADO.value,
            intentos=Recordatorio.intentos + 1,
        )

    def registrar_fallo(self, recordatorio_id: UUID) -> RecordatorioRegistrado:
        """Suma un intento; al llegar a `MAX_INTENTOS` pasa a `fallido`. Devuelve el resultado."""
        fila = self._actualizar(
            recordatorio_id,
            estado=case(
                (Recordatorio.intentos + 1 >= MAX_INTENTOS, EstadoRecordatorio.FALLIDO.value),
                else_=Recordatorio.estado,
            ),
            intentos=Recordatorio.intentos + 1,
        )
        return _a_registrado(fila)

    def marcar_cancelado(self, recordatorio_id: UUID) -> None:
        """Pasa a `cancelado` sin sumar intentos."""
        self._actualizar(recordatorio_id, estado=EstadoRecordatorio.CANCELADO.value)

    def commit(self) -> None:
        self._session.commit()

    def rollback(self) -> None:
        self._session.rollback()

    def _actualizar(self, recordatorio_id: UUID, **valores: object) -> Recordatorio:
        return self._session.execute(
            update(Recordatorio)
            .where(Recordatorio.id == recordatorio_id)
            .values(**valores)
            .returning(Recordatorio)
            .execution_options(populate_existing=True)
        ).scalar_one()


def _a_registrado(fila: Recordatorio) -> RecordatorioRegistrado:
    return RecordatorioRegistrado(
        id=fila.id,
        turno_id=fila.turno_id,
        programado_para=to_utc(fila.programado_para),
        estado=EstadoRecordatorio(fila.estado),
        canal=fila.canal,
        intentos=fila.intentos,
    )
