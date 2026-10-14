"""Acceso a datos de turnos: carga de referencias, pre-chequeo de solape e inserción."""

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.domain.time import to_utc
from app.domain.turnos import (
    Intervalo,
    Recurso,
    ReferenciaInvalidaError,
    SolapamientoError,
    TurnoCreado,
    TurnoInexistenteError,
    TurnoPropuesto,
    TurnoRegistrado,
)
from app.infrastructure.db.models import Paciente, Prestacion, Profesional, Sillon, Turno

SQLSTATE_EXCLUSION = "23P01"
# El nombre de cada exclusión (migración 003) es contrato: de él se deduce el recurso.
RECURSO_POR_CONSTRAINT: dict[str, Recurso] = {
    "turno_sin_solape_profesional": "profesional",
    "turno_sin_solape_sillon": "sillon",
    "turno_sin_solape_paciente": "paciente",
}


@dataclass(frozen=True)
class Referencias:
    profesional: Profesional
    paciente: Paciente
    prestacion: Prestacion
    sillon: Sillon | None


class RepositorioTurnos:
    def __init__(self, session: Session) -> None:
        self._session = session

    def cargar_referencias(
        self,
        *,
        profesional_id: UUID,
        paciente_id: UUID,
        prestacion_id: UUID,
        sillon_id: UUID | None,
    ) -> Referencias:
        """Carga y valida existencia y actividad. Falla con el primer problema encontrado."""
        profesional = self._activa(Profesional, profesional_id, "profesional", "activo")
        paciente = self._activa(Paciente, paciente_id, "paciente", "activo")
        prestacion = self._activa(Prestacion, prestacion_id, "prestacion", "activa")
        sillon = None if sillon_id is None else self._activa(Sillon, sillon_id, "sillon", "activo")
        return Referencias(profesional, paciente, prestacion, sillon)

    def _activa[T](self, modelo: type[T], id: UUID, nombre: str, flag: str) -> T:
        entidad = self._session.get(modelo, id)
        if entidad is None:
            raise ReferenciaInvalidaError(nombre, "inexistente")
        if not getattr(entidad, flag):
            raise ReferenciaInvalidaError(nombre, "inactiva")
        return entidad

    def commit(self) -> None:
        self._session.commit()

    def rollback(self) -> None:
        self._session.rollback()

    def buscar_conflictos(
        self,
        intervalo: Intervalo,
        *,
        profesional_id: UUID,
        sillon_id: UUID | None,
        paciente_id: UUID,
        excluir_id: UUID | None = None,
    ) -> set[Recurso]:
        """Pre-chequeo en una consulta: recursos que comparten un turno activo solapado.

        `excluir_id` deja afuera al propio turno cuando se está reprogramando.
        """
        compartidos = [Turno.profesional_id == profesional_id, Turno.paciente_id == paciente_id]
        if sillon_id is not None:
            compartidos.append(Turno.sillon_id == sillon_id)
        solapa = func.tstzrange(Turno.inicio, Turno.fin, "[)").op("&&")(
            func.tstzrange(intervalo.inicio, intervalo.fin, "[)")
        )
        consulta = select(Turno.profesional_id, Turno.sillon_id, Turno.paciente_id).where(
            Turno.estado != "cancelado", solapa, or_(*compartidos)
        )
        if excluir_id is not None:
            consulta = consulta.where(Turno.id != excluir_id)
        filas = self._session.execute(consulta).all()
        recursos: set[Recurso] = set()
        for fila_profesional, fila_sillon, fila_paciente in filas:
            if fila_profesional == profesional_id:
                recursos.add("profesional")
            if sillon_id is not None and fila_sillon == sillon_id:
                recursos.add("sillon")
            if fila_paciente == paciente_id:
                recursos.add("paciente")
        return recursos

    def insertar(self, propuesto: TurnoPropuesto) -> TurnoCreado:
        """Persiste el turno (instantes en UTC). Una exclusión violada se traduce a 409.

        El INSERT corre en un SAVEPOINT: si la base lo rechaza solo se deshace ese alta y la
        sesión sigue utilizable; la transacción exterior la cierra quien la abrió.
        """
        turno = Turno(
            profesional_id=propuesto.profesional_id,
            paciente_id=propuesto.paciente_id,
            prestacion_id=propuesto.prestacion_id,
            sillon_id=propuesto.sillon_id,
            inicio=to_utc(propuesto.inicio),
            fin=to_utc(propuesto.fin),
            duracion_min=propuesto.duracion_min,
        )
        try:
            with self._session.begin_nested():
                self._session.add(turno)
                self._session.flush()
        except IntegrityError as error:
            recurso = _recurso_en_conflicto(error)
            if recurso is None:
                raise
            raise SolapamientoError({recurso}) from error
        return TurnoCreado.desde_propuesto(propuesto, id=turno.id)

    def obtener_para_actualizar(self, turno_id: UUID) -> TurnoRegistrado | None:
        """Lee el turno bloqueando su fila (FOR UPDATE) hasta el fin de la transacción.

        Serializa operaciones concurrentes sobre el mismo turno: la segunda espera al commit
        de la primera y relee el estado ya actualizado.
        """
        turno = self._session.scalars(
            select(Turno)
            .where(Turno.id == turno_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        ).one_or_none()
        return None if turno is None else _a_registrado(turno)

    def marcar_cancelado(self, turno_id: UUID, motivo: str | None) -> TurnoRegistrado:
        """Marca como cancelado un turno ya leído con `obtener_para_actualizar` (fila bloqueada).

        La fila no se borra; al dejar de ser activa sale del WHERE de las tres exclusiones y el
        horario queda libre. Sin SAVEPOINT: el valor de estado es fijo y válido.
        """
        turno = self._session.get(Turno, turno_id)
        if turno is None:
            raise TurnoInexistenteError(turno_id)
        turno.estado = "cancelado"
        turno.motivo_cancelacion = motivo
        self._session.flush()
        self._session.refresh(turno)
        return _a_registrado(turno)


def _a_registrado(turno: Turno) -> TurnoRegistrado:
    return TurnoRegistrado(
        id=turno.id,
        profesional_id=turno.profesional_id,
        paciente_id=turno.paciente_id,
        prestacion_id=turno.prestacion_id,
        sillon_id=turno.sillon_id,
        inicio=to_utc(turno.inicio),
        fin=to_utc(turno.fin),
        duracion_min=turno.duracion_min,
        estado=turno.estado,
        motivo_cancelacion=turno.motivo_cancelacion,
        creado_por=turno.creado_por,
    )


def _recurso_en_conflicto(error: IntegrityError) -> Recurso | None:
    if getattr(error.orig, "sqlstate", None) != SQLSTATE_EXCLUSION:
        return None
    constraint = getattr(getattr(error.orig, "diag", None), "constraint_name", None)
    return RECURSO_POR_CONSTRAINT.get(constraint or "")
