"""Fábricas de catálogo ficticio para tests de turnos (solo datos inventados)."""

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from itertools import count

from sqlalchemy.orm import Session

from app.infrastructure.db.models import Paciente, Prestacion, Profesional, Sillon, Turno

_secuencia = count(1)


@dataclass
class Catalogo:
    profesionales: list[Profesional]
    sillones: list[Sillon]
    pacientes: list[Paciente]
    limpieza: Prestacion  # 45 min, requiere sillón
    consulta: Prestacion  # 30 min, no requiere sillón


def crear_catalogo(session: Session) -> Catalogo:
    """Dos profesionales, dos sillones, dos pacientes y dos prestaciones, con nombres únicos."""
    n = next(_secuencia)
    profesionales = [
        Profesional(nombre=f"Ana{n}", apellido="Ficticia"),
        Profesional(nombre=f"Beto{n}", apellido="Ficticio"),
    ]
    sillones = [Sillon(nombre=f"Sillon {n}-{i}") for i in (1, 2)]
    pacientes = [
        Paciente(
            nombre=f"Paula{n}",
            apellido="Ficticia",
            documento=f"FIC-{n}-1",
            telefono="+54 11 5555-0001",
        ),
        Paciente(
            nombre=f"Quique{n}",
            apellido="Ficticio",
            documento=f"FIC-{n}-2",
            telefono="+54 11 5555-0002",
        ),
    ]
    limpieza = Prestacion(nombre=f"Limpieza {n}", duracion_min=45)
    consulta = Prestacion(nombre=f"Consulta {n}", duracion_min=30, requiere_sillon=False)
    session.add_all([*profesionales, *sillones, *pacientes, limpieza, consulta])
    session.flush()
    return Catalogo(profesionales, sillones, pacientes, limpieza, consulta)


INICIO_BASE = datetime(2026, 10, 8, 13, 0, tzinfo=UTC)  # 10:00 hora local


def crear_turno(session: Session, catalogo: Catalogo, *, desplazamiento_min: int = 0) -> Turno:
    """Turno `programado` de 45 min insertado directo (sin casos de uso ni auditoría)."""
    inicio = INICIO_BASE + timedelta(minutes=desplazamiento_min)
    turno = Turno(
        profesional_id=catalogo.profesionales[0].id,
        sillon_id=catalogo.sillones[0].id,
        paciente_id=catalogo.pacientes[0].id,
        prestacion_id=catalogo.limpieza.id,
        inicio=inicio,
        fin=inicio + timedelta(minutes=45),
        duracion_min=45,
    )
    session.add(turno)
    session.flush()
    return turno
