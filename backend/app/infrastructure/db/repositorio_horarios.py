"""Acceso a datos de los horarios de atención: franjas por profesional y bloqueo de escritura."""

from collections.abc import Mapping
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.domain.horarios import Franja, FranjaSuperpuestaError, se_superponen
from app.infrastructure.db.models import HorarioAtencion, Profesional

SQLSTATE_EXCLUSION = "23P01"
# El nombre de la exclusión (migración 007) es contrato: de él se deduce la superposición.
EXCLUSION_SUPERPOSICION = "horario_atencion_sin_superposicion"


def _franja(horario: HorarioAtencion) -> Franja:
    return Franja(horario.dia_semana, horario.hora_inicio, horario.hora_fin)


class RepositorioHorarios:
    def __init__(self, session: Session) -> None:
        self._session = session
        self._nuevos: list[HorarioAtencion] = []
        self._cambios: list[tuple[HorarioAtencion, Mapping[str, Any]]] = []

    def bloquear_profesional(self, profesional_id: UUID) -> Profesional | None:
        """`FOR NO KEY UPDATE` sobre el profesional: serializa las escrituras de sus franjas."""
        return self._session.get(
            Profesional,
            profesional_id,
            with_for_update={"key_share": True},
            populate_existing=True,
        )

    def obtener_profesional(self, profesional_id: UUID) -> Profesional | None:
        """Lectura sin bloqueo: para consultar, activo o no."""
        return self._session.get(Profesional, profesional_id)

    def listar(self, profesional_id: UUID) -> list[HorarioAtencion]:
        consulta = (
            select(HorarioAtencion)
            .where(HorarioAtencion.profesional_id == profesional_id)
            .order_by(HorarioAtencion.dia_semana, HorarioAtencion.hora_inicio)
        )
        return list(self._session.scalars(consulta))

    def franjas_del_dia(self, profesional_id: UUID, dia_semana: int) -> list[Franja]:
        consulta = (
            select(HorarioAtencion)
            .where(
                HorarioAtencion.profesional_id == profesional_id,
                HorarioAtencion.dia_semana == dia_semana,
            )
            .order_by(HorarioAtencion.hora_inicio)
        )
        return [_franja(h) for h in self._session.scalars(consulta)]

    def obtener(self, profesional_id: UUID, horario_id: UUID) -> HorarioAtencion | None:
        """La franja `horario_id` solo si es del profesional pedido."""
        consulta = select(HorarioAtencion).where(
            HorarioAtencion.id == horario_id, HorarioAtencion.profesional_id == profesional_id
        )
        return self._session.scalars(consulta).one_or_none()

    def superpuestas(
        self, profesional_id: UUID, franja: Franja, excluir_id: UUID | None
    ) -> list[HorarioAtencion]:
        """Franjas del profesional en el día de `franja` que la pisan, sin contar `excluir_id`."""
        consulta = select(HorarioAtencion).where(
            HorarioAtencion.profesional_id == profesional_id,
            HorarioAtencion.dia_semana == franja.dia_semana,
        )
        if excluir_id is not None:
            consulta = consulta.where(HorarioAtencion.id != excluir_id)
        return [h for h in self._session.scalars(consulta) if se_superponen(_franja(h), franja)]

    def agregar(self, horario: HorarioAtencion) -> None:
        """Deja la franja para el próximo `guardar`; entra a la sesión dentro de su SAVEPOINT."""
        self._nuevos.append(horario)

    def modificar(self, horario: HorarioAtencion, cambios: Mapping[str, Any]) -> None:
        """Deja `cambios` para el próximo `guardar`; se aplican dentro de su SAVEPOINT."""
        self._cambios.append((horario, cambios))

    def eliminar(self, horario: HorarioAtencion) -> None:
        self._session.delete(horario)
        self._session.flush()

    def guardar(self) -> None:
        """`flush` en un SAVEPOINT que traduce la exclusión a `FranjaSuperpuestaError`.

        El SAVEPOINT deja la sesión usable tras el rechazo: solo se revierte esta escritura.
        """
        nuevos, self._nuevos = self._nuevos, []
        cambios, self._cambios = self._cambios, []
        try:
            with self._session.begin_nested():
                self._session.add_all(nuevos)
                for horario, valores in cambios:
                    for campo, valor in valores.items():
                        setattr(horario, campo, valor)
                self._session.flush()
        except IntegrityError as error:
            if getattr(error.orig, "sqlstate", None) != SQLSTATE_EXCLUSION:
                raise
            constraint = getattr(getattr(error.orig, "diag", None), "constraint_name", None)
            if constraint != EXCLUSION_SUPERPOSICION:
                raise
            raise FranjaSuperpuestaError from error

    def commit(self) -> None:
        self._session.commit()

    def rollback(self) -> None:
        self._session.rollback()
