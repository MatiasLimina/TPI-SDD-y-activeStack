import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Integer, String, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.db.base import Base
from app.infrastructure.db.models.mixins import CatalogoMixin

_PENDIENTE = text("estado = 'pendiente'")


class Recordatorio(CatalogoMixin, Base):
    """Recordatorio previo a un turno (RN-NO-01..05). La base es la fuente de verdad del estado.

    Los nombres de las restricciones son contrato (migración 006). `programado_para` y `canal`
    no tienen default: los informa la aplicación con su reloj inyectado.
    """

    __tablename__ = "recordatorio"
    __table_args__ = (
        CheckConstraint(
            "estado IN ('pendiente', 'enviado', 'fallido', 'cancelado')", name="estado_valido"
        ),
        CheckConstraint("canal IN ('mock')", name="canal_valido"),
        CheckConstraint("intentos BETWEEN 0 AND 3", name="intentos_rango"),
        CheckConstraint(
            "(estado <> 'fallido' OR intentos = 3) AND (estado <> 'enviado' OR intentos >= 1)",
            name="intentos_segun_estado",
        ),
        Index(
            "ux_recordatorio_turno_pendiente",
            "turno_id",
            unique=True,
            postgresql_where=_PENDIENTE,
        ),
        Index("ix_recordatorio_turno_id", "turno_id"),
        Index(
            "ix_recordatorio_pendiente_programado_para",
            "programado_para",
            postgresql_where=_PENDIENTE,
        ),
    )

    turno_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("turno.id", ondelete="RESTRICT")
    )
    programado_para: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    estado: Mapped[str] = mapped_column(String(20), server_default="pendiente")
    canal: Mapped[str] = mapped_column(String(20))
    intentos: Mapped[int] = mapped_column(Integer, server_default=text("0"))
