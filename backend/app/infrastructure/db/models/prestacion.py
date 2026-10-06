from sqlalchemy import Boolean, CheckConstraint, Integer, String, text
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.db.base import Base
from app.infrastructure.db.models.mixins import CatalogoMixin


class Prestacion(CatalogoMixin, Base):
    __tablename__ = "prestacion"
    __table_args__ = (CheckConstraint("duracion_min > 0", name="duracion_min_positiva"),)

    nombre: Mapped[str] = mapped_column(String(100), unique=True)
    duracion_min: Mapped[int] = mapped_column(Integer)
    requiere_sillon: Mapped[bool] = mapped_column(Boolean, server_default=text("true"))
    activa: Mapped[bool] = mapped_column(Boolean, server_default=text("true"))
