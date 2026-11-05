import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.db.base import Base
from app.infrastructure.db.models.mixins import CatalogoMixin


class Bloqueo(CatalogoMixin, Base):
    """Franja `[inicio, fin)` en la que un profesional no atiende (RN-HB-02, `timestamptz` UTC).

    La base garantiza la forma (intervalo, motivo, autor). Que no pise turnos activos (RN-HB-03)
    lo garantiza la aplicación con un lock sobre el profesional (DD-30, D13): no hay restricción
    de exclusión entre tablas.
    """

    __tablename__ = "bloqueo"
    __table_args__ = (
        CheckConstraint("fin > inicio", name="fin_mayor"),
        CheckConstraint("btrim(motivo) <> ''", name="motivo_no_vacio"),
        # Cubre la FK y el listado ordenado por inicio de un profesional
        Index("ix_bloqueo_profesional_id_inicio", "profesional_id", "inicio"),
    )

    profesional_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("profesional.id", ondelete="CASCADE")
    )
    inicio: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    fin: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    motivo: Mapped[str] = mapped_column(String(255))
    creado_por: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("usuario.id", ondelete="RESTRICT")
    )
