import uuid
from datetime import time

from sqlalchemy import CheckConstraint, ForeignKey, SmallInteger, Time, text
from sqlalchemy.dialects.postgresql import UUID, ExcludeConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.db.base import Base
from app.infrastructure.db.models.mixins import CatalogoMixin

# La fecha es arbitraria: solo sirve para armar un `tsrange` de horas de un mismo día (D5)
_RANGO = text("tsrange(DATE '2000-01-03' + hora_inicio, DATE '2000-01-03' + hora_fin, '[)')")


class HorarioAtencion(CatalogoMixin, Base):
    """Franja de atención semanal de un profesional (`dia_semana`: 0 = lunes … 6 = domingo).

    Las horas son de pared en hora local, sin zona. La exclusión impide franjas superpuestas.
    """

    __tablename__ = "horario_atencion"
    __table_args__ = (
        CheckConstraint("dia_semana BETWEEN 0 AND 6", name="dia_semana_valido"),
        CheckConstraint("hora_fin > hora_inicio", name="hora_fin_mayor"),
        # `mod(...)` en vez de `%`: el `%` del texto SQL se confundiría con un marcador del driver
        CheckConstraint(
            "mod(extract(epoch FROM hora_inicio)::int, 300) = 0 "
            "AND mod(extract(epoch FROM hora_fin)::int, 300) = 0",
            name="grilla",
        ),
        ExcludeConstraint(
            ("profesional_id", "="),
            ("dia_semana", "="),
            (_RANGO, "&&"),
            name="horario_atencion_sin_superposicion",
            using="gist",
        ),
    )

    profesional_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("profesional.id", ondelete="CASCADE")
    )
    dia_semana: Mapped[int] = mapped_column(SmallInteger)
    hora_inicio: Mapped[time] = mapped_column(Time)
    hora_fin: Mapped[time] = mapped_column(Time)
