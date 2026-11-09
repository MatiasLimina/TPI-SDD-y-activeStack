"""Reglas de dominio de la consulta de agenda: puras, sin base de datos ni FastAPI."""

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from uuid import UUID
from zoneinfo import ZoneInfo

from app.domain.horarios import ProfesionalAjenoError
from app.domain.time import DEFAULT_TIMEZONE, to_utc
from app.domain.turnos import Intervalo
from app.domain.usuarios import Rol, UsuarioAutenticado

MAX_DIAS_AGENDA = 7
MENSAJE_RANGO_INVALIDO = (
    f"hasta debe ser igual o posterior a desde y el rango abarcar a lo sumo {MAX_DIAS_AGENDA} días"
)
MENSAJE_AGENDA_AJENA = "Solo podés consultar tu propia agenda"


@dataclass(frozen=True)
class TurnoDeAgenda:
    """Turno tal como lo muestra la agenda: el estado persistido más el nombre del paciente."""

    id: UUID
    profesional_id: UUID
    paciente_id: UUID
    paciente_nombre: str
    paciente_apellido: str
    prestacion_id: UUID
    sillon_id: UUID | None
    inicio: datetime
    fin: datetime
    duracion_min: int
    estado: str
    creado_por: UUID | None
    motivo_cancelacion: str | None


class RangoInvalidoError(Exception):
    """El rango de la agenda está invertido o supera una semana (se traduce a 422)."""

    def __init__(self, mensaje: str = MENSAJE_RANGO_INVALIDO) -> None:
        super().__init__(mensaje)
        self.codigo = "rango_invalido"
        self.mensaje = mensaje


def rango_local_a_intervalo(desde: date, hasta: date, tz: str = DEFAULT_TIMEZONE) -> Intervalo:
    """Convierte un rango de fechas locales (ambas incluidas) en un Intervalo UTC [).

    Devuelve [desde 00:00 local, hasta + 1 dia 00:00 local), con los instantes en UTC.
    Lanza `RangoInvalidoError` si `hasta < desde` si abarca más de `MAX_DIAS_AGENDA` días
    o si `hasta` es `date.max` (su día siguiente, el fin del intervalo, no es representable).
    """
    if hasta < desde or hasta == date.max or (hasta - desde).days + 1 > MAX_DIAS_AGENDA:
        raise RangoInvalidoError
    zona = ZoneInfo(tz)
    inicio = datetime.combine(desde, time.min, tzinfo=zona)
    fin = datetime.combine(hasta + timedelta(days=1), time.min, tzinfo=zona)
    return Intervalo(inicio=to_utc(inicio), fin=to_utc(fin))


def resolver_profesional_agenda(
    usuario: UsuarioAutenticado, profesional_id: UUID | None
) -> UUID | None:
    """Filtro de profesional efectivo según el rol (RN-AU-02, D10).

    El odontólogo consulta siempre la suya: omite el filtro o informa el propio; otro (exista o
    no) es `ProfesionalAjenoError`. La recepcionista conserva el filtro tal cual (`None` = todos).
    """
    if usuario.rol == Rol.ODONTOLOGO:
        if profesional_id is not None and profesional_id != usuario.profesional_id:
            raise ProfesionalAjenoError(MENSAJE_AGENDA_AJENA)
        return usuario.profesional_id
    return profesional_id
