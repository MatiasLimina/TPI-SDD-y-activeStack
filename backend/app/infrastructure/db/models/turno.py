import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Integer, String, text
from sqlalchemy.dialects.postgresql import UUID, ExcludeConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.db.base import Base
from app.infrastructure.db.models.mixins import CatalogoMixin

_ACTIVO = "estado <> 'cancelado'"
_RANGO = text("tstzrange(inicio, fin, '[)')")


class Turno(CatalogoMixin, Base):
    """Turno. Las exclusiones son la garantía de no solape (RN-AG-09); los nombres son contrato."""

    __tablename__ = "turno"
    __table_args__ = (
        CheckConstraint("estado IN ('programado', 'cancelado')", name="estado_valido"),
        CheckConstraint("fin > inicio", name="fin_mayor"),
        ExcludeConstraint(
            ("profesional_id", "="),
            (_RANGO, "&&"),
            name="turno_sin_solape_profesional",
            using="gist",
            where=text(_ACTIVO),
        ),
        ExcludeConstraint(
            ("sillon_id", "="),
            (_RANGO, "&&"),
            name="turno_sin_solape_sillon",
            using="gist",
            where=text(f"{_ACTIVO} AND sillon_id IS NOT NULL"),
        ),
        ExcludeConstraint(
            ("paciente_id", "="),
            (_RANGO, "&&"),
            name="turno_sin_solape_paciente",
            using="gist",
            where=text(_ACTIVO),
        ),
        Index("ix_turno_profesional_id_inicio", "profesional_id", "inicio"),
        Index("ix_turno_sillon_id_inicio", "sillon_id", "inicio"),
        Index("ix_turno_creado_por", "creado_por"),
    )

    profesional_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("profesional.id", ondelete="RESTRICT")
    )
    paciente_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("paciente.id", ondelete="RESTRICT")
    )
    prestacion_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("prestacion.id", ondelete="RESTRICT")
    )
    sillon_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("sillon.id", ondelete="RESTRICT")
    )
    inicio: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    fin: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    duracion_min: Mapped[int] = mapped_column(Integer)
    estado: Mapped[str] = mapped_column(String(20), server_default="programado")
    motivo_cancelacion: Mapped[str | None] = mapped_column(String(255))
    creado_por: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("usuario.id", ondelete="RESTRICT")
    )
