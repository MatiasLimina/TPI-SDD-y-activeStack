import uuid

from sqlalchemy import Boolean, CheckConstraint, ForeignKey, Index, String, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.db.base import Base
from app.infrastructure.db.models.mixins import CatalogoMixin


class Usuario(CatalogoMixin, Base):
    """Cuenta del sistema. La integridad (rol, email normalizado, un activo por profesional)
    vive en la base; los nombres de las restricciones son contrato (DD-24)."""

    __tablename__ = "usuario"
    __table_args__ = (
        CheckConstraint("rol IN ('recepcionista', 'odontologo')", name="rol_valido"),
        CheckConstraint(
            "(rol = 'odontologo') = (profesional_id IS NOT NULL)", name="profesional_segun_rol"
        ),
        CheckConstraint("email = lower(btrim(email)) AND email <> ''", name="email_normalizado"),
        Index("ix_usuario_profesional_id", "profesional_id"),
        Index(
            "uq_usuario_profesional_activo",
            "profesional_id",
            unique=True,
            postgresql_where=text("activo"),
        ),
    )

    email: Mapped[str] = mapped_column(String(254), unique=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    rol: Mapped[str] = mapped_column(String(20))
    profesional_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("profesional.id", ondelete="RESTRICT")
    )
    activo: Mapped[bool] = mapped_column(Boolean, server_default=text("true"))
