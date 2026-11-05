"""Acceso a datos de los bloqueos de agenda: lock del profesional, solapes `[)` y consultas."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.bloqueos import TurnoAfectado
from app.domain.turnos import Intervalo
from app.infrastructure.db.models import Bloqueo, Profesional, Turno


class RepositorioBloqueos:
    def __init__(self, session: Session) -> None:
        self._session = session

    def bloquear_profesional(self, profesional_id: UUID) -> Profesional | None:
        """`FOR NO KEY UPDATE` sobre el profesional (activo o no), antes de leer turnos (D13).

        Choca con el `FOR SHARE` que toman el alta y la reprogramación de turnos al cargar sus
        referencias; no choca con el `FOR KEY SHARE` de las FK. `None` si no existe.
        """
        return self._session.get(
            Profesional,
            profesional_id,
            with_for_update={"key_share": True},
            populate_existing=True,
        )

    def turnos_activos_en(self, profesional_id: UUID, intervalo: Intervalo) -> list[TurnoAfectado]:
        """Turnos no cancelados del profesional que pisan `intervalo`, por `inicio` e `id`."""
        consulta = (
            select(Turno.id, Turno.inicio, Turno.fin)
            .where(
                Turno.profesional_id == profesional_id,
                Turno.estado != "cancelado",
                Turno.inicio < intervalo.fin,
                Turno.fin > intervalo.inicio,
            )
            .order_by(Turno.inicio, Turno.id)
        )
        return [
            TurnoAfectado(id, inicio, fin) for id, inicio, fin in self._session.execute(consulta)
        ]

    def bloqueos_en(self, profesional_id: UUID, intervalo: Intervalo) -> bool:
        """Si el profesional tiene algún bloqueo que pise `intervalo` (RN-AG-06)."""
        consulta = select(
            select(Bloqueo.id)
            .where(
                Bloqueo.profesional_id == profesional_id,
                Bloqueo.inicio < intervalo.fin,
                Bloqueo.fin > intervalo.inicio,
            )
            .exists()
        )
        return bool(self._session.scalar(consulta))

    def listar(self, profesional_id: UUID | None) -> list[Bloqueo]:
        """Bloqueos de un profesional, o de todos si `None`, por `inicio` e `id`."""
        consulta = select(Bloqueo).order_by(Bloqueo.inicio, Bloqueo.id)
        if profesional_id is not None:
            consulta = consulta.where(Bloqueo.profesional_id == profesional_id)
        return list(self._session.scalars(consulta))

    def obtener(self, bloqueo_id: UUID) -> Bloqueo | None:
        return self._session.get(Bloqueo, bloqueo_id)

    def agregar(self, bloqueo: Bloqueo) -> None:
        self._session.add(bloqueo)
        self._session.flush()

    def eliminar(self, bloqueo: Bloqueo) -> None:
        self._session.delete(bloqueo)
        self._session.flush()

    def commit(self) -> None:
        self._session.commit()

    def rollback(self) -> None:
        self._session.rollback()
