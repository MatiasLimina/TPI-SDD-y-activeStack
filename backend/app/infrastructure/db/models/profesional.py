from sqlalchemy import Boolean, String, text
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.db.base import Base
from app.infrastructure.db.models.mixins import CatalogoMixin


class Profesional(CatalogoMixin, Base):
    __tablename__ = "profesional"

    nombre: Mapped[str] = mapped_column(String(100))
    apellido: Mapped[str] = mapped_column(String(100))
    matricula: Mapped[str | None] = mapped_column(String(30), unique=True)
    activo: Mapped[bool] = mapped_column(Boolean, server_default=text("true"))
