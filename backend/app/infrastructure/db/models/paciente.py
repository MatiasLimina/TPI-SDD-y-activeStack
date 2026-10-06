from sqlalchemy import Boolean, String, text
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.db.base import Base
from app.infrastructure.db.models.mixins import CatalogoMixin


class Paciente(CatalogoMixin, Base):
    __tablename__ = "paciente"

    nombre: Mapped[str] = mapped_column(String(100))
    apellido: Mapped[str] = mapped_column(String(100))
    documento: Mapped[str] = mapped_column(String(20), unique=True)
    telefono: Mapped[str] = mapped_column(String(30))
    email: Mapped[str | None] = mapped_column(String(254))
    activo: Mapped[bool] = mapped_column(Boolean, server_default=text("true"))
