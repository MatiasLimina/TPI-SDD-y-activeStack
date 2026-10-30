import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import BigInteger, CheckConstraint, DateTime, ForeignKey, Identity, Index, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.db.base import Base

# none_as_null: un `None` de Python es NULL de SQL, no el JSON `null` (que rompería el CHECK
# de coherencia entre acción y valores_previos y esquivaría el NOT NULL de valores_nuevos).
_JSONB = JSONB(none_as_null=True)


class TurnoAuditoria(Base):
    """Registro append-only de un cambio de turno (RN-CU-01).

    No usa `CatalogoMixin`: nunca se actualiza, así que no tiene `actualizado_en`. La base
    rechaza UPDATE, DELETE y TRUNCATE con triggers (migración 005; no se declaran acá). Los
    nombres de las restricciones son contrato. `ocurrido_en` no tiene default: lo informa la
    aplicación con su reloj inyectado.
    """

    __tablename__ = "turno_auditoria"
    __table_args__ = (
        CheckConstraint("accion IN ('crear', 'reprogramar', 'cancelar')", name="accion_valida"),
        CheckConstraint(
            "(accion = 'crear') = (valores_previos IS NULL)", name="previos_segun_accion"
        ),
        Index("ix_turno_auditoria_turno_id", "turno_id", "id"),
        Index("ix_turno_auditoria_usuario_id", "usuario_id"),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    turno_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("turno.id", ondelete="RESTRICT")
    )
    usuario_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("usuario.id", ondelete="RESTRICT")
    )
    accion: Mapped[str] = mapped_column(String(20))
    valores_previos: Mapped[dict[str, Any] | None] = mapped_column(_JSONB)
    valores_nuevos: Mapped[dict[str, Any]] = mapped_column(_JSONB)
    ocurrido_en: Mapped[datetime] = mapped_column(DateTime(timezone=True))
