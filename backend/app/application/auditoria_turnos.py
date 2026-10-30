"""Auditoría de turnos (RN-CU-01): el auditor se enchufa como observador de los casos de uso.

Los observadores corren dentro de la transacción del cambio y antes del commit: si registrar
falla, el caso de uso revierte el cambio. La auditoría es opcional a nivel de caso de uso; todo
punto de entrada que modifique turnos (API, CLI, worker) debe registrar al auditor.
"""

from uuid import UUID

from app.application.validacion_turno import Reloj
from app.domain.auditoria import AccionAuditoria, RegistroAuditoria, instantanea_turno
from app.domain.time import to_utc
from app.domain.turnos import TurnoCreado, TurnoInexistenteError, TurnoRegistrado
from app.infrastructure.db.repositorio_auditoria import RepositorioAuditoria
from app.infrastructure.db.repositorio_turnos import RepositorioTurnos


class AuditorTurnos:
    """Registra quién hizo cada cambio de turno y cuándo, con los valores antes y después.

    `usuario_id` es el usuario autenticado (nunca un valor del body) y el instante sale del
    mismo reloj inyectado que usan las validaciones (no de `now()` de la base).
    """

    def __init__(self, repositorio: RepositorioAuditoria, usuario_id: UUID, reloj: Reloj) -> None:
        self._repositorio = repositorio
        self._usuario_id = usuario_id
        self._reloj = reloj

    def al_crear(self, creado: TurnoCreado) -> None:
        self._registrar(AccionAuditoria.CREAR, None, creado)

    def al_reprogramar(self, anterior: TurnoRegistrado, nuevo: TurnoRegistrado) -> None:
        """Siempre que el caso de uso confirma, también sin cambio efectivo (DD-23a, D10)."""
        self._registrar(AccionAuditoria.REPROGRAMAR, anterior, nuevo)

    def al_cancelar(self, anterior: TurnoRegistrado, nuevo: TurnoRegistrado) -> None:
        self._registrar(AccionAuditoria.CANCELAR, anterior, nuevo)

    def _registrar(
        self,
        accion: AccionAuditoria,
        anterior: TurnoCreado | TurnoRegistrado | None,
        nuevo: TurnoCreado | TurnoRegistrado,
    ) -> None:
        self._repositorio.registrar(
            nuevo.id,
            self._usuario_id,
            accion,
            None if anterior is None else instantanea_turno(anterior),
            instantanea_turno(nuevo),
            to_utc(self._reloj()),
        )


class ConsultarAuditoriaTurno:
    """Historial de auditoría de un turno, en el orden en que ocurrió (solo lectura)."""

    def __init__(
        self, repositorio_turnos: RepositorioTurnos, repositorio_auditoria: RepositorioAuditoria
    ) -> None:
        self._repositorio_turnos = repositorio_turnos
        self._repositorio_auditoria = repositorio_auditoria

    def ejecutar(self, turno_id: UUID) -> list[RegistroAuditoria]:
        """Un turno sin registros (previo a C-07) da lista vacía; uno inexistente, un error."""
        if not self._repositorio_turnos.existe(turno_id):
            raise TurnoInexistenteError(turno_id)
        return self._repositorio_auditoria.listar_por_turno(turno_id)
