"""Acceso a datos de la auditoría de turnos: solo agregar y leer (la tabla es append-only)."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.auditoria import AccionAuditoria, Instantanea, RegistroAuditoria
from app.domain.time import to_utc
from app.infrastructure.db.models import TurnoAuditoria


class RepositorioAuditoria:
    """No hace `commit` ni `rollback`: la transacción es del caso de uso que audita."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def registrar(
        self,
        turno_id: UUID,
        usuario_id: UUID,
        accion: AccionAuditoria,
        previos: Instantanea | None,
        nuevos: Instantanea,
        ocurrido_en: datetime,
    ) -> None:
        """Agrega el registro y hace `flush`: una violación de la base salta acá, antes del commit.

        `ocurrido_en` se persiste en UTC (RN-CU-04).
        """
        self._session.add(
            TurnoAuditoria(
                turno_id=turno_id,
                usuario_id=usuario_id,
                accion=accion.value,
                valores_previos=previos,
                valores_nuevos=nuevos,
                ocurrido_en=to_utc(ocurrido_en),
            )
        )
        self._session.flush()

    def listar_por_turno(self, turno_id: UUID) -> list[RegistroAuditoria]:
        """Registros del turno por orden de inserción (`id`), que no depende del reloj."""
        filas = self._session.scalars(
            select(TurnoAuditoria)
            .where(TurnoAuditoria.turno_id == turno_id)
            .order_by(TurnoAuditoria.id)
            .execution_options(populate_existing=True)
        )
        return [_a_registro(fila) for fila in filas]


def _a_registro(fila: TurnoAuditoria) -> RegistroAuditoria:
    return RegistroAuditoria(
        id=fila.id,
        turno_id=fila.turno_id,
        usuario_id=fila.usuario_id,
        accion=AccionAuditoria(fila.accion),
        valores_previos=fila.valores_previos,
        valores_nuevos=fila.valores_nuevos,
        ocurrido_en=to_utc(fila.ocurrido_en),
    )
