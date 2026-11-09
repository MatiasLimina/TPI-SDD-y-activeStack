"""Caso de uso de la consulta de agenda por rango de días locales (US-008, RN-AU-02)."""

from dataclasses import dataclass
from datetime import date
from typing import Protocol
from uuid import UUID

from app.domain.agenda import (
    TurnoDeAgenda,
    rango_local_a_intervalo,
    resolver_profesional_agenda,
)
from app.domain.turnos import Intervalo
from app.domain.usuarios import UsuarioAutenticado
from app.infrastructure.db.models import Bloqueo


class LecturaTurnos(Protocol):
    def listar_en(
        self,
        intervalo: Intervalo,
        profesional_id: UUID | None = None,
        sillon_id: UUID | None = None,
    ) -> list[TurnoDeAgenda]: ...


class LecturaBloqueos(Protocol):
    def listar_en(
        self, intervalo: Intervalo, profesional_id: UUID | None = None
    ) -> list[Bloqueo]: ...


@dataclass(frozen=True)
class AgendaConsultada:
    turnos: list[TurnoDeAgenda]
    bloqueos: list[Bloqueo]


class ConsultarAgenda:
    def __init__(self, turnos: LecturaTurnos, bloqueos: LecturaBloqueos) -> None:
        self._turnos = turnos
        self._bloqueos = bloqueos

    def ejecutar(
        self,
        usuario: UsuarioAutenticado,
        desde: date,
        hasta: date,
        profesional_id: UUID | None,
        sillon_id: UUID | None,
    ) -> AgendaConsultada:
        """Turnos y bloqueos del rango; primero el profesional (403), después el rango (422).

        El sillón filtra solo los turnos: los bloqueos son por profesional (D9).
        """
        profesional_id = resolver_profesional_agenda(usuario, profesional_id)
        intervalo = rango_local_a_intervalo(desde, hasta)
        return AgendaConsultada(
            turnos=self._turnos.listar_en(intervalo, profesional_id, sillon_id),
            bloqueos=self._bloqueos.listar_en(intervalo, profesional_id),
        )
