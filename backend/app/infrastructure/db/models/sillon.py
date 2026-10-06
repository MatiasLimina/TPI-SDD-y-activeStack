from sqlalchemy import Boolean, String, text
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.db.base import Base
from app.infrastructure.db.models.mixins import CatalogoMixin


class Sillon(CatalogoMixin, Base):
    __tablename__ = "sillon"

    nombre: Mapped[str] = mapped_column(String(50), unique=True)
    activo: Mapped[bool] = mapped_column(Boolean, server_default=text("true"))
